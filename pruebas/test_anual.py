"""Las series anuales (D-046): once años que tienen que contar la historia real.

Consultas de producto, no de forma: la serie de construcción tiene que existir y
moverse, la mediana no puede sumarse, y el año en curso tiene que estar incompleto
— si pareciera completo, algo cuenta de más.
"""
from __future__ import annotations

import datetime as dt
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


def test_la_serie_cubre_los_once_anios():
    with _conexion() as con, con.cursor() as cur:
        cur.execute("select count(distinct anio), min(anio), max(anio) from mercado_nodo_anual")
        n, desde, hasta = cur.fetchone()
        if not n:
            pytest.skip("mercado_nodo_anual aún sin cargar")
        assert desde == 2015 and hasta >= dt.date.today().year - 1
        assert n >= 10, f"solo {n} años en la serie"


def test_construccion_tiene_serie_completa_y_con_dinero():
    """La consulta que motivó todo (D-046): «cómo ha evolucionado este mercado»."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            select count(*), min(monto), max(monto)
            from mercado_nodo_anual where codigo = '54' and anio < extract(year from now())
        """)
        anios, minimo, maximo = cur.fetchone()
        if not anios:
            pytest.skip("sin datos aún")
        assert anios >= 9, f"la división 54 solo tiene {anios} años"
        assert float(minimo) > 1e7, "un año de construcción por debajo de 10 M no es creíble"
        assert float(maximo) > 1e8


def test_los_distintos_no_se_suman_entre_anios_ni_niveles():
    """Un contratista activo en 2020 y 2021 cuenta una vez en cada año; y el de la
    división no es la suma de sus grupos. Igual que en mercado_nodo (D-045)."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            with hijos as (
                select left(codigo, 2) padre, anio, sum(n_contratistas) suma
                from mercado_nodo_anual where nivel = 3 group by 1, 2
            )
            select count(*) filter (where p.n_contratistas > h.suma) imposibles,
                   count(*) filter (where p.n_contratistas < h.suma) con_solape
            from mercado_nodo_anual p
            join hijos h on h.padre = p.codigo and h.anio = p.anio
            where p.nivel = 2 and p.n_contratistas > 0
        """)
        imposibles, con_solape = cur.fetchone()
        assert imposibles == 0, f"{imposibles} celdas con más contratistas que sus hijos"
        assert con_solape > 0, (
            "ninguna celda tiene menos contratistas que la suma de sus grupos: "
            "alguien está sumando los distintos (D-045/D-046)"
        )


def test_el_monto_anual_cuadra_contra_hecho_mes():
    """La reconstrucción desde el Parquet contra la contabilidad del CSV, que trae el
    adjudicado real. No serán iguales —subasta inversa va por convocado (~7% alto) y
    algún proceso no trae ítems— pero un año por debajo del 60% o por encima del 115%
    del CSV es un fallo de reconstrucción, no una diferencia de método."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            with arbol as (
                select anio, sum(monto) m from mercado_nodo_anual
                where nivel = 1 or codigo = '_sin_clasificar' group by 1
            ),
            csv as (
                select anio, sum(adjudicado) m from hecho_mes group by 1
            )
            select a.anio, round(a.m / nullif(c.m, 0), 3)
            from arbol a join csv c using (anio)
            where a.anio < extract(year from now())
            order by a.anio
        """)
        filas = cur.fetchall()
        if not filas:
            pytest.skip("sin datos aún")
        malos = [(a, float(r)) for a, r in filas if r is None or not 0.60 <= float(r) <= 1.15]
        assert not malos, (
            f"años cuya reconstrucción no cuadra con el CSV (razón árbol/CSV): {malos}"
        )


def test_precio_anual_solo_publica_con_muestra():
    """Invariante 11: ninguna fila con n < 10."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("select count(*) from precio_cpc_anual where n < 10")
        assert cur.fetchone()[0] == 0


def test_precio_anual_tiene_series_largas():
    """El motivo de la tabla: productos con 5+ años de precio para dibujar tendencia."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            select count(*) from (
                select cpc, unidad from precio_cpc_anual
                group by 1, 2 having count(distinct anio) >= 5
            ) x
        """)
        (largas,) = cur.fetchone()
        if largas == 0:
            cur.execute("select count(*) from precio_cpc_anual")
            if cur.fetchone()[0] == 0:
                pytest.skip("precio_cpc_anual aún sin cargar")
        assert largas > 200, (
            f"solo {largas} productos con 5+ años de serie: o la reconstrucción "
            f"histórica falló o los ítems viejos no traen unidad"
        )
