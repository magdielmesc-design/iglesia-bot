import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3, os, time, csv

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
    m.add("👥 Miembros","🙏 Oración")
    m.add("💊 Medicamentos","📦 Ayudas")
    m.add("📦 Asignar Ayuda","📦 Ver Ayudas")
    m.add("🏠 Casas","➕ Discípulo")
    m.add("📅 Agenda","📊 Ver Todo")
    m.add("📤 Exportar")
    return m

# ===== CONTROL =====
def cancelar(chat):
    estado[chat] = None
    data_temp[chat] = {}
    bot.send_message(chat,"Cancelado",reply_markup=menu())

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    data_temp[m.chat.id] = {}
    bot.send_message(m.chat.id,"Sistema Iglesia Monte de Dios",reply_markup=menu())

# ===== ROL =====
@bot.message_handler(commands=['rol'])
def rol(m):
    try:
        _, nombre, rol = m.text.split(" ",2)
        cursor.execute("INSERT OR REPLACE INTO usuarios VALUES (?,?,?)",(m.chat.id,nombre,rol))
        conn.commit()
        bot.reply_to(m,"Rol asignado")
    except:
        bot.reply_to(m,"Uso: /rol Nombre Pastor|Lider|Miembro")

# ===== BOT =====
@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text.strip()

    if text.lower() == "cancelar":
        cancelar(chat)
        return

    if text == "-":
        text = ""

    st = estado.get(chat)

    try:
        # ===== MIEMBROS =====
        if text == "👥 Miembros":
            estado[chat] = "m1"
            data_temp[chat] = {}
            bot.send_message(chat,"Nombre:")

        elif st == "m1":
            data_temp[chat]["n"] = text
            estado[chat] = "m2"
            bot.send_message(chat,"Teléfono (- si no):")

        elif st == "m2":
            data_temp[chat]["t"] = text
            estado[chat] = "m3"
            bot.send_message(chat,"Dirección (- si no):")

        elif st == "m3":
            aprobado = 1 if es_pastor(chat) else 0
            d = data_temp[chat]

            cursor.execute("INSERT INTO miembros (nombre,telefono,direccion,aprobado) VALUES (?,?,?,?)",
                           (d["n"],d["t"],text,aprobado))
            conn.commit()

            bot.send_message(chat,"Guardado" if aprobado else "Pendiente aprobación")
            cancelar(chat)

        # ===== ORACION =====
        elif text == "🙏 Oración":
            estado[chat] = "o1"
            bot.send_message(chat,"Motivo:")

        elif st == "o1":
            cursor.execute("INSERT INTO oraciones (user_id,motivo) VALUES (?,?)",(chat,text))
            conn.commit()
            bot.send_message(chat,"Guardado")
            cancelar(chat)

        # ===== MEDICAMENTOS (VER STOCK TODOS) =====
        elif text == "💊 Medicamentos":
            cursor.execute("SELECT nombre,stock FROM medicamentos")
            data = cursor.fetchall()
            msg = "\n".join([f"{n}: {s}" for n,s in data])
            bot.send_message(chat,msg or "Sin stock")

        # ===== AYUDAS =====
        elif text == "📦 Ayudas":
            if not es_pastor(chat):
                bot.send_message(chat,"Solo Pastor")
                return
            estado[chat] = "a1"
            data_temp[chat] = {}
            bot.send_message(chat,"Nombre:")

        elif st == "a1":
            data_temp[chat]["n"] = text
            estado[chat] = "a2"
            bot.send_message(chat,"Cantidad:")

        elif st == "a2":
            data_temp[chat]["c"] = text
            estado[chat] = "a3"
            bot.send_message(chat,"Unidad:")

        elif st == "a3":
            d = data_temp[chat]
            cursor.execute("INSERT INTO ayudas (nombre,cantidad,unidad) VALUES (?,?,?)",
                           (d["n"],d["c"],text))
            conn.commit()
            bot.send_message(chat,"Ayuda registrada (sin asignar)")
            cancelar(chat)

        # ===== ASIGNAR AYUDA =====
        elif text == "📦 Asignar Ayuda":
            if not es_pastor(chat):
                return bot.send_message(chat,"Solo Pastor")

            cursor.execute("SELECT id,nombre FROM ayudas WHERE estado='sin_asignar'")
            data = cursor.fetchall()

            if not data:
                return bot.send_message(chat,"No hay pendientes")

            msg = "\n".join([f"{i}-{n}" for i,n in data])
            bot.send_message(chat,"ID ayuda:\n"+msg)
            estado[chat] = "as1"

        elif st == "as1":
            data_temp[chat] = {"id": text}
            estado[chat] = "as2"
            bot.send_message(chat,"ID líder:")

        elif st == "as2":
            data_temp[chat]["l"] = text
            estado[chat] = "as3"
            bot.send_message(chat,"Destino:")

        elif st == "as3":
            d = data_temp[chat]

            cursor.execute("""
            UPDATE ayudas SET estado='asignada', lider_id=?, destino=?
            WHERE id=?
            """,(d["l"],text,d["id"]))
            conn.commit()

            try:
                bot.send_message(int(d["l"]),f"Entrega ayuda {d['id']} a {text}")
            except:
                pass

            bot.send_message(chat,"Asignada")
            cancelar(chat)

        # ===== ENTREGAR AYUDA =====
        elif text == "📦 Ver Ayudas":
            cursor.execute("SELECT id,nombre,estado FROM ayudas")
            data = cursor.fetchall()

            msg = "\n".join([f"{i}-{n}({e})" for i,n,e in data])
            bot.send_message(chat,msg or "Sin datos")

        # ===== DISCIPULOS =====
        elif text == "➕ Discípulo":
            estado[chat] = "d1"
            bot.send_message(chat,"Nombre:")

        elif st == "d1":
            data_temp[chat] = {"n": text}
            estado[chat] = "d2"
            bot.send_message(chat,"Teléfono (- si no):")

        elif st == "d2":
            cursor.execute("INSERT INTO discipulos (nombre,telefono) VALUES (?,?)",
                           (data_temp[chat]["n"],text))
            conn.commit()
            bot.send_message(chat,"Discípulo guardado")
            cancelar(chat)

        # ===== CASAS =====
        elif text == "🏠 Casas":
            estado[chat] = "c1"
            bot.send_message(chat,"Nombre:")

        elif st == "c1":
            data_temp[chat] = {"n": text}
            estado[chat] = "c2"
            bot.send_message(chat,"ID anfitrión:")

        elif st == "c2":
            data_temp[chat]["a"] = text
            estado[chat] = "c3"
            bot.send_message(chat,"Dirección:")

        elif st == "c3":
            data_temp[chat]["d"] = text
            estado[chat] = "c4"
            bot.send_message(chat,"Día:")

        elif st == "c4":
            data_temp[chat]["dia"] = text
            estado[chat] = "c5"
            bot.send_message(chat,"Hora:")

        elif st == "c5":
            data_temp[chat]["h"] = text
            estado[chat] = "c6"
            bot.send_message(chat,"IDs discipuladores:")

        elif st == "c6":
            d = data_temp[chat]
            cursor.execute("""
            INSERT INTO casas (nombre,anfitrion_id,direccion,dia,hora,discipuladores)
            VALUES (?,?,?,?,?,?)
            """,(d["n"],d["a"],d["d"],d["dia"],d["h"],text))
            conn.commit()
            bot.send_message(chat,"Casa guardada")
            cancelar(chat)

        # ===== AGENDA =====
        elif text == "📅 Agenda":
            estado[chat] = "ag1"
            bot.send_message(chat,"Tipo (iglesia/personal):")

        elif st == "ag1":
            data_temp[chat] = {"t": text}
            estado[chat] = "ag2"
            bot.send_message(chat,"Evento:")

        elif st == "ag2":
            data_temp[chat]["e"] = text
            estado[chat] = "ag3"
            bot.send_message(chat,"Fecha:")

        elif st == "ag3":
            d = data_temp[chat]
            cursor.execute("INSERT INTO agenda (tipo,user_id,evento,fecha) VALUES (?,?,?,?)",
                           (d["t"],chat,d["e"],text))
            conn.commit()
            bot.send_message(chat,"Guardado")
            cancelar(chat)

        # ===== EXPORTAR =====
        elif text == "📤 Exportar":
            if not es_pastor(chat):
                return bot.send_message(chat,"Solo Pastor")

            for tabla in ["miembros","ayudas","medicamentos"]:
                cursor.execute(f"SELECT * FROM {tabla}")
                data = cursor.fetchall()

                with open(f"{tabla}.csv","w",newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(data)

                bot.send_document(chat,open(f"{tabla}.csv","rb"))

        # ===== VER TODO =====
        elif text == "📊 Ver Todo":
            cursor.execute("SELECT nombre FROM miembros WHERE aprobado=1")
            msg = "\n".join([x[0] for x in cursor.fetchall()])
            bot.send_message(chat,msg or "Sin datos")

    except Exception as e:
        bot.send_message(chat,f"Error: {e}")
        cancelar(chat)

print("ACTIVO")
bot.remove_webhook()
time.sleep(2)
bot.infinity_polling()
