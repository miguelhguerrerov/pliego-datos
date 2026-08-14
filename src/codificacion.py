"""Validación de codificación de la fuente.

La fuente del SERCOP entrega UTF-8 válido. Este módulo NO repara: valida, y detiene
la ingesta si la fuente cambia.

Ver docs/datos.md §5.1 y docs/decisiones.md D-011. Una nota temprana del análisis afirmaba
que la fuente llegaba en latin-1 mal etiquetado; era un artefacto de la consola de Windows.
"Reparar" habría convertido `Catálogo` en `CatÃ¡logo` en los 2,77 M de registros.
"""

from __future__ import annotations


class ErrorCodificacion(Exception):
    """La fuente no entrega UTF-8 válido, o entrega texto doblemente codificado."""


# Secuencias que solo aparecen cuando un texto UTF-8 se decodifica como latin-1 y se
# vuelve a codificar como UTF-8: los dos bytes de la letra acentuada pasan a ser dos
# caracteres, y el primero es siempre U+00C3 o U+00C2.
#
# Se escriben con escapes explicitos A PROPOSITO. Como literales quedan expuestas a que
# el editor o la herramienta que toque el archivo las "arregle" y las convierta en las
# letras correctas: entonces el detector marcaria como corrupto cualquier texto en
# espanol bien codificado. Ocurrio al crear este archivo por primera vez.
SECUENCIAS_DOBLE_CODIFICACION = (
    "Ã¡",  # a con tilde
    "Ã©",  # e con tilde
    "Ã­",  # i con tilde
    "Ã³",  # o con tilde
    "Ãº",  # u con tilde
    "Ã±",  # enie
    "Ã",  # A con tilde
    "Ã",  # E con tilde
    "Ã",  # I con tilde
    "Ã",  # O con tilde
    "Ã",  # U con tilde
    "Ã",  # ENIE
    "Â¿",  # apertura de interrogacion
    "Â¡",  # apertura de exclamacion
    "Â°",  # grado
)


def decodificar(datos: bytes, origen: str) -> str:
    """Decodifica bytes de la fuente en UTF-8 estricto.

    Lanza ErrorCodificacion si no es UTF-8 válido. No intenta ninguna reparación:
    un fallo aquí significa que la fuente cambió y hay que actualizar el contrato
    de datos antes de volver a cargar.
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

    verificar_sin_doble_codificacion(texto, origen)
    return texto


def verificar_sin_doble_codificacion(texto: str, origen: str) -> None:
    """Detecta texto que ya venía corrupto en la fuente (mojibake)."""
    encontradas = [s for s in SECUENCIAS_DOBLE_CODIFICACION if s in texto]
    if encontradas:
        raise ErrorCodificacion(
            f"{origen} contiene secuencias de doble codificación: {encontradas[:5]}.\n"
            f"La fuente está entregando texto corrupto. No lo cargues: quedaría "
            f"corrupto en la base y sería indistinguible de un dato legítimo."
        )


def resumen_no_ascii(texto: str, limite: int = 8) -> dict[str, int]:
    """Cuenta caracteres no ASCII. Útil para el registro de cobertura: si un mes
    trae cero acentos, algo va mal aunque decodifique."""
    conteo: dict[str, int] = {}
    for c in texto:
        if ord(c) > 127:
            conteo[c] = conteo.get(c, 0) + 1
    return dict(sorted(conteo.items(), key=lambda kv: -kv[1])[:limite])
