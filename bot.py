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
    nombre TEXT UNIQUE,
    telefono TEXT,
    direccion TEXT,
    ministerio TEXT
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

CREATE TABLE IF NOT EXISTS medicamentos (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    stock INTEGER
);

CREATE TABLE IF NOT EXISTS oraciones (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER,
    motivo TEXT,
    fecha TEXT
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
    dia TEXT,
    discipuladores TEXT,
    discipulos TEXT
);

CREATE TABLE IF NOT EXISTS servicios (
    id INTEGER PRIMARY KEY,
    fecha TEXT,
    predicador TEXT,
    tema TEXT,
    coro TEXT,
    lectura TEXT,
    ofrendas TEXT,
    mensaje TEXT
);

CREATE TABLE IF NOT EXISTS crecimiento (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER,
    idea TEXT,
    fecha TEXT
);

CREATE TABLE IF NOT EXISTS estados (
    chat_id TEXT PRIMARY KEY,
    estado TEXT,
    data TEXT
);
""")
conn.commit()

# ===== UTIL =====
def user(chat):
    cursor.execute("SELECT * FROM usuarios WHERE chat_id=?", (chat,))
    return cursor.fetchone()

def es_admin(chat):
    u = user(chat)
    return u and u[3] in ["Pastor","Líder"]

def es_pastor(chat):
    u = user(chat)
    return u and u[3]=="Pastor"

def set_estado(chat, estado, data=""):
    cursor.execute("REPLACE INTO estados VALUES (?,?,?)", (chat, estado, data))
    conn.commit()

def get_estado(chat):
    cursor.execute("SELECT estado,data FROM estados WHERE chat_id=?", (chat,))
    r = cursor.fetchone()
    return r if r else (None,None)

def clear_estado(chat):
    cursor.execute("DELETE FROM estados WHERE chat_id=?", (chat,))
    conn.commit()

def es_numero(x):
    try:
        return int(x)
    except:
        return None

def validar_fecha(f):
    try:
        datetime.strptime(f, "%Y-%m-%d")
        return True
    except:
        return False

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
    m.add("👥 Miembros","📦 Ayudas")
    m.add("💊 Medicamentos","🙏 Oración")
    m.add("🏠 Casas","⛪ Servicios")
    m.add("📅 Agenda","📊 Reportes")
    m.add("💡 Crecimiento")
    if rol=="Pastor":
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
    rol = "Pastor" if cursor.fetchone()[0]==0 else "Miembro"

    cursor.execute("INSERT OR IGNORE INTO usuarios VALUES (NULL,?,?,?,0)", (chat,nombre,rol))
    conn.commit()

    u = user(chat)
    if u[3]=="Pastor":
        cursor.execute("UPDATE usuarios SET aprobado=1 WHERE chat_id=?", (chat,))
        conn.commit()
        u = user(chat)

    if u[4]==0:
        bot.send_message(msg.chat.id,"⏳ Espera aprobación")
        return

    bot.send_message(msg.chat.id,"Sistema listo", reply_markup=menu_principal(u[3]))

# ===== MOTOR DIARIO =====
def motor_diario():
    while True:
        try:
            hoy = datetime.now().strftime("%Y-%m-%d")
            # Agenda
            cursor.execute("SELECT titulo FROM agenda WHERE fecha=?", (hoy,))
            for e in cursor.fetchall():
                notificar_admins(f"📅 Hoy: {e[0]}")

            # Stock bajo ayudas
            cursor.execute("SELECT tipo,SUM(cantidad) FROM ayudas GROUP BY tipo")
            for t,c in cursor.fetchall():
                if c<=5:
                    notificar_admins(f"⚠️ Stock bajo: {t} ({c})")

            # Stock bajo medicamentos
            cursor.execute("SELECT nombre,stock FROM medicamentos")
            for n,s in cursor.fetchall():
                if s<=5:
                    notificar_admins(f"⚠️ Stock bajo de medicamento: {n} ({s})")
        except:
            pass
        time.sleep(86400)  # 1 vez al día

threading.Thread(target=motor_diario, daemon=True).start()

# ===== FLUJO PRINCIPAL =====
@bot.message_handler(func=lambda msg: True)
def flujo(msg):
    chat = str(msg.chat.id)
    estado, data = get_estado(chat)
    t = msg.text
    u = user(chat)

    if t=="⬅️ Volver":
        bot.send_message(msg.chat.id,"Menú",reply_markup=menu_principal(u[3]))
        clear_estado(chat)
        return

    # ===== MIEMBROS =====
    if t=="👥 Miembros":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id,"Nombre del miembro:")
        set_estado(chat,"m")
        return
    if estado=="m":
        cursor.execute("INSERT OR IGNORE INTO miembros (nombre) VALUES (?)",(t,))
        conn.commit()
        bot.send_message(msg.chat.id,"Miembro creado")
        clear_estado(chat)
        return

    # ===== AYUDAS =====
    if t=="📦 Ayudas":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id,"Tipo de ayuda:")
        set_estado(chat,"a_t")
        return
    if estado=="a_t":
        set_estado(chat,"a_c",t)
        bot.send_message(msg.chat.id,"Cantidad:")
        return
    if estado=="a_c":
        c = es_numero(t)
        if c is None:
            bot.send_message(msg.chat.id,"Número inválido")
            return
        cursor.execute("INSERT INTO ayudas VALUES (NULL,?,?)",(data,c))
        conn.commit()
        notificar_admins(f"📦 Nuevo stock {data}+{c}")
        clear_estado(chat)
        bot.send_message(msg.chat.id,"Ayuda registrada")
        return

    # ===== ENTREGA DE AYUDAS =====
    if t=="📤 Entregar":
        if not es_admin(chat): return
        cursor.execute("SELECT nombre FROM miembros")
        lista = "\n".join([x[0] for x in cursor.fetchall()])
        bot.send_message(msg.chat.id,lista)
        set_estado(chat,"e_m")
        return
    if estado=="e_m":
        set_estado(chat,"e_t",t)
        bot.send_message(msg.chat.id,"Tipo de ayuda:")
        return
    if estado=="e_t":
        set_estado(chat,"e_c",data+"|"+t)
        bot.send_message(msg.chat.id,"Cantidad:")
        return
    if estado=="e_c":
        miembro,tipo = data.split("|")
        c = es_numero(t)
        if c is None:
            bot.send_message(msg.chat.id,"Número inválido")
            return
        cursor.execute("SELECT SUM(cantidad) FROM ayudas WHERE tipo=?",(tipo,))
        stock = cursor.fetchone()[0] or 0
        if c>stock:
            bot.send_message(msg.chat.id,"Stock insuficiente")
            return
        cursor.execute("UPDATE ayudas SET cantidad=cantidad-? WHERE tipo=?",(c,tipo))
        cursor.execute("INSERT INTO ayudas_asignadas VALUES (NULL,?,?,?,?)",
                       (miembro,tipo,c,datetime.now()))
        conn.commit()
        notificar_admins(f"📤 {miembro} recibió {c} de {tipo}")
        clear_estado(chat)
        bot.send_message(msg.chat.id,"Entrega OK")
        return

    # ===== MEDICAMENTOS =====
    if t=="💊 Medicamentos":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id,"Nombre del medicamento:")
        set_estado(chat,"med_n")
        return
    if estado=="med_n":
        set_estado(chat,"med_s",t)
        bot.send_message(msg.chat.id,"Stock inicial:")
        return
    if estado=="med_s":
        s = es_numero(t)
        if s is None:
            bot.send_message(msg.chat.id,"Número inválido")
            return
        cursor.execute("INSERT INTO medicamentos VALUES (NULL,?,?)",(data,s))
        conn.commit()
        notificar_admins(f"💊 Nuevo medicamento {data} stock {s}")
        clear_estado(chat)
        bot.send_message(msg.chat.id,"Medicamento registrado")
        return

    # ===== ORACIÓN =====
    if t=="🙏 Oración":
        bot.send_message(msg.chat.id,"Motivo:")
        set_estado(chat,"or")
        return
    if estado=="or":
        cursor.execute("INSERT INTO oraciones VALUES (NULL,?,?,?)",(u[0],t,datetime.now()))
        conn.commit()
        bot.send_message(msg.chat.id,"Oración registrada")
        clear_estado(chat)
        return

    # ===== AGENDA =====
    if t=="📅 Agenda":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id,"Título:")
        set_estado(chat,"ag_t")
        return
    if estado=="ag_t":
        set_estado(chat,"ag_f",t)
        bot.send_message(msg.chat.id,"Fecha YYYY-MM-DD:")
        return
    if estado=="ag_f":
        if not validar_fecha(t):
            bot.send_message(msg.chat.id,"Formato incorrecto")
            return
        cursor.execute("INSERT INTO agenda VALUES (NULL,?,?)",(data,t))
        conn.commit()
        bot.send_message(msg.chat.id,"Evento creado")
        clear_estado(chat)
        return

    # ===== CASAS DE PAZ =====
    if t=="🏠 Casas":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id,"Anfitrión:")
        set_estado(chat,"c_a")
        return
    if estado=="c_a":
        set_estado(chat,"c_d",t)
        bot.send_message(msg.chat.id,"Dirección:")
        return
    if estado=="c_d":
        set_estado(chat,"c_di",data+"|"+t)
        bot.send_message(msg.chat.id,"Día de la semana:")
        return
    if estado=="c_di":
        anfitrion,direccion = data.split("|")
        cursor.execute("INSERT INTO casas VALUES (NULL,?,?,?,NULL,NULL)",(anfitrion,direccion,t))
        conn.commit()
        bot.send_message(msg.chat.id,"Casa registrada")
        clear_estado(chat)
        return

    # ===== SERVICIOS =====
    if t=="⛪ Servicios":
        if not es_admin(chat): return
        bot.send_message(msg.chat.id,"Fecha YYYY-MM-DD:")
        set_estado(chat,"s_f")
        return
    if estado=="s_f":
        if not validar_fecha(t):
            bot.send_message(msg.chat.id,"Formato incorrecto")
            return
        set_estado(chat,"s_p",t)
        bot.send_message(msg.chat.id,"Predicador:")
        return
    if estado=="s_p":
        set_estado(chat,"s_t",data+"|"+t)
        bot.send_message(msg.chat.id,"Tema:")
        return
    if estado=="s_t":
        f,p = data.split("|")
        cursor.execute("INSERT INTO servicios VALUES (NULL,?,?,?,?,?,?,?,?)",(f,p,t,"","","","", ""))
        conn.commit()
        bot.send_message(msg.chat.id,"Servicio registrado")
        clear_estado(chat)
        return

    # ===== CRECIMIENTO =====
    if t=="💡 Crecimiento":
        bot.send_message(msg.chat.id,"Idea / sugerencia:")
        set_estado(chat,"idea")
        return
    if estado=="idea":
        cursor.execute("INSERT INTO crecimiento VALUES (NULL,?,?,?)",(u[0],t,datetime.now()))
        conn.commit()
        bot.send_message(msg.chat.id,"Idea registrada")
        clear_estado(chat)
        return

    # ===== REPORTES =====
    if t=="📊 Reportes":
        cursor.execute("SELECT SUM(cantidad) FROM ayudas_asignadas")
        total = cursor.fetchone()[0] or 0
        bot.send_message(msg.chat.id,f"Total entregado: {total}")
        return

print("BOT FINAL COMPLETO ACTIVO")
bot.infinity_polling()
