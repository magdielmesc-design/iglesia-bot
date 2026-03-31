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

CREATE TABLE IF NOT EXISTS recordatorios (
id INTEGER PRIMARY KEY,
chat_id TEXT,
mensaje TEXT,
fecha TEXT
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

def menu(rol):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("👥 Miembros", "📦 Ayudas")
    m.add("📊 Stock", "📤 Entregar")
    m.add("📊 Reportes PRO", "📊 Reporte Avanzado")
    m.add("📅 Agenda", "⬅️ Volver")
    if rol == "Pastor":
        m.add("⚙️ Control")
    return m

def notificar_admins(msg):
    cursor.execute("SELECT chat_id FROM usuarios WHERE rol IN ('Pastor','Líder') AND aprobado=1")
    for u in cursor.fetchall():
        try:
            bot.send_message(u[0], msg)
        except:
            pass

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
        bot.send_message(msg.chat.id, "⏳ Pendiente aprobación")
        return

    bot.send_message(msg.chat.id, "Sistema activo", reply_markup=menu(u[3]))

# ===== CONTROL =====
@bot.message_handler(func=lambda m: m.text == "⚙️ Control")
def control(msg):
    if not es_admin(str(msg.chat.id)):
        return

    cursor.execute("SELECT id,nombre FROM usuarios WHERE aprobado=0")
    data = cursor.fetchall()

    txt = "\n".join([f"{x[0]}-{x[1]}" for x in data]) or "Vacío"
    bot.send_message(msg.chat.id, txt + "\nID:")
    set_estado(str(msg.chat.id), "aprobar")

# ===== MOTOR =====
def verificar_stock():
    cursor.execute("SELECT tipo,SUM(cantidad) FROM ayudas GROUP BY tipo")
    for t, c in cursor.fetchall():
        if c <= 5:
            notificar_admins(f"⚠️ Stock bajo: {t} ({c})")

def revisar_agenda():
    hoy = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT titulo FROM agenda WHERE fecha=?", (hoy,))
    for e in cursor.fetchall():
        notificar_admins(f"📅 Hoy: {e[0]}")

def ejecutar_recordatorios():
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("SELECT id,chat_id,mensaje FROM recordatorios WHERE fecha=?", (ahora,))
    for r in cursor.fetchall():
        try:
            bot.send_message(r[1], f"⏰ {r[2]}")
        except:
            pass
        cursor.execute("DELETE FROM recordatorios WHERE id=?", (r[0],))
        conn.commit()

def motor():
    while True:
        try:
            verificar_stock()
            revisar_agenda()
            ejecutar_recordatorios()
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

    # aprobar
    if estado == "aprobar":
        cursor.execute("UPDATE usuarios SET aprobado=1 WHERE id=?", (t,))
        conn.commit()
        clear_estado(chat)
        bot.send_message(msg.chat.id, "Aprobado")
        return

    # miembros
    if t == "👥 Miembros":
        bot.send_message(msg.chat.id, "Nombre:")
        set_estado(chat, "m")
        return

    if estado == "m":
        try:
            cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (t,))
            conn.commit()
            bot.send_message(msg.chat.id, "OK")
        except:
            bot.send_message(msg.chat.id, "Existe")
        clear_estado(chat)
        return

    # ayudas
    if t == "📦 Ayudas":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id, "Tipo:")
        set_estado(chat, "tipo")
        return

    if estado == "tipo":
        set_estado(chat, "cant", t)
        bot.send_message(msg.chat.id, "Cantidad:")
        return

    if estado == "cant":
        cursor.execute("INSERT INTO ayudas VALUES (NULL,?,?)", (data, int(t)))
        conn.commit()
        notificar_admins(f"📦 Stock: {data}+{t}")
        clear_estado(chat)
        bot.send_message(msg.chat.id, "OK")
        return

    # stock
    if t == "📊 Stock":
        cursor.execute("SELECT tipo,SUM(cantidad) FROM ayudas GROUP BY tipo")
        txt = "\n".join([f"{x[0]}:{x[1]}" for x in cursor.fetchall()])
        bot.send_message(msg.chat.id, txt or "Vacío")
        return

    # entregar
    if t == "📤 Entregar":
        if not es_admin(chat): return
        cursor.execute("SELECT nombre FROM miembros")
        lista = "\n".join([x[0] for x in cursor.fetchall()])
        bot.send_message(msg.chat.id, lista)
        set_estado(chat, "ent_m")
        return

    if estado == "ent_m":
        set_estado(chat, "ent_t", t)
        bot.send_message(msg.chat.id, "Tipo:")
        return

    if estado == "ent_t":
        set_estado(chat, "ent_c", data + "|" + t)
        bot.send_message(msg.chat.id, "Cantidad:")
        return

    if estado == "ent_c":
        miembro, tipo = data.split("|")
        cantidad = int(t)

        cursor.execute("SELECT SUM(cantidad) FROM ayudas WHERE tipo=?", (tipo,))
        stock = cursor.fetchone()[0] or 0

        if cantidad > stock:
            bot.send_message(msg.chat.id, "Stock insuficiente")
            return

        cursor.execute("INSERT INTO ayudas_asignadas VALUES (NULL,?,?,?,?)",
                       (miembro, tipo, cantidad, datetime.now()))

        cursor.execute("UPDATE ayudas SET cantidad = cantidad - ? WHERE tipo=?",
                       (cantidad, tipo))

        conn.commit()

        notificar_admins(f"📤 {miembro} recibió {cantidad} de {tipo}")

        clear_estado(chat)
        bot.send_message(msg.chat.id, "Entrega OK")
        return

    # reporte pro
    if t == "📊 Reportes PRO":
        cursor.execute("SELECT SUM(cantidad) FROM ayudas_asignadas")
        total = cursor.fetchone()[0] or 0
        bot.send_message(msg.chat.id, f"Total entregado: {total}")
        return

    # volver
    if t == "⬅️ Volver":
        u = user(chat)
        bot.send_message(msg.chat.id, "Menú", reply_markup=menu(u[3]))
        clear_estado(chat)
        return

# ===== RUN =====
print("SISTEMA FINAL ACTIVO")
bot.infinity_polling()
