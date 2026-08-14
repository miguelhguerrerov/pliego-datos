"""La ruta JSON trae lo que el CSV no: ítems con precio unitario y todos los oferentes.

Sin esto no hay benchmark de precios, que es la función que se cobra.
Ver docs/datos.md §3 y docs/decisiones.md D-001.
"""

import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detalle import DetalleMes, _extraer  # noqa: E402

# El acento se construye para que ninguna herramienta de edición lo normalice.
METODO_PRUEBA = "Menor Cuant" + chr(0xED) + "a"


@pytest.fixture(scope="module")
def detalle_real():
    url = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/download?" + urllib.parse.urlencode(
        {"type": "json", "year": 2024, "month": 2, "method": METODO_PRUEBA}
    )
    try:
        crudo = urllib.request.urlopen(url, timeout=180).read()
        z = zipfile.ZipFile(io.BytesIO(crudo))
        paquetes = json.loads(z.read(z.infolist()[0].filename).decode("utf-8"))
    except Exception:  # noqa: BLE001
        pytest.skip("sin acceso a la fuente")

    d = DetalleMes(2024, 2)
    for paquete in (paquetes if isinstance(paquetes, list) else [paquetes]):
        for r in paquete.get("releases", []):
            _extraer(r, d)
    return d


def test_items_traen_cpc_y_precio_unitario(detalle_real):
    """Es la base del benchmark. Si esto se rompe, el producto de pago no existe."""
    assert detalle_real.items
    completos = [i for i in detalle_real.items if i["cpc"] and i["precio_unitario"]]
    assert len(completos) == len(detalle_real.items)


def test_trae_todos_los_oferentes_no_solo_ganadores(detalle_real):
    """El CSV solo da el adjudicatario. La competencia real está aquí: en la muestra
    de febrero de 2024 son 3 580 oferentes frente a 208 ganadores."""
    ganadores = [o for o in detalle_real.oferentes if o["gano"]]
    assert len(detalle_real.oferentes) > len(ganadores) * 5


def test_procesos_traen_referencial_y_competencia(detalle_real):
    assert all(p["referencial"] for p in detalle_real.procesos)
    assert all(p["n_oferentes"] is not None for p in detalle_real.procesos)


def test_partes_traen_territorio(detalle_real):
    """El CSV no trae provincia ni cantón: solo se obtienen de parties[].address."""
    con_provincia = [p for p in detalle_real.partes if p["provincia"]]
    assert len(con_provincia) / len(detalle_real.partes) > 0.95
