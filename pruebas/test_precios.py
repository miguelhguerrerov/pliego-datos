"""El benchmark de precio unitario: la función que se cobra.

Las reglas que se prueban aquí no son de presentación sino de honestidad estadística.
Un benchmark mal calculado es peor que no tenerlo: el cliente oferta con él.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

_spec = importlib.util.spec_from_file_location("precios", RAIZ / "src" / "precios.py")
precios = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(precios)


def item(cpc="3525015266", anio=2025, unidad="Unidad", precio=30.0, cantidad=1, ocid="o"):
    return {"cpc": cpc, "anio": anio, "unidad": unidad, "precio_unitario": precio,
            "cantidad": cantidad, "ocid": ocid}


def test_la_ventana_excluye_los_meses_sin_cerrar():
    """24 meses que terminan en el corte, no en hoy: un mes tarda 4 o 5 en cerrar y
    un benchmark sobre datos a medio llenar sale sesgado. Ver D-009."""
    from agrega import corte_estadistico

    ventana = precios.meses_de_la_ventana()
    assert len(ventana) == precios.VENTANA_MESES
    assert max(ventana) == corte_estadistico()


def test_no_se_publica_precio_con_muestra_insuficiente():
    """Una mediana sobre cuatro observaciones es peor que no dar mediana: el cliente
    ofertaría con ella."""
    from agrega import N_MINIMO

    pocos, _ = precios.calcular([item(ocid=f"o{i}") for i in range(N_MINIMO - 1)])
    assert pocos == []

    bastantes, _ = precios.calcular([item(ocid=f"o{i}") for i in range(N_MINIMO)])
    assert len(bastantes) == 1


def test_sin_unidad_no_entra_en_la_distribucion():
    """Sin unidad dos precios no son comparables: no es lo mismo el precio de una caja
    que el de una unidad. Cuenta para el tamaño de mercado, no para la mediana."""
    items = [item(ocid=f"o{i}") for i in range(10)]
    items.append(item(unidad=None, precio=99999, ocid="sin-unidad"))
    filas, mercado = precios.calcular(items)
    assert filas[0][3] == 10, "el ítem sin unidad no debe contar en la distribución"
    assert mercado, "pero sí debe contar para el tamaño de mercado"


def test_los_percentiles_estan_ordenados():
    items = [item(precio=float(p), ocid=f"o{p}") for p in range(10, 110)]
    (fila,), _ = precios.calcular(items)
    _, _, _, n, p10, p25, mediana, p75, p90, minimo, maximo = fila
    assert n == 100
    assert minimo <= p10 <= p25 <= mediana <= p75 <= p90 <= maximo


def test_unidades_distintas_no_se_mezclan():
    """Comparar el precio por caja con el precio por unidad da una mediana sin sentido."""
    items = ([item(unidad="Unidad", precio=10, ocid=f"u{i}") for i in range(10)] +
             [item(unidad="Caja", precio=200, ocid=f"c{i}") for i in range(10)])
    filas, _ = precios.calcular(items)
    assert len(filas) == 2
    por_unidad = {f[2]: f[6] for f in filas}
    assert por_unidad["Unidad"] == 10 and por_unidad["Caja"] == 200


def test_falla_si_casi_nada_es_utilizable():
    """Regla 2.2 del método: si la mayoría de ítems se descarta, algo cambió en la
    fuente y hay que enterarse aquí, no al publicar el benchmark."""
    basura = [{"cpc": None, "anio": None} for _ in range(100)]
    with pytest.raises(SystemExit, match="utilizables"):
        precios.calcular(basura + [item()])
