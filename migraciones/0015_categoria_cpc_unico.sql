-- Pliego · el indice unico de categoria.cpc no puede ser parcial
--
-- La 0014 lo creo con `where cpc is not null`, pensando en las categorias viejas que no
-- tienen codigo. Postgres no acepta un indice parcial como destino de `on conflict`
-- salvo que se repita el predicado, asi que `taxonomia.py` fallo al escribir:
--
--   InvalidColumnReference: there is no unique or exclusion constraint
--   matching the ON CONFLICT specification
--
-- Y fallo **al final**, despues de 35 minutos nombrando 350 categorias. El trabajo se
-- perdio entero por la ultima instruccion.
--
-- No hacia falta que fuera parcial: en un indice unico de Postgres los nulos son
-- distintos entre si, asi que un `unique (cpc)` normal ya admite todas las categorias
-- viejas sin codigo. El predicado no aportaba nada y costaba esto.

begin;

drop index if exists idx_categoria_cpc;

create unique index if not exists idx_categoria_cpc on categoria (cpc);

comment on index idx_categoria_cpc is
    'Sin predicado a proposito: los nulos son distintos entre si en un indice unico, y '
    'un indice parcial no sirve como destino de `on conflict`.';

commit;
