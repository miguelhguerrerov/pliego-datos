"""Ruta JSON: el detalle que el CSV no trae.

El CSV normalizado sirve para el radar y los agregados de cabecera, pero **no trae
ítems, ni oferentes, ni pujas, ni direcciones, ni el referencial de subasta inversa**.
Todo eso vive solo en la descarga JSON. Ver docs/datos.md §3 y §4.

Sin esta ruta no hay benchmark de precio unitario, que es la función que se cobra.

El JSON de un mes entero corta la conexión a los ~120 s: hay que trocear por método.
"""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from codificacion import decodificar
from descarga import BASE, INTENTOS, METODOS, TIMEOUT, ErrorDescarga
from entidades import extraer_ruc
from normaliza import estado_de_tag, metodo_base


@dataclass
class DetalleMes:
    anio: int
    mes: int
    sin_datos: list[str] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    oferentes: list[dict] = field(default_factory=list)
    pujas: list[dict] = field(default_factory=list)
    partes: list[dict] = field(default_factory=list)
    procesos: list[dict] = field(default_factory=list)
    metodos_fallidos: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (
            f"{len(self.procesos):,} procesos · {len(self.items):,} ítems · "
            f"{len(self.oferentes):,} oferentes · {len(self.pujas):,} pujas · "
            f"{len(self.partes):,} partes"
        )

    @property
    def completo(self) -> bool:
        """Un metodo sin datos NO es un fallo. Solo lo son los que fallaron de verdad."""
        return not self.metodos_fallidos


# El servidor responde 500 con FileNotFoundException cuando NO HAY DATOS de ese metodo
# ese mes, en vez de devolver un archivo vacio. Medido en agosto de 2026: los 6 metodos
# que "fallaban" eran exactamente los 6 sin ningun proceso segun el CSV.
#
# Distinguirlo importa: si todos los meses aparecen como parciales, la etiqueta deja de
# significar nada y entrena a ignorarla. Ver docs/decisiones.md D-020.
SIN_DATOS = "FileNotFoundException"


class MetodoSinDatos(Exception):
    """No hay procesos de ese metodo ese mes. No es un fallo."""


def _descargar_metodo(anio: int, mes: int, metodo: str, cache: Path | None) -> list | None:
    """Descarga el JSON de un método concreto.

    Devuelve None si agota los reintentos; lanza MetodoSinDatos si la fuente indica
    que no hay procesos de ese método ese mes.
    """
    clave = urllib.parse.quote(metodo, safe="")[:40]
    destino = cache / f"{anio}_{mes:02d}_{clave}.json.zip" if cache else None
    if destino and destino.exists() and destino.stat().st_size > 500:
        crudo = destino.read_bytes()
    else:
        params = urllib.parse.urlencode(
            {"type": "json", "year": anio, "month": mes, "method": metodo}
        )
        url = f"{BASE}?{params}"
        crudo = None
        for intento in range(1, INTENTOS + 1):
            try:
                pet = urllib.request.Request(url, headers={"User-Agent": "pliego-datos/1.0"})
                with urllib.request.urlopen(pet, timeout=TIMEOUT) as r:
                    crudo = r.read()
                zipfile.ZipFile(io.BytesIO(crudo))  # falla si viene truncado
                break
            except urllib.error.HTTPError as e:
                cuerpo = e.read()[:400].decode("utf-8", errors="replace")
                if e.code == 500 and SIN_DATOS in cuerpo:
                    raise MetodoSinDatos(metodo) from None
                print(f"    reintento {metodo[:24]} ({intento}/{INTENTOS}): HTTP {e.code}")
                crudo = None
                time.sleep(3 * intento)
            except Exception as e:  # noqa: BLE001 - se registra y se reintenta
                print(f"    reintento {metodo[:24]} ({intento}/{INTENTOS}): {type(e).__name__}")
                crudo = None
                time.sleep(3 * intento)
        if crudo is None:
            return None
        if destino:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(crudo)

    zf = zipfile.ZipFile(io.BytesIO(crudo))
    nombres = [i.filename for i in zf.infolist() if i.filename.endswith(".json")]
    if not nombres:
        return None
    validado = decodificar(zf.read(nombres[0]), f"{anio}-{mes:02d}/{nombres[0]}")
    return json.loads(validado.texto)


