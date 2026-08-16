-- Pliego · la funcion de huerfanos lee por la vista, no por la tabla
--
-- La 0019 unia contra `entidad`, y `entidad` tiene el acceso **revocado para `anon` y
-- para `authenticated`** desde la 0007: solo se llega a ella por `entidad_publica`, que
-- es quien enmascara el RUC de persona natural.
--
-- Como la funcion es `security invoker` —a proposito, para que RLS siga mandando—, se
-- ejecuta con los permisos de quien llama. Resultado:
--
--     42501: permission denied for table entidad
--
-- Con la clave anonima eso parecia el muro funcionando. **No lo era.** Le habria pasado
-- igual a un suscriptor de pago: la funcion que se cobra estaba rota para justamente
-- quien la paga, y el error se leia como si fuera la seguridad haciendo su trabajo.
--
-- Es el fallo mas caro de detectar de este proyecto: **una comprobacion que da el
-- resultado correcto por el motivo equivocado**. Verificar que el muro cierra con la
-- clave anonima no dice nada sobre si abre para quien debe.
--
-- Se une contra `entidad_publica`, que es `security definer` y esta abierta a los dos
-- roles, y que ademas ya devuelve el RUC enmascarado — asi que el `case when
-- es_persona_natural` de la 0019 sobraba y se va.

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
        select distinct categoria_id
        from proceso_resumen
        where proveedor_ruc = p_ruc and categoria_id is not null
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
    join suyas s on s.categoria_id = p.categoria_id
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
$$;

comment on function compradores_huerfanos is
    'Entidades que compran las categorias de un proveedor y nunca le han adjudicado a el. '
    'Cero filas sin plan activo. Lee por entidad_publica: `entidad` esta revocada para '
    'anon Y para authenticated, y unir contra ella rompia la funcion para quien paga.';

revoke all on function compradores_huerfanos(text) from public;
grant execute on function compradores_huerfanos(text) to authenticated;

commit;
