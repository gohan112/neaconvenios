"""
NeaEvento — páginas HTML.

Todo el HTML de la app se genera aquí: la página del participante (móvil
primero) y el panel de administración. Sin plantillas externas ni JavaScript
de terceros: una sola hoja de estilos y funciones que devuelven HTML.

Regla de oro: TODO dato que venga de la base de datos o de un formulario pasa
por `e()` antes de incrustarse en el HTML.
"""

from __future__ import annotations

import json
import os
import re
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


def nombre_corto(p: dict) -> str:
    """
    Cómo llamar a la persona: su apodo si lo tiene, o su primer nombre.
    Solo para mostrar: la primera letra siempre en mayúscula («pablo» → «Pablo»).
    """
    corto = (p.get("apodo") or "").strip() or (p.get("nombre", "").split() or [""])[0]
    return corto[:1].upper() + corto[1:]


def lineas_historia(cfg: dict, n_equipos: int, n_participantes: int) -> list[str]:
    """La historia que se cuenta antes del sorteo, una frase por línea."""
    texto = cfg.get("historia") or ""
    try:
        texto = texto.format(equipos=n_equipos, participantes=n_participantes)
    except (KeyError, IndexError, ValueError):
        pass
    return [linea.strip() for linea in texto.splitlines() if linea.strip()]


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


def color_texto(fondo: str, grande: bool = False) -> str:
    """
    Blanco o tinta oscura, el que se lea mejor sobre ese color. Los equipos
    eligen su color libremente (un amarillo con letras blancas no se lee).

    `grande=True` para títulos: basta con 3:1 (WCAG para texto grande), así que
    se prefiere el blanco, que es lo que da empaque al color del equipo. Para
    texto pequeño se exige el máximo contraste posible.
    """
    color = (fondo or "").strip()
    if len(color) != 7 or not color.startswith("#"):
        return "#fff"
    try:
        r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    except ValueError:
        return "#fff"

    def lineal(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    luminancia = 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b)
    # Contraste con blanco vs. con la tinta oscura (#23231F, luminancia ≈ 0.016)
    contraste_blanco = 1.05 / (luminancia + 0.05)
    contraste_tinta = (luminancia + 0.05) / 0.066
    if grande:
        return "#fff" if contraste_blanco >= 3.0 else "#23231F"
    return "#fff" if contraste_blanco >= contraste_tinta else "#23231F"


def iniciales(p: dict) -> str:
    """Una o dos letras para el avatar de la persona."""
    corto = nombre_corto(p)
    partes = (p.get("nombre") or corto).split()
    if len(partes) >= 2 and not (p.get("apodo") or "").strip():
        return (partes[0][:1] + partes[1][:1]).upper()
    return corto[:2].upper()


