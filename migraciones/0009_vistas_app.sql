-- Pliego · vistas de resumen para la aplicacion
--
-- PostgREST devuelve como maximo 1.000 filas por peticion. La portada sumaba
-- `referencial` sobre las filas devueltas y daba 56,1 M cuando el total real es otro:
-- el conteo era correcto y la suma no, sin ningun error visible. Se detecto porque la
-- misma cifra en dos pantallas no cuadraba.
--
-- La regla del proyecto ya lo decia y yo la salte: los agregados se precalculan en la
-- base y la aplicacion los lee. Sumar en el cliente es ademas traer miles de filas para
-- tirarlas, que consume el egress de 5 GB del plan gratuito. Ver docs/decisiones.md D-026.

begin;

create or replace view v_radar_resumen as
select
    count(*)                                              as procesos,
    coalesce(sum(referencial), 0)                         as en_juego,
    count(*) filter (where estado = 'planificacion')      as en_planificacion,
    count(*) filter (where estado = 'abierto')            as abiertos,
    count(*) filter (where cierra between current_date and current_date + 7) as cierran_semana
from proceso_resumen
where estado in ('planificacion', 'abierto');

comment on view v_radar_resumen is
    'Totales del radar. Existe porque PostgREST corta en 1.000 filas y sumar en el '
    'cliente da cifras falsas sin avisar.';

create or replace view v_portada as
select
    (select coalesce(sum(registros), 0) from cobertura)                  as procesos_historicos,
    (select count(*) from entidad where tipo in ('proveedor','ambos'))   as proveedores,
    (select count(*) from entidad where tipo in ('comprador','ambos'))   as compradores,
    (select count(*) from categoria)                                     as categorias,
    (select procesos from v_radar_resumen)                               as oportunidades,
    (select en_juego from v_radar_resumen)                               as en_juego;

grant select on v_radar_resumen, v_portada to anon, authenticated;

commit;
