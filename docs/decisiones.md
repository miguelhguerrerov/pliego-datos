# Registro de decisiones

Una entrada por decisión difícil de revertir. Formato fijo: fecha, contexto, opciones,
decisión, consecuencias aceptadas.

**Regla:** violar un invariante del `CLAUDE.md` exige añadir aquí una entrada nueva que lo
justifique, *antes* de escribir el código que lo viola.

---

## D-001 · Descarga masiva en lugar de la API paginada
**2026-08-14**

**Contexto.** El notebook original recorre `api/search_ocds` página a página. Medido: el
servidor impone `X-RateLimit-Limit: 60` por minuto y 10 registros por página fijos —
`page_size` y `limit` se ignoran. El histórico son 277 427 páginas.

**Opciones.** (a) API paginada con reintentos. (b) Endpoint de descarga masiva
`download?type=…&year=&month=&method=`, hallado inspeccionando el portal de datos abiertos.

**Decisión.** Descarga masiva como ruta principal. La API paginada queda solo para el refresco
del día en curso, que es lo único que la descarga masiva no cubre con inmediatez.

**Consecuencias.** El backfill pasa de ~77 h a menos de 1 h. Además el JSON masivo trae
`items[]`, `tenderers[]`, `bids` y `parties[]`, que la ruta paginada no exponía. Se acepta
depender de un endpoint no documentado formalmente: se mitiga con la prueba de contrato.

---

## D-002 · El detalle vive en Parquet sobre releases de GitHub, no en Postgres
**2026-08-14**

**Contexto.** El detalle normalizado de los 11 años pesa ~4 GB de datos, ~12–15 GB en Postgres
con índices. El plan gratuito de Supabase da 500 MB.

**Opciones.** (a) Recortar el histórico. (b) Pagar Supabase Pro desde el día uno.
(c) Separar por capas: agregados en Postgres, detalle en Parquet servido por CDN.

**Decisión.** (c). Los releases de GitHub no tienen límite práctico de tamaño, se sirven por
CDN y cuestan cero. El detalle fino se consulta con DuckDB en el navegador.

**Consecuencias.** Se conserva la serie completa sin pagar. Añade una capa que no existiría
con Postgres grande. **La capa se conserva aunque más adelante se pague Pro**: es también la
copia de seguridad —reconstruye la base entera en menos de una hora— y el activo público que
da tráfico orgánico.

---

## D-003 · El cliente principal es el contratista, no la entidad contratante
**2026-08-14**

**Contexto.** Los mismos datos sirven a ambos lados del mercado.

**Decisión.** El proveedor del Estado. Retorno directo y medible —más contratos ganados—,
decide la compra solo, y son 20 972 empresas frente a 5 066 entidades.

**Consecuencias.** La entidad contratante queda como plan institucional posterior, con la
pregunta invertida: de «a quién le vendo» a «quién me está cobrando de más». El diseño de
agregados sirve a ambos sin cambios, así que la decisión es reversible en producto aunque no
en mensaje.

---

## D-004 · Segmento objetivo: facturación de 100 K a 2 M USD
**2026-08-14**

**Contexto.** Segmentación medida sobre los 20 972 proveedores de 2024, cruzada con
recurrencia respecto a 2023 y número de entidades por proveedor.

**Decisión.** El tramo de 100 K a 2 M: 6 697 empresas, 31,9% de los proveedores y 40,2% del
monto.

**Por qué se descartan los extremos.** Debajo de 25 K son el 34% de los proveedores y el 1,1%
del monto: una suscripción sería entre el 2% y el 12% de todo lo que facturan. El tramo de
25 K a 100 K tiene la recurrencia más baja de la tabla, 52,3%: población flotante. Encima de
2 M ya trabajan con 35 a 79 entidades y tienen área de licitaciones.

**Consecuencias.** El precio se ancla en 600 USD/año, el 0,25% de lo que factura la mediana
del tramo.

---

## D-005 · Cobro por transferencia y factura electrónica
**2026-08-14**

