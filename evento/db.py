"""
NeaEvento — capa de datos (SQLite).

Todo el evento vive en UN único fichero `evento.db` (configurable con la
variable de entorno EVENTO_DB_PATH): configuración, equipos, participantes,
agenda y lugares. Sin servidor de base de datos: la copia de seguridad es
copiar ese fichero.
"""

from __future__ import annotations

import os
import random
import re
import secrets
import sqlite3
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo("Europe/Madrid")
except Exception:  # noqa: BLE001 — sin datos de zona horaria, hora local del sistema
    _TZ = None

RUTA_DB = os.environ.get("EVENTO_DB_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "evento.db"
)

# Colores que se reparten automáticamente al crear equipos
PALETA = ["#CC0C18", "#1D6FB8", "#1E9E5A", "#E8A013", "#7B3FA0", "#0F9BA8", "#D3559C", "#5A6B7A"]

CONFIG_DEFECTO = {
    "nombre": "Olimpiada Nea Master",
    "fecha": "2026-09-12",
    "hora": "09:00",
    "descripcion": "¡Bienvenido/a a la Olimpiada! Aquí tienes tu equipo, el programa "
                   "del día y los lugares. Confirma tu asistencia más abajo.",
    # La historia que se cuenta antes del sorteo (una frase por línea).
    # Admite {equipos} y {participantes}, que se sustituyen por los números reales.
    "historia": "🏅 Se celebra la OLIMPIADA NEA MASTER.\n"
                "{equipos} equipos se juegan la victoria. Solo uno pasará a la historia.\n"
                "Los nombres de los {participantes} participantes ya están en el bombo.\n"
                "El sorteo es totalmente aleatorio: nadie sabe dónde caerá cada uno…\n"
                "¡Pasemos al sorteo!",
    # Tandas de karts (o similar): horas de cada tanda y nombre de la actividad
    "karts_nombre": "Karts",
    "karts_hora1": "11:30",
    "karts_hora2": "12:00",
    "karts_hora3": "12:45",
    "karts_lugar_id": "",
    # Escape room: hora de llegada, salas (una por línea, «Nombre: descripción»)
    # y lugar (id de la pestaña Lugares, para el botón «cómo llegar»)
    "escape_titulo": "Escape room",
    "escape_hora": "08:40",
    "escape_salas": "Luxor: nuestra famosa pirámide, aventura, sustos…\n"
                    "Barbarroja: un viejo búnker soviético que tendrá que repeler "
                    "el ataque nazi\n"
                    "Infamia: un submarino japonés es el primero en llegar a "
                    "Pearl Harbor",
    "escape_lugar_id": "",
    # Hasta esta fecha y hora, cada uno ve su equipo pero NO quién va con él.
    # Vacío = se ve desde el primer momento. Formato «2026-09-11T20:00».
    "equipos_desde": "",
    # Lo que hay que saber para llegar bien (aparcar, margen…). Sale junto a la hora.
    "escape_nota": "",
    # Puntos de la escape room por orden de salida (1º, 2º, 3º…)
    "puntos_escape": "20, 10, 5",
    "url_base": "",
    "contacto": "",
    # Asunto del correo (el cuerpo es el mismo texto que el de WhatsApp)
    "msg_asunto": "Olimpiada Nea Master: tu enlace personal",
    "msg_whatsapp": "¡Hola, {nombre}! Este es tu enlace personal para el evento: {enlace}\n"
                    "Dentro verás tu equipo, el programa del día y los lugares. "
                    "¡Entra y confirma tu asistencia!\n"
                    "Guárdalo en la pantalla de inicio del móvil (te dice cómo "
                    "nada más entrar): así lo tienes a mano el sábado.",
}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS config (
  clave TEXT PRIMARY KEY,
  valor TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS equipos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre      TEXT NOT NULL,
  color       TEXT NOT NULL DEFAULT '#CC0C18',
  emoji       TEXT NOT NULL DEFAULT '',
  descripcion TEXT NOT NULL DEFAULT '',
  sala        TEXT NOT NULL DEFAULT '',   -- sala de la escape room sorteada
  sala_desc   TEXT NOT NULL DEFAULT '',
  capitan_id  INTEGER,                    -- capitán sorteado (mete el tiempo)
  tiempo_escape TEXT NOT NULL DEFAULT '' -- hora de salida de su sala (HH:MM[:SS])
);

