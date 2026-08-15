"""Benchmark de precio unitario a partir de los Parquet publicados.

    python src/precios.py                    # descarga los releases y puebla
    python src/precios.py --seco             # calcula y muestra, sin escribir

**Es la función que se cobra.** Todo lo demás del producto —radar, fichas, buscador— se
resuelve con el CSV; el benchmark necesita los ítems, que solo vienen por la ruta JSON y
viven como Parquet en los releases de GitHub. Ver docs/decisiones.md D-002 y docs/datos.md §4.

Lee de los releases, no de Postgres: el detalle nunca entra en la base (invariante 1).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agrega import MESES_SIN_CERRAR, N_MINIMO, corte_estadistico  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "miguelhguerrerov/pliego-datos")
API = "https://api.github.com"
CACHE = Path(".parquet-cache")

# El benchmark mira 24 meses. Once años no aportan: los precios de 2016 no dicen nada
# sobre a cuánto se adjudica hoy, y la ventana corta mantiene los agregados pequeños.
VENTANA_MESES = 24


def _releases() -> list[dict]:
    pet = urllib.request.Request(
        f"{API}/repos/{REPO}/releases?per_page=100",
        headers={"User-Agent": "pliego-datos", "Accept": "application/vnd.github+json"},
    )
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        pet.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(pet, timeout=120) as r:
        return json.loads(r.read().decode())


def meses_de_la_ventana() -> set[tuple[int, int]]:
    """Los 24 meses que terminan en el corte estadístico.

    El corte excluye los últimos 4 meses porque un mes tarda 4 o 5 en cerrar
    (invariante 10). Un benchmark sobre datos a medio llenar sale sesgado.
    """
    anio, mes = corte_estadistico()
    salida = set()
    total = anio * 12 + (mes - 1)
    for k in range(VENTANA_MESES):
        t = total - k
        salida.add((t // 12, t % 12 + 1))
    return salida


def descargar_items(ventana: set[tuple[int, int]]) -> list[dict]:
    """Trae los Parquet de ítems de la ventana. Devuelve las filas."""
    import pyarrow.parquet as pq

    CACHE.mkdir(parents=True, exist_ok=True)
    filas: list[dict] = []
    disponibles = 0
    for rel in _releases():
        for activo in rel.get("assets", []):
            nombre = activo["name"]
            if not nombre.startswith("items_") or not nombre.endswith(".parquet"):
                continue
            partes = nombre[:-8].split("_")
            anio, mes = int(partes[1]), int(partes[2])
            if (anio, mes) not in ventana:
                continue
            disponibles += 1
            destino = CACHE / nombre
            if not destino.exists():
                pet = urllib.request.Request(
                    activo["browser_download_url"], headers={"User-Agent": "pliego-datos"}
                )
                with urllib.request.urlopen(pet, timeout=300) as r:
                    destino.write_bytes(r.read())
            tabla = pq.read_table(destino)
            # Los items del Parquet NO llevan fecha: detalle.py guarda ocid, cpc,
            # cantidad, unidad y precio. El periodo esta en el nombre del archivo, que
            # es por mes. Sin esto, calcular() devolveria cero filas en silencio.
            for fila in tabla.to_pylist():
                fila["anio"] = anio
                fila["mes"] = mes
                filas.append(fila)
            print(f"    {nombre}: {tabla.num_rows:,} ítems")

    print(f"  meses de la ventana con Parquet: {disponibles} de {len(ventana)}")
    if disponibles < len(ventana):
        print(f"  AVISO: faltan {len(ventana) - disponibles} meses. El benchmark se "
              f"calcula sobre lo disponible y el n lo refleja.")
    return filas


def calcular(items: list[dict]) -> tuple[list[tuple], list[tuple]]:
    """Distribución de precio unitario por CPC y año, y tamaño de mercado por CPC.

    Solo entran ítems con **CPC, precio unitario y unidad declarados**: sin unidad, dos
    precios no son comparables —no es lo mismo el precio de una caja que el de una
    unidad—. Los demás cuentan para el tamaño de mercado pero no para la distribución.
    Ver docs/agregados.md §2.
    """
    precios: dict[tuple, list[float]] = defaultdict(list)
    mercado: dict[tuple, dict] = defaultdict(
        lambda: {"monto": 0.0, "procesos": set(), "cpc_n": 0}
    )

    sin_cpc = sin_unidad = 0
    for it in items:
        cpc = it.get("cpc")
        anio = it.get("anio")
        if not cpc or not anio:
            sin_cpc += 1
            continue
        precio = it.get("precio_unitario")
        unidad = (it.get("unidad") or "").strip()
        cantidad = it.get("cantidad") or 0

        if precio and precio > 0 and unidad:
            precios[(cpc, anio, unidad)].append(float(precio))
        elif precio:
            sin_unidad += 1

        m = mercado[(cpc, anio)]
        m["monto"] += float(precio or 0) * float(cantidad or 0)
        m["procesos"].add(it.get("ocid"))

    # Regla 2.2 del metodo: cardinalidad de entrada y salida. Si casi todo se descarta,
    # algo cambio en la fuente o en la extraccion, y hay que enterarse aqui.
    print(f"  ítems sin CPC o sin periodo: {sin_cpc:,} · con precio pero sin unidad: {sin_unidad:,}")
    utiles = len(items) - sin_cpc
    if items and utiles / len(items) < 0.5:
        raise SystemExit(
            f"Solo {utiles:,} de {len(items):,} ítems son utilizables ({utiles/len(items):.0%}). "
            f"Se esperaba la mayoría: revisa la extracción en detalle.py o el esquema de "
            f"la fuente antes de publicar un benchmark sobre esto."
        )

    filas_precio = []
    for (cpc, anio, unidad), valores in precios.items():
        if len(valores) < N_MINIMO:
            continue                      # nada se publica con muestra insuficiente
        valores.sort()
        def p(q: float) -> float:
            return round(valores[min(int(len(valores) * q), len(valores) - 1)], 4)
        filas_precio.append((
            cpc, anio, unidad[:40], len(valores),
            p(0.10), p(0.25), round(statistics.median(valores), 4), p(0.75), p(0.90),
            round(valores[0], 4), round(valores[-1], 4),
        ))

    filas_mercado = [
        (cpc, "", anio, round(m["monto"], 2), len(m["procesos"]), 0, 0)
        for (cpc, anio), m in mercado.items()
    ]
    return filas_precio, filas_mercado


def main() -> int:
    p = argparse.ArgumentParser(description="Puebla el benchmark de precio unitario")
    p.add_argument("--seco", action="store_true", help="calcula y muestra, sin escribir")
    args = p.parse_args()

    ventana = meses_de_la_ventana()
    anio, mes = corte_estadistico()
    print(f"ventana del benchmark: {VENTANA_MESES} meses hasta {anio}-{mes:02d} "
          f"(se excluyen los últimos {MESES_SIN_CERRAR})")

    items = descargar_items(ventana)
    print(f"ítems leídos: {len(items):,}")
    if not items:
        print("sin ítems: publica primero el Parquet de la ventana")
        return 1

    precio, mercado = calcular(items)
    print(f"  precio_cpc:       {len(precio):,} filas (CPC × año × unidad, n >= {N_MINIMO})")
    print(f"  mercado_cpc_prov: {len(mercado):,} filas")

    if args.seco:
        print("\n  categorías con más observaciones:")
        for f in sorted(precio, key=lambda r: -r[3])[:8]:
            print(f"    CPC {f[0]:<12} {f[1]}  n={f[3]:>5,}  mediana ${f[6]:>12,.2f}  {f[2]}")
        return 0

    from carga import conexion, reemplazar, verificar_presupuesto

    with conexion() as con:
        reemplazar(con, "precio_cpc",
                   ["cpc", "anio", "unidad", "n", "p10", "p25", "mediana", "p75", "p90",
                    "minimo", "maximo"], precio)
        reemplazar(con, "mercado_cpc_prov",
                   ["cpc", "provincia", "anio", "monto", "n_procesos", "n_proveedores",
                    "n_entidades"], mercado)
        con.commit()
        print(f"\nbase: {verificar_presupuesto(con)} MB de 460")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
