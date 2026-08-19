"""Carga la clasificación CPC oficial y el catálogo de productos con umbral VAE.

    python src/cpc.py            # carga referencia/*.csv en cpc_nivel y cpc_producto
    python src/cpc.py --seco     # valida y muestra recuentos, sin escribir

Los ficheros y su procedencia están en `referencia/LEEME.md`; la decisión, en D-045.
Esto NO corre en cada ingesta: la clasificación cambia raramente. Se ejecuta a mano
(flujo `referencia.yml`) cuando cambian los ficheros de referencia.

**Codificación**: `cpc_clasificacion.csv` es UTF-8 con BOM; `umbral_vae.csv` es
**latin-1** — la única fuente del proyecto que no es UTF-8. Se declara explícito aquí
para que un cambio en el fichero pare la carga en vez de corromperla en silencio.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

RAIZ = Path(__file__).resolve().parents[1]

# Lo que DEBE haber. Si un fichero nuevo trae otra cosa, la carga se detiene y lo dice:
# una clasificacion a medias es peor que la anterior completa.
ESPERADO_NIVELES = {1: 10, 2: 73, 3: 313, 4: 1192, 5: 2137}
ESPERADO_PRODUCTOS_MIN = 30_000


def leer_arbol() -> list[tuple]:
    """(codigo, nivel, nombre, padre) validado: padre = prefijo y existe."""
    crudo = (RAIZ / "referencia" / "cpc_clasificacion.csv").read_text(encoding="utf-8-sig")
    filas = list(csv.DictReader(io.StringIO(crudo)))

    nodos: dict[str, tuple] = {}
    for f in filas:
        codigo = f["Codigo"].strip()
        nivel = int(f["Nivel"])
        nombre = f["Descripcion"].strip()
        padre = f["Codigo_Padre"].strip() or None
        if len(codigo) != nivel:
            raise SystemExit(f"cpc_clasificacion: {codigo!r} tiene longitud "
                             f"{len(codigo)} pero declara nivel {nivel}")
        if nivel > 1 and padre != codigo[:-1]:
            raise SystemExit(f"cpc_clasificacion: el padre de {codigo} es {padre!r}, "
                             f"no su prefijo {codigo[:-1]!r}")
        if codigo in nodos:
            raise SystemExit(f"cpc_clasificacion: codigo duplicado {codigo}")
        nodos[codigo] = (codigo, nivel, nombre, padre)

    for codigo, nivel, _, padre in nodos.values():
        if nivel > 1 and padre not in nodos:
            raise SystemExit(f"cpc_clasificacion: {codigo} cuelga de {padre}, que no existe")

    reales = {}
    for _, nivel, _, _ in nodos.values():
        reales[nivel] = reales.get(nivel, 0) + 1
    if reales != ESPERADO_NIVELES:
        raise SystemExit(f"cpc_clasificacion: niveles {reales}, "
                         f"se esperaba {ESPERADO_NIVELES}. Si el SERCOP amplio la "
                         f"clasificacion, actualiza ESPERADO_NIVELES a conciencia.")
    return list(nodos.values())


def _umbral(texto: str):
    """«40,00%» -> 0.4000. Vacio -> None."""
    t = texto.strip().replace("%", "").replace(",", ".")
    if not t:
        return None
    return round(float(t) / 100, 4)


def leer_productos(subclases: set[str]) -> list[tuple]:
    """(codigo, nombre, umbral_vae, subclase). La subclase se resuelve aqui una vez."""
    crudo = (RAIZ / "referencia" / "umbral_vae.csv").read_bytes().decode("latin-1")
    filas = list(csv.reader(io.StringIO(crudo), delimiter=";"))

    salida, sin_subclase = [], 0
    vistos: set[str] = set()
    for f in filas[1:]:
        if len(f) < 3 or not f[0].strip():
            continue
        codigo, nombre = f[0].strip(), f[1].strip()
        if codigo in vistos:
            continue
        vistos.add(codigo)
        sub = codigo[:5] if codigo[:5] in subclases else None
        if sub is None:
            sin_subclase += 1
        salida.append((codigo, nombre, _umbral(f[2]), sub))

    if len(salida) < ESPERADO_PRODUCTOS_MIN:
        raise SystemExit(f"umbral_vae: {len(salida):,} productos, se esperaban al "
                         f"menos {ESPERADO_PRODUCTOS_MIN:,}")
    # Medido al validar: 26 codigos cortos y algun fuera de arbol. Si crece, gritar.
    if sin_subclase > len(salida) * 0.01:
        raise SystemExit(f"umbral_vae: {sin_subclase:,} productos sin subclase en el "
                         f"arbol ({sin_subclase / len(salida):.1%}). El fichero y la "
                         f"clasificacion no casan.")
    print(f"  productos sin subclase en el arbol: {sin_subclase} "
          f"(se cargan con subclase nula)")
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description="Carga la clasificacion CPC oficial")
    p.add_argument("--seco", action="store_true", help="validar sin escribir")
    args = p.parse_args()

    arbol = leer_arbol()
    print(f"arbol: {len(arbol):,} nodos validados")
    productos = leer_productos({c for c, n, _, _ in arbol if n == 5})
    print(f"productos: {len(productos):,} con nombre oficial"
          f" · {sum(1 for x in productos if x[2] is not None):,} con umbral VAE")

    if args.seco:
        return 0

    from carga import conexion, reemplazar

    with conexion() as con:
        # El arbol se carga por niveles: la FK del padre exige que el padre ya exista.
        with con.cursor() as cur:
            # `reemplazar` truncaria sin respetar la FK circular; aqui se borra en
            # orden inverso y se inserta en orden.
            cur.execute("delete from cpc_producto")
            cur.execute("delete from cpc_nivel")
        for nivel in (1, 2, 3, 4, 5):
            lote = [x for x in arbol if x[1] == nivel]
            with con.cursor() as cur:
                with cur.copy("copy cpc_nivel (codigo, nivel, nombre, padre) from stdin") as cp:
                    for fila in lote:
                        cp.write_row(fila)
        with con.cursor() as cur:
            with cur.copy("copy cpc_producto (codigo, nombre, umbral_vae, subclase) from stdin") as cp:
                for fila in productos:
                    cp.write_row(fila)
        con.commit()

        with con.cursor() as cur:
            cur.execute("select nivel, count(*) from cpc_nivel group by 1 order by 1")
            print("cargado cpc_nivel:", dict(cur.fetchall()))
            cur.execute("select count(*), count(umbral_vae) from cpc_producto")
            total, con_vae = cur.fetchone()
            print(f"cargado cpc_producto: {total:,} ({con_vae:,} con VAE)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
