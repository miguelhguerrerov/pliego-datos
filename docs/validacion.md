# Plan de validación

Documento 12. El documento más barato de escribir y el que más dinero puede ahorrar.

> **Este documento se congela antes de publicar la fase 3.** Modificar el umbral después de ver
> los datos invalida el experimento entero. Si se cambia, se anota aquí la fecha y el motivo, y
> se reconoce que el resultado ya no es una validación sino una impresión.

---

## 1. La hipótesis, en forma falsable

> Un proveedor que factura entre 100 000 y 2 000 000 USD al Estado pagará **600 USD al año**
> por saber qué entidades compran su categoría sin comprarle a él, y a qué precio se está
> adjudicando.

Tres supuestos, y los tres pueden fallar por separado:
1. Que el problema le duela lo suficiente.
2. Que crea que estos datos lo resuelven.
3. Que 600 al año le parezca proporcionado.

El diseño del test separa los tres: si hay visitas pero no registros, falla el 2; si hay
registros pero no aceptan el precio, falla el 3; si no hay ni visitas, no hemos probado nada.

---

## 2. Umbral, fijado ahora

Ventana de medición: **6 semanas** desde la publicación de la fase 3.

| Métrica | Umbral |
|---|---|
| Visitas a `/precio` | ≥ 400 |
| Registros en lista de espera | ≥ 60 |
| Marcan «acepto el precio anunciado» | ≥ 25 |
| **Pagan por adelantado al abrir el cobro** | **≥ 15** |

**Quince clientes anuales son 9 000 USD** y once veces la infraestructura. Es el mínimo que
distingue interés real de cortesía.

La casilla «acepto el precio anunciado» en `/precio` es la métrica central: separa la
curiosidad del compromiso sin necesidad de cobrar todavía.

---

## 3. Cómo se llega a esos proveedores

El producto genera su propia lista de clientes. Cuatro canales, detallados en
`modelo-negocio.md` §6. Para el test:

- **Contacto directo** es el canal principal, porque es el único con retroalimentación
  conversable: un «no» explicado vale más que cien visitas anónimas.
- Se aborda **por categoría**, empezando por una sola, con el informe de compradores huérfanos
  de esa empresa como carta de presentación.
- **Lotes de 20 correos**, no envíos masivos. El dominio y el canal se queman una sola vez.

---

## 4. Qué se hace si falla — decidido ahora, no después

| Síntoma | Diagnóstico | Acción |
|---|---|---|
| Visitas pero nadie se registra | El problema es el mensaje, no el producto | Reescribir `propuesta-valor.md` y repetir **una** vez |
| Registros pero nadie acepta el precio | El precio o el segmento | Probar el tramo 25 K–100 K con un plan básico antes de abandonar |
| Nadie llega | El canal | Agotar el contacto directo antes de concluir nada |
| Aceptan el precio pero no pagan | La fricción de cobro, o cortesía | Llamar a los 25. Es una conversación, no un análisis |
| **Tras dos iteraciones no se llega a 15** | La hipótesis es falsa | **Parar** |

**Si se para:** el histórico limpio, el pipeline de ingesta y el dataset público en Parquet
quedan como activo reutilizable. No es una pérdida total, y conviene recordarlo ahora para que
la decisión de parar no se posponga por aversión a la pérdida.

---

## 5. Qué NO cuenta como validación

Escrito aquí porque es donde uno se engaña:

- Felicitaciones sin registro.
- «Me parece muy interesante, mándame información.»
- Registros de gente fuera del segmento objetivo.
- Tráfico de curiosos que llegan por la ficha de un competidor y no vuelven.
- Interés de entidades contratantes. Es señal de otro producto, no de este.

---

## 6. Instrumentación mínima

Para medir lo anterior sin analítica de terceros:

- `lista_espera` en Postgres: correo, RUC, categoría, `acepta_precio`, fecha.
- Conteo de visitas a `/precio` en una tabla propia, sin cookies ni rastreo externo.
- Origen registrado como parámetro de campaña en el enlace de cada lote de contacto directo.

Nada más. La analítica detallada es una distracción cuando la pregunta es binaria.
