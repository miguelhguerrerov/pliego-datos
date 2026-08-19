# Manual de operación

Documento 13. La ingesta va a fallar: de 24 meses cargados en las pruebas, **10 necesitaron
reintentos**. Esto no es una hipótesis.

---

## 1. Calendario

| Trabajo | Cuándo | Qué hace |
|---|---|---|
| `ingesta-diaria` | 09:00 UTC (04:00 ECT) | Mes en curso y anterior · ~3 MB |
| `enviar-resumenes` | Tras la ingesta diaria | Un correo por suscriptor, agrupado |
| `exportar-suscriptores` | Tras el envío | Vuelca tablas de usuario al repo privado |
| `ingesta-semanal` | Domingo | Últimos 6 meses |
| `ingesta-mensual` | Día 3 | Últimos 18 meses |
| `ingesta-trimestral` | Días 1 de ene/abr/jul/oct | Histórico completo + cuadre contra la API |

La ingesta diaria mantiene además el proyecto de Supabase activo por sí sola, lo que evita la
pausa por inactividad del plan gratuito.

---

## 2. Procedimientos

### Un mes no descarga tras 4 intentos
1. Trocear por `method` y reintentar solo los métodos que faltan.
2. Si sigue fallando, marcar el mes como `pendiente` en `cobertura` y **continuar con el
   resto**.
3. **Nunca detener toda la ingesta por un mes.** El trabajo semanal lo reintentará solo.

Verificado: un mes que agotó los tres intentos en una pasada entró sin problema en la
siguiente.

### Respuesta truncada (`IncompleteRead`)
Se trata como fallo de descarga. **El ZIP parcial se descarta sin intentar abrirlo** — un ZIP
truncado puede abrirse parcialmente y cargar datos incompletos sin error visible.

### Reprocesar un mes concreto
```bash
python src/ingesta.py --mes 2026-08 --forzar
python src/agrega.py
```
No hace falta tocar el resto.

### Reconstruir todo desde cero
```bash
psql "$SUPABASE_DB_URL" -f migraciones/0001_esquema.sql   # y siguientes
python src/ingesta.py --desde-releases                    # lee de Parquet, NO del SERCOP
python src/agrega.py
```
**Menos de una hora.** Es también el procedimiento de migración a otra cuenta de Supabase.

### Cambio de esquema en la fuente
La prueba de contrato falla y detiene la ingesta. Se actualiza `docs/datos.md` y el
normalizador **antes** de volver a cargar.

⚠ **Jamás relajar la prueba para que pase.** Es la única defensa contra corromper la base en
silencio.

### Proyecto de Supabase pausado
No debería ocurrir: el trabajo diario lo mantiene activo. Si ocurre, restaurar desde el panel;
los datos siguen ahí.

### Cuota de Resend agotada
Resend **pausa el envío en vez de facturar**. Los pendientes quedan en cola y se reintentan al
día siguiente. **No se pierden avisos.** Si ocurre dos días seguidos, es momento de Resend Pro
o de cuenta separada — la cuota está compartida con otros proyectos de Darkmelon.

### `Network is unreachable` al conectar a Postgres
El host directo `db.<ref>.supabase.co` **solo resuelve a IPv6** y los runners de GitHub
Actions no tienen IPv6. Usar el agrupador en **modo sesión**:

```
postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

**Puerto 5432, no 6543.** El 6543 es modo transacción y no soporta `COPY` ni sentencias
preparadas, que es de lo que depende la carga masiva. `carga.py` valida ambas cosas y
falla con el mensaje correcto en vez de con un error de red.

### Base cerca del límite
Aplicar la primera válvula: ventana de `proceso_resumen` de 24 a 18 meses. Libera ~45 MB y es
un parámetro, no una migración. Segunda válvula en `agregados.md` §1.

---

### El respaldo no corrió, o salió vacío

El flujo `respaldo.yml` vive en **pliego-app** (privado), no en pliego-datos: los correos
de los suscriptores no pueden acabar en un repositorio público. Corre a las 07:00 UTC.

- **Falla con «Falta el secreto SUPABASE_DB_URL»**: hay que añadirlo en
  *pliego-app → Settings → Secrets → Actions*. Es el mismo valor que ya está en
  pliego-datos.
- **Falla con «suscriptor.csv salió con 0 filas»**: se detiene a propósito y **no
  guarda**. Un respaldo vacío es peor que ninguno, porque da sensación de cobertura. Si
  la tabla está de verdad vacía, algo se borró: mirar Postgres antes de tocar nada.
- **Restaurar**: los CSV están en `respaldo/` del repositorio privado, con cabecera.
  `\copy suscriptor from 'suscriptor.csv' with (format csv, header)`.

---

## 3. Alarmas

Llegan por correo al operador desde el mismo trabajo nocturno. **Un fallo silencioso es peor
que uno ruidoso.**

| Señal | Umbral | Gravedad |
|---|---|---|
| Tamaño de la base | > 420 MB | Alta |
| Mes sin cargar | > 48 h | Alta |
| Cambio de esquema en la fuente | Inmediata | **Crítica** |
| Cuota de correo | > 80% del tope diario | Media |
| Caducidad del token de GitHub | 30 días antes | **Crítica** |
| Cuadre anual contra la API | Desvío > 0,1% | Media |
| Ratio de baja fuera de rango histórico | Desviación > 10 pp | Media |

La última detecta corrupción silenciosa: si el ratio de menor cuantía deja de ser 1,000, algo
se rompió en la normalización.

---

## 4. Qué se le dice al usuario

**Se le dice, visiblemente.** Cuando un mes está incompleto, la interfaz lo muestra en la nota
de cobertura al pie de cada vista afectada, con la fecha de la última carga correcta.

La tentación de esconderlo es fuerte porque parece un defecto. Es al revés: **declarar la
incertidumbre es la fuente de credibilidad del producto**, y es lo que lo distingue de un Excel
que afirma con la misma seguridad esté completo o no.

Texto tipo, no negociable en su contenido:

> Datos actualizados al 13 de agosto de 2026. Julio está al 59% de cierre y no entra en las
> estadísticas de mercado.

---

## 5. Credenciales y su ciclo

| Credencial | Caduca | Acción |
|---|---|---|
| Token de GitHub | **13 de septiembre de 2026** | Renovar y actualizar el secreto |
| Las siete que pasaron por chat | — | **Rotar antes del primer despliegue** |
| Contraseña de la base | — | Guardada fuera del repo; se puede restablecer desde el panel |

La más sensible es el token antiguo de Supabase: da acceso de gestión a los seis proyectos de
la cuenta personal, incluidos dos en producción.

---

## 6. Registro de incidentes

Cada fallo que llegue a producción se anota al final de este documento: fecha, síntoma, causa,
qué se cambió. Es lo que convierte un susto en una prueba automatizada.

```
## Incidentes

(ninguno todavía — el sistema no está construido)
```
