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
cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS miembros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS oraciones (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS ayudas (id INTEGER PRIMARY KEY AUTOINCREMENT, descripcion TEXT, aprobado INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, stock INTEGER)")

# NUEVO NIVEL 3
cursor.execute("CREATE TABLE IF NOT EXISTS casas (id INTEGER PRIMARY KEY AUTOINCREMENT, anfitrion TEXT, direccion TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, mensaje TEXT, predicador TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, evento TEXT)")

conn.commit()

# ===== ESTADOS =====
user_states = {}

# ===== ROLES =====
def get_rol(user_id):
    user = cursor.execute("SELECT rol FROM usuarios WHERE id=?", (user_id,)).fetchone()
    return user[0] if user else None

def es_pastor(user_id):
    return get_rol(user_id) == "pastor"

# ===== MENÚ =====
def menu_principal(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Miembros", "🙏 Oración")
    markup.add("🎁 Ayudas", "💊 Medicamentos")
    markup.add("🏠 Casas de Paz", "⛪ Servicios")
    markup.add("📅 Agenda", "⚙️ Administración")
    bot.send_message(chat_id, "Sistema Iglesia NIVEL 3", reply_markup=markup)

def menu_modulo(chat_id, nombre):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Agregar", "📄 Ver")
    markup.add("🔙 Volver", "🏠 Inicio")
    bot.send_message(chat_id, nombre, reply_markup=markup)

# ===== START AUTO PASTOR =====
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    nombre = message.from_user.first_name

    pastor = cursor.execute("SELECT * FROM usuarios WHERE rol='pastor'").fetchone()
    user = cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()

    if not user:
        rol = "pastor" if not pastor else "miembro"
        cursor.execute("INSERT INTO usuarios VALUES (?,?,?)", (user_id, nombre, rol))
        conn.commit()
        if rol == "pastor":
            bot.send_message(user_id, "Eres Pastor (primer acceso)")

    menu_principal(user_id)

# ===== HANDLER =====
@bot.message_handler(func=lambda m: True)
def manejar(message):
    chat_id = message.chat.id
    texto = message.text
    estado = user_states.get(chat_id)
    rol = get_rol(chat_id)

    # NAVEGACIÓN
    if texto in ["🏠 Inicio", "🔙 Volver"]:
        menu_principal(chat_id)

    elif texto == "📋 Miembros":
        menu_modulo(chat_id, "Miembros")

    elif texto == "🙏 Oración":
        menu_modulo(chat_id, "Oración")

    elif texto == "🎁 Ayudas":
        menu_modulo(chat_id, "Ayudas")

    elif texto == "💊 Medicamentos":
        menu_modulo(chat_id, "Medicamentos")

    elif texto == "🏠 Casas de Paz":
        menu_modulo(chat_id, "Casas de Paz")

    elif texto == "⛪ Servicios":
        menu_modulo(chat_id, "Servicios")

    elif texto == "📅 Agenda":
        menu_modulo(chat_id, "Agenda")

    elif texto == "⚙️ Administración":
        if es_pastor(chat_id):
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Ver Usuarios")
            markup.add("🔙 Volver")
            bot.send_message(chat_id, "Admin", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Acceso denegado")

    # ===== AGREGAR =====
    elif texto == "➕ Agregar":

        ref = message.reply_to_message.text

        if "Miembros" in ref:
            user_states[chat_id] = "miembro"
            bot.send_message(chat_id, "Nombre:")

        elif "Oración" in ref:
            user_states[chat_id] = "oracion"
            bot.send_message(chat_id, "Motivo:")

        elif "Ayudas" in ref:
            if es_pastor(chat_id):
                user_states[chat_id] = "ayuda"
                bot.send_message(chat_id, "Descripción:")
            else:
                bot.send_message(chat_id, "Solo Pastor")

        elif "Medicamentos" in ref:
            if es_pastor(chat_id):
                user_states[chat_id] = "med1"
                bot.send_message(chat_id, "Nombre:")
            else:
                bot.send_message(chat_id, "Solo Pastor")

        elif "Casas de Paz" in ref:
            user_states[chat_id] = "casa1"
            bot.send_message(chat_id, "Anfitrión:")

        elif "Servicios" in ref:
            user_states[chat_id] = "serv1"
            bot.send_message(chat_id, "Predicador:")

        elif "Agenda" in ref:
            user_states[chat_id] = "agenda1"
            bot.send_message(chat_id, "Evento:")

    # ===== VER =====
    elif texto == "📄 Ver":

        ref = message.reply_to_message.text

        def mostrar(tabla):
            data = cursor.execute(f"SELECT * FROM {tabla}").fetchall()
            bot.send_message(chat_id, "\n".join([str(d) for d in data]) or "Vacío")

        if "Miembros" in ref:
            mostrar("miembros")
        elif "Oración" in ref:
            mostrar("oraciones")
        elif "Ayudas" in ref:
            mostrar("ayudas")
        elif "Medicamentos" in ref:
            mostrar("medicamentos")
        elif "Casas de Paz" in ref:
            mostrar("casas")
        elif "Servicios" in ref:
            mostrar("servicios")
        elif "Agenda" in ref:
            mostrar("agenda")

    # ===== ESTADOS =====
    elif estado == "miembro":
        cursor.execute("INSERT INTO miembros (nombre, estado) VALUES (?,?)", (texto, "activo"))
        conn.commit()

    elif estado == "oracion":
        cursor.execute("INSERT INTO oraciones (texto, user_id) VALUES (?,?)", (texto, chat_id))
        conn.commit()

    elif estado == "ayuda":
        cursor.execute("INSERT INTO ayudas (descripcion, aprobado) VALUES (?,1)", (texto,))
        conn.commit()

    elif estado == "med1":
        user_states[chat_id] = ("med2", texto)
        bot.send_message(chat_id, "Cantidad:")
        return

    elif isinstance(estado, tuple):
        cursor.execute("INSERT INTO medicamentos (nombre, stock) VALUES (?,?)", (estado[1], int(texto)))
        conn.commit()

    elif estado == "casa1":
        user_states[chat_id] = ("casa2", texto)
        bot.send_message(chat_id, "Dirección:")
        return

    elif isinstance(estado, tuple) and estado[0] == "casa2":
        cursor.execute("INSERT INTO casas (anfitrion, direccion) VALUES (?,?)", (estado[1], texto))
        conn.commit()

    elif estado == "serv1":
        user_states[chat_id] = ("serv2", texto)
        bot.send_message(chat_id, "Mensaje:")
        return

    elif isinstance(estado, tuple) and estado[0] == "serv2":
        fecha = str(datetime.date.today())
        cursor.execute("INSERT INTO servicios (fecha, mensaje, predicador) VALUES (?,?,?)", (fecha, texto, estado[1]))
        conn.commit()

    elif estado == "agenda1":
        fecha = str(datetime.date.today())
        cursor.execute("INSERT INTO agenda (fecha, evento) VALUES (?,?)", (fecha, texto))
        conn.commit()

    # RESET
    if estado:
        user_states[chat_id] = None
        bot.send_message(chat_id, "Guardado")
        menu_principal(chat_id)

# ===== RUN =====
bot.infinity_polling()
