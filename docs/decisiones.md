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

---

## D-020 · Un método sin datos no es un fallo
**2026-08-14**

**Contexto.** La primera publicación de Parquet terminó con `resumen: parcial=2` y una
cascada de reintentos agotados. Agosto de 2026 publicó 509 procesos cuando el CSV —que
sabemos completo— tiene 1 546.

**Causa.** La fuente responde **HTTP 500 con `FileNotFoundException`** cuando **no hay
datos** de ese método ese mes, en vez de devolver un archivo vacío. El código lo trataba
como fallo, agotaba los cuatro reintentos y marcaba el mes como parcial.

Comprobado contra el CSV: los **seis** métodos que «fallaban» en agosto son exactamente
los **seis que tienen cero procesos** ese mes — licitación de seguros, cotización, menor
cuantía, catálogo de mejor oferta, bienes y servicios únicos, y contrataciones con
empresas públicas internacionales.

**El mes estaba completo. Fui yo quien lo etiquetó mal.**

**Decisión.** Se distinguen tres situaciones: `sin_datos` (500 con `FileNotFoundException`,
no es fallo y no se reintenta), `metodos_fallidos` (502, tiempos de espera, respuesta
truncada) y `pendiente` (fallaron todos). Solo la segunda marca el mes como parcial.

**Por qué importa más de lo que parece.** Una advertencia que salta sin motivo **entrena a
ignorarla**. Si todos los meses aparecen como parciales, la etiqueta deja de significar
nada — justo lo contrario de para lo que existe el registro de cobertura. Un aviso falso
no es ruido inocuo: destruye el valor de los avisos verdaderos.

**Y de paso, la cobertura del Parquet no se registraba en ningún sitio.** La capa CSV
lleva su registro en `cobertura` desde el principio; la JSON no llevaba ninguno, así que
un mes con métodos realmente fallidos quedaba publicado y en silencio. Se añade
`cobertura_parquet` (migración 0006).

---

## D-021 · Fusionar categorías que nombran lo mismo
**2026-08-14**

**Contexto.** La primera taxonomía dio 400 grupos y **solo 257 nombres distintos**. Las
categorías con más procesos eran variantes de la misma cosa:

- «Material de oficina» partido en **7 grupos**, 28 114 procesos entre todos.
- «Toner para impresora» en **13 grupos**.
- «Productos de limpieza» en 5, «Medicamentos» en 9.

**Por qué rompe el producto.** El benchmark de precio se calcula por categoría. Repartida
entre siete, cada mediana sale sobre un séptimo de las observaciones — y el umbral de
`n < 5` empieza a ocultar categorías que en realidad tienen miles de procesos. El
tamaño de mercado por sector queda igualmente partido.

**Causa.** Con 400 grupos sobre ~50 000 textos únicos, el agrupamiento produce grupos
semánticamente adyacentes y el modelo los bautiza igual. No es un fallo del modelo: es que
400 es más granularidad de la que el dominio tiene.

**Decisión.** Un paso de fusión posterior que agrupa categorías por **similitud de sus
nombres**, con umbral de 0,92 de coseno. Quedan **242 categorías**. Se fusiona por el
nombre y no por los textos porque son 400 embeddings en vez de 50 000, y el nombre ya
condensa el significado del grupo.

El representante de cada fusión es **el grupo con más procesos**: su nombre es el que más
gente verá.

**Y una lección de espacio.** El `update` masivo que asigna categorías dejó casi 300 MB de
tuplas muertas: la base pasó de 365 a **662 MB**, por encima del techo de 500. Hace falta
`vacuum full` después de cualquier actualización masiva, y está incorporado al paso.

---

## D-022 · La ingesta diaria descategorizaba el radar cada mañana
**2026-08-15**

**Contexto.** Tras la primera ejecución programada sin intervención, los procesos
clasificados bajaron de **266 794 a 262 244**.

**Causa.** La ingesta hace `delete` + `copy` del mes para ser idempotente, así que las
filas recargadas entran con `categoria_id` vacío. El trabajo diario recarga el mes en
curso y el anterior — que son **exactamente los dos meses que alimentan el radar**.

**Por qué importa.** El radar filtra oportunidades por la categoría del suscriptor. Sin
categoría, los procesos más recientes no aparecen en ningún perfil. El producto se
degradaba solo cada mañana, en su función principal, y sin ningún error visible: la
ingesta terminaba con éxito y los agregados también.

**Decisión.** Un paso `--pendientes` en el trabajo diario, después de la ingesta y antes
de los agregados. Asigna categoría **por coincidencia de texto normalizado** contra lo ya
clasificado, sin llamar a la API: los objetos contractuales se repiten mucho —2 786 textos
únicos en 17 477 procesos— así que cubre la mayoría. Lo que no coincida espera a la
reconstrucción semanal, que sí embebe.

**Consecuencia de método.** Una operación idempotente que borra y reescribe **pierde todo
lo que otros procesos añadieron a esas filas**. Al diseñar un `delete`+`copy` hay que
preguntarse qué columnas las escribe alguien más — aquí, `categoria_id`. Es un fallo que
ninguna prueba detecta porque cada pieza funciona bien por separado.

---

## D-023 · Las funciones añadidas al final quedaban después del guard
**2026-08-15**

**Contexto.** La fusión de categorías falló en Actions con
`NameError: name 'fusionar' is not defined`, aunque la función estaba escrita en el
archivo y el módulo importaba sin error.

**Causa.** Añadí `fusionar()` y `asignar_pendientes()` **al final del archivo**, con un
append. `clasifica.py` termina en el bloque `if __name__ == "__main__": raise
SystemExit(main())`, así que al ejecutarse el módulo Python llega al guard, llama a
`main()`, y las funciones que vienen después todavía no se han evaluado.

Afectaba a las dos: `--pendientes` —el arreglo de D-022, que corre a diario— también
habría fallado.

**Por qué no lo detectó nada.** El módulo **importa bien**: al importar, Python sí evalúa
el archivo entero y las funciones quedan definidas. `python -c "import clasifica"` pasa.
Solo falla cuando se ejecuta como programa. Ninguna prueba lo cubría porque todas
importan el módulo en vez de invocarlo.

**Decisión.** El guard vuelve al final, y una prueba comprueba dos cosas: que las cuatro
funciones son alcanzables, y que **el archivo termina en el guard**.

**Consecuencia de método.** Añadir código al final de un archivo con `append` es seguro en
un módulo sin guard y peligroso en uno con él. Es el tercer fallo de la sesión causado por
editar a ciegas en vez de con la herramienta de edición, que habría exigido decir dónde.

---

## D-024 · `VACUUM` no cabe dentro de una transacción
**2026-08-15**

**Contexto.** La fusión de categorías falló con
`psycopg.errors.ActiveSqlTransaction: VACUUM cannot run inside a transaction block`.

**Matiz importante: la fusión sí se aplicó.** 400 categorías pasaron a 242, con cero
nombres duplicados y cero procesos apuntando a una categoría inexistente. Lo único que
no ocurrió fue la recuperación de espacio. Conviene decirlo porque el flujo aparece en
rojo y el dato estaba bien: **un fallo al final no invalida lo anterior**, y saber cuál de
las dos cosas pasó es la diferencia entre repetir el trabajo o no.

**Causa.** `carga.conexion()` abre con `autocommit=False`, así que todo va dentro de una
transacción. Intenté sortearlo con `cur.execute("commit")`, que no es la forma de cerrar
una transacción en psycopg3 y dejó la conexión igualmente en estado transaccional.

**Decisión.** Una función `compactar()` que abre **su propia conexión con autocommit**
para el `VACUUM FULL`, después de que la transacción principal haya confirmado con
`con.commit()`.

**Consecuencia de método.** Las operaciones de mantenimiento de PostgreSQL —`VACUUM`,
`CREATE INDEX CONCURRENTLY`, `REINDEX CONCURRENTLY`— no admiten transacción. Si el módulo
de conexión abre siempre con transacción, hacen falta dos vías, y conviene que la segunda
sea explícita y con nombre en vez de un apaño dentro de la primera.

---

## D-025 · RLS: la base estaba abierta de par en par
**2026-08-15**

**Contexto.** Antes de escribir la primera pantalla, auditoría del estado de seguridad:
**las 16 tablas con RLS desactivado y cero políticas.**

**Por qué era grave.** Supabase expone por API todo lo que vive en el esquema `public`, y
la clave anónima va **incrustada en el JavaScript del navegador**. Sin RLS, cualquiera con
esa clave podía leer y escribir la base entera: los suscriptores, la lista de espera, y
`precio_cpc` — que es la función que se cobra. **El muro de pago habría sido decorativo**:
el benchmark se habría podido descargar entero con una petición.

