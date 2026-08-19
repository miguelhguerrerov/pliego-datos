-- Pliego · el mercado como arbol CPC de cinco niveles (D-045, fase 3)
--
-- Sustituye el mercado plano por categoria del LLM. Cuatro vistas materializadas:
--
--   mercado_nodo             las cifras de cada nodo (3.725 + el cubo sin clasificar)
--   mercado_nodo_metodo      reparto por metodo de contratacion por nodo
--   mercado_nodo_contratista los proveedores de cada nodo, completos
--   mercado_nodo_contratante las entidades de cada nodo, completas
--
-- **Cada nivel se calcula desde los procesos crudos, nunca sumando hijos.** Solo el
-- monto y el numero de procesos son aditivos: los distintos (contratantes,
-- contratistas), las medianas y los percentiles NO se combinan hacia arriba. Medido:
-- la division 54 tiene 1.222 proveedores reales; sumar sus grupos daria 1.244, porque
-- un proveedor activo en tres grupos contaria tres veces. Ver D-045.
--
-- **Los nodos sin actividad aparecen con cero** (decision 18-08): un mercado vacio es
-- informacion. Por eso el LEFT JOIN parte de cpc_nivel, no de los procesos.
--
-- **El corte estadistico (invariante 10) se aplica aqui**: las estadisticas excluyen
-- los ultimos 4 meses, que estan a medio cerrar. Lo unico sin corte es `n_abiertos`,
-- que es dato del dia y se presenta como tal. Esto ademas corrige la violacion del
-- invariante 10 que la auditoria 2026-08 encontro en v_mercado.
--
-- El cubo «sin clasificar» (codigo '_sin_clasificar', nivel 0) recoge lo que no
-- engancha al arbol: 0,489% del monto. Visible, nunca descartado.

begin;

drop materialized view if exists mercado_nodo cascade;

create materialized view mercado_nodo as
with corte as (
    -- Igual que agrega.corte_estadistico: el ultimo (anio, mes) que entra es hoy
    -- menos MESES_SIN_CERRAR (4). El mes de referencia es el del FICHERO (D-037).
    select extract(year from current_date)::int * 12
         + extract(month from current_date)::int - 4 as tope
),
base as (
    select p.cpc_nodo,
           p.adjudicado, p.referencial, p.comprador_ruc, p.proveedor_ruc,
           p.n_oferentes, p.estado,
           (p.anio * 12 + p.mes) <= (select tope from corte) as cerrado
    from proceso_resumen p
),
niveles as (select generate_series(1, 5) as nivel),
agg as (
    select l.nivel,
           left(b.cpc_nodo, l.nivel)                                          as codigo,
           count(*)              filter (where b.cerrado and b.adjudicado > 0) as n_procesos,
           sum(b.adjudicado)     filter (where b.cerrado and b.adjudicado > 0) as monto,
           percentile_cont(0.5)  within group (order by b.adjudicado)
                                 filter (where b.cerrado and b.adjudicado > 0) as mediana,
           percentile_cont(0.25) within group (order by b.adjudicado)
                                 filter (where b.cerrado and b.adjudicado > 0) as p25,
           percentile_cont(0.75) within group (order by b.adjudicado)
                                 filter (where b.cerrado and b.adjudicado > 0) as p75,
           count(distinct b.comprador_ruc)
                                 filter (where b.cerrado and b.adjudicado > 0) as n_contratantes,
           count(distinct b.proveedor_ruc)
                                 filter (where b.cerrado and b.adjudicado > 0) as n_contratistas,
           percentile_cont(0.5)  within group (order by b.n_oferentes)
                                 filter (where b.cerrado and b.n_oferentes is not null) as mediana_oferentes,
           count(*)              filter (where b.cerrado and b.n_oferentes = 1) as n_un_oferente,
           count(*)              filter (where b.cerrado and b.n_oferentes is not null) as n_con_oferentes,
           percentile_cont(0.5)  within group (order by b.adjudicado / nullif(b.referencial, 0))
                                 filter (where b.cerrado and b.adjudicado > 0
                                           and b.referencial > 0) as baja_mediana,
           count(*)              filter (where b.estado in ('planificacion', 'abierto')) as n_abiertos
    from base b cross join niveles l
    where b.cpc_nodo is not null and length(b.cpc_nodo) >= l.nivel
    group by 1, 2
)
select n.codigo, n.nivel, n.nombre, n.padre,
       coalesce(a.n_procesos, 0)     as n_procesos,
       coalesce(a.monto, 0)          as monto,
       a.mediana, a.p25, a.p75,
       coalesce(a.n_contratantes, 0) as n_contratantes,
       coalesce(a.n_contratistas, 0) as n_contratistas,
       a.mediana_oferentes,
       coalesce(a.n_un_oferente, 0)  as n_un_oferente,
       coalesce(a.n_con_oferentes, 0) as n_con_oferentes,
       a.baja_mediana,
       coalesce(a.n_abiertos, 0)     as n_abiertos
