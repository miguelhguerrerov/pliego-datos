"""El árbol de mercado: coherencia entre niveles.

La regla que protege todo esto (D-045): **solo el monto y el número de procesos son
aditivos**. Los distintos, las medianas y los percentiles se calculan en cada nivel
desde los procesos crudos. Estas pruebas hacen imposible que alguien "optimice" el
cálculo sumando hijos sin que se entere.

Necesitan base: corren en Actions con el resto de la suite.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))


def _conexion():
    if not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("sin SUPABASE_DB_URL")
    try:
        from carga import conexion
    except ImportError:
        pytest.skip("psycopg no disponible: corre en Actions")
    return conexion()


def test_lo_aditivo_cuadra_entre_niveles():
    """El monto de cada división es la suma exacta de sus grupos, y el de cada
    sección la de sus divisiones. Si no cuadra, algún proceso cae en dos ramas."""
    with _conexion() as con, con.cursor() as cur:
        # Solo niveles 1-3: en el nivel 4 hay 25 procesos enganchados directamente a
        # una clase (sin subclase en el arbol), asi que una clase puede sumar mas que
        # sus subclases sin que sea un error.
        cur.execute("""
            with hijos as (
                select padre, sum(monto) monto, sum(n_procesos) n
                from mercado_nodo where padre is not null group by 1
            )
            select count(*)
            from mercado_nodo p join hijos h on h.padre = p.codigo
            where p.nivel < 4  -- niveles 1-3: todo proceso enganchado tiene hijo
              and (abs(p.monto - h.monto) > greatest(p.monto * 0.0001, 1))
        """)
        (rotos,) = cur.fetchone()
        assert rotos == 0, (
            f"{rotos} nodos cuyo monto no es la suma de sus hijos. O un proceso "
            f"cae en dos ramas, o el calculo dejo de partir de los procesos crudos."
        )


def test_los_distintos_no_se_suman():
    """El corazón de D-045: los contratistas de un nodo deben ser MENOS O IGUAL que
    la suma de los de sus hijos, y estrictamente menos en algún nodo grande (el
    solapamiento existe). Si alguna vez son iguales en todos, alguien sumó."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            with hijos as (
                select padre, sum(n_contratistas) suma
                from mercado_nodo where padre is not null group by 1
            )
            select
              count(*) filter (where p.n_contratistas > h.suma)          as imposibles,
              count(*) filter (where p.n_contratistas < h.suma)         as con_solape,
              count(*)                                                   as comparables
            from mercado_nodo p join hijos h on h.padre = p.codigo
            where p.nivel <= 3 and p.n_contratistas > 0 and h.suma > 0
        """)
        imposibles, con_solape, comparables = cur.fetchone()
        assert imposibles == 0, (
            f"{imposibles} nodos con MAS contratistas que la suma de sus hijos: "
            f"imposible por construccion."
        )
        assert con_solape > 0, (
            "Ningun nodo tiene menos contratistas que la suma de sus hijos. Eso "
            "significa que el calculo SUMA los distintos en vez de contarlos desde "
            "los procesos: el fallo exacto que D-045 prohibe."
        )


def test_el_arbol_esta_completo_y_con_ceros():
    """Los 3.725 nodos oficiales están, incluidos los vacíos (decisión 18-08), más
    el cubo sin clasificar."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("select count(*), count(*) filter (where n_procesos = 0) from mercado_nodo")
        total, vacios = cur.fetchone()
        assert total == 3726, f"esperados 3725 nodos + sin_clasificar, hay {total}"
        assert vacios > 500, "los nodos sin actividad deben estar, con cero"
        cur.execute("select monto from mercado_nodo where codigo = '_sin_clasificar'")
        fila = cur.fetchone()
        assert fila is not None, "el cubo sin clasificar debe existir"


def test_el_corte_estadistico_se_aplica():
    """Invariante 10: las estadísticas del árbol no incluyen los últimos 4 meses.
    El total del árbol debe ser MENOR que el total crudo de la tabla, y la
    diferencia debe ser exactamente lo que cae después del corte."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            with corte as (select extract(year from current_date)::int*12
                                + extract(month from current_date)::int - 4 as tope)
            select
              (select sum(monto) from mercado_nodo where nivel = 1),
              (select sum(adjudicado) from proceso_resumen
                where cpc_nodo is not null and adjudicado > 0
                  and (anio*12 + mes) <= (select tope from corte))
        """)
        arbol, crudo = cur.fetchone()
        assert arbol is not None and crudo is not None
        assert abs(float(arbol) - float(crudo)) < max(float(crudo) * 1e-6, 1), (
            f"el nivel 1 del arbol ({arbol}) no cuadra con los procesos dentro del "
            f"corte ({crudo}): o el corte no se aplica, o se aplica dos veces"
        )


def test_consulta_de_producto_del_arbol():
    """Regla 1 del método: no «la vista tiene filas» sino «la sección de servicios
    devuelve un mercado navegable con dinero y competencia»."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            select nombre, n_procesos, monto, n_contratistas, n_contratantes
            from mercado_nodo where codigo = '8'
        """)
        fila = cur.fetchone()
        assert fila is not None
        nombre, n, monto, contratistas, contratantes = fila
        assert n > 1000 and float(monto) > 1e8
        assert contratistas > 100 and contratantes > 100
        cur.execute("""
            select count(*) from mercado_nodo
            where padre = '8' and n_procesos > 0
        """)
        (hijos_activos,) = cur.fetchone()
        assert hijos_activos >= 5, "la seccion 8 debe tener divisiones navegables"
