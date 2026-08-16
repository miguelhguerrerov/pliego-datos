-- Pliego · el detalle de lo que sigue abierto
--
-- **Esto matiza el invariante 1**, que dice que el detalle OCDS no entra en Postgres.
-- Ver docs/decisiones.md D-035 para el razonamiento completo; el resumen es:
--
-- El invariante existe por espacio: el detalle de 2,77 millones de procesos no cabe en
-- 460 MB, ni de lejos. Pero el detalle de los **2.000 procesos que siguen abiertos**
-- ocupa ~29 MB, y es justo donde el cliente actua. Guardarlo no rompe el motivo del
-- invariante; lo respeta con una excepcion medida y que se recicla sola.
--
-- **Por que no una llamada en vivo al SERCOP**, que era la alternativa obvia y mas
-- barata en espacio. Medido contra su API:
--
--   20 peticiones seguidas          -> 20 x HTTP 429
--   8 peticiones a 30/min           ->  8 x HTTP 429
--   1 peticion tras 9 min de pausa  ->      HTTP 429
--   1 peticion mas, 20 s despues    ->      HTTP 429
--
-- Sigue bloqueado doce minutos despues, y la respuesta no trae ninguna cabecera
-- `X-RateLimit-*`, asi que no hay forma de auto-regularse. En Vercel las funciones
-- comparten IP: un usuario abriendo cinco procesos dejaria la pantalla rota para todos
-- durante un cuarto de hora, de forma intermitente e inexplicable. El invariante 3
-- existe exactamente para esto, y ahora hay medicion en vez de principio.
--
-- **El ciclo de vida es lo que mantiene el tamano acotado**: `abiertos.py` reemplaza
-- estas tablas enteras en cada pasada, con los procesos que estan en estado `abierto`
-- ese dia. Cuando uno cierra, su detalle desaparece de aqui y se queda en el Parquet,
-- que es el archivo permanente. La tabla no crece: se recicla.

begin;

-- Los articulos del pliego: que se compra, cuanto y a que precio de referencia.
create table if not exists proceso_item (
    ocid          text not null,
    item_id       text,
    origen        text,
    cpc           text,
    descripcion   text,
    cantidad      numeric(16,4),
    unidad        text,
    monto_linea   numeric(16,2),
    primary key (ocid, item_id, origen)
);

comment on column proceso_item.monto_linea is
    'Total de la linea, NO el precio unitario. El precio unitario es esto entre '
    'cantidad. Ver docs/decisiones.md D-033.';

-- Contra quien se compite. El CSV solo trae el ganador; esto sale del JSON.
create table if not exists proceso_oferente (
    ocid    text not null,
    ruc     text not null,
    nombre  text,
    gano    boolean not null default false,
    primary key (ocid, ruc)
);

-- La subasta inversa, puja a puja y con hora. No esta en ningun otro sitio, ni
-- siquiera en la ficha del propio SERCOP.
create table if not exists proceso_puja (
    ocid    text not null,
    puja_id text not null,
    ruc     text,
    fecha   timestamptz,
    valor   numeric(16,2),
    primary key (ocid, puja_id)
);

-- Lo mas valioso del registro: lo que preguntaron los oferentes y lo que contesto la
-- entidad, con nombre y fecha.
create table if not exists proceso_consulta (
    ocid            text not null,
    consulta_id     text not null,
    fecha           timestamptz,
    autor_ruc       text,
    autor           text,
    pregunta        text,
    respuesta       text,
    fecha_respuesta timestamptz,
    primary key (ocid, consulta_id)
);

comment on table proceso_consulta is
    'Preguntas de los oferentes y respuestas de la entidad. Es donde se lee POR QUE se '
    'descalifica a alguien, y no se puede buscar entre procesos en ningun otro sitio.';

-- Un proceso grande se adjudica por partes: competir por un lote no es competir por
-- el total, y el monto del lote es el que importa para decidir si presentarse.
create table if not exists proceso_lote (
    ocid     text not null,
    lote_id  text not null,
    titulo   text,
    monto    numeric(16,2),
    tecnicas text,
    primary key (ocid, lote_id)
);

create index if not exists idx_item_ocid     on proceso_item (ocid);
create index if not exists idx_oferente_ocid on proceso_oferente (ocid);
create index if not exists idx_puja_ocid     on proceso_puja (ocid);
create index if not exists idx_consulta_ocid on proceso_consulta (ocid);
create index if not exists idx_lote_ocid     on proceso_lote (ocid);

-- El oferente enlaza con su ficha: quien mira un proceso quiere saber contra quien
-- compite, y eso ya esta en el producto.
create index if not exists idx_oferente_ruc  on proceso_oferente (ruc);

-- ---------------------------------------------------------------------------
-- Todo esto es descriptivo: qué se compra, quién se presentó, qué se preguntó.
-- Va abierto, como el resto de lo descriptivo. Lo que se cobra sigue siendo el
-- precio al que se adjudica la categoria y los compradores huerfanos.
-- ---------------------------------------------------------------------------
alter table proceso_item      enable row level security;
alter table proceso_oferente  enable row level security;
alter table proceso_puja      enable row level security;
alter table proceso_consulta  enable row level security;
alter table proceso_lote      enable row level security;

create policy "lectura publica" on proceso_item      for select using (true);
create policy "lectura publica" on proceso_oferente  for select using (true);
create policy "lectura publica" on proceso_puja      for select using (true);
create policy "lectura publica" on proceso_consulta  for select using (true);
create policy "lectura publica" on proceso_lote      for select using (true);

commit;
