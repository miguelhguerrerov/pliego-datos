"""La taxonomía sale del CPC de la fuente, no de agrupar texto.

    python src/taxonomia.py --seco      # construye y muestra, sin escribir
    python src/taxonomia.py             # construye, bautiza y sustituye la taxonomía

**Por qué esto reemplaza a `clasifica.py` como fuente de categorías.**

La primera taxonomía se construyó agrupando embeddings del objeto contractual y pidiendo
a un modelo que bautizara cada grupo. Medido sobre las 242 categorías resultantes:

- «oficina» quedó repartido en **12 categorías y 74 209 procesos**: Material, Artículos,
  Productos, Utensilios, Papel, Archivador, Goma de oficina.
- «medicamento», en **15 categorías**.
- Duplicados por mayúscula y plural: «Equipo médico», «Equipo Médico», «Equipos médicos».
- Y una categoría con 4 308 procesos llamada literalmente **«Medicamento antiviral y
  antibiótico no, es más genérico: Med»** — el razonamiento del modelo, truncado a 60
  caracteres, publicado como nombre de categoría.

Fusionar por parecido de nombres (D-021) fue un parche: no puede funcionar, porque nada
garantizaba que dos grupos de lo mismo recibieran el mismo nombre, y «Papel de oficina» y
«Material de oficina» son nombres distintos de cosas que a veces son la misma.

**La fuente ya trae una taxonomía oficial y no la estábamos usando.** Medido contra la
fuente: el **100%** de los procesos con ítems trae `classification.id` —el CPC— con su
descripción oficial en español. Es jerárquica por truncamiento del código, es estable
entre recargas sin depender de una semilla, y `precio_cpc` ya está diseñada con ella
como clave. Ver docs/decisiones.md D-030.

**Dos niveles, deliberadamente distintos:**

- `categoria` agrupa por **CPC de 5 dígitos** —la subclase, ~350 grupos—. Es el nivel de
  navegación: lo que se lista, se filtra y se enlaza.
- `precio_cpc` sigue usando el **CPC completo**, de 8 a 12 dígitos. Comparar precios
  exige el producto exacto: «Amoxicilina 500 mg, caja x blíster», no «medicamentos».
  Agrupar el precio al nivel de navegación sería comparar peras con manzanas y publicar
  la mezcla como si fuera un mercado.

Al modelo solo se le pide **acortar** el nombre oficial de cada grupo, con la descripción
delante. Es un trabajo acotado —unos 350 nombres, una vez— y **con la salida validada**:
lo que no pasa la validación no se publica, se cae a la descripción oficial recortada.
La categoría de la basura de arriba no habría pasado.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

NIVEL = 5              # dígitos de CPC que definen una categoría: la subclase
LARGO_MINIMO = 3       # un CPC más corto que esto no identifica nada
MUESTRA_DESCRIPCIONES = 10   # descripciones oficiales que ve el modelo por grupo
LARGO_NOMBRE = 48


# --- el nivel de agrupación -----------------------------------------------------

def grupo_de(cpc: str | None) -> str | None:
    """La subclase CPC de un código. Devuelve None si el código no sirve.

    Los códigos de la fuente van de 8 a 12 dígitos: los 5 primeros son la subclase de la
    CPC internacional y el resto es detalle nacional del Ecuador.
    """
    if not cpc:
        return None
    limpio = re.sub(r"\D", "", str(cpc))
    if len(limpio) < LARGO_MINIMO:
        return None
    return limpio[:NIVEL]


def cpc_dominante(items: list[dict]) -> dict[str, tuple[str, float]]:
    """El CPC de cada proceso: el que concentra más monto entre sus ítems.

    Un proceso puede tener ítems de varios CPC —una compra de insumos de oficina lleva
    papel y tóner—. Se toma el dominante **por monto y no por número de líneas**: cien
    líneas de clips no definen una compra que es de computadoras.

    Se prefieren los ítems de `award` sobre los de `tender`: son los efectivamente
    adjudicados. Si un proceso tiene ambos, los de tender ni se miran.
    """
    por_ocid: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: {"award": defaultdict(float), "tender": defaultdict(float)}
    )
    for it in items:
        ocid, cpc = it.get("ocid"), it.get("cpc")
        if not ocid or not cpc:
            continue
        cantidad = it.get("cantidad") or 0
        precio = it.get("precio_unitario") or 0
        # Sin monto la línea sigue contando: un ítem sin precio es igualmente una
        # declaración de qué se compra. Pesa lo mínimo para no ganarle a uno con monto.
        monto = float(cantidad) * float(precio) or 1e-6
        origen = "award" if it.get("origen") == "award" else "tender"
        por_ocid[ocid][origen][str(cpc)] += monto

    salida: dict[str, tuple[str, float]] = {}
    for ocid, origenes in por_ocid.items():
        montos = origenes["award"] or origenes["tender"]
        if not montos:
            continue
        cpc, monto = max(montos.items(), key=lambda kv: kv[1])
        salida[ocid] = (cpc, monto)
    return salida


# --- los nombres ----------------------------------------------------------------

RUIDO = re.compile(
    r"(?i)\b(n\.?c\.?p\.?|excepto|incluidas?|inclusive|estos servicios|los siguientes|"
    r"y otros|varios|otras?)\b"
)

# Frases que delatan que el modelo respondió en vez de nombrar. La taxonomía anterior
# publicó «Medicamento antiviral y antibiótico no, es más genérico: Med» con 4.308
# procesos detrás; nadie miraba la salida.
DELATORES = re.compile(
    r"(?i)(:|\bes m[aá]s\b|\bes un\b|\bcategor[ií]a\b|\bnombre\b|\bser[ií]a\b|"
    r"\bcreo\b|\bpodr[ií]a\b|\bmejor\b|^\W|\bno,)"
)


def validar_nombre(nombre: str) -> bool:
    """Un nombre de categoría es un sustantivo corto, no una respuesta.

    Esta comprobación es la que faltaba: sin ella el producto publicó el razonamiento
    del modelo como nombre de una categoría con 4.308 procesos. Ver D-030.
    """
    if not nombre:
        return False
    n = nombre.strip()
    if not (3 <= len(n) <= LARGO_NOMBRE):
        return False
    if not (1 <= len(n.split()) <= 5):
        return False
    if DELATORES.search(n):
        return False
    if not n[0].isupper():
        return False
    if any(ch.isdigit() for ch in n):
        return False
    return True


def nombre_de_respaldo(descripciones: Counter) -> str:
    """Cuando el modelo no da un nombre válido, manda la descripción oficial.

    Recortada y en formato de título, pero **de la fuente**: es preferible un nombre
    largo y burocrático a uno inventado que nadie ha comprobado.
    """
    if not descripciones:
        return "Sin clasificar"
    cruda = descripciones.most_common(1)[0][0]
    limpia = RUIDO.sub("", cruda)
    limpia = re.sub(r"[.,;:].*$", "", limpia).strip()
    limpia = re.sub(r"\s+", " ", limpia)
    if not limpia:
        limpia = cruda[:LARGO_NOMBRE]
    if limpia.isupper():
        limpia = limpia.capitalize()
    return limpia[:LARGO_NOMBRE].strip()


def _clave_normalizada(nombre: str) -> str:
    """Para detectar duplicados que solo difieren en acentos, mayúsculas o plural.

    «Equipo médico», «Equipo Médico» y «Equipos médicos» convivieron en la taxonomía
    anterior porque el parecido de embeddings no llegaba al umbral. Aquí no hace falta
    un modelo: es comparación de cadenas.
    """
    s = unicodedata.normalize("NFD", nombre.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    vacias = {"de", "del", "la", "el", "los", "las", "y", "para", "en", "con", "a"}
    palabras = [p for p in re.findall(r"[a-z]+", s) if p not in vacias]
    singular = [
        p[:-2] if p.endswith("es") and len(p) > 5 else (p[:-1] if p.endswith("s") and len(p) > 4 else p)
        for p in palabras
    ]
    return " ".join(sorted(singular))


def bautizar(grupo: str, descripciones: Counter) -> str:
    """Pide al modelo un nombre corto, y comprueba lo que devuelve."""
    from clasifica import _peticion

    muestra = "\n".join(
        f"- {d[:100]}" for d, _ in descripciones.most_common(MUESTRA_DESCRIPCIONES)
    )
    try:
        r = _peticion("/chat/completions", {
            "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "max_tokens": 16,
            "temperature": 0,
            "messages": [{
                "role": "user",
                "content": (
                    "Estas son las descripciones oficiales de los productos y servicios "
                    f"de la subclase CPC {grupo} en las compras públicas del Ecuador:\n\n"
                    + muestra + "\n\n"
                    "Escribe un nombre corto para esta categoría, de una a cuatro "
                    "palabras, en español, empezando por mayúscula. Responde SOLO con el "
                    "nombre: sin comillas, sin dos puntos, sin explicación y sin cifras."
                ),
            }],
        })
        propuesto = r["choices"][0]["message"]["content"].strip().strip('".')
    except Exception as e:  # noqa: BLE001
        print(f"    {grupo}: el modelo falló ({e}); se usa la descripción oficial")
        return nombre_de_respaldo(descripciones)

    if validar_nombre(propuesto):
        return propuesto
    print(f"    {grupo}: nombre rechazado {propuesto!r}; se usa la descripción oficial")
    return nombre_de_respaldo(descripciones)


# --- construcción ---------------------------------------------------------------

def agrupar_items(items: list[dict]) -> tuple[dict[str, Counter], dict[str, str]]:
    """Devuelve (descripciones por subclase, subclase de cada ocid)."""
    descripciones: dict[str, Counter] = defaultdict(Counter)
    for it in items:
        g = grupo_de(it.get("cpc"))
        if g and it.get("descripcion"):
            descripciones[g][str(it["descripcion"]).strip()] += 1

    por_ocid = {}
    for ocid, (cpc, _monto) in cpc_dominante(items).items():
        g = grupo_de(cpc)
        if g:
            por_ocid[ocid] = g
    return descripciones, por_ocid


def resolver_nombres(descripciones: dict[str, Counter], bautizador=bautizar,
                     ya_nombradas: dict[str, str] | None = None) -> dict[str, str]:
    """Un nombre por subclase, sin colisiones.

    Dos subclases distintas pueden recibir el mismo nombre corto —«Reactivos» para dos
    grupos de química clínica—. Eso volvería a partir el mercado en dos categorías con el
    mismo rótulo, que es justo el defecto que este módulo existe para eliminar. Cuando
    pasa, se desambigua con el código, que es lo único que de verdad las distingue.
    """
    # Una categoria que ya tiene nombre lo conserva. Sin esto cada pasada gastaba 350
    # llamadas al modelo por gusto y, peor, el rotulo de una categoria podia cambiar bajo
    # los pies del usuario entre dos noches.
    ya_nombradas = ya_nombradas or {}
    orden = sorted(
        (g for g in descripciones if g not in ya_nombradas),
        key=lambda g: -sum(descripciones[g].values()),
    )
    if ya_nombradas:
        print(f"  {len(ya_nombradas):,} categorias conservan su nombre; "
              f"se nombran {len(orden):,} nuevas")

    # En paralelo: son ~350 llamadas independientes y en serie tardaban 35 minutos, que
    # es tiempo en el que algo se cae y hay que repetirlo entero. El orden del resultado
    # se conserva para que la desambiguacion sea determinista.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=8) as pool:
        propuestos = list(pool.map(lambda g: bautizador(g, descripciones[g]), orden))

    nombres: dict[str, str] = dict(ya_nombradas)
    vistos: dict[str, str] = {_clave_normalizada(n): g for g, n in ya_nombradas.items()}
    for grupo, nombre in zip(orden, propuestos):
        clave = _clave_normalizada(nombre)
        if clave in vistos:
            nombre = f"{nombre} ({grupo})"
        else:
            vistos[clave] = grupo
        nombres[grupo] = nombre
    return nombres


# --- escritura ------------------------------------------------------------------

def escribir(con, nombres: dict[str, str], por_ocid: dict[str, str],
             cpc_completo: dict[str, str]) -> tuple[int, int]:
    """Sustituye la taxonomía y recategoriza los procesos.

    La asignación va por tabla temporal y un solo `update ... from`: 280.020 procesos
    actualizados de uno en uno son media hora de ida y vuelta contra Supabase, y el
    trabajo de agregados corre en una ventana de minutos.
    """
    with con.cursor() as cur:
        # 0. La secuencia de `id`. La taxonomía anterior insertaba identificadores
        #    explícitos, así que la secuencia se quedó atrás y el primer insert sin `id`
        #    choca contra la clave primaria. No se ve venir: el error aparece al escribir,
        #    después de todo el trabajo.
        cur.execute("select setval(pg_get_serial_sequence('categoria','id'), "
                    "coalesce((select max(id) from categoria), 1))")

        # 1. Las categorías. Se conserva el nombre de las que ya existen: renombrar cada
        #    noche haría que la misma categoría cambiara de rótulo bajo los pies del
        #    usuario, y gastaría 350 llamadas al modelo por gusto.
        cur.execute("select cpc, id from categoria where cpc is not null")
        existentes = dict(cur.fetchall())

        nuevas = [(c, n) for c, n in nombres.items() if c not in existentes]
        if nuevas:
            cur.executemany(
                "insert into categoria (cpc, nombre, n_procesos) values (%s, %s, 0) "
                "on conflict (cpc) do nothing",
                nuevas,
            )
        cur.execute("select cpc, id from categoria where cpc is not null")
        id_de = dict(cur.fetchall())

        # 2. La asignación.
        cur.execute("create temp table asignacion_tmp "
                    "(ocid text primary key, cpc text, categoria_id integer) "
                    "on commit drop")
        filas = [
            (ocid, cpc_completo.get(ocid), id_de[grupo])
            for ocid, grupo in por_ocid.items() if grupo in id_de
        ]
        with cur.copy("copy asignacion_tmp (ocid, cpc, categoria_id) from stdin") as cp:
            for f in filas:
                cp.write_row(f)

        cur.execute("""
            update proceso_resumen p
               set cpc = a.cpc, categoria_id = a.categoria_id
              from asignacion_tmp a
             where p.ocid = a.ocid
               and (p.categoria_id is distinct from a.categoria_id
                    or p.cpc is distinct from a.cpc)
        """)
        actualizados = cur.rowcount

        # 3. El recuento que muestra el producto, y la limpieza de lo que quedó vacío.
        cur.execute("""
            update categoria c set n_procesos = coalesce(x.n, 0)
              from (select categoria_id, count(*) n from proceso_resumen
                     where categoria_id is not null group by 1) x
             where c.id = x.categoria_id
        """)
        cur.execute("update categoria set n_procesos = 0 where id not in "
                    "(select distinct categoria_id from proceso_resumen "
                    "  where categoria_id is not null)")
    con.commit()
    return len(id_de), actualizados


def main() -> int:
    p = argparse.ArgumentParser(description="Construye la taxonomía desde el CPC")
    p.add_argument("--seco", action="store_true", help="construye y muestra, sin escribir")
    p.add_argument("--sin-modelo", action="store_true",
                   help="nombra solo con la descripción oficial, sin llamar al modelo")
    args = p.parse_args()

    from precios import descargar_items, meses_de_la_ventana

    ventana = meses_de_la_ventana()
    print(f"ventana: {len(ventana)} meses")
    items = descargar_items(ventana)
    print(f"ítems leídos: {len(items):,}")

    descripciones, por_ocid = agrupar_items(items)
    cpc_completo = {o: c for o, (c, _) in cpc_dominante(items).items()}
    print(f"subclases CPC: {len(descripciones):,}  ·  procesos con categoría: {len(por_ocid):,}")

    # Las que ya tienen nombre se leen ANTES de nombrar: nombrar y descartar despues es
    # pagar 350 llamadas para tirarlas.
    ya = {}
    if not args.seco:
        from carga import conexion as _con
        with _con() as c, c.cursor() as cur:
            cur.execute("select cpc, nombre from categoria where cpc is not null")
            ya = dict(cur.fetchall())

    bautizador = (lambda g, d: nombre_de_respaldo(d)) if args.sin_modelo else bautizar
    nombres = resolver_nombres(descripciones, bautizador=bautizador, ya_nombradas=ya)

    grandes = sorted(descripciones, key=lambda g: -sum(descripciones[g].values()))
    print("\nlas 15 subclases con más ítems:")
    for g in grandes[:15]:
        print(f"  {g}  {sum(descripciones[g].values()):>7,} ítems  {nombres[g]}")

    if args.seco:
        return 0

    from carga import conexion

    with conexion() as con:
        n_cat, n_proc = escribir(con, nombres, por_ocid, cpc_completo)
        print(f"\ncategorías: {n_cat:,}  ·  procesos recategorizados: {n_proc:,}")

        # El referencial que el CSV no trae para subasta inversa: el 22,1% de los
        # procesos convocados salía sin cifra, y los ítems del JSON la recuperan.
        refs = referencial_de_items(items)
        n_ref = completar_referencial(con, refs)
        print(f"referencial reconstruido de ítems: {n_ref:,} procesos "
              f"(de {len(refs):,} calculables)")
    return 0




# --- el referencial que el CSV no trae ------------------------------------------

def referencial_de_items(items: list[dict]) -> dict[str, float]:
    """Monto convocado de cada proceso, reconstruido de sus ítems.

    **Por qué hace falta.** El CSV no trae `value_amount` para subasta inversa
    electrónica: medido en julio de 2026, **1 264 de 5 717 procesos convocados (22,1%)
    salían sin monto, y los 1 264 eran subasta inversa**. Ni uno de otro método.

    `CLAUDE.md` ya lo anotaba como «no calculable desde CSV» y ahí se quedó — pero sí es
    calculable desde el JSON, que ya descargamos y publicamos: cantidad × precio unitario
    de los ítems recupera **1 170 de los 1 264, el 92,6%**.

    Importa porque la subasta inversa es el método donde más compite el segmento
    objetivo, y una oportunidad sin cifra no es accionable.

    Solo ítems de `tender`: el referencial es lo que se convoca. Lo adjudicado ya viene
    de `awards` por la ruta CSV, y mezclarlos daría una cifra que no es ninguna de las dos.
    """
    total: dict[str, float] = defaultdict(float)
    for it in items:
        if it.get("origen") != "tender":
            continue
        ocid = it.get("ocid")
        cantidad = it.get("cantidad")
        precio = it.get("precio_unitario")
        if not ocid or not cantidad or not precio:
            continue
        try:
            total[ocid] += float(cantidad) * float(precio)
        except (TypeError, ValueError):
            continue
    return {o: round(v, 2) for o, v in total.items() if v > 0}


def completar_referencial(con, montos: dict[str, float]) -> int:
    """Rellena `referencial` SOLO donde falta. Nunca pisa un dato de la fuente.

    Si el CSV declaró un referencial, ese manda: es lo que la entidad publicó. Lo
    reconstruido es un respaldo para donde no hay nada, no una corrección.
    """
    if not montos:
        return 0
    with con.cursor() as cur:
        cur.execute("create temp table ref_tmp (ocid text primary key, monto numeric) "
                    "on commit drop")
        with cur.copy("copy ref_tmp (ocid, monto) from stdin") as cp:
            for ocid, monto in montos.items():
                cp.write_row((ocid, monto))
        cur.execute("""
            update proceso_resumen p
               set referencial = r.monto
              from ref_tmp r
             where p.ocid = r.ocid
               and p.referencial is null
        """)
        n = cur.rowcount
    con.commit()
    return n

if __name__ == "__main__":
    raise SystemExit(main())
