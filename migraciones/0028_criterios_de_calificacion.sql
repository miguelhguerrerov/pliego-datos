-- Pliego · los criterios de calificacion, que ya teniamos y no mirabamos
--
-- **Origen del cambio.** Comparando nuestra ficha de proceso con la del portal oficial
-- del SERCOP, la nuestra cuadraba en todo lo que mostraba —objeto, referencial,
-- licitadores, fechas con hora, articulos con CPC— pero se dejaba fuera informacion que
-- **ya viene en la fuente** y que decide como se oferta.
--
-- Estos cuatro campos estan en el CSV de `tender_` desde el primer dia y nadie los leia:
--
--   awardCriteria           -> como se adjudica: `ratedCriteria`, `lowestCost`...
--   eligibilityCriteria     -> los criterios: «Oferta Economica, Participacion
--                              Ecuatoriana, Subcontratacion, Experiencia General...»
--   mainProcurementCategory -> obra, bienes o servicios
--   numberOfTenderers       -> contra cuantos se compitio
--
-- **Por que importa el segundo.** Saber que un proceso se califica por «Oferta Economica,
-- Experiencia Especifica, Participacion Ecuatoriana» le dice al oferente que el precio no
-- es lo unico que cuenta. Es el complemento directo del benchmark: uno dice a que precio
-- se adjudica, el otro cuanto pesa el precio.
--
-- **Lo que NO esta y no se puede traer.** Los PORCENTAJES de cada criterio (50% oferta
-- economica, 26% experiencia especifica...) solo existen en el portal oficial, y ese
-- portal protege su buscador con CAPTCHA. Se comprobo campo por campo sobre el registro
-- OCDS completo. La via correcta es pedir al SERCOP que los publique en el estandar, que
-- ya tiene sitio para criterios ponderados. Ver docs/decisiones.md D-040.

begin;

alter table proceso_resumen
    add column if not exists criterio     text,
    add column if not exists criterios    text,
    add column if not exists tipo_compra  text,
    add column if not exists n_oferentes  integer;

comment on column proceso_resumen.criterio is
    'Como se adjudica (awardCriteria). `ratedCriteria` significa que el precio compite '
    'contra otros factores y no decide solo.';
comment on column proceso_resumen.criterios is
    'Los criterios de calificacion, en texto (eligibilityCriteria). Los PESOS de cada uno '
    'no vienen en el dato abierto: solo estan en el portal oficial.';
comment on column proceso_resumen.tipo_compra is
    'Obra, bienes o servicios (mainProcurementCategory). En el portal se llama Tipo Compra.';
comment on column proceso_resumen.n_oferentes is
    'Cuantos se presentaron segun la fuente. Distinto de contar `proceso_oferente`, que '
    'solo existe para lo abierto: este viene en el CSV para todo.';

-- Cuanta competencia hubo es una pregunta de producto, no solo un dato de ficha.
create index if not exists idx_proceso_oferentes
    on proceso_resumen (n_oferentes) where n_oferentes is not null;

commit;