CREATE TABLE IF NOT EXISTS participantes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre        TEXT NOT NULL,
  apodo         TEXT NOT NULL DEFAULT '',    -- cómo le llaman (para el saludo)
  rol           TEXT NOT NULL DEFAULT '',    -- p. ej. comercial / técnico
  telefono      TEXT NOT NULL DEFAULT '',
  email         TEXT NOT NULL DEFAULT '',
  equipo_id     INTEGER REFERENCES equipos(id) ON DELETE SET NULL,
  token         TEXT NOT NULL UNIQUE,
  tiempo_karts  TEXT NOT NULL DEFAULT '',      -- su vuelta en su tanda (1:02.45)
  tiempo_final  TEXT NOT NULL DEFAULT '',      -- su vuelta en la 3ª tanda (la final)
  finalista     INTEGER NOT NULL DEFAULT 0,    -- pasa a la final por tiempo
  grupo_sorteo  TEXT NOT NULL DEFAULT '',      -- quienes comparten grupo van JUNTOS
  visto_en      TEXT,                          -- primera vez que abrió su enlace
  revelado_en   TEXT,                          -- cuándo vio la animación del sorteo
  confirmado    INTEGER NOT NULL DEFAULT 0,    -- 0 pendiente · 1 viene · -1 no viene
  confirmado_en TEXT,
  notas         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS lugares (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre    TEXT NOT NULL,
  direccion TEXT NOT NULL DEFAULT '',
  maps      TEXT NOT NULL DEFAULT '',          -- enlace a Google Maps (opcional)
  notas     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS agenda (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  hora        TEXT NOT NULL,                   -- "09:30"
  hora_fin    TEXT NOT NULL DEFAULT '',
  actividad   TEXT NOT NULL,
  descripcion TEXT NOT NULL DEFAULT '',
  lugar_id    INTEGER REFERENCES lugares(id) ON DELETE SET NULL,
  equipo_id   INTEGER REFERENCES equipos(id) ON DELETE CASCADE  -- NULL = para todos
);
"""


# ------------------------------------------------------------------ utilidades

def ahora() -> str:
    dt = datetime.now(_TZ) if _TZ else datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M")


def hoy() -> date:
    dt = datetime.now(_TZ) if _TZ else datetime.now()
    return dt.date()


def companeros_a_la_vista() -> bool:
    """¿Se puede ver ya quién va en cada equipo?

    Si se van descubriendo de uno en uno se nota el orden en que abre la
    gente; con una hora fija se destapan todos a la vez.
    """
    cuando = (leer_config().get("equipos_desde") or "").strip()
    if not cuando:
        return True
    try:
        limite = datetime.fromisoformat(cuando)
    except ValueError:
        return True                      # una fecha mal escrita no bloquea nada
    ahora_ = datetime.now(_TZ) if _TZ else datetime.now()
    if limite.tzinfo is None and ahora_.tzinfo is not None:
        limite = limite.replace(tzinfo=ahora_.tzinfo)
    return ahora_ >= limite


def conexion() -> sqlite3.Connection:
    carpeta = os.path.dirname(RUTA_DB)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    con = sqlite3.connect(RUTA_DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def iniciar() -> None:
    con = conexion()
    con.executescript(ESQUEMA)
    # Migraciones para bases de datos creadas antes de existir estas columnas
    columnas = {r["name"] for r in con.execute("PRAGMA table_info(participantes)")}
    if "revelado_en" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN revelado_en TEXT")
    if "apodo" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN apodo TEXT NOT NULL DEFAULT ''")
    if "rol" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN rol TEXT NOT NULL DEFAULT ''")
    if "grupo_sorteo" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN grupo_sorteo TEXT NOT NULL DEFAULT ''")
    if "tanda" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN tanda TEXT NOT NULL DEFAULT ''")
    if "tiempo_karts" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN tiempo_karts TEXT NOT NULL DEFAULT ''")
    if "tiempo_final" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN tiempo_final TEXT NOT NULL DEFAULT ''")
    if "finalista" not in columnas:
        con.execute("ALTER TABLE participantes ADD COLUMN finalista INTEGER NOT NULL DEFAULT 0")
    columnas_eq = {r["name"] for r in con.execute("PRAGMA table_info(equipos)")}
    if "sala" not in columnas_eq:
        con.execute("ALTER TABLE equipos ADD COLUMN sala TEXT NOT NULL DEFAULT ''")
    if "sala_desc" not in columnas_eq:
        con.execute("ALTER TABLE equipos ADD COLUMN sala_desc TEXT NOT NULL DEFAULT ''")
    if "capitan_id" not in columnas_eq:
        con.execute("ALTER TABLE equipos ADD COLUMN capitan_id INTEGER")
    if "tiempo_escape" not in columnas_eq:
        con.execute("ALTER TABLE equipos ADD COLUMN tiempo_escape TEXT NOT NULL DEFAULT ''")
    # Semillas de configuración (solo las claves que falten)
    existentes = {r["clave"] for r in con.execute("SELECT clave FROM config")}
    for clave, valor in CONFIG_DEFECTO.items():
        if clave not in existentes:
            con.execute("INSERT INTO config (clave, valor) VALUES (?, ?)", (clave, valor))
    if "secreto" not in existentes:
        con.execute("INSERT INTO config (clave, valor) VALUES ('secreto', ?)",
                    (secrets.token_hex(32),))
    con.commit()
    con.close()


def normalizar_hora(texto: str) -> str:
    """'9:30', '9.30' o '9h30' → '09:30'. Si no se reconoce, se guarda tal cual."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*[:.hH]\s*(\d{2})\s*", texto or "")
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return (texto or "").strip()


# Sin I, O, 0 ni 1: son las que se confunden al leer un código en voz alta o
# al copiarlo de un papel. Con 32 letras y 6 huecos salen mil millones de
# combinaciones, de sobra para que nadie acierte el de otro por casualidad.
LETRAS_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalizar_codigo(texto: str) -> str:
    """«k7 rq-4m» → «K7RQ4M». Así da igual cómo lo teclee cada uno."""
    return "".join(c for c in (texto or "").upper()
                   if c.isalnum())


def _token_nuevo(con: sqlite3.Connection) -> str:
    while True:
        token = "".join(secrets.choice(LETRAS_CODIGO) for _ in range(6))
        if not con.execute("SELECT 1 FROM participantes WHERE token = ?", (token,)).fetchone():
            return token


def color_valido(color: str, defecto: str = "#CC0C18") -> str:
    return color if re.fullmatch(r"#[0-9A-Fa-f]{6}", color or "") else defecto


# ------------------------------------------------------------------ config

def leer_config() -> dict:
    con = conexion()
    cfg = {r["clave"]: r["valor"] for r in con.execute("SELECT clave, valor FROM config")}
    con.close()
    return cfg


def guardar_config(valores: dict) -> None:
    con = conexion()
    for clave, valor in valores.items():
        if clave == "secreto":
            continue  # el secreto de sesión no se toca desde formularios
        con.execute(
            "INSERT INTO config (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, (valor or "").strip()),
        )
    con.commit()
    con.close()


def secreto_app() -> str:
    return leer_config().get("secreto") or secrets.token_hex(32)


# ------------------------------------------------------------------ equipos

def crear_equipos(nombres: list[str]) -> int:
    """Crea varios equipos de golpe repartiendo la paleta de colores."""
    con = conexion()
    ocupados = con.execute("SELECT COUNT(*) FROM equipos").fetchone()[0]
    creados = 0
    for i, nombre in enumerate(nombres):
        nombre = nombre.strip()
        if not nombre:
            continue
        existe = con.execute(
            "SELECT 1 FROM equipos WHERE lower(nombre) = lower(?)", (nombre,)
        ).fetchone()
        if existe:
            continue
        color = PALETA[(ocupados + i) % len(PALETA)]
        con.execute("INSERT INTO equipos (nombre, color) VALUES (?, ?)", (nombre, color))
        creados += 1
    con.commit()
    con.close()
    return creados


def editar_equipo(equipo_id: int, nombre: str, color: str, emoji: str, descripcion: str) -> None:
    con = conexion()
    con.execute(
        "UPDATE equipos SET nombre = ?, color = ?, emoji = ?, descripcion = ? WHERE id = ?",
        (nombre.strip(), color_valido(color), emoji.strip(), descripcion.strip(), equipo_id),
    )
    con.commit()
    con.close()


def borrar_equipo(equipo_id: int) -> None:
    con = conexion()
    con.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    con.commit()
    con.close()


def listar_equipos() -> list[dict]:
    con = conexion()
    filas = con.execute(
        """
        SELECT e.*,
               (SELECT COUNT(*) FROM participantes p WHERE p.equipo_id = e.id) AS n_miembros,
               (SELECT COUNT(*) FROM participantes p
                 WHERE p.equipo_id = e.id AND p.confirmado = 1)               AS n_confirmados
          FROM equipos e
         ORDER BY e.id
        """
    ).fetchall()
    con.close()
    return [dict(f) for f in filas]


