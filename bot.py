import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== BASE DE DATOS =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS oraciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    motivo TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS medicamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    medicamento TEXT,
    descripcion TEXT
)
""")

conn.commit()

estado = {}

# ===== MENÚ =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("👥 Miembros")
    m.add("🙏 Oración", "💊 Medicamentos")
    m.add("📋 Ver datos")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    bot.send_message(m.chat.id, "Sistema Iglesia Monte de Dios", reply_markup=menu())

# ===== BOT =====
@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text
    st = estado.get(chat)

    try:

        # ===== MIEMBROS =====
        if text == "👥 Miembros":
            estado[chat] = "miembro"
            bot.send_message(chat, "Escribe el nombre:")

        elif st == "miembro":
            cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (text,))
            conn.commit()
            bot.send_message(chat, "Guardado ✅", reply_markup=menu())
            estado[chat] = None

        # ===== ORACIÓN =====
        elif text == "🙏 Oración":
            estado[chat] = "oracion"
            bot.send_message(chat, "Formato: Nombre,Motivo")

        elif st == "oracion":
            nombre, motivo = text.split(",",1)
            cursor.execute("INSERT INTO oraciones (nombre,motivo) VALUES (?,?)", (nombre,motivo))
            conn.commit()
            bot.send_message(chat, "Motivo guardado 🙏", reply_markup=menu())
            estado[chat] = None

        # ===== MEDICAMENTOS =====
        elif text == "💊 Medicamentos":
            estado[chat] = "med"
            bot.send_message(chat, "Formato: Nombre,Medicamento,Descripción")

        elif st == "med":
            nombre, med, desc = text.split(",",2)
            cursor.execute("INSERT INTO medicamentos (nombre,medicamento,descripcion) VALUES (?,?,?)", (nombre,med,desc))
            conn.commit()
            bot.send_message(chat, "Guardado 💊", reply_markup=menu())
            estado[chat] = None

        # ===== VER DATOS =====
        elif text == "📋 Ver datos":
            msg = "👥 Miembros:\n"
            cursor.execute("SELECT nombre FROM miembros")
            miembros = cursor.fetchall()
            msg += "\n".join([x[0] for x in miembros]) or "Vacío"

            msg += "\n\n🙏 Oración:\n"
            cursor.execute("SELECT nombre,motivo FROM oraciones")
            oraciones = cursor.fetchall()
            msg += "\n".join([f"{n}: {m}" for n,m in oraciones]) or "Vacío"

            msg += "\n\n💊 Medicamentos:\n"
            cursor.execute("SELECT nombre,medicamento FROM medicamentos")
            meds = cursor.fetchall()
            msg += "\n".join([f"{n}: {med}" for n,med in meds]) or "Vacío"

            bot.send_message(chat, msg)

    except Exception as e:
        bot.send_message(chat, f"Error: {e}")
        estado[chat] = None

# ===== INICIO =====
print("BOT NUEVO FUNCIONANDO")

bot.remove_webhook()

bot.infinity_polling()
