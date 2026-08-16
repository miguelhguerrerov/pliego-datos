-- Pliego · el benchmark, con su regla de calidad
--
-- **La medicion que dio forma a esta pantalla.** `precio_cpc` tiene 10 424 filas, y al
-- mirar la dispersion de cada una —el cociente entre el tercer y el primer cuartil—:
--
--   <= 2x  muy ajustado ... 1.095  (11%)
--   2-5x   usable ......... 2.186  (21%)
--   5-20x  disperso ....... 3.481  (34%)
--   > 20x  inservible ..... 3.447  (33%)
--
-- **Razon mediana: 9,6x.** Publicar «la mediana es 118,83» cuando el rango intercuartil
-- va de 4,79 a 1.318,55 no es informar: es dar una cifra que parece un precio y no lo es.
-- Quien la use para ofertar pierde el contrato o pierde dinero, y en los dos casos por
-- culpa nuestra.
--
-- **No es un defecto de calculo, se comprobo.** Aunque el CPC tenga una sola descripcion
-- la razon mediana sigue en 8,9x, y mirando los precios crudos de un producto bien
-- definido se ve por que: la unidad declarada es ambigua en origen. «Unidad» puede ser
-- una pastilla o una caja de cien, y eso no lo arregla nadie desde aqui.
--
-- Asi que se publica **solo lo que sostiene una afirmacion**:
--
--   n >= 10        -- por debajo, la distribucion es anecdota
--   p75/p25 <= 5   -- por encima, no hay un precio: hay un rango inutil
--
-- Quedan **1.931 filas sobre 1.409 productos y 498 de las 831 subclases**, con 64.472
-- observaciones detras. Es menos de la mitad del catalogo y es lo unico que se puede
-- afirmar. Es la misma regla que ya aplica `Cifra` al negarse a mostrar nada con n<5.
--
-- Ver docs/decisiones.md D-039.

begin;

create or replace view v_benchmark
with (security_invoker = true) as
select
    left(p.cpc, 5)                          as subclase,
    p.cpc,
    p.anio,
    p.unidad,
    p.n,
    p.p10, p.p25, p.mediana, p.p75, p.p90,
    p.minimo, p.maximo,
    round((p.p75 / p.p25)::numeric, 1)      as dispersion
from precio_cpc p
where p.mediana > 0
  and p.p25 > 0
  and p.n >= 10
  and p.p75 / p.p25 <= 5;

comment on view v_benchmark is
    'El benchmark que se puede afirmar: n>=10 y rango intercuartil por debajo de 5x. '
    'El 68% de precio_cpc no lo pasa, y publicarlo seria dar una cifra que parece un '
    'precio sin serlo. `security_invoker`: hereda el muro de precio_cpc de la 0007.';

-- Cuantos productos con precio tiene cada subclase. Es lo que decide si la pantalla de
-- benchmark de una categoria tiene algo que ensenar, y se consulta desde `/mercado`
-- para no ofrecer una puerta que da a una habitacion vacia.
--
-- Esta SI es publica: saber que existe un dato no es el dato. El muro esta en el precio.
create or replace view v_benchmark_cobertura as
select
    left(cpc, 5)        as subclase,
    count(*)            as filas,
    count(distinct cpc) as productos,
    sum(n)              as observaciones,
    max(anio)           as hasta
from precio_cpc
where mediana > 0 and p25 > 0 and n >= 10 and p75 / p25 <= 5
group by left(cpc, 5);

comment on view v_benchmark_cobertura is
    'Cuantos precios publicables tiene cada categoria. Publica a proposito: el muro esta '
    'en el precio, no en saber que existe.';

grant select on v_benchmark to authenticated;
grant select on v_benchmark_cobertura to anon, authenticated;

commit;
