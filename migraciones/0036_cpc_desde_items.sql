-- Pliego · los procesos abiertos toman su CPC de sus propios items (D-045, fase 5)
--
-- La clasificacion CPC de cabecera llega por la ruta mensual del Parquet, con ~4 meses
-- de retraso — el corte estadistico lo absorbe para el arbol, pero el RADAR vive en
-- esos meses: sus 4.306 oportunidades tenian 0 con nodo CPC, y la etiqueta de
-- categoria desaparecia de la pantalla mas visitada.
--
-- El puente ya estaba cargado: `abiertos.py` trae a diario los items de todo proceso
-- abierto, CON su CPC (D-035). El CPC de cabecera es el del item dominante por monto —
-- la fase 0.1 midio que cabecera e items coinciden en subclase en el 100% de 3.564
-- procesos, asi que derivarlo de los items es fiel por construccion.
--
-- La funcion corre en la ingesta diaria tras cargar los abiertos. El trigger de la
-- 0032 convierte el cpc en cpc_nodo solo.

begin;

create or replace function asignar_cpc_desde_items() returns integer
language plpgsql as $$
declare filas integer;
begin
    with dominante as (
        select distinct on (i.ocid) i.ocid, i.cpc
        from proceso_item i
        where i.cpc is not null
        order by i.ocid, coalesce(i.monto_linea, 0) desc
    )
    update proceso_resumen p
       set cpc = d.cpc
      from dominante d
     where p.ocid = d.ocid
       and p.cpc is null;
    get diagnostics filas = row_count;
    return filas;
end $$;

-- Primera pasada, ya.
select asignar_cpc_desde_items() as procesos_clasificados_desde_items;

commit;
