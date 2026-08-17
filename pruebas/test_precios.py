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


# `calcular` necesita saber el metodo de cada proceso porque `unit.value.amount` es el
# total del renglon en subasta inversa y el precio por unidad en el resto (D-041). Estas
# pruebas usan licitacion por omision: es el caso mayoritario y el que estaba mal.
def calcular(items, metodo="Licitación"):
    return precios.calcular(items, {it.get("ocid"): metodo for it in items})


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

    pocos, _ = calcular([item(ocid=f"o{i}") for i in range(N_MINIMO - 1)])
    assert pocos == []

    bastantes, _ = calcular([item(ocid=f"o{i}") for i in range(N_MINIMO)])
    assert len(bastantes) == 1


def test_sin_unidad_no_entra_en_la_distribucion():
    """Sin unidad dos precios no son comparables: no es lo mismo el precio de una caja
    que el de una unidad. Cuenta para el tamaño de mercado, no para la mediana."""
    items = [item(ocid=f"o{i}") for i in range(10)]
    items.append(item(unidad=None, precio=99999, ocid="sin-unidad"))
    filas, mercado = calcular(items)
    assert filas[0][3] == 10, "el ítem sin unidad no debe contar en la distribución"
    assert mercado, "pero sí debe contar para el tamaño de mercado"


def test_los_percentiles_estan_ordenados():
    items = [item(precio=float(p), ocid=f"o{p}") for p in range(10, 110)]
    (fila,), _ = calcular(items)
    _, _, _, n, p10, p25, mediana, p75, p90, minimo, maximo = fila
    assert n == 100
    assert minimo <= p10 <= p25 <= mediana <= p75 <= p90 <= maximo


def test_unidades_distintas_no_se_mezclan():
    """Comparar el precio por caja con el precio por unidad da una mediana sin sentido."""
    items = ([item(unidad="Unidad", precio=10, ocid=f"u{i}") for i in range(10)] +
             [item(unidad="Caja", precio=200, ocid=f"c{i}") for i in range(10)])
    filas, _ = calcular(items)
    assert len(filas) == 2
    por_unidad = {f[2]: f[6] for f in filas}
    assert por_unidad["Unidad"] == 10 and por_unidad["Caja"] == 200


def test_falla_si_casi_nada_es_utilizable():
    """Regla 2.2 del método: si la mayoría de ítems se descarta, algo cambió en la
    fuente y hay que enterarse aquí, no al publicar el benchmark."""
    basura = [{"cpc": None, "anio": None} for _ in range(100)]
    with pytest.raises(SystemExit, match="utilizables"):
        calcular(basura + [item()])


# --- D-041: `unit.value.amount` significa una cosa u otra según el método -----------
#
# D-033 midió subasta inversa y dedujo «total de línea» para todo. Era correcto para
# subasta inversa y falso para el resto: en licitación el mismo campo es el precio por
# unidad, verificado al céntimo (94.102,18 calculado contra 94.102,17 declarado).
#
# Estas pruebas van por pares deliberadamente. Con un solo método no se distingue nada,
# y esa es exactamente la forma que tuvo el fallo las dos veces.

def test_en_subasta_inversa_el_precio_sale_de_dividir():
    """El caso de D-033, ahora con su método puesto. Medido sobre 688 procesos con
    cantidad > 1: como total de línea el error mediano es del 7,0% —que es la baja del
    propio remate—; como precio unitario, del 15.323%.

    Tomarlo por precio unitario publicaba «LECHE LÍQUIDA a 1.260.000 USD la unidad»."""
    items = [
        {"cpc": "35260", "anio": 2025, "unidad": "Unidad",
         "cantidad": 600_000, "precio_unitario": 45_600, "ocid": f"o{i}"}
        for i in range(6)
    ]
    filas_precio, _ = calcular(items, "Subasta Inversa Electrónica")
    assert filas_precio, "debería publicarse una distribución con n=6"
    mediana = filas_precio[0][6]
    assert abs(mediana - 0.076) < 0.001, (
        f"la mediana es {mediana}: 600.000 unidades por 45.600 USD son 0,076 la unidad, "
        f"no 45.600"
    )


def test_en_licitacion_el_precio_ya_viene_dado():
    """El caso que D-033 no miró. Aquí dividir es el error: una alcantarilla de 2000 mm
    a 18,82 el metro son 564,60 los treinta metros, no 0,63."""
    items = [
        {"cpc": "42190", "anio": 2025, "unidad": "Metro",
         "cantidad": 30, "precio_unitario": 18.82, "ocid": f"o{i}"}
        for i in range(6)
    ]
    filas_precio, filas_mercado = calcular(items, "Licitación")
    assert filas_precio[0][6] == pytest.approx(18.82), (
        f"la mediana es {filas_precio[0][6]}: en licitación el campo YA es el precio por "
        f"metro. Dividirlo entre 30 da 0,63, que no es el precio de nada."
    )
    assert filas_mercado[0][3] == pytest.approx(6 * 564.6), (
        "el mercado son seis renglones de 30 × 18,82 = 564,60 cada uno"
    )


def test_el_tamano_de_mercado_de_una_subasta_no_multiplica():
    """Sumar cantidad × total daba 8,1 billones de dólares para un solo CPC en un año:
    veinte veces el PIB del Ecuador, en una cifra que el producto publica."""
    items = [
        {"cpc": "35260", "anio": 2025, "unidad": "Unidad",
         "cantidad": 600_000, "precio_unitario": 45_600, "ocid": "a"},
        {"cpc": "35260", "anio": 2025, "unidad": "Unidad",
         "cantidad": 1_000, "precio_unitario": 5_000, "ocid": "b"},
    ]
    _, filas_mercado = calcular(items, "Subasta Inversa Electrónica")
    monto = filas_mercado[0][3]
    assert monto == 50_600, f"el mercado son 45.600 + 5.000 = 50.600, no {monto:,}"


def test_un_item_sin_metodo_no_se_adivina():
    """Sin método no se sabe qué es `amount`. Caer en una rama por omisión es el fallo
    que se está corrigiendo, así que se corta con un mensaje que diga qué hacer."""
    items = [{"cpc": "35260", "anio": 2025, "unidad": "Unidad",
              "cantidad": 5, "precio_unitario": 100, "ocid": f"o{i}"} for i in range(10)]
    with pytest.raises(SystemExit, match="no están en el Parquet de procesos"):
        precios.calcular(items, {})


def test_una_cifra_de_mercado_absurda_no_pasa_desapercibida():
    """La prueba que faltaba: comprobé el número de filas y no su magnitud. Un total de
    mercado por encima del PIB del país es imposible por construcción."""
    items = [{"cpc": "35260", "anio": 2025, "unidad": "Unidad",
              "cantidad": 1, "precio_unitario": 1_000, "ocid": f"o{i}"} for i in range(10)]
    _, filas_mercado = calcular(items)
    for fila in filas_mercado:
        assert fila[3] < 2e11, (
            f"el mercado de un CPC en un año da {fila[3]:,.0f} USD. La contratación "
            f"pública entera del Ecuador ronda los 7.000 millones al año."
        )
