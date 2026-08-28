# NeaEvento — app del evento (día 12)

App web para organizar el evento de empresa. Cada participante recibe un
**enlace personal**; al abrirlo queda «activado», su nombre ya aparece escrito
y, la primera vez, ve la **animación del sorteo** (una caja estilo «ítem de
Mario» por la que van pasando los colores de los equipos cada vez más despacio
hasta caer en el suyo — el equipo real ya asignado por la organización: el
sorteo es solo el espectáculo). Después ve **su equipo y sus compañeros, el
programa del día (calendario) y los lugares** con botón de «cómo llegar», y
puede **confirmar su asistencia**. La organización lo gestiona todo desde un
panel: participantes, equipos con **sorteo automático equilibrado**, agenda,
lugares y reparto de enlaces (copiar, WhatsApp o CSV).

Es una app independiente de NeaConvenios: Python + Flask + SQLite, sin más.
Todos los datos viven en **un solo fichero** (`evento.db`): la copia de
seguridad es copiar ese fichero.

## Cómo se usa (flujo completo)

1. **⚙️ Evento** — nombre, fecha (por defecto 12/09/2026: cámbiala si es otro
   día 12), hora, mensaje de bienvenida, contacto y **URL pública** (la
   dirección donde está publicada la app: con ella se generan los enlaces).
2. **👥 Participantes** — añádelos uno a uno, pega la lista, o importa un
   Excel/CSV con columnas `nombre` (obligatoria), `apodo` (como le saluda la
   app), `rol` (p. ej. comercial/técnico), `telefono`, `email`/`correo`,
   `equipo`. Re-importar la misma lista no duplica a nadie: a los ya existentes
   solo se les rellenan los datos vacíos (sin tocar lo ya relleno ni su enlace).
3. **🎽 Equipos** — escribe los nombres separados por comas (los colores se
   asignan solos) y pulsa **Sorteo**: reparte de forma aleatoria y equilibrada
   (y si los participantes tienen `rol`, también reparte cada rol a partes
   iguales entre los equipos: mismos comerciales y técnicos en cada uno).
   Las asignaciones a mano se respetan si repartes «solo a los que no tienen
   equipo». También puedes importar el reparto ya decidido (columna `equipo`
   del Excel/CSV). La primera vez que cada participante abra su enlace después
   de tener equipo verá la animación del sorteo cayendo en su equipo real; si
   luego cambias a alguien de equipo, volverá a ver la animación con el nuevo.
4. **🗓️ Agenda** y **📍 Lugares** — el programa del día, cada actividad con su
   hora, lugar y, si hace falta, solo para un equipo (rotaciones). Los lugares
   con dirección generan solos el botón «Cómo llegar» (o pega el enlace exacto
   de Google Maps).
5. **🔗 Enlaces** — cada participante tiene su enlace personal. Repártelos con
   el botón de **WhatsApp** (mensaje ya escrito, plantilla editable), copiando
   uno a uno, o descargando el **CSV** para Excel/correo. En **📊 Resumen** ves
   quién abrió su enlace y quién confirmó.

El participante no necesita contraseña ni instalar nada: solo abrir su enlace
en el móvil.

## Ejecutar en un ordenador (probar en local)

```bash
pip install -r requirements.txt
python app.py            # → http://localhost:8502  (panel en /admin)
```

En Windows/Mac también valen los dobles clics: `Instalar.bat` / `Instalar
(primera vez).command` una vez, y luego `Abrir Evento.bat` / `Abrir
Evento.command`.

## Publicarla en internet (para que lleguen los enlaces)

Opción A — servidor Ubuntu/Lightsail (igual que NeaConvenios):

```bash
bash deploy/setup.sh     # deja el servicio corriendo en el puerto 8502
```

Opción B — Docker:

```bash
docker build -t neaevento evento/
docker run -d -p 8502:8502 -v neaevento_datos:/data \
  -e EVENTO_ADMIN_PASSWORD=una_buena_contraseña neaevento
```

Después, en el panel **⚙️ Evento**, pon la **URL pública** (p. ej.
`http://IP:8502`) para que los enlaces personales se generen con ella.

## Seguridad

- **Pon SIEMPRE `EVENTO_ADMIN_PASSWORD`** antes de publicar la app en internet:
  sin ella el panel queda abierto (solo aceptable en local). En los lanzadores
  de doble clic puede ir en un fichero `clave_admin.txt` (no se sube a git).
- El enlace de cada participante es su «llave»: si se envió a la persona
  equivocada, en su ficha hay un botón **«Generar enlace nuevo»** que invalida
  el anterior.

## Variables de entorno

| Variable | Qué hace | Por defecto |
|---|---|---|
| `EVENTO_ADMIN_PASSWORD` | Contraseña del panel `/admin` | *(sin contraseña, solo local)* |
| `EVENTO_DB_PATH` | Ruta del fichero de datos | `evento.db` junto a la app |
| `PUERTO` | Puerto del servidor | `8502` |

## Ficheros

| Archivo | Función |
|---|---|
| `app.py` | Rutas web (participante + panel de organización) y arranque |
| `db.py` | Datos en SQLite: config, equipos, participantes, agenda, lugares, sorteo |
| `paginas.py` | Todo el HTML/CSS (página del participante y panel) |
| `deploy/setup.sh` | Instalación como servicio en un servidor Ubuntu |
| `Dockerfile` | Imagen Docker (datos persistentes en el volumen `/data`) |
