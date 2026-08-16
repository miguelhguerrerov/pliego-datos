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
    p.add_argument("--fusionar", action="store_true", help="fusiona categorias duplicadas")
    p.add_argument("--pendientes", action="store_true", help="clasifica lo recargado por la ingesta")
    p.add_argument("--seco", action="store_true", help="muestra sin escribir")
    p.add_argument("--por-texto", action="store_true",
                   help="asigna categoria CPC por cercania a los que no pueden tenerla")
    args = p.parse_args()

    if args.por_texto:
        from carga import conexion

        with conexion() as con:
            n, textos = asignar_por_texto(con, seco=args.seco)
        print(f"asignados por cercania: {n:,} procesos sobre {textos:,} textos unicos")
        return 0

    if args.pendientes:
        from carga import conexion

        with conexion() as con:
            pend, asig = asignar_pendientes(con)
        print(f"pendientes: {pend:,} · asignados por coincidencia: {asig:,} "
              f"({100*asig/max(pend,1):.1f}%)")
        return 0

    if args.fusionar:
        from carga import conexion

        with conexion() as con:
            n, fus = fusionar(con)
        print(f"categorías tras fusionar: {n} · {fus} absorbidas")
        return 0

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


# --- fusion de categorias duplicadas -------------------------------------------

UMBRAL_FUSION = 0.92


def fusionar(con, umbral: float = UMBRAL_FUSION) -> tuple[int, int]:
    """Fusiona categorias que nombran lo mismo.

    El agrupamiento produce grupos semanticamente adyacentes que el modelo bautiza
    igual o casi: medido sobre la primera taxonomia, 400 grupos dieron solo 257
    nombres distintos, y "Material de oficina" quedo partido en siete grupos con
    28.114 procesos entre todos.

    Eso rompe el producto: un benchmark repartido entre siete categorias que son la
    misma da medianas calculadas sobre un septimo de las observaciones.

    Se fusiona por similitud de los NOMBRES, no de los textos: son 400 embeddings en
    vez de 50.000. Ver docs/decisiones.md D-021.
    """
    import numpy as np

    with con.cursor() as cur:
        cur.execute("""select c.id, c.nombre, count(p.ocid) n
                       from categoria c left join proceso_resumen p on p.categoria_id = c.id
                       group by 1, 2 order by 3 desc""")
        cats = cur.fetchall()
    if not cats:
        return 0, 0

    ids = [c[0] for c in cats]
    nombres = [c[1] for c in cats]
    pesos = [c[2] for c in cats]

    V = np.asarray(embeber(nombres), dtype="float32")
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    S = V @ V.T
    np.fill_diagonal(S, 0.0)

    padre = list(range(len(ids)))

    def raiz(i: int) -> int:
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    for i, j in zip(*np.where(np.triu(S, 1) >= umbral)):
        a, b = raiz(int(i)), raiz(int(j))
        if a != b:
            # El representante es el grupo con mas procesos: su nombre es el que
            # mas gente vera, asi que conviene que sea el mas representativo.
            padre[max(a, b, key=lambda k: -pesos[k])] = min(a, b, key=lambda k: -pesos[k])

    grupos: dict[int, list[int]] = {}
    for i in range(len(ids)):
        grupos.setdefault(raiz(i), []).append(i)

    remapeo = [(ids[i], ids[r]) for r, miembros in grupos.items() for i in miembros if i != r]
    if not remapeo:
        return len(grupos), 0

    with con.cursor() as cur:
        cur.executemany(
            "update proceso_resumen set categoria_id=%s where categoria_id=%s",
            [(destino, origen) for origen, destino in remapeo],
        )
        cur.execute("delete from categoria where id = any(%s)",
                    ([o for o, _ in remapeo],))
        cur.execute("""update categoria c set n_procesos =
                       (select count(*) from proceso_resumen p where p.categoria_id = c.id)""")
    con.commit()
    compactar("proceso_resumen")
    return len(grupos), len(remapeo)


