# NeaEvento — app del evento (día 12)

App web para organizar el evento de empresa. Cada participante recibe un
**enlace personal**; al abrirlo queda «activado», su nombre ya aparece escrito
y, la primera vez, ve la **historia del evento** (frase a frase: «se celebra la
Olimpiada Nea Master, N equipos se juegan la victoria… el sorteo es aleatorio…
¡pasemos al sorteo!» — texto editable desde el panel) y la **animación del
sorteo**: una caja estilo «ítem de Mario» por la que van pasando los colores de
los equipos cada vez más despacio hasta caer en el suyo — el equipo real ya
asignado por la organización: el sorteo es el espectáculo. Después su página
—**teñida con el color de su equipo**— tiene cuatro secciones: **🎽 Equipo**
(los compañeros van apareciendo EN DIRECTO según pasan por el sorteo; los que
faltan son incógnitas «?»), **🗓️ Programa** (con su sala y su tanda, y el día
del evento marca la actividad **en curso** y la **siguiente**), **🏆 Puntos**
(clasificación en directo) y **📍 Lugares** con botón de «cómo llegar»; y puede
**confirmar su asistencia**. La organización lo gestiona todo desde un panel:
participantes, equipos con **sorteo automático equilibrado** y reglas de «van
juntos», agenda, lugares, puntos y reparto de enlaces (copiar, WhatsApp o CSV).

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
   Con **🔗 Personas que van juntas** puedes crear reglas (parejas o grupos)
   que el sorteo respeta siempre: los unidos caen en el mismo equipo.
   Las asignaciones a mano se respetan si repartes «solo a los que no tienen
   equipo». También puedes importar el reparto ya decidido (columna `equipo`
   del Excel/CSV). La primera vez que cada participante abra su enlace después
   de tener equipo verá la animación del sorteo cayendo en su equipo real; si
   luego cambias a alguien de equipo, volverá a ver la animación con el nuevo.
4. **🗓️ Agenda** y **📍 Lugares** — el programa del día, cada actividad con su
   hora, lugar y, si hace falta, solo para un equipo (rotaciones). Los lugares
   con dirección generan solos el botón «Cómo llegar» (o pega el enlace exacto
   de Google Maps). En Agenda están además los otros dos sorteos del día:
   **🗝️ Salas de la escape room** (una sala por equipo, al azar, con
   restricción opcional «esta sala no puede tocarle a este equipo») y
   **🏎️ Tandas de karts** (8 y 8 al azar repartiendo cada equipo entre ambas;
   los que quedan fuera, a la 3ª — la final — junto a los 2 mejores tiempos,
   que marcas en 🏆 Puntos con «pasa a la final»). Cada participante ve su
   sala y su tanda en su Programa, y al que pasa a la final se le avisa
   ahí mismo.
5. **🏆 Puntos** — el sistema de puntos del día: en **🎽 Equipos** se sortea
   un **capitán** por equipo (👑), y ese capitán —y solo él— apunta desde su
   móvil la hora de salida de su sala de la escape room. La escape reparte
   puntos por orden de salida (editables; 20/10/5 por defecto). En los karts
   **cada piloto mete su propia vuelta** desde su enlace (minutos:segundos.
   milésimas, `1:02.451`, o `48.123` si bajó del minuto). A la 3ª tanda pasan
   **solos los 2 mejores tiempos** de las dos primeras: en cuanto están todas
   las vueltas apuntadas, la app se lo dice a ellos en su móvil («¡Pasas a la
   final!») y les abre un **hueco extra** para esa vuelta, que les cuenta si es
   mejor que la primera. Mientras falte alguna vuelta no se canta nada (sería
   una alegría en falso) y se dice cuántas faltan. En 🏆 Puntos del panel ves
   quién pasa o a quién le falta apuntar, puedes corregir o meter tú cualquier
   tiempo, y la casilla «pasa a la final» sirve para forzarlo a mano si alguien
   no puede apuntar el suyo. Cada piloto puntúa por su mejor vuelta: el más rápido tantos
   puntos como pilotos, el último 1 — todas las posiciones cuentan. La
   **clasificación en directo** (escape + karts + total) la ve todo el mundo
   en la pestaña 🏆 de su enlace;
   gana el equipo con más puntos (medalla para todos sus miembros).
   Cada uno tiene ahí mismo el **tutorial**: cómo se reparten los puntos y qué
   le toca hacer a él (su vuelta; la hora de salida, solo el capitán), y en su
   Programa se le recuerda al lado de cada cita.
   Cuando acabe todo, con **🏁 Cerrar la Olimpiada** se publica el resultado: a
   los del equipo ganador y a la vuelta rápida del día les sale una
   felicitación con el aviso de **recoger el premio en los postres**; al resto,
   el resultado final. Se puede retirar si se publicó antes de tiempo.
