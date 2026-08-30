"""
Pruebas de NeaEvento. Se ejecutan solas y no tocan tus datos: crean un evento
de mentira en una base de datos temporal.

    python pruebas.py

Cubren lo que no se puede revisar «a ojo»: que el sorteo respete las reglas,
que los puntos salgan bien, que cada uno vea lo suyo y que la copia de
seguridad recupere el evento tal cual.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from collections import Counter

# Base de datos temporal ANTES de importar la app (la lee al arrancar)
os.environ["EVENTO_DB_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="neaevento_pruebas_"), "evento.db")
os.environ.pop("EVENTO_ADMIN_PASSWORD", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as modulo_app  # noqa: E402
import db  # noqa: E402
import paginas  # noqa: E402

app = modulo_app.app
app.config["TESTING"] = True
c = app.test_client()
fallos: list[str] = []


def ok(condicion, mensaje: str) -> None:
    print(("  ✔" if condicion else "  ✘ FALLO"), mensaje)
    if not condicion:
        fallos.append(mensaje)


def titulo(texto: str) -> None:
    print(f"\n{texto}")


# ------------------------------------------------------------ 1. Participantes
titulo("Participantes")
LISTA = (
    "nombre;apodo;rol;telefono\n"
    "Ana Comercial;Ana;comercial;600111222\n"
    "Bea Comercial;Bea;comercial;600111223\n"
    "Carlos Comercial;Carlos;comercial;\n"
    "Diana Comercial;Diana;comercial;\n"
    "Elena Tecnica;Elena;tecnico;\n"
    "Félix Tecnico;Félix;tecnico;\n"
    "Gonzalo Tecnico;Gonzalo;tecnico;\n"
    "Hugo Tecnico;Hugo;tecnico;\n"
).encode("utf-8")
r = c.post("/admin/participantes/importar",
           data={"fichero": (io.BytesIO(LISTA), "lista.csv")},
           content_type="multipart/form-data", follow_redirects=True)
ok("Importados 8" in r.text, "se importan 8 participantes de un CSV")
r = c.post("/admin/participantes/importar",
           data={"fichero": (io.BytesIO(LISTA), "lista.csv")},
           content_type="multipart/form-data", follow_redirects=True)
ok("Otros 8 ya existían" in r.text, "re-importar la misma lista no duplica a nadie")
ok(len(db.listar_participantes()) == 8, "siguen siendo 8")
ok(all(p["token"] for p in db.listar_participantes()), "todos tienen enlace personal")


# ------------------------------------------------- 2. Equipos, reglas y sorteo
titulo("Sorteo de equipos")
c.post("/admin/equipos/nuevo", data={"nombres": "Rojo, Azul"})
ok(len(db.listar_equipos()) == 2, "se crean los equipos de una vez")


def pid(nombre: str) -> int:
    return next(p["id"] for p in db.listar_participantes() if p["nombre"] == nombre)


c.post("/admin/juntos/nuevo", data={"ids": [str(pid("Ana Comercial")),
                                            str(pid("Hugo Tecnico"))]})
r = c.post("/admin/juntos/nuevo", data={"ids": [str(pid("Bea Comercial"))]},
           follow_redirects=True)
ok("al menos a 2" in r.text, "una sola persona no forma una regla de «van juntos»")

mal_juntos = mal_tam = 0
peor_rol = 0
for _ in range(60):
    db.sortear(todos=True)
    lista = db.listar_participantes()
    equipo_de = {p["nombre"]: p["equipo_id"] for p in lista}
    if equipo_de["Ana Comercial"] != equipo_de["Hugo Tecnico"]:
        mal_juntos += 1
    tam = Counter(p["equipo_id"] for p in lista)
    if sorted(tam.values()) != [4, 4]:
        mal_tam += 1
    for eq in db.listar_equipos():
        roles = Counter(p["rol"] for p in lista if p["equipo_id"] == eq["id"])
        peor_rol = max(peor_rol, abs(roles["comercial"] - roles["tecnico"]))
ok(mal_juntos == 0, "60 sorteos: los unidos con una regla caen SIEMPRE juntos")
ok(mal_tam == 0, "60 sorteos: los equipos quedan siempre igualados (4 y 4)")
ok(peor_rol <= 1, f"60 sorteos: los roles se reparten (diferencia máxima {peor_rol})")

n = db.sortear_capitanes()
ok(n == 2, "se sortea un capitán por equipo")
ok(all(db.participante(eq["capitan_id"])["equipo_id"] == eq["id"]
       for eq in db.listar_equipos()), "cada capitán es de su propio equipo")


# ------------------------------------------------------- 3. Salas de la escape
titulo("Salas de la escape room")
db.guardar_config({"escape_salas": "Luxor: pirámide\nInfamia: submarino"})
salas = db.parsear_salas(db.leer_config()["escape_salas"])
ok([s["nombre"] for s in salas] == ["Luxor", "Infamia"], "se leen las salas escritas")
equipo_rojo = next(eq["id"] for eq in db.listar_equipos() if eq["nombre"] == "Rojo")
for _ in range(40):
    db.sortear_salas(salas, sala_excluida="Infamia", equipo_excluido=equipo_rojo)
    asignadas = {eq["id"]: eq["sala"] for eq in db.listar_equipos()}
    if asignadas[equipo_rojo] == "Infamia" or len(set(asignadas.values())) != 2:
        ok(False, "40 sorteos de salas con restricción")
        break
else:
    ok(True, "40 sorteos de salas: una por equipo y la excluida nunca a ese equipo")
try:
    db.sortear_salas(salas[:1])
    ok(False, "sortear con menos salas que equipos debe avisar")
except ValueError as exc:
    ok("deben coincidir" in str(exc), "avisa si no hay una sala por equipo")


# ------------------------------------------------------- 4. Tandas de los karts
titulo("Tandas de karts")
n1, n2, n3 = db.sortear_tandas()
ok((n1, n2, n3) == (8, 0, 0) or n1 + n2 + n3 == 8,
   f"todos entran en alguna tanda ({n1}+{n2}+{n3})")
ok(all((p.get("tanda") or "") in ("1", "2", "3") for p in db.listar_participantes()),
   "nadie se queda sin tanda")


# ------------------------------------------------------------------ 5. Puntos
titulo("Puntos y clasificación")
ok(db.parsear_tiempo_vuelta("1:02.451") == 62451, "se entiende una vuelta 1:02.451")
ok(db.parsear_tiempo_vuelta("48,3") == 48300, "se entiende una vuelta 48,3")
ok(db.parsear_tiempo_vuelta("34.567") == 34567 and db.parsear_tiempo_vuelta("34.5") == 34500,
   "las milésimas cuentan, y con menos decimales no se desplazan")
ok(db.parsear_tiempo_vuelta("1'02.451") == 62451, "también con apóstrofo, como el circuito")
ok(db.parsear_tiempo_vuelta("48.123") < db.parsear_tiempo_vuelta("48.124"),
   "una milésima decide quién va delante")
ok(db.parsear_hora_dia("10:05") == 36300, "se entiende una hora de salida 10:05")
ok(db.parsear_tiempo_vuelta("lo que sea") is None, "un texto raro no puntúa")

equipos = db.listar_equipos()
c.post("/admin/puntos/escape", data={f"tiempo_{equipos[0]['id']}": "10:10",
                                     f"tiempo_{equipos[1]['id']}": "09:55",
                                     "puntos_escape": "20, 10"})
lista = db.listar_participantes()
c.post("/admin/puntos/karts",
       data={f"tiempo_{p['id']}": f"{40 + i}.000" for i, p in enumerate(lista)})
clasif = db.clasificacion()
puntos_escape = {f["equipo"]["id"]: f["escape"] for f in clasif["equipos"]}
ok(puntos_escape[equipos[1]["id"]] == 20 and puntos_escape[equipos[0]["id"]] == 10,
   "en la escape, salir antes da más puntos")
ok(clasif["karts"][0]["puntos"] == 8 and clasif["karts"][-1]["puntos"] == 1,
   "en los karts puntúan todos: 8 al más rápido y 1 al último")
ok(clasif["equipos"][0]["total"] >= clasif["equipos"][-1]["total"],
   "la clasificación va ordenada por puntos")

# empate a la milésima: los dos se llevan los mismos puntos
dos = db.listar_participantes()[:2]
for x in dos:
    db.poner_tiempo_karts(x["id"], "0:42.500")
filas = {f["participante"]["id"]: f["puntos"] for f in db.clasificacion()["karts"]}
ok(filas[dos[0]["id"]] == filas[dos[1]["id"]],
   "dos vueltas idénticas puntúan igual (no decide el orden de la lista)")
for i, x in enumerate(dos):     # se deshace el empate para lo que viene después
    db.poner_tiempo_karts(x["id"], f"0:42.5{i + 1}0")


# --------------------------------------------- 6. Lo que ve cada participante
titulo("La página del participante")
capitan = db.participante(db.listar_equipos()[0]["capitan_id"])
otro = next(p for p in db.listar_participantes()
            if p["equipo_id"] == capitan["equipo_id"] and p["id"] != capitan["id"])

r = c.get(f"/p/{capitan['token']}")
ok("Dale al sorteo" in r.text, "la primera visita enseña la animación del sorteo")
ok("Programa del día" not in r.text, "el sorteo no destripa el programa")
c.post(f"/p/{capitan['token']}/revelado")
r = c.get(f"/p/{capitan['token']}")
ok(f"¡Hola, {paginas.nombre_corto(capitan)}!" in r.text, "después le saluda por su nombre")
ok("Eres el capitán" in r.text, "el capitán ve su formulario de la hora de salida")
r = c.get(f"/p/{otro['token']}")
ok("Eres el capitán" not in r.text, "los demás no lo ven")
ok(c.post(f"/p/{otro['token']}/tiempo_escape",
          data={"tiempo": "09:00"}).status_code == 403,
   "y tampoco pueden guardar la hora del equipo")
r = c.post(f"/p/{capitan['token']}/tiempo_escape", data={"tiempo": "no es una hora"},
           follow_redirects=True)
ok("no se entiende" in r.text, "una hora mal escrita se rechaza con un aviso")

r = c.get(f"/p/{capitan['token']}")
ok("no-store" in r.headers.get("Cache-Control", ""),
   "la página no se guarda en caché (el móvil ve siempre lo de ahora)")
r = c.get("/assets/neamaster_horizontal.png")
ok(r.status_code == 200 and "no-store" not in r.headers.get("Cache-Control", ""),
   "pero el logo sí se puede guardar (no se descarga cada vez)")

r = c.get(f"/p/{capitan['token']}/equipo.json")
ok(r.status_code == 200 and r.json["dentro"], "el equipo se puede consultar en directo")
ok(c.get("/p/inventado").status_code == 404, "un enlace inventado no existe")
malo = db.crear_participante("<script>alert(1)</script>")
r = c.get(f"/p/{db.participante(malo)['token']}")
ok("<script>alert(1)</script>" not in r.text, "los nombres se escapan (sin HTML colado)")
db.borrar_participante(malo)


# ---------------------------------------- 7. Cada piloto apunta su vuelta
titulo("Cada piloto mete su tiempo de karts")


def pon_tanda(persona: dict, valor: str) -> dict:
    """Cambia la tanda de alguien desde el panel (como haría el organizador)."""
    c.post(f"/admin/participantes/{persona['id']}/guardar",
           data={"nombre": persona["nombre"], "apodo": persona.get("apodo") or "",
                 "rol": persona.get("rol") or "",
                 "telefono": persona.get("telefono") or "",
                 "email": persona.get("email") or "",
                 "equipo_id": persona["equipo_id"] or "",
                 "notas": persona.get("notas") or "", "tanda": valor})
    return db.participante(persona["id"])


pilotos = [p for p in db.listar_participantes()
           if (p.get("tanda") or "").strip() in ("1", "2")]
# Tiempos a mano: los dos primeros vuelan, el resto van más lentos
for i, x in enumerate(pilotos):
    db.poner_tiempo_karts(x["id"], f"0:4{i}.100" if i < 2 else f"1:0{i}.500")
rapidos, piloto = pilotos[:2], pilotos[2]
for x in pilotos:
    db.marcar_revelado(x["id"])

r = c.get(f"/p/{piloto['token']}")
ok("Tu vuelta en la" in r.text, "cada uno ve el hueco de su tanda")
ok("Tu vuelta en la final" not in r.text, "quien no pasa no tiene hueco extra")
ok("Pasas a la final" not in r.text, "ni enhorabuena")

estado = db.estado_final()
ok(estado["cerrado"] and [x["id"] for x in estado["por_tiempo"]]
   == [x["id"] for x in rapidos], "con todos los tiempos, pasan los 2 mejores")
r = c.get(f"/p/{rapidos[0]['token']}")
ok("Pasas a la final" in r.text, "y a ellos se lo dice la app, sin que nadie los marque")
ok("Tu vuelta en la final" in r.text, "con su hueco para la vuelta de la 3ª tanda")
ok("Has pasado a la final" in r.text, "y el aviso en su programa")
ok(c.get(f"/p/{rapidos[0]['token']}/equipo.json").json["final"] is True,
   "el sondeo del móvil lleva la bandera (para enterarse sin recargar)")

# Mientras falte una vuelta por apuntar no se canta nada: sería una alegría en falso
db.poner_tiempo_karts(piloto["id"], "")
ok(not db.estado_final()["cerrado"], "sin todos los tiempos, la final no está decidida")
r = c.get(f"/p/{rapidos[0]['token']}")
ok("Pasas a la final" not in r.text and "Tu vuelta en la final" not in r.text,
   "y nadie recibe la enhorabuena todavía")
ok("falta 1 tiempo por apuntar" in r.text, "se dice cuántos tiempos faltan")
ok(c.post(f"/p/{rapidos[0]['token']}/tiempo_karts",
          data={"tiempo_final": "40.0"}).status_code == 403,
   "y tampoco se puede colar un tiempo de la final")
c.post(f"/p/{piloto['token']}/tiempo_karts", data={"tiempo": "1:02.500"})
ok(db.estado_final()["cerrado"], "en cuanto apunta el último, ya está decidida")

r = c.post(f"/p/{piloto['token']}/tiempo_karts", data={"tiempo": "rapidísimo"},
           follow_redirects=True)
ok("no se entiende" in r.text, "un tiempo mal escrito se rechaza con un aviso")
ok(db.participante(piloto["id"])["tiempo_karts"] == "1:02.500",
   "y no se borra el que ya estaba")

# El panel manda: se puede meter a alguien a mano (si se queda sin móvil, p. ej.)
c.post("/admin/puntos/karts", data={"finalista": str(piloto["id"])})
ok(db.corre_la_final(db.participante(piloto["id"])),
   "el panel puede meter a alguien a mano")
r = c.get(f"/p/{piloto['token']}")
ok("Tu vuelta en la final" in r.text, "y se le abre su hueco igual")
formulario = r.text.split(
    f'action="/p/{piloto["token"]}/tiempo_karts"')[1].split("</form>")[0]
ok('name="tiempo"' in formulario and 'name="tiempo_final"' in formulario
   and formulario.count("submit") == 1,
   "las dos vueltas van en el mismo formulario, con un solo Guardar")
c.post(f"/p/{piloto['token']}/tiempo_karts",
       data={"tiempo": "1:02.500", "tiempo_final": "0:39.900"})
piloto = db.participante(piloto["id"])
ok(piloto["tiempo_karts"] == "1:02.500" and piloto["tiempo_final"] == "0:39.900",
   "las dos vueltas se guardan de una vez, sin pisarse")
fila = next(f for f in db.clasificacion()["karts"]
            if f["participante"]["id"] == piloto["id"])
ok(fila["tiempo"] == "0:39.900", "para los puntos cuenta la mejor de las dos")

piloto = pon_tanda(piloto, "3")
r = c.get(f"/p/{piloto['token']}")
ok("Tu vuelta en la final" in r.text and "Tu vuelta en la 3ª tanda" not in r.text,
   "quien sale ya en la 3ª tanda solo tiene un hueco")
pon_tanda(piloto, "1")

r = c.get("/admin/puntos")
ok("pasan a la final" in r.text, "el panel dice quién pasa")


# ----------------------------------------- 8. Fin de fiesta: quién tiene premio
titulo("Cierre de la Olimpiada y premios")
r = c.get(f"/p/{piloto['token']}")
ok("Cómo se ganan los puntos" in r.text, "todos tienen el tutorial de los puntos")
ok("Lo que te toca a ti" in r.text, "y sus deberes: apuntar su vuelta")
ok("recoger tu premio" not in r.text, "sin cerrar, nadie recibe felicitación")

campeon = db.clasificacion()["equipos"][0]["equipo"]
premios = db.ganadores(db.clasificacion())
ok(premios["equipos"] and premios["equipos"][0]["id"] == campeon["id"],
   "db.ganadores() señala al equipo con más puntos")
ok(len(premios["pilotos"]) >= 1, "y a la vuelta rápida del día")

c.post("/admin/puntos/final", data={"valor": "1"})
uno_del_campeon = next(x for x in db.listar_participantes()
                       if x["equipo_id"] == campeon["id"])
db.marcar_revelado(uno_del_campeon["id"])
r = c.get(f"/p/{uno_del_campeon['token']}")
ok("Campeones" in r.text, "el campeón ve que ha ganado")
ok("recoger tu premio en los postres" in r.text, "y que recoge el premio en los postres")

rapido = premios["pilotos"][0]
db.marcar_revelado(rapido["id"])
r = c.get(f"/p/{rapido['token']}")
ok("premio en los postres" in r.text, "el más rápido también tiene premio")

# alguien que no gane nada: ni equipo campeón (puede haber empate) ni vuelta rápida
ganadores_ = {x["id"] for x in premios["equipos"]}
perdedor = next((x for x in db.listar_participantes()
                 if x["equipo_id"] and x["equipo_id"] not in ganadores_
                 and x["id"] not in [y["id"] for y in premios["pilotos"]]), None)
if perdedor:
    db.marcar_revelado(perdedor["id"])
    r = c.get(f"/p/{perdedor['token']}")
    ok("Se acabó la Olimpiada" in r.text and "Campeones" not in r.text,
       "el resto ve el resultado, sin felicitación")
    ok("¿Contamos contigo" not in r.text,
       "y ya no se le pregunta si viene: el evento ha terminado")

c.post("/admin/puntos/final", data={"valor": ""})
r = c.get(f"/p/{uno_del_campeon['token']}")
ok("Campeones" not in r.text, "se puede retirar el resultado si se publicó por error")


# ------------------------------------------------------- 9. Copia de seguridad
titulo("Copia de seguridad")
copia = c.get("/admin/copia.db").data
ok(copia.startswith(b"SQLite format 3\x00"), "la copia se descarga")
antes = len(db.listar_participantes())
for p in db.listar_participantes():
    db.borrar_participante(p["id"])
r = c.post("/admin/restaurar", data={"fichero": (io.BytesIO(copia), "copia.db")},
           content_type="multipart/form-data", follow_redirects=True)
ok(len(db.listar_participantes()) == antes, "restaurar recupera el evento entero")
r = c.post("/admin/restaurar", data={"fichero": (io.BytesIO(b"no soy una copia"), "x.db")},
           content_type="multipart/form-data", follow_redirects=True)
ok("no es una copia" in r.text, "un fichero que no es una copia se rechaza")


# -------------------------------------------------------------- 10. Resultado
print()
if fallos:
    print(f"❌ {len(fallos)} fallo(s):")
    for f in fallos:
        print("   ·", f)
    raise SystemExit(1)
print("✅ TODO CORRECTO")
