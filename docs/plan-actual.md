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

### En vuelo ahora mismo

- **Recarga de 2026-07 y 2026-08** tras el fallo de índices (D-046). `hecho_mes` ya
  está limpio (0 RUC malformados).
- **Pendiente inmediato**: correr `agregados.yml` cuando la ingesta termine. Reconstruye
  `entidad` y con ello las **5.441 fichas que hoy salen sin monto** (son consecuencia
  del fallo de índices, no un problema nuevo). Verificación: `v_proveedor` con
  `monto_base > 0` debe superar el 90%.

---

## Lo que sigue, en orden

### Paso A — Respaldo de suscriptores (invariante 14) · BLOQUEANTE del funnel

**Por qué antes del funnel**: el funnel añade datos de usuario irreemplazables (RUC,
categorías declaradas, competidores). Hoy **no existe ningún respaldo** y el plan
gratuito de Supabase no tiene copias. Hay 1 suscriptor real y `lista_espera` será el
registro del test de precio.

Un flujo nocturno que vuelca `suscriptor`, `perfil`, `lista_espera` y `envio_log` al
repositorio privado (`pliego-app`), cifrado o en CSV plano según se decida. ~20 líneas.

### Paso B — El funnel (analizado, sin programar aún)

El análisis completo está en la conversación del 19-08; el resumen operativo:

1. **Portada**: hoy solo habla del país. Añadir el buscador «escribe tu RUC y mira tu
   espejo» como bloque central.
2. **Onboarding de 3 pasos** tras el primer enlace mágico: RUC → confirmación del
   espejo derivado → frecuencia de resumen.
3. **`/perfil` como mesa de trabajo**: mi empresa, mi radar, mis mercados, mis
   compradores huérfanos (muro), mis precios (muro), mis competidores.
4. **Migración de `perfil`**: añadir `ruc`, `competidores text[]`, `monto_max`, y
   `origen` por campo (derivado/declarado) para re-derivar sin pisar lo editado.

**El hallazgo que ordena el diseño**: el RUC ya es el perfil. Medido — de un RUC se
derivan sus categorías (`v_proveedor_categoria`), sus competidores (364 en sus
subclases), sus compradores huérfanos (188) y su provincia. **4.232 proveedores del
núcleo tienen categorías derivables y 4.195 huérfanos ya calculados.** Lo declarado
queda solo para lo que los datos no saben: categorías aspiracionales, competidores a
vigilar fuera de su subclase, provincias de interés, rango de monto.

**Dos decisiones del cliente pendientes**:
- ¿El radar filtrado por perfil es gratis (propuesto) o va tras el muro?
- ¿Las adjudicaciones de competidores son gratis y solo la comparativa de precios se
  paga?

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
- **`/precio`** con la casilla de «acepto el precio anunciado»: es la métrica central de
  `validacion.md` y hoy no existe, así que el plan de validación es inmedible.

---

## Reglas que no se negocian en lo que queda

- Toda cifra agregada se mide contra una magnitud conocida antes de publicarla.
- Ningún índice de tupla por posición (D-046).
- Los distintos no se suman entre niveles (D-045).
- Cada paso termina con una **consulta de producto**, no con «la tabla tiene filas».
