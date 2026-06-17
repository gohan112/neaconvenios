"""
Extractor de tablas salariales mediante Claude Opus 4.8 (API de Anthropic).

Complementa a extractor.py (determinista). Claude lee el PDF de forma nativa
—cualquier maquetación— y devuelve las tablas en un esquema fijo (salida
estructurada). Instrucciones afinadas de forma adversarial para datos de nómina.

Optimización de tokens: antes de enviar, se recorta el PDF a solo las páginas con
tablas salariales (un convenio completo tiene decenas de páginas; las tablas son
2-3). El recorte NUNCA descarta una tabla: ante la duda incluye de más, y si no
detecta cabeceras envía el PDF entero.

IMPORTANTE (datos de nómina):
- Claude PUEDE equivocarse. Su salida es un BORRADOR: revísala en pantalla y, con
  SQL de referencia de WK, crúzala con el comparador. Marca filas dudosas en
  'revisar' y avisos globales, pero nunca inventa cifras.
- Requiere ANTHROPIC_API_KEY en el servidor (console.anthropic.com).
"""

from __future__ import annotations

import base64
import json
import os
import re

from extractor import _RE_HEADER_ANIO, NIVELES_ROMANOS, TablaSalarial

MODELO = "claude-opus-4-8"

# Tokens que parecen importe en estas tablas (siempre llevan coma decimal).
_RE_IMPORTE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+")
_RE_ORDINAL = re.compile(r"^\d{1,2}\.$")