**Contexto.** Stripe no opera en Ecuador; una empresa ecuatoriana no puede recibir pagos por
ahí. Verificado en agosto de 2026.

**Decisión.** Transferencia bancaria más factura electrónica desde el primer cliente, con plan
anual anticipado y descuento de dos meses. PayPhone cuando la cobranza manual duela; Kushki o
PlaceToPay con volumen y recurrencia.

**Consecuencias.** Cero comisión y cero integración en el MVP. La cobranza es manual, lo que
el pago anual anticipado convierte en una tarea al año por cliente en vez de doce. Se acepta
no tener plan mensual hasta que haya pasarela integrada.

---

## D-006 · Clasificación por embeddings y agrupamiento, no registro a registro
**2026-08-14**

**Contexto.** El código CPC solo viene poblado en catálogo electrónico. En el resto de métodos
el objeto contractual es texto libre. Sin categoría normalizada no hay benchmark de precios ni
compradores huérfanos.

**Opciones.** (a) Un modelo de lenguaje clasifica cada uno de los 2,77 M de procesos.
(b) Embeddings de todos, agrupamiento, y el modelo etiqueta solo los grupos.

**Decisión.** (b). Medido contra DeepInfra: BGE-M3 devuelve 1024 dimensiones y separa bien el
dominio en español —«suero antiofídico» contra «medicamentos» da 0,663; contra «vía asfaltada»
0,477—. A ~30 tokens por objeto, embeber los 2,77 M cuesta menos de 1 USD.

**Consecuencias.** El coste baja de ~50 USD a menos de 3. Añade un paso de agrupamiento.
Prueba adicional que confirma la decisión: pedirle al modelo que clasificara «suero antiofídico
polivalente» sin contexto devolvió «medicina veterinaria», que es incorrecto. Etiquetar grupos
con sus miembros a la vista da mejor resultado que etiquetar registros sueltos.

---

## D-007 · Cuenta de Supabase separada y temporal para el MVP
**2026-08-14**

**Contexto.** La cuenta personal tenía sus 2 proyectos activos ocupados. Comprobado con un 400
explícito: **el límite de proyectos activos del plan gratuito es por usuario, no por
organización** — crear una organización nueva no da cupo.

**Decisión.** Cuenta separada con la organización `miguelhguerrerov@gmail.com` para el MVP.
Al llegar los clientes se migra a la cuenta personal con plan Pro.

**Consecuencias.** Se acepta una zona gris de los términos de Supabase, acotada porque es
temporal y termina en un plan de pago. Para que la migración cueste media jornada y no dos
días, los invariantes 5, 6, 7 y 8 del `CLAUDE.md` pasan de buena práctica a obligación:
migraciones versionadas, enlace mágico sin contraseñas, tablas enlazadas por correo y cero
referencias al proyecto en el código. Y el invariante 14 —exportación nocturna de las tablas de
suscriptores— existe porque el plan gratuito no tiene copias de seguridad.

---

## D-008 · Los estados intermedios son el producto, no ruido
**2026-08-14**

**Contexto.** El notebook original solo consulta procesos adjudicados. El campo `tag` de cada
release es en realidad la máquina de estados del proceso, y la fuente publica los intermedios.
Medido: en agosto de 2026, 1 059 de 1 546 registros estaban en sola planificación.

**Decisión.** El embudo de `planning` y `tender` entra en la fase 2, no en la 4.

**Consecuencias.** No cuesta ingesta adicional: los registros vienen en la misma descarga que
ya se procesa. Cambia el orden del plan de construcción — el radar es la razón para volver cada
día; el benchmark es la razón para pagar.

---

## D-009 · Ventana de análisis con cuatro meses de retraso
**2026-08-14**

**Contexto.** Curva de maduración medida en 2026: enero al 98,3% de cierre, junio al 89,0%,
julio al 59,0%, agosto al 30,9%. Un mes tarda cuatro o cinco meses en cerrar; los registros no
solo se añaden, se completan.

