"""Las plantillas de correo de Pliego, en un solo sitio.

    python src/correo.py --publicar    # sube las plantillas de autenticacion a Supabase
    python src/correo.py --vista       # escribe muestras HTML para mirarlas en el navegador

**Por que un modulo y no HTML suelto.** Los correos salen por dos caminos distintos
—los de autenticacion los envia Supabase, las alertas las enviamos nosotros desde
Actions— y si cada uno lleva su propio HTML, la marca se separa a la primera prisa. Aqui
el envoltorio es uno y los cuerpos cambian. Ver docs/correo.md.

**Las reglas del correo no son las de la web**, y casi todas empujan hacia atras:

- **Tablas, no `flex` ni `grid`.** Outlook usa el motor de Word para maquetar.
- **Estilos en linea.** Gmail descarta buena parte de un `<style>` y todo lo externo.
- **Sin imagenes para lo esencial.** Muchos clientes las bloquean por omision, asi que
  el isotipo va con celdas de color: dos barras, referencial y adjudicado, y el hueco
  entre ellas es el ahorro (docs/marca.md §2). Si se bloquean imagenes, no se pierde nada
  porque no hay ninguna.
- **Georgia y las pilas del sistema.** Una tipografia web no carga; elegir una que no
  esta produce una sustitucion peor que la que se eligiria a mano.
- **Nada de blanco puro ni negro puro**, igual que en la interfaz: papel `#F1F4F2` y
  tinta `#0E1A1D`.
- **Una linea de preencabezado.** Es lo que la bandeja muestra junto al asunto. Sin ella,
  el cliente de correo coge la primera frase del HTML, que suele ser «Pliego».
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# La paleta, con el significado fijo que manda docs/marca.md §3.
ADJUDICADO = "#0E7259"   # el valor real, el cierre, la accion
REFERENCIAL = "#3C6280"  # el valor de partida, lo planificado
ATENCION = "#A25617"     # dato provisional, tu posicion
TINTA = "#0E1A1D"
TINTA_SUAVE = "#33474B"
APAGADO = "#5A6A6D"
PAPEL = "#F1F4F2"
SUPERFICIE = "#FAFCFB"
REGLA = "#D2DCD8"
REGLA_SUAVE = "#E2E9E5"

DISPLAY = "Georgia,'Iowan Old Style','Times New Roman',serif"
TEXTO = "system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',sans-serif"
DATOS = "ui-monospace,'Cascadia Mono',Consolas,'SF Mono',Menlo,monospace"

SITIO = os.environ.get("PLIEGO_URL", "https://pliego-app-liart.vercel.app")


def _isotipo() -> str:
    """Las dos barras de la marca, con celdas de tabla.

    No es una imagen ni un SVG a proposito: los clientes bloquean lo primero y no
    entienden lo segundo. Con celdas siempre se ve, incluso con las imagenes desactivadas.
    """
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse">
<tr><td style="padding:0 0 3px 0"><div style="width:30px;height:7px;background:{REFERENCIAL};opacity:.45;border-radius:2px;font-size:0;line-height:7px">&nbsp;</div></td></tr>
<tr><td style="padding:3px 0 0 0"><div style="width:21px;height:7px;background:{ADJUDICADO};border-radius:2px;font-size:0;line-height:7px">&nbsp;</div></td></tr>
</table>"""


def envoltorio(titulo: str, cuerpo: str, preencabezado: str, pie_extra: str = "") -> str:
    """El marco comun: cabecera con la marca, cuerpo, y un pie que dice qué es Pliego.

    El pie no es decoracion. Un correo de un producto que el destinatario uso una vez
    hace tres semanas tiene que decir de que va sin que haya que recordarlo, o acaba en
    la carpeta de no deseado por la via mas cara: marcado a mano.
    """
    return f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{titulo}</title>
