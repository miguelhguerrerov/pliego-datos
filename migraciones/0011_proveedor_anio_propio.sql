-- Pliego · la ficha usa el ultimo anio completo DE CADA PROVEEDOR
--
-- La 0010 tomaba un unico anio de referencia para todos: el ultimo completo del conjunto,
-- 2025. Pero solo 6.539 de los 21.132 proveedores con ficha estuvieron activos en 2025.
-- Los otros **14.593 —el 69%— salian con guiones en las cuatro cifras de cabecera**, y
-- ademas con un tramo lleno debajo, porque `agrega.py` si usa el anio propio de cada uno.
--
-- No daba ningun error. La vista existia, devolvia filas, la migracion aplico en verde y
-- las pruebas pasaron: `v_proveedor` tiene 21.132 filas y el 30% con cifras completas era
-- justo lo que la prueba exigia. Se vio consultando la vista como la consulta la pagina.
-- Regla 1 de docs/metodo.md, otra vez.
--
-- Aqui cada proveedor trae su propio anio base. Un proveedor que dejo de contratar en 2019
-- tiene ficha con las cifras de 2019 y lo dice; no tiene una ficha vacia.
--
-- El puesto es la excepcion deliberada: solo se calcula para quien sigue activo. Comparar
-- a una empresa de 2019 contra la cohorte de 2025 daria un numero con aspecto de dato y
-- sin significado.

begin;

drop view if exists v_proveedor;

create view v_proveedor as
with base_global as (
    -- La cohorte de comparacion: el ultimo anio cerrado del conjunto. El anio en curso
    -- va a medias y clasificar con el subestima (D-027).
    select max(anio) as anio
    from entidad_ano
    where rol = 'proveedor' and anio < extract(year from current_date)
),
propio as (
    -- El ultimo anio completo DE CADA UNO. Misma regla que aplica agrega.py al tramo,
    -- para que la cifra de cabecera y el tramo hablen del mismo periodo.
    select ea.ruc, max(ea.anio) as anio
    from entidad_ano ea, base_global b
    where ea.rol = 'proveedor' and ea.anio <= b.anio
    group by ea.ruc
),
cifras as (
    select p.ruc, p.anio, ea.monto, ea.n_procesos, ea.n_contrapartes
    from propio p
    join entidad_ano ea
      on ea.ruc = p.ruc and ea.anio = p.anio and ea.rol = 'proveedor'
),
historico as (
    select ruc,
           sum(monto)      as monto_total,
           sum(n_procesos) as procesos_total,
           min(anio)       as primer_anio,
           max(anio)       as ultimo_anio,
           count(*)        as anios_activo
    from entidad_ano
    where rol = 'proveedor'
    group by ruc
),
puesto as (
    select e.ruc,
           rank() over (partition by e.tramo order by c.monto desc) as puesto_tramo,
           count(*) over (partition by e.tramo)                     as n_tramo
    from entidad e
    join cifras c on c.ruc = e.ruc
    join base_global b on c.anio = b.anio    -- solo los que siguen activos
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
    c.anio                                    as anio_base,
    c.monto                                   as monto_base,
    c.n_procesos                              as procesos_base,
    c.n_contrapartes                          as compradores_base,
    (c.anio = (select anio from base_global))  as activo,
    p.puesto_tramo,
    p.n_tramo,
    h.monto_total,
    h.procesos_total,
    h.primer_anio,
    h.ultimo_anio,
    h.anios_activo
from entidad e
join historico h on h.ruc = e.ruc
left join cifras c on c.ruc = e.ruc
left join puesto p on p.ruc = e.ruc
where e.tipo in ('proveedor', 'ambos')
  and not e.es_persona_natural;   -- invariante 9: sin ficha, sin ruta, sin indexar

comment on view v_proveedor is
    'Cabecera de la ficha de proveedor. Cifras del ultimo anio completo DE CADA UNO, para '
    'que no salgan vacias las de quien ya no contrata; `activo` dice si ese anio es el '
    'ultimo cerrado del conjunto. El puesto solo se calcula para los activos.';

grant select on v_proveedor to anon, authenticated;

commit;