**Decisión.** RLS en todas las tablas y la frontera del wireframe llevada al dato:

- **Abierto:** `proceso_resumen`, `categoria`, `entidad_ano`, `baja_metodo`,
  `mercado_cpc_prov`, `cobertura`. Es el canal de adquisición y lo que se indexa.
- **Tras el muro:** `precio_cpc` y `relacion`, con política que comprueba plan activo
  **por correo**, no por la UUID de `auth.users` (invariante 7).
- **Solo lo suyo:** `suscriptor`, `perfil`, `envio_log`.
- **Escritura anónima únicamente en `lista_espera`**, que es el mecanismo de conversión de
  la fase 3: cualquiera se apunta, nadie la lee.
- **Sin política:** `hecho_mes` y `entidad_nombre`, insumos de agregación que no son
  producto. Solo los ve `service_role`, que salta RLS.

**El enmascaramiento como frontera, no como cortesía.** El RUC de persona natural contiene
la cédula. La vista `entidad_publica` lo enmascara y **el acceso directo a `entidad` queda
negado**, así que el dato sin enmascarar no tiene ninguna vía hacia el navegador. No
depende de que un componente se acuerde de ocultarlo.

**Y una confirmación del método (regla 2.3).** La primera versión de la vista usaba
`security_invoker`, que la ejecuta con los permisos de quien llama — y a `anon` se le había
revocado el acceso a `entidad`, así que devolvía 401. **Mirar las políticas no lo habría
detectado**: se detectó probando con la clave anónima real contra la API pública, que es
el nivel donde el fallo ocurre.

---

## D-026 · PostgREST corta en 1.000 filas y la portada mentía por un factor de 57
**2026-08-15**

**Contexto.** Primera construcción de la aplicación. La portada mostraba **56,1 M** «en
juego» sobre 15 194 procesos; el radar, **1,2 MM** sobre los 60 mayores. Sesenta procesos
no pueden sumar veinte veces más que quince mil.

**Causa.** PostgREST devuelve **como máximo 1 000 filas** por petición. El conteo
(`count: "exact"`) era correcto porque lo calcula el servidor, pero la suma se hacía en el
cliente sobre las filas devueltas: sumaba mil de quince mil. **La cifra real son 3 203
millones** — la portada se equivocaba por un factor de 57, en el número principal del
producto.

**Cómo apareció.** Comparando la misma magnitud en dos pantallas. No hubo error, ni
excepción, ni prueba en rojo: dos números plausibles que no cuadraban entre sí. Es la
tercera vez en el proyecto que un fallo se detecta por contraste y no por una alarma
(D-019 y D-014 fueron igual).

**Decisión.** Los totales se precalculan en vistas —`v_radar_resumen`, `v_portada`— y la
aplicación los lee. **Nunca se agrega en el cliente.**

**Consecuencia de método.** La regla ya existía —«los agregados se precalculan y la
aplicación los lee»— y la salté porque para tres cifras parecía desproporcionado montar
una vista. Además de dar cifras falsas, sumar en el cliente obliga a traer miles de filas
para tirarlas, que es justo lo que consume el egress de 5 GB del plan gratuito.

Añadir a las trampas del `CLAUDE.md`: **cualquier `sum`, `count` o `avg` hecho en
JavaScript sobre datos de Supabase está mal por defecto.** Si el resultado cabe en una
fila, es una vista.

## D-027 — El tramo se calcula sobre el último año completo

**14 de agosto de 2026.**

`construir_entidad()` tomaba el tramo del **último año con actividad**. Para casi todos los
proveedores vivos ese año es 2026, que va por agosto y con datos aún sin cerrar. Resultado:
el tamaño de la empresa se medía con dos tercios de año.

PLASTILIMPIO S.A. facturó **7 279 531 USD en 2025** y aparecía en el tramo `500K-2M` por sus
824 145 USD de 2026.

Alcance medido sobre los datos cargados:

| | |
|---|---|
| Proveedores con actividad en 2025 o 2026 | 20 004 |
| Clasificados distinto según el año que se use | **3 198** |
| Sin actividad en 2026 → tramo viejo o ausente | 10 336 |
| Segmento objetivo (100K–2M) con 2026 | 2 694 |
| Segmento objetivo (100K–2M) con 2025 | **5 928** |

El segmento objetivo es el eje del modelo de negocio (D-004: 6 697 empresas en la banda
100K–2M) y la aplicación filtra por él. Con el defecto, **más de la mitad del mercado
direccionable quedaba fuera de su propio segmento**.

**Decisión.** El tramo sale del último año **anterior al año en curso**. Si un proveedor solo
tiene actividad en el año en curso —es decir, entró al mercado este año— se usa ese, porque
clasificarlo mal es mejor que dejarlo sin tramo y fuera de todo segmento.

Es el mismo principio que D-009 y el invariante 10: **un periodo sin cerrar no sostiene una
estadística**. La regla existía para los meses y no se había aplicado a los años.

Dos pruebas en `pruebas/test_agregados.py` lo fijan, una por cada rama.

## D-028 — El esquema del Parquet se declara, no se infiere

**15 de agosto de 2026.**

`_escribir_parquet` usaba `pa.Table.from_pylist(filas)`, que deduce el tipo de cada
columna del primer lote de filas. Funcionó en 137 meses y falló en 2023-03:

```
pyarrow.lib.ArrowTypeError: Expected bytes, got a 'int' object
```

La fuente entrega `planning.budget.id` como texto casi siempre y como número a veces.

**El fallo visible era el menor de los dos problemas.** El otro no daba error: con el
tipo inferido, `cpc` podía salir como texto en un mes y como entero en otro. Los 140
archivos dejarían de ser **un** dataset — leerlos con un comodín falla, o peor, descarta
columnas en silencio. Eso solo se habría notado al construir el benchmark encima, que es
la función que se cobra, y para entonces el diagnóstico habría costado un día.

**Decisión.** `ESQUEMAS` en `publicar.py` declara el tipo de cada columna de cada tabla.
Los valores se convierten antes de escribir; lo que no se puede convertir vale nulo,
porque perder un campo mal formado es mejor que abortar un mes de 16 000 procesos.

El esquema manda sobre los datos en las dos direcciones:

- Un campo que la fuente deja de enviar sale como **columna de nulos**, no como columna
  ausente.
- Un campo que `detalle.py` extrae y `ESQUEMAS` no declara **detiene la publicación**.
  Al revés se perdería sin ruido, que es exactamente la clase de fallo que este proyecto
  ya ha pagado cuatro veces (regla 6 de `metodo.md`).

Se declara en texto plano y no con tipos de pyarrow porque el entorno local es Windows
ARM64, donde no hay ruedas: el módulo tiene que poder importarse sin pyarrow.

**Consecuencia.** Los meses publicados antes de este cambio se escribieron con el
esquema inferido y no son comparables con los nuevos. Se republican los 140, en cuatro
tandas paralelas por rango de años: un solo trabajo pasaría del límite de 360 minutos.

## D-029 — La alarma de codificación medía sobre el denominador equivocado

**15 de agosto de 2026.**

La republicación de los 140 meses de Parquet se detuvo en 2019-09 con:

```
el 3.6% de las líneas viene doblemente codificado, por encima del umbral del 1%.
Eso ya no es suciedad de captura sino un cambio en la fuente.
```

**Era un falso positivo, y se llevó por delante dieciséis meses** (2019-09 a 2020-12),
que no tenían nada malo.

Los bytes, mirados con `repr()` y no en pantalla:

| | |
|---|---|
| Archivo | `releases_2019_septiembre_licitacion.json`, 4 847 691 bytes |
| Líneas | **28** |
| Líneas con mojibake | 1 |
| Fragmentos rotos | **1** — `TOPOGRÁFICO` como `TOPOGR` + `Ã` + `U+0081` |

Un carácter roto en 4,8 MB da «3,6% de las líneas» porque un JSON de un mes son 28
líneas de 170 KB. La misma corrupción daba 0,09% en un CSV de 1 070 líneas: el umbral se
calibró contra CSV (D-013) y se aplicó a JSON sin volver a medirlo.

**El tamaño del fichero no puede decidir si la fuente cambió de codificación.**

**Decisión.** La alarma mide sobre el **texto acentuado**, que es el denominador que
responde a la pregunta real: un cambio de codificación en origen rompe *todos* los
acentos, no uno. Se añade además un suelo absoluto de 20 fragmentos, porque en un fichero
con doce acentos uno roto es una errata de captura.

