import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import os
from datetime import datetime

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# TABLAS
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

# ===== TECLADO PRINCIPAL =====
def menu_principal():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👥 Miembros", "🙏 Oración")
    return markup

# ===== INICIO =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "Sistema Iglesia Monte de Dios activo", reply_markup=menu_principal())

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
    bot.send_message(msg.chat.id, "Miembro guardado", reply_markup=menu_principal())

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

    bot.send_message(msg.chat.id, "Motivo guardado", reply_markup=menu_principal())

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
    bot.send_message(msg.chat.id, "Menú principal", reply_markup=menu_principal())

# ===== RUN =====
print("Bot corriendo...")
bot.infinity_polling()