def equipo(equipo_id: int) -> dict | None:
    con = conexion()
    fila = con.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,)).fetchone()
    con.close()
    return dict(fila) if fila else None


def miembros(equipo_id: int) -> list[dict]:
    con = conexion()
    filas = con.execute(
        "SELECT id, nombre, apodo, rol, revelado_en FROM participantes "
        "WHERE equipo_id = ? ORDER BY revelado_en IS NULL, revelado_en, "
        "nombre COLLATE NOCASE",
        (equipo_id,),
    ).fetchall()
    con.close()
    return [dict(f) for f in filas]


def sortear(todos: bool = False) -> int:
    """
    Reparte participantes entre los equipos de forma aleatoria y EQUILIBRADA,
    respetando las reglas:

      1. JUNTOS: quienes comparten `grupo_sorteo` caen siempre en el MISMO
         equipo (los grupos se colocan primero, de mayor a menor, en el equipo
         con menos gente). Además, cada grupo evita los equipos donde ya hay
         OTRO grupo: mientras haya equipos de sobra, cada regla cae en un
         equipo distinto (si hay más reglas que equipos, se reparten).
      2. Tamaños: cada persona va al equipo que menos gente tenga.
      3. Roles: si hay «rol» (p. ej. comercial / técnico), cada rol se reparte
         a partes iguales entre los equipos, dentro de lo que permitan las
         reglas anteriores.

    todos=False → solo reparte a quien aún no tiene equipo (respeta asignaciones a mano).
    todos=True  → borra todas las asignaciones y vuelve a sortear desde cero.
    Devuelve cuántas personas se han repartido.
    """
    con = conexion()
    ids_equipos = [r["id"] for r in con.execute("SELECT id FROM equipos ORDER BY id")]
    if not ids_equipos:
        con.close()
        raise ValueError("No hay equipos: crea los equipos antes de sortear.")
    if todos:
        con.execute("UPDATE participantes SET equipo_id = NULL, revelado_en = NULL")

    pendientes = con.execute(
        "SELECT id, rol, grupo_sorteo FROM participantes WHERE equipo_id IS NULL"
    ).fetchall()
    n_repartidos = len(pendientes)
    if not pendientes:
        con.close()
        return 0

    # Tamaños actuales (total y por rol) de lo ya asignado a mano
    tam_total = {
        eid: con.execute(
            "SELECT COUNT(*) FROM participantes WHERE equipo_id = ?", (eid,)
        ).fetchone()[0]
        for eid in ids_equipos
    }
    tam_rol: dict[tuple[int, str], int] = {}
    for fila in con.execute(
        "SELECT equipo_id, lower(trim(rol)) AS r, COUNT(*) AS n FROM participantes "
        "WHERE equipo_id IS NOT NULL GROUP BY equipo_id, r"
    ):
        tam_rol[(fila["equipo_id"], fila["r"] or "")] = fila["n"]

    def asignar(pid: int, eid: int, rol: str) -> None:
        # revelado_en a NULL: al cambiar de equipo vuelve a ver la animación
        con.execute("UPDATE participantes SET equipo_id = ?, revelado_en = NULL "
                    "WHERE id = ?", (eid, pid))
        tam_total[eid] += 1
        tam_rol[(eid, rol)] = tam_rol.get((eid, rol), 0) + 1

    # Si un grupo «juntos» ya tiene algún miembro con equipo (puesto a mano),
    # el resto del grupo va a ese mismo equipo, pase lo que pase.
    anclas: dict[str, int] = {}
    for fila in con.execute(
        "SELECT trim(grupo_sorteo) AS g, equipo_id FROM participantes "
        "WHERE equipo_id IS NOT NULL AND trim(grupo_sorteo) != ''"
    ):
        anclas.setdefault(fila["g"], fila["equipo_id"])

    unidades_grupo: dict[str, list[tuple[int, str]]] = {}
    sueltos: list[tuple[int, str]] = []
    for fila in pendientes:
        grupo = (fila["grupo_sorteo"] or "").strip()
        rol = (fila["rol"] or "").strip().lower()
        if grupo and grupo in anclas:
            asignar(fila["id"], anclas[grupo], rol)
        elif grupo:
            unidades_grupo.setdefault(grupo, []).append((fila["id"], rol))
        else:
            sueltos.append((fila["id"], rol))

    # 1) Grupos «juntos» primero, de mayor a menor. Cada grupo va al equipo con
    #    menos gente, evitando los equipos que YA tienen otro grupo (así cada
    #    regla cae en un equipo distinto mientras haya equipos de sobra); a
    #    igualdad, al que menos repita los roles del grupo.
    equipos_con_grupo: set[int] = {
        fila["equipo_id"] for fila in con.execute(
            "SELECT DISTINCT equipo_id FROM participantes "
            "WHERE equipo_id IS NOT NULL AND trim(grupo_sorteo) != ''"
        )
    }
    unidades = list(unidades_grupo.values())
    random.shuffle(unidades)
    unidades.sort(key=len, reverse=True)  # el orden aleatorio se conserva por tamaño
    for unidad in unidades:
        def clave_unidad(eid: int) -> tuple[int, int, int]:
            solape = sum(tam_rol.get((eid, rol), 0) for _pid, rol in unidad)
            return (1 if eid in equipos_con_grupo else 0, tam_total[eid], solape)
        mejor = min(clave_unidad(eid) for eid in ids_equipos)
        eid = random.choice([i for i in ids_equipos if clave_unidad(i) == mejor])
        for pid, rol in unidad:
            asignar(pid, eid, rol)
        equipos_con_grupo.add(eid)

    # 2) El resto, rol a rol (los roles grandes primero, los sin rol al final).
    #    Primero manda el TAMAÑO (nunca sobrellenar un equipo) y, a igualdad,
    #    el equipo al que le falte ese rol.
    grupos_rol: dict[str, list[int]] = {}
    for pid, rol in sueltos:
        grupos_rol.setdefault(rol, []).append(pid)
    for ids in grupos_rol.values():
        random.shuffle(ids)
    orden = sorted((r for r in grupos_rol if r), key=lambda r: -len(grupos_rol[r]))
    if "" in grupos_rol:
        orden.append("")
    for rol in orden:
        for pid in grupos_rol[rol]:
            def clave(eid: int) -> tuple[int, int]:
                return (tam_total[eid], tam_rol.get((eid, rol), 0))
            mejor = min(clave(eid) for eid in ids_equipos)
            eid = random.choice([i for i in ids_equipos if clave(i) == mejor])
            asignar(pid, eid, rol)
    con.commit()
    con.close()
    return n_repartidos