`fraccion_lineas_afectadas` se conserva para el informe de cobertura, pero no decide.

**Segundo defecto, del mismo fallo.** `publicar_mes` no capturaba `ErrorCodificacion`:
la excepción subía y abortaba el rango entero. El fallo de un mes es información sobre
ese mes, no sobre los quince siguientes. Ahora se anota como `degradado` y continúa —
que es lo que ya hacía con `ErrorDescarga` y lo que manda `CLAUDE.md` §4.

Cuatro pruebas nuevas, incluidas las dos direcciones: que un carácter roto en un JSON
enorme **no** detenga, y que una fuente que cambia de codificación **sí**.

## D-030 — La taxonomía sale del CPC de la fuente, no de agrupar texto

**15 de agosto de 2026.** Sustituye el enfoque de D-021.

### Lo que falló

La taxonomía se construía agrupando embeddings del objeto contractual con k-means y
pidiendo a un modelo que bautizara cada grupo. D-021 ya detectó que 400 grupos daban 257
nombres distintos y añadió una fusión por parecido de nombres. **No bastó.** Medido sobre
las 242 categorías que llegaron a producción:

| Familia | Categorías | Procesos |
|---|---|---|
| «oficina» | **12** | 74 209 |
| «medicamento» | **15** | 24 525 |
| «impresora» | 10 | 13 361 |
| «limpieza» | 5 | 36 832 |

Más duplicados que ni siquiera necesitaban un modelo para detectarse: «Equipo médico»,
«Equipo Médico» y «Equipos médicos» como tres categorías.

Y el que ordena todo lo demás: una categoría con **4 308 procesos** llamada literalmente

> «Medicamento antiviral y antibiótico no, es más genérico: Med»

Es el razonamiento del modelo, cortado a los 60 caracteres del campo, publicado como
nombre de categoría. **Nadie validaba la salida del modelo.**

### Por qué el parche no podía funcionar

Fusionar por parecido de nombres es un parche sobre un parche. Nada garantizaba que dos
grupos de la misma cosa recibieran nombres parecidos, porque cada grupo se bautizaba por
separado y sin vocabulario común. Y bajar el umbral no arregla nada: «Papel de oficina» y
«Material de oficina» son nombres distintos de cosas que a veces son la misma y a veces
no. La información para decidirlo no está en los nombres.

### La taxonomía ya existía

Medido contra la fuente (2024-03, subasta inversa y menor cuantía):

- **1 708 de 1 708** procesos con ítems traen `classification.id` — el CPC. El 100%.
- Con su **descripción oficial en español**.
- **Jerárquico por truncamiento**: 3 dígitos → 155 grupos, 4 → 291, 5 → 353.
- Los grupos son coherentes: `87141` mantenimiento de vehículos, `54121` construcción de
  edificaciones, `35260` medicamentos.

Y `precio_cpc` **ya estaba diseñada con el CPC como clave** desde la migración 0002. La
tabla `categoria` era una segunda taxonomía, paralela y peor, compitiendo con la que el
benchmark necesita.

### Decisión

1. **La categoría es la subclase CPC, 5 dígitos.** ~350 grupos. Oficial, estable entre
   ejecuciones sin depender de una semilla, y jerárquica si algún día hace falta subir o
   bajar de nivel.
2. **`precio_cpc` sigue con el CPC completo**, de 8 a 12 dígitos. Comparar precios exige
   el producto exacto: «Amoxicilina 500 mg, caja x blíster», no «medicamentos». Los dos
   niveles son complementarios, no alternativos.
3. **`proceso_resumen.cpc`** —declarada en la 0001 y **nula en los 280 020 procesos**,
   porque la ruta CSV no la trae— se puebla desde los ítems del Parquet, tomando el CPC
   **dominante por monto**: cien líneas de clips no convierten en papelería una compra de
   computadoras.
4. **Al modelo solo se le pide acortar el nombre oficial**, con las descripciones
   delante. Trabajo acotado: ~350 llamadas, una vez, y no se repiten en cada ejecución
   porque el nombre de una categoría existente se conserva.
5. **La salida del modelo se valida.** Longitud, número de palabras, mayúscula inicial,
   sin cifras y sin las frases que delatan una respuesta en vez de un nombre. Lo que no
   pasa **no se publica**: se cae a la descripción oficial recortada. Es preferible un
   nombre burocrático de la fuente a uno inventado que nadie ha comprobado.

`clasifica.py` deja de ser la fuente de la taxonomía. Su maquinaria de embeddings queda
para lo que sí hace bien —emparejar un texto con una categoría existente—, que es como se
resolverá el ~5% de procesos que no traen ítems.

### Lo que enseña

El proyecto gastó embeddings, agrupamiento, un modelo de 70 B y dos rondas de fusión para
reconstruir peor una clasificación que la fuente entregaba gratis y completa en cada
registro. La pregunta «¿ya viene esto en el dato?» tenía que haber ido antes que
«¿cómo lo calculo?».

## D-031 — El objeto de un proceso en planificación vive en `planning.rationale`

**15 de agosto de 2026.**

En el radar y en las fichas, la mayoría de las oportunidades salían con un guion donde
debe decir qué se compra. Medido:

| Estado | Sin objeto |
|---|---|
| **planificación** | **13 176 de 13 176 — el 100%** |
| abierto | 0 de 2 018 |
| cerrado | 0 de 263 493 |

No es aleatorio: es estructural, y **no es un problema de la fuente**. Un proceso en
planificación todavía no tiene bloque `tender` —no se ha convocado nada—, así que
`tender.description` no existe. Lo que sí trae es `planning.rationale`, y en el CSV de
julio de 2026 viene poblado en **4 040 de 4 040 filas**:

```
rationale = 'CONSULTORÍA PARA EL DISEÑO, DESARROLLO E IMPLEMENTACIÓN DE UN…'
```

La ingesta solo miraba `tender`. Es la misma familia que D-014, que ya había descubierto
que el presupuesto de esos procesos vive en `planning.budget_amount`: se arregló el monto
y no se miró el resto del bloque.

**Decisión.** El objeto se toma de `tender.description`, luego `planning.rationale`, y
solo después `tender.title`. El orden importa: `title` es el código del expediente
(D-016), así que dejarlo ganar devolvería códigos y el fallo volvería por otra puerta.

**Lo que enseña.** El radar es la razón para volver cada día, y el 87% de sus filas no
decía qué se compra. Nada falló: la ingesta terminó en verde, las pruebas pasaron y la
columna estaba poblada al 95% *sobre el total de la tabla*, porque los 263 493 procesos
cerrados la tienen. **Una cobertura global sana escondía un agujero del 100% en el
subconjunto que es el producto.** Las comprobaciones de poblado tienen que ir por estado,
no sobre el total.

**Lo que sigue sin estar, y es de la fuente:** solo el 44,5% de los procesos en
planificación declara `budget_amount`. Esa mitad no tiene monto porque la entidad aún no
lo ha presupuestado, y ahí no hay nada que arreglar — se muestra sin cifra y se dice.

## D-032 — El umbral de cercanía se queda en 0,55 y el hueco se declara

**16 de agosto de 2026.**

Los procesos en planificación no pueden recibir CPC —el JSON troceado por método no
contiene ni un release en esa fase (D-030)—, así que se les busca la categoría más
cercana por embedding del objeto contractual. La primera versión usó un umbral de 0,55
elegido a ojo y dejó fuera al 86%.

**Lo primero que hice fue mejorar la comparación, no bajar el umbral.** Comparar el
rótulo de la categoría —«Medicamentos», dos palabras— contra un objeto contractual entero
no funciona: se pasó a comparar contra la descripción oficial del CPC, que está escrita en
el mismo registro. Los asignados subieron de 8 874 a 12 561.

**Lo segundo fue mirar los emparejamientos, no el porcentaje.** La distribución dice
cuántos entran; solo los ejemplos dicen si son correctos:

| Parecido | Ejemplo |
|---|---|
| 0,40 | `alprostadil` → **Equipos Informáticos** |
| 0,39 | `construcción de baterías sanitarias` → **Productos Veterinarios** |
| 0,51 | `alquiler de maquinaria para relleno sanitario` → **Servicios Agroquímicos** |
| 0,48 | `estudios y diseños para tanque reservorio de agua` → **Peces Y Servicios** |
| 0,49 | `reactivos para uroanálisis` → **Circuitos Integrados Electrónicos** |

