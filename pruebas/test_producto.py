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


# --- D-045: el arbol CPC oficial sustituyo a la taxonomia del LLM ----------------

def test_todo_proceso_con_cpc_engancha_al_arbol(con):
    """La invariante aritmética: si un proceso trae CPC, su nodo es una consecuencia
    del código (subclase, o clase si la subclase no existe). El 0,5% que no engancha
    es el cubo «sin clasificar», visible en /mercado — pero no puede crecer en
    silencio."""
    total = _uno(con, "select count(*) from proceso_resumen where cpc is not null")
    sin_nodo = _uno(con, "select count(*) from proceso_resumen "
                         "where cpc is not null and cpc_nodo is null")
    assert sin_nodo / max(total, 1) < 0.01, (
        f"{sin_nodo:,} de {total:,} procesos con CPC no enganchan al árbol. "
        f"O la fuente cambió de códigos o cpc_nivel está incompleto (D-045)."
    )


def test_los_abiertos_con_items_tienen_cpc(con):
    """El radar depende de esto: los abiertos toman su CPC de sus propios ítems
    (0036). Si la función deja de correr, la etiqueta desaparece sin error."""
    con_items = _uno(con, """
        select count(distinct i.ocid) from proceso_item i
        join proceso_resumen p using (ocid)
        where i.cpc is not null and p.estado in ('abierto', 'planificacion')
    """)
    if con_items < 20:
        pytest.skip("casi ningún abierto con ítems ahora mismo")
    clasificados = _uno(con, """
        select count(distinct i.ocid) from proceso_item i
        join proceso_resumen p using (ocid)
        where i.cpc is not null and p.estado in ('abierto', 'planificacion')
          and p.cpc is not null
    """)
    assert clasificados / con_items > 0.9, (
        f"solo {clasificados} de {con_items} abiertos con ítems tienen CPC de "
        f"cabecera: `asignar_cpc_desde_items()` no corre tras la ingesta."
    )


# --- la función que se cobra ----------------------------------------------------

