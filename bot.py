import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ================= BASE DE DATOS =================
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# Usuarios
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    nombre TEXT,
    rol TEXT
)
""")

# Miembros
cursor.execute("""
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    telegram_id INTEGER,
    casa_id INTEGER
)
""")

# Casas
cursor.execute("""
CREATE TABLE IF NOT EXISTS casas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    dia TEXT,
    hora TEXT,
    direccion TEXT,
    anfitrion TEXT,
    discipulador1 TEXT,
    discipulador2 TEXT
)
""")

# Donaciones
cursor.execute("""
CREATE TABLE IF NOT EXISTS donaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    cantidad REAL,
    unidad TEXT,
    restante REAL,
    descripcion TEXT,
    fecha TEXT
)
""")

# Entregas
cursor.execute("""
CREATE TABLE IF NOT EXISTS entregas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donacion_id INTEGER,
    miembro_id INTEGER,
    cantidad REAL,
    fecha TEXT
)
""")

# Oración
cursor.execute("""
CREATE TABLE IF NOT EXISTS oraciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miembro TEXT,
    motivo TEXT,
    fecha TEXT
)
""")

# Medicamentos
cursor.execute("""
CREATE TABLE IF NOT EXISTS medicamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miembro TEXT,
    nombre TEXT,
    descripcion TEXT,
    fecha TEXT
)
""")

conn.commit()

estado = {}

# ================= ROLES =================
def obtener_rol(chat_id):
    cursor.execute("SELECT rol FROM usuarios WHERE telegram_id=?", (chat_id,))
    res = cursor.fetchone()
    return res[0] if res else "Miembro"

# ================= MENÚ =================
def menu_principal(chat_id):
    rol = obtener_rol(chat_id)
    m = ReplyKeyboardMarkup(resize_keyboard=True)

    m.add("👥 Miembros", "🏠 Casas", "📖 Discipulado")

    if rol in ["Lider", "Pastor"]:
        m.add("🛠 Servicio", "💰 Donaciones")

    if rol == "Pastor":
        m.add("📩 Notificar", "⚙️ Administración")

    m.add("🙏 Oración", "💊 Medicamentos")

    return m

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):
    chat_id = m.chat.id
    nombre = m.from_user.first_name

    cursor.execute("SELECT id FROM usuarios WHERE telegram_id=?", (chat_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (telegram_id, nombre, rol) VALUES (?, ?, ?)",
            (chat_id, nombre, "Miembro")
        )
        conn.commit()

    estado[chat_id] = None
    bot.send_message(chat_id, "Sistema Iglesia Monte de Dios", reply_markup=menu_principal(chat_id))

# ================= BOT =================
@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text
    user_state = estado.get(chat)

    try:

        # ========= MIEMBROS =========
        if text == "👥 Miembros":
            estado[chat] = "miembro"
            bot.send_message(chat, "Agregar: Nombre")

        elif user_state == "miembro":
            cursor.execute("INSERT INTO miembros (nombre) VALUES (?)", (text,))
            conn.commit()
            bot.send_message(chat, "Miembro agregado ✅", reply_markup=menu_principal(chat))
            estado[chat] = None

        # ========= CASAS =========
        elif text == "🏠 Casas":
            estado[chat] = "casa"
            bot.send_message(chat, "Formato: Nombre,Día,Hora,Dirección,Anfitrión,D1,D2")

        elif user_state == "casa":
            n,d,h,dir,a,d1,d2 = text.split(",")
            cursor.execute(
                "INSERT INTO casas (nombre,dia,hora,direccion,anfitrion,discipulador1,discipulador2) VALUES (?,?,?,?,?,?,?)",
                (n,d,h,dir,a,d1,d2)
            )
            conn.commit()
            bot.send_message(chat, "Casa creada ✅", reply_markup=menu_principal(chat))
            estado[chat] = None

        # ========= DONACIONES =========
        elif text == "💰 Donaciones":
            estado[chat] = "donacion"
            bot.send_message(chat, "Formato: Tipo,Cantidad,Unidad,Descripción")

        elif user_state == "donacion":
            tipo,cant,unidad,desc = text.split(",")
            cursor.execute(
                "INSERT INTO donaciones (tipo,cantidad,unidad,restante,descripcion,fecha) VALUES (?,?,?,?,?,DATE('now'))",
                (tipo,float(cant),unidad,float(cant),desc)
            )
            conn.commit()
            bot.send_message(chat, "Donación registrada ✅", reply_markup=menu_principal(chat))
            estado[chat] = None

        # ========= ORACIÓN =========
        elif text == "🙏 Oración":
            estado[chat] = "oracion"
            bot.send_message(chat, "Formato: Nombre,Motivo")

        elif user_state == "oracion":
            nombre,motivo = text.split(",")
            cursor.execute(
                "INSERT INTO oraciones (miembro,motivo,fecha) VALUES (?,?,DATE('now'))",
                (nombre,motivo)
            )
            conn.commit()
            bot.send_message(chat, "Motivo registrado 🙏", reply_markup=menu_principal(chat))
            estado[chat] = None

        # ========= MEDICAMENTOS =========
        elif text == "💊 Medicamentos":
            estado[chat] = "med"
            bot.send_message(chat, "Formato: Nombre,Medicamento,Descripción")

        elif user_state == "med":
            nombre,med,desc = text.split(",")
            cursor.execute(
                "INSERT INTO medicamentos (miembro,nombre,descripcion,fecha) VALUES (?,?,?,DATE('now'))",
                (nombre,med,desc)
            )
            conn.commit()
            bot.send_message(chat, "Solicitud registrada 💊", reply_markup=menu_principal(chat))
            estado[chat] = None

        # ========= NOTIFICAR =========
        elif text == "📩 Notificar":
            estado[chat] = "notificar"
            bot.send_message(chat, "Formato: Nombre,Mensaje")

        elif user_state == "notificar":
            nombre,msg = text.split(",",1)
            cursor.execute("SELECT telegram_id FROM miembros WHERE nombre LIKE ?", ('%'+nombre+'%',))
            res = cursor.fetchone()
            if res and res[0]:
                bot.send_message(res[0], msg)
                bot.send_message(chat, "Enviado ✅")
            else:
                bot.send_message(chat, "No encontrado ❌")
            estado[chat] = None

    except Exception as e:
        bot.send_message(chat, f"Error: {e}")
        estado[chat] = None

print("Bot listo...")
bot.infinity_polling()
print("Bot listo...")

bot.remove_webhook()

bot.infinity_polling(timeout=60, long_polling_timeout=60)
