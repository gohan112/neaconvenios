"""
NeaConvenios — app web (Streamlit) para importar convenios a a3nom
(Wolters Kluwer) y al módulo de obras de Nea Master.

El PDF puede venir de cualquier boletín oficial (BOE, BOPA u otro autonómico):
la estructura de las tablas es equivalente.

Estructura:
  1. Eliges arriba qué quieres generar: «Módulo de obras» o «a3nom».
     - Módulo de obras: solo pide el PDF del convenio.
     - a3nom: pide el PDF del convenio + el SQL de referencia de WK (plantilla).
  2. Se lee el PDF (automático, o con Claude Opus 4.8 para formatos nuevos).
  3. Revisas/corriges los importes y descargas el Excel o el SQL.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import base64
import os
import tempfile

import pandas as pd
import streamlit as st

from comparador import comparar
from extractor import extraer
from generador_excel import CabeceraConvenio, generar_excel
from generador_sql import cobertura_mapeo, generar

ROJO = "#CC0C18"
_ICONO = "assets/neamaster_icono.png" if os.path.exists("assets/neamaster_icono.png") else "📄"
st.set_page_config(page_title="NeaConvenios", page_icon=_ICONO, layout="wide")


def _logo_b64() -> str | None:
    ruta = "assets/neamaster_horizontal.png"
    if os.path.exists(ruta):
        return base64.b64encode(open(ruta, "rb").read()).decode()
    return None


# ------------------------------------------------------------------ Cabecera
_logo = _logo_b64()
_img = f'<img src="data:image/png;base64,{_logo}" style="height:44px;" alt="Nea Master"/>' if _logo else ""
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:16px; padding:4px 0 12px;
                border-bottom:3px solid {ROJO}; margin-bottom:20px;">
      {_img}
      <div style="font-size:24px; font-weight:600; color:#2C2C2A; letter-spacing:-0.3px;">
        Nea<span style="color:{ROJO};">Convenios</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Sube el PDF del convenio (BOE, BOPA u otro boletín oficial) y genera el Excel "
    "del módulo de obras o el SQL "
    "para a3nom. Revisa siempre los importes antes de usarlos: alimentan nóminas."
)


def _guardar_temporal(archivo) -> str:
    sufijo = "." + archivo.name.rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as tmp:
        tmp.write(archivo.getbuffer())
        return tmp.name


def _leer_sql(archivo) -> str:
    """a3nom usa latin-1; si lo guardaron en UTF-8 lo detectamos. Sin mojibake."""
    datos = archivo.getvalue()
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        texto = datos.decode("latin-1")
    return texto.replace("\r\n", "\n")


# ============================================================ 1. Elegir destino
modo = st.segmented_control(
    "¿Qué quieres generar?",
    options=["📊 Módulo de obras", "🗄️ a3nom"],
    default="📊 Módulo de obras",
)
if not modo:
    st.info("Elige arriba qué quieres generar.")
    st.stop()
es_obras = "obras" in modo

# ============================================================ 2. Subida (según destino)
if es_obras:
    st.caption("Para el módulo de obras solo necesitas el PDF del convenio.")
    pdf_file = st.file_uploader("PDF del convenio (tablas salariales)", type=["pdf"])
    sql_ref_file = None
else:
    st.caption("Para a3nom necesitas el PDF del convenio y el SQL que ya tengas de ese "
               "convenio (de WK o exportado de a3nom) como plantilla.")
    c1, c2 = st.columns(2)
    with c1:
        pdf_file = st.file_uploader("1) PDF del convenio (tablas salariales)", type=["pdf"])
    with c2:
        sql_ref_file = st.file_uploader("2) SQL de referencia del mismo convenio", type=["sql", "txt"])

# Opción de lectura (visible siempre, antes y después de subir el PDF).
usar_claude = st.checkbox(
    "🤖 Leer el PDF con Claude Opus 4.8",
    value=False,
    help="Útil para convenios con un formato que el lector automático no reconoce. "
         "Requiere ANTHROPIC_API_KEY en el servidor. Revisa SIEMPRE los importes.",
)

if not pdf_file:
    st.info("Sube el PDF para empezar.")
    st.stop()

# ============================================================ 3. Extracción
ruta_pdf = _guardar_temporal(pdf_file)
try:
    if usar_claude:
        from extractor_claude import extraer_con_claude
        with st.spinner("Leyendo el PDF con Claude…"):
            tablas = extraer_con_claude(ruta_pdf)
    else:
        tablas = extraer(ruta_pdf)
except Exception as exc:  # noqa: BLE001 — mostrar el error, no tragarlo
    st.error(f"No se pudo leer el PDF: {exc}")
    st.stop()

if not tablas:
    st.error(
        "No se detectó ninguna tabla salarial en el PDF. Si el formato es distinto al "
        "habitual, prueba a marcar «Leer el PDF con Claude Opus 4.8»."
    )
    st.stop()

anios = [t.anio for t in tablas]
anio_sel = st.selectbox("Año a importar", anios, index=len(anios) - 1)
tabla = next(t for t in tablas if t.anio == anio_sel)

st.success(f"Tabla {anio_sel} extraída: {len(tabla.filas)} niveles · perfil: **{tabla.perfil}**.")
if tabla.nota_vigencia:
    st.info(f"Subtítulo de la tabla: «{tabla.nota_vigencia}». Confirma que es la que aplica.")
if tabla.perfil == "generico":
    st.warning(
        "Formato no reconocido: las columnas salen como 'col_1, col_2…'. Puedes revisar "
        "los números, pero el SQL necesita mapear las columnas a conceptos de a3nom."
    )
if tabla.avisos:
    with st.expander(f"⚠️ {len(tabla.avisos)} aviso(s) de revisión — míralos antes de generar", expanded=True):
        for aviso in tabla.avisos:
            st.write(f"• {aviso}")

# ============================================================ 4. Revisión
st.subheader("Revisión de importes")
st.caption("⚠️ Revisa y corrige antes de generar. La extracción automática del PDF puede fallar.")
cols_presentes = [c for c in tabla.columnas if any(c in f for f in tabla.filas)]
df = pd.DataFrame(
    [{"nivel": f["nivel"], **{c: f.get(c) for c in cols_presentes}} for f in tabla.filas]
)
df_edit = st.data_editor(df, use_container_width=True, hide_index=True, key="tabla_niveles")
niveles_edit: dict[str, dict] = {}
for _, fila in df_edit.iterrows():
    d = {c: (None if pd.isna(fila[c]) else float(fila[c])) for c in cols_presentes}
    d["nivel"] = fila["nivel"]
    niveles_edit[fila["nivel"]] = d

# ============================================================ 5a. Módulo de obras
if es_obras:
    st.subheader("📊 Excel para el módulo de obras")
    st.caption(
        "⚠️ CODCONVE, nombre, días y tipo de vacaciones son datos de CABECERA del convenio "
        "(su articulado), NO salen del PDF. Rellénalos/confírmalos. La tabla salarial sí sale del PDF."
    )
    cod = st.number_input("CODCONVE", value=1, step=1)
    nombre = st.text_input("NOMCONVE", value="", placeholder="Nombre del convenio")
    tipo_vac = st.selectbox(
        "Tipo de días (VACALABORABLES)", ["Naturales (F)", "Laborables (T)"], index=0,
        help="Solo escribe 'F' o 'T' en esa columna; no genera un Excel distinto. "
             "Es lo que cuenta el convenio en su artículo de vacaciones.",
    )
    vac_lab = "T" if tipo_vac.startswith("Laborables") else "F"
    dias_vac = st.number_input(
        "DIASVACACIONES", value=30, step=1,
        help="Según el convenio. Naturales suele ser 30; laborables varía (Metal 22, Construcción 21).",
    )
    if not nombre.strip():
        st.caption("Escribe el nombre del convenio antes de generar.")
    elif st.button("Generar Excel", type="primary", use_container_width=True):
        cab = CabeceraConvenio(
            cod_conve=int(cod), nom_conve=nombre, anyo=anio_sel,
            dias_vacaciones=int(dias_vac), vac_laborables=vac_lab,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            generar_excel(tmp.name, cab, niveles_edit)
            tmp.seek(0)
            datos = open(tmp.name, "rb").read()
        st.download_button(
            "⬇️ Descargar .xlsx", data=datos,
            file_name=f"convenio_{anio_sel}_obras.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ============================================================ 5b. a3nom (SQL)
else:
    st.subheader("🗄️ SQL para a3nom (SQL Server)")
    sql_ref = _leer_sql(sql_ref_file) if sql_ref_file else None

    pie = dict(tabla.pie)
    pc1, pc2, pc3, pc4 = st.columns(4)
    plus_extra = pc1.number_input(
        "Plus Extrasalarial (€/día)", value=float(pie.get("plus_mixto_extrasalarial", 0.0) or 0.0),
        step=0.01, format="%.4f", help="Concepto 399, propio del convenio de Construcción.",
    )
    pc2.number_input("Dieta (€)", value=float(pie.get("dieta", 0.0) or 0.0), step=0.01, format="%.2f", key="dieta")
    pc3.number_input("½ Dieta (€)", value=float(pie.get("media_dieta", 0.0) or 0.0), step=0.01, format="%.2f", key="media_dieta")
    pc4.number_input("Kilometraje (€/km)", value=float(pie.get("kilometraje", 0.0) or 0.0), step=0.0001, format="%.4f", key="km")

    ref_coincide = False
    if sql_ref:
        casadas, total_ref = cobertura_mapeo(sql_ref, niveles_edit)
        ratio = casadas / total_ref if total_ref else 0.0
        ref_coincide = ratio >= 0.6
        if not ref_coincide:
            st.error(
                f"⛔ El SQL de referencia NO parece corresponder a este convenio/año: solo casan "
                f"{casadas} de {total_ref} categorías. Revisa que sea el MISMO convenio y el año correcto."
            )

    if sql_ref and ref_coincide:
        st.markdown("**🔍 Discrepancias frente al SQL de referencia**")
        try:
            disc = comparar(sql_ref, niveles_edit, plus_extrasalarial=plus_extra)
        except Exception as exc:  # noqa: BLE001
            st.warning(f"No se pudo comparar: {exc}")
            disc = []
        if not disc:
            st.success("Sin discrepancias: el PDF coincide con el SQL de referencia.")
        else:
            st.warning(f"{len(disc)} discrepancia(s). Revísalas: puede ser error del SQL de WK o de extracción.")
            st.dataframe(
                pd.DataFrame([{
                    "Concepto": f"{d.concepto} {d.nombre}", "Nivel": d.nivel,
                    "Valor SQL (WK)": d.valor_sql, "Valor PDF": d.valor_pdf,
                    "Diferencia": d.diferencia, "Nº categorías": d.n_categorias,
                } for d in disc]),
                use_container_width=True, hide_index=True,
            )

    aplicar_pe = st.checkbox(
        "Actualizar también el Plus Extrasalarial (399) con el valor del pie", value=True,
        help="Solo aplica a convenios con concepto 399 (Construcción).",
    )
    if not sql_ref:
        st.info("Sube el SQL de referencia (arriba) para comparar y generar el SQL de a3nom.")
    elif not ref_coincide:
        st.caption("El SQL de referencia no corresponde a este convenio/año (ver aviso arriba).")
    elif st.button("Generar SQL", type="primary", use_container_width=True):
        try:
            res = generar(
                sql_ref, niveles_edit, anio=anio_sel,
                plus_extrasalarial=plus_extra if aplicar_pe else None,
            )
            for aviso in res.avisos:
                st.caption(f"• {aviso}")
            st.download_button(
                "⬇️ Descargar .SQL", data=res.sql.encode("latin-1", errors="replace"),
                file_name=f"convenio_{anio_sel}.sql", mime="text/plain",
                use_container_width=True,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo generar el SQL: {exc}")