**Decisión.** Las estadísticas de mercado excluyen los últimos 4 meses. El radar, en cambio,
usa el dato del día.

**Consecuencias.** Dos ventanas distintas sobre la misma base, y así deben verse en el
producto. Sin esta regla, un benchmark calculado sobre un mes al 59% de cierre saldría sesgado
sin que nada lo advirtiera.

---

## D-010 · Dominio propio `pliego.ec`
**2026-08-14**

**Contexto.** `pliego.ec` está disponible por 35 USD al año. La cuenta de Resend ya tiene
`darkmelon.com` verificado, y el plan gratuito permite un solo dominio.

**Decisión.** Registrar `pliego.ec` para el sitio. El correo sigue saliendo de `darkmelon.com`
mientras dure el plan gratuito de Resend.

**Consecuencias.** Se acepta la disonancia temporal de que el sitio sea `pliego.ec` y el
remitente `darkmelon.com`. Se resuelve al pasar a Resend Pro, verificando entonces
`avisos.pliego.ec` como subdominio dedicado de envío — que es lo que protege la reputación del
dominio corporativo. Hasta entonces, volumen bajo y opt-in real.

---

## D-011 · La codificación de la fuente es correcta; no se repara, se valida
**2026-08-14**

**Contexto.** Durante el análisis se anotó que el servidor devolvía latin-1 etiquetado como
UTF-8, y así quedó escrito en el contrato de datos y en el `CLAUDE.md`.

**Hallazgo al implementar.** Es falso. Los bytes reales son `b'CatÃ¡logo'`, UTF-8
correcto para «Catálogo». Los ocho archivos del ZIP y la respuesta JSON de la API decodifican
en UTF-8 estricto sin error. El símbolo de sustitución que se observaba venía de la consola de
Windows al imprimir, no de los datos.

**Decisión.** `codificacion.py` no repara: valida en UTF-8 estricto, detecta doble codificación
(`Ã¡`, `Ã³`, `Â`) y **detiene la ingesta** si algo de eso aparece.

**Consecuencias.** Se evita corromper datos correctos: la «reparación» documentada habría
convertido `Catálogo` en `CatÃ¡logo` en los 2,77 M de registros. Queda como recordatorio de
que una observación hecha a través de una capa de presentación no es una observación sobre los
datos.

---

## D-012 · Conexión a Postgres por el agrupador en modo sesión
**2026-08-14**

**Contexto.** El primer flujo de ingesta en GitHub Actions falló con
`connection to server at "2600:1f18:...", port 5432 failed: Network is unreachable`.

**Causa.** El host directo `db.<ref>.supabase.co` solo resuelve a IPv6. Los runners de
GitHub Actions no tienen conectividad IPv6.

**Decisión.** Toda conexión usa el agrupador `aws-0-<region>.pooler.supabase.com` en
**modo sesión, puerto 5432**. No el 6543: el modo transacción no soporta `COPY` ni
sentencias preparadas, y la carga masiva depende de `COPY`.

**Consecuencias.** `carga.py` valida la cadena y falla con un mensaje que explica esto,
en vez de dejar un error de red que parece caída del servicio. El modo sesión limita el
número de conexiones simultáneas, lo cual es irrelevante aquí: la ingesta usa una sola.

---

## D-013 · Corrupción esporádica se repara; sistemática detiene la ingesta
**2026-08-14**

**Contexto.** Tras aplicar D-011 (la fuente entrega UTF-8 válido, no se repara nada), el
validador detuvo la ingesta de agosto de 2026 al encontrar doble codificación en
`planning_2026_agosto.csv`.

**Hallazgo al medirlo.** Era **1 línea de 1070, el 0,09%**: una entidad cargó
«georreferenciación» desde un sistema que lo manglió. Suciedad normal de captura, no un
cambio de la fuente.

**Decisión.** El validador distingue dos casos por umbral del 1% de líneas afectadas:

- **Sistemática** (por encima): la fuente cambió. Se detiene la ingesta.
- **Esporádica** (por debajo): se repara el fragmento concreto, se cuenta y se anota en
  `cobertura.nota`. La ingesta continúa.

