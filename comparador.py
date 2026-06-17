"""
Comparador: cruza los importes extraídos del PDF con los de un SQL de referencia
(el que entrega Wolters Kluwer) y devuelve las DISCREPANCIAS.

Es la función de mayor valor de la herramienta: detecta errores como el del Plus
Extrasalarial 2026, que WK cargó a 3,06 € (valor de 2025) en lugar de 3,15 €.

No decide quién tiene razón: marca las diferencias para que una persona las revise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from generador_sql import (
    CONCEPTO_A_COLUMNA,
    _RE_CLASSIF_CONCEPT,
    _mapa_categoria_nivel,
)

# Nombre legible de cada concepto a3nom.
NOMBRE_CONCEPTO = {
    "001": "Salario Base",
    "006": "Plus Asistencia",
    "010": "Vacaciones",
    "101": "Paga Verano",
    "102": "Paga Navidad",
    "399": "Plus Extrasalarial",
}
# Tolerancia de redondeo al comparar importes (céntimos).
TOLERANCIA = 0.005


@dataclass
class Discrepancia:
    concepto: str          # código a3nom (p.ej. '399')
    nombre: str            # 'Plus Extrasalarial'
    nivel: str             # nivel o '(todos)'
    valor_sql: float       # importe en el SQL de WK
    valor_pdf: float       # importe extraído del PDF
    n_categorias: int      # a cuántas categorías afecta
    nota: str = ""

    @property
    def diferencia(self) -> float:
        return round(self.valor_pdf - self.valor_sql, 4)


def _amounts_por_categoria(sql: str) -> dict[str, dict[str, float]]:
    """{classification_code: {concept_code: amount}} desde el SQL de referencia."""
    out: dict[str, dict[str, float]] = {}
    for m in _RE_CLASSIF_CONCEPT.finditer(sql):
        concepto, clazz, importe = m.group(2), m.group(3), float(m.group(4))
        out.setdefault(clazz, {})[concepto] = importe
    return out


def comparar(
    sql_referencia: str,
    niveles: dict[str, dict],
    *,
    plus_extrasalarial: float | None = None,
) -> list[Discrepancia]:
    """
    Compara el SQL de referencia con los importes del PDF (por nivel) y el plus
    extrasalarial del pie de tabla. Agrupa discrepancias idénticas (mismo concepto,
    nivel, par de valores) para no repetir 60 veces la misma.
    """
    amounts = _amounts_por_categoria(sql_referencia)
    cat_nivel = _mapa_categoria_nivel(sql_referencia, niveles)

    # acumulador: (concepto, nivel, valor_sql, valor_pdf) -> nº categorías
    acc: dict[tuple, int] = {}

    for clazz, conceptos in amounts.items():
        nivel = cat_nivel.get(clazz)
        for concepto, valor_sql in conceptos.items():
            if concepto == "399":
                valor_pdf = plus_extrasalarial
                nivel_etq = "(todos)"
            else:
                col = CONCEPTO_A_COLUMNA.get(concepto)
                if col is None or nivel is None:
                    continue  # concepto no mapeado o categoría especial
                valor_pdf = niveles[nivel].get(col)
                nivel_etq = nivel
            if valor_pdf is None:
                continue
            if abs(valor_pdf - valor_sql) > TOLERANCIA:
                clave = (concepto, nivel_etq, round(valor_sql, 2), round(valor_pdf, 2))
                acc[clave] = acc.get(clave, 0) + 1

    discrepancias = [
        Discrepancia(
            concepto=c, nombre=NOMBRE_CONCEPTO.get(c, c), nivel=niv,
            valor_sql=vs, valor_pdf=vp, n_categorias=n,
        )
        for (c, niv, vs, vp), n in sorted(acc.items())
    ]
    return discrepancias


if __name__ == "__main__":
    import sys
    from extractor import extraer

    ruta_pdf = sys.argv[1] if len(sys.argv) > 1 else "33029708.pdf"
    ruta_ref = sys.argv[2] if len(sys.argv) > 2 else "IV332978.SQL"
    anio = int(sys.argv[3]) if len(sys.argv) > 3 else 2026

    sql = open(ruta_ref, encoding="latin-1").read().replace("\r\n", "\n")
    tabla = next(t for t in extraer(ruta_pdf) if t.anio == anio)
    pe = tabla.pie.get("plus_mixto_extrasalarial")

    disc = comparar(sql, tabla.como_niveles(), plus_extrasalarial=pe)
    if not disc:
        print(f"Sin discrepancias entre el PDF (año {anio}) y el SQL de referencia.")
    else:
        print(f"{len(disc)} discrepancia(s) PDF (año {anio}) vs SQL de referencia:\n")
        for d in disc:
            print(f"  [{d.concepto} {d.nombre}] nivel {d.nivel}: "
                  f"SQL={d.valor_sql} | PDF={d.valor_pdf} | dif={d.diferencia:+} "
                  f"({d.n_categorias} categoría/s)")