# --- Esquema de salida (reconciliado con el prompt; additionalProperties:False) ---
_NUM_O_NULL = {"anyOf": [{"type": "number"}, {"type": "null"}]}
ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tablas", "avisos"],
    "properties": {
        "avisos": {"type": "array", "items": {"type": "string"}},
        "tablas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["anio", "nota_vigencia", "perfil", "columnas", "filas", "pie"],
                "properties": {
                    "anio": {"type": "integer"},
                    "nota_vigencia": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "perfil": {"type": "string"},
                    "columnas": {"type": "array", "items": {"type": "string"}},
                    "filas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["nivel", "valores", "revisar", "nota"],
                            "properties": {
                                "nivel": {"type": "string"},
                                "valores": {"type": "array", "items": _NUM_O_NULL},
                                "revisar": {"type": "boolean"},
                                "nota": {"type": "string"},
                            },
                        },
                    },
                    "pie": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["plus_extrasalarial", "dieta", "media_dieta",
                                     "kilometraje", "otros_pluses"],
                        "properties": {
                            "plus_extrasalarial": _NUM_O_NULL,
                            "dieta": _NUM_O_NULL,
                            "media_dieta": _NUM_O_NULL,
                            "kilometraje": _NUM_O_NULL,
                            "otros_pluses": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["rotulo", "importes"],
                                    "properties": {
                                        "rotulo": {"type": "string"},
                                        "importes": {"type": "array", "items": {"type": "number"}},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}

# --- Instrucciones para Claude (diseñadas y revisadas de forma adversarial) ---
_INSTRUCCIONES = """\
Eres un extractor de tablas salariales de convenios colectivos publicados en boletines \
oficiales (el BOE estatal, el BOPA de Asturias u otro boletín autonómico; la estructura de \
las tablas es equivalente). Recibes un PDF y devuelves EXCLUSIVAMENTE \
un objeto JSON con el esquema del final. Estos datos alimentan nóminas: un importe \
equivocado paga mal a una persona. Tu prioridad ABSOLUTA es la fidelidad literal.

0. REGLA SUPREMA — NO INVENTES NI CORRIJAS CIFRAS
- Transcribe cada importe EXACTAMENTE como aparece, dígito a dígito, con su coma y todos \
sus decimales. Prohibido redondear, truncar, reformatear, interpolar, copiar de otra \
fila/otro año, o "corregir" un valor porque rompa una tendencia o parezca atípico.
- Si NO puedes leer una celda con certeza, pon null en su posición y marca esa fila con \
revisar=true y una nota. Un hueco es preferible a un número inventado.
- No añadas ni renumeres niveles/categorías que no aparezcan literalmente. Emite SOLO lo que ves.
- Si una cifra parece errónea, transcríbela TAL CUAL y marca revisar=true; nunca la cambies.

1. QUÉ ES UNA TABLA Y CÓMO TROCEAR POR AÑO
- Una tabla empieza en una cabecera "TABLA SALARIAL AÑO 20XX" o "TABLAS SALARIALES AÑO 20XX" \
(plural). El boletín puede espaciar los caracteres y la "Ñ" salir como "N"; acepta variantes.
- Emite UN objeto-tabla por CADA cabecera. Una página puede traer 2-3 tablas (años distintos): \
trocea por cabeceras y asigna cada fila/pie a la tabla cuya cabecera la precede. NO mezcles \
filas ni importes entre años aunque estén en la misma página. Si un mismo año se parte en \
varias páginas, fusiónalo en una sola tabla.
- NO son cabeceras: líneas que empiezan por "SOBRE TABLA..." (son notas de base de cálculo) \
aunque contengan "AÑO 20XX". Una mención de "tabla salarial" dentro de un PÁRRAFO de prosa \
(articulado del convenio) NO es cabecera: solo cuenta "TABLA(S) SALARIAL(ES) ... AÑO 20XX" \
seguido de la rejilla de niveles. En convenios largos, ignora las menciones en prosa.
- Tablas "(clausula de revisión)", "(Revisada)", "DEFINITIVA", "provisional"... NO las descartes \
ni fusiones: emítelas TODAS por separado, cada una con su año, y copia LITERALMENTE su subtítulo \
en "nota_vigencia". NO decidas tú cuál está vigente.

2. FILAS — SEPARAR EL RÓTULO DE LOS IMPORTES
REGLA DE ORO: todo importe lleva coma decimal (40,24 / 2.448,37 / 8,5079). Un entero SIN coma \
NUNCA es importe.
- El rótulo es todo el texto desde el inicio de la fila hasta el PRIMER token que sea importe \
(con coma) o "-". Pertenecen al rótulo, nunca a los importes: el ordinal ("14.", "1."), la EDAD \
(el "17" de "14. Aspirante 17 años"), y las marcas "1ª/2ª/3ª".
- Dos formatos: ROMANO (Construcción: II, III, ... XIII; suele empezar en II). ARÁBIGO "N. Nombre" \
(Metal: "1. Titulado Superior" ... "15."). No INVENTES niveles ausentes (no añadas un I si no está); \
pero si un convenio trae un "I" literal, emítelo.

3. COLUMNAS — MAPEO POSICIONAL ESTRICTO
- Reconstruye la cabecera APILANDO por posición horizontal (columna), no concatenando por orden de \
lectura: el boletín parte títulos en 2-3 líneas ("Carencia/Incentivo", "Plus" arriba de "Festivo" = \
"Plus Festivo"). Los textos "Dia", "Periodo", "anual", "mensual", "por día natural/trabajado", \
"Festivo" son rótulos de unidad: NUNCA son importes, ignóralos al contar valores.
- Mapea cada importe a su columna SOLO por POSICIÓN, de izquierda a derecha. Nunca reasignes una \
columna porque el valor parezca alto o bajo: el orden del PDF es la única verdad.
- Construcción: 11 columnas en este orden: salario_base, plus_asistencia, vac_dia, vac_periodo, \
verano_dia, verano_periodo, navidad_dia, navidad_periodo, retribucion_anual, plan_pensiones, \
plan_pensiones_2. Metal: 7 columnas: salario_convenio, plus_asistencia, carencia_incentivo, \
plus_convenio, pagas_extras, plus_festivo, horas_extras. Otros formatos: usa los nombres que veas; \
si no los reconoces, col_1, col_2... Si una columna existe en un año y no en otro, decláralas por \
año de forma independiente; no la inventes donde no está.
- "columnas" = lista de nombres en orden. "valores" de cada fila = importes en ESE mismo orden.

4. CELDAS VACÍAS
- Una celda "-" o en blanco se emite como null OCUPANDO su posición. Nunca la elimines ni colapses \
(si no, los importes se corren de columna). "valores" debe tener SIEMPRE tantos elementos como \
columnas (contando los null). Un null se queda null; prohibido rellenarlo infiriendo.

5. FILAS PARTIDAS (solo Construcción)
- En Construcción la Retribución Anual / plan de pensiones a veces va en la línea siguiente SIN \
rótulo: concaténala a la fila anterior hasta completar las 11 columnas. En Metal y otros, una línea \
sin rótulo es pie o ruido, NO una fila.

6. PIE DE TABLA (dietas, kilometraje, pluses)
- El pie pertenece a la tabla del año cuya cabecera lo precede; no lo compartas entre años.
- EL PIE SUELE VENIR EN REJILLA DE DOS COLUMNAS (TITULO EUROS | TITULO EUROS): una misma línea \
física contiene DOS pares rótulo+valor independientes. Pártela en sus pares; el segundo importe es \
del rótulo de la DERECHA, no un segundo valor del de la izquierda. Ej.: "Turnicidad ... 4,62 Dieta \
... 68,00" -> Turnicidad=4,62 y Dieta=68,00 (no Turnicidad=[4,62; 68,00]). Ej. Construcción: \
"Kilometraje Euros/km. 0,4146 1/2 Dieta 12,68" -> kilometraje=0,4146 y media_dieta=12,68 (no los cruces).
- Conceptos a "pie" (los que existan; también con coma decimal):
  * plus_extrasalarial: "Plus Mixto Extrasalarial" (OJO errata frecuente del boletín "Plus Mixto Extrasarial", sin la 'l').
  * dieta: "Dieta" a secas (sin "1/2" ni "Media").
  * media_dieta: "1/2 Dieta", "½ Dieta" o "Media Dieta" -> SIEMPRE media_dieta, nunca dieta.
  * kilometraje: "Kilometraje".
- Otros pluses (Trabajo Nocturno, "Penosos, tóxicos y peligrosos", Turnicidad, Jefatura de Equipo, \
"Incremento hora extra en festivo"...) van en "otros_pluses" como {rotulo, importes[]}. Un rótulo \
puede tener VARIOS importes propios en su línea: ej. "Penosos, tóxicos y peligrosos 4,45 6,31 8,29 \
Incremento hora extra en festivo 1,74" -> Penosos tiene EXACTAMENTE [4,45; 6,31; 8,29]; el 1,74 es \
de "Incremento hora extra en festivo" (columna derecha), NO un cuarto valor de Penosos.

7. RUIDO DEL BOLETÍN (ignorar siempre)
- Cabeceras/pies del boletín ("BOLETÍN OFICIAL...", "BOE núm. ...", "núm. ... de ...", la URL del \
boletín como "sede.asturias.es/bopa" o "boe.es", números de página). Texto rotado/espejo \
("25301-5202", ".dóC" = "Cód." invertido): nunca son datos.
- Números de subtítulo/jornada ("1.736 horas", "365 días", "366 días", "%"): NO son importes de fila.
- Rellenos de puntos ("............", el carácter "…") y unidades sueltas ("Euros/km.", "por día \
natural", "anual", "mensual") separan rótulo de valor pero no son ni rótulo ni cifra: ignóralos.
- Punto = separador de miles (3.310,51); coma = decimal. Preserva TODOS los decimales (2 en \
mensual/anual; 4 en día/kilometraje: 8,5079; 0,4006). Importes negativos (-12,34): conserva el signo.

8. AUTOCOMPROBACIÓN (reporta en revisar/nota o avisos; NO corrijas)
- Cada fila debe tener tantos valores como columnas (contando null). Si no, revisar=true con el conteo.
- Si una celda no se pudo leer con certeza, revisar=true indicando cuál.
- Sospechas de divergencia (años con importes idénticos, o un nivel que decrece de un año al \
siguiente) SOLO en columnas que normalmente varían (salario base, retribución anual). EXCLUYE las \
columnas y conceptos típicamente constantes (Plus Convenio, Plus Asistencia, Dieta), cuyo valor \
repetido es normal y no debe inundar los avisos.

9. SALIDA — devuelve SOLO este JSON, sin texto alrededor. No emitas claves fuera del esquema \
(se rechazan). Campos por tabla: anio (int), nota_vigencia (texto literal del subtítulo o null), \
perfil ("construccion"|"metal"|"generico"), columnas (lista), filas (cada una: nivel = rótulo \
literal; valores = números o null en el orden de columnas; revisar = true si dudosa; nota = motivo \
o ""), pie (plus_extrasalarial, dieta, media_dieta, kilometraje = número o null; otros_pluses = \
lista de {rotulo, importes[]}). Y "avisos" = lista de mensajes globales de revisión.
Recuerda: es un BORRADOR para revisión humana antes de generar nóminas. NUNCA inventes una cifra.
"""


def construir_pdf_tablas(ruta_pdf: str) -> tuple[str, str]:
    """
    Detecta las páginas con tablas salariales y devuelve (ruta_a_enviar, motivo).
    Solo es una optimización de tokens: NUNCA descarta una tabla; ante la duda incluye
    de más, y si no detecta cabeceras devuelve el PDF entero. motivo: 'recortado' o
    'entero:<razón>'. Propaga errores de I/O; no los traga.
    """
    import pdfplumber
    from pypdf import PdfReader, PdfWriter

    señales: dict[int, dict] = {}
    cabeceras: set[int] = set()
    con_texto = 0

    with pdfplumber.open(ruta_pdf) as pdf:
        total = len(pdf.pages)
        for i, pagina in enumerate(pdf.pages):
            try:
                palabras = pagina.extract_words(x_tolerance=1.5, y_tolerance=2)
            except Exception:  # noqa: BLE001 — una página ilegible no aborta el documento
                palabras = []
            textos = [w["text"] for w in palabras]
            texto_pag = " ".join(textos)
            if texto_pag.strip():
                con_texto += 1
            es_cab = bool(_RE_HEADER_ANIO.search(texto_pag))
            n_imp = sum(1 for t in textos if _RE_IMPORTE.fullmatch(t))
            tiene_nivel = any(t in NIVELES_ROMANOS or _RE_ORDINAL.match(t) for t in textos)
            señales[i] = {"nimp": n_imp, "niv": tiene_nivel}
            if es_cab:
                cabeceras.add(i)

    if not cabeceras:
        return ruta_pdf, ("entero:sin_texto" if con_texto == 0 else "entero:sin_cabecera")

    # Cabeceras + arrastre en cascada de páginas de continuación (tabla larga / partida)
    seleccion = set(cabeceras)
    for c in cabeceras:
        j = c + 1
        while j < total and j not in cabeceras and (señales[j]["niv"] or señales[j]["nimp"] >= 6):
            seleccion.add(j)
            j += 1

    if len(seleccion) >= total:
        return ruta_pdf, "entero:todas_paginas"

    reader = PdfReader(ruta_pdf)
    writer = PdfWriter()
    for i in sorted(seleccion):
        writer.add_page(reader.pages[i])
    ruta_out = ruta_pdf.rsplit(".", 1)[0] + "_tablas.pdf"
    with open(ruta_out, "wb") as f:
        writer.write(f)
    return ruta_out, "recortado"


def _pdf_base64(ruta_pdf: str) -> str:
    with open(ruta_pdf, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def extraer_con_claude(ruta_pdf: str, api_key: str | None = None) -> list[TablaSalarial]:
    """
    Extrae las tablas del PDF con Claude Opus 4.8 -> objetos TablaSalarial.
    Recorta el PDF a las páginas con tablas para ahorrar tokens. Lanza RuntimeError
    si falta el SDK/clave o la respuesta no es interpretable (no devuelve datos a medias).
    """
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("Falta el paquete 'anthropic'. Instálalo: pip install anthropic") from exc

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("No hay API key de Anthropic (define ANTHROPIC_API_KEY).")

    ruta_envio, motivo = construir_pdf_tablas(ruta_pdf)
    avisos_locales = []
    if motivo.startswith("entero"):
        avisos_locales.append(
            f"Se envió el PDF completo a Claude (motivo: {motivo}); puede consumir más tokens."
        )

    client = anthropic.Anthropic(api_key=key)
    try:
        respuesta = client.messages.create(
            model=MODELO,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": ESQUEMA},
            },
            messages=[{
                "role": "user",
                "content": [
                    {"type": "document", "source": {
                        "type": "base64", "media_type": "application/pdf",
                        "data": _pdf_base64(ruta_envio)}},
                    {"type": "text", "text": _INSTRUCCIONES},
                ],
            }],
        )
    except anthropic.APIError as exc:
        raise RuntimeError(f"Error llamando a la API de Claude: {exc}") from exc

    texto = next((b.text for b in respuesta.content if b.type == "text"), None)
    if not texto:
        raise RuntimeError("Claude no devolvió contenido de texto interpretable.")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"La respuesta de Claude no es JSON válido: {exc}") from exc

    avisos_globales = avisos_locales + list(datos.get("avisos", []))
    tablas = [_a_tabla(t, avisos_globales) for t in datos.get("tablas", [])]
    return tablas


