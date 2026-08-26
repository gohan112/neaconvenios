"""
NeaEvento — páginas HTML.

Todo el HTML de la app se genera aquí: la página del participante (móvil
primero) y el panel de administración. Sin plantillas externas ni JavaScript
de terceros: una sola hoja de estilos y funciones que devuelven HTML.

Regla de oro: TODO dato que venga de la base de datos o de un formulario pasa
por `e()` antes de incrustarse en el HTML.
"""

from __future__ import annotations

import os
from datetime import date
from urllib.parse import quote

from markupsafe import escape

_CARPETA = os.path.dirname(os.path.abspath(__file__))
HAY_LOGO = os.path.exists(os.path.join(_CARPETA, "assets", "neamaster_horizontal.png"))
HAY_ICONO = os.path.exists(os.path.join(_CARPETA, "assets", "neamaster_icono.png"))

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def e(valor) -> str:
    """Escapa cualquier valor para HTML ('' si es None)."""
    return str(escape("" if valor is None else str(valor)))


def fecha_bonita(iso: str) -> str:
    try:
        d = date.fromisoformat((iso or "").strip())
        return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"
    except ValueError:
        return iso or ""


def cuenta_atras(iso: str, referencia: date) -> str:
    try:
        d = date.fromisoformat((iso or "").strip())
    except ValueError:
        return ""
    dias = (d - referencia).days
    if dias > 1:
        return f"Faltan {dias} días"
    if dias == 1:
        return "¡Es mañana!"
    if dias == 0:
        return "¡Es hoy!"
    return ""


def enlace_maps(lugar: dict) -> str:
    """Enlace de 'cómo llegar': el de Google Maps si lo hay, o buscar la dirección."""
    if lugar.get("maps"):
        return lugar["maps"]
    if lugar.get("direccion"):
        return "https://www.google.com/maps/search/?api=1&query=" + quote(lugar["direccion"])
    return ""


ESTILO = """
:root{--rojo:#CC0C18;--rojo-oscuro:#A50A13;--tinta:#2C2C2A;--gris:#6B6862;
      --fondo:#F5F4F2;--borde:#E4E1DC;--verde:#1E9E5A;--ok-fondo:#E8F6EE}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",
     Arial,sans-serif;background:var(--fondo);color:var(--tinta);line-height:1.5;
     font-size:16px}
a{color:var(--rojo)}
.contenedor{max-width:680px;margin:0 auto;padding:0 14px 40px}
body.admin .contenedor{max-width:1100px}
.cabecera{background:#fff;border-bottom:3px solid var(--rojo);padding:12px 0}
.cabecera .contenedor{display:flex;align-items:center;gap:14px;padding-bottom:0;
                      flex-wrap:wrap}
.cabecera img{height:34px;display:block}
.marca{font-size:20px;font-weight:700;letter-spacing:-.3px}
.marca span{color:var(--rojo)}
.tarjeta{background:#fff;border:1px solid var(--borde);border-radius:14px;
         padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
h1{font-size:24px;margin:12px 0 4px}
h2{font-size:17px;margin:0 0 10px}
.etiqueta{font-size:12px;text-transform:uppercase;letter-spacing:.6px;
          color:var(--gris);font-weight:600;margin-bottom:4px}
.chip{display:inline-block;background:var(--fondo);border:1px solid var(--borde);
      border-radius:999px;padding:3px 10px;margin:2px;font-size:14px}
.chip.yo{background:#FCE9EA;border-color:var(--rojo);font-weight:600}
.insignia{display:inline-block;border-radius:999px;padding:1px 8px;font-size:12px;
          font-weight:600;white-space:nowrap}
.insignia.ok{background:var(--ok-fondo);color:var(--verde)}
.insignia.no{background:#FDECEC;color:var(--rojo)}
.insignia.pte{background:#F1EFEC;color:var(--gris)}
.boton{display:inline-block;background:var(--rojo);color:#fff;border:0;
       border-radius:10px;padding:10px 16px;font-size:15px;font-weight:600;
       cursor:pointer;text-decoration:none;text-align:center;font-family:inherit}
.boton:hover{background:var(--rojo-oscuro)}
.boton.secundario{background:#fff;color:var(--tinta);border:1px solid var(--borde)}
.boton.secundario:hover{background:var(--fondo)}
.boton.mini{padding:4px 10px;font-size:13px;border-radius:8px}
.boton.bloque{display:block;width:100%}
input,select,textarea{font:inherit;border:1px solid var(--borde);border-radius:8px;
                      padding:8px 10px;background:#fff;color:var(--tinta);
                      max-width:100%}
input:focus,select:focus,textarea:focus{outline:2px solid #F0B6BA;
                                        border-color:var(--rojo)}
label{font-size:13px;color:var(--gris);display:block;margin:8px 0 2px;font-weight:600}
form.linea{display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:0}
form.compacta{display:inline;margin:0}
.tabla{width:100%;border-collapse:collapse;font-size:14px}
.tabla th{text-align:left;color:var(--gris);font-size:12px;text-transform:uppercase;
          letter-spacing:.5px}
.tabla th,.tabla td{padding:8px;border-bottom:1px solid var(--borde);
                    vertical-align:middle}
.envoltorio-tabla{overflow-x:auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
      gap:10px;margin:12px 0}
.kpi{background:#fff;border:1px solid var(--borde);border-radius:12px;padding:12px}
.kpi .valor{font-size:26px;font-weight:700}
.kpi .texto{font-size:13px;color:var(--gris)}
.navadmin{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}
.navadmin a{padding:7px 13px;border-radius:999px;text-decoration:none;
            color:var(--tinta);background:#fff;border:1px solid var(--borde);
            font-size:14px;font-weight:600}
.navadmin a.activo{background:var(--rojo);border-color:var(--rojo);color:#fff}
.aviso{border-radius:10px;padding:10px 14px;margin:10px 0;font-size:14px;
       background:#FFF7E0;border:1px solid #EAD48A}
.aviso.ok{background:var(--ok-fondo);border-color:#BFE5CE}
.aviso.error{background:#FDECEC;border-color:#F0B6BA}
.agenda-item{display:flex;gap:12px;padding:10px 0;border-bottom:1px dashed var(--borde)}
.agenda-item:last-child{border-bottom:0}
.agenda-hora{min-width:62px;font-weight:700;color:var(--rojo);
             font-variant-numeric:tabular-nums}
.agenda-texto{flex:1}
.agenda-lugar{font-size:14px;color:var(--gris)}
.equipo-cinta{height:8px;border-radius:14px 14px 0 0;margin:-16px -16px 12px}
.equipo-nombre{font-size:22px;font-weight:700}
.pie{color:var(--gris);font-size:13px;text-align:center;margin-top:28px}
.pie a{color:var(--gris)}
details summary{cursor:pointer;color:var(--gris);font-size:14px;margin-top:8px}
.fecha-chip{display:inline-block;background:#FCE9EA;color:var(--rojo);
            border-radius:999px;padding:3px 12px;font-weight:600;font-size:14px;
            margin:6px 0}
.acciones{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.silencio{color:var(--gris);font-size:14px}
.punto-color{display:inline-block;width:14px;height:14px;border-radius:50%;
             vertical-align:-2px;margin-right:6px}
@media (max-width:520px){h1{font-size:21px}.agenda-hora{min-width:52px}}
"""

