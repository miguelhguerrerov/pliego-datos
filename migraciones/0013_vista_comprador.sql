-- Pliego · la ficha de entidad compradora
--
-- El espejo de la de proveedor, y **sin muro**. Quien compra no es cliente: es el objeto
-- de estudio del cliente. Una ficha completa de cada uno de los ~5.000 compradores del
-- Estado es lo que hace que el producto se encuentre y se enlace, y lo que da contexto a
-- la funcion que si se cobra —quien compra tu categoria sin comprarte a ti— sin
-- regalarla. Ver docs/wireframe.md.
--
-- **Por que aqui no hay columnas precalculadas y en `v_proveedor` si.** Lo que reventaba
-- en la 0012 no era agregar, sino la ventana `rank() over (partition by tramo)`, que no
-- se puede filtrar por RUC antes de calcularla: para una sola ficha, Postgres ordenaba
-- los 21.132 proveedores. Aqui no hay puesto nacional —comparar a un municipio de 4.000
-- habitantes con el IESS no dice nada— asi que un `distinct on (ruc)` con el filtro por
-- clave basta y no cuesta 2 MB mas de presupuesto.
--
-- El tramo tampoco existe para compradores: es una segmentacion de venta, y a estos no se
-- les vende. Poner uno seria inventarse una categoria que el modelo de negocio no usa.

begin;

create or replace view v_comprador as
with base_global as (
    -- El anio en curso va a medias: no sostiene una cifra de cabecera (invariante 10).
    select max(anio) as anio
    from entidad_ano
    where rol = 'comprador' and anio < extract(year from current_date)
),
propio as (
    -- El ultimo anio completo DE CADA UNO, para que la ficha de quien dejo de comprar en
    -- 2019 tenga cifras de 2019 y lo diga, en vez de salir vacia. Ver la 0011.
    select distinct on (ea.ruc)
           ea.ruc, ea.anio, ea.monto, ea.n_procesos, ea.n_contrapartes
    from entidad_ano ea, base_global b
    where ea.rol = 'comprador' and ea.anio <= b.anio
    order by ea.ruc, ea.anio desc
),
historico as (
    select ruc,
           sum(monto)      as monto_total,
           sum(n_procesos) as procesos_total,
           min(anio)       as primer_anio,
           max(anio)       as ultimo_anio,
           count(*)        as anios_activo
    from entidad_ano
    where rol = 'comprador'
    group by ruc
)
select
    e.ruc,
    e.nombre,
    e.tipo,
    e.es_publica,
    e.provincia,
    p.anio                                     as anio_base,
    (p.anio = (select anio from base_global))  as activo,
    p.monto                                    as monto_base,
    p.n_procesos                               as procesos_base,
    p.n_contrapartes                           as proveedores_base,
    h.monto_total,
    h.procesos_total,
    h.primer_anio,
    h.ultimo_anio,
    h.anios_activo
from entidad e
join historico h on h.ruc = e.ruc
left join propio p on p.ruc = e.ruc
where e.tipo in ('comprador', 'ambos')
  and not e.es_persona_natural;   -- invariante 9, igual que en la de proveedor

comment on view v_comprador is
    'Cabecera de la ficha de entidad compradora. Sin muro y sin tramo: a quien compra no '
    'se le vende, y una ficha suya completa es canal de adquisicion, no producto.';

-- ---------------------------------------------------------------------------
-- En que gasta. La contraparte de v_proveedor_categoria.
-- ---------------------------------------------------------------------------
create or replace view v_comprador_categoria as
select
    pr.comprador_ruc                       as ruc,
    pr.categoria_id,
    c.nombre                               as categoria,
    count(*)                               as n_procesos,
    coalesce(sum(pr.adjudicado), 0)        as monto,
    count(distinct pr.proveedor_ruc)       as n_proveedores
from proceso_resumen pr
join categoria c on c.id = pr.categoria_id
where pr.comprador_ruc is not null
  and pr.estado in ('adjudicado', 'cerrado')
group by pr.comprador_ruc, pr.categoria_id, c.nombre;

comment on view v_comprador_categoria is
    'En que gasta una entidad, ventana de 24 meses. La otra mitad de la pregunta que el '
    'proveedor se hace al mirar una ficha de comprador.';

grant select on v_comprador, v_comprador_categoria to anon, authenticated;

commit;
