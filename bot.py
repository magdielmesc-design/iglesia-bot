import telebot
from telebot.types import ReplyKeyboardMarkup
import sqlite3
import os
import time

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# ===== DB =====
conn = sqlite3.connect("iglesia.db", check_same_thread=False)
cursor = conn.cursor()

# TABLAS
cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT, rol TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS miembros (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT, direccion TEXT, aprobado INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS oraciones (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, motivo TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, stock INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS ayudas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, cantidad INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, direccion TEXT, lectura TEXT, ofrenda TEXT, alabanza TEXT, coro TEXT)")
conn.commit()

estado = {}

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
    m.add("👥 Miembros", "🙏 Oración")
    m.add("💊 Medicamentos", "📦 Ayudas")
    m.add("⛪ Servicios", "📊 Ver Todo")
    return m

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    bot.send_message(m.chat.id, "Sistema Iglesia", reply_markup=menu())

# ===== ROL =====
@bot.message_handler(commands=['rol'])
def rol(m):
    try:
        nombre, rol = m.text.split(" ",2)[1:]
        cursor.execute("INSERT OR REPLACE INTO usuarios VALUES (?,?,?)",
                       (m.chat.id, nombre, rol))
        conn.commit()
        bot.reply_to(m, f"Rol: {rol}")
    except:
        bot.reply_to(m, "Uso: /rol Nombre Pastor|Lider|Miembro")

# ===== BOT =====
@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text
    st = estado.get(chat)
    rol = get_rol(chat)

    try:

        # ===== MIEMBROS =====
        if text == "👥 Miembros":
            estado[chat] = "miembro"
            bot.send_message(chat, "Nombre,Teléfono,Dirección")

        elif st == "miembro":
            if "," not in text:
                bot.send_message(chat, "Formato incorrecto")
                return

            n,t,d = text.split(",",2)

            aprobado = 1 if es_pastor(chat) else 0

            cursor.execute("INSERT INTO miembros (nombre,telefono,direccion,aprobado) VALUES (?,?,?,?)",
                           (n,t,d,aprobado))
            conn.commit()

            if aprobado:
                bot.send_message(chat, "Miembro guardado ✅")
            else:
                bot.send_message(chat, "Pendiente aprobación ⏳")

            estado[chat] = None

        # ===== ORACION =====
        elif text == "🙏 Oración":
            estado[chat] = "oracion"
            bot.send_message(chat, "Escribe motivo")

        elif st == "oracion":
            cursor.execute("INSERT INTO oraciones (user_id,motivo) VALUES (?,?)",(chat,text))
            conn.commit()
            bot.send_message(chat, "Guardado 🙏", reply_markup=menu())
            estado[chat] = None

        # ===== MEDICAMENTOS =====
        elif text == "💊 Medicamentos":
            estado[chat] = "med"
            bot.send_message(chat, "Nombre,Stock")

        elif st == "med":
            n,s = text.split(",",1)
            cursor.execute("INSERT INTO medicamentos (nombre,stock) VALUES (?,?)",(n,s))
            conn.commit()
            bot.send_message(chat, "Guardado 💊", reply_markup=menu())
            estado[chat] = None

        elif text == "📦 Stock Medicamentos":
            cursor.execute("SELECT nombre,stock FROM medicamentos")
            data = cursor.fetchall()
            msg = "\n".join([f"{n}: {s}" for n,s in data])
            bot.send_message(chat, msg or "Sin stock")

        # ===== AYUDAS =====
        elif text == "📦 Ayudas":
            if not es_pastor(chat):
                bot.send_message(chat, "Solo Pastor")
                return

            estado[chat] = "ayuda"
            bot.send_message(chat, "Nombre,Cantidad")

        elif st == "ayuda":
            n,c = text.split(",",1)
            cursor.execute("INSERT INTO ayudas (nombre,cantidad) VALUES (?,?)",(n,c))
            conn.commit()
            bot.send_message(chat, "Ayuda registrada 📦", reply_markup=menu())
            estado[chat] = None

        elif text == "📦 Stock Ayudas":
            cursor.execute("SELECT nombre,cantidad FROM ayudas")
            data = cursor.fetchall()
            msg = "\n".join([f"{n}: {c}" for n,c in data])
            bot.send_message(chat, msg or "Sin stock")

        # ===== SERVICIOS =====
        elif text == "⛪ Servicios":
            estado[chat] = "servicio"
            bot.send_message(chat, "Fecha,Direccion,Lectura,Ofrenda,Alabanza,Coro")

        elif st == "servicio":
            f,d,l,o,a,c = text.split(",",5)
            cursor.execute("INSERT INTO servicios (fecha,direccion,lectura,ofrenda,alabanza,coro) VALUES (?,?,?,?,?,?)",
                           (f,d,l,o,a,c))
            conn.commit()
            bot.send_message(chat, "Servicio guardado ⛪", reply_markup=menu())
            estado[chat] = None

        # ===== VER TODO =====
        elif text == "📊 Ver Todo":
            msg = ""

            cursor.execute("SELECT nombre FROM miembros WHERE aprobado=1")
            msg += "👥 Miembros:\n" + "\n".join([x[0] for x in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT motivo FROM oraciones")
            msg += "🙏 Oración:\n" + "\n".join([x[0] for x in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT nombre,stock FROM medicamentos")
            msg += "💊 Medicamentos:\n" + "\n".join([f"{n}:{s}" for n,s in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT nombre,cantidad FROM ayudas")
            msg += "📦 Ayudas:\n" + "\n".join([f"{n}:{c}" for n,c in cursor.fetchall()]) + "\n\n"

            cursor.execute("SELECT fecha,alabanza,coro FROM servicios")
            msg += "⛪ Servicios:\n" + "\n".join([f"{f} - {a} ({c})" for f,a,c in cursor.fetchall()])

            bot.send_message(chat, msg or "Sin datos")

    except Exception as e:
        bot.send_message(chat, f"Error: {e}")
        estado[chat] = None

# ===== INICIO =====
print("SISTEMA ACTIVO")

bot.remove_webhook()
time.sleep(2)
bot.infinity_polling()
