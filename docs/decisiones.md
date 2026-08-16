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