ESTILO = """
/* ---------------------------------------------------------------- 1. Tokens */
:root{
  /* Marca Nea Master + acento «olímpico» dorado */
  --rojo:#CC0C18; --rojo-oscuro:#A50A13; --rojo-suave:#FCE9EA;
  --oro:#E8A013; --oro-claro:#FFD766; --oro-suave:#FDF3DF;
  /* El acento cambia al color del equipo en la página del participante */
  --acento:#CC0C18; --acento-tinta:#fff;
  /* Neutros */
  --tinta:#23231F; --gris:#6B6862; --gris-claro:#8C887F;
  --fondo:#F4F3F0; --papel:#FFFFFF; --borde:#E4E1DC; --borde-fuerte:#D5D1CA;
  /* Semánticos */
  --verde:#17834A; --ok-fondo:#E8F6EE; --ok-borde:#B7E3C9;
  --ambar-fondo:#FFF7E0; --ambar-borde:#EAD48A;
  --error-fondo:#FDECEC; --error-borde:#F3BFC2;
  /* Espaciado y formas */
  --e1:4px; --e2:8px; --e3:12px; --e4:16px; --e5:24px; --e6:32px;
  --r-chico:10px; --r:14px; --r-grande:20px;
  --sombra:0 1px 2px rgba(35,35,31,.06), 0 1px 3px rgba(35,35,31,.04);
  --sombra-media:0 6px 20px -10px rgba(35,35,31,.28);
  --sombra-alta:0 14px 32px -12px rgba(35,35,31,.35);
}

/* ------------------------------------------------------------- 2. Base */
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;color-scheme:light}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",
     Arial,sans-serif;background:var(--fondo);color:var(--tinta);
     line-height:1.55;font-size:16px;
     -webkit-font-smoothing:antialiased;overflow-wrap:break-word}
a{color:var(--rojo);text-underline-offset:2px}
a:hover{color:var(--rojo-oscuro)}
img{max-width:100%}
:focus-visible{outline:3px solid rgba(204,12,24,.45);outline-offset:2px;
               border-radius:6px}

/* ------------------------------------------------------------- 3. Layout */
.contenedor{max-width:660px;margin:0 auto;padding:0 16px calc(48px + env(safe-area-inset-bottom))}
body.admin .contenedor{max-width:1120px}
.cabecera{background:var(--papel);border-bottom:3px solid var(--acento);
          padding:10px 0;box-shadow:var(--sombra)}
.cabecera .contenedor{display:flex;align-items:center;gap:12px;padding-bottom:0;
                      min-height:44px}
.cabecera img{height:30px;display:block;flex:none}
.marca{font-size:19px;font-weight:800;letter-spacing:-.35px;white-space:nowrap}
.marca span{color:var(--rojo)}
.pie{color:var(--gris);font-size:13px;text-align:center;margin-top:var(--e6)}
.pie a{color:var(--gris)}

/* --------------------------------------------------------- 4. Tipografía */
h1{font-size:clamp(22px,5.6vw,28px);line-height:1.2;margin:var(--e4) 0 var(--e1);
   letter-spacing:-.5px;font-weight:800;text-wrap:balance}
h2{font-size:18px;line-height:1.3;margin:0 0 var(--e3);letter-spacing:-.2px;
   font-weight:700;text-wrap:balance}
h3{font-size:15px;margin:0 0 var(--e2);font-weight:700}
p{text-wrap:pretty}
.etiqueta{font-size:11.5px;text-transform:uppercase;letter-spacing:.8px;
          color:var(--gris-claro);font-weight:700;margin-bottom:var(--e1)}
.silencio{color:var(--gris);font-size:14.5px}
.meta{display:flex;flex-wrap:wrap;gap:4px 12px;color:var(--gris);font-size:14.5px;
      align-items:center}
.meta span{white-space:nowrap}

/* --------------------------------------------------------- 5. Componentes */
/* Tarjetas */
.tarjeta{background:var(--papel);border:1px solid var(--borde);border-radius:var(--r);
         padding:var(--e4);margin:var(--e3) 0;box-shadow:var(--sombra)}
.tarjeta.destacada{border-color:var(--acento);box-shadow:var(--sombra-media)}
.tarjeta.plana{box-shadow:none}
.tarjeta > :last-child{margin-bottom:0}

/* Botones */
.boton{display:inline-flex;align-items:center;justify-content:center;gap:6px;
       background:var(--rojo);color:#fff;border:1px solid var(--rojo);
       border-radius:var(--r-chico);padding:11px 18px;font-size:15px;font-weight:700;
       cursor:pointer;text-decoration:none;text-align:center;font-family:inherit;
       min-height:44px;transition:background .15s,transform .1s,box-shadow .15s}
.boton:hover{background:var(--rojo-oscuro);border-color:var(--rojo-oscuro);color:#fff}
.boton:active{transform:translateY(1px)}
.boton.secundario{background:var(--papel);color:var(--tinta);border-color:var(--borde-fuerte)}
.boton.secundario:hover{background:var(--fondo);color:var(--tinta)}
.boton.mini{padding:6px 12px;font-size:13.5px;border-radius:8px;min-height:34px}
.boton.bloque{display:flex;width:100%}
.boton[disabled]{opacity:.5;cursor:not-allowed}

/* Formularios */
input,select,textarea{font:inherit;font-size:16px;border:1px solid var(--borde-fuerte);
                      border-radius:var(--r-chico);padding:9px 11px;
                      background:var(--papel);color:var(--tinta);max-width:100%;
                      min-height:42px}
textarea{min-height:auto;line-height:1.5}
input:hover,select:hover,textarea:hover{border-color:var(--gris-claro)}
input:focus,select:focus,textarea:focus{outline:3px solid rgba(204,12,24,.28);
                                        outline-offset:0;border-color:var(--rojo)}
input[type=color]{padding:3px;min-height:42px;cursor:pointer}
input[type=file]{padding:8px;background:var(--fondo)}
label{font-size:13px;color:var(--gris);display:block;margin:var(--e3) 0 var(--e1);
      font-weight:700;letter-spacing:.1px}
form.linea{display:flex;gap:var(--e2);flex-wrap:wrap;align-items:flex-end;margin:0}
form.linea > div{display:flex;flex-direction:column}
form.linea label{margin-top:0}
form.compacta{display:inline;margin:0}
fieldset{border:0;margin:0;padding:0}

/* Chips e insignias */
.chip{display:inline-flex;align-items:center;gap:6px;background:var(--fondo);
      border:1px solid var(--borde);border-radius:999px;padding:5px 12px;
      margin:3px 3px 0 0;font-size:14.5px;line-height:1.35}
.chip.yo{background:var(--rojo-suave);border-color:var(--rojo);font-weight:700}
.chip.incognita{color:var(--gris-claro);border-style:dashed;font-weight:700;
                letter-spacing:1px;min-width:44px;justify-content:center}
.insignia{display:inline-flex;align-items:center;gap:4px;border-radius:999px;
          padding:2px 9px;font-size:12.5px;font-weight:700;white-space:nowrap}
.insignia.ok{background:var(--ok-fondo);color:var(--verde)}
.insignia.no{background:var(--error-fondo);color:var(--rojo)}
.insignia.pte{background:#F0EEEA;color:var(--gris)}
.punto-color{display:inline-block;width:12px;height:12px;border-radius:50%;
             flex:none;margin-right:7px;vertical-align:-1px;
             box-shadow:0 0 0 1px rgba(0,0,0,.08) inset}
.inicial{display:inline-flex;align-items:center;justify-content:center;
         width:24px;height:24px;border-radius:50%;font-size:12px;font-weight:800;
         color:#fff;flex:none;letter-spacing:0}
.fecha-chip{display:inline-flex;align-items:center;gap:6px;background:var(--rojo-suave);
            color:var(--rojo);border-radius:999px;padding:5px 14px;font-weight:700;
            font-size:14px;margin:var(--e2) 0 0}
.pulso{width:8px;height:8px;border-radius:50%;background:var(--verde);flex:none;
       animation:latido 2s ease-in-out infinite}
@keyframes latido{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.8)}}
.en-directo{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;
            color:var(--gris);font-weight:600}

/* Avisos */
.aviso{border-radius:var(--r-chico);padding:12px 14px;margin:var(--e3) 0;
       font-size:14.5px;background:var(--ambar-fondo);border:1px solid var(--ambar-borde)}
.aviso.ok{background:var(--ok-fondo);border-color:var(--ok-borde)}
.aviso.error{background:var(--error-fondo);border-color:var(--error-borde)}
.aviso :last-child{margin-bottom:0}
/* Aviso de una línea con su «Cambiar» al lado (asistencia ya respondida) */
.linea-aviso{display:flex;gap:6px 12px;align-items:baseline;flex-wrap:wrap;
             padding:9px 13px}
.linea-aviso summary{margin:0;white-space:nowrap}

/* Tablas */
.tabla{width:100%;border-collapse:collapse;font-size:14.5px}
.tabla th{text-align:left;color:var(--gris-claro);font-size:11.5px;
          text-transform:uppercase;letter-spacing:.7px;font-weight:700;
          padding-bottom:var(--e2)}
.tabla th,.tabla td{padding:10px 10px;border-bottom:1px solid var(--borde);
                    vertical-align:middle}
.tabla tr:last-child td{border-bottom:0}
.tabla td:first-child,.tabla th:first-child{padding-left:0}
.tabla td:last-child,.tabla th:last-child{padding-right:0}
.envoltorio-tabla{overflow-x:auto;-webkit-overflow-scrolling:touch}
/* La columna de botones se ciñe a su contenido y no se sale de la tabla */
.tabla td.acciones{width:1%;white-space:nowrap;justify-content:flex-end;
                   flex-wrap:nowrap}
.nowrap{white-space:nowrap}
@media (max-width:620px){.solo-ancho{display:none}}

/* KPIs */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
      gap:var(--e2);margin:var(--e3) 0}
.kpi{background:var(--papel);border:1px solid var(--borde);border-radius:var(--r);
     padding:var(--e3) var(--e4);box-shadow:var(--sombra)}
.kpi .valor{font-size:28px;font-weight:800;line-height:1.1;letter-spacing:-1px;
            font-variant-numeric:tabular-nums}
.kpi .texto{font-size:13px;color:var(--gris);margin-top:2px}
.barra{height:8px;border-radius:999px;background:var(--fondo);overflow:hidden;
       margin-top:var(--e2)}
.barra > span{display:block;height:100%;border-radius:999px;background:var(--acento)}

/* Navegación del panel */
.navadmin{display:flex;gap:6px;margin:var(--e3) 0;overflow-x:auto;padding-bottom:4px;
          scrollbar-width:thin;-webkit-overflow-scrolling:touch;
          /* se difumina por la derecha: se ve que hay más pestañas al deslizar */
          -webkit-mask-image:linear-gradient(90deg,#000 88%,transparent);
          mask-image:linear-gradient(90deg,#000 88%,transparent)}
@media (min-width:1000px){.navadmin{-webkit-mask-image:none;mask-image:none}}
.navadmin a{padding:9px 14px;border-radius:999px;text-decoration:none;
            color:var(--tinta);background:var(--papel);border:1px solid var(--borde);
            font-size:14px;font-weight:700;white-space:nowrap;flex:none}
.navadmin a:hover{border-color:var(--borde-fuerte);background:var(--fondo)}
.navadmin a.activo{background:var(--rojo);border-color:var(--rojo);color:#fff}
.navadmin .salir{margin-left:auto;color:var(--gris)}

/* Pestañas del participante (barra fija arriba) */
/* Barra de secciones tipo app: el emoji cae solo en la primera línea y el
   nombre debajo, así entran las cuatro sin apretarse ni en pantallas de 320px */
.pestanas{display:flex;gap:6px;margin:var(--e4) 0 var(--e2);position:sticky;top:0;
          z-index:20;background:var(--fondo);padding:8px 0;
          box-shadow:0 8px 12px -10px rgba(35,35,31,.35)}
.pestanas button{flex:1 1 0;min-width:0;padding:7px 1px;border-radius:12px;
                 border:1px solid var(--borde);background:var(--papel);font:inherit;
                 font-size:12.5px;font-weight:700;color:var(--tinta);cursor:pointer;
                 min-height:52px;line-height:1.25;transition:background .15s,color .15s;
                 /* el texto va centrado, quepa en una línea o en dos, y el nombre
                    nunca se parte por la mitad («Progra/ma») */
                 display:flex;align-items:center;justify-content:center;
                 text-align:center;overflow-wrap:normal;word-break:normal}
.pestanas button:hover{background:var(--fondo)}
.pestanas button.activa{background:var(--acento);border-color:var(--acento);
                        color:var(--acento-tinta);box-shadow:var(--sombra-media)}
.panel-pestana{display:none;animation:entra .25s ease}
.panel-pestana.activa{display:block}
@keyframes entra{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

/* Agenda */
.agenda-item{display:flex;gap:var(--e3);padding:12px 0;
             border-bottom:1px dashed var(--borde)}
.agenda-item:last-child{border-bottom:0}
.agenda-item.ahora{background:var(--oro-suave);border-radius:var(--r-chico);
                   padding:12px;margin:0 -12px;border-bottom:0}
.agenda-hora{min-width:58px;font-weight:800;color:var(--acento);
             font-variant-numeric:tabular-nums;font-size:15px;line-height:1.4}
.agenda-texto{flex:1;min-width:0}
.agenda-lugar{font-size:14px;color:var(--gris);margin-top:2px}
.agenda-lugar a{color:var(--gris);text-decoration:underline}
.agenda-lugar a:hover{color:var(--rojo)}

/* Equipo */
.equipo-cabecera{margin:calc(var(--e4) * -1) calc(var(--e4) * -1) var(--e4);
                 padding:var(--e4);border-radius:var(--r) var(--r) 0 0;
                 background:var(--acento);color:var(--acento-tinta)}
.equipo-nombre{font-size:26px;font-weight:800;letter-spacing:-.5px;line-height:1.1;
               display:flex;align-items:center;gap:10px}
.equipo-cabecera .etiqueta{color:inherit;opacity:.8}

/* Podio de la clasificación */
.podio{display:flex;flex-direction:column;gap:var(--e2);margin:var(--e3) 0}
.podio-fila{display:flex;align-items:center;gap:var(--e3)}
.podio-puesto{font-size:20px;width:28px;text-align:center;flex:none}
.podio-cuerpo{flex:1;min-width:0}
.podio-nombre{display:flex;justify-content:space-between;gap:var(--e2);
              font-weight:700;font-size:15px;align-items:baseline}
.podio-total{font-variant-numeric:tabular-nums;font-weight:800}
.podio-barra{height:10px;border-radius:999px;background:var(--fondo);
             overflow:hidden;margin-top:5px}
.podio-barra > span{display:block;height:100%;border-radius:999px;
                    transition:width .6s ease}
.lista-datos > div{padding:5px 0;border-bottom:1px dashed var(--borde);font-size:14.5px}
.lista-datos > div:last-child{border-bottom:0}
/* Rejilla para meter los tiempos de los karts: una columna por equipo */
.rejilla-tiempos{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
                 gap:var(--e4) var(--e5)}
.fila-tiempo{display:flex;align-items:center;justify-content:space-between;gap:var(--e2);
             padding:4px 0}
.fila-tiempo label{margin:0;font-weight:600;color:var(--tinta);font-size:14.5px}
.fila-tiempo input{width:110px;flex:none;font-variant-numeric:tabular-nums}
.fila-tiempo.sub-final{padding:0 0 6px var(--e2);margin-left:3px;
                       border-left:2px solid var(--borde)}
.fila-tiempo.sub-final label{font-size:13.5px;font-weight:500;color:var(--gris);
                             display:inline-flex;align-items:center;gap:7px;
                             cursor:pointer}
.fila-tiempo.sub-final input{width:96px}
.campos-vuelta{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
               gap:var(--e2) var(--e3);margin-top:var(--e3)}
.campos-vuelta label{margin-top:0}
.campos-vuelta input{width:100%;font-variant-numeric:tabular-nums}
input[type=checkbox]{width:18px;height:18px;min-height:0;flex:none;padding:0;
                     accent-color:var(--rojo);cursor:pointer}

/* Utilidades y varios */
.acciones{display:flex;gap:var(--e2);flex-wrap:wrap;align-items:center}
details summary{cursor:pointer;color:var(--gris);font-size:14px;margin-top:var(--e2);
                font-weight:600}
details summary:hover{color:var(--rojo)}
.selector-personas{display:flex;flex-wrap:wrap;gap:6px;margin:var(--e2) 0}
.selector-personas label{display:inline-flex;align-items:center;gap:7px;
                         background:var(--fondo);border:1px solid var(--borde);
                         border-radius:999px;padding:7px 13px;font-size:14px;
                         cursor:pointer;margin:0;color:var(--tinta);font-weight:500;
                         min-height:38px}
.selector-personas label:hover{border-color:var(--borde-fuerte)}
.selector-personas label:has(input:checked){background:var(--rojo-suave);
                                            border-color:var(--rojo);font-weight:700}
.selector-personas input{margin:0;accent-color:var(--rojo);min-height:auto;
                         width:16px;height:16px}
.regla-juntos{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
              padding:10px 0;border-bottom:1px dashed var(--borde)}
.regla-juntos:last-of-type{border-bottom:0}
.paso{display:flex;align-items:flex-start;gap:10px;padding:9px 0;
      border-bottom:1px dashed var(--borde);font-size:14.5px}
.paso:last-child{border-bottom:0}
.paso-icono{flex:none;font-size:15px;width:22px;text-align:center}
.paso.hecho{color:var(--gris)}
/* En pantalla ancha, los preparativos en dos columnas: se ven de una ojeada */
@media (min-width:800px){
  .preparativos{display:grid;grid-template-columns:1fr 1fr;column-gap:var(--e5)}
  .preparativos .paso:nth-last-child(2){border-bottom:0}
}

/* ------------------------------------------------- 6. Sorteo (espectáculo) */
.historia{margin:var(--e3) 0 0}
.historia p{opacity:0;animation:aparece .7s ease forwards;margin:9px 0;
            font-size:17px;line-height:1.45}
.aparece-tarde{opacity:0;animation:aparece .7s ease forwards}
@keyframes aparece{to{opacity:1}}
.sorteo-escena{text-align:center;padding:var(--e2) 0 var(--e1)}
.caja-sorteo{width:min(200px,58vw);aspect-ratio:1;margin:var(--e5) auto var(--e3);
             border-radius:28px;background:linear-gradient(150deg,var(--oro-claro),var(--oro));
             padding:12px;box-shadow:var(--sombra-alta);transition:transform .35s}
.caja-sorteo .baldosa{width:100%;height:100%;border-radius:18px;background:var(--papel);
                      display:flex;align-items:center;justify-content:center;
                      font-size:min(88px,26vw);font-weight:800;color:var(--oro);
                      transition:background .06s;user-select:none;line-height:1}
.caja-sorteo.girando{animation:tiembla .22s infinite}
@keyframes tiembla{0%{transform:rotate(-1.5deg) scale(1.02)}
                   50%{transform:rotate(1.5deg) scale(1.02)}
                   100%{transform:rotate(-1.5deg) scale(1.02)}}
.caja-sorteo.ganador{transform:scale(1.12)}
.sorteo-equipo{font-size:28px;font-weight:800;min-height:40px;margin:var(--e2) 0;
               letter-spacing:-.5px}
.sorteo-resultado{display:none}
.boton.gordo{font-size:18px;padding:15px 28px;border-radius:var(--r);min-height:52px;
             animation:late 1.6s ease-out infinite}
.boton.gordo.aparece-tarde{opacity:0;
             animation:aparece .7s ease forwards, late 1.6s ease-out infinite}
@keyframes late{0%{box-shadow:0 0 0 0 rgba(204,12,24,.45)}
                70%{box-shadow:0 0 0 16px rgba(204,12,24,0)}
                100%{box-shadow:0 0 0 0 rgba(204,12,24,0)}}
.celebracion{text-align:center;background:linear-gradient(180deg,
             rgba(232,160,19,.14),transparent 70%)}
.celebracion h2{margin:0 0 var(--e2);font-size:26px}
.celebracion .medallon{font-size:52px;line-height:1;margin-bottom:6px}
.celebracion p{margin:0 0 var(--e2)}
.celebracion p:last-child{margin-bottom:0}
.confeti{position:fixed;top:42%;left:50%;width:12px;height:12px;border-radius:3px;
         pointer-events:none;z-index:50;animation:vuela 1.2s ease-out forwards}
@keyframes vuela{to{transform:translate(var(--dx),var(--dy)) rotate(720deg);opacity:0}}

/* ------------------------------------------------------- 7. Adaptaciones */
@media (max-width:420px){
  .contenedor{padding-left:13px;padding-right:13px}
  .tarjeta{padding:var(--e3)}
  .equipo-cabecera{margin:calc(var(--e3) * -1) calc(var(--e3) * -1) var(--e3);
                   padding:var(--e3)}
  .pestanas button{font-size:11.5px}
}
@media (max-width:360px){
  .pestanas button{font-size:10.5px;letter-spacing:-.2px}
  .agenda-hora{min-width:52px}
  .kpi{padding:var(--e3)}
  .kpi .valor{font-size:24px}
}
@media (min-width:900px){
  .navadmin{position:sticky;top:0;z-index:10;background:var(--fondo);
            padding-top:var(--e3)}
}
/* Quien pida menos movimiento ve la app quieta (el sorteo sigue funcionando) */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms !important;
                       animation-iteration-count:1 !important;
                       transition-duration:.01ms !important;
                       scroll-behavior:auto !important}
  .historia p,.aparece-tarde{opacity:1}
}
@media print{
  .navadmin,.pestanas,.boton{display:none}
  .tarjeta{break-inside:avoid;box-shadow:none}
}
"""