def compactar(*tablas: str) -> None:
    """Recupera el espacio de las tuplas muertas que deja un update masivo.

    Va en su propia conexion con autocommit porque **VACUUM no puede correr dentro de
    una transaccion**, y `carga.conexion()` abre con transaccion. Sin esto la base
    crecio de 365 a 662 MB, por encima del techo de 500 del plan gratuito.
    Ver docs/decisiones.md D-021 y D-024.
    """
    import psycopg

    from carga import url_conexion

    with psycopg.connect(url_conexion(), autocommit=True) as con, con.cursor() as cur:
        for tabla in tablas:
            cur.execute(f"vacuum full {tabla}")
            print(f"    compactada {tabla}")


def asignar_pendientes(con) -> tuple[int, int]:
    """Asigna categoria a los procesos que no la tienen, por coincidencia de texto.

    Existe porque la ingesta diaria hace borrado y copia del mes, asi que las filas
    recargadas entran sin categoria. Sin este paso, los dos meses mas recientes se
    quedan sin clasificar cada manana — y son justo los que alimentan el radar.
    Ver docs/decisiones.md D-022.

    No llama a la API: busca el texto normalizado entre los procesos ya clasificados.
    Los objetos contractuales se repiten mucho (2.786 textos unicos en 17.477 procesos),
    asi que cubre la mayoria. Lo que quede sin coincidencia espera a la reconstruccion
    semanal, que si embebe.
    """
    with con.cursor() as cur:
        cur.execute("select count(*) from proceso_resumen where categoria_id is null and objeto is not null")
        pendientes = cur.fetchone()[0]
        if not pendientes:
            return 0, 0

        # Diccionario texto -> categoria a partir de lo ya clasificado.
        cur.execute("""select objeto, categoria_id from proceso_resumen
                       where categoria_id is not null and objeto is not null""")
        conocido: dict[str, int] = {}
        for objeto, cid in cur.fetchall():
            t = normalizar_texto(objeto)
            if t:
                conocido.setdefault(t, cid)

        cur.execute("select ocid, objeto from proceso_resumen where categoria_id is null and objeto is not null")
        asignaciones = []
        for ocid, objeto in cur.fetchall():
            cid = conocido.get(normalizar_texto(objeto))
            if cid:
                asignaciones.append((cid, ocid))

    if asignaciones:
        with con.cursor() as cur:
            cur.executemany("update proceso_resumen set categoria_id=%s where ocid=%s", asignaciones)
        con.commit()
    return pendientes, len(asignaciones)




# --- asignacion por cercania semantica a una categoria CPC ----------------------

UMBRAL_CERCANIA = 0.55   # por debajo, mejor sin categoria que con una inventada