**Decisión: el umbral se queda en 0,55.** Bajarlo llenaría la cifra de cobertura con
basura. Un dato falso que parece bueno es peor que un hueco visible — el usuario filtra
por una categoría, no encuentra lo suyo, y no tiene forma de saber por qué.

**Por qué los que sobran son difíciles, y no es culpa del método.** Lo que queda sin
asignar es sobre todo **obra pública y servicios**: caminos, cerramientos, adecuaciones,
estudios. Esas contrataciones no declaran ítems con CPC, así que su subclase no está en
el catálogo, que se construye desde los ítems. No hay a qué emparejarlas. Forzarlas a una
categoría de bienes sería inventar.

**Consecuencia en las pruebas.** El umbral de `test_los_meses_del_radar_estan_clasificados`
baja de 0,7 a 0,5, y se añade la invariante que sí debe ser del 100%:
`test_todo_proceso_con_cpc_tiene_categoria`. Esa distingue una regresión real —la ingesta
descategorizó el radar— de una limitación conocida y declarada.

Bajar el umbral de una prueba para ponerla en verde suele ser hacer trampa. Aquí no lo es
porque **el techo alcanzable cambió a propósito** y hay una comprobación nueva, más
estricta, que cubre lo que la vieja pretendía cubrir.

## D-033 — `unit.value.amount` es el total de la línea, no el precio unitario

> **CORREGIDO PARCIALMENTE POR D-041.** Todo lo que sigue es cierto **para subasta
> inversa**, que es el único método que se midió aquí. En licitación, menor cuantía,
> cotización, contratos entre entidades y bienes y servicios únicos, el mismo campo es
> el **precio por unidad** — verificado al céntimo. La conclusión correcta no es «es el
> total» sino «depende del método». **No aplicar esta entrada sin leer D-041.**

**16 de agosto de 2026.** Corrige el benchmark, que es la función que se cobra.

`detalle.py` guardaba `tender.items[].unit.value.amount` en una columna llamada
`precio_unitario`, y `precios.py` publicaba ese valor como distribución de precio y
`cantidad × ese valor` como tamaño de mercado.

**Las dos cosas estaban mal.** El campo trae el **total de la línea**.

### Cómo se vio

No por el benchmark —que parecía razonable— sino por una cifra absurda a su lado:
`mercado_cpc_prov` daba **8 167 678 542 326 USD** para un CPC en un año. La contratación
pública entera del Ecuador ronda los 7 000 millones anuales.

Al mirar los ítems, el patrón saltó solo:

```
LECHE LIQUIDA ULTRAPASTEURIZADA   q = 1 260 000   amount = 1 260 000
Loratadina 10 mg, caja x blíster  q =   600 000   amount =    45 600
```

600 000 pastillas por 45 600 USD son **0,076 la pastilla**, que es un precio real. Como
«precio unitario» serían 45 600 USD por pastilla.

### La medición que lo cierra

688 procesos de un solo ítem con cantidad > 1 (2025-12, subasta inversa), comparando
contra el monto adjudicado del proceso:

| Hipótesis | Error mediano |
|---|---|
| `amount` es el **total de la línea** | **7,0%** |
| `amount` es el precio unitario | 15 323% |

Y ese 7,0% no es ruido: **es la baja de la subasta inversa**, referencial contra
adjudicado. El residuo confirma la hipótesis en vez de solo no contradecirla.

### Decisión

- El precio unitario es `amount / cantidad`.
- El tamaño de mercado es la **suma de `amount`**, sin multiplicar por la cantidad.
- La columna sigue llamándose `precio_unitario` en el Parquet porque renombrarla obliga
  a republicar 140 meses; se anota en `detalle.py`, en `precios.py` y aquí. **Un nombre
  heredado y engañoso es deuda: quien lo lea sin este aviso repetirá el error.**

### Por qué el ensayo en seco no lo atrapó

Lo ejecuté y lo di por bueno. Miré el número de filas —10 424, razonable— y las medianas
—117,17 USD, razonable—, y no miré la magnitud de `mercado_cpc_prov`.

**La mediana no delataba nada porque la cantidad mediana es 1.** Para un ítem de una
unidad, total y precio unitario son el mismo número. El error solo aparece en las compras
grandes, que son justo las que le importan al cliente.

Regla que faltaba y ahora es prueba: **una cifra agregada se comprueba contra una
magnitud conocida del mundo**, no solo contra su propia forma. Un mercado por encima del
PIB del país es imposible por construcción, y eso se puede afirmar en un `assert`.

## D-034 — Las fechas de un proceso abierto llevan hora

**16 de agosto de 2026.** Lo señaló el cliente, no una prueba.

`cierra` se guardaba como **fecha**: la ingesta recortaba el texto de la fuente a diez
caracteres. La fuente publica `2026-07-09T14:00:00-05:00` y nosotros escribíamos
`2026-07-09`.

Para quien tiene que presentar una oferta, esa diferencia es el producto:

> «Cierra el 9» y «cierra el 9 a las 14:00» son decisiones distintas. En la primera se
> prepara una oferta; en la segunda se descarta o se corre.

Estábamos redondeando a peor y sin decirlo. Medido sobre 2026-07: de 5 717 procesos con
`tender`, **1 987 traen hora de publicación y 652 hora de cierre**, todas reales y en
horario de Ecuador. No es un campo anecdótico.

**Decisión.** `cierra` pasa a `timestamptz`, y se añaden dos fechas que la fuente da y no
guardábamos:

| Columna | Qué es | Por qué importa |
|---|---|---|
| `publicado` | Inicio del periodo de ofertas | Única forma de medir si el radar llega a tiempo |
| `preguntas_hasta` | Cierre del periodo de preguntas | En la práctica, la **primera** fecha que un oferente debe respetar |

La interfaz muestra minutos por debajo de una hora, horas por debajo de dos días, y días
por encima. Un «1 d» donde quedan 27 horas y un «1 d» donde quedan 47 son lo mismo en
pantalla y no lo son en la realidad.

`v_radar_resumen` comparaba `cierra` contra `current_date`; con hora hay que comparar
contra `now()`, o un proceso que cerró hoy a las 09:00 seguiría contando como abierto a
las 18:00.

**Lo que enseña.** Ninguna prueba podía detectar esto: la columna estaba poblada, el tipo
era coherente y las cifras cuadraban. Faltaba **preguntarle al dato para qué se usa**. Un
campo llamado `cierra` en un producto de oportunidades tiene que soportar la pregunta
«¿me da tiempo?», y esa pregunta no se responde con una fecha.

## D-035 — El detalle de lo abierto entra en Postgres; el resto sigue en Parquet

**16 de agosto de 2026.** Matiza el invariante 1 y confirma el 3.

La ficha de un proceso necesita sus ítems, sus oferentes, sus pujas y sus consultas. Eso
solo viene por la ruta JSON y vivía únicamente en Parquet, donde la aplicación no puede
consultarlo por `ocid`.

### La alternativa que se descartó, y por qué

Llamar al SERCOP en vivo al abrir la ficha. Es lo más barato en espacio y lo primero que
uno propone. Medido contra su API antes de decidir:

| Prueba | Resultado |
|---|---|
| 20 peticiones seguidas (0,3 s entre ellas) | **20 × HTTP 429** |
| 8 peticiones a 30/min — la mitad del límite declarado | **8 × 429** |
| 1 petición tras 9 minutos de pausa | **429** |
| 1 petición más, 20 s después | **429** |

Sigue bloqueado **doce minutos después**, con dos peticiones en ese rato. Y la respuesta
no trae ninguna cabecera `X-RateLimit-*`, así que no hay forma de auto-regularse.

En Vercel las funciones comparten IP: **un usuario abriendo cinco procesos dejaría la
pantalla rota para todos los demás durante un cuarto de hora**, de forma intermitente y
sin mensaje que lo explique. El invariante 3 existe exactamente para esto; ahora hay
medición en vez de principio.

### El tamaño, que es lo que decidió el alcance

Medido sobre 1 264 procesos de subasta inversa —el método con más detalle—:

| Bloque | Filas/proceso | Bytes/proceso |
|---|---|---|
| Ítems | 1,4 | 152 |
| Oferentes | 4,1 | 203 |
| Pujas | 3,4 | 204 |
| **Consultas** | 7,8 | **5 824** |
| Lotes | 1,0 | 142 |

Las consultas son el **89% del peso**. La primera estimación —«unos 30 MB para los 15 800
procesos abiertos»— salía **216 MB**, siete veces más, porque no contó el texto.

