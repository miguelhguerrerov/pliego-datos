-- Pliego · cobertura de la capa Parquet
--
-- Sin esto no hay forma de saber que meses tienen el detalle completo. La capa CSV ya
-- lleva su registro en `cobertura`; la JSON no llevaba ninguno, asi que un mes con
-- metodos fallidos quedaba publicado y en silencio.

begin;

create table if not exists cobertura_parquet (
    anio             smallint not null,
    mes              smallint not null check (mes between 1 and 12),
    estado           text not null check (estado in ('publicado','parcial','pendiente')),
    n_procesos       integer,
    n_items          integer,
    n_oferentes      integer,
    n_pujas          integer,
    metodos_sin_datos smallint not null default 0,
    metodos_fallidos  smallint not null default 0,
    kb               integer,
    fecha            timestamptz default now(),
    primary key (anio, mes)
);

comment on table cobertura_parquet is
    'Un metodo SIN DATOS no es un fallo: la fuente responde 500 con FileNotFoundException '
    'cuando no hay procesos de ese metodo ese mes. Solo metodos_fallidos indica averia. '
    'Ver docs/decisiones.md D-020.';

commit;
