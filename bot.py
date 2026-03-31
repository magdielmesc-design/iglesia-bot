import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
from datetime import datetime
import threading
import time

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS usuarios (
id INTEGER PRIMARY KEY,
chat_id TEXT UNIQUE,
nombre TEXT,
rol TEXT,
aprobado INTEGER
);

CREATE TABLE IF NOT EXISTS miembros (
id INTEGER PRIMARY KEY,
nombre TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS ayudas (
id INTEGER PRIMARY KEY,
tipo TEXT,
cantidad INTEGER
);

CREATE TABLE IF NOT EXISTS ayudas_asignadas (
id INTEGER PRIMARY KEY,
miembro TEXT,
tipo TEXT,
cantidad INTEGER,
fecha TEXT
);

CREATE TABLE IF NOT EXISTS oraciones (
id INTEGER PRIMARY KEY,
usuario_id INTEGER,
motivo TEXT,
fecha TEXT
);

CREATE TABLE IF NOT EXISTS estados (
chat_id TEXT PRIMARY KEY,
estado TEXT,
data TEXT
);

CREATE TABLE IF NOT EXISTS agenda (
id INTEGER PRIMARY KEY,
titulo TEXT,
fecha TEXT
);

CREATE TABLE IF NOT EXISTS casas (
id INTEGER PRIMARY KEY,
anfitrion TEXT,
direccion TEXT,
dia TEXT
);

CREATE TABLE IF NOT EXISTS servicios (
id INTEGER PRIMARY KEY,
fecha TEXT,
predicador TEXT,
tema TEXT,
coro TEXT
);

CREATE TABLE IF NOT EXISTS medicamentos (
id INTEGER PRIMARY KEY,
nombre TEXT,
stock INTEGER
);
""")
conn.commit()

# ===== UTIL =====
def user(chat):
    cursor.execute("SELECT * FROM usuarios WHERE chat_id=?", (chat,))
    return cursor.fetchone()

def es_admin(chat):
    u = user(chat)
    return u and u[3] in ["Pastor", "Líder"]

def es_pastor(chat):
    u = user(chat)
    return u and u[3] == "Pastor"

def set_estado(chat, estado, data=""):
    cursor.execute("REPLACE INTO estados VALUES (?,?,?)", (chat, estado, data))
    conn.commit()

def get_estado(chat):
    cursor.execute("SELECT estado,data FROM estados WHERE chat_id=?", (chat,))
    r = cursor.fetchone()
    return r if r else (None, None)

def clear_estado(chat):
    cursor.execute("DELETE FROM estados WHERE chat_id=?", (chat,))
    conn.commit()

def es_numero(x):
    try:
        return int(x)
    except:
        return None

def notificar_admins(msg):
    cursor.execute("SELECT chat_id FROM usuarios WHERE rol IN ('Pastor','Líder') AND aprobado=1")
    for u in cursor.fetchall():
        try:
            bot.send_message(u[0], msg)
        except:
            pass

# ===== MENÚS =====
def menu_principal(rol):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("👥 Miembros", "🙏 Oración")
    m.add("📦 Ayudas", "💊 Medicamentos")
    m.add("🏠 Casas", "⛪ Servicios")
    m.add("📅 Agenda", "📊 Reportes")
    if rol == "Pastor":
        m.add("⚙️ Control")
    return m

def menu_simple():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("⬅️ Volver")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    chat = str(msg.chat.id)
    nombre = msg.from_user.first_name

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    rol = "Pastor" if cursor.fetchone()[0] == 0 else "Miembro"

    cursor.execute("INSERT OR IGNORE INTO usuarios VALUES (NULL,?,?,?,0)",
                   (chat, nombre, rol))
    conn.commit()

    u = user(chat)

    if u[3] == "Pastor":
        cursor.execute("UPDATE usuarios SET aprobado=1 WHERE chat_id=?", (chat,))
        conn.commit()
        u = user(chat)

    if u[4] == 0:
        bot.send_message(msg.chat.id, "⏳ Espera aprobación")
        return

    bot.send_message(msg.chat.id, "Sistema listo", reply_markup=menu_principal(u[3]))

# ===== MOTOR =====
def motor():
    while True:
        try:
            hoy = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("SELECT titulo FROM agenda WHERE fecha=?", (hoy,))
            for e in cursor.fetchall():
                notificar_admins(f"📅 Hoy: {e[0]}")

            cursor.execute("SELECT tipo,SUM(cantidad) FROM ayudas GROUP BY tipo")
            for t, c in cursor.fetchall():
                if c <= 5:
                    notificar_admins(f"⚠️ Stock bajo: {t} ({c})")
        except:
            pass
        time.sleep(60)

threading.Thread(target=motor, daemon=True).start()

# ===== FLUJO =====
@bot.message_handler(func=lambda msg: True)
def flujo(msg):
    chat = str(msg.chat.id)
    estado, data = get_estado(chat)
    t = msg.text
    u = user(chat)

    if t == "⬅️ Volver":
        bot.send_message(msg.chat.id, "Menú", reply_markup=menu_principal(u[3]))
        clear_estado(chat)
        return

    # ===== MIEMBROS =====
    if t == "👥 Miembros":
        bot.send_message(msg.chat.id, "Nombre:")
        set_estado(chat, "m")
        return

    if estado == "m":
        try:
            cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (t,))
            conn.commit()
            bot.send_message(msg.chat.id, "Creado")
        except:
            bot.send_message(msg.chat.id, "Existe")
        clear_estado(chat)
        return

    # ===== AYUDAS =====
    if t == "📦 Ayudas":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id, "Tipo:")
        set_estado(chat, "a_t")
        return

    if estado == "a_t":
        set_estado(chat, "a_c", t)
        bot.send_message(msg.chat.id, "Cantidad:")
        return

    if estado == "a_c":
        c = es_numero(t)
        if c is None:
            bot.send_message(msg.chat.id, "Número inválido")
            return

        cursor.execute("INSERT INTO ayudas VALUES (NULL,?,?)", (data, c))
        conn.commit()
        notificar_admins(f"📦 Stock {data}+{c}")
        clear_estado(chat)
        bot.send_message(msg.chat.id, "OK")
        return

    # ===== ENTREGA =====
    if t == "📤 Entregar":
        cursor.execute("SELECT nombre FROM miembros")
        lista = "\n".join([x[0] for x in cursor.fetchall()])
        bot.send_message(msg.chat.id, lista)
        set_estado(chat, "e_m")
        return

    if estado == "e_m":
        set_estado(chat, "e_t", t)
        bot.send_message(msg.chat.id, "Tipo:")
        return

    if estado == "e_t":
        set_estado(chat, "e_c", data + "|" + t)
        bot.send_message(msg.chat.id, "Cantidad:")
        return

    if estado == "e_c":
        miembro, tipo = data.split("|")
        c = es_numero(t)
        if c is None:
            bot.send_message(msg.chat.id, "Número inválido")
            return

        cursor.execute("SELECT SUM(cantidad) FROM ayudas WHERE tipo=?", (tipo,))
        stock = cursor.fetchone()[0] or 0

        if c > stock:
            bot.send_message(msg.chat.id, "Stock insuficiente")
            return

        cursor.execute("UPDATE ayudas SET cantidad=cantidad-? WHERE tipo=?", (c, tipo))
        cursor.execute("INSERT INTO ayudas_asignadas VALUES (NULL,?,?,?,?)",
                       (miembro, tipo, c, datetime.now()))
        conn.commit()

        notificar_admins(f"📤 {miembro} recibió {c} de {tipo}")
        clear_estado(chat)
        bot.send_message(msg.chat.id, "Entrega OK")
        return

    # ===== ORACIÓN =====
    if t == "🙏 Oración":
        bot.send_message(msg.chat.id, "Motivo:")
        set_estado(chat, "or")
        return

    if estado == "or":
        cursor.execute("INSERT INTO oraciones VALUES (NULL,?,?,?)",
                       (u[0], t, datetime.now()))
        conn.commit()
        bot.send_message(msg.chat.id, "Guardado")
        clear_estado(chat)
        return

    # ===== AGENDA =====
    if t == "📅 Agenda":
        bot.send_message(msg.chat.id, "Título:")
        set_estado(chat, "ag_t")
        return

    if estado == "ag_t":
        set_estado(chat, "ag_f", t)
        bot.send_message(msg.chat.id, "Fecha YYYY-MM-DD:")
        return

    if estado == "ag_f":
        cursor.execute("INSERT INTO agenda VALUES (NULL,?,?)", (data, t))
        conn.commit()
        bot.send_message(msg.chat.id, "Evento creado")
        clear_estado(chat)
        return

    # ===== REPORTES =====
    if t == "📊 Reportes":
        cursor.execute("SELECT SUM(cantidad) FROM ayudas_asignadas")
        total = cursor.fetchone()[0] or 0
        bot.send_message(msg.chat.id, f"Total entregado: {total}")
        return

print("BOT FINAL ACTIVO")
bot.infinity_polling()
