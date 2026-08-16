-- Pliego · el resumen de mercados se materializa
--
-- `/mercado` salia vacio. La consulta de la pagina —ordenar 856 categorias por monto—
-- devolvia `57014: canceling statement due to statement timeout`.
--
-- Filtrada por UNA categoria la misma vista responde en 0,25 s. Lo que no escala es el
-- indice: ordenar por monto obliga a agregar las 280.480 filas de `proceso_resumen`
-- enteras antes de poder quedarse con las 120 primeras.
--
-- **Y ya lo sabia.** Al desplegar medi 1,25 s y lo di por bueno. Con el limite de
-- sentencia en unos pocos segundos, 1,25 s no es «rapido»: es el aviso de que queda un
-- factor cuatro. Una medicion cerca del limite no es una medicion que pasa.
--
-- Es la tercera vez que este proyecto tropieza con lo mismo —D-026 sumando en el
-- cliente, la 0012 con las ventanas de `v_proveedor`— y la leccion se repite entera:
-- **lo que se lista se precalcula; lo que se filtra por clave se puede calcular al
-- vuelo.** El coste en disco de esta vista es de kilobytes.

begin;

drop view if exists v_mercado;

create materialized view v_mercado as
select
    c.id                                            as categoria_id,
    c.cpc,
    c.nombre,
    c.descripcion,
    count(*)                                        as n_procesos,
    coalesce(sum(p.adjudicado), 0)                  as monto,
    count(distinct p.proveedor_ruc)                 as n_proveedores,
    count(distinct p.comprador_ruc)                 as n_entidades,
    count(*) filter (where p.estado in ('planificacion','abierto')) as n_abiertos,
    min(p.fecha)                                    as desde,
    max(p.fecha)                                    as hasta
from categoria c
join proceso_resumen p on p.categoria_id = c.id
where c.cpc is not null
group by c.id, c.cpc, c.nombre, c.descripcion;

-- Unico sobre `cpc`: es la clave de la ruta `/mercado/[cpc]`, y ademas un indice unico
-- es lo que permite `refresh ... concurrently`, que refresca sin bloquear lecturas.
create unique index idx_v_mercado_cpc on v_mercado (cpc);
create index idx_v_mercado_monto on v_mercado (monto desc);

comment on materialized view v_mercado is
    'Resumen de mercados. Materializada porque el indice ordena 856 categorias por monto '
    'y calcularlo al vuelo expiraba. Se refresca tras los agregados y la taxonomia.';

grant select on v_mercado to anon, authenticated;

commit;