def crear_grupo_juntos(ids: list[int]) -> str:
    """
    Marca a varias personas para que el sorteo las meta SIEMPRE en el mismo
    equipo. Si alguna ya estaba en otro grupo, se muda a este.
    Devuelve el nombre del grupo (G1, G2, …).
    """
    con = conexion()
    existentes = {
        r[0] for r in con.execute(
            "SELECT DISTINCT trim(grupo_sorteo) FROM participantes "
            "WHERE trim(grupo_sorteo) != ''"
        )
    }
    n = 1
    while f"G{n}" in existentes:
        n += 1
    grupo = f"G{n}"
    con.executemany(
        "UPDATE participantes SET grupo_sorteo = ? WHERE id = ?",
        [(grupo, pid) for pid in ids],
    )
    con.commit()
    con.close()
    return grupo


def deshacer_grupo_juntos(grupo: str) -> None:
    con = conexion()
    con.execute(
        "UPDATE participantes SET grupo_sorteo = '' WHERE trim(grupo_sorteo) = ?",
        (grupo.strip(),),
    )
    con.commit()
    con.close()


def grupos_juntos() -> list[dict]:
    """Los grupos «van juntos»: [{grupo, miembros: [{id, nombre, apodo, rol}]}]."""
    con = conexion()
    filas = con.execute(
        "SELECT id, nombre, apodo, rol, trim(grupo_sorteo) AS grupo "
        "FROM participantes WHERE trim(grupo_sorteo) != '' "
        "ORDER BY grupo, nombre COLLATE NOCASE"
    ).fetchall()
    con.close()
    grupos: dict[str, list[dict]] = {}
    for fila in filas:
        grupos.setdefault(fila["grupo"], []).append(dict(fila))
    return [{"grupo": g, "miembros": miembros} for g, miembros in grupos.items()]


def sortear_tandas() -> tuple[int, int, int]:
    """
    Reparte a TODOS los participantes en las tandas de karts:
      · Tanda 1 y tanda 2: 8 personas cada una, al azar pero repartiendo a cada
        equipo más o menos por igual entre ambas.
      · Los que no caben (con 18 personas, 2): tanda 3 — la final, a la que
        además irán los mejores tiempos (eso se decide en la pista, no aquí).
    Devuelve (n_tanda1, n_tanda2, n_tanda3).
    """
    con = conexion()
    filas = con.execute("SELECT id, equipo_id FROM participantes").fetchall()
    personas = [(f["id"], f["equipo_id"] or 0) for f in filas]
    random.shuffle(personas)

    # Primero, los que van directos a la 3ª (los que exceden de 16),
    # intentando que sean de equipos distintos
    n_fuera = max(0, len(personas) - 16)
    fuera: list[int] = []
    equipos_usados: set[int] = set()
    for pid, eq in personas:
        if len(fuera) >= n_fuera:
            break
        if eq not in equipos_usados:
            fuera.append(pid)
            equipos_usados.add(eq)
    for pid, _eq in personas:  # si hicieran falta más que equipos hay, se repite
        if len(fuera) >= n_fuera:
            break
        if pid not in fuera:
            fuera.append(pid)

    # El resto: equipo a equipo, ALTERNANDO estrictamente entre tanda 1 y 2
    # (empezando por la más vacía). Así cada equipo queda repartido entre las
    # dos tandas con diferencia de 1 como mucho, y los totales acaban en 8 y 8.
    ids_fuera = set(fuera)
    cupo = {1: 8, 2: 8}
    tam = {1: 0, 2: 0}
    asignacion: dict[int, int] = {}
    por_equipo: dict[int, list[int]] = {}
    for pid, eq in personas:  # `personas` ya viene barajada
        if pid not in ids_fuera:
            por_equipo.setdefault(eq, []).append(pid)
    orden_equipos = list(por_equipo)
    random.shuffle(orden_equipos)
    for eq in orden_equipos:
        if tam[1] < tam[2]:
            lado = 1
        elif tam[2] < tam[1]:
            lado = 2
        else:
            lado = random.choice((1, 2))
        for pid in por_equipo[eq]:
            if tam[lado] >= cupo[lado]:
                lado = 3 - lado
            if tam[lado] >= cupo[lado]:  # ambas llenas: a la 3ª tanda
                fuera.append(pid)
                continue
            asignacion[pid] = lado
            tam[lado] += 1
            lado = 3 - lado

    for pid, tanda in asignacion.items():
        con.execute("UPDATE participantes SET tanda = ? WHERE id = ?",
                    (str(tanda), pid))
    for pid in fuera:
        con.execute("UPDATE participantes SET tanda = '3' WHERE id = ?", (pid,))
    con.commit()
    con.close()
    return tam[1], tam[2], len(fuera)


def deshacer_tandas() -> None:
    con = conexion()
    con.execute("UPDATE participantes SET tanda = ''")
    con.commit()
    con.close()


def sortear_capitanes() -> int:
    """Elige al azar un capitán por equipo (entre sus miembros). Devuelve cuántos."""
    con = conexion()
    elegidos = 0
    for eq in con.execute("SELECT id FROM equipos").fetchall():
        ids = [r["id"] for r in con.execute(
            "SELECT id FROM participantes WHERE equipo_id = ?", (eq["id"],))]
        capitan = random.choice(ids) if ids else None
        con.execute("UPDATE equipos SET capitan_id = ? WHERE id = ?",
                    (capitan, eq["id"]))
        if capitan:
            elegidos += 1
    con.commit()
    con.close()
    return elegidos


def poner_tiempo_escape(equipo_id: int, texto: str) -> None:
    con = conexion()
    con.execute("UPDATE equipos SET tiempo_escape = ? WHERE id = ?",
                ((texto or "").strip(), equipo_id))
    con.commit()
    con.close()


def poner_tiempo_karts(participante_id: int, texto: str, final: bool = False) -> None:
    """Guarda su vuelta: la de su tanda o, con final=True, la de la 3ª tanda."""
    columna = "tiempo_final" if final else "tiempo_karts"
    con = conexion()
    con.execute(f"UPDATE participantes SET {columna} = ? WHERE id = ?",
                ((texto or "").strip(), participante_id))
    con.commit()
    con.close()


def marcar_finalista(participante_id: int, pasa: bool) -> None:
    """Los dos mejores tiempos pasan a la final: se les abre un hueco extra."""
    con = conexion()
    con.execute("UPDATE participantes SET finalista = ? WHERE id = ?",
                (1 if pasa else 0, participante_id))
    con.commit()
    con.close()


