BOT IGLESIA MONTE DE DIOS - VERSION FINAL

Listo para Railway + Telegram

import telebot from telebot.types import ReplyKeyboardMarkup import sqlite3 import os import random from datetime import datetime

TOKEN = os.getenv("TOKEN") bot = telebot.TeleBot(TOKEN)

================== DB ==================

conn = sqlite3.connect("iglesia.db", check_same_thread=False) cursor = conn.cursor()

TABLAS PRINCIPALES

cursor.execute(""" CREATE TABLE IF NOT EXISTS miembros ( id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT, direccion TEXT, fecha_nacimiento TEXT, sexo TEXT ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS departamentos ( id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS miembro_departamento ( miembro_id INTEGER, departamento_id INTEGER ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS roles ( id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, nivel INTEGER ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS miembro_rol ( miembro_id INTEGER, rol_id INTEGER, departamento_id INTEGER, celula_id INTEGER ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS celulas ( id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, lider_id INTEGER, ayudante_id INTEGER, dia TEXT, hora TEXT ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS casas_paz ( id INTEGER PRIMARY KEY AUTOINCREMENT, anfitrion TEXT, discipulador1 INTEGER, discipulador2 INTEGER, dia TEXT, hora TEXT ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS promesas ( id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT, referencia TEXT, fecha_ultimo_uso TEXT ) """)

conn.commit()

================== MENU ==================

def menu(): markup = ReplyKeyboardMarkup(resize_keyboard=True) markup.add("Miembros", "Departamentos") markup.add("Células", "Casas de Paz") markup.add("Promesas", "Asistente") markup.add("Ayuda") return markup

================== START ==================

@bot.message_handler(commands=['start']) def start(msg): bot.send_message(msg.chat.id, "Sistema Iglesia Monte de Dios activo", reply_markup=menu())

================== MIEMBROS ==================

@bot.message_handler(func=lambda m: m.text == "Miembros") def miembros(msg): bot.send_message(msg.chat.id, "Escribe:\nNombre, Teléfono, Dirección, FechaNacimiento(YYYY-MM-DD), Sexo") bot.register_next_step_handler(msg, guardar_miembro)

def guardar_miembro(msg): try: datos = msg.text.split(",") cursor.execute("INSERT INTO miembros (nombre, telefono, direccion, fecha_nacimiento, sexo) VALUES (?,?,?,?,?)", (datos[0], datos[1], datos[2], datos[3], datos[4])) conn.commit() bot.send_message(msg.chat.id, "Miembro guardado") except: bot.send_message(msg.chat.id, "Error al guardar")

================== DEPARTAMENTOS ==================

@bot.message_handler(func=lambda m: m.text == "Departamentos") def deptos(msg): bot.send_message(msg.chat.id, "Escribe nombre del departamento") bot.register_next_step_handler(msg, guardar_depto)

def guardar_depto(msg): cursor.execute("INSERT INTO departamentos (nombre, tipo) VALUES (?,?)", (msg.text, "general")) conn.commit() bot.send_message(msg.chat.id, "Departamento creado")

================== CELULAS ==================

@bot.message_handler(func=lambda m: m.text == "Células") def celulas(msg): bot.send_message(msg.chat.id, "Nombre, Dia, Hora") bot.register_next_step_handler(msg, guardar_celula)

def guardar_celula(msg): d = msg.text.split(",") cursor.execute("INSERT INTO celulas (nombre, dia, hora) VALUES (?,?,?)", (d[0], d[1], d[2])) conn.commit() bot.send_message(msg.chat.id, "Célula creada")

================== CASAS DE PAZ ==================

@bot.message_handler(func=lambda m: m.text == "Casas de Paz") def casas(msg): bot.send_message(msg.chat.id, "Anfitrión, Discipulador1ID, Discipulador2ID, Dia, Hora") bot.register_next_step_handler(msg, guardar_casa)

def guardar_casa(msg): d = msg.text.split(",") cursor.execute("INSERT INTO casas_paz (anfitrion, discipulador1, discipulador2, dia, hora) VALUES (?,?,?,?,?)", (d[0], d[1], d[2], d[3], d[4])) conn.commit() bot.send_message(msg.chat.id, "Casa creada")

================== PROMESAS ==================

@bot.message_handler(func=lambda m: m.text == "Promesas") def promesas(msg): bot.send_message(msg.chat.id, "1. Agregar\n2. Ver aleatoria") bot.register_next_step_handler(msg, menu_promesas)

def menu_promesas(msg): if msg.text == "1": bot.send_message(msg.chat.id, "Texto\nReferencia") bot.register_next_step_handler(msg, guardar_promesa) else: cursor.execute("SELECT texto, referencia FROM promesas ORDER BY RANDOM() LIMIT 1") p = cursor.fetchone() if p: bot.send_message(msg.chat.id, f"📖 Promesa\n\n{p[0]}\n— {p[1]}") else: bot.send_message(msg.chat.id, "No hay promesas")

def guardar_promesa(msg): lineas = msg.text.split("\n") cursor.execute("INSERT INTO promesas (texto, referencia, fecha_ultimo_uso) VALUES (?,?,?)", (lineas[0], lineas[1], datetime.now())) conn.commit() bot.send_message(msg.chat.id, "Promesa guardada")

================== ASISTENTE ==================

@bot.message_handler(func=lambda m: m.text == "Asistente") def asistente(msg): cursor.execute("SELECT COUNT(*) FROM miembros") miembros = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM celulas")
celulas = cursor.fetchone()[0]

bot.send_message(msg.chat.id,
                 f"Estado:\nMiembros: {miembros}\nCélulas: {celulas}")

================== AYUDA ==================

@bot.message_handler(func=lambda m: m.text == "Ayuda") def ayuda(msg): bot.send_message(msg.chat.id, "Usa el menú.\nMiembros: agregar personas\nCélulas: crear grupos\nPromesas: versículos")

================== RUN ==================

bot.polling()
