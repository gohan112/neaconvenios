"""
Generador del Excel para el módulo de obras (y otros programas internos).

El módulo de obras importa una fila por convenio con parámetros de cabecera
(no las tablas salariales). Formato indicado por el cliente:

  CODCONVE  NOMCONVE  ANYO  JORNADAACTUAL  DIASVACACIONES  VACALABORABLES
  PORCCOSTE  PORCCOMPANYO  PORCCOMPANYOPASADO  PORSAB  PORFEST

Origen de cada campo:
- CODCONVE / NOMCONVE / ANYO       -> del convenio y del PDF (revisión).
- JORNADAACTUAL / DIASVACACIONES   -> de la tabla Agreements del SQL (o manual).
- VACALABORABLES                   -> 'T' (días laborables) por defecto.
- PORC* / PORSAB / PORFEST         -> porcentajes de coste; manuales (0 por defecto).

Se añade además una segunda hoja con la tabla salarial completa por nivel, útil
para otros consumos aunque el módulo de obras solo lea la primera.
"""

from __future__ import annotations

from dataclasses import dataclass

from openpyxl import Workbook

COLUMNAS_OBRAS = [
    "CODCONVE", "NOMCONVE", "ANYO", "JORNADAACTUAL", "DIASVACACIONES",
    "VACALABORABLES", "PORCCOSTE", "PORCCOMPANYO", "PORCCOMPANYOPASADO",
    "PORSAB", "PORFEST",
]


@dataclass
class CabeceraConvenio:
    cod_conve: int
    nom_conve: str
    anyo: int
    jornada_actual: float = 0
    dias_vacaciones: int = 20
    vac_laborables: str = "T"
    porc_coste: float = 0
    porc_companyo: float = 0
    porc_companyo_pasado: float = 0
    por_sab: float = 0
    por_fest: float = 0

    def fila(self) -> list:
        return [
            self.cod_conve, self.nom_conve, self.anyo, self.jornada_actual,
            self.dias_vacaciones, self.vac_laborables, self.porc_coste,
            self.porc_companyo, self.porc_companyo_pasado, self.por_sab, self.por_fest,
        ]


def generar_excel(
    ruta_salida: str,
    cabecera: CabeceraConvenio,
    niveles: dict[str, dict] | None = None,
) -> str:
    """Crea el .xlsx. Devuelve la ruta del archivo escrito."""
    wb = Workbook()

    # --- Hoja 1: cabecera para el módulo de obras ---
    ws = wb.active
    ws.title = "Convenio"
    ws.append(COLUMNAS_OBRAS)
    ws.append(cabecera.fila())

    # --- Hoja 2: tabla salarial por nivel (consumo general) ---
    if niveles:
        ws2 = wb.create_sheet("TablaSalarial")
        # cabecera dinámica a partir de las claves de la primera fila
        claves = [k for k in next(iter(niveles.values())).keys()
                  if not k.startswith("_") and k != "nivel"]
        ws2.append(["Nivel"] + claves)
        for niv, datos in niveles.items():
            ws2.append([niv] + [datos.get(k) for k in claves])

    wb.save(ruta_salida)
    return ruta_salida


if __name__ == "__main__":
    import sys
    from extractor import extraer

    ruta_pdf = sys.argv[1] if len(sys.argv) > 1 else "33029708.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "convenio_obras.xlsx"

    tablas = extraer(ruta_pdf)
    tabla = next(t for t in tablas if t.anio == 2026)
    niveles = {f["nivel"]: f for f in tabla.filas}

    cab = CabeceraConvenio(
        cod_conve=1,
        nom_conve="CONSTRUCCIÓN Y OBRAS PÚBLICAS - ASTURIAS",
        anyo=tabla.anio,
        dias_vacaciones=20,
    )
    ruta = generar_excel(salida, cab, niveles)
    print(f"Excel generado: {ruta}")
    print(f"  Hoja 'Convenio': 1 fila de cabecera ({len(COLUMNAS_OBRAS)} columnas)")
    print(f"  Hoja 'TablaSalarial': {len(niveles)} niveles")