GUION = """
function copiar(btn){
  var t = btn.getAttribute('data-c') || '';
  var listo = function(){
    var v = btn.textContent; btn.textContent = '\\u2714 Copiado';
    setTimeout(function(){ btn.textContent = v; }, 1500);
  };
  if (navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(t).then(listo, function(){ window.prompt('Copia el enlace:', t); });
  } else {
    window.prompt('Copia el enlace:', t);
  }
}
"""


def base(titulo: str, cuerpo: str, *, admin: bool = False, avisos=None) -> str:
    favicon = '<link rel="icon" href="/assets/neamaster_icono.png">' if HAY_ICONO else ""
    logo = ('<img src="/assets/neamaster_horizontal.png" alt="Nea Master">'
            if HAY_LOGO else "")
    html_avisos = ""
    for categoria, texto in (avisos or []):
        clase = categoria if categoria in ("ok", "error") else ""
        html_avisos += f'<div class="aviso {clase}">{e(texto)}</div>'
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#CC0C18">
<meta name="robots" content="noindex">
<title>{e(titulo)}</title>
{favicon}
<style>{ESTILO}</style>
<script>{GUION}</script>
</head>
<body class="{'admin' if admin else ''}">
<div class="cabecera"><div class="contenedor">
  {logo}
  <div class="marca">Nea<span>Evento</span></div>
</div></div>
<div class="contenedor">
{html_avisos}
{cuerpo}
</div>
</body>
</html>"""


# ================================================================== público

def render_portada(cfg: dict, referencia: date) -> str:
    contador = cuenta_atras(cfg.get("fecha", ""), referencia)
    chip = f'<span class="fecha-chip">{e(contador)}</span>' if contador else ""
    cuerpo = f"""
<h1>{e(cfg.get('nombre'))}</h1>
<div class="silencio">📅 {e(fecha_bonita(cfg.get('fecha', '')))}
 · 🕘 {e(cfg.get('hora'))} h</div>
{chip}
<div class="tarjeta">
  <p style="margin-top:0">{e(cfg.get('descripcion'))}</p>
  <p class="silencio">Cada participante tiene un <strong>enlace personal</strong>
  donde ve su equipo, el programa del día y los lugares. Si no lo has recibido,
  pide el tuyo a la organización.</p>
  <form class="linea" method="post" action="/ir">
    <div>
      <label for="codigo">¿Tienes ya tu código?</label>
      <input id="codigo" name="codigo" placeholder="Código del enlace" required>
    </div>
    <button class="boton secundario" type="submit">Entrar</button>
  </form>
</div>
<div class="pie">Nea Master · <a href="/admin">organización</a></div>
"""
    return base(cfg.get("nombre", "Evento"), cuerpo)


def render_no_encontrado(cfg: dict) -> str:
    contacto = e(cfg.get("contacto")) or "la organización"
    cuerpo = f"""
<div class="tarjeta">
  <h2>😕 Enlace no válido</h2>
  <p>Este enlace no corresponde a ningún participante. Puede que esté incompleto
  (al copiarlo se cortó) o que la organización lo haya renovado.</p>
  <p class="silencio">Pide tu enlace de nuevo a {contacto}.</p>
  <a class="boton secundario" href="/">Ir a la portada</a>
</div>
"""
    return base("Enlace no válido", cuerpo)


def _bloque_asistencia(p: dict, cfg: dict) -> str:
    boton_si = ('<button class="boton" type="submit" name="valor" value="si">'
                '✅ ¡Sí, voy!</button>')
    boton_no = ('<button class="boton secundario" type="submit" name="valor" value="no">'
                'No puedo ir</button>')
    formulario = (f'<form class="linea" method="post" action="/p/{e(p["token"])}/asistencia">'
                  f'{boton_si} {boton_no}</form>')
    if p["confirmado"] == 1:
        return f"""
<div class="aviso ok">✅ <strong>Has confirmado tu asistencia.</strong> ¡Te esperamos!
<details><summary>Cambiar mi respuesta</summary>{formulario}</details></div>"""
    if p["confirmado"] == -1:
        return f"""
