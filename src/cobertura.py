"""Informe de cobertura: qué meses faltan o están incompletos.

    python src/cobertura.py --informe

Existe porque presentar datos incompletos como completos es el peor fallo posible de
este producto. Ver docs/datos.md §7.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PRIMER_ANIO = 2015

# Meses que los trabajos diario y semanal mantienen al día. Un hueco aquí es avería;
# fuera de aquí es backfill pendiente, que no es lo mismo y no debe fallar la ejecución.
VENTANA_OPERATIVA_MESES = 6


def meses_esperados(hasta: dt.date | None = None) -> list[tuple[int, int]]:
    hasta = hasta or dt.date.today()
    salida = []
    for anio in range(PRIMER_ANIO, hasta.year + 1):
        for mes in range(1, 13):
            if (anio, mes) <= (hasta.year, hasta.month):
                salida.append((anio, mes))
    return salida


def informe() -> int:
    from carga import conexion

    with conexion() as con, con.cursor() as cur:
        cur.execute("select anio, mes, estado, registros, pct_cerrado from cobertura")
        filas = {(r[0], r[1]): r for r in cur.fetchall()}

        esperados = meses_esperados()
        faltan = [m for m in esperados if m not in filas]
        problemas = [r for r in filas.values() if r[2] != "cargado"]

        print(f"meses esperados : {len(esperados)}")
        print(f"meses cargados  : {len(filas) - len(problemas)}")
        print(f"meses con aviso : {len(problemas)}")
        print(f"meses ausentes  : {len(faltan)}")

        if problemas:
            print("\ncon aviso:")
            for a, m, estado, reg, pct in sorted(problemas):
                print(f"  {a}-{m:02d}  {estado:<10} {reg or 0:>7,} registros  {pct or 0:>5.1f}% cerrado")

        if faltan:
            print("\nausentes:", ", ".join(f"{a}-{m:02d}" for a, m in faltan[:24]))
            if len(faltan) > 24:
                print(f"  ... y {len(faltan) - 24} más")

        # Los últimos 4 meses no son un problema: es la curva de maduración normal.
        hoy = dt.date.today()
        recientes = [
            (a, m) for a, m in faltan
            if (hoy.year - a) * 12 + (hoy.month - m) <= 4
        ]
        criticos = [m for m in faltan if m not in recientes]
        if criticos:
            print(f"\nAUSENCIAS CRÍTICAS (fuera de la ventana de maduración): {len(criticos)}")
            return 1

        cur.execute("select round(sum(mb),2) from v_tamano_base")
        mb = cur.fetchone()[0] or 0
        print(f"\nbase: {mb} MB de 460 presupuestados (alarma a 420)")
        return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Cobertura de la ingesta")
    p.add_argument("--informe", action="store_true")
    args = p.parse_args()
    if args.informe:
        return informe()
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
