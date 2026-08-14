"""Descarga masiva desde el portal de datos abiertos del SERCOP.

Ruta principal del proyecto. NO usar la API paginada para backfill: son 60 peticiones
por minuto y 10 registros por página, 77 horas para el histórico. Ver docs/datos.md §1.
"""

from __future__ import annotations

import io
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

BASE = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/download"
API = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api"

# Medido: de 24 meses, 10 necesitaron reintentos. Tiempos entre 17 y 200 s.
INTENTOS = 4
ESPERA_BASE = 3
TIMEOUT = 180

METODOS = (
    "Subasta Inversa Electrónica",
    "Licitación",
    "Licitación de Seguros",
    "Cotización",
    "Menor Cuantía",
    "Catálogo electrónico - Compra directa",
    "Catálogo electrónico - Mejor oferta",
    "Catálogo electrónico - Gran compra mejor oferta",
    "Catálogo electrónico - Gran compra puja",
    "Contratos entre Entidades Públicas o sus subsidiarias",
    "Bienes y Servicios únicos",
    "Contrataciones con empresas públicas internacionales",
)


class ErrorDescarga(Exception):
    """No se pudo descargar el mes tras agotar los reintentos."""


@dataclass
class Descarga:
    anio: int
    mes: int
    zip: zipfile.ZipFile
    bytes_crudos: int
    intentos: int
    troceado: bool = False


def _url(anio: int, mes: int, tipo: str, metodo: str) -> str:
    params = urllib.parse.urlencode(
        {"type": tipo, "year": anio, "month": mes, "method": metodo}
    )
    return f"{BASE}?{params}"


def _pedir(url: str) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": "pliego-datos/1.0"})
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta:
        return respuesta.read()


def descargar_mes(
    anio: int,
    mes: int,
    tipo: str = "csv",
    cache: Path | None = None,
    forzar: bool = False,
) -> Descarga:
    """Descarga un mes completo. Reintenta con espera creciente y, si el mes entero
    no pasa, trocea por método.

    `cache` guarda el ZIP crudo en disco: acelera el desarrollo y es lo que permite
    reconstruir sin volver a golpear la fuente.
    """
    destino = cache / f"{anio}_{mes:02d}_{tipo}.zip" if cache else None
    if destino and destino.exists() and destino.stat().st_size > 1000 and not forzar:
        return Descarga(anio, mes, zipfile.ZipFile(destino), destino.stat().st_size, 0)

    ultimo_error: Exception | None = None
    for intento in range(1, INTENTOS + 1):
        try:
            crudo = _pedir(_url(anio, mes, tipo, "all"))
            zf = zipfile.ZipFile(io.BytesIO(crudo))  # falla si viene truncado
            if destino:
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(crudo)
            return Descarga(anio, mes, zf, len(crudo), intento)
        except (urllib.error.URLError, TimeoutError, zipfile.BadZipFile, OSError) as e:
            # IncompleteRead llega como OSError o http.client.IncompleteRead.
            # El ZIP parcial se descarta sin intentar abrirlo: un ZIP truncado puede
            # abrirse a medias y cargar datos incompletos sin error visible.
            ultimo_error = e
            print(f"  reintento {anio}-{mes:02d} ({intento}/{INTENTOS}): {type(e).__name__}: {e}")
            time.sleep(ESPERA_BASE * intento)

    raise ErrorDescarga(
        f"{anio}-{mes:02d} agotó {INTENTOS} intentos. Último error: {ultimo_error}. "
        f"Márcalo como pendiente en cobertura y continúa con el resto: el trabajo "
        f"semanal lo reintentará."
    )


def total_declarado(anio: int) -> int:
    """Total de procedimientos que declara la API para un año.

    Se usa solo para el cuadre trimestral, no para ingerir. Sobre 2024 dio 219 186
    frente a 219 185 cargados: un registro de diferencia es el margen aceptable.
    """
    import json

    url = f"{API}/search_ocds?year={anio}&page=1"
    peticion = urllib.request.Request(url, headers={"User-Agent": "pliego-datos/1.0"})
    with urllib.request.urlopen(peticion, timeout=60) as r:
        return int(json.loads(r.read().decode("utf-8"))["total"])
