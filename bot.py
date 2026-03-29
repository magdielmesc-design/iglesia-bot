import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# TABLAS
cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS miembros (id INTEGER PRIMARY KEY, nombre TEXT, estado TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS oraciones (id INTEGER PRIMARY KEY, texto TEXT, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS ayudas (id INTEGER PRIMARY KEY, descripcion TEXT, aprobado INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, stock INTEGER)")
conn.commit()

# ===== ESTADOS =====
user_states = {}

# ===== ROLES =====
def get_rol(user_id):
    user = cursor.execute("SELECT rol FROM usuarios WHERE id=?", (user_id,)).fetchone()
    return user[0] if user else "miembro"

def es_pastor(user_id):
    return get_rol(user_id) == "pastor"

# ===== MENÚ =====
def menu_principal(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Miembros", "🙏 Oración")
    markup.add("🎁 Ayudas", "💊 Medicamentos")
    markup.add("⚙️ Administración")
    bot.send_message(chat_id, "Sistema Iglesia", reply_markup=markup)

def menu_modulo(chat_id, nombre):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Agregar", "📄 Ver")
    markup.add("🔙 Volver", "🏠 Inicio")
    bot.send_message(chat_id, nombre, reply_markup=markup)

# ===== START =====
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    nombre = message.from_user.first_name

    if not cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone():
        cursor.execute("INSERT INTO usuarios (id, nombre, rol) VALUES (?, ?, ?)", (user_id, nombre, "miembro"))
        conn.commit()

    menu_principal(user_id)

# ===== HANDLER =====
@bot.message_handler(func=lambda message: True)
def manejar(message):
    chat_id = message.chat.id
    texto = message.text
    estado = user_states.get(chat_id)
    rol = get_rol(chat_id)

    # ===== MENÚ =====
    if texto == "🏠 Inicio" or texto == "🔙 Volver":
        menu_principal(chat_id)

    elif texto == "📋 Miembros":
        menu_modulo(chat_id, "Miembros")

    elif texto == "🙏 Oración":
        menu_modulo(chat_id, "Oración")

    elif texto == "🎁 Ayudas":
        menu_modulo(chat_id, "Ayudas")

    elif texto == "💊 Medicamentos":
        menu_modulo(chat_id, "Medicamentos")

    elif texto == "⚙️ Administración":
        if es_pastor(chat_id):
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Asignar Pastor", "Ver Usuarios")
            markup.add("🔙 Volver")
            bot.send_message(chat_id, "Admin", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Acceso denegado")

    # ===== ACCIONES =====
    elif texto == "➕ Agregar":

        if "Miembros" in message.reply_to_message.text:
            if rol != "pastor":
                user_states[chat_id] = "miembro_pendiente"
                bot.send_message(chat_id, "Nombre (queda pendiente aprobación):")
            else:
                user_states[chat_id] = "miembro_ok"
                bot.send_message(chat_id, "Nombre:")

        elif "Oración" in message.reply_to_message.text:
            user_states[chat_id] = "oracion"
            bot.send_message(chat_id, "Motivo:")

        elif "Ayudas" in message.reply_to_message.text:
            if es_pastor(chat_id):
                user_states[chat_id] = "ayuda"
                bot.send_message(chat_id, "Descripción:")
            else:
                bot.send_message(chat_id, "Solo Pastor")

        elif "Medicamentos" in message.reply_to_message.text:
            if es_pastor(chat_id):
                user_states[chat_id] = "med1"
                bot.send_message(chat_id, "Nombre:")
            else:
                bot.send_message(chat_id, "Solo Pastor")

    elif texto == "📄 Ver":

        if "Miembros" in message.reply_to_message.text:
            data = cursor.execute("SELECT nombre, estado FROM miembros").fetchall()
            txt = "\n".join([f"{n} ({e})" for n,e in data]) or "Vacío"
            bot.send_message(chat_id, txt)

        elif "Oración" in message.reply_to_message.text:
            data = cursor.execute("SELECT texto FROM oraciones").fetchall()
            bot.send_message(chat_id, "\n".join([d[0] for d in data]) or "Vacío")

        elif "Ayudas" in message.reply_to_message.text:
            data = cursor.execute("SELECT descripcion, aprobado FROM ayudas").fetchall()
            txt = "\n".join([f"{d} ({'OK' if a else 'Pendiente'})" for d,a in data])
            bot.send_message(chat_id, txt or "Vacío")

    # ===== ADMIN =====
    elif texto == "Asignar Pastor":
        user_states[chat_id] = "set_pastor"
        bot.send_message(chat_id, "ID usuario:")

    elif texto == "Ver Usuarios":
        data = cursor.execute("SELECT id, nombre, rol FROM usuarios").fetchall()
        txt = "\n".join([f"{i} - {n} ({r})" for i,n,r in data])
        bot.send_message(chat_id, txt or "Vacío")

    # ===== ESTADOS =====
    elif estado == "miembro_ok":
        cursor.execute("INSERT INTO miembros (nombre, estado) VALUES (?,?)", (texto, "activo"))
        conn.commit()
        user_states[chat_id] = None
        bot.send_message(chat_id, "Miembro agregado")
        menu_principal(chat_id)

    elif estado == "miembro_pendiente":
        cursor.execute("INSERT INTO miembros (nombre, estado) VALUES (?,?)", (texto, "pendiente"))
        conn.commit()
        user_states[chat_id] = None
        bot.send_message(chat_id, "Enviado a aprobación")
        menu_principal(chat_id)

    elif estado == "oracion":
        cursor.execute("INSERT INTO oraciones (texto, user_id) VALUES (?,?)", (texto, chat_id))
        conn.commit()
        user_states[chat_id] = None
        bot.send_message(chat_id, "Guardado")
        menu_principal(chat_id)

    elif estado == "ayuda":
        cursor.execute("INSERT INTO ayudas (descripcion, aprobado) VALUES (?,1)", (texto,))
        conn.commit()
        user_states[chat_id] = None
        bot.send_message(chat_id, "Registrado")
        menu_principal(chat_id)

    elif estado == "med1":
        user_states[chat_id] = ("med2", texto)
        bot.send_message(chat_id, "Cantidad:")

    elif isinstance(estado, tuple) and estado[0] == "med2":
        cursor.execute("INSERT INTO medicamentos (nombre, stock) VALUES (?,?)", (estado[1], int(texto)))
        conn.commit()
        user_states[chat_id] = None
        bot.send_message(chat_id, "Guardado")
        menu_principal(chat_id)

    elif estado == "set_pastor":
        cursor.execute("UPDATE usuarios SET rol='pastor' WHERE id=?", (int(texto),))
        conn.commit()
        user_states[chat_id] = None
        bot.send_message(chat_id, "Asignado como Pastor")
        menu_principal(chat_id)

# ===== RUN =====
bot.infinity_polling()