<div class="aviso">😔 Has indicado que <strong>no puedes venir</strong>.
Si cambias de planes, aquí te esperamos.
<details><summary>Cambiar mi respuesta</summary>{formulario}</details></div>"""
    return f"""
<div class="tarjeta" style="border-color:var(--rojo)">
  <h2>¿Contamos contigo el {e(fecha_bonita(cfg.get('fecha', '')))}?</h2>
  {formulario}
</div>"""


def _bloque_equipo(p: dict, equipo: dict | None, companeros: list[dict]) -> str:
    if not equipo:
        return """
<div class="tarjeta">
  <div class="etiqueta">Tu equipo</div>
  <p style="margin:4px 0">🎲 Todavía no tienes equipo asignado.</p>
  <p class="silencio" style="margin:0">Cuando se haga el reparto lo verás aquí
  mismo: vuelve a abrir este enlace más adelante.</p>
</div>"""
    color = e(equipo.get("color") or "#CC0C18")
    emoji = e(equipo.get("emoji"))
    chips = ""
    for m in companeros:
        if m["id"] == p["id"]:
            chips += f'<span class="chip yo">{e(m["nombre"])} (tú)</span>'
        else:
            chips += f'<span class="chip">{e(m["nombre"])}</span>'
    descripcion = (f'<p class="silencio" style="margin:4px 0 10px">'
                   f'{e(equipo.get("descripcion"))}</p>'
                   if equipo.get("descripcion") else "")
    return f"""
<div class="tarjeta">
  <div class="equipo-cinta" style="background:{color}"></div>
  <div class="etiqueta">Tu equipo</div>
  <div class="equipo-nombre">{emoji} {e(equipo['nombre'])}</div>
  {descripcion}
  <div class="etiqueta" style="margin-top:10px">Compañeros de equipo
  ({len(companeros)})</div>
  <div>{chips or '<span class="silencio">De momento estás tú.</span>'}</div>
</div>"""


def _item_agenda(a: dict, mostrar_equipo: bool = True) -> str:
    horas = e(a["hora"]) + (f" – {e(a['hora_fin'])}" if a.get("hora_fin") else "")
    lugar = ""
    if a.get("lugar_nombre"):
        url = enlace_maps({"maps": a.get("lugar_maps"), "direccion": a.get("lugar_direccion")})
        if url:
            lugar = (f'<div class="agenda-lugar">📍 <a href="{e(url)}" target="_blank" '
                     f'rel="noopener">{e(a["lugar_nombre"])}</a></div>')
        else:
            lugar = f'<div class="agenda-lugar">📍 {e(a["lugar_nombre"])}</div>'
    insignia = ""
    if mostrar_equipo and a.get("equipo_id"):
        color = e(a.get("equipo_color") or "#CC0C18")
        insignia = (f' <span class="insignia" style="background:{color}1A;color:{color}">'
                    f'{e(a.get("equipo_emoji"))} {e(a.get("equipo_nombre"))}</span>')
    descripcion = (f'<div class="silencio">{e(a["descripcion"])}</div>'
                   if a.get("descripcion") else "")
    return f"""
<div class="agenda-item">
  <div class="agenda-hora">{horas}</div>
  <div class="agenda-texto"><strong>{e(a['actividad'])}</strong>{insignia}
  {descripcion}{lugar}</div>
</div>"""


def _bloque_agenda(agenda: list[dict]) -> str:
    if not agenda:
        contenido = ('<p class="silencio" style="margin:0">El programa del día se '
                     'publicará aquí. Vuelve a mirar más adelante.</p>')
    else:
        contenido = "".join(_item_agenda(a) for a in agenda)
    return f'<div class="tarjeta"><h2>🗓️ Programa del día</h2>{contenido}</div>'


def _bloque_lugares(lugares: list[dict]) -> str:
    if not lugares:
        return ""
    tarjetas = ""
    for lugar_ in lugares:
        url = enlace_maps(lugar_)
        boton = (f'<a class="boton secundario mini" href="{e(url)}" target="_blank" '
                 f'rel="noopener">Cómo llegar →</a>' if url else "")
        direccion = (f'<div class="silencio">{e(lugar_["direccion"])}</div>'
                     if lugar_.get("direccion") else "")
        notas = (f'<div class="silencio">{e(lugar_["notas"])}</div>'
                 if lugar_.get("notas") else "")
        tarjetas += f"""
<div style="padding:10px 0;border-bottom:1px dashed var(--borde)">
  <strong>📍 {e(lugar_['nombre'])}</strong>
  {direccion}{notas}
  <div style="margin-top:6px">{boton}</div>
</div>"""
    return f'<div class="tarjeta"><h2>📍 Lugares</h2>{tarjetas}</div>'


def render_participante(cfg: dict, p: dict, equipo: dict | None,
                        companeros: list[dict], agenda: list[dict],
                        lugares: list[dict], referencia: date,
                        avisos=None) -> str:
    contador = cuenta_atras(cfg.get("fecha", ""), referencia)
    chip = f'<span class="fecha-chip">{e(contador)}</span>' if contador else ""
    contacto = (f'<div class="pie">¿Dudas? Contacta con {e(cfg.get("contacto"))}</div>'
                if cfg.get("contacto") else "")
    nombre_pila = (p["nombre"].split() or [""])[0]
    cuerpo = f"""
