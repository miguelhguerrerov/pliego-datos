-- Pliego · la portada se materializa
--
-- Con la 0025 dejo de expirar, pero tarda **3,35 s**. El limite de sentencia esta en
-- pocos segundos: eso no es «rapido», es el aviso de que queda poco margen — y es
-- exactamente el error que ya cometi con `/mercado`, donde medi 1,25 s, lo di por bueno
-- y la pantalla acabo saliendo vacia en produccion (0021).
--
-- Son seis numeros en la pagina mas visitada del producto y la primera que ve alguien
-- que llega desde un buscador. No hay ninguna razon para calcularlos en cada peticion.
--
-- El coste en disco son unos bytes. El coste de no hacerlo ya se pago dos veces.

begin;

drop view if exists v_portada;

create materialized view v_portada as
select
    (select coalesce(sum(registros), 0) from cobertura)                as procesos_historicos,
    (select count(*) from entidad where tipo in ('proveedor','ambos')) as proveedores,
    (select count(*) from entidad where tipo in ('comprador','ambos')) as compradores,
    (select count(*) from categoria)                                   as categorias,
    r.procesos                                                         as oportunidades,
    r.en_juego                                                         as en_juego,
    now()                                                              as calculada
from v_radar_resumen r;

-- Unico para poder refrescar sin bloquear lecturas. La vista tiene una sola fila, asi
-- que la constante vale como clave.
create unique index idx_v_portada on v_portada ((1));

comment on materialized view v_portada is
    'Cifras de la portada. Materializada porque calcularlas al vuelo tardaba 3,35 s con '
    'el limite de sentencia en pocos segundos. Se refresca tras la ingesta.';

grant select on v_portada to anon, authenticated;

commit;
