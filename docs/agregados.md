# Agregados y presupuesto de 500 MB

Documento 11. La restricción del plan gratuito convertida en especificación ejecutable.

**Regla de admisión.** Una tabla entra en Postgres solo si responde que sí a: *¿la consulta la
aplicación en cada carga de página?* Si no, va a Parquet.

---

## 1. Presupuesto

| Tabla | Grano | Filas | MB |
|---|---|---|---|
| `entidad` | RUC | 120 K | 25 |
| `entidad_ano` | RUC × año × rol | 600 K | 45 |
| `precio_cpc` | CPC × año | 200 K | 20 |
| `mercado_cpc_prov` | CPC × provincia × año | 800 K | 60 |
| `relacion` | comprador × proveedor × año | 1,5 M | 90 |
| `proceso_resumen` | ocid, ventana 24 meses | 490 K | 140 |
| `baja_metodo` | método × CPC × año | 80 K | 5 |
| `categoria` | categoría normalizada | 3 K | <1 |
| `cobertura` | año × mes | 150 | <1 |
| Índices y `tsvector` español | — | — | 80 |
| Tablas de usuario | — | — | <5 |
| **Total** | | | **~460** |

**Alarma a 420 MB.** `pruebas/test_presupuesto.py` falla la construcción al superarla.
El trabajo nocturno registra el tamaño por tabla para ver la tendencia, no solo el valor.

### Válvulas, decididas de antemano

1. **Ventana de `proceso_resumen` de 24 a 18 meses** → libera ~45 MB. Es un parámetro, no una
   migración. Ninguna función del producto se pierde.
2. **`relacion` limitada a los últimos 3 años** → libera ~40 MB, a costa de profundidad en
   compradores huérfanos.

---

## 2. Definición de cada tabla

### `entidad`
```sql
ruc              text primary key
nombre           text        -- la grafía más frecuente en los últimos 2 años
tipo             text        -- 'comprador' | 'proveedor' | 'ambos'
es_persona_natural boolean   -- determina el enmascaramiento (ver legal.md)
provincia        text
canton           text
tramo            text        -- '<5K' | '5-25K' | '25-100K' | '100-500K' | '500K-2M' | '2-10M' | '>10M'
activa_desde     date
activa_hasta     date
```
Solo entidades con actividad en los últimos 3 años. El resto vive en Parquet.
`nombre` se resuelve por moda, no por el último visto: los datos antiguos tienen más erratas.

### `entidad_ano`
```sql
ruc, anio, rol   -- clave compuesta; rol = 'comprador' | 'proveedor'
monto            numeric
n_procesos       int
n_contrapartes   int      -- la métrica que sostiene la tesis del producto
n_categorias     int
```

### `precio_cpc`
```sql
cpc, anio, unidad -- clave compuesta
n                int      -- número de adjudicaciones con unidad y cantidad declaradas
p10, p25, mediana, p75, p90, minimo, maximo   numeric
```
**Solo ítems con unidad y cantidad declaradas.** Los que no las tienen entran al conteo de la
categoría pero no a la distribución de precio.

### `mercado_cpc_prov`
```sql
cpc, provincia, anio
monto, n_procesos, n_proveedores, n_entidades
```

### `relacion`
```sql
comprador_ruc, proveedor_ruc, anio
monto, n_procesos
categorias   text[]
```
Es la matriz que alimenta compradores huérfanos. La consulta es *«entidades que compraron la
categoría X y no tienen fila con el proveedor Y»*.

### `proceso_resumen`
```sql
ocid             text primary key
fecha            date
estado           text        -- 'planificacion' | 'abierto' | 'adjudicado' | 'cerrado'
metodo           text
cpc              text
categoria_id     int         -- la clasificada por embeddings
comprador_ruc    text
proveedor_ruc    text
referencial      numeric
adjudicado       numeric
provincia        text
objeto           text        -- truncado a 200 caracteres
objeto_ts        tsvector    -- búsqueda de texto completo en español
```
Ventana de 24 meses. Alimenta el radar y el buscador; **no** alimenta estadísticas.

### `baja_metodo`
```sql
metodo, cpc, anio
n, ratio_mediana, ratio_p25, ratio_p75
```
Solo filas donde referencial y adjudicado existen ambos. **Subasta inversa electrónica solo se
puebla desde la ruta JSON** (ver `datos.md` §4).

### `categoria`
```sql
id, nombre, cpc_representativos text[], n_procesos
```
Resultado del agrupamiento por embeddings. Los vectores viven en Parquet, no aquí.

---

## 3. Reglas de cálculo

**Ventana de análisis.** Termina 4 meses antes de hoy. Los meses posteriores existen en
`proceso_resumen` para el radar pero **no alimentan ningún agregado estadístico**
(ver `decisiones.md` D-009).

**Umbral de publicación.**

| n | Comportamiento |
|---|---|
| `n < 5` | No se muestra nada. «Datos insuficientes en esta categoría» |
| `5 ≤ n < 20` | Se muestra con advertencia visible de muestra pequeña |
| `n ≥ 20` | Se muestra normal |

En todos los casos el `n` va junto a la cifra (invariante 11).

**Compradores huérfanos.** Entidad que:
- adjudicó en la categoría del suscriptor en los **últimos 18 meses**,
- por un monto acumulado **superior a 5 000 USD**,
- y **nunca** le adjudicó a ese proveedor en toda la serie.

Ordenados por monto descendente. Los tres parámetros son configurables y su valor por defecto
es esta especificación, no una constante enterrada en el código.

**Ratio de baja.** `adjudicado / referencial`, descartando los casos donde el ratio supera 1,5
(errores de captura en la fuente). Se reporta la mediana, no la media.

**Refresco.** Los agregados se recalculan **enteros** cada noche desde los Parquet. No hay
actualización incremental: es más lento y más frágil que rehacerlos, y el coste de rehacerlos
es de minutos.

---

## 4. Tablas de usuario

No son regenerables. Son las que migran cuando se cambie de cuenta, y las que se exportan cada
noche al repositorio privado (invariante 14).

```sql
suscriptor    correo (pk) · nombre · ruc · plan · alta · estado
perfil        correo · categorias[] · provincias[] · monto_min · frecuencia('diaria'|'semanal')
envio_log     correo · fecha · n_coincidencias · resend_id · estado
lista_espera  correo · ruc · categoria · acepta_precio(bool) · fecha
```

**Enlazadas por correo, no por la UUID de `auth.users`** (invariante 7). Es lo que hace que la
migración de cuenta cueste media jornada.
