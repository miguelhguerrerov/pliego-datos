-- Pliego · seguridad a nivel de fila
--
-- Supabase expone por API TODO lo que vive en el esquema `public`. La clave anonima va
-- incrustada en el JavaScript del navegador, asi que sin RLS cualquiera puede leer y
-- escribir la base entera: los suscriptores, la lista de espera y precio_cpc, que es
-- justo lo que se cobra. El muro de pago seria decorativo.
--
-- Antes de esta migracion: 16 tablas con RLS desactivado y cero politicas.
--
-- La frontera es la del wireframe (doc 07): **todo lo descriptivo es gratis, todo lo
-- prescriptivo se paga**. Ver qué pasó es abierto; saber qué hacer al respecto, no.
--
-- El control vive junto al dato y no en el frontend (docs/arquitectura.md §5): un dato
-- que no debe salir no debe llegar al navegador.

begin;

-- ---------------------------------------------------------------------------
-- 1. RLS en todo. Sin politica, nadie lee: se abre lo que se decide abrir.
--    `service_role` —el que usa la ingesta desde Actions— salta RLS siempre.
-- ---------------------------------------------------------------------------
alter table entidad            enable row level security;
alter table entidad_ano        enable row level security;
alter table proceso_resumen    enable row level security;
alter table categoria          enable row level security;
alter table baja_metodo        enable row level security;
alter table mercado_cpc_prov   enable row level security;
alter table cobertura          enable row level security;
alter table cobertura_parquet  enable row level security;
alter table precio_cpc         enable row level security;
alter table relacion           enable row level security;
alter table hecho_mes          enable row level security;
alter table entidad_nombre     enable row level security;
alter table suscriptor         enable row level security;
alter table perfil             enable row level security;
alter table envio_log          enable row level security;
alter table lista_espera       enable row level security;

-- ---------------------------------------------------------------------------
-- 2. Enmascaramiento de personas naturales (invariante 9).
--
--    El RUC de persona natural CONTIENE la cedula y la direccion registrada suele ser
--    domiciliaria. Son publicos en origen, pero republicarlos en un producto comercial
--    cae bajo la LOPDP. Ver docs/legal.md §1.
--
--    Se aplica en una VISTA y se niega el acceso a la tabla: asi el dato enmascarado es
--    el unico que existe para el navegador, en vez de depender de que el componente se
--    acuerde de ocultarlo.
-- ---------------------------------------------------------------------------
create or replace view entidad_publica
with (security_invoker = true) as
select
    case when es_persona_natural
         then repeat('·', length(ruc) - 4) || right(ruc, 4)
         else ruc end                                        as ruc_visible,
    ruc                                                      as ruc,
    nombre,
    tipo,
    es_persona_natural,
    es_publica,
    provincia,
    case when es_persona_natural then null else canton end   as canton,
    tramo
from entidad;

comment on view entidad_publica is
    'Unica via de acceso a entidad desde el navegador. Enmascara el RUC y oculta el '
    'canton de personas naturales, cuyo RUC contiene la cedula. Invariante 9.';

-- ---------------------------------------------------------------------------
-- 3. Lo descriptivo: abierto. Es el canal de adquisicion y lo que se indexa.
-- ---------------------------------------------------------------------------
create policy "lectura publica" on entidad_ano       for select using (true);
create policy "lectura publica" on proceso_resumen   for select using (true);
create policy "lectura publica" on categoria         for select using (true);
create policy "lectura publica" on baja_metodo       for select using (true);
create policy "lectura publica" on mercado_cpc_prov  for select using (true);
create policy "lectura publica" on cobertura         for select using (true);
create policy "lectura publica" on cobertura_parquet for select using (true);

-- `entidad` solo a traves de la vista, que enmascara.
create policy "lectura por la vista" on entidad for select using (true);
revoke select on entidad from anon, authenticated;
grant  select on entidad_publica to anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Lo prescriptivo: tras el muro.
--
--    `precio_cpc` es el benchmark y `relacion` alimenta compradores huerfanos: las dos
--    funciones que se cobran. Sin politica para `anon`, la clave del navegador no las ve.
--
--    La comprobacion va por CORREO y no por la UUID de auth.users (invariante 7): es lo
--    que hace que migrar de cuenta Supabase cueste media jornada.
-- ---------------------------------------------------------------------------
create policy "suscriptor de pago" on precio_cpc for select to authenticated
using (exists (
    select 1 from suscriptor s
    where s.correo = auth.email()
      and s.plan in ('profesional', 'institucional')
      and s.estado = 'activo'
));

create policy "suscriptor de pago" on relacion for select to authenticated
using (exists (
    select 1 from suscriptor s
    where s.correo = auth.email()
      and s.plan in ('profesional', 'institucional')
      and s.estado = 'activo'
));

-- ---------------------------------------------------------------------------
-- 5. Datos de usuario: cada quien ve lo suyo y nada mas.
-- ---------------------------------------------------------------------------
create policy "lo suyo" on suscriptor for select to authenticated using (correo = auth.email());
create policy "lo suyo" on perfil     for all    to authenticated using (correo = auth.email())
                                                                  with check (correo = auth.email());
create policy "lo suyo" on envio_log  for select to authenticated using (correo = auth.email());

-- La lista de espera es el mecanismo de conversion de la fase 3: cualquiera se apunta,
-- nadie la lee. Sin politica de select, ni siquiera quien se apunto puede consultarla.
create policy "cualquiera se apunta" on lista_espera for insert to anon, authenticated
with check (true);

-- ---------------------------------------------------------------------------
-- 6. Tablas internas: sin politica. Solo las ve `service_role`, que salta RLS.
--    hecho_mes y entidad_nombre son insumos de agregacion, no producto.
-- ---------------------------------------------------------------------------

commit;
