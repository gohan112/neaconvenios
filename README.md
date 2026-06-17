# Convenios BOPA → a3nom

Herramienta para importar convenios colectivos publicados en el BOPA al programa
de nóminas **a3nom** (Wolters Kluwer), generando el `.SQL` de importación y un
`.xlsx` para el módulo de obras.

## Idea

La **estructura** de un convenio (categorías, conceptos, complementos, pagas) casi
no cambia entre años: vive en el **convenio base** y en el **SQL de referencia** de
WK. Lo único que cambia cada año son los **importes**, que están en el último PDF
de tablas del BOPA. La herramienta:

1. Lee los importes del PDF.
2. Los inyecta en el SQL de referencia (plantilla) → genera el SQL nuevo.
3. Compara PDF vs SQL de WK y **avisa de discrepancias** (p.ej. detecta que WK
   cargó el Plus Extrasalarial 2026 a 3,06 € cuando debía ser 3,15 €).
4. Genera el Excel para el módulo de obras.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso (app web)

```bash
streamlit run app.py
```

Sube el PDF del BOPA y, recomendado, el SQL de referencia de WK del mismo convenio.

## Uso por línea de comandos

```bash
python3 extractor.py   <pdf>                      # ver tablas extraídas
python3 comparador.py  <pdf> <sql_ref> <año>      # ver discrepancias
python3 generador_sql.py  <pdf> <sql_ref>         # validar SQL contra WK
python3 generador_excel.py <pdf> <salida.xlsx>    # generar Excel
```

## Módulos

| Archivo | Función |
|---|---|
| `extractor.py` | PDF del BOPA → tablas salariales por nivel + pie (plus mixto, dietas, km) |
| `comparador.py` | Cruza importes PDF vs SQL de WK y devuelve discrepancias |
| `generador_sql.py` | Plantilla SQL de WK + importes del PDF → `.SQL` nuevo (GUIDs regenerados) |
| `generador_excel.py` | Importes → `.xlsx` para el módulo de obras |
| `app.py` | Interfaz web (Streamlit) que une todo lo anterior |

## Alcance y límites

- **Soporta** el formato actual del BOPA (cabecera "TABLA SALARIAL AÑO XXXX"). Si el
  BOPA cambia de maquetación, hay que ajustar `extractor.py`.
- **Genera solo el `.SQL`** (a3nom sobre SQL Server). Los ficheros binarios
  `.DAT/.IDX` (a3nom de ficheros, formato propietario Micro Focus de WK) **no** se
  generan: son fuera de alcance por su complejidad y riesgo.
- Hay reglas que solo están en el **convenio base** (p.ej. el salario de los
  contratos de formación = % del Nivel IX). La plantilla por convenio debe
  codificarlas una vez; no se deducen del PDF anual.
- ⚠️ **Los importes alimentan nóminas.** Revisa siempre la tabla y las discrepancias
  antes de generar e importar.