La reparación solo se aplica si el viaje de ida y vuelta —`latin-1` a `utf-8`— es limpio.
Si no lo es, se deja el original: más vale un campo feo que uno inventado.

**Consecuencias.** Detener 2,77 M de registros porque un organismo tecleó mal un campo
sería desproporcionado; cargar mojibake sin contarlo sería deshonesto. El umbral separa
las dos cosas y el conteo queda visible en el registro de cobertura.

**Nota de método.** El patrón de detección se **construye con `chr()`**, no se escribe
como literal ni como escape. Al crear estos archivos, las herramientas de edición
normalizaron los literales tres veces seguidas, y en una de ellas el detector pasó a
marcar como corrupto cualquier texto en español bien escrito. Lo mismo aplica a las
cadenas de prueba: se construyen con `encode`/`decode`, nunca se escriben.

---

## D-014 · El referencial de los procesos en planificación viene de `planning`, no de `tender`
**2026-08-14**

**Contexto.** Tras la primera carga correcta, una consulta al radar devolvió cero filas:
los procesos en estado `planning` salían **sin monto**.

**Causa.** Un release en sola planificación no tiene fila en `tender`, y el normalizador
leía el referencial solo de `tender.value_amount`. El presupuesto de esos procesos está en
`planning.budget_amount`.

**Por qué importa.** En agosto de 2026, **1 059 de 1 546 registros** están en sola
planificación. Sin el monto, el radar —que es la razón para volver cada día— muestra
oportunidades sin la cifra que las hace accionables.

**Decisión.** El referencial se toma de `tender.value_amount` y, si no existe, de
`planning.budget_amount`.

**Consecuencias.** Es el tipo de fallo que no rompe nada: la ingesta pasa, las pruebas
pasan, la base se llena, y el producto queda inservible en silencio. Solo apareció al
mirar los datos cargados con la consulta que haría un usuario. Conviene añadir esa
comprobación a `test_agregados.py` cuando exista.

---

## D-015 · `hecho_mes`: el grano mínimo que reconcilia 24 meses con once años
**2026-08-14**

**Contexto.** `proceso_resumen` guarda una ventana de 24 meses porque es la que alimenta
el radar y el buscador, y guardar once años con objeto contractual reventaría el
presupuesto de 500 MB. Pero los agregados de proveedor —facturación por año, número de
compradores distintos, ratio de baja— necesitan **la serie completa**. No pueden salir de
la misma tabla.

**Opciones.** (a) Ampliar `proceso_resumen` a once años: rompe el presupuesto.
(b) Recalcular los agregados leyendo los 140 ZIP en cada ejecución: una hora cada noche.
(c) Una tabla de hechos al grano mínimo que alimenta agregados.

**Decisión.** (c). `hecho_mes` guarda `(anio, mes, comprador, proveedor, metodo)` con
número de procesos, referencial y adjudicado sumados. **Sin `ocid` ni objeto contractual**,
que es lo que pesa y lo que vive en Parquet.

**Consecuencias.** La ingesta escribe en las dos tablas: `proceso_resumen` solo si el mes
está dentro de la ventana, `hecho_mes` siempre. `agrega.py` lee de `hecho_mes` y recalcula
las tablas enteras en segundos, sin volver a tocar la fuente.

`precio_cpc` y `mercado_cpc_prov` no se pueden calcular así: necesitan los ítems, que solo
vienen por la ruta JSON. Se pueblan desde Parquet cuando esa capa esté publicada. El
esquema de ambas ya está creado en la migración 0002 para que no falte nada después.

---

## D-016 · El objeto contractual está en `description`, no en `title`
**2026-08-14**

**Contexto.** Al probar la clasificación por embeddings, la normalización colapsó 17 473
objetos únicos a 15. Toda la señal desaparecía.

**Dos causas, ambas mías.**

