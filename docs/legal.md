# Datos personales y términos

Documento 14. El único riesgo de la lista capaz de **terminar el proyecto** en vez de
retrasarlo.

> **Bloquea la apertura al público.** No es un documento que se escriba después del
> lanzamiento.

---

## 1. Enmascaramiento de personas naturales

El RUC de una persona natural **contiene su número de cédula**, y la dirección registrada suele
ser domiciliaria. Son públicos en origen, pero republicarlos en un producto comercial cae bajo
la Ley Orgánica de Protección de Datos Personales del Ecuador.

**Detección.** Un RUC de persona natural empieza por los dos dígitos de provincia y su tercer
dígito es menor que 6; los de sociedad tienen 9 y los públicos 6. La regla se implementa en
`src/entidades.py` y se refleja en la columna `entidad.es_persona_natural`.

| Campo | Persona jurídica | Persona natural |
|---|---|---|
| Razón social / nombre | Completo | Completo |
| RUC | Completo | **Enmascarado**: `····0001` |
| Dirección | Completa | **Solo provincia y cantón** |
| Contacto (correo, teléfono, web) | Si es corporativo | **No se publica** |
| Actividad contractual | Completa | Completa |

**La actividad contractual se muestra íntegra en ambos casos** —qué ganó, de quién, por
cuánto—: es el objeto legítimo del servicio y es información de gasto público, no personal.

**El enmascaramiento se aplica en la capa de datos**, en vistas SQL y en `lib/enmascarar.ts`,
no en el componente. Un dato que no debe salir no debe llegar al navegador.

---

## 2. Atribución y licencia

Los datos provienen del **Servicio Nacional de Contratación Pública del Ecuador**, publicados
bajo **Creative Commons BY 3.0 EC**, que permite el uso comercial y exige el crédito.

Texto de atribución, en el pie de todas las páginas y en cada exportación —no solo en «acerca
de»—:

> Fuente: Contrataciones Abiertas Ecuador — Servicio Nacional de Contratación Pública.
> Licencia CC BY 3.0 EC. Pliego no está afiliado al SERCOP ni al Gobierno del Ecuador.

La segunda frase importa tanto como la primera: evita que el producto se lea como oficial.

---

## 3. Redacción sobre indicadores

Todo indicador de concentración, oferente único o adjudicación al referencial lleva junto a él
—**en la propia interfaz, no enterrado en los términos**— la frase que lo enmarca:

> Este es un indicador estadístico calculado sobre datos públicos de contratación. No implica
> irregularidad ni juicio sobre la conducta de ninguna entidad o proveedor.

**Prohibido en todo el producto:** las palabras «irregular», «sospechoso», «riesgo de
corrupción», «alerta roja» aplicadas a una entidad o proveedor identificable. Y cualquier
listado ordenado por «riesgo».

No es delicadeza. El producto vive de que entidades públicas y grandes proveedores lo sigan
viendo como herramienta y no como amenaza: **una demanda cierra la empresa mucho antes que
cualquier problema técnico.**

---

## 4. Corrección y retiro

Procedimiento publicado en `/legal/correccion`:

1. Cualquier entidad o proveedor puede solicitar la revisión de un dato, indicando el `ocid` o
   el RUC afectado.
2. Se responde en **10 días hábiles**.
3. **Si el dato discrepa de la fuente**, se corrige y se anota en el registro de incidentes.
4. **Si coincide con la fuente**, se responde señalando el origen y enlazando al registro
   oficial. No se altera un dato público, pero **se documenta la solicitud**.
5. Los datos personales de persona natural se retiran a solicitud, conforme a la LOPDP, sin
   discusión: el enmascaramiento por defecto ya debería hacer innecesaria la solicitud.

### El respaldo también cuenta

La baja de un suscriptor **no termina en Postgres**. El respaldo nocturno del invariante
14 vive en un repositorio git privado, y **git conserva el historial**: borrar la fila y
esperar al respaldo siguiente deja el dato en los commits anteriores.

Procedimiento al dar de baja a un suscriptor que lo solicita:

1. Borrar en Postgres (`suscriptor`, `perfil`, `lista_espera`, `envio_log`).
2. **Purgar el historial del respaldo** en `pliego-app` para esa dirección, o rotar el
   respaldo entero a un almacén sin historial.
3. Anotarlo en el registro de incidentes.

Es una consecuencia deliberada de haber elegido git como almacén de respaldo —simple,
gratuito y auditable— y el precio es este paso manual. Si el volumen de bajas lo hace
inviable, la señal es mover el respaldo a un almacén con borrado real.

---

## 5. Lo que no se hace

Escrito para que esté decidido antes de que alguien lo proponga:

- **No se cruzan** estos datos con fuentes personales externas.
- **No se construyen perfiles** de personas.
- **No se publican listados** ordenados por «riesgo» ni etiquetas valorativas.
- **No se venden ni ceden** los datos de contacto de los suscriptores.
- **No se usa rastreo de terceros** ni cookies publicitarias. La instrumentación es propia y
  mínima (`validacion.md` §6).

---

## 6. Términos de uso — puntos que deben constar

Para `/legal/terminos`:

- El servicio agrega información pública y **no garantiza exactitud ni completitud**. La
  cobertura declarada en cada vista es parte del servicio, no una advertencia formularia.
- **No constituye asesoría legal, tributaria ni de contratación pública.**
- Las decisiones de oferta son responsabilidad exclusiva del suscriptor.
- Uso personal y de la empresa suscriptora; **prohibida la reventa** o redistribución masiva de
  los agregados. El dataset público en Parquet, en cambio, es libre bajo la misma licencia CC
  BY que la fuente.
- Suscripción anual, con reembolso proporcional en los primeros 30 días.
- Jurisdicción: Ecuador.

## 7. Política de privacidad — puntos que deben constar

Para `/legal/privacidad`:

- Datos que se recogen del suscriptor: **correo, RUC, categorías de interés y provincia**.
  Nada más.
- **No hay contraseñas**: la autenticación es por enlace mágico.
- Finalidad: prestar el servicio y enviar los avisos solicitados. **No se usan para otra cosa.**
- Encargados de tratamiento: Supabase (alojamiento), Resend (envío de correo), Vercel
  (servicio web), DeepInfra (clasificación de texto de contratación, **sin datos personales**).
- Derechos LOPDP: acceso, rectificación, eliminación y portabilidad, en el mismo plazo de 10
  días hábiles.
- Baja de los avisos en un clic, sin necesidad de cancelar la suscripción.
- Conservación: mientras dure la suscripción y 12 meses después, por obligaciones tributarias.
