"""El detalle de los procesos que siguen abiertos.

    python src/abiertos.py            # descarga, filtra y carga
    python src/abiertos.py --seco     # cuenta y muestra, sin escribir

**Qué hace y por qué.** La ficha de un proceso necesita sus ítems, sus oferentes, sus
pujas y sus consultas. Ese detalle solo viene por la ruta JSON, y hasta ahora únicamente
se publicaba en Parquet una vez al mes — donde la aplicación no puede consultarlo por
`ocid`.

Este paso trae ese detalle a Postgres **solo para los procesos en estado `abierto`**, que
son unos 2.000 de los 280.000 de la ventana. Es la excepción medida al invariante 1 que
justifica D-035.

**El reciclaje es lo que mantiene el tamaño acotado.** Cada pasada reemplaza las cinco
tablas enteras con los procesos abiertos de ese día. Cuando uno cierra, su detalle
desaparece de Postgres y se queda en el Parquet, que es el archivo permanente. La tabla
no crece con el tiempo: gira.

**Por qué no se llama al SERCOP en vivo desde la aplicación.** Medido contra su API:
20 peticiones seguidas dieron 20 × HTTP 429; ocho a la mitad del límite declarado, ocho
más; y una sola petición tras nueve minutos de pausa, otro 429. No hay cabeceras de
límite, así que no se puede auto-regular. Ver D-035.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from descarga import ErrorDescarga  # noqa: E402
from detalle import descargar_detalle  # noqa: E402
from normaliza import desglosar_renglon  # noqa: E402

CACHE = Path(".cache")

TABLAS = {
    # `precio_unitario` y `monto_linea` se guardan las DOS, ya desglosadas. Antes solo
    # estaba una y la ficha derivaba la otra dividiendo entre la cantidad, que es
    # correcto en subasta inversa y falso en todo lo demás. Ver D-041.
    "proceso_item": ["ocid", "item_id", "origen", "cpc", "descripcion",
                     "cantidad", "unidad", "precio_unitario", "monto_linea"],
    "proceso_oferente": ["ocid", "ruc", "nombre", "gano"],
    "proceso_puja": ["ocid", "puja_id", "ruc", "fecha", "valor"],
    "proceso_consulta": ["ocid", "consulta_id", "fecha", "autor_ruc", "autor",
                         "pregunta", "respuesta", "fecha_respuesta"],
    "proceso_lote": ["ocid", "lote_id", "titulo", "monto", "tecnicas"],
}


def meses_a_mirar(hoy: dt.date | None = None) -> list[tuple[int, int]]:
    """El mes en curso y el anterior.

    Un proceso abierto se convocó hace días o semanas, no meses: la ventana de dos meses
    cubre el ciclo entero de una subasta inversa con margen. Bajar más meses multiplica
    el tiempo de descarga sin traer procesos que sigan abiertos.
    """
    hoy = hoy or dt.date.today()
    anterior = (hoy.replace(day=1) - dt.timedelta(days=1))
    return [(anterior.year, anterior.month), (hoy.year, hoy.month)]


def _instante(texto):
    if not texto:
        return None
    try:
        return dt.datetime.fromisoformat(str(texto)[:19])
    except ValueError:
        return None


def filtrar(detalle, abiertos: set[str]) -> dict[str, list[tuple]]:
    """Se queda con lo que pertenece a un proceso abierto, y lo pasa a filas.

    Filtrar aquí y no al descargar es deliberado: la descarga viene troceada por método
    y no sabe qué está abierto. Filtrar después cuesta memoria y nada más.
    """
    filas: dict[str, list[tuple]] = {t: [] for t in TABLAS}

    # El método decide si `unit.value.amount` es un precio o un total, así que hay que
    # tenerlo a mano antes de recorrer los ítems.
    metodo_de = {p["ocid"]: p.get("metodo") for p in detalle.procesos}

    for it in detalle.items:
        if it["ocid"] not in abiertos:
            continue
        precio, monto_linea = desglosar_renglon(
            metodo_de.get(it["ocid"]), it.get("precio_unitario"), it.get("cantidad")
        )
        filas["proceso_item"].append((
            it["ocid"], it.get("item_id"), it.get("origen"), it.get("cpc"),
            (it.get("descripcion") or "")[:400] or None,
            it.get("cantidad"), it.get("unidad"), precio, monto_linea,
        ))

    vistos = set()
    for o in detalle.oferentes:
        clave = (o["ocid"], o.get("ruc"))
        if o["ocid"] not in abiertos or not o.get("ruc") or clave in vistos:
            continue
        vistos.add(clave)
        filas["proceso_oferente"].append(
            (o["ocid"], o["ruc"], (o.get("nombre") or "")[:180] or None, bool(o.get("gano"))))

    for p in detalle.pujas:
        if p["ocid"] not in abiertos or not p.get("puja_id"):
            continue
        filas["proceso_puja"].append(
            (p["ocid"], p["puja_id"], p.get("ruc"), _instante(p.get("fecha")), p.get("valor")))

    for q in detalle.consultas:
        if q["ocid"] not in abiertos or not q.get("consulta_id"):
            continue
        filas["proceso_consulta"].append((
            q["ocid"], q["consulta_id"], _instante(q.get("fecha")),
            q.get("autor_ruc"), (q.get("autor") or "")[:180] or None,
            q.get("pregunta"), q.get("respuesta"), _instante(q.get("fecha_respuesta")),
        ))

    for l in detalle.lotes:
        if l["ocid"] not in abiertos or not l.get("lote_id"):
            continue
        filas["proceso_lote"].append((
            l["ocid"], l["lote_id"], (l.get("titulo") or "")[:200] or None,
            l.get("monto"), l.get("tecnicas"),
        ))

    # Claves repetidas dentro de la misma tanda: la fuente reparte un proceso entre
    # varios metodos alguna vez, y `copy` no perdona un duplicado de clave primaria.
    for tabla in ("proceso_item", "proceso_puja", "proceso_consulta", "proceso_lote"):
        n_clave = {"proceso_item": 3}.get(tabla, 2)
        unicas, salida = set(), []
        for f in filas[tabla]:
            k = f[:n_clave]
            if k in unicas:
                continue
            unicas.add(k)
            salida.append(f)
        filas[tabla] = salida
    return filas


def main() -> int:
    p = argparse.ArgumentParser(description="Detalle de los procesos abiertos")
    p.add_argument("--seco", action="store_true", help="cuenta y muestra, sin escribir")
    args = p.parse_args()

    from carga import conexion, reemplazar, verificar_presupuesto

    with conexion() as con:
        with con.cursor() as cur:
            cur.execute("select ocid from proceso_resumen where estado = 'abierto'")
            abiertos = {f[0] for f in cur.fetchall()}
        print(f"procesos abiertos: {len(abiertos):,}")
        if not abiertos:
            print("  nada que hacer")
            return 0

        total: dict[str, list[tuple]] = {t: [] for t in TABLAS}
        for anio, mes in meses_a_mirar():
            try:
                d = descargar_detalle(anio, mes, cache=CACHE)
            except ErrorDescarga as e:
                # Un mes que falla no detiene el paso: el otro sigue trayendo detalle,
                # y una ficha con menos datos es mejor que ninguna ficha.
                print(f"  {anio}-{mes:02d} no disponible: {e}")
                continue
            print(f"  {anio}-{mes:02d} {d.resumen()}")
            for tabla, filas in filtrar(d, abiertos).items():
                total[tabla].extend(filas)

        con_detalle = {f[0] for f in total["proceso_item"]} | {f[0] for f in total["proceso_oferente"]}
        print(f"\nabiertos con algun detalle: {len(con_detalle):,} de {len(abiertos):,} "
              f"({len(con_detalle)/len(abiertos):.0%})")
        for tabla, filas in total.items():
            print(f"  {tabla:<18} {len(filas):>7,} filas")

        if args.seco:
            return 0

        # Reemplazo entero: es lo que recicla el espacio cuando un proceso cierra.
        for tabla, columnas in TABLAS.items():
            reemplazar(con, tabla, columnas, total[tabla])
        con.commit()

        mb = verificar_presupuesto(con)
        print(f"\nbase: {mb} MB de 460 presupuestados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
