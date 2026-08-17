# Pliego — contrato operativo

Servicio de consulta, investigación de mercado y alertas sobre la contratación pública del
Ecuador, construido sobre los datos abiertos OCDS del SERCOP.

**Cliente objetivo:** proveedores del Estado que facturan entre 100 000 y 2 000 000 USD al año.
Son 6 697 empresas identificadas nominalmente por los propios datos.
**Lo que se cobra:** saber a qué precio compite cada categoría, y qué entidades compran lo que
uno vende sin comprárselo a uno.

Dos repositorios:
- `pliego-datos` — **público**. Ingesta, normalización, agregación, Parquet. Minutos de Actions ilimitados.
- `pliego-app` — privado. Next.js desplegado en Vercel.

---

## 1. Invariantes

No se violan sin añadir antes una entrada en `docs/decisiones.md` que lo justifique.

1. **El detalle OCDS no entra en Postgres.** Vive como Parquet en releases de GitHub.
2. **Postgres solo contiene agregados regenerables y datos de usuario.** Presupuesto duro
   460 MB, alarma automática a 420 MB.
3. **La aplicación nunca consulta al SERCOP en vivo.** Lee de Postgres y de los Parquet.
4. **Todo el cómputo pesado corre en GitHub Actions**, nunca en Vercel (límite 60–300 s).
5. **Toda la estructura de base de datos vive en `migraciones/*.sql`.** Nada se crea desde el
   panel de Supabase. Esto es lo que hace que migrar de cuenta cueste media jornada.
6. **Autenticación por enlace mágico.** Sin contraseñas, para que no haya hashes que migrar.
7. **Las tablas propias se enlazan al usuario por correo**, no por la UUID de `auth.users`.
8. **Cero referencias a proyecto, URL o claves en el código.** Todo por variables de entorno.
9. **No se publican datos personales de proveedores persona natural**: RUC completo ni
   dirección domiciliaria. El RUC de persona natural contiene la cédula.
10. **Los últimos 4 meses no entran en estadísticas de mercado.** Un mes tarda 4–5 meses en
    cerrar; incluirlos sesga cualquier benchmark sin que nada lo advierta.
11. **Toda cifra agregada se muestra junto a su número de observaciones.**
12. **Ningún indicador se presenta como acusación de conducta.** Solo señales estadísticas.
13. **Un solo correo por suscriptor y por día**, con todas las coincidencias agrupadas.
    Nunca un correo por oportunidad: reventaría la cuota de Resend en una mañana.
14. **Exportación nocturna de las tablas de suscriptores** al repositorio privado. El plan
    gratuito de Supabase no tiene copias de seguridad y esos datos no se regeneran.

---

## 2. Trampas

Cosas que parecen buena idea al empezar una sesión en frío y no lo son.

