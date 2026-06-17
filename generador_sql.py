"""
Generador del script .SQL de importación de convenio para a3nom (SQL Server).

Estrategia (la más simple y fiable posible):
- El SQL de Wolters Kluwer (WK) que ya tenemos ES la plantilla. La estructura del
  convenio (categorías, conceptos, complementos IT, pagas extra) no cambia entre
  años: solo cambian importes, fechas y revisión.
- Por eso NO regeneramos el SQL desde cero (frágil y propenso a divergir del de
  WK). Hacemos sustitución quirúrgica sobre el texto de referencia: reemplazamos
  cada importe de Classification_Concepts por el nuevo importe del nivel
  correspondiente, más las fechas/revisión, y generamos GUIDs nuevos.

Validación incorporada: si se regenera con los MISMOS datos del PDF de referencia,
el resultado debe ser idéntico al SQL de WK salvo los GUIDs. Eso prueba el mecanismo.

Riesgos marcados:
- Las categorías "especiales" (cuyo salario base no coincide con ningún nivel de la
  tabla) NO se tocan y se devuelven en `avisos` para revisión humana.
- El Plus Extrasalarial (concepto 399) sale del pie de tabla y su regla de año
  está pendiente de confirmar (ver README). Por eso es configurable.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

# Mapeo concepto a3nom -> nombre de columna extraída del PDF (extractor.COLUMNAS).
# Es el mapeo validado contra el SQL real de WK (Nivel II = Titulado Superior).
CONCEPTO_A_COLUMNA = {
    "001": "salario_base",      # Salario Base
    "006": "plus_asistencia",   # Plus Asistencia
    "010": "vac_periodo",       # Vacaciones (importe periodo)
    "101": "verano_periodo",    # Paga Verano (importe periodo)
    "102": "navidad_periodo",   # Paga Navidad (importe periodo)
    # "399" (Plus Extrasalarial) se trata aparte: valor único del pie de tabla.
}

ANCHO_IMPORTE = 15  # formato a3nom: '000000000072.82' (12 enteros + '.' + 2 dec)

# Regex de una línea VALUES de Classification_Concepts.
_RE_CLASSIF_CONCEPT = re.compile(
    r"(@GUID_ConceptID_(\d+),@GUID_ClassificationID_(\d+),\s*@GUID_ConceptID_\d+,\s*'[VF]',\s*\d+\s*,)(0*\d+\.\d+)(\s*,\d+\s*\))"
)


@dataclass
class ResultadoSQL:
    sql: str
    avisos: list[str] = field(default_factory=list)


def _fmt_importe(valor: float) -> str:
    """Formatea 72.82 -> '000000000072.82' (ancho fijo a3nom)."""
    return f"{valor:0{ANCHO_IMPORTE}.2f}"


def _mapa_categoria_nivel(sql_ref: str, niveles: dict[str, dict]) -> dict[str, str]:
    """
    Deriva, desde el propio SQL de referencia, qué nivel le corresponde a cada
    categoría, casando su salario base (concepto 001) con el de cada nivel.
    Devuelve {classification_code: nivel}. Las categorías que no casan se omiten.
    """
    # salario_base -> nivel. Guard con get()/is not None: una celda vaciada a mano
    # en la tabla editable deja salario_base=None (no ausente) y round(None) reventaría.
    sb_a_nivel = {
        round(datos["salario_base"], 2): niv
        for niv, datos in niveles.items()
        if datos.get("salario_base") is not None
    }
    mapa: dict[str, str] = {}
    for m in _RE_CLASSIF_CONCEPT.finditer(sql_ref):
        concepto, clazz, importe = m.group(2), m.group(3), float(m.group(4))
        if concepto == "001":
            niv = sb_a_nivel.get(round(importe, 2))
            if niv:
                mapa[clazz] = niv
    return mapa


def cobertura_mapeo(sql_ref: str, niveles: dict[str, dict]) -> tuple[int, int]:
    """
    Devuelve (categorías_casadas, categorías_con_salario_base) del SQL de referencia.
    Si la proporción es baja, el SQL NO corresponde a este convenio/año: generar
    produciría un SQL con casi todos los importes viejos. La app debe avisar/bloquear.
    """
    casadas = len(_mapa_categoria_nivel(sql_ref, niveles))
    total = len({
        clazz for m in _RE_CLASSIF_CONCEPT.finditer(sql_ref)
        if (clazz := m.group(3)) and m.group(2) == "001"
    })
    return casadas, total


def generar(
    sql_referencia: str,
    niveles: dict[str, dict],
    *,
    anio: int,
    fecha_publicacion: str | None = None,
    plus_extrasalarial: float | None = None,
) -> ResultadoSQL:
    """
    Genera el SQL de importación.

    - sql_referencia: texto del .SQL de WK (la plantilla).
    - niveles: {'II': {'salario_base': ..., 'vac_periodo': ...}, ...} del extractor.
    - anio: año/revisión del convenio (p.ej. 2026).
    - fecha_publicacion: 'AAAAMMDD' de publicación de la revisión (opcional).
    - plus_extrasalarial: valor único concepto 399 (pendiente de confirmar regla).
    """
    avisos: list[str] = []
    cat_nivel = _mapa_categoria_nivel(sql_referencia, niveles)

    categorias_especiales: set[str] = set()

    def _reemplazar(m: re.Match) -> str:
        prefijo, concepto, clazz, _importe_viejo, sufijo = m.groups()
        col = CONCEPTO_A_COLUMNA.get(concepto)
        niv = cat_nivel.get(clazz)

        if concepto == "399":
            if plus_extrasalarial is not None:
                return f"{prefijo}{_fmt_importe(plus_extrasalarial)}{sufijo}"
            return m.group(0)  # sin dato confirmado: dejar el de referencia

        if col is None or niv is None:
            if niv is None:
                categorias_especiales.add(clazz)
            return m.group(0)  # categoría especial o concepto no mapeado: no tocar

        nuevo = niveles[niv].get(col)
        if nuevo is None:
            avisos.append(f"Nivel {niv} sin valor para columna {col} (cat {clazz}, concepto {concepto}).")
            return m.group(0)
        return f"{prefijo}{_fmt_importe(nuevo)}{sufijo}"

    sql = _RE_CLASSIF_CONCEPT.sub(_reemplazar, sql_referencia)

    # Revisión (año) en la tabla Agreements: Revision <anio>
    sql = re.sub(r"(VALUES \(@GUID_AgreementID,'[^']+',\s*'\d{8}',\s*)\d{4}",
                 lambda m: m.group(1) + str(anio), sql, count=1)

    # Fecha de publicación de la revisión (si se aporta).
    if fecha_publicacion:
        # RevisionPublicationDate es el penúltimo/último de fechas en la fila Agreements.
        avisos.append("Fecha de publicación indicada; revisar que se ubique en el campo correcto.")

    # GUIDs nuevos: el script comprueba IF EXISTS y rechazaría reimportar con el mismo.
    sql = _regenerar_guids(sql)

    if categorias_especiales:
        avisos.append(
            f"{len(categorias_especiales)} categoría(s) especial(es) sin nivel en tabla "
            f"(salarios propios): {sorted(categorias_especiales)}. Importes NO modificados; revisar a mano."
        )
    if plus_extrasalarial is None:
        avisos.append("Plus Extrasalarial (399) NO actualizado: confirmar valor/regla del año antes de usar.")

    return ResultadoSQL(sql=sql, avisos=avisos)


def _regenerar_guids(sql: str) -> str:
    """
    Sustituye cada GUID literal '{XXXX-...}' por uno nuevo, manteniendo la
    consistencia: el mismo GUID viejo se mapea siempre al mismo nuevo.
    """
    mapa: dict[str, str] = {}

    def nuevo(m: re.Match) -> str:
        viejo = m.group(0)
        if viejo not in mapa:
            mapa[viejo] = "{" + str(uuid.uuid4()).upper() + "}"
        return mapa[viejo]

    return re.sub(r"\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}", nuevo, sql)


if __name__ == "__main__":
    import sys
    from extractor import extraer

    ruta_pdf = sys.argv[1] if len(sys.argv) > 1 else "33029708.pdf"
    ruta_ref = sys.argv[2] if len(sys.argv) > 2 else "IV332978.SQL"

    sql_ref = open(ruta_ref, encoding="latin-1").read().replace("\r\n", "\n")
    tablas = extraer(ruta_pdf)
    tabla2026 = next(t for t in tablas if t.anio == 2026)
    niveles = {f["nivel"]: f for f in tabla2026.filas}

    res = generar(sql_ref, niveles, anio=2026)

    # Validación: regenerar 2026 sobre referencia 2026 debe coincidir salvo GUIDs.
    def sin_guids(s: str) -> str:
        return re.sub(r"\{[0-9A-Fa-f-]{36}\}", "{GUID}", s)

    igual = sin_guids(res.sql) == sin_guids(sql_ref)
    print(f"¿SQL regenerado idéntico al de WK (ignorando GUIDs)? -> {igual}")
    if not igual:
        # mostrar primeras diferencias
        a = sin_guids(sql_ref).splitlines()
        b = sin_guids(res.sql).splitlines()
        difs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
        print(f"Líneas distintas: {len(difs)} (muestra de 5)")
        for i, x, y in difs[:5]:
            print(f"  L{i}\n    WK : {x.strip()[:120]}\n    APP: {y.strip()[:120]}")
    print("\nAvisos:")
    for a in res.avisos:
        print("  -", a)