Lo que salvó el diseño fue mirar el desglose por estado: de esos 15 800, **13 210 están en
planificación y no tienen detalle que traer** — el JSON troceado por método no contiene ni
un release en esa fase (D-030). El objetivo real son los **2 000 en estado `abierto`**:
**~29 MB**, dentro de los 44 libres.

### Decisión

Cinco tablas con el detalle de los procesos **`abierto`**, reemplazadas enteras en cada
pasada de la ingesta diaria. Cuando un proceso cierra, su detalle sale de Postgres y se
queda en el Parquet, que es el archivo permanente. **La tabla no crece con el tiempo:
gira.**

Esto no rompe el invariante 1, lo acota: el invariante existe porque el detalle de 2,77
millones de procesos no cabe en 460 MB. El de 2 000 sí, y es justo donde el cliente actúa.

`detalle.py` pasa además a extraer **consultas y lotes**, que llevaban en el registro
desde el principio sin que nadie los mirara. Las consultas son el único sitio del dato
abierto donde se lee **por qué** se descalifica a un oferente, y no se pueden buscar entre
procesos en ningún otro lugar — ni en la ficha del propio SERCOP.

### Lo que enseña

Estimé 30 MB de memoria y eran 216. La diferencia entera estaba en un campo de texto que
no había medido. **Una estimación de espacio sin medir el campo más grande no es una
estimación**, y aquí habría significado descubrirlo al llenar la base.

## D-036 — El radar solo muestra lo que todavía se puede ofertar

**16 de agosto de 2026.** Lo reportó el cliente, dos veces.

El radar es «la razón para volver cada día» (D-008) y mostraba 15 210 procesos como
oportunidades. Al medirlos:

| | |
|---|---|
| Con fecha de cierre **futura** | **0** |
| Con fecha de cierre **ya pasada** | 386 |
| Sin cierre declarado, de hace menos de 45 días | 3 417 |
| Sin cierre declarado y **viejos** | **11 407** |

**El 78% no se podía ofertar.** Había procesos etiquetados `abierto` desde julio de 2025:
trece meses.

### La causa

El campo `tag` es la máquina de estados del proceso, y esa parte es correcta. Lo que no
es cierto es la inferencia que hacíamos encima: **que `abierto` signifique «se puede
ofertar hoy»**. La fuente no siempre publica el cierre —solo el 11% de los procesos
convocados lo declara—, así que un proceso se queda en `abierto` para siempre aunque
terminara hace un año.

### La ventana sale de medir

Sobre los 1 512 procesos que declaran inicio y cierre:

| Mediana | p90 | Máximo |
|---|---|---|
| **6,7 días** | 14,0 | **44,8** |

Ninguno vivió más de 45 días. Se usan **60** como margen sobre el máximo observado y
sobre el retraso de publicación de la propia fuente.

### Decisión

Una vista, `v_radar`, con la regla en un solo sitio: cierre futuro declarado, **o** sin
cierre y con menos de 60 días. Y `v_radar_resumen` pasa a **leer de esa vista** en vez de
calcular aparte.

Eso segundo importa tanto como lo primero. Con la regla repetida en cada consulta, tarde
o temprano la cabecera dice 15 210 y la tabla de debajo muestra 3 417 — y **una cifra que
no cuadra con lo que hay justo debajo destruye la confianza más rápido que un dato
ausente**. Hay una prueba que compara las dos.

### Lo que enseña

Ninguna comprobación podía atrapar esto, porque el dato era correcto: los procesos
existían, sus estados venían de la fuente y las cifras cuadraban entre sí. **Lo que
fallaba era la promesa de la pantalla**, no el dato que la llenaba.

Es el mismo patrón que D-034: un campo llamado `cierra` tiene que aguantar la pregunta
«¿me da tiempo?», y una pantalla llamada radar tiene que aguantar «¿puedo presentarme a
esto?». Preguntarle al dato para qué se usa no es una fase del trabajo — es la única
prueba que encuentra esta clase de fallo.

## D-037 — `proceso_resumen` perdía el 14% de los procesos, en silencio

**16 de agosto de 2026.** Lo destapó el cliente preguntando por qué TELCONET, con 724
procesos, mostraba **3**.

`a_proceso_resumen` guardaba `anio` y `mes` tomándolos de `date`. Pero `date` en el OCDS
compilado es la **última actualización** del proceso, no su publicación.

Medido sobre el archivo de 2025-04:

| | |
|---|---|
| Filas en el archivo | 28 098 |
| Con fecha del propio abril | 24 038 |
| **Con fecha de otro mes** | **4 060 (14%)** |
| En `proceso_resumen` tras la carga | **24 038** |

`reemplazar` borra y copia **por partición** — `delete where anio=? and mes=?`. Una fila
del archivo de abril con fecha de mayo se insertaba bajo mayo, y al procesar el archivo
de mayo se borraba, porque allí no estaba. **Se caían sin un solo error.**

Y no se caían al azar: se caían **las que más se habían actualizado**, o sea las
adjudicadas y contratadas — justo las que importan para la ficha de un proveedor.

### Por qué las cifras no lo delataron

`hecho_mes` nunca lo sufrió, porque `a_hecho_mes` agrupa por el mes del **archivo**, que
recibe como parámetro. Las dos tablas discrepaban desde el principio:

| | `proceso_resumen` | `hecho_mes` |
|---|---|---|
| Procesos 2025 | 156 918 | **188 198** |
| Proveedores distintos | 5 699 | **17 503** |

Y como los agregados, los tramos y la portada salen de `hecho_mes`, **todas las cifras
del producto eran correctas**. Lo único mal era la lista de contratos de cada proveedor,
que es lo que se mira al entrar en una ficha.

### Decisión

`anio` y `mes` son los del archivo — la partición con la que la fuente reparte los datos
y con la que se borra y copia. `fecha` sigue siendo la fecha real de la fila, que es lo
que se muestra y lo que ordena el radar.

### Lo que enseña

Había una prueba de cardinalidad para las transformaciones (regla 2 del método) y no
saltó, porque entrada y salida del mes cuadraban: 28 098 entraban y 28 098 se escribían.
La pérdida ocurría **en la siguiente carga, de otro mes**.

La regla que faltaba: **dos tablas que derivan del mismo dato tienen que cuadrar entre
sí, y compararlas es barato**. `select count(*)` contra `sum(n_procesos)` habría gritado
desde el primer día — y hay ahora una prueba que lo hace.

## D-038 — Ventana de 12 meses, y la alarma deja de fallar sin motivo

**16 de agosto de 2026.**

Tres cosas que salieron del mismo sitio: la base llegó a **552,5 MB**, por encima del
techo de 500 del plan gratuito de Supabase.

### Por qué creció

No fue el detalle de procesos abiertos que se añadió el día antes: esas cinco tablas
juntas no llegan a 1,5 MB. Fue **D-037**. Al arreglar la pérdida silenciosa del 14%,
`proceso_resumen` pasó de 280 480 a **340 209 filas** y de 7 346 a **24 213 proveedores**.

Recuperar datos correctos cuesta espacio. El reparto:

| Tabla | MB |
|---|---|
| `proceso_resumen` | 266,5 |
| `hecho_mes` | 165,3 |
| resto | ~120 |

### La ventana baja de 24 a 12 meses

Con los datos completos, 24 meses ya no caben en 460 MB. Doce siguen cubriendo de sobra
lo que el producto necesita: ningún proceso vive más de 45 días abierto (D-036), y la
ficha de proveedor muestra actividad reciente. El histórico de once años **no se toca** —
vive en `hecho_mes` y en los Parquet.

**Y faltaba la mitad de la ventana.** `_dentro_de_ventana` impedía *cargar* un mes viejo,
pero nada borraba los que envejecían dentro de la tabla. Con 24 meses no se notó porque
el backfill los cargó todos de golpe; al bajar a 12, sin poda el cambio no habría servido
de nada. **Una ventana que solo se aplica en un sentido no es una ventana.**

### La alarma estaba en el sitio equivocado

Las dos ejecuciones programadas del día fallaron con `PresupuestoExcedido`, **después de
haber hecho todo su trabajo**: la de agregados escribió 264 352 + 168 427 + 256 + 77 704
filas y murió en su última línea. Un correo de fallo cada mañana por un trabajo correcto.

La tentación era silenciar el aviso. **No se silencia una alarma: se le quita el motivo.**
La ingesta ahora poda la ventana y compacta —mantenimiento que siempre hizo falta y nadie
hacía— y *después* comprueba. Si tras eso la base sigue pasada, es un problema de verdad
y el trabajo debe fallar.

### La portada mostraba ceros