1. **Campo equivocado.** `tender.title` es casi siempre el **código del expediente**
   —`MCO-GADMAA-2024-001-50459`, `Orden de compra CE-20240002564098`—: 17 473 valores
   únicos sobre 17 477 procesos, es decir, uno por proceso. `tender.description` es lo
   que se compra, con 2 786 valores únicos. El normalizador guardaba
   `title or description`, o sea el código.

2. **Normalización destructiva.** Quitaba «adquisición de», «servicio de», «contratación
   de» y similares, además de códigos y cifras largas. Sobre títulos que ya eran solo
   códigos, el resultado era la cadena vacía.

**Decisión.** `proceso_resumen.objeto` se toma de `description`. La normalización solo
quita el código de expediente y el preámbulo fijo del catálogo electrónico («Orden de
compra para adquirir los siguientes productos:»); el resto se conserva.

**Consecuencias.** El fallo era grave y silencioso: el índice de texto completo estaba
construido sobre códigos de expediente, así que **el buscador habría devuelto nada útil**,
y la clasificación no tenía nada que clasificar. Ninguna prueba lo detectaba porque el
campo se poblaba correctamente — con el contenido equivocado.

Obliga a rehacer el backfill. Regla que se deriva: **normalizar de menos es más seguro
que normalizar de más**, y conviene comprobar la cardinalidad antes y después de cualquier
normalización. 17 473 → 15 debió saltar a la vista de inmediato.

**Pendiente de refinar.** Con pocos grupos aparecen nombres repetidos («Medicamentos» dos
veces) y etiquetas genéricas de cajón de sastre («Adquisición de suministros»). Al
construir la taxonomía completa con 400 grupos conviene fusionar por nombre y revisar las
etiquetas vagas a mano: son pocas y es trabajo de una hora.

---

## D-017 · Clave de `hecho_mes` con nulos, y nombre canónico por moda
**2026-08-14**

**Contexto.** El backfill corregido falló en el primer mes con
`NotNullViolation: null value in column "proveedor_ruc"`.

**Causa.** `hecho_mes` tenía clave primaria sobre
`(anio, mes, comprador_ruc, proveedor_ruc, metodo)`, y **las columnas de una clave
primaria son implícitamente `NOT NULL`**. Muchos procesos no tienen proveedor: los que
están en sola planificación son el 68% de un mes en curso. La clave estaba mal elegida.

**Decisión.** `unique ... nulls not distinct` en lugar de clave primaria. PostgreSQL 17
—el que corre Supabase— trata los nulos como iguales a efectos de unicidad, así que se
conserva la garantía sin inventar valores de relleno. Rellenar con cadena vacía habría
ensuciado los `join` contra `entidad`.

**Y de paso, el nombre canónico.** El contrato de datos dice que la grafía se resuelve
por moda y no por el último visto, porque los registros antiguos tienen más erratas.
Estuve a punto de rebajar la regla a «gana el más reciente» por ahorrar espacio.
Antes de hacerlo lo medí: **solo el 1,8% de los RUC tiene más de una grafía**, y guardar
todas las variantes con su frecuencia ocupa unos **4 MB**. La regla se cumple tal como
está escrita, mediante la tabla `entidad_nombre`.

**Consecuencia de método.** Medir antes de rebajar un invariante. El coste que yo suponía
prohibitivo era el 0,9% del presupuesto.

**Apéndice a D-017 · el `NOT NULL` sobrevive a la clave primaria.**
La migración 0003 cambió la clave primaria por `unique nulls not distinct`, y el backfill
**volvió a fallar con el mismo error**. En PostgreSQL, eliminar una clave primaria **no
elimina el `NOT NULL`** que implicaba: las columnas lo conservan como restricción
independiente. Hace falta `alter column ... drop not null` explícito, que es lo que hace
la migración 0004.

Lo que falló en mi comprobación: consulté `pg_constraint`, vi que la restricción única
estaba puesta, y di el resto por hecho sin mirar `information_schema.columns.is_nullable`.
**Verificar el estado que importa, no un estado adyacente.** La comprobación buena fue
insertar la fila exacta que fallaba y ver que entraba.

