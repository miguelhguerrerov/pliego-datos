-- Pliego · el mercado por categoria
--
-- La antesala del benchmark: cuanto se mueve en una categoria, quien gana y quien compra.
-- Es la pantalla donde caen los enlaces de categoria del buscador y de las dos fichas, y
-- la que hace evidente para que sirve pagar.
--
-- **Todo lo de aqui es descriptivo y va abierto.** Que paso en un mercado se puede
-- contar; a que precio deberias ofertar tu, no. La frontera del wireframe (doc 07)
-- pasa exactamente entre `v_mercado_*` y `precio_cpc`.
--
-- Se agrega desde `proceso_resumen` y no desde `mercado_cpc_prov` por dos razones:
--
-- 1. `mercado_cpc_prov` esta al grano del **CPC completo** —de 8 a 12 digitos—, que es lo
--    que necesita el benchmark de precio. La navegacion va por la **subclase de 5**, que
--    es `categoria`. Sumar aqui evita mantener una tercera correspondencia.
-- 2. `proceso_resumen` es lo unico que tiene proveedor y comprador por proceso, que son
--    las dos columnas que dan valor a esta pantalla.
--
-- `n_proveedores` y `n_entidades` de `mercado_cpc_prov` estan a cero: `precios.py` no los
-- calcula porque los items del Parquet no traen quien gano. Estas vistas los dan de
-- verdad, y por eso son la fuente para la pantalla.

begin;

-- ---------------------------------------------------------------------------
-- 1. Cabecera del mercado: una fila por categoria.
-- ---------------------------------------------------------------------------
create or replace view v_mercado as
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

comment on view v_mercado is
    'Tamano de un mercado por subclase CPC, ventana de 24 meses. Descriptivo y abierto: '
    'el precio al que competir es lo que se cobra, y vive en precio_cpc tras el muro.';

-- ---------------------------------------------------------------------------
-- 2. Quien gana. Enmascarado como en todas partes (invariante 9).
-- ---------------------------------------------------------------------------
create or replace view v_mercado_proveedor as
select
    p.categoria_id,
    case when e.es_persona_natural then null else e.ruc end as ruc,
    e.nombre,
    e.provincia,
    e.tramo,
    count(*)                          as n_procesos,
    coalesce(sum(p.adjudicado), 0)    as monto,
    count(distinct p.comprador_ruc)   as n_compradores
from proceso_resumen p
join entidad e on e.ruc = p.proveedor_ruc
where p.categoria_id is not null and p.estado in ('adjudicado','cerrado')
group by p.categoria_id, e.ruc, e.nombre, e.provincia, e.tramo, e.es_persona_natural;

-- ---------------------------------------------------------------------------
-- 3. Quien compra.
-- ---------------------------------------------------------------------------
create or replace view v_mercado_comprador as
select
    p.categoria_id,
    case when e.es_persona_natural then null else e.ruc end as ruc,
    e.nombre,
    e.provincia,
    count(*)                          as n_procesos,
    coalesce(sum(p.adjudicado), 0)    as monto,
    count(distinct p.proveedor_ruc)   as n_proveedores
from proceso_resumen p
join entidad e on e.ruc = p.comprador_ruc
where p.categoria_id is not null and p.estado in ('adjudicado','cerrado')
group by p.categoria_id, e.ruc, e.nombre, e.provincia, e.es_persona_natural;

comment on view v_mercado_proveedor is
    'Quien gana en una categoria. La columna de compradores por proveedor es la tesis '
    'del producto puesta en una sola pantalla.';

grant select on v_mercado, v_mercado_proveedor, v_mercado_comprador
    to anon, authenticated;

commit;
