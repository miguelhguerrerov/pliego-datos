-- Pliego · la categoria pasa a ser la subclase CPC
--
-- La taxonomia dejaba de inventarse. Ver docs/decisiones.md D-030 y src/taxonomia.py.
--
-- Lo que habia: 242 categorias construidas agrupando embeddings del objeto contractual
-- y pidiendo a un modelo que bautizara cada grupo. Medido sobre lo que llego a
-- produccion: «oficina» repartido en 12 categorias con 74.209 procesos, «medicamento» en
-- 15, y una categoria con 4.308 procesos llamada «Medicamento antiviral y antibiotico
-- no, es mas generico: Med» — el razonamiento del modelo, truncado a 60 caracteres.
--
-- Lo que hay: el CPC que la fuente ya entrega en el 100% de los procesos con items,
-- truncado a 5 digitos, que es la subclase de la clasificacion internacional.
--
-- `proceso_resumen.cpc` se declaro en la 0001 y estaba **nula en los 280.020 procesos**:
-- la ruta CSV no la trae y solo aparece en el JSON, que vive en Parquet. Ahora se puebla
-- desde ahi, con el CPC dominante por monto de cada proceso.

begin;

-- ---------------------------------------------------------------------------
-- 1. La categoria queda anclada a un codigo, no a un nombre.
--
--    Es la diferencia de fondo: el nombre pasa a ser una etiqueta legible sobre una
--    clave estable, en vez de ser la identidad. Dos ejecuciones dan la misma taxonomia
--    sin depender de una semilla de k-means.
-- ---------------------------------------------------------------------------
alter table categoria
    add column if not exists cpc text;

create unique index if not exists idx_categoria_cpc on categoria (cpc) where cpc is not null;

comment on column categoria.cpc is
    'Subclase CPC de 5 digitos. La identidad de la categoria. El nombre es una etiqueta '
    'legible encima, y puede cambiar sin que cambie la categoria.';
comment on table categoria is
    'Taxonomia de navegacion, anclada al CPC de la fuente. El benchmark de precio usa el '
    'CPC COMPLETO en precio_cpc: comparar precios exige el producto exacto.';

-- Las categorias viejas no tienen CPC y no se pueden traducir a uno: se van cuando
-- taxonomia.py reasigne los procesos. Se marcan ahora para que la limpieza sea
-- explicita y no un borrado silencioso.
update categoria set n_procesos = 0 where cpc is null;

create index if not exists idx_proceso_cpc on proceso_resumen (cpc) where cpc is not null;

commit;
