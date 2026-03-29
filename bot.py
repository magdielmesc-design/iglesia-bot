import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
from datetime import datetime

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# ===== TABLAS =====
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT UNIQUE,
    rol TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS oraciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    motivo TEXT,
    fecha TEXT
)
""")

conn.commit()

# ===== FUNCIONES =====
def obtener_rol(chat_id):
    cursor.execute("SELECT rol FROM usuarios WHERE chat_id=?", (chat_id,))
    data = cursor.fetchone()
    return data[0] if data else None

def registrar_usuario(chat_id):
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total = cursor.fetchone()[0]

    if total == 0:
        rol = "Pastor"
    else:
        rol = "Miembro"

    cursor.execute("INSERT OR IGNORE INTO usuarios (chat_id, rol) VALUES (?, ?)", (chat_id, rol))
    conn.commit()

    return rol

# ===== MENÚ =====
def menu_principal(rol):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    if rol == "Pastor":
        markup.add("👥 Miembros", "🙏 Oración", "🎁 Ayudas", "⚙️ Admin")
    elif rol == "Líder":
        markup.add("👥 Miembros", "🙏 Oración")
    else:
        markup.add("🙏 Oración")

    return markup

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    chat_id = str(msg.chat.id)

    registrar_usuario(chat_id)
    rol = obtener_rol(chat_id)

    bot.send_message(
        msg.chat.id,
        f"Sistema activo\nRol: {rol}",
        reply_markup=menu_principal(rol)
    )

# ===== MIEMBROS =====
@bot.message_handler(func=lambda m: m.text == "👥 Miembros")
def miembros_menu(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Agregar", "📋 Ver", "⬅️ Volver")
    bot.send_message(msg.chat.id, "Módulo Miembros", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Agregar")
def agregar_miembro(msg):
    msg2 = bot.send_message(msg.chat.id, "Nombre del miembro:")
    bot.register_next_step_handler(msg2, guardar_miembro)

def guardar_miembro(msg):
    cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (msg.text,))
    conn.commit()
    bot.send_message(msg.chat.id, "Miembro guardado")

@bot.message_handler(func=lambda m: m.text == "📋 Ver")
def ver_miembros(msg):
    cursor.execute("SELECT nombre FROM miembros")
    datos = cursor.fetchall()

    if not datos:
        bot.send_message(msg.chat.id, "No hay miembros")
        return

    texto = "Miembros:\n"
    for d in datos:
        texto += f"- {d[0]}\n"

    bot.send_message(msg.chat.id, texto)

# ===== ORACIÓN =====
@bot.message_handler(func=lambda m: m.text == "🙏 Oración")
def oracion_menu(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Agregar", "📖 Ver", "⬅️ Volver")
    bot.send_message(msg.chat.id, "Módulo Oración", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📝 Agregar")
def agregar_oracion(msg):
    msg2 = bot.send_message(msg.chat.id, "Escribe tu motivo:")
    bot.register_next_step_handler(msg2, guardar_oracion)

def guardar_oracion(msg):
    usuario = str(msg.chat.id)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute(
        "INSERT INTO oraciones (usuario, motivo, fecha) VALUES (?, ?, ?)",
        (usuario, msg.text, fecha)
    )
    conn.commit()

    bot.send_message(msg.chat.id, "Motivo guardado")

@bot.message_handler(func=lambda m: m.text == "📖 Ver")
def ver_oraciones(msg):
    cursor.execute("SELECT motivo, fecha FROM oraciones ORDER BY id DESC LIMIT 10")
    datos = cursor.fetchall()

    if not datos:
        bot.send_message(msg.chat.id, "No hay motivos")
        return

    texto = "Últimos motivos:\n"
    for d in datos:
        texto += f"- {d[0]} ({d[1]})\n"

    bot.send_message(msg.chat.id, texto)

# ===== VOLVER =====
@bot.message_handler(func=lambda m: m.text == "⬅️ Volver")
def volver(msg):
    chat_id = str(msg.chat.id)
    rol = obtener_rol(chat_id)
    bot.send_message(msg.chat.id, "Menú principal", reply_markup=menu_principal(rol))

# ===== RUN =====
print("Bot corriendo con roles...")
bot.infinity_polling()
