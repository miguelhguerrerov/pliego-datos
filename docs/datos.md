# Contrato de datos

Documento 10. Todo lo que sigue está **medido contra el servicio real** el 14 de agosto de
2026, no leído de una especificación. La fuente no está documentada en ningún otro sitio.

---

## 1. Rutas de acceso

### 1.1 Descarga masiva — ruta principal

```
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/download
  ?type=csv|json|xlsx
  &year=YYYY
  &month=M          (1–12; omitir para el año entero, no recomendado)
  &method=all       (o el nombre exacto del método, con acentos y espacios codificados)
```

Devuelve un **ZIP**. Sin autenticación. Sin límite de peticiones observado.
`Access-Control-Allow-Origin: *`.

| Formato | Contenido | Tamaño de un mes | Tiempo |
|---|---|---|---|
| `csv` | 8 archivos normalizados | ~2,6 MB | ~1,8 s |
| `json` | Array de paquetes OCDS completos | ~10–20 MB | 20–120 s |
| `xlsx` | Equivalente al CSV | — | no se usa |

**El JSON de un mes entero corta la conexión a los ~120 s.** Trocear por `method`.
Valores válidos de `method`, tal como los publica el portal:

```
Subasta Inversa Electrónica
Licitación
Licitación de Seguros
Cotización
Menor Cuantía
Catálogo electrónico - Compra directa
Catálogo electrónico - Mejor oferta
Catálogo electrónico - Gran compra mejor oferta
Catálogo electrónico - Gran compra puja
Contratos entre Entidades Públicas o sus subsidiarias
Bienes y Servicios únicos
Contrataciones con empresas públicas internacionales
all
```

### 1.2 API paginada — solo refresco del día en curso

```
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds
  ?year=&search=&page=&buyer=&supplier=
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/record?ocid=
```

- `X-RateLimit-Limit: 60` por minuto.
- **10 registros por página, fijo.** `page_size` y `limit` se ignoran silenciosamente.
- Respuesta de `search_ocds`: `{total, page, pages, data[]}`.
- Campos de `data[]`: `id · ocid · year · month · method · internal_type · locality ·
  region · suppliers · buyer · amount · date · title · description · budget`.
- Tiene datos del día en curso; la descarga masiva va un día por detrás.

**No usar para backfill:** 277 427 páginas a 60/min son 77 horas.

---

## 2. Esquema del ZIP en CSV

Ocho archivos, con el mes en español en el nombre: `releases_2024_febrero.csv`.

| Archivo | Filas por mes | Columnas |
|---|---|---|
| `metadata_` | 1 | metadatos del paquete |
| `extensions_` | pocas | URLs de extensiones OCDS aplicadas |
| `releases_` | ~17 800 | `ocid · id · initiationType · buyer_id · buyer_name · language · date · tag` |
| `planning_` | ~1 800 | `ocid · id · rationale · budget_id · budget_description · budget_amount · budget_currency` |
| `tender_` | ~17 500 | ver abajo |
| `awards_` | ~17 400 | `ocid · release_id · id · title · description · status · date · amount · currency · correctedValue_amount · correctedValue_currency · enteredValue_amount · enteredValue_currency · contractPeriod_startDate · contractPeriod_endDate · contractPeriod_maxExtentDate · contractPeriod_durationInDays` |
| `suppliers_` | ~17 400 | `ocid · release_id · award_id · id · name` |
| `contracts_` | ~17 200 | `ocid · release_id · id · awardID · title · description · status · contractPeriod_startDate · contractPeriod_endDate · contractPeriod_maxExtentDate · contractPeriod_durationInDays · amount · currency · dateSigned` |

`tender_` completo:

```
ocid · release_id · id · title · description · status
procuringEntity_id · procuringEntity_name
value_amount · value_currency
procurementMethod · procurementMethodDetails · mainProcurementCategory · awardCriteria
tenderPeriod_startDate · tenderPeriod_endDate · tenderPeriod_maxExtentDate · tenderPeriod_durationInDays
enquiryPeriod_startDate · enquiryPeriod_endDate · enquiryPeriod_maxExtentDate · enquiryPeriod_durationInDays
hasEnquiries · eligibilityCriteria
awardPeriod_startDate · awardPeriod_endDate · awardPeriod_maxExtentDate · awardPeriod_durationInDays
numberOfTenderers
```

