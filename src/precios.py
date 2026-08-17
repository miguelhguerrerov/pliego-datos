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
from normaliza import desglosar_renglon  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "miguelhguerrerov/pliego-datos")
API = "https://api.github.com"
CACHE = Path(".parquet-cache")

# El benchmark mira 24 meses. Once años no aportan: los precios de 2016 no dicen nada
# sobre a cuánto se adjudica hoy, y la ventana corta mantiene los agregados pequeños.
VENTANA_MESES = 24


def _release_de(etiqueta: str) -> dict | None:
    """Un release por su etiqueta, o None si no existe."""
    pet = urllib.request.Request(
        f"{API}/repos/{REPO}/releases/tags/{etiqueta}",
        headers={"User-Agent": "pliego-datos", "Accept": "application/vnd.github+json"},
    )
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        pet.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(pet, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _releases(ventana: set[tuple[int, int]]) -> list[dict]:
    """Los releases de los años de la ventana, **pedidos uno a uno por etiqueta**.

    No se usa `GET /releases`: ese endpoint devuelve una lista VACÍA en este repositorio
    aunque los releases existan, estén publicados y tengan sus activos. Comprobado el
    17 de agosto de 2026, con token y sin token, HTTP 200 y cuerpo `[]` — mientras
    `GET /releases/tags/datos-2025` devolvía los 60 activos del mismo release.

    El fallo era silencioso de la peor manera: «meses de la ventana con Parquet: 0 de 24»
    y un AVISO que decía que el benchmark se calcularía «sobre lo disponible». Sin
    ítems corta, pero con un listado a medias habría publicado un benchmark incompleto
    sin que nada lo advirtiera.

    Las etiquetas son deterministas —`datos-AAAA`, las que escribe `publicar.py`—, así
    que no hace falta listar nada. `publicar.py` ya consultaba por etiqueta; esto solo
    lo alinea.
    """
    salida = []
    for anio in sorted({a for a, _ in ventana}):
        rel = _release_de(f"datos-{anio}")
        if rel is not None:
            salida.append(rel)
        else:
            print(f"    sin release datos-{anio}")
    return salida


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


def descargar_items(ventana: set[tuple[int, int]]) -> tuple[list[dict], dict[str, str]]:
    """Trae los Parquet de la ventana. Devuelve `(items, ocid -> metodo)`.

    **Se bajan los dos Parquet, no solo el de ítems.** `unit.value.amount` significa una
    cosa en subasta inversa y otra en el resto (ver `desglosar_renglon`), y el método no
    está en la tabla de ítems: está en la de procesos. Sin ese cruce no hay forma de
    saber si un renglón trae un precio o un total, y el benchmark sale mal en un sentido
    o en el otro. Bajar `procesos_*` cuesta unos pocos MB por mes.
    """
    import pyarrow.parquet as pq

    CACHE.mkdir(parents=True, exist_ok=True)

    def bajar(activo, nombre: str):
        destino = CACHE / nombre
        if not destino.exists():
            pet = urllib.request.Request(
                activo["browser_download_url"], headers={"User-Agent": "pliego-datos"}
            )
            with urllib.request.urlopen(pet, timeout=300) as r:
                destino.write_bytes(r.read())
        return pq.read_table(destino)

    filas: list[dict] = []
    metodos: dict[str, str] = {}
    meses_items, meses_procesos = set(), set()
    for rel in _releases(ventana):
        for activo in rel.get("assets", []):
            nombre = activo["name"]
            if not nombre.endswith(".parquet"):
                continue
            es_item = nombre.startswith("items_")
            es_proceso = nombre.startswith("procesos_")
            if not (es_item or es_proceso):
                continue
            partes = nombre[:-8].split("_")
            anio, mes = int(partes[1]), int(partes[2])
            if (anio, mes) not in ventana:
                continue
            tabla = bajar(activo, nombre)
            if es_proceso:
                meses_procesos.add((anio, mes))
                for f in tabla.select(["ocid", "metodo"]).to_pylist():
                    if f.get("ocid") and f.get("metodo"):
                        metodos[f["ocid"]] = f["metodo"]
                continue
            meses_items.add((anio, mes))
            # Los items del Parquet NO llevan fecha: detalle.py guarda ocid, cpc,
            # cantidad, unidad y precio. El periodo esta en el nombre del archivo, que
            # es por mes. Sin esto, calcular() devolveria cero filas en silencio.
            for fila in tabla.to_pylist():
                fila["anio"] = anio
                fila["mes"] = mes
                filas.append(fila)
            print(f"    {nombre}: {tabla.num_rows:,} ítems")

    print(f"  meses de la ventana con Parquet: {len(meses_items)} de {len(ventana)}")
    # Antes esto era un AVISO que decía «se calcula sobre lo disponible». Con 0 de 24
    # meses eso significaba publicar un benchmark vacío o a medias sin que nada lo
    # impidiera; el fallo del listado de releases se descubrió porque la ejecución murió
    # después, por otro motivo. Una advertencia que no detiene nada no protege nada.
    if len(meses_items) < len(ventana) * 0.75:
        raise SystemExit(
            f"Solo {len(meses_items)} de {len(ventana)} meses de la ventana tienen "
            f"Parquet de ítems. Un benchmark sobre menos de tres cuartos de la ventana "
            f"no es comparable con el anterior y nadie lo notaría al mirarlo. Publica los "
            f"meses que faltan con publicar.py, o revisa que los releases `datos-AAAA` "
            f"existan y tengan sus activos."
        )
    if len(meses_items) < len(ventana):
        print(f"  faltan {len(ventana) - len(meses_items)} meses de {len(ventana)}: el "
              f"benchmark se calcula sobre el resto y el n lo refleja.")

    # Un mes con ítems y sin procesos deja esos ítems sin método, y sin método la regla
    # del renglón no se puede aplicar. Que se sepa aquí y no se descubra en el benchmark.
    huerfanos = meses_items - meses_procesos
    if huerfanos:
        raise SystemExit(
            f"Hay ítems sin su Parquet de procesos en {len(huerfanos)} meses: "
            f"{sorted(huerfanos)[:6]}. Sin `metodo` no se puede saber si "
            f"`unit.value.amount` es un precio unitario o el total del renglón. "
            f"Republica esos meses con publicar.py antes de calcular el benchmark."
        )
    return filas, metodos


def calcular(items: list[dict], metodos: dict[str, str]) -> tuple[list[tuple], list[tuple]]:
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

    # ------------------------------------------------------------------
    # Un solo origen por proceso: `awards` si trae importes, si no `tender`
    # ------------------------------------------------------------------
    # `detalle.py` guarda los ítems de tender Y los de awards, porque los de awards son
    # los efectivamente adjudicados. Pero el cálculo los sumaba TODOS, y en licitación
    # 1.383 de 1.495 procesos tienen ítems en los dos sitios: el mercado se inflaba
    # ×1,78. Medido en 2025-12 sobre la fuente.
    #
    # Se prefiere `award` porque es el precio al que de verdad se adjudicó, que es lo que
    # el cliente necesita saber. En subasta inversa los ítems de award vienen **sin
    # importe** —1.833 ítems, monto total 0— así que ahí se cae a `tender` y lo que se
    # publica es el referencial. Ver D-043.
    con_award = set()
    for it in items:
        if it.get("origen") == "award":
            try:
                if float(it.get("precio_unitario") or 0) > 0:
                    con_award.add(it.get("ocid"))
            except (TypeError, ValueError):
                pass

    antes = len(items)
    items = [it for it in items
             if (it.get("origen") == "award") == (it.get("ocid") in con_award)]
    print(f"  ítems tras quedarse con un solo origen por proceso: {len(items):,} "
          f"de {antes:,} · procesos con importe adjudicado: {len(con_award):,}")

    sin_cpc = sin_unidad = sin_metodo = 0
    for it in items:
        cpc = it.get("cpc")
        anio = it.get("anio")
        if not cpc or not anio:
            sin_cpc += 1
            continue
        # `precio_unitario` es el nombre de la columna del Parquet, y es ENGAÑOSO: lo que
        # guarda es `unit.value.amount` en crudo, que en subasta inversa es el total del
        # renglón y en el resto de métodos sí es el precio por unidad. Por eso hace falta
        # el método, y por eso el desglose está en un solo sitio. Ver D-041.
        unidad = (it.get("unidad") or "").strip()
        metodo = metodos.get(it.get("ocid"))
        if metodo is None:
            # Sin método no se sabe qué es `amount`, y el desglose caería en la rama
            # «precio unitario» por omisión. Un valor por defecto en el campo ambiguo es
            # exactamente el fallo que se está corrigiendo: se cuenta y se corta abajo.
            sin_metodo += 1
            continue
        precio, monto_linea = desglosar_renglon(
            metodo, it.get("precio_unitario"), it.get("cantidad")
        )

        if precio and unidad:
            precios[(cpc, anio, unidad)].append(precio)
        elif precio:
            sin_unidad += 1

        m = mercado[(cpc, anio)]
        # El tamaño de mercado es la suma de los totales de renglón, que ahora es una
        # cifra derivada y no un campo: en subasta inversa el total viene dado, en el
        # resto es precio por cantidad.
        m["monto"] += float(monto_linea or 0)
        m["procesos"].add(it.get("ocid"))

    # Regla 2.2 del metodo: cardinalidad de entrada y salida. Si casi todo se descarta,
    # algo cambio en la fuente o en la extraccion, y hay que enterarse aqui.
    print(f"  ítems sin CPC o sin periodo: {sin_cpc:,} · con precio pero sin unidad: "
          f"{sin_unidad:,} · sin método: {sin_metodo:,}")
    if sin_metodo > len(items) * 0.01:
        raise SystemExit(
            f"{sin_metodo:,} de {len(items):,} ítems ({sin_metodo/len(items):.1%}) "
            f"pertenecen a procesos que no están en el Parquet de procesos. Sin método no "
            f"se puede saber si `unit.value.amount` es precio o total, y adivinarlo es el "
            f"fallo de D-041. Republica los meses de la ventana con publicar.py."
        )
    utiles = len(items) - sin_cpc - sin_metodo
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

    items, metodos = descargar_items(ventana)
    print(f"ítems leídos: {len(items):,} · procesos con método: {len(metodos):,}")
    if not items:
        print("sin ítems: publica primero el Parquet de la ventana")
        return 1

    precio, mercado = calcular(items, metodos)
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
