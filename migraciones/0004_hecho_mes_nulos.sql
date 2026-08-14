-- Pliego · quitar el NOT NULL residual de hecho_mes
--
-- La migración 0003 sustituyó la clave primaria por un UNIQUE NULLS NOT DISTINCT,
-- pero en PostgreSQL **eliminar una clave primaria NO elimina el NOT NULL** que
-- implicaba: las columnas conservan la restricción por separado. El backfill volvió
-- a fallar con el mismo error en el mismo mes.
--
-- comprador_ruc, proveedor_ruc y metodo pueden faltar legítimamente: un proceso en
-- sola planificación no tiene proveedor ni método, y son el 68% de un mes en curso.
-- Ver docs/decisiones.md D-017.

begin;

alter table hecho_mes alter column comprador_ruc drop not null;
alter table hecho_mes alter column proveedor_ruc drop not null;
alter table hecho_mes alter column metodo        drop not null;

commit;
