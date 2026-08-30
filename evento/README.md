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
   milésimas, `1:02.451`, o `48.123` si bajó del minuto); los 2 que pasan a la
   final tienen un **hueco extra** para la vuelta de la 3ª tanda y les cuenta
   la mejor de las dos. Para abrirles ese hueco, marca «pasa a la final» en
   🏆 Puntos del panel (ahí también puedes corregir o meter tú cualquier
   tiempo). Cada piloto puntúa por su mejor vuelta: el más rápido tantos
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
| `db.py` | Datos en SQLite: config, equipos, participantes, agenda, lugares, sorteos y puntos |
| `paginas.py` | Todo el HTML/CSS (página del participante y panel) |
| `pruebas.py` | Pruebas automáticas: `python pruebas.py` |
| `deploy/lightsail.sh` | Instalación en Lightsail pegando un solo comando |
| `deploy/setup.sh` | Instalación como servicio en un servidor Ubuntu |
| `Dockerfile` | Imagen Docker (datos persistentes en el volumen `/data`) |

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
