-- Pliego · la portada dejo de expirar
--
-- **El fallo.** La portada mostraba «0 procesos desde 2015», «0 proveedores», «$0 en
-- juego». No era que faltaran datos: `v_portada` devolvia
-- `57014: canceling statement due to statement timeout` y la pagina renderizaba ceros.
--
-- **La causa es mia, de la migracion 0024.** Alli hice que `v_radar_resumen` leyera de
-- `v_radar` para que la cabecera cuadrase con la tabla — correcto y necesario. Pero
-- `v_portada` invoca `v_radar_resumen` **dos veces**, una por columna:
--
--     (select procesos from v_radar_resumen) as oportunidades,
--     (select en_juego  from v_radar_resumen) as en_juego
--
-- Antes daba igual porque la vista era un filtro barato sobre `proceso_resumen`. Al
-- meterla detras de `v_radar` cada invocacion pasa a filtrar la tabla entera, y son dos.
--
-- Se evalua **una vez** con un `cross join lateral`. No es una optimizacion elegante:
-- es que pedir dos veces lo mismo en la misma consulta era el defecto.
--
-- Ver docs/decisiones.md D-038.

begin;

create or replace view v_portada as
select
    (select coalesce(sum(registros), 0) from cobertura)                as procesos_historicos,
    (select count(*) from entidad where tipo in ('proveedor','ambos')) as proveedores,
    (select count(*) from entidad where tipo in ('comprador','ambos')) as compradores,
    (select count(*) from categoria)                                   as categorias,
    r.procesos                                                         as oportunidades,
    r.en_juego                                                         as en_juego
from v_radar_resumen r;

comment on view v_portada is
    'Cifras de la portada. `v_radar_resumen` se evalua UNA vez: invocarla dos veces la '
    'hacia expirar y la portada mostraba ceros sin decir que habia fallado.';

-- El radar filtra por antiguedad en cada consulta; sin indice es un recorrido entero.
create index if not exists idx_proceso_publicado
    on proceso_resumen (publicado) where publicado is not null;
create index if not exists idx_proceso_estado_fecha
    on proceso_resumen (estado, fecha desc)
    where estado in ('planificacion', 'abierto');

grant select on v_portada to anon, authenticated;

commit;