6. **🔗 Enlaces** — cada participante tiene su enlace personal. Repártelos con
   el botón de **WhatsApp** (mensaje ya escrito, plantilla editable), copiando
   uno a uno, o descargando el **CSV** para Excel/correo. En **📊 Resumen** ves
   quién abrió su enlace y quién confirmó.

En **📊 Resumen** hay una lista de **Preparativos** que dice, con ✓ y ⬜, qué
está listo y qué falta (equipos, capitanes, salas, tandas, URL, contraseña,
enlaces abiertos), con enlace directo a lo que queda pendiente.

### En la pantalla de inicio, como una app

Cada página de participante trae su propio **manifiesto** (`/p/<token>/
manifest.webmanifest`), así que quien le dé a «Añadir a pantalla de inicio»
—en iPhone desde *Compartir*, en Android desde el menú del navegador— se queda
con un icono que abre **su** página directamente, a pantalla completa y con el
color de su equipo. La app se lo propone sola la primera vez (y no insiste si
dice que no o si ya la tiene). No hace falta tienda de aplicaciones ni instalar
nada.

La app lleva su **service worker**, así que una vez abierta funciona con mala
cobertura: enseña la última página que vio esa persona (equipo, sala, tanda)
con un aviso de «sin conexión», y se recupera sola en cuanto vuelve la señal.
Los navegadores solo lo activan por **https** (o en localhost).

Y lo más importante para el día: **si alguien guarda su tiempo sin cobertura no
lo pierde**. El móvil se lo queda apuntado, avisa abajo («tienes un tiempo sin
enviar») y lo manda solo en cuanto vuelve la señal — vale igual para la vuelta
de karts y para la hora de salida del capitán. Esto funciona sin https.

### Https en un rato, y ya es app de verdad

```bash
cd ~/neaevento && bash evento/deploy/https.sh
```

Instala Caddy, pide un certificado gratis de Let's Encrypt para un dominio del
tipo `13.38.46.216.nip.io` (no hay que comprar ni configurar nada: ese dominio
ya apunta a la IP), deja la app detrás y fija la URL pública en el evento.
Antes hay que abrir los **puertos 80 y 443** en Lightsail («Networking»). Con
eso desaparece el aviso de «sitio no seguro», Android ofrece «Instalar
aplicación» y el service worker entra en juego. Los enlaces repartidos por
`http://IP:8502` siguen valiendo: la app sigue escuchando ahí.

El participante no necesita contraseña ni instalar nada: solo abrir su enlace
en el móvil.

## Ejecutar en un ordenador (probar en local)

```bash
pip install -r requirements.txt
python app.py            # → http://localhost:8502  (panel en /admin)
python pruebas.py        # comprueba que todo sigue funcionando
```

En Windows/Mac también valen los dobles clics: `Instalar.bat` / `Instalar
(primera vez).command` una vez, y luego `Abrir Evento.bat` / `Abrir
Evento.command`.

## Publicarla en internet (para que lleguen los enlaces)