<h1>¡Hola, {e(nombre_pila)}! 👋</h1>
<div class="silencio"><strong>{e(cfg.get('nombre'))}</strong><br>
📅 {e(fecha_bonita(cfg.get('fecha', '')))} · 🕘 {e(cfg.get('hora'))} h</div>
{chip}
<p class="silencio">{e(cfg.get('descripcion'))}</p>
{_bloque_asistencia(p, cfg)}
{_bloque_equipo(p, equipo, companeros)}
{_bloque_agenda(agenda)}
{_bloque_lugares(lugares)}
{contacto}
<div class="pie">Nea Master · NeaEvento</div>
"""
    return base(cfg.get("nombre", "Evento"), cuerpo, avisos=avisos)


# ================================================================== admin

NAV_ADMIN = [
    ("/admin", "📊 Resumen"),
    ("/admin/participantes", "👥 Participantes"),
    ("/admin/equipos", "🎽 Equipos"),
    ("/admin/agenda", "🗓️ Agenda"),
    ("/admin/lugares", "📍 Lugares"),
    ("/admin/enlaces", "🔗 Enlaces"),
    ("/admin/evento", "⚙️ Evento"),
]


def _nav(ruta_actual: str, con_salir: bool) -> str:
    enlaces = ""
    for url, texto in NAV_ADMIN:
        activo = " activo" if ruta_actual == url else ""
        enlaces += f'<a class="{activo.strip()}" href="{url}">{texto}</a>'
    if con_salir:
        enlaces += '<a href="/admin/salir" style="margin-left:auto">Salir</a>'
    return f'<nav class="navadmin">{enlaces}</nav>'


def pagina_admin(titulo: str, ruta: str, cuerpo: str, *, avisos=None,
                 sin_password: bool = False, con_salir: bool = True) -> str:
    aviso_pw = ""
    if sin_password:
        aviso_pw = ('<div class="aviso">⚠️ El panel está <strong>sin contraseña</strong>. '
                    'Antes de publicar la app en internet define la variable '
                    '<code>EVENTO_ADMIN_PASSWORD</code> (ver README).</div>')
    contenido = f"{_nav(ruta, con_salir)}{aviso_pw}<h1>{e(titulo)}</h1>{cuerpo}"
    return base(f"{titulo} — NeaEvento", contenido, admin=True, avisos=avisos)


def render_entrar(avisos=None) -> str:
    cuerpo = """
<div class="tarjeta" style="max-width:420px">
  <h2>Panel de organización</h2>
  <form method="post">
    <label for="password">Contraseña</label>
    <input id="password" name="password" type="password" autofocus required>
    <div style="margin-top:12px">
      <button class="boton bloque" type="submit">Entrar</button>
    </div>
  </form>
</div>
"""
    return base("Entrar — NeaEvento", f"<h1>Organización</h1>{cuerpo}", admin=True,
                avisos=avisos)


def render_resumen(cfg: dict, datos: dict, equipos: list[dict],
                   referencia: date, avisos=None, sin_password=False) -> str:
    contador = cuenta_atras(cfg.get("fecha", ""), referencia)
    chip = f'<span class="fecha-chip">{e(contador)}</span>' if contador else ""

    kpis = ""
    for valor, texto in [
        (datos["participantes"], "participantes"),
        (datos["confirmados"], "✅ confirmados"),
        (datos["no_vienen"], "❌ no vienen"),
        (datos["pendientes"], "⏳ sin responder"),
        (datos["han_abierto"], "👁 abrieron su enlace"),
        (datos["sin_equipo"], "🎲 sin equipo"),
    ]:
        kpis += f'<div class="kpi"><div class="valor">{valor}</div><div class="texto">{texto}</div></div>'

    filas_equipos = ""
    for eq in equipos:
        filas_equipos += (f'<tr><td>{_simbolo_equipo(eq.get("color"), eq.get("emoji"))}'
                          f'{e(eq["nombre"])}</td>'
                          f'<td>{eq["n_miembros"]}</td><td>{eq["n_confirmados"]}</td></tr>')
    tabla_equipos = (f'<div class="tarjeta"><h2>Equipos</h2><div class="envoltorio-tabla">'
                     f'<table class="tabla"><tr><th>Equipo</th><th>Miembros</th>'
                     f'<th>Confirmados</th></tr>{filas_equipos}</table></div></div>'
                     if filas_equipos else
                     '<div class="tarjeta"><h2>Equipos</h2><p class="silencio">Aún no hay '
                     'equipos. Créalos en la pestaña <a href="/admin/equipos">Equipos</a>.'
                     '</p></div>')

    sin_abrir = datos.get("sin_abrir") or []
    if sin_abrir:
        nombres = ", ".join(e(n) for n in sin_abrir)
        bloque_sin_abrir = (f'<div class="tarjeta"><h2>Aún no han abierto su enlace '
                            f'({len(sin_abrir)})</h2><p class="silencio">{nombres}</p>'
                            f'<p class="silencio">Reenvíales el enlace desde la pestaña '
                            f'<a href="/admin/enlaces">Enlaces</a>.</p></div>')
    else:
        bloque_sin_abrir = ""

    pasos = ""
    if datos["participantes"] == 0:
        pasos = ('<div class="aviso">Primeros pasos: ① revisa los datos en '
                 '<a href="/admin/evento">Evento</a> · ② añade la gente en '
                 '<a href="/admin/participantes">Participantes</a> · ③ crea los '
                 '<a href="/admin/equipos">Equipos</a> y sortea · ④ monta la '
                 '<a href="/admin/agenda">Agenda</a> y los <a href="/admin/lugares">'
                 'Lugares</a> · ⑤ reparte los <a href="/admin/enlaces">Enlaces</a>.</div>')

    cuerpo = f"""
