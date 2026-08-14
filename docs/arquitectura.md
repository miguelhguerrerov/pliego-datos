# Arquitectura del servicio

Documento 04. Tres capas, y el dato pesado nunca toca la base de datos.

---

## 1. Flujo completo

```
FUENTE  datosabiertos.compraspublicas.gob.ec
  │  descarga masiva mensual en ZIP · 144 archivos · <1 h el histórico
  ▼
INGESTA  GitHub Actions · repositorio público · minutos ilimitados
  │  1. descargar (4 reintentos, troceo por method)
  │  2. validar codificación utf-8 (no reparar: la fuente es correcta)
  │  3. validar contra el contrato de datos
  │  4. normalizar a tablas
  │  5. unificar entidades por RUC
  │  6. clasificar objeto contractual (embeddings + agrupamiento)
  │  7. calcular agregados
  │
  ├──► GITHUB RELEASES   detalle íntegro en Parquet + ZIP originales
  │     sin límite de tamaño · CDN · costo cero
  │     ES TAMBIÉN LA COPIA DE SEGURIDAD: reconstruye la base en <1 h
  │     ES TAMBIÉN EL ACTIVO PÚBLICO: dataset abierto, tráfico orgánico
  │
  └──► SUPABASE POSTGRES   solo agregados · ~460 MB
        │
        ▼
      VERCEL · Next.js
        │  agregados desde Postgres (ISR, caché agresivo)
        │  detalle fino desde Parquet con DuckDB en el navegador
        ▼
      RESEND  un resumen por suscriptor y día, agrupado
```

**Por qué la ingesta no puede vivir en Vercel:** las funciones topan en 60 s (Hobby) y 300 s
(Pro). Descargar, descomprimir, reparar codificación y normalizar 144 paquetes no cabe ahí ni
troceado. GitHub Actions da 6 h por trabajo.

**Por qué la app no consulta al SERCOP en vivo:** la latencia del mismo endpoint varió entre
17 y 200 segundos en las mediciones. La disponibilidad del producto no puede depender de eso.

---

## 2. Los cuatro horizontes

El campo `tag` es la máquina de estados del proceso, y la fuente publica los intermedios. El
notebook original solo miraba el último. **Ahí está el producto.**

| Horizonte | Fuente | Anticipación | Vista |
|---|---|---|---|
| Plan Anual de Contratación | Raspado del portal transaccional | Meses | Fuera del MVP |
| Necesidad declarada (`planning`) | OCDS | Semanas | Radar |
| Proceso abierto (`tender`) | OCDS | Días | Radar, urgente |
| Adjudicado y contratado | OCDS | Pasado | Estadística |

Medido en agosto de 2026: **1 059 de 1 546 registros del mes estaban en sola planificación**.

---

## 3. Cadencia de actualización

Un mes no queda cerrado hasta 4 o 5 meses después. Los registros no solo se añaden, se
completan. De ahí cuatro ritmos:

| Frecuencia | Qué recarga | Por qué |
|---|---|---|
| **Diaria** 04:00 ECT | Mes en curso y anterior | Ahí nacen `planning` y `tender`. Son 3 MB |
| **Semanal** domingo | Últimos 6 meses | Junio todavía tenía un 11% sin cerrar |
| **Mensual** día 3 | Últimos 18 meses | Reconsolidación de la ventana de agregados |
| **Trimestral** | Histórico completo + cuadre contra la API | Detecta reescrituras retroactivas |

**Regla dura.** Las estadísticas de mercado excluyen los últimos 4 meses. El radar usa el dato
del día. Son dos ventanas distintas sobre la misma base y en el producto deben verse como
tales.

---

## 4. Capa de inteligencia artificial

El código CPC solo viene poblado en catálogo electrónico. En el resto de métodos —los de mayor
valor— el objeto contractual es texto libre. **Sin categoría normalizada no hay benchmark, ni
compradores huérfanos, ni tamaño de mercado por sector.** Todo lo que se cobra depende de
resolver esto.

```
2,77 M objetos contractuales
   │
   ├─► embeddings BAAI/bge-m3 (1024 dim)          ~$1
   │      truncados a 256 dim para almacenar (Matryoshka)
   │      viven en Parquet, NO en Postgres
   │
   ├─► agrupamiento por similitud                  aritmética, gratis
   │
   └─► Llama 3.3 70B etiqueta SOLO los grupos      ~$1
          cada proceso hereda la etiqueta de su grupo
```

**Por qué no registro a registro:** serían 2,77 M de llamadas, ~50 USD, y peor resultado.
Comprobado: preguntarle al modelo por «suero antiofídico polivalente» sin contexto devolvió
«medicina veterinaria», que es incorrecto. Etiquetar grupos con sus miembros a la vista da
mejor resultado que etiquetar registros sueltos.

Otras funciones, por orden de valor:

| Función | Modelo | Cuándo |
|---|---|---|
| Búsqueda semántica y encaje de perfil | Embeddings ya calculados | Fase 2 |
| Resolución de entidades duplicadas | Embeddings + reglas de RUC | Fase 1 |
| Resumen de oportunidad en la alerta | Llama 3.3 70B, ~600/día | Fase 4 |
| Extracción de ítems desde texto libre | Llama 3.3 70B, salida estructurada | Fase 3 |
| Consulta en lenguaje natural | Llama 3.3 70B sobre lista blanca de vistas | Después |

**Dónde NO usar modelos de lenguaje.** La predicción de precio de corte y de probabilidad de
adjudicación es trabajo de un modelo estadístico sobre variables numéricas: más preciso, más
barato y explicable ante un cliente que va a decidir con esa cifra. La IA clasifica y redacta;
la estadística predice.

---

## 5. Seguridad y acceso

- **Autenticación por enlace mágico**, sin contraseñas. No hay hashes que migrar y para una
  herramienta que se abre una o dos veces por semana es mejor experiencia.
- **RLS en Postgres**: el plan del suscriptor decide qué tablas puede leer. El control vive
  junto al dato, no en el frontend.
- Las tablas agregadas públicas son legibles con la clave anónima; `precio_cpc`, `relacion` y
  las de usuario, no.
- **Enmascaramiento de personas naturales aplicado en la capa de datos** (`lib/enmascarar.ts`
  y vistas SQL), no en el componente. Un dato que no debe salir no debe llegar al navegador.

---

## 6. Rendimiento y caché

- Las páginas públicas se generan con ISR y se revalidan tras la ingesta diaria. **El tráfico
  casi nunca toca Supabase**, lo que protege los 5 GB de egress del plan gratuito.
- Las consultas caras se resuelven contra tablas agregadas precalculadas una vez al día para
  todos: el coste marginal por suscriptor es cercano a cero.
- El detalle fino —histórico completo de un proveedor, pujas, exploración de ítems— se
  consulta con DuckDB sobre los Parquet **en el navegador**. Cero coste de servidor.

---

## 7. Qué queda fuera de esta arquitectura

- **Módulo de predicción.** Necesita histórico limpio y usuarios reales que digan qué decisión
  están tomando. Fase 5.
- **API pública.** Es del plan institucional.
- **Integración del PAC.** Tokens cifrados, 27 s por consulta, ~38 h por ejercicio para las
  5 066 entidades. Entra tras validar el mercado, y solo para unos cientos de entidades
  relevantes.
