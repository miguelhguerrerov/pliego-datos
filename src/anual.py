"""Series anuales desde los Parquet: el árbol por año y la tendencia de precios.

    python src/anual.py                     # todos los años publicados
    python src/anual.py --desde 2023        # solo 2023 en adelante
    python src/anual.py --seco              # calcula y muestra, sin escribir

Llena `mercado_nodo_anual` y `precio_cpc_anual` (D-046) en una sola pasada por año.
Corre en Actions: descarga ~30 MB por año de los releases (por etiqueta, D-042).

**Reglas del renglón**: las mismas del benchmark, en un solo sitio.
  - Un origen por proceso: `award` si trae importe, si no `tender` (D-043). El catálogo
    entra por sus items de award, que traen monto y CPC (medido: 4.705/4.705).
  - `unit.value.amount` es total del renglón en subasta inversa y precio por unidad en
    el resto (`normaliza.desglosar_renglon`, D-041).
  - El CPC del proceso es el del ítem dominante por monto (100% de acuerdo con la
    cabecera, medido en D-045 fase 0).

**El enganche al árbol replica el trigger de la 0032** leyendo la clasificación de
`referencia/cpc_clasificacion.csv`: subclase → clase → '_sin_clasificar'. Visible,
nunca descartado.

**Los distintos no se suman** (D-045): cada nodo×año se calcula desde sus procesos.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from normaliza import desglosar_renglon  # noqa: E402
from precios import _release_de  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CACHE = Path(".parquet-anual")

PRIMER_ANIO = 2015
N_MINIMO = 10          # invariante 11: ningún precio con menos de 10 observaciones
NIVEL_SIN = "_sin_clasificar"


def nodos_del_arbol() -> tuple[set[str], set[str]]:
    """(subclases, clases) de la clasificación oficial, para replicar el trigger."""
    crudo = (RAIZ / "referencia" / "cpc_clasificacion.csv").read_text(encoding="utf-8-sig")
    subclases, clases = set(), set()
    for f in csv.DictReader(io.StringIO(crudo)):
        if f["Nivel"] == "5":
            subclases.add(f["Codigo"].strip())
        elif f["Nivel"] == "4":
            clases.add(f["Codigo"].strip())
    return subclases, clases


def nodo_de(cpc: str | None, subclases: set[str], clases: set[str]) -> str | None:
    """La regla de la 0032: subclase, si no clase, si no nada."""
    if not cpc:
        return None
    if cpc[:5] in subclases:
        return cpc[:5]
    if cpc[:4] in clases:
        return cpc[:4]
    return None


def _bajar(activo: dict, destino: Path) -> "object":
    import pyarrow.parquet as pq

    if not destino.exists():
        pet = urllib.request.Request(
            activo["browser_download_url"], headers={"User-Agent": "pliego-datos"})
        with urllib.request.urlopen(pet, timeout=300) as r:
            destino.write_bytes(r.read())
    return pq.read_table(destino)


def leer_anio(anio: int) -> tuple[dict, dict, dict]:
    """(procesos, items_por_ocid, ganadores_por_ocid) de los 12 Parquet del año."""
    rel = _release_de(f"datos-{anio}")
    if rel is None:
        return {}, {}, {}
    CACHE.mkdir(parents=True, exist_ok=True)

    procesos: dict[str, tuple] = {}          # ocid -> (metodo, comprador)
    items: dict[str, list] = collections.defaultdict(list)
    ganadores: dict[str, set] = collections.defaultdict(set)

    for activo in rel.get("assets", []):
        nombre = activo["name"]
        if not nombre.endswith(".parquet"):
            continue
        tabla = None
        if nombre.startswith("procesos_"):
            tabla = _bajar(activo, CACHE / nombre)
            for f in tabla.select(["ocid", "metodo", "comprador_ruc"]).to_pylist():
                if f["ocid"]:
                    procesos[f["ocid"]] = (f.get("metodo"), f.get("comprador_ruc"))
        elif nombre.startswith("items_"):
            tabla = _bajar(activo, CACHE / nombre)
            for f in tabla.select(
                    ["ocid", "origen", "cpc", "cantidad", "unidad", "precio_unitario"]
            ).to_pylist():
                if f["ocid"]:
                    items[f["ocid"]].append(f)
        elif nombre.startswith("oferentes_"):
            tabla = _bajar(activo, CACHE / nombre)
            for f in tabla.select(["ocid", "ruc", "gano"]).to_pylist():
                if f["ocid"] and f.get("gano") and f.get("ruc"):
                    ganadores[f["ocid"]].add(f["ruc"])
    return procesos, items, ganadores


def procesar_anio(anio: int, subclases: set[str], clases: set[str],
                  acc_nodo: dict, acc_precio: dict) -> dict:
    """Acumula el año en los agregados. Devuelve las cifras de control."""
    procesos, items, ganadores = leer_anio(anio)
    if not procesos:
        return {"procesos": 0}

    con_monto = 0
    for ocid, filas in items.items():
        metodo, comprador = procesos.get(ocid, (None, None))

        # Un origen por proceso (D-043): award si trae importe, si no tender.
        award = [f for f in filas if f.get("origen") == "award"]
        con_importe = [f for f in award
                       if f.get("precio_unitario") and float(f["precio_unitario"] or 0) > 0]
        elegidas = con_importe if con_importe else [f for f in filas
                                                    if f.get("origen") == "tender"]
        if not elegidas:
            continue

        monto_proceso = 0.0
        por_cpc: collections.Counter = collections.Counter()
        for f in elegidas:
            precio, linea = desglosar_renglon(metodo, f.get("precio_unitario"),
                                              f.get("cantidad"))
            if linea is None:
                continue
            monto_proceso += linea
            cpc = (f.get("cpc") or "").strip()
            if cpc:
                por_cpc[cpc] += linea
                unidad = (f.get("unidad") or "").strip()
                if precio and unidad:
                    acc_precio.setdefault((cpc, unidad[:40], anio), []).append(precio)

        if monto_proceso <= 0:
            continue
        con_monto += 1

        cpc_dominante = por_cpc.most_common(1)[0][0] if por_cpc else None
        nodo5 = nodo_de(cpc_dominante, subclases, clases)
        niveles = ([nodo5[:n] for n in range(1, len(nodo5) + 1)] if nodo5
                   else [NIVEL_SIN])

        for codigo in niveles:
            a = acc_nodo.setdefault((codigo, anio), {
                "montos": [], "compradores": set(), "proveedores": set()})
            a["montos"].append(monto_proceso)
            if comprador:
                a["compradores"].add(comprador)
            for g in ganadores.get(ocid, ()):
                a["proveedores"].add(g)

    return {"procesos": len(procesos), "con_monto": con_monto}


def filas_finales(acc_nodo: dict, acc_precio: dict) -> tuple[list, list]:
    nodo = []
    for (codigo, anio), a in acc_nodo.items():
        m = a["montos"]
        nivel = 0 if codigo == NIVEL_SIN else len(codigo)
        nodo.append((codigo, nivel, anio, len(m), round(sum(m), 2),
                     round(statistics.median(m), 2),
                     len(a["compradores"]), len(a["proveedores"])))

    precio = []
    for (cpc, unidad, anio), valores in acc_precio.items():
        if len(valores) < N_MINIMO:
            continue
        valores.sort()
        def p(q: float) -> float:
            return round(valores[min(len(valores) - 1, int(q * len(valores)))], 4)
        precio.append((cpc, unidad, anio, len(valores),
                       p(0.25), round(statistics.median(valores), 4), p(0.75)))
    return nodo, precio


def main() -> int:
    ap = argparse.ArgumentParser(description="Series anuales desde los Parquet (D-046)")
    ap.add_argument("--desde", type=int, default=PRIMER_ANIO)
    ap.add_argument("--seco", action="store_true")
    args = ap.parse_args()

    import datetime as dt
    anios = range(args.desde, dt.date.today().year + 1)

    subclases, clases = nodos_del_arbol()
    print(f"árbol: {len(subclases):,} subclases · {len(clases):,} clases")

    # Los acumuladores se cierran AÑO A AÑO: las claves llevan el año, así que nada de
    # un año sirve para el siguiente, y el histórico entero de precios en memoria son
    # millones de valores que no caben con holgura en un runner.
    nodo: list = []
    precio: list = []
    por_anio: collections.Counter = collections.Counter()
    for anio in anios:
        acc_nodo: dict = {}
        acc_precio: dict = {}
        c = procesar_anio(anio, subclases, clases, acc_nodo, acc_precio)
        n_a, p_a = filas_finales(acc_nodo, acc_precio)
        nodo.extend(n_a)
        precio.extend(p_a)
        por_anio[anio] = len(acc_nodo)
        print(f"  {anio}: {c.get('procesos', 0):>7,} procesos · "
              f"{c.get('con_monto', 0):>7,} con monto · {len(n_a):>6,} nodos "
              f"· {len(p_a):>6,} precios")

    print(f"\nmercado_nodo_anual: {len(nodo):,} filas · "
          f"precio_cpc_anual: {len(precio):,} filas (n >= {N_MINIMO})")

    # Cardinalidad (regla 2 del método): un año vacío en medio de la serie grita.
    completos = [a for a in anios if por_anio.get(a, 0) > 100]
    if len(completos) < len(list(anios)) - 1:      # el año en curso puede ser flaco
        faltan = [a for a in anios if a not in completos]
        raise SystemExit(f"Años sin datos suficientes: {faltan}. "
                         f"¿Faltan releases datos-AAAA o cambió el esquema?")

    if args.seco:
        for a in sorted(por_anio):
            print(f"  {a}: {por_anio[a]:,} nodos con actividad")
        return 0

    from carga import conexion, reemplazar, verificar_presupuesto

    with conexion() as con:
        reemplazar(con, "mercado_nodo_anual",
                   ["codigo", "nivel", "anio", "n_procesos", "monto", "mediana",
                    "n_contratantes", "n_contratistas"], nodo)
        reemplazar(con, "precio_cpc_anual",
                   ["cpc", "unidad", "anio", "n", "p25", "mediana", "p75"], precio)
        con.commit()
        print(f"base: {verificar_presupuesto(con)} MB de 460")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