</head>
<body style="margin:0;padding:0;background:{PAPEL};color:{TINTA};font-family:{TEXTO};-webkit-font-smoothing:antialiased">
<!-- La linea que la bandeja de entrada muestra junto al asunto. Oculta en el cuerpo. -->
<div style="display:none;font-size:1px;color:{PAPEL};line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden">{preencabezado}
&#8199;&#65279;&#847;&#8199;&#65279;&#847;&#8199;&#65279;&#847;&#8199;&#65279;&#847;&#8199;&#65279;&#847;&#8199;&#65279;&#847;&#8199;&#65279;&#847;</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAPEL}">
<tr><td align="center" style="padding:28px 16px">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background:{SUPERFICIE};border:1px solid {REGLA};border-collapse:collapse">

<tr><td style="padding:26px 30px 0 30px">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
    <td style="padding-right:10px;vertical-align:middle">{_isotipo()}</td>
    <td style="vertical-align:middle;font-family:{DISPLAY};font-size:19px;color:{TINTA};letter-spacing:-.01em">Pliego</td>
  </tr></table>
</td></tr>

<tr><td style="padding:20px 30px 28px 30px">
{cuerpo}
</td></tr>

<tr><td style="padding:0 30px 26px 30px">
  <div style="border-top:1px solid {REGLA_SUAVE};padding-top:16px;font-size:12px;line-height:1.6;color:{APAGADO}">
    <strong style="color:{TINTA_SUAVE};font-weight:600">Pliego</strong> &mdash; qu&eacute; compra el Estado ecuatoriano, a qui&eacute;n y a qu&eacute; precio.
    Sobre los datos abiertos del SERCOP.{pie_extra}
  </div>
</td></tr>