| Idea tentadora | Por qué no |
|---|---|
| «Sería más simple meter todo en Postgres» | Rompe el presupuesto de 500 MB y el costo cero. La capa Parquet es deliberada, no accidental. |
| «Usemos la API paginada» | 60 peticiones/min, 10 registros/página, 277 427 páginas: 77 h para el histórico. Usar siempre `download?type=…`. |
| «El CSV es más fácil de parsear que el JSON» | El CSV **no** trae ítems, ni oferentes, ni el referencial de subasta inversa (vacío en los 24 060 casos de 2024). El JSON sí. |
| «Los acentos llegan rotos, hay que repararlos» | **No.** La fuente es UTF-8 válido; lo que se ve roto es la consola de Windows. «Reparar» corrompe datos correctos. |
| «Los datos del mes pasado ya están completos» | Un mes tarda 4–5 meses en cerrar. En agosto de 2026, julio estaba al 59%. |
| «Stripe para cobrar» | No opera en Ecuador. Transferencia + factura electrónica; PayPhone después. |
| «pgvector para la búsqueda semántica» | Los embeddings no caben en 500 MB. Van en Parquet, truncados a 256 dimensiones. |
| «Clasificar cada proceso con un LLM» | Son 2,77 M llamadas. Embeddings + agrupamiento + etiquetar solo los grupos: de ~50 USD a ~2 USD. |
| «Un cron de Vercel para la ingesta» | Timeout garantizado. Va en Actions. |
| «Sumo estas cifras en el cliente y listo» | PostgREST corta en **1.000 filas**: la portada dio 56 M donde el real eran 3.203 M, sin error visible. Todo `sum`/`count`/`avg` va en una vista. |
| «Verificar un subdominio aparte en Resend» | El plan gratuito permite un solo dominio y `darkmelon.com` ya lo ocupa. |
| «Crear otra organización en Supabase para tener más cupo» | El límite de 2 proyectos activos es **por usuario**, no por organización. Comprobado con un 400 explícito. |
| «Sacamos del portal del SERCOP los datos que faltan» | El enlace lleva un token de 32 bytes cifrados y el buscador tiene CAPTCHA. Y el producto entero depende de que nos sigan sirviendo la descarga masiva. Ver D-040. |
| «El detalle de un proceso lo pedimos en vivo a su API» | 60 peticiones/min sin cabeceras de límite, y el castigo dura más de doce minutos. En Vercel las funciones comparten IP: un usuario rompería la pantalla para todos. Ver D-035. |
| «El precio unitario es el total del renglón entre la cantidad» | Solo en **subasta inversa**. En licitación y el resto, `unit.value.amount` YA es el precio por unidad y dividir lo destroza: acero de construcción a 0,0005 USD el kilo. El mismo campo, dos magnitudes. Ver D-041. |
| «Listo los releases con `GET /releases` y busco el activo» | Ese endpoint devuelve **`[]`** en `pliego-datos` aunque los releases existan y tengan sus activos —HTTP 200, cuerpo de 2 bytes, con token y sin token—, mientras `GET /releases/tags/datos-2025` devuelve los 60. Pedir siempre **por etiqueta**. Ver D-042. |
| «Sumo los ítems de `tender` y los de `awards`» | Son **el mismo renglón dos veces**, antes y después de adjudicar: 1.383 de 1.495 licitaciones los tienen en los dos sitios y el mercado se infla ×1,78. Un origen por proceso, `award` si trae importe. Ver D-043. |

---

## 2b. Cómo se verifica

Siete reglas destiladas de los catorce fallos de la fase 1. El detalle y qué caso atrapó
cada una están en `docs/metodo.md`.

**El dato que las ordena: cuatro de los catorce fallos no produjeron ningún error.** El
trabajo terminó en verde, las 36 pruebas pasaron, y el dato estaba mal — porque las
pruebas verificaban funciones y el fallo estaba en el resultado.

1. **Una consulta de producto tras cada carga.** No «la tabla tiene filas», sino «el radar
   devuelve oportunidades con monto». Está en `pruebas/test_producto.py` y sola cubre
   cuatro de los catorce.
2. **Cardinalidad de entrada y salida en cada transformación.** `17 473 → 15` tenía que
   gritar. Falla si la proporción es extrema.
3. **Verificar en el nivel donde ocurre el fallo.** Si falla como programa, pruébalo como
   programa; si el problema son bytes, mira bytes. La consola de Windows miente.
4. **Medir antes de rebajar un invariante.** La intuición sobre costes se equivocó en un
   orden de magnitud en las dos direcciones: 4 MB que parecían caros, 173 MB que parecían
   inocuos.
5. **Toda alarma necesita una prueba de falso positivo.** Una advertencia que salta sin
   motivo entrena a ignorarla y destruye el valor de las verdaderas.
6. **Nunca editar a ciegas.** Sustituir texto por programa falla en silencio; usar la
   herramienta de edición o comprobar con `assert` después.
7. **Verificar el estado antes de reaccionar a un fallo.** Un fallo al final no invalida
   lo anterior: la fusión se aplicó entera y el flujo salió en rojo.

---

## 3. Hechos verificados

Medidos contra la fuente el 14 de agosto de 2026. **No recalcular**: están aquí para no repetir
horas de descarga.

### Volumen
- **2 774 265** procedimientos entre 2015 y agosto de 2026.
- 2024 completo: **219 185** procesos cargados frente a **219 186** que declara la API.
  La ingesta es fiel; ese 1 de diferencia es el margen aceptable.
- 2024: **6 895 826 063 USD** adjudicados, **20 972** proveedores, **5 066** entidades.
- Por año: 2015 · 280 643 | 2016 · 279 636 | 2017 · 334 275 | 2018 · 357 687 | 2019 · 275 055
  | 2020 · 160 676 | 2021 · 167 058 | 2022 · 212 324 | 2023 · 217 914 | 2024 · 219 186
  | 2025 · 188 139 | 2026 · 81 672 (a agosto).