def asignar_por_texto(con, umbral: float = UMBRAL_CERCANIA,
                      seco: bool = False) -> tuple[int, int]:
    """Asigna categoria a los procesos que NUNCA podran recibirla del CPC.

    **Por que existe, medido.** La taxonomia sale del CPC de los items, y los items solo
    vienen por la ruta JSON. Pero el JSON troceado por metodo **no contiene ni un release
    en planificacion**: en esa fase el proceso todavia no tiene metodo asignado, asi que
    no cae en ningun trozo. Comprobado sobre subasta inversa de 2026-07 — de 1.264
    releases, cero con tag solo `planning`:

        ["planning","tender"]                     681
        ["planning","tender","award"]             518
        ["planning","tender","award","contract"]   65

    Consecuencia: los ~13.000 procesos del radar **no pueden recibir CPC por la ruta del
    Parquet, nunca**. No es el 5% de casos raros que se suponia: es la pantalla que da
    la razon para volver cada dia, entera.

    Aqui los embeddings hacen lo que si hacen bien —emparejar un texto con una categoria
    que ya existe— en vez de lo que hacian mal, que era inventar la taxonomia (D-030).

    Por debajo del umbral no se asigna nada. Una categoria equivocada es peor que
    ninguna: el usuario filtra por ella y no encuentra lo suyo, sin saber por que.
    """
    import numpy as np

    with con.cursor() as cur:
        cur.execute("select id, nombre, cpc, coalesce(descripcion, nombre) "
                    "from categoria where cpc is not null")
        cats = cur.fetchall()
        cur.execute("""
            select ocid, objeto from proceso_resumen
             where categoria_id is null and objeto is not null and length(objeto) > 8
        """)
        pendientes = cur.fetchall()

    if not cats or not pendientes:
        print(f"  nada que asignar (categorias={len(cats)}, pendientes={len(pendientes)})")
        return 0, 0

    # Textos unicos: 13.000 procesos son muchos menos objetos distintos, y cada
    # embedding se paga.
    textos = {}
    for ocid, objeto in pendientes:
        textos.setdefault(normalizar_texto(objeto), []).append(ocid)
    unicos = [t for t in textos if t]
    print(f"  {len(pendientes):,} procesos sin categoria · {len(unicos):,} textos unicos "
          f"· {len(cats):,} categorias")

    # Nombre Y descripcion oficial: el rotulo solo no se parece a un objeto contractual.
    V = np.asarray(embeber([f"{c[1]}. {c[3]}" for c in cats]), dtype="float32")
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    T = np.asarray(embeber(unicos), dtype="float32")
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9

    S = T @ V.T
    mejor = S.argmax(axis=1)
    parecido = S.max(axis=1)

    # La distribucion ANTES de aplicar el umbral. La primera vez se eligio 0,55 a ojo y
    # dejo fuera al 86%: un umbral se mide, no se intuye.
    cortes = [0.35, 0.45, 0.55, 0.65, 0.75]
    print("  parecido con la mejor categoria:")
    for c in cortes:
        print(f"    >= {c}: {int((parecido >= c).sum()):,} textos "
              f"({(parecido >= c).mean():.0%})")

    if seco:
        # Muestras por banda. La distribucion dice CUANTOS entran; solo mirar los
        # emparejamientos dice si son correctos, que es la pregunta. Elegir el umbral
        # por el porcentaje seria repetir el error de elegirlo por intuicion.
        import random

        rnd = random.Random(7)
        for bajo, alto in ((0.35, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 1.01)):
            indices = [i for i in range(len(unicos))
                       if bajo <= parecido[i] < alto]
            print(f"
  --- parecido {bajo}-{alto}: {len(indices):,} textos ---")
            for i in rnd.sample(indices, min(6, len(indices))):
                print(f"    [{parecido[i]:.2f}] {unicos[i][:78]}")
                print(f"           -> {cats[int(mejor[i])][1]}")
        return 0, len(unicos)

    asignaciones = []
    flojos = 0
    for i, texto in enumerate(unicos):
        if parecido[i] < umbral:
            flojos += 1
            continue
        cid = cats[int(mejor[i])][0]
        for ocid in textos[texto]:
            asignaciones.append((ocid, cid))

    print(f"  por debajo del umbral {umbral}: {flojos:,} textos se quedan sin categoria")

    if not asignaciones:
        return 0, 0
    with con.cursor() as cur:
        cur.execute("create temp table cercania_tmp (ocid text primary key, "
                    "categoria_id integer) on commit drop")
        with cur.copy("copy cercania_tmp (ocid, categoria_id) from stdin") as cp:
            for fila in asignaciones:
                cp.write_row(fila)
        cur.execute("""
            update proceso_resumen p set categoria_id = c.categoria_id
              from cercania_tmp c
             where p.ocid = c.ocid and p.categoria_id is null
        """)
        n = cur.rowcount
    con.commit()
    return n, len(unicos)

if __name__ == "__main__":
    raise SystemExit(main())
