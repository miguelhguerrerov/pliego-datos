"""La fuente entrega UTF-8 válido. Estas pruebas fijan esa afirmación.

Si alguna falla contra datos reales, la fuente cambió: actualiza docs/datos.md §5.1
antes de tocar el código. Ver docs/decisiones.md D-011.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codificacion import ErrorCodificacion, decodificar, resumen_no_ascii  # noqa: E402


def test_utf8_valido_se_decodifica():
    # Así llega realmente "Catálogo" desde el SERCOP.
    assert decodificar(b"Cat\xc3\xa1logo electr\xc3\xb3nico", "prueba") == "Catálogo electrónico"
    assert decodificar(b"Contrataci\xc3\xb3n", "prueba") == "Contratación"
    assert decodificar(b"Menor Cuant\xc3\xada", "prueba") == "Menor Cuantía"
    assert decodificar(b"COMPA\xc3\x91IA", "prueba") == "COMPAÑIA"


def test_latin1_detiene_la_ingesta():
    """Si la fuente pasara a latin-1, hay que enterarse, no adivinar."""
    with pytest.raises(ErrorCodificacion, match="no es UTF-8 válido"):
        decodificar(b"Cat\xf3logo", "prueba")


def test_doble_codificacion_detiene_la_ingesta():
    """Texto ya corrupto en origen no se carga: en la base sería indistinguible
    de un dato legítimo."""
    with pytest.raises(ErrorCodificacion, match="doble codificación"):
        decodificar("CatÃ¡logo".encode("utf-8"), "prueba")


def test_resumen_no_ascii():
    # á una vez, ó dos veces (electrónico, cotización), í una vez
    r = resumen_no_ascii("Catálogo electrónico cotización Cuantía")
    assert r["ó"] == 2
    assert r["á"] == 1
    assert r["í"] == 1


@pytest.mark.parametrize("anio,mes", [(2024, 2)])
def test_fuente_real_es_utf8(anio, mes):
    """Contra la fuente en vivo. Se salta si no hay red."""
    from descarga import ErrorDescarga, descargar_mes

    try:
        d = descargar_mes(anio, mes, cache=Path(".cache"))
    except (ErrorDescarga, OSError):
        pytest.skip("sin acceso a la fuente")

    nombres = [i.filename for i in d.zip.infolist() if i.filename.startswith("tender_")]
    texto = decodificar(d.zip.read(nombres[0]), "tender")
    assert "Catálogo" in texto or "Cotización" in texto or "Licitación" in texto
