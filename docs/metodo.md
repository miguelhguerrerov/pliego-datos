# Método de verificación

Documento 15. Escrito a posteriori, sobre los **catorce fallos encontrados construyendo**
la fase 1 (D-011 a D-024). No son buenas prácticas generales: son las reglas que habrían
atrapado esos catorce casos concretos.

---

## 1. El dato que ordena todo lo demás

De los catorce fallos, **cuatro no produjeron ningún error**:

| | Qué pasó | Qué se veía |
|---|---|---|
| D-014 | El radar cargaba sin montos | Ingesta en verde, 1 546 filas cargadas |
| D-016 | `objeto` guardaba el código de expediente, no lo que se compra | Campo poblado al 100% |
| D-021 | «Material de oficina» partido en 7 categorías | 400 categorías creadas |
| D-022 | La ingesta diaria descategorizaba el radar cada mañana | Ingesta y agregados en verde |

**Las 36 pruebas pasaron en los cuatro casos.** No es que fueran malas pruebas: es que
verificaban funciones, y el fallo estaba en el resultado. Una función que escribe
`title` en la columna `objeto` funciona perfectamente; lo que falla es que `title` no es
el objeto.

De ahí la regla principal.

---

## 2. Las siete reglas

### 2.1 Una consulta de producto por cada función que se cobra

Después de cada carga, ejecutar **las consultas que haría un usuario** y afirmar que
devuelven algo sensato. No «la tabla tiene filas», sino «el radar devuelve oportunidades
con monto», «el buscador encuentra "medicamentos"», «los compradores huérfanos de una
categoría existen».

Los cuatro fallos silenciosos se detectaron así, y dos de ellos por casualidad: consulté
los datos para enseñarlos, no para verificarlos. Convertir esa casualidad en obligación es
la mejora de mayor rendimiento de toda la lista.

Implementado en `pruebas/test_producto.py`.

### 2.2 Cardinalidad de entrada y salida en cada transformación

`17 473 → 15` tenía que gritar. `400 categorías → 257 nombres` también. `266 794 → 262 244
clasificados` también.

Toda transformación registra cuántos elementos entran y cuántos salen, y **falla si la
proporción es extrema**. Es una línea de código y habría atrapado D-016, D-021 y D-022.

### 2.3 Verificar en el mismo nivel donde ocurre el fallo

Tres fallos vinieron de observar a través de una capa que miente:

- **D-011**: diagnostiqué la codificación mirando la consola de Windows, que mutila
  acentos. Los bytes estaban bien. La «reparación» habría corrompido 2,77 M de registros.
- **D-017**: comprobé `pg_constraint`, vi la restricción única y di el resto por hecho. El
  `NOT NULL` seguía ahí, en `information_schema.columns`. La comprobación buena fue
  **insertar la fila exacta que fallaba**.
- **D-023**: verifiqué con `import clasifica`, que evalúa el archivo entero. En producción
  se ejecuta como programa, y ahí las funciones definidas tras el guard `__main__` no
  existen cuando `main()` las llama.

**Si falla como programa, pruébalo como programa. Si el problema son bytes, mira bytes.**

### 2.4 Medir antes de rebajar un invariante

Dos veces estuve a punto de relajar una regla documentada por un coste que resultó ser
irrelevante:

- Guardar todas las grafías de nombre para resolver la moda parecía caro. Medido: **4 MB,
  el 0,9% del presupuesto**. La regla se cumplió tal como estaba escrita.
- Al revés también: los índices de `hecho_mes` parecían inocuos y costaban **173,5 MB, el
  38% del presupuesto**, sin servir a ninguna consulta.

La intuición sobre costes se equivocó en un orden de magnitud en ambas direcciones.
**Medir cuesta minutos; rebajar un invariante cuesta el resto del proyecto.**

### 2.5 Toda alarma necesita una prueba de falso positivo

D-020: el publicador marcaba como parcial todo mes en el que algún método no tuviera
datos. Como siempre hay métodos sin datos, **todos los meses salían parciales**.

Una advertencia que salta sin motivo entrena a ignorarla. No es ruido inocuo: **destruye
el valor de las advertencias verdaderas**, que son las que quedarán cuando algo falle de
verdad. Cada alarma necesita una prueba que confirme que **no** salta en el caso normal.

### 2.6 Nunca editar a ciegas

Dos fallos —y media hora de trabajo perdida— vinieron de sustituir texto por programa sin
comprobar que la sustitución se aplicó:

- La lista de detección de mojibake quedó normalizada y el detector pasó a marcar como
  corrupto cualquier texto en español bien escrito.
- `main()` nunca llamó a `escribir()`: la taxonomía se construyó, costó treinta minutos y
  se tiró.

Usar la herramienta de edición, que falla cuando no encuentra el texto. Si hay que
sustituir por programa, **`assert` después**. Y no añadir código al final de un archivo que
termina en `if __name__` (D-023).

### 2.7 Distinguir «falló el trabajo» de «falló el último paso»

D-024: el flujo apareció en rojo y la fusión **sí se había aplicado** — 400 categorías
pasaron a 242 correctamente. Solo falló la recuperación de espacio, al final.

Si hubiera dado el trabajo por perdido, habría repetido treinta minutos sin necesidad.
**Ante un fallo, verificar el estado antes de reaccionar.**

---

## 3. Lo que no hay que cambiar

Tres cosas funcionaron y conviene no perderlas al añadir reglas:

- **El registro de decisiones.** Catorce de las veinticuatro entradas son errores. Sin
  ellas, una sesión futura repetiría la reparación de codificación o los índices inútiles.
- **Las cifras de control.** Tener escrito «2024 son 219 185 procesos» convirtió la
  validación del backfill en una comparación de un segundo.
- **Parar a medir en vez de suponer.** Todos los aciertos de esta sesión —la descarga
  masiva, el hueco de la subasta inversa, el coste de la clasificación— salieron de
  comprobar contra la fuente en vez de razonar sobre ella.

---

## 4. Resumen operativo

| Regla | Fallos que habría atrapado |
|---|---|
| Consulta de producto tras cada carga | D-014, D-016, D-021, D-022 |
| Cardinalidad de entrada y salida | D-016, D-021, D-022 |
| Verificar en el nivel del fallo | D-011, D-017, D-023 |
| Medir antes de rebajar un invariante | D-018 y un falso ahorro |
| Prueba de falso positivo por alarma | D-020 |
| No editar a ciegas | dos reemplazos silenciosos |
| Verificar el estado antes de reaccionar | D-024 |

**Siete reglas, catorce fallos.** La primera sola cubre cuatro.
