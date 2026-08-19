-- Pliego · el perfil deja de ser una cuenta y pasa a ser un espejo (D-047)
--
-- **Primero, una deuda de D-045**: `perfil.categorias` era `integer[]` y guardaba los
-- `categoria_id` del LLM. Esa tabla se borro en la fase 6 y la columna quedo huerfana
-- apuntando a identificadores que ya no existen. Se cambia a `text[]` con codigos del
-- arbol CPC oficial. La unica fila existente la tiene vacia, asi que no se pierde nada.
--
-- **El hallazgo que ordena el diseño**: el RUC ya es el perfil. Medido sobre un
-- proveedor del tramo objetivo, del RUC se derivan sus categorias
-- (`v_proveedor_categoria`), sus competidores (364 contratistas en sus mismas
-- subclases), sus compradores huerfanos (188) y su provincia. **4.232 proveedores del
-- nucleo tienen categorias derivables y 4.195 huerfanos ya calculados.**
--
-- Por eso aqui NO se guarda nada derivable. Lo derivado se consulta en vivo desde el
-- RUC y siempre esta fresco; lo declarado es solo lo que los datos no saben:
--
--   categorias    las ASPIRACIONALES — lo que quiere vender y aun no vende. Es la
--                 tesis del producto (crecer es diversificar) y no hay dato que la
--                 adivine.
--   competidores  RUCs a vigilar que NO comparten subclase con el. Los que si la
--                 comparten salen solos de mercado_nodo_contratista.
--   provincias    donde quiere trabajar, que no es donde esta domiciliado.
--   monto_min/max el rango de contrato que puede atender de verdad.
--
-- Guardar una copia de lo derivado seria crear dos verdades que se desincronizan: el
-- mismo error de la taxonomia del LLM, en pequeño.

begin;

-- La columna huerfana. Vacia en la unica fila que existe, comprobado antes de tocarla.
alter table perfil drop column if exists categorias;
alter table perfil add column categorias text[] not null default '{}';

alter table perfil
    add column if not exists ruc          text,
    add column if not exists competidores text[] not null default '{}',
    add column if not exists monto_max    numeric,
    -- Marca el fin del alta guiada. Sin esto no hay forma de saber si un perfil vacio
    -- es «no lo ha rellenado» o «lo dejo vacio a proposito», y la aplicacion volveria
    -- a pedirle el RUC para siempre.
    add column if not exists onboarding   timestamptz;

comment on column perfil.ruc is
    'El RUC del suscriptor. Es la llave de todo lo derivado: categorias en las que ya '
    'vende, competidores, compradores huerfanos y provincia salen de aqui en vivo. No '
    'se verifica: es dato publico y todo lo que muestra ya es publico.';
comment on column perfil.categorias is
    'Codigos del arbol CPC (cpc_nivel) que el suscriptor declara como objetivo, '
    'incluidos los ASPIRACIONALES. Lo que ya vende no se guarda aqui: se deriva del RUC.';
comment on column perfil.competidores is
    'RUCs a vigilar que no comparten subclase con el suscriptor. Los que la comparten '
    'ya salen de mercado_nodo_contratista sin declararlos.';

-- Un codigo CPC que no existe produce un radar vacio y el usuario concluye que no hay
-- trabajo en su categoria. Es exactamente la clase de fallo silencioso que el proyecto
-- persigue, asi que la base lo rechaza en vez de confiar en el formulario.
create or replace function validar_perfil() returns trigger
language plpgsql as $$
declare huerfano text;
begin
    if new.ruc is not null and new.ruc !~ '^[0-9]{13}$' then
        raise exception 'RUC invalido: % (deben ser 13 digitos)', new.ruc;
    end if;

    select c into huerfano
    from unnest(new.categorias) c
    where not exists (select 1 from cpc_nivel n where n.codigo = c)
    limit 1;
    if huerfano is not null then
        raise exception 'La categoria % no existe en el arbol CPC oficial', huerfano;
    end if;

    select c into huerfano
    from unnest(new.competidores) c
    where c !~ '^[0-9]{13}$'
    limit 1;
    if huerfano is not null then
        raise exception 'RUC de competidor invalido: %', huerfano;
    end if;

    if new.monto_max is not null and new.monto_min is not null
       and new.monto_max < new.monto_min then
        raise exception 'El monto maximo (%) es menor que el minimo (%)',
            new.monto_max, new.monto_min;
    end if;
    return new;
end $$;

drop trigger if exists trg_validar_perfil on perfil;
create trigger trg_validar_perfil
    before insert or update on perfil
    for each row execute function validar_perfil();

-- Buscar suscriptores por RUC (para soporte y para el alta guiada).
create index if not exists idx_perfil_ruc on perfil (ruc) where ruc is not null;

-- La politica no cambia —«lo suyo», correo = auth.email()— pero se reafirma el cierre:
-- `anon` no toca esta tabla ni para leer. Es dato de cliente, no de producto.
revoke all on perfil from anon;

commit;
