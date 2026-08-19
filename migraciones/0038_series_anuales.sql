-- Pliego · las series anuales: once años de analisis sin romper el presupuesto (D-046)
--
-- La ventana de 12 meses limita las FILAS, no el analisis: el historico completo vive
-- en los Parquet (140 meses) y lo que faltaba era un agregado que nadie habia
-- construido. Dos tablas, calculadas en Actions desde los Parquet por `src/anual.py`:
--
--   mercado_nodo_anual   el arbol CPC por año — el nodo nuevo solo tenia 8 meses
--                        efectivos de estadistica y no podia responder «como ha
--                        evolucionado este mercado»
--   precio_cpc_anual     la TENDENCIA del precio por producto y año. Complementa al
--                        benchmark de 24 meses, que responde otra pregunta («a que
--                        oferto hoy»); esta responde «hacia donde va».
--
-- Coste medido antes de construir: ~41.000 + ~50.000 filas ≈ 15-20 MB, dentro del
-- margen de 29 MB hasta la alarma de 420 (base en 391). La valvula documentada si
-- aprieta: hecho_mes (140 MB, regenerable). Ver D-046.
--
-- **Cobertura, medida y honesta**: se reconstruye desde los items del Parquet. El
-- catalogo electronico SI entra —sus items viven en awards, con monto y CPC: 4.705 de
-- 4.705 releases medidos— lo que ademas corrige la explicacion de D-043. En subasta
-- inversa el monto es el convocado del renglon (el adjudicado real es ~7% menor,
-- D-041): el sesgo es estable entre años, asi que la TENDENCIA es valida aunque el
-- absoluto vaya ligeramente alto en nodos con mucha subasta.

begin;

create table if not exists mercado_nodo_anual (
    codigo          text not null,      -- nodo del arbol o '_sin_clasificar'
    nivel           smallint not null,  -- 0 (sin clasificar) a 5
    anio            smallint not null,
    n_procesos      integer not null,
    monto           numeric(16,2) not null,
    mediana         numeric(14,2),
    n_contratantes  integer not null,
    n_contratistas  integer not null,
    primary key (codigo, anio)
);

comment on table mercado_nodo_anual is
    'El arbol CPC por año, 2015 en adelante, reconstruido de los Parquet (D-046). Los '
    'distintos NO se suman entre niveles ni entre años: cada celda se calcula desde '
    'los procesos crudos. El año en curso esta incompleto y la aplicacion lo dice.';

create index if not exists idx_mna_codigo on mercado_nodo_anual (codigo, anio);

create table if not exists precio_cpc_anual (
    cpc      text not null,
    unidad   text not null,
    anio     smallint not null,
    n        integer not null,
    p25      numeric(14,4),
    mediana  numeric(14,4),
    p75      numeric(14,4),
    primary key (cpc, unidad, anio)
);

comment on table precio_cpc_anual is
    'Tendencia del precio unitario por producto CPC, unidad y año (D-046). No es el '
    'benchmark de oferta (ese es precio_cpc, 24 meses): es la serie larga. Solo filas '
    'con n >= 10, como todo precio publicado (invariante 11).';

-- Cerraduras. El tamaño de mercado es descriptivo y gratis; el precio es la funcion
-- que se cobra y hereda EXACTAMENTE la politica de precio_cpc.
alter table mercado_nodo_anual enable row level security;
alter table precio_cpc_anual enable row level security;

create policy "lectura publica" on mercado_nodo_anual for select using (true);
create policy "suscriptor de pago" on precio_cpc_anual for select
    to authenticated
    using (exists (
        select 1 from suscriptor s
        where s.correo = auth.email()
          and s.plan = any (array['profesional'::text, 'institucional'::text])
          and s.estado = 'activo'::text
    ));

revoke insert, update, delete, truncate on mercado_nodo_anual from anon, authenticated;
revoke insert, update, delete, truncate on precio_cpc_anual from anon, authenticated;

commit;
