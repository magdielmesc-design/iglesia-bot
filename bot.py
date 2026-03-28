import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# 🔹 BASE DE DATOS
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT
)
""")

conn.commit()

estado = {}

# 🔹 MENÚ
def menu_principal():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("➕ Miembro", "🔍 Buscar")
    m.add("✏️ Editar", "❌ Eliminar")
    return m

# 🔹 START
@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    bot.send_message(m.chat.id, "Sistema Iglesia Monte de Dios", reply_markup=menu_principal())

# 🔹 LÓGICA
@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text
    user_state = estado.get(chat)

    try:
        if text == "➕ Miembro":
            estado[chat] = "agregar"
            bot.send_message(chat, "Escribe el nombre del miembro")

        elif text == "🔍 Buscar":
            estado[chat] = "buscar"
            bot.send_message(chat, "Nombre a buscar")

        elif text == "✏️ Editar":
            estado[chat] = "editar"
            bot.send_message(chat, "Nombre actual")

        elif text == "❌ Eliminar":
            estado[chat] = "eliminar"
            bot.send_message(chat, "Nombre a eliminar")

        elif user_state == "agregar":
            cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (text,))
            conn.commit()
            bot.send_message(chat, f"Agregado: {text} ✅", reply_markup=menu_principal())
            estado[chat] = None

        elif user_state == "buscar":
            cursor.execute("SELECT nombre FROM miembros WHERE nombre LIKE ?", ('%' + text + '%',))
            resultados = cursor.fetchall()
            res = "\n".join([r[0] for r in resultados])
            bot.send_message(chat, res if res else "No encontrado ❌", reply_markup=menu_principal())
            estado[chat] = None

        elif user_state == "eliminar":
            cursor.execute("DELETE FROM miembros WHERE nombre LIKE ?", ('%' + text + '%',))
            conn.commit()
            bot.send_message(chat, f"Eliminado: {text} ✅", reply_markup=menu_principal())
            estado[chat] = None

        elif user_state == "editar":
            estado[chat] = {"editar": text}
            bot.send_message(chat, "Nuevo nombre")

        elif isinstance(user_state, dict) and user_state.get("editar"):
            cursor.execute("UPDATE miembros SET nombre=? WHERE nombre=?", (text, user_state["editar"]))
            conn.commit()
            bot.send_message(chat, f"Actualizado a: {text} ✅", reply_markup=menu_principal())
            estado[chat] = None

    except Exception as e:
        bot.send_message(chat, f"Error: {e}")
        estado[chat] = None

print("Bot iniciado...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
