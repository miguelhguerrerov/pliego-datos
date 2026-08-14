"""La fuente entrega UTF-8 válido; dentro de él hay registros sueltos ya corruptos.

Las cadenas de mojibake se CONSTRUYEN con encode/decode, nunca se escriben como
literales: al escribirlas, las herramientas de edición las normalizan y la prueba deja
de probar lo que dice probar. Pasó de verdad al crear estos archivos, tres veces.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codificacion import (  # noqa: E402
    UMBRAL_SISTEMATICO,
    ErrorCodificacion,
    decodificar,
    fraccion_lineas_afectadas,
    reparar_doble_codificacion,
    resumen_no_ascii,
)

LIMPIO = "Catálogo electrónico Cuantía Selección COMPAÑIA"
MOJIBAKE = LIMPIO.encode("utf-8").decode("latin-1")


def test_utf8_valido_se_decodifica_intacto():
    v = decodificar(LIMPIO.encode("utf-8"), "prueba")
    assert v.texto == LIMPIO
    assert v.reparaciones == 0
    assert v.fraccion_afectada == 0.0


def test_texto_correcto_no_se_toca():
    """El fallo más caro posible es 'reparar' texto que estaba bien: convertiría
    Catálogo en CatÃ¡logo en 2,77 M de registros. Ver docs/decisiones.md D-011."""
    reparado, n = reparar_doble_codificacion(LIMPIO)
    assert reparado == LIMPIO
    assert n == 0


def test_latin1_detiene_la_ingesta():
    with pytest.raises(ErrorCodificacion, match="no es UTF-8"):
        decodificar(b"Cat\xf3logo", "prueba")


def test_corrupcion_sistematica_detiene_la_ingesta():
    with pytest.raises(ErrorCodificacion, match="doblemente codificado"):
        decodificar(MOJIBAKE.encode("utf-8"), "prueba")


def test_corrupcion_esporadica_se_repara_y_continua():
    """Una línea corrupta de 1070 es suciedad de captura, no cambio de la fuente.
    Detener 2,77 M de registros por eso sería desproporcionado. Ver D-013."""
    lineas = [LIMPIO] * 200 + [MOJIBAKE]
    texto = "\n".join(lineas)
    assert fraccion_lineas_afectadas(texto) < UMBRAL_SISTEMATICO

    v = decodificar(texto.encode("utf-8"), "prueba")
    assert v.reparaciones == 5           # cinco fragmentos en la línea corrupta
    assert MOJIBAKE not in v.texto
    assert v.texto.count(LIMPIO) == 201  # la corrupta quedó igual que las buenas


def test_reparacion_solo_si_el_viaje_de_ida_y_vuelta_es_limpio():
    """Si deshacer la doble codificación no produce UTF-8 válido, se deja el original:
    más vale un campo feo que uno inventado."""
    basura = chr(0xC3) + chr(0xC3) + chr(0xC3)
    reparado, _ = reparar_doble_codificacion(basura)
    assert reparado == basura


def test_resumen_no_ascii():
    r = resumen_no_ascii("Catálogo electrónico cotización Cuantía")
    assert r["ó"] == 2
    assert r["á"] == 1
    assert r["í"] == 1


def test_fuente_real_es_utf8():
    """Contra la fuente en vivo. Se salta si no hay red."""
    from descarga import ErrorDescarga, descargar_mes

    try:
        d = descargar_mes(2024, 2, cache=Path(".cache"))
    except (ErrorDescarga, OSError):
        pytest.skip("sin acceso a la fuente")

    nombre = [i.filename for i in d.zip.infolist() if i.filename.startswith("tender_")][0]
    v = decodificar(d.zip.read(nombre), "tender")
    assert "Licitación" in v.texto or "Cotización" in v.texto
    assert v.fraccion_afectada < UMBRAL_SISTEMATICO