`v_portada` expiraba (`57014`) porque la migración 0024 —mía, del día anterior— puso
`v_radar_resumen` detrás de `v_radar`, y `v_portada` la invoca **dos veces**, una por
columna. Ahora se evalúa una sola vez con un `cross join lateral`.

Pero el fallo de fondo estaba en la aplicación:

```ts
total: Number(data?.procesos_historicos ?? 0)
```

Cuando la consulta falla, `data` es nulo y la portada afirma **«0 procesos desde 2015»**.
Un visitante ve un producto vacío y se va. **Un cero es una afirmación**: decirlo cuando
en realidad no se pudo preguntar no es degradar con elegancia, es mentir con buena
tipografía — exactamente lo que costó D-026.

Ahora lanza excepción y hay una pantalla de error que dice qué pasó. Un hueco visible se
arregla; una cifra falsa que parece buena no se detecta hasta que alguien la usa.

### Y la ventana estaba escrita en ocho sitios

Ocho pantallas decían «los últimos 24 meses» sobre datos que iban a pasar a 12. Ahora hay
una constante, `VENTANA_MESES`, y un texto derivado. El benchmark de precios mantiene sus
24 meses **a propósito**: lee de los Parquet, no de Postgres, y son dos preguntas
distintas.

## D-040 — Qué se puede traer del portal oficial y qué no

**16 de agosto de 2026.** Salió de comparar nuestra ficha de proceso con la del SERCOP.

### La comparación

Sobre `LICO-GADPO-2026-21`, campo por campo: **objeto, referencial (94 102,17), 2
licitadores, publicación 13-07 20:00, cierre de preguntas 15-07 20:00, cierre de ofertas
23-07 09:00, 13 artículos con CPC** — todo cuadra. Lo que publicamos es correcto.

Lo que faltaba se reparte en dos grupos, y la diferencia entre ellos es lo que importa.

### Grupo 1 — estaba en la fuente y no lo leíamos

Cuatro campos en el CSV de `tender_`, desde el primer día:

| Campo | Qué es |
|---|---|
| `awardCriteria` | `ratedCriteria`: el precio compite contra otros factores |
| `eligibilityCriteria` | «Oferta Económica, Participación Ecuatoriana, Subcontratación, Experiencia General, Experiencia Específica» |
| `mainProcurementCategory` | Obra, bienes o servicios |
| `numberOfTenderers` | Contra cuántos se compitió |

El segundo es el complemento directo del benchmark: **uno dice a qué precio se adjudica,
el otro dice cuánto pesa el precio**. Añadidos en la migración 0028.

### Grupo 2 — no está en el dato abierto y no se puede traer

Comprobado clave por clave sobre el registro OCDS completo, incluidas sus ocho
extensiones:

- **Los pesos de cada criterio** (Oferta Económica 50%, Experiencia Específica 26%…)
- Agregado nacional, forma de pago, plazo de entrega, vigencia de oferta
- Funcionario encargado, costo de pliegos
- Invitaciones a proveedores
- **Los pliegos**: `documents` está vacío en 1 264 de 1 264 procesos

### Por qué no se puede automatizar

**El enlace del portal no es derivable.** `idSoliCompra` es un token de 44 caracteres —la
coma final sustituye el `=` de relleno— que decodifica a **32 bytes binarios**. Es AES o
SHA-256: sin la clave del SERCOP no hay forma, y si es un hash no la hay ni con ella.

**Y el buscador que lo resolvería tiene CAPTCHA.** El formulario publica por POST a
`consultarProcesos_exe.php` con los campos `captccc2`, `captchaBP` y `captcha_img`.

**No se intenta rodearlo, y la razón es de negocio antes que de otra cosa:** el producto
entero depende de que el SERCOP siga sirviéndonos la descarga masiva. Ya vimos con los
`429` de su API lo rápido que bloquean y lo largo que dura. Arriesgar el acceso por unos
campos complementarios es un mal cambio.

### Lo que sí se hizo

**El código del proceso sí es derivable, y se midió.** El `ocid` termina en el
identificador interno de la entidad compradora: sobre 20 000 procesos hay **1 954 sufijos
distintos y 1 954 compradores distintos**, correspondencia uno a uno.

```
ocds-5wno2w-LICO-GADPO-2026-21-29112  →  LICO-GADPO-2026-21
```

La ficha lo muestra con un botón de copiar y un enlace al buscador oficial. No automatiza
nada, pero convierte «búscalo tú» en «copia esto».

Y la pantalla **dice lo que no tiene**: que el peso de cada criterio está en el portal y
no en el dato abierto. Un hueco declarado se entiende; uno callado se lee como que no
existe.

### La vía que de verdad lo resuelve

Los campos del grupo 2 **ya son públicos** en el portal del SERCOP. No hay razón de fondo
para que no estén en el OCDS, y el estándar tiene una extensión para criterios ponderados
— el SERCOP ya publica ocho extensiones, una de ellas propia.

La petición es concreta: *que publiquen los pesos de los parámetros de calificación, como
ya publican los criterios*. Por LOTAIP o al equipo de datos abiertos. Beneficia a todo el
ecosistema y no solo a nosotros, que es lo que hace que valga la pena pedirla.

---

## D-041 — `unit.value.amount` significa dos cosas, según el método

**17 de agosto de 2026.** Lo vio el cliente mirando la tabla de artículos de una obra:
*«creo que estás usando mal los valores de precio unitario y total. La suma de los
valores totales no es igual a la del monto contractual.»*

Tenía razón. Y corrige a **D-033**, que sigue siendo válido en su mitad.

### El síntoma

En `LICO-GADPO-2026-21`, la ficha daba:

| Artículo | Cantidad | Total línea |
|---|---|---|
| Acero de refuerzo fy = 4200 kg/cm² | 5 063,22 kg | **2 USD** |
| Excavación y relleno para estructuras | 827,5 m³ | **4 USD** |
| Transporte de material de mejoramiento | 18 935 m³-km | **0 USD** |

Los trece renglones sumaban **2 127 USD** contra un referencial declarado de
**94 102,17**. Acero de construcción a 0,0005 USD el kilo.

### La causa

El campo `unit.value.amount` **no significa lo mismo en todos los métodos**:

| Método | Qué es `unit.value.amount` |
|---|---|
| **Subasta Inversa Electrónica** | el **total del renglón** |
| todos los demás con ítems | el **precio por unidad** |
| Catálogo electrónico (4 variantes) | no publica ítems |

Nada en la fuente lo advierte. El mismo nombre, dos magnitudes.

### La medición

Por proceso se comparó `sum(amount)` y `sum(amount × quantity)` contra el referencial
—o contra el adjudicado en subasta inversa, que no publica referencial en **ninguno** de
sus 2 217 releases—. Solo cuentan los procesos donde alguna cantidad ≠ 1: si todas son 1
las dos lecturas son idénticas y el proceso no distingue nada.

| Método | 2025-12 · n | como total | como unitario | 2024-06 · n | gana «total» |
|---|---|---|---|---|---|
| **Subasta inversa** | 688 | **7,0%** | 15 323% | 572 | **100%** |
| Licitación | 1 161 | 95,1% | **0,0%** | 32 | **0%** |
| Menor cuantía | — | — | — | 10 | **0%** |
| Cotización | — | — | — | 2 | **0%** |
| Contratos entre entidades | 12 | 99,9% | **0,0%** | 9 | **0%** |
| Bienes y servicios únicos | 15 | 91,7% | **0,0%** | 13 | **0%** |
| Catálogo × 4 | 7 188 releases sin ítems | | | 14 435 sin ítems | no aplica |

**La columna que decide es la última.** No es una mediana favorable: es 100% o 0%, nunca
intermedia. Eso es una regla, no una tendencia. Ese 7% de la subasta inversa no es error,
es la baja del propio remate — allí el árbitro es el adjudicado.

Y el proceso del cliente lo confirma al céntimo: **94 102,18 calculado contra 94 102,17
declarado**.

### Por qué se equivocaron las dos mediciones anteriores

**D-033 midió subasta inversa** —688 procesos, los mismos 688— y concluyó «total de
línea» para todo. **La revisión de esta ficha midió licitación** y concluyó «precio
unitario» para todo. Las dos generalizaron desde el único método que habían mirado.

D-033 no se borra: **acertó en su método**, y su ejemplo —«LECHE LÍQUIDA a 1 260 000 USD
la unidad»— sigue siendo el motivo por el que en subasta inversa hay que dividir.

Lo que faltaba en las dos era **la segunda muestra**. Una medición sobre un solo estrato
de una fuente heterogénea no mide la fuente: mide el estrato.

