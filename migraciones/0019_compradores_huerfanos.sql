-- Pliego · la lista de compradores huerfanos, la funcion que se cobra
--
-- La 0010 dejo `v_proveedor_huerfanos`, que solo cuenta. Aqui van los NOMBRES, que es
-- lo que se paga: «34 entidades compran lo que usted vende» engancha, y saber cuales
-- son, cuanto gastaron y desde cuando no le compran a usted es el producto.
--
-- **Es una funcion y no una vista** por una razon concreta: una vista se filtra por RUC
-- desde fuera y nada impide pedirla sin filtro, con lo que un suscriptor de pago podria
-- descargarse la matriz entera de relaciones comerciales del pais en una peticion. Una
-- funcion obliga a pasar un proveedor cada vez.
--
-- `security invoker` a proposito: se ejecuta con los permisos de quien llama, asi que
-- **RLS sigue mandando**. Si quien pregunta no tiene plan activo, la politica de la 0007
-- sobre `relacion` le devuelve cero filas y esta funcion no puede saltarsela. La
-- cerradura sigue estando en la base, no en la aplicacion.

begin;

create or replace function compradores_huerfanos(p_ruc text)
returns table (
    ruc          text,
    nombre       text,
    provincia    text,
    monto        numeric,
    n_procesos   bigint,
    ultima_compra date
)
language sql
stable
security invoker
set search_path = public
as $$
    with suyas as (
        -- Las categorias en que este proveedor gana.
        select distinct categoria_id
        from proceso_resumen
        where proveedor_ruc = p_ruc and categoria_id is not null
          and estado in ('adjudicado', 'cerrado')
    ),
    ya_le_compraron as (
        -- Cualquier trato previo cuenta, aunque fuera de otra categoria: el producto
        -- promete entidades que NO le han comprado, no entidades con las que no ha
        -- trabajado en esta categoria. Prometer menos de lo que se entrega esta bien;
        -- al reves, no.
        select distinct comprador_ruc
        from proceso_resumen
        where proveedor_ruc = p_ruc and comprador_ruc is not null
    )
    select
        case when e.es_persona_natural then null else e.ruc end,
        e.nombre,
        e.provincia,
        round(sum(p.adjudicado), 2),
        count(*),
        max(p.fecha)
    from proceso_resumen p
    join suyas s on s.categoria_id = p.categoria_id
    join entidad e on e.ruc = p.comprador_ruc
    where p.estado in ('adjudicado', 'cerrado')
      and p.comprador_ruc not in (select comprador_ruc from ya_le_compraron)
      -- El muro: sin plan activo, cero filas. La misma comprobacion por CORREO que la
      -- 0007, porque las tablas propias se enlazan por correo y no por UUID
      -- (invariante 7). Repetirla aqui es deliberado: esta funcion no lee `relacion`,
      -- asi que no hereda su politica.
      and exists (
          select 1 from suscriptor su
          where su.correo = auth.email()
            and su.plan in ('profesional', 'institucional')
            and su.estado = 'activo'
      )
    group by e.ruc, e.nombre, e.provincia, e.es_persona_natural
    order by 4 desc
    limit 100;
$$;

comment on function compradores_huerfanos is
    'Entidades que compran las categorias de un proveedor y nunca le han adjudicado a el. '
    'Devuelve cero filas sin plan activo. Es funcion y no vista para que no se pueda '
    'pedir sin filtro y descargar la matriz de relaciones del pais entero.';

revoke all on function compradores_huerfanos(text) from public;
grant execute on function compradores_huerfanos(text) to authenticated;

commit;
