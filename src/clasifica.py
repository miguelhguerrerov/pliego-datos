"""Clasificación del objeto contractual por embeddings y agrupamiento.

    python src/clasifica.py --construir      # taxonomía desde cero
    python src/clasifica.py --pendientes     # asigna categoría a lo no clasificado

**Por qué existe.** El código CPC solo viene poblado en catálogo electrónico. En el resto
de métodos —los de mayor valor— el objeto contractual es texto libre. Sin categoría
normalizada no hay benchmark de precios, ni compradores huérfanos, ni tamaño de mercado
por sector: todo lo que se cobra depende de resolver esto.

**Por qué no se clasifica registro a registro con un modelo de lenguaje.** Serían 2,77 M
de llamadas, unos 50 USD, y peor resultado. Comprobado: preguntarle al modelo por «suero
antiofídico polivalente» sin contexto devolvió «medicina veterinaria», que es incorrecto.
Etiquetar grupos con sus miembros a la vista da mejor resultado y cuesta un dólar.
Ver docs/decisiones.md D-006.

El trabajo caro lo hace el agrupamiento, que es aritmética. El modelo solo bautiza.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

API = "https://api.deepinfra.com/v1/openai"
MODELO_EMBEDDING = "BAAI/bge-m3"
MODELO_ETIQUETA = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

DIMENSIONES = 256      # truncado Matryoshka: los 1024 originales no caben en Parquet
                       # sin cuadruplicar el peso, y 256 basta para agrupar.
LOTE_EMBEDDING = 256   # textos por petición
N_CATEGORIAS = 400     # grupos que el modelo tendrá que bautizar
MUESTRA_POR_GRUPO = 12 # ejemplos que se le muestran al modelo para bautizar cada grupo

# Solo se quita lo que NO informa: codigos de expediente y la formula fija con que
# el catalogo electronico encabeza todas sus ordenes. El resto se conserva.
#
# Una version anterior tambien quitaba "adquisicion de", "servicio de" y similares, y
# colapsaba 17.473 objetos unicos a 15: destruia toda la senal. Normalizar de mas es
# peor que no normalizar. Ver docs/decisiones.md D-016.
PREAMBULO = re.compile(
    r"^\s*orden de compra para adquirir los siguientes productos:?\s*", re.IGNORECASE
)
CODIGOS = re.compile(r"[A-Z]{2,}[A-Z0-9]*-[A-Z0-9-]{4,}")


def normalizar_texto(objeto: str | None) -> str:
    """Deja el objeto contractual comparable sin perder de que trata."""
    if not objeto:
        return ""
    t = PREAMBULO.sub("", objeto)
    t = CODIGOS.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t[:300] if len(t) >= 8 else ""


# --- DeepInfra -----------------------------------------------------------------

def _clave() -> str:
    clave = os.environ.get("DEEPINFRA_API_KEY")
    if not clave:
        raise RuntimeError(
            "Falta DEEPINFRA_API_KEY. Es un secreto del repositorio; nunca va en el "
            "código (invariante 8)."
        )
    return clave


def _peticion(ruta: str, cuerpo: dict, intentos: int = 4) -> dict:
    datos = json.dumps(cuerpo).encode()
    cabeceras = {
        "Authorization": f"Bearer {_clave()}",
        "Content-Type": "application/json",
        "User-Agent": "pliego-datos/1.0",
    }
    for intento in range(1, intentos + 1):
        try:
            pet = urllib.request.Request(API + ruta, data=datos, headers=cabeceras)
            with urllib.request.urlopen(pet, timeout=180) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            if intento == intentos:
                raise
            print(f"    reintento {intento}/{intentos}: {type(e).__name__}")
            time.sleep(3 * intento)
    raise RuntimeError("inalcanzable")


def embeber(textos: list[str]) -> list[list[float]]:
    """Devuelve un vector de DIMENSIONES por texto.

    Coste medido: ~30 tokens por objeto contractual. Embeber los 2,77 M sale por
    menos de 1 USD. Ver CLAUDE.md §9.
    """
    salida: list[list[float]] = []
    for i in range(0, len(textos), LOTE_EMBEDDING):
        lote = textos[i : i + LOTE_EMBEDDING]
        r = _peticion("/embeddings", {"model": MODELO_EMBEDDING, "input": lote})
        for fila in r["data"]:
            salida.append(fila["embedding"][:DIMENSIONES])
        print(f"    embebidos {min(i + LOTE_EMBEDDING, len(textos)):,}/{len(textos):,}")
    return salida


def bautizar(ejemplos: list[str]) -> str:
    """El modelo solo nombra un grupo, con sus miembros a la vista."""
    lista = "\n".join(f"- {e[:110]}" for e in ejemplos[:MUESTRA_POR_GRUPO])
    r = _peticion("/chat/completions", {
        "model": MODELO_ETIQUETA,
        "max_tokens": 24,
        "temperature": 0,
        "messages": [{
            "role": "user",
            "content": (
                "Estos son objetos contractuales de compras públicas del Ecuador que "
                "pertenecen a la misma categoría:\n\n" + lista + "\n\n"
                "Responde SOLO con el nombre de la categoría, de dos a cuatro palabras, "
                "en español, en singular y sin comillas ni explicación."
            ),
        }],
    })
    nombre = r["choices"][0]["message"]["content"].strip().strip('".')
    return nombre[:60] or "Sin clasificar"


# --- agrupamiento ---------------------------------------------------------------

def agrupar(vectores, n_grupos: int = N_CATEGORIAS, semilla: int = 7):
    """K-means por lotes. Determinista con semilla fija: dos ejecuciones sobre los
    mismos datos dan la misma taxonomía, que es lo que permite que las categorías
    sean estables entre recargas."""
    import numpy as np
    from sklearn.cluster import MiniBatchKMeans

    X = np.asarray(vectores, dtype="float32")
    # Normalizar para que la distancia euclídea equivalga a la similitud coseno.
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    n_grupos = min(n_grupos, len(X))
    modelo = MiniBatchKMeans(
        n_clusters=n_grupos, random_state=semilla, batch_size=2048, n_init=3
    )
    return modelo.fit_predict(X), modelo


def construir_taxonomia(textos: list[str], n_grupos: int = N_CATEGORIAS) -> dict:
    """Devuelve {indice_de_texto: (id_grupo, nombre_grupo)} y la lista de categorías."""
    unicos = sorted({normalizar_texto(t) for t in textos if normalizar_texto(t)})
    print(f"  textos únicos tras normalizar: {len(unicos):,} de {len(textos):,}")

    vectores = embeber(unicos)
    etiquetas, _ = agrupar(vectores, n_grupos)

    miembros: dict[int, list[str]] = {}
    for texto, grupo in zip(unicos, etiquetas):
        miembros.setdefault(int(grupo), []).append(texto)

    categorias = {}
    for grupo, ejemplos in sorted(miembros.items()):
        nombre = bautizar(ejemplos)
        categorias[grupo] = {"nombre": nombre, "n": len(ejemplos)}
        print(f"    grupo {grupo:>3}  {len(ejemplos):>6,} textos  {nombre}")

    return {
        "categorias": categorias,
        "asignacion": {t: int(g) for t, g in zip(unicos, etiquetas)},
    }


def escribir(con, categorias: dict, asignacion: dict) -> tuple[int, int]:
    """Guarda la taxonomia y asigna la categoria a cada proceso.

    La asignacion se hace por el texto normalizado, no por ocid: dos procesos con el
    mismo objeto contractual comparten categoria por construccion.
    """
    from carga import copiar

    with con.cursor() as cur:
        cur.execute("update proceso_resumen set categoria_id = null")
        cur.execute("truncate categoria restart identity cascade")

    filas = [(int(g) + 1, d["nombre"], d["n"]) for g, d in sorted(categorias.items())]
    copiar(con, "categoria", ["id", "nombre", "n_procesos"], filas)

    # Tabla temporal + un solo update: 280.000 updates fila a fila tardarian minutos.
    with con.cursor() as cur:
        cur.execute("create temp table asig (texto text primary key, cid int) on commit drop")
    copiar(con, "asig", ["texto", "cid"],
           [(t, int(g) + 1) for t, g in asignacion.items()])

    with con.cursor() as cur:
        cur.execute("create index on asig (texto)")
        cur.execute("select ocid, objeto from proceso_resumen where objeto is not null")
        pares = [(normalizar_texto(o), ocid) for ocid, o in cur.fetchall()]

    with con.cursor() as cur:
        cur.execute("create temp table ocid_texto (ocid text primary key, texto text) on commit drop")
    copiar(con, "ocid_texto", ["ocid", "texto"], [(o, t) for t, o in pares if t])

    with con.cursor() as cur:
        cur.execute("""
            update proceso_resumen p set categoria_id = a.cid
            from ocid_texto ot join asig a on a.texto = ot.texto
            where p.ocid = ot.ocid
        """)
        n = cur.rowcount
        cur.execute("select count(*) from proceso_resumen where categoria_id is not null")
        total = cur.fetchone()[0]
    con.commit()
    return len(filas), total


def main() -> int:
    p = argparse.ArgumentParser(description="Clasifica el objeto contractual")
    p.add_argument("--construir", action="store_true", help="taxonomía desde cero")
    p.add_argument("--limite", type=int, default=0, help="solo N objetos (pruebas)")
    p.add_argument("--grupos", type=int, default=N_CATEGORIAS)
    p.add_argument("--salida", default="taxonomia.json")
    p.add_argument("--reusar", help="aplica una taxonomia ya construida (JSON + asignacion)")
    args = p.parse_args()

    if not args.construir:
        p.print_help()
        return 0

    from carga import conexion

    with conexion() as con, con.cursor() as cur:
        cur.execute(
            "select objeto from proceso_resumen where objeto is not null"
            + (f" limit {args.limite}" if args.limite else "")
        )
        textos = [r[0] for r in cur.fetchall()]
    print(f"objetos contractuales: {len(textos):,}")

    resultado = construir_taxonomia(textos, args.grupos)
    Path(args.salida).write_text(
        json.dumps(resultado["categorias"], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\ntaxonomía de {len(resultado['categorias'])} categorías en {args.salida}")

    # Sin esto la taxonomía existe pero no sirve: hay que escribirla y asignarla.
    with conexion() as con:
        n_cat, n_proc = escribir(con, resultado["categorias"], resultado["asignacion"])
    print(f"escritas {n_cat} categorías · {n_proc:,} procesos clasificados "
          f"de {len(textos):,}")

    frecuentes = Counter(
        resultado["categorias"][g]["nombre"] for g in resultado["asignacion"].values()
    )
    print("\ncategorías más frecuentes:")
    for nombre, n in frecuentes.most_common(12):
        print(f"  {n:>6,}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
