-- Pliego · esquema base
-- Invariante 5: toda la estructura vive aquí. Nada se crea desde el panel de Supabase.
-- Invariante 1: el detalle OCDS NO entra aquí. Solo agregados regenerables y datos de usuario.
-- Ver docs/agregados.md para el grano y el presupuesto en MB de cada tabla.

begin;

-- ---------------------------------------------------------------------------
-- Registro de cobertura. Consultable desde la aplicación, no escondido en un log:
-- es lo que impide presentar datos incompletos como completos.
-- ---------------------------------------------------------------------------
create table if not exists cobertura (
    anio         smallint not null,
    mes          smallint not null check (mes between 1 and 12),
    estado       text     not null check (estado in ('cargado','parcial','pendiente','degradado')),
    registros    integer,
    pct_cerrado  numeric(5,2),
    bytes_zip    integer,
    intentos     smallint,
    fecha_carga  timestamptz default now(),
    nota         text,
    primary key (anio, mes)
);

comment on table cobertura is
    'Qué meses están cargados y con qué calidad. La aplicación la muestra al usuario.';

-- ---------------------------------------------------------------------------
-- Entidades: compradores y proveedores unificados POR RUC, nunca por nombre.
-- ---------------------------------------------------------------------------
create table if not exists entidad (
    ruc                text primary key,
    nombre             text not null,
    tipo               text not null check (tipo in ('comprador','proveedor','ambos')),
    es_persona_natural boolean not null default false,
    es_publica         boolean not null default false,
    provincia          text,
    canton             text,
    tramo              text check (tramo in ('<5K','5-25K','25-100K','100-500K','500K-2M','2-10M','>10M')),
    activa_desde       date,
    activa_hasta       date
);

create index if not exists idx_entidad_tipo     on entidad (tipo);
create index if not exists idx_entidad_provincia on entidad (provincia);
create index if not exists idx_entidad_tramo    on entidad (tramo) where tramo is not null;

comment on column entidad.es_persona_natural is
    'El RUC de persona natural contiene la cédula: se enmascara al publicar. Ver docs/legal.md';

-- ---------------------------------------------------------------------------
-- Ventana de procesos (24 meses). Alimenta el radar y el buscador.
-- NO alimenta estadísticas: para eso está la ventana con 4 meses de retraso.
-- ---------------------------------------------------------------------------
create table if not exists proceso_resumen (
    ocid           text primary key,
    fecha          date not null,
    anio           smallint not null,
    mes            smallint not null,
    estado         text not null check (estado in ('planificacion','abierto','adjudicado','cerrado','desconocido')),
    metodo         text,
    cpc            text,
    categoria_id   integer,
    comprador_ruc  text,
    proveedor_ruc  text,
    referencial    numeric(16,2),
    adjudicado     numeric(16,2),
    provincia      text,
    objeto         text,
    cierra         date,
    objeto_ts      tsvector generated always as (to_tsvector('spanish', coalesce(objeto,''))) stored
);

create index if not exists idx_proceso_fecha     on proceso_resumen (fecha desc);
create index if not exists idx_proceso_estado    on proceso_resumen (estado) where estado in ('planificacion','abierto');
create index if not exists idx_proceso_comprador on proceso_resumen (comprador_ruc);
create index if not exists idx_proceso_proveedor on proceso_resumen (proveedor_ruc);
create index if not exists idx_proceso_categoria on proceso_resumen (categoria_id);
create index if not exists idx_proceso_ts        on proceso_resumen using gin (objeto_ts);

comment on table proceso_resumen is
    'Ventana de 24 meses. Al superar 420 MB de base, acortar a 18 (primera válvula de docs/agregados.md).';

-- ---------------------------------------------------------------------------
-- Tablas de usuario. NO son regenerables: son las que migran y las que se
-- exportan cada noche al repositorio privado (invariante 14).
-- Enlazadas por correo, NO por la UUID de auth.users (invariante 7).
-- ---------------------------------------------------------------------------
create table if not exists suscriptor (
    correo   text primary key,
    nombre   text,
    ruc      text,
    plan     text not null default 'gratuito' check (plan in ('gratuito','profesional','institucional')),
    alta     timestamptz not null default now(),
    estado   text not null default 'activo' check (estado in ('activo','pausado','baja'))
);

create table if not exists perfil (
    correo      text primary key references suscriptor(correo) on delete cascade,
    categorias  integer[] not null default '{}',
    provincias  text[]    not null default '{}',
    monto_min   numeric(16,2) not null default 0,
    frecuencia  text not null default 'semanal' check (frecuencia in ('diaria','semanal','ninguna'))
);

create table if not exists envio_log (
    id              bigserial primary key,
    correo          text not null,
    fecha           date not null,
    n_coincidencias integer not null default 0,
    resend_id       text,
    estado          text not null default 'enviado' check (estado in ('enviado','encolado','fallido')),
    unique (correo, fecha)
);

comment on table envio_log is
    'Registro propio de envíos: el de Resend caduca a los 30 días en el plan gratuito.';

create table if not exists lista_espera (
    correo        text primary key,
    ruc           text,
    categoria     text,
    acepta_precio boolean not null default false,
    origen        text,
    fecha         timestamptz not null default now()
);

comment on table lista_espera is
    'La columna acepta_precio ES la métrica del test de mercado. Ver docs/validacion.md';

-- ---------------------------------------------------------------------------
-- Vigilancia del presupuesto de 500 MB (invariante 2).
-- ---------------------------------------------------------------------------
create or replace view v_tamano_base as
select
    relname                                    as tabla,
    pg_total_relation_size(c.oid)              as bytes,
    round(pg_total_relation_size(c.oid) / 1048576.0, 1) as mb
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
order by pg_total_relation_size(c.oid) desc;

comment on view v_tamano_base is
    'Alarma a 420 MB, presupuesto duro 460. pruebas/test_presupuesto.py falla al superarlo.';

commit;
