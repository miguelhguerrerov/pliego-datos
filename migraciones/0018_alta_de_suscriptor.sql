-- Pliego · el alta de un suscriptor al entrar por primera vez
--
-- El muro ya existe y funciona —`precio_cpc` y `relacion` devuelven cero filas con la
-- clave anonima, comprobado—, pero **nadie puede autenticarse todavia**, asi que los
-- tres muros del producto apuntan a una ruta que no esta.
--
-- Las politicas de la 0007 comprueban por CORREO y no por la UUID de `auth.users`
-- (invariante 7): `exists (select 1 from suscriptor where correo = auth.email() ...)`.
-- Para que eso pueda dar verdadero alguna vez, la fila tiene que existir.
--
-- **Se crea con un disparador y no desde la aplicacion** por dos razones:
--
-- 1. Si dependiera de que el frontend acordase de insertarla, un usuario que entra por
--    un enlace directo a una pantalla de pago se quedaria sin fila y sin explicacion.
-- 2. Es estructura, y la estructura vive en migraciones (invariante 5).
--
-- El alta es en plan `gratuito`: entrar no da acceso a nada de pago. El unico camino a
-- `profesional` es que alguien cambie el plan tras cobrar, a mano y por transferencia,
-- que es como se cobra en Ecuador hasta que exista PayPhone (D-005).

begin;

create or replace function crear_suscriptor()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    -- El correo en minusculas: `auth.email()` lo devuelve tal cual lo escribio el
    -- usuario, y una clave primaria que distingue Juan@ de juan@ crea dos cuentas para
    -- la misma persona y deja una de las dos sin su plan de pago.
    insert into suscriptor (correo, plan, estado)
    values (lower(new.email), 'gratuito', 'activo')
    on conflict (correo) do nothing;

    insert into perfil (correo)
    values (lower(new.email))
    on conflict (correo) do nothing;

    return new;
end;
$$;

comment on function crear_suscriptor is
    'Da de alta al suscriptor y su perfil al confirmarse el enlace magico. En plan '
    'gratuito: entrar no da acceso a nada de pago.';

drop trigger if exists al_crear_usuario on auth.users;

create trigger al_crear_usuario
    after insert on auth.users
    for each row execute function crear_suscriptor();

-- El usuario puede corregir su nombre y su RUC, y nada mas: `plan` y `estado` son
-- decisiones del negocio y no del cliente. Sin esta restriccion, cualquiera con su
-- propia sesion se pone `profesional` con una peticion y el muro es decorativo otra vez.
create policy "corrige lo suyo" on suscriptor for update to authenticated
    using (correo = auth.email())
    with check (correo = auth.email()
                and plan = (select s.plan from suscriptor s where s.correo = auth.email())
                and estado = (select s.estado from suscriptor s where s.correo = auth.email()));

-- La lista de espera ya admite altas anonimas desde la 0007; aqui se le permite al
-- usuario ver si el correo con el que entro tiene plan, que es lo que dibuja el muro.
grant select on suscriptor to authenticated;

commit;
