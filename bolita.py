import json
import re
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import filters
from datetime import datetime, time
import pytz
import asyncio
from telegram.helpers import mention_html
from necesario import hacer_copia_seguridad, marca_tiempo, comando_basura_user, restaurar_usuario_desde_basura, lock_data, ejecutar_consulta_segura, obtener_registro, actualizar_registro	

DB_FILE = "user_data.db"
CANAL_TICKET = "-1002309255787"
# Constantes
GROUP_CHAT_ID = "-1002128871685"  # Reemplaza con el ID de tu grupo
GROUP_CHAT_ADMIN = "-1002128871685" 

#borrar
async def load_loteria(data):
    async with aiofiles.open(file_path, mode='r') as f:
        contents = await f.read()
        return json.loads(contents)
        
#xxxxxxxxxxbasedatos
# Función para guardar jugada en la base de datos
def guardar_jugada_loteria(user_id, nombre_usuario, loteria, jugada, total):
    """Guarda una jugada de lotería en la base de datos"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO loterias (user_id, nombre_usuario, loteria, jugada, total)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, nombre_usuario, loteria, jugada, total))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error al guardar jugada de lotería: {e}")
        return False

# Función para obtener jugadas de un usuario
def obtener_jugadas_usuario(user_id, loteria=None):
    """Obtiene las jugadas de un usuario, opcionalmente filtradas por lotería"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        if loteria:
            c.execute("""
                SELECT loteria, jugada, total, fecha 
                FROM loterias 
                WHERE user_id = ? AND loteria = ?
                ORDER BY fecha DESC
            """, (user_id, loteria))
        else:
            c.execute("""
                SELECT loteria, jugada, total, fecha 
                FROM loterias 
                WHERE user_id = ? 
                ORDER BY fecha DESC
            """, (user_id,))
        
        resultados = c.fetchall()
        conn.close()
        
        return resultados
        
    except Exception as e:
        print(f"Error al obtener jugadas de usuario: {e}")
        return []

# Función para obtener resumen de loterías
def obtener_resumen_loterias():
    """Obtiene un resumen de todas las loterías"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Resumen por lotería
        c.execute("""
            SELECT loteria, SUM(total) as total_loteria, COUNT(*) as cantidad_jugadas
            FROM loterias 
            GROUP BY loteria
            ORDER BY total_loteria DESC
        """)
        
        resumen_loterias = c.fetchall()
        
        # Total general
        c.execute("SELECT SUM(total) FROM loterias")
        total_general = c.fetchone()[0] or 0
        
        conn.close()
        
        return resumen_loterias, total_general
        
    except Exception as e:
        print(f"Error al obtener resumen de loterías: {e}")
        return [], 0

# Función para limpiar todas las jugadas
def limpiar_jugadas_loterias():
    """Elimina todas las jugadas de lotería"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("DELETE FROM loterias")
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error al limpiar jugadas de lotería: {e}")
        return False
  
      
# Función para verificar si la hora actual está dentro de un rango
def time_in_range(start, end, current):
    if start <= current <= end:
        return True
    if start > end and (current >= start or current <= end):
        return True
    return False