### Segmentación de proveedores en 2024
| Tramo de facturación | Empresas | % del monto | Repiten desde 2023 | Compradores/año | En 2 años |
|---|---|---|---|---|---|
| < 5 K | 1 021 | 0,0% | 61,6% | 1,5 | 3,1 |
| 5 K – 25 K | 6 073 | 1,1% | 58,8% | 1,5 | 2,2 |
| 25 K – 100 K | 6 617 | 5,1% | 52,3% | 2,2 | 3,2 |
| **100 K – 500 K** | **5 010** | **17,0%** | 57,8% | **4,2** | 6,1 |
| **500 K – 2 M** | **1 687** | **23,2%** | 66,6% | **10,2** | 15,5 |
| 2 M – 10 M | 496 | 28,4% | 74,0% | 25,6 | 35,1 |
| > 10 M | 68 | 25,2% | 80,9% | 53,6 | 79,9 |

**Cuidado con la ventana** (D-019): las cifras de compradores por proveedor que circularon
primero eran de DOS años presentadas como si fueran anuales. En el producto se usa la
anual. Toda media va con su ventana temporal, igual que va con su `n`.

Mediana de facturación 49 919 USD. Concentración: top-10 = 10,34%, top-100 = 29,08%.
**La columna de entidades por proveedor es la tesis del producto**: crecer es diversificar
compradores, y la función principal es el mecanismo de esa transición.

### Ratio adjudicado / referencial, mediana 2024
| Método | Ratio | n |
|---|---|---|
| Licitación de seguros | 0,863 | 804 |
| Licitación | 0,949 | 522 |
| Cotización | 0,951 | 2 307 |
| Menor cuantía | 1,000 | 5 694 |
| Catálogo electrónico | 1,000 | 53 059 |
| **Subasta inversa electrónica** | **no calculable desde CSV** | 0 |

### Estacionalidad
Enero es un mes muerto: 5 047 procesos en enero de 2023 y 5 261 en enero de 2024, contra unos
20 000 de un mes corriente. Marzo es el pico en ambos años. Es ciclo presupuestario, no un
hueco de datos.

### Curva de maduración, medida en 2026
| Mes | Registros | % cerrado |
|---|---|---|
| Enero | 3 939 | 98,3% |
| Marzo | 18 213 | 98,5% |
| Mayo | 9 321 | 91,9% |
| Junio | 11 728 | 89,0% |
| Julio | 7 654 | 59,0% |
| Agosto (en curso) | 1 546 | 30,9% |

---

## 4. Fuente de datos

### Descarga masiva (ruta principal)
```
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/download
  ?type=csv|json|xlsx&year=YYYY&month=M&method=all
```
Devuelve un ZIP. En CSV contiene 8 archivos: `metadata_`, `extensions_`, `releases_`,
`planning_`, `tender_`, `awards_`, `suppliers_`, `contracts_`. Un mes ronda 2,6 MB y 1,8 s.

**Usar `type=json` para el detalle**: trae `tender.items[]` con CPC, cantidad y precio
unitario, `tender.tenderers[]` con todos los oferentes, `numberOfTenderers`, `bids`,
`parties[]` con RUC y dirección, y `planning.budget` con la partida presupuestaria.
El JSON de un mes entero corta la conexión a los ~120 s: **trocear por `method`**.

### API paginada (solo refresco del día)
```
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds
  ?year=&search=&page=&buyer=&supplier=
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/record?ocid=
```
`X-RateLimit-Limit: 60` por minuto. 10 registros por página, fijo — `page_size` y `limit` se
ignoran. Tiene datos del día en curso.

### Reglas de tratamiento
- **Codificación: la fuente entrega UTF-8 válido.** Verificado: «Catálogo» llega como
  `b'Cat\xc3\xa1logo'`. **No reparar nada.** `codificacion.py` solo valida y detiene la ingesta
  si la fuente cambia o si detecta doble codificación (`Ã¡`, `Ã³`, `Â`).
  *(Una nota anterior afirmaba que llegaba en latin-1; era un artefacto de la consola de
  Windows. «Reparar» habría convertido `Catálogo` en `CatÃ¡logo`.)*