Opción A — servidor Ubuntu/Lightsail (igual que NeaConvenios). En el terminal
del navegador de Lightsail («Connect using SSH») basta pegar UN comando:

```bash
curl -fsSL https://raw.githubusercontent.com/gohan112/neaconvenios/claude/event-app-day-12-e4lcrp/evento/deploy/lightsail.sh | bash
```

Descarga el código, deja el servicio corriendo en el puerto 8502, genera la
contraseña del panel y la muestra al final. Solo quedan 2 pasos manuales:
abrir el puerto 8502 en la pestaña «Networking» de la instancia y fijar la
URL pública en ⚙️ Evento. (Si la rama ya se fusionó, cambia
`claude/event-app-day-12-e4lcrp` por `main` en la URL. Con el código ya en el
servidor: `bash deploy/setup.sh`.)

### Se actualiza sola

El instalador deja también un temporizador (`neaevento-update.timer`) que cada
5 minutos mira si hay versión nueva en GitHub. Si la hay: la baja, instala lo
que falte, **pasa las pruebas** y reinicia el servicio. Si algo falla, vuelve
sola a la versión anterior, apunta cuál falló para no reintentarla y la app
sigue funcionando con la versión buena. La base de datos del evento
(`evento.db`) no se toca nunca: no está en el repositorio.

```bash
journalctl -u neaevento-update -n 50      # qué ha hecho
sudo systemctl start neaevento-update     # actualizar ahora, sin esperar
sudo systemctl disable --now neaevento-update.timer   # desactivarla
```

Para instalarla en un servidor que ya estaba en marcha, una última vez a mano:

```bash
cd ~/neaevento && git pull && bash evento/deploy/setup.sh
```

Opción B — Docker:

```bash
docker build -t neaevento evento/
docker run -d -p 8502:8502 -v neaevento_datos:/data \
  -e EVENTO_ADMIN_PASSWORD=una_buena_contraseña neaevento
```

Opción C — Google Cloud Run (sirve la cuenta **Blaze de Firebase**: un
proyecto de Firebase *es* un proyecto de Google Cloud). Una sola vez:

```bash
gcloud auth login && gcloud config set project TU-PROYECTO
cd evento && bash deploy/nube.sh
```

Deja la app en `https://neaevento-xxxx.a.run.app`, con certificado ya puesto:
no hay que abrir puertos, ni instalar Caddy, ni mantener ninguna máquina. Al
terminar imprime la dirección y la contraseña del panel.

Lo delicado aquí es la base de datos: en Cloud Run el disco del contenedor se
borra en cada reinicio. Por eso la imagen (`Dockerfile.nube`) lleva dentro
**Litestream**, que copia el `evento.db` a un bucket cada segundo y lo
restaura al arrancar. Si Google reinicia el contenedor a media mañana, la app
vuelve con todos los tiempos apuntados. Va con **una sola instancia**
(`--min-instances 1 --max-instances 1 --no-cpu-throttling`) a propósito:
SQLite lo escribe uno cada vez, y así no se duerme entre tiempo y tiempo.

Con `min-instances 1` la instancia está encendida siempre. Para no gastar el
resto del año, cuando pase el evento:

```bash
gcloud run services update neaevento --region europe-west1 --min-instances 0
```

#### También se actualiza sola

Como el servidor de Ubuntu, pero por el camino de la nube. Una sola vez:

```bash
cd evento && bash deploy/autodespliegue.sh
```

Deja un disparador de Cloud Build enganchado al repositorio: cada cambio que
llega a la rama **pasa primero las pruebas** (`pruebas.py`) y solo entonces se
construye la imagen y se despliega. Si las pruebas fallan, la construcción se
para y Cloud Run sigue sirviendo la versión buena — no hace falta ni deshacer
nada, porque la versión anterior nunca se llegó a tocar. La receta está en
`evento/cloudbuild.yaml`.