# Función para mostrar el menú de loterías
async def bolita(update, context):
    try:
        user_id = str(update.callback_query.from_user.id) if update.callback_query else str(update.message.from_user.id)
        cuba_tz = pytz.timezone("America/Havana")
        current_time = datetime.now(cuba_tz).time()

        keyboard = []

        # Florida
        if time(8, 30) <= current_time <= time(13, 15):
            keyboard.append([InlineKeyboardButton("🇺🇸 Florida🌞 [1:35 PM]", callback_data="🇺🇸 Florida🌞 [1:35 PM]")])
        elif time(14, 0) <= current_time <= time(21, 20):
            keyboard.append([InlineKeyboardButton("🇺🇸 Florida🌙 [9:50 PM]", callback_data="🇺🇸 Florida🌙 [9:50 PM]")])
        elif time(22, 0) <= current_time or current_time <= time(5, 45):
            keyboard.append([InlineKeyboardButton("🇺🇸 Florida🌚 [6:00 AM]", callback_data="🇺🇸 Florida🌚 [6:00 AM]")])
        else:
            keyboard.append([InlineKeyboardButton("🔐 Florida (cerrado)", callback_data="🔐 Florida (cerrado)")])

        # Georgia
        if time(8, 30) <= current_time <= time(12, 15):
            keyboard.append([InlineKeyboardButton("🍑 Georgia🌞 [12:30 PM]", callback_data="🍑 Georgia🌞 [12:30 PM]")])
        elif time(14, 0) <= current_time <= time(18, 45):
            keyboard.append([InlineKeyboardButton("🍑 Georgia⛅ [7:00 PM]", callback_data="🍑 Georgia⛅ [7:00 PM]")])
        elif time(19, 30) <= current_time <= time(23, 20):
            keyboard.append([InlineKeyboardButton("🍑 Georgia🌛 [11:35 PM]", callback_data="🍑 Georgia🌛 [11:35 PM]")])
        else:
            keyboard.append([InlineKeyboardButton("🔐 Georgia (cerrado)", callback_data="🔐 Georgia (cerrado)")])

        # New York
        if time(11, 0) <= current_time <= time(14, 15):
            keyboard.append([InlineKeyboardButton("🗽 New_York🌞 [2:30 PM]", callback_data="🗽 New_York🌞 [2:30 PM]")])
        elif time(17, 30) <= current_time <= time(22, 15):
            keyboard.append([InlineKeyboardButton("🗽 New_York🌛 [10:30 PM]", callback_data="🗽 New_York🌛 [10:30 PM]")])
        else:
            keyboard.append([InlineKeyboardButton("🔐 New_York (cerrado)", callback_data="🔐 New_York (cerrado)")])

        # Haití
        if time(11, 0) <= current_time <= time(11, 45):
            keyboard.append([InlineKeyboardButton("🇭🇹 Haití🌞 [12:00 PM]", callback_data="🇭🇹 Haití🌞 [12:00 PM]")])
        elif time(20, 0) <= current_time <= time(20, 45):
            keyboard.append([InlineKeyboardButton("🇭🇹 Haití🌛 [9:00 PM]", callback_data="🇭🇹 Haití🌛 [9:00 PM]")])
        else:
            keyboard.append([InlineKeyboardButton("🔐 Haití (cerrado)", callback_data="🔐 Haití (cerrado)")])

        # Miami
        if time(21, 0) <= current_time <= time(21, 45):
            keyboard.append([InlineKeyboardButton("🏙️ Miami🌛 [10:00 PM]", callback_data="🏙️ Miami🌛 [10:00 PM]")])
        else:
            keyboard.append([InlineKeyboardButton("🔐 Miami (cerrado)", callback_data="🔐 Miami (cerrado)")])

        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text("Elige una lotería para jugar:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Elige una lotería para jugar:", reply_markup=reply_markup)

    except Exception as e:
        print(f"Error en bolita: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text("Ocurrió un error. Intenta de nuevo.")
        else:
            await update.message.reply_text("Ocurrió un error. Intenta de nuevo.")

# Función para seleccionar una lotería
async def seleccionar_loteria(update, context):
    try:
        user_id = str(update.callback_query.from_user.id)
        selected_lottery = update.callback_query.data
        current_time = datetime.now(pytz.timezone("America/Havana")).time()

        lottery_times = {
            "🇺🇸 Florida🌞 [1:35 PM]": (time(8, 30), time(13, 35)),
            "🇺🇸 Florida🌙 [9:50 PM]": (time(14, 0), time(21, 50)),
            "🇺🇸 Florida🌚 [6:00 AM]": (time(22, 0), time(6, 0)),
            "🍑 Georgia🌞 [12:30 PM]": (time(8, 30), time(12, 30)),
            "🍑 Georgia⛅ [7:00 PM]": (time(14, 0), time(19, 0)),
            "🍑 Georgia🌛 [11:35 PM]": (time(20, 0), time(23, 35)),
            "🗽 New_York🌞 [2:30 PM]": (time(11, 0), time(14, 30)),
            "🗽 New_York🌛 [10:30 PM]": (time(17, 30), time(22, 30)),
            "🇭🇹 Haití🌞 [12:00 PM]": (time(8, 0), time(12, 0)),
            "🇭🇹 Haití🌛 [9:00 PM]": (time(19, 0), time(21, 0)),
            "🏙️ Miami🌛 [10:00 PM]": (time(20, 30), time(22, 0)),
        }

        if selected_lottery in lottery_times:
            start_time, end_time = lottery_times[selected_lottery]
            if time_in_range(start_time, end_time, current_time):
                context.user_data['estado'] = 'esperando_jugada'
                context.user_data['loteria'] = selected_lottery

                await update.callback_query.answer()
                cancel_button = InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")
                keyboard = InlineKeyboardMarkup([[cancel_button]])

                await update.callback_query.message.reply_text(
                    f"<b>Loteria seleccionada:</b> {selected_lottery}.\n\n"
                    f"Por favor, envíame tu jugada.\n\n"
                    f"⚠️ Debe incluir Total: (total de su jugada) en el mismo mensaje.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text("🔐 La lotería seleccionada está cerrada en este momento.")
        else:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("🔐 La lotería seleccionada está cerrada en este momento.")

    except Exception as e:
        print(f"Error en seleccionar_loteria: {e}")
        await update.callback_query.message.reply_text("Ocurrió un error. Intenta de nuevo.")


# Función para recibir la jugada del usuario
async def recibir_jugada(update, context):
    try:
        if context.user_data is None:
            return
        if context.user_data.get('estado') != 'esperando_jugada':
            return

        loteria_seleccionada = context.user_data.get('loteria')
        if not loteria_seleccionada:
            await update.message.reply_text("🚫 No se ha seleccionado una lotería válida.")
            return

        mensaje = update.message.text.strip()
        match = re.search(r"Total:\s*(\d+)", mensaje)

        if match:
            total = int(match.group(1))
            jugada = mensaje.replace(f"Total: {total}", "").strip()

            context.user_data['total'] = total
            context.user_data['jugada'] = jugada
            context.user_data['estado'] = 'esperando_monto'

            botones = [
                [InlineKeyboardButton("✅ Confirmar", callback_data="procesar_jugada")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="bolita")]
            ]
            teclado = InlineKeyboardMarkup(botones)

            fecha_hora_actual = datetime.now().strftime("%d de %B de %Y, %I:%M %p")

            await update.message.reply_text(
                f"<blockquote>🎰 {loteria_seleccionada.title()}</blockquote>\n\n"
                f"🎯 <b>Jugada:</b>\n {jugada}\n"
                f"📅 <b>Fecha:</b> <code>{fecha_hora_actual}</code>\n\n"
                f"💰 <b>Total:</b> <code>{total}</code> CUP\n\n"
                "🌟 <i>Buena suerte!</i>",
                reply_markup=teclado,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ No se encontró un monto total en el mensaje. Asegúrate de incluir 'Total: <monto>'.")

    except Exception as e:
        print(f"Error en recibir_jugada: {e}")
        await update.message.reply_text("⚠️ Ocurrió un error al procesar la jugada. Intenta de nuevo.")

# Función para procesar la jugada

async def procesar_jugada(update, context):
    try:
        user_id = str(update.callback_query.from_user.id)
        total = context.user_data.get('total')
        jugada = context.user_data.get('jugada')
        loteria = context.user_data.get('loteria')

        if not total or not jugada or not loteria:
            await update.callback_query.message.reply_text("❌ Datos incompletos. Intenta de nuevo.")
            return

        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Nombre, Balance")
        
        if not usuario_data:
            await update.callback_query.message.reply_text("❌ No estás registrado. Usa /start para registrarte.")
            return

        nombre_usuario, balance_usuario = usuario_data

        if balance_usuario >= total:
            # Actualizar balance del usuario
            exito_balance = actualizar_registro("usuarios", user_id, {
                "Balance": balance_usuario - total
            })
            
            if exito_balance:
                # Guardar jugada en la base de datos
                exito_jugada = guardar_jugada_loteria(user_id, nombre_usuario, loteria, jugada, total)
                
                if exito_jugada:
                    balance_restante = balance_usuario - total
                    
                    keyboard = [[InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_principal")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await update.callback_query.message.reply_text(
                        f"✅ <b>Tu jugada fue procesada correctamente.</b>\n\n"
                        f"🎰 <b>Lotería:</b> {loteria}\n"
                        f"🎯 <b>Jugada:</b>\n {jugada}\n"
                        f"💰 <b>Total descontado:</b> {total} CUP\n"
                        f"💳 <b>Balance restante:</b> {balance_restante} CUP",
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                    mensaje_grupo = (
                        f"<blockquote>{loteria}</blockquote> \n"
                        f"<b>👤 Usuario</b>: {mention_html(user_id, nombre_usuario)}\n"                    
                        f"🎯 <b>Jugada:</b>\n {jugada}\n"
                        f"💰 <b>Total:</b> <code>{total}</code> CUP"
                    )

                    await context.bot.send_message(
                        chat_id=CANAL_TICKET,
                        text=mensaje_grupo,
                        parse_mode="HTML"
                    )
                else:
                    await update.callback_query.message.reply_text("❌ Error al guardar la jugada.")
            else:
                await update.callback_query.message.reply_text("❌ Error al actualizar el balance.")
        else:
            keyboard = [[InlineKeyboardButton("📥 Depositar", callback_data="depositar")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.message.reply_text(
                f"❌ <b>Balance insuficiente</b>, recarga tu cuenta antes de jugar.\n\n"
                f"🏧<b>Balance disponible:</b> {balance_usuario} CUP",
                parse_mode="HTML",
                reply_markup=reply_markup
            )

    except Exception as e:
        print(f"Error al procesar la jugada: {e}")
        await update.callback_query.message.reply_text("⚠️ Ocurrió un error al procesar tu jugada. Intenta de nuevo.")

# Función para generar un resumen de las loterías
async def resumen_loterias(update, context):
    try:
        resumen_loterias, total_general = obtener_resumen_loterias()
        
        mensaje = "*🏆 Resumen de Loterías*\n\n"
        
        for loteria, total_loteria, cantidad_jugadas in resumen_loterias:
            if "Florida" in loteria:
                emoji = "🌞"
            elif "Georgia" in loteria:
                emoji = "🍑"
            elif "New_York" in loteria:
                emoji = "🗽"
            else:
                emoji = "🌟"

            mensaje += f"{emoji} *{loteria}:* {total_loteria} CUP ({cantidad_jugadas} jugadas)\n"

        mensaje += f"\n*💰 Total en todas las loterías: {total_general} CUP*"
        await update.message.reply_text(mensaje, parse_mode="Markdown")

    except Exception as e:
        print(f"Error al generar el resumen de las loterías: {e}")
        await update.message.reply_text("❌ Ocurrió un error al generar el resumen de las loterías.")

# Función para refrescar loterías (MODIFICADA)
async def refrescar_loterias(update, context):
    try:
        # Obtener resumen antes de limpiar para enviar como backup
        resumen_loterias, total_general = obtener_resumen_loterias()
        
        # Crear mensaje de backup
        mensaje_backup = "📊 *Resumen de jugadas antes de limpiar:*\n\n"
        for loteria, total_loteria, cantidad_jugadas in resumen_loterias:
            mensaje_backup += f"• {loteria}: {total_loteria} CUP ({cantidad_jugadas} jugadas)\n"
        mensaje_backup += f"\n*Total general: {total_general} CUP*"
        
        # Enviar backup al grupo de admin
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=mensaje_backup,
            parse_mode="Markdown"
        )
        
        # Limpiar jugadas
        exito = limpiar_jugadas_loterias()
        
        if exito:
            await update.message.reply_text("✅ *Se han borrado todas las jugadas de las loterías.*", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error al borrar las jugadas.")

    except Exception as e:
        print(f"Error al refrescar las loterías: {e}")
        await update.message.reply_text("❌ Ocurrió un error al intentar borrar las jugadas.")

# Función para refrescar las loterías
async def refrescar_loterias(update, context):
    try:
        # Obtener resumen antes de limpiar para enviar como backup
        resumen_loterias, total_general = obtener_resumen_loterias()
        
        # Crear mensaje de backup
        mensaje_backup = "📊 *Resumen de jugadas antes de limpiar:*\n\n"
        for loteria, total_loteria, cantidad_jugadas in resumen_loterias:
            mensaje_backup += f"• {loteria}: {total_loteria} CUP ({cantidad_jugadas} jugadas)\n"
        mensaje_backup += f"\n*Total general: {total_general} CUP*"
        
        # Enviar backup al grupo de admin
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=mensaje_backup,
            parse_mode="Markdown"
        )
        
        # Limpiar jugadas
        exito = limpiar_jugadas_loterias()
        
        if exito:
            await update.message.reply_text("✅ *Se han borrado todas las jugadas de las loterías.*", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error al borrar las jugadas.")

    except Exception as e:
        print(f"Error al refrescar las loterías: {e}")
        await update.message.reply_text("❌ Ocurrió un error al intentar borrar las jugadas.")
    

