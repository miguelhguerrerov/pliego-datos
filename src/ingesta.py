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


def _momento(texto: str | None) -> dt.datetime | None:
    """Un instante de la fuente, con su zona. `None` si no lo hay o viene mal.

    La fuente entrega `2026-07-09T14:00:00-05:00`. Guardarlo entero y no recortado es lo
    que permite decir «quedan 3 horas» en vez de «cierra hoy». Ver D-034.
    """
    if not texto:
        return None
    try:
        return dt.datetime.fromisoformat(str(texto).strip())
    except ValueError:
        # Algunas filas traen solo la fecha. Vale como instante a medianoche, pero se
        # deja constancia de que la hora no es un dato: es el valor por omision.
        try:
            return dt.datetime.fromisoformat(str(texto).strip()[:10])
        except ValueError:
            return None


def a_proceso_resumen(mes: MesNormalizado) -> list[tuple]:
    """Aplana el mes a filas de proceso_resumen.

    Los estados intermedios (planificacion, abierto) se conservan: son el producto
    de radar, no ruido. Ver docs/decisiones.md D-008.
    """
    tender = {t["ocid"]: t for t in mes.tablas["tender"]}
    # Los procesos en estado planning NO tienen fila en tender: su presupuesto vive en
    # planning.budget_amount. Sin esto el radar muestra oportunidades sin monto, que es
    # justo la cifra que las hace accionables. Ver docs/decisiones.md D-014.
    #
    # Y tampoco tienen `description`: el objeto de un proceso en planificacion vive en
    # `planning.rationale`, poblado al 100%. Sin esto, los 13.176 procesos en
    # planificacion —el 87% del radar— salian con un guion donde va lo que se compra.
    # Ver docs/decisiones.md D-031.
    presupuesto = {}
    razon = {}
    for pl in mes.tablas["planning"]:
        v = numero(pl.get("budget_amount"))
        if v is not None:
            presupuesto.setdefault(pl["ocid"], v)
        r_txt = (pl.get("rationale") or "").strip()
        if r_txt:
            razon.setdefault(pl["ocid"], r_txt)
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
        # CON HORA. Recortar a diez caracteres convertia «cierra hoy a las 14:00» en
        # «cierra hoy», que para quien tiene que presentar una oferta es la diferencia
        # entre tres horas y un dia. Ver docs/decisiones.md D-034.
        cierra = _momento(t.get("tenderPeriod_endDate"))
        publicado = _momento(t.get("tenderPeriod_startDate"))
        preguntas = _momento(t.get("enquiryPeriod_endDate"))

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
            numero(t.get("value_amount")) or presupuesto.get(ocid),
            awards.get(ocid),
            None,                                   # provincia: solo desde la ruta JSON
            # description lleva QUE se compra; title es solo el codigo del expediente
            # (17.473 valores unicos, todos codigos). Ver docs/decisiones.md D-016.
            #
            # `rationale` ANTES que `title`: en planificacion no hay tender, y rationale
            # es el objeto de verdad. Dejar que gane title devolveria el codigo del
            # expediente, que es el mismo fallo de D-016 por otra puerta.
            (t.get("description") or razon.get(ocid) or t.get("title") or "")[:200] or None,
            cierra,
            publicado,
            preguntas,
        ))
    return filas


COLUMNAS_RESUMEN = [
    "ocid", "fecha", "anio", "mes", "estado", "metodo", "cpc", "categoria_id",
    "comprador_ruc", "proveedor_ruc", "referencial", "adjudicado", "provincia",
    "objeto", "cierra", "publicado", "preguntas_hasta",
]

COLUMNAS_HECHO = [
    "anio", "mes", "comprador_ruc", "proveedor_ruc", "metodo",
    "n_procesos", "referencial", "adjudicado",
]


def a_entidad_nombre(mes: MesNormalizado) -> list[tuple]:
    """Cuenta las grafias vistas por RUC en el mes.

    El nombre canonico se resuelve por moda y no por el ultimo visto: los registros
    antiguos tienen mas erratas. Medido: solo el 1,8% de los RUC tiene mas de una
    grafia, y la tabla completa pesa unos 4 MB. Ver docs/decisiones.md D-017.
    """
    cuenta: dict[tuple, int] = {}
    for r in mes.tablas["releases"]:
        ruc = extraer_ruc(r.get("buyer_id"))
        nombre = (r.get("buyer_name") or "").strip()
        if ruc and nombre:
            cuenta[(ruc, nombre[:180])] = cuenta.get((ruc, nombre[:180]), 0) + 1
    for sup in mes.tablas["suppliers"]:
        ruc = extraer_ruc(sup.get("id"))
        nombre = (sup.get("name") or "").strip()
        if ruc and nombre:
            cuenta[(ruc, nombre[:180])] = cuenta.get((ruc, nombre[:180]), 0) + 1
    return [(ruc, nombre, n) for (ruc, nombre), n in cuenta.items()]


def a_hecho_mes(filas_resumen: list[tuple], anio: int, mes: int) -> list[tuple]:
    """Colapsa las filas del mes al grano mínimo que alimenta los agregados.

    Existe porque `proceso_resumen` solo guarda 24 meses —es la ventana del radar— y
    los agregados de proveedor necesitan los once años. Guardar el detalle completo
    de once años en Postgres rompería el presupuesto de 500 MB.
    Ver docs/decisiones.md D-015.

    Sin ocid ni objeto: eso vive en Parquet.
    """
    cubos: dict[tuple, list] = {}
    for f in filas_resumen:
        clave = (anio, mes, f[8] or "", f[9] or "", f[5] or "")
        cubo = cubos.setdefault(clave, [0, 0.0, 0.0])
        cubo[0] += 1
        cubo[1] += float(f[10] or 0)
        cubo[2] += float(f[11] or 0)
    return [
        (a, m, c or None, p or None, met or None, n, round(ref, 2), round(adj, 2))
        for (a, m, c, p, met), (n, ref, adj) in cubos.items()
    ]


def _dentro_de_ventana(anio: int, mes: int, hoy: dt.date | None = None) -> bool:
    """proceso_resumen guarda solo la ventana del radar. Cargar los once años ahí
    reventaría el presupuesto de 500 MB: los meses viejos van a hecho_mes y a Parquet."""
    hoy = hoy or dt.date.today()
    antiguedad = (hoy.year - anio) * 12 + (hoy.month - mes)
    return 0 <= antiguedad < VENTANA_RESUMEN_MESES


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
    hechos = a_hecho_mes(filas, anio, mes)
    nombres = a_entidad_nombre(normalizado)
    with con.cursor() as cur:
        # proceso_resumen: solo la ventana del radar. Los meses viejos se descartan.
        cur.execute("delete from proceso_resumen where anio=%s and mes=%s", (anio, mes))
        cur.execute("delete from hecho_mes where anio=%s and mes=%s", (anio, mes))
    if _dentro_de_ventana(anio, mes):
        copiar(con, "proceso_resumen", COLUMNAS_RESUMEN, filas)
    copiar(con, "hecho_mes", COLUMNAS_HECHO, hechos)
    # Acumula frecuencias: un RUC visto en muchos meses suma en cada uno.
    with con.cursor() as cur:
        cur.executemany(
            "insert into entidad_nombre (ruc, nombre, n) values (%s,%s,%s) "
            "on conflict (ruc, nombre) do update set n = entidad_nombre.n + excluded.n",
            nombres,
        )
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