<div class="silencio"><strong>{e(cfg.get('nombre'))}</strong> ·
📅 {e(fecha_bonita(cfg.get('fecha', '')))} · 🕘 {e(cfg.get('hora'))} h</div>
{chip}
{pasos}
<div class="kpis">{kpis}</div>
{tabla_equipos}
{bloque_sin_abrir}
"""
    return pagina_admin("Resumen", "/admin", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def _simbolo_equipo(color, emoji) -> str:
    """Emoji del equipo si lo tiene; si no, su punto de color."""
    if emoji:
        return f"{e(emoji)} "
    return (f'<span class="punto-color" '
            f'style="background:{e(color or "#CC0C18")}"></span>')


def _opciones_equipos(equipos: list[dict], seleccionado=None,
                      texto_vacio: str = "— Sin equipo —") -> str:
    opciones = f'<option value="">{e(texto_vacio)}</option>'
    for eq in equipos:
        sel = " selected" if seleccionado == eq["id"] else ""
        opciones += (f'<option value="{eq["id"]}"{sel}>{e(eq.get("emoji"))} '
                     f'{e(eq["nombre"])}</option>')
    return opciones


def _insignia_estado(p: dict) -> str:
    if p["confirmado"] == 1:
        estado = '<span class="insignia ok">✅ viene</span>'
    elif p["confirmado"] == -1:
        estado = '<span class="insignia no">❌ no viene</span>'
    else:
        estado = '<span class="insignia pte">⏳ sin responder</span>'
    if p.get("visto_en"):
        estado += f' <span class="insignia pte" title="Abrió su enlace el {e(p["visto_en"])}">👁</span>'
    return estado


def render_participantes(lista: list[dict], equipos: list[dict],
                         avisos=None, sin_password=False) -> str:
    filas = ""
    for p in lista:
        if p.get("equipo_nombre"):
            equipo_html = (_simbolo_equipo(p.get("equipo_color"), p.get("equipo_emoji"))
                           + e(p["equipo_nombre"]))
        else:
            equipo_html = '<span class="silencio">—</span>'
        filas += f"""
<tr>
  <td><strong>{e(p['nombre'])}</strong></td>
  <td>{e(p['telefono']) or '<span class="silencio">—</span>'}</td>
  <td>{equipo_html}</td>
  <td>{_insignia_estado(p)}</td>
  <td class="acciones">
    <a class="boton secundario mini" href="/admin/participantes/{p['id']}">Editar</a>
  </td>
</tr>"""
    tabla = (f'<div class="envoltorio-tabla"><table class="tabla">'
             f'<tr><th>Nombre</th><th>Teléfono</th><th>Equipo</th><th>Estado</th>'
             f'<th></th></tr>{filas}</table></div>'
             if filas else
             '<p class="silencio">Todavía no hay participantes: añádelos aquí arriba, '
             'pégalos de una lista o importa un Excel/CSV.</p>')

    cuerpo = f"""
<div class="tarjeta">
  <h2>Añadir participante</h2>
  <form class="linea" method="post" action="/admin/participantes/nuevo">
    <div><label>Nombre *</label><input name="nombre" required placeholder="Nombre y apellidos"></div>
    <div><label>Teléfono</label><input name="telefono" placeholder="6XXXXXXXX"></div>
    <div><label>Email</label><input name="email" type="email"></div>
    <div><label>Equipo</label><select name="equipo_id">{_opciones_equipos(equipos)}</select></div>
    <button class="boton" type="submit">Añadir</button>
  </form>
</div>

<div class="tarjeta">
  <h2>Cargar una lista entera</h2>
  <form class="linea" method="post" action="/admin/participantes/importar"
        enctype="multipart/form-data">
    <div>
      <label>Excel (.xlsx) o CSV — columnas: nombre, telefono, email, equipo
      (solo «nombre» es obligatoria)</label>
      <input type="file" name="fichero" accept=".csv,.xlsx,.txt" required>
    </div>
    <button class="boton secundario" type="submit">Importar</button>
  </form>
  <details>
    <summary>…o pegar los nombres a mano</summary>
    <form method="post" action="/admin/participantes/pegar">
      <label>Un participante por línea: «Nombre» o «Nombre; teléfono; email»</label>
      <textarea name="lineas" rows="6" style="width:100%"
        placeholder="Ana García; 600111222&#10;Luis Pérez"></textarea>
      <div style="margin-top:8px">
        <button class="boton secundario" type="submit">Añadir lista</button>
      </div>
    </form>
  </details>
  <p class="silencio" style="margin-bottom:0">Los nombres que ya existan se omiten:
  puedes re-importar la misma lista sin duplicar.</p>
</div>

<div class="tarjeta">
  <h2>Participantes ({len(lista)})</h2>
  {tabla}
</div>
"""
    return pagina_admin("Participantes", "/admin/participantes", cuerpo,
                        avisos=avisos, sin_password=sin_password)


def render_participante_editar(p: dict, equipos: list[dict], enlace: str,
                               avisos=None, sin_password=False) -> str:
    cuerpo = f"""
<div class="tarjeta" style="max-width:560px">
  <form method="post" action="/admin/participantes/{p['id']}/guardar">
    <label>Nombre *</label><input name="nombre" required value="{e(p['nombre'])}" style="width:100%">
    <label>Teléfono</label><input name="telefono" value="{e(p['telefono'])}" style="width:100%">
    <label>Email</label><input name="email" type="email" value="{e(p['email'])}" style="width:100%">
    <label>Equipo</label>
    <select name="equipo_id" style="width:100%">{_opciones_equipos(equipos, p['equipo_id'])}</select>
    <label>Notas (solo las ve la organización)</label>
    <textarea name="notas" rows="3" style="width:100%">{e(p['notas'])}</textarea>
    <div style="margin-top:12px" class="acciones">
      <button class="boton" type="submit">Guardar</button>
      <a class="boton secundario" href="/admin/participantes">Volver</a>
    </div>
  </form>
</div>

