"""Orquestador de la ingesta.

    python src/ingesta.py --mes 2026-08
    python src/ingesta.py --desde 2015-01 --hasta 2026-08
    python src/ingesta.py --incremental
    python src/ingesta.py --mes 2026-08 --seco     (sin escribir en Postgres)

Regla de operación: un mes que falla se marca como pendiente y la ingesta CONTINÚA.
Nunca se detiene todo por un mes. Ver docs/operacion.md §2.
La única excepción es un cambio de esquema en la fuente, que sí detiene todo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# carga.py se importa de forma diferida: el modo --seco no necesita psycopg, lo que
# permite validar el parseo sin base de datos ni dependencias binarias.
from codificacion import ErrorCodificacion  # noqa: E402
from descarga import ErrorDescarga, descargar_mes  # noqa: E402
from entidades import extraer_ruc  # noqa: E402
from normaliza import ErrorContrato, MesNormalizado, estado_de_tag, metodo_base, normalizar, numero  # noqa: E402

CACHE = Path(".cache")
VENTANA_RESUMEN_MESES = 24  # primera válvula: bajar a 18 si la base supera 420 MB


def meses_entre(desde: str, hasta: str) -> list[tuple[int, int]]:
    a1, m1 = (int(x) for x in desde.split("-"))
    a2, m2 = (int(x) for x in hasta.split("-"))
    salida = []
    a, m = a1, m1
    while (a, m) <= (a2, m2):
        salida.append((a, m))
        m += 1
        if m > 12:
            a, m = a + 1, 1
    return salida


def a_proceso_resumen(mes: MesNormalizado) -> list[tuple]:
    """Aplana el mes a filas de proceso_resumen.

    Los estados intermedios (planificacion, abierto) se conservan: son el producto
    de radar, no ruido. Ver docs/decisiones.md D-008.
    """
    tender = {t["ocid"]: t for t in mes.tablas["tender"]}
    awards: dict[str, float] = {}
    for a in mes.tablas["awards"]:
        v = numero(a.get("amount"))
        if v is not None:
            awards[a["ocid"]] = awards.get(a["ocid"], 0.0) + v
    proveedor: dict[str, str] = {}
    for s in mes.tablas["suppliers"]:
        ruc = extraer_ruc(s.get("id"))
        if ruc:
            proveedor.setdefault(s["ocid"], ruc)

    filas = []
    for r in mes.tablas["releases"]:
        ocid = r["ocid"]
        t = tender.get(ocid, {})
        fecha_txt = (r.get("date") or "")[:10]
        try:
            fecha = dt.date.fromisoformat(fecha_txt)
        except ValueError:
            continue
        cierra_txt = (t.get("tenderPeriod_endDate") or "")[:10]
        try:
            cierra = dt.date.fromisoformat(cierra_txt) if cierra_txt else None
        except ValueError:
            cierra = None

        filas.append((
            ocid,
            fecha,
            fecha.year,
            fecha.month,
            estado_de_tag(r.get("tag")),
            metodo_base(t.get("procurementMethodDetails")),
            None,                                   # cpc: solo desde la ruta JSON
            None,                                   # categoria_id: la pone clasifica.py
            extraer_ruc(r.get("buyer_id")),
            proveedor.get(ocid),
            numero(t.get("value_amount")),
            awards.get(ocid),
            None,                                   # provincia: solo desde la ruta JSON
            (t.get("title") or t.get("description") or "")[:200] or None,
            cierra,
        ))
    return filas


COLUMNAS_RESUMEN = [
    "ocid", "fecha", "anio", "mes", "estado", "metodo", "cpc", "categoria_id",
    "comprador_ruc", "proveedor_ruc", "referencial", "adjudicado", "provincia",
    "objeto", "cierra",
]


def pct_cerrado(mes: MesNormalizado) -> float:
    total = mes.n_releases or 1
    cerrados = sum(
        1 for r in mes.tablas["releases"] if estado_de_tag(r.get("tag")) in ("cerrado", "adjudicado")
    )
    return round(100.0 * cerrados / total, 2)


def procesar_mes(anio: int, mes: int, con, seco: bool, forzar: bool) -> str:
    etiqueta = f"{anio}-{mes:02d}"
    try:
        d = descargar_mes(anio, mes, cache=CACHE, forzar=forzar)
    except ErrorDescarga as e:
        print(f"{etiqueta} PENDIENTE: {e}")
        if con:
            from carga import upsert_cobertura
            upsert_cobertura(con, anio, mes, "pendiente", nota=str(e)[:400])
            con.commit()
        return "pendiente"

    normalizado = normalizar(d.zip, anio, mes)  # ErrorContrato sube y detiene todo
    filas = a_proceso_resumen(normalizado)
    cerrado = pct_cerrado(normalizado)
    print(f"{etiqueta} {normalizado.n_releases:>6,} releases · {cerrado:>5.1f}% cerrado", end="")

    if seco or con is None:
        print("  (seco)")
        return "cargado"

    from carga import copiar, upsert_cobertura
    with con.cursor() as cur:
        cur.execute("delete from proceso_resumen where anio=%s and mes=%s", (anio, mes))
    copiar(con, "proceso_resumen", COLUMNAS_RESUMEN, filas)
    estado = "parcial" if normalizado.avisos else "cargado"
    upsert_cobertura(
        con, anio, mes, estado,
        registros=normalizado.n_releases, pct_cerrado=cerrado,
        bytes_zip=d.bytes_crudos, intentos=d.intentos,
        nota="; ".join(normalizado.avisos) or None,
    )
    con.commit()
    print(f"  cargado ({len(filas):,} filas)")
    return estado


def main() -> int:
    p = argparse.ArgumentParser(description="Ingesta OCDS del SERCOP")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--mes", help="AAAA-MM")
    g.add_argument("--desde", help="AAAA-MM (usar con --hasta)")
    g.add_argument("--incremental", action="store_true", help="mes en curso y anterior")
    p.add_argument("--hasta", help="AAAA-MM")
    p.add_argument("--forzar", action="store_true", help="reprocesa aunque esté en caché")
    p.add_argument("--seco", action="store_true", help="no escribe en Postgres")
    args = p.parse_args()

    if args.mes:
        objetivo = meses_entre(args.mes, args.mes)
    elif args.incremental:
        hoy = dt.date.today()
        anterior = (hoy.replace(day=1) - dt.timedelta(days=1))
        objetivo = [(anterior.year, anterior.month), (hoy.year, hoy.month)]
    else:
        if not args.hasta:
            p.error("--desde requiere --hasta")
        objetivo = meses_entre(args.desde, args.hasta)

    con = ctx = None
    if not args.seco:
        from carga import conexion
        ctx = conexion()
        con = ctx.__enter__()

    resumen: dict[str, int] = {}
    try:
        for anio, mes in objetivo:
            try:
                estado = procesar_mes(anio, mes, con, args.seco, args.forzar)
            except (ErrorContrato, ErrorCodificacion) as e:
                # Esto SÍ detiene todo: la fuente cambió.
                print(f"\nDETENIDO. {e}", file=sys.stderr)
                return 2
            resumen[estado] = resumen.get(estado, 0) + 1

        if con:
            from carga import PRESUPUESTO_MB, verificar_presupuesto
            mb = verificar_presupuesto(con)
            print(f"\nbase: {mb} MB de {PRESUPUESTO_MB} presupuestados")
    finally:
        if con:
            ctx.__exit__(None, None, None)

    print("resumen:", ", ".join(f"{k}={v}" for k, v in sorted(resumen.items())))
    return 0 if resumen.get("pendiente", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
