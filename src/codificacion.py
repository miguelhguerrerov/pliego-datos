"""Validación y saneamiento de la codificación de la fuente.

La fuente del SERCOP entrega **UTF-8 válido**. Ver docs/decisiones.md D-011: una nota
temprana del análisis afirmaba que llegaba en latin-1, y era un artefacto de la consola
de Windows. "Reparar" todo habría convertido `Catálogo` en `CatÃ¡logo` en 2,77 M de
registros.

Ahora bien, dentro de ese UTF-8 válido aparecen registros sueltos con texto ya doblemente
codificado en origen: alguien cargó "georreferenciación" desde un sistema que lo mangló.
Medido en planning_2026_agosto.csv: 1 línea de 1070, el 0,09%.

De ahí la distinción que hace este módulo, y que es toda su razón de ser:

- **Sistemática** (por encima del umbral): la fuente cambió. Se detiene la ingesta.
- **Esporádica** (por debajo): suciedad normal de captura. Se repara el campo concreto,
  se cuenta y se anota en cobertura. La ingesta continúa.

Detener 2,77 M de registros porque una entidad tecleó mal un campo sería desproporcionado;
cargar mojibake sin contarlo sería deshonesto. El umbral separa las dos cosas.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# Por encima de esta fracción de líneas afectadas se considera cambio de la fuente.
UMBRAL_SISTEMATICO = 0.01  # 1%


class ErrorCodificacion(Exception):
    """La fuente no entrega UTF-8 válido, o la corrupción dejó de ser esporádica."""


class TextoValidado(NamedTuple):
    texto: str
    reparaciones: int
    fraccion_afectada: float

    @property
    def hubo_reparaciones(self) -> bool:
        return self.reparaciones > 0


# Un caracter doblemente codificado siempre empieza por U+00C2 o U+00C3 seguido de uno
# o mas bytes de continuacion (U+0080 a U+00BF) leidos como caracteres.
#
# El patron se CONSTRUYE con chr(), no se escribe como literal ni como escape dentro de
# una cadena. Motivo: al crear este archivo, los literales fueron normalizados dos veces
# por las herramientas de edicion y el detector paso a marcar como corrupto cualquier
# texto en espanol bien codificado. chr() es inmune a eso.
_PREFIJOS = chr(0xC2) + chr(0xC3)
_CONTINUACION = chr(0x80) + "-" + chr(0xBF)
PATRON_MOJIBAKE = re.compile("[" + _PREFIJOS + "][" + _CONTINUACION + "]+")


def _reparar_coincidencia(m: re.Match) -> str:
    """Deshace la doble codificación de un fragmento, solo si el viaje de ida y vuelta
    es limpio. Si no lo es, se deja el original: más vale un campo feo que uno inventado.
    """
    try:
        return m.group(0).encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return m.group(0)


def reparar_doble_codificacion(texto: str) -> tuple[str, int]:
    """Repara los fragmentos doblemente codificados. Devuelve el texto y cuántos cambió."""
    reparaciones = 0

    def _sub(m: re.Match) -> str:
        nonlocal reparaciones
        nuevo = _reparar_coincidencia(m)
        if nuevo != m.group(0):
            reparaciones += 1
        return nuevo

    return PATRON_MOJIBAKE.sub(_sub, texto), reparaciones


def fraccion_lineas_afectadas(texto: str) -> float:
    lineas = texto.splitlines()
    if not lineas:
        return 0.0
    afectadas = sum(1 for l in lineas if PATRON_MOJIBAKE.search(l))
    return afectadas / len(lineas)


def decodificar(datos: bytes, origen: str) -> TextoValidado:
    """Decodifica en UTF-8 estricto y sanea la corrupción esporádica.

    Lanza ErrorCodificacion si los bytes no son UTF-8 (la fuente cambió de codificación)
    o si la doble codificación supera el umbral (la fuente se rompió en origen).
    """
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError as e:
        muestra = datos[max(0, e.start - 30) : e.start + 30]
        raise ErrorCodificacion(
            f"{origen} no es UTF-8 válido: byte {datos[e.start]:#04x} en posición {e.start}.\n"
            f"Contexto: {muestra!r}\n"
            f"La fuente cambió de codificación. Actualiza docs/datos.md §5.1 y el "
            f"normalizador ANTES de volver a cargar. No relajes esta comprobación."
        ) from e

    fraccion = fraccion_lineas_afectadas(texto)
    if fraccion > UMBRAL_SISTEMATICO:
        raise ErrorCodificacion(
            f"{origen}: el {fraccion:.1%} de las líneas viene doblemente codificado, "
            f"por encima del umbral del {UMBRAL_SISTEMATICO:.0%}.\n"
            f"Eso ya no es suciedad de captura sino un cambio en la fuente. "
            f"Revisa docs/datos.md §5.1 antes de cargar nada."
        )

    texto, reparaciones = reparar_doble_codificacion(texto)
    return TextoValidado(texto, reparaciones, fraccion)


def resumen_no_ascii(texto: str, limite: int = 8) -> dict[str, int]:
    """Cuenta caracteres no ASCII. Si un mes trae cero acentos, algo va mal aunque
    decodifique sin error."""
    conteo: dict[str, int] = {}
    for c in texto:
        if ord(c) > 127:
            conteo[c] = conteo.get(c, 0) + 1
    return dict(sorted(conteo.items(), key=lambda kv: -kv[1])[:limite])