from cpc_nivel n
left join agg a on a.codigo = n.codigo and a.nivel = n.nivel

union all

-- El cubo sin clasificar: procesos cuyo CPC no engancha al arbol (o no traen CPC).
select '_sin_clasificar', 0, 'Sin clasificar', null,
       count(*)          filter (where cerrado and adjudicado > 0),
       coalesce(sum(adjudicado) filter (where cerrado and adjudicado > 0), 0),
       percentile_cont(0.5)  within group (order by adjudicado)
                             filter (where cerrado and adjudicado > 0),
       null, null,
       count(distinct comprador_ruc)  filter (where cerrado and adjudicado > 0),
       count(distinct proveedor_ruc)  filter (where cerrado and adjudicado > 0),
       null, 0, 0, null,
       count(*) filter (where estado in ('planificacion', 'abierto'))
from base where cpc_nodo is null;

-- Sobre COLUMNA, no expresion: la leccion de la 0029.
create unique index idx_mercado_nodo on mercado_nodo (codigo);
create index idx_mercado_nodo_padre on mercado_nodo (padre, monto desc);

create materialized view mercado_nodo_metodo as
with corte as (
    select extract(year from current_date)::int * 12
         + extract(month from current_date)::int - 4 as tope
),
niveles as (select generate_series(1, 5) as nivel)
select left(p.cpc_nodo, l.nivel)            as codigo,
       coalesce(p.metodo, '(sin método)')   as metodo,
       count(*)                             as n_procesos,
       sum(p.adjudicado)                    as monto
from proceso_resumen p cross join niveles l
where p.cpc_nodo is not null and length(p.cpc_nodo) >= l.nivel
  and p.adjudicado > 0
  and (p.anio * 12 + p.mes) <= (select tope from corte)
group by 1, 2;

create unique index idx_mercado_nodo_metodo on mercado_nodo_metodo (codigo, metodo);

create materialized view mercado_nodo_contratista as
with corte as (
    select extract(year from current_date)::int * 12
         + extract(month from current_date)::int - 4 as tope
),
niveles as (select generate_series(1, 5) as nivel)
select left(p.cpc_nodo, l.nivel)        as codigo,
       p.proveedor_ruc                  as ruc,
       count(*)                         as n_procesos,
       sum(p.adjudicado)                as monto,
       count(distinct p.comprador_ruc)  as n_contratantes
from proceso_resumen p cross join niveles l
where p.cpc_nodo is not null and length(p.cpc_nodo) >= l.nivel
  and p.adjudicado > 0 and p.proveedor_ruc is not null
  and (p.anio * 12 + p.mes) <= (select tope from corte)
group by 1, 2;

create unique index idx_mnc_clave on mercado_nodo_contratista (codigo, ruc);
create index idx_mnc_orden on mercado_nodo_contratista (codigo, monto desc);

create materialized view mercado_nodo_contratante as
with corte as (
    select extract(year from current_date)::int * 12
         + extract(month from current_date)::int - 4 as tope
),
niveles as (select generate_series(1, 5) as nivel)
select left(p.cpc_nodo, l.nivel)        as codigo,
       p.comprador_ruc                  as ruc,
       count(*)                         as n_procesos,
       sum(p.adjudicado)                as monto,
       count(distinct p.proveedor_ruc)  as n_contratistas
from proceso_resumen p cross join niveles l
where p.cpc_nodo is not null and length(p.cpc_nodo) >= l.nivel
  and p.adjudicado > 0 and p.comprador_ruc is not null
  and (p.anio * 12 + p.mes) <= (select tope from corte)
group by 1, 2;

create unique index idx_mnt_clave on mercado_nodo_contratante (codigo, ruc);
create index idx_mnt_orden on mercado_nodo_contratante (codigo, monto desc);

grant select on mercado_nodo, mercado_nodo_metodo,
                mercado_nodo_contratista, mercado_nodo_contratante
    to anon, authenticated;

commit;
