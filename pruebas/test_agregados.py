"""Las reglas de negocio que viven en el cálculo de agregados.

Están aquí y no en la interfaz para que no se puedan olvidar: excluir los meses sin
cerrar y no publicar con muestra insuficiente son invariantes del producto, no
decisiones de presentación.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agrega import MESES_SIN_CERRAR, N_MINIMO, calcular, corte_estadistico  # noqa: E402
from ingesta import _dentro_de_ventana, a_hecho_mes  # noqa: E402


def hecho(anio, mes, comp, prov, metodo, n=1, ref=None, adj=None):
    return (anio, mes, comp, prov, metodo, n, ref, adj)


# --- ventana de análisis --------------------------------------------------------

def test_corte_excluye_los_ultimos_cuatro_meses():
    """Un mes tarda 4 o 5 meses en cerrar. Julio de 2026 estaba al 59% en agosto:
    un benchmark calculado sobre él saldría sesgado. Ver docs/decisiones.md D-009."""
    anio, mes = corte_estadistico(dt.date(2026, 8, 14))
    assert (anio, mes) == (2026, 4)
    assert MESES_SIN_CERRAR == 4


def test_proceso_resumen_solo_guarda_la_ventana_del_radar():
    hoy = dt.date(2026, 8, 14)
    assert _dentro_de_ventana(2026, 8, hoy) is True
    assert _dentro_de_ventana(2025, 9, hoy) is True     # 23 meses atrás
    assert _dentro_de_ventana(2024, 8, hoy) is False    # 24 meses: fuera
    assert _dentro_de_ventana(2015, 1, hoy) is False


# --- hecho_mes ------------------------------------------------------------------

def test_hecho_mes_colapsa_al_grano_minimo():
    """Sin ocid ni objeto: es lo que permite guardar once años sin romper los 500 MB."""
    filas = [
        # (ocid, fecha, anio, mes, estado, metodo, cpc, cat, comp, prov, ref, adj, ...)
        ("a", None, 2024, 2, "cerrado", "Menor Cuantia", None, None, "C1", "P1", 100, 90),
        ("b", None, 2024, 2, "cerrado", "Menor Cuantia", None, None, "C1", "P1", 200, 180),
        ("c", None, 2024, 2, "cerrado", "Licitacion", None, None, "C1", "P2", 500, 400),
    ]
    hechos = a_hecho_mes(filas, 2024, 2)
    assert len(hechos) == 2
    por_metodo = {h[4]: h for h in hechos}
    assert por_metodo["Menor Cuantia"][5] == 2      # dos procesos agrupados
    assert por_metodo["Menor Cuantia"][6] == 300    # referencial sumado
    assert por_metodo["Menor Cuantia"][7] == 270    # adjudicado sumado


# --- agregados ------------------------------------------------------------------

def test_contrapartes_es_la_tesis_del_producto():
    """Crecer es diversificar compradores: la métrica tiene que contar entidades
    distintas, no procesos. Ver docs/propuesta-valor.md §1."""
    hechos = [
        hecho(2024, 1, "C1", "P1", "m", adj=100),
        hecho(2024, 2, "C2", "P1", "m", adj=100),
        hecho(2024, 3, "C2", "P1", "m", adj=100),   # mismo comprador, no suma contraparte
    ]
    r = {(f[0], f[2]): f for f in calcular(hechos)["entidad_ano"]}
    proveedor = r[("P1", "proveedor")]
    assert proveedor[3] == 300      # monto
    assert proveedor[5] == 2        # dos compradores distintos, no tres procesos


def test_no_se_publica_estadistica_con_muestra_insuficiente():
    """Una mediana sobre tres observaciones es peor que no tener mediana."""
    pocos = [hecho(2024, 1, "C", "P", "Licitacion", ref=100, adj=90) for _ in range(N_MINIMO - 1)]
    assert calcular(pocos)["baja_metodo"] == []

    suficientes = [hecho(2024, 1, "C", "P", "Licitacion", ref=100, adj=90) for _ in range(N_MINIMO)]
    assert len(calcular(suficientes)["baja_metodo"]) == 1


def test_la_baja_excluye_los_meses_sin_cerrar():
    """Meses recientes no entran aunque tengan datos: están a medio llenar."""
    reciente = (dt.date.today().year, dt.date.today().month)
    hechos = [hecho(reciente[0], reciente[1], "C", "P", "Licitacion", ref=100, adj=50)
              for _ in range(20)]
    assert calcular(hechos)["baja_metodo"] == []


def test_la_baja_descarta_ratios_imposibles():
    """Adjudicar por encima del 150% del referencial es error de captura en la fuente."""
    validos = [hecho(2023, 1, "C", "P", "Licitacion", ref=100, adj=90) for _ in range(10)]
    basura = [hecho(2023, 1, "C", "P", "Licitacion", ref=1, adj=99999) for _ in range(10)]
    r = calcular(validos + basura)["baja_metodo"]
    assert len(r) == 1
    assert r[0][2] == 10            # solo los válidos entraron
    assert r[0][3] == 0.9


def test_relacion_alimenta_compradores_huerfanos():
    hechos = [
        hecho(2024, 1, "C1", "P1", "m", n=2, adj=500),
        hecho(2024, 5, "C1", "P1", "m", n=1, adj=300),
        hecho(2024, 1, "C2", "P1", "m", n=1, adj=100),
    ]
    r = {(f[0], f[1]): f for f in calcular(hechos)["relacion"]}
    assert r[("C1", "P1")][3] == 800
    assert r[("C1", "P1")][4] == 3
    assert ("C2", "P1") in r


# --- tabla entidad --------------------------------------------------------------

def test_nombre_canonico_por_moda_no_por_el_ultimo():
    """Los registros antiguos tienen mas erratas: el mas frecuente es mejor criterio.
    Ver docs/decisiones.md D-017."""
    from agrega import construir_entidad

    entidad_ano = [("1791240502001", 2024, "proveedor", 250000, 5, 3)]
    nombres = [
        ("1791240502001", "CEDIMED CIA LTDA", 2),
        ("1791240502001", "CEDIMED CIA. LTDA.", 9),
    ]
    fila = construir_entidad(entidad_ano, nombres)[0]
    assert fila[1] == "CEDIMED CIA. LTDA."


def test_entidad_marca_persona_natural_para_enmascarar():
    """El RUC de persona natural contiene la cedula: la marca decide el
    enmascaramiento. Ver docs/legal.md §1."""
    from agrega import construir_entidad

    filas = {f[0]: f for f in construir_entidad(
        [("1104567890001", 2024, "proveedor", 50000, 2, 1),
         ("1791240502001", 2024, "proveedor", 50000, 2, 1)],
        [])}
    assert filas["1104567890001"][3] is True    # persona natural
    assert filas["1791240502001"][3] is False   # sociedad


def test_tramo_situa_el_segmento_objetivo():
    from agrega import tramo_de

    assert tramo_de(3_000) == "<5K"
    assert tramo_de(250_000) == "100-500K"      # segmento objetivo
    assert tramo_de(1_500_000) == "500K-2M"     # segmento objetivo
    assert tramo_de(50_000_000) == ">10M"
