import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, os, time, threading
from datetime import datetime

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT);

CREATE TABLE IF NOT EXISTS miembros (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
telefono TEXT,
direccion TEXT,
aprobado INTEGER DEFAULT 0
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

CREATE TABLE IF NOT EXISTS medicamentos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
stock INTEGER
);

CREATE TABLE IF NOT EXISTS discipulos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
telefono TEXT
);

CREATE TABLE IF NOT EXISTS casas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nombre TEXT,
dia TEXT,
hora TEXT
);

CREATE TABLE IF NOT EXISTS agenda (
id INTEGER PRIMARY KEY AUTOINCREMENT,
evento TEXT,
fecha TEXT
);
""")
conn.commit()

estado = {}
temp = {}

# ===== ROLES =====
def es_pastor(chat):
    cursor.execute("SELECT rol FROM usuarios WHERE id=?", (chat,))
    r = cursor.fetchone()
    return r and r[0] == "Pastor"

# ===== MENUS =====
def menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("👥 Miembros","📦 Ayudas")
    m.row("💊 Medicamentos","🏠 Casas")
    m.row("📅 Agenda","📊 Panel")
    return m

def menu_back():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔙 Volver")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    bot.send_message(m.chat.id,"Sistema Iglesia",reply_markup=menu())

# ===== HANDLER PRINCIPAL =====
@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text
    st = estado.get(chat)

    # ===== VOLVER =====
    if text == "🔙 Volver":
        estado[chat] = None
        return bot.send_message(chat,"Menú",reply_markup=menu())

    # ===== PANEL =====
    if text == "📊 Panel":
        cursor.execute("SELECT COUNT(*) FROM miembros WHERE aprobado=1")
        m1 = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM discipulos")
        d = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ayudas WHERE estado='sin_asignar'")
        a = cursor.fetchone()[0]
        return bot.send_message(chat,f"👥 {m1} miembros\n🧑 {d} discípulos\n📦 {a} pendientes")

    # ===== MIEMBROS =====
    if text == "👥 Miembros":
        estado[chat] = "m1"
        return bot.send_message(chat,"Nombre:",reply_markup=menu_back())

    if st == "m1":
        temp[chat]={"n":text}
        estado[chat]="m2"
        return bot.send_message(chat,"Teléfono:")

    if st == "m2":
        temp[chat]["t"]=text
        estado[chat]="m3"
        return bot.send_message(chat,"Dirección:")

    if st == "m3":
        aprobado = 1 if es_pastor(chat) else 0
        d=temp[chat]
        cursor.execute("INSERT INTO miembros (nombre,telefono,direccion,aprobado) VALUES (?,?,?,?)",
                       (d["n"],d["t"],text,aprobado))
        conn.commit()
        estado[chat]=None
        return bot.send_message(chat,"Guardado",reply_markup=menu())

    # ===== AYUDAS =====
    if text == "📦 Ayudas":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Crear",callback_data="crear_ayuda"))
        markup.add(InlineKeyboardButton("📋 Ver",callback_data="ver_ayuda"))
        markup.add(InlineKeyboardButton("📌 Asignar",callback_data="asignar"))
        return bot.send_message(chat,"Ayudas:",reply_markup=markup)

    # ===== MEDICAMENTOS =====
    if text == "💊 Medicamentos":
        cursor.execute("SELECT nombre,stock FROM medicamentos")
        data=cursor.fetchall()
        msg="\n".join([f"{n}: {s}" for n,s in data])
        return bot.send_message(chat,msg or "Sin stock")

    # ===== CASAS =====
    if text == "🏠 Casas":
        estado[chat]="c1"
        return bot.send_message(chat,"Nombre casa:")

    if st=="c1":
        temp[chat]={"n":text}
        estado[chat]="c2"
        return bot.send_message(chat,"Día:")

    if st=="c2":
        temp[chat]["d"]=text
        estado[chat]="c3"
        return bot.send_message(chat,"Hora:")

    if st=="c3":
        cursor.execute("INSERT INTO casas (nombre,dia,hora) VALUES (?,?,?)",
                       (temp[chat]["n"],temp[chat]["d"],text))
        conn.commit()
        estado[chat]=None
        return bot.send_message(chat,"Casa guardada",reply_markup=menu())

    # ===== AGENDA =====
    if text == "📅 Agenda":
        estado[chat]="ag1"
        return bot.send_message(chat,"Evento:")

    if st=="ag1":
        temp[chat]={"e":text}
        estado[chat]="ag2"
        return bot.send_message(chat,"Fecha:")

    if st=="ag2":
        cursor.execute("INSERT INTO agenda (evento,fecha) VALUES (?,?)",
                       (temp[chat]["e"],text))
        conn.commit()
        estado[chat]=None
        return bot.send_message(chat,"Guardado",reply_markup=menu())

# ===== CALLBACKS =====
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    chat = call.message.chat.id

    if call.data=="crear_ayuda":
        estado[chat]="a1"
        bot.send_message(chat,"Nombre:")

    elif call.data=="ver_ayuda":
        cursor.execute("SELECT id,nombre,estado FROM ayudas")
        data=cursor.fetchall()
        msg="\n".join([f"{i}-{n}({e})" for i,n,e in data])
        bot.send_message(chat,msg or "Sin datos")

    elif call.data=="asignar":
        cursor.execute("SELECT id,nombre FROM ayudas WHERE estado='sin_asignar'")
        markup=InlineKeyboardMarkup()
        for i,n in cursor.fetchall():
            markup.add(InlineKeyboardButton(n,callback_data=f"sel_{i}"))
        bot.send_message(chat,"Selecciona:",reply_markup=markup)

    elif call.data.startswith("sel_"):
        aid=call.data.split("_")[1]
        cursor.execute("UPDATE ayudas SET estado='asignada' WHERE id=?", (aid,))
        conn.commit()
        bot.send_message(chat,"Asignada")

# ===== AUTOMATIZACIÓN =====
def loop():
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

threading.Thread(target=loop).start()

print("ACTIVO")
bot.remove_webhook()
time.sleep(2)
bot.infinity_polling()
