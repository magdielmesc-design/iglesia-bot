import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
import time

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# TABLAS
cursor.execute("CREATE TABLE IF NOT EXISTS miembros (id INTEGER PRIMARY KEY, nombre TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS oraciones (id INTEGER PRIMARY KEY, nombre TEXT, motivo TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, medicamento TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS casas (id INTEGER PRIMARY KEY, nombre TEXT, dia TEXT, hora TEXT, direccion TEXT, discipuladores TEXT, miembros TEXT)")
conn.commit()

estado = {}

# ===== MENU =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("👥 Miembros", "🏠 Casas de Paz")
    m.add("🙏 Oración", "💊 Medicamentos")
    m.add("📊 Ver Todo")
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
            bot.send_message(chat, "Nombre:")

        elif st == "miembro":
            cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (text,))
            conn.commit()
            bot.send_message(chat, "Guardado ✅", reply_markup=menu())
            estado[chat] = None

        # ===== ORACION =====
        elif text == "🙏 Oración":
            estado[chat] = "oracion"
            bot.send_message(chat, "Formato: Nombre,Motivo")

        elif st == "oracion":
            n,mot = text.split(",",1)
            cursor.execute("INSERT INTO oraciones (nombre,motivo) VALUES (?,?)",(n,mot))
            conn.commit()
            bot.send_message(chat, "Guardado 🙏", reply_markup=menu())
            estado[chat] = None

        # ===== MEDICAMENTOS =====
        elif text == "💊 Medicamentos":
            estado[chat] = "med"
            bot.send_message(chat, "Formato: Nombre,Medicamento")

        elif st == "med":
            n,med = text.split(",",1)
            cursor.execute("INSERT INTO medicamentos (nombre,medicamento) VALUES (?,?)",(n,med))
            conn.commit()
            bot.send_message(chat, "Guardado 💊", reply_markup=menu())
            estado[chat] = None

        # ===== CASAS DE PAZ =====
        elif text == "🏠 Casas de Paz":
            estado[chat] = "casa"
            bot.send_message(chat, "Formato:\nNombre,Día,Hora,Dirección,Discipuladores,Miembros")

        elif st == "casa":
            n,d,h,dir,dis,miem = text.split(",",5)
            cursor.execute("INSERT INTO casas (nombre,dia,hora,direccion,discipuladores,miembros) VALUES (?,?,?,?,?,?)",(n,d,h,dir,dis,miem))
            conn.commit()
            bot.send_message(chat, "Casa guardada 🏠", reply_markup=menu())
            estado[chat] = None

        # ===== VER TODO =====
        elif text == "📊 Ver Todo":
            msg = ""

            cursor.execute("SELECT nombre FROM miembros")
            msg += "👥 Miembros:\n" + "\n".join([x[0] for x in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT nombre,motivo FROM oraciones")
            msg += "🙏 Oración:\n" + "\n".join([f"{n}: {m}" for n,m in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT nombre,medicamento FROM medicamentos")
            msg += "💊 Medicamentos:\n" + "\n".join([f"{n}: {m}" for n,m in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT nombre,dia,hora FROM casas")
            msg += "🏠 Casas:\n" + "\n".join([f"{n} - {d} {h}" for n,d,h in cursor.fetchall()])

            bot.send_message(chat, msg or "Sin datos")

    except Exception as e:
        bot.send_message(chat, f"Error: {e}")
        estado[chat] = None

# ===== INICIO =====
print("SISTEMA IGLESIA ACTIVO")

bot.remove_webhook()
time.sleep(2)

bot.infinity_polling()
