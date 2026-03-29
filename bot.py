import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
import datetime

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT
);
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ministerio TEXT, estado TEXT
);
CREATE TABLE IF NOT EXISTS oraciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT, user_id INTEGER
);
CREATE TABLE IF NOT EXISTS ayudas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, descripcion TEXT, aprobado INTEGER, asignado INTEGER
);
CREATE TABLE IF NOT EXISTS medicamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, stock INTEGER
);
CREATE TABLE IF NOT EXISTS casas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, anfitrion TEXT, direccion TEXT
);
CREATE TABLE IF NOT EXISTS servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, predicador TEXT, mensaje TEXT, coro TEXT, ofrendas TEXT
);
CREATE TABLE IF NOT EXISTS agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, evento TEXT
);
""")
conn.commit()

# ===== ESTADOS =====
user_states = {}

# ===== ROLES =====
def get_rol(uid):
    r = cursor.execute("SELECT rol FROM usuarios WHERE id=?", (uid,)).fetchone()
    return r[0] if r else None

def es_pastor(uid):
    return get_rol(uid) == "pastor"

def es_lider(uid):
    return get_rol(uid) == "lider"

# ===== MENÚ PRINCIPAL =====
def menu(chat_id):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("📋 Miembros", "🙏 Oración")
    m.add("🎁 Ayudas", "💊 Medicamentos")
    m.add("🏠 Casas de Paz", "⛪ Servicios")
    m.add("📅 Agenda", "⚙️ Administración")
    bot.send_message(chat_id, "Sistema Iglesia Monte de Dios", reply_markup=m)

def menu_mod(chat_id, nombre):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("➕ Agregar", "📄 Ver")
    m.add("🔙 Volver")
    bot.send_message(chat_id, nombre, reply_markup=m)

# ===== START =====
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.chat.id
    nombre = msg.from_user.first_name
    pastor = cursor.execute("SELECT * FROM usuarios WHERE rol='pastor'").fetchone()
    user = cursor.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()

    if not user:
        rol = "pastor" if not pastor else "miembro"
        cursor.execute("INSERT INTO usuarios VALUES (?,?,?)", (uid, nombre, rol))
        conn.commit()
        if rol == "pastor":
            bot.send_message(uid, "Bienvenido Pastor (primer acceso)")
        else:
            bot.send_message(uid, f"Bienvenido {nombre}, tu rol es Miembro")

    menu(uid)

# ===== HANDLER PRINCIPAL =====
@bot.message_handler(func=lambda m: True)
def manejar(m):
    uid = m.chat.id
    txt = m.text
    estado = user_states.get(uid)

    # ===== NAVEGACIÓN =====
    if txt == "🔙 Volver":
        user_states[uid] = None
        menu(uid)
        return

    # ===== MENÚS =====
    if txt == "📋 Miembros":
        user_states[uid] = "menu_miembros"
        menu_mod(uid, "Miembros")
        return
    if txt == "🙏 Oración":
        user_states[uid] = "menu_oracion"
        menu_mod(uid, "Oración")
        return
    if txt == "🎁 Ayudas":
        user_states[uid] = "menu_ayudas"
        menu_mod(uid, "Ayudas")
        return
    if txt == "💊 Medicamentos":
        user_states[uid] = "menu_medicamentos"
        menu_mod(uid, "Medicamentos")
        return
    if txt == "🏠 Casas de Paz":
        user_states[uid] = "menu_casas"
        menu_mod(uid, "Casas de Paz")
        return
    if txt == "⛪ Servicios":
        user_states[uid] = "menu_servicios"
        menu_mod(uid, "Servicios")
        return
    if txt == "📅 Agenda":
        user_states[uid] = "menu_agenda"
        menu_mod(uid, "Agenda")
        return
    if txt == "⚙️ Administración":
        if es_pastor(uid):
            data = cursor.execute("SELECT id,nombre,rol FROM usuarios").fetchall()
            bot.send_message(uid, "\n".join([str(d) for d in data]) or "Vacío")
        else:
            bot.send_message(uid, "Sin acceso")
        return

    # ===== AGREGAR =====
    if txt == "➕ Agregar":
        if estado == "menu_miembros":
            user_states[uid] = "miembro"
            bot.send_message(uid, "Nombre (si quieres ministerio: Nombre - Ministerio):")
            return
        elif estado == "menu_oracion":
            user_states[uid] = "oracion"
            bot.send_message(uid, "Motivo de oración:")
            return
        elif estado == "menu_ayudas":
            if not es_pastor(uid):
                bot.send_message(uid, "Solo Pastor")
                return
            user_states[uid] = "ayuda"
            bot.send_message(uid, "Descripción de la ayuda:")
            return
        elif estado == "menu_medicamentos":
            if not es_pastor(uid):
                bot.send_message(uid, "Solo Pastor")
                return
            user_states[uid] = "med1"
            bot.send_message(uid, "Nombre del medicamento:")
            return
        elif estado == "menu_casas":
            user_states[uid] = "casa1"
            bot.send_message(uid, "Anfitrión:")
            return
        elif estado == "menu_servicios":
            user_states[uid] = "serv1"
            bot.send_message(uid, "Predicador:")
            return
        elif estado == "menu_agenda":
            user_states[uid] = "agenda"
            bot.send_message(uid, "Evento:")
            return

    # ===== VER =====
    if txt == "📄 Ver":
        if estado == "menu_miembros":
            data = cursor.execute("SELECT nombre,ministerio,estado FROM miembros").fetchall()
            bot.send_message(uid, "\n".join([f"{d[0]} ({d[1]}) - {d[2]}" for d in data]) or "Vacío")
            return
        if estado == "menu_oracion":
            data = cursor.execute("SELECT texto,user_id FROM oraciones").fetchall()
            filtrado = [d for d in data if d[1] == uid or es_pastor(uid)]
            bot.send_message(uid, "\n".join([d[0] for d in filtrado]) or "Vacío")
            return
        if estado == "menu_ayudas":
            data = cursor.execute("SELECT descripcion FROM ayudas").fetchall()
            bot.send_message(uid, "\n".join([d[0] for d in data]) or "Vacío")
            return
        if estado == "menu_medicamentos":
            data = cursor.execute("SELECT nombre,stock FROM medicamentos").fetchall()
            bot.send_message(uid, "\n".join([f"{d[0]} - {d[1]}" for d in data]) or "Vacío")
            return

    # ===== FLUJOS POR ESTADO =====
    if estado == "miembro":
        nombre, *ministerio = txt.split(" - ")
        ministerio = ministerio[0] if ministerio else ""
        estado_m = "activo" if es_pastor(uid) else "pendiente"
        cursor.execute("INSERT INTO miembros (nombre,ministerio,estado) VALUES (?,?,?)",(nombre,ministerio,estado_m))
        conn.commit()
        bot.send_message(uid, "Miembro guardado")
        user_states[uid] = None
        menu(uid)
        return

    if estado == "oracion":
        cursor.execute("INSERT INTO oraciones (texto,user_id) VALUES (?,?)",(txt,uid))
        conn.commit()
        bot.send_message(uid, "Oración guardada")
        user_states[uid] = None
        menu(uid)
        return

    if estado == "ayuda":
        cursor.execute("INSERT INTO ayudas (descripcion,aprobado,asignado) VALUES (?,1,NULL)",(txt,))
        conn.commit()
        bot.send_message(uid, "Ayuda guardada")
        user_states[uid] = None
        menu(uid)
        return

    if estado == "med1":
        user_states[uid] = ("med2", txt)
        bot.send_message(uid, "Cantidad:")
        return

    if isinstance(estado, tuple) and estado[0] == "med2":
        nombre = estado[1]
        try:
            cantidad = int(txt)
        except:
            bot.send_message(uid, "Cantidad inválida")
            return
        cursor.execute("INSERT INTO medicamentos (nombre,stock) VALUES (?,?)",(nombre,cantidad))
        conn.commit()
        bot.send_message(uid, "Medicamento guardado")
        user_states[uid] = None
        menu(uid)
        return

    if estado == "casa1":
        user_states[uid] = ("casa2", txt)
        bot.send_message(uid, "Dirección:")
        return
    if isinstance(estado, tuple) and estado[0] == "casa2":
        cursor.execute("INSERT INTO casas (anfitrion,direccion) VALUES (?,?)",(estado[1],txt))
        conn.commit()
        bot.send_message(uid, "Casa de Paz guardada")
        user_states[uid] = None
        menu(uid)
        return

    if estado == "serv1":
        user_states[uid] = ("serv2", txt)
        bot.send_message(uid, "Mensaje:")
        return
    if isinstance(estado, tuple) and estado[0] == "serv2":
        user_states[uid] = ("serv3", estado[1], txt)
        bot.send_message(uid, "Coro:")
        return
    if isinstance(estado, tuple) and estado[0] == "serv3":
        predicador, mensaje = estado[1], estado[2]
        bot.send_message(uid, "Ofrendas (hasta 3 miembros, separados por coma):")
        user_states[uid] = ("serv4", predicador, mensaje)
        return
    if isinstance(estado, tuple) and estado[0] == "serv4":
        predicador, mensaje = estado[1], estado[2]
        coro = txt
        ofrendas = txt
        cursor.execute("INSERT INTO servicios (fecha,predicador,mensaje,coro,ofrendas) VALUES (?,?,?,?,?)",
                       (str(datetime.date.today()), predicador, mensaje, coro, ofrendas))
        conn.commit()
        bot.send_message(uid, "Servicio guardado")
        user_states[uid] = None
        menu(uid)
        return

    if estado == "agenda":
        cursor.execute("INSERT INTO agenda (fecha,evento) VALUES (?,?)",(str(datetime.date.today()),txt))
        conn.commit()
        bot.send_message(uid, "Evento guardado")
        user_states[uid] = None
        menu(uid)
        return

# ===== RUN =====
bot.infinity_polling()
