import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, os, time, csv, threading
from datetime import datetime

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""

CREATE TABLE IF NOT EXISTS usuarios (
id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT
);

CREATE TABLE IF NOT EXISTS miembros (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
telefono TEXT,
direccion TEXT,
aprobado INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS oraciones (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
motivo TEXT
);

CREATE TABLE IF NOT EXISTS medicamentos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
stock INTEGER,
tipo TEXT,
uso TEXT
);

CREATE TABLE IF NOT EXISTS ayudas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
cantidad INTEGER,
unidad TEXT,
estado TEXT DEFAULT 'sin_asignar',
lider_id INTEGER,
destino TEXT
);

CREATE TABLE IF NOT EXISTS discipulos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
telefono TEXT,
casa_id INTEGER
);

CREATE TABLE IF NOT EXISTS casas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
anfitrion_id INTEGER,
direccion TEXT,
dia TEXT,
hora TEXT,
discipuladores TEXT
);

CREATE TABLE IF NOT EXISTS agenda (
id INTEGER PRIMARY KEY AUTOINCREMENT,
tipo TEXT,
user_id INTEGER,
evento TEXT,
fecha TEXT
);

""")

conn.commit()

estado = {}
data_temp = {}
temp = {}

# ===== ROLES =====
def get_rol(chat):
    cursor.execute("SELECT rol FROM usuarios WHERE id=?", (chat,))
    r = cursor.fetchone()
    return r[0] if r else None

def es_pastor(chat):
    return get_rol(chat) == "Pastor"

# ===== MENU =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("👥 Miembros","📦 Ayudas")
    m.row("🙏 Oración","💊 Medicamentos")
    m.row("🏠 Casas","📅 Agenda")
    m.row("📊 Panel","📤 Exportar")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    bot.send_message(m.chat.id,"Sistema Iglesia",reply_markup=menu())

# ===== PANEL =====
@bot.message_handler(func=lambda m: m.text=="📊 Panel")
def panel(m):
    cursor.execute("SELECT COUNT(*) FROM miembros WHERE aprobado=1")
    m1 = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM discipulos")
    d = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ayudas WHERE estado='sin_asignar'")
    a = cursor.fetchone()[0]

    bot.send_message(m.chat.id,f"Miembros:{m1}\nDiscípulos:{d}\nAyudas pendientes:{a}")

# ===== AYUDAS MENU =====
@bot.message_handler(func=lambda m: m.text=="📦 Ayudas")
def ayudas_menu(m):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Crear","📋 Ver")
    markup.row("📌 Asignar","🔙 Volver")
    bot.send_message(m.chat.id,"Ayudas:",reply_markup=markup)

# ===== CREAR AYUDA =====
@bot.message_handler(func=lambda m: m.text=="➕ Crear")
def crear_ayuda(m):
    if not es_pastor(m.chat.id):
        return bot.send_message(m.chat.id,"Solo Pastor")
    estado[m.chat.id]="a1"
    bot.send_message(m.chat.id,"Nombre:")

@bot.message_handler(func=lambda m: estado.get(m.chat.id)=="a1")
def a1(m):
    data_temp[m.chat.id]={"n":m.text}
    estado[m.chat.id]="a2"
    bot.send_message(m.chat.id,"Cantidad:")

@bot.message_handler(func=lambda m: estado.get(m.chat.id)=="a2")
def a2(m):
    data_temp[m.chat.id]["c"]=m.text
    estado[m.chat.id]="a3"
    bot.send_message(m.chat.id,"Unidad:")

@bot.message_handler(func=lambda m: estado.get(m.chat.id)=="a3")
def a3(m):
    d=data_temp[m.chat.id]
    cursor.execute("INSERT INTO ayudas (nombre,cantidad,unidad) VALUES (?,?,?)",
                   (d["n"],d["c"],m.text))
    conn.commit()
    bot.send_message(m.chat.id,"Guardado")
    estado[m.chat.id]=None

# ===== AUTOMATIZACIÓN =====
def tareas():
    while True:
        try:
            hoy=datetime.now().strftime("%Y-%m-%d")

            cursor.execute("SELECT evento FROM agenda WHERE fecha=?", (hoy,))
            for (e,) in cursor.fetchall():
                cursor.execute("SELECT id FROM usuarios")
                for (uid,) in cursor.fetchall():
                    try: bot.send_message(uid,f"Hoy: {e}")
                    except: pass

        except: pass
        time.sleep(3600)

threading.Thread(target=tareas).start()

print("ACTIVO")
bot.infinity_polling()
