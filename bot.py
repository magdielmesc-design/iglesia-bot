import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
from datetime import datetime

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS ayudas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    cantidad INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS medicamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    cantidad INTEGER
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

    rol = "Pastor" if total == 0 else "Miembro"

    cursor.execute("INSERT OR IGNORE INTO usuarios (chat_id, rol) VALUES (?, ?)", (chat_id, rol))
    conn.commit()

    return rol

# ===== MENÚ =====
def menu_principal(rol):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    if rol == "Pastor":
        markup.add("👥 Miembros", "🙏 Oración")
        markup.add("📦 Ayudas", "💊 Medicamentos")
        markup.add("⚙️ Admin")
    else:
        markup.add("🙏 Oración")

    return markup

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    chat_id = str(msg.chat.id)
    registrar_usuario(chat_id)
    rol = obtener_rol(chat_id)

    bot.send_message(msg.chat.id, f"Sistema activo\nRol: {rol}", reply_markup=menu_principal(rol))

# ===== MIEMBROS =====
@bot.message_handler(func=lambda m: m.text == "👥 Miembros")
def miembros_menu(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Miembro", "📋 Miembros", "⬅️ Volver")
    bot.send_message(msg.chat.id, "Miembros", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Miembro")
def agregar_miembro(msg):
    msg2 = bot.send_message(msg.chat.id, "Nombre:")
    bot.register_next_step_handler(msg2, guardar_miembro)

def guardar_miembro(msg):
    cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (msg.text,))
    conn.commit()
    bot.send_message(msg.chat.id, "Guardado")

@bot.message_handler(func=lambda m: m.text == "📋 Miembros")
def ver_miembros(msg):
    cursor.execute("SELECT nombre FROM miembros")
    datos = cursor.fetchall()
    texto = "\n".join([f"- {d[0]}" for d in datos]) or "Sin datos"
    bot.send_message(msg.chat.id, texto)

# ===== ORACIÓN =====
@bot.message_handler(func=lambda m: m.text == "🙏 Oración")
def oracion_menu(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Nueva Oración", "📖 Ver Oraciones", "⬅️ Volver")
    bot.send_message(msg.chat.id, "Oración", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📝 Nueva Oración")
def agregar_oracion(msg):
    msg2 = bot.send_message(msg.chat.id, "Motivo:")
    bot.register_next_step_handler(msg2, guardar_oracion)

def guardar_oracion(msg):
    usuario = str(msg.chat.id)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("INSERT INTO oraciones (usuario, motivo, fecha) VALUES (?, ?, ?)",
                   (usuario, msg.text, fecha))
    conn.commit()

    bot.send_message(msg.chat.id, "Guardado")

@bot.message_handler(func=lambda m: m.text == "📖 Ver Oraciones")
def ver_oraciones(msg):
    cursor.execute("SELECT motivo, fecha FROM oraciones ORDER BY id DESC LIMIT 10")
    datos = cursor.fetchall()
    texto = "\n".join([f"- {d[0]} ({d[1]})" for d in datos]) or "Sin datos"
    bot.send_message(msg.chat.id, texto)

# ===== AYUDAS =====
@bot.message_handler(func=lambda m: m.text == "📦 Ayudas")
def ayudas_menu(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Ayuda", "📊 Stock Ayudas", "⬅️ Volver")
    bot.send_message(msg.chat.id, "Ayudas", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Ayuda")
def agregar_ayuda(msg):
    msg2 = bot.send_message(msg.chat.id, "Tipo:")
    bot.register_next_step_handler(msg2, guardar_ayuda)

def guardar_ayuda(msg):
    tipo = msg.text
    msg2 = bot.send_message(msg.chat.id, "Cantidad:")
    bot.register_next_step_handler(msg2, lambda m: finalizar_ayuda(m, tipo))

def finalizar_ayuda(msg, tipo):
    cursor.execute("INSERT INTO ayudas (tipo, cantidad) VALUES (?,?)", (tipo, int(msg.text)))
    conn.commit()
    bot.send_message(msg.chat.id, "Guardado")

@bot.message_handler(func=lambda m: m.text == "📊 Stock Ayudas")
def ver_ayudas(msg):
    cursor.execute("SELECT tipo, SUM(cantidad) FROM ayudas GROUP BY tipo")
    datos = cursor.fetchall()
    texto = "\n".join([f"{d[0]}: {d[1]}" for d in datos]) or "Sin datos"
    bot.send_message(msg.chat.id, texto)

# ===== MEDICAMENTOS =====
@bot.message_handler(func=lambda m: m.text == "💊 Medicamentos")
def medicamentos_menu(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Medicamento", "📊 Stock Medicamentos", "⬅️ Volver")
    bot.send_message(msg.chat.id, "Medicamentos", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Medicamento")
def agregar_medicamento(msg):
    msg2 = bot.send_message(msg.chat.id, "Nombre:")
    bot.register_next_step_handler(msg2, guardar_medicamento)

def guardar_medicamento(msg):
    nombre = msg.text
    msg2 = bot.send_message(msg.chat.id, "Cantidad:")
    bot.register_next_step_handler(msg2, lambda m: finalizar_medicamento(m, nombre))

def finalizar_medicamento(msg, nombre):
    cursor.execute("INSERT INTO medicamentos (nombre, cantidad) VALUES (?,?)", (nombre, int(msg.text)))
    conn.commit()
    bot.send_message(msg.chat.id, "Guardado")

@bot.message_handler(func=lambda m: m.text == "📊 Stock Medicamentos")
def ver_medicamentos(msg):
    cursor.execute("SELECT nombre, SUM(cantidad) FROM medicamentos GROUP BY nombre")
    datos = cursor.fetchall()
    texto = "\n".join([f"{d[0]}: {d[1]}" for d in datos]) or "Sin datos"
    bot.send_message(msg.chat.id, texto)

# ===== VOLVER =====
@bot.message_handler(func=lambda m: m.text == "⬅️ Volver")
def volver(msg):
    chat_id = str(msg.chat.id)
    rol = obtener_rol(chat_id)
    bot.send_message(msg.chat.id, "Menú principal", reply_markup=menu_principal(rol))

# ===== RUN =====
print("BOT MEJORADO ACTIVO")
bot.infinity_polling()