def mejor_vuelta(p: dict) -> int | None:
    """Su mejor vuelta en milisegundos, mirando la de su tanda y la de la final."""
    tiempos = [x for x in (parsear_tiempo_vuelta(p.get("tiempo_karts") or ""),
                           parsear_tiempo_vuelta(p.get("tiempo_final") or ""))
               if x is not None]
    return min(tiempos) if tiempos else None


def estado_final() -> dict:
    """Quién corre la 3ª tanda (la final) y si eso ya es definitivo.

    Van los que se quedaron fuera de las dos primeras tandas y, por tiempo, los
    2 mejores. Para no dar una alegría en falso, los 2 mejores no se anuncian
    hasta que TODOS los de las tandas 1 y 2 tengan su vuelta apuntada; mientras
    tanto se dice cuántos faltan. Marcar a alguien a mano en el panel manda
    siempre (por si a alguien se le queda el móvil sin batería).
    """
    gente = listar_participantes()
    pilotos = [p for p in gente if (p.get("tanda") or "").strip() in ("1", "2")]
    pendientes = [p for p in pilotos if mejor_vuelta(p) is None]
    cerrado = bool(pilotos) and not pendientes
    por_tiempo = []
    if cerrado:
        ordenados = sorted(pilotos, key=lambda p: mejor_vuelta(p))
        corte = mejor_vuelta(ordenados[min(1, len(ordenados) - 1)])
        por_tiempo = [p for p in ordenados if mejor_vuelta(p) <= corte]  # empates dentro
    ids = {p["id"] for p in gente
           if (p.get("tanda") or "").strip() == "3" or p.get("finalista")}
    ids |= {p["id"] for p in por_tiempo}
    return {"ids": ids, "por_tiempo": por_tiempo, "pendientes": pendientes,
            "cerrado": cerrado}


def corre_la_final(p: dict) -> bool:
    """Corre la 3ª tanda quien se quedó fuera de las dos primeras o clasificó."""
    if (p.get("tanda") or "").strip() == "3" or p.get("finalista"):
        return True
    return p["id"] in estado_final()["ids"]


def parsear_hora_dia(texto: str) -> int | None:
    """'10:05' o '10:05:30' → segundos desde medianoche (para ordenar salidas)."""
    m = re.fullmatch(r"\s*(\d{1,2})[:.hH](\d{2})(?::(\d{2}))?\s*", texto or "")
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)


def parsear_tiempo_vuelta(texto: str) -> int | None:
    """'48.123', '48,3', '1:02.451' o '62' → milisegundos (para ordenar vueltas)."""
    # Se admite lo que imprimen los circuitos: 1:02.451, 1'02.451 y 1'02"451
    m = re.fullmatch(r"""\s*(?:(\d+)[:'])?(\d{1,3})(?:[.,"](\d{1,3}))?\s*""",
                     texto or "")
    if not m:
        return None
    minutos = int(m.group(1) or 0)
    segundos = int(m.group(2))
    if m.group(1) and segundos > 59:
        return None            # «1:75» no es una vuelta: son minutos y segundos
    fraccion = (m.group(3) or "").ljust(3, "0")[:3]
    return (minutos * 60 + segundos) * 1000 + int(fraccion or 0)


def _puntos_escape_lista(cfg: dict) -> list[int]:
    puntos = []
    for trozo in (cfg.get("puntos_escape") or "").replace(";", ",").split(","):
        try:
            puntos.append(int(trozo.strip()))
        except ValueError:
            continue
    return puntos or [20, 10, 5]


def clasificacion() -> dict:
    """
    Calcula la clasificación de la Olimpiada:
      · Escape room: por hora de salida (antes = mejor), puntos configurables
        (por defecto 20 / 10 / 5).
      · Karts: cada piloto puntúa por su mejor vuelta — el más rápido tantos
        puntos como pilotos con tiempo, el último 1 (todos los puestos cuentan).
      · Total por equipo = escape + karts. Gana el que más puntos tenga.
    """
    cfg = leer_config()
    equipos_ = listar_equipos()
    participantes_ = listar_participantes()

    # Escape room
    con_tiempo = [(eq, parsear_hora_dia(eq.get("tiempo_escape") or ""))
                  for eq in equipos_]
    validos = sorted([x for x in con_tiempo if x[1] is not None], key=lambda x: x[1])
    lista_puntos = _puntos_escape_lista(cfg)
    puntos_escape: dict[int, int] = {}
    escape = []
    for i, (eq, _segundos) in enumerate(validos):
        pts = lista_puntos[i] if i < len(lista_puntos) else 0
        puntos_escape[eq["id"]] = pts
        escape.append({"equipo": eq, "tiempo": eq.get("tiempo_escape"), "puntos": pts})
    for eq, segundos in con_tiempo:
        if segundos is None:
            escape.append({"equipo": eq, "tiempo": eq.get("tiempo_escape") or "",
                           "puntos": 0})

    # Karts (individual): de sus dos vueltas posibles cuenta la mejor
    corredores = [(p, mejor_vuelta(p)) for p in participantes_]
    ordenados = sorted([x for x in corredores if x[1] is not None], key=lambda x: x[1])
    n = len(ordenados)
    puntos_karts_equipo: dict[int, int] = {}
    karts = []
    puntos_por_tiempo: dict[int, int] = {}
    for i, (p, ms) in enumerate(ordenados):
        # el mejor se lleva n, el último 1; y si dos empatan a la milésima, los
        # dos se llevan lo mismo (nadie pierde un punto por el orden de la lista)
        pts = puntos_por_tiempo.setdefault(ms, n - i)
        # se enseña la vuelta que le ha puntuado, que puede ser la de la final
        final = p.get("tiempo_final") or ""
        cual = (final if parsear_tiempo_vuelta(final) == ms
                else p.get("tiempo_karts"))
        karts.append({"participante": p, "tiempo": cual, "puntos": pts})
        if p.get("equipo_id"):
            puntos_karts_equipo[p["equipo_id"]] = \
                puntos_karts_equipo.get(p["equipo_id"], 0) + pts

    # Totales por equipo
    tabla = []
    for eq in equipos_:
        pts_escape = puntos_escape.get(eq["id"], 0)
        pts_karts = puntos_karts_equipo.get(eq["id"], 0)
        tabla.append({"equipo": eq, "escape": pts_escape, "karts": pts_karts,
                      "total": pts_escape + pts_karts})
    tabla.sort(key=lambda fila: -fila["total"])
    # Pilotos que van a correr (para explicar los puntos: el primero se lleva
    # tantos como pilotos). Si aún no hay tandas, son todos los participantes.
    con_tanda = sum(1 for p in participantes_ if (p.get("tanda") or "").strip())
    return {"escape": escape, "karts": karts, "equipos": tabla,
            "n_corredores": n, "n_pilotos": con_tanda or len(participantes_)}


