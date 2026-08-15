-- Pliego · la vista de entidad como frontera de seguridad
--
-- La 0007 creo entidad_publica con security_invoker: se ejecuta con los permisos de
-- quien llama, y a anon se le revoco el acceso a `entidad`, asi que la vista devolvia
-- 401. La comprobacion con la clave anonima real lo detecto; mirar las politicas no
-- habria bastado.
--
-- Aqui la vista ES la frontera: se ejecuta con los permisos de su propietario, lee la
-- tabla y devuelve el dato ya enmascarado. El acceso directo a `entidad` sigue negado,
-- asi que el dato sin enmascarar no tiene ninguna via hacia el navegador.

begin;

drop view if exists entidad_publica;

create view entidad_publica as
select
    case when es_persona_natural
         then repeat('.', length(ruc) - 4) || right(ruc, 4)
         else ruc end                                        as ruc_visible,
    case when es_persona_natural then null else ruc end       as ruc,
    nombre,
    tipo,
    es_persona_natural,
    es_publica,
    provincia,
    case when es_persona_natural then null else canton end   as canton,
    tramo
from entidad;

comment on view entidad_publica is
    'Unica via de acceso a entidad desde el navegador. Enmascara el RUC y oculta canton '
    'de personas naturales, cuyo RUC contiene la cedula. Invariante 9 y docs/legal.md.';

grant select on entidad_publica to anon, authenticated;

commit;