def _extraer(release: dict, destino: DetalleMes) -> None:
    ocid = release.get("ocid")
    if not ocid:
        return
    tender = release.get("tender") or {}
    planning = release.get("planning") or {}

    destino.procesos.append({
        "ocid": ocid,
        "estado": estado_de_tag(json.dumps(release.get("tag", []))),
        "metodo": metodo_base(tender.get("procurementMethodDetails")),
        "titulo": tender.get("title"),
        "objeto": tender.get("description"),
        "referencial": (tender.get("value") or {}).get("amount")
                       or ((planning.get("budget") or {}).get("amount") or {}).get("amount"),
        "n_oferentes": tender.get("numberOfTenderers"),
        "categoria_ocds": tender.get("mainProcurementCategory"),
        "criterio": tender.get("awardCriteria"),
        "partida": (planning.get("budget") or {}).get("id"),
        "justificacion": planning.get("rationale"),
        "comprador_ruc": extraer_ruc((release.get("buyer") or {}).get("id")),
        "fecha": (release.get("date") or "")[:10],
    })

    # Ítems: la base del benchmark de precio unitario. Vienen en tender y en awards;
    # los de awards son los efectivamente adjudicados, que es lo que interesa.
    for origen, contenedor in (("tender", [tender]), ("award", release.get("awards") or [])):
        for c in contenedor:
            for it in (c.get("items") or []):
                unidad = it.get("unit") or {}
                clasif = it.get("classification") or {}
                destino.items.append({
                    "ocid": ocid,
                    "origen": origen,
                    "item_id": it.get("id"),
                    "cpc": clasif.get("id"),
                    "descripcion": it.get("description"),
                    "cantidad": it.get("quantity"),
                    "unidad": unidad.get("name"),
                    "precio_unitario": (unidad.get("value") or {}).get("amount"),
                    "moneda": (unidad.get("value") or {}).get("currency"),
                })

    # Oferentes: TODOS los participantes, no solo el ganador. Es la base del análisis
    # de competencia, y el CSV no los trae.
    for t in (tender.get("tenderers") or []):
        destino.oferentes.append({
            "ocid": ocid,
            "ruc": extraer_ruc(t.get("id")),
            "nombre": t.get("name"),
            "gano": False,
        })
    ganadores = {
        extraer_ruc(s.get("id"))
        for a in (release.get("awards") or [])
        for s in (a.get("suppliers") or [])
    }
    for o in destino.oferentes:
        if o["ocid"] == ocid and o["ruc"] in ganadores:
            o["gano"] = True

    # Pujas de subasta inversa: el único sitio donde se ve cómo baja el precio.
    for subasta in (release.get("auctions") or []):
        for etapa in (subasta.get("stages") or []):
            for b in (etapa.get("bids") or []):
                tend = (b.get("tenderers") or [{}])[0]
                destino.pujas.append({
                    "ocid": ocid,
                    "puja_id": b.get("id"),
                    "ruc": extraer_ruc(tend.get("id")),
                    "fecha": (b.get("date") or "")[:19],
                    "valor": (b.get("value") or {}).get("amount"),
                })

    # Partes: territorio real y contacto. El CSV no trae provincia ni cantón.
    for p in (release.get("parties") or []):
        dir_ = p.get("address") or {}
        ruc = extraer_ruc(p.get("id"))
        if not ruc:
            continue
        destino.partes.append({
            "ocid": ocid,
            "ruc": ruc,
            "nombre": p.get("name"),
            "roles": ",".join(p.get("roles") or []),
            "provincia": dir_.get("region"),
            "canton": dir_.get("locality"),
            "web": (p.get("contactPoint") or {}).get("url"),
        })


def descargar_detalle(anio: int, mes: int, cache: Path | None = None) -> DetalleMes:
    """Descarga y extrae el detalle de un mes, troceando por método."""
    detalle = DetalleMes(anio, mes)
    for metodo in METODOS:
        try:
            paquetes = _descargar_metodo(anio, mes, metodo, cache)
        except MetodoSinDatos:
            detalle.sin_datos.append(metodo)
            continue
        if paquetes is None:
            detalle.metodos_fallidos.append(metodo)
            continue
        if isinstance(paquetes, dict):
            paquetes = [paquetes]
        for paquete in paquetes:
            for release in (paquete.get("releases") or []):
                _extraer(release, detalle)

    if len(detalle.metodos_fallidos) + len(detalle.sin_datos) == len(METODOS)             and not detalle.sin_datos:
        raise ErrorDescarga(
            f"{anio}-{mes:02d}: fallaron los {len(METODOS)} métodos. Márcalo pendiente."
        )
    return detalle
