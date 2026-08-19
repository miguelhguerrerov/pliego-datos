"""Asigna el CPC de cabecera desde los ítems del Parquet publicado (mensual).

    python src/clasifica_cpc.py           # ventana completa
    python src/clasifica_cpc.py --seco    # calcula y muestra, sin escribir

Sustituye a la construcción de la taxonomía del LLM (D-045): ya no se nombra nada —los
nombres son los oficiales de `cpc_nivel`— pero la ASIGNACIÓN sigue haciendo falta: el
CSV diario no trae CPC, y los ítems viven en el Parquet mensual.

Hace dos cosas y las dos existían antes dentro de `taxonomia.py`:

  1. `proceso_resumen.cpc` = el CPC del ítem dominante por monto de cada proceso
     (fase 0.1 de D-045: cabecera e ítems coinciden en subclase en el 100% de 3.564
     procesos medidos). El trigger de la 0032 deriva `cpc_nodo` solo.
  2. El referencial de subasta inversa que el CSV no trae: el 22,1% de los convocados
     salía sin cifra y los ítems la recuperan (`completar_referencial`).

Los procesos en PLANIFICACIÓN quedan sin CPC a propósito: el método aún no existe, así
que el JSON troceado por método no los contiene. El CPC oficial es declarado, no
adivinado; el clasificador de texto que los etiquetaba murió con el LLM.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from precios import descargar_items, meses_de_la_ventana  # noqa: E402
from taxonomia import cpc_dominante, referencial_de_items  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="CPC de cabecera desde los ítems del Parquet")
    p.add_argument("--seco", action="store_true", help="calcular y mostrar, sin escribir")
    args = p.parse_args()

    ventana = meses_de_la_ventana()
    items, _metodos = descargar_items(ventana)
    print(f"ítems leídos: {len(items):,}")

    por_ocid = {o: c for o, (c, _) in cpc_dominante(items).items()}
    print(f"procesos con CPC dominante: {len(por_ocid):,}")
    if len(por_ocid) < 1000:
        raise SystemExit(
            f"Solo {len(por_ocid)} procesos con CPC en la ventana entera: o faltan "
            f"Parquet o cambió el esquema. No se escribe una clasificación raquítica."
        )

    referenciales = referencial_de_items(items)
    print(f"referenciales recuperables de los ítems: {len(referenciales):,}")

    if args.seco:
        return 0

    from carga import conexion
    from taxonomia import completar_referencial

    with conexion() as con:
        with con.cursor() as cur:
            cur.executemany(
                "update proceso_resumen set cpc = %s "
                "where ocid = %s and cpc is distinct from %s",
                [(c, o, c) for o, c in por_ocid.items()],
            )
            print(f"cpc actualizado (el trigger pone cpc_nodo)")
        n_ref = completar_referencial(con, referenciales)
        print(f"referenciales completados: {n_ref:,}")
        con.commit()

        with con.cursor() as cur:
            cur.execute("""
                select count(*), count(cpc), count(cpc_nodo)
                from proceso_resumen
            """)
            total, con_cpc, con_nodo = cur.fetchone()
            print(f"proceso_resumen: {total:,} filas · {con_cpc:,} con cpc "
                  f"· {con_nodo:,} enganchadas al arbol")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