# Animación del sorteo: la caja va pasando por los equipos cada vez más despacio
# y cae SIEMPRE en el equipo real del participante (índice FINAL, ya asignado).
# Espera las constantes EQUIPOS (lista), FINAL (índice) y RUTA_REVELADO (POST).
GUION_SORTEO = """
(function(){
  var boton = document.getElementById('boton-sorteo');
  if (!boton) return;
  var caja = document.getElementById('caja-sorteo');
  var baldosa = document.getElementById('baldosa');
  var nombreEq = document.getElementById('sorteo-equipo');
  var resultado = document.getElementById('sorteo-resultado');
  var intro = document.getElementById('sorteo-intro');

  function pinta(i){
    var eq = EQUIPOS[i];
    baldosa.style.background = eq.color;
    baldosa.style.color = '#fff';
    baldosa.textContent = eq.emoji || (eq.nombre || '?').charAt(0).toUpperCase();
    nombreEq.textContent = eq.nombre;
    nombreEq.style.color = eq.color;
  }
  function confeti(color){
    for (var i = 0; i < 30; i++){
      var s = document.createElement('span');
      s.className = 'confeti';
      s.style.background = (i % 3 === 0) ? '#E8A013' : color;
      s.style.setProperty('--dx', (Math.random() * 340 - 170) + 'px');
      s.style.setProperty('--dy', (Math.random() * -320 - 60) + 'px');
      document.body.appendChild(s);
      (function(el){ setTimeout(function(){ el.remove(); }, 1300); })(s);
    }
  }
  function acaba(){
    caja.classList.remove('girando');
    caja.classList.add('ganador');
    try { if (navigator.vibrate) navigator.vibrate([90, 40, 140]); } catch (e) {}
    confeti(EQUIPOS[FINAL].color);
    resultado.style.display = 'block';
    // el .catch hace falta: si falla la red, un try/catch no atrapa la promesa
    try { fetch(RUTA_REVELADO, {method: 'POST', keepalive: true})
            .catch(function(){}); } catch (e) {}
  }
  boton.addEventListener('click', function(){
    boton.style.display = 'none';
    if (intro) intro.style.display = 'none';
    // Al empezar a girar hay que soltar la animación de aparición: la clase
    // «girando» sustituye la propiedad animation, y sin esto la caja se
    // quedaría con la opacidad 0 de partida (invisible justo en lo bueno).
    caja.classList.remove('aparece-tarde');
    caja.style.opacity = '1';
    caja.style.animationDelay = '0s';
    caja.classList.add('girando');
    var n = EQUIPOS.length;
    var total = 4 * n + FINAL + 1;   // acaba exactamente en FINAL
    var i = -1, paso = 0, retardo = 70;
    function tic(){
      paso++; i = (i + 1) % n; pinta(i);
      if (paso >= total){ acaba(); return; }
      retardo *= (paso > total - n) ? 1.35 : 1.05;  // última vuelta, frenazo
      setTimeout(tic, retardo);
    }
    tic();
  });
})();
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


def base(titulo: str, cuerpo: str, *, admin: bool = False, avisos=None,
         acento: str | None = None) -> str:
    """
    Envoltorio común de todas las páginas. `acento` tiñe la interfaz con el
    color del equipo del participante (línea de la cabecera, pestañas, horas…).
    """
    favicon = '<link rel="icon" href="/assets/neamaster_icono.png">' if HAY_ICONO else ""
    logo = ('<img src="/assets/neamaster_horizontal.png" alt="Nea Master">'
            if HAY_LOGO else "")
    html_avisos = ""
    for categoria, texto in (avisos or []):
        clase = categoria if categoria in ("ok", "error") else ""
        icono = {"ok": "✅", "error": "⛔"}.get(categoria, "ℹ️")
        html_avisos += (f'<div class="aviso {clase}" role="status">{icono} '
                        f'{e(texto)}</div>')
    tema = "#CC0C18"
    estilo_acento = ""
    if acento and re.fullmatch(r"#[0-9A-Fa-f]{6}", acento):
        tema = acento
        estilo_acento = (f'<style>:root{{--acento:{acento};'
                         f'--acento-tinta:{color_texto(acento, grande=True)}}}</style>')
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{e(tema)}">
<meta name="robots" content="noindex">
<meta name="description" content="{e(titulo)} — Nea Master">
<title>{e(titulo)}</title>
{favicon}
<style>{ESTILO}</style>{estilo_acento}
<script>{GUION}</script>
</head>
<body class="{'admin' if admin else ''}">
<header class="cabecera"><div class="contenedor">
  {logo}
  <div class="marca">Nea<span>Evento</span></div>
</div></header>
<main class="contenedor">
{html_avisos}
{cuerpo}
</main>
</body>
</html>"""


# ================================================================== público

def render_portada(cfg: dict, referencia: date) -> str:
    contador = cuenta_atras(cfg.get("fecha", ""), referencia)
    chip = f'<span class="fecha-chip">{e(contador)}</span>' if contador else ""
    cuerpo = f"""
<div style="text-align:center;padding:var(--e5) 0 var(--e2)">
  <div style="font-size:52px;line-height:1">🏅</div>
  <h1 style="margin:var(--e2) 0 var(--e1)">{e(cfg.get('nombre'))}</h1>
  <div class="meta" style="justify-content:center">
    <span>📅 {e(fecha_bonita(cfg.get('fecha', '')))}</span>
    <span>🕘 {e(cfg.get('hora'))} h</span>
  </div>
  <div>{chip}</div>
</div>
<div class="tarjeta">
  <p style="margin-top:0">{e(cfg.get('descripcion'))}</p>
  <p class="silencio">Cada participante tiene un <strong>enlace personal</strong>
  donde ve su equipo, el programa del día y los lugares. Si no lo has recibido,
  pide el tuyo a la organización.</p>
  <form class="linea" method="post" action="/ir">
    <div style="flex:1;min-width:160px">
      <label for="codigo">¿Tienes ya tu código?</label>
      <input id="codigo" name="codigo" placeholder="Código del enlace" required
             autocomplete="off" style="width:100%">
    </div>
    <button class="boton" type="submit">Entrar</button>
  </form>
</div>
<div class="pie">Nea Master · <a href="/admin">organización</a></div>
"""
    return base(cfg.get("nombre", "Evento"), cuerpo)


def render_no_encontrado(cfg: dict) -> str:
    contacto = e(cfg.get("contacto")) or "la organización"
    cuerpo = f"""
<div class="tarjeta" style="margin-top:var(--e5);text-align:center">
  <div style="font-size:44px;line-height:1">😕</div>
  <h2>Enlace no válido</h2>
  <p>Este enlace no corresponde a ningún participante. Puede que esté incompleto
  (al copiarlo se cortó) o que la organización lo haya renovado.</p>
  <p class="silencio">Pide tu enlace de nuevo a {contacto}.</p>
  <a class="boton secundario" href="/">Ir a la portada</a>
</div>
"""
    return base("Enlace no válido", cuerpo)


def render_sorteo(cfg: dict, p: dict, equipos: list[dict], indice_final: int,
                  historia: list[str], avisos=None) -> str:
    """
    Pantalla del sorteo simulado (estilo caja de ítems de Mario): primero se
    cuenta la historia del evento frase a frase, y después los colores de los
    equipos van pasando por la caja cada vez más despacio hasta caer en el
    equipo REAL del participante, que ya está asignado. Se enseña una sola vez.
    """
    datos_equipos = [
        {"nombre": eq["nombre"], "color": eq.get("color") or "#CC0C18",
         "emoji": eq.get("emoji") or ""}
        for eq in equipos
    ]
    # json.dumps con ensure_ascii y sin '</' peligrosos para incrustar en <script>
    json_equipos = json.dumps(datos_equipos, ensure_ascii=True).replace("</", "<\\/")
    equipo_final = equipos[indice_final]
    nombre_pila = nombre_corto(p)
    ruta_revelado = f"/p/{p['token']}/revelado"

    # La historia aparece frase a frase; la caja y el botón, al terminar
    historia_html = ""
    for i, linea in enumerate(historia):
        historia_html += (f'<p style="animation-delay:{0.3 + i * 0.85:.2f}s">'
                          f'{e(linea)}</p>')
    retardo = 0.4 + len(historia) * 0.85
    cuerpo = f"""
<div class="sorteo-escena">
  <h1>¡Hola, {e(nombre_pila)}! 👋</h1>
  <div class="silencio"><strong>{e(cfg.get('nombre'))}</strong> ·
  📅 {e(fecha_bonita(cfg.get('fecha', '')))}</div>
  <div class="historia" id="sorteo-intro">{historia_html}</div>

  <div class="caja-sorteo aparece-tarde" id="caja-sorteo"
       style="animation-delay:{retardo:.2f}s">
    <div class="baldosa" id="baldosa">?</div>
  </div>
  <div class="sorteo-equipo" id="sorteo-equipo"></div>

  <button class="boton gordo aparece-tarde" id="boton-sorteo" type="button"
          style="animation-delay:{retardo + 0.35:.2f}s">🎲 ¡Dale al sorteo!</button>
  <div class="silencio aparece-tarde" style="animation-delay:{retardo + 0.5:.2f}s">
  Sorteo aleatorio · en directo</div>

  <div class="sorteo-resultado" id="sorteo-resultado">
    <h2 style="font-size:22px">¡Estás en el equipo
    {e(equipo_final.get('emoji'))} {e(equipo_final['nombre'])}!</h2>
    <a class="boton" href="/p/{e(p['token'])}">Ver mi equipo y el programa →</a>
  </div>

  <noscript>
    <div class="aviso">Tu navegador no puede reproducir la animación del sorteo.</div>
    <form method="post" action="{e(ruta_revelado)}">
      <button class="boton" type="submit">Ver mi equipo</button>
    </form>
  </noscript>
</div>
<div class="pie">Nea Master · NeaEvento</div>
<script>
var EQUIPOS = {json_equipos};
var FINAL = {int(indice_final)};
var RUTA_REVELADO = {json.dumps(ruta_revelado)};
{GUION_SORTEO}
</script>
"""
    return base(cfg.get("nombre", "Evento"), cuerpo, avisos=avisos)


def _bloque_asistencia(p: dict, cfg: dict) -> str:
    """
    Pendiente de responder → tarjeta destacada (es LA acción de la página).
    Ya respondido → una línea discreta: la página pasa a ser la guía del día.
    """
    boton_si = ('<button class="boton" type="submit" name="valor" value="si">'
                '✅ ¡Sí, voy!</button>')
    boton_no = ('<button class="boton secundario" type="submit" name="valor" value="no">'
                'No puedo ir</button>')
    formulario = (f'<form class="linea" method="post" action="/p/{e(p["token"])}/asistencia">'
                  f'{boton_si} {boton_no}</form>')
    if p["confirmado"] == 1:
        return f"""
<div class="aviso ok linea-aviso">
  <span>✅ <strong>Confirmado.</strong> ¡Te esperamos!</span>
  <details><summary>Cambiar</summary>{formulario}</details>
</div>"""
    if p["confirmado"] == -1:
        return f"""
<div class="aviso linea-aviso">
  <span>😔 Has dicho que <strong>no puedes venir</strong>.</span>
  <details><summary>Cambiar</summary>{formulario}</details>
</div>"""
    return f"""
<div class="tarjeta destacada">
  <h2>¿Contamos contigo el {e(fecha_bonita(cfg.get('fecha', '')))}?</h2>
  {formulario}
</div>"""


def _texto_contador(n_dentro: int, n_pendientes: int) -> str:
    if n_pendientes > 0:
        return (f"Ya estáis {n_dentro} de {n_dentro + n_pendientes} — el equipo se "
                f"completa en directo según van pasando por el sorteo.")
    return f"¡Equipo completo! Ya estáis los {n_dentro}."


def _chip_miembro(m: dict, p: dict, color: str, capitan_id) -> str:
    """Un compañero de equipo: avatar con sus iniciales, apodo y corona si manda."""
    corona = "👑 " if m["id"] == capitan_id else ""
    avatar = (f'<span class="inicial" style="background:{e(color)};'
              f'color:{color_texto(color)}" aria-hidden="true">{e(iniciales(m))}</span>')
    if m["id"] == p["id"]:
        return f'<span class="chip yo">{avatar}{corona}{e(nombre_corto(m))} (tú)</span>'
    return (f'<span class="chip" title="{e(m["nombre"])}">{avatar}{corona}'
            f'{e(nombre_corto(m))}</span>')


def _bloque_equipo(p: dict, equipo: dict | None, companeros: list[dict]) -> str:
    if not equipo:
        return """
<div class="tarjeta">
  <div class="etiqueta">Tu equipo</div>
  <p style="margin:4px 0;font-size:17px">🎲 Todavía no tienes equipo asignado.</p>
  <p class="silencio" style="margin:0">Cuando se haga el reparto lo verás aquí
  mismo: vuelve a abrir este enlace más adelante.</p>
</div>"""
    color = equipo.get("color") or "#CC0C18"
    emoji = e(equipo.get("emoji"))
    # Solo se muestran los compañeros que YA pasaron por el sorteo; el resto
    # son incógnitas que se van desvelando en directo (la página se refresca sola).
    dentro = [m for m in companeros if m.get("revelado_en")]
    pendientes = len(companeros) - len(dentro)
    total = len(companeros) or 1
    chips = "".join(_chip_miembro(m, p, color, equipo.get("capitan_id")) for m in dentro)
    chips += ('<span class="chip incognita" title="Aún no ha pasado por el sorteo">?'
              '</span>') * pendientes
    descripcion = (f'<p style="margin:0;opacity:.9">{e(equipo.get("descripcion"))}</p>'
                   if equipo.get("descripcion") else "")
    return f"""
<div class="tarjeta">
  <div class="equipo-cabecera">
    <div class="etiqueta">Tu equipo</div>
    <div class="equipo-nombre">{emoji} {e(equipo['nombre'])}</div>
    {descripcion}
  </div>
  <div class="etiqueta">El equipo
    <span class="en-directo" style="float:right;text-transform:none;letter-spacing:0">
    <span class="pulso"></span> en directo</span>
  </div>
  <div id="chips-equipo">{chips}</div>
  <div class="barra"><span style="width:{round(len(dentro) / total * 100)}%;
       background:{e(color)}"></span></div>
  <p class="silencio" id="contador-equipo" style="margin:8px 0 0" aria-live="polite">
  {e(_texto_contador(len(dentro), pendientes))}</p>
</div>"""


