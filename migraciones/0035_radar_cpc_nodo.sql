-- Pliego · v_radar expone el nodo CPC oficial (D-045, fase 5)
--
-- El radar etiquetaba cada oportunidad con la categoria del LLM (categoria_id). Ahora
-- etiqueta ademas con el nodo oficial (cpc_nodo) y la aplicacion enlaza a su pagina
-- de mercado. categoria_id se queda hasta la fase 6, el desmontaje del LLM.
--
-- La definicion es la VIGENTE copiada de pg_views (regla de vigencia de D-036) con
-- cpc_nodo anadida al final — `create or replace view` exige conservar las columnas
-- existentes en su orden. No se reescribe nada de la logica: reescribirla de memoria
-- estuvo a punto de cambiar `cierra >= now()` por `>` y la semantica entera de
-- `se_puede_ofertar`.

begin;

create or replace view v_radar as
select ocid,
       fecha,
       anio,
       mes,
       estado,
       metodo,
       cpc,
       categoria_id,
       comprador_ruc,
       proveedor_ruc,
       referencial,
       adjudicado,
       provincia,
       objeto,
       cierra,
       objeto_ts,
       publicado,
       preguntas_hasta,
       (estado = 'abierto'::text)                             as se_puede_ofertar,
       coalesce(publicado, fecha::timestamp with time zone)   as desde_cuando,
       cpc_nodo
from proceso_resumen p
where estado = any (array['planificacion'::text, 'abierto'::text])
  and (cierra >= now()
       or (cierra is null
           and coalesce(publicado, fecha::timestamp with time zone)
               >= now() - '60 days'::interval));

commit;
