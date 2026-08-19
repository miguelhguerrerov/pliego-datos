-- Pliego · el desmontaje de la taxonomia del LLM (D-045, fase 6)
--
-- La taxonomia generada por LLM (tabla `categoria`, 1.579 filas) muere aqui. La
-- sustituye el arbol CPC oficial (0031-0036), que ya alimenta /mercado, el radar y la
-- ficha de proceso. Este es el ultimo paso y el unico destructivo, por eso va al
-- final: cuando nada la referencia.
--
-- Lo que se recrea sobre `cpc_nodo` conserva nombres y columnas de salida donde la
-- aplicacion los consume (fichas), y gana `codigo` para poder enlazar al arbol.
--
-- La planificacion queda sin categoria A PROPOSITO: no puede tener CPC porque el
-- metodo aun no existe (el JSON troceado por metodo no la contiene), y el clasificador
-- de texto que la etiquetaba era un adivino. El CPC oficial es declarado, no
-- adivinado; la etiqueta aparece cuando existe.

begin;

-- 1. Las vistas del mercado viejo. Nada las consume ya.
drop materialized view if exists v_mercado cascade;
drop view if exists v_mercado_proveedor;
drop view if exists v_mercado_comprador;

-- 2. v_radar y su resumen, sin categoria_id. El drop arrastra v_radar_resumen y
--    v_portada (lee de v_radar_resumen): se recrean los tres.
drop materialized view if exists v_portada;
drop view if exists v_radar_resumen;
drop view if exists v_radar;

create view v_radar as
select ocid, fecha, anio, mes, estado, metodo, cpc,
       comprador_ruc, proveedor_ruc, referencial, adjudicado, provincia,
       objeto, cierra, objeto_ts, publicado, preguntas_hasta,
       (estado = 'abierto'::text)                             as se_puede_ofertar,
       coalesce(publicado, fecha::timestamp with time zone)   as desde_cuando,
       cpc_nodo
from proceso_resumen p
where estado = any (array['planificacion'::text, 'abierto'::text])
  and (cierra >= now()
       or (cierra is null
           and coalesce(publicado, fecha::timestamp with time zone)
               >= now() - '60 days'::interval));

create view v_radar_resumen as
select count(*)                                   as procesos,
       coalesce(sum(referencial), 0)              as en_juego,
       count(*) filter (where estado = 'planificacion') as en_planificacion,
       count(*) filter (where estado = 'abierto')       as abiertos,
       count(*) filter (where cierra >= now()
                          and cierra <= now() + '7 days'::interval) as cierran_semana
from v_radar;

create materialized view v_portada as
select 1                                                                  as fila,
       (select coalesce(sum(registros), 0) from cobertura)                as procesos_historicos,
       (select count(*) from entidad where tipo in ('proveedor','ambos')) as proveedores,
       (select count(*) from entidad where tipo in ('comprador','ambos')) as compradores,
       -- Antes contaba las categorias del LLM. Ahora: subclases oficiales con
       -- actividad, que es lo que un visitante puede navegar de verdad.
       (select count(*) from mercado_nodo where nivel = 5 and n_procesos > 0) as categorias,
       r.procesos                                                         as oportunidades,
       r.en_juego                                                         as en_juego,
       now()                                                              as calculada
from v_radar_resumen r;

create unique index idx_v_portada on v_portada (fila);
grant select on v_portada, v_radar, v_radar_resumen to anon, authenticated;

-- 3. Las vistas de las fichas, sobre el nodo oficial. Ganan `codigo` para enlazar.
drop view if exists v_comprador_categoria;
drop view if exists v_proveedor_categoria;
drop view if exists v_proveedor_huerfanos;

create view v_comprador_categoria as
select pr.comprador_ruc                       as ruc,
       pr.cpc_nodo                            as codigo,
       n.nombre                               as categoria,
       count(*)                               as n_procesos,
       coalesce(sum(pr.adjudicado), 0)        as monto,
       count(distinct pr.proveedor_ruc)       as n_proveedores
from proceso_resumen pr
join cpc_nivel n on n.codigo = pr.cpc_nodo
where pr.comprador_ruc is not null
  and pr.estado = any (array['adjudicado'::text, 'cerrado'::text])
