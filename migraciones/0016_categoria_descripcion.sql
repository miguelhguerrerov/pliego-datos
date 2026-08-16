-- Pliego · la categoria guarda su descripcion oficial
--
-- La asignacion por cercania comparaba el NOMBRE de la categoria —«Medicamentos», dos
-- palabras— contra el objeto contractual entero:
--
--   «CONTRATACION DEL SERVICIO DE TRANSPORTE TERRESTRE PARA EL PERSONAL MILITAR QUE
--    SE EMPLEARAN EN LAS OPERACIONES DE DESMINADO HUMANITARIO»
--
-- Un rotulo corto y un parrafo burocratico no se parecen aunque hablen de lo mismo:
-- **13.374 de 15.618 textos (el 86%) quedaron por debajo del umbral** y sin categoria.
--
-- La descripcion oficial del CPC esta escrita en el mismo registro que el objeto
-- contractual —mayusculas, jerga administrativa, la misma longitud—, asi que es el
-- puente natural. Se guarda al construir la taxonomia, que es cuando se tiene.
--
-- El umbral no se vuelve a elegir a ojo: `clasifica.py --por-texto` imprime la
-- distribucion de parecidos antes de aplicarlo.

begin;

alter table categoria
    add column if not exists descripcion text;

comment on column categoria.descripcion is
    'Descripciones oficiales del CPC de esta subclase, las mas frecuentes. Es lo que se '
    'compara contra el objeto contractual: el nombre corto no se parece a un parrafo.';

commit;