- **Identidad de proceso:** el `ocid`.
- **Identidad de entidad:** el RUC, extraído de `EC-RUC-<ruc>-<secuencia>` tomando el tercer
  segmento. **No unificar por nombre**: la misma empresa aparece escrita de varias formas.
- **Estados:** el campo `tag` es la máquina de estados del proceso —
  `planning` → `tender` → `award` → `contract`. Los intermedios son el producto de radar.
- **Descargas fallidas:** de 24 meses cargados, 10 necesitaron reintentos por tiempo de espera
  o respuesta truncada (`IncompleteRead`). Reintento con espera creciente, 4 intentos, y
  registrar el mes como pendiente en lugar de darlo por cargado.

---

## 5. Comandos

```bash
# ingesta
python src/ingesta.py --desde 2015-01 --hasta 2026-08     # backfill completo (~1 h)
python src/ingesta.py --mes 2026-08                        # un mes concreto
python src/ingesta.py --incremental                        # mes en curso y anterior
python src/agrega.py                                       # recalcular agregados y cargar
python src/cobertura.py --informe                          # qué meses faltan o están incompletos

# comprobaciones
pytest pruebas/test_contrato_datos.py                      # falla si la fuente cambió
pytest pruebas/test_presupuesto.py                         # falla si Postgres pasa de 420 MB

# base de datos
psql "$SUPABASE_DB_URL" -f migraciones/0001_esquema.sql

# aplicación
npm run dev
npm run build
```

---

## 6. Estructura

```
pliego-datos/                     pliego-app/
  .github/workflows/                app/
    ingesta-diaria.yml                radar/  proveedor/[ruc]/  entidad/[ruc]/
    ingesta-semanal.yml               buscar/  mercado/[cpc]/
    ingesta-mensual.yml               benchmark/[cpc]/   ← tras el muro
    ingesta-trimestral.yml            compradores/       ← tras el muro
    publicar-parquet.yml              perfil/  entrar/  api/
  src/                              componentes/
    descarga.py  codificacion.py      Cifra.tsx  Distribucion.tsx
    normaliza.py  entidades.py        FilaOportunidad.tsx  NotaCobertura.tsx  Muro.tsx
    clasifica.py  agrega.py         lib/
    carga.py  cobertura.py            supabase.ts  parquet.ts  formato.ts
  migraciones/*.sql                 estilos/tokens.css
  pruebas/                          CLAUDE.md
  docs/
  CLAUDE.md
```

---

## 7. Estilo

- Español en interfaz, documentación, nombres de tabla y de columna. Inglés solo donde el
  esquema OCDS lo impone (`ocid`, `tag`, `tender`).
- Cifras siempre en tipografía monoespaciada con `font-variant-numeric: tabular-nums`.
- Colores solo desde variables CSS. Verde = adjudicado, azul = referencial, ámbar = atención.
  Nunca decorativos.
- Sin emojis como marcadores de sección.
- Los errores dicen qué pasó y cómo arreglarlo. Sin disculpas ni vaguedad.

---

## 8. Documentos

Los catorce documentos del MVP viven en `docs/`. **Leer antes de tocar el área
correspondiente**, no después.

| Doc | Archivo | Qué fija |
|---|---|---|
| 09 | este `CLAUDE.md` | Invariantes, trampas, hechos verificados |
| — | `decisiones.md` | Registro de decisiones difíciles de revertir (D-001 a D-010) |
| 10 | `datos.md` | Esquema exacto de la fuente, matriz de poblado, validaciones, cobertura |
| 11 | `agregados.md` | Grano y presupuesto en MB de cada tabla, umbrales, válvulas |
| 08 | `repositorio.md` | Árboles de los dos repos, CLI, convenciones, secretos |
| 03 | `infraestructura.md` | Cuentas, límites medidos, costes, escalamiento |
| 04 | `arquitectura.md` | Flujo, horizontes, cadencia, capa de IA |
| 02 | `propuesta-valor.md` | Tesis, promesa, pruebas, objeciones, lo que no se promete |
| 05 | `marca.md` | Nombre, isotipo, paleta con significado, tipografía, tono |
| 06 | `mockup.md` | Especificación de Radar y Benchmark |
| 07 | `wireframe.md` | Mapa de navegación y dónde cae el muro |
| 01 | `modelo-negocio.md` | Segmentos, planes, precio, cobro, canales |
| 12 | `validacion.md` | Hipótesis, umbral congelado, qué hacer si falla |
| 13 | `operacion.md` | Procedimientos ante fallo, alarmas, credenciales |
| 14 | `legal.md` | Enmascaramiento, atribución, corrección, términos |