La primera vez hay que conectar el repositorio con Cloud Build desde la
consola (una pantalla, dos clics); el script te dice dónde si falta. Y como el
despliegue solo cambia la imagen, la contraseña del panel, el bucket de la
copia y el número de instancias se quedan como estaban.

#### Una dirección corta

La que da Cloud Run (`neaevento-jeak2blh5q-ew.a.run.app`) no se puede dictar.
Con Firebase Hosting por delante queda en algo repartible:

```bash
cd evento && bash deploy/dominio.sh          # → https://neaevento.web.app
bash deploy/dominio.sh el-nombre-que-sea     # si prefieres otro
```

Pide ese nombre; si está cogido usa el del proyecto y sigue. No mueve la app:
la dirección larga sigue funcionando, esto es otra puerta al mismo sitio.
Después hay que poner la nueva en ⚙️ Evento como URL pública (los códigos de
cada participante no cambian).

(La app guarda la sesión del panel en la cookie `__session` justamente por
esto: es la única que Firebase Hosting deja pasar hasta Cloud Run.)

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
| `PUERTO` / `PORT` | Puerto del servidor (`PORT` lo pone Cloud Run) | `8502` |
| `REPLICA_URL` | Bucket donde replicar la base en la nube, p. ej. `gcs://bucket/neaevento` | *(sin copia)* |

## Ficheros

| Archivo | Función |
|---|---|
| `app.py` | Rutas web (participante + panel de organización) y arranque |
| `db.py` | Datos en SQLite: config, equipos, participantes, agenda, lugares, sorteos y puntos |
| `paginas.py` | Todo el HTML/CSS (página del participante y panel) |
| `pruebas.py` | Pruebas automáticas: `python pruebas.py` |
| `deploy/lightsail.sh` | Instalación en Lightsail pegando un solo comando |
| `deploy/setup.sh` | Instalación como servicio en un servidor Ubuntu |
| `Dockerfile` | Imagen Docker (datos persistentes en el volumen `/data`) |
| `deploy/nube.sh` | Sube la app a Google Cloud Run (cuenta Blaze de Firebase) |
| `deploy/autodespliegue.sh` | Deja Cloud Run actualizándose solo con cada cambio |
| `cloudbuild.yaml` | Receta de ese automatismo: pruebas → imagen → despliegue |
| `Dockerfile.nube` | Imagen para Cloud Run: la app + Litestream (copia al bucket) |
| `deploy/dominio.sh` | Deja la app en una dirección corta (…web.app) |
| `firebase.json` | Configuración de eso mismo, por si se hace a mano |

## Notas de diseño

Por si hay que tocar el aspecto más adelante, el criterio que sigue la app:

- **Móvil primero.** Todo está pensado para un móvil en la mano el día del
  evento: botones y pestañas de 44px o más, textos de 16px en los campos (así
  el iPhone no hace zoom al escribir) y nada que se salga de pantalla ni a
  320px de ancho.
- **Un solo sistema.** En `paginas.py`, el bloque `ESTILO` empieza con los
  *tokens* (colores, espaciado `--e1…--e6`, radios y sombras). Cambia el token
  y cambia toda la app; evita estilos sueltos.
- **El color manda.** La página de cada participante se tiñe con el color de
  su equipo (variable `--acento`); el texto encima lo elige `color_texto()`
  según el contraste real, para que un equipo amarillo se lea igual de bien
  que uno azul.
- **Una acción principal por pantalla.** Solo la tarjeta más importante lleva
  `class="destacada"`; si todo destaca, no destaca nada.
- **La app se adapta al momento.** Antes del evento se abre la pestaña del
  equipo (la novedad); el día del evento, el programa, con la actividad en
  curso marcada. El texto de bienvenida desaparece cuando ya has confirmado.
- **Accesible por defecto.** Foco visible en todo lo pulsable, `aria-selected`
  en las pestañas (y flechas del teclado), avisos con `role="status"` y
  respeto por «reducir movimiento» del sistema.
