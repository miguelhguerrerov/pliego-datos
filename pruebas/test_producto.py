"""Las consultas que haría un usuario, como aserciones.

**Por qué existe.** Cuatro de los catorce fallos de la fase 1 no produjeron ningún error:
el trabajo terminó en verde, las 36 pruebas pasaron, y el dato estaba mal. Las pruebas
verificaban funciones; el fallo estaba en el resultado.

Una función que escribe `title` en la columna `objeto` funciona perfectamente. Lo que
falla es que `title` no es el objeto contractual. Solo se ve consultando los datos como
los consultaría un cliente. Ver docs/metodo.md §2.1.

Cada prueba de aquí corresponde a un fallo real que pasó desapercibido.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("psycopg", reason="sin controlador de Postgres")
if not os.environ.get("SUPABASE_DB_URL"):
    pytest.skip("sin SUPABASE_DB_URL", allow_module_level=True)

from carga import conexion  # noqa: E402


@pytest.fixture(scope="module")
def con():
    with conexion() as c:
        yield c


def _uno(con, sql, *args):
    with con.cursor() as cur:
        cur.execute(sql, args)
        f = cur.fetchone()
        return f[0] if f else None


# --- D-014: el radar cargaba sin montos ----------------------------------------

def test_el_radar_devuelve_oportunidades_con_monto(con):
    """Los procesos en planificación no tienen fila en `tender`: su presupuesto está en
    `planning.budget_amount`. Sin él, el radar muestra oportunidades sin la cifra que las
    hace accionables — y la ingesta termina en verde igualmente."""
    total = _uno(con, "select count(*) from proceso_resumen where estado='planificacion'")
    if not total:
        pytest.skip("sin procesos en planificación")
    con_monto = _uno(
        con,
        "select count(*) from proceso_resumen where estado='planificacion' and referencial > 0",
    )
    assert con_monto / total > 0.5, (
        f"solo {con_monto} de {total} procesos en planificación tienen monto. "
        f"Revisa que el referencial se tome de planning.budget_amount (D-014)."
    )


# --- D-016: `objeto` guardaba el código de expediente ---------------------------

def test_el_objeto_contractual_no_es_un_codigo(con):
    """`tender.title` es el código del expediente —MCO-GADMAA-2024-001-50459— y
    `tender.description` es lo que se compra. Guardar el primero deja el buscador
    indexando códigos: el campo se puebla al 100% y no sirve para nada."""
    total = _uno(con, "select count(*) from proceso_resumen where objeto is not null")
    if not total:
        pytest.skip("sin objetos cargados")

    # Un objeto real tiene palabras; un código, guiones y mayúsculas.
    parecen_codigo = _uno(
        con,
        r"select count(*) from proceso_resumen "
        r"where objeto ~ '^[A-Z0-9]+-[A-Z0-9-]+$' or objeto !~ ' '",
    )
    assert parecen_codigo / total < 0.2, (
        f"{parecen_codigo} de {total} objetos parecen códigos de expediente. "
        f"El objeto se toma de description, no de title (D-016)."
    )

    # Y tiene que repetirse: 2.786 textos únicos en 17.477 procesos.
    unicos = _uno(con, "select count(distinct objeto) from proceso_resumen where objeto is not null")
    assert unicos / total < 0.6, (
        f"{unicos} objetos únicos sobre {total} procesos: demasiada variedad para ser "
        f"descripciones de compra. Probablemente son identificadores (D-016)."
    )


# --- D-021: categorías duplicadas ----------------------------------------------

def test_las_categorias_no_estan_duplicadas(con):
    """400 grupos daban solo 257 nombres distintos: «Material de oficina» partido en
    siete. El benchmark repartido entre siete da medianas sobre un séptimo de las
    observaciones, y el umbral de n<5 empieza a ocultar categorías con miles de procesos."""
    total = _uno(con, "select count(*) from categoria")
    if not total:
        pytest.skip("sin taxonomía construida")
    duplicados = _uno(
        con, "select count(*) from (select nombre from categoria group by 1 having count(*) > 1) x"
    )
    assert duplicados == 0, (
        f"{duplicados} nombres de categoría aparecen más de una vez. "
        f"Ejecuta `clasifica.py --fusionar` (D-021)."
    )


def test_ninguna_categoria_huerfana(con):
    """Un proceso apuntando a una categoría que ya no existe queda invisible en
    cualquier filtro por categoría."""
    huerfanos = _uno(
        con,
        "select count(*) from proceso_resumen p where p.categoria_id is not null "
        "and not exists (select 1 from categoria c where c.id = p.categoria_id)",
    )
    assert huerfanos == 0, f"{huerfanos} procesos apuntan a una categoría inexistente"


# --- D-022: la ingesta diaria descategorizaba el radar --------------------------

def test_los_meses_del_radar_estan_clasificados(con):
    """La ingesta hace delete+copy del mes: las filas recargadas entran sin categoría.
    Como el trabajo diario recarga el mes en curso y el anterior, el radar se
    descategorizaba cada mañana — sin ningún error visible."""
    if not _uno(con, "select count(*) from categoria"):
        pytest.skip("sin taxonomía construida")

    total = _uno(
        con,
        "select count(*) from proceso_resumen where objeto is not null "
        "and fecha >= current_date - interval '60 days'",
    )
    if not total:
        pytest.skip("sin procesos recientes")
    clasificados = _uno(
        con,
        "select count(*) from proceso_resumen where objeto is not null "
        "and categoria_id is not null and fecha >= current_date - interval '60 days'",
    )
    assert clasificados / total > 0.7, (
        f"solo {clasificados} de {total} procesos de los últimos 60 días tienen "
        f"categoría. El paso `clasifica.py --pendientes` debe correr tras la ingesta "
        f"diaria (D-022)."
    )


# --- la función que se cobra ----------------------------------------------------

def test_los_compradores_de_una_categoria_existen(con):
    """La consulta central del producto: qué entidades compran una categoría dada.
    Si esto devuelve vacío, no hay compradores huérfanos ni benchmark que valgan."""
    if not _uno(con, "select count(*) from categoria"):
        pytest.skip("sin taxonomía construida")

    with con.cursor() as cur:
        cur.execute("""
            select c.nombre, count(distinct p.comprador_ruc) compradores
            from proceso_resumen p
            join categoria c on c.id = p.categoria_id
            where p.adjudicado > 0
            group by 1 order by 2 desc limit 1
        """)
        fila = cur.fetchone()
    assert fila and fila[1] > 10, (
        "la categoría más comprada no llega a diez compradores distintos: "
        "algo falla en la clasificación o en el enlace con entidad"
    )


def test_la_tesis_del_producto_se_sostiene(con):
    """Crecer es diversificar compradores. Si esa escalada desaparece, la propuesta de
    valor deja de tener respaldo y hay que enterarse antes que un cliente."""
    with con.cursor() as cur:
        cur.execute("""
            select e.tramo, round(avg(ea.n_contrapartes), 2)::float
            from entidad_ano ea join entidad e on e.ruc = ea.ruc
            where ea.rol = 'proveedor' and e.tramo in ('25-100K', '500K-2M')
              and ea.anio = (select max(anio) from entidad_ano)
            group by 1
        """)
        m = dict(cur.fetchall())
    if len(m) < 2:
        pytest.skip("sin agregados suficientes")
    assert m["500K-2M"] > m["25-100K"] * 2, (
        f"los proveedores de 500K-2M trabajan con {m['500K-2M']} compradores y los de "
        f"25-100K con {m['25-100K']}: la escalada que sostiene la propuesta de valor "
        f"no aparece en los datos"
    )
