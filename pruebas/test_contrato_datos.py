"""Prueba de contrato: falla si la fuente cambió de esquema.

Es la única defensa contra corromper la base en silencio. Si falla, se actualiza
docs/datos.md y el normalizador ANTES de volver a cargar. Jamás relajarla para que pase.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from entidades import (  # noqa: E402
    enmascarar_ruc,
    es_entidad_publica,
    es_persona_natural,
    extraer_ruc,
    nombre_canonico,
    provincia_de_ruc,
)
from normaliza import estado_de_tag, metodo_base, numero  # noqa: E402

CACHE = Path(".cache")


# --- identidad ------------------------------------------------------------------

def test_extraer_ruc():
    assert extraer_ruc("EC-RUC-1791240502001-14583") == "1791240502001"
    assert extraer_ruc("EC-RUC-1660003510001-2711") == "1660003510001"
    assert extraer_ruc("EC-RUC-1660003510001") == "1660003510001"
    assert extraer_ruc("1791240502001") == "1791240502001"
    assert extraer_ruc("") is None
    assert extraer_ruc(None) is None


def test_el_sufijo_no_forma_parte_de_la_identidad():
    """La misma empresa aparece con sufijos distintos entre releases. Usarlo como
    clave duplica entidades: fue lo que dio 18 908 proveedores en vez de 20 972."""
    assert extraer_ruc("EC-RUC-1791240502001-14583") == extraer_ruc("EC-RUC-1791240502001-99")


def test_tipo_de_contribuyente():
    assert es_persona_natural("1104567890001") is True     # tercer dígito 0
    assert es_persona_natural("1791240502001") is False    # tercer dígito 9
    assert es_entidad_publica("1660003510001") is True     # tercer dígito 6
    assert es_persona_natural(None) is False


def test_provincia_de_ruc():
    assert provincia_de_ruc("1791240502001") == "PICHINCHA"
    assert provincia_de_ruc("0925051385001") == "GUAYAS"
    assert provincia_de_ruc("1660003510001") == "PASTAZA"


def test_enmascarar_solo_persona_natural():
    assert enmascarar_ruc("1791240502001", False) == "1791240502001"
    assert enmascarar_ruc("1104567890001", True).endswith("0001")
    assert "1104567890" not in enmascarar_ruc("1104567890001", True)


def test_nombre_canonico_por_moda():
    nombres = ["CEDIMED CIA. LTDA.", "CEDIMED CIA LTDA", "CEDIMED CIA. LTDA."]
    assert nombre_canonico(nombres) == "CEDIMED CIA. LTDA."
    assert nombre_canonico([]) is None


# --- campos ---------------------------------------------------------------------

def test_estado_de_tag():
    assert estado_de_tag('["planning"]') == "planificacion"
    assert estado_de_tag('["planning","tender"]') == "abierto"
    assert estado_de_tag('["planning","tender","award"]') == "adjudicado"
    assert estado_de_tag('["tender","award","contract"]') == "cerrado"
    assert estado_de_tag(None) == "desconocido"


def test_numero_distingue_cero_de_ausente():
    assert numero("77562.000000") == 77562.0
    assert numero("0") == 0.0
    assert numero("") is None
    assert numero(None) is None


def test_metodo_base_recorta_el_convenio():
    assert metodo_base("Catálogo electrónico - Mejor oferta en el convenio SERCOP-123") == \
        "Catálogo electrónico - Mejor oferta"
    assert metodo_base("Menor Cuantía") == "Menor Cuantía"


# --- contra la fuente real ------------------------------------------------------

@pytest.fixture(scope="module")
def mes_real():
    from descarga import ErrorDescarga, descargar_mes
    from normaliza import normalizar

    try:
        d = descargar_mes(2024, 2, cache=CACHE)
    except (ErrorDescarga, OSError):
        pytest.skip("sin acceso a la fuente")
    return normalizar(d.zip, 2024, 2)


def test_esquema_de_la_fuente_no_cambio(mes_real):
    """Si esto falla, la fuente cambió. Actualiza docs/datos.md §2."""
    assert mes_real.n_releases > 15_000
    for tabla in ("releases", "tender", "awards", "suppliers", "contracts"):
        assert mes_real.tablas[tabla], f"{tabla} vino vacía"


def test_subasta_inversa_no_trae_referencial_en_csv(mes_real):
    """El hallazgo que justifica usar la ruta JSON para el benchmark.
    Ver docs/datos.md §4. Si esto empieza a fallar, la fuente MEJORÓ y hay que
    revisar si el troceo por JSON sigue siendo necesario."""
    sie = [
        t for t in mes_real.tablas["tender"]
        if metodo_base(t.get("procurementMethodDetails")) == "Subasta Inversa Electrónica"
    ]
    assert sie, "no hay procesos de subasta inversa en el mes de prueba"
    con_referencial = [t for t in sie if numero(t.get("value_amount"))]
    assert not con_referencial, (
        f"{len(con_referencial)} de {len(sie)} procesos de subasta inversa traen "
        f"referencial en CSV. La fuente cambió: revisa docs/datos.md §4."
    )


def test_estados_intermedios_estan_presentes(mes_real):
    """Los estados intermedios son el producto de radar, no ruido."""
    estados = {estado_de_tag(r.get("tag")) for r in mes_real.tablas["releases"]}
    assert "cerrado" in estados
