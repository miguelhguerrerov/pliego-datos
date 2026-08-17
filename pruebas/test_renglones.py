"""Los renglones de un proceso tienen que sumar su monto.

**Por que existe este fichero.** El fallo D-041 estuvo publicado con las 56 pruebas en
verde. Ninguna lo vio porque todas comprobaban funciones —«desglosar devuelve un
numero», «la tabla tiene filas»— y el fallo estaba en el RESULTADO: la suma de los
renglones de una licitacion daba 2.127 USD contra un referencial de 94.102,17.

Lo detecto una persona mirando la pantalla y sumando la columna. Eso es lo que
automatiza esto. Regla 1 del metodo: una consulta de producto tras cada carga.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from normaliza import desglosar_renglon  # noqa: E402


# Casos reales, tomados de la fuente y verificados uno a uno contra el referencial o el
# adjudicado del proceso. No son inventados: son los que aparecen en D-041.
RENGLONES = [
    # (metodo, amount, cantidad, precio esperado, total esperado, etiqueta)
    ("Licitación", 18.82, 30, 18.82, 564.6, "alcantarilla 2000 mm"),
    ("Licitación", 4.1142, 78, 4.1142, 320.9076, "alcantarilla 1000 mm"),
    ("Licitación", 283.25, 1, 283.25, 283.25, "pancarta, cantidad 1"),
    ("Subasta Inversa Electrónica", 11082.25, 440, 25.186932, 11082.25, "hueso de res"),
    ("Subasta Inversa Electrónica", 89475.0, 596500, 0.15, 89475.0, "sulfasalazina"),
    ("Menor Cuantía", 12.5, 4, 12.5, 50.0, "menor cuantia"),
]


@pytest.mark.parametrize("metodo,amount,cantidad,precio,total,etiqueta", RENGLONES)
def test_desglose_de_un_renglon(metodo, amount, cantidad, precio, total, etiqueta):
    p, t = desglosar_renglon(metodo, amount, cantidad)
    assert p == pytest.approx(precio), f"{etiqueta}: precio unitario"
    assert t == pytest.approx(total), f"{etiqueta}: total de linea"


def test_el_metodo_cambia_el_significado():
    """El nucleo de D-041, escrito como prueba.

    El mismo `amount` y la misma cantidad dan resultados distintos segun el metodo. Si
    alguien «simplifica» la funcion quitando el metodo, esto se pone rojo.
    """
    sie = desglosar_renglon("Subasta Inversa Electrónica", 1000.0, 50)
    lico = desglosar_renglon("Licitación", 1000.0, 50)
    assert sie == (20.0, 1000.0)
    assert lico == (1000.0, 50000.0)
    assert sie != lico


def test_el_convenio_marco_no_despista():
    """`metodo_base` corta el convenio; el desglose tiene que verlo igual."""
    largo = "Subasta Inversa Electrónica en el convenio SERCOP-CM-2024-001"
    assert desglosar_renglon(largo, 1000.0, 50) == (20.0, 1000.0)


def test_sin_cantidad_las_dos_cifras_siguen_siendo_coherentes():
    """Sin cantidad se asume 1, y entonces precio y total tienen que coincidir."""
    for metodo in ("Licitación", "Subasta Inversa Electrónica"):
        p, t = desglosar_renglon(metodo, 700.0, None)
        assert p == t == 700.0, metodo


def test_sin_amount_no_se_inventa_nada():
    assert desglosar_renglon("Licitación", None, 10) == (None, None)
    assert desglosar_renglon("Licitación", 0, 10) == (None, None)
    assert desglosar_renglon("Licitación", "no es un numero", 10) == (None, None)


# ---------------------------------------------------------------------------
# La prueba de producto: contra la base, no contra la funcion
# ---------------------------------------------------------------------------

TOLERANCIA = 0.02          # 2%: redondeo de la fuente, no error de lectura
MINIMO_PROCESOS = 5        # por debajo de esto la senal no significa nada


def _conexion():
    try:
        from carga import conexion
    except ImportError:                                  # sin psycopg (Windows ARM64)
        pytest.skip("psycopg no disponible: esta prueba corre en Actions")
    import os
    if not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("sin SUPABASE_DB_URL")
    return conexion()


def test_los_renglones_suman_el_referencial_del_proceso():
    """La comprobacion que faltaba, y la unica que habria atrapado D-041.

    Se excluye subasta inversa porque no publica referencial en ningun release: alli el
    arbitro es el adjudicado, que llega despues de que el proceso cierre.
    """
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            select count(*),
                   count(*) filter (where abs(suma - ref) / ref <= %s)
            from (
                select i.ocid,
                       sum(i.monto_linea) suma,
                       max(p.referencial)  ref
                from proceso_item i
                join proceso_resumen p using (ocid)
                where p.referencial > 0
                  and p.metodo not ilike 'Subasta Inversa%%'
                  and i.monto_linea is not null
                group by i.ocid
            ) x
        """, (TOLERANCIA,))
        total, cuadran = cur.fetchone()

    if total < MINIMO_PROCESOS:
        pytest.skip(f"solo {total} procesos con items y referencial: muestra insuficiente")

    assert cuadran / total >= 0.9, (
        f"Solo {cuadran} de {total} procesos tienen renglones que sumen su referencial "
        f"(±{TOLERANCIA:.0%}). Es el sintoma de D-041: `unit.value.amount` leido como lo "
        f"que no es. Revisa normaliza.desglosar_renglon() y el metodo de los que fallan."
    )


def test_ningun_precio_unitario_absurdo():
    """Un precio por unidad de siete cifras es casi siempre un total mal leido.

    Lo que se publicaba antes: «LECHE LIQUIDA a 1.260.000 USD la unidad».
    """
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            select count(*) from proceso_item i
            join proceso_resumen p using (ocid)
            where i.precio_unitario > 1000000
              and i.cantidad > 100
        """)
        (absurdos,) = cur.fetchone()

    assert absurdos == 0, (
        f"{absurdos} items con precio unitario por encima de 1.000.000 USD y mas de 100 "
        f"unidades. Eso no es un precio, es un total mal desglosado."
    )