def _minutos(hhmm: str) -> int | None:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", hhmm or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _item_agenda(a: dict, mostrar_equipo: bool = True, estado: str = "") -> str:
    horas = e(a["hora"]) + (f"<br>– {e(a['hora_fin'])}" if a.get("hora_fin") else "")
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
    if estado == "ahora":
        insignia = ('<span class="insignia" style="background:var(--oro);color:#fff">'
                    '● AHORA</span> ') + insignia
    elif estado == "siguiente":
        insignia = '<span class="insignia pte">SIGUIENTE</span> ' + insignia
    descripcion = (f'<div class="silencio">{e(a["descripcion"])}</div>'
                   if a.get("descripcion") else "")
    return f"""
<div class="agenda-item{' ahora' if estado == 'ahora' else ''}">
  <div class="agenda-hora">{horas}</div>
  <div class="agenda-texto">{insignia}<strong>{e(a['actividad'])}</strong>
  {descripcion}{lugar}</div>
</div>"""


def _estados_agenda(agenda: list[dict], hora_actual: str | None) -> dict[int, str]:
    """El día del evento marca qué actividad está EN CURSO y cuál es la siguiente."""
    ahora = _minutos(hora_actual or "")
    if ahora is None:
        return {}
    estados: dict[int, str] = {}
    en_curso = None
    for i, a in enumerate(agenda):
        inicio = _minutos(a.get("hora") or "")
        if inicio is None or inicio > ahora:
            continue
        fin = _minutos(a.get("hora_fin") or "")
        siguiente_inicio = next(
            (_minutos(b.get("hora") or "") for b in agenda[i + 1:]
             if _minutos(b.get("hora") or "") is not None), None)
        limite = fin or siguiente_inicio or (inicio + 90)
        if ahora < limite:
            en_curso = i
    if en_curso is not None:
        estados[en_curso] = "ahora"
    for i, a in enumerate(agenda):
        inicio = _minutos(a.get("hora") or "")
        if inicio is not None and inicio > ahora:
            estados.setdefault(i, "siguiente")
            break
    return estados


def _bloque_agenda(agenda: list[dict], hora_actual: str | None = None) -> str:
    if not agenda:
        contenido = ('<p class="silencio" style="margin:0">El programa del día se '
                     'publicará aquí. Vuelve a mirar más adelante.</p>')
    else:
        estados = _estados_agenda(agenda, hora_actual)
        contenido = "".join(_item_agenda(a, estado=estados.get(i, ""))
                            for i, a in enumerate(agenda))
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
<div class="agenda-item" style="display:block">
  <strong style="font-size:16px">📍 {e(lugar_['nombre'])}</strong>
  {direccion}{notas}
  <div style="margin-top:8px">{boton}</div>
</div>"""
    return f'<div class="tarjeta"><h2>📍 Lugares</h2>{tarjetas}</div>'


GUION_PARTICIPANTE = """
// --- Pestañas: el nombre va en la dirección (#programa), así que al volver de
// un formulario o al recargar se sigue viendo la misma pestaña.
function mostrarPestana(nombre){
  var panel = document.getElementById('panel-' + nombre);
  if (!panel) return false;
  document.querySelectorAll('.panel-pestana').forEach(function(x){
    x.classList.remove('activa'); });
  document.querySelectorAll('.pestanas button').forEach(function(b){
    var suya = b.getAttribute('data-p') === nombre;
    b.classList.toggle('activa', suya);
    b.setAttribute('aria-selected', suya ? 'true' : 'false');
  });
  panel.classList.add('activa');
  return true;
}
function abrirPestana(nombre, btn){
  if (mostrarPestana(nombre)){
    try { history.replaceState(null, '', '#' + nombre); } catch (e) {}
  }
}
(function(){
  var inicial = (location.hash || '').replace('#', '');
  if (inicial) mostrarPestana(inicial);
  window.addEventListener('hashchange', function(){
    mostrarPestana((location.hash || '').replace('#', ''));
  });
  // Con teclado, las flechas mueven entre secciones (lo esperable en pestañas)
  var botones = [].slice.call(document.querySelectorAll('.pestanas button'));
  botones.forEach(function(b, i){
    b.addEventListener('keydown', function(ev){
      var salto = ev.key === 'ArrowRight' ? 1 : (ev.key === 'ArrowLeft' ? -1 : 0);
      if (!salto) return;
      ev.preventDefault();
      var otro = botones[(i + salto + botones.length) % botones.length];
      otro.focus();
      abrirPestana(otro.getAttribute('data-p'), otro);
    });
  });
})();

// --- El equipo se completa en directo según pasan por el sorteo
(function(){
  var cont = document.getElementById('chips-equipo');
  if (!cont || !window.fetch || !window.RUTA_EQUIPO) return;
  function pinta(d){
    cont.textContent = '';
    d.dentro.forEach(function(m){
      var s = document.createElement('span');
      s.className = 'chip' + (m.yo ? ' yo' : '');
      if (m.ini){
        var av = document.createElement('span');
        av.className = 'inicial';
        av.style.background = d.color; av.style.color = d.tinta;
        av.setAttribute('aria-hidden', 'true');
        av.textContent = m.ini;
        s.appendChild(av);
      }
      s.appendChild(document.createTextNode(
        (m.cap ? '\\ud83d\\udc51 ' : '') + m.n + (m.yo ? ' (t\\u00fa)' : '')));
      cont.appendChild(s);
    });
    for (var i = 0; i < d.pendientes; i++){
      var q = document.createElement('span');
      q.className = 'chip incognita';
      q.textContent = '?';
      cont.appendChild(q);
    }
    var c = document.getElementById('contador-equipo');
    if (c) c.textContent = d.texto;
    var barra = document.querySelector('#panel-equipo .barra > span');
    if (barra){
      var total = d.dentro.length + d.pendientes;
      barra.style.width = (total ? Math.round(d.dentro.length / total * 100) : 0) + '%';
    }
  }
  setInterval(function(){
    fetch(RUTA_EQUIPO).then(function(r){ return r.json(); }).then(pinta)
      .catch(function(){});
  }, 6000);
})();

