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
        # 'parcial' está cargado, con una nota. 'pendiente' y 'degradado' no lo están.
        con_datos = [r for r in filas.values() if r[2] in ("cargado", "parcial")]
        averiados = [r for r in filas.values() if r[2] not in ("cargado", "parcial")]
        con_nota = [r for r in filas.values() if r[2] == "parcial"]

        print(f"meses esperados : {len(esperados)}")
        print(f"meses con datos : {len(con_datos)}")
        print(f"meses con nota  : {len(con_nota)}")
        print(f"meses averiados : {len(averiados)}")
        print(f"meses ausentes  : {len(faltan)}")

        for etiqueta, grupo in (("con nota", con_nota), ("averiados", averiados)):
            if grupo:
                print(f"\n{etiqueta}:")
                for a, m, estado, reg, pct in sorted(grupo):
                    print(f"  {a}-{m:02d}  {estado:<10} {reg or 0:>7,} registros  {pct or 0:>5.1f}% cerrado")

        # Un hueco histórico es backfill pendiente, no una avería: se informa y ya.
        # Un hueco en la ventana operativa SÍ es avería: es lo que mantienen los trabajos
        # diario y semanal, y significa que llevan días sin cargar.
        hoy = dt.date.today()

        def antiguedad(m: tuple[int, int]) -> int:
            return (hoy.year - m[0]) * 12 + (hoy.month - m[1])

        operativos = [m for m in faltan if antiguedad(m) <= VENTANA_OPERATIVA_MESES]
        historicos = [m for m in faltan if antiguedad(m) > VENTANA_OPERATIVA_MESES]

        if historicos:
            print(f"\nbackfill pendiente: {len(historicos)} meses históricos sin cargar")
            print("  " + ", ".join(f"{a}-{m:02d}" for a, m in historicos[:12])
                  + (f" ... y {len(historicos) - 12} más" if len(historicos) > 12 else ""))

        if operativos or averiados:
            if operativos:
                print(f"\nAVERÍA: faltan {len(operativos)} meses de la ventana operativa "
                      f"de {VENTANA_OPERATIVA_MESES} meses: "
                      + ", ".join(f"{a}-{m:02d}" for a, m in operativos))
            print("Los trabajos diario y semanal deberían mantenerlos. Ver docs/operacion.md §2.")
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
