-- Pliego · los cimientos del buscador
--
-- El buscador es la puerta de entrada: hay 21.132 fichas de proveedor y hasta ahora la
-- unica forma de llegar a una era teclear el RUC en la barra de direcciones. Tambien es
-- lo que indexan los buscadores externos, que es el canal de adquisicion entero.
--
-- Tres cosas medidas antes de escribir esto, no supuestas:
--
-- 1. **`v_proveedor` no aguanta un listado.** Calculaba las cifras de cabecera con
--    ventanas sobre las 264.276 filas de `entidad_ano`: 0,85 s por ficha suelta, y al
--    ordenar por monto —lo que hace cualquier lista de resultados— devolvia
--    «canceling statement due to statement timeout». Las cifras pasan a `entidad`, que
--    las calcula `agrega.py` una vez al dia. Cuesta ~2 MB de los 460.
--
-- 2. **Buscar por nombre eran 1,2 s de escaneo completo** de 77.693 filas. Indice
--    trigrama.
--
-- 3. **Buscar texto en `objeto` tardaba 3,2 s y en `objeto_ts` 0,23 s.** PostgREST
--    traduce un filtro sobre `objeto` a `to_tsvector(objeto) @@ ...`, que NO puede usar
--    el indice GIN, porque el indice esta sobre la columna generada `objeto_ts`
--    —`to_tsvector('spanish', ...)`— y para el planificador son expresiones distintas.
--    El indice existia desde la 0001 y no lo usaba nadie. La aplicacion debe consultar
--    `objeto_ts=wfts(spanish).<texto>`; queda anotado en las trampas de CLAUDE.md.
--
-- `activa_desde` y `activa_hasta` se declararon en la 0001 y nunca se poblaron: se
-- sustituyen por `primer_anio` y `ultimo_anio`, que es la precision que da la fuente.
-- Fingir el dia exacto seria inventarse una precision que no existe.

begin;

-- ---------------------------------------------------------------------------
-- 1. Las cifras de cabecera, precalculadas
-- ---------------------------------------------------------------------------
alter table entidad
    drop column if exists activa_desde,
    drop column if exists activa_hasta,
    add column if not exists anio_base        smallint,
    add column if not exists monto_base       numeric(18,2),
    add column if not exists procesos_base    integer,
    add column if not exists compradores_base integer,
    add column if not exists activo           boolean,
    add column if not exists monto_total      numeric(18,2),
    add column if not exists procesos_total   integer,
    add column if not exists primer_anio      smallint,
    add column if not exists ultimo_anio      smallint,
    add column if not exists anios_activo     smallint;

comment on column entidad.anio_base is
    'Ultimo anio COMPLETO de este proveedor. El anio en curso va a medias y clasificar '
    'con el subestimaba a 3.198 proveedores. Ver docs/decisiones.md D-027.';
comment on column entidad.activo is
    'Si su anio base es el ultimo cerrado del conjunto. Solo los activos reciben puesto: '
    'comparar a una empresa de 2019 con la cohorte de 2025 da un numero sin significado.';

-- Orden por tamano dentro de un tramo, que es como se listan los resultados.
create index if not exists idx_entidad_monto_base
    on entidad (tramo, monto_base desc) where monto_base is not null;

-- ---------------------------------------------------------------------------
-- 2. Busqueda por nombre sin escanear 77.693 filas
-- ---------------------------------------------------------------------------
create extension if not exists pg_trgm;

create index if not exists idx_entidad_nombre_trgm
    on entidad using gin (nombre gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- 3. La vista del buscador. Enmascara igual que `entidad_publica`: es la misma
--    frontera, y un buscador que devuelve el RUC completo de una persona natural
--    rompe el invariante 9 con mas alcance que una ficha suelta.
-- ---------------------------------------------------------------------------
create or replace view v_busqueda_entidad as
select
    case when es_persona_natural then null else ruc end as ruc,
    case when es_persona_natural
         then repeat('.', length(ruc) - 4) || right(ruc, 4)
         else ruc end                                   as ruc_visible,
    nombre,
    tipo,
    es_persona_natural,
    es_publica,
    provincia,
    tramo,
    anio_base,
    monto_base,
    procesos_base,
    compradores_base,
    activo,
    monto_total,
    primer_anio,
    ultimo_anio
from entidad;

comment on view v_busqueda_entidad is
    'Resultados del buscador. Enmascara el RUC de persona natural igual que '
    'entidad_publica: el acceso directo a `entidad` sigue revocado para anon.';

-- ---------------------------------------------------------------------------
-- 4. `v_proveedor` pasa a leer las cifras ya calculadas.
--    De 0,85 s a una lectura por clave primaria.
-- ---------------------------------------------------------------------------
drop view if exists v_proveedor;

create view v_proveedor as
with cohorte as (
    select e.tramo,
           e.ruc,
           rank() over (partition by e.tramo order by e.monto_base desc) as puesto_tramo,
           count(*) over (partition by e.tramo)                          as n_tramo
    from entidad e
    where e.activo and e.tramo is not null
)
select
    e.ruc, e.nombre, e.tipo, e.es_publica, e.provincia, e.canton, e.tramo,
    e.anio_base, e.activo,
    e.monto_base, e.procesos_base, e.compradores_base,
    c.puesto_tramo, c.n_tramo,
    e.monto_total, e.procesos_total, e.primer_anio, e.ultimo_anio, e.anios_activo
from entidad e
left join cohorte c on c.ruc = e.ruc
where e.tipo in ('proveedor', 'ambos')
  and not e.es_persona_natural;   -- invariante 9: sin ficha, sin ruta, sin indexar

comment on view v_proveedor is
    'Cabecera de la ficha de proveedor. Lee las cifras precalculadas de `entidad`; '
    'calcularlas al vuelo costaba 0,85 s por ficha y expiraba al ordenar.';

grant select on v_busqueda_entidad, v_proveedor to anon, authenticated;

commit;
