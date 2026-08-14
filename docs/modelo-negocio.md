# Modelo de negocio

Documento 01. Contiene lo necesario para poner un precio en una página y medir si alguien lo
acepta. Nada más.

---

## 1. La ventaja de partida

**El censo completo de clientes potenciales lo genera el propio producto.** No hay que estimar
el mercado ni comprar una base de datos: los 20 972 proveedores que ganaron algo en 2024 están
en los datos, con RUC, categoría, territorio y facturación.

Pocas veces se empieza un negocio con la lista nominal de clientes ya en la mano.

---

## 2. Segmentación y prioridad

| Segmento | Empresas | % del monto | Producto | Prioridad |
|---|---|---|---|---|
| **Núcleo** — facturan 100 K a 2 M | **6 697** | **40,2%** | Profesional | **MVP** |
| Cola — facturan 25 K a 100 K | 6 617 | 5,1% | Básico | Segundo escalón |
| Grandes — más de 2 M | 564 | 53,6% | Institucional con API | Venta acompañada |
| Entidades contratantes | 5 066 | — | Institucional | Mercado invertido |

Justificación del recorte en `decisiones.md` D-004. En resumen: por debajo de 25 K la
suscripción sería entre el 2% y el 12% de todo lo que facturan al Estado; el tramo de 25 K a
100 K tiene la recurrencia más baja de la tabla (52,3%), población flotante; por encima de 2 M
ya hay área de licitaciones y la venta es otra.

---

## 3. Planes

### Gratuito — consulta abierta
Fichas de proveedor y entidad, histórico, buscador, tamaño de mercado por categoría, y el radar
con 24 horas de retardo.

**Función:** canal de adquisición y posicionamiento en buscadores. **No es una versión
recortada: es el anzuelo, y tiene que ser bueno por sí solo.**

### Profesional — 600 USD al año, IVA incluido
Benchmark de precio unitario, compradores huérfanos, ratio de baja por método, radar sin
retardo, alertas por correo con frecuencia elegible, y exportación.

**Ancla de precio:** el 0,25% de lo que factura la mediana del tramo objetivo. Se paga cuarenta
veces con un solo contrato de menor cuantía ganado de más — el ticket medio de ese método fue
55 233 USD en 2024.

### Institucional — a convenir
Para entidades contratantes y gremios: en qué categorías se paga por encima del mercado, qué
proveedores concentran, acceso por API.

**Función:** tique alto y prueba social. **No se persigue hasta que el Profesional funcione.**

---

## 4. Economía unitaria

- **Costo marginal por suscriptor: prácticamente cero.** Todas las consultas caras se resuelven
  contra tablas agregadas precalculadas una vez al día para todos.
- **Infraestructura en régimen: ~69 USD/mes** (`infraestructura.md` §3).
- **Dos suscripciones anuales cubren la infraestructura entera.**

| Hito | Clientes | Ingreso anual |
|---|---|---|
| Cubrir infraestructura | 2 | 1 200 |
| Validación del MVP | 15 | 9 000 |
| Penetración del 3% del núcleo | 201 | 120 600 |
| Mercado total del núcleo | 6 697 | 4 018 200 |

---

## 5. Cobro

**Stripe no opera en Ecuador.** Detalle y alternativas en `decisiones.md` D-005.

- **Transferencia bancaria más factura electrónica** desde el primer cliente. Cero comisión,
  cero integración, y en B2B ecuatoriano es lo normal.
- **Plan anual anticipado con descuento de dos meses.** Elimina la cobranza recurrente —que sin
  pasarela es trabajo manual—, mejora la caja desde el primer cliente, y filtra hacia el
  proveedor que se toma en serio vender al Estado.
- **IVA del 15% dentro del precio anunciado**, no encima. Una sorpresa al final del checkout
  arruina la conversión justo en el momento que se está midiendo.
- **Prever las retenciones**: los clientes que son agentes de retención retienen parte del IVA
  y del impuesto a la renta. Se cobra menos de lo facturado y la diferencia se recupera como
  crédito tributario. No es impago.
- **Factura electrónica ante el SRI con API** desde el inicio, para que la emisión no sea una
  tarea manual por cliente.

PayPhone cuando la cobranza manual duela; Kushki o PlaceToPay con volumen y recurrencia.

---

## 6. Canales

En orden de coste, no de eficacia:

1. **Búsqueda orgánica.** Las fichas de proveedor son públicas e indexables. Lento pero compone.
2. **Contacto directo.** El propio dato incluye el `contactPoint` de muchas partes. Se aborda
   por categoría, con el informe de sus compradores huérfanos como carta de presentación.
3. **Gremios y cámaras** del sector elegido.
4. **Contenido**: publicar el análisis de una categoría al mes. El material ya lo produce el
   pipeline sin trabajo adicional.

⚠ **La lista no se quema.** Un envío masivo mal hecho arruina el dominio y el canal a la vez.
Lotes pequeños, opt-in real, DMARC publicado antes.

---

## 7. Aplazado

Proyecciones financieras a tres años, coste de adquisición y valor de vida del cliente. No son
estimables antes de tener los primeros quince clientes, y calcularlos ahora produciría números
inventados con apariencia de análisis.
