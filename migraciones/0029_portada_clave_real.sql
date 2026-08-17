-- Pliego · el indice unico de v_portada tiene que ser sobre una columna
--
-- La 0026 creo el indice como `on v_portada ((1))` — sobre una expresion constante,
-- porque la vista tiene una sola fila y parecia suficiente. Postgres lo acepto sin
-- protestar, y luego `refresh materialized view concurrently` fallo con:
--
--   ObjectNotInPrerequisiteState: cannot refresh materialized view
--   "public.v_portada" concurrently
--
-- Para refrescar en concurrente, el indice unico debe ser **sobre columnas**, no sobre
-- una expresion ni parcial. El `create index` no valida eso: lo descubres al refrescar.
--
-- Y fallo donde mas molesta: al final de la ingesta diaria, despues de cargar los doce
-- meses correctamente. Otro trabajo bueno marcado como fallido.
--
-- Se anade una columna `fila` con valor constante y el indice va sobre ella.

begin;

drop materialized view if exists v_portada;

create materialized view v_portada as
select
    1                                                                  as fila,
    (select coalesce(sum(registros), 0) from cobertura)                as procesos_historicos,
    (select count(*) from entidad where tipo in ('proveedor','ambos')) as proveedores,
    (select count(*) from entidad where tipo in ('comprador','ambos')) as compradores,
    (select count(*) from categoria)                                   as categorias,
    r.procesos                                                         as oportunidades,
    r.en_juego                                                         as en_juego,
    now()                                                              as calculada
from v_radar_resumen r;

-- Sobre la COLUMNA. Un indice de expresion no vale para refrescar en concurrente, y eso
-- no se sabe hasta que se intenta refrescar.
create unique index idx_v_portada on v_portada (fila);

comment on materialized view v_portada is
    'Cifras de la portada. La columna `fila` existe solo para tener una clave unica sobre '
    'la que refrescar en concurrente: un indice de expresion no sirve para eso.';

grant select on v_portada to anon, authenticated;

commit;
