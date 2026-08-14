-- Pliego · corrección de la clave de hecho_mes y variantes de nombre
--
-- Dos cosas:
--
-- 1. `hecho_mes` tenía clave primaria sobre (anio, mes, comprador, proveedor, metodo).
--    Las columnas de una clave primaria son implícitamente NOT NULL, y muchos procesos
--    NO tienen proveedor: los que están en sola planificación, por ejemplo, que son el
--    68% de un mes en curso. La ingesta fallaba con NotNullViolation en el primer mes.
--    PostgreSQL 17 permite UNIQUE ... NULLS NOT DISTINCT, que conserva la garantía de
--    unicidad tratando los nulos como iguales. Ver docs/decisiones.md D-017.
--
-- 2. `entidad_nombre` guarda todas las grafías vistas por RUC, con su frecuencia, para
--    resolver el nombre canónico por moda y no por el último visto. Medido: solo el
--    1,8% de los RUC tiene más de una grafía y la tabla pesa unos 4 MB, así que la
--    regla documentada se puede cumplir sin rebajarla.

begin;

alter table hecho_mes drop constraint if exists hecho_mes_pkey;

alter table hecho_mes
    add constraint hecho_mes_unico
    unique nulls not distinct (anio, mes, comprador_ruc, proveedor_ruc, metodo);

create table if not exists entidad_nombre (
    ruc     text not null,
    nombre  text not null,
    n       integer not null default 0,
    primary key (ruc, nombre)
);

comment on table entidad_nombre is
    'Variantes de grafia por RUC. entidad.nombre se resuelve por moda: los registros '
    'antiguos tienen mas erratas, asi que el mas frecuente es mejor criterio que el ultimo.';

commit;
