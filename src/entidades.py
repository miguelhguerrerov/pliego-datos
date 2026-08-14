"""Identidad de entidades: extracción de RUC y clasificación de tipo de contribuyente.

Regla central del proyecto: se unifica por RUC, NUNCA por nombre. La misma empresa
aparece con varias grafías a lo largo de once años. Ver docs/datos.md §5.2.
"""

from __future__ import annotations

import re
from collections import Counter

# Los identificadores OCDS del SERCOP tienen la forma EC-RUC-<ruc>-<secuencia>.
# El sufijo de secuencia varía entre releases para la misma empresa: usarlo como
# clave duplica entidades.
PATRON_ID = re.compile(r"^EC-RUC-(\d{10,13})(?:-\d+)?$", re.IGNORECASE)

PROVINCIAS = {
    "01": "AZUAY", "02": "BOLIVAR", "03": "CAÑAR", "04": "CARCHI",
    "05": "COTOPAXI", "06": "CHIMBORAZO", "07": "EL ORO", "08": "ESMERALDAS",
    "09": "GUAYAS", "10": "IMBABURA", "11": "LOJA", "12": "LOS RIOS",
    "13": "MANABI", "14": "MORONA SANTIAGO", "15": "NAPO", "16": "PASTAZA",
    "17": "PICHINCHA", "18": "TUNGURAHUA", "19": "ZAMORA CHINCHIPE",
    "20": "GALAPAGOS", "21": "SUCUMBIOS", "22": "ORELLANA",
    "23": "SANTO DOMINGO DE LOS TSACHILAS", "24": "SANTA ELENA",
    "30": "EXTERIOR", "88": "EXTERIOR",
}


def extraer_ruc(identificador: str | None) -> str | None:
    """Extrae el RUC de un identificador OCDS.

    >>> extraer_ruc("EC-RUC-1791240502001-14583")
    '1791240502001'
    >>> extraer_ruc("EC-RUC-1660003510001")
    '1660003510001'
    >>> extraer_ruc(None) is None
    True
    """
    if not identificador:
        return None
    coincidencia = PATRON_ID.match(identificador.strip())
    if coincidencia:
        return coincidencia.group(1)
    # Algunos registros traen el RUC pelado.
    limpio = identificador.strip()
    return limpio if limpio.isdigit() and 10 <= len(limpio) <= 13 else None


def es_persona_natural(ruc: str | None) -> bool:
    """El tercer dígito del RUC indica el tipo de contribuyente:
    - menor que 6  -> persona natural
    - igual a 6    -> entidad pública
    - igual a 9    -> sociedad privada

    Importa porque el RUC de persona natural contiene la cédula, y la dirección
    registrada suele ser domiciliaria: ambos van enmascarados. Ver docs/legal.md §1.
    """
    if not ruc or len(ruc) < 3 or not ruc.isdigit():
        return False
    return int(ruc[2]) < 6


def es_entidad_publica(ruc: str | None) -> bool:
    if not ruc or len(ruc) < 3 or not ruc.isdigit():
        return False
    return ruc[2] == "6"


def provincia_de_ruc(ruc: str | None) -> str | None:
    """Los dos primeros dígitos codifican la provincia de inscripción.

    Es la provincia FISCAL, no necesariamente donde opera. Se usa solo como respaldo
    cuando no hay `parties[].address`.
    """
    if not ruc or len(ruc) < 2:
        return None
    return PROVINCIAS.get(ruc[:2])


def nombre_canonico(nombres: list[str]) -> str | None:
    """Resuelve la grafía de una entidad por moda, no por el último visto.

    Los registros antiguos tienen más erratas, así que "el último" no es mejor
    criterio que "el más frecuente".
    """
    limpios = [n.strip() for n in nombres if n and n.strip()]
    if not limpios:
        return None
    return Counter(limpios).most_common(1)[0][0]


def enmascarar_ruc(ruc: str, natural: bool) -> str:
    """Enmascara el RUC de persona natural dejando solo el sufijo de establecimiento.

    >>> enmascarar_ruc("1791240502001", False)
    '1791240502001'
    >>> enmascarar_ruc("1104567890001", True)
    '·········0001'
    """
    if not natural:
        return ruc
    return "·" * (len(ruc) - 4) + ruc[-4:]