def test_los_compradores_de_una_categoria_existen(con):
    """La consulta central del producto: qué entidades compran una categoría dada.
    Si esto devuelve vacío, no hay compradores huérfanos ni benchmark que valgan."""
    with con.cursor() as cur:
        cur.execute("""
            select n.nombre, count(distinct p.comprador_ruc) compradores
            from proceso_resumen p
            join cpc_nivel n on n.codigo = p.cpc_nodo
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


# --- D-027: el tramo salia de un anio a medias ---------------------------------

def test_el_segmento_objetivo_tiene_el_tamano_esperado(con):
    """El segmento objetivo son ~6.700 empresas entre 100 K y 2 M (D-004). Es el eje del
    modelo de negocio y la aplicación filtra por él.

    **Con su ventana**, como toda cifra de este proyecto (D-019): las 6.700 son las
    empresas ACTIVAS en el último año completo, no las que alguna vez estuvieron en esa
    banda en once años — que son 17.347 y no son mercado direccionable, porque una
    empresa que dejó de contratar en 2017 no compra una suscripción.

    Calcular el tramo sobre el año en curso —que va por agosto— dejaba el segmento en
    2.694: más de la mitad fuera de su propio segmento, sin ningún error. Ver D-027."""
    n = _uno(con, """
        with base as (
            select max(anio) as anio from entidad_ano
            where rol='proveedor' and anio < extract(year from current_date)
        )
        select count(*)
        from entidad e
        join entidad_ano ea on ea.ruc = e.ruc and ea.rol = 'proveedor'
        join base b on ea.anio = b.anio
        where e.tramo in ('100-500K','500K-2M')
    """)
    assert 4_500 <= n <= 9_000, (
        f"el segmento objetivo activo tiene {n:,} empresas; se esperan unas 6.700. "
        f"Si es la mitad, el tramo se está calculando sobre el año en curso (D-027)."
    )


def test_ningun_proveedor_grande_cae_en_un_tramo_pequeno(con):
    """Contraste directo: quien facturó más de 2 M en el último año completo no puede
    estar en un tramo por debajo de 2 M."""
    mal = _uno(con, """
        with base as (
            select max(anio) as anio from entidad_ano
            where rol='proveedor' and anio < extract(year from current_date)
        )
        select count(*)
        from entidad e
        join entidad_ano ea on ea.ruc = e.ruc and ea.rol='proveedor'
        join base b on ea.anio = b.anio
        where ea.monto >= 2000000
          and e.tramo in ('<5K','5-25K','25-100K','100-500K','500K-2M')
    """)
    assert mal == 0, (
        f"{mal} proveedores facturaron más de 2 M en el último año completo y están "
        f"clasificados por debajo. El tramo no sale del año completo (D-027)."
    )


# --- la ficha de proveedor (migracion 0010) ------------------------------------

def test_la_ficha_de_proveedor_devuelve_datos(con):
    """La ficha es la pantalla que se indexa: 77.693 URLs con nombre de empresa real.
    Una vista que existe y devuelve cero filas se despliega en verde."""
    n = _uno(con, "select count(*) from v_proveedor")
    assert n > 15_000, f"v_proveedor devuelve {n} filas; se esperan decenas de miles"

    completas = _uno(con, """
        select count(*) from v_proveedor
        where monto_base > 0 and nombre is not null and tramo is not null
    """)
    assert completas / n > 0.9, (
        f"solo {completas} de {n} fichas tienen monto, nombre y tramo. "
        f"Una ficha sin cifras no sirve como canal de adquisición."
    )


def test_la_ficha_no_expone_personas_naturales(con):
    """Invariante 9: el RUC de persona natural contiene la cédula. Sin ficha, sin ruta,
    sin indexar. Se excluyen en la vista y no en el componente."""
    n = _uno(con, """
        select count(*) from v_proveedor v
        join entidad e on e.ruc = v.ruc
        where e.es_persona_natural
    """)
    assert n == 0, f"{n} personas naturales tienen ficha pública. Rompe el invariante 9."


def test_el_puesto_en_el_tramo_es_coherente(con):
    """El puesto se muestra como «412 de 5.928 en su tramo». Si el puesto supera al
    total, la cifra que ve el cliente es absurda."""
    mal = _uno(con,
               "select count(*) from v_proveedor where puesto_tramo > n_tramo")
    assert mal == 0, f"{mal} fichas tienen un puesto mayor que el tamaño de su tramo"


def test_los_compradores_huerfanos_no_incluyen_a_los_propios(con):
    """La cifra que engancha: «hay N entidades comprando lo que usted vende y ninguna le
    ha comprado». Si incluye a sus propios clientes, la promesa es falsa."""
    fila = _uno(con, "select count(*) from v_proveedor_huerfanos where n_huerfanos > 0")
    assert fila and fila > 1_000, (
        f"solo {fila} proveedores tienen compradores huérfanos; se esperan miles"
    )


def test_casi_ninguna_ficha_sale_vacia(con):
    """Con un único año de referencia para todos, 14.593 de 21.132 fichas —el 69%— salían
    con guiones en las cuatro cifras de cabecera. No dio ningún error: la vista existía,
    devolvía 21.132 filas y la migración aplicó en verde.

    Cada proveedor trae ahora su propio último año completo. Ver la 0011."""
    n = _uno(con, "select count(*) from v_proveedor")
    vacias = _uno(con, "select count(*) from v_proveedor where monto_base is null")
    assert vacias / n < 0.05, (
        f"{vacias:,} de {n:,} fichas ({vacias / n:.0%}) no tienen ni una cifra de "
        f"cabecera. El año base debe ser el de cada proveedor, no uno global."
    )


def test_solo_los_activos_tienen_puesto(con):
    """Comparar a una empresa que dejó de contratar en 2019 contra la cohorte de 2025 da
    un número con aspecto de dato y sin significado."""
    mal = _uno(con,
               "select count(*) from v_proveedor where not activo and puesto_tramo is not null")
    assert mal == 0, f"{mal} fichas inactivas traen puesto en el tramo actual"


def test_la_ficha_de_comprador_devuelve_datos(con):
    """El espejo de la de proveedor, sin muro: quien compra no paga, atrae. Una vista que
    existe y devuelve cero filas se despliega en verde."""
    n = _uno(con, "select count(*) from v_comprador")
    assert n > 3_000, f"v_comprador devuelve {n} filas; se esperan miles de entidades"

    vacias = _uno(con, "select count(*) from v_comprador where monto_base is null")
    assert vacias / n < 0.05, (
        f"{vacias:,} de {n:,} fichas de comprador no tienen cifras de cabecera. "
        f"El año base debe ser el de cada entidad, no uno global (ver la 0011)."
    )


def test_la_ficha_de_comprador_no_expone_personas_naturales(con):
    """Invariante 9, igual que en la de proveedor."""
    n = _uno(con, """
        select count(*) from v_comprador v
        join entidad e on e.ruc = v.ruc where e.es_persona_natural
    """)
    assert n == 0, f"{n} personas naturales tienen ficha de comprador"


# --- D-031: el radar salía sin objeto contractual --------------------------------

def test_los_procesos_en_planificacion_dicen_que_se_compra(con):
    """13.176 de 13.176 procesos en planificación —el 87% del radar— tenían el objeto
    vacío. No era la fuente: `planning.rationale` viene poblado al 100%, y la ingesta
    solo miraba `tender.description`, que en esa fase no existe todavía.

    Una oportunidad sin decir qué se compra no es una oportunidad. Ver D-031."""
    total = _uno(con, "select count(*) from proceso_resumen where estado='planificacion'")
    if not total:
        pytest.skip("sin procesos en planificación")
    con_objeto = _uno(
        con,
        "select count(*) from proceso_resumen "
        "where estado='planificacion' and objeto is not null and length(objeto) > 5",
    )
    assert con_objeto / total > 0.9, (
        f"solo {con_objeto:,} de {total:,} procesos en planificación dicen qué se "
        f"compra. El objeto sale de planning.rationale (D-031)."
    )


def test_el_objeto_en_planificacion_no_es_el_codigo_del_expediente(con):
    """La misma trampa de D-016 por otra puerta: si `title` gana a `rationale`, el radar
    vuelve a mostrar códigos donde debería decir qué se compra."""
    parecen_codigo = _uno(
        con,
        r"select count(*) from proceso_resumen where estado='planificacion' "
        r"and objeto is not null and (objeto ~ '^[A-Z0-9]+-[A-Z0-9-]+$' or objeto !~ ' ')",
    )
    total = _uno(con, "select count(*) from proceso_resumen "
                      "where estado='planificacion' and objeto is not null")
    if not total:
        pytest.skip("sin objetos en planificación")
    assert parecen_codigo / total < 0.2, (
        f"{parecen_codigo:,} de {total:,} objetos en planificación parecen códigos de "
        f"expediente: `rationale` debe ir antes que `title` (D-031)."
    )


# --- el mercado por categoría (migración 0017) ----------------------------------

def test_el_mercado_por_categoria_devuelve_datos(con):
    """Es la antesala del benchmark y el destino de los enlaces de categoría. Una vista
    que existe y devuelve cero filas se despliega en verde."""
    n = _uno(con, "select count(*) from mercado_nodo where nivel = 5 and n_procesos > 0")
    assert n > 500, f"solo {n} subclases con actividad; se esperan cientos (había 921)"

    completas = _uno(con, "select count(*) from mercado_nodo "
                          "where nivel = 5 and monto > 0 and n_contratistas > 0")
    assert completas / n > 0.5, (
        f"solo {completas} de {n} subclases activas tienen monto y contratistas."
    )


def test_ningun_mercado_supera_una_magnitud_imposible(con):
    """La regla que faltaba cuando `mercado_cpc_prov` publicó 8,1 billones de dólares
    para un CPC (D-033): una cifra agregada se comprueba contra una magnitud conocida
    del mundo, no solo contra su propia forma.

    La contratación pública entera del Ecuador ronda los 7.000 millones al año, y esta
    ventana son dos años."""
    peor = _uno(con, "select max(monto) from mercado_nodo where nivel = 5")
    assert peor is None or peor < 5e9, (
        f"un solo mercado da {peor:,.0f} USD en 24 meses. Es más que toda la "
        f"contratación pública del país en ese periodo: revisa el cálculo."
    )


def test_el_mercado_no_expone_el_ruc_de_personas_naturales(con):
    """Invariante 9, también aquí: el listado de quién gana es la vista con más
    proveedores por pantalla de todo el producto."""
    n = _uno(con, """
        select count(*) from mercado_nodo_contratista c
        join entidad e on e.ruc = c.ruc
        where e.es_persona_natural
          and exists (select 1 from entidad_publica ep
                      where ep.ruc_visible = c.ruc and ep.ruc is not null)
    """)
    assert n == 0, f"{n} personas naturales con RUC visible en el listado de mercado"


# --- el muro, comprobado desde el otro lado -------------------------------------

def test_la_funcion_de_huerfanos_no_devuelve_nada_sin_plan(con):
    """La comprobación que importa: **que el muro cierre**, no que abra.

    `compradores_huerfanos` es `security invoker` y comprueba el plan dentro de la propia
    consulta. Ejecutada sin sesión —`auth.email()` es nulo— el `exists` falla y no sale
    ni una fila. Si esto devolviera algo, la función que se cobra sería gratuita para
    cualquiera con la clave anónima, que va incrustada en el navegador."""
    existe = _uno(con, "select count(*) from pg_proc where proname = 'compradores_huerfanos'")
    if not existe:
        pytest.skip("sin la migración 0019")

    ruc = _uno(con, """
        select proveedor_ruc from proceso_resumen
        where proveedor_ruc is not null and cpc_nodo is not null
        group by 1 order by count(*) desc limit 1
    """)
    n = _uno(con, "select count(*) from compradores_huerfanos(%s)", ruc)
    assert n == 0, (
        f"la función devolvió {n} filas sin sesión ni plan. El muro no cierra: "
        f"revisa el `exists` sobre suscriptor en la migración 0019."
    )


def test_el_alta_de_suscriptor_no_regala_plan(con):
    """Entrar es gratis y no da acceso a nada de pago. Si el disparador diera de alta en
    `profesional`, bastaría un correo válido para llevarse el producto entero.

    **Esta prueba nació mal y saltó en falso el mismo día.** Comprobaba la población:
    «no todos los suscriptores tienen plan de pago». Con un único suscriptor, que lo
    tenía legítimamente, la condición se cumplía y la alarma sonaba sin motivo — que es
    justo lo que la regla 5 de docs/metodo.md prohíbe, porque una alarma que salta sin
    razón entrena a ignorarla.

    Se comprueba el MECANISMO: qué plan asigna el disparador y qué dice el valor por
    omisión de la columna. Eso es invariante; la población cambia con cada venta."""
    cuerpo = _uno(con, """
        select pg_get_functiondef(oid) from pg_proc
        where proname = 'crear_suscriptor' limit 1
    """)
    if not cuerpo:
        pytest.skip("sin la migración 0018")
    assert "'gratuito'" in cuerpo, (
        "el disparador de alta no asigna plan 'gratuito': bastaría un correo válido "
        "para llevarse el producto entero"
    )
    assert "'profesional'" not in cuerpo and "'institucional'" not in cuerpo, (
        "el disparador de alta menciona un plan de pago"
    )

    por_omision = _uno(con, """
        select column_default from information_schema.columns
        where table_name = 'suscriptor' and column_name = 'plan'
    """)
    assert por_omision and "gratuito" in por_omision, (
        f"el valor por omisión de `plan` es {por_omision!r}: un insert que olvide la "
        f"columna regalaría el plan"
    )


def test_la_funcion_de_huerfanos_no_toca_tablas_revocadas(con):
    """La otra mitad de la comprobación, y la que faltaba.

    `compradores_huerfanos` es `security invoker` para que RLS siga mandando. Eso
    significa que solo puede leer lo que el rol `authenticated` puede leer — y `entidad`
    está **revocada** desde la 0007. Unirla contra `entidad` devolvía

        42501: permission denied for table entidad

    que con la clave anónima parecía el muro funcionando y no lo era: le habría pasado
    igual a un suscriptor de pago. La función que se cobra, rota para quien la paga, con
    un error que se leía como seguridad.

    **Una comprobación que da el resultado correcto por el motivo equivocado.** Por eso
    esto se verifica sobre el texto de la función y no sobre su salida: la salida es
    vacía en los dos casos."""
    cuerpo = _uno(con, """
        select pg_get_functiondef(oid) from pg_proc
        where proname = 'compradores_huerfanos' limit 1
    """)
    if not cuerpo:
        pytest.skip("sin la migración 0019")

    revocadas = ["entidad", "entidad_nombre", "hecho_mes"]
    for tabla in revocadas:
        import re
        assert not re.search(rf"\bjoin\s+{tabla}\b", cuerpo, re.I), (
            f"la función une contra `{tabla}`, que está revocada para `authenticated`. "
            f"Devolverá «permission denied» a quien paga. Usa la vista pública."
        )
    assert "entidad_publica" in cuerpo, (
        "la función debe leer entidades por `entidad_publica`, que enmascara el RUC de "
        "persona natural (invariante 9)"
    )


def test_el_indice_de_mercados_responde(con):
    """`/mercado` salió vacío en producción: la consulta del índice —ordenar 856
    categorías por monto— expiraba con `57014: statement timeout`.

    Filtrada por una categoría la misma vista respondía en 0,25 s; lo que no escala es
    listar. Al desplegar medí 1,25 s y lo di por bueno, que con el límite de sentencia en
    pocos segundos era el aviso de que quedaba un factor cuatro."""
    # La consulta exacta de la raíz del árbol: las secciones por monto.
    with con.cursor() as cur:
        cur.execute("""
            select codigo, nombre, n_procesos, monto, n_contratantes, n_contratistas
            from mercado_nodo where nivel in (0, 1) order by monto desc
        """)
        filas = cur.fetchall()
    assert len(filas) == 11, f"el índice devuelve {len(filas)} filas, no 11 (10 + sin clasificar)"
    assert filas[0][3] > 0, "la sección de mayor monto no tiene monto"


def test_el_resumen_de_mercados_no_esta_rancio(con):
    """Una vista materializada que nadie refresca miente en silencio: da las cifras del
    día anterior sin decir que son viejas. Se compara contra la fuente de la que sale."""
    vivas = _uno(con, "select count(distinct cpc_nodo) from proceso_resumen "
                      "where cpc_nodo is not null")
    activas = _uno(con, "select count(*) from mercado_nodo where nivel = 5 and n_procesos > 0")
    # El árbol usa el corte estadístico y los vivos incluyen el mes en curso: puede
    # haber algo menos en el árbol, nunca un orden de magnitud menos.
    assert activas >= vivas * 0.7, (
        f"el árbol tiene {activas} subclases activas y hay {vivas} con procesos: "
        f"faltan los `refresh materialized view` del árbol."
    )


# --- D-036: el radar mostraba procesos de hace un año como oportunidades ---------

def test_el_radar_no_muestra_lo_que_ya_no_se_puede_ofertar(con):
    """Lo reportó el cliente, dos veces. El radar mostraba 15.210 procesos y **el 78% no
    se podía ofertar**: 386 con fecha de cierre ya pasada y 11.407 sin cierre declarado y
    con más de un año de antigüedad — había procesos etiquetados «abierto» desde julio de
    2025.

    La etiqueta `tag` es la máquina de estados del proceso, pero la fuente no siempre
    publica el cierre, así que uno se queda en `abierto` para siempre aunque terminara
    hace un año. Ver D-036."""
    if not _uno(con, "select count(*) from v_radar"):
        pytest.skip("sin la migración 0024")

    cerrados = _uno(con, "select count(*) from v_radar where cierra < now()")
    assert cerrados == 0, (
        f"{cerrados} procesos del radar tienen fecha de cierre ya pasada. "
        f"Una oportunidad que no se puede ofertar no es una oportunidad."
    )

    viejos = _uno(con, """
        select count(*) from v_radar
        where cierra is null and desde_cuando < now() - interval '60 days'
    """)
    assert viejos == 0, (
        f"{viejos} procesos del radar llevan más de 60 días sin cierre declarado. "
        f"Medido: ningún proceso vive más de 45 días abierto."
    )


def test_la_cabecera_del_radar_cuadra_con_su_tabla(con):
    """El fallo que erosiona la confianza más rápido que un dato ausente: la cifra de
    arriba dice 15.210 y la tabla de abajo muestra 3.417.

    Pasó porque la regla vivía en la consulta de cada pantalla y el resumen se calculaba
    aparte. Ahora el resumen lee de la misma vista, y esta prueba lo fija."""
    if not _uno(con, "select count(*) from v_radar"):
        pytest.skip("sin la migración 0024")
    tabla = _uno(con, "select count(*) from v_radar")
    cabecera = _uno(con, "select procesos from v_radar_resumen")
    assert tabla == cabecera, (
        f"la cabecera dice {cabecera:,} y la tabla tiene {tabla:,}"
    )


# --- D-039: el benchmark publica solo lo que sostiene una afirmación -------------

def test_el_benchmark_solo_publica_lo_defendible(con):
    """`precio_cpc` tiene 10.424 filas y la razón p75/p25 **mediana es 9,6×**. Un tercio
    supera 20×.

    Publicar «la mediana es 118,83» cuando el rango intercuartil va de 4,79 a 1.318,55 no
    es informar: es dar una cifra que parece un precio y no lo es. Quien la use para
    ofertar pierde el contrato o pierde dinero, y en los dos casos por culpa nuestra.

    No es un defecto de cálculo: aunque el CPC tenga una sola descripción la razón sigue
    en 8,9×, porque la unidad declarada es ambigua en origen — «Unidad» puede ser una
    pastilla o una caja de cien."""
    if not _uno(con, "select count(*) from precio_cpc"):
        pytest.skip("sin benchmark poblado")

    mal = _uno(con, "select count(*) from v_benchmark where p75 / p25 > 5 or n < 10")
    assert mal == 0, (
        f"{mal} filas del benchmark superan 5× de rango intercuartil o no llegan a n=10. "
        f"Esas no son un precio, son un rango inútil."
    )

    filas = _uno(con, "select count(*) from v_benchmark")
    assert filas > 1_000, (
        f"el benchmark publicable tiene {filas} filas; se esperan ~1.900. Si cayó mucho, "
        f"revisa el cálculo antes de relajar el umbral."
    )


def test_la_cobertura_del_benchmark_es_publica_pero_el_precio_no(con):
    """La frontera exacta: **saber que existe un dato no es el dato**. La categoría puede
    decir «hay 12 productos con precio»; cuál es el precio se paga.

    Sin esto, `/mercado` ofrecería una puerta a una habitación vacía en el 40% de las
    categorías que no tienen ni un precio publicable."""
    cob = _uno(con, "select count(*) from v_benchmark_cobertura")
    assert cob > 300, f"solo {cob} categorías tienen precio publicable; se esperan ~498"


# --- D-046: los indices de tupla corrieron y nadie lo vio -------------------------

def test_los_rucs_de_hecho_mes_tienen_forma_de_ruc(con):
    """El 19-08-2026, quitar una columna de la tupla del resumen corrió los índices
    fijos de `a_hecho_mes`: el RUC del proveedor pasó a ser el referencial y 5.440
    proveedores llamados «694.0» nacieron en una noche, con la ingesta en verde.

    Medido antes de escribir esto: en 1,24 M de filas sanas el proveedor es SIEMPRE
    nulo o un RUC de 13 dígitos. Cero excepciones — la alarma no puede saltar en falso.
    """
    for campo in ("proveedor_ruc", "comprador_ruc"):
        raros = _uno(con, f"""
            select count(*) from hecho_mes
            where {campo} is not null and {campo} !~ '^[0-9]{{13}}$'
        """)
        assert raros == 0, (
            f"{raros:,} filas de hecho_mes con {campo} que no es un RUC de 13 dígitos. "
            f"Los índices de a_hecho_mes volvieron a desalinearse de COLUMNAS_RESUMEN "
            f"(D-046): revisa la tupla antes de recargar nada."
        )