### Por qué no lo vio ninguna prueba

Las 56 estaban en verde. Comprobaban **funciones** —«calcular devuelve filas», «los
percentiles están ordenados»— y el fallo estaba en el **resultado**. Es el cuarto caso
del mismo patrón, y el que lo hace explícito: la comprobación que faltaba era la que hizo
el cliente a ojo, **sumar la columna y compararla con el monto**.

`pruebas/test_renglones.py` la automatiza, y las pruebas del benchmark ahora van **por
pares**: el mismo ítem con los dos métodos. Con un solo método no se distingue nada, y
esa es exactamente la forma que tuvo el fallo las dos veces.

### Lo que se cambió

- **`normaliza.desglosar_renglon()`** — la regla, en un solo sitio. Devuelve
  `(precio_unitario, monto_linea)` y necesita el método. Vive ahí porque la consumen
  `precios.py` y `abiertos.py`: con la regla escrita dos veces, arreglar una y no la
  otra es cuestión de tiempo.
- **`precios.py`** — baja también `procesos_*.parquet` para cruzar el método. Un ítem sin
  método **corta la ejecución** en lugar de caer en una rama por omisión: un valor por
  defecto en el campo ambiguo es este mismo fallo otra vez.
- **`abiertos.py` + migración 0030** — `proceso_item` guarda las **dos** columnas ya
  desglosadas. La aplicación no divide ni multiplica.
- **La ficha** — muestra la **suma de los renglones junto al referencial**. La
  comprobación del cliente, hecha visible en la pantalla donde falló.

### Alcance

`precio_cpc` (10 424 filas) y `mercado_cpc_prov` (19 113) estaban calculadas aplicando a
todo la regla de subasta inversa. El total de mercado salía **creíble** —6 245 M en 2024
contra 6 896 M reales, un 91%— porque el volumen lo domina subasta inversa, donde la
lectura era correcta. Eso es lo que lo mantuvo escondido: **el agregado tapaba el error
del caso individual**. Hay que recalcular las dos tablas.

---

## D-042 — Los releases se piden por etiqueta, nunca listando

**17 de agosto de 2026.** Salió al intentar recalcular el benchmark tras D-041.

`benchmark.yml` murió con:

```
meses de la ventana con Parquet: 0 de 24
AVISO: faltan 24 meses. El benchmark se calcula sobre lo disponible y el n lo refleja.
ítems leídos: 0 · procesos con método: 0
sin ítems: publica primero el Parquet de la ventana
```

Los Parquet **estaban ahí**. `GET /repos/.../releases?per_page=100` devuelve
**HTTP 200 con cuerpo `[]`** —dos bytes— con token y sin token, mientras
`GET /repos/.../releases/tags/datos-2025` devuelve el mismo release con sus **60
activos**. Los tres releases de la ventana suman 159 activos y 73 MB.

No es un problema de permisos, de paginación ni de borrado: los releases existen y se
leen perfectamente por su otra ruta.

**Lo que no se puede afirmar.** Ese mismo día GitHub tuvo una caída parcial con la API
en «major outage». El listado devolvió `[]` en tres intentos seguidos mientras el acceso
por etiqueta funcionaba en el mismo minuto —una asimetría que la caída no explica bien—,
pero **no se puede separar con certeza un comportamiento permanente de un síntoma de la
caída**. Da igual para la decisión: por etiqueta funciona en los dos escenarios y no
depende de que el listado esté sano. Si algún día se comprueba que el listado responde,
tampoco hay motivo para volver a él.

### El arreglo

`precios.py` pide `releases/tags/datos-AAAA` para cada año de la ventana. Las etiquetas
son deterministas y son las que ya escribía `publicar.py`, que **siempre** consultó por
etiqueta. Solo `precios.py` dependía del listado. Con el cambio: **24 de 24 meses**.

### Lo que hacía peor el fallo

El aviso decía «el benchmark se calcula sobre lo disponible y el `n` lo refleja». Con
cero meses la ejecución cortaba por otro motivo —no había ítems—, pero con un listado
**a medias** habría publicado un benchmark sobre una fracción de la ventana, comparable
con el anterior solo en apariencia y sin nada que lo advirtiera.

Ahora corta por debajo de tres cuartos de la ventana. **Una advertencia que no detiene
nada no protege nada**, y es además el patrón que la regla 5 del método ya señalaba desde
el otro lado: una alarma que salta sin motivo entrena a ignorarla.

### Regla

**Cualquier acceso a un release va por etiqueta.** Listar es una dependencia sobre un
comportamiento que ya se demostró poco fiable, y su fallo es silencioso: devuelve una
lista vacía, no un error.

---

## D-043 — Los ítems de `tender` y de `awards` no se suman los dos

**17 de agosto de 2026.** Salió al comprobar el benchmark ya corregido por D-041.

El tamaño de mercado de 2024 daba **8 329 M USD** contra **6 896 M** reales — un 121%,
y eso **excluyendo el catálogo electrónico entero**, que no publica ítems. Una cifra por
encima del total del país mientras se deja fuera la mitad de los procesos no puede estar
bien.

### La causa

`detalle.py` guarda los ítems de `tender` **y** los de `awards`, con una columna `origen`
para distinguirlos. `precios.py` los sumaba todos.

Medido en 2025-12 sobre la fuente:

| Método | Ítems en tender | Ítems en awards | Procesos con ambos | Inflación |
|---|---|---|---|---|
| Licitación | 122 221 · 799 M | 112 487 · 627 M | 1 383 de 1 495 | **×1,78** |
| Subasta inversa | 2 069 · 355 M | 1 833 · **0** | 1 832 de 2 217 | ×1,00 |

El 0,78 entre award y tender en licitación es la baja del proceso, y confirma que son el
mismo renglón dos veces: antes y después de adjudicar.

### Por qué no se vio antes

**Dos errores que se cancelaban a medias.** Con la lectura equivocada de D-041 —sumar
importes crudos sin multiplicar por la cantidad— el total salía 6 245 M, un 91% del real.
Parecía razonable. Al corregir uno, el otro quedó al descubierto.

Es el argumento de la regla 1 del método en su forma más incómoda: un agregado que cuadra
no prueba que el cálculo sea correcto, solo que los errores se compensan.

### La regla

**Un solo origen por proceso.** Se prefiere `award`, que es el precio al que de verdad se
adjudicó y es lo que el cliente necesita. Donde los ítems de award vienen sin importe
—subasta inversa, sus 1 833 ítems suman cero— se usa `tender`, y lo que se publica ahí es
el referencial.

Nunca los dos: cada renglón entra una vez.

### Comprobación después de recalcular

| Momento | Mercado 2024 | Contra los 6 896 M adjudicados |
|---|---|---|
| Con la lectura de D-033 aplicada a todo | 6 245 M | 91% — *parecía bien* |
| Con D-041 corregido, sumando los dos orígenes | 8 329 M | **121% — imposible** |
| Con D-041 y D-043 | **5 425 M** | **79%** |

El 79% es el número que se espera: **el catálogo electrónico pesa el 25,4% del monto
adjudicado y no publica ítems**, así que un benchmark construido sobre ítems tiene que
quedarse en torno al 75%. Los cuatro puntos de más son subasta inversa aportando su
referencial en lugar del adjudicado, que es un 7% más alto.

Tres cifras que se explican entre sí. La primera, la que parecía bien, era la única que
no se podía justificar.

### Lo que sigue sin resolver

Quedan medianas como **4 187 675 USD por «Unidad»** en CPC 891210111 —servicios de
construcción— con `n = 5`. No es un error de lectura: es una obra entera declarada como
«1 unidad». El precio es correcto y el benchmark es inútil, porque comparar el precio de
«una obra» contra el de «otra obra» no dice nada.

Es un problema de **qué se publica**, no de cómo se calcula, y se trata aparte.

---

## D-044 — Las listas se paginan, se ordenan y se buscan; y dicen cuántas hay

**17 de agosto de 2026.** Salió de una revisión del cliente sobre la pantalla de
mercados: *«las tablas se truncan, no se pueden buscar, filtrar ni ordenar, y no se
muestran todos los registros.»*

### Lo que había

Cada pantalla pedía un número fijo de filas y las pintaba **sin decir de cuántas**:

| Pantalla | Se mostraban | Había | Visible |
|---|---|---|---|
| `/mercado` | 120 | **1 065** | 82,2% del monto |
| `/radar` | 60 | **4 393** | 1,4% |
| `/buscar` · entidades | 25 | 1 056 (para «construccion») | — |
| `/buscar` · procesos | 25 | **3 873** | — |
| `/mercado/[cpc]` · compradores | 15 | **562** en vigilancia | — |
| `/mercado/[cpc]` · proveedores | 15 | 190 | — |
| `/entidad/[ruc]` · recientes | 12 | 29 en Quito | — |

