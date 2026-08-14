# Infraestructura

Documento 03. Estado verificado contra las API con credenciales reales el 14 de agosto de 2026.
No leído de páginas de precios.

---

## 1. Cuentas

| Servicio | Cuenta | Plan | Estado |
|---|---|---|---|
| GitHub | `miguelhguerrerov` | Free | Listo. 3 repos públicos, 12 privados |
| Supabase | org `miguelhguerrerov@gmail.com` (`qqrkhdsvynqorznusxxi`) | Free | Listo, 0 proyectos, **2 cupos libres** |
| Vercel | equipo `miguelhguerrerovs-projects` | Hobby | Listo. 7 proyectos, 0 dominios |
| Resend | cuenta Darkmelon | Free | `darkmelon.com` verificado (DKIM + SPF) |
| DeepInfra | — | Uso | Verificado: BGE-M3 y Llama 3.3 70B responden |
| Dominio | `pliego.ec` | 35 USD/año | **Por registrar** |

---

## 2. Límites reales y qué imponen

### GitHub Free
- 2 000 min/mes de Actions en repositorios **privados**; **ilimitados en públicos**.
- Token clásico con `repo`, `workflow`, `admin:repo_hook`, `write:packages`.
- Límite de API: 5 000 peticiones/hora.
- **Los releases no tienen límite práctico de tamaño** y se sirven por CDN.

→ *Impone:* el repositorio de ingesta va público. Es donde corre todo el cómputo pesado y
donde vive el detalle en Parquet.

⚠ **El token caduca el 13 de septiembre de 2026.** Si para entonces los flujos ya corren,
dejarán de funcionar en silencio. Alarma 30 días antes en `operacion.md`.

### Supabase Free
- **500 MB de base de datos.**
- **2 proyectos activos por usuario, no por organización.** Comprobado con un 400 explícito:
  crear organizaciones adicionales no da cupo (ver `decisiones.md` D-007).
- 5 GB de egress, 1 GB de storage, 50 000 usuarios activos al mes.
- Proyecto pausado tras una semana de inactividad.
- **Sin copias de seguridad.**

→ *Impone:* el detalle no entra en Postgres (invariante 1); la exportación nocturna de
suscriptores es obligatoria (invariante 14); el cron diario mantiene el proyecto activo por sí
solo.

**Región: `us-east-1`.** Aunque São Paulo esté más cerca en el mapa, el tráfico desde Ecuador
se enruta habitualmente por Miami, y us-east es donde Vercel tiene mejor conectividad.

**La cuenta es temporal por diseño.** Al llegar los clientes se migra a la cuenta personal con
Pro. Los invariantes 5, 6, 7 y 8 existen para que esa migración cueste media jornada.

### Vercel Hobby
- 100 GB de tránsito, compartidos entre los 7 proyectos de la cuenta.
- Fluid compute, CI/CD, CDN global.
- **Los términos prohíben el uso comercial.**

→ *Impone:* Pro (20 USD/mes) es obligatorio **en el momento en que se activa un botón de
pago**, no antes. Un test gratuito con lista de espera es defendible.

### Resend Free
- 3 000 correos al mes, **tope de 100 diarios**, 1 dominio verificado, 30 días de registro.
- Al llegar al tope **pausa el envío en vez de facturar**.
- La cuota es **de la cuenta, compartida** con los proyectos `focus-360` y
  `Supabase_AgroFinca_V3`, que ya tienen claves ahí.

→ *Impone:* un solo correo por suscriptor y día con todo agrupado (invariante 13); frecuencia
elegible entre diaria y semanal para multiplicar la capacidad; cola con reintento y alarma al
80%; y log de envíos propio en Postgres, porque el de Resend caduca a los 30 días.

⚠ **Falta DMARC.** DKIM y SPF están verificados; DMARC no aparece. Para escribir a empresas
ecuatorianas con filtros corporativos, DMARC es buena parte de lo que separa la bandeja de
entrada del spam. Registro TXT, arrancar en `p=none`, **antes del primer envío masivo**.

### DeepInfra
Verificado con llamadas reales:

| Modelo | Uso | Coste medido |
|---|---|---|
| `BAAI/bge-m3` | Embeddings, 1024 dimensiones | 48 tokens por 3 objetos contractuales |
| `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Etiquetado de grupos | 0,0000055 USD por 44 tokens |

Separación semántica comprobada en español: «suero antiofídico» contra «medicamentos» da
0,663; contra «vía asfaltada», 0,477.

**Proyección:** a ~30 tokens por objeto contractual, embeber los 2,77 M cuesta **menos de
1 USD**. El etiquetado de grupos, otro dólar. Es el único gasto variable del MVP.

---

## 3. Costes

### MVP — hasta la validación
| Concepto | USD |
|---|---|
| GitHub, Supabase, Vercel, Resend | 0 |
| Dominio `pliego.ec` | 35 / año |
| DeepInfra, carga histórica | ~2 una vez |
| DeepInfra, operación | ~1 / mes |
| **Total del primer año** | **~50** |

### Régimen — con producto de pago
| Concepto | USD/mes |
|---|---|
| Supabase Pro | 25 |
| Vercel Pro | 20 |
| Resend Pro | 20 |
| Dominio | ~3 |
| DeepInfra | ~1 |
| **Total** | **~69** |

Dos suscripciones anuales de 600 USD cubren la infraestructura entera.

---

## 4. Disparadores de escalamiento

| Señal | Acción | USD/mes |
|---|---|---|
| Se activa el primer botón de pago | Vercel Pro — obligatorio por términos | 20 |
| La base pasa de 500 MB | Supabase Pro | 25 |
| Los resúmenes pasan de 100 diarios (~85 suscriptores, menos lo que consuman los otros proyectos) | Resend Pro | 20 |
| Llegan clientes de verdad | Migrar a la cuenta personal con Pro | — |

---

## 5. Pendientes con fecha

1. **Registrar `pliego.ec`** — 35 USD/año. Bloquea el sitio.
2. **Publicar DMARC en `darkmelon.com`** — antes del primer envío masivo.
3. **Rotar las credenciales que pasaron por chat** — antes del primer despliegue. Son siete:
   dos de Supabase, una de GitHub, dos de Resend, una de Vercel, una de DeepInfra.
   La más sensible es el token antiguo de Supabase: da acceso de gestión a los seis proyectos
   de la cuenta personal, incluidos dos en producción.
4. **Renovar el token de GitHub** — antes del 13 de septiembre de 2026.
