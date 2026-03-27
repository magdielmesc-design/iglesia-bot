import telebot
from telebot.types import ReplyKeyboardMarkup
import json
import time

TOKEN = "8611160489:AAE0NOReS4OpFr1gQTDcrHJJLaNRd1ZADa0"  # Reemplaza con tu token
bot = telebot.TeleBot(TOKEN)

FILES = {
    "miembros": "miembros.json",
    "asistencia": "asistencia.json",
    "casas": "casas.json",
    "donaciones": "donaciones.json"
}

estado = {}

def cargar(nombre):
    try:
        with open(FILES[nombre], "r") as f:
            return json.load(f)
    except:
        return []

def guardar(nombre, data):
    with open(FILES[nombre], "w") as f:
        json.dump(data, f)

def menu_principal():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("➕ Miembro", "🔍 Buscar")
    m.add("✏️ Editar", "❌ Eliminar")
    m.add("📝 Asistencia", "💰 Donaciones")
    m.add("🏠 Casas de Paz", "📖 Evangelismo")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    estado[m.chat.id] = None
    bot.send_message(m.chat.id, "Sistema Iglesia Monte de Dios", reply_markup=menu_principal())

@bot.message_handler(func=lambda m: True)
def manejar(m):
    chat = m.chat.id
    text = m.text
    user_state = estado.get(chat)

    if text == "➕ Miembro":
        estado[chat] = "agregar"
        bot.send_message(chat, "Escribe el nombre del miembro a agregar")
    elif text == "🔍 Buscar":
        estado[chat] = "buscar"
        bot.send_message(chat, "Escribe el nombre a buscar")
    elif text == "✏️ Editar":
        estado[chat] = "editar_inicial"
        bot.send_message(chat, "Escribe el nombre del miembro a editar")
    elif text == "❌ Eliminar":
        estado[chat] = "eliminar"
        bot.send_message(chat, "Escribe el nombre del miembro a eliminar")
    elif text == "📝 Asistencia":
        estado[chat] = "asistencia"
        bot.send_message(chat, "Escribe el nombre del miembro para registrar asistencia")
    elif text == "💰 Donaciones":
        estado[chat] = "donacion"
        bot.send_message(chat, "Escribe el nombre del miembro y monto separados por coma: Nombre,Monto")
    elif text == "🏠 Casas de Paz":
        estado[chat] = "casas"
        bot.send_message(chat, "Escribe el nombre de la Casa de Paz a agregar o 'listar' para ver todas")
    elif text == "📖 Evangelismo":
        bot.send_message(chat, "Funcionalidad de Evangelismo/Discipulado (pendiente implementar)")
    else:
        try:
            if user_state == "agregar":
                miembros = cargar("miembros")
                miembros.append({"nombre": text})
                guardar("miembros", miembros)
                bot.send_message(chat, f"Miembro '{text}' agregado ✅", reply_markup=menu_principal())
                estado[chat] = None

            elif user_state == "buscar":
                miembros = cargar("miembros")
                res = [m["nombre"] for m in miembros if text.lower() in m["nombre"].lower()]
                bot.send_message(chat, "\n".join(res) if res else "No se encontraron coincidencias ❌", reply_markup=menu_principal())
                estado[chat] = None

            elif user_state == "editar_inicial":
                miembros = cargar("miembros")
                encontrados = [m for m in miembros if text.lower() in m["nombre"].lower()]
                if encontrados:
                    estado[chat] = {"editar": encontrados[0]["nombre"]}
                    bot.send_message(chat, f"Escribe el nuevo nombre para '{encontrados[0]['nombre']}'")
                else:
                    bot.send_message(chat, "Miembro no encontrado ❌", reply_markup=menu_principal())
                    estado[chat] = None

            elif isinstance(user_state, dict) and user_state.get("editar"):
                miembros = cargar("miembros")
                for m in miembros:
                    if m["nombre"] == user_state["editar"]:
                        m["nombre"] = text
                guardar("miembros", miembros)
                bot.send_message(chat, f"Miembro actualizado a '{text}' ✅", reply_markup=menu_principal())
                estado[chat] = None

            elif user_state == "eliminar":
                miembros = cargar("miembros")
                miembros = [m for m in miembros if text.lower() not in m["nombre"].lower()]
                guardar("miembros", miembros)
                bot.send_message(chat, f"Miembro '{text}' eliminado ✅", reply_markup=menu_principal())
                estado[chat] = None

            elif user_state == "asistencia":
                asistencia = cargar("asistencia")
                asistencia.append({"nombre": text})
                guardar("asistencia", asistencia)
                bot.send_message(chat, f"Asistencia de '{text}' registrada ✅", reply_markup=menu_principal())
                estado[chat] = None

            elif user_state == "donacion":
                nombre, monto = text.split(",")
                donaciones = cargar("donaciones")
                donaciones.append({"nombre": nombre.strip(), "monto": float(monto.strip())})
                guardar("donaciones", donaciones)
                bot.send_message(chat, f"Donación de {monto} de '{nombre}' registrada ✅", reply_markup=menu_principal())
                estado[chat] = None

            elif user_state == "casas":
                casas = cargar("casas")
                if text.lower() == "listar":
                    bot.send_message(chat, "\n".join([c["nombre"] for c in casas]) if casas else "No hay Casas de Paz registradas", reply_markup=menu_principal())
                else:
                    casas.append({"nombre": text})
                    guardar("casas", casas)
                    bot.send_message(chat, f"Casa de Paz '{text}' agregada ✅", reply_markup=menu_principal())
                estado[chat] = None
        except Exception as e:
            bot.send_message(chat, f"Error procesando la acción: {e}")
            estado[chat] = None

# Loop para reinicio automático en caso de errores de conexión
while True:
    try:
        bot.polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Error de conexión, reiniciando bot: {e}")
        time.sleep(5)