def ganadores(clasif: dict) -> dict:
    """Quién se lleva premio: el equipo con más puntos y la vuelta rápida del día.

    Se usa al cerrar la Olimpiada para felicitar a cada uno desde su enlace. Si
    hay empate arriba (o dos vueltas idénticas), salen todos: nadie se queda
    fuera de su medalla por un desempate inventado."""
    tabla = [f for f in clasif.get("equipos", []) if f["total"] > 0]
    mejor = max((f["total"] for f in tabla), default=0)
    equipos_ = [f["equipo"] for f in tabla if f["total"] == mejor] if mejor else []
    karts = clasif.get("karts") or []
    tiempo = karts[0]["tiempo"] if karts else ""
    pilotos = [f["participante"] for f in karts if f["tiempo"] == tiempo] if tiempo else []
    return {"equipos": equipos_, "puntos": mejor, "pilotos": pilotos, "tiempo": tiempo}


def parsear_salas(texto: str) -> list[dict]:
    """Líneas «Nombre: descripción» → [{nombre, descripcion}]."""
    salas = []
    for linea in (texto or "").splitlines():
        linea = linea.strip().lstrip("•-· ").strip()
        if not linea:
            continue
        if ":" in linea:
            nombre, descripcion = linea.split(":", 1)
        else:
            nombre, descripcion = linea, ""
        if nombre.strip():
            salas.append({"nombre": nombre.strip(), "descripcion": descripcion.strip()})
    return salas


def sortear_salas(salas: list[dict], sala_excluida: str = "",
                  equipo_excluido: int | None = None) -> None:
    """
    Reparte al azar una sala de la escape room a cada equipo. Si se indica una
    exclusión («la sala X no puede tocarle al equipo Y»), se respeta.
    """
    equipos_ = listar_equipos()
    if not equipos_:
        raise ValueError("No hay equipos: créalos antes de sortear las salas.")
    if len(salas) != len(equipos_):
        raise ValueError(f"Hay {len(salas)} sala(s) y {len(equipos_)} equipo(s): "
                         f"deben coincidir para el sorteo.")
    orden = None
    for _ in range(500):
        candidato = random.sample(salas, len(salas))
        valido = all(
            not (sala["nombre"] == sala_excluida.strip() and eq["id"] == equipo_excluido)
            for eq, sala in zip(equipos_, candidato)
        )
        if valido:
            orden = candidato
            break
    if orden is None:
        raise ValueError("No hay ningún reparto posible con esa restricción.")
    con = conexion()
    for eq, sala in zip(equipos_, orden):
        con.execute("UPDATE equipos SET sala = ?, sala_desc = ? WHERE id = ?",
                    (sala["nombre"], sala["descripcion"], eq["id"]))
    con.commit()
    con.close()


def deshacer_salas() -> None:
    con = conexion()
    con.execute("UPDATE equipos SET sala = '', sala_desc = ''")
    con.commit()
    con.close()


def _buscar_o_crear_equipo(con: sqlite3.Connection, nombre: str) -> int:
    fila = con.execute(
        "SELECT id FROM equipos WHERE lower(nombre) = lower(?)", (nombre.strip(),)
    ).fetchone()
    if fila:
        return fila["id"]
    n = con.execute("SELECT COUNT(*) FROM equipos").fetchone()[0]
    cur = con.execute(
        "INSERT INTO equipos (nombre, color) VALUES (?, ?)",
        (nombre.strip(), PALETA[n % len(PALETA)]),
    )
    return cur.lastrowid


# ------------------------------------------------------------------ participantes

def crear_participante(nombre: str, telefono: str = "", email: str = "",
                       equipo_id: int | None = None, apodo: str = "",
                       rol: str = "") -> int:
    con = conexion()
    cur = con.execute(
        "INSERT INTO participantes (nombre, apodo, rol, telefono, email, equipo_id, token) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nombre.strip(), apodo.strip(), rol.strip(), telefono.strip(), email.strip(),
         equipo_id, _token_nuevo(con)),
    )
    con.commit()
    con.close()
    return cur.lastrowid


def importar(filas: list[dict]) -> tuple[int, int]:
    """
    Importa participantes [{nombre, apodo, rol, telefono, email, equipo}]. Si el
    equipo no existe se crea. Se puede re-importar la misma lista sin miedo:
    a los nombres que ya existen (sin distinguir mayúsculas) NO se les duplica
    ni se les machaca nada — solo se les rellenan los campos que tuvieran
    vacíos (p. ej. si el Excel nuevo trae los correos). Su enlace no cambia.
    Devuelve (añadidos, ya_existentes).
    """
    con = conexion()
    existentes = {
        r["nombre"].strip().lower(): dict(r)
        for r in con.execute(
            "SELECT id, nombre, apodo, rol, telefono, email, equipo_id "
            "FROM participantes"
        )
    }
    nuevos = repetidos = 0
    for fila in filas:
        nombre = (fila.get("nombre") or "").strip()
        if not nombre:
            continue
        nombre_equipo = (fila.get("equipo") or "").strip()
        if nombre.lower() in existentes:
            repetidos += 1
            actual = existentes[nombre.lower()]
            # Completar SOLO campos vacíos, sin tocar lo ya relleno
            for campo in ("apodo", "rol", "telefono", "email"):
                valor = (fila.get(campo) or "").strip()
                if valor and not (actual.get(campo) or "").strip():
                    con.execute(f"UPDATE participantes SET {campo} = ? WHERE id = ?",
                                (valor, actual["id"]))
                    actual[campo] = valor
            if nombre_equipo and not actual.get("equipo_id"):
                equipo_id = _buscar_o_crear_equipo(con, nombre_equipo)
                con.execute("UPDATE participantes SET equipo_id = ?, "
                            "revelado_en = NULL WHERE id = ?",
                            (equipo_id, actual["id"]))
                actual["equipo_id"] = equipo_id
            continue
        equipo_id = None
        if nombre_equipo:
            equipo_id = _buscar_o_crear_equipo(con, nombre_equipo)
        cur = con.execute(
            "INSERT INTO participantes (nombre, apodo, rol, telefono, email, "
            "equipo_id, token) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nombre, (fila.get("apodo") or "").strip(), (fila.get("rol") or "").strip(),
             (fila.get("telefono") or "").strip(),
             (fila.get("email") or "").strip(), equipo_id, _token_nuevo(con)),
        )
        existentes[nombre.lower()] = {
            "id": cur.lastrowid, "nombre": nombre,
            "apodo": (fila.get("apodo") or "").strip(),
            "rol": (fila.get("rol") or "").strip(),
            "telefono": (fila.get("telefono") or "").strip(),
            "email": (fila.get("email") or "").strip(), "equipo_id": equipo_id,
        }
        nuevos += 1
    con.commit()
    con.close()
    return nuevos, repetidos


