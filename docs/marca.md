# Manual de marca

Documento 05. Esbozo operativo: lo suficiente para construir la interfaz sin decidir color y
tipografía sobre la marcha. Un manual de cuarenta páginas para un producto sin clientes es
justo el documento que envejece y miente.

---

## 1. Nombre

**Pliego.** Es el documento que define qué compra el Estado y bajo qué condiciones: vocabulario
nativo del sector, que el cliente ya usa a diario. Corto, pronunciable, sin anglicismo y sin
necesidad de explicación.

Descarta deliberadamente el registro habitual del sector —nombres con «data», «tech» o
«smart»— porque el cliente objetivo no se identifica con eso: dirige una empresa mediana que
vende al Estado y desconfía del vocabulario de consultora.

**Dominio:** `pliego.ec`, 35 USD/año. El `.ec` no es una concesión: refuerza que es un producto
ecuatoriano sobre datos ecuatorianos.

**Escritura.** Siempre «Pliego», nunca «PLIEGO» ni «pliego» en cuerpo de texto. Sin eslogan
pegado al nombre.

---

## 2. Marca gráfica

Dos barras: el **presupuesto referencial** y el **monto adjudicado**. El hueco entre ambas es
el ahorro, que es la cifra alrededor de la cual gira el producto entero. La marca *es* la
tesis.

```svg
<svg viewBox="0 0 34 34">
  <rect x="2" y="7"  width="30" height="7" rx="1.5" fill="#3C6280" opacity="0.45"/>
  <rect x="2" y="20" width="21" height="7" rx="1.5" fill="#0E7259"/>
</svg>
```

- Barra superior: referencial, en azul al 45% de opacidad.
- Barra inferior: adjudicado, en verde pleno. Ancho al 70% de la superior.
- **Prueba mínima obligatoria:** legible a 16 px como favicon. La pasa.
- Versión monocroma: ambas barras en tinta, la superior al 35%.
- Nunca inclinar, rotar, añadir sombra ni degradado.

---

## 3. Paleta

Derivada del papel de registro contable y de la tinta, no de una tendencia. **Los dos colores
de datos significan algo fijo en todo el producto.**

| Nombre | Claro | Oscuro | Significado — no negociable |
|---|---|---|---|
| Adjudicado | `#0E7259` | `#48BA9A` | El valor real, el cierre, la acción |
| Referencial | `#3C6280` | `#82A9C6` | El valor de partida, lo planificado, lo abierto |
| Atención | `#A25617` | `#D98B3F` | Dato provisional, cobertura incompleta, tu posición |
| Tinta | `#0E1A1D` | `#E7EEEC` | Texto. Negro sesgado a azul, nunca negro puro |
| Papel | `#F1F4F2` | `#0C1214` | Fondo. Gris sesgado a verde, nunca blanco puro |
| Superficie | `#FAFCFB` | `#141E21` | Tarjetas y tablas |
| Apagado | `#5A6A6D` | `#8D9FA1` | Texto secundario, etiquetas, metadatos |
| Regla | `#D2DCD8` | `#253338` | Bordes y separadores |

**Reglas de uso**

- Verde y azul **solo** como adjudicado y referencial. Nunca decorativos.
- El ámbar nunca es «error»: es «mira esto con cuidado». Los errores usan tinta y texto claro.
- Todo color se toma de `estilos/tokens.css`, jamás como literal en un componente. La interfaz
  vive en claro y oscuro, y un literal rompe uno de los dos.

---

## 4. Tipografía

Sin webfonts: el producto carga rápido y no depende de un CDN externo.

| Rol | Pila | Uso |
|---|---|---|
| Display | `Georgia, "Iowan Old Style", "Times New Roman", serif` | Titulares y cifras destacadas. Aporta la formalidad de documento oficial que el sector espera. Con moderación |
| Texto | `system-ui, "Segoe UI", Roboto, sans-serif` | Lectura corrida e interfaz. Neutra a propósito: en un producto de datos la personalidad la ponen las cifras |
| Datos | `ui-monospace, "Cascadia Mono", Consolas, "SF Mono", monospace` | **Toda** cifra, código CPC, RUC, fecha y etiqueta |

**Regla que más cambia la percepción de rigor:** `font-variant-numeric: tabular-nums` en todo
lo numérico. Las columnas de números tienen que alinear.

Escala: `0,66 · 0,72 · 0,82 · 0,94 · 1,0 · 1,15 · 1,4 · 1,9 · 2,6 rem`. No se sale de ella.

---

## 5. Tono de voz

- **Cifra antes que adjetivo.** «El 86,3% del referencial», no «un ahorro significativo».
- **Se declara lo que no se sabe.** Cobertura incompleta, muestra pequeña y dato provisional se
  dicen en pantalla. Es la fuente de credibilidad del producto, no un defecto a esconder.
- **Sin épica.** El cliente quiere ganar un contrato más, no transformarse digitalmente.
  Prohibidos: «revolucionar», «potenciar», «solución integral», «transformación digital».
- **Señal, nunca acusación.** Ni una palabra que sugiera conducta indebida de nadie. No es
  delicadeza: es supervivencia legal y comercial.
- **Los errores dicen qué pasó y cómo arreglarlo.** Sin disculpas ni vaguedad.
  Mal: «Algo salió mal». Bien: «No hay datos de esta categoría en Loja. Prueba a nivel
  nacional».
- **Español de Ecuador.** «Adjudicar», «oferente», «entidad contratante», «referencial»,
  «partida presupuestaria». El vocabulario del cliente, no el nuestro.

---

## 6. Reglas de aplicación en interfaz

- **Toda cifra agregada muestra su número de observaciones** al lado. Sin excepción.
- Con `n < 5` no se muestra la cifra; se dice que no hay datos suficientes.
- Con `5 ≤ n < 20` se muestra con advertencia visible de muestra pequeña.
- El estado se codifica **en forma y color a la vez**, nunca solo en color.
- La nota de cobertura va al pie de cada vista afectada, visible, no escondida.
- Sin emojis como marcadores de sección ni iconografía redundante.
- Densidad alta y sin adornos: el cliente escanea, no lee.

---

## 7. Aplazado

Aplicaciones de marca, papelería, sistema completo de iconos, variantes del logotipo,
plantillas de presentación. Nada de eso desbloquea trabajo del MVP.

**Pendiente de verificar:** que `pliego.ec` siga disponible al registrar, y que no haya
conflicto de nombre con un servicio existente en el sector.
