"""Normalización del ZIP mensual a tablas.

Valida el contrato de datos antes de devolver nada: si el esquema de la fuente cambió,
esto detiene la ingesta en vez de cargar datos silenciosamente distintos.
Ver docs/datos.md §2 y §6.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass, field

from codificacion import decodificar

# Esquema esperado. Si la fuente añade columnas, la ingesta se detiene y hay que
# actualizar docs/datos.md antes de continuar. NUNCA relajar esta comprobación.
COLUMNAS = {
    "releases": ["ocid", "id", "initiationType", "buyer_id", "buyer_name", "language", "date", "tag"],
    "planning": ["ocid", "id", "rationale", "budget_id", "budget_description", "budget_amount", "budget_currency"],
    "tender": [
        "ocid", "release_id", "id", "title", "description", "status",
        "procuringEntity_id", "procuringEntity_name", "value_amount", "value_currency",
        "procurementMethod", "procurementMethodDetails", "mainProcurementCategory", "awardCriteria",
        "tenderPeriod_startDate", "tenderPeriod_endDate", "tenderPeriod_maxExtentDate", "tenderPeriod_durationInDays",
        "enquiryPeriod_startDate", "enquiryPeriod_endDate", "enquiryPeriod_maxExtentDate", "enquiryPeriod_durationInDays",
        "hasEnquiries", "eligibilityCriteria",
        "awardPeriod_startDate", "awardPeriod_endDate", "awardPeriod_maxExtentDate", "awardPeriod_durationInDays",
        "numberOfTenderers",
    ],
    "awards": [
        "ocid", "release_id", "id", "title", "description", "status", "date",
        "amount", "currency", "correctedValue_amount", "correctedValue_currency",
        "enteredValue_amount", "enteredValue_currency",
        "contractPeriod_startDate", "contractPeriod_endDate",
        "contractPeriod_maxExtentDate", "contractPeriod_durationInDays",
    ],
    "suppliers": ["ocid", "release_id", "award_id", "id", "name"],
    "contracts": [
        "ocid", "release_id", "id", "awardID", "title", "description", "status",
        "contractPeriod_startDate", "contractPeriod_endDate",
        "contractPeriod_maxExtentDate", "contractPeriod_durationInDays",
        "amount", "currency", "dateSigned",
    ],
}

ARCHIVOS_ESPERADOS = ("metadata", "extensions", *COLUMNAS)


class ErrorContrato(Exception):
    """La fuente cambió de esquema. Actualiza docs/datos.md antes de volver a cargar."""


@dataclass
class MesNormalizado:
    anio: int
    mes: int
    tablas: dict[str, list[dict]] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    @property
    def n_releases(self) -> int:
        return len(self.tablas.get("releases", []))


def _leer_tabla(zf: zipfile.ZipFile, prefijo: str, anio: int, mes: int) -> list[dict]:
    nombres = [i.filename for i in zf.infolist() if i.filename.startswith(prefijo + "_")]
    if not nombres:
        return []
    origen = f"{anio}-{mes:02d}/{nombres[0]}"
    texto = decodificar(zf.read(nombres[0]), origen)
    lector = csv.DictReader(io.StringIO(texto))

    esperadas = COLUMNAS.get(prefijo)
    if esperadas is not None:
        reales = list(lector.fieldnames or [])
        if reales != esperadas:
            faltan = set(esperadas) - set(reales)
            sobran = set(reales) - set(esperadas)
            raise ErrorContrato(
                f"{origen}: el esquema cambió.\n"
                f"  faltan: {sorted(faltan) or 'ninguna'}\n"
                f"  sobran: {sorted(sobran) or 'ninguna'}\n"
                f"Actualiza docs/datos.md §2 y este módulo ANTES de volver a cargar."
            )
    return list(lector)


def normalizar(zf: zipfile.ZipFile, anio: int, mes: int) -> MesNormalizado:
    """Lee el ZIP, valida el contrato y devuelve las tablas deduplicadas."""
    presentes = {i.filename.split("_")[0] for i in zf.infolist()}
    faltantes = [a for a in ARCHIVOS_ESPERADOS if a not in presentes]
    if faltantes:
        raise ErrorContrato(
            f"{anio}-{mes:02d}: el ZIP no trae {faltantes}. Márcalo como pendiente."
        )

    resultado = MesNormalizado(anio, mes)
    for prefijo in COLUMNAS:
        resultado.tablas[prefijo] = _leer_tabla(zf, prefijo, anio, mes)

    # Deduplicación por ocid en releases: la identidad del proceso es el ocid.
    releases = resultado.tablas["releases"]
    vistos: set[str] = set()
    unicos = []
    for r in releases:
        if r["ocid"] in vistos:
            continue
        vistos.add(r["ocid"])
        unicos.append(r)
    if len(unicos) != len(releases):
        resultado.avisos.append(f"{len(releases) - len(unicos)} releases duplicados por ocid")
    resultado.tablas["releases"] = unicos

    return resultado


# --- utilidades de campo -------------------------------------------------------

def numero(valor: str | None) -> float | None:
    """Los montos llegan como texto. Nulo se marca como None, no como cero:
    un cero real y un dato ausente son cosas distintas."""
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def estado_de_tag(tag: str | None) -> str:
    """El campo `tag` es la máquina de estados del proceso, y los intermedios son el
    producto de radar. Ver docs/datos.md §5.3.

    >>> estado_de_tag('["planning"]')
    'planificacion'
    >>> estado_de_tag('["tender","award","contract"]')
    'cerrado'
    """
    if not tag:
        return "desconocido"
    try:
        etapas = set(json.loads(tag))
    except (json.JSONDecodeError, TypeError):
        etapas = {t.strip(' "[]') for t in str(tag).split(",")}

    if "contract" in etapas:
        return "cerrado"
    if "award" in etapas:
        return "adjudicado"
    if "tender" in etapas:
        return "abierto"
    if "planning" in etapas:
        return "planificacion"
    return "desconocido"


def metodo_base(detalle: str | None) -> str | None:
    """`procurementMethodDetails` incluye a veces el convenio marco completo.
    Se corta para poder agrupar.

    >>> metodo_base("Catálogo electrónico - Mejor oferta en el convenio SERCOP-123")
    'Catálogo electrónico - Mejor oferta'
    """
    if not detalle:
        return None
    return detalle.split(" en el convenio")[0].strip()
