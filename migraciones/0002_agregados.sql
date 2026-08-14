-- Pliego · tablas agregadas
-- Ver docs/agregados.md para el grano y el presupuesto en MB de cada una.
-- Invariante 2: solo agregados regenerables. Se vacían y recargan enteras cada noche.

begin;

-- ---------------------------------------------------------------------------
-- Hechos por mes: la pieza que resuelve la tensión entre la ventana de 24 meses
-- de proceso_resumen y los once años que necesitan los agregados de proveedor.
--
-- Guarda solo las columnas que alimentan agregados, sin objeto ni ocid, para
-- TODOS los meses. Ver docs/decisiones.md D-015.
-- ---------------------------------------------------------------------------
create table if not exists hecho_mes (
    anio           smallint not null,
    mes            smallint not null,
    comprador_ruc  text,
    proveedor_ruc  text,
    metodo         text,
    n_procesos     integer  not null default 0,
    referencial    numeric(16,2),
    adjudicado     numeric(16,2),
    primary key (anio, mes, comprador_ruc, proveedor_ruc, metodo)
);

create index if not exists idx_hecho_anio      on hecho_mes (anio);
create index if not exists idx_hecho_proveedor on hecho_mes (proveedor_ruc) where proveedor_ruc is not null;
create index if not exists idx_hecho_comprador on hecho_mes (comprador_ruc) where comprador_ruc is not null;

comment on table hecho_mes is
    'Grano mínimo para agregados, once años. Sin objeto ni ocid: eso vive en Parquet.';

-- ---------------------------------------------------------------------------
-- Agregados de consulta
-- ---------------------------------------------------------------------------
create table if not exists entidad_ano (
    ruc            text not null,
    anio           smallint not null,
    rol            text not null check (rol in ('comprador','proveedor')),
    monto          numeric(18,2) not null default 0,
    n_procesos     integer not null default 0,
    n_contrapartes integer not null default 0,
    primary key (ruc, anio, rol)
);

comment on column entidad_ano.n_contrapartes is
    'La tesis del producto: crecer es diversificar compradores. Ver docs/propuesta-valor.md';

create table if not exists relacion (
    comprador_ruc text not null,
    proveedor_ruc text not null,
    anio          smallint not null,
    monto         numeric(18,2) not null default 0,
    n_procesos    integer not null default 0,
    primary key (comprador_ruc, proveedor_ruc, anio)
);

comment on table relacion is
    'Matriz que alimenta compradores huerfanos: entidades que compran la categoria del '
    'suscriptor y nunca le han adjudicado a el.';

create table if not exists baja_metodo (
    metodo        text not null,
    anio          smallint not null,
    n             integer not null,
    ratio_mediana numeric(6,4),
    ratio_p25     numeric(6,4),
    ratio_p75     numeric(6,4),
    primary key (metodo, anio)
);

comment on table baja_metodo is
    'Cuanto por debajo del referencial se adjudica. Medido 2024: seguros 0,863; '
    'licitacion 0,949; menor cuantia 1,000. Excluye los ultimos 4 meses.';

-- precio_cpc y mercado_cpc_prov necesitan los items, que solo vienen por la ruta
-- JSON y viven en Parquet. Se crean aqui para que el esquema este completo, y las
-- puebla agrega.py cuando la capa Parquet este publicada.
create table if not exists precio_cpc (
    cpc      text not null,
    anio     smallint not null,
    unidad   text not null default '',
    n        integer not null,
    p10      numeric(16,4),
    p25      numeric(16,4),
    mediana  numeric(16,4),
    p75      numeric(16,4),
    p90      numeric(16,4),
    minimo   numeric(16,4),
    maximo   numeric(16,4),
    primary key (cpc, anio, unidad)
);

create table if not exists mercado_cpc_prov (
    cpc            text not null,
    provincia      text not null default '',
    anio           smallint not null,
    monto          numeric(18,2) not null default 0,
    n_procesos     integer not null default 0,
    n_proveedores  integer not null default 0,
    n_entidades    integer not null default 0,
    primary key (cpc, provincia, anio)
);

create table if not exists categoria (
    id            serial primary key,
    nombre        text not null,
    cpc_ejemplos  text[],
    n_procesos    integer not null default 0
);

commit;
