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
| Migraciones `0001`–`0016` | Hecho | Toda la estructura en SQL |
| RLS en las 16 tablas | Hecho | El muro vive aquí, no en el frontend |
| Enmascaramiento de persona natural | Hecho | Vista `security definer` |
| Flujos: ingesta, agregados, Parquet, taxonomía, benchmark, migrar, compactar | Hecho | |
| Pruebas | Hecho | **81 verdes** |

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
| **Mercado por categoría `/mercado/[cpc]`** | **En curso** | Ya tiene datos reales debajo |
| Benchmark de precio tras el muro | Pendiente | `precio_cpc` ya poblada |
| Entrar / perfil con enlace mágico | **Pendiente** | Hasta entonces el muro apunta a un 404 |
| Lista de compradores huérfanos | Bloqueado | La cifra se muestra; los nombres necesitan sesión |
| Alertas diarias por correo | Pendiente | Invariante 13 |
| Exportación nocturna de suscriptores | Pendiente | Invariante 14 |

---

## Fase 3 — Cobro y lanzamiento · **pendiente**

| Actividad | Estado | Nota |
|---|---|---|
| Cobro por transferencia + factura electrónica | Pendiente | Stripe no opera en Ecuador |
| PayPhone / Kushki | Pendiente | Después del primer cliente |
| Umbral de validación (doc 12) | Pendiente | Congelar antes de medir |
| Registrar `pliego.ec` | Pendiente | 35 USD/año |
| Publicar DMARC | **Pendiente** | Antes del primer envío masivo |
| Rotar las 7 credenciales que pasaron por chat | **Pendiente** | Antes de cobrar |
| Renovar el token de GitHub | **Con fecha** | **Caduca el 13 de septiembre de 2026** |

---

## Camino crítico

1. **`/mercado/[cpc]`** — en curso. Es la antesala del benchmark y el destino de los
   enlaces de categoría.
2. **`/entrar`** con enlace mágico — convierte el muro en real. Todo lo que hay detrás
   (`precio_cpc`, `relacion`) ya está poblado y protegido.
3. **Cobro** — cuando haya algo que cobrar y alguien a quien cobrárselo.

---

## Deuda conocida y declarada

- **36 324 procesos sin categoría (13%).** Son sobre todo obra pública y servicios, que
  no declaran ítems con CPC. Forzarlos daría categorías falsas (D-032).
- **5 943 procesos en planificación sin monto.** No está en la fuente: la entidad declaró
  qué quiere comprar antes de tener la cifra.
- **`precio_unitario` es un nombre heredado y engañoso** en el Parquet: contiene el total
  de la línea. Renombrarlo obliga a republicar 140 meses. Anotado en tres sitios (D-033).
