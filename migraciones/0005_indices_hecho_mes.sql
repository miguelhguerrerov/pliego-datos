-- Pliego · quitar los indices de hecho_mes
--
-- Medido con 137 de 140 meses cargados:
--   hecho_mes        313,7 MB  =  140,2 datos + 173,5 INDICES
--   proceso_resumen  173,7 MB  =  124,2 datos +  49,4 indices
--   base completa    513 MB    ->  por encima del techo de 500 del plan gratuito
--
-- Los indices de hecho_mes no los usa nadie:
--   - la ingesta escribe con delete + copy por mes
--   - agrega.py lee con un recorrido completo de la tabla
-- Ningun consumidor filtra por esas columnas. Costaban el 38% del presupuesto
-- para no servir a nada. Ver docs/decisiones.md D-018.
--
-- Se pierde la garantia de unicidad. La ingesta ya la garantiza por construccion:
-- borra el mes antes de insertarlo y deduplica en memoria antes de copiar.

begin;

alter table hecho_mes drop constraint if exists hecho_mes_unico;
drop index if exists idx_hecho_anio;
drop index if exists idx_hecho_proveedor;
drop index if exists idx_hecho_comprador;

commit;
