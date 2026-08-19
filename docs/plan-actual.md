# Plan en curso — actualizado 19 de agosto de 2026

Este documento existe para que **una sesión nueva pueda continuar sin contexto previo**.
Se actualiza al terminar cada paso. Lo que está hecho vive en `decisiones.md`; aquí solo
lo que está en vuelo y lo que sigue.

---

## Estado del sistema, medido hoy

| Pieza | Estado |
|---|---|
| Taxonomía CPC oficial | **Hecha** (D-045). 3.725 nodos, 30.098 productos, 99,86% de enganche |
| Árbol de mercado navegable | **Hecho**. `/mercado` sección → subclase con contratos, contratantes, contratistas |
| Series anuales | **Hechas** (D-046). 24.010 + 17.316 filas, 5 MB, once años |
| Paginación/orden/filtro | **Hecho** (D-044) en las siete pantallas con tabla |
| Base | 386–398 MB de 460 |
| Pruebas | 119 locales verdes + las de base en Actions |

### Resuelto el 19-08 por la noche

- Recarga de 2026-07/08 y `agregados` en verde. **Fichas al 100% completas** (21.141 de
  21.142); las 5.441 fantasma del fallo de índices desaparecieron.
- **Respaldo de suscriptores hecho** (`respaldo.yml` en pliego-app). ⚠ **Requiere que el
  cliente añada el secreto `SUPABASE_DB_URL` en pliego-app** → Settings → Secrets →
  Actions. Hasta entonces el flujo falla con un mensaje explícito.
- **Perfil-espejo y portada** hechos (D-047).

---

## Lo que sigue, en orden

### Paso A — Respaldo de suscriptores · HECHO, falta un secreto

`respaldo.yml` en pliego-app (privado, para que los correos no acaben en el repo
público). Se detiene y no guarda si `suscriptor` sale vacío. **Acción del cliente:
añadir `SUPABASE_DB_URL` como secreto de Actions en pliego-app.**

### Paso B — El funnel · PARCIALMENTE HECHO (D-047)

Hecho: perfil-espejo, formulario de lo declarado, validación en la base (0039), portada
con «busca tu empresa».

**Falta**, por orden de valor:

1. **`/precio`** con la casilla «acepto el precio anunciado». Es la métrica central de
   `validacion.md` y sin ella el plan de validación es **inmedible**: sus cuatro
   umbrales dependen de esta página. `lista_espera` ya tiene `acepta_precio` y su
   política de RLS. Es el mayor apalancamiento que queda.
2. **«Mi radar»** en el perfil: `v_radar` filtrado por las categorías del suscriptor
   (las derivadas del RUC más las aspiracionales), su provincia y su rango de monto.
   Es lo que crea el hábito de volver.
3. **«Mis competidores»**: qué ganaron este mes los RUCs declarados y los de sus
   subclases.
4. **Alertas por correo**: el perfil ya es su insumo exacto. Bloqueadas por DMARC y por
   que el respaldo esté corriendo de verdad.
5. **Instrumentación del embudo**: hoy nada cuenta altas, perfiles completados ni
   visitas a `/precio`. Sin esto, `validacion.md` no se puede medir aunque exista la
   página.

**Dos decisiones del cliente, aún sin responder**:
- ¿El radar filtrado por perfil es gratis (lo propuesto) o va tras el muro?
- ¿Las adjudicaciones de competidores son gratis —dato público reorganizado— y solo la
  comparativa de precios se paga?

Mientras no se respondan, lo construido asume: **radar filtrado gratis**, y **precios
siempre tras el muro**.

### Paso C — Resto de la auditoría (`informe-auditoria-2026-08.md`)

Por orden de urgencia real:

1. **Renovar el token de GitHub — ACCIÓN DEL CLIENTE, caduca el 13-09-2026.** Si nadie
   lo renueva, los flujos dejan de correr **en silencio**. No lo puede hacer Claude.
2. Crear la alarma de caducidad que el manual documenta y no existe.
3. Rotar las credenciales que pasaron por chat.
4. Revocar escritura de `anon` en `public` salvo `lista_espera.INSERT`.
5. DMARC a `p=quarantine` con informes propios — antes del primer lote de correos.
6. Alarmas restantes de `operacion.md` (mes sin cargar, cuota, cuadre, ratio de baja).
7. Superficie para `baja_metodo` o retirarla de la promesa del plan.

### Paso D — Diferido, sin incógnita técnica

- **Modo análisis con DuckDB-WASM** (D-046): viable y medido; exige publicar los
  Parquet **en el repositorio** porque los activos de release no dan CORS.
- **Supabase Pro** cuando entren los primeros clientes: hace desaparecer la ventana de
  12 meses como concepto.

---

## Reglas que no se negocian en lo que queda

- Toda cifra agregada se mide contra una magnitud conocida antes de publicarla.
- Ningún índice de tupla por posición (D-046).
- Los distintos no se suman entre niveles (D-045).
- Cada paso termina con una **consulta de producto**, no con «la tabla tiene filas».