<div class="tarjeta" style="max-width:560px">
  <h2>Su enlace personal</h2>
  <p style="word-break:break-all"><a href="{e(enlace)}" target="_blank" rel="noopener">{e(enlace)}</a></p>
  <p class="silencio">Estado: {_insignia_estado(p)}
  {('· abrió el enlace el ' + e(p['visto_en'])) if p.get('visto_en') else '· aún no lo ha abierto'}</p>
  <div class="acciones">
    <button class="boton secundario mini" type="button" data-c="{e(enlace)}"
            onclick="copiar(this)">Copiar</button>
    <form class="compacta" method="post" action="/admin/participantes/{p['id']}/token"
          onsubmit="return confirm('El enlace actual dejará de funcionar y habrá que enviarle el nuevo. ¿Seguir?')">
      <button class="boton secundario mini" type="submit">♻ Generar enlace nuevo</button>
    </form>
  </div>
</div>

<div class="tarjeta" style="max-width:560px;border-color:#F0B6BA">
  <form class="compacta" method="post" action="/admin/participantes/{p['id']}/borrar"
        onsubmit="return confirm('¿Borrar a {e(p['nombre'])}? Esta acción no se puede deshacer.')">
    <button class="boton secundario" type="submit">🗑 Borrar participante</button>
  </form>
</div>
"""
    return pagina_admin(f"Editar · {p['nombre']}", "/admin/participantes", cuerpo,
                        avisos=avisos, sin_password=sin_password)


def render_equipos(equipos: list[dict], miembros_por_equipo: dict[int, list[dict]],
                   n_sin_equipo: int, avisos=None, sin_password=False) -> str:
    filas = ""
    for eq in equipos:
        nombres = ", ".join(e(m["nombre"]) for m in miembros_por_equipo.get(eq["id"], []))
        filas += f"""
<div class="tarjeta">
  <form class="linea" method="post" action="/admin/equipos/{eq['id']}/guardar">
    <div><label>Nombre</label><input name="nombre" value="{e(eq['nombre'])}" required></div>
    <div><label>Color</label><input name="color" type="color" value="{e(eq.get('color') or '#CC0C18')}" style="height:40px;width:64px;padding:2px"></div>
    <div><label>Emoji</label><input name="emoji" value="{e(eq.get('emoji'))}" size="4" style="width:70px"></div>
    <div style="flex:1;min-width:180px"><label>Lema / descripción (opcional)</label>
      <input name="descripcion" value="{e(eq.get('descripcion'))}" style="width:100%"></div>
    <button class="boton mini" type="submit">Guardar</button>
  </form>
  <form class="compacta" method="post" action="/admin/equipos/{eq['id']}/borrar"
        onsubmit="return confirm('¿Borrar el equipo {e(eq['nombre'])}? Sus miembros quedarán sin equipo y se borrarán sus actividades específicas de la agenda.')">
    <button class="boton secundario mini" type="submit" style="margin-top:8px">🗑 Borrar equipo</button>
  </form>
  <p class="silencio" style="margin:8px 0 0"><strong>{eq['n_miembros']}</strong> miembro(s):
  {nombres or 'ninguno todavía'}</p>
</div>"""

    aviso_sorteo = (f'<p class="silencio">Hay <strong>{n_sin_equipo}</strong> '
                    f'participante(s) sin equipo.</p>' if n_sin_equipo else
                    '<p class="silencio">Todos los participantes tienen equipo.</p>')

    cuerpo = f"""
<div class="tarjeta">
  <h2>Crear equipos</h2>
  <form class="linea" method="post" action="/admin/equipos/nuevo">
    <div style="flex:1;min-width:240px">
      <label>Nombres separados por comas (los colores se asignan solos)</label>
      <input name="nombres" placeholder="Rojo, Azul, Verde, Amarillo" required style="width:100%">
    </div>
    <button class="boton" type="submit">Crear</button>
  </form>
</div>

<div class="tarjeta">
  <h2>🎲 Sorteo de equipos</h2>
  {aviso_sorteo}
  <div class="acciones">
    <form class="compacta" method="post" action="/admin/sorteo">
      <input type="hidden" name="modo" value="pendientes">
      <button class="boton" type="submit">Repartir a los que no tienen equipo</button>
    </form>
    <form class="compacta" method="post" action="/admin/sorteo"
          onsubmit="return confirm('Se borrarán TODAS las asignaciones actuales y se volverá a sortear. ¿Seguir?')">
      <input type="hidden" name="modo" value="todos">
      <button class="boton secundario" type="submit">Resortear a todos</button>
    </form>
  </div>
  <p class="silencio" style="margin-bottom:0">El reparto es aleatorio y equilibrado:
  cada persona entra en el equipo que menos gente tiene. Las asignaciones hechas a
  mano se respetan si usas «Repartir a los que no tienen equipo».</p>
</div>

{filas or '<p class="silencio">Aún no hay equipos.</p>'}
"""
    return pagina_admin("Equipos", "/admin/equipos", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def _formulario_actividad(accion: str, lugares: list[dict], equipos: list[dict],
                          a: dict | None = None, texto_boton: str = "Añadir") -> str:
    a = a or {}
    opciones_lugar = '<option value="">— Sin lugar —</option>'
    for lugar_ in lugares:
        sel = " selected" if a.get("lugar_id") == lugar_["id"] else ""
        opciones_lugar += f'<option value="{lugar_["id"]}"{sel}>{e(lugar_["nombre"])}</option>'
    return f"""