def listar_participantes() -> list[dict]:
    con = conexion()
    filas = con.execute(
        """
        SELECT p.*, e.nombre AS equipo_nombre, e.color AS equipo_color, e.emoji AS equipo_emoji
          FROM participantes p
          LEFT JOIN equipos e ON e.id = p.equipo_id
         ORDER BY p.nombre COLLATE NOCASE
        """
    ).fetchall()
    con.close()
    return [dict(f) for f in filas]


def participante(participante_id: int) -> dict | None:
    con = conexion()
    fila = con.execute(
        "SELECT * FROM participantes WHERE id = ?", (participante_id,)
    ).fetchone()
    con.close()
    return dict(fila) if fila else None


def participante_por_token(token: str) -> dict | None:
    """Busca por código. Primero tal cual (enlaces antiguos, que distinguen
    mayúsculas) y si no, sin distinguir mayúsculas ni guiones: quien teclea
    «k7 rq-4m» quiere entrar igual que quien escribe «K7RQ4M»."""
    con = conexion()
    fila = con.execute(
        "SELECT * FROM participantes WHERE token = ?", ((token or "").strip(),)
    ).fetchone()
    if fila is None:
        limpio = normalizar_codigo(token)
        if limpio:
            fila = con.execute(
                "SELECT * FROM participantes WHERE upper(token) = ?", (limpio,)
            ).fetchone()
    con.close()
    return dict(fila) if fila else None


def editar_participante(participante_id: int, nombre: str, telefono: str, email: str,
                        equipo_id: int | None, notas: str, apodo: str = "",
                        rol: str = "", tanda: str = "") -> None:
    con = conexion()
    actual = con.execute(
        "SELECT equipo_id FROM participantes WHERE id = ?", (participante_id,)
    ).fetchone()
    con.execute(
        "UPDATE participantes SET nombre = ?, apodo = ?, rol = ?, telefono = ?, "
        "email = ?, equipo_id = ?, notas = ?, tanda = ? WHERE id = ?",
        (nombre.strip(), apodo.strip(), rol.strip(), telefono.strip(), email.strip(),
         equipo_id, notas.strip(), tanda.strip(), participante_id),
    )
    if actual and actual["equipo_id"] != equipo_id:
        # Cambia de equipo → volverá a ver la animación del sorteo con el nuevo
        con.execute("UPDATE participantes SET revelado_en = NULL WHERE id = ?",
                    (participante_id,))
    con.commit()
    con.close()


def borrar_participante(participante_id: int) -> None:
    con = conexion()
    con.execute("DELETE FROM participantes WHERE id = ?", (participante_id,))
    con.commit()
    con.close()


def regenerar_token(participante_id: int) -> str:
    """Invalida el enlace anterior (p. ej. si se envió a la persona equivocada)."""
    con = conexion()
    token = _token_nuevo(con)
    con.execute(
        "UPDATE participantes SET token = ?, visto_en = NULL, revelado_en = NULL "
        "WHERE id = ?",
        (token, participante_id),
    )
    con.commit()
    con.close()
    return token


def marcar_visto(participante_id: int) -> None:
    con = conexion()
    con.execute(
        "UPDATE participantes SET visto_en = ? WHERE id = ? AND visto_en IS NULL",
        (ahora(), participante_id),
    )
    con.commit()
    con.close()


def marcar_revelado(participante_id: int) -> None:
    """El participante ya ha visto la animación del sorteo de su equipo."""
    con = conexion()
    con.execute(
        "UPDATE participantes SET revelado_en = ? WHERE id = ? AND revelado_en IS NULL",
        (ahora(), participante_id),
    )
    con.commit()
    con.close()


def poner_asistencia(participante_id: int, viene: bool) -> None:
    con = conexion()
    con.execute(
        "UPDATE participantes SET confirmado = ?, confirmado_en = ? WHERE id = ?",
        (1 if viene else -1, ahora(), participante_id),
    )
    con.commit()
    con.close()


def resumen() -> dict:
    con = conexion()

    def contar(sql: str) -> int:
        return con.execute(sql).fetchone()[0]

    datos = {
        "participantes": contar("SELECT COUNT(*) FROM participantes"),
        "confirmados":   contar("SELECT COUNT(*) FROM participantes WHERE confirmado = 1"),
        "no_vienen":     contar("SELECT COUNT(*) FROM participantes WHERE confirmado = -1"),
        "pendientes":    contar("SELECT COUNT(*) FROM participantes WHERE confirmado = 0"),
        "han_abierto":   contar("SELECT COUNT(*) FROM participantes WHERE visto_en IS NOT NULL"),
        "sin_equipo":    contar("SELECT COUNT(*) FROM participantes WHERE equipo_id IS NULL"),
        "equipos":       contar("SELECT COUNT(*) FROM equipos"),
        "actividades":   contar("SELECT COUNT(*) FROM agenda"),
        "lugares":       contar("SELECT COUNT(*) FROM lugares"),
        # Para saber de un vistazo qué queda por preparar
        "con_tanda":     contar("SELECT COUNT(*) FROM participantes "
                                "WHERE trim(tanda) != ''"),
        "con_vuelta":    contar("SELECT COUNT(*) FROM participantes "
                                "WHERE trim(tiempo_karts) != '' "
                                "   OR trim(tiempo_final) != ''"),
        "con_capitan":   contar("SELECT COUNT(*) FROM equipos "
                                "WHERE capitan_id IS NOT NULL"),
        "con_sala":      contar("SELECT COUNT(*) FROM equipos "
                                "WHERE trim(sala) != ''"),
        "con_salida":    contar("SELECT COUNT(*) FROM equipos "
                                "WHERE trim(tiempo_escape) != ''"),
        "reglas":        contar("SELECT COUNT(DISTINCT trim(grupo_sorteo)) "
                                "FROM participantes WHERE trim(grupo_sorteo) != ''"),
    }
    datos["sin_abrir"] = [
        r["nombre"] for r in con.execute(
            "SELECT nombre FROM participantes WHERE visto_en IS NULL "
            "ORDER BY nombre COLLATE NOCASE"
        )
    ]
    con.close()
    return datos


# ------------------------------------------------------------------ lugares

def crear_lugar(nombre: str, direccion: str, maps: str, notas: str) -> int:
    con = conexion()
    cur = con.execute(
        "INSERT INTO lugares (nombre, direccion, maps, notas) VALUES (?, ?, ?, ?)",
        (nombre.strip(), direccion.strip(), maps.strip(), notas.strip()),
    )
    con.commit()
    con.close()
    return cur.lastrowid


