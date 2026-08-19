-- Pliego · la clasificacion CPC oficial entra como taxonomia (D-045, fase 1)
--
-- Sustituye a la taxonomia generada por LLM (tabla `categoria`), que repetia el mismo
-- nombre en hasta 36 subclases distintas y fragmentaba «construccion» en 87 pedazos.
-- La CPC ya es una jerarquia: no habia que inventarla, habia que cargarla.
--
-- Dos tablas y no una porque son dos cosas: `cpc_nivel` es el ARBOL (5 niveles, el
-- codigo ES el prefijo), `cpc_producto` son las HOJAS del catalogo del SERCOP (codigos
-- de 8 a 13 digitos, con el umbral VAE). El VAE vive en el producto y no en la
-- subclase: 276 subclases tienen varios umbrales, la 35290 llega a nueve.
--
-- La fuente y su validacion estan en referencia/LEEME.md. La carga es src/cpc.py.

begin;

create table if not exists cpc_nivel (
    codigo  text primary key,
    -- 1 seccion · 2 division · 3 grupo · 4 clase · 5 subclase. Coincide con
    -- length(codigo): se comprueba, no se asume.
    nivel   smallint not null check (nivel between 1 and 5),
    nombre  text not null,
    padre   text references cpc_nivel(codigo),
    check (length(codigo) = nivel),
    check ((nivel = 1 and padre is null) or (nivel > 1 and padre = left(codigo, nivel - 1)))
);

comment on table cpc_nivel is
    'El arbol CPC oficial del SERCOP, 3.725 nodos. El codigo es el prefijo: los hijos '
    'de un nodo son los codigos que empiezan por el. Ver referencia/LEEME.md y D-045.';

create table if not exists cpc_producto (
    codigo      text primary key,
    nombre      text not null,
    -- El umbral VAE como fraccion (0.4000, no «40,00%»). Nulo si el catalogo no lo trae.
    umbral_vae  numeric(6,4),
    -- La subclase de la que cuelga: left(codigo,5) si existe en el arbol. Se guarda
    -- resuelta para no repetir la regla de enganche en cada consulta.
    subclase    text references cpc_nivel(codigo)
);

comment on table cpc_producto is
    'Las hojas del catalogo del SERCOP: 30.098 productos con nombre oficial y umbral '
    'VAE. Los codigos van de 8 a 13 digitos — nunca asumir longitud fija (D-045).';

create index if not exists idx_cpc_producto_subclase on cpc_producto (subclase);
create index if not exists idx_cpc_nivel_padre on cpc_nivel (padre);

-- Lectura publica; escritura para nadie que no sea el cargador (service role).
-- Leccion de la auditoria 2026-08: la puerta Y la cerradura, no solo la politica.
alter table cpc_nivel enable row level security;
alter table cpc_producto enable row level security;
create policy "lectura publica" on cpc_nivel for select using (true);
create policy "lectura publica" on cpc_producto for select using (true);
revoke insert, update, delete, truncate on cpc_nivel from anon, authenticated;
revoke insert, update, delete, truncate on cpc_producto from anon, authenticated;

commit;