<form class="linea" method="post" action="{accion}">
  <div><label>Hora inicio *</label>
    <input name="hora" type="time" value="{e(a.get('hora'))}" required></div>
  <div><label>Hora fin</label>
    <input name="hora_fin" type="time" value="{e(a.get('hora_fin'))}"></div>
  <div style="flex:1;min-width:180px"><label>Actividad *</label>
    <input name="actividad" value="{e(a.get('actividad'))}" required style="width:100%"
           placeholder="Bienvenida y café"></div>
  <div style="flex:1;min-width:180px"><label>Detalle</label>
    <input name="descripcion" value="{e(a.get('descripcion'))}" style="width:100%"></div>
  <div><label>Lugar</label><select name="lugar_id">{opciones_lugar}</select></div>
  <div><label>¿Para quién?</label>
    <select name="equipo_id">{_opciones_equipos(equipos, a.get('equipo_id'), '👥 Todos')}</select></div>
  <button class="boton" type="submit">{e(texto_boton)}</button>
</form>"""


def render_agenda(items: list[dict], lugares: list[dict], equipos: list[dict],
                  avisos=None, sin_password=False) -> str:
    filas = ""
    for a in items:
        if a.get("equipo_nombre"):
            color = e(a.get("equipo_color") or "#CC0C18")
            para = (f'<span class="insignia" style="background:{color}1A;color:{color}">'
                    f'{e(a.get("equipo_emoji"))} {e(a["equipo_nombre"])}</span>')
        else:
            para = '<span class="insignia pte">👥 Todos</span>'
        horas = e(a["hora"]) + (f" – {e(a['hora_fin'])}" if a.get("hora_fin") else "")
        filas += f"""
<tr>
  <td style="white-space:nowrap"><strong>{horas}</strong></td>
  <td>{e(a['actividad'])}
      {('<div class="silencio">' + e(a['descripcion']) + '</div>') if a.get('descripcion') else ''}</td>
  <td>{e(a.get('lugar_nombre')) or '<span class="silencio">—</span>'}</td>
  <td>{para}</td>
  <td class="acciones">
    <a class="boton secundario mini" href="/admin/agenda/{a['id']}">Editar</a>
    <form class="compacta" method="post" action="/admin/agenda/{a['id']}/borrar"
          onsubmit="return confirm('¿Borrar esta actividad?')">
      <button class="boton secundario mini" type="submit">🗑</button>
    </form>
  </td>
</tr>"""
    tabla = (f'<div class="envoltorio-tabla"><table class="tabla">'
             f'<tr><th>Hora</th><th>Actividad</th><th>Lugar</th><th>Para</th><th></th></tr>'
             f'{filas}</table></div>'
             if filas else
             '<p class="silencio">Aún no hay actividades. Añade la primera arriba: '
             'hora, nombre y, si quieres, lugar y equipo.</p>')
    cuerpo = f"""
<div class="tarjeta">
  <h2>Añadir actividad</h2>
  {_formulario_actividad('/admin/agenda/nueva', lugares, equipos)}
  <p class="silencio" style="margin-bottom:0">«¿Para quién?» → <strong>Todos</strong> es
  lo normal; elige un equipo solo para rotaciones o pruebas específicas de ese
  equipo (cada participante ve lo general + lo de su equipo).</p>
</div>
<div class="tarjeta">
  <h2>Programa del día ({len(items)})</h2>
  {tabla}
</div>
"""
    return pagina_admin("Agenda", "/admin/agenda", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def render_agenda_editar(a: dict, lugares: list[dict], equipos: list[dict],
                         avisos=None, sin_password=False) -> str:
    cuerpo = f"""
<div class="tarjeta">
  {_formulario_actividad(f"/admin/agenda/{a['id']}/guardar", lugares, equipos, a,
                         texto_boton="Guardar")}
  <div style="margin-top:10px"><a class="boton secundario mini" href="/admin/agenda">Volver</a></div>
</div>
"""
    return pagina_admin("Editar actividad", "/admin/agenda", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def _formulario_lugar(accion: str, lugar_: dict | None = None,
                      texto_boton: str = "Añadir") -> str:
    lugar_ = lugar_ or {}
    return f"""
<form class="linea" method="post" action="{accion}">
  <div style="flex:1;min-width:160px"><label>Nombre *</label>
    <input name="nombre" value="{e(lugar_.get('nombre'))}" required style="width:100%"
           placeholder="Restaurante El Llagar"></div>
  <div style="flex:1;min-width:200px"><label>Dirección</label>
    <input name="direccion" value="{e(lugar_.get('direccion'))}" style="width:100%"
           placeholder="C/ Uría 1, Oviedo"></div>
  <div style="flex:1;min-width:200px"><label>Enlace de Google Maps (opcional)</label>
    <input name="maps" value="{e(lugar_.get('maps'))}" style="width:100%"
           placeholder="https://maps.app.goo.gl/..."></div>
  <div style="flex:1;min-width:160px"><label>Notas (parking, cómo entrar…)</label>
    <input name="notas" value="{e(lugar_.get('notas'))}" style="width:100%"></div>
  <button class="boton" type="submit">{e(texto_boton)}</button>
</form>"""


def render_lugares(lugares: list[dict], avisos=None, sin_password=False) -> str:
    filas = ""
    for lugar_ in lugares:
        url = enlace_maps(lugar_)
        enlace = (f'<a href="{e(url)}" target="_blank" rel="noopener">abrir mapa</a>'
                  if url else '<span class="silencio">—</span>')
        filas += f"""
<tr>
  <td><strong>{e(lugar_['nombre'])}</strong></td>
  <td>{e(lugar_['direccion']) or '<span class="silencio">—</span>'}</td>
  <td>{enlace}</td>
  <td class="acciones">
    <a class="boton secundario mini" href="/admin/lugares/{lugar_['id']}">Editar</a>
    <form class="compacta" method="post" action="/admin/lugares/{lugar_['id']}/borrar"
          onsubmit="return confirm('¿Borrar este lugar? Las actividades que lo usen quedarán sin lugar.')">
      <button class="boton secundario mini" type="submit">🗑</button>
    </form>
  </td>
