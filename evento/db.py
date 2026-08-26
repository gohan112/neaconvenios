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
    "nombre": "Evento del día 12",
    "fecha": "2026-09-12",
    "hora": "09:00",
    "descripcion": "¡Bienvenido/a! Aquí tienes tu equipo, el programa del día y los "
                   "lugares. Confirma tu asistencia más abajo.",
    "url_base": "",
    "contacto": "",
    "msg_whatsapp": "¡Hola, {nombre}! Este es tu enlace personal para el evento: {enlace}\n"
                    "Dentro verás tu equipo, el programa del día y los lugares. "
                    "¡Entra y confirma tu asistencia!",
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
  descripcion TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS participantes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre        TEXT NOT NULL,
  telefono      TEXT NOT NULL DEFAULT '',
  email         TEXT NOT NULL DEFAULT '',
  equipo_id     INTEGER REFERENCES equipos(id) ON DELETE SET NULL,
  token         TEXT NOT NULL UNIQUE,
  visto_en      TEXT,                          -- primera vez que abrió su enlace
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


def _token_nuevo(con: sqlite3.Connection) -> str:
    while True:
        token = secrets.token_urlsafe(6)  # 8 caracteres, aptos para URL
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
        "SELECT id, nombre FROM participantes WHERE equipo_id = ? ORDER BY nombre COLLATE NOCASE",
        (equipo_id,),
    ).fetchall()
    con.close()
    return [dict(f) for f in filas]


def sortear(todos: bool = False) -> int:
    """
    Reparte participantes entre los equipos de forma aleatoria y EQUILIBRADA
    (cada persona va al equipo que menos gente tenga en ese momento).

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
        con.execute("UPDATE participantes SET equipo_id = NULL")
    pendientes = [r["id"] for r in con.execute(
        "SELECT id FROM participantes WHERE equipo_id IS NULL"
    )]
    tam = {
        eid: con.execute(
            "SELECT COUNT(*) FROM participantes WHERE equipo_id = ?", (eid,)
        ).fetchone()[0]
        for eid in ids_equipos
    }
    random.shuffle(pendientes)
    for pid in pendientes:
        minimo = min(tam.values())
        eid = random.choice([i for i in ids_equipos if tam[i] == minimo])
        con.execute("UPDATE participantes SET equipo_id = ? WHERE id = ?", (eid, pid))
        tam[eid] += 1
    con.commit()
    con.close()
    return len(pendientes)


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
                       equipo_id: int | None = None) -> int:
    con = conexion()
    cur = con.execute(
        "INSERT INTO participantes (nombre, telefono, email, equipo_id, token) "
        "VALUES (?, ?, ?, ?, ?)",
        (nombre.strip(), telefono.strip(), email.strip(), equipo_id, _token_nuevo(con)),
    )
    con.commit()
    con.close()
    return cur.lastrowid


def importar(filas: list[dict]) -> tuple[int, int]:
    """
    Importa participantes [{nombre, telefono, email, equipo}]. Si el equipo no
    existe se crea. Los nombres ya existentes (sin distinguir mayúsculas) se
    omiten para poder re-importar la misma lista sin duplicar.
    Devuelve (añadidos, omitidos).
    """
    con = conexion()
    existentes = {
        r["nombre"].strip().lower()
        for r in con.execute("SELECT nombre FROM participantes")
    }
    nuevos = omitidos = 0
    for fila in filas:
        nombre = (fila.get("nombre") or "").strip()
        if not nombre:
            continue
        if nombre.lower() in existentes:
            omitidos += 1
            continue
        equipo_id = None
        nombre_equipo = (fila.get("equipo") or "").strip()
        if nombre_equipo:
            equipo_id = _buscar_o_crear_equipo(con, nombre_equipo)
        con.execute(
            "INSERT INTO participantes (nombre, telefono, email, equipo_id, token) "
            "VALUES (?, ?, ?, ?, ?)",
            (nombre, (fila.get("telefono") or "").strip(),
             (fila.get("email") or "").strip(), equipo_id, _token_nuevo(con)),
        )
        existentes.add(nombre.lower())
        nuevos += 1
    con.commit()
    con.close()
    return nuevos, omitidos


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
    con = conexion()
    fila = con.execute(
        "SELECT * FROM participantes WHERE token = ?", ((token or "").strip(),)
    ).fetchone()
    con.close()
    return dict(fila) if fila else None


def editar_participante(participante_id: int, nombre: str, telefono: str, email: str,
                        equipo_id: int | None, notas: str) -> None:
    con = conexion()
    con.execute(
        "UPDATE participantes SET nombre = ?, telefono = ?, email = ?, equipo_id = ?, "
        "notas = ? WHERE id = ?",
        (nombre.strip(), telefono.strip(), email.strip(), equipo_id, notas.strip(),
         participante_id),
    )
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
        "UPDATE participantes SET token = ?, visto_en = NULL WHERE id = ?",
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


def agenda_para(equipo_id: int | None) -> list[dict]:
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
    return [dict(f) for f in filas]


def actividad(actividad_id: int) -> dict | None:
    con = conexion()
    fila = con.execute("SELECT * FROM agenda WHERE id = ?", (actividad_id,)).fetchone()
    con.close()
    return dict(fila) if fila else None