**Ninguna emitía `count: "exact"`**, así que ni la aplicación sabía el total. Una lista
truncada sin total **se lee como completa**: es la misma clase de fallo que D-041 y
D-043 —nada falla, y el dato es falso—. Por eso el componente `Tabla` **exige** `total`
y no lo acepta opcional: una tabla que no sabe cuántas filas hay no debería pintarse.

### Lo que se hizo

`lib/lista.ts` lee y **valida** los parámetros, `componentes/Tabla.tsx` pinta cabeceras
que ordenan y su paginación, `FiltroLista.tsx` busca dentro. Se aplicó a las siete
pantallas con tabla.

**En el servidor y no en el navegador**, por tres razones y ninguna de gusto:

1. PostgREST corta en **1.000 filas**. El radar tiene 4.393: no caben, así que ordenar
   en el cliente exigiría traérselas todas y no se puede.
2. Las páginas se indexan. Un orden que vive en `useState` no tiene URL y no se puede
   enlazar ni compartir.
3. El muro de pago vive en las políticas RLS. Filtrar en el cliente obliga a mandar los
   datos primero, y eso regalaría justo lo que se cobra.

**La columna de orden nunca sale del usuario.** Va contra una lista blanca por tabla:
`orden` acaba dentro de `.order()` y de ahí a PostgREST tal cual. Comprobado que
`?orden=hackeame&dir=xx&p=-5` cae en los valores por omisión sin error.

**Páginas con varias listas**, con prefijo por lista: `/buscar` usa `ep`/`eorden`/`edir`
para entidades y `pp`/`porden`/`pdir` para procesos, con la `q` compartida. Verificado
que paginar una no mueve la otra.

### Lo que se encontró de paso

- **`/radar` pedía la tabla `categoria` entera** con un `select` sin límite. Tiene 1.579
  filas y PostgREST devuelve 1.000: **579 categorías no llegaban nunca**, y las filas que
  caían en ellas se pintaban sin categoría. La trampa documentada, ocurriendo de verdad.
  Ahora se piden solo los ids de la página, que son 50 como mucho.
- **La cifra de concentración de `/mercado/[cpc]`** —«el primero se lleva el 15,3%»— se
  calcula sobre las filas que se pintan. Con la tabla ordenada por nombre, «el primero»
  pasaría a ser el primero del alfabeto y el porcentaje no significaría nada. Ahora solo
  aparece en el orden por monto y en la primera página; en cualquier otro caso se calla.
  **Una cifra que cambia de significado según cómo esté ordenada la tabla no se enseña.**
- Los guardas de sección iban sobre las filas de la página y no sobre el total. En la
  última página + 1, la sección desaparecía **con su paginación dentro** y no había forma
  de volver.

### Lo que NO se hizo, y por qué

El cliente pidió **primera página cacheada y el resto dinámico**. En Next 16 eso ya no se
puede activar por ruta: `experimental.ppr` da error y remite a `cacheComponents`, que
**invierte el modelo de caché de toda la aplicación** —todo dinámico salvo lo marcado con
`use cache`—. Hasta terminar esa migración, portada, fichas y benchmark consultarían
Supabase en cada visita: lo contrario de lo que se busca con el egress de 5 GB.

Se hizo lo que cumple el objetivo real: **la caché es de datos, no de HTML**. El HTML se
renderiza por petición —barato— y `unstable_cache` guarda la consulta por combinación de
orden, filtro y página. La primera página por monto, que es la que ve casi todo el mundo
y la que se indexa, se sirve sin tocar Supabase. Un `Suspense` mantiene la cabecera
visible mientras llega la tabla.

Migrar a `cacheComponents` queda pendiente y es la vía para tener además el HTML estático.

---

## D-045 — La clasificación CPC oficial sustituye a la taxonomía del LLM

**18-19 de agosto de 2026.** La decisión de más alcance desde D-002. Pedida por el
cliente tras ver «Materiales De Construcción» repetido 36 veces y «construcción»
partida en 87 pedazos.

### Lo que había y por qué murió

Dos taxonomías conviviendo: 242 categorías por embeddings (muertas, 0 procesos) y
1.337 nombradas por LLM subclase a subclase. Con 1.337 llamadas independientes y sin
vocabulario compartido, el 27% de las subclases compartía nombre con otra y una se
llamaba literalmente «Medicamento antiviral y antibiótico no, es más genérico: Med».
**No había que inventar una jerarquía: la CPC ya lo es.** Había que cargarla.

### La fuente y su validación (fase 0)

`referencia/cpc_clasificacion.csv` (3.725 nodos, extraído del navegador oficial) y
`referencia/umbral_vae.csv` (30.098 productos con umbral VAE, **latin-1**). Validados
antes de cargar: cero fallos de integridad, 55/55 nodos contra el HTML oficial,
las 2.025 subclases con productos existen todas, y los 30.098 productos cuelgan del
árbol. Cinco subclases sin nombre en el portal heredan el de su clase (documentado en
`referencia/LEEME.md`); la carga se detiene si un fichero nuevo trae más.

**Cabecera contra renglones, medido en la fuente**: el CPC de cabecera coincide en
subclase con los ítems en el **100% de 3.564 procesos**. Agregar por cabecera es fiel.

### El modelo (fases 1-3)

- `cpc_nivel` (árbol, el código ES el prefijo) y `cpc_producto` (hojas + VAE). El VAE
  vive en el producto: 276 subclases tienen varios umbrales.
- `proceso_resumen.cpc_nodo` por **trigger** (una sola copia de la regla): subclase →
  clase → sin clasificar. Cobertura medida: 99,86% de los procesos con CPC; el 0,5%
  del monto restante es el cubo «Sin clasificar», **visible en /mercado**.
- `mercado_nodo` + método + contratistas + contratantes (materializadas): **cada nivel
  se calcula desde los procesos crudos.** Solo monto y n.º de contratos son aditivos;
  los distintos NO (división 54: 1.222 proveedores reales contra 1.244 sumando grupos)
  y las medianas tampoco. `test_arbol.py` hace imposible la suma sin que grite.
- **El corte estadístico (invariante 10) se aplica en el árbol** — y de paso corrige
  la violación que la auditoría encontró en v_mercado. Los abiertos van aparte, con el
  dato del día.
- Los nodos sin actividad **se muestran con cero** (decisión del cliente): la sección
  0 —agricultura— está a cero de verdad, y eso es un hallazgo, no un hueco.

### La clasificación diaria y la mensual (fases 5-6)

El CSV diario no trae CPC; los ítems viven en el Parquet mensual (~4 meses de retraso,
que el corte absorbe). Para el radar, que vive en esos meses:

- **Diario**: `asignar_cpc_desde_items()` — los abiertos toman el CPC de sus propios
  ítems (cargados por `abiertos.py`). 606 oportunidades etiquetadas el primer día.
- **Mensual**: `clasifica_cpc.py` asigna desde el Parquet y recupera el referencial de
  subasta (lo que quedaba vivo de `taxonomia.py`, que ahora es biblioteca). De paso se
  arregló un roto latente: su main llamaba a `descargar_items` con la firma anterior a
  D-041 y habría fallado el 5 de septiembre.
- **La planificación queda sin categoría a propósito**: su método no existe aún, así
  que su CPC tampoco. El clasificador de texto que la etiquetaba era un adivino, y el
  CPC oficial es declarado, no adivinado.

### El benchmark (fase 4)

`v_benchmark` gana nombre oficial, VAE y la marca `comparable`, con regla medida:
«Global» nunca es precio unitario; «Unidad» en las secciones de servicios (5-9) es el
contrato entero; «Unidad» en bienes se queda — una motoniveladora a 500.000 la unidad
es un precio real y marcarla por cara sería mentir.

### Lo que se conservó sin tocar

Las URL indexadas `/mercado/[cpc5]` (la subclase es un nodo del árbol). El muro:
`compradores_huerfanos()` cambió el JOIN a `cpc_nodo` y **ni un carácter** del
`exists` sobre suscriptor.

### Números finales

3.725 nodos + 30.098 productos cargados · 99,86% de enganche · 886 subclases activas
en portada · base en 380 MB tras compactar (el UPDATE masivo de la 0032 la llevó a
456 y el paso de compactación existe exactamente para eso) · migraciones 0031-0037.