// --- Confeti para quien tiene premio (una vez, y solo si no pidió menos
// movimiento: la felicitación se lee igual sin él)
(function(){
  if (!window.COLOR_PREMIO) return;
  try {
    if (window.matchMedia &&
        matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  } catch (e) {}
  for (var i = 0; i < 40; i++){
    var s = document.createElement('span');
    s.className = 'confeti';
    s.style.background = (i % 3 === 0) ? '#E8A013' : COLOR_PREMIO;
    s.style.setProperty('--dx', (Math.random() * 360 - 180) + 'px');
    s.style.setProperty('--dy', (Math.random() * -340 - 60) + 'px');
    document.body.appendChild(s);
    (function(el){ setTimeout(function(){ el.remove(); }, 1400); })(s);
  }
})();

// --- La clasificación también se refresca sola
(function(){
  var zona = document.getElementById('zona-puntos');
  if (!zona || !window.fetch || !window.RUTA_PUNTOS) return;
  setInterval(function(){
    fetch(RUTA_PUNTOS).then(function(r){ return r.text(); }).then(function(html){
      zona.innerHTML = html;
    }).catch(function(){});
  }, 12000);
})();
"""


def _tarjeta_cita(icono: str, titulo: str, hora: str, cuerpo: str) -> str:
    """Tarjeta de «tu cita»: la sala de la escape o la tanda de karts."""
    return f"""
<div class="tarjeta">
  <h2>{icono} {e(titulo)}</h2>
  <div class="agenda-item" style="padding-top:0">
    <div class="agenda-hora">{e(hora)}</div>
    <div class="agenda-texto">{cuerpo}</div>
  </div>
</div>"""


def _form_vueltas(token: str, filas: list[tuple]) -> str:
    """El formulario donde el piloto apunta su vuelta (y la de la final, si la corre).

    Va todo en un único formulario con un solo «Guardar»: si fueran dos, quien
    escribiese los dos tiempos y diera a un botón perdería el otro."""
    campos = ""
    for ident, campo, etiqueta, valor in filas:
        campos += (f'<div><label for="{ident}">{etiqueta}</label>'
                   f'<input id="{ident}" name="{campo}" value="{e(valor or "")}" '
                   f'placeholder="1:02.45" inputmode="decimal" autocomplete="off">'
                   f'</div>')
    return (f'<form method="post" action="/p/{e(token)}/tiempo_karts">'
            f'<div class="campos-vuelta">{campos}</div>'
            f'<button class="boton" type="submit" style="margin-top:var(--e3)">'
            f'Guardar</button></form>')


def render_participante(cfg: dict, p: dict, equipo: dict | None,
                        companeros: list[dict], agenda: list[dict],
                        lugares: list[dict], referencia: date,
                        lugar_escape: dict | None = None,
                        lugar_karts: dict | None = None,
                        clasif: dict | None = None,
                        hora_actual: str | None = None,
                        corre_final: bool = False,
                        ganadores: dict | None = None,
                        avisos=None) -> str:
    contador = cuenta_atras(cfg.get("fecha", ""), referencia)
    chip = f'<span class="fecha-chip">{e(contador)}</span>' if contador else ""
    color_equipo = (equipo.get("color") or "#CC0C18") if equipo else None
    if equipo:
        chip += (f'<span class="fecha-chip" style="background:{e(color_equipo)}1A;'
                 f'color:{e(color_equipo)}">{e(equipo.get("emoji"))} '
                 f'Equipo {e(equipo["nombre"])}</span>')
    contacto = (f'<div class="pie">¿Dudas? Contacta con {e(cfg.get("contacto"))}</div>'
                if cfg.get("contacto") else "")
    nombre_pila = nombre_corto(p)
    panel_lugares = _bloque_lugares(lugares) or (
        '<div class="tarjeta"><p class="silencio" style="margin:0">Los lugares se '
        'publicarán aquí.</p></div>')
    ruta_equipo = f"/p/{p['token']}/equipo.json" if equipo else ""
    ruta_puntos = f"/p/{p['token']}/puntos.html" if clasif else ""
    # El texto de bienvenida es de acogida: cuando ya ha respondido, la página
    # pasa a ser la guía del día y ese párrafo solo estorba.
    bienvenida = (f'<p class="silencio">{e(cfg.get("descripcion"))}</p>'
                  if p["confirmado"] == 0 and cfg.get("descripcion") else "")

    # Pestaña de puntos: si es capitán, el formulario de la hora de salida
    es_capitan = bool(equipo and equipo.get("capitan_id") == p["id"])
    tarjeta_capitan = ""
    if es_capitan:
        tarjeta_capitan = f"""
<div class="tarjeta destacada">
  <h2>👑 Eres el capitán de tu equipo</h2>
  <p class="silencio" style="margin-top:0">Cuando salgáis de vuestra sala de la
  escape room, apunta aquí la hora de salida: con ella se calculan los puntos
  del equipo.</p>
  <form class="linea" method="post" action="/p/{e(p['token'])}/tiempo_escape">
    <div style="flex:1;min-width:120px">
      <label for="hora-salida">Hora de salida</label>
      <input id="hora-salida" name="tiempo" value="{e(equipo.get('tiempo_escape'))}"
             placeholder="10:05" inputmode="numeric" autocomplete="off"></div>
    <button class="boton" type="submit">Guardar</button>
  </form>
</div>"""
    # Cada piloto apunta su propia vuelta. Quien corre la 3ª tanda (los 2 que se
    # quedaron fuera y los 2 que pasan por tiempo) tiene ahí su hueco extra.
    tarjeta_vuelta = ""
    tanda_p = (p.get("tanda") or "").strip()
    ya_puso = bool((p.get("tiempo_karts") or "").strip()
                   or (p.get("tiempo_final") or "").strip())
    if tanda_p in ORDINAL_TANDA or corre_final or ya_puso:
        filas = []
        if tanda_p != "3":          # quien sale en la 3ª tanda solo corre la final
            filas.append(("mi-vuelta", "tiempo",
                          (f"Tu vuelta en la {ORDINAL_TANDA[tanda_p]} tanda"
                           if tanda_p in ORDINAL_TANDA else "Tu mejor vuelta"),
                          p.get("tiempo_karts")))
        if corre_final:
            filas.append(("mi-vuelta-final", "tiempo_final",
                          "Tu vuelta en la final (3ª tanda)", p.get("tiempo_final")))
        campos = _form_vueltas(p["token"], filas)
        nota_final = ('<p class="silencio" style="margin-bottom:0">Corres dos veces: '
                      'para los puntos cuenta tu <strong>mejor</strong> vuelta de las '
                      'dos.</p>' if corre_final and tanda_p != "3" else "")
        tarjeta_vuelta = f"""
<div class="tarjeta">
  <h2>🏎️ Tu vuelta en los karts</h2>
  <p class="silencio" style="margin-top:0">Apúntala tal y como sale en la pantalla del
  circuito: minutos, segundos y centésimas (<code>1:02.45</code>). Si bajaste del
  minuto, con <code>48.12</code> vale. Cuanto más rápido, más puntos para tu equipo.</p>
  {campos}{nota_final}
</div>"""

    # Tutorial: cómo se reparten los puntos y qué tiene que hacer él
    tarjeta_reglas = ""
    if clasif:
        n_pilotos = clasif.get("n_pilotos") or 0
        premios = [x.strip() for x in (cfg.get("puntos_escape") or "").split(",")
                   if x.strip()]
        reparto = " · ".join(f"{i + 1}º: {e(v)} pt" for i, v in enumerate(premios))
        linea_escape = (f'por orden de salida — {reparto}.' if reparto
                        else 'salir antes da más puntos.')
        if n_pilotos >= 3:
            linea_karts = (f'el más rápido se lleva tantos puntos como pilotos apunten '
                           f'su tiempo (apuntando los {n_pilotos}: {n_pilotos} al '
                           f'primero, {n_pilotos - 1} al segundo… y 1 al último).')
        else:
            linea_karts = ('el más rápido se lleva tantos puntos como pilotos; '
                           'el último, 1.')
        if tanda_p == "3":
            deberes = ('<div>🏎️ <strong>Apunta tu vuelta de la final</strong> aquí '
                       'abajo en cuanto te bajes del kart.</div>')
        elif corre_final:
            deberes = ('<div>🏎️ <strong>Apunta tus dos vueltas</strong> aquí abajo: '
                       'la de tu tanda y la de la final. Cuenta la mejor.</div>')
        else:
            deberes = ('<div>🏎️ <strong>Apunta tu vuelta</strong> aquí abajo en '
                       'cuanto te bajes del kart.</div>')
        if es_capitan:
            deberes += ('<div>👑 <strong>Eres el capitán:</strong> al salir de vuestra '
                        'sala, apunta aquí la hora de salida. Esa solo la puedes meter '
                        'tú.</div>')
        else:
            deberes += ('<div>🗝️ La hora de salida de la escape room la apunta '
                        'vuestro capitán (👑): tú, tranquilo.</div>')
        tarjeta_reglas = f"""
<div class="tarjeta">
  <h2>🏆 Cómo se ganan los puntos</h2>
  <div class="lista-datos">
    <div>🗝️ <strong>Escape room</strong> — {linea_escape}
    La hora la apunta el capitán de cada equipo.</div>
    <div>🏎️ <strong>Karts</strong> — cuenta tu mejor vuelta: {linea_karts}
    Todas las posiciones suman, así que apunta tu tiempo aunque no sea el mejor.</div>
    <div>🏅 <strong>El premio</strong> —
    gana el equipo con más puntos: medalla para todos sus miembros.</div>
  </div>
  <div class="etiqueta" style="margin-top:var(--e4)">Lo que te toca a ti</div>
  <div class="lista-datos">{deberes}</div>
</div>"""

    panel_puntos = (f'{tarjeta_reglas}{tarjeta_capitan}{tarjeta_vuelta}'
                    f'<div class="tarjeta"><h2>🏆 Clasificación'
                    f'<span class="en-directo" style="float:right;font-weight:600">'
                    f'<span class="pulso"></span> en directo</span></h2>'
                    f'<div id="zona-puntos">'
                    f'{fragmento_clasificacion(clasif, nota=False)}</div>'
                    f'</div>') if clasif else ""

    # Su sala de la escape room, si está sorteada
    aviso_sala = ""
    if equipo and (equipo.get("sala") or "").strip():
        enlace_sitio = ""
        if lugar_escape:
            url = enlace_maps(lugar_escape)
            sitio = e(lugar_escape["nombre"])
            enlace_sitio = (f'<div class="agenda-lugar">📍 <a href="{e(url)}" '
                            f'target="_blank" rel="noopener">{sitio}</a></div>'
                            if url else f'<div class="agenda-lugar">📍 {sitio}</div>')
        descripcion_sala = (f'<div class="silencio">{e(equipo.get("sala_desc"))}</div>'
                            if equipo.get("sala_desc") else "")
        recuerdo_capitan = ('<div class="silencio">👑 Al salir, apunta la hora en la '
                            'pestaña 🏆 Puntos: da 20, 10 o 5 puntos según el orden.'
                            '</div>' if es_capitan else "")
        aviso_sala = _tarjeta_cita(
            "🗝️", cfg.get("escape_titulo") or "Escape room", cfg.get("escape_hora") or "",
            f'<strong>Vuestra sala: {e(equipo["sala"])}</strong>{descripcion_sala}'
            f'{enlace_sitio}<div class="silencio">Hay que estar allí a las '
            f'{e(cfg.get("escape_hora"))}.</div>{recuerdo_capitan}')

    # Su tanda de karts, si está sorteada
    aviso_tanda = ""
    tanda = (p.get("tanda") or "").strip()
    if tanda in ORDINAL_TANDA:
        extra = ""
        if tanda == "3":
            extra = ('<div class="silencio">A la 3ª tanda, la final, también irán los '
                     '2 mejores tiempos de las tandas anteriores.</div>')
        elif corre_final:
            hora_final = (cfg.get("karts_hora3") or "").strip()
            extra = ('<div class="silencio">🎉 <strong>¡Has pasado a la final!</strong> '
                     'Vuelves a pista en la 3ª tanda'
                     f'{f" a las {e(hora_final)}" if hora_final else ""}.</div>')
        sitio_karts = ""
        if lugar_karts:
            url = enlace_maps(lugar_karts)
            nombre_sitio = e(lugar_karts["nombre"])
            sitio_karts = (f'<div class="agenda-lugar">📍 <a href="{e(url)}" '
                           f'target="_blank" rel="noopener">{nombre_sitio}</a></div>'
                           if url else
                           f'<div class="agenda-lugar">📍 {nombre_sitio}</div>')
        aviso_tanda = _tarjeta_cita(
            "🏎️", cfg.get("karts_nombre") or "Karts",
            cfg.get(f"karts_hora{tanda}") or "",
            f'<strong>Te toca en la {ORDINAL_TANDA[tanda]} tanda</strong>'
            f'{extra}{sitio_karts}<div class="silencio">Al bajarte del kart, apunta '
            f'tu vuelta en la pestaña 🏆 Puntos.</div>')

    # Olimpiada cerrada: felicitación a quien tiene premio y resultado para el resto
    banda_final, confeti_color = "", ""
    if ganadores and ganadores.get("equipos"):
        campeones = ganadores["equipos"]
        nombres = " y ".join(e(x["nombre"]) for x in campeones)
        gane = bool(equipo and any(x["id"] == equipo["id"] for x in campeones))
        rapido = any(x["id"] == p["id"] for x in (ganadores.get("pilotos") or []))
        vuelta = e(ganadores.get("tiempo") or "")
        nombres_rapidos = " y ".join(e(nombre_corto(x))
                                     for x in (ganadores.get("pilotos") or []))
        premio = ('<p><strong>🍰 Pásate a recoger tu premio en los postres.'
                  '</strong></p>')
        if gane:
            confeti_color = color_equipo or "#CC0C18"
            titulo = "¡Campeones!" if len(campeones) == 1 else "¡Campeones (empate arriba)!"
            extra_rapido = (f'<p>🏎️ Y encima, <strong>vuelta rápida del día</strong> '
                            f'con {vuelta}. Doblete.</p>' if rapido else "")
            banda_final = f"""
<div class="tarjeta destacada celebracion">
  <div class="medallon" aria-hidden="true">🥇</div>
  <h2>{titulo}</h2>
  <p>Tu equipo, <strong>{nombres}</strong>, gana la Olimpiada con
  <strong>{ganadores["puntos"]} puntos</strong>.</p>
  {extra_rapido}
  <p><strong>🏅 Tienes medalla.</strong></p>
  {premio}
</div>"""
        elif rapido:
            confeti_color = "#E8A013"
            banda_final = f"""
<div class="tarjeta destacada celebracion">
  <div class="medallon" aria-hidden="true">🏎️</div>
  <h2>¡Vuelta rápida del día!</h2>
  <p>Nadie ha bajado de tu <strong>{vuelta}</strong>. El más rápido de la
  Olimpiada eres tú.</p>
  {premio}
</div>"""
        else:
            nota_rapida = (f' La vuelta rápida ha sido para <strong>{nombres_rapidos}'
                           f'</strong> ({vuelta}).' if nombres_rapidos else "")
            banda_final = f"""
<div class="tarjeta">
  <h2>🏁 Se acabó la Olimpiada</h2>
  <p style="margin-bottom:var(--e2)">Gana <strong>{nombres}</strong> con
  {ganadores["puntos"]} puntos: sus medallas se entregan en los postres.
  {nota_rapida}</p>
  <p class="silencio" style="margin:0">¡Gracias por jugar! Tienes la
  clasificación completa en la pestaña 🏆 Puntos.</p>
</div>"""

    # El día del evento lo que hace falta es saber a dónde ir ahora, así que se
    # abre el Programa; los días previos, el equipo (que es la novedad).
    inicial = "programa" if hora_actual else "equipo"
    pestanas = ""
    for clave, etiqueta in [("equipo", "🎽 Equipo"), ("programa", "🗓️ Programa"),
                            ("puntos", "🏆 Puntos"), ("lugares", "📍 Lugares")]:
        activa = " activa" if clave == inicial else ""
        pestanas += (f'<button type="button" role="tab" data-p="{clave}"'
                     f' aria-controls="panel-{clave}"'
                     f' aria-selected="{"true" if activa else "false"}"'
                     f' class="{activa.strip()}"'
                     f' onclick="abrirPestana(\'{clave}\', this)">{etiqueta}</button>')

    cuerpo = f"""
<div class="etiqueta" style="margin-top:var(--e4)">{e(cfg.get('nombre'))}</div>
<h1 style="margin-top:0">¡Hola, {e(nombre_pila)}! 👋</h1>
<div class="meta">
  <span>📅 {e(fecha_bonita(cfg.get('fecha', '')))}</span>
  <span>🕘 {e(cfg.get('hora'))} h</span>
</div>
<div class="acciones" style="gap:6px">{chip}</div>
{"" if banda_final else bienvenida}
{banda_final}
{_bloque_asistencia(p, cfg) if not banda_final else ""}
<nav class="pestanas" role="tablist" aria-label="Secciones">{pestanas}</nav>
<div class="panel-pestana{' activa' if inicial == 'equipo' else ''}"
     id="panel-equipo" role="tabpanel">
  {_bloque_equipo(p, equipo, companeros)}
</div>
<div class="panel-pestana{' activa' if inicial == 'programa' else ''}"
     id="panel-programa" role="tabpanel">
  {aviso_sala}
  {aviso_tanda}
  {_bloque_agenda(agenda, hora_actual)}
</div>
<div class="panel-pestana" id="panel-puntos" role="tabpanel">
  {panel_puntos}
</div>
<div class="panel-pestana" id="panel-lugares" role="tabpanel">
  {panel_lugares}
</div>
{contacto}
<div class="pie">Nea Master · NeaEvento</div>
<script>
var RUTA_EQUIPO = {json.dumps(ruta_equipo)};
var RUTA_PUNTOS = {json.dumps(ruta_puntos)};
var COLOR_PREMIO = {json.dumps(confeti_color)};
{GUION_PARTICIPANTE}
</script>
"""
    return base(cfg.get("nombre", "Evento"), cuerpo, avisos=avisos,
                acento=color_equipo)


# ================================================================== admin

NAV_ADMIN = [
    ("/admin", "📊 Resumen"),
    ("/admin/participantes", "👥 Participantes"),
    ("/admin/equipos", "🎽 Equipos"),
    ("/admin/agenda", "🗓️ Agenda"),
    ("/admin/puntos", "🏆 Puntos"),
    ("/admin/lugares", "📍 Lugares"),
    ("/admin/enlaces", "🔗 Enlaces"),
    ("/admin/evento", "⚙️ Evento"),
]


def fragmento_clasificacion(clasif: dict, nota: bool = True) -> str:
    """La clasificación (se usa igual en el panel y en el móvil, y se refresca sola).

    `nota=False` quita el recordatorio del premio: en el móvil ya lo cuenta la
    tarjeta «Cómo se ganan los puntos» justo encima."""
    tabla = clasif["equipos"]
    hay_puntos = any(fila["total"] for fila in tabla)
    medallas = ["🥇", "🥈", "🥉"]
    tope = max([fila["total"] for fila in tabla] or [0]) or 1

    # Podio: una barra por equipo con su color y el total bien grande
    podio = ""
    for i, fila in enumerate(tabla):
        eq = fila["equipo"]
        color = e(eq.get("color") or "#CC0C18")
        puesto = medallas[i] if i < len(medallas) and hay_puntos else f"{i + 1}º"
        ancho = round(fila["total"] / tope * 100) if hay_puntos else 0
        podio += f"""
<div class="podio-fila">
  <div class="podio-puesto">{puesto}</div>
  <div class="podio-cuerpo">
    <div class="podio-nombre"><span>{e(eq.get('emoji'))} {e(eq['nombre'])}</span>
      <span class="podio-total">{fila['total']} pt</span></div>
    <div class="podio-barra"><span style="width:{ancho}%;background:{color}"></span></div>
  </div>
</div>"""
    podio = f'<div class="podio">{podio}</div>' if tabla else \
        '<p class="silencio">Aún no hay equipos.</p>'

    # Detalle: de dónde salen esos puntos
    filas = ""
    for i, fila in enumerate(tabla):
        eq = fila["equipo"]
        filas += (f'<tr><td>{_simbolo_equipo(eq.get("color"), eq.get("emoji"))}'
                  f'{e(eq["nombre"])}</td>'
                  f'<td>{fila["escape"]}</td><td>{fila["karts"]}</td>'
                  f'<td><strong>{fila["total"]}</strong></td></tr>')
    tabla_html = (f'<div class="envoltorio-tabla"><table class="tabla">'
                  f'<tr><th>Equipo</th><th>🗝️ Escape</th><th>🏎️ Karts</th>'
                  f'<th>Total</th></tr>{filas}</table></div>' if tabla else "")

    salidas = ""
    for fila in clasif["escape"]:
        if fila["tiempo"]:
            eq = fila["equipo"]
            salidas += (f'<div>{_simbolo_equipo(eq.get("color"), eq.get("emoji"))}'
                        f'{e(eq["nombre"])} — salió a las {e(fila["tiempo"])}'
                        f' → <strong>{fila["puntos"]} pt</strong></div>')
    bloque_salidas = (f'<div class="etiqueta" style="margin-top:var(--e4)">Salidas de '
                      f'la escape room</div><div class="lista-datos">{salidas}</div>'
                      if salidas else "")

    mejores = ""
    for fila in clasif["karts"][:5]:
        p = fila["participante"]
        mejores += (f'<div>{e(nombre_corto(p))} — {e(fila["tiempo"])}'
                    f' → <strong>{fila["puntos"]} pt</strong></div>')
    bloque_karts = ""
    if mejores:
        bloque_karts = (f'<div class="etiqueta" style="margin-top:var(--e4)">Mejores '
                        f'vueltas ({clasif["n_corredores"]} pilotos con tiempo)</div>'
                        f'<div class="lista-datos">{mejores}</div>')

    if hay_puntos:
        detalle = (f'<details><summary>Ver el desglose de los puntos</summary>'
                   f'{tabla_html}</details>')
    else:
        detalle = ('<p class="silencio">La clasificación se irá rellenando durante '
                   'el día: la salida de la escape room y las vueltas de los karts.</p>')
    recordatorio = (f'<p class="silencio" style="margin-top:var(--e3)">🏅 <strong>Gana '
                    f'el equipo con más puntos: medalla para todos sus miembros.'
                    f'</strong> Karts: el más rápido se lleva tantos puntos como '
                    f'pilotos, el último 1 — todas las posiciones cuentan.</p>'
                    if nota else '')
    return f'{podio}{detalle}{recordatorio}{bloque_salidas}{bloque_karts}'


def render_puntos(cfg: dict, clasif: dict, equipos: list[dict],
                  participantes: list[dict], ganadores: dict | None = None,
                  avisos=None, sin_password=False) -> str:
    filas_escape = ""
    for eq in equipos:
        capitan = next((nombre_corto(p) for p in participantes
                        if p["id"] == eq.get("capitan_id")), None)
        nota_capitan = (f'👑 {e(capitan)}' if capitan else "sin capitán aún")
        filas_escape += f"""
<div class="fila-tiempo" style="align-items:flex-start">
  <label for="te{eq['id']}" style="color:var(--tinta);font-size:15px">
    {_simbolo_equipo(eq.get('color'), eq.get('emoji'))}{e(eq['nombre'])}
    <div class="silencio" style="font-size:13px;font-weight:500">{nota_capitan}</div>
  </label>
  <input id="te{eq['id']}" name="tiempo_{eq['id']}" value="{e(eq.get('tiempo_escape'))}"
         placeholder="10:05" size="7" inputmode="numeric" style="width:100px">
</div>"""

    filas_karts = ""
    for eq in equipos + [None]:
        grupo = [p for p in participantes
                 if (p.get("equipo_id") == (eq["id"] if eq else None))]
        if not grupo:
            continue
        titulo = (f'{_simbolo_equipo(eq.get("color"), eq.get("emoji"))}'
                  f'{e(eq["nombre"])}' if eq else "Sin equipo")
        columna = ""
        for p in grupo:
            tanda = (p.get("tanda") or "").strip()
            nombre = e(nombre_corto(p))
            sufijo = f" · {ORDINAL_TANDA[tanda]}" if tanda in ORDINAL_TANDA else ""
            if tanda == "3":     # sale directo en la final: un único hueco
                columna += (f'<div class="fila-tiempo">'
                            f'<label for="f{p["id"]}">{nombre}{sufijo}</label>'
                            f'<input id="f{p["id"]}" name="final_{p["id"]}" '
                            f'value="{e(p.get("tiempo_final"))}" inputmode="decimal" '
                            f'placeholder="48.123" size="8"></div>')
                continue
            columna += (f'<div class="fila-tiempo">'
                        f'<label for="t{p["id"]}">{nombre}{sufijo}</label>'
                        f'<input id="t{p["id"]}" name="tiempo_{p["id"]}" '
                        f'value="{e(p.get("tiempo_karts"))}" inputmode="decimal" '
                        f'placeholder="48.123" size="8"></div>')
            if tanda in ("1", "2"):   # puede pasar a la final por tiempo
                marca = " checked" if p.get("finalista") else ""
                columna += (f'<div class="fila-tiempo sub-final">'
                            f'<label><input type="checkbox" name="finalista" '
                            f'value="{p["id"]}"{marca}> pasa a la final</label>'
                            f'<input name="final_{p["id"]}" inputmode="decimal" '
                            f'value="{e(p.get("tiempo_final"))}" placeholder="3ª tanda" '
                            f'size="8" aria-label="Vuelta de {nombre} en la 3ª tanda">'
                            f'</div>')
        filas_karts += (f'<div><div class="etiqueta">{titulo}</div>{columna}</div>')

    # Cerrar la Olimpiada: publica el resultado y felicita a los ganadores
    cerrada = bool((cfg.get("resultado_final") or "").strip())
    campeones = ", ".join(e(x["nombre"]) for x in (ganadores or {}).get("equipos", []))
    rapidos = ", ".join(e(nombre_corto(x)) for x in (ganadores or {}).get("pilotos", []))
    if campeones:
        quien = (f'Ahora mismo ganaría <strong>{campeones}</strong> con '
                 f'{ganadores["puntos"]} puntos'
                 + (f', y la vuelta rápida sería para <strong>{rapidos}</strong> '
                    f'({e(ganadores["tiempo"])})' if rapidos else "") + '.')
    else:
        quien = "Todavía no hay puntos: en cuanto los haya, aquí verás quién gana."
    if cerrada:
        boton_cierre = (
            '<form class="compacta" method="post" action="/admin/puntos/final">'
            '<input type="hidden" name="valor" value="">'
            '<button class="boton secundario" type="submit">Quitar la felicitación'
            '</button></form>')
        estado = ('<div class="aviso ok" style="margin-top:var(--e3)">✅ Resultado '
                  '<strong>publicado</strong>: cada uno ve al abrir su enlace si tiene '
                  'premio y que lo recoge en los postres.</div>')
    else:
        boton_cierre = (
            '<form class="compacta" method="post" action="/admin/puntos/final" '
            "onsubmit=\"return confirm('Se publicará el resultado y todos verán "
            "quién gana. ¿Seguir?')\">"
            '<input type="hidden" name="valor" value="1">'
            '<button class="boton" type="submit">🏁 Publicar el resultado y felicitar'
            '</button></form>')
        estado = ""
    tarjeta_cierre = f"""
<div class="tarjeta">
  <h2>🏁 Cerrar la Olimpiada</h2>
  <p class="silencio" style="margin-top:0">Cuando estén todos los tiempos, publica el
  resultado: a los del equipo ganador y a la vuelta rápida del día les sale una
  felicitación con el aviso de <strong>recoger el premio en los postres</strong>; al
  resto, el resultado final. {quien}</p>
  {boton_cierre}{estado}
</div>"""

    cuerpo = f"""
<div class="tarjeta">
  <h2>🏆 Clasificación</h2>
  {fragmento_clasificacion(clasif)}
</div>

<div class="tarjeta">
  <h2>🗝️ Escape room — hora de salida de cada sala</h2>
  <p class="silencio" style="margin-top:0">La mete el capitán desde su móvil
  (pestaña 🏆 Puntos de su enlace), o tú aquí. Antes = mejor.</p>
  <form method="post" action="/admin/puntos/escape">
    {filas_escape}
    <div class="acciones" style="margin-top:var(--e3)">
      <label for="puntos-escape" style="margin:0">Puntos (1º, 2º, 3º…):</label>
      <input id="puntos-escape" name="puntos_escape"
             value="{e(cfg.get('puntos_escape'))}" size="10">
      <button class="boton mini" type="submit">Guardar</button>
    </div>
  </form>
</div>

<div class="tarjeta">
  <h2>🏎️ Karts — mejor vuelta de cada piloto</h2>
  <p class="silencio" style="margin-top:0">Cada piloto mete su vuelta desde su
  enlace (pestaña 🏆 Puntos); aquí puedes corregirla o meterla tú. Formatos válidos:
  <code>48.123</code>, <code>48,3</code> o <code>1:02.451</code>.</p>
  <p class="silencio">Marca <strong>«pasa a la final»</strong> en los 2 mejores
  tiempos: se les abre el hueco de la 3ª tanda en su móvil y cuenta su mejor vuelta
  de las dos. El más rápido se lleva tantos puntos como pilotos con tiempo; el
  último, 1.</p>
  <form method="post" action="/admin/puntos/karts">
    <div class="rejilla-tiempos">{filas_karts}</div>
    <div style="margin-top:var(--e4)">
      <button class="boton" type="submit">Guardar todos</button></div>
  </form>
</div>

{tarjeta_cierre}
"""
    return pagina_admin("Puntos", "/admin/puntos", cuerpo, avisos=avisos,
                        sin_password=sin_password)


def _nav(ruta_actual: str, con_salir: bool) -> str:
    enlaces = ""
    for url, texto in NAV_ADMIN:
        activo = " activo" if ruta_actual == url else ""
        aria = ' aria-current="page"' if activo else ""
        enlaces += f'<a class="{activo.strip()}" href="{url}"{aria}>{texto}</a>'
    if con_salir:
        enlaces += '<a class="salir" href="/admin/salir">Salir</a>'
    return f'<nav class="navadmin" aria-label="Secciones del panel">{enlaces}</nav>'


def pagina_admin(titulo: str, ruta: str, cuerpo: str, *, avisos=None,
                 sin_password: bool = False, con_salir: bool = True) -> str:
    aviso_pw = ""
    if sin_password:
        aviso_pw = ('<div class="aviso">⚠️ El panel está <strong>sin contraseña</strong>. '
                    'Antes de publicar la app en internet define la variable '
                    '<code>EVENTO_ADMIN_PASSWORD</code> (ver README).</div>')
    contenido = (f"{_nav(ruta, con_salir)}{aviso_pw}"
                 f'<h1 style="margin-top:var(--e2)">{e(titulo)}</h1>{cuerpo}')
    return base(f"{titulo} — NeaEvento", contenido, admin=True, avisos=avisos)


def render_entrar(avisos=None) -> str:
    cuerpo = """
<div style="max-width:400px;margin:var(--e6) auto 0">
  <h1 style="text-align:center">🔒 Organización</h1>
  <div class="tarjeta">
    <form method="post">
      <label for="password">Contraseña del panel</label>
      <input id="password" name="password" type="password" autofocus required
             autocomplete="current-password" style="width:100%">
      <div style="margin-top:var(--e4)">
        <button class="boton bloque" type="submit">Entrar</button>
      </div>
    </form>
  </div>
  <div class="pie">Nea Master · NeaEvento</div>
</div>
"""
    return base("Entrar — NeaEvento", cuerpo, admin=True, avisos=avisos)


def _kpi(valor, texto: str, de: int = 0) -> str:
    """Un número grande con su etiqueta y, si tiene sentido, su barra de avance."""
    barra = ""
    if de:
        barra = (f'<div class="barra"><span style="width:'
                 f'{min(100, round(valor / de * 100))}%"></span></div>')
    return (f'<div class="kpi"><div class="valor">{valor}'
            f'{f"<span style=font-size:15px;color:var(--gris)> / {de}</span>" if de else ""}'
            f'</div><div class="texto">{texto}</div>{barra}</div>')


def _preparativos(cfg: dict, datos: dict, sin_password: bool) -> str:
    """Lista de «qué está listo y qué falta» para el día del evento."""
    n = datos["participantes"]
    eq = datos["equipos"]
    pasos = [
        (n > 0, f"{n} participantes cargados" if n else
         "Cargar la lista de participantes", "/admin/participantes", "Participantes"),
        (eq > 0, f"{eq} equipos creados" if eq else "Crear los equipos",
         "/admin/equipos", "Equipos"),
        (eq > 0 and n > 0 and datos["sin_equipo"] == 0,
         "Sorteo de equipos hecho" if eq and datos["sin_equipo"] == 0 else
         f"Sortear los equipos ({datos['sin_equipo']} sin equipo)",
         "/admin/equipos", "Sortear"),
        (eq > 0 and datos["con_capitan"] >= eq,
         "Capitanes sorteados" if eq and datos["con_capitan"] >= eq else
         "Sortear los capitanes", "/admin/equipos", "Capitanes"),
        (eq > 0 and datos["con_sala"] >= eq,
         "Salas de la escape repartidas" if eq and datos["con_sala"] >= eq else
         "Sortear las salas de la escape room", "/admin/agenda", "Salas"),
        (datos["con_tanda"] > 0,
         "Tandas de karts sorteadas" if datos["con_tanda"] else
         "Sortear las tandas de karts", "/admin/agenda", "Tandas"),
        (datos["actividades"] > 0 and datos["lugares"] > 0,
         f"Agenda ({datos['actividades']}) y lugares ({datos['lugares']}) puestos",
         "/admin/agenda", "Agenda"),
        (bool((cfg.get("url_base") or "").strip()),
         "URL pública fijada (los enlaces se generan con ella)" if
         (cfg.get("url_base") or "").strip() else
         "Fijar la URL pública antes de repartir enlaces", "/admin/evento", "Evento"),
        (not sin_password, "Panel protegido con contraseña" if not sin_password else
         "Poner contraseña al panel (EVENTO_ADMIN_PASSWORD)", "", ""),
        (n > 0 and datos["han_abierto"] >= n,
         f"Enlaces abiertos por {datos['han_abierto']} de {n}" if n else
         "Repartir los enlaces personales", "/admin/enlaces", "Enlaces"),
    ]
    filas = ""
    for hecho, texto, url, accion in pasos:
        icono = "✅" if hecho else "⬜"
        enlace = (f' <a href="{url}" style="white-space:nowrap">{e(accion)} →</a>'
                  if url and not hecho else "")
        filas += (f'<div class="paso{" hecho" if hecho else ""}">'
                  f'<span class="paso-icono" aria-hidden="true">{icono}</span>'
                  f'<span>{e(texto)}{enlace}</span></div>')
    listos = sum(1 for hecho, *_ in pasos if hecho)
    return f"""
<div class="tarjeta">
  <h2>Preparativos <span class="silencio" style="font-weight:600">
  · {listos} de {len(pasos)} listos</span></h2>
  <div class="barra" style="margin-bottom:var(--e3)"><span
       style="width:{round(listos / len(pasos) * 100)}%"></span></div>
  <div class="preparativos">{filas}</div>
</div>"""


def render_resumen(cfg: dict, datos: dict, equipos: list[dict],
                   referencia: date, avisos=None, sin_password=False) -> str:
    contador = cuenta_atras(cfg.get("fecha", ""), referencia)
    chip = f'<span class="fecha-chip">{e(contador)}</span>' if contador else ""
    n = datos["participantes"]

    kpis = (_kpi(n, "participantes")
            + _kpi(datos["confirmados"], "✅ confirmados", de=n)
            + _kpi(datos["han_abierto"], "👁 abrieron su enlace", de=n)
            + _kpi(datos["pendientes"], "⏳ sin responder")
            + _kpi(datos["no_vienen"], "❌ no vienen")
            + _kpi(datos["sin_equipo"], "🎲 sin equipo"))

    filas_equipos = ""
    for eq in equipos:
        filas_equipos += (f'<tr><td class="nowrap">'
                          f'{_simbolo_equipo(eq.get("color"), eq.get("emoji"))}'
                          f'{e(eq["nombre"])}</td>'
                          f'<td>{eq["n_miembros"]}</td><td>{eq["n_confirmados"]}</td>'
                          f'<td>{e(eq.get("sala")) or "—"}</td></tr>')
    tabla_equipos = (f'<div class="tarjeta"><h2>Equipos</h2><div class="envoltorio-tabla">'
                     f'<table class="tabla"><tr><th>Equipo</th><th>Miembros</th>'
                     f'<th>Confirmados</th><th>Sala</th></tr>{filas_equipos}</table>'
                     f'</div></div>'
                     if filas_equipos else
                     '<div class="tarjeta"><h2>Equipos</h2><p class="silencio">Aún no hay '
                     'equipos. Créalos en la pestaña <a href="/admin/equipos">Equipos</a>.'
                     '</p></div>')

    sin_abrir = datos.get("sin_abrir") or []
    if sin_abrir:
        nombres = ", ".join(e(x) for x in sin_abrir)
        bloque_sin_abrir = (f'<div class="tarjeta"><h2>Aún no han abierto su enlace '
                            f'({len(sin_abrir)})</h2><p class="silencio">{nombres}</p>'
                            f'<p class="silencio" style="margin-bottom:0">Reenvíales el '
                            f'enlace desde la pestaña <a href="/admin/enlaces">Enlaces'
                            f'</a>.</p></div>')
    else:
        bloque_sin_abrir = ""

    cuerpo = f"""
<div class="meta"><span><strong>{e(cfg.get('nombre'))}</strong></span>
  <span>📅 {e(fecha_bonita(cfg.get('fecha', '')))}</span>
  <span>🕘 {e(cfg.get('hora'))} h</span></div>
{chip}
<div class="kpis">{kpis}</div>
{_preparativos(cfg, datos, sin_password)}
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
    companeros_grupo: dict[str, list[str]] = {}
    for p in lista:
        grupo = (p.get("grupo_sorteo") or "").strip()
        if grupo:
            companeros_grupo.setdefault(grupo, []).append(nombre_corto(p))
    filas = ""
    for p in lista:
        if p.get("equipo_nombre"):
            equipo_html = (_simbolo_equipo(p.get("equipo_color"), p.get("equipo_emoji"))
                           + e(p["equipo_nombre"]))
        else:
            equipo_html = '<span class="silencio">—</span>'
        partes_detalle = [x for x in (p.get("apodo"), p.get("rol")) if x]
        grupo = (p.get("grupo_sorteo") or "").strip()
        if grupo:
            otros = [n for n in companeros_grupo.get(grupo, [])
                     if n != nombre_corto(p)]
            if otros:
                partes_detalle.append("🔗 va con " + ", ".join(otros))
        detalle = " · ".join(partes_detalle)
        detalle_html = f'<div class="silencio">{e(detalle)}</div>' if detalle else ""
        filas += f"""
<tr>
  <td><strong>{e(p['nombre'])}</strong>{detalle_html}</td>
  <td class="solo-ancho">{e(p['telefono']) or '<span class="silencio">—</span>'}</td>
  <td class="nowrap">{equipo_html}</td>
  <td>{_insignia_estado(p)}</td>
  <td class="acciones">
    <a class="boton secundario mini" href="/admin/participantes/{p['id']}">Editar</a>
  </td>
</tr>"""
    tabla = (f'<div class="envoltorio-tabla"><table class="tabla">'
             f'<tr><th>Nombre</th><th class="solo-ancho">Teléfono</th><th>Equipo</th>'
             f'<th>Estado</th><th></th></tr>{filas}</table></div>'
             if filas else
             '<p class="silencio">Todavía no hay participantes: añádelos aquí arriba, '
             'pégalos de una lista o importa un Excel/CSV.</p>')

    cuerpo = f"""
<div class="tarjeta">
  <h2>Añadir participante</h2>
  <form class="linea" method="post" action="/admin/participantes/nuevo">
    <div><label>Nombre *</label><input name="nombre" required placeholder="Nombre y apellidos"></div>
    <div><label>Apodo</label><input name="apodo" size="10" placeholder="Bea"></div>
    <div><label>Rol</label><input name="rol" size="10" placeholder="comercial / técnico"></div>
    <div><label>Teléfono</label><input name="telefono" placeholder="6XXXXXXXX"></div>
    <div><label>Email</label><input name="email" type="email"></div>
    <div><label>Equipo</label><select name="equipo_id">{_opciones_equipos(equipos)}</select></div>
    <button class="boton" type="submit">Añadir</button>
  </form>
  <p class="silencio" style="margin-bottom:0">El <strong>apodo</strong> es como le
  saluda la app («¡Hola, Bea!»). El <strong>rol</strong> (p. ej. comercial /
  técnico) sirve para que el sorteo reparta los roles a partes iguales entre
  los equipos.</p>
</div>

<div class="tarjeta">
  <h2>Cargar una lista entera</h2>
  <form class="linea" method="post" action="/admin/participantes/importar"
        enctype="multipart/form-data">
    <div>
      <label>Excel (.xlsx) o CSV — columnas: nombre, apodo, rol, telefono, email,
      equipo (solo «nombre» es obligatoria)</label>
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
  <p class="silencio" style="margin-bottom:0">Puedes re-importar la lista cuantas
  veces quieras: a los nombres que ya existen no se les duplica ni se les cambia
  nada — solo se les rellenan los datos que tuvieran vacíos (p. ej. si el Excel
  nuevo trae los correos o teléfonos). Su enlace personal no cambia.</p>
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
    <label>Apodo (como le saluda la app)</label>
    <input name="apodo" value="{e(p.get('apodo'))}" style="width:100%">
    <label>Rol (p. ej. comercial / técnico — el sorteo los reparte a partes iguales)</label>
    <input name="rol" value="{e(p.get('rol'))}" style="width:100%">
    <label>Teléfono</label><input name="telefono" value="{e(p['telefono'])}" style="width:100%">
    <label>Email</label><input name="email" type="email" value="{e(p['email'])}" style="width:100%">
    <label>Equipo</label>
    <select name="equipo_id" style="width:100%">{_opciones_equipos(equipos, p['equipo_id'])}</select>
    <label>Tanda de karts</label>
    <select name="tanda" style="width:100%">
      <option value="">— Sin tanda —</option>
      {"".join(f'<option value="{t}"{" selected" if (p.get("tanda") or "").strip() == t else ""}>{ORDINAL_TANDA[t]} tanda</option>' for t in ("1", "2", "3"))}
    </select>
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


def _tarjeta_juntos(grupos: list[dict], participantes: list[dict]) -> str:
    reglas = ""
    for g in grupos:
        nombres = " + ".join(f"<strong>{e(nombre_corto(m))}</strong>"
                             for m in g["miembros"])
        reglas += f"""
<div class="regla-juntos">🔗 {nombres}
  <form class="compacta" method="post" action="/admin/juntos/{e(g['grupo'])}/borrar">
    <button class="boton secundario mini" type="submit">Deshacer</button>
  </form>
</div>"""
    if not reglas:
        reglas = ('<p class="silencio">No hay ninguna regla todavía. Marca abajo a '
                  'las personas y pulsa «Unir».</p>')
    casillas = ""
    for p in participantes:
        marca = " 🔗" if (p.get("grupo_sorteo") or "").strip() else ""
        casillas += (f'<label title="{e(p["nombre"])}">'
                     f'<input type="checkbox" name="ids" value="{p["id"]}">'
                     f'{e(nombre_corto(p))}{marca}</label>')
    return f"""
<div class="tarjeta">
  <h2>🔗 Personas que van juntas</h2>
  <p class="silencio">El sorteo sigue siendo aleatorio, pero a las personas unidas
  con una regla las mete <strong>siempre en el mismo equipo</strong>. Puedes crear
  varias parejas o grupos.</p>
  {reglas}
  <form method="post" action="/admin/juntos/nuevo">
    <div class="selector-personas">{casillas}</div>
    <button class="boton secundario" type="submit">🔗 Unir a los marcados</button>
  </form>
</div>"""


def render_equipos(equipos: list[dict], miembros_por_equipo: dict[int, list[dict]],
                   n_sin_equipo: int, grupos: list[dict],
                   participantes: list[dict], avisos=None,
                   sin_password=False) -> str:
    filas = ""
    for eq in equipos:
        nombres = ", ".join(
            e(f"{m['nombre']} ({m['rol'].strip()})" if (m.get("rol") or "").strip()
              else m["nombre"])
            for m in miembros_por_equipo.get(eq["id"], [])
        )
        capitan = next((nombre_corto(m) for m in miembros_por_equipo.get(eq["id"], [])
                        if m["id"] == eq.get("capitan_id")), None)
        filas += f"""
<div class="tarjeta" style="border-left:5px solid {e(eq.get('color') or '#CC0C18')}">
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
  {f'<p class="silencio" style="margin:4px 0 0">👑 Capitán: <strong>{e(capitan)}</strong></p>' if capitan else ''}
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

{_tarjeta_juntos(grupos, participantes)}

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
  cada persona entra en el equipo que menos gente tiene, y si los participantes
  tienen <strong>rol</strong> (p. ej. comercial / técnico) también se reparte cada
  rol a partes iguales entre los equipos. Las reglas <strong>🔗 van juntos</strong>
  se respetan siempre. Las asignaciones hechas a mano se respetan si usas
  «Repartir a los que no tienen equipo».</p>
</div>

<div class="tarjeta">
  <h2>👑 Capitanes</h2>
  <form class="compacta" method="post" action="/admin/capitanes/sortear"
        onsubmit="return confirm('Se sorteará un capitán por equipo (si ya había, se rehacen). ¿Seguir?')">
    <button class="boton" type="submit">🎲 Sortear capitanes</button>
  </form>
  <p class="silencio" style="margin-bottom:0">Uno al azar por equipo. El capitán
  sale con 👑 en su equipo y es quien apunta, desde su móvil, la hora de salida
  de su sala de la escape room (pestaña 🏆 Puntos de su enlace). Hazlo después
  del sorteo de equipos.</p>
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


ORDINAL_TANDA = {"1": "1ª", "2": "2ª", "3": "3ª"}


def _tarjeta_salas(cfg: dict, equipos: list[dict], lugares: list[dict],
                   salas: list[dict]) -> str:
    titulo = cfg.get("escape_titulo") or "Escape room"
    opciones_lugar = '<option value="">— Sin lugar —</option>'
    for lugar_ in lugares:
        sel = " selected" if str(lugar_["id"]) == (cfg.get("escape_lugar_id") or "") else ""
        opciones_lugar += f'<option value="{lugar_["id"]}"{sel}>{e(lugar_["nombre"])}</option>'
    opciones_sala = '<option value="">— (sin restricción) —</option>'
    for s in salas:
        opciones_sala += f'<option value="{e(s["nombre"])}">{e(s["nombre"])}</option>'
    reparto = ""
    if any((eq.get("sala") or "").strip() for eq in equipos):
        for eq in equipos:
            reparto += (f'<div style="margin:4px 0">'
                        f'{_simbolo_equipo(eq.get("color"), eq.get("emoji"))}'
                        f'<strong>{e(eq["nombre"])}</strong> → '
                        f'{e(eq.get("sala")) or "<span class=silencio>—</span>"}</div>')
    else:
        reparto = ('<p class="silencio">Salas aún sin sortear. Haz primero el sorteo '
                   'de equipos y luego pulsa «Sortear salas».</p>')
    return f"""
<div class="tarjeta">
  <h2>🗝️ Salas de la {e(titulo)}</h2>
  <form method="post" action="/admin/salas/config">
    <div class="linea" style="display:flex;gap:8px;flex-wrap:wrap">
      <div><label>Actividad</label>
        <input name="escape_titulo" value="{e(titulo)}" size="12"></div>
      <div><label>Hora (hay que estar allí)</label>
        <input name="escape_hora" type="time" value="{e(cfg.get('escape_hora'))}"></div>
      <div><label>Lugar</label>
        <select name="escape_lugar_id">{opciones_lugar}</select></div>
    </div>
    <label>Salas (una por línea: «Nombre: descripción») — debe haber una por equipo</label>
    <textarea name="escape_salas" rows="4" style="width:100%">{e(cfg.get('escape_salas'))}</textarea>
    <div style="margin-top:8px"><button class="boton mini" type="submit">Guardar</button></div>
  </form>
  <form method="post" action="/admin/salas/sortear" style="margin-top:12px"
        onsubmit="return confirm('Se sorteará qué sala juega cada equipo (si ya había reparto, se rehace). ¿Seguir?')">
    <div class="linea" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">
      <div><label>Restricción (opcional): la sala…</label>
        <select name="sala_excluida">{opciones_sala}</select></div>
      <div><label>…NO puede tocarle al equipo</label>
        <select name="equipo_excluido">{_opciones_equipos(equipos, texto_vacio="— (ninguno) —")}</select></div>
      <button class="boton" type="submit">🎲 Sortear salas</button>
    </div>
  </form>
  <form class="compacta" method="post" action="/admin/salas/deshacer"
        onsubmit="return confirm('¿Quitar el reparto de salas?')">
    <button class="boton secundario mini" type="submit" style="margin-top:8px">Deshacer</button>
  </form>
  <p class="silencio">Cada participante verá su sala (con su descripción y el
  «cómo llegar») en su Programa.</p>
  {reparto}
</div>"""


def _tarjeta_tandas(cfg: dict, participantes: list[dict],
                    lugares: list[dict]) -> str:
    nombre = cfg.get("karts_nombre") or "Karts"
    opciones_lugar = '<option value="">— Sin lugar —</option>'
    for lugar_ in lugares:
        sel = " selected" if str(lugar_["id"]) == (cfg.get("karts_lugar_id") or "") else ""
        opciones_lugar += f'<option value="{lugar_["id"]}"{sel}>{e(lugar_["nombre"])}</option>'
    listas = ""
    hay_tandas = any((p.get("tanda") or "").strip() for p in participantes)
    for t in ("1", "2", "3"):
        hora = cfg.get(f"karts_hora{t}") or ""
        chips = ""
        for p in participantes:
            if (p.get("tanda") or "").strip() == t:
                chips += (f'<span class="chip">'
                          f'{_simbolo_equipo(p.get("equipo_color"), p.get("equipo_emoji")) if p.get("equipo_nombre") else ""}'
                          f'{e(nombre_corto(p))}</span>')
        extra = (' <span class="silencio">+ los 2 mejores tiempos de las tandas '
                 'anteriores</span>' if t == "3" else "")
        if hay_tandas:
            listas += (f'<div style="margin:6px 0"><strong>{ORDINAL_TANDA[t]} tanda '
                       f'· {e(hora)}</strong>{extra}<br>'
                       f'{chips or "<span class=silencio>—</span>"}</div>')
    if not hay_tandas:
        listas = ('<p class="silencio">Aún no hay tandas sorteadas. Haz primero el '
                  'sorteo de equipos y luego pulsa «Sortear tandas».</p>')
    return f"""
<div class="tarjeta">
  <h2>🏎️ Tandas de {e(nombre)}</h2>
  <form class="linea" method="post" action="/admin/tandas/config">
    <div><label>Actividad</label><input name="karts_nombre" value="{e(nombre)}" size="10"></div>
    <div><label>1ª tanda</label><input name="karts_hora1" type="time" value="{e(cfg.get('karts_hora1'))}"></div>
    <div><label>2ª tanda</label><input name="karts_hora2" type="time" value="{e(cfg.get('karts_hora2'))}"></div>
    <div><label>3ª tanda (final)</label><input name="karts_hora3" type="time" value="{e(cfg.get('karts_hora3'))}"></div>
    <div><label>Lugar</label><select name="karts_lugar_id">{opciones_lugar}</select></div>
    <button class="boton mini" type="submit">Guardar</button>
  </form>
  <div class="acciones" style="margin-top:10px">
    <form class="compacta" method="post" action="/admin/tandas/sortear"
          onsubmit="return confirm('Se sortearán las tandas (si ya había, se rehacen). ¿Seguir?')">
      <button class="boton" type="submit">🎲 Sortear tandas</button>
    </form>
    <form class="compacta" method="post" action="/admin/tandas/deshacer"
          onsubmit="return confirm('¿Quitar todas las tandas?')">
      <button class="boton secundario mini" type="submit">Deshacer</button>
    </form>
  </div>
  <p class="silencio">8 y 8 al azar en las dos primeras (repartiendo cada equipo
  entre ambas); los que quedan fuera van a la 3ª, la final, junto a los 2 mejores
  tiempos (eso se decide en la pista — puedes cambiar la tanda de cualquiera en
  su ficha). Cada participante ve su tanda y su hora en su Programa.</p>
  {listas}
</div>"""


def render_agenda(items: list[dict], lugares: list[dict], equipos: list[dict],
                  cfg: dict, participantes: list[dict], salas: list[dict],
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
  equipo (p. ej. cada equipo a su sala de la escape room: crea una actividad por
  sala y asígnale su equipo — cada participante ve solo la suya).</p>
</div>
<div class="tarjeta">
  <h2>Programa del día ({len(items)})</h2>
  {tabla}
</div>
{_tarjeta_salas(cfg, equipos, lugares, salas)}
{_tarjeta_tandas(cfg, participantes, lugares)}
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
        if f["confirmado"] == 1:
            estado = '<span class="insignia ok">✅ viene</span>'
        elif f["confirmado"] == -1:
            estado = '<span class="insignia no">❌ no viene</span>'
        elif f["visto_en"]:
            estado = '<span class="insignia pte">👁 lo abrió</span>'
        else:
            estado = '<span class="insignia pte">sin abrir</span>'
        filas += f"""
<tr>
  <td><strong>{e(f['nombre'])}</strong></td>
  <td style="word-break:break-all"><a href="{e(f['enlace'])}" target="_blank"
      rel="noopener">{e(f['enlace'])}</a></td>
  <td class="nowrap">{estado}</td>
  <td class="acciones">
    <button class="boton secundario mini" type="button" data-c="{e(f['enlace'])}"
            onclick="copiar(this)">Copiar</button>
    {wa}
  </td>
</tr>"""
    tabla = (f'<div class="envoltorio-tabla"><table class="tabla">'
             f'<tr><th>Participante</th><th>Enlace personal</th><th>Estado</th>'
             f'<th></th></tr>{filas}</table></div>'
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
    <label>Historia que se cuenta antes del sorteo (una frase por línea; puedes
    usar {{equipos}} y {{participantes}}, que se cambian por los números reales)</label>
    <textarea name="historia" rows="6" style="width:100%">{e(cfg.get('historia'))}</textarea>
    <label>Contacto de la organización (nombre y teléfono; sale al pie de la página)</label>
    <input name="contacto" value="{e(cfg.get('contacto'))}" style="width:100%"
           placeholder="Borja (600 111 222)">
    <label>URL pública de la app (para generar los enlaces personales)</label>
    <input name="url_base" value="{e(cfg.get('url_base'))}" style="width:100%"
           placeholder="https://evento.neamaster.com o http://IP:8502">
    <label>Plantilla del mensaje de WhatsApp — usa {{nombre}}, {{apodo}} y {{enlace}}</label>
    <textarea name="msg_whatsapp" rows="4" style="width:100%">{e(cfg.get('msg_whatsapp'))}</textarea>
    <div style="margin-top:12px">
      <button class="boton" type="submit">Guardar</button>
    </div>
  </form>
</div>

<div class="tarjeta" style="max-width:640px">
  <h2>💾 Copia de seguridad</h2>
  <p class="silencio">Todo el evento (participantes con sus enlaces, equipos,
  reglas, salas, tandas, agenda y lugares) vive en un único fichero. Descárgalo
  de vez en cuando; restaurarlo lo deja todo exactamente como estaba.</p>
  <div class="acciones">
    <a class="boton secundario" href="/admin/copia.db">⬇️ Descargar copia</a>
    <form class="compacta" method="post" action="/admin/restaurar"
          enctype="multipart/form-data"
          onsubmit="return confirm('Se SUSTITUIRÁ todo el evento actual por la copia. ¿Seguir?')">
      <input type="file" name="fichero" accept=".db" required>
      <button class="boton secundario" type="submit">♻ Restaurar copia</button>
    </form>
  </div>
</div>
"""
    return pagina_admin("Evento", "/admin/evento", cuerpo, avisos=avisos,
                        sin_password=sin_password)
