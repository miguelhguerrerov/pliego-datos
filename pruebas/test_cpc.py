"""La clasificación CPC oficial: el árbol del que cuelga todo el mercado.

Las pruebas locales validan los ficheros de referencia (no necesitan base); las de
base comprueban lo cargado. Ver D-045.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import cpc  # noqa: E402


# ---------------------------------------------------------------------------
# Sobre los ficheros de referencia (sin base)
# ---------------------------------------------------------------------------

def test_el_arbol_valida_y_tiene_los_recuentos_oficiales():
    arbol = cpc.leer_arbol()
    por_nivel: dict[int, int] = {}
    for _, nivel, _, _ in arbol:
        por_nivel[nivel] = por_nivel.get(nivel, 0) + 1
    assert por_nivel == {1: 10, 2: 73, 3: 313, 4: 1192, 5: 2137}


def test_todo_padre_es_el_prefijo_de_su_hijo():
    """La regla que hace seguro truncar por posición: el árbol ES el prefijo."""
    arbol = {c: (n, p) for c, n, _, p in cpc.leer_arbol()}
    for codigo, (nivel, padre) in arbol.items():
        if nivel > 1:
            assert padre == codigo[:-1]
            assert padre in arbol


def test_los_productos_cuelgan_del_arbol():
    arbol = cpc.leer_arbol()
    subclases = {c for c, n, _, _ in arbol if n == 5}
    productos = cpc.leer_productos(subclases)
    assert len(productos) >= 30_000
    sin = sum(1 for _, _, _, s in productos if s is None)
    # Medido al validar el fichero: un punado de codigos cortos fuera del arbol.
    assert sin < len(productos) * 0.01


def test_el_umbral_vae_es_una_fraccion():
    assert cpc._umbral("40,00%") == 0.4
    assert cpc._umbral("0,00%") == 0.0
    assert cpc._umbral("20,18%") == 0.2018
    assert cpc._umbral("") is None


def test_construccion_es_dos_divisiones_y_no_87_fragmentos():
    """El motivo del cambio entero, como prueba: en la CPC oficial, «construcción»
    son las divisiones 53 y 54 con nombre propio — no 87 categorías repetidas."""
    nombres = {c: nom for c, n, nom, _ in cpc.leer_arbol() if n == 2}
    assert "CONSTRUCCIONES" in nombres["53"].upper()
    assert "CONSTRUCCION" in nombres["54"].upper()


# ---------------------------------------------------------------------------
# Sobre lo cargado (necesitan base; corren en Actions)
# ---------------------------------------------------------------------------

def _conexion():
    if not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("sin SUPABASE_DB_URL")
    try:
        from carga import conexion
    except ImportError:
        pytest.skip("psycopg no disponible: corre en Actions")
    return conexion()


def test_cargado_completo_y_conforme():
    with _conexion() as con, con.cursor() as cur:
        cur.execute("select nivel, count(*) from cpc_nivel group by 1")
        niveles = dict(cur.fetchall())
        if not niveles:
            pytest.skip("cpc_nivel aun sin cargar")
        assert niveles == {1: 10, 2: 73, 3: 313, 4: 1192, 5: 2137}
        cur.execute("select count(*), count(umbral_vae) from cpc_producto")
        total, con_vae = cur.fetchone()
        assert total >= 30_000
        assert con_vae == total, "el catalogo trae VAE para todos; si falta, cambio"


def test_ningun_nombre_de_nodo_vacio_ni_con_residuo():
    """Lo que enterro a la taxonomia anterior: nombres con respuestas del LLM dentro.
    La oficial no puede tener nada parecido."""
    with _conexion() as con, con.cursor() as cur:
        cur.execute("""
            select count(*) from cpc_nivel
            where length(trim(nombre)) < 3
               or nombre ~ '(?i)(lo siento|como modelo|aqui tienes|no, es)'
        """)
        assert cur.fetchone()[0] == 0
