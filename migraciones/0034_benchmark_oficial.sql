-- Pliego · el benchmark habla el idioma oficial del CPC (D-045, fase 4)
--
-- Tres cosas que el catalogo oficial permite y la vista anterior no tenia:
--
--   1. El NOMBRE oficial del producto, en vez de depender de la descripcion del item
--      que tocara en la muestra.
--   2. El UMBRAL VAE del producto: cuanto valor agregado ecuatoriano exige la
--      preferencia. Es la otra mitad de «como se califica» (D-040).
--   3. La marca `comparable`: distingue un precio unitario real de un contrato
--      disfrazado de unidad.
--
-- **La regla de `comparable`, medida antes de escribirla** (fase 0.3):
--
--   - «Global» nunca es un precio por unidad: es un tanto alzado. Fuera siempre.
--   - «Unidad»/«U» en las secciones de servicios e intangibles (5-9) es casi siempre
--     el contrato entero: obras a 4,19 M «por unidad». Fuera.
--   - «Unidad» en bienes (secciones 0-4) se queda: una motoniveladora a 500.000 USD
--     la unidad es un precio real, y marcarla por cara seria mentir.
--
--   Con esto se apartan 85 de las ~155 filas con mediana > 100.000; las ~70 restantes
--   son maquinaria y equipos con precios plausibles. La fila no se borra: se marca, y
--   la aplicacion la ensena como «contrato por obra/servicio completo», no como precio.
--
-- Se recrean las vistas (drop + create) porque cambian columnas. Siguen siendo
-- `security_invoker`: la politica de precio_cpc (solo suscriptores) es la cerradura.

begin;

drop view if exists v_benchmark;
drop view if exists v_benchmark_cobertura;

create view v_benchmark
    with (security_invoker = true) as
select left(p.cpc, 5)                          as subclase,
       p.cpc,
       pr.nombre                               as nombre_oficial,
       pr.umbral_vae,
       p.anio,
       p.unidad,
       p.n,
       p.p10, p.p25, p.mediana, p.p75, p.p90,
       p.minimo, p.maximo,
       round(p.p75 / p.p25, 1)                 as dispersion,
       not (
            lower(p.unidad) = 'global'
         or (lower(p.unidad) in ('unidad', 'u') and left(p.cpc, 1) between '5' and '9')
       )                                       as comparable
from precio_cpc p
left join cpc_producto pr on pr.codigo = p.cpc
where p.mediana > 0 and p.p25 > 0 and p.n >= 10 and p.p75 / p.p25 <= 5;

comment on view v_benchmark is
    'Distribucion de precio unitario por producto CPC, con nombre oficial y umbral '
    'VAE. `comparable = false` marca contratos disfrazados de unidad (tanto alzado, '
    'obras «por unidad»): se ensenan como contrato, nunca como precio. Ver D-045.';

create view v_benchmark_cobertura
    with (security_invoker = true) as
select left(cpc, 5)        as subclase,
       count(*)            as filas,
       count(distinct cpc) as productos,
       sum(n)              as observaciones,
       max(anio)           as hasta
from precio_cpc
where mediana > 0 and p25 > 0 and n >= 10 and p75 / p25 <= 5
group by left(cpc, 5);

comment on view v_benchmark_cobertura is
    'Cuantos productos de una subclase tienen precio medido. Publica (la cifra vende '
    'el benchmark; los precios estan detras del muro).';

commit;
