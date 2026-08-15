# Pliego — fases, actividades y estado

Al 15 de agosto de 2026. Estados: **Hecho** · **En curso** · **Pendiente** · **Bloqueado**.

Este documento es el tablero. Lo que explica *por qué* de cada decisión está en
`decisiones.md`; lo que fija cada área, en los catorce documentos de `docs/`.

---

## Fase 0 — Documentación y decisiones · **cerrada**

| Actividad | Estado | Nota |
|---|---|---|
| Análisis de la fuente y de lo que se puede construir | Hecho | |
| Modelo de negocio, segmento y precio (doc 01) | Hecho | Objetivo: 6 697 empresas de 100 K–2 M |
| Propuesta de valor (doc 02) | Hecho | |
| Infraestructura y límites medidos (doc 03) | Hecho | Coste cero verificado |
| Arquitectura de tres capas (doc 04) | Hecho | Parquet · Postgres · Vercel |
| Marca, mockup, wireframe (docs 05–07) | Hecho | |
| Repositorio, agregados, datos (docs 08, 10, 11) | Hecho | |
| Validación, operación, legal (docs 12–14) | Hecho | |
| `CLAUDE.md` — invariantes y trampas (doc 09) | Hecho | 14 invariantes |
| `decisiones.md` — registro | En curso | D-001 a **D-030**, vivo por diseño |
| `metodo.md` — las 7 reglas de verificación | Hecho | Destiladas de 14 fallos |

---

## Fase 1 — Datos · **cerrada, con la taxonomía rehaciéndose**

### Ingesta y normalización

| Actividad | Estado | Nota |
|---|---|---|
| Descarga masiva con reintentos | Hecho | 4 intentos, espera creciente |
| Validación de codificación | Hecho | Corregida hoy: mide sobre texto acentuado (D-029) |
| Contrato de columnas de la fuente | Hecho | `test_contrato_datos.py` falla si cambia |
| Identidad por RUC, no por nombre | Hecho | |
| Histórico completo | **Hecho** | **140 de 140 meses** · 2 774 263 procesos |
| Ventana de 24 meses en Postgres | Hecho | 280 020 procesos |

### Agregados

| Actividad | Estado | Nota |
|---|---|---|
| `hecho_mes` — grano mínimo, 11 años | Hecho | |
| `entidad`, `entidad_ano`, `relacion`, `baja_metodo` | Hecho | 77 693 entidades |
| Tramo sobre el último año completo | Hecho | Corregido hoy (D-027) |
| Cifras de cabecera precalculadas | Hecho | De 0,85 s a 0,19 s por ficha |
| Corte estadístico de 4 meses | Hecho | Invariante 10 |
| Presupuesto de espacio | Hecho | 380 MB de 460 |

### Detalle en Parquet

| Actividad | Estado | Nota |
|---|---|---|
| Ruta JSON troceada por método | Hecho | |
| Esquema declarado, no inferido | Hecho | Corregido hoy (D-028) |
| Publicación en releases de GitHub | **Hecho** | **140 de 140 meses**, uno por año |
| Registro de cobertura | Hecho | `cobertura_parquet` |

### Clasificación

| Actividad | Estado | Nota |
|---|---|---|
| ~~Taxonomía por agrupamiento + LLM~~ | Retirada | 242 categorías con duplicación grave (D-030) |
| **Taxonomía desde el CPC de la fuente** | **En curso** | Subclase de 5 dígitos, ~350 grupos |
| Validación del nombre generado | Hecho | Lo que no pasa cae a la descripción oficial |
| `proceso_resumen.cpc` poblada | En curso | Desde los ítems del Parquet, dominante por monto |
| Reasignación diaria de lo recargado | Hecho | Sin esto el radar se descategoriza cada mañana (D-022) |

### Base de datos y automatización

| Actividad | Estado | Nota |
|---|---|---|
| Migraciones `0001`–`0014` | Hecho | Toda la estructura en SQL (invariante 5) |
| RLS en las 16 tablas | Hecho | El muro vive aquí, no en el frontend (D-025) |
| Enmascaramiento de persona natural | Hecho | Vista `security definer` (invariante 9) |
| Flujo para aplicar migraciones | Hecho | `migrar.yml`, con recálculo opcional |
| Ingesta diaria 09:30 UTC | Hecho | Verde |
| Agregados diarios 09:48 UTC | Hecho | Verde |
| Publicación mensual de Parquet | Hecho | Día 3 |
| Taxonomía mensual | Hecho | Día 5 |
| Pruebas | Hecho | **73 verdes**, 2 omitidas |
| Consultas de producto como aserciones | Hecho | `test_producto.py` — 4 de los 14 fallos |

---

## Fase 2 — Aplicación · **en curso**

| Actividad | Estado | Nota |
|---|---|---|
| Next.js 16.3.1 en Vercel | Hecho | Desplegado, dominio provisional |
| Sistema de diseño y componentes | Hecho | `Cifra`, `SerieAnual`, `Muro`, `NotaCobertura` |
| Portada | Hecho | Cifras desde vista precalculada (D-026) |
| Radar — lo que el Estado va a comprar | Hecho | Único sitio que usa el dato del día |
| **Ficha 360 de proveedor** | Hecho | 21 132 fichas indexables |
| **Ficha 360 de entidad compradora** | Hecho | Sin muro: quien compra atrae |
| **Buscador** | Hecho | Por nombre y por objeto contractual |
| Enlazado entre pantallas | Hecho | |
| Mercado por categoría `/mercado/[cpc]` | **Pendiente** | Antesala del benchmark |
| Benchmark de precio `/benchmark/[cpc]` | **Bloqueado** | Necesita `precio_cpc` poblada |
| Entrar / perfil con enlace mágico | **Pendiente** | Hasta entonces el muro apunta a un 404 |
| Lista de compradores huérfanos | **Bloqueado** | La cifra ya se muestra; los nombres necesitan sesión |
| Alertas diarias por correo | Pendiente | Un correo por suscriptor y día (invariante 13) |
| Exportación nocturna de suscriptores | Pendiente | Invariante 14 |

---

## Fase 3 — Cobro y lanzamiento · **pendiente**

| Actividad | Estado | Nota |
|---|---|---|
| Poblar `precio_cpc` y `mercado_cpc_prov` | **Siguiente** | Desbloqueado: los 140 meses ya están |
| Cobro por transferencia + factura electrónica | Pendiente | Stripe no opera en Ecuador |
| PayPhone / Kushki | Pendiente | Después del primer cliente |
| Umbral de validación (doc 12) | Pendiente | Congelado antes de medir |
| Registrar `pliego.ec` | Pendiente | 35 USD/año |
| Publicar DMARC en `darkmelon.com` | **Pendiente** | Antes del primer envío masivo |
| Rotar las 7 credenciales que pasaron por chat | **Pendiente** | Antes de cobrar |
| Renovar el token de GitHub | **Con fecha** | **Caduca el 13 de septiembre de 2026**; si no, los flujos paran en silencio |

---

## Lo que está en el camino crítico

1. **`precios.py` → `precio_cpc`.** Es la función que se cobra y ya no tiene nada delante.
2. **`/entrar` con enlace mágico.** Convierte el muro en real. Los compradores huérfanos
   ya están calculados: solo falta quién puede verlos.
3. **`/mercado/[cpc]`.** Donde caen los enlaces de categoría y la antesala del benchmark.

Todo lo demás es mejora, no habilitación.
