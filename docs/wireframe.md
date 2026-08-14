# Wireframe

Documento 07. En bloques sin acabado, a propósito: lo que se discute aquí es **estructura y
frontera comercial**, no estética.

---

## 1. Mapa de navegación

```
/                    portada                          ABIERTO
/radar               embudo en vivo                   ABIERTO con 24 h de retardo
/proveedor/[ruc]     ficha 360                        ABIERTO · indexable
/entidad/[ruc]       ficha 360                        ABIERTO · indexable
/buscar              búsqueda de objeto contractual   ABIERTO
/mercado/[cpc]       tamaño y estacionalidad          ABIERTO
─────────────────────────────────────────────────────────────
/benchmark/[cpc]     precio unitario                  MURO
/compradores         huérfanos por categoría          MURO
/perfil              alertas y frecuencia             MURO
/exportar            descargas                        MURO
─────────────────────────────────────────────────────────────
/entrar              enlace mágico, sin contraseña
/precio              plan y lista de espera
/legal/terminos  /legal/privacidad  /legal/correccion
```

## 2. Dónde cae el muro, y por qué

> **Todo lo descriptivo es gratis. Todo lo prescriptivo se paga.**
> Ver qué pasó es abierto; saber qué hacer al respecto, no.

Es una decisión de negocio, no de diseño, y equivocarse cuesta la conversión entera del test de
mercado.

| Gratis | De pago |
|---|---|
| Cuánto adjudicó esta entidad | A qué entidades deberías venderles |
| Quién ganó este proceso | A qué precio deberías ofertar |
| Qué se publicó ayer | Aviso el día que se publica |
| El tamaño de tu mercado | Tu posición dentro de él |

**El radar es gratis con 24 horas de retardo.** Da valor real, demuestra que el producto
funciona, y la inmediatez —que es lo que importa cuando un proceso cierra en tres días— es
justamente lo que se paga.

---

## 3. Estructura de pantallas

### `/radar`
```
┌─────────────────────────────────────────────┐
│ marca      navegación              entrar   │
├─────────────────────────────────────────────┤
│ [selector de perfil] [filtros: estado ·     │
│                       provincia · monto]    │
├──────────┬──────────┬──────────┬────────────┤
│ indicador│ indicador│ indicador│ indicador  │
├──────────┴──────────┴──────────┴────────────┤
│ fila: estado │ objeto · comprador │ monto   │
│ fila                                        │
│ fila                                        │
├─────────────────────────────────────────────┤
│ paginación · nota de cobertura y hora       │
└─────────────────────────────────────────────┘
```

### `/benchmark/[cpc]` — tras el muro
```
┌─────────────────────────────────────────────┐
│ marca      navegación              cuenta   │
├─────────────────────────────────────────────┤
│ CPC 3525015266                              │
│ Suero antiofídico polivalente               │
├─────────────────────────────────────────────┤
│ distribución: mín · p25 · mediana · p75 ·   │
│ máx · TU POSICIÓN            n = 214        │
├─────────────────────────────────────────────┤
│ lectura en una frase                        │
├─────────────────────────────────────────────┤
│ tabla: quién más vende · precio ·           │
│        adjudicaciones · entidades           │
├──────────────────────┬──────────────────────┤
│ baja del método      │ estacionalidad       │
├──────────────────────┴──────────────────────┤
│ nota: excluye los últimos 4 meses           │
└─────────────────────────────────────────────┘
```

### `/proveedor/[ruc]` — abierto e indexable
```
┌─────────────────────────────────────────────┐
│ marca      navegación              entrar   │
├─────────────────────────────────────────────┤
│ razón social · RUC · territorio · tramo     │
├──────────────┬──────────────┬───────────────┤
│ facturado    │ entidades    │ adjudicaciones│
├──────────────┴──────────────┴───────────────┤
│ serie anual de monto adjudicado             │
├──────────────────────┬──────────────────────┤
│ sus compradores      │ sus categorías       │
├──────────────────────┴──────────────────────┤
│ ►► «quién más compra esto y no le compra    │
│     a él»                          [MURO]   │
└─────────────────────────────────────────────┘
```

### `/entidad/[ruc]` — abierto e indexable
Simétrica a la de proveedor: qué compra, a quién, con qué estacionalidad, con qué métodos.
La llamada al muro es la inversa: «a qué precio compran otras entidades lo mismo».

### `/compradores` — tras el muro
```
┌─────────────────────────────────────────────┐
│ tus categorías: [chips editables]           │
├─────────────────────────────────────────────┤
│ entidad │ qué compró │ monto 18m │ última   │
│ entidad                                     │
│ entidad                                     │
├─────────────────────────────────────────────┤
│ ordenado por monto · exportar CSV           │
└─────────────────────────────────────────────┘
```
Cada fila enlaza a la ficha de entidad. La columna «última» es la fecha de su última
adjudicación en la categoría: indica si el ciclo está por repetirse.

### `/precio` — la pantalla que decide el test
```
┌─────────────────────────────────────────────┐
│ la promesa en una frase                     │
├─────────────────────────────────────────────┤
│ las tres pruebas, con cifras reales         │
├─────────────────────────────────────────────┤
│ qué incluye · $600 al año, IVA incluido     │
├─────────────────────────────────────────────┤
│ [correo] [RUC] [categoría]                  │
│ ☐ acepto el precio anunciado                │
│ [ Reservar mi lugar ]                       │
├─────────────────────────────────────────────┤
│ objeciones y respuesta                      │
└─────────────────────────────────────────────┘
```
La casilla «acepto el precio anunciado» **es la métrica del test**: separa el interés de la
curiosidad. Ver `validacion.md`.

---

## 4. La decisión estructural que más pesa

**Las fichas de proveedor son públicas e indexables, incluidas las de la competencia del
suscriptor.** Eso da el tráfico orgánico: alguien busca el nombre de una empresa y llega a
Pliego. Y es donde vive la llamada al muro, porque el momento de máxima intención de compra es
justo cuando alguien está mirando a un competidor.

Riesgo asumido: un proveedor puede molestarse al ver su ficha pública. Se mitiga con lo de
siempre — solo cifras de contratación pública, sin juicios, con procedimiento de corrección
publicado, y con enmascaramiento para personas naturales.

---

## 5. Navegación móvil

Por debajo de 34 rem la navegación superior se oculta y pasa a una barra inferior de cuatro
destinos: Radar · Buscar · Benchmark · Cuenta. Las filas de oportunidad colapsan a una columna.
Las tablas anchas van en contenedor con desplazamiento horizontal propio; **el cuerpo de la
página nunca se desplaza en horizontal**.

---

## 6. Aplazado

Nada estructural. Los estados vacíos, de error y de carga se definen al construir cada
pantalla, que es cuando se sabe qué puede fallar de verdad.
