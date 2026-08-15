-- Pliego · la ficha de proveedor
--
-- Es la pantalla que se indexa: hay 77.693 entidades y cada una es una URL con el nombre
-- de una empresa real. Es el canal de adquisicion, y por eso todo lo que hay aqui es
-- descriptivo y gratis. Lo prescriptivo —quien compra lo que tu vendes sin comprartelo—
-- vive en `relacion`, que sigue tras el muro de la 0007.
--
-- Dos cosas que esta migracion resuelve y que la aplicacion NO debe rehacer:
--
-- 1. **Nada se suma en el cliente.** PostgREST corta en 1.000 filas y la portada ya dio
--    56 M donde el real eran 3.203 M sin ningun error visible (D-026).
-- 2. **`entidad` tiene el acceso revocado.** Estas vistas son security definer —el
--    comportamiento por omision— igual que `entidad_publica` en la 0008: leen la tabla
--    y devuelven el dato ya enmascarado. Poner `security_invoker` aqui devolveria 401,
--    que es exactamente el fallo que costo la 0008.
--
-- **Las personas naturales no tienen ficha.** Su RUC contiene la cedula, asi que la vista
-- lo anula; sin clave no hay ruta, y una pagina indexable sobre una persona fisica es
-- justo lo que el invariante 9 y docs/legal.md §1 impiden. Se excluyen de raiz, no en el
-- componente: un dato que no debe salir no debe llegar al navegador.

begin;

-- ---------------------------------------------------------------------------
-- 1. La cabecera de la ficha: una fila por proveedor.
--
--    El tramo y el puesto salen del ultimo anio COMPLETO. El anio en curso va por
--    agosto y clasificar con el subestimaba a 3.198 proveedores; ver D-027. La misma
--    regla que aplica `agrega.py`, repetida aqui porque el puesto se calcula en SQL.
-- ---------------------------------------------------------------------------
create or replace view v_proveedor as
with anio_base as (
    select max(anio) as anio
    from entidad_ano
    where rol = 'proveedor'
      and anio < extract(year from current_date)
),
ultimo as (
    select ea.ruc, ea.monto, ea.n_procesos, ea.n_contrapartes
    from entidad_ano ea, anio_base b
    where ea.rol = 'proveedor' and ea.anio = b.anio
),
historico as (
    select ruc,
           sum(monto)            as monto_total,
           sum(n_procesos)       as procesos_total,
           min(anio)             as primer_anio,
           max(anio)             as ultimo_anio,
           count(*)              as anios_activo
    from entidad_ano
    where rol = 'proveedor'
    group by ruc
),
puesto as (
    -- Puesto dentro del propio tramo, no nacional: comparar una empresa de 300 mil
    -- con Petroecuador no le dice nada. El tramo es su liga.
    select e.ruc,
           rank() over (partition by e.tramo order by u.monto desc) as puesto_tramo,
           count(*) over (partition by e.tramo)                     as n_tramo
    from entidad e join ultimo u on u.ruc = e.ruc
    where e.tramo is not null
)
select
    e.ruc,
    e.nombre,
    e.tipo,
    e.es_publica,
    e.provincia,
    e.canton,
    e.tramo,
    (select anio from anio_base)          as anio_base,
    u.monto                               as monto_base,
    u.n_procesos                          as procesos_base,
    u.n_contrapartes                      as compradores_base,
    p.puesto_tramo,
    p.n_tramo,
    h.monto_total,
    h.procesos_total,
    h.primer_anio,
    h.ultimo_anio,
    h.anios_activo
from entidad e
join historico h on h.ruc = e.ruc
left join ultimo u on u.ruc = e.ruc
left join puesto p on p.ruc = e.ruc
where e.tipo in ('proveedor', 'ambos')
  and not e.es_persona_natural;   -- invariante 9: sin ficha, sin ruta, sin indexar

comment on view v_proveedor is
    'Cabecera de la ficha de proveedor. Cifras del ultimo anio completo (D-027) y puesto '
    'dentro del propio tramo. Excluye personas naturales: su RUC contiene la cedula.';

-- ---------------------------------------------------------------------------
-- 2. En que compra el Estado a este proveedor.
--
--    Ventana de 24 meses porque sale de `proceso_resumen`. Es demanda reciente, que es
--    la pregunta que se hace quien mira la ficha; el historico de once anios esta en la
--    serie anual.
-- ---------------------------------------------------------------------------
create or replace view v_proveedor_categoria as
select
    pr.proveedor_ruc                       as ruc,
    pr.categoria_id,
    c.nombre                               as categoria,
    count(*)                               as n_procesos,
    coalesce(sum(pr.adjudicado), 0)        as monto,
    count(distinct pr.comprador_ruc)       as n_compradores
from proceso_resumen pr
join categoria c on c.id = pr.categoria_id
where pr.proveedor_ruc is not null
  and pr.estado in ('adjudicado', 'cerrado')
group by pr.proveedor_ruc, pr.categoria_id, c.nombre;

comment on view v_proveedor_categoria is
    'Categorias en que un proveedor gana, ventana de 24 meses. Alimenta la ficha y es la '
    'entrada de compradores huerfanos.';

-- ---------------------------------------------------------------------------
-- 3. Compradores huerfanos: la tesis del producto, contada pero no nombrada.
--
--    Entidades que compraron la categoria del proveedor y NUNCA le adjudicaron a el.
--    D-004 y docs/propuesta-valor.md: crecer es diversificar compradores, y este es el
--    mecanismo de esa transicion.
--
--    **Aqui solo va el numero.** El listado con nombres es lo que se cobra y sale de
--    `relacion`, que la 0007 dejo sin politica para `anon`. La cifra publica es el
--    gancho: «hay 34 entidades comprando lo que usted vende y ninguna le ha comprado».
--    Nombrarlas es el producto.
-- ---------------------------------------------------------------------------
create or replace view v_proveedor_huerfanos as
with suyas as (
    select distinct proveedor_ruc as ruc, categoria_id
    from proceso_resumen
    where proveedor_ruc is not null and categoria_id is not null
      and estado in ('adjudicado', 'cerrado')
),
compradores_categoria as (
    select distinct categoria_id, comprador_ruc
    from proceso_resumen
    where comprador_ruc is not null and categoria_id is not null
      and estado in ('adjudicado', 'cerrado')
),
ya_compraron as (
    select distinct proveedor_ruc as ruc, comprador_ruc
    from proceso_resumen
    where proveedor_ruc is not null and comprador_ruc is not null
)
select
    s.ruc,
    count(distinct cc.comprador_ruc) as n_huerfanos
from suyas s
join compradores_categoria cc on cc.categoria_id = s.categoria_id
left join ya_compraron yc on yc.ruc = s.ruc and yc.comprador_ruc = cc.comprador_ruc
where yc.comprador_ruc is null
group by s.ruc;

comment on view v_proveedor_huerfanos is
    'Cuantas entidades compran la categoria de un proveedor sin haberle comprado nunca. '
    'Solo el numero: los nombres son la funcion que se cobra y salen de relacion.';

grant select on v_proveedor, v_proveedor_categoria, v_proveedor_huerfanos
    to anon, authenticated;

commit;