</table>
</td></tr></table>
</body></html>"""


def boton(url: str, texto: str) -> str:
    """Un boton que sobrevive a Outlook.

    Es un enlace con relleno y no un `<button>`: los clientes de correo no ejecutan nada,
    y un boton de formulario sin formulario no hace nada en ninguno.
    """
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="background:{ADJUDICADO};border-radius:2px">'
        f'<a href="{url}" style="display:inline-block;padding:12px 22px;font-family:{TEXTO};'
        f'font-size:15px;color:{PAPEL};text-decoration:none;font-weight:500">{texto}</a>'
        f"</td></tr></table>"
    )


def _titular(t: str) -> str:
    return (f'<h1 style="margin:0 0 12px 0;font-family:{DISPLAY};font-weight:400;'
            f'font-size:23px;line-height:1.25;color:{TINTA}">{t}</h1>')


def _parrafo(t: str, tam: int = 15) -> str:
    return (f'<p style="margin:0 0 16px 0;font-size:{tam}px;line-height:1.62;'
            f'color:{TINTA_SUAVE}">{t}</p>')


# --- autenticacion --------------------------------------------------------------

def plantilla_enlace_magico() -> str:
    """El primer correo que recibe un cliente. Es la primera impresion del producto.

    `{{ .ConfirmationURL }}` es el marcador de Supabase y se deja tal cual.
    """
    cuerpo = (
        _titular("Tu enlace para entrar")
        + _parrafo(
            "Pulsa el bot&oacute;n y entras. No hay contrase&ntilde;a que crear ni que "
            "recordar &mdash; en Pliego no existen."
        )
        + f'<div style="margin:0 0 18px 0">{boton("{{ .ConfirmationURL }}", "Entrar en Pliego")}</div>'
        + f'<p style="margin:0 0 20px 0;font-size:13px;line-height:1.6;color:{APAGADO}">'
          f'Caduca en una hora y solo funciona una vez. &Aacute;brelo en el mismo '
          f'dispositivo desde el que lo pediste.</p>'
        + f'<div style="border-top:1px solid {REGLA_SUAVE};padding-top:14px">'
          f'<p style="margin:0 0 6px 0;font-size:12px;color:{APAGADO}">Si el bot&oacute;n no funciona, copia esta direcci&oacute;n:</p>'
          f'<p style="margin:0;font-family:{DATOS};font-size:11px;line-height:1.5;'
          f'word-break:break-all;color:{REFERENCIAL}">{{{{ .ConfirmationURL }}}}</p></div>'
    )
    pie = (
        f'<br><br><span style="color:{APAGADO}">Si no pediste este enlace, ign&oacute;ralo: '
        f'nadie ha entrado en tu cuenta y no hace falta que hagas nada.</span>'
    )
    return envoltorio(
        "Tu enlace para entrar en Pliego",
        cuerpo,
        "Un enlace, sin contraseña. Caduca en una hora.",
        pie,
    )


def plantilla_cambio_correo() -> str:
    cuerpo = (
        _titular("Confirma tu correo nuevo")
        + _parrafo(
            "Has pedido cambiar la direcci&oacute;n de tu cuenta de Pliego. "
            "Confirma desde el correo nuevo para que el cambio surta efecto."
        )
        + f'<div style="margin:0 0 18px 0">{boton("{{ .ConfirmationURL }}", "Confirmar el cambio")}</div>'
        + f'<p style="margin:0;font-size:13px;line-height:1.6;color:{ATENCION}">'
          f'Tu plan y tus alertas viajan con la direcci&oacute;n nueva: en Pliego la cuenta '
          f'<strong>es</strong> el correo.</p>'
    )
    return envoltorio(
        "Confirma tu correo nuevo en Pliego",
        cuerpo,
        "Confirma el cambio de dirección de tu cuenta.",
        f'<br><br><span style="color:{APAGADO}">Si no pediste el cambio, ign&oacute;ralo '
        f'y escr&iacute;benos: alguien conoce tu direcci&oacute;n.</span>',
    )


PLANTILLAS_AUTH = {
    "magic_link": ("Tu enlace para entrar en Pliego", plantilla_enlace_magico),
    "email_change": ("Confirma tu correo nuevo en Pliego", plantilla_cambio_correo),
}


# --- la alerta diaria -----------------------------------------------------------

def _dinero(v) -> str:
    if v is None:
        return "no declarado"
    v = float(v)
    if v >= 1e6:
        return f"${v/1e6:,.1f} M".replace(",", ".")
    if v >= 1e3:
        return f"${v/1e3:,.0f} K".replace(",", ".")
    return f"${v:,.0f}".replace(",", ".")


def plantilla_alerta(nombre: str, oportunidades: list[dict], correo: str) -> str:
    """El correo que justifica la suscripción mes a mes.

    **Un solo correo al día con todo agrupado** (invariante 13). No es una decisión de
    diseño: el radar tiene ~15.000 procesos abiertos, y un correo por oportunidad agota
    la cuota de Resend en una mañana y la paciencia del cliente antes.

    Tres cosas que este correo hace y la mayoría de las alertas del sector no:

    1. **Dice el monto en el asunto y en la primera línea.** Quien lo abre en el móvil
       entre reuniones decide en dos segundos si le interesa.
    2. **Dice cuándo cierra**, y lo destaca en ámbar si quedan siete días o menos. Una
       oportunidad que se conoce tarde vale lo mismo que no conocerla.
    3. **Dice por qué le llega.** Un correo que no explica su propio criterio se percibe
       como ruido aunque acierte, y acaba marcado como no deseado — que es la forma más
       cara de perder un canal.
    """
    urgentes = [o for o in oportunidades if (o.get("dias") is not None and o["dias"] <= 7)]
    total = sum(float(o.get("referencial") or 0) for o in oportunidades)
    n = len(oportunidades)
    plural = "es" if n != 1 else ""

    filas = []
    for o in oportunidades[:20]:
        dias = o.get("dias")
        if dias is None:
            cierre = f'<span style="color:{APAGADO}">sin fecha</span>'
        elif dias <= 7:
            cierre = f'<strong style="color:{ATENCION}">{dias} d&iacute;as</strong>'
        else:
            cierre = f"{dias} d&iacute;as"
        lugar = " &middot; " + o["provincia"] if o.get("provincia") else ""
        filas.append(
            f'<tr><td style="padding:12px 0;border-bottom:1px solid {REGLA_SUAVE};vertical-align:top">'
            f'<div style="font-size:14px;line-height:1.5;color:{TINTA}">'
            f'{o.get("objeto") or "Sin descripci&oacute;n"}</div>'
            f'<div style="font-size:12px;color:{APAGADO};padding-top:3px">'
            f'{o.get("comprador") or ""}{lugar}</div></td>'
            f'<td style="padding:12px 0 12px 14px;border-bottom:1px solid {REGLA_SUAVE};'
            f'text-align:right;white-space:nowrap;vertical-align:top">'
            f'<div style="font-family:{DATOS};font-size:14px;color:{ADJUDICADO}">'
            f'{_dinero(o.get("referencial"))}</div>'
            f'<div style="font-family:{DATOS};font-size:12px;padding-top:3px">{cierre}</div>'
            f"</td></tr>"
        )

    saludo = "Hola" + (", " + nombre if nombre else "") + "."
    resumen = (
        f"{n} oportunidad{plural} nueva{'s' if n != 1 else ''} que encajan con tu perfil"
        + (f", por {_dinero(total)} en total" if total > 0 else "")
        + "."
    )

    aviso = ""
    if urgentes:
        u = len(urgentes)
        aviso = (
            f'<div style="background:#F1E2D1;border-left:3px solid {ATENCION};'
            f'padding:11px 14px;margin:0 0 18px 0;font-size:14px;line-height:1.55;color:{TINTA}">'
            f'<strong>{u} cierra{"n" if u != 1 else ""} esta semana.</strong> '
            f"Van marcadas en &aacute;mbar m&aacute;s abajo.</div>"
        )

    cabecera_tabla = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;margin:6px 0 20px 0"><tr>'
        f'<th align="left" style="padding:0 0 8px 0;border-bottom:1px solid {TINTA};'
        f'font-family:{DATOS};font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
        f'font-weight:500;color:{APAGADO}">Objeto y comprador</th>'
        f'<th align="right" style="padding:0 0 8px 14px;border-bottom:1px solid {TINTA};'
        f'font-family:{DATOS};font-size:10px;letter-spacing:.1em;text-transform:uppercase;'
        f'font-weight:500;color:{APAGADO}">Referencial y cierre</th></tr>'
    )

    resto = ""
    if n > 20:
        resto = (f'<p style="margin:0 0 18px 0;font-size:13px;color:{APAGADO}">'
                 f"Y {n - 20} m&aacute;s en el radar.</p>")

    cuerpo = (
        _parrafo(saludo)
        + _titular(resumen)
        + aviso
        + cabecera_tabla
        + "".join(filas)
        + "</table>"
        + resto
        + f'<div style="margin:0 0 8px 0">{boton(SITIO + "/radar", "Ver el radar completo")}</div>'
    )

    pie = (
        f'<br><br><span style="color:{APAGADO}">Recibes esto porque configuraste alertas '
        f'para <span style="font-family:{DATOS}">{correo}</span>. '
        f'<a href="{SITIO}/perfil" style="color:{APAGADO}">Cambia el criterio o date de baja</a> '
        f"cuando quieras &mdash; un correo al d&iacute;a como m&aacute;ximo, nunca uno "
        f"por oportunidad.</span>"
    )

    preencabezado = (
        f"{n} nueva{'s' if n != 1 else ''}"
        + (f" por {_dinero(total)}" if total > 0 else "")
        + (f" · {len(urgentes)} cierran esta semana" if urgentes else "")
    )
    return envoltorio(f"{n} oportunidad{plural} nueva{'s' if n != 1 else ''}",
                      cuerpo, preencabezado, pie)


def asunto_alerta(oportunidades: list[dict]) -> str:
    """El asunto decide si el correo se abre. Cifra primero, adjetivos ninguno.

    Nada de «Nuevas oportunidades para tu empresa»: eso lo manda todo el mundo y no dice
    nada. Un número y un monto sí.
    """
    n = len(oportunidades)
    total = sum(float(o.get("referencial") or 0) for o in oportunidades)
    urgentes = sum(1 for o in oportunidades
                   if o.get("dias") is not None and o["dias"] <= 7)
    base = f"{n} oportunidad{'es' if n != 1 else ''} para ti"
    if total > 0:
        base += f" · {_dinero(total)}"
    if urgentes:
        base += f" · {urgentes} cierra{'n' if urgentes != 1 else ''} esta semana"
    return base


# --- publicacion ----------------------------------------------------------------

def publicar_en_supabase() -> int:
    """Sube las plantillas de autenticación por la API de gestión.

    Por API y no por el panel para que quede reproducible: es la única parte del sistema
    que vive solo en la configuración de un servicio, y si el proyecto migra de cuenta
    esto se pierde en silencio. Ver docs/correo.md.
    """
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    ref = os.environ.get("SUPABASE_PROJECT_REF")
    if not token or not ref:
        raise RuntimeError(
            "Faltan SUPABASE_ACCESS_TOKEN o SUPABASE_PROJECT_REF. Son secretos del "
            "repositorio; nunca van en el código (invariante 8)."
        )

    cuerpo = {}
    for clave, (asunto, generador) in PLANTILLAS_AUTH.items():
        cuerpo[f"mailer_subjects_{clave}"] = asunto
        cuerpo[f"mailer_templates_{clave}_content"] = generador()

    pet = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/config/auth",
        data=json.dumps(cuerpo).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # Sin esto la API responde 403. El mismo token por `curl` funciona: lo que
            # rechaza es el agente por omisión de urllib, no las credenciales — y el 403
            # se lee como «token inválido», que manda a buscar en el sitio equivocado.
            "User-Agent": "pliego-datos",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(pet, timeout=60) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")[:300]
        raise RuntimeError(
            f"La API de Supabase respondió {e.code}: {detalle}\n"
            f"Si es 401, el token de acceso caducó o no es de esta cuenta.\n"
            f"Si es 403 con un token que funciona por curl, falta la cabecera User-Agent."
        ) from e

    for clave in PLANTILLAS_AUTH:
        largo = len(d.get(f"mailer_templates_{clave}_content") or "")
        print(f"  {clave}: {largo:,} caracteres · «{d.get(f'mailer_subjects_{clave}')}»")
    return 0


MUESTRA = [
    {"objeto": "Adquisición de medicamentos e insumos para el hospital general",
     "comprador": "HOSPITAL GENERAL DOCENTE DE CALDERÓN", "provincia": "PICHINCHA",
     "referencial": 184320.50, "dias": 4},
    {"objeto": "Servicio de mantenimiento preventivo y correctivo del parque automotor",
     "comprador": "GAD MUNICIPAL DE SANTO DOMINGO", "provincia": "SANTO DOMINGO",
     "referencial": 62800, "dias": 12},
    {"objeto": "Uniformes institucionales para el personal administrativo",
     "comprador": "MINISTERIO DE EDUCACIÓN", "provincia": "PICHINCHA",
     "referencial": None, "dias": None},
]


def main() -> int:
    p = argparse.ArgumentParser(description="Plantillas de correo de Pliego")
    p.add_argument("--publicar", action="store_true", help="sube las de autenticación")
    p.add_argument("--vista", action="store_true", help="escribe muestras en .correo/")
    args = p.parse_args()

    if args.vista:
        destino = Path(".correo")
        destino.mkdir(exist_ok=True)
        (destino / "enlace.html").write_text(plantilla_enlace_magico(), encoding="utf-8")
        (destino / "cambio.html").write_text(plantilla_cambio_correo(), encoding="utf-8")
        (destino / "alerta.html").write_text(
            plantilla_alerta("Miguel", MUESTRA, "cliente@empresa.com"), encoding="utf-8")
        print(f"  muestras en {destino.resolve()}")
        print(f"  asunto de la alerta: {asunto_alerta(MUESTRA)}")
        return 0

    if args.publicar:
        return publicar_en_supabase()

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
