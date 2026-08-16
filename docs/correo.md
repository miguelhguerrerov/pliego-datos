# Correo — cómo sale cada mensaje de Pliego

Resend, por **dos caminos distintos** que conviene no confundir, porque fallan de forma
distinta y tienen cuotas distintas.

---

## 1. Enlace mágico — lo envía Supabase, no nosotros

El correo de autenticación lo genera Supabase Auth cuando alguien pide entrar. Nuestro
código nunca lo toca.

**Hoy sale por el remitente por omisión de Supabase**, que tiene dos problemas:

- Límite de unos **4 correos por hora** para todo el proyecto. Sirve para probar y no
  para tener usuarios.
- Llega con remitente de Supabase, no de Pliego. En un producto que se vende a empresas,
  eso resta más de lo que parece.

**La solución es SMTP propio, y es configuración del panel, no código.** En
*Project Settings → Auth → SMTP Settings*:

| Campo | Valor |
|---|---|
| Host | `smtp.resend.com` |
| Puerto | `465` |
| Usuario | `resend` |
| Contraseña | la clave de API de Resend |
| Remitente | `pliego@darkmelon.com` |

**Esto no puede vivir en una migración** porque no es estructura de base de datos. Es la
única pieza del sistema que se configura a mano, y por eso está escrita aquí: si alguien
migra el proyecto a otra cuenta de Supabase, esto se pierde en silencio y el síntoma será
«nadie puede entrar», no «falta el SMTP».

---

## 2. Alertas diarias — las enviamos nosotros

Van desde GitHub Actions con la API de Resend. Es lo que fija el **invariante 13**:

> Un solo correo por suscriptor y por día, con todas las coincidencias agrupadas. Nunca
> un correo por oportunidad.

Ese invariante no es estético, es aritmético. El radar tiene unos 15 000 procesos
abiertos; un correo por oportunidad y por suscriptor agota cualquier cuota en una mañana.

---

## Las cuotas, y dónde aprieta primero

Plan gratuito de Resend: **3 000 correos al mes, 100 al día, un solo dominio**.

Los 100 diarios son el techo real, y con el invariante 13 se traducen directamente:

| Suscriptores con alerta diaria | Correos/día | ¿Cabe? |
|---|---|---|
| 50 | 50 | Sí |
| 100 | 100 | Justo en el límite |
| 150 | 150 | **No** |

El segmento objetivo son 6 697 empresas. Si se suscribe el 2%, son 134 al día y el plan
gratuito ya no llega. **El primer límite de crecimiento del producto cuesta 20 USD al
mes** (Resend Pro, 50 000 correos) — y para cuando haga falta, habrá ingresos. No es un
problema que resolver ahora; es uno que hay que saber que llega y cuándo.

**El dominio único sí aprieta antes.** El plan gratuito permite uno y `darkmelon.com` ya
lo ocupa. Consecuencias:

- Los correos salen de `pliego@darkmelon.com`, no de `pliego.ec`.
- Cuando se registre `pliego.ec`, añadirlo como segundo dominio **exige el plan de pago**.
- Verificar un subdominio aparte tampoco vale: cuenta como dominio. Ya está en la tabla
  de trampas de `CLAUDE.md`.

---

## DMARC — corregir lo que hay, no publicarlo de cero

`CLAUDE.md` decía «sin DMARC». **Es falso**, comprobado contra el DNS:

```
_dmarc.darkmelon.com   "v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com"
```

Existe, pero:

- **`p=none`** significa «observa y no hagas nada». No protege contra suplantación; solo
  evita que la ausencia del registro penalice.
- **Los informes agregados van a Brevo**, un proveedor de correo que ya no se usa. Es
  telemetría del propio dominio saliendo hacia un tercero sin motivo.

DKIM y SPF sí están verificados y correctos.

**Qué hacer, en orden:**

1. Apuntar `rua` a una dirección propia. Es cambiar una cadena en el DNS.
2. Dejar `p=none` unas semanas y **leer los informes** antes de endurecer. Pasar a
   `p=quarantine` sin mirar antes es la forma más rápida de que el correo legítimo de la
   empresa deje de llegar.
3. Endurecer a `p=quarantine` cuando los informes confirmen que todo lo legítimo pasa.

El orden importa: el paso 3 antes del 2 rompe el correo de la empresa entera, no solo el
de Pliego.