---

## 9. Estado actual — 15 de agosto de 2026

**Fase 1 cerrada. Fase 2 en curso: la aplicacion.**

| Pieza | Estado |
|---|---|
| Historico | **140 de 140 meses.** 2.774.263 procesos frente a 2.774.265 de la API |
| Agregados | 77.693 entidades · 264.276 entidad_ano · 168.151 relaciones · 256 baja_metodo |
| Taxonomia | 242 categorias tras fusionar · 262.244 procesos clasificados |
| Migraciones | 0001-0030 aplicadas. `migrar.yml` las aplica desde Actions, con `recalcular` |
| Parquet | **Republicandose los 140 meses** con esquema declarado (D-028), 4 tandas |
| Espacio | 379 MB de 460 presupuestados |
| Pruebas | 107 verdes. `test_renglones.py` comprueba que los renglones sumen el monto (D-041) |
| Aplicacion | Next.js 16.3.1 en Vercel. Portada, radar, buscador, ficha de proveedor y ficha de entidad |

**Flujos programados, corriendo solos:** ingesta 09:30 UTC, agregados 09:48. Verdes.

**Servicios:** GitHub listo (**el token caduca el 13 de septiembre de 2026**); Vercel
Hobby con `pliego` desplegado; Resend con `darkmelon.com` verificado (DKIM y SPF correctos, region sa-east-1); **DMARC existe pero es `p=none` y sus informes van a Brevo**, un proveedor anterior;
DeepInfra verificado y en uso.

**Pendientes con fecha:** registrar `pliego.ec` (35 USD/año); rotar las siete credenciales
que pasaron por chat antes de cobrar; publicar DMARC antes del primer envio masivo;
renovar el token de GitHub antes del 13 de septiembre o los flujos dejaran de correr en
silencio.

---

## 10. Que falta

**Fase 2, la aplicacion.** Hechas: buscador, ficha de proveedor, ficha de entidad.
Faltan:
1. **Mercado por categoria** — precio, quien gana, quien compra. Es la antesala del
   benchmark, y donde deberian caer los enlaces de categoria del buscador. Vuelve a la
   barra de navegacion cuando exista.
2. **Entrar / perfil** — enlace magico, y el muro pasa a ser real. Hasta que exista,
   `Muro.tsx` lleva a una ruta que no esta. Los compradores huerfanos YA estan
   calculados: solo falta quien puede verlos.
3. **Fusionar mas categorias.** El umbral de 0,92 se quedo corto: «Equipo de maquinaria»,
   «Maquinaria pesada» y «Equipo y Maquinaria» siguen siendo tres. Ver D-021.

**Lo ultimo para que el benchmark exista:** poblar `precio_cpc` y `mercado_cpc_prov`
desde los Parquet, cuando termine la republicacion. `precios.py` ya esta escrito.

**Trampas del entorno local**, para no redescubrirlas:
- Windows ARM64 no tiene ruedas de `psycopg` ni `pyarrow`. El destino es Actions sobre
  Linux x86-64. Por eso `ingesta.py --seco` no importa `carga.py`, y por eso el esquema
  del Parquet se declara en texto y no con tipos de pyarrow (D-028).
- `git push` **se queda colgado sin decir nada** cuando el gestor de credenciales de
  Windows no responde. Con la URL y el token explicitos sube en segundos. El
  `-c http.version=HTTP/1.1` sigue haciendo falta por el «Connection was reset».
- La consola de Windows mutila el texto acentuado. **Nunca diagnosticar codificacion
  mirando la pantalla**: usar `repr()` o `ord()`.
- No escribir literales acentuados en codigo de deteccion de mojibake: las herramientas
  de edicion los normalizan. Construirlos con `chr()`.
- **Sustituir texto por programa falla en silencio si no encuentra la cadena.** Usar la
  herramienta de edicion, que si falla, o verificar con `assert` despues.
- **PostgREST y el indice de texto completo:** un filtro sobre `objeto` se traduce a
  `to_tsvector(objeto)`, que NO usa el GIN de la columna generada `objeto_ts`. 3,2 s
  contra 0,23 s. Consultar siempre `objeto_ts=wfts(spanish).<texto>`.