**Lo que el CSV no trae y el JSON sí:** ítems con CPC y precio unitario, oferentes,
pujas, direcciones de las partes, cantón y provincia.

---

## 3. Esquema del ZIP en JSON

Un array de paquetes; cada paquete contiene `releases[]` con normalmente un release.

Claves de nivel de paquete: `uri · license · version · releases · publisher · extensions ·
publishedDate · publicationPolicy`. La licencia declarada es
`https://creativecommons.org/licenses/by/3.0/ec/`.

Claves de un release:

```
id · ocid · tag · date · language · initiationType
buyer{id, name}
planning{budget{id, amount{amount,currency}}, rationale}
tender{...}
awards[]
contracts[]
parties[]
bids{statistics[] | details[]}
auctions[]            (en subasta inversa: stages[].bids[] y winningBids[])
relatedProcesses[]    (vínculo a convenio marco / catálogo)
```

`tender`:

```
id · title · description · status · value{amount,currency}
procuringEntity{id, name} · procurementMethod · procurementMethodDetails
mainProcurementCategory · awardCriteria · eligibilityCriteria
tenderPeriod · enquiryPeriod · awardPeriod
numberOfTenderers          ← competencia real del proceso
tenderers[]{id, name}      ← TODOS los oferentes, no solo el ganador
lots[]
items[]                    ← la base del benchmark de precios
```

`tender.items[]` y `awards[].items[]`:

```json
{
  "id": "13007-PE-C",
  "quantity": 2085,
  "description": "Suero antiofidico polivalente",
  "unit": {"id":"436","name":"Unidad","scheme":"SERCOP",
           "value":{"amount":37.2,"currency":"USD"}},
  "classification": {"id":"3525015266","scheme":"CPC","description":"..."},
  "additionalClassifications": [{"id":"35250.1.5266","scheme":"CPC","uri":"..."}],
  "valueBreakdown": [
    {"id":"discount-…","description":"Descuento por producto","value":{...}},
    {"id":"net-…","description":"Precio unitario","value":{...}},
    {"id":"tax-iva-0%-…","description":"Iva por producto 0%","value":{...}},
    {"id":"total-iva-0%-…","description":"Total por producto","value":{...}}
  ],
  "relatedLot": "398007"
}
```

`parties[]`:

```json
{
  "id": "EC-RUC-1791240502001-14583",
  "name": "CEDIMED CIA. LTDA.",
  "roles": ["supplier"],
  "address": {"region":"PICHINCHA","locality":"QUITO","countryName":"ECUADOR",
              "streetAddress":"..."},
  "identifier": {"id":"EC-RUC-1791240502001-14583","scheme":"EC-RUC","legalName":"..."},
  "contactPoint": {"url":"http://www.cedimed.com.ec","name":"..."}
}
```

---

## 4. Matriz de poblado — el hueco que cuesta caro

Presupuesto referencial (`tender.value_amount`) disponible por método, 2024 completo:

| Método | Procesos | Monto | Referencial en CSV | En JSON |
|---|---|---|---|---|
| **Subasta inversa electrónica** | 24 060 | 1 881 M | **vacío en los 24 060** | sí, + pujas |
| Catálogo electrónico compra directa | 53 059 | 735 M | sí | sí |
| Menor cuantía | 5 887 | 325 M | sí (5 694) | sí |
| Cotización | 2 469 | 705 M | sí (2 307) | sí |
| Licitación | 574 | 1 201 M | sí (522) | sí |
| Licitación de seguros | 837 | 219 M | sí (804) | sí |
| Contratos entre entidades públicas | 1 074 | 414 M | sí (1 049) | sí |
| Bienes y servicios únicos | 1 779 | 275 M | sí (1 707) | sí |

**Consecuencia.** El método con más procesos competidos del país y el mayor monto adjudicado
es justo donde el análisis más valioso solo existe por la ruta JSON. Cualquier cálculo de baja
que salga `NaN` para subasta inversa indica que se está leyendo el CSV.

