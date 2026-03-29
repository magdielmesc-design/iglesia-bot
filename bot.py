BOT IGLESIA MONTE DE DIOS - NIVEL 2 (INTERFAZ REAL)

import telebot from telebot.types import ReplyKeyboardMarkup import sqlite3 import os from datetime import datetime

TOKEN = os.getenv("TOKEN") bot = telebot.TeleBot(TOKEN)

===== DB =====

conn = sqlite3.connect("iglesia.db", check_same_thread=False) cursor = conn.cursor()

cursor.execute(""" CREATE TABLE IF NOT EXISTS miembros ( id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT, direccion TEXT, fecha_nacimiento TEXT, sexo TEXT ) """)

conn.commit()

===== MENU PRINCIPAL =====

def menu_principal(): m = ReplyKeyboardMarkup(resize_keyboard=True) m.add("👥 Miembros", "📊 Panel") m.add("🤖 Asistente", "🆘 Ayuda") return m

===== SUBMENU MIEMBROS =====

def menu_miembros(): m = ReplyKeyboardMarkup(resize_keyboard=True) m.add("➕ Agregar", "📋 Ver") m.add("🔙 Volver") return m

===== START =====

@bot.message_handler(commands=['start']) def start(msg): bot.send_message(msg.chat.id, "Sistema activo", reply_markup=menu_principal())

===== NAVEGACION =====

@bot.message_handler(func=lambda m: m.text == "👥 Miembros") def miembros_menu(msg): bot.send_message(msg.chat.id, "Módulo Miembros", reply_markup=menu_miembros())

@bot.message_handler(func=lambda m: m.text == "🔙 Volver") def volver(msg): bot.send_message(msg.chat.id, "Menú principal", reply_markup=menu_principal())

===== AGREGAR MIEMBRO PASO A PASO =====

@bot.message_handler(func=lambda m: m.text == "➕ Agregar") def agregar_miembro(msg): bot.send_message(msg.chat.id, "Nombre:") bot.register_next_step_handler(msg, paso_nombre)

def paso_nombre(msg): nombre = msg.text bot.send_message(msg.chat.id, "Teléfono:") bot.register_next_step_handler(msg, paso_telefono, nombre)

def paso_telefono(msg, nombre): telefono = msg.text bot.send_message(msg.chat.id, "Dirección:") bot.register_next_step_handler(msg, paso_direccion, nombre, telefono)

def paso_direccion(msg, nombre, telefono): direccion = msg.text bot.send_message(msg.chat.id, "Fecha nacimiento (YYYY-MM-DD):") bot.register_next_step_handler(msg, paso_fecha, nombre, telefono, direccion)

def paso_fecha(msg, nombre, telefono, direccion): fecha = msg.text bot.send_message(msg.chat.id, "Sexo (M/F):") bot.register_next_step_handler(msg, paso_sexo, nombre, telefono, direccion, fecha)

def paso_sexo(msg, nombre, telefono, direccion, fecha): sexo = msg.text

cursor.execute("""
INSERT INTO miembros (nombre, telefono, direccion, fecha_nacimiento, sexo)
VALUES (?,?,?,?,?)
""", (nombre, telefono, direccion, fecha, sexo))
conn.commit()

bot.send_message(msg.chat.id, f"✅ Guardado: {nombre}", reply_markup=menu_principal())

===== VER MIEMBROS =====

@bot.message_handler(func=lambda m: m.text == "📋 Ver") def ver_miembros(msg): cursor.execute("SELECT nombre, telefono FROM miembros") data = cursor.fetchall()

if not data:
    bot.send_message(msg.chat.id, "No hay miembros")
    return

texto = "👥 Miembros:\n\n"
for m in data:
    texto += f"- {m[0]} ({m[1]})\n"

bot.send_message(msg.chat.id, texto)

===== PANEL =====

@bot.message_handler(func=lambda m: m.text == "📊 Panel") def panel(msg): cursor.execute("SELECT COUNT(*) FROM miembros") total = cursor.fetchone()[0]

bot.send_message(msg.chat.id, f"📊 Total miembros: {total}")

===== ASISTENTE =====

@bot.message_handler(func=lambda m: m.text == "🤖 Asistente") def asistente(msg): bot.send_message(msg.chat.id, "Puedes preguntar:\n- estado\n- miembros")

===== AYUDA =====

@bot.message_handler(func=lambda m: m.text == "🆘 Ayuda") def ayuda(msg): bot.send_message(msg.chat.id, "Usa botones.\nAgregar miembro paso a paso.")

===== RUN =====

bot.polling()
