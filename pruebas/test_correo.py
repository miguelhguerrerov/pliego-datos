"""Las plantillas de correo, comprobadas donde fallan de verdad.

Un correo no da errores: se ve mal, o no se ve. Estas pruebas fijan las restricciones
del medio, que son las que se olvidan al copiar HTML de la web.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from correo import (  # noqa: E402
    MUESTRA,
    asunto_alerta,
    plantilla_alerta,
    plantilla_cambio_correo,
    plantilla_enlace_magico,
)

TODAS = [plantilla_enlace_magico(), plantilla_cambio_correo(),
         plantilla_alerta("Miguel", MUESTRA, "cliente@empresa.com")]


def test_ninguna_plantilla_usa_lo_que_el_correo_no_entiende():
    """Outlook maqueta con el motor de Word y Gmail recorta los `<style>`. Copiar el
    CSS de la interfaz es la forma más rápida de mandar un correo roto sin enterarse."""
    for html in TODAS:
        assert "<style" not in html, "un <style> lo recorta Gmail"
        assert "display:flex" not in html, "Outlook no entiende flex"
        assert "display:grid" not in html, "Outlook no entiende grid"
        assert 'src="http' not in html, "imagen externa: muchos clientes la bloquean"


def test_el_isotipo_no_depende_de_imagenes():
    """La marca son dos barras (docs/marca.md §2). Con celdas de color se ve siempre;
    como imagen, no se vería en la mitad de los clientes por omisión."""
    html = plantilla_enlace_magico()
    assert "#3C6280" in html and "#0E7259" in html, "faltan los colores de las barras"
    assert "<img" not in html, "la marca no debe depender de una imagen"


def test_el_marcador_de_supabase_sobrevive():
    """Si el marcador se rompe, el correo sale con un enlace literal `{{ .Confirmation…`
    y nadie puede entrar. No da error en ningún sitio: llega y no funciona."""
    html = plantilla_enlace_magico()
    assert html.count("{{ .ConfirmationURL }}") == 2, (
        "el marcador debe aparecer en el botón y en el texto copiable"
    )


def test_hay_linea_de_preencabezado():
    """Es lo que la bandeja muestra junto al asunto. Sin ella el cliente coge la primera
    frase del HTML, que es «Pliego» — y se desperdicia la única línea que decide si se
    abre el correo."""
    for html in TODAS:
        assert "max-height:0" in html, "falta el preencabezado oculto"


def test_el_asunto_lleva_cifra_y_no_adjetivos():
    """«Nuevas oportunidades para tu empresa» lo manda todo el mundo y no dice nada."""
    a = asunto_alerta(MUESTRA)
    assert re.match(r"^\d+ oportunidad", a), f"el asunto debe empezar por la cifra: {a}"
    assert "$" in a, "el monto va en el asunto: es lo que decide si se abre"
    for vago in ("nuevas oportunidades para tu empresa", "no te lo pierdas", "importante"):
        assert vago not in a.lower()


def test_la_alerta_dice_por_que_llega_y_como_darse_de_baja():
    """Un correo que no explica su propio criterio se percibe como ruido aunque acierte,
    y acaba marcado a mano como no deseado — la forma más cara de perder el canal."""
    html = plantilla_alerta("Miguel", MUESTRA, "cliente@empresa.com")
    assert "configuraste alertas" in html
    assert "/perfil" in html, "tiene que haber salida visible"
    assert "un correo al d" in html, "debe recordar el invariante 13 al destinatario"


def test_un_monto_no_declarado_no_se_muestra_como_cero():
    """La mitad de los procesos en planificación no traen cifra (D-031). Un cero es una
    afirmación falsa; «no declarado» es el dato."""
    html = plantilla_alerta("Miguel", MUESTRA, "c@e.com")
    assert "no declarado" in html
    assert "$0" not in html


def test_lo_que_cierra_pronto_se_distingue():
    """Una oportunidad que se conoce tarde vale lo mismo que no conocerla."""
    html = plantilla_alerta("Miguel", MUESTRA, "c@e.com")
    assert "#A25617" in html, "lo urgente va en ámbar, que es el color de atención"
    assert "cierra" in html.lower()