Otros campos con poblado parcial que hay que declarar en la interfaz:

- `mainProcurementCategory`, `awardCriteria`, `eligibilityCriteria`: vacíos en catálogo
  electrónico.
- `numberOfTenderers`: ausente en catálogo electrónico y en compra directa.
- `planning`: presente en ~10% de los releases del CSV, más frecuente en el JSON.
- `locality` y `region`: **no están en el CSV**; se obtienen de `parties[].address` en el
  JSON, o de `search_ocds`.

---

## 5. Reglas de tratamiento

### 5.1 Codificación — CORREGIDO 2026-08-14

**La fuente entrega UTF-8 válido.** Verificado sobre los archivos reales: «Catálogo» llega
como `b'Cat\xc3\xa1logo'`, que es UTF-8 correcto. Los ocho archivos del ZIP y la respuesta
JSON de la API decodifican como UTF-8 sin error.

> **Corrección de una conclusión previa.** Durante el análisis se anotó que el servidor
> devolvía «latin-1 etiquetado como UTF-8». **Era falso**: el símbolo de sustitución que se
> veía provenía de la consola de Windows al imprimir, no de los datos. Implementar esa
> reparación habría convertido `Catálogo` en `CatÃ¡logo`, corrompiendo datos correctos.
> Se deja escrito porque es el error exacto que este documento existe para evitar.

**Qué se hace en su lugar.** `src/codificacion.py` no repara: **valida**.

1. Decodifica en UTF-8 estricto. Si falla, **detiene la ingesta** — significa que la fuente
   cambió.
2. Detecta doble codificación buscando secuencias delatoras (`Ã¡`, `Ã©`, `Ã³`, `Ã±`, `Â`).
   Si aparecen, detiene la ingesta.
3. Registra el resultado en `cobertura.nota`.

Casos de prueba en `pruebas/test_codificacion.py`:

| Entrada | Resultado esperado |
|---|---|
| `b'Cat\xc3\xa1logo'` | `Catálogo`, válido |
| `b'Cat\xf3logo'` | Error de decodificación, ingesta detenida |
| `'CatÃ¡logo'` | Doble codificación detectada, ingesta detenida |
| `b'Contrataci\xc3\xb3n'` | `Contratación`, válido |

### 5.2 Identidad
- **Proceso:** el `ocid`. Deduplicar por él antes de cargar.
- **Entidad:** el RUC, extraído de `EC-RUC-<ruc>-<secuencia>` tomando **el tercer segmento**
  al partir por `-`. El sufijo de secuencia varía entre releases para la misma empresa: usarlo
  como clave duplica entidades.
- **Nunca unificar por nombre.** La misma empresa aparece con varias grafías a lo largo de
  once años, y ese es el defecto que ensucia cualquier ranking. En el análisis previo, contar
  por `id` completo dio 18 908 proveedores y contar por RUC dio 20 972 sobre datos distintos:
  la clave importa.

### 5.3 Estados
`tag` es la máquina de estados y **los intermedios son el producto**:

| `tag` | Significado | Uso |
|---|---|---|
| `["planning"]` | Necesidad declarada, con partida y monto. Sin proceso abierto | Radar, anticipación de semanas |
| `["planning","tender"]` | Proceso abierto, recibiendo ofertas | Radar, urgente |
| `["planning","tender","award"]` | Adjudicado, sin contrato firmado | Seguimiento |
| `["tender","award","contract"]` | Cerrado | Estadística |

### 5.4 Montos
Llegan como texto con decimales. `amount` nulo se trata como cero **y se marca**; la fila no
se descarta. `budget - amount` es el ahorro; solo tiene sentido cuando ambos existen.

---

## 6. Validaciones previas a la carga

| Comprobación | Si falla |
|---|---|
| El ZIP contiene los 8 archivos esperados | Rechazar el mes, marcarlo `pendiente` |
| Las columnas coinciden con el esquema de la sección 2 | **Detener la ingesta y avisar.** Es cambio de esquema |
| Ningún `ocid` duplicado tras deduplicar | Rechazar |
| Las cadenas reparadas no contienen el carácter de sustitución `U+FFFD` | Rechazar |
| El total del año cuadra con el declarado por `search_ocds` | Cargar como `degradado` |
| El mes tiene menos del 50% de los registros del mismo mes del año anterior | Cargar como `parcial` |

