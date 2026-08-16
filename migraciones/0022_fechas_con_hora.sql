-- Pliego · las fechas de un proceso abierto llevan hora
--
-- `cierra` se guardaba como **fecha**, recortando el texto de la fuente a diez
-- caracteres. La fuente publica `2026-07-09T14:00:00-05:00` y nosotros escribiamos
-- `2026-07-09`.
--
-- Para un proveedor esa diferencia es el producto entero: entre «cierra el 9» y «cierra
-- el 9 a las 14:00» va tener un dia o tener tres horas. Una oportunidad que se conoce
-- tarde vale lo mismo que no conocerla, y aqui la estabamos redondeando a peor sin
-- decirlo.
--
-- Medido sobre 2026-07: de 5.717 procesos con `tender`, **1.987 traen hora de publicacion
-- y 652 hora de cierre**, todas reales y en horario de Ecuador (-05:00). No es un campo
-- anecdotico.
--
-- Se anaden ademas dos fechas que la fuente da y no guardabamos:
--
-- - `publicado` — cuando se convoco. Sin ella no se puede saber cuanto tiempo llevaba
--   disponible una oportunidad al descubrirla, que es la unica forma de medir si el
--   radar llega a tiempo.
-- - `preguntas_hasta` — el cierre del periodo de preguntas, que en la practica es la
--   primera fecha que un oferente tiene que respetar y suele vencer varios dias antes
--   que la oferta.

begin;

alter table proceso_resumen
    alter column cierra type timestamptz using cierra::timestamptz,
    add column if not exists publicado       timestamptz,
    add column if not exists preguntas_hasta timestamptz;

comment on column proceso_resumen.cierra is
    'Cierre de recepcion de ofertas, CON HORA. La fuente la da y recortarla a fecha '
    'convertia tres horas restantes en un dia entero.';
comment on column proceso_resumen.publicado is
    'Inicio del periodo de ofertas. Permite medir cuanto llevaba abierta una '
    'oportunidad cuando el radar la mostro.';
comment on column proceso_resumen.preguntas_hasta is
    'Cierre del periodo de preguntas: en la practica, la primera fecha que un oferente '
    'tiene que respetar.';

-- El radar ordena y filtra por cierre; con hora, el indice sigue haciendo falta.
create index if not exists idx_proceso_cierra
    on proceso_resumen (cierra) where cierra is not null;

-- La vista del radar comparaba `cierra` contra `current_date`. Con hora hay que comparar
-- contra `now()`, o un proceso que cierra hoy a las 09:00 seguiria contando como abierto
-- a las 18:00.
create or replace view v_radar_resumen as
select
    count(*)                                              as procesos,
    coalesce(sum(referencial), 0)                         as en_juego,
    count(*) filter (where estado = 'planificacion')      as en_planificacion,
    count(*) filter (where estado = 'abierto')            as abiertos,
    count(*) filter (where cierra between now() and now() + interval '7 days') as cierran_semana
from proceso_resumen
where estado in ('planificacion', 'abierto');

commit;
