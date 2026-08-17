"""El detalle de los procesos abiertos: la excepción medida al invariante 1.

Ver docs/decisiones.md D-035.
"""

import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from abiertos import TABLAS, filtrar, meses_a_mirar  # noqa: E402


def _detalle(**kw):
    # `procesos` hace falta porque el desglose de cada renglón depende del método:
    # `unit.value.amount` es el total en subasta inversa y el precio por unidad en el
    # resto. Ver D-041.
    base = dict(items=[], oferentes=[], pujas=[], consultas=[], lotes=[], procesos=[])
    base.update(kw)
    return SimpleNamespace(**base)


def test_solo_entra_lo_que_sigue_abierto():
    """Es lo único que mantiene la tabla acotada. Si entrara todo, el detalle de 280.000
    procesos son cientos de MB y se rompe el presupuesto — que es exactamente el motivo
    por el que existe el invariante 1."""
    d = _detalle(
        items=[{"ocid": "abierto", "item_id": "1", "origen": "tender", "cpc": "35260",
                "descripcion": "x", "cantidad": 1, "unidad": "u", "precio_unitario": 10},
               {"ocid": "cerrado", "item_id": "1", "origen": "tender", "cpc": "35260",
                "descripcion": "y", "cantidad": 1, "unidad": "u", "precio_unitario": 10}],
    )
    filas = filtrar(d, {"abierto"})
    assert len(filas["proceso_item"]) == 1
    assert filas["proceso_item"][0][0] == "abierto"


def test_el_metodo_del_proceso_llega_hasta_el_renglon():
    """D-041: el mismo ítem tiene que salir distinto según el método de su proceso.

    Si `filtrar` dejara de mirar `detalle.procesos`, los dos casos darían lo mismo y la
    ficha volvería a publicar «acero de refuerzo, 5.063 kg, total 2 USD». Esta prueba es
    la que lo impide, porque compara los dos métodos en la misma llamada.
    """
    def renglon(ocid):
        return {"ocid": ocid, "item_id": "1", "origen": "tender", "cpc": "35260",
                "descripcion": "x", "cantidad": 50, "unidad": "u", "precio_unitario": 1000}

    d = _detalle(
        items=[renglon("sie"), renglon("lico")],
        procesos=[{"ocid": "sie", "metodo": "Subasta Inversa Electrónica"},
                  {"ocid": "lico", "metodo": "Licitación"}],
    )
    filas = {f[0]: f for f in filtrar(d, {"sie", "lico"})["proceso_item"]}
    # (ocid, item_id, origen, cpc, descripcion, cantidad, unidad, precio, monto_linea)
    assert filas["sie"][7:] == (20.0, 1000.0), "en subasta inversa el campo es el total"
    assert filas["lico"][7:] == (1000.0, 50000.0), "en licitación es el precio por unidad"


def test_las_consultas_conservan_pregunta_y_respuesta():
    """Es el dato por el que existe todo esto: la entidad diciendo en público por qué
    descalifica a alguien."""
    d = _detalle(consultas=[{
        "ocid": "a", "consulta_id": "c1", "fecha": "2024-12-19T00:00:00",
        "autor_ruc": "0991266461001", "autor": "INPROFARM",
        "pregunta": "EL OFERENTE NO PRESENTA EL CERTIFICADO DE DISTRIBUIDOR",
        "respuesta": "Se adjunta documentación solicitada.",
        "fecha_respuesta": "2024-12-23T00:00:00",
    }])
    f = filtrar(d, {"a"})["proceso_consulta"][0]
    assert f[4] == "INPROFARM"
    assert "CERTIFICADO DE DISTRIBUIDOR" in f[5]
    assert "adjunta" in f[6]
    assert isinstance(f[2], dt.datetime) and isinstance(f[7], dt.datetime)


def test_una_clave_repetida_no_revienta_la_carga():
    """La fuente reparte un proceso entre varios métodos alguna vez. `copy` no perdona
    un duplicado de clave primaria, y el fallo llega al final de la carga — con todo el
    trabajo de descarga ya hecho."""
    q = {"ocid": "a", "consulta_id": "c1", "fecha": None, "autor_ruc": None,
         "autor": "X", "pregunta": "p", "respuesta": "r", "fecha_respuesta": None}
    filas = filtrar(_detalle(consultas=[q, dict(q)]), {"a"})
    assert len(filas["proceso_consulta"]) == 1


def test_un_oferente_repetido_cuenta_una_vez():
    o = {"ocid": "a", "ruc": "0991284214001", "nombre": "DITECA", "gano": False}
    filas = filtrar(_detalle(oferentes=[o, dict(o, gano=True)]), {"a"})
    assert len(filas["proceso_oferente"]) == 1


def test_se_miran_el_mes_en_curso_y_el_anterior():
    """Un proceso abierto se convocó hace días o semanas, no meses. Y en enero hay que
    cruzar al año anterior, que es donde suelen romperse estas cuentas."""
    assert meses_a_mirar(dt.date(2026, 1, 15)) == [(2025, 12), (2026, 1)]
    assert meses_a_mirar(dt.date(2026, 8, 3)) == [(2026, 7), (2026, 8)]


def test_las_columnas_declaradas_calzan_con_las_filas():
    """Cada tabla se carga contra una lista de columnas escrita aparte. Si divergen, el
    desajuste aparece al escribir en producción."""
    d = _detalle(
        items=[{"ocid": "a", "item_id": "1", "origen": "tender", "cpc": "1",
                "descripcion": "d", "cantidad": 1, "unidad": "u", "precio_unitario": 1}],
        oferentes=[{"ocid": "a", "ruc": "r", "nombre": "n", "gano": True}],
        pujas=[{"ocid": "a", "puja_id": "p", "ruc": "r", "fecha": None, "valor": 1}],
        consultas=[{"ocid": "a", "consulta_id": "c", "fecha": None, "autor_ruc": None,
                    "autor": "a", "pregunta": "p", "respuesta": "r", "fecha_respuesta": None}],
        lotes=[{"ocid": "a", "lote_id": "l", "titulo": "t", "monto": 1, "tecnicas": None}],
    )
    filas = filtrar(d, {"a"})
    for tabla, columnas in TABLAS.items():
        assert filas[tabla], f"{tabla} sin filas de muestra"
        assert len(filas[tabla][0]) == len(columnas), (
            f"{tabla}: {len(filas[tabla][0])} valores contra {len(columnas)} columnas"
        )
