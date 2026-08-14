# Mockup de interfaz

Documento 06. **Dos pantallas en alta fidelidad, deliberadamente.** Dos fijan el lenguaje
visual completo —rejilla, tipografía, color, densidad, tratamiento de cifras y estados— y el
resto de la aplicación lo hereda. Maquetar doce antes de construir duplica el trabajo y congela
decisiones que se toman mejor con el dato real delante.

Las elegidas resuelven las dos preguntas distintas del producto: **Radar**, la razón para
volver cada día, y **Benchmark**, la razón para pagar.

> La versión renderizada de ambas está en el dossier técnico. Este documento fija las
> especificaciones que hay que respetar al implementarlas.

---

## 1. Pantalla · Radar — `/radar`

### Estructura vertical
1. Barra de aplicación: isotipo + «Pliego», navegación, entrar/cuenta.
2. Selector de perfil y filtros (estado, provincia, monto mínimo).
3. Tira de indicadores: 4 casillas.
4. Lista de oportunidades.
5. Pie: nota de cobertura con hora de la última actualización.

### Tira de indicadores
Cuatro, en rejilla de `minmax(8rem, 1fr)` con separador de 1 px:

| Indicador | Cálculo |
|---|---|
| Encajan con tu perfil | Procesos en `planning` o `tender` que cruzan categoría y territorio del perfil |
| En juego | Suma del referencial de esos procesos |
| Cierran esta semana | Los de `tender` con `tenderPeriod_endDate` a ≤ 7 días |
| Compradores nuevos | Entidades del conjunto que nunca han adjudicado al suscriptor |

Cifra en monoespaciada `1,25 rem` color adjudicado; etiqueta en `0,7 rem` apagado.

### Fila de oportunidad
Rejilla de tres columnas: `5,5rem | 1fr | auto`.

| Columna | Contenido |
|---|---|
| Estado | Píldora: `Planificación` azul, `Abierto` verde, `Comprador nuevo` ámbar |
| Cuerpo | Objeto contractual (`0,82 rem` tinta) + línea de metadatos (`0,72 rem` mono apagado): entidad · provincia · CPC o plazo |
| Valor | Monto en mono tabular, alineado a la derecha, con «referencial» debajo en `0,66 rem` |

**Por debajo de 34 rem** la rejilla colapsa a una columna y el valor se alinea a la izquierda.

### Estados a implementar
- **Sin perfil configurado:** invitación a definir categorías, no lista vacía.
- **Perfil sin coincidencias hoy:** «Nada nuevo en tus categorías desde ayer», con enlace a
  ampliar territorio o categorías. No es un error.
- **Datos del día no cargados:** nota de cobertura en ámbar con la fecha de la última carga
  correcta.

---

## 2. Pantalla · Benchmark — `/benchmark/[cpc]`

Tras el muro.

### Estructura vertical
1. Barra de aplicación.
2. Encabezado: código CPC en mono `0,68 rem` + descripción en display `1,4 rem`.
3. Bloque de distribución de precio.
4. Lectura en una frase.
5. Tabla «quién más vende esto».
6. Pie: exclusión de los últimos 4 meses y método predominante con su baja histórica.

### Bloque de distribución
Es el componente más importante del producto. Eje horizontal de 44 px de alto:

| Elemento | Tratamiento |
|---|---|
| Carril base | 6 px, superficie profunda, esquinas de 3 px |
| Rango intercuartílico | 10 px, verde al 20% |
| Mediana | Marca vertical de 2×22 px, verde pleno |
| Tu precio | Marca vertical de 2×30 px, **ámbar** |
| Etiquetas | Mono `0,63 rem`, centradas bajo cada marca |

Encabezado del bloque: «PRECIO UNITARIO ADJUDICADO · 24 meses» a la izquierda, `n = 214
adjudicaciones` a la derecha. **El n nunca es opcional.**

### Lectura en una frase
Debajo del gráfico, en `0,86 rem`, con el dato en negrita:

> Tu precio está **un 9,1% por encima de la mediana** y dentro del cuartil superior. Nueve de
> cada diez adjudicaciones de los últimos dos años cerraron por debajo.

Es la frase la que se recuerda, no el gráfico. Se genera con plantilla, no con modelo de
lenguaje: tiene que ser exacta.

### Estados a implementar
- **`n < 5`:** no se muestra la distribución. «No hay adjudicaciones suficientes de este ítem
  en los últimos 24 meses para calcular un precio de referencia.»
- **`5 ≤ n < 20`:** se muestra con banda ámbar de muestra pequeña.
- **Sin precio propio del suscriptor:** se muestra la distribución sin la marca ámbar y se
  invita a introducir su precio.
- **Método sin referencial** (subasta inversa desde CSV): la sección de baja se oculta con nota
  explicativa, no con un `NaN`.

---

## 3. Decisiones que estas dos pantallas dejan fijadas

- **Densidad alta y sin adornos.** El cliente escanea.
- **Toda cifra en monoespaciada tabular.** Sin excepciones.
- **El estado se codifica en forma y color a la vez**, nunca solo en color.
- **El número de observaciones acompaña siempre al agregado.**
- **La nota de cobertura va al pie, visible.** Es la regla de marca convertida en componente
  reutilizable (`NotaCobertura.tsx`).
- **Sin ilustraciones, sin fotografía, sin iconos decorativos.** El único gráfico es el que
  contiene datos.

---

## 4. Aplazado

Ficha de proveedor, ficha de entidad, buscador, panel de compradores huérfanos, ajustes de
perfil, registro, muro de pago y portada. **Todas están en el wireframe**, que es donde su
estructura importa; su acabado se resuelve construyéndolas con datos reales delante.

Estados de carga y de error se definen al implementar cada pantalla, que es cuando se sabe qué
puede fallar de verdad.
