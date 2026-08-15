"""Publicación del detalle como Parquet en releases de GitHub.

    python src/publicar.py --mes 2026-08
    python src/publicar.py --desde 2026-01 --hasta 2026-08

Esta es la capa que sostiene toda la arquitectura (invariante 1 y decisiones.md D-002):

- Es donde vive el detalle íntegro, que NO cabe en los 500 MB de Postgres.
- Es la copia de seguridad: reconstruye la base entera en menos de una hora, y el plan
  gratuito de Supabase no tiene copias.
- Es el activo público: un dataset limpio del SERCOP en Parquet, bajo la misma licencia
  CC BY 3.0 EC que la fuente.

Los releases de GitHub no tienen límite práctico de tamaño y se sirven por CDN.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from descarga import ErrorDescarga  # noqa: E402
from detalle import DetalleMes, descargar_detalle  # noqa: E402

CACHE = Path(".cache")
SALIDA = Path(".parquet")
REPO = os.environ.get("GITHUB_REPOSITORY", "miguelhguerrerov/pliego-datos")
API = "https://api.github.com"

TABLAS = ("procesos", "items", "oferentes", "pujas", "partes")


def _escribir_parquet(detalle: DetalleMes, destino: Path) -> list[Path]:
    """Un archivo por tabla y mes. Compresión zstd: mejor ratio que snappy y DuckDB
    la lee de forma nativa en el navegador."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    destino.mkdir(parents=True, exist_ok=True)
    escritos = []
    for nombre in TABLAS:
        filas = getattr(detalle, nombre)
        if not filas:
            continue
        ruta = destino / f"{nombre}_{detalle.anio}_{detalle.mes:02d}.parquet"
        pq.write_table(pa.Table.from_pylist(filas), ruta, compression="zstd")
        escritos.append(ruta)
    return escritos


def _peticion(metodo: str, url: str, cuerpo=None, tipo="application/json"):
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise RuntimeError(
            "Falta GITHUB_TOKEN. En Actions se pasa como ${{ secrets.GITHUB_TOKEN }} "
            "con permiso contents: write."
        )
    cabeceras = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "pliego-datos",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    datos = cuerpo
    if isinstance(cuerpo, (dict, list)):
        datos = json.dumps(cuerpo).encode()
        cabeceras["Content-Type"] = tipo
    elif isinstance(cuerpo, bytes):
        cabeceras["Content-Type"] = tipo
    pet = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    with urllib.request.urlopen(pet, timeout=300) as r:
        texto = r.read().decode()
        return json.loads(texto) if texto else {}


def _asegurar_release(etiqueta: str) -> dict:
    """Un release por año: 12 archivos por tabla dentro de cada uno."""
    try:
        return _peticion("GET", f"{API}/repos/{REPO}/releases/tags/{etiqueta}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    return _peticion("POST", f"{API}/repos/{REPO}/releases", {
        "tag_name": etiqueta,
        "name": f"Detalle OCDS {etiqueta.replace('datos-', '')}",
        "body": (
            "Detalle íntegro de la contratación pública del Ecuador en Parquet.\n\n"
            "Ítems con CPC y precio unitario, oferentes, pujas de subasta inversa y "
            "partes con territorio.\n\n"
            "Fuente: Servicio Nacional de Contratación Pública del Ecuador, "
            "licencia CC BY 3.0 EC. Pliego no está afiliado al SERCOP."
        ),
    })


def _subir(release: dict, ruta: Path) -> None:
    # Un activo con el mismo nombre bloquea la subida: se reemplaza.
    for activo in release.get("assets", []):
        if activo["name"] == ruta.name:
            _peticion("DELETE", f"{API}/repos/{REPO}/releases/assets/{activo['id']}")
    url = release["upload_url"].split("{")[0] + f"?name={ruta.name}"
    _peticion("POST", url, ruta.read_bytes(), tipo="application/octet-stream")


def _registrar(anio, mes, estado, detalle=None, kb=0):
    """Deja constancia en cobertura_parquet. Sin registro, un mes incompleto queda
    publicado y en silencio, que es el fallo que este proyecto existe para evitar."""
    if not os.environ.get("SUPABASE_DB_URL"):
        return
    from carga import conexion

    with conexion() as con, con.cursor() as cur:
        cur.execute("""
            insert into cobertura_parquet (anio, mes, estado, n_procesos, n_items,
                n_oferentes, n_pujas, metodos_sin_datos, metodos_fallidos, kb, fecha)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
            on conflict (anio, mes) do update set
                estado=excluded.estado, n_procesos=excluded.n_procesos,
                n_items=excluded.n_items, n_oferentes=excluded.n_oferentes,
                n_pujas=excluded.n_pujas, metodos_sin_datos=excluded.metodos_sin_datos,
                metodos_fallidos=excluded.metodos_fallidos, kb=excluded.kb, fecha=now()
        """, (anio, mes, estado,
              len(detalle.procesos) if detalle else None,
              len(detalle.items) if detalle else None,
              len(detalle.oferentes) if detalle else None,
              len(detalle.pujas) if detalle else None,
              len(detalle.sin_datos) if detalle else 0,
              len(detalle.metodos_fallidos) if detalle else 0,
              int(kb)))
        con.commit()


def publicar_mes(anio: int, mes: int, subir: bool) -> str:
    try:
        detalle = descargar_detalle(anio, mes, cache=CACHE)
    except ErrorDescarga as e:
        print(f"{anio}-{mes:02d} PENDIENTE: {e}")
        _registrar(anio, mes, "pendiente")
        return "pendiente"

    rutas = _escribir_parquet(detalle, SALIDA)
    peso = sum(r.stat().st_size for r in rutas) / 1024
    partes = []
    if detalle.sin_datos:
        partes.append(f"{len(detalle.sin_datos)} métodos sin datos")
    if detalle.metodos_fallidos:
        partes.append(f"{len(detalle.metodos_fallidos)} FALLIDOS")
    aviso = (" · " + " · ".join(partes)) if partes else ""
    print(f"{anio}-{mes:02d} {detalle.resumen()} · {peso:,.0f} KB{aviso}")

    if subir and rutas:
        release = _asegurar_release(f"datos-{anio}")
        for r in rutas:
            _subir(release, r)
        print(f"          publicado en el release datos-{anio}")
    estado = "publicado" if detalle.completo else "parcial"
    _registrar(anio, mes, estado, detalle, peso)
    return estado


def main() -> int:
    p = argparse.ArgumentParser(description="Publica el detalle en Parquet")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--mes", help="AAAA-MM")
    g.add_argument("--desde", help="AAAA-MM")
    p.add_argument("--hasta", help="AAAA-MM")
    p.add_argument("--sin-subir", action="store_true", help="solo escribe local")
    args = p.parse_args()

    from ingesta import meses_entre

    objetivo = (
        meses_entre(args.mes, args.mes) if args.mes
        else meses_entre(args.desde, args.hasta or args.desde)
    )

    resumen: dict[str, int] = {}
    for anio, mes in objetivo:
        estado = publicar_mes(anio, mes, subir=not args.sin_subir)
        resumen[estado] = resumen.get(estado, 0) + 1

    print("resumen:", ", ".join(f"{k}={v}" for k, v in sorted(resumen.items())))
    return 0 if resumen.get("pendiente", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
