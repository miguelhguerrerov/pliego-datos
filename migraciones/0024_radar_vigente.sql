-- Pliego · el radar solo muestra lo que todavia se puede ofertar
--
-- **El fallo, reportado por el cliente y recurrente.** El radar mostraba 15.210 procesos
-- como oportunidades. Al medirlos:
--
--   con fecha de cierre futura ............     0
--   con fecha de cierre YA PASADA .........   386
--   sin fecha de cierre y de hace <45 dias . 3.417
--   sin fecha de cierre y VIEJOS .......... 11.407
--
-- **El 78% no se podia ofertar.** Habia procesos etiquetados «abierto» desde julio de
-- 2025 — trece meses. La etiqueta `tag` es la maquina de estados del proceso, pero la
-- fuente no siempre publica el cierre, asi que un proceso se queda en `abierto` para
-- siempre aunque haya terminado hace un ano.
--
-- **La ventana sale de medir, no de intuir.** Sobre los 1.512 procesos que declaran
-- inicio y cierre:
--
--   mediana 6,7 dias abierto · p90 14,0 · maximo 44,8
--
-- Ninguno vivio mas de 45 dias. Se usan 60 como margen sobre el maximo observado y sobre
-- el retraso de publicacion de la propia fuente.
--
-- **Por que una vista y no un `where` en la pagina.** Porque son cinco pantallas las que
-- listan procesos, y la cifra de cabecera se calcula aparte: si la regla vive en cada
-- consulta, tarde o temprano una dice 15.210 y la tabla de debajo muestra 3.417. Una
-- cifra que no cuadra con lo que hay debajo destruye la confianza mas rapido que un dato
-- ausente.

begin;

drop view if exists v_radar_resumen cascade;

-- ---------------------------------------------------------------------------
-- La regla, en un sitio.
-- ---------------------------------------------------------------------------
create view v_radar as
select
    p.*,
    -- `abierto` se puede ofertar; `planificacion` es una intencion declarada, sin fecha
    -- de oferta todavia. Mezclarlos bajo una sola columna de «cierre» es parte de lo que
    -- confundia: no son la misma promesa.
    (p.estado = 'abierto')                       as se_puede_ofertar,
    coalesce(p.publicado, p.fecha::timestamptz)  as desde_cuando
from proceso_resumen p
where p.estado in ('planificacion', 'abierto')
  and (
        -- Declara cierre futuro: es indiscutible.
        p.cierra >= now()
        -- O no declara cierre y es reciente. La fuente publica el cierre en solo el 11%
        -- de los casos, asi que su ausencia no prueba nada; la antiguedad si.
        or (p.cierra is null
            and coalesce(p.publicado, p.fecha::timestamptz) >= now() - interval '60 days')
      );

comment on view v_radar is
    'Oportunidades que todavia se pueden ofertar. Excluye lo que ya cerro y lo que lleva '
    'mas de 60 dias sin cierre declarado: medido, ningun proceso vive mas de 45 dias. '
    'Una oportunidad que no se puede ofertar no es una oportunidad.';

-- ---------------------------------------------------------------------------
-- La cabecera cuenta EXACTAMENTE lo mismo que la tabla. Antes se calculaba aparte y
-- ahora lee de la vista, que es lo que impide que vuelvan a divergir.
-- ---------------------------------------------------------------------------
create view v_radar_resumen as
select
    count(*)                                              as procesos,
    coalesce(sum(referencial), 0)                         as en_juego,
    count(*) filter (where estado = 'planificacion')      as en_planificacion,
    count(*) filter (where estado = 'abierto')            as abiertos,
    count(*) filter (where cierra between now() and now() + interval '7 days') as cierran_semana
from v_radar;

create view v_portada as
select
    (select coalesce(sum(registros), 0) from cobertura)                  as procesos_historicos,
    (select count(*) from entidad where tipo in ('proveedor','ambos'))   as proveedores,
    (select count(*) from entidad where tipo in ('comprador','ambos'))   as compradores,
    (select count(*) from categoria)                                     as categorias,
    (select procesos from v_radar_resumen)                               as oportunidades,
    (select en_juego from v_radar_resumen)                               as en_juego;

grant select on v_radar, v_radar_resumen, v_portada to anon, authenticated;

commit;