</tr>"""
    tabla = (f'<div class="envoltorio-tabla"><table class="tabla">'
             f'<tr><th>Nombre</th><th>Dirección</th><th>Mapa</th><th></th></tr>'
             f'{filas}</table></div>'
             if filas else
             '<p class="silencio">Aún no hay lugares. Con la dirección basta: el botón '
             '«Cómo llegar» se genera solo (o pega el enlace exacto de Google Maps).</p>')
    cuerpo = f"""
<div class="tarjeta"><h2>Añadir lugar</h2>{_formulario_lugar('/admin/lugares/nuevo')}</div>
<div class="tarjeta"><h2>Lugares ({len(lugares)})</h2>{tabla}</div>
"""
    return pagina_admin("Lugares", "/admin/lugares", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def render_lugar_editar(lugar_: dict, avisos=None, sin_password=False) -> str:
    cuerpo = f"""
<div class="tarjeta">
  {_formulario_lugar(f"/admin/lugares/{lugar_['id']}/guardar", lugar_, "Guardar")}
  <div style="margin-top:10px"><a class="boton secundario mini" href="/admin/lugares">Volver</a></div>
</div>
"""
    return pagina_admin("Editar lugar", "/admin/lugares", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def render_enlaces(filas_datos: list[dict], url_base: str, url_definida: bool,
                   texto_todos: str, avisos=None, sin_password=False) -> str:
    aviso_url = ""
    if not url_definida:
        aviso_url = (f'<div class="aviso">Los enlaces se están generando con la dirección '
                     f'actual del navegador (<code>{e(url_base)}</code>). Si vas a '
                     f'repartirlos, fija la <strong>URL pública</strong> definitiva en '
                     f'<a href="/admin/evento">⚙️ Evento</a> para que no cambien.</div>')
    filas = ""
    for f in filas_datos:
        if f["wa"]:
            wa = (f'<a class="boton secundario mini" href="{e(f["wa"])}" target="_blank" '
                  f'rel="noopener">WhatsApp</a>')
        else:
            wa = '<span class="silencio" title="Sin teléfono">—</span>'
        filas += f"""
<tr>
  <td><strong>{e(f['nombre'])}</strong></td>
  <td style="word-break:break-all"><a href="{e(f['enlace'])}" target="_blank"
      rel="noopener">{e(f['enlace'])}</a></td>
  <td class="acciones">
    <button class="boton secundario mini" type="button" data-c="{e(f['enlace'])}"
            onclick="copiar(this)">Copiar</button>
    {wa}
  </td>
</tr>"""
    tabla = (f'<div class="envoltorio-tabla"><table class="tabla">'
             f'<tr><th>Participante</th><th>Enlace personal</th><th></th></tr>'
             f'{filas}</table></div>'
             if filas else
             '<p class="silencio">Añade participantes primero: cada uno tendrá aquí su '
             'enlace personal.</p>')
    cuerpo = f"""
{aviso_url}
<div class="tarjeta">
  <h2>Enlaces personales ({len(filas_datos)})</h2>
  <p class="silencio">Cada participante debe recibir <strong>su</strong> enlace (es
  personal: al abrirlo queda registrado y puede confirmar asistencia). El botón
  «WhatsApp» abre el chat con el mensaje ya escrito — puedes cambiar la plantilla en
  <a href="/admin/evento">⚙️ Evento</a>.</p>
  <div class="acciones" style="margin-bottom:10px">
    <a class="boton secundario mini" href="/admin/enlaces.csv">⬇️ Descargar CSV
    (para Excel / combinar correspondencia)</a>
  </div>
  {tabla}
  <details>
    <summary>Ver todos los enlaces en texto (para copiar y pegar)</summary>
    <textarea rows="8" style="width:100%" readonly>{e(texto_todos)}</textarea>
  </details>
</div>
"""
    return pagina_admin("Enlaces", "/admin/enlaces", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def render_evento(cfg: dict, avisos=None, sin_password=False) -> str:
    cuerpo = f"""
<div class="tarjeta" style="max-width:640px">
  <form method="post" action="/admin/evento/guardar">
    <label>Nombre del evento</label>
    <input name="nombre" value="{e(cfg.get('nombre'))}" required style="width:100%">
    <div class="linea" style="display:flex;gap:8px;flex-wrap:wrap">
      <div><label>Fecha</label>
        <input name="fecha" type="date" value="{e(cfg.get('fecha'))}" required></div>
      <div><label>Hora de inicio</label>
        <input name="hora" type="time" value="{e(cfg.get('hora'))}"></div>
    </div>
    <label>Mensaje de bienvenida (lo ven los participantes)</label>
    <textarea name="descripcion" rows="3" style="width:100%">{e(cfg.get('descripcion'))}</textarea>
    <label>Contacto de la organización (nombre y teléfono; sale al pie de la página)</label>
    <input name="contacto" value="{e(cfg.get('contacto'))}" style="width:100%"
           placeholder="Borja (600 111 222)">
    <label>URL pública de la app (para generar los enlaces personales)</label>
    <input name="url_base" value="{e(cfg.get('url_base'))}" style="width:100%"
           placeholder="https://evento.neamaster.com o http://IP:8502">
    <label>Plantilla del mensaje de WhatsApp — usa {{nombre}} y {{enlace}}</label>
    <textarea name="msg_whatsapp" rows="4" style="width:100%">{e(cfg.get('msg_whatsapp'))}</textarea>
    <div style="margin-top:12px">
      <button class="boton" type="submit">Guardar</button>
    </div>
  </form>
</div>
"""
    return pagina_admin("Evento", "/admin/evento", cuerpo, avisos=avisos,
                        sin_password=sin_password)
