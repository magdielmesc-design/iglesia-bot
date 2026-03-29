# BOT IGLESIA MONTE DE DIOS - FINAL FUNCIONAL

import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
import random
from datetime import datetime

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# ===== TABLAS =====
cursor.execute("""
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    telefono TEXT,
    direccion TEXT,
    fecha_nacimiento TEXT,
    sexo TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS celulas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    dia TEXT,
    hora TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS casas_paz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anfitrion TEXT,
    discipulador1 TEXT,
    discipulador2 TEXT,
    dia TEXT,
    hora TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promesas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    texto TEXT,
    referencia TEXT,
    fecha_ultimo_uso TEXT
)
""")

conn.commit()

# ===== MENU =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("Miembros", "Células")
    m.add("Casas de Paz", "Promesas")
    m.add("Asistente", "Ayuda")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "Sistema activo", reply_markup=menu())

# ===== MIEMBROS =====
@bot.message_handler(func=lambda m: m.text == "Miembros")
def miembros(msg):
    bot.send_message(msg.chat.id,
    "Formato:\nNombre,Teléfono,Dirección,Fecha(YYYY-MM-DD),Sexo")
    bot.register_next_step_handler(msg, guardar_miembro)

def guardar_miembro(msg):
    try:
        d = msg.text.split(",")
        cursor.execute("""
        INSERT INTO miembros (nombre, telefono, direccion, fecha_nacimiento, sexo)
        VALUES (?,?,?,?,?)
        """, (d[0], d[1], d[2], d[3], d[4]))
        conn.commit()

        bot.send_message(msg.chat.id, "✅ Miembro guardado", reply_markup=menu())

        # Bienvenida automática
        bot.send_message(msg.chat.id,
        f"Bienvenido {d[0]} a Iglesia Monte de Dios")

    except:
        bot.send_message(msg.chat.id, "❌ Error", reply_markup=menu())

# ===== CELULAS =====
@bot.message_handler(func=lambda m: m.text == "Células")
def celulas(msg):
    bot.send_message(msg.chat.id, "Formato:\nNombre,Día,Hora")
    bot.register_next_step_handler(msg, guardar_celula)

def guardar_celula(msg):
    try:
        d = msg.text.split(",")
        cursor.execute("""
        INSERT INTO celulas (nombre, dia, hora)
        VALUES (?,?,?)
        """, (d[0], d[1], d[2]))
        conn.commit()
        bot.send_message(msg.chat.id, "✅ Célula creada", reply_markup=menu())
    except:
        bot.send_message(msg.chat.id, "❌ Error", reply_markup=menu())

# ===== CASAS DE PAZ =====
@bot.message_handler(func=lambda m: m.text == "Casas de Paz")
def casas(msg):
    bot.send_message(msg.chat.id,
    "Formato:\nAnfitrión,Discipulador1,Discipulador2,Día,Hora")
    bot.register_next_step_handler(msg, guardar_casa)

def guardar_casa(msg):
    try:
        d = msg.text.split(",")
        cursor.execute("""
        INSERT INTO casas_paz (anfitrion, discipulador1, discipulador2, dia, hora)
        VALUES (?,?,?,?,?)
        """, (d[0], d[1], d[2], d[3], d[4]))
        conn.commit()
        bot.send_message(msg.chat.id, "✅ Casa creada", reply_markup=menu())
    except:
        bot.send_message(msg.chat.id, "❌ Error", reply_markup=menu())

# ===== PROMESAS =====
@bot.message_handler(func=lambda m: m.text == "Promesas")
def promesas(msg):
    bot.send_message(msg.chat.id,
    "1 = Agregar\n2 = Ver")
    bot.register_next_step_handler(msg, menu_promesas)

def menu_promesas(msg):
    if msg.text == "1":
        bot.send_message(msg.chat.id, "Texto\nReferencia")
        bot.register_next_step_handler(msg, guardar_promesa)
    else:
        cursor.execute("SELECT texto, referencia FROM promesas ORDER BY RANDOM() LIMIT 1")
        p = cursor.fetchone()
        if p:
            bot.send_message(msg.chat.id,
            f"📖 Promesa del día\n\n{p[0]}\n— {p[1]}")
        else:
            bot.send_message(msg.chat.id, "No hay promesas")

def guardar_promesa(msg):
    try:
        l = msg.text.split("\n")
        cursor.execute("""
        INSERT INTO promesas (texto, referencia, fecha_ultimo_uso)
        VALUES (?,?,?)
        """, (l[0], l[1], datetime.now()))
        conn.commit()
        bot.send_message(msg.chat.id, "✅ Guardada", reply_markup=menu())
    except:
        bot.send_message(msg.chat.id, "❌ Error", reply_markup=menu())

# ===== ASISTENTE =====
@bot.message_handler(func=lambda m: m.text == "Asistente")
def asistente(msg):
    cursor.execute("SELECT COUNT(*) FROM miembros")
    m = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM celulas")
    c = cursor.fetchone()[0]

    bot.send_message(msg.chat.id,
    f"📊 Estado\nMiembros: {m}\nCélulas: {c}",
    reply_markup=menu())

# ===== AYUDA =====
@bot.message_handler(func=lambda m: m.text == "Ayuda")
def ayuda(msg):
    bot.send_message(msg.chat.id,
    "Usa el menú.\nMiembros: agregar\nCélulas: crear\nPromesas: guardar/ver",
    reply_markup=menu())

# ===== RUN =====
bot.polling()
