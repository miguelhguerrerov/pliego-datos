"""Carga a Postgres.

Solo entran agregados regenerables y datos de usuario (invariante 2). El detalle OCDS
va a Parquet sobre releases de GitHub, nunca aquí.

Nota de entorno: en Windows ARM64 no hay ruedas de psycopg. Este módulo está escrito
para su destino real, que es GitHub Actions sobre Linux x86-64.
"""

from __future__ import annotations

import io
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import psycopg

# psycopg se importa dentro de conexion(), no aqui: asi la validacion de la cadena
# de conexion se puede probar en cualquier maquina, incluidas las que no tienen
# ruedas del controlador (Windows ARM64).

PRESUPUESTO_MB = 460
ALARMA_MB = 420


class PresupuestoExcedido(Exception):
    """La base superó el presupuesto. Aplica la primera válvula de docs/agregados.md:
    acortar la ventana de proceso_resumen de 24 a 18 meses."""


def url_conexion() -> str:
    """Devuelve la cadena de conexión, exigiendo el agrupador.

    El host directo `db.<ref>.supabase.co` **solo resuelve a IPv6**, y los runners de
    GitHub Actions no tienen conectividad IPv6: falla con "Network is unreachable".
    Hay que usar el agrupador `aws-0-<region>.pooler.supabase.com` en **modo sesión
    (puerto 5432)**, no en modo transacción (6543): COPY y las sentencias preparadas
    no funcionan en modo transacción, y la carga masiva depende de COPY.
    """
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "Falta SUPABASE_DB_URL. Es un secreto del repositorio; nunca va en el código "
            "(invariante 8). Ver docs/repositorio.md §4."
        )
    if ".supabase.co" in url and "pooler" not in url:
        raise RuntimeError(
            "SUPABASE_DB_URL apunta al host directo, que solo resuelve a IPv6 y es "
            "inalcanzable desde GitHub Actions.\n"
            "Usa el agrupador en modo sesion:\n"
            "  postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres"
        )
    if url.endswith(":6543/postgres"):
        raise RuntimeError(
            "SUPABASE_DB_URL usa el puerto 6543 (modo transacción). COPY y las sentencias "
            "preparadas lo requieren en modo sesión: cambia el puerto a 5432."
        )
    return url


@contextmanager
def conexion():
    import psycopg

    with psycopg.connect(url_conexion(), autocommit=False) as con:
        yield con


def copiar(con: "psycopg.Connection", tabla: str, columnas: list[str], filas: list[tuple]) -> int:
    """Carga masiva por COPY. Mucho más rápido que INSERT fila a fila, que es lo que
    hacía el notebook original y lo que lo volvía inviable a escala."""
    if not filas:
        return 0
    cols = ", ".join(columnas)
    with con.cursor() as cur:
        with cur.copy(f"copy {tabla} ({cols}) from stdin") as copy:
            for fila in filas:
                copy.write_row(fila)
    return len(filas)


def reemplazar(con: "psycopg.Connection", tabla: str, columnas: list[str], filas: list[tuple]) -> int:
    """Vacía y recarga una tabla agregada.

    Los agregados se recalculan enteros cada noche: es más simple y más robusto que
    la actualización incremental, y cuesta minutos. Ver docs/agregados.md §3.
    """
    with con.cursor() as cur:
        cur.execute(f"truncate {tabla}")
    return copiar(con, tabla, columnas, filas)


def upsert_cobertura(
    con: "psycopg.Connection",
    anio: int,
    mes: int,
    estado: str,
    registros: int | None = None,
    pct_cerrado: float | None = None,
    bytes_zip: int | None = None,
    intentos: int | None = None,
    nota: str | None = None,
) -> None:
    """El registro de cobertura es lo que impide presentar datos incompletos como
    completos. Se escribe SIEMPRE, también cuando el mes falla."""
    with con.cursor() as cur:
        cur.execute(
            """
            insert into cobertura (anio, mes, estado, registros, pct_cerrado,
                                   bytes_zip, intentos, fecha_carga, nota)
            values (%s,%s,%s,%s,%s,%s,%s, now(), %s)
            on conflict (anio, mes) do update set
                estado = excluded.estado,
                registros = excluded.registros,
                pct_cerrado = excluded.pct_cerrado,
                bytes_zip = excluded.bytes_zip,
                intentos = excluded.intentos,
                fecha_carga = now(),
                nota = excluded.nota
            """,
            (anio, mes, estado, registros, pct_cerrado, bytes_zip, intentos, nota),
        )


def tamano_mb(con: "psycopg.Connection") -> float:
    with con.cursor() as cur:
        cur.execute("select coalesce(round(sum(mb),2), 0) from v_tamano_base")
        return float(cur.fetchone()[0])


def verificar_presupuesto(con: "psycopg.Connection") -> float:
    """Invariante 2. Falla la ingesta antes de que la base se llene sin aviso."""
    mb = tamano_mb(con)
    if mb > PRESUPUESTO_MB:
        raise PresupuestoExcedido(
            f"La base ocupa {mb} MB y el presupuesto duro es {PRESUPUESTO_MB} MB.\n"
            f"Aplica la primera válvula: acorta la ventana de proceso_resumen de 24 a "
            f"18 meses (libera ~45 MB). Ver docs/agregados.md §1."
        )
    if mb > ALARMA_MB:
        print(f"  AVISO: la base ocupa {mb} MB, por encima de la alarma de {ALARMA_MB} MB.")
    return mb
