-- Pliego · cada proceso se engancha al arbol CPC oficial (D-045, fase 2)
--
-- `proceso_resumen.cpc` trae el codigo crudo de la fuente (8 a 13 digitos). Aqui se
-- resuelve UNA VEZ a que nodo del arbol cuelga, con la regla de tres pasos medida:
--
--   1. left(cpc,5) existe como subclase        -> 98,8% de los procesos
--   2. si no, left(cpc,4) existe como clase    -> +0,3%
--   3. si no, queda NULL                       -> 38 codigos, 0,489% del monto
--
-- El paso 3 NO se esconde: el cubo «sin clasificar» se muestra en el arbol con su
-- monto (decision del 18-08: los huecos son informacion).
--
-- La columna se llama `cpc_nodo` y no «subclase» a proposito: casi siempre es una
-- subclase (5 digitos) pero puede ser una clase (4). Un nombre que miente un 0,3% de
-- las veces acaba costando una sesion de depuracion.
--
-- Es un TRIGGER y no logica de ingesta: la regla queda en un solo sitio, la ingesta
-- (delete+copy diario) la aplica sola, y no hay dos copias que desincronizar — que es
-- como se llego a D-041.

begin;

alter table proceso_resumen
    add column if not exists cpc_nodo text references cpc_nivel(codigo);

comment on column proceso_resumen.cpc_nodo is
    'Nodo del arbol CPC oficial del que cuelga el proceso: subclase (5 digitos) o, si '
    'no existe, clase (4). NULL = sin clasificar, y se muestra como tal. Lo puebla un '
    'trigger desde `cpc`; no escribir a mano. Ver D-045.';

create or replace function asignar_cpc_nodo() returns trigger
language plpgsql as $$
begin
    if new.cpc is null then
        new.cpc_nodo := null;
    elsif exists (select 1 from cpc_nivel where codigo = left(new.cpc, 5)) then
        new.cpc_nodo := left(new.cpc, 5);
    elsif exists (select 1 from cpc_nivel where codigo = left(new.cpc, 4)) then
        new.cpc_nodo := left(new.cpc, 4);
    else
        new.cpc_nodo := null;
    end if;
    return new;
end $$;

drop trigger if exists trg_cpc_nodo on proceso_resumen;
create trigger trg_cpc_nodo
    before insert or update of cpc on proceso_resumen
    for each row execute function asignar_cpc_nodo();

-- Relleno de lo existente. El UPDATE dispara el trigger fila a fila; con 133.000
-- filas son segundos.
update proceso_resumen set cpc = cpc where cpc is not null;

create index if not exists idx_proceso_cpc_nodo on proceso_resumen (cpc_nodo);

commit;