**Nunca relajar una prueba para que pase.** Si el esquema cambió, se actualiza este documento
y el normalizador antes de volver a cargar.

---

## 7. Registro de cobertura

```sql
create table cobertura (
  anio          int  not null,
  mes           int  not null,
  estado        text not null check (estado in ('cargado','parcial','pendiente','degradado')),
  registros     int,
  pct_cerrado   numeric(5,2),
  fecha_carga   timestamptz,
  nota          text,
  primary key (anio, mes)
);
```

**Consultable desde la aplicación, no escondido en un log.** Es lo que impide presentar datos
incompletos como completos — lo que ya ocurrió una vez en el análisis previo, y solo se
detectó porque el mes faltante estaba anotado.

---

## 8. Fallos conocidos de la fuente

De 24 meses cargados, **10 necesitaron reintentos**:

- `The read operation timed out` — el más común.
- `IncompleteRead(3183108 bytes read, 691772 more expected)` — respuesta truncada a media
  descarga. El ZIP parcial se descarta sin intentar abrirlo.
- Tiempos del mismo endpoint entre **17 y 200 segundos**, sin patrón.
- Un mes agotó los tres intentos en una pasada y entró sin problema en la siguiente.

**Política:** 4 intentos con espera creciente, troceo por `method` cuando el mes entero no
pasa, y registrar como `pendiente` antes que dar por cargado.

---

## 9. Cifras de control

Para verificar que una carga es correcta:

| Comprobación | Valor esperado |
|---|---|
| Procesos 2024 | 219 185 cargados / 219 186 declarados por la API |
| Monto adjudicado 2024 | 6 895 826 063 USD |
| Proveedores únicos por RUC 2024 | 20 972 |
| Entidades únicas 2024 | 5 066 |
| Total 2015 – ago 2026 | 2 774 265 |

Ratio adjudicado/referencial, mediana 2024 — si estos valores cambian mucho, algo se rompió:

| Método | Ratio | n |
|---|---|---|
| Licitación de seguros | 0,863 | 804 |
| Licitación | 0,949 | 522 |
| Cotización | 0,951 | 2 307 |
| Menor cuantía | 1,000 | 5 694 |
| Catálogo electrónico | 1,000 | 53 059 |

---

## 10. Fuente complementaria: el PAC

Plan Anual de Contratación, en el portal transaccional, **no en OCDS**:

```
https://www.compraspublicas.gob.ec/ProcesoContratacion/compras/PC/buscarPACe.cpe
  ?entidadPac=<token>&anio=<token>&nombre=<token>
```

**Los tres parámetros van cifrados** y no se pueden construir: hay que obtenerlos del buscador
del portal, entidad por entidad. El token de año está incluido, así que una URL capturada sirve
solo para ese ejercicio.

Devuelve HTML. Filas en `<tr class=filaElemento1|filaElemento2>` — **el atributo va sin
comillas**, lo que rompe los selectores ingenuos. 17 columnas:

```
Nro · Partida Presupuestaria · CPC · Tipo Compra · Tipo Régimen · Fondo BID
Tipo de Presupuesto · Tipo de Producto · Catálogo Electrónico · Procedimiento
Descripción · Cantidad · Unidad de Medida · Costo Unitario · Valor Total · (vacío) · Período
```

`Período` es el cuatrimestre previsto: `C1`, `C2`, `C3` o combinaciones.

**Qué aporta que el OCDS no tiene:** anticipación de meses en vez de semanas, el cuatrimestre
planificado, el costo unitario previsto, y sobre todo **ínfima cuantía** — 90 de 305 líneas en
la muestra medida. Ese método no aparece en OCDS por estar bajo el umbral de publicación.

**Coste:** 27 s por consulta. Recorrer las 5 066 entidades serían ~38 h por ejercicio.

**Decisión:** no entra en el MVP. Cuando entre, se resuelven los tokens una sola vez para unos
cientos de entidades relevantes y se recorren mensualmente. Queda por comprobar si el token de
entidad es estable entre ejercicios o cambia entero cada enero.
