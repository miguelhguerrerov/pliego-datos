"""Guardias sobre la base cargada: presupuesto de espacio y cifras de control.

Se salta sin `SUPABASE_DB_URL` o sin el controlador, así que no estorba en local
—Windows ARM64 no tiene ruedas de psycopg— y corre en Actions, que es donde importa.

Automatiza el contraste que se hizo a mano tras el primer backfill. Sin él, una
corrupción silenciosa —un normalizador que empieza a descartar filas, una fuente que
cambia— solo se notaría cuando un cliente pregunte por qué falta su contrato.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("psycopg", reason="sin controlador de Postgres")
if not os.environ.get("SUPABASE_DB_URL"):
    pytest.skip("sin SUPABASE_DB_URL", allow_module_level=True)

from carga import ALARMA_MB, PRESUPUESTO_MB, conexion  # noqa: E402

# Cifras verificadas contra la fuente el 14 de agosto de 2026. Ver docs/datos.md §9.
PROCESOS_2024 = 219_185
TOTAL_HISTORICO = 2_774_263
TOLERANCIA = 0.001          # 0,1%

# Ratio adjudicado/referencial, mediana 2024. Si esto se mueve, algo se rompió en la
# normalización: son medianas sobre miles de observaciones, no cifras volátiles.
BAJA_ESPERADA = {
    "Cotización": 0.951,
    "Menor Cuantía": 1.000,
    "Catálogo electrónico - Compra directa": 1.000,
}


@pytest.fixture(scope="module")
def con():
    with conexion() as c:
        yield c


def _uno(con, sql, *args):
    with con.cursor() as cur:
        cur.execute(sql, args)
        fila = cur.fetchone()
        return fila[0] if fila else None


def test_la_base_no_supera_el_presupuesto(con):
    """Invariante 2. Al superarlo, aplicar la primera válvula de docs/agregados.md:
    ventana de proceso_resumen de 24 a 18 meses."""
    mb = float(_uno(con, "select coalesce(round(sum(mb),2),0) from v_tamano_base"))
    assert mb <= PRESUPUESTO_MB, (
        f"La base ocupa {mb} MB y el presupuesto duro es {PRESUPUESTO_MB}. "
        f"Aplica la primera válvula: acorta la ventana de proceso_resumen a 18 meses."
    )
    if mb > ALARMA_MB:
        pytest.warns  # informativo: la alarma no falla la construcción
        print(f"AVISO: {mb} MB, por encima de la alarma de {ALARMA_MB} MB")


def test_cuadra_con_la_fuente(con):
    """La ingesta es fiel: 219 185 procesos de 2024 frente a 219 186 declarados."""
    n = _uno(con, "select coalesce(sum(registros),0) from cobertura where anio=2024")
    if not n:
        pytest.skip("2024 sin cargar")
    desvio = abs(n - PROCESOS_2024) / PROCESOS_2024
    assert desvio <= TOLERANCIA, (
        f"2024 tiene {n:,} procesos y se esperaban {PROCESOS_2024:,} "
        f"({desvio:.2%} de desvío). Revisa docs/datos.md §9."
    )


def test_el_historico_esta_completo(con):
    total = _uno(con, "select coalesce(sum(registros),0) from cobertura")
    if total < TOTAL_HISTORICO * 0.5:
        pytest.skip("backfill incompleto")
    desvio = abs(total - TOTAL_HISTORICO) / TOTAL_HISTORICO
    assert desvio <= TOLERANCIA, f"total {total:,}, esperado {TOTAL_HISTORICO:,}"


def test_la_baja_por_metodo_no_se_movio(con):
    """Detecta corrupción silenciosa en la normalización: si menor cuantía deja de
    adjudicarse al 100% del referencial, algo cambió y no son los datos."""
    with con.cursor() as cur:
        cur.execute(
            "select metodo, ratio_mediana::float from baja_metodo where anio=2024"
        )
        real = dict(cur.fetchall())
    if not real:
        pytest.skip("agregados sin calcular")

    for metodo, esperado in BAJA_ESPERADA.items():
        if metodo not in real:
            continue
        assert abs(real[metodo] - esperado) < 0.01, (
            f"{metodo}: ratio {real[metodo]:.3f}, esperado {esperado:.3f}. "
            f"Revisa la normalización antes de dar el dato por bueno."
        )


def test_los_estados_intermedios_siguen_llegando(con):
    """El radar depende de ellos. Si la fuente dejara de publicarlos, el producto
    se queda sin su función principal y conviene enterarse pronto."""
    n = _uno(
        con,
        "select count(*) from proceso_resumen where estado in ('planificacion','abierto')",
    )
    if _uno(con, "select count(*) from proceso_resumen") == 0:
        pytest.skip("sin datos cargados")
    assert n > 0, "no hay procesos en planificación ni abiertos: el radar quedaría vacío"


def test_ninguna_estadistica_con_muestra_insuficiente(con):
    """Invariante del producto: nada se publica con n < 5."""
    n = _uno(con, "select count(*) from baja_metodo where n < 5")
    assert n == 0, f"{n} filas de baja_metodo con menos de 5 observaciones"