def _a_tabla(t: dict, avisos_globales: list) -> TablaSalarial:
    """Convierte una tabla del JSON de Claude en un TablaSalarial."""
    columnas = list(t.get("columnas", []))
    tabla = TablaSalarial(
        anio=int(t["anio"]),
        titulo=f"AÑO {t['anio']}",
        perfil=t.get("perfil") or "claude",
        columnas=columnas,
        nota_vigencia=t.get("nota_vigencia"),
        avisos=list(avisos_globales),
    )
    for fila in t.get("filas", []):
        valores = fila.get("valores", [])
        d = {"nivel": fila.get("nivel", ""), "_n_valores": len(valores)}
        for i, valor in enumerate(valores):
            d[columnas[i] if i < len(columnas) else f"col_{i + 1}"] = valor
        if fila.get("revisar"):
            d["_revisar"] = True
            d["_nota"] = fila.get("nota", "")
            tabla.avisos.append(f"Nivel {d['nivel']}: revisar — {fila.get('nota', '')}".rstrip(" —"))
        tabla.filas.append(d)
    pie = t.get("pie", {}) or {}
    tabla.pie = {
        "plus_mixto_extrasalarial": pie.get("plus_extrasalarial"),
        "dieta": pie.get("dieta"),
        "media_dieta": pie.get("media_dieta"),
        "kilometraje": pie.get("kilometraje"),
    }
    tabla.pie = {k: v for k, v in tabla.pie.items() if v is not None}
    if pie.get("otros_pluses"):
        tabla.pie["otros_pluses"] = pie["otros_pluses"]
    return tabla


if __name__ == "__main__":
    import sys

    ruta = sys.argv[1] if len(sys.argv) > 1 else "33029708.pdf"
    # Diagnóstico del recorte (no llama a la API):
    envio, motivo = construir_pdf_tablas(ruta)
    print(f"Recorte de páginas: {motivo}  ->  {envio}")
    if "--solo-recorte" in sys.argv:
        sys.exit(0)
    print(f"Extrayendo con {MODELO}…")
    for tabla in extraer_con_claude(ruta):
        print(f"\n===== {tabla.titulo}  ({len(tabla.filas)} niveles)  nota={tabla.nota_vigencia} =====")
        print(f"  columnas: {tabla.columnas}")
        print(f"  pie: {tabla.pie}")
        for fila in tabla.filas[:3]:
            campos = {k: v for k, v in fila.items() if not k.startswith('_') and k != 'nivel'}
            print(f"  {fila['nivel']}: {campos}")
        if tabla.avisos:
            print(f"  ⚠ avisos: {tabla.avisos[:5]}")