---

## D-018 · Los índices de `hecho_mes` costaban el 38% del presupuesto y no servían a nadie
**2026-08-14**

**Contexto.** Con 137 de 140 meses cargados, la base llegó a **513 MB — por encima del
techo de 500 del plan gratuito**. El presupuesto proyectado era 460.

**Medición.**

| Tabla | Total | Datos | Índices |
|---|---|---|---|
| `hecho_mes` | 313,7 MB | 140,2 | **173,5** |
| `proceso_resumen` | 173,7 MB | 124,2 | 49,4 |
| `entidad_nombre` | 15,0 MB | 7,7 | 7,3 |

Los índices de `hecho_mes` pesaban **más que sus propios datos**. La causa: una restricción
única sobre cinco columnas, una de ellas `metodo`, que es texto largo repetido 1,23 millones
de veces, más tres índices adicionales.

**Y no los usaba nadie.** `hecho_mes` la escribe la ingesta con `delete` + `copy` por mes,
y la lee `agrega.py` con un recorrido completo de la tabla. Ningún consumidor filtra por
esas columnas.

**Decisión.** Eliminar los cuatro. Resultado medido: **513 MB → 339 MB**.

Se pierde la garantía de unicidad, que la ingesta ya asegura por construcción: borra el
mes antes de insertarlo y deduplica en memoria antes de copiar.

**Consecuencia de método.** Un índice tiene un coste que se paga siempre y un beneficio
que solo existe si alguien consulta por él. En una tabla de escritura masiva y lectura
secuencial, todos los índices son puro coste. Conviene preguntarse **qué consulta lo usa**
antes de crear cada uno — y en este proyecto, además, medir el tamaño después.

---

## D-019 · La tesis del producto se medía sobre dos años, no sobre uno
**2026-08-14**

**Contexto.** Al contrastar los agregados calculados contra las cifras documentadas, el
ratio de baja cuadró al tercer decimal —Cotización 0,951 contra 0,951— pero **la métrica
central del producto no**: el tramo de 500 K a 2 M daba 8,1 compradores distintos por
proveedor frente a los 15,6 documentados.

**Causa.** El script de análisis original acumulaba compradores distintos sobre **2023 y
2024 juntos**; `entidad_ano.n_contrapartes` los cuenta **dentro de un solo año**. Dos
métricas distintas con el mismo nombre. Reconstruido desde `hecho_mes`:

| Tramo 2024 | 1 año | 2 años | Documentado |
|---|---|---|---|
| 5 K – 25 K | 1,5 | 2,2 | 2,2 |
| 25 K – 100 K | 2,2 | 3,2 | 3,2 |
| **100 K – 500 K** | **4,2** | **6,1** | 6,2 |
| **500 K – 2 M** | **10,2** | **15,5** | 15,6 |
| 2 M – 10 M | 25,6 | 35,1 | 35,5 |
| > 10 M | 53,6 | 79,9 | 79,1 |

La columna de dos años reproduce lo documentado. La cifra no era falsa: estaba **sin
etiquetar**.

**Decisión.** La tesis se enuncia con su ventana explícita. En el producto se usa la
**anual** —1,5 → 2,2 → 4,2 → 10,2 → 25,6 → 53,6— porque es la que responde a «con cuántos
compradores trabajo este año», que es la pregunta del suscriptor. La de dos años queda
como dato de contexto, dicha como tal.

**Consecuencias.** Hay que corregir `propuesta-valor.md`, el `CLAUDE.md` y la propuesta
publicada, donde la cifra aparece como argumento de venta.

La tesis **no cambia**: la escalada monótona está en las dos columnas y sigue siendo el
hallazgo que sostiene el producto. Lo que cambia es que ahora dice de qué ventana habla.

**Consecuencia de método.** El invariante 11 exige mostrar el número de observaciones
junto a cada cifra agregada. Le falta una mitad: **junto a la ventana temporal**. Una
media sin periodo es tan ambigua como una media sin `n`.