group by pr.comprador_ruc, pr.cpc_nodo, n.nombre;

create view v_proveedor_categoria as
select pr.proveedor_ruc                       as ruc,
       pr.cpc_nodo                            as codigo,
       n.nombre                               as categoria,
       count(*)                               as n_procesos,
       coalesce(sum(pr.adjudicado), 0)        as monto,
       count(distinct pr.comprador_ruc)       as n_compradores
from proceso_resumen pr
join cpc_nivel n on n.codigo = pr.cpc_nodo
where pr.proveedor_ruc is not null
  and pr.estado = any (array['adjudicado'::text, 'cerrado'::text])
group by pr.proveedor_ruc, pr.cpc_nodo, n.nombre;

-- La tesis del producto (D-004), ahora sobre la subclase oficial: entidades que
-- compran lo que tu vendes y nunca te han comprado a ti.
create view v_proveedor_huerfanos as
with suyas as (
    select distinct proveedor_ruc as ruc, cpc_nodo
    from proceso_resumen
    where proveedor_ruc is not null and cpc_nodo is not null
      and estado = any (array['adjudicado'::text, 'cerrado'::text])
), compradores_categoria as (
    select distinct cpc_nodo, comprador_ruc
    from proceso_resumen
    where comprador_ruc is not null and cpc_nodo is not null
      and estado = any (array['adjudicado'::text, 'cerrado'::text])
), ya_compraron as (
    select distinct proveedor_ruc as ruc, comprador_ruc
    from proceso_resumen
    where proveedor_ruc is not null and comprador_ruc is not null
)
select s.ruc, count(distinct cc.comprador_ruc) as n_huerfanos
from suyas s
join compradores_categoria cc on cc.cpc_nodo = s.cpc_nodo
left join ya_compraron yc on yc.ruc = s.ruc and yc.comprador_ruc = cc.comprador_ruc
where yc.comprador_ruc is null
group by s.ruc;

-- Recrear una vista borra sus permisos: se reponen. Las tres publican solo
-- agregados (la cifra vende; los nombres de huerfanos siguen tras el muro RLS de
-- `relacion`, que no se toca).
grant select on v_comprador_categoria, v_proveedor_categoria, v_proveedor_huerfanos
    to anon, authenticated;

-- 4. La funcion que se cobra, sobre el nodo oficial. Identica en todo lo demas:
--    el muro (el exists sobre suscriptor) no se toca ni un caracter.
create or replace function public.compradores_huerfanos(p_ruc text)
 returns table(ruc text, nombre text, provincia text, monto numeric, n_procesos bigint, ultima_compra date)
 language sql
 stable
 set search_path to 'public'
as $function$
    with suyas as (
        select distinct cpc_nodo
        from proceso_resumen
        where proveedor_ruc = p_ruc and cpc_nodo is not null
          and estado in ('adjudicado', 'cerrado')
    ),
    ya_le_compraron as (
        -- Cualquier trato previo cuenta, aunque fuera de otra categoria: el producto
        -- promete entidades que NO le han comprado, no entidades con las que no ha
        -- trabajado en esta categoria.
        select distinct comprador_ruc
        from proceso_resumen
        where proveedor_ruc = p_ruc and comprador_ruc is not null
    )
    select
        e.ruc,              -- ya viene nulo si es persona natural (invariante 9)
        e.nombre,
        e.provincia,
        round(sum(p.adjudicado), 2),
        count(*),
        max(p.fecha)
    from proceso_resumen p
    join suyas s on s.cpc_nodo = p.cpc_nodo
    join entidad_publica e on e.ruc_visible = p.comprador_ruc
    where p.estado in ('adjudicado', 'cerrado')
      and p.comprador_ruc not in (select comprador_ruc from ya_le_compraron)
      and exists (
          select 1 from suscriptor su
          where su.correo = auth.email()
            and su.plan in ('profesional', 'institucional')
            and su.estado = 'activo'
      )
    group by e.ruc, e.nombre, e.provincia
    order by 4 desc
    limit 100;
$function$;

-- 5. La columna y la tabla del LLM.
alter table proceso_resumen drop column if exists categoria_id;
drop table if exists categoria cascade;

commit;
