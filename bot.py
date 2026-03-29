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

# ===== TABLAS =====
cursor.executescript("""
CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT);
CREATE TABLE IF NOT EXISTS miembros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);
CREATE TABLE IF NOT EXISTS oraciones (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT, user_id INTEGER);
CREATE TABLE IF NOT EXISTS ayudas (id INTEGER PRIMARY KEY AUTOINCREMENT, descripcion TEXT, aprobado INTEGER);
CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, stock INTEGER);
CREATE TABLE IF NOT EXISTS casas (id INTEGER PRIMARY KEY AUTOINCREMENT, anfitrion TEXT, direccion TEXT);
CREATE TABLE IF NOT EXISTS servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, mensaje TEXT, predicador TEXT);
CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, evento TEXT);
""")
conn.commit()

# ===== ESTADOS =====
user_states = {}

# ===== ROLES =====
def get_rol(user_id):
    r = cursor.execute("SELECT rol FROM usuarios WHERE id=?", (user_id,)).fetchone()
    return r[0] if r else None

def es_pastor(user_id):
    return get_rol(user_id) == "pastor"

# ===== MENÚ PRINCIPAL =====
def menu(chat_id):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("📋 Miembros", "🙏 Oración")
    m.add("🎁 Ayudas", "💊 Medicamentos")
    m.add("🏠 Casas de Paz", "⛪ Servicios")
    m.add("📅 Agenda", "⚙️ Administración")
    bot.send_message(chat_id, "Sistema Iglesia FINAL", reply_markup=m)

# ===== MENÚ MÓDULO =====
def menu_mod(chat_id, nombre):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("➕ Agregar", "📄 Ver")
    m.add("🔙 Volver", "🏠 Inicio")
    bot.send_message(chat_id, nombre, reply_markup=m)

# ===== START AUTO PASTOR =====
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
            bot.send_message(uid, "Eres Pastor (primer acceso)")

    menu(uid)

# ===== HANDLER =====
@bot.message_handler(func=lambda m: True)
def manejar(m):
    uid = m.chat.id
    txt = m.text
    estado = user_states.get(uid)

    # ===== NAVEGACIÓN =====
    if txt in ["🔙 Volver", "🏠 Inicio"]:
        menu(uid)

    elif txt == "📋 Miembros":
        menu_mod(uid, "Miembros")

    elif txt == "🙏 Oración":
        menu_mod(uid, "Oración")

    elif txt == "🎁 Ayudas":
        menu_mod(uid, "Ayudas")

    elif txt == "💊 Medicamentos":
        menu_mod(uid, "Medicamentos")

    elif txt == "🏠 Casas de Paz":
        menu_mod(uid, "Casas de Paz")

    elif txt == "⛪ Servicios":
        menu_mod(uid, "Servicios")

    elif txt == "📅 Agenda":
        menu_mod(uid, "Agenda")

    elif txt == "⚙️ Administración":
        if es_pastor(uid):
            data = cursor.execute("SELECT id,nombre,rol FROM usuarios").fetchall()
            bot.send_message(uid, "\n".join([str(d) for d in data]))
        else:
            bot.send_message(uid, "Acceso denegado")

    # ===== AGREGAR =====
    elif txt == "➕ Agregar":
        ref = m.reply_to_message.text

        if "Miembros" in ref:
            user_states[uid] = "miembro"
            bot.send_message(uid, "Nombre:")

        elif "Oración" in ref:
            user_states[uid] = "oracion"
            bot.send_message(uid, "Motivo:")

        elif "Ayudas" in ref:
            if es_pastor(uid):
                user_states[uid] = "ayuda"
                bot.send_message(uid, "Descripción:")
            else:
                bot.send_message(uid, "Solo Pastor")

        elif "Medicamentos" in ref:
            if es_pastor(uid):
                user_states[uid] = "med1"
                bot.send_message(uid, "Nombre:")
            else:
                bot.send_message(uid, "Solo Pastor")

        elif "Casas de Paz" in ref:
            user_states[uid] = "casa1"
            bot.send_message(uid, "Anfitrión:")

        elif "Servicios" in ref:
            user_states[uid] = "serv1"
            bot.send_message(uid, "Predicador:")

        elif "Agenda" in ref:
            user_states[uid] = "agenda"
            bot.send_message(uid, "Evento:")

    # ===== VER =====
    elif txt == "📄 Ver":
        ref = m.reply_to_message.text

        tablas = {
            "Miembros": "miembros",
            "Oración": "oraciones",
            "Ayudas": "ayudas",
            "Medicamentos": "medicamentos",
            "Casas de Paz": "casas",
            "Servicios": "servicios",
            "Agenda": "agenda"
        }

        for k in tablas:
            if k in ref:
                data = cursor.execute(f"SELECT * FROM {tablas[k]}").fetchall()
                bot.send_message(uid, "\n".join([str(d) for d in data]) or "Vacío")

    # ===== ESTADOS =====
    elif estado == "miembro":
        cursor.execute("INSERT INTO miembros (nombre, estado) VALUES (?,?)",(txt,"activo"))

    elif estado == "oracion":
        cursor.execute("INSERT INTO oraciones (texto, user_id) VALUES (?,?)",(txt,uid))

    elif estado == "ayuda":
        cursor.execute("INSERT INTO ayudas (descripcion, aprobado) VALUES (?,1)",(txt,))

    elif estado == "med1":
        user_states[uid] = ("med2", txt)
        bot.send_message(uid, "Cantidad:")
        return

    elif isinstance(estado, tuple) and estado[0] == "med2":
        cursor.execute("INSERT INTO medicamentos (nombre, stock) VALUES (?,?)",(estado[1],int(txt)))

    elif estado == "casa1":
        user_states[uid] = ("casa2", txt)
        bot.send_message(uid, "Dirección:")
        return

    elif isinstance(estado, tuple) and estado[0] == "casa2":
        cursor.execute("INSERT INTO casas (anfitrion, direccion) VALUES (?,?)",(estado[1],txt))

    elif estado == "serv1":
        user_states[uid] = ("serv2", txt)
        bot.send_message(uid, "Mensaje:")
        return

    elif isinstance(estado, tuple) and estado[0] == "serv2":
        cursor.execute("INSERT INTO servicios (fecha, mensaje, predicador) VALUES (?,?,?)",
                       (str(datetime.date.today()), txt, estado[1]))

    elif estado == "agenda":
        cursor.execute("INSERT INTO agenda (fecha, evento) VALUES (?,?)",
                       (str(datetime.date.today()), txt))

    # ===== FINALIZAR =====
    if estado:
        conn.commit()
        user_states[uid] = None
        bot.send_message(uid, "Guardado")
        menu(uid)

# ===== RUN =====
bot.infinity_polling()
