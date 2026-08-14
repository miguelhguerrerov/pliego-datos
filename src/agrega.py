"""Cálculo de las tablas agregadas.

    python src/agrega.py

Los agregados se recalculan **enteros** desde `hecho_mes`, no de forma incremental:
es más simple, más robusto, y cuesta segundos. Ver docs/agregados.md §3.

Reglas que se aplican aquí y no en la interfaz, para que no se puedan olvidar:

- Las estadísticas de mercado **excluyen los últimos 4 meses** (invariante 10 y D-009):
  un mes tarda 4 o 5 meses en cerrar y un benchmark sobre datos a medio llenar sale
  sesgado sin que nada lo advierta. El radar, en cambio, usa el dato del día.
- Ninguna estadística se publica con `n < 5` (docs/agregados.md §3).
"""

from __future__ import annotations

import argparse
import datetime as dt
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MESES_SIN_CERRAR = 4      # invariante 10
N_MINIMO = 5              # por debajo no se publica nada
VENTANA_RELACION_ANIOS = 3  # segunda válvula de docs/agregados.md §1


def corte_estadistico(hoy: dt.date | None = None) -> tuple[int, int]:
    """Último (anio, mes) que entra en estadísticas de mercado."""
    hoy = hoy or dt.date.today()
    total = hoy.year * 12 + (hoy.month - 1) - MESES_SIN_CERRAR
    return total // 12, total % 12 + 1


def _antes_del_corte(anio: int, mes: int, corte: tuple[int, int]) -> bool:
    return (anio, mes) <= corte


def calcular(hechos: list[tuple]) -> dict[str, list[tuple]]:
    """Recibe filas de hecho_mes y devuelve las tablas agregadas listas para cargar.

    hechos: (anio, mes, comprador_ruc, proveedor_ruc, metodo, n_procesos,
             referencial, adjudicado)
    """
    corte = corte_estadistico()
    anio_min_relacion = corte[0] - VENTANA_RELACION_ANIOS + 1

    monto_ent: dict[tuple, float] = defaultdict(float)
    proc_ent: dict[tuple, int] = defaultdict(int)
    contrapartes: dict[tuple, set] = defaultdict(set)
    relacion: dict[tuple, list] = defaultdict(lambda: [0.0, 0])
    ratios: dict[tuple, list] = defaultdict(list)

    for anio, mes, comprador, proveedor, metodo, n, ref, adj in hechos:
        adj = float(adj or 0)
        n = int(n or 0)

        if comprador:
            monto_ent[(comprador, anio, "comprador")] += adj
            proc_ent[(comprador, anio, "comprador")] += n
            if proveedor:
                contrapartes[(comprador, anio, "comprador")].add(proveedor)
        if proveedor:
            monto_ent[(proveedor, anio, "proveedor")] += adj
            proc_ent[(proveedor, anio, "proveedor")] += n
            if comprador:
                contrapartes[(proveedor, anio, "proveedor")].add(comprador)

        if comprador and proveedor and anio >= anio_min_relacion:
            r = relacion[(comprador, proveedor, anio)]
            r[0] += adj
            r[1] += n

        # El ratio de baja solo tiene sentido con ambas cifras y sobre meses cerrados.
        if metodo and ref and adj and _antes_del_corte(anio, mes, corte):
            cociente = adj / float(ref)
            if 0 < cociente <= 1.5:      # por encima es error de captura en la fuente
                ratios[(metodo, anio)].append(cociente)

    salida: dict[str, list[tuple]] = {}

    salida["entidad_ano"] = [
        (ruc, anio, rol, round(monto_ent[(ruc, anio, rol)], 2),
         proc_ent[(ruc, anio, rol)], len(contrapartes[(ruc, anio, rol)]))
        for (ruc, anio, rol) in monto_ent
    ]

    salida["relacion"] = [
        (c, p, a, round(v[0], 2), v[1]) for (c, p, a), v in relacion.items()
    ]

    baja = []
    for (metodo, anio), valores in ratios.items():
        if len(valores) < N_MINIMO:
            continue          # no se publica nada con muestra insuficiente
        valores.sort()
        baja.append((
            metodo, anio, len(valores),
            round(statistics.median(valores), 4),
            round(valores[len(valores) // 4], 4),
            round(valores[3 * len(valores) // 4], 4),
        ))
    salida["baja_metodo"] = baja

    return salida


def main() -> int:
    p = argparse.ArgumentParser(description="Recalcula las tablas agregadas")
    p.add_argument("--seco", action="store_true", help="calcula y muestra, sin escribir")
    args = p.parse_args()

    from carga import conexion, reemplazar, verificar_presupuesto

    with conexion() as con:
        with con.cursor() as cur:
            cur.execute("""
                select anio, mes, comprador_ruc, proveedor_ruc, metodo,
                       n_procesos, referencial, adjudicado
                from hecho_mes
            """)
            hechos = cur.fetchall()
        print(f"hechos leídos: {len(hechos):,}")

        tablas = calcular(hechos)
        corte = corte_estadistico()
        print(f"corte estadístico: hasta {corte[0]}-{corte[1]:02d} "
              f"(se excluyen los últimos {MESES_SIN_CERRAR} meses)")
        for nombre, filas in tablas.items():
            print(f"  {nombre:<14} {len(filas):>8,} filas")

        if args.seco:
            for metodo, anio, n, med, p25, p75 in sorted(tablas["baja_metodo"], key=lambda r: -r[2])[:8]:
                print(f"    {anio} {metodo[:38]:<38} mediana {med}  n={n:,}")
            return 0

        columnas = {
            "entidad_ano": ["ruc", "anio", "rol", "monto", "n_procesos", "n_contrapartes"],
            "relacion": ["comprador_ruc", "proveedor_ruc", "anio", "monto", "n_procesos"],
            "baja_metodo": ["metodo", "anio", "n", "ratio_mediana", "ratio_p25", "ratio_p75"],
        }
        for nombre, filas in tablas.items():
            reemplazar(con, nombre, columnas[nombre], filas)
        con.commit()

        mb = verificar_presupuesto(con)
        print(f"base: {mb} MB de 460 presupuestados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