def editar_lugar(lugar_id: int, nombre: str, direccion: str, maps: str, notas: str) -> None:
    con = conexion()
    con.execute(
        "UPDATE lugares SET nombre = ?, direccion = ?, maps = ?, notas = ? WHERE id = ?",
        (nombre.strip(), direccion.strip(), maps.strip(), notas.strip(), lugar_id),
    )
    con.commit()
    con.close()


def borrar_lugar(lugar_id: int) -> None:
    con = conexion()
    con.execute("DELETE FROM lugares WHERE id = ?", (lugar_id,))
    con.commit()
    con.close()


def listar_lugares() -> list[dict]:
    con = conexion()
    filas = con.execute("SELECT * FROM lugares ORDER BY nombre COLLATE NOCASE").fetchall()
    con.close()
    return [dict(f) for f in filas]


def lugar(lugar_id: int) -> dict | None:
    con = conexion()
    fila = con.execute("SELECT * FROM lugares WHERE id = ?", (lugar_id,)).fetchone()
    con.close()
    return dict(fila) if fila else None


# ------------------------------------------------------------------ agenda

def crear_actividad(hora: str, hora_fin: str, actividad: str, descripcion: str,
                    lugar_id: int | None, equipo_id: int | None) -> int:
    con = conexion()
    cur = con.execute(
        "INSERT INTO agenda (hora, hora_fin, actividad, descripcion, lugar_id, equipo_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (normalizar_hora(hora), normalizar_hora(hora_fin), actividad.strip(),
         descripcion.strip(), lugar_id, equipo_id),
    )
    con.commit()
    con.close()
    return cur.lastrowid


def editar_actividad(actividad_id: int, hora: str, hora_fin: str, actividad: str,
                     descripcion: str, lugar_id: int | None, equipo_id: int | None) -> None:
    con = conexion()
    con.execute(
        "UPDATE agenda SET hora = ?, hora_fin = ?, actividad = ?, descripcion = ?, "
        "lugar_id = ?, equipo_id = ? WHERE id = ?",
        (normalizar_hora(hora), normalizar_hora(hora_fin), actividad.strip(),
         descripcion.strip(), lugar_id, equipo_id, actividad_id),
    )
    con.commit()
    con.close()


def borrar_actividad(actividad_id: int) -> None:
    con = conexion()
    con.execute("DELETE FROM agenda WHERE id = ?", (actividad_id,))
    con.commit()
    con.close()


_SQL_AGENDA = """
    SELECT a.*, l.nombre AS lugar_nombre, l.direccion AS lugar_direccion,
           l.maps AS lugar_maps,
           e.nombre AS equipo_nombre, e.color AS equipo_color, e.emoji AS equipo_emoji
      FROM agenda a
      LEFT JOIN lugares l ON l.id = a.lugar_id
      LEFT JOIN equipos e ON e.id = a.equipo_id
"""


def listar_agenda() -> list[dict]:
    con = conexion()
    filas = con.execute(_SQL_AGENDA + " ORDER BY a.hora, a.id").fetchall()
    con.close()
    return [dict(f) for f in filas]


ORDINALES = {"1": "1ª", "2": "2ª", "3": "3ª"}


def _cita(hora: str, titulo: str, descripcion: str, lugar_id, lugares) -> dict:
    """Una actividad que no está en la tabla de agenda, sino en la configuración."""
    lugar = next((l for l in lugares if str(l["id"]) == str(lugar_id or "")), None)
    return {"id": None, "hora": hora, "hora_fin": "", "actividad": titulo,
            "descripcion": descripcion, "lugar_id": lugar["id"] if lugar else None,
            "equipo_id": None,
            "lugar_nombre": lugar["nombre"] if lugar else "",
            "lugar_direccion": lugar["direccion"] if lugar else "",
            "lugar_maps": lugar["maps"] if lugar else "",
            "equipo_nombre": None, "equipo_color": None, "equipo_emoji": None}


def citas_de_la_configuracion(sala: str = "", tanda: str = "") -> list[dict]:
    """La escape room y las tandas de karts, sacadas de ⚙️ Evento.

    Sus horas se configuran ahí, no en la agenda, y antes eso hacía que no
    aparecieran en el programa del día: se veía solo la comida. Se generan
    aquí para que programa y configuración no puedan descuadrarse nunca.
    """
    cfg = leer_config()
    lugares = listar_lugares()
    citas = []
    hora_escape = (cfg.get("escape_hora") or "").strip()
    if hora_escape:
        detalle = " · ".join(x for x in (
            f"Vuestra sala: {sala}" if sala else "",
            (cfg.get("escape_nota") or "").strip()) if x)
        citas.append(_cita(
            hora_escape, cfg.get("escape_titulo") or "Escape room", detalle,
            cfg.get("escape_lugar_id"), lugares))
    for numero in ("1", "2", "3"):
        hora = (cfg.get(f"karts_hora{numero}") or "").strip()
        if not hora:
            continue
        citas.append(_cita(
            hora, f'{cfg.get("karts_nombre") or "Karts"} · {ORDINALES[numero]} tanda',
            "👉 Te toca a ti" if tanda == numero else "",
            cfg.get("karts_lugar_id"), lugares))
    return citas


def agenda_para(equipo_id: int | None, sala: str = "", tanda: str = "") -> list[dict]:
    """Agenda que ve un participante: lo general + lo específico de su equipo."""
    con = conexion()
    if equipo_id is None:
        filas = con.execute(
            _SQL_AGENDA + " WHERE a.equipo_id IS NULL ORDER BY a.hora, a.id"
        ).fetchall()
    else:
        filas = con.execute(
            _SQL_AGENDA + " WHERE a.equipo_id IS NULL OR a.equipo_id = ? "
                          "ORDER BY a.hora, a.id",
            (equipo_id,),
        ).fetchall()
    con.close()
    items = [dict(f) for f in filas]
    # Si alguien ya puso a mano una actividad a esa hora, se respeta la suya
    horas_puestas = {(i["hora"] or "").strip() for i in items}
    items += [c for c in citas_de_la_configuracion(sala, tanda)
              if c["hora"] not in horas_puestas]
    return sorted(items, key=lambda i: ((i["hora"] or "99:99"), i["id"] or 0))


def actividad(actividad_id: int) -> dict | None:
    con = conexion()
    fila = con.execute("SELECT * FROM agenda WHERE id = ?", (actividad_id,)).fetchone()
    con.close()
    return dict(fila) if fila else None
