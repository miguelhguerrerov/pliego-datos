# Pliego — fases, actividades y estado

Al 16 de agosto de 2026. Estados: **Hecho** · **En curso** · **Pendiente** · **Bloqueado**.

Este documento es el tablero. El *por qué* de cada decisión está en `decisiones.md`
(D-001 a D-033); lo que fija cada área, en los catorce documentos de `docs/`.

---

## Fase 0 — Documentación y decisiones · **cerrada**

| Actividad | Estado |
|---|---|
| Los 14 documentos del MVP | Hecho |
| `CLAUDE.md` — 14 invariantes y tabla de trampas | Hecho |
| `metodo.md` — reglas de verificación destiladas de los fallos | Hecho |
| `decisiones.md` — D-001 a **D-033** | En curso, vivo por diseño |

---

## Fase 1 — Datos · **cerrada**

### Ingesta y normalización

| Actividad | Estado | Nota |
|---|---|---|
| Descarga masiva con reintentos | Hecho | |
| Validación de codificación | Hecho | Mide sobre texto acentuado, no líneas (D-029) |
| Contrato de columnas de la fuente | Hecho | Falla si la fuente cambia |
| **Histórico completo** | Hecho | **140 de 140 meses** · 2 774 263 procesos |
| Ventana de 24 meses en Postgres | Hecho | 280 480 procesos |
| **Objeto contractual en planificación** | Hecho | De 0 a **13 210** — sale de `planning.rationale` (D-031) |

### Agregados

| Actividad | Estado | Nota |
|---|---|---|
| `hecho_mes`, `entidad`, `entidad_ano`, `relacion`, `baja_metodo` | Hecho | 77 693 entidades |
| Tramo y cifras de cabecera sobre el último año completo | Hecho | D-027 |
| Cifras precalculadas en `entidad` | Hecho | 0,85 s → 0,19 s por ficha |
| Corte estadístico de 4 meses | Hecho | Invariante 10 |
| **Compactación tras toda escritura masiva** | Hecho | La base llegó a 534 MB; techo del plan son 500 |
| Espacio | Hecho | **392 MB** de 460 |

### Detalle en Parquet

| Actividad | Estado | Nota |
|---|---|---|
| Ruta JSON troceada por método | Hecho | |
| Esquema declarado, no inferido | Hecho | D-028 |
| **Publicación en releases** | Hecho | **140 de 140 meses** |

### Clasificación

| Actividad | Estado | Nota |
|---|---|---|
| ~~Taxonomía por agrupamiento + LLM~~ | Retirada | 242 categorías con duplicación grave (D-030) |
| **Taxonomía desde el CPC** | Hecho | **1 337 subclases**, nombres validados |
| `proceso_resumen.cpc` poblada | Hecho | CPC dominante **por monto** |
| Asignación por cercanía para el radar | Hecho | Umbral 0,55 medido, no intuido (D-032) |
| Procesos con categoría | Hecho | **244 156 de 280 480** (87%) |

### Benchmark — **la función que se cobra**

| Actividad | Estado | Nota |
|---|---|---|
| `precio_cpc` poblada | **Hecho** | **10 424 filas**, CPC × año × unidad, n ≥ 5 |
| `mercado_cpc_prov` poblada | **Hecho** | 19 113 filas |
| Precio unitario = `amount / cantidad` | Hecho | `amount` es el total de línea (D-033) |
| Referencial de subasta inversa | Hecho | El CSV no lo trae; se reconstruye del JSON |
| Muro sobre `precio_cpc` | Hecho | 0 filas con la clave anónima, comprobado |

### Base de datos y automatización

| Actividad | Estado | Nota |
|---|---|---|
| Migraciones `0001`–`0020` | Hecho | Toda la estructura en SQL |
| RLS en las 16 tablas | Hecho | El muro vive aquí, no en el frontend |
| Enmascaramiento de persona natural | Hecho | Vista `security definer` |
| Flujos: ingesta, agregados, Parquet, taxonomía, benchmark, migrar, compactar | Hecho | |
| Pruebas | Hecho | **82 verdes** |

---

## Fase 2 — Aplicación · **en curso**

| Actividad | Estado | Nota |
|---|---|---|
| Next.js 16.3.1 en Vercel, diseño y componentes | Hecho | |
| Portada | Hecho | |
| Radar | Hecho | Ya dice qué se compra en cada fila |
| Ficha 360 de proveedor | Hecho | 21 132 fichas indexables |
| Ficha 360 de entidad compradora | Hecho | Sin muro |
| Buscador | Hecho | Por nombre y por objeto contractual |
| «no declarado» distinto de «—» | Hecho | |
| Mercado por categoría e índice | Hecho | 856 mercados con movimiento |
| **Entrar con enlace mágico** | **Hecho** | Sin contraseñas (invariante 6) |
| **Perfil y alta de suscriptor** | **Hecho** | Disparador en `auth.users`, alta en plan gratuito |
| **Lista de compradores huérfanos** | **Hecho** | Cifra en abierto, nombres tras el muro |
| Alertas diarias por correo | Pendiente | Invariante 13 |
| Exportación nocturna de suscriptores | Pendiente | Invariante 14 |

---

## Fase 3 — Cobro y lanzamiento · **pendiente**

| Actividad | Estado | Nota |
|---|---|---|
| **Correo propio en Supabase (SMTP de Resend)** | **Pendiente** | El remitente por omisión limita a ~4 enlaces/hora y no lleva la marca |
| Cobro por transferencia + factura electrónica | Pendiente | Stripe no opera en Ecuador; la activación es manual y hay pantalla para pedirla |
| PayPhone / Kushki | Pendiente | Después del primer cliente |
| Umbral de validación (doc 12) | Pendiente | Congelar antes de medir |
| Registrar `pliego.ec` | Pendiente | 35 USD/año |
| Publicar DMARC | **Pendiente** | Antes del primer envío masivo |
| Rotar las 7 credenciales que pasaron por chat | **Pendiente** | Antes de cobrar |
| Renovar el token de GitHub | **Con fecha** | **Caduca el 13 de septiembre de 2026** |

---

## Camino crítico

**El producto ya se puede cobrar.** Lo que queda para que se cobre solo:

1. **SMTP propio en Supabase.** Sin él, el enlace mágico está limitado a unos pocos
   envíos por hora y llega con remitente ajeno. Es configuración, no código.
2. **Alertas diarias por correo** — la razón recurrente para pagar, no solo la puntual.
3. **Exportación nocturna de suscriptores** (invariante 14): esos datos no se regeneran
   y el plan gratuito de Supabase no hace copias.
4. **Precio y cobro** — activar un plan es hoy una acción manual con una pantalla que la
   pide. Está bien para los primeros clientes y mal para los cincuenta primeros.

---

## Deuda conocida y declarada

- **36 324 procesos sin categoría (13%).** Son sobre todo obra pública y servicios, que
  no declaran ítems con CPC. Forzarlos daría categorías falsas (D-032).
- **5 943 procesos en planificación sin monto.** No está en la fuente: la entidad declaró
  qué quiere comprar antes de tener la cifra.
- **`precio_unitario` es un nombre heredado y engañoso** en el Parquet: contiene el total
  de la línea. Renombrarlo obliga a republicar 140 meses. Anotado en tres sitios (D-033).
- **Los compradores huérfanos bajaron mucho al cambiar la taxonomía.** DITECA pasó de 282
  a 12. No es una pérdida: con 1 337 subclases CPC en vez de 242 categorías inventadas,
  «quién compra lo mío» es un conjunto mucho más estrecho y mucho más cierto. La cifra
  vende menos y sirve más.
