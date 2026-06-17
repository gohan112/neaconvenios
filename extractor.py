"""
Extractor de tablas salariales de convenios publicados en el BOPA.

Lee un PDF del BOPA y devuelve, por cada AÑO con tabla salarial, las filas por
NIVEL/CATEGORÍA con sus importes, más los conceptos de pie de tabla.

Soporta varios formatos mediante PERFILES (auto-detectados):
- "construccion": niveles en romano (II, III, ...), 11 columnas (S.Base, Vacaciones,
  Verano, Navidad, Retri.Anual, plan pensiones...). El BOPA los maqueta con
  caracteres espaciados y parte la Retri.Anual en dos líneas.
- "metal": categorías "1. Titulado Superior", 7 columnas (Salario Convenio, Plus
  Asistencia, Carencia Incentivo, Plus Convenio, Pagas Extras, Plus Festivo, Horas
  Extras). Texto limpio; celdas vacías marcadas con "-".
- "generico": cualquier otra tabla; las columnas se nombran col_1, col_2, ...

Notas de diseño / riesgos:
- Agrupamos palabras por coordenada (top) y ordenamos por x: es lo único que da
  cifras fiables cuando el BOPA espacia los caracteres.
- Una misma página puede traer varias tablas (años distintos); se trocea por las
  cabeceras "TABLA(S) SALARIAL(ES) AÑO XXXX".
- El resultado SIEMPRE debe revisarlo una persona antes de generar nóminas. Esta
  función extrae lo más fielmente posible, NO valida los importes.
- Para AÑADIR un convenio nuevo basta con que case un perfil; si la tabla tiene un
  formato distinto, sale como "generico" (se ven los números, pero hay que mapear
  las columnas a mano para generar el SQL).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

import pdfplumber

NIVELES_ROMANOS = {
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII",
    "IX", "X", "XI", "XII", "XIII", "XIV", "XV",
}

# --- Perfiles de columnas por convenio ------------------------------------
# Construcción Asturias: 11 columnas (mapeo validado contra el SQL de WK).
COLUMNAS_CONSTRUCCION = [
    "salario_base", "plus_asistencia",
    "vac_dia", "vac_periodo",
    "verano_dia", "verano_periodo",
    "navidad_dia", "navidad_periodo",
    "retribucion_anual", "plan_pensiones", "plan_pensiones_2",
]
# Metal Asturias: 7 columnas.
COLUMNAS_METAL = [
    "salario_convenio", "plus_asistencia", "carencia_incentivo",
    "plus_convenio", "pagas_extras", "plus_festivo", "horas_extras",
]
# Alias para compatibilidad con módulos que importan COLUMNAS (Construcción).
COLUMNAS = COLUMNAS_CONSTRUCCION

# Cabecera de una tabla de un año: "TABLA SALARIAL AÑO 2026" o "TABLAS SALARIALES
# AÑO 2024". A\w?O casa "AÑO"/"AO"; \s* tolera el espaciado del BOPA.
_RE_HEADER_ANIO = re.compile(
    r"TABLAS?\s*SALARIAL(?:ES)?\s*A\w?O\s*\(?\s*(20\d{2})", re.IGNORECASE
)
# Nivel en romano al inicio de línea (Construcción).
_RE_NIVEL_ROMANO = re.compile(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\b")
# Categoría "N. Nombre" al inicio de línea (Metal y similares).
_RE_NIVEL_ARABIGO = re.compile(r"^\d{1,2}\.\s*\D")

# Rótulos del pie de tabla.
_RE_PIE_ROTULO = re.compile(r"plus\s*mixto|kilometraje|dieta", re.IGNORECASE)
_RE_PIE_PLUS_MIXTO = re.compile(r"plus\s*mixto\s*extrasa\w*[:\s]*([\d.]+,\d+)", re.IGNORECASE)
_RE_PIE_MEDIA_DIETA = re.compile(r"(?:1\s*/\s*2|media)\s*dieta[:\s]*([\d.]+,\d+)", re.IGNORECASE)
_RE_PIE_KM = re.compile(r"kilometraje[^\d]*([\d.]+,\d+)", re.IGNORECASE)
_RE_PIE_DIETA = re.compile(r"(?<![/2]\s)(?<!media\s)\bdieta[:\s]*([\d.]+,\d+)", re.IGNORECASE)


@dataclass
class TablaSalarial:
    anio: int
    titulo: str
    perfil: str = "generico"               # construccion | metal | generico | claude
    columnas: list[str] = field(default_factory=list)
    filas: list[dict] = field(default_factory=list)   # una dict por nivel
    pie: dict = field(default_factory=dict)
    nota_vigencia: str | None = None       # subtítulo (definitiva/provisional/revisada)
    avisos: list = field(default_factory=list)  # avisos del extractor (revisión humana)
    _raw: list = field(default_factory=list, repr=False)  # [(label|None, [valores])]

    def como_niveles(self) -> dict[str, dict]:
        """Devuelve {nivel: fila} para alimentar los generadores."""
        return {f["nivel"]: f for f in self.filas}

    def __repr__(self) -> str:  # noqa: D105
        return (f"<TablaSalarial anio={self.anio} perfil={self.perfil} "
                f"niveles={len(self.filas)} pie={list(self.pie)}>")


def _numero(texto: str) -> float | None:
    """'3.310,51' (formato español) -> float. None si no es número."""
    t = texto.strip()
    if not re.fullmatch(r"-?[\d.]+,\d+", t) and not re.fullmatch(r"-?\d+", t):
        return None
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _lineas_pagina(pagina) -> list[tuple[float, list]]:
    palabras = pagina.extract_words(x_tolerance=1.5, y_tolerance=2)
    lineas: dict[int, list] = defaultdict(list)
    for w in palabras:
        lineas[round(w["top"])].append(w)
    return [(top, sorted(lineas[top], key=lambda w: w["x0"])) for top in sorted(lineas)]


def _texto_linea(ws) -> str:
    return " ".join(w["text"] for w in ws)


def _label_y_valores(txt: str) -> tuple[str | None, list]:
    """
    Separa el rótulo de nivel y la lista de valores de una línea.
    - Romano: rótulo = el romano; valores = números siguientes.
    - Arábigo "N. Nombre": rótulo = texto hasta el primer número/guion; valores
      = números ('-' se conserva como None para no descuadrar columnas).
    Devuelve (None, [...]) si la línea no empieza por un nivel reconocible.
    """
    tokens = txt.split()
    if not tokens:
        return None, []

    if _RE_NIVEL_ROMANO.match(txt):
        return tokens[0], [n for t in tokens[1:] if (n := _numero(t)) is not None]

    if _RE_NIVEL_ARABIGO.match(txt):
        # Un importe lleva SIEMPRE coma decimal (65,71 / 2.448,37). Los enteros
        # sueltos ("14.", la edad "17 años") son parte del rótulo, no importes.
        def es_valor(t: str) -> bool:
            return t == "-" or ("," in t and _numero(t) is not None)

        label_toks, valores, en_valores = [], [], False
        for t in tokens:
            if not en_valores:
                if es_valor(t):
                    en_valores = True
                else:
                    label_toks.append(t)
                    continue
            if t == "-":
                valores.append(None)            # celda vacía: conserva la columna
            elif _numero(t) is not None:
                valores.append(_numero(t))
            # cualquier otro token dentro de la zona de valores se ignora
        return " ".join(label_toks), valores

    return None, []


def _detectar_perfil(labels: list[str]) -> str:
    if not labels:
        return "generico"
    romanos = sum(1 for l in labels if l in NIVELES_ROMANOS)
    arabigos = sum(1 for l in labels if re.match(r"^\d{1,2}\.", l))
    if romanos >= max(1, len(labels) // 2):
        return "construccion"
    if arabigos >= max(1, len(labels) // 2):
        return "metal"
    return "generico"


def _nombres_columnas(perfil: str, n: int) -> list[str]:
    base = {"construccion": COLUMNAS_CONSTRUCCION, "metal": COLUMNAS_METAL}.get(perfil, [])
    return [base[i] if i < len(base) else f"col_{i + 1}" for i in range(n)]


def _parsear_pie(texto_pie: str) -> dict:
    def cap(rx):
        m = rx.search(texto_pie)
        return _numero(m.group(1)) if m else None
    pie = {
        "plus_mixto_extrasalarial": cap(_RE_PIE_PLUS_MIXTO),
        "dieta": cap(_RE_PIE_DIETA),
        "media_dieta": cap(_RE_PIE_MEDIA_DIETA),
        "kilometraje": cap(_RE_PIE_KM),
    }
    return {k: v for k, v in pie.items() if v is not None}


def _construir_filas(tabla: TablaSalarial) -> None:
    """Tras recoger _raw, detecta perfil, fusiona continuaciones y nombra columnas."""
    labels = [lab for lab, _ in tabla._raw if lab is not None]
    tabla.perfil = _detectar_perfil(labels)

    filas_valores: list[tuple[str, list]] = []
    for lab, valores in tabla._raw:
        if lab is not None:
            filas_valores.append((lab, list(valores)))
        elif (tabla.perfil == "construccion" and filas_valores
              and len(filas_valores[-1][1]) < len(COLUMNAS_CONSTRUCCION)):
            # continuación: Retri.Anual / plan pensiones partidos en línea aparte
            # (solo Construcción, y solo mientras la fila previa esté incompleta)
            filas_valores[-1][1].extend(valores)
        # en otros perfiles, las líneas sin rótulo son pie/ruido y se ignoran

    n_cols = max((len(v) for _, v in filas_valores), default=0)
    tabla.columnas = _nombres_columnas(tabla.perfil, n_cols)
    for lab, valores in filas_valores:
        fila = {"nivel": lab, "_n_valores": len(valores)}
        for i, valor in enumerate(valores):
            fila[tabla.columnas[i] if i < len(tabla.columnas) else f"col_{i + 1}"] = valor
        tabla.filas.append(fila)


def extraer(ruta_pdf: str) -> list[TablaSalarial]:
    """Extrae todas las tablas salariales (una por año) de un PDF del BOPA."""
    tablas: dict[int, TablaSalarial] = {}
    pie_buffer: dict[int, list[str]] = {}

    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            lineas = _lineas_pagina(pagina)

            cabeceras: list[tuple[float, int]] = []
            for top, ws in lineas:
                txt = _texto_linea(ws)
                if re.match(r"\s*SOBRE\s+TABLA", txt, re.IGNORECASE):
                    continue
                m = _RE_HEADER_ANIO.search(txt)
                if m:
                    cabeceras.append((top, int(m.group(1))))
            if not cabeceras:
                continue

            for top, ws in lineas:
                anio = None
                for h_top, h_anio in cabeceras:
                    if top >= h_top:
                        anio = h_anio
                if anio is None:
                    continue
                txt = _texto_linea(ws)
                tabla = tablas.setdefault(anio, TablaSalarial(anio=anio, titulo=f"AÑO {anio}"))
                label, valores = _label_y_valores(txt)
                if label is not None:
                    tabla._raw.append((label, valores))
                elif _RE_PIE_ROTULO.search(txt):
                    pie_buffer.setdefault(anio, []).append(txt)
                elif any(_numero(w["text"]) is not None for w in ws):
                    # posible continuación (se resolverá según perfil en _construir_filas)
                    nums = [n for w in ws if (n := _numero(w["text"])) is not None]
                    tabla._raw.append((None, nums))

    for tabla in tablas.values():
        _construir_filas(tabla)
    for anio, lineas_pie in pie_buffer.items():
        if anio in tablas:
            tablas[anio].pie.update(_parsear_pie(" ".join(lineas_pie)))

    return [tablas[a] for a in sorted(tablas)]


if __name__ == "__main__":
    import sys

    ruta = sys.argv[1] if len(sys.argv) > 1 else "33029708.pdf"
    tablas = extraer(ruta)
    if not tablas:
        print("No se detectó ninguna tabla salarial en el PDF.")
    for tabla in tablas:
        print(f"\n===== {tabla.titulo}  perfil={tabla.perfil}  "
              f"({len(tabla.filas)} niveles)  pie={tabla.pie} =====")
        print(f"  columnas: {tabla.columnas}")
        for fila in tabla.filas:
            n = fila.get("_n_valores", "?")
            campos = "  ".join(f"{k}={v}" for k, v in fila.items()
                                if k not in ("nivel", "_n_valores"))
            print(f"  {fila['nivel']:<28} [{n}]  {campos}")
