import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext, ConversationHandler, ContextTypes, JobQueue, ApplicationHandlerStop
from telegram import ChatMember, ReplyKeyboardRemove
import random
import sqlite3
import uuid
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, TypeHandler
from telegram.error import BadRequest
from functools import wraps  
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
import aiofiles
import asyncio
from aiogram import types
import traceback
import threading
import time as tm  
from datetime import datetime, time, timedelta, timezone
import pytz 
import json
import os
import re
import aiohttp
import requests
import shutil


from juegopirata import (
    ver_balance, 
    juego_pirata, 
    comprar_piratas, 
    confirmar_compra_piratas,
    format_time, 
    reclamar_ganancias, 
    vender_barriles, 
    recibir_cantidad_vender, 
    confirmar_vender, 
    comprar_barriles, 
    recibir_cantidad_comprar, 
    confirmar_comprar,
    mejorar_elemento, 
    confirmar_mejora_elemento,
    mostrar_ranking_pvp,
    buscar_combate,
    reparar_barco,
    menu_combate_pvp,
    resolver_combate,
    mercado_pirata,
    confirmar_escudo_basico,
    confirmar_escudo_premium,
    comprar_escudo_handler,
    comprar_escudo,
    confirmar_ataque,
    init_tareas_pirata,
    top_pirata, 
    aplicar_evento_aleatorio,
    mostrar_eventos_activos,
    confirmar_combate
)
from bolita import guardar_jugada_loteria, obtener_jugadas_usuario, bolita, time_in_range, seleccionar_loteria, recibir_jugada,		 procesar_jugada, resumen_loterias, refrescar_loterias



from fantasy import juego_fantasy, mi_equipo_handler, show_market_main_menu, listar_equipos_mercado, listar_jugadores_equipo, confirmar_venta, mostrar_formulario_oferta, procesar_oferta, listar_mis_ventas, mercado_volver, comprar_jugador, ver_jugador, poner_en_venta_handler, procesar_venta_manual, confirmar_venta_jugador, hacer_oferta_handler, manejar_respuesta_oferta, configurar_subasta, iniciar_subasta_handler, mis_ofertas_handler, procesar_puja, pujar_subasta, listar_subastas_activas,crear_subasta, procesar_puja_subasta, mostrar_menu_subastas, mis_pujas_handler, gestionar_subasta, aceptar_puja_handler, cancelar_subasta_handler, mis_subastas_handler, torneo_handler, mostrar_sistema_torneo, unirse_al_torneo, mostrar_participantes, mostrar_clasificacion, mostrar_ultimos_resultados, mostrar_mis_partidos, mostrar_ayuda_torneo, cancelar_torneo_handler, mostrar_info_torneo_detallada, confirmar_cancelar_torneo, mostrar_menu_alineacion, volver_alineacion_handler, reiniciar_alineacion_handler, confirmar_alineacion_handler, toggle_jugador_handler, seleccionar_posicion_handler, seleccionar_formacion_handler, cambiar_formacion_handler, estadisticas_equipo, ver_jugador_stats, procesar_aceptar_reto, procesar_rechazar_reto, cerrar_tutorial, mostrar_tutorial_partidos, mostrar_tutorial_torneos, cerrar_tutorial_torneos, eliminar_usuario_handler, confirmar_eliminar_usuario, cancelar_eliminar, get_fantasy_handler, refresh_fantasy_stats, show_all_users, cancelar_compra, confirmar_compra_handler, mostrar_ranking, reiniciar_ranking, mostrar_rivales_retar, seleccionar_rival, procesar_monto_reto, revisar_inactividad_fantasy, confirmar_venta_jugador, vender_jugador_handler, tarea_actualizacion_diaria, explicar_sistema_puntos, actualizar_jugadores

from necesario import hacer_copia_seguridad, marca_tiempo, comando_basura_user, restaurar_usuario_desde_basura, lock_minijuegos, has_lock, ejecutar_consulta_segura, obtener_registro, actualizar_registro, obtener_apuestas_usuario, eliminar_todas_apuestas_usuario, eliminar_apuesta_de_db, hacer_backup_db, backup_periodico	
	
from bet import (
    realizar_solicitud_deportes, limpiar_cache, obtener_deportes, mostrar_deportes, obtener_ligas, seleccionar_deporte, manejar_paginacion_paises, mostrar_ligas_principales, manejar_seleccion_pais, 
    detectar_pais, obtener_bandera, manejar_navegacion, obtener_eventos_liga, handle_resumen_callback,  mostrar_todos_partidos_live, seleccionar_liga,  seleccionar_liga_futbol,
    mostrar_mercados_evento, obtener_mercados_evento, cargar_mercado_especifico_futbol, refresh_evento, cargar_mercado_otros_deportes, mostrar_opciones_mercado_futbol,  handle_market_selection,  seleccionar_apuesta,
    manejar_monto_apuesta, confirmar_apuesta, manejar_metodo_pago, mis_apuestas,  notificar_usuario, decidir_apuesta_ganada,
    ejecutar_pagar,
    decidir_h2h, decidir_total_anotaciones, decidir_handicap, decidir_btts, decidir_dnb,
    obtener_resultados_eventos, buscar_apuestas_finalizadas,
    resumen_apuestas,
    eliminar_apuesta,
    detalles_partido,
    cancelar_apuesta,
    reembolsar_apuestas,
    pagar_apuestas_ganadoras,
    reembolsar_apuesta,
    ganada_apuesta,
    perdida_apuesta,
    detener_pagos,
    mostrar_tipos_apuestas,
    mostrar_futbol_live,
    mostrar_eventos_live,
    manejar_navegacion_ligas_live,
    mostrar_mercados_en_vivo,
    handle_vivo_callback,
    handle_prepartido_callback,
    handle_combinadas_callback,
    manejar_acciones_combinadas,
    handle_pago_combinada,
    confirmar_combinada_handler,
    manejar_monto_combinada,
    procesar_marcador,
    comando_basura,
    mostrar_apuestas_seleccion,
    TIEMPOS_DURACION,
    MERCADOS_CON_POINT,
    buscar_equipo,
    mostrar_partidos_equipo,
    manejar_busqueda_equipo
)

BOT_USERNAME = "QvaPlay_bot"  



ADMIN_IDS = ["5266566202", "7031172659", "6687647767", "8027657221"]
REQUIRED_CHANNEL_ID = "-1002128871685"
CHANNEL_INVITE_LINK = "https://t.me/CubaPlayCANAL"
GROUP_INVITE_LINK = "https://t.me/QvaPlay"
TOKEN = '7595579942:AAGegIDsfAwU522KXSHy6cO2JWQqItpeX9w'
cambio_mlc = 220  # Valor de cambio de MLC a CUP
cambio_cripto = 400  # Valor de cambio de cripto a CUP

GROUP_CHAT_ID = -1001929466623
GROUP_CHAT_ADMIN = -1002492508397
GROUP_REGISTRO = -1002261941863
DB_FILE = "user_data.db"
REGISTRO_MINIJUEGOS = -1002566004558


usuarios_bloqueados_lock = asyncio.Lock()
MINIJUEGOS_FILE = "minijuegos.json" 
# Variables globales para porcentajes en depósitos automaticos (facil acceso y modificación)
BONO_PORCENTAJE = 0.2  # 20%
ROLLOVER_PORCENTAJE = 0.50  # 40%


# Definición global con formato HTML directo
TEXTOS_METODOS = {
    'bpa': {
        'nombre': "<pre>BANCO POPULAR DE AHORRO (BPA)</pre>",
        'instrucciones': "Realiza la transferencia desde tu app BPA al número proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>💳 Número de tarjeta:</b> <code>9205129977430389\n</code>
<b>🔕 Confirmación obligatoria al:</b> <code>54082678</code>
""",
        'nota': "Obligatorio en la app cuando valla a realizar la transferencia marcar la casilla ☑️  El destinatario recibe mi número de móvil"
    },
    'mi_transfer': {
        'nombre': "<pre>MI TRANSFER (BOLSA)</pre>",
        'instrucciones': "Realiza la transferencia desde tu app al número de bolsa proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>💳 Número de bolsa:</b> <code>54082678\n</code>
""",
        'nota': "Obligatorio usar el número asociado a tu cuenta en QvaPlay"
    },
    'bandec': {
        'nombre': "<pre>BANCO CENTRAL DE CUBA (BANDEC)</pre>",
        'instrucciones': "Realiza la transferencia desde tu app al número de bolsa proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>💳 Número de tarjeta:</b> <code>9205129977430389\n</code>
<b>🔕 Confirmación obligatoria al:</b> <code>5408 2678</code>
""",
        'nota': "Esta es una transferencia a bolsa"
    },
    'mlc': {
        'nombre': "<pre>MONEDA LIBREMENTE CONVERTIBLE (MLC)</pre>",
        'instrucciones': "Realiza la transferencia desde tu app al número de tarjeta proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>💳 Número de tarjeta:</b> <code>9225129979794663</code>
<b>🔕 Confirmación obligatoria al:</b> <code>5408 2678</code>
""",
        'nota': "<b>1MLC</b> = {cambio_mlc} CUP"
    },
    'metro': {
        'nombre': "<pre>BANCO METROPOLITANO S.A (METROPOLITANO)</pre>",
        'instrucciones': "Realiza la transferencia desde tu app al número de tarjeta proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>💳 Número de tarjeta:</b> <code>9205129977430389</code>
<b>🔕 Confirmación obligatoria al:</b> <code>54082678</code>
""",
        'nota': "Obligatorio en la app cuando valla a realizar la transferencia marcar la casilla ☑️  El destinatario recibe mi número de móvil"
    },
    'saldo_movil': {
        'nombre': "<pre>SALDO MÓVIL (SALDO MOVIL)</pre>",
        'instrucciones': "Realiza la transferencia al número de teléfono proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>📱 Número destino:</b> <code>54082678</code>
""",
        'nota': "Si va a transferir desde otro número asegúrate de registrarlo en el perfil antes de transferir"
    },
    'enzona': {
        'nombre': "<pre>ENZONA</pre>",
        'instrucciones': "Realiza la transferencia desde tu app al número de tarjeta proporcionado, asegúrate de usar tu número asociado para realizar la transferencia y luego pulsa el botón de abajo, no se te pedirá ningún dato más",
        'detalle_cuenta': """
<b>📱 Número destino:</b> <code>9205129977430389</code>
<b>🔕 Confirmar al:</b> <code>54082678</code> (♦️OBLIGATORIO)
""",
        'nota': "Las transferencias por ENZONA tienden a rebotar muchas veces, podría pasar la verificación pero si el saldo rebota y no llega a la tarjeta de destino el saldo será restado en su cuenta."
    }
}



consejo = [
    "💡 ¡Invita a tus amigos y gana más! Tus referidos también generan ganancias para ti. 🎉",
    "💰 Recarga tu balance para participar en más jugadas. ¡Mientras más juegas, más oportunidades de ganar! 🎯",
    "🔗 Comparte tu enlace de referido y gana un porcentaje de lo que gasten tus amigos. ¡Es dinero fácil! 💸",
    "🎮 ¡En el juego de piratas, puedes mejorar tu barco, cañones y velas para aumentar tus ganancias! ⛵",
    "🏴‍☠️ Cada pirata que tengas genera más barriles. ¡Cuantos más piratas, más ganancias! 💰",
    "🌟 Asegúrate de mejorar en el juego de piratas. ¡Aumenta el nivel del barco, cañones y velas para generar más barriles y ganancias! 🚢💥",
    "📲 Unirte a canales y grupos es una forma genial de obtener CUP y otras recompensas sin hacer mucho. ¡Solo únete y gana! 📢",
    "🚀 ¡Haz crecer tu red! Comparte tu canal y haz que más personas se unan. Cuantos más usuarios, más oportunidades de ganar. 🌍",
    "🎯 Jugar minijuegos te permite ganar CUP adicionales. ¡Juega todos los que puedas para aumentar tu saldo! 🎲",
    "🧩 Participa en los minijuegos de piratas para ganar fichas y mejorar tus elementos. ¡Juega y mejora tu equipo para más ganancias! 💎",
    "💥 ¡Los minijuegos tienen recompensas sorpresa! Cada victoria puede darte CUP extra y mejoras para tu barco y tu tripulacion. 🎉",
    "⚽ En las apuestas de Total, predice el número total de goles en un partido. ¡La clave está en conocer a los equipos! ⚽",
    "🎯 Con las apuestas BTTS (ambos equipos marcan), ¡se gana cuando ambos equipos marcan goles durante el partido! ⚽💥",
    "👥 En las apuestas H2H (Head to Head), apuestas por cuál de los dos equipos ganará. ¡Todo depende de los duelos directos! 🔥",
    "🏅 El Hándicap permite que un equipo tenga ventaja o desventaja antes de empezar el partido. ¡Estudia bien las estadísticas! 📊",
    "🔄 En las apuestas DNB (Draw No Bet), si el partido termina en empate, te devuelven tu dinero. ¡Apostar con mayor seguridad! 🔒",
    "💡 Recuerda que el bono no puede ser retirado directamente, solo puedes retirar las ganancias generadas con él. ¡Juega para ganar! 💰",
    "🔄 Para retirar el bono retirable, debes cumplir con el rollover establecido y alcanzar la medalla requerida. ¡Hazlo bien! 🏅",
    "🎯 Si apuestas con un bono, las ganancias irán directamente al bono retirable, no al bono inicial. ¡Gana y convierte el bono en saldo! 🔄",
    "📊 Conoce bien las reglas de cada tipo de apuesta: Total, BTTS, H2H, Hándicap y DNB para apostar de forma inteligente. 📈",
    "💸 Si deseas retirar el bono, ¡no olvides cumplir con los requisitos de rollover y alcanzar la medalla necesaria para hacerlo! 🎯",
    "⚽ Elige bien tus apuestas de Total, BTTS, H2H, Hándicap y DNB según el análisis de equipos y su rendimiento en los partidos. 📅",
    "🔍 Las apuestas AMBOS ANOTAN son perfectas para partidos con equipos ofensivos. ¡Asegúrate de estudiar las tácticas antes de apostar! 💡",
    "📌 En H2H, ten en cuenta los enfrentamientos previos y el rendimiento reciente de los equipos. ¡La historia de los duelos importa! 🧐",
    "💎 Recuerda que el bono solo es útil si juegas con él. ¡Utiliza tus ganancias para cumplir con el rollover y desbloquearlo para el retiro! 🏆"
]

oponente_id = "7106422817"  # ID del oponente automático
nombres_aleatorios = [
    "Odalis", "Ede", "Bigote", "Elizabeth", "Cristian", "yandri", 
    "Erian09", "El naja", "laurita", "yaima", "El chiqui", "Estefani", "Elier", 
    "lurdes", "Lázaro", "Elizabeth", "yennys", "Neray", "Dayany", "Ashley_Demir", 
    "Yoel", "Albertico", "Rauli", "Lorenso", "El chuli", "Pancho", "El flaco", 
    "Ramonsito", "Armandito", "Yariel", "Niurka", "El Gato", "Yadira", "El Chacal", 
    "Kike", "La Yuma", "El Loco", "Alicia", "Pipo", "Reinaldo", "El Bebe", "La Chiqui", 
    "El Titi", "La Mulata", "Yunior", "La China", "El Coche", "Panchito", "La Rusa", 
    "Nene", "Marta", "Beto", "Chery", "Mayito", "Coco", "El Padrino", "Tatiana", 
    "El Monje", "Lissette", "El Titi", "Juanito", "Carmen", "El Bebo", "Raulito", 
    "Chama", "Yohandri", "Mili", "El Loco", "Nelson", "El Tio", "La Roca", "Carmencita"
]


logging.basicConfig(level=logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)









bot_activo = True
tiempo_restante = 0
motivo_mantenimiento = ""  # Motivo para el mantenimiento

def load_tunnel_url():
    """Carga la URL del tunnel desde el JSON"""
    try:
        with open("tunnel_urls.json", "r") as f:
            data = json.load(f)
            return data.get("tunnel_url")
    except:
        return None

def create_web_app_button(user_id, endpoint="/main", button_text="🌐 Ir a la App", url_only=False):
    """
    Crea un botón web o retorna la URL para un endpoint específico
    
    Args:
        user_id: ID del usuario de Telegram
        endpoint: Ruta específica (/juego_alta_baja, /piedra-papel-tijera, etc.)
        button_text: Texto que aparecerá en el botón
        url_only: Si True, retorna solo la URL sin el objeto InlineKeyboardButton
    
    Returns:
        InlineKeyboardButton o str: Dependiendo de url_only
    """
    tunnel_url = load_tunnel_url()
    if tunnel_url:
        # URL con el endpoint y user_id como parámetro
        web_app_url = f"{tunnel_url}{endpoint}?user_id={user_id}"
        
        if url_only:
            return web_app_url
        else:
            return InlineKeyboardButton(button_text, url=web_app_url)
    else:
        return None


async def apagar_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para desactivar el bot durante un tiempo específico"""
    global bot_activo, tiempo_restante, motivo_mantenimiento

    user_id = str(update.effective_user.id)  # Convertir el ID a cadena
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    try:
        horas = float(context.args[0])  # Permitir decimales
        tiempo_restante = int(horas * 3600)  # Convertir horas a segundos
        # Guardar el motivo del mantenimiento
        motivo_mantenimiento = " ".join(context.args[1:]) if len(context.args) > 1 else "Mantenimiento general"
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usa el comando así: /off <horas> <motivo>\nEjemplo: `/off 0.5 Corrigiendo errores`", parse_mode="Markdown")
        return

    bot_activo = False
    await update.message.reply_text(f"⚙️ Modo mantenimiento activado por {horas} horas.\nMotivo: {motivo_mantenimiento}")

    async def temporizador():
        global bot_activo, tiempo_restante
        while tiempo_restante > 0:
            await asyncio.sleep(60)  # Esperar 1 minuto antes de actualizar
            tiempo_restante -= 60
        bot_activo = True

    asyncio.create_task(temporizador())


async def encender_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para reactivar el bot manualmente"""
    global bot_activo, tiempo_restante, motivo_mantenimiento

    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            "🚫 <b>Acceso denegado</b>\n"
            "No tienes permisos para usar este comando.",
            parse_mode='HTML'
        )
        return

    bot_activo = True
    tiempo_restante = 0
    motivo_mantenimiento = ""
    
    await update.message.reply_text(
        "🟢 <b>Bot Reactivado</b>\n\n"
        "✅ Todos los servicios han sido restablecidos\n"
        "🔄 Puedes volver a usar el bot normalmente",
        parse_mode='HTML'
    )
    
async def filtro_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_activo, tiempo_restante, motivo_mantenimiento
    
    # Permitir comandos críticos
    if update.message and update.message.text:
        cmd = update.message.text.split()[0].lower()
        if cmd in ["/on", "/off", "/balance", "/bono", "get", "/ban"] and str(update.effective_user.id) in ADMIN_IDS:
            print(f"✅ Comando admin permitido: {cmd}")
            return

    if not bot_activo:
        horas, minutos = divmod(tiempo_restante // 60, 60)
        tiempo_formato = f"{horas}h {minutos}m" if horas > 0 else f"{minutos}m"
        
        mensaje_html = (
            "🔧 <b>MANTENIMIENTO EN CURSO</b>\n\n"
            f"⏳ <b>Tiempo restante:</b> {tiempo_formato}\n"
            f"📝 <b>Motivo:</b> {motivo_mantenimiento or 'Mantenimiento general'}\n\n"
            "⚠️ El bot no está disponible temporalmente\n"
            "🔔 Te notificaremos cuando vuelva a estar operativo"
        )
        
        if update.message:
            await update.message.reply_text(
                mensaje_html,
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()  # Elimina teclado si existe
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "🚧 Bot en mantenimiento - Intente más tarde",
                show_alert=True
            )
        
        raise ApplicationHandlerStop    
    
# Añadir al inicio del archivo con las otras constantes
REGALO_ACTIVO = False
CONTADOR_MENSAJES = {}  # {user_id: count}
ULTIMO_PREMIO = 0

async def regalo_on(update: Update, context: CallbackContext):
    """Activa el sistema de regalos por mensajes (solo admin)"""
    if str(update.effective_user.id) != "7031172659":  # Reemplaza con el ID de tu admin
        await update.message.reply_text("❌ Comando solo para administradores")
        return
    
    global REGALO_ACTIVO
    REGALO_ACTIVO = True
    await update.message.reply_text(
        "🎁 <b>Sistema de regalos ACTIVADO</b>\n\n"
        "Ahora los usuarios ganarán CUP aleatorios por enviar mensajes en el grupo.",
        parse_mode="HTML"
    )

async def regalo_off(update: Update, context: CallbackContext):
    """Desactiva el sistema de regalos por mensajes (solo admin)"""
    if str(update.effective_user.id) != "7031172659":  # Reemplaza con el ID de tu admin
        await update.message.reply_text("❌ Comando solo para administradores")
        return
    
    global REGALO_ACTIVO, CONTADOR_MENSAJES, ULTIMO_PREMIO
    REGALO_ACTIVO = False
    CONTADOR_MENSAJES = {}
    ULTIMO_PREMIO = 0
    await update.message.reply_text(
        "🚫 <b>Sistema de regalos DESACTIVADO</b>",
        parse_mode="HTML"
    )


async def contar_mensajes_para_regalo(update: Update, context: CallbackContext):
    """Cuenta los mensajes y otorga premios aleatorios usando SQLite"""
    global REGALO_ACTIVO, CONTADOR_MENSAJES, ULTIMO_PREMIO
    
    if not update or not update.message:
        print("⚠️ Update inválido recibido")
        return
    
    if not REGALO_ACTIVO or update.message.chat.id != GROUP_CHAT_ID:
        return
    
    user_id = str(update.effective_user.id)
    
    # Inicializar contador si es nuevo usuario
    if user_id not in CONTADOR_MENSAJES:
        CONTADOR_MENSAJES[user_id] = 0
        
    CONTADOR_MENSAJES[user_id] += 1
    
    # Elegir aleatoriamente el umbral para el próximo premio
    umbral_premio = random.choice([30, 50, 60])
    
    if CONTADOR_MENSAJES[user_id] >= umbral_premio and (tm.time() - ULTIMO_PREMIO) > 1:
        premio = random.randint(1, 6)

        # --- Aquí se actualiza SQLite ---
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            
            # Crear usuario si no existe
            c.execute("SELECT balance FROM usuarios WHERE id = ?", (user_id,))
            row = c.fetchone()
            if row is None:
                c.execute("INSERT INTO usuarios (id, nombre, balance) VALUES (?, ?, ?)",
                          (user_id, update.effective_user.first_name, premio))
                balance_actual = premio
            else:
                balance_actual = row[0] + premio
                c.execute("UPDATE usuarios SET balance = ? WHERE id = ?", (balance_actual, user_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error al actualizar balance en DB: {e}")
            return
        
        # Reiniciar contador y cooldown
        CONTADOR_MENSAJES[user_id] = 0
        ULTIMO_PREMIO = tm.time()
        
        # Notificar al usuario
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 <b>¡Has ganado un premio!</b>\n\n"
                     f"Por tu actividad en el grupo, recibiste <b>{premio} CUP</b>.\n\n"
                     f"💰 Balance actual: <b>{balance_actual} CUP</b>\n\n"
                     f"¡Sigue participando para ganar más!",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error al notificar usuario: {str(e)}")
        
        # Mensaje en el grupo
        try:
            await update.message.reply_text(
                f"🎁 ¡Felicidades! <a href='tg://user?id={user_id}'>{update.effective_user.first_name}</a> "
                f"ha ganado {premio} CUP en balance por su actividad en el grupo!",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error al anunciar en grupo: {str(e)}")
    
    else:
        print(f"! No cumple condiciones para premio (contador: {CONTADOR_MENSAJES[user_id]}/{umbral_premio}, cooldown: {tm.time() - ULTIMO_PREMIO}s)")
        
async def guardar_usuarios_bloqueados():
    async with usuarios_bloqueados_lock:  # Bloquea el acceso concurrente
        with open("usuarios_bloqueados.json", "w") as f:
            json.dump(list(usuarios_bloqueados), f)

# Función para cargar datos de minijuegos
async def load_minijuegos_datafull():
    try:
        with open(MINIJUEGOS_FILE, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    except Exception as e:
        print(f"Error al cargar minijuegos.json: {e}")
        data = {}

    # Verificar si el usuario ya tiene datos, si no, inicializar los minijuegos
    if "ALTA BAJA" not in data:
        data["ALTA BAJA"] = {
            "FichGanadas": {},
            "FichPerdidas": {},
            "BetLost": {},
            "BetWin": {}
        }
    if user_id not in data["ALTA BAJA"]["FichGanadas"]:
        data["ALTA BAJA"]["FichGanadas"][user_id] = 0
    if user_id not in data["ALTA BAJA"]["FichPerdidas"]:
        data["ALTA BAJA"]["FichPerdidas"][user_id] = 0
    if user_id not in data["ALTA BAJA"]["BetLost"]:
        data["ALTA BAJA"]["BetLost"][user_id] = 0
    if user_id not in data["ALTA BAJA"]["BetWin"]:
        data["ALTA BAJA"]["BetWin"][user_id] = 0

    # Inicializar datos para otros minijuegos si es necesario
    minijuegos = ["BUSCAMINAS", "BLACKJACK", "PIEDRA PAPEL TIJERA", "ABRE COFRES"]
    for minijuego in minijuegos:
        if minijuego not in data:
            data[minijuego] = {
                "FichGanadas": {},
                "FichPerdidas": {},
                "BetLost": {},
                "BetWin": {}
            }
        if user_id not in data[minijuego]["FichGanadas"]:
            data[minijuego]["FichGanadas"][user_id] = 0
        if user_id not in data[minijuego]["FichPerdidas"]:
            data[minijuego]["FichPerdidas"][user_id] = 0
        if user_id not in data[minijuego]["BetLost"]:
            data[minijuego]["BetLost"][user_id] = 0
        if user_id not in data[minijuego]["BetWin"]:
            data[minijuego]["BetWin"][user_id] = 0

    # Guardar los datos actualizados
    await save_minijuegos_data(data)
    return data


# Función para guardar datos de minijuegos con lock
async def save_minijuegos_data(data):
    async with minijuegos_lock:  # Bloquear acceso al archivo
        try:
            with open(MINIJUEGOS_FILE, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Error al guardar minijuegos.json: {e}")    



# Decorador para verificar si el usuario está bloqueado
def verificar_bloqueo(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = None

        # Comprobamos si la actualización es un mensaje
        if update.message:
            user_id = str(update.message.from_user.id)
        
        # Comprobamos si la actualización es un callback
        elif update.callback_query:
            user_id = str(update.callback_query.from_user.id)

        # Si no encontramos un user_id, continuamos con la función original
        if not user_id:
            return await func(update, context, *args, **kwargs)

        # Llamamos a detectar_multicuentas antes de verificar si está bloqueado
        

        # Cargar los usuarios bloqueados
        usuarios_bloqueados = await cargar_usuarios_bloqueados()

        # Si el usuario está bloqueado, enviamos un mensaje y detenemos la ejecución
        if user_id in usuarios_bloqueados:
            if update.message:
                await update.message.reply_text("❌ Has sido bloqueado y no puedes usar este bot.")
            elif update.callback_query:
                await update.callback_query.answer("❌ Has sido bloqueado y no puedes usar este bot.")
            return  # Detenemos el flujo

        # Si no está bloqueado, llamamos a la función original
        return await func(update, context, *args, **kwargs)

    return wrapper




@verificar_bloqueo 
async def start(update: Update, context: CallbackContext):
    try:
        # Verificar que el comando se ejecuta en chat privado
        if update.message.chat.type != "private":
            await update.message.reply_text(
                "<blockquote>❌ Lo siento, no puedo darte mis servicios en público.</blockquote>\n"
                "<i>Por favor, envíame un mensaje en privado usando el botón de abajo</i>:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🤖 Envíame un mensaje🤖",
                        url=f"https://t.me/QvaPlay_bot"
                    )]
                ])
            )
            return

        # Procesar datos del usuario
        user = update.message.from_user
        user_name = user.first_name or "Usuario"
        user_id = str(user.id)
        now = datetime.now().strftime('%d/%m/%Y %H:%M')

        # Conexión a la DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Asegurar tablas mínimas (no reescribe si ya existen)
        c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                        id TEXT PRIMARY KEY,
                        nombre TEXT,
                        balance INTEGER,
                        referidos INTEGER,
                        lider TEXT,
                        total_ganado_ref INTEGER,
                        medalla TEXT,
                        marca TEXT
                    )""")
        c.execute("""CREATE TABLE IF NOT EXISTS depositos (
                        id TEXT PRIMARY KEY,
                        nombre TEXT,
                        payment INTEGER,
                        amount INTEGER,
                        total_deposit INTEGER
                    )""")
        c.execute("""CREATE TABLE IF NOT EXISTS bono_apuesta (
                        id TEXT PRIMARY KEY,
                        bono INTEGER,
                        rollover_requerido INTEGER,
                        rollover_actual INTEGER,
                        bono_retirable INTEGER
                    )""")
        c.execute("""CREATE TABLE IF NOT EXISTS juego_pirata (
                        id TEXT PRIMARY KEY,
                        nombre TEXT,
                        barriles INTEGER,
                        piratas INTEGER,
                        tiempo_ultimo_reclamo REAL,
                        tiempo_para_ganar REAL,
                        ganancias_totales INTEGER,
                        hp_barco INTEGER,
                        prestigio INTEGER,
                        escudo_hasta REAL,
                        victorias INTEGER,
                        derrotas INTEGER
                    )""")
        conn.commit()

        nuevo_usuario = False
        leader_name = None

        # Contar usuarios actuales
        c.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = c.fetchone()[0] or 0

        # Verificar si el usuario existe
        c.execute("SELECT nombre, balance FROM usuarios WHERE id = ?", (user_id,))
        row = c.fetchone()

        if row is None:
            # Intentar restaurar desde basura (si existe esa función)
            restaurado = await restaurar_usuario_desde_basura(user_id, user_name, context)

            if restaurado:
                # Si restaurado, verificar que ahora exista en la DB
                c.execute("SELECT nombre, balance FROM usuarios WHERE id = ?", (user_id,))
                row = c.fetchone()
                await update.message.reply_text(
                    "♻️ <b>¡Bienvenido de nuevo!</b>\n\n"
                    "Ha pasado algún tiempo me alegro que hayas vuelto 👐.",
                    parse_mode='HTML'
                )
                # Recalcular total usuarios
                c.execute("SELECT COUNT(*) FROM usuarios")
                total_usuarios = c.fetchone()[0] or total_usuarios
            else:
                # Registrar nuevo usuario en varias tablas
                nuevo_usuario = True

                # usuarios
                c.execute("""INSERT OR REPLACE INTO usuarios
                             (id, nombre, balance, referidos, lider, total_ganado_ref, medalla, marca)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                          (user_id, user_name, 0, 0, "0", 0, "Sin medalla", now))

                # bono_apuesta
                c.execute("""INSERT OR REPLACE INTO bono_apuesta
                             (id, bono, rollover_requerido, rollover_actual, bono_retirable)
                             VALUES (?, ?, ?, ?, ?)""",
                          (user_id, 50, 250, 0, 0))

                # depositos
                c.execute("""INSERT OR REPLACE INTO depositos
                             (id, nombre, payment, amount, totalDeposit)
                             VALUES (?, ?, ?, ?, ?)""",
                          (user_id, user_name, 0, 0, 0))

                # juego_pirata (si quieres crear una entrada inicial)
                c.execute("""INSERT OR IGNORE INTO juego_pirata
                             (id, nombre, barriles, piratas, tiempo_ultimo_reclamo, tiempo_para_ganar,
                              ganancias_totales, hp_barco, prestigio, escudo_hasta, victorias, derrotas)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (user_id, user_name, 0, 0, 0, 3600, 0, 0, 0, 0, 0, 0))

                conn.commit()

                # Manejo de referidos SOLO para nuevos usuarios
                args = context.args
                if args and len(args) > 0:
                    leader_id = args[0]
                    # Verificar que el líder exista y no sea el mismo
                    c.execute("SELECT nombre FROM usuarios WHERE id = ?", (leader_id,))
                    leader_row = c.fetchone()
                    if leader_id != user_id and leader_row:
                        # Registrar referido: actualizar campos en DB
                        # 1) Set leader in user
                        c.execute("UPDATE usuarios SET lider = ? WHERE id = ?", (leader_id, user_id))
                        # 2) Incrementar referidos del líder
                        c.execute("UPDATE usuarios SET referidos = COALESCE(referidos,0) + 1 WHERE id = ?", (leader_id,))
                        # Obtener leader name
                        leader_name = leader_row[0]

                        # Asegurar entrada en bono_apuesta para el líder
                        c.execute("SELECT bono, rollover_requerido FROM bono_apuesta WHERE id = ?", (leader_id,))
                        bono_row = c.fetchone()
                        if not bono_row:
                            c.execute("""INSERT OR REPLACE INTO bono_apuesta
                                         (id, bono, rollover_requerido, rollover_actual, bono_retirable)
                                         VALUES (?, ?, ?, ?, ?)""",
                                      (leader_id, 0, 0, 0, 0))
                        # Aplicar bonificación al líder
                        c.execute("UPDATE usuarios SET balance = COALESCE(balance,0) + 5 WHERE id = ?", (leader_id,))
                        # Actualizar bono_apuesta del líder
                        c.execute("""UPDATE bono_apuesta
                                     SET bono = COALESCE(bono,0) + 30,
                                         rollover_requerido = COALESCE(rollover_requerido,0) + 160
                                     WHERE id = ?""", (leader_id,))

                        # Bonificación en juego_pirata para el líder
                        piratas_bonus = 1
                        barriles_bonus = 200
                        c.execute("SELECT piratas, barriles FROM juego_pirata WHERE id = ?", (leader_id,))
                        gp_row = c.fetchone()
                        if gp_row:
                            # actualizar
                            c.execute("""UPDATE juego_pirata
                                         SET piratas = COALESCE(piratas,0) + ?,
                                             barriles = COALESCE(barriles,0) + ?
                                         WHERE id = ?""", (piratas_bonus, barriles_bonus, leader_id))
                        else:
                            # crear con valores iniciales (piratas +6)
                            c.execute("""INSERT OR REPLACE INTO juego_pirata
                                         (id, nombre, barriles, piratas, tiempo_ultimo_reclamo, tiempo_para_ganar,
                                          ganancias_totales, hp_barco, prestigio, escudo_hasta, victorias, derrotas)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                      (leader_id, leader_name, barriles_bonus, piratas_bonus + 6, 0, 3600, 0, 0, 0, 0, 0, 0))

                        conn.commit()

        else:
            # Si el usuario ya existe, actualizar nombre si cambió
            nombre_actual = row[0]
            if nombre_actual != user_name:
                c.execute("UPDATE usuarios SET nombre = ? WHERE id = ?", (user_name, user_id))
                # actualizar depositos si existe
                c.execute("UPDATE depositos SET nombre = ? WHERE id = ?", (user_name, user_id))
                conn.commit()

        # Verificar y crear Bono_apuesta si no existe para el usuario (asegurar fila)
        c.execute("SELECT 1 FROM bono_apuesta WHERE id = ?", (user_id,))
        if c.fetchone() is None:
            c.execute("""INSERT OR REPLACE INTO bono_apuesta
                         (id, bono, rollover_requerido, rollover_actual, bono_retirable)
                         VALUES (?, ?, ?, ?, ?)""",
                      (user_id, 50, 200, 0, 0))
            conn.commit()

        # FIN DE BLOQUE DE DB
        conn.close()

        # Notificaciones (fuera del bloqueo)
        if nuevo_usuario and leader_name:
            # Notificar al líder
            try:
                await context.bot.send_message(
                    chat_id=int(leader_id),
                    text=(
                        f"<blockquote>🙌 ¡Nueva referencia!</blockquote>\n\n"
                        f"👤 <b>Has invitado a:</b> {user_name}\n"
                        f"💰 <b>Balance:</b> +5 CUP\n"
                        f"🎁 <b>Bono de apuesta:</b> +30 CUP\n"
                        f"🏴‍☠️ <b>Piratas:</b> +{piratas_bonus}\n"
                        f"🛢️ <b>Barriles:</b> +{barriles_bonus}"
                    ),
                    parse_mode='HTML'
                )
            except Exception as e:
                logging.error(f"Error al notificar al líder {leader_id}: {str(e)}")

            # Registrar en grupos
            registro_message = (
                f"<blockquote>🆕NEW USER REGISTRADO</blockquote>\n\n"
                f"👤 <b>Usuario:</b> {user_name}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"📅 <b>Registro:</b> {now}\n"
                f"👥 <b>Total usuarios:</b> {total_usuarios + 1}\n"
                f"👑 <b>Invitado por:</b> {leader_name}"
            )

            if GROUP_REGISTRO:
                try:
                    await context.bot.send_message(
                        chat_id=REGISTRO_MINIJUEGOS,
                        text=registro_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logging.error(f"Error al enviar a GROUP_REGISTRO: {str(e)}")

            if GROUP_CHAT_ID:
                try:
                    await context.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=f"🎁 {leader_name} ha invitado a {user_name} y ha ganado <b>30 CUP gratis</b>. ¿Que esperas? invita y gana, tu tambien puedes",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logging.error(f"Error al enviar a GROUP_CHAT_ID: {str(e)}")

        # Notificar registro para usuarios no referidos
        if nuevo_usuario and not leader_name and GROUP_REGISTRO:
            registro_message = (
                f"<blockquote>🆕NEW USER REGISTRADO</blockquote>\n\n"
                f"👤 <b>Usuario:</b> {user_name}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"📅 <b>Registro:</b> {now}\n"
                f"👥 <b>Total usuarios:</b> {total_usuarios + 1}"
            )
            try:
                await context.bot.send_message(
                    chat_id=REGISTRO_MINIJUEGOS,
                    text=registro_message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logging.error(f"Error al notificar registro: {str(e)}")

        # Verificar canales y mostrar menú (fuera del lock)
        result = await verificar_canales(update, context)
        if not result:
            return

        keyboard = [
            [create_web_app_button(user_id, endpoint="/index", button_text="🚀AppWeb🚀")],
            [InlineKeyboardButton("💰 Mi Saldo", callback_data="Mi Saldo"),
             InlineKeyboardButton("🎰 La bolita", callback_data="La_bolita")],
            [InlineKeyboardButton("💥 Invita y Gana 💥", callback_data="Invita_Gana")],
            [InlineKeyboardButton("🎮 Minijuegos", callback_data="Minijuegos"),
             InlineKeyboardButton("⚽ Apuestas", callback_data="mostrar_tipos_apuestas")],
            [InlineKeyboardButton("👨‍💻 Tareas Pagadas 👨‍💻", callback_data="Tareas_Pagadas")],
            [InlineKeyboardButton("🆘 Soporte", callback_data="menu_soporte"),
             InlineKeyboardButton("🚔 Reglas", callback_data="Reglas")],
            [InlineKeyboardButton("🔮 Pronósticos 🔮", callback_data="Pronosticos")],
            [InlineKeyboardButton("🎁 Bono diario 🎁", callback_data="bono_diario")]
        ]

        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="Admin_Panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        consejo_aleatorio = random.choice(consejo)

        await update.message.reply_text(
            f"¡Hola, {user_name}! 👋\n\n<b>Selecciona una opción del menú para empezar:</b>\n\n🌟<blockquote>{consejo_aleatorio}</blockquote>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        logging.error(f"Error en /start: {str(e)}", exc_info=True)
        try:
            await update.message.reply_text("Ocurrió un error. Por favor, inténtalo de nuevo más tarde.")
        except Exception as e2:
            logging.error(f"Error al enviar mensaje de error: {str(e2)}")

from telegram.error import RetryAfter, TimedOut, NetworkError

async def verificar_canales(update, context):
    required_chats = {
        REQUIRED_CHANNEL_ID: {
            "name": "Canal Oficial 📢",
            "link": CHANNEL_INVITE_LINK
        },
        GROUP_CHAT_ID: {
            "name": "Grupo Principal 💬",
            "link": GROUP_INVITE_LINK
        }
    }

    missing_chats = []

    for chat_id, info in required_chats.items():
        try:
            member_status = await context.bot.get_chat_member(chat_id, update.message.from_user.id)
            if member_status.status not in ["member", "administrator", "creator"]:
                missing_chats.append(info)
        except (TimedOut, NetworkError, RetryAfter) as e:
         
            # Si hay error de red o timeout => consideramos que sí está suscrito
            continue
        except Exception as e:
            logging.error(f"Error inesperado verificando membresía en {chat_id}: {e}")
            # Si es otro error inesperado, asumimos que falta
            missing_chats.append(info)

    if missing_chats:
        buttons = [
            InlineKeyboardButton(
                text=f"Unirme a {info['name']}",
                url=info['link']
            ) for info in missing_chats
        ]
        await update.message.reply_text(
            f"⚠️ {update.message.from_user.first_name}, para usar este bot debes estar unido a:\n\n" +
            "\n".join([f"• {info['name']}" for info in missing_chats]),
            reply_markup=InlineKeyboardMarkup([buttons]),
            parse_mode='HTML'
        )
        return False

    return True
        

async def Invita_Gana(update: Update, context: CallbackContext):
    try:
        # Verificación más segura del objeto update
        if not update:
            logging.error("Update es None")
            return

        # Determinar si viene de comando o callback_query
        is_command = update.message is not None
        
        if is_command:
            # Lógica para comando /invitar
            user = update.message.from_user
            chat_id = update.message.chat_id
            message_id = update.message.message_id
            send_method = context.bot.send_message
        else:
            # Lógica para botón
            if not update.callback_query:
                logging.error("No hay callback_query en el update")
                return
                
            user = update.callback_query.from_user
            chat_id = update.callback_query.message.chat_id
            message_id = update.callback_query.message.message_id
            send_method = update.callback_query.edit_message_text
            await update.callback_query.answer()

        if not user:
            logging.error("No se pudo obtener información del usuario")
            return

        user_id = str(user.id)

        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Nombre, Referidos, total_ganado_ref")
        
        # Verificar registro
        if not usuario_data:
            response = "⚠️ Regístrate primero con /start"
            if is_command:
                await context.bot.send_message(chat_id, response)
            else:
                await update.callback_query.answer(response, show_alert=True)
            return
        
        # Extraer datos del usuario
        nombre = usuario_data[0] if usuario_data[0] else "Usuario"
        referidos = usuario_data[1] if usuario_data[1] is not None else 0
        total_ganado = usuario_data[2] if usuario_data[2] is not None else 0
        
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        # Mensaje mejorado
        mensaje_principal = f"""
<pre>🔥 ¡INVITA Y GANA DINERO REAL! 🔥</pre>

💰 <b>¡OFERTA EXCLUSIVA!</b>
└ 50 CUP GRATIS para nuevos usuarios

🤑 <b>¡TÚ GANAS!</b>
├ 🎁 30 CUP por cada amigo.
├ 🛢️ 200 barriles.
├ ☠️ + 1 pirata.
├ 10% de sus apuestas con bono. 
└ 1% de sus apuestas con balance.

🔗 <b>Tu enlace personal:</b>
<code>{referral_link}</code>

📊 <b>TUS ESTADÍSTICAS:</b>
┌ 👥 Referidos: <b>{referidos}</b>
└ 🎁 Bono ganado: <b>{total_ganado} CUP</b>
"""

        keyboard = [
            [InlineKeyboardButton("🍻 Mensaje para Invitar ✉️", callback_data="invitar")],
            [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Enviar o editar mensaje según corresponda
        if is_command:
            await context.bot.send_message(
                chat_id=chat_id,
                text=mensaje_principal,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            try:
                await update.callback_query.edit_message_text(
                    text=mensaje_principal,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            except BadRequest as e:
                if "message is not modified" in str(e):
                    pass  # El mensaje es el mismo, no hay necesidad de actualizar
                else:
                    raise

    except Exception as e:
        logging.error(f"Error en Invita_Gana: {str(e)}", exc_info=True)
        if not is_command and update.callback_query:
            await update.callback_query.answer("❌ Error al procesar la solicitud", show_alert=True)
        elif is_command and update.message:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="❌ Error al procesar la solicitud"
            )

# Función que maneja la invitación al grupo
@verificar_bloqueo
async def compartir_invitacion(update: Update, context: CallbackContext):  
    try:  
        user = update.callback_query.from_user  
        user_id = user.id  
        user_name = user.first_name  
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"  
  
        mensaje_invitacion = (  
            f"<b>🔥 ¡RECLAMA 50 CUP GRATIS AHORA!</b>\n\n"
            "<i>Comienza gratis y gana desde el primer momento!</i>\n"  
            " <blockquote>🎮Minijuego Pirata: mejora tus velas, cañones y barco, compra piratas para tu tripulación, "  
            "y aumenta tu producción de barriles por hora. Luego, ¡vende tus barriles y obtén dinero directo a tu tarjeta! 💵\n</blockquote>"  
            " <blockquote>🎱La Bolita 🎲: ¡Juega la bolita y prueba tu suerte en todas las loterías existentes! 🎰</blockquote>\n"  
            " <blockquote>🔮Pronósticos gratuitos: Usamos inteligencia artificial para predecir qué números van a salir. 📈\n\n</blockquote>"  
            "<blockquote>⚽Apuestas deportivas: Apuestas en tiempo real para casi todos los deportes. Pagos automáticos sin demoras🏀🏈</blockquote>\n"  
            " <blockquote>📱Cobra en CUP por unirte a grupos y canales de Telegram o agrega tu propio canal y ve cómo se llena de usuarios. 🌐</blockquote>\n"  
            "<pre>¡Y muchos más minijuegos para ganar CUP!</pre>\n"  
            "✊ Piedra, Papel, Tijera (Multiplayer)\n"  
            "🔍 Buscaminas 🕹️\n"  
            "♠️ BlackJack (Multiplayer)\n"  
            "🔢 Alta o Baja\n"  
            "🎁 Abre cofres misteriosos 🗝️\n\n"  
            "💎 <b>Único proyecto cubano con depósitos automáticos, no necesitas administrador el bot acredita tu deposito en cuestión de segundos</b>\n\n"  
            "<i>¡Y todo esto en un solo lugar! No te lo puedes perder 🚀</i>\n\n"  
            f"🔗 <b>¡ÚNETE PULSANDO AQUÍ:</b> {referral_link}"  
        )  
  
        # Crear botón con enlace de referido  
        keyboard = [  
            [InlineKeyboardButton("✅ UNIRME Y RECLAMAR 50 CUP", url=referral_link)]  
        ]  
        reply_markup = InlineKeyboardMarkup(keyboard)  
  
        # Enviar mensaje principal con botón  
        await update.callback_query.message.reply_text(  
            mensaje_invitacion,  
            parse_mode="HTML",  
            reply_markup=reply_markup  
        )  
  
        # Enviar mensaje personalizado adicional  
        mensaje_extra = (  
            f"🍾He preparado para ti un mensaje agradable, {user_name}. "  
            "Compártelo en grupos para atraer invitados y multiplicar tus ganancias."  
        )  
        await update.callback_query.message.reply_text(mensaje_extra)  
  
        await update.callback_query.answer("✅¡Mensaje listo para compartir!")  
  
    except Exception as e:  
        logging.error(f"Error en compartir_invitacion: {e}")  
        if update.callback_query.message:  
            await update.callback_query.message.reply_text("Ocurrió un error al compartir la invitación.")

# Función para el panel de administración
@verificar_bloqueo
async def Admin_Panel(update: Update, context: CallbackContext):
    try:
        query = update.callback_query  
        if not query:
            return  
        
        user_id = str(update.effective_user.id)

        # Verificar permisos de admin
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ Acceso denegado", show_alert=True)
            return

        # Obtener datos desde la base de datos
        # Total de usuarios
        consulta_usuarios = "SELECT COUNT(*) FROM usuarios"
        total_usuarios = ejecutar_consulta_segura(consulta_usuarios, obtener_resultados=True)[0][0]

        # Suma de balances de usuarios
        consulta_balance = "SELECT SUM(balance) FROM usuarios"
        total_balance_result = ejecutar_consulta_segura(consulta_balance, obtener_resultados=True)
        total_balance = float(total_balance_result[0][0] or 0) if total_balance_result else 0

        # Datos de bonos
        consulta_bonos = "SELECT SUM(bono), SUM(rollover_requerido), SUM(rollover_actual), SUM(bono_retirable) FROM bono_apuesta"
        bono_data = ejecutar_consulta_segura(consulta_bonos, obtener_resultados=True)
        
        if bono_data and bono_data[0]:
            total_bono = float(bono_data[0][0] or 0)
            total_rollover_requerido = float(bono_data[0][1] or 0)
            total_rollover_actual = float(bono_data[0][2] or 0)
            total_bono_retirable = float(bono_data[0][3] or 0)
        else:
            total_bono = total_rollover_requerido = total_rollover_actual = total_bono_retirable = 0

        # Construir mensaje HTML
        mensaje = f"""
🏦 <b>PANEL DE CONTROL ADMINISTRATIVO</b> 🏦

👥 <b>Usuarios Registrados:</b> {total_usuarios}
💰 <b>Balance Total:</b> {total_balance:.2f} CUP

🎰 <b>Bonos en Sistema:</b>
├ 🎁 Total Bono: {total_bono:.2f} CUP
├ 🎯 Rollover Requerido: {total_rollover_requerido:.2f} CUP
├ 📈 Rollover Actual: {total_rollover_actual:.2f} CUP
└ 💸 Bono Retirable: {total_bono_retirable:.2f} CUP
"""

        # Crear teclado inline
        keyboard = [
            [InlineKeyboardButton("⏩ Pagar", callback_data='ejecutar_pagar'),
             InlineKeyboardButton("⏹️ Detener", callback_data='detener_pagos')],
            [InlineKeyboardButton("📂 Apuestas", callback_data='resumen_apuestas'),
             InlineKeyboardButton("👨‍💻 Tareas", callback_data='resumen_tareas')],
            [InlineKeyboardButton("🎮 Minijuegos", callback_data='resumen_minijuegos')],
            [InlineKeyboardButton("🎰 Loterías", callback_data='cmd_loterias'),
             InlineKeyboardButton("⛔ Refrescar", callback_data='cmd_refrescar_loterias')],
            [InlineKeyboardButton("🔙 Menu principal", callback_data='cmd_menu_principal')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(mensaje, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

        await query.answer()

    except Exception as e:
        print(f"Error en admin_panel: {str(e)}")
        import traceback
        traceback.print_exc()
        if query:
            await query.answer("⚠️ Error al cargar el panel", show_alert=True)

async def resumen_minijuegos(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    try:
        with open('minijuegos.json', 'r') as f:
            minijuegos_data = json.load(f)
        
        with open('user_data.json', 'r') as f:
            user_data = json.load(f)

        # Calcular estadísticas generales
        stats = {
            'total_fichas_ganadas': 0,
            'total_fichas_perdidas': 0,
            'total_apuestas_ganadas': 0,
            'total_apuestas_perdidas': 0
        }

        # Procesar cada minijuego
        mensaje = "🎮 <b>RESUMEN DE MINIJUEGOS</b> 🎮\n\n"
        
        for juego, datos in minijuegos_data.items():
            mensaje += f"🕹️ <b>{juego.upper()}</b>\n"
            
            # Estadísticas por juego
            fichas_ganadas = sum(datos['FichGanadas'].values())
            fichas_perdidas = sum(datos['FichPerdidas'].values())
            apuestas_ganadas = sum(datos['BetWin'].values())
            apuestas_perdidas = sum(datos['BetLost'].values())
            
            mensaje += f"├ 🏆 Fichas Ganadas: {fichas_ganadas}\n"
            mensaje += f"├ 💸 Fichas Perdidas: {fichas_perdidas}\n"
            mensaje += f"├ ✅ Apuestas Ganadas: {apuestas_ganadas}\n"
            mensaje += f"└ ❌ Apuestas Perdidas: {apuestas_perdidas}\n\n"
            
            # Actualizar totales generales
            stats['total_fichas_ganadas'] += fichas_ganadas
            stats['total_fichas_perdidas'] += fichas_perdidas
            stats['total_apuestas_ganadas'] += apuestas_ganadas
            stats['total_apuestas_perdidas'] += apuestas_perdidas

        # Estadísticas generales
        mensaje += "📊 <b>ESTADÍSTICAS GLOBALES</b>\n"
        mensaje += f"├ 🏆 Total Fichas Ganadas: {stats['total_fichas_ganadas']}\n"
        mensaje += f"├ 💸 Total Fichas Perdidas: {stats['total_fichas_perdidas']}\n"
        mensaje += f"├ ✅ Total Apuestas Ganadas: {stats['total_apuestas_ganadas']}\n"
        mensaje += f"└ ❌ Total Apuestas Perdidas: {stats['total_apuestas_perdidas']}\n\n"

        # Top 5 productores del juego pirata
        if 'juego_pirata' in user_data:
            productores = []
            for user_id, datos in user_data['juego_pirata'].items():
                productores.append((
                    user_data['usuarios'][user_id]['Nombre'],
                    datos.get('ganancias_totales', 0)
                ))
            
            top_5 = sorted(productores, key=lambda x: x[1], reverse=True)[:5]
            
            mensaje += "🏴‍☠️ <b>TOP 5 PRODUCTORES PIRATAS</b>\n"
            for i, (nombre, ganancia) in enumerate(top_5, 1):
                mensaje += f"{i}. {nombre}: {ganancia:.2f} CUP/h\n"

        await update.callback_query.edit_message_text(mensaje, parse_mode=ParseMode.HTML)

    except Exception as e:
        logging.error(f"Error en resumen_minijuegos: {str(e)}")
        await update.callback_query.edit_message_text("⚠️ Error al cargar minijuegos")


# Y estas son las funciones que manejan los callbacks
async def handle_eliminar_apuesta(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    print(f"Eliminar apuesta llamada")
    # Extraer el ID de la apuesta del callback_data
    apuesta_id = query.data.replace("eliminar0_apuesta_", "")
   
    
    try:
        # Eliminar la apuesta de la base de datos
        resultado = eliminar_apuesta_de_db(apuesta_id)
        
        if resultado:
            await query.edit_message_text(
                f"✅ Apuesta {apuesta_id} eliminada correctamente.",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ Error al eliminar la apuesta {apuesta_id}.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        print(f"Error al eliminar apuesta: {e}")
        await query.edit_message_text(
            f"❌ Error al procesar la eliminación.",
            parse_mode="HTML"
        )

async def handle_eliminar_todas(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Extraer el ID del usuario del callback_data
    user_id = query.data.replace("eliminar0_todas_", "")
    
    try:
        # Eliminar todas las apuestas pendientes del usuario
        resultado = eliminar_todas_apuestas_usuario(user_id)
        
        if resultado:
            await query.edit_message_text(
                f"✅ Todas las apuestas pendientes del usuario {user_id} han sido eliminadas.",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ Error al eliminar las apuestas del usuario {user_id}.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        print(f"Error al eliminar todas las apuestas: {e}")
        await query.edit_message_text(
            f"❌ Error al procesar la eliminación.",
            parse_mode="HTML"
        )

async def get_user_data(update: Update, context: CallbackContext):
    try:
        # Verificación de admin
        user_id = str(update.effective_user.id)
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permisos para usar este comando.")
            return

        # Obtener ID objetivo
        args = context.args
        if not args:
            await update.message.reply_text("Por favor, proporciona un ID de usuario. Ejemplo: /get 123456789")
            return
        target_user_id = args[0]

        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro('usuarios', target_user_id)
        if not usuario_data:
            await update.message.reply_text(f"El usuario con ID {target_user_id} no está registrado.")
            return

        # Obtener datos de bono
        bono_data = obtener_registro('bono_apuesta', target_user_id)
        
        # Obtener datos de mejoras (barco, cañones, velas)
        mejoras_barco = obtener_registro('mejoras', (target_user_id, 'barco'))
        mejoras_caniones = obtener_registro('mejoras', (target_user_id, 'cañones'))
        mejoras_velas = obtener_registro('mejoras', (target_user_id, 'velas'))
        
        # Obtener datos del juego pirata (manejar caso None)
        juego_pirata_data = obtener_registro('juego_pirata', target_user_id)
        
        # Obtener depósitos
        consulta_depositos = "SELECT SUM(amount) FROM depositos WHERE id = ?"
        total_depositado_result = ejecutar_consulta_segura(consulta_depositos, (target_user_id,), obtener_resultados=True)
        total_depositado = float(total_depositado_result[0][0] or 0) if total_depositado_result else 0

        # Obtener apuestas pendientes usando la función mejorada
        apuestas_pendientes = obtener_apuestas_usuario(target_user_id)
        apuestas_pendientes = [a for a in apuestas_pendientes if a.get('estado') in ['⌛Pendiente', '🔚 Finalizado']]

        # Extraer datos del usuario (ajusta índices según tu estructura)
        firstname = usuario_data[1] if len(usuario_data) > 1 else 'No obtenido'
        balance = usuario_data[2] if len(usuario_data) > 2 else 0
        referidos = usuario_data[3] if len(usuario_data) > 3 else 0
        medalla = usuario_data[6] if len(usuario_data) > 6 else 'Sin medalla'

        # Datos de mejoras (niveles de barco, cañones, velas)
        nivel_barco = mejoras_barco[2] if mejoras_barco and len(mejoras_barco) > 2 else 0
        nivel_caniones = mejoras_caniones[2] if mejoras_caniones and len(mejoras_caniones) > 2 else 0
        nivel_velas = mejoras_velas[2] if mejoras_velas and len(mejoras_velas) > 2 else 0

        # Datos del juego pirata (con manejo de None)
        total_piratas = juego_pirata_data[1] if juego_pirata_data and len(juego_pirata_data) > 1 else 0
        total_barriles = juego_pirata_data[2] if juego_pirata_data and len(juego_pirata_data) > 2 else 0
        ganancia_hora = juego_pirata_data[3] if juego_pirata_data and len(juego_pirata_data) > 3 else 0

        # Datos de bonos y rollover (con manejo de None)
        bono = float(bono_data[1] or 0) if bono_data and len(bono_data) > 1 else 0
        rollover_actual = float(bono_data[3] or 0) if bono_data and len(bono_data) > 3 else 0
        rollover_requerido = float(bono_data[2] or 0) if bono_data and len(bono_data) > 2 else 0
        bono_retirable = float(bono_data[4] or 0) if bono_data and len(bono_data) > 4 else 0

        # Cálculo de progreso del rollover
        try:
            porcentaje_progreso = (rollover_actual / rollover_requerido) * 100 if rollover_requerido > 0 else 0.0
        except ZeroDivisionError:
            porcentaje_progreso = 0.0
            
        bloques_llenos = int(porcentaje_progreso // 10)
        barra_progreso = "▓" * bloques_llenos + "░" * (10 - bloques_llenos)
        falta_apostar = max(rollover_requerido - rollover_actual, 0)

        # Construcción del mensaje principal
        namelink = f'<a href="tg://user?id={target_user_id}">{firstname}</a>'
        mensaje = (
            f" <blockquote>ℹ️INFORME COMPLETO</blockquote> \n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ <b>ID:</b> <code>{target_user_id}</code>\n"
            f"▫️ <b>Nombre:</b> {namelink}\n"
            f"▫️ <b>Medalla:</b> {medalla}\n"
            f"▫️ <b>Referidos:</b> {referidos}\n\n"
            
            f" <blockquote>🚢ESTADO DEL BARCO</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"▪ Nivel Barco: {nivel_barco}\n"
            f"▪ Nivel Cañones: {nivel_caniones}\n"
            f"▪ Nivel Velas: {nivel_velas}\n"
            f"▪ Tripulación: {total_piratas} piratas\n"
            f"▪ Barriles: {total_barriles}\n"
            f"▪ Producción/hora: {ganancia_hora:.2f} CUP\n\n"
            
            f" <blockquote>🎰BONOS DE APUESTA</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 Bono de Apuesta: {bono:.2f} CUP\n"
            f"💲 Bono Retirable: {bono_retirable:.2f} CUP\n\n"
            
            f"📊 <b>ROLLOVER</b>\n"
            f"├ Requerido: {rollover_requerido:.2f} CUP\n"
            f"├ Actual: {rollover_actual:.2f} CUP\n"
            f"└ Progreso: [{barra_progreso}] {porcentaje_progreso:.1f}%\n\n"
            f"⚠️ Falta apostar {falta_apostar:.2f} CUP para liberar el bono\n\n"
            
            f" <blockquote>💰FINANZAS</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"▪ Balance actual: {balance:.2f} CUP\n"
            f"▪ Total depositado: {total_depositado:.2f} CUP\n"
            f"▪ Apuestas pendientes: {len(apuestas_pendientes)}\n"
        )

        # Enviar mensaje principal
        await update.message.reply_text(mensaje, parse_mode='HTML')

        # Mostrar apuestas pendientes con botones para eliminar
        if apuestas_pendientes:
            mensaje_apuestas = "🎯 <b>APUESTAS PENDIENTES:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            
            for apuesta in apuestas_pendientes:
                apuesta_id = apuesta.get('id', 'N/A')
                betting_type = apuesta.get('betting', 'Desconocido')
                partido = apuesta.get('partido', 'Sin partido') or 'Sin partido'  # Asegurar que no sea None
                monto = float(apuesta.get('monto', 0))
                estado = apuesta.get('estado', 'Desconocido')
                event_id = apuesta.get('event_id', '')
                cuota = apuesta.get('cuota', 0)
                ganancia = apuesta.get('ganancia', 0)
                tipo_apuesta = apuesta.get('tipo_apuesta', '')

                mensaje_apuestas += (
                    f"▫️ <b>ID:</b> <code>{apuesta_id}</code>\n"
                    f"▫️ <b>Tipo:</b> {betting_type}\n"
                    f"▫️ <b>Partido:</b> {partido}\n"
                    f"▫️ <b>Mercado:</b> {tipo_apuesta}\n"
                    f"▫️ <b>Monto:</b> {monto:.2f} CUP\n"
                    f"▫️ <b>Cuota:</b> {cuota:.2f}\n"
                    f"▫️ <b>Ganancia:</b> {ganancia:.2f} CUP\n"
                    f"▫️ <b>Estado:</b> {estado}\n"
                    f"▫️ <b>Event ID:</b> <code>{event_id}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                )

            # Crear teclado con botones para eliminar apuestas
            keyboard = []
            for apuesta in apuestas_pendientes:
                apuesta_id = apuesta.get('id')
                if apuesta_id:  # Solo agregar si tiene ID
                    partido = apuesta.get('partido') or 'Apuesta'  # Asegurar que no sea None
                    
                    # Manejar caso donde partido podría ser None o vacío
                    if partido and isinstance(partido, str):
                        # Limitar longitud del texto del botón
                        button_text = f"❌ {partido[:15]}..." if len(partido) > 15 else f"❌ {partido}"
                    else:
                        button_text = f"❌ Apuesta {apuesta_id}"
                    
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"eliminar0_apuesta_{apuesta_id}")])
            
            # Añadir botón para eliminar todas
            if keyboard:  # Solo si hay apuestas para eliminar
                keyboard.append([InlineKeyboardButton("🗑️ ELIMINAR TODAS LAS APUESTAS", callback_data=f"eliminar0_todas_{target_user_id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(mensaje_apuestas, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await update.message.reply_text(mensaje_apuestas, parse_mode='HTML')
        else:
            await update.message.reply_text("✅ El usuario no tiene apuestas pendientes.")

    except Exception as e:
        print(f"Error en get_user_data: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text("⛔ Error al obtener datos del usuario")

async def modify_balance(update: Update, context: CallbackContext):
    try:
        admin_id = str(update.effective_user.id)
        if admin_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Sin permisos.")
            return

        # Procesar argumentos
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("ℹ️ Uso: /balance <ID> <cantidad>")
            return

        try:
            target_user_id_str = args[0]
            target_user_id_int = int(target_user_id_str)
            amount = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ ID o cantidad inválidos.")
            return

        # Conectar a SQLite
        DB_FILE = "user_data.db"
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar usuario existente
        c.execute("SELECT Balance, nombre FROM usuarios WHERE id = ?", (target_user_id_str,))
        row = c.fetchone()
        if not row:
            await update.message.reply_text(f"❌ Usuario {target_user_id_str} no registrado.")
            conn.close()
            return

        old_balance, nombre_usuario = row
        new_balance = old_balance + amount

        # Actualizar balance en la DB
        c.execute("UPDATE usuarios SET balance = ? WHERE id = ?", (new_balance, target_user_id_str))
        conn.commit()
        conn.close()

        # Registrar tiempo de modificación
        mod_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Notificar al usuario modificado
        try:
            await context.bot.send_message(
                chat_id=target_user_id_int,
                text=f"📢 <b>Actualización de Balance</b>\n\n"
                     f"• Cambio: <code>{amount:+} CUP</code>\n"
                     f"• Nuevo balance: <code>{new_balance} CUP</code>\n"
                     f"• Fecha: {mod_time}",
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error notificando usuario: {e}")

        # Reporte detallado al administrador principal
        admin_report = (
            f"📊 <b>Reporte de Modificación</b>\n\n"
            f"<b>Administrador:</b>\n"
            f"• ID: <code>{admin_id}</code>\n"
            f"• Nombre: {update.effective_user.full_name}\n\n"
            f"<b>Usuario modificado:</b>\n"
            f"• ID: <code>{target_user_id_str}</code>\n"
            f"• Nombre: {nombre_usuario}\n\n"
            f"<b>Balance:</b>\n"
            f"• Anterior: <code>{old_balance} CUP</code>\n"
            f"• Cambio: <code>{amount:+} CUP</code>\n"
            f"• Nuevo: <code>{new_balance} CUP</code>\n\n"
            f"<b>Fecha:</b> {mod_time}"
        )

        await context.bot.send_message(
            chat_id=7031172659,
            text=admin_report,
            parse_mode='HTML'
        )

        # Confirmación rápida al admin que ejecutó el comando
        await update.message.reply_text(
            f"✅ Balance actualizado\n"
            f"🆔 Usuario: {target_user_id_str}\n"
            f"💰 Nuevo balance: {new_balance} CUP"
        )

    except Exception as e:
        logging.error(f"Error en modify_balance: {e}", exc_info=True)
        await update.message.reply_text("❌ Error crítico al actualizar el balance")
        await context.bot.send_message(
            chat_id=7031172659,
            text=f"⚠️ <b>Error en modify_balance</b>\n\n"
                 f"<code>{str(e)}</code>",
            parse_mode='HTML'
        )



async def modify_leader(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if user_id not in ADMIN_IDS:  
            await update.message.reply_text("❌ Sin permisos.")
            return

        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Uso: /líder <ID usuario> <ID líder>")
            return

        target_user_id_str = args[0]
        new_leader_id = args[1]

        # Conexión DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar que el usuario existe
        c.execute("SELECT 1 FROM usuarios WHERE id = ?", (target_user_id_str,))
        if not c.fetchone():
            await update.message.reply_text(f"❌ Usuario {target_user_id_str} no registrado.")
            conn.close()
            return

        # Actualizar líder
        c.execute("UPDATE usuarios SET lider = ? WHERE id = ?", (new_leader_id, target_user_id_str))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Líder actualizado.\n👤 Usuario: {target_user_id_str}\n🆕 Nuevo líder: {new_leader_id}"
        )

    except Exception as e:
        logging.error(f"Error en modify_leader: {e}", exc_info=True)
        await update.message.reply_text("❌ Error al actualizar el líder.")


async def modificar_bono(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, command_name: str):
    try:
        admin_id = str(update.effective_user.id)
        if admin_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permisos para este comando")
            return

        if len(context.args) != 2:
            await update.message.reply_text(f"⚠️ Uso: /{command_name} <user_id> <monto>")
            return

        target_user = context.args[0]
        amount = context.args[1]
        if not amount.lstrip('-').isdigit():
            await update.message.reply_text("❌ El monto debe ser un número entero")
            return

        amount = int(amount)

        # Conexión DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar usuario en bono_apuesta
        c.execute(f"SELECT {field} FROM bono_apuesta WHERE id = ?", (target_user,))
        row = c.fetchone()
        if not row:
            await update.message.reply_text("❌ Usuario no encontrado")
            conn.close()
            return

        old_value = row[0]
        new_value = max(0, old_value + amount)  # Evitar negativo
        c.execute(f"UPDATE bono_apuesta SET {field} = ? WHERE id = ?", (new_value, target_user))
        conn.commit()

        # Obtener nombre usuario
        c.execute("SELECT nombre FROM usuarios WHERE id = ?", (target_user,))
        user_row = c.fetchone()
        nombre_usuario = user_row[0] if user_row else "Desconocido"
        conn.close()

        await update.message.reply_text(
            f"✅ <b>Bono actualizado</b>\n\n"
            f"👤 <b>Usuario:</b> {nombre_usuario}\n"
            f"🆔 <b>ID:</b> <code>{target_user}</code>\n"
            f"📝 <b>Campo:</b> {field.replace('_', ' ').title()}\n"
            f"📈 <b>Nuevo valor:</b> <code>{new_value} CUP</code>",
            parse_mode='HTML'
        )

        # Reporte admin
        admin_report = (
            f"📊 <b>Reporte de Modificación de Bono</b>\n\n"
            f"<b>Administrador:</b>\n"
            f"• ID: <code>{admin_id}</code>\n"
            f"• Nombre: {update.effective_user.full_name}\n\n"
            f"<b>Usuario modificado:</b>\n"
            f"• ID: <code>{target_user}</code>\n"
            f"• Nombre: {nombre_usuario}\n\n"
            f"<b>Detalles:</b>\n"
            f"• Campo: {field.replace('_', ' ').title()}\n"
            f"• Valor anterior: <code>{old_value} CUP</code>\n"
            f"• Cambio: <code>{amount:+} CUP</code>\n"
            f"• Nuevo valor: <code>{new_value} CUP</code>\n\n"
            f"<b>Comando:</b> /{command_name}\n"
            f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await context.bot.send_message(chat_id=7031172659, text=admin_report, parse_mode='HTML')

        # Notificar al usuario afectado
        try:
            await context.bot.send_message(
                chat_id=int(target_user),
                text=(
                    f"📢 <b>Actualización de Bono</b>\n\n"
                    f"• <b>Tipo:</b> {field.replace('_', ' ').title()}\n"
                    f"• <b>Cambio:</b> <code>{amount:+} CUP</code>\n"
                    f"• <b>Nuevo total:</b> <code>{new_value} CUP</code>\n\n"
                    f"ℹ️ Esta modificación fue realizada por un administrador"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error notificando al usuario {target_user}: {e}")
            await update.message.reply_text("⚠️ No se pudo notificar al usuario")

    except Exception as e:
        logging.error(f"Error en /{command_name}: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ Error procesando el comando")
        await context.bot.send_message(
            chat_id=7031172659,
            text=f"⚠️ <b>Error en {command_name}</b>\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )
# Comandos existentes
async def bono_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await modificar_bono(update, context, "Bono", "bono")

async def rollover_actual_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await modificar_bono(update, context, "Rollover_actual", "rollover_actual")

async def rollover_requerido_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await modificar_bono(update, context, "Rollover_requerido", "rollover_requerido")

# Nuevo comando para modificar Bono_retirable
async def bono_retirable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await modificar_bono(update, context, "Bono_retirable", "bono_retirable")

        
        
# Modificar barriles
async def modify_barriles(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permisos para usar este comando.")
            return

        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Uso correcto: /barriles (ID) (cantidad).")
            return

        target_user_id, amount = args[0], int(args[1])

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar si el usuario tiene registro en juego_pirata
        c.execute("SELECT barriles FROM juego_pirata WHERE id = ?", (target_user_id,))
        row = c.fetchone()
        if not row:
            await update.message.reply_text(f"El usuario con ID {target_user_id} no tiene barriles registrados.")
            conn.close()
            return

        new_barriles = row[0] + amount
        c.execute("UPDATE juego_pirata SET barriles = ? WHERE id = ?", (new_barriles, target_user_id))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Los barriles del usuario {target_user_id} fueron actualizados.\n\n"
            f"🛢️ Cambio: {amount}\n"
            f"🛢️ Nuevos Barriles: {new_barriles}"
        )

        # Notificar al usuario afectado
        try:
            await context.bot.send_message(
                chat_id=int(target_user_id),
                text=(
                    f"✅ Tus barriles fueron actualizados.\n\n"
                    f"🛢️ Cambio: {amount}\n"
                    f"🛢️ Nuevos Barriles: {new_barriles}"
                )
            )
        except Exception as e:
            logging.warning(f"No se pudo notificar al usuario {target_user_id}: {e}")

    except Exception as e:
        logging.error(f"Error en modify_barriles: {e}")
        await update.message.reply_text("Ocurrió un error al actualizar los barriles. Inténtalo nuevamente.")


# Modificar referidos
async def modify_referidos(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permisos para usar este comando.")
            return

        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Uso correcto: /referidos (ID) (cantidad).")
            return

        target_user_id, amount = args[0], int(args[1])

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar que el usuario exista
        c.execute("SELECT referidos FROM usuarios WHERE id = ?", (target_user_id,))
        row = c.fetchone()
        if not row:
            await update.message.reply_text(f"El usuario con ID {target_user_id} no está registrado.")
            conn.close()
            return

        new_referidos = row[0] + amount
        c.execute("UPDATE usuarios SET referidos = ? WHERE id = ?", (new_referidos, target_user_id))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Los referidos del usuario {target_user_id} fueron actualizados.\n\n"
            f"👥 Cambio: {amount}\n"
            f"👥 Nuevos Referidos: {new_referidos}"
        )

    except Exception as e:
        logging.error(f"Error en modify_referidos: {e}")
        await update.message.reply_text("Ocurrió un error al actualizar los referidos. Inténtalo nuevamente.")
@verificar_bloqueo
@marca_tiempo
async def handle_tareas_pagadas(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        user_first_name = update.callback_query.from_user.first_name

        keyboard = [
            [
                InlineKeyboardButton("🔍Ver canales💰", callback_data="ver_tareas_disponibles"),
                InlineKeyboardButton("👨‍💻Agregar canal📢", callback_data="agregar_tarea")
            ],
            [InlineKeyboardButton("📊 Mi ads 📊", callback_data="mis_tareas")],
            [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=f"<b>¡Hola {user_first_name}!</b>\n\n"
                 f"<i>Bienvenido al sistema de tareas automatizado.</i>\n\n"
                 f"💸 En esta sección puedes <b>ganar dinero</b> uniéndote a grupos y canales o "
                 f"<b>promocionar tu propio canal</b>. El sistema es completamente automático y "
                 f"funciona de manera rápida y eficiente. ¡Es muy fácil ganar con nosotros! 💰\n\n"
                 f"<i>¿Qué deseas hacer a continuación?</i>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        # Manejo de errores
        logger.error(f"Error en handle_tareas_pagadas(): {e}")
        await query.edit_message_text("❌ Ocurrió un error al procesar la solicitud.")

@verificar_bloqueo
async def mis_tareas(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        user_id = str(query.from_user.id)
        user_name = query.from_user.username

        with open('user_data.json', 'r') as f:
            data = json.load(f)

        # Verificar si el usuario tiene tareas
        if user_id not in data["tareas"] or not data["tareas"][user_id]:
            await query.answer("❌ No tienes tareas activas.")
            return

        tareas_usuario = data["tareas"][user_id]

        # Crear un mensaje inicial
        mensaje_inicial = "<b>📋 Estas son tus tareas activas:</b>\n\n"
        await query.edit_message_text(
            text=mensaje_inicial,
            parse_mode="HTML"
        )

        # Enviar cada tarea en un mensaje separado
        for tarea_id, tarea in tareas_usuario.items():
            mensaje_tarea = (
                "----------------------------------------------------------------\n"
               
                f"🔹 <b>Tipo:</b> {tarea['Tipo']}\n"
                f"🔹 <b>Canal:</b> {tarea['Nombre_canal']}\n"
                f"🔹 <b>Link:</b> <a href='{tarea['Link_canal']}'>Ir al canal</a>\n"
                f"🔹 <b>Presupuesto:</b> <code>{tarea['Presupuesto']}</code> CUP\n"
                f"🔹 <b>Pago por usuario:</b> <code>{round(tarea['Pago'], 2)}</code> CUP\n"
                f"🔹 <b>Usuarios requeridos:</b> <code>{tarea['UsuariosRequer']}</code>\n"
                f"🔹 <b>Usuarios completados:</b> <code>{len(tarea['Usuarios_completados'])}</code>\n"
                "----------------------------------------------------------------"
            )

            # Enviar la tarea como un mensaje separado
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=mensaje_tarea,
                parse_mode="HTML"
            )

        # Crear los botones para volver al menú principal
        keyboard = [
            [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Estás son todas tus tareas activas",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    except Exception as e:
        
        logger.error(f"Error en mis_tareas(): {e}")
        await query.edit_message_text("❌ Ocurrió un error al procesar la solicitud.")
# Función para iniciar la solicitud de tarea
@verificar_bloqueo
async def agregar_tarea(update: Update, context: CallbackContext):
    try:
        # Paso 1: Solicitar que el usuario reenvíe un mensaje desde su canal
        await update.callback_query.answer()

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            "🔗 <b>Por favor, reenvía un mensaje desde tu canal al bot.</b>\n\n"
            "<i>⚠️ Asegúrate de que el bot sea <b>administrador</b> en el canal que intentas promocionar, es necesario para verificar si los usuarios se unieron.</i>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        context.user_data['estado'] = 'esperando_mensaje_reenviado'
    except Exception as e:
        await update.callback_query.edit_message_text(
            "❌ Ocurrió un error al iniciar la tarea."
        )
        print(f"Error en agregar_tarea: {e}")

# Función para manejar el mensaje reenviado
@verificar_bloqueo
async def handle_forwarded_message(update: Update, context: CallbackContext):
    try:

        # Verificar si el mensaje es reenviado desde un canal
        if not update.message.forward_origin or update.message.forward_origin['type'] != 'channel':
            await update.message.reply_text(
"❌ Por favor, reenvía un mensaje desde un canal.\n\n"
"⚠️ Asegúrate de que el mensaje sea reenviado directamente desde el canal, no copiado y pegado."
)
            return

        # Obtener el ID y el nombre de usuario del canal
        id_canal = update.message.forward_origin['chat']['id']
        nombre_canal = update.message.forward_origin['chat'].username

        # Verificar si el canal tiene un nombre de usuario
        if not nombre_canal:
            await update.message.reply_text(
                "❌ El canal no tiene un nombre de usuario (por ejemplo, @nombre_canal).\n\n"
                "⚠️ Asegúrate de que el canal tenga un nombre de usuario para poder generar el enlace."
            )
            return

        # Generar el enlace del canal
        link_canal = f"https://t.me/{nombre_canal}"

        # Almacenar los datos en el contexto
        context.user_data['link_canal'] = link_canal
        context.user_data['id_canal'] = id_canal

        # Verificar si el bot es administrador del canal
        try:
            bot_member = await context.bot.get_chat_member(chat_id=id_canal, user_id=context.bot.id)

            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    "❌ El bot no es administrador del canal proporcionado.\n\n"
                    "⚠️ Asegúrate de que el bot sea administrador del canal con los permisos necesarios."
                )
                return

            # Solicitar la descripción del canal
            keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "📝 <b>Ahora, por favor envíame una breve descripción sobre qué trata tu canal.</b>\n"
                "<i>💡 Recuerda: Esta descripción será visible para los usuarios que intenten unirse a tu canal.</i>\n\n"
                "<i>🔞 Está prohibido incluir contenido XXX o cualquier tipo de material inapropiado.</i>\n\n"
                "<b>⚠️ La descripción no debe exceder de 20 palabras.</b>",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            context.user_data['estado'] = 'esperando_descripcion'

        except Exception as e:
            await update.message.reply_text(
                "❌ No se pudo verificar si el bot es administrador del canal.\n\n"
                "⚠️ Asegúrate de que el bot esté agregado al canal como administrador con los permisos necesarios."
            )
            print(f"Error en verificación de admin: {e}")

    except Exception as e:
        await update.message.reply_text(
            "❌ Ocurrió un error al procesar el mensaje reenviado.\n\n"
            "⚠️ Asegúrate de reenviar un mensaje directamente desde un canal."
        )
        print(f"Error en handle_forwarded_message: {e}")

@verificar_bloqueo
async def handle_descripcion(update: Update, context: CallbackContext):
    try:
        descripcion = update.message.text
        if len(descripcion.split()) > 20:
            await update.message.reply_text(
                "❌ La descripción no debe exceder de 20 palabras. Por favor, intenta de nuevo."
            )
            return

        context.user_data['descripcion'] = descripcion  # Almacenar descripción
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
    "💵 <b>Ingresa el presupuesto para esta tarea y cuántos usuarios quieres que se unan.</b>\n\n"
    "<i>🔹 Cuanto mayor sea el presupuesto y menor la cantidad de usuarios, mejor será el pago para los usuarios unidos.</i>\n\n"
    "📌 <i>Las tareas se muestran en orden: aquellas con mejor pago aparecerán primero.</i>\n\n"
    "💡<b>El mensaje debe estar en el formato:</b>\n"
    "Presupuesto: (dinero total)\n"
    "Usuarios: (cantidad de usuarios a unirse)",
    parse_mode="HTML",
    reply_markup=reply_markup
)
        context.user_data['estado'] = 'esperando_presupuesto'

    except Exception as e:
        await update.message.reply_text(
            "❌ Ocurrió un error al guardar la descripción."
        )
        print(f"Error en handle_descripcion: {e}")

async def handle_presupuesto(update: Update, context: CallbackContext):
    try:
        datos = update.message.text.splitlines()
        if len(datos) != 2:
            await update.message.reply_text(
                "❌ El formato no es correcto. Asegúrate de usar el formato:\n\n"
                "Presupuesto: <cantidad>\nUsuarios: <cantidad>\n\n 🔃 Vuelve a intentarlo."
            )
            return

        try:
            # Extraer y validar presupuesto
            presupuesto = int(datos[0].split(":")[1].strip())

            # Extraer y validar usuarios requeridos
            usuarios_requeridos = int(datos[1].split(":")[1].strip())
            if usuarios_requeridos <= 0:
                await update.message.reply_text("❌ El número de usuarios requeridos debe ser mayor a 0.")
                return
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Ocurrió un error al procesar los datos. Asegúrate de usar números válidos en el formato:\n\n"
                "Presupuesto: <cantidad>\nUsuarios: <cantidad>"
            )
            return

        # Validar el pago mínimo por usuario (debe ser al menos 1 CUP)
        pago_por_usuario = presupuesto / usuarios_requeridos

        if pago_por_usuario < 1:
            usuarios_sugeridos = presupuesto // 1  # Para que el pago mínimo sea 1 CUP
            await update.message.reply_text(
    f"❌ El pago por usuario es muy bajo (<b>{pago_por_usuario:.2f} CUP</b>).\n\n"
    f"🔹 Para que cada usuario reciba al menos <b>1 CUP</b>, podrías establecer <b>{usuarios_sugeridos} usuarios</b> en lugar de <b>{usuarios_requeridos}</b>.\n\n"
    "🔃 Intenta nuevamente con un número de usuarios diferente.",
    parse_mode="HTML"
)
        context.user_data['presupuesto'] = presupuesto
        context.user_data['usuarios_requeridos'] = usuarios_requeridos

        # Recuperar otros datos del contexto
        link_canal = context.user_data.get('link_canal', '')
        descripcion = context.user_data.get('descripcion', '')

        if not link_canal or not descripcion:
            await update.message.reply_text("❌ Faltan datos del canal o descripción. Vuelve a intentarlo.")
            return

        confirm_message = (
            f"<blockquote>✅Confirmar tarea</blockquote>\n\n"
            f"🔗 <b>Canal:</b> {link_canal}\n"
            f"📝 <b>Descripción:</b> {descripcion}\n"
            f"💰 <b>Presupuesto:</b> <code>{presupuesto}</code> CUP\n"
            f"👥 <b>Usuarios requeridos:</b> <code>{usuarios_requeridos}</code>\n"
            f"💵 <b>Pago por usuario:</b> <code>{pago_por_usuario:.2f}</code> CUP"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_tarea")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            confirm_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Ocurrió un error al guardar el presupuesto y usuarios requeridos."
        )
        print(f"Error en handle_presupuesto: {e}")


async def confirmar_tarea(update, context):
    
    
    try:
        user_id = str(update.callback_query.from_user.id)
        user_name = update.callback_query.from_user.username

        async with lock_data:
            data = await load_data()

            # Verificar si el usuario está registrado
            if user_id not in data["usuarios"]:
                keyboard = [[InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.message.reply_text(
                    "❌ <b>No estás registrado</b>\n\nUsa /start para registrarte.", 
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return

            user_balance = data["usuarios"][user_id].get("Balance", 0)

            # Recuperar datos del contexto
            link_canal = context.user_data.get("link_canal", "")
            id_canal = context.user_data.get("id_canal", "")
            descripcion = context.user_data.get("descripcion", "")
            presupuesto = context.user_data.get("presupuesto", 0)
            usuarios_requeridos = context.user_data.get("usuarios_requeridos", 0)

            if not link_canal or not id_canal or not descripcion:
                await update.callback_query.answer("❌ Faltan datos para confirmar la tarea.", show_alert=True)
                return

            try:
                presupuesto = int(presupuesto)
            except ValueError:
                await update.callback_query.answer("❌ El presupuesto debe ser un número válido.", show_alert=True)
                return       

            if user_balance < presupuesto:
                await update.callback_query.answer(
                    f"❌ Saldo insuficiente\n\nNecesitas: {presupuesto} CUP\nTienes: {user_balance} CUP", 
                    show_alert=True
                )
                return

            if usuarios_requeridos <= 0:
                await update.callback_query.answer("❌ Se requieren al menos 1 participante.", show_alert=True)
                return

            # Verificar el canal/grupo
            try:
                chat = await context.bot.get_chat(chat_id=id_canal)
                tipo_chat = chat.type
                tipo = "Canal" if tipo_chat == "channel" else "Grupo" if tipo_chat in ["group", "supergroup"] else "Desconocido"

                bot_member = await context.bot.get_chat_member(chat_id=id_canal, user_id=context.bot.id)
                if bot_member.status not in ["administrator", "creator"]:
                    await update.callback_query.answer("❌ El bot no es administrador.", show_alert=True)
                    return
            except Exception as e:
                print(f"Error verificando canal: {e}")
                await update.callback_query.answer("❌ Error verificando el canal/grupo.", show_alert=True)
                return

            # Cálculos financieros
            pago_bruto = presupuesto / usuarios_requeridos
            pago_neto = round(pago_bruto - (pago_bruto * 0.10), 2)

            # Actualizar saldo
            data["usuarios"][user_id]["Balance"] = user_balance - presupuesto

            # Crear tarea
            tarea_id = str(uuid.uuid4())
            nueva_tarea = {
                "Tipo": tipo,
                "Creador": user_id,
                "Detalles": descripcion,
                "Nombre_canal": chat.title,
                "Link_canal": link_canal,
                "id_canal": id_canal,
                "Presupuesto": presupuesto,
                "Pago": pago_neto,
                "UsuariosRequer": usuarios_requeridos,
                "Usuarios_completados": []
            }

            # Guardar tarea
            if "tareas" not in data:
                data["tareas"] = {}
            if user_id not in data["tareas"]:
                data["tareas"][user_id] = {}
            data["tareas"][user_id][tarea_id] = nueva_tarea

            

        # Mensaje al administrador (mejorado)
        mensaje_admin = f"""
📢 <b>NUEVA TAREA REGISTRADA</b>

┌ 🏷️ <b>Tipo:</b> {tipo}
├ 📝 <b>Descripción:</b> 
│  └ {descripcion}
├ 🔗 <b>Canal/Grupo:</b> 
│  ├ {chat.title}
│  └ {link_canal}
├ 💰 <b>Presupuesto:</b> <code>{presupuesto}</code> CUP
├ 👥 <b>Usuarios requeridos:</b> {usuarios_requeridos}
└ 💸 <b>Pago por usuario:</b> <code>{pago_neto}</code> CUP

👤 <b>Creador:</b> @{user_name} (<code>{user_id}</code>)
"""
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=mensaje_admin,
            parse_mode="HTML"
        )

        # Mensaje al usuario (mejorado)
        mensaje_usuario = f"""
✅ <b>TAREA CONFIRMADA</b>

┌ 🏷️ <b>Tipo:</b> {tipo}
├ 📝 <b>Descripción:</b> 
│  └ {descripcion}
├ 🔗 <b>Canal/Grupo:</b> 
│  ├ {chat.title}
│  └ {link_canal}
├ 💰 <b>Presupuesto:</b> <code>{presupuesto}</code> CUP
├ 👥 <b>Usuarios requeridos:</b> {usuarios_requeridos}
└ 💸 <b>Pago por usuario:</b> <code>{pago_neto}</code> CUP

💰 <b>Nuevo saldo:</b> <code>{user_balance - presupuesto}</code> CUP
"""
        keyboard = [[InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_principal")]]
        await update.callback_query.message.edit_text(
            text=mensaje_usuario,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error en confirmar_tarea: {str(e)}")
        await update.callback_query.answer(
            "⚠️ Error al procesar la tarea. Intente nuevamente.",
            show_alert=True
        )

async def is_user_in_channel(bot, user_id, id_canal):
    try:
        chat_member = await bot.get_chat_member(id_canal, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False


# Función para ver tareas disponibles
async def ver_tareas_disponibles(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()  # Responde a la interacción del usuario

        user_id = str(query.from_user.id)  # Obtener el ID del usuario
        user_firstname = query.from_user.first_name  # Obtener el nombre

        with open('user_data.json', 'r') as f:  
            data = json.load(f)  

        tareas_disponibles = {}  
        for creador_id, tareas in data.get("tareas", {}).items():  
            tareas_disponibles.update(tareas)  

        if not tareas_disponibles:  
            await context.bot.send_message(  
                chat_id=update.effective_chat.id,  
                text="❌ No hay tareas disponibles en este momento, vuelve más tarde."  
            )  
            return  

        tareas_filtradas = {  
            tarea_id: tarea  
            for tarea_id, tarea in tareas_disponibles.items()  
            if user_id not in tarea.get("Usuarios_completados", [])  
        }  

        if not tareas_filtradas:  
            await context.bot.send_message(  
                chat_id=update.effective_chat.id,  
                text="😔 ¡Has completado todas las tareas disponibles! Vuelve mas tarde."  
            )  
            return  

        # Ordenar las tareas por el pago  
        tareas_ordenadas = sorted(tareas_filtradas.items(), key=lambda x: x[1].get("Pago", 0), reverse=True)  

        # Mostrar la primera tarea disponible
        tarea_id, tarea = tareas_ordenadas[0]  # Tomar la primera tarea
        tipo = tarea.get("Tipo", "Desconocido")  
        nombre_canal = tarea.get("Nombre_canal", "Desconocido")  
        link_canal = tarea.get("Link_canal", "")  
        descripcion = tarea.get("Detalles", "Descripción no disponible")  
        pago = tarea.get("Pago", 0)  

        mensaje = f"🔹 <b>Tipo:</b> {tipo}\n"  
        mensaje += f"🔹 <b>Canal:</b> {nombre_canal}\n"  
        mensaje += f"🔹 <b>Descripción:</b> {descripcion}\n\n"  
        mensaje += f"🔹 <b>Pago por unirte:</b> {round(pago, 2)} CUP\n"  

        # Verificar si el link al canal está vacío  
        if link_canal:                  
            keyboard = [  
                [InlineKeyboardButton("🔗Ir al canal", url=link_canal)],    
                [  
                    InlineKeyboardButton("⏭️ Omitir", callback_data=f"omitir_{tarea_id}"),  
                    InlineKeyboardButton("✅ Completado", callback_data=f"verificar_{tarea_id}")  
                ],    
                [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_principal")]    
            ]  
        else:
            keyboard = [  
                [InlineKeyboardButton("❌ Omitir", callback_data=f"omitir_{tarea_id}")],  
                [InlineKeyboardButton("✅ Verificar", callback_data=f"verificar_{tarea_id}")],  
                [InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")]  
            ]  

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Enviar el mensaje con los detalles de la tarea
        await context.bot.send_message(  
            chat_id=update.effective_chat.id,  
            text=mensaje,  
            parse_mode="HTML",  
            reply_markup=reply_markup  
        )  

    except Exception as e:  
        logger.error(f"Error en ver_tareas_disponibles(): {e}")  
        await context.bot.send_message(  
            chat_id=update.effective_chat.id,  
            text="❌ Ocurrió un error al procesar la solicitud."  
        )


async def cargar_datos_tareas():
    
    async with lock_data:
        try:
            with open('user_data.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"usuarios": {}, "tareas": {}}

async def guardar_datos_tareas(data):
    """Guarda los datos en user_data.json de manera segura."""
    async with lock_data:
        with open('user_data.json', 'w') as f:
            json.dump(data, f, indent=4)
            
async def verificar_tarea(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()  # Responder a la interacción del usuario

        user_id = str(query.from_user.id)
        tarea_id = query.data.split("_")[1]

        # Cargar datos de manera segura
        data = await cargar_datos_tareas()

        # Buscar la tarea en el JSON
        tarea = None
        creador_id = None
        for creador, tareas in data.get("tareas", {}).items():
            if tarea_id in tareas:
                tarea = tareas[tarea_id]
                creador_id = creador
                break

        if not tarea:
            print(f"No se encontró la tarea {tarea_id}")
            await query.answer("❌ No se pudo encontrar la tarea.")
            return

        id_canal = tarea.get("id_canal")
        nombre_canal = tarea.get("Nombre_canal", "Canal desconocido")
        usuarios_requeridos = int(tarea.get("UsuariosRequer", 0))  # Asegúrate de usar la clave correcta

        

        # Si el usuario ya completó la tarea, enviar mensaje y salir
        if user_id in tarea.get("Usuarios_completados", []):
            
            await query.answer("⚠️ Ya has completado esta tarea.")
            return

        # Verificar si el usuario está en el canal
        bot = context.bot
        try:
            chat_member = await bot.get_chat_member(id_canal, user_id)
            print(f"Estado del usuario en el canal: {chat_member.status}")

            # Verificar si el usuario es miembro, administrador o creador del canal
            if chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                # Agregar usuario a la lista de completados
                tarea.setdefault("Usuarios_completados", []).append(user_id)

                # Pagar solo si es la primera vez que completa la tarea
                pago_tarea = tarea.get("Pago", 0)
                user_data = data["usuarios"].setdefault(user_id, {})
                user_data["Balance"] = user_data.get("Balance", 0) + pago_tarea

                # Guardar los cambios en el archivo JSON
                await guardar_datos_tareas(data)

                # Notificar al usuario sobre el pago recibido
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ <b>Tarea Completada</b>\n\n💰<b>Pago recibido:</b> <code>{round(pago_tarea, 2)}</code> CUP!",
                    parse_mode="HTML"
                )

                # Notificar en el grupo GROUP_REGISTRO que un usuario completó la tarea
                nombre_usuario = user_data.get("Nombre", "Usuario desconocido")
                nuevo_balance = user_data["Balance"]
                mensaje_usuario_completo = (
                    f"📝 <b>Usuario completó una tarea:</b>\n\n"
                    f"👤 <b>Usuario:</b> {nombre_usuario}\n"
                    f"💰 <b>Pago recibido:</b> <code>{round(pago_tarea, 2)}</code> CUP\n"
                    f"💳 <b>Nuevo balance:</b> <code>{round(nuevo_balance, 2)}</code> CUP"
                )
                await context.bot.send_message(
                    chat_id=REGISTRO_MINIJUEGOS,  # Reemplaza con el ID del grupo
                    text=mensaje_usuario_completo,
                    parse_mode="HTML"
                )

                # Verificar si la tarea ha sido completada
                if len(tarea["Usuarios_completados"]) >= usuarios_requeridos:
                    print(f"La tarea {tarea_id} ha sido completada por {len(tarea['Usuarios_completados'])} usuarios.")
                    # Notificar al creador de la tarea
                    mensaje_completado = (
                        f"🎯 <b>¡Tu tarea ha sido completada!</b>\n\n"
                        f"📌 <b>Canal:</b> {nombre_canal}\n"
                        f"👥 <b>Usuarios requeridos:</b> {usuarios_requeridos}\n"
                        f"✅ <b>Usuarios que se unieron:</b> {len(tarea['Usuarios_completados'])}\n\n"
                        f"📣 <b>La tarea ha sido eliminada.</b>"
                    )
                    await context.bot.send_message(
                        chat_id=creador_id,
                        text=mensaje_completado,
                        parse_mode="HTML"
                    )

                    # Notificar en el grupo GROUP_REGISTRO que la tarea fue completada y eliminada
                    presupuesto_tarea = tarea.get("Presupuesto", 0)
                    mensaje_tarea_completada = (
                        f"🎉 <b>Tarea completada y eliminada:</b>\n\n"
                        f"📌 <b>Tarea:</b> {tarea.get('Nombre_canal', 'Tarea desconocida')}\n"
                        f"👥 <b>Usuarios que la completaron:</b> {len(tarea['Usuarios_completados'])}\n"
                        f"💰 <b>Presupuesto:</b> <code>{round(presupuesto_tarea, 2)}</code> CUP"
                    )
                    await context.bot.send_message(
                        chat_id=GROUP_REGISTRO,  # Reemplaza con el ID del grupo
                        text=mensaje_tarea_completada,
                        parse_mode="HTML"
                    )

                    # Eliminar la tarea del JSON
                    try:
                        if creador_id in data["tareas"] and tarea_id in data["tareas"][creador_id]:
                            del data["tareas"][creador_id][tarea_id]
                            print(f"Tarea {tarea_id} eliminada del creador {creador_id}.")
                        else:
                            print(f"No se pudo encontrar la tarea {tarea_id} en el JSON.")
                    except KeyError as e:
                        print(f"Error al eliminar la tarea: {e}")

                    # Guardar los cambios en el archivo JSON
                    await guardar_datos_tareas(data)

                # Mostrar la siguiente tarea disponible
                await ver_tareas_disponibles(update, context)

            else:
                print(f"El usuario {user_id} no es miembro del canal {id_canal}.")
                await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text="❌ No te has unido al canal. \n\n🔗 Únete al canal y vuelve a intentarlo."
)

        except Exception as e:
            logger.error(f"Error al verificar el canal: {e}")

    except Exception as e:
        logger.error(f"Error en verificar_tarea(): {e}")
        await query.edit_message_text("❌ Ocurrió un error al procesar la solicitud.")
        
async def omitir_tarea(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()  # Responder a la interacción del usuario

        user_id = str(query.from_user.id)
        tarea_id = query.data.split("_")[1]
        
        print(f"Usuario ID: {user_id}, Tarea ID: {tarea_id}")  # Depuración

        # Cargar los datos del JSON para verificar que la tarea exista
        with open('user_data.json', 'r') as f:
            data = json.load(f)

        # Buscar la tarea en el JSON
        tarea = None
        for creador_id, tareas in data.get("tareas", {}).items():
            if tarea_id in tareas:
                tarea = tareas[tarea_id]
                break

        if not tarea:
            await query.answer("❌ No se pudo encontrar la tarea.")
            print("La tarea no fue encontrada en el JSON.")
            return

        # Guardar la tarea omitida en el contexto del usuario
        if "Tareas_omitidas" not in context.user_data:
            context.user_data["Tareas_omitidas"] = []

        if tarea_id not in context.user_data["Tareas_omitidas"]:
            context.user_data["Tareas_omitidas"].append(tarea_id)
            print(f"Tarea {tarea_id} omitida para el usuario {user_id}.")  # Depuración
        else:
            print(f"La tarea {tarea_id} ya estaba omitida para el usuario {user_id}.")  # Depuración

        # Notificar al usuario que la tarea fue omitida
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Has omitido esta tarea. No se te mostrará nuevamente.",
            parse_mode="HTML"
        )

        # Mostrar la siguiente tarea disponible
        await ver_tareas_disponibles(update, context)

    except Exception as e:
        logger.error(f"Error en omitir_tarea(): {e}")
        await query.edit_message_text("❌ Ocurrió un error al omitir la tarea.")
        print(f"Error en omitir_tarea(): {e}")  # Depuración
    
# Comando /resumentareas
async def resumen_tareas(update: Update, context: CallbackContext):
    try:
        user_id = str(update.message.from_user.id)

        # Verificar si el usuario es administrador
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permisos para usar este comando.")
            return

        # Cargar los datos desde el archivo JSON
        with open('user_data.json', 'r') as f:
            data = json.load(f)

        # Verificar si hay tareas activas
        if not data["tareas"]:
            await update.message.reply_text("❌ No hay tareas activas.")
            return

        # Crear un mensaje inicial
        await update.message.reply_text("📋 <b>Resumen de todas las tareas activas:</b>\n\n", parse_mode="HTML")

        # Recorrer todas las tareas de todos los usuarios
        for user_id, tareas_usuario in data["tareas"].items():
            for tarea_id, tarea in tareas_usuario.items():
                mensaje_tarea = (
                    "----------------------------------------------------------------\n"
                    f"<b>📌 Tarea #{tarea_id}:</b>\n"
                    f"🔹 <b>Usuario:</b> {user_id}\n"
                    f"🔹 <b>Tipo:</b> {tarea['Tipo']}\n"
                    f"🔹 <b>Canal:</b> {tarea['Nombre_canal']}\n"
                    f"🔹 <b>Link:</b> <a href='{tarea['Link_canal']}'>Ir al canal</a>\n"
                    f"🔹 <b>Presupuesto:</b> {tarea['Presupuesto']} CUP\n"
                    f"🔹 <b>Pago por usuario:</b> {round(tarea['Pago'], 2)} CUP\n"
                    f"🔹 <b>Usuarios requeridos:</b> {tarea['UsuariosRequer']}\n"
                    f"🔹 <b>Usuarios completados:</b> {len(tarea['Usuarios_completados'])}\n"
                    "----------------------------------------------------------------"
                )

                # Enviar la tarea como un mensaje separado
                await update.message.reply_text(mensaje_tarea, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error en resumen_tareas: {e}")
        await update.message.reply_text("❌ Ocurrió un error al procesar el comando.")

# Comando /killtarea (ID de la tarea)
async def kill_tarea(update: Update, context: CallbackContext):
    try:
        user_id = str(update.message.from_user.id)

        # Verificar si el usuario es administrador
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permisos para usar este comando.")
            return

        # Obtener el ID de la tarea desde el comando
        if not context.args:
            await update.message.reply_text("❌ Debes proporcionar el ID de la tarea. Uso: /killtarea <ID de la tarea>")
            return

        tarea_id = context.args[0]

        # Cargar los datos desde el archivo JSON
        with open('user_data.json', 'r') as f:
            data = json.load(f)

        # Buscar y eliminar la tarea
        tarea_encontrada = False
        for user_id, tareas_usuario in data["tareas"].items():
            if tarea_id in tareas_usuario:
                del tareas_usuario[tarea_id]
                tarea_encontrada = True
                break

        if not tarea_encontrada:
            await update.message.reply_text(f"❌ No se encontró ninguna tarea con el ID {tarea_id}.")
            return

        # Guardar los cambios en el archivo JSON
      

        await update.message.reply_text(f"✅ Tarea #{tarea_id} eliminada correctamente.")

    except Exception as e:
        logger.error(f"Error en kill_tarea: {e}")
        await update.message.reply_text("❌ Ocurrió un error al procesar el comando.")


@marca_tiempo
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Determinar usuario y método
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = str(query.from_user.id)
            payment_method = query.data  # CallbackQuery
        else:
            user_id = str(update.message.from_user.id)
            payment_method = None

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar si tiene teléfono registrado
        c.execute("SELECT telefono FROM depositos WHERE id = ?", (user_id,))
        row = c.fetchone()

        if row and row[0]:  # Tiene teléfono
            telefono = row[0]
            if payment_method:
                context.user_data['payment_method'] = payment_method
                context.user_data['payment_time'] = tm.time()
                context.user_data['numero_telefono'] = telefono

                logger.info(f"Usuario {update.effective_user.full_name} seleccionó método: {payment_method}")

                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("MI TRANSFER (bolsa)", callback_data="mi_transfer")],
                    [InlineKeyboardButton("BPA 💳", callback_data="bpa"), InlineKeyboardButton("BANDEC 💳", callback_data="bandec")],
                    [InlineKeyboardButton("SALDO MOVIL 📲", callback_data="saldo_movil")],
                    [InlineKeyboardButton("BANCA REMOTA 🍏", callback_data="banca"), InlineKeyboardButton("MLC 🪪", callback_data="mlc")],
                    [InlineKeyboardButton("METRO 💳", callback_data="metro"), InlineKeyboardButton("ENZONA 💳", callback_data="enzona")],
                    [InlineKeyboardButton("CRIPTOMONEDAS 🪙", callback_data="criptomonedas")],
                    [InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")]
                ])

                await query.edit_message_text(
                    text=(
                        f"<b>🚀 Sistema de pagos 100% automático</b>\n\n"
                        f"<b>💳 VÍAS DE DEPÓSITO AUTOMÁTICAS:</b>\n"
                        f"<code>• BPA </code>\n"
                        f"<code>• BANDEC </code>\n"
                        f"<code>• METROPOLITANO</code>\n"
                        f"<code>• MLC </code>\n"
                        f"<code>• ENZONA</code>\n"
                        f"<code>• SALDO MÓVIL (+30%) </code>\n"
                        f"<code>• MI TRANSFER (bolsa)</code>\n\n"
                        f"<b>⚡ CARACTERÍSTICAS:</b>\n"
                        f"▸ Verificación <b>instantánea</b> (2-5 min)\n"
                        f"▸ Procesamiento <b>24/7</b>\n"
                        f"▸ <b>0% intervención</b> de administración\n"
                        f"▸ Tecnología <b>Blockchain</b> integrada\n\n"
                        f"<b>👇 SELECCIONA TU MÉTODO DE PAGO:</b>"
                    ),
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                conn.close()
                return

        # Si no tiene teléfono registrado o primer acceso
        context.user_data['estado'] = 'registrando_telefono'
        await context.bot.send_message(
            chat_id=user_id,
            text="📱 Por favor ingresa tu número de teléfono para depósitos automáticos 💫 (ej: 55512345):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancelar", callback_data="show_balance")]
            ])
        )
        conn.close()

    except Exception as e:
        logger.error(f"Error en deposit(): {e}")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Ocurrió un error al iniciar el depósito."
            )
        except Exception:
            pass
        
async def registrar_telefono_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Esto evita el "reloj de carga" en el botón
    
    user_id = query.from_user.id
    context.user_data['estado'] = 'registrando_telefono'
    
    try:
        # Editar el mensaje existente en lugar de enviar uno nuevo
        await query.edit_message_text(
            text="📱 Por favor ingresa tu número de teléfono, se usará para depósitos automáticos 💫 (ej: 55512345):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancelar", callback_data="show_balance")]
            ])
        )
    except Exception as e:
        logger.error(f"Error al editar mensaje para registrar teléfono: {str(e)}")
        # Si falla la edición, enviar un nuevo mensaje como fallback
        await context.bot.send_message(
            chat_id=user_id,
            text="📱 Por favor ingresa tu número de teléfono, se usará para depósitos automáticos 💫 (ej: 55512345):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancelar", callback_data="show_balance")]
            ])
        )        

# Registrar teléfono del usuario en la DB
import sqlite3

# Registrar teléfono del usuario en la DB
async def registrar_telefono(update, context):
    try:
        user_id = str(update.message.from_user.id)
        telefono = update.message.text.strip()
        
        # Validar formato del teléfono
        if not telefono.isdigit() or len(telefono) not in (8, 9):
            await update.message.reply_text(
                "❌ Formato inválido. Ingresa un número de 8 dígitos\n"
                "Ejemplo: 55512345"
            )
            return

        # Registrar teléfono en DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Verificar si existe el registro
        c.execute("SELECT id FROM depositos WHERE id = ?", (user_id,))
        if c.fetchone():
            c.execute("UPDATE depositos SET telefono = ? WHERE id = ?", (telefono, user_id))
        else:
            c.execute(
                "INSERT INTO depositos (id, nombre, telefono, Payment, Amount, TotalDeposit) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, update.message.from_user.full_name, telefono, 0, 0, 0)
            )

        conn.commit()
        conn.close()

        await update.message.reply_text("✅ Teléfono registrado correctamente.")
        context.user_data['estado'] = 'none'

    except Exception as e:
        logger.error(f"Error en registrar_telefono(): {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al registrar tu teléfono. Por favor intenta nuevamente."
        )


# Confirmar datos del depósito y mostrar instrucciones
async def confirmar_datos_deposito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.callback_query:
            logger.error("confirmar_datos_deposito llamado sin callback_query")
            return

        query = update.callback_query
        await query.answer()
        metodo = query.data  # Extrae el método de pago
        user_id = str(update.effective_user.id)

        # Guardar el método en context.user_data
        context.user_data['metodo'] = metodo

        # Obtener el número de teléfono desde DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT telefono FROM depositos WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()

        if not row or not row[0]:
            await query.edit_message_text("❌ No se encontró el número de teléfono asociado a tu cuenta")
            return

        numero_telefono = row[0]
        context.user_data['numero_telefono'] = numero_telefono

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Verificar transferencia", callback_data="verificar_deposito")]
        ])

        await query.edit_message_text(
            text=(
                f"{TEXTOS_METODOS[metodo]['nombre']}\n\n"
                f"<pre>📋 INSTRUCCIONES DE DEPÓSITO</pre>\n\n"
                f"<b>🏦 Método:</b> {TEXTOS_METODOS[metodo]['nombre'].replace('<pre>', '').replace('</pre>', '')}\n"
                f"<b>📱 Tu teléfono asociado:</b> <code>{numero_telefono}</code>\n\n"
                f"{TEXTOS_METODOS[metodo]['detalle_cuenta']}\n\n"
                f"<i>ℹ️ {TEXTOS_METODOS[metodo]['instrucciones']}</i>\n\n"
                f"<i>⚠️ La verificación es automática (2-5 minutos según los mensajes de ETECSA)</i>\n\n"
                f"<i>🔹 {TEXTOS_METODOS[metodo]['nota']}</i>"
            ),
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except KeyError as e:
        logger.error(f"Error en confirmar_datos_deposito (faltan datos): {e}")
        await query.edit_message_text("❌ Error: Método de pago no reconocido")
    except Exception as e:
        logger.error(f"Error en confirmar_datos_deposito: {e}")
        await query.edit_message_text("❌ Ocurrió un error al confirmar el depósito")
# Confirmar datos del depósito y mostrar instrucciones
async def confirmar_datos_deposito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.callback_query:
            logger.error("confirmar_datos_deposito llamado sin callback_query")
            return

        query = update.callback_query
        await query.answer()
        metodo = query.data  # Extrae el método de pago
        user_id = str(update.effective_user.id)

        # Guardar el método en context.user_data
        context.user_data['metodo'] = metodo

        # Obtener el número de teléfono desde DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT telefono FROM depositos WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()

        if not row or not row[0]:
            await query.edit_message_text("❌ No se encontró el número de teléfono asociado a tu cuenta")
            return

        numero_telefono = row[0]
        context.user_data['numero_telefono'] = numero_telefono

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Verificar transferencia", callback_data="verificar_deposito")]
        ])

        await query.edit_message_text(
            text=(
                f"{TEXTOS_METODOS[metodo]['nombre']}\n\n"
                f"<pre>📋 INSTRUCCIONES DE DEPÓSITO</pre>\n\n"
                f"<b>🏦 Método:</b> {TEXTOS_METODOS[metodo]['nombre'].replace('<pre>', '').replace('</pre>', '')}\n"
                f"<b>📱 Tu teléfono asociado:</b> <code>{numero_telefono}</code>\n\n"
                f"{TEXTOS_METODOS[metodo]['detalle_cuenta']}\n\n"
                f"<i>ℹ️ {TEXTOS_METODOS[metodo]['instrucciones']}</i>\n\n"
                f"<i>⚠️ La verificación es automática (2-5 minutos según los mensajes de ETECSA)</i>\n\n"
                f"<i>🔹 {TEXTOS_METODOS[metodo]['nota']}</i>"
            ),
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except KeyError as e:
        logger.error(f"Error en confirmar_datos_deposito (faltan datos): {e}")
        await query.edit_message_text("❌ Error: Método de pago no reconocido")
    except Exception as e:
        logger.error(f"Error en confirmar_datos_deposito: {e}")
        await query.edit_message_text("❌ Ocurrió un error al confirmar el depósito")
# Bloqueos
lock_depositos = asyncio.Lock()

# --------------------------
# FUNCIONES DE NOTIFICACIÓN
# --------------------------


async def notificar_verificacion_fallida(query, user_data):
    try:
        # Obtenemos los datos con manejo seguro de errores
        metodo_pago = user_data.get('metodo', 'método desconocido')
        telefono = user_data.get('numero_telefono', 'N/A')
        
        # Obtenemos el nombre del método de pago con manejo seguro
        nombre_metodo = TEXTOS_METODOS.get(metodo_pago, {}).get('nombre', metodo_pago)

        await query.edit_message_text(
            text=f" <pre>😔 No se encontró el depósito</pre>\n\n"
                 f"<b>⁉️¿Que pudo ocurrir? Verifica:</b>\n\n"
                 
                 f"•📲 Que usaste el teléfono: <code>{telefono}</code> para realizar la operación.\n\n"           
                 f"• 🪙 Que completaste la transferencia por {nombre_metodo}\n\n"
                 
                 f"• ⏳Puede que la notificación de ETECSA  tarde en confirmar, la transacción depende de ello.\n\n"                
                 f"• 😁 Que no hallas transferido o hallas simulado un depósito falzo.\n\n"
                 
                  f"• No marcaste la casilla en la app para que el destinatario reciba el número de teléfono del titular.\n\n"                         
                                  
                 f"<pre>🔄 Intenta nuevamente o contacta soporte.</pre>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error en notificar_verificacion_fallida: {e}")
        await query.edit_message_text(
            text="⚠️ <b>Error al verificar el depósito</b>\n\n"
                 "Por favor intenta nuevamente o contacta soporte.",
            parse_mode='HTML'
        )



async def notificar_error_verificacion(query, mensaje: str):
    await query.edit_message_text(
        text=f"⚠️ <b>Error en verificación</b>\n\n{mensaje}\n\nPor favor intenta más tarde.",
        parse_mode='HTML'
    )


async def notificar_verificacion_exitosa(query, context, monto_verificado):
    """Notificación mejorada al usuario con formato profesional"""
    user_id = str(query.from_user.id)
    bono = round(float(monto_verificado) * 0.20, 2)  # 20% de bono
    rollover = round(float(monto_verificado) * 0.40, 2)  # 40% de rollover
    
    try:
        # Obtener datos desde la base de datos
        usuario_data = obtener_registro('usuarios', user_id)
        deposito_data = obtener_registro('depositos', user_id)
        
        if usuario_data:
            # Suponiendo estructura: (id, nombre, balance, referidos, lider, total_ganado_ref, medalla, ...)
            nuevo_balance = usuario_data[2] if len(usuario_data) > 2 else 0  # Índice 2: balance
        else:
            nuevo_balance = 0
            
        if deposito_data:
            # Suponiendo estructura: (id, nombre, payment, amount, total_deposit, ultimo_deposito, ...)
            total_depositado = deposito_data[4] if len(deposito_data) > 4 else 0  # Índice 4: total_deposit
        else:
            total_depositado = 0
            
    except Exception as e:
        logger.error(f"Error obteniendo datos del usuario: {e}")
        nuevo_balance = 0
        total_depositado = 0
    
    # Formateamos números con separadores de miles
    monto_formateado = f"{float(monto_verificado):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    bono_formateado = f"{bono:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    balance_formateado = f"{float(nuevo_balance):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    total_depositado_formateado = f"{float(total_depositado):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    rollover_formateado = f"{rollover:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    mensaje = (
        " <pre>🏦DEPÓSITO VERIFICADO CON ÉXITO🏦</pre> \n\n"
        "✅ <b>Transacción completada</b>\n\n"
        "💳 <b>Detalles de la transacción:</b>\n"
        f"┣ <b>Monto depositado:</b> <code>{monto_formateado}</code> CUP\n"
        f"┗ <b>Bono recibido (20%):</b> +<code>{bono_formateado}</code> CUP\n\n"
        
        " <pre>📊Estado de tu cuenta:</pre>\n"
        f"<b>Nuevo balance:</b> <code>{balance_formateado}</code> CUP\n\n"
        
        "• El saldo ya está disponible para usar\n"
        "¡Gracias por confiar en nosotros! 💫"
    )
    
    try:
        await query.edit_message_text(
            text=mensaje,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆Apostar🏆", callback_data="mostrar_tipos_apuestas")],
                [InlineKeyboardButton("🔙 Volver", callback_data="show_balance")]
            ])
        )
    except Exception as e:
        logger.error(f"Error al enviar notificación al usuario: {e}")
        # Intento alternativo si falla la edición
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=mensaje,
            parse_mode='HTML'
        )
        
        


async def actualizar_datos_usuario(user_id, metodo_pago, monto):
    """Actualiza la base de datos con los datos del depósito"""
    try:
        # Obtener datos actuales del usuario
        usuario_data = obtener_registro('usuarios', user_id)
        bono_data = obtener_registro('bono_apuesta', user_id)
        depositos_data = obtener_registro('depositos', user_id)
        
        # Guardar valores ANTES de la actualización
        old_balance = usuario_data[2] if usuario_data and len(usuario_data) > 2 else 0  # Índice 2: balance
        old_total_deposit = depositos_data[4] if depositos_data and len(depositos_data) > 4 else 0  # Índice 4: TotalDeposit
        old_bono = bono_data[1] if bono_data and len(bono_data) > 1 else 0  # Índice 1: bono
        old_rollover = bono_data[2] if bono_data and len(bono_data) > 2 else 0  # Índice 2: rollover_requerido

        # Calcular monto aplicado
        if metodo_pago == "saldo_movil":
            monto_aplicado = float(monto) * 3
        else:
            monto_aplicado = float(monto) * 1.10

        # 1. Actualizar balance del usuario
        new_balance = round(old_balance + monto_aplicado, 2)
        actualizar_registro('usuarios', user_id, {'balance': new_balance})

        # 2. Actualizar o crear registro en depósitos
        if depositos_data:
            # Actualizar depósito existente
            new_total_deposit = round(old_total_deposit + float(monto), 2)
            campos_deposito = {
                'payment': metodo_pago,
                'amount': float(monto),
                'TotalDeposit': new_total_deposit,
                'UltimoDeposito': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            actualizar_registro('depositos', user_id, campos_deposito)
        else:
            # Crear nuevo registro de depósito
            nombre_usuario = usuario_data[1] if usuario_data and len(usuario_data) > 1 else 'Nuevo Usuario'
            campos_deposito = {
                'id': user_id,
                'nombre': nombre_usuario,
                'payment': metodo_pago,
                'amount': float(monto),
                'TotalDeposit': float(monto),
                'UltimoDeposito': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            insertar_registro('depositos', campos_deposito)
            new_total_deposit = float(monto)

        # 3. Actualizar sistema de bonos
        bono = round(float(monto) * BONO_PORCENTAJE, 2)
        rollover = round(bono * 4, 2)  # Rollover 4 veces el bono

        if bono_data:
            # Actualizar bono existente
            new_bono = round(old_bono + bono, 2)
            new_rollover = round(old_rollover + rollover, 2)
            
            campos_bono = {
                'bono': new_bono,
                'rollover_requerido': new_rollover
            }
            actualizar_registro('bono_apuesta', user_id, campos_bono)
        else:
            # Crear nuevo registro de bono
            new_bono = bono
            new_rollover = rollover
            
            campos_bono = {
                'id': user_id,
                'bono': new_bono,
                'rollover_requerido': new_rollover,
                'rollover_actual': 0,
                'bono_retirable': 0
            }
            insertar_registro('bono_apuesta', campos_bono)

        logger.info(f"Datos actualizados correctamente para usuario {user_id}")
        
        # Devolver los valores antiguos y nuevos
        return {
            'success': True,
            'old_values': {
                'balance': old_balance,
                'TotalDeposit': old_total_deposit,
                'bono': old_bono,
                'rollover': old_rollover
            },
            'new_values': {
                'balance': new_balance,
                'TotalDeposit': new_total_deposit,
                'bono': new_bono,
                'rollover': new_rollover
            }
        }

    except Exception as e:
        logger.error(f"Error crítico actualizando datos: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Guardar error en la base de datos si es posible
        try:
            consulta_error = """
                INSERT INTO error_log (timestamp, user_id, error, monto, metodo_pago)
                VALUES (?, ?, ?, ?, ?)
            """
            valores_error = (
                datetime.now().isoformat(),
                user_id,
                str(e),
                str(monto),
                metodo_pago
            )
            ejecutar_consulta_segura(consulta_error, valores_error)
        except Exception as db_error:
            print(f"Error guardando en log de errores: {db_error}")
        
        return {'success': False}


async def enviar_reporte_exitoso(context, user_id, user_name, metodo_pago, monto_verificado, telefono, detalles, seccion, update_data):
    """Versión mejorada del reporte exitoso con balance antes/después"""
    try:
        # Preparar texto de cambios
        cambios_texto = (
            f"💵 Balance: {update_data['old_values']['balance']} → {update_data['new_values']['balance']} CUP\n"
            f"📊 Total depositado: {update_data['old_values']['TotalDeposit']} → {update_data['new_values']['TotalDeposit']} CUP\n"
            f"🎁 Bono: {update_data['old_values']['bono']} → {update_data['new_values']['bono']} CUP\n"
            f"🔄 Rollover: {update_data['old_values']['rollover']} → {update_data['new_values']['rollover']} CUP"
        )
        
        texto = (
            f"<pre>✅ DEPÓSITO VERIFICADO</pre>\n\n"
            f"👤 Usuario: {user_name} (ID: {user_id})\n"
            f"🏦 Método: {TEXTOS_METODOS.get(metodo_pago, {}).get('nombre', metodo_pago)}\n"
            f"💰 Monto: {monto_verificado} CUP\n"
            f"📱 Teléfono: {telefono}\n"
            f"🔍 Sección: {seccion}\n\n"
            f"<b>📈 CAMBIOS REALIZADOS:</b>\n"
            f"{cambios_texto}\n\n"
            f"📄 Detalles: {detalles}\n"
            f"🕒 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=texto,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error enviando reporte exitoso: {e}")

# --------------------------
# MANEJADOR PRINCIPAL
# --------------------------

async def manejar_verificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Obtener datos básicos con timestamp
    start_time = datetime.now()
    user_data = context.user_data
    user_id = str(query.from_user.id)
    user_name = query.from_user.full_name
    metodo_pago = user_data.get('metodo')
    telefono = user_data.get('numero_telefono')
    
    # Validación inicial mejorada
    if not metodo_pago or not telefono:
        error_msg = "⚠️ Datos incompletos para verificación. Falta: "
        missing = []
        if not metodo_pago: missing.append("método de pago")
        if not telefono: missing.append("número de teléfono")
        error_msg += ", ".join(missing)
        
        await notificar_error_verificacion(query, error_msg)
        await enviar_reporte_fallo(
            context, user_id, user_name, 
            metodo_pago or "No especificado", 
            "N/A", telefono or "No especificado", 
            error_msg
        )
        return
    
    try:
        # Diccionario de verificadores con nombres legibles
        verificadores = {
            'saldo_movil': ('Saldo Móvil', verificar_saldo_movil),
            'enzona': ('EnZona', verificar_enzona),
            'mlc': ('MLC', verificar_mlc),
            'bpa': ('Pago Móvil BPA', verificar_pagomovil),
            'bandec': ('Pago Móvil Bandec', verificar_pagomovil),
            'mi_transfer': ('Mi Transfer', verificar_pagomovil),
            'metro': ('Pago Móvil Metro', verificar_pagomovil)
        }
        
        if metodo_pago not in verificadores:
            error_msg = f"❌ Método de pago '{metodo_pago}' no está soportado"
            await notificar_error_verificacion(query, error_msg)
            await enviar_reporte_fallo(
                context, user_id, user_name, 
                metodo_pago, "N/A", telefono, 
                error_msg
            )
            return
        
        metodo_nombre, verificador = verificadores[metodo_pago]
        
        # Ejecutar verificación con tiempo de espera
        try:
            resultado = await asyncio.wait_for(verificador(telefono), timeout=30)
            detalles_verificacion = resultado.get('detalles', "Sin detalles adicionales")
            monto_encontrado = resultado.get('monto', 0)
        except asyncio.TimeoutError:
            error_msg = "⌛ Tiempo de espera agotado al verificar"
            await notificar_error_verificacion(query, error_msg)
            await enviar_reporte_fallo(
                context, user_id, user_name, 
                metodo_pago, "N/A", telefono, 
                error_msg
            )
            return
        
        if resultado['encontrado']:
            try:
                # Proceso de marcado como completado
                marcado_ok = await marcar_transferencia_completada(
                    resultado['seccion'],
                    resultado['transferencia'],
                    user_id
                )
                
                if not marcado_ok:
                    error_msg = "⚠️ Transferencia verificada pero no se pudo marcar como completada"
                    await query.edit_message_text(text=f"{error_msg}. Contacta soporte.")
                    await enviar_reporte_fallo(
                        context, user_id, user_name,
                        metodo_pago, monto_encontrado, telefono,
                        f"{detalles_verificacion} | {error_msg}"
                    )
                    return
                
                # Actualizar datos del usuario con tracking completo
                update_result = await actualizar_datos_usuario(user_id, metodo_pago, monto_encontrado)
                
                if update_result.get('success'):
                    # Notificaciones mejoradas
                    await notificar_verificacion_exitosa(query, context, monto_encontrado)
                    
                    # Reporte exitoso con todos los datos
                    await enviar_reporte_exitoso(
                        context, user_id, user_name, 
                        metodo_pago, monto_encontrado, 
                        telefono, detalles_verificacion, 
                        resultado['seccion'],
                        update_result  # Pasar los datos de antes/después
                    )
                    
                    # Log de éxito
                    logger.info(f"Depósito exitoso | User: {user_id} | Monto: {monto_encontrado} | Método: {metodo_pago}")
                else:
                    error_msg = "⚠️ Error actualizando saldo del usuario"
                    await query.edit_message_text(text=f"✅ Depósito verificado pero {error_msg.lower()}. Contacta soporte.")
                    await enviar_reporte_fallo(
                        context, user_id, user_name,
                        metodo_pago, monto_encontrado, telefono,
                        f"{detalles_verificacion} | {error_msg} | Detalles: {update_result.get('error', 'Sin detalles')}"
                    )
                    
            except Exception as e:
                error_msg = f"❌ Error en proceso post-verificación: {str(e)}"
                logger.error(f"Error post-verificación: {e}", exc_info=True)
                await notificar_error_verificacion(query, "Error al completar el proceso")
                await enviar_reporte_fallo(
                    context, user_id, user_name,
                    metodo_pago, monto_encontrado or "N/A", telefono,
                    f"{detalles_verificacion} | {error_msg}"
                )
                
        else:
            # Verificación fallida con detalles
            await notificar_verificacion_fallida(query, user_data)
            await enviar_reporte_fallo(
                context, user_id, user_name,
                metodo_pago, "N/A", telefono,
                f"Verificación fallida | {detalles_verificacion}"
            )
    
    except Exception as e:
        error_msg = f"⛔ Error crítico: {str(e)}"
        logger.error(f"Error en manejar_verificacion: {e}", exc_info=True)
        await notificar_error_verificacion(query, "Error interno al verificar")
        await enviar_reporte_fallo(
            context, user_id, user_name,
            metodo_pago, "N/A", telefono,
            f"Excepción no controlada: {error_msg}"
        )
    finally:
        # Métricas de tiempo de procesamiento
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Tiempo de procesamiento para {user_id}: {processing_time:.2f} segundos")
async def verificar_saldo_movil(telefono):
    """Verificación mejorada para saldo móvil de Cubacel"""
    resultado = {
        'encontrado': False,
        'seccion': 'Cubacel',
        'detalles': "No se encontró transferencia con los datos proporcionados",
        'transferencia': None,
        'monto': 0
    }
    
    try:
        with open('depositos.json', 'r') as f:
            datos = json.load(f)
        
        telefono_str = str(telefono)
        
        # Buscar en Cubacel
        for transferencia in datos.get('Cubacel', []):
            datos_transfer = transferencia.get('datos', {})
            mensaje = transferencia.get('mensaje', '')
            
            condiciones = [
                # Verificar que el teléfono coincida
                str(datos_transfer.get('telefono_remitente', '')) == telefono_str,
                # Verificar formato Cubacel (más flexible)
                "Usted ha recibido" in mensaje or "recarga de saldo movil" in mensaje,
                # Verificar que no esté completada
                not transferencia.get('completed', False)
            ]
            
            if all(condiciones):
                monto = float(datos_transfer.get('monto', 0))
                resultado.update({
                    'encontrado': True,
                    'transferencia': transferencia,
                    'monto': monto,
                    'detalles': f"Transferencia encontrada en Cubacel - Monto: {monto}"
                })
                return resultado

        # Buscar en DESCONOCIDO como fallback (verificación menos estricta)
        for transferencia in datos.get('DESCONOCIDO', []):
            datos_transfer = transferencia.get('datos', {})
            mensaje = transferencia.get('mensaje', '')
            
            condiciones = [
                # Coincidencia parcial del teléfono (últimos 4 dígitos)
                str(datos_transfer.get('telefono_remitente', '')).endswith(telefono_str[-4:]),
                # Verificar patrones de Cubacel
                ("Usted ha recibido" in mensaje or "recarga de saldo movil" in mensaje),
                not transferencia.get('completed', False)
            ]
            
            if all(condiciones):
                monto = float(datos_transfer.get('monto', 0))
                resultado.update({
                    'encontrado': True,
                    'seccion': 'DESCONOCIDO',
                    'transferencia': transferencia,
                    'monto': monto,
                    'detalles': f"Transferencia encontrada en sección desconocida - Monto: {monto}"
                })
                return resultado

        resultado['detalles'] = f"No se encontró transferencia desde el teléfono {telefono_str}"
        
    except Exception as e:
        resultado['detalles'] = f"Error en verificación: {str(e)}"
        logger.error(f"Error en verificación saldo móvil: {e}", exc_info=True)
    
    return resultado

async def enviar_reporte_fallo(context, user_id, user_name, metodo_pago, monto, telefono, motivo):
    try:
        from datetime import datetime
        
        # Procesar el motivo para hacerlo más descriptivo
        if "No se encontró transferencia desde el teléfono" in motivo:
            motivo_formateado = f"El teléfono {telefono} no tiene transferencias registradas por {TEXTOS_METODOS.get(metodo_pago, {}).get('nombre', metodo_pago)}"
        elif "Error en verificación" in motivo:
            motivo_formateado = f"Error técnico al verificar: {motivo.split(':')[-1].strip()}"
        else:
            motivo_formateado = motivo

        texto = (
            f"<pre>❌ DEPÓSITO FALSO RECHAZADO ❌</pre>\n\n"
            f"👤 Usuario: {user_name} (ID: <code>{user_id}</code>)\n"
            f"🏦 Método: {TEXTOS_METODOS.get(metodo_pago, {}).get('nombre', metodo_pago)}\n"
            f"📱 Teléfono: <code>{telefono}</code>\n"
            f"📛 Motivo: {motivo_formateado}\n"
            f"🕒 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await context.bot.send_message(
            chat_id=REGISTRO_MINIJUEGOS,
            text=texto,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error enviando reporte de fallo: {e}")

async def verificar_pagomovil(telefono: str) -> dict:
    """Versión corregida con manejo exacto de teléfonos"""
    resultado = {
        'encontrado': False,
        'seccion': 'PAGOxMOVIL',
        'detalles': "No se encontró transferencia válida",
        'transferencia': None,
        'monto': 0.0
    }
    
    try:
        with open('depositos.json', 'r') as f:
            datos = json.load(f)
        
        # Normalización de teléfonos (eliminar espacios, guiones, etc.)
        telefono_prov = re.sub(r'\D', '', str(telefono))[-8:]  # Solo últimos 8 dígitos numéricos
        cuenta_esperada = "9205129977430389"
        
        for transferencia in datos.get('PAGOxMOVIL', []):
            mensaje = transferencia.get('mensaje', '')
            datos_transfer = transferencia.get('datos', {})
            
            if "El titular del telefono" in mensaje:
                # Extraer teléfono exacto del mensaje
                tel_match = re.search(r'El titular del telefono (\d+)', mensaje)
                if tel_match:
                    tel_transfer = re.sub(r'\D', '', tel_match.group(1))[-8:]  # Normalizar y tomar últimos 8
                    
                    # Depuración detallada
                    logger.debug(f"🔍 Comparando: Tel-Prov:{telefono_prov} vs Tel-Transfer:{tel_transfer} | "
                               f"Cuenta: {datos_transfer.get('cuenta_destino')} | "
                               f"Completed: {transferencia.get('completed', False)}")
                    
                    if (tel_transfer == telefono_prov and 
                        datos_transfer.get('cuenta_destino') == cuenta_esperada and
                        not transferencia.get('completed', False)):
                        
                        try:
                            monto = float(datos_transfer.get('monto', 0))
                            resultado.update({
                                'encontrado': True,
                                'transferencia': transferencia,
                                'monto': monto,
                                'detalles': f"Transferencia válida (Monto: {monto} CUP, Transacción: {datos_transfer.get('numero_transaccion', 'N/A')})"
                            })
                            logger.info(f"✅ Transferencia encontrada: {resultado}")
                            return resultado
                        except (TypeError, ValueError) as e:
                            logger.error(f"Error en formato de monto: {e}")
                            continue
        
        resultado['detalles'] = (
            f"No se a podido verificar esta transferencia:\n"
            f"• Teléfono: {telefono_prov} (proporcionado)"
        )
    
    except Exception as e:
        resultado['detalles'] = f"Error en verificación: {str(e)}"
        logger.error(f"🔥 Error crítico en verificar_pagomovil: {e}", exc_info=True)
    
    return resultado    
    
    
async def verificar_enzona(telefono: str, monto: float) -> dict:
    """Verifica transferencias en PagoMovil (para BPA, Bandec, etc.)"""
    return await verificar_transferencia_generica(
        seccion='PAGOxMOVIL',
        telefono=telefono,
        monto=monto,
        campo_telefono='telefono_remitente'
    )    
    

async def verificar_mlc(telefono: str, monto: float) -> dict:
    """Verifica transferencias MLC"""
    return await verificar_transferencia_generica(
        seccion='MLC',
        telefono=telefono,
        monto=monto,
        campo_telefono='telefono_remitente'
    )

async def verificar_transferencia_generica(seccion: str, telefono: str, monto: float, 
                                         campo_telefono: str, coincidencia_exacta=False) -> dict:
    """
    Función genérica para verificar transferencias
    Retorna un dict con:
    - 'encontrado': bool
    - 'transferencia': dict (si se encontró)
    - 'seccion': str (sección donde se encontró)
    """
    resultado = {'encontrado': False, 'transferencia': None, 'seccion': seccion}
    
    try:
        async with lock_depositos:  # Usando el asyncio.Lock() global
            # Leer archivo JSON
            with open('depositos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            for transferencia in datos.get(seccion, []):
                datos_transfer = transferencia.get('datos', {})
                
                # Verificar monto (con tolerancia pequeña para floats)
                monto_transfer = float(datos_transfer.get('monto', 0))
                if abs(monto_transfer - float(monto)) > 0.01:
                    continue
                
                # Verificar teléfono
                tel_transfer = str(datos_transfer.get(campo_telefono, ''))
                if coincidencia_exacta:
                    if tel_transfer != str(telefono):
                        continue
                else:
                    if not tel_transfer.endswith(str(telefono)[-4:]):
                        continue
                
                # Verificar si ya estaba completada
                if transferencia.get('completed', False):
                    continue
                
                resultado.update({
                    'encontrado': True,
                    'transferencia': transferencia
                })
                break
            
            # Si no se encontró en la sección principal, buscar en DESCONOCIDO
            if not resultado['encontrado'] and seccion != 'DESCONOCIDO':
                resultado_desconocido = await verificar_transferencia_generica(
                    seccion='DESCONOCIDO',
                    telefono=telefono,
                    monto=monto,
                    campo_telefono=campo_telefono,
                    coincidencia_exacta=coincidencia_exacta
                )
                if resultado_desconocido['encontrado']:
                    return resultado_desconocido
            
            return resultado
    
    except Exception as e:
        logger.error(f"Error en verificación genérica ({seccion}): {e}")
        return resultado





async def marcar_transferencia_completada(seccion: str, transferencia: dict, user_id: int):
    """Marca una transferencia como completada en el JSON"""
    try:
        async with lock_depositos:
            # 1. Leer el archivo completo
            with open('depositos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            logger.debug(f"Buscando transferencia en sección {seccion} con timestamp {transferencia.get('timestamp')}")
            
            # 2. Buscar y actualizar la transferencia específica
            transferencia_actualizada = False
            
            # Buscar en la sección principal
            for idx, trans in enumerate(datos.get(seccion, [])):
                if trans.get('timestamp') == transferencia.get('timestamp'):
                    logger.debug(f"Transferencia encontrada en índice {idx}")
                    datos[seccion][idx]['completed'] = True
                    datos[seccion][idx]['fecha_verificacion'] = datetime.now().isoformat()
                    datos[seccion][idx]['usuario'] = user_id
                    transferencia_actualizada = True
                    break
            
            # Si no se encontró, buscar en DESCONOCIDO
            if not transferencia_actualizada:
                logger.debug("Transferencia no encontrada en la sección principal, buscando en DESCONOCIDO")
                for idx, trans in enumerate(datos.get('DESCONOCIDO', [])):
                    if trans.get('timestamp') == transferencia.get('timestamp'):
                        datos['DESCONOCIDO'][idx]['completed'] = True
                        datos['DESCONOCIDO'][idx]['fecha_verificacion'] = datetime.now().isoformat()
                        datos['DESCONOCIDO'][idx]['usuario'] = user_id
                        transferencia_actualizada = True
                        break
            
            if not transferencia_actualizada:
                raise ValueError("Transferencia no encontrada en ninguna sección")
            
            # 3. Guardar los cambios
            with open('depositos.json', 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=4, ensure_ascii=False)
            
            logger.debug("Transferencia marcada como completada correctamente")
            return True
    
    except Exception as e:
        logger.error(f"Error marcando transferencia como completada: {e}")
        raise


        
#mostrar criptomonedas
@verificar_bloqueo
async def criptomonedas(update, context):
    try:
        query = update.callback_query
        await query.answer()

        payment_method = query.data

        context.user_data['payment_method'] = payment_method
        context.user_data['payment_time'] = tm.time()  

        logger.info(f"Usuario {query.from_user.full_name} seleccionó el método de pago: {payment_method}")

        reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("💰 Litecoin (LTC)", callback_data="ltc")],
    [InlineKeyboardButton("🐕 Doge", callback_data="doge"), InlineKeyboardButton("💸 Bitcoin (BTC)", callback_data="btc")],
    [InlineKeyboardButton("⚡ Solana", callback_data="solana")],
    [InlineKeyboardButton("🔼 TRX", callback_data="trx"), InlineKeyboardButton("💎 TON", callback_data="ton")],
    [InlineKeyboardButton("🌕 BNB", callback_data="bnb")],
    [InlineKeyboardButton("♻️ Ethereum (ETH)", callback_data="eth"), InlineKeyboardButton("💵 Bitcoin Cash (BCH)", callback_data="bch")],
    [InlineKeyboardButton("🌈 DGB", callback_data="dgb")],
    [InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")]
])

        await query.edit_message_text(
            "Selecciona la criptomoneda con la que deseas realizar el depósito:",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error en criptomonedas(): {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Ocurrió un error al intentar seleccionar la criptomoneda."
        )





# Función para manejar el método de pago 
@verificar_bloqueo
async def handle_payment_method(update, context):
    try:
        query = update.callback_query
        await query.answer()
        logger.info(f"Método de pago seleccionado: {query.data}")

        user_id = query.from_user.id  
        user_name = query.from_user.full_name 
        payment_method = query.data  

        # Métodos de pago que requieren el mensaje especial
        metodos_especiales = ["mlc", "doge", "ltc", "btc", "solana", "trx", "ton", "bnb", "eth", "bch", "dgb"]

        if payment_method in ["tarjeta", "telefono", "banca"] + metodos_especiales:
            context.user_data['payment_method'] = payment_method
            context.user_data['payment_time'] = tm.time()

            # Actualizar método de pago en la base de datos
            usuario_data = obtener_registro('usuarios', str(user_id))
            if usuario_data:
                actualizar_registro('depositos', str(user_id), {'payment': payment_method})
            else:
                # Crear usuario si no existe
                insertar_registro('usuarios', {
                    'id': str(user_id),
                    'nombre': user_name,
                    'balance': 0,
                    'referidos': 0,
                    'lider': 0,
                    'total_ganado_ref': 0,
                    'medalla': 'Sin medalla',
                    'payment': payment_method
                })

        else:
            logger.warning("Método de pago inválido recibido.")
            await menu_principal(update, context)
            return

        # Definir el mensaje según el método de pago
        if payment_method in metodos_especiales:
            mensaje = (
                "🔻 Por favor, ingresa el monto que deseas depositar en USD\n\n"
                "⚠️ <b>Mínimo de depósito 1 USD</b>"
            )
        else:
            mensaje = "Por favor, ingresa el monto que deseas depositar:"

        # Crear el teclado
        keyboard = [
            [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
        ]

        # Enviar el mensaje
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        context.user_data['estado'] = 'handle_amount'

    except Exception as e:
        logger.error(f"Error en handle_payment_method(): {e}")
        import traceback
        traceback.print_exc()



# Función para manejar el monto transferido
async def handle_amount(update, context):
    try:
        user_id = update.message.from_user.id
        amount = update.message.text.strip()
        user_name = update.message.from_user.full_name
        payment_method = context.user_data.get('payment_method')
        payment_time = context.user_data.get('payment_time')

        

        if not payment_method or not payment_time or tm.time() - payment_time > 20:
            
            return

        # Validar que el monto sea un número
        if not amount.isdigit():
            logger.warning(f"Monto inválido recibido de {user_name} (ID: {user_id}): {amount}")

            keyboard = [
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ]
            await update.message.reply_text(
                "⚠️El monto debe ser un número, sin texto.\n\n🔄_Intenta de nuevo_",
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
            )
            return

        # Guardar el depósito en la base de datos
        deposito_data = obtener_registro('depositos', str(user_id))
        if deposito_data:
            # Actualizar depósito existente
            actualizar_registro('depositos', str(user_id), {
                'amount': float(amount),
                'payment': payment_method,
                'UltimoDeposito': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            # Crear nuevo depósito
            insertar_registro('depositos', {
                'id': str(user_id),
                'nombre': user_name,
                'payment': payment_method,
                'amount': float(amount),
                'TotalDeposit': 0,
                'UltimoDeposito': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        logger.info(f"Datos del depósito guardados para usuario {user_id}")

        # Mensajes según el método de pago (se mantiene igual)
        if payment_method == "telefono":
            await update.message.reply_text(
                f"<blockquote>Método de pago 📱 Teléfono</blockquote>\n\n"
                f"Transfiere <b>{amount}</b> al número <code>54082678</code>\n\n"
                f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
                    [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
                ]),
                parse_mode="HTML"
            )
        elif payment_method == "tarjeta":
            await update.message.reply_text(
        f"<blockquote>Método de pago 💳 Tarjeta</blockquote>\n\n"
        f"Transfiere <b>{amount}</b> al número de tarjeta:\n💳<code>9205129977430389</code>\n🔕Confirmar al: <code>54082678</code>.\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "banca":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🏦 Banca Remota</blockquote>\n\n"
        f"Transfiere <b>{amount}</b> a la tarjeta\n<code>9205129977430389</code>.\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "mlc":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🪪 MLC</blockquote>\n\n"
        f"Transfiere <b>{amount}</b> en MLC a la tarjeta:\n\n🪪<code>9225129979794663</code>\n🔕Número a comfirmar:<code>54082678</code>.\n\n⚠️1MLC = {cambio_mlc} CUP\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "ltc":
            await update.message.reply_text(
        f"<blockquote>Método de pago ⚡ Litecoin (LTC)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Litecoin a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>ltc1qd0kqueevs9tud6p0lrgayctwq3kcmxnat50ehl</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "doge":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🐕 Dogecoin (DOGE)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Dogecoin a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>DF5mEPVF1iaw1WbALdVGyUZLQpVmm8JUM2</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "btc":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🪙 Bitcoin (BTC)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Bitcoin a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>bc1qhvktpylqfxxyny5c6lsqm4504wy3q3l0dxnug9</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "solana":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🌞 Solana (SOL)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Solana a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>2aPhj2R1DyHDMEj2XsfLFQXMTEGbnXZqqgqa7zFgxrAf</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "trx":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🔵 TRON (TRX)</blockquote>\n\n"
        f"⚠️ Envia solo activos de TRON a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>TGERP5ShgLYo8Trwrjx3MHKvPVKxhk4UBF</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "ton":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🔷 TON (Toncoin)</blockquote>\n\n"
        f"⚠️ Envia solo activos de TON a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>UQCJsu7jQMzma3AOjhyH9MjZxv2yW8Nb4OQaM3IqaW6bmZlc</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "bnb":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🌐 Binance Coin (BNB)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Binance Coin a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>0x084eDa31cbd5590b6Ccf748643519FE5c9ADCE60</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "eth":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🌍 Ethereum (ETH)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Ethereum a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>0x084eDa31cbd5590b6Ccf748643519FE5c9ADCE60</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "dgb":
            await update.message.reply_text(
        f"<blockquote>Método de pago 🌈DigiByte (DGB)</blockquote>\n\n"
        f"⚠️ Envia solo activos de DigiByte a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>dgb1q6q6jkf3huw64t4azrcrfrej9n5k4jq70kj628p</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        elif payment_method == "bch":
            await update.message.reply_text(
        f"<blockquote>Método de pago 💸 Bitcoin Cash (BCH)</blockquote>\n\n"
        f"⚠️ Envia solo activos de Bitcoin Cash a esta dirección, activos de otra red se perderán para siempre:\n"
        f"<code>qrh5amukt9kl3ja206sn82sm56gmzd2x35wxneu8sa</code>\n\n"
        f"<i>Una vez terminada la transferencia, pulsa el botón de abajo</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"enviar_captura_deposito")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )
        else:
            await update.message.reply_text(
        "<blockquote>⚠️ Método de pago no reconocido</blockquote>\n\n"
        "<i>Por favor, selecciona un método de pago válido desde el menú principal.</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]),
        parse_mode="HTML"
    )

        logger.info(f"Solicitud de confirmación enviada al usuario {user_name} (ID: {user_id})")

    except Exception as e:
        logger.error(f"Error en handle_amount(): {e}")
        await update.message.reply_text("Hubo un error al procesar tu solicitud. Intenta nuevamente.")




async def enviar_captura_deposito(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        # Extraer el user_id del callback
        user_id = query.from_user.id

        # Solicitar la captura de pantalla al usuario
        await context.bot.send_message(
            chat_id=user_id,
            text="📸 Por favor, envía la captura de pantalla de la transferencia."
        )

        # Guardar el estado para esperar la captura
        context.user_data['esperando_captura'] = True
        context.user_data['user_id'] = user_id

    except Exception as e:
        logger.error(f"Error al solicitar la captura de pantalla: {e}")
        await context.bot.send_message(
            chat_id=update.callback_query.from_user.id,
            text="❌ Ocurrió un error al solicitar la captura de pantalla."
        )


async def handle_captura(update: Update, context: CallbackContext):
    try:
        user_id = update.message.from_user.id
        if not context.user_data.get('esperando_captura', False):
            return

        # Verificar si el mensaje contiene una foto
        if update.message.photo:
            # Obtener la foto con la mejor calidad
            photo_file = update.message.photo[-1].file_id

            # Obtener datos del depósito desde la base de datos
            deposito_data = obtener_registro('depositos', str(user_id))
            
            if not deposito_data:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ No se encontraron datos de depósito para tu usuario."
                )
                return

            # Extraer datos (ajusta índices según tu estructura)
            # Suponiendo estructura: (id, nombre, payment, amount, total_deposit, ultimo_deposito, ...)
            nombre = deposito_data[1] if len(deposito_data) > 1 else "Usuario Desconocido"  # Índice 1: nombre
            monto = deposito_data[4] if len(deposito_data) > 3 else 0  # Índice 3: amount
            metodo_pago = deposito_data[3] if len(deposito_data) > 2 else "Método Desconocido"  # Índice 2: payment

            # Crear el mensaje con formato HTML
            mensaje = (
                f" <pre>Solicitud de depósito</pre>\n\n"
                f"👤 <b>Nombre:</b> <code>{nombre}</code>\n"
                f"💰 <b>Monto:</b> <code>{monto}</code>\n"
                f"💳 <b>Método de Pago:</b> <code>{metodo_pago}</code>\n\n"
                f"<i>🔽 Revisa y confirma para enviar a los administradores</i>."
            )

            # Mostrar la captura al usuario con el mensaje formateado
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo_file,
                caption=mensaje,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Transferencia completada", callback_data=f"send_to_admin_{user_id}")],
                    [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
                ])
            )

            # Limpiar el estado
            context.user_data['esperando_captura'] = False
            context.user_data['photo_file'] = photo_file  # Guardar la foto para enviarla a los administradores

        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Por favor, envía una imagen válida."
            )

    except Exception as e:
        logger.error(f"Error al manejar la captura de pantalla: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="❌ Ocurrió un error al procesar la captura de pantalla."
        )

# Función para enviar la solicitud de depósito 
@verificar_bloqueo
async def send_to_admin(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)
        user_name = query.from_user.full_name

        logger.info(f"Usuario identificado: {user_name} (ID: {user_id})")

        # Obtener datos del depósito desde la base de datos
        deposito_data = obtener_registro('depositos', user_id)
        if not deposito_data:
            logger.error(f"No se encontraron datos para el usuario con ID {user_id}")
            await query.edit_message_text("No se encontró la información de tu depósito.")
            return

        # Extraer datos (ajusta índices según tu estructura)
        amount = deposito_data[4] if len(deposito_data) > 3 else "Desconocido"  # Índice 3: amount
        payment_method = deposito_data[3] if len(deposito_data) > 2 else "Desconocido"  # Índice 2: payment

        if amount == "Desconocido" or payment_method == "Desconocido":
            logger.error(f"Datos incompletos para el usuario {user_name}: Monto={amount}, Método de Pago={payment_method}")
            await query.edit_message_text("Información incompleta sobre el depósito.")
            return

        logger.info(f"Enviando al grupo: Usuario={user_name}, Monto={amount}, Método de pago={payment_method}")

        # Obtener la imagen del contexto
        photo_file = context.user_data.get('photo_file')
        if not photo_file:
            logger.error(f"No se encontró la imagen en el contexto para el usuario {user_name}")
            await query.edit_message_text("No se encontró la imagen de la captura. Intenta nuevamente.")
            return

        # Crear el mensaje de notificación
        notification_text = f"""
        <blockquote>📥Solicitud de Depósito📥</blockquote>

        <b>Nombre del Usuario</b>: {user_name}
        <b>ID de Usuario</b> : <code>{user_id}</code>
        <b>Método de Pago</b>: {payment_method}
        <b>Monto Transferido</b>: <code>{amount}</code> CUP        
        """

        try:
            # Enviar la imagen y el mensaje al grupo de administradores
            await context.bot.send_photo(
                chat_id=GROUP_CHAT_ADMIN,
                photo=photo_file,
                caption=notification_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✔️ Aceptar", callback_data=f"accept_deposit_{user_id}")],
                    [InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_deposit_{user_id}")],
                ]),
                parse_mode='HTML'
            )
            logger.info(f"Mensaje enviado al grupo con ID: {GROUP_CHAT_ADMIN}")
        except Exception as e:
            logger.error(f"No se pudo enviar el mensaje al grupo: {e}")
            await query.edit_message_text("Hubo un error al intentar enviar tu solicitud al grupo.")
            return

        # Eliminar el mensaje anterior con la foto
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

        # Enviar un nuevo mensaje de confirmación al usuario
        confirmation_message = f"""
        <blockquote>✅Solicitud de Depósito enviada✅</blockquote>

        <b>👤Nombre de Usuario:</b> {user_name}
        <b>🪪Método de Pago</b>: {payment_method}
        <b>💰Monto Transferido</b>: <code>{amount}</code> CUP

        👮‍♂️ <i>Esta solicitud será revisada por un administrador, si todo es correcto en breve se acredita a tu balance.</i>
        """

        keyboard = [
            [InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=confirmation_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error en send_to_admin(): {e}")
        await query.edit_message_text("Hubo un error al procesar tu solicitud. Intenta nuevamente.")

async def accept_deposit(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        # Extraer el user_id del callback
        callback_data = query.data
        if callback_data.startswith('accept_deposit_'):
            user_id = callback_data.split('_')[2]  
        else:
            logger.error("El formato del callback_data es incorrecto.")
            await query.edit_message_text("❌ El formato del callback_data es incorrecto.")
            return

        # Obtener datos desde la base de datos
        deposito_data = obtener_registro('depositos', user_id)
        usuario_data = obtener_registro('usuarios', user_id)
        bono_data = obtener_registro('bono_apuesta', user_id)
        
        if not deposito_data or not usuario_data:
            await query.edit_message_text("❌ No se encontraron datos para este usuario.")
            return

        # Extraer valores (ajusta índices según tu estructura)
        amount = float(deposito_data[4] or 0) if len(deposito_data) > 3 else 0  # Índice 3: amount
        payment_method = deposito_data[2] if len(deposito_data) > 2 else ""  # Índice 2: payment
        nombre_usuario = deposito_data[1] if len(deposito_data) > 1 else "Usuario"  # Índice 1: nombre

        if amount <= 0:
            await query.edit_message_text("❌ El monto del depósito es inválido.")
            return

        # Aplicar el cambio según el método de pago
        if payment_method == "mlc":
            amount *= cambio_mlc  # Multiplicar por el valor de cambio MLC
        elif payment_method in ["doge", "ltc", "btc", "solana", "trx", "ton", "bnb", "eth", "bch", "dgb"]:
            amount *= cambio_cripto  # Multiplicar por el valor de cambio cripto

        # Obtener el nombre del administrador
        admin_name = update.callback_query.from_user.first_name

        # Actualizar el balance del usuario
        old_balance = usuario_data[2] if len(usuario_data) > 2 else 0  # Índice 2: balance
        new_balance = old_balance + amount
        actualizar_registro('usuarios', user_id, {'balance': new_balance})

        # Actualizar total depositado
        old_total_deposit = deposito_data[4] if len(deposito_data) > 4 else 0  # Índice 4: total_deposit
        new_total_deposit = old_total_deposit + amount
        actualizar_registro('depositos', user_id, {'TotalDeposit': new_total_deposit})

        # Calcular el 30% del amount para el bono y el rollover
        bono_amount = amount * 0.30
        rollover_amount = bono_amount * 3

        # Actualizar el bono y el rollover requerido
        if bono_data:
            old_bono = bono_data[1] if len(bono_data) > 1 else 0  # Índice 1: bono
            old_rollover = bono_data[2] if len(bono_data) > 2 else 0  # Índice 2: rollover_requerido
            new_bono = old_bono + bono_amount
            new_rollover = old_rollover + rollover_amount
            actualizar_registro('bono_apuesta', user_id, {
                'bono': new_bono,
                'rollover_requerido': new_rollover
            })
        else:
            # Crear nuevo registro de bono
            insertar_registro('bono_apuesta', {
                'id': user_id,
                'bono': bono_amount,
                'rollover_requerido': rollover_amount,
                'rollover_actual': 0,
                'bono_retirable': 0
            })

        # Obtener el ID del líder del usuario
        lider_id = str(usuario_data[4] if len(usuario_data) > 4 else user_id)  # Índice 4: lider

        # Verificar que el líder esté registrado en la base de datos
        if lider_id and lider_id != user_id:
            lider_data = obtener_registro('usuarios', lider_id)
            if lider_data:
                # Calcular el 1% del depósito y añadirlo al líder
                lider_amount = amount * 0.01
                old_balance_lider = lider_data[2] if len(lider_data) > 2 else 0
                new_balance_lider = old_balance_lider + lider_amount
                actualizar_registro('usuarios', lider_id, {'balance': new_balance_lider})
                
                # Notificar al líder
                lider_message = f"""
<blockquote>🙌¡Nuevo depósito realizado por tu referido!</blockquote>

👤 <b>Usuario:</b> <a href="tg://user?id={user_id}">{nombre_usuario}</a>

💰 <b>Has recibido:</b><code> {lider_amount}</code> CUP.
🏦 <b>Nuevo balance:</b> <code>{new_balance_lider}</code> CUP.
"""
                await context.bot.send_message(
                    chat_id=int(lider_id),
                    text=lider_message,
                    parse_mode="HTML"
                )

        # Eliminar el mensaje anterior en el grupo
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )

        # Enviar un nuevo mensaje al grupo
        admin_message = f"""
<blockquote>✅ Depósito aceptado ✅</blockquote>

👤 <b>Usuario:</b> <a href="tg://user?id={user_id}">{nombre_usuario}</a>
🆔 <b>ID del usuario:</b> <code>{user_id}</code>
💰 <b>Monto:</b><code> {amount}</code> CUP
🎁 <b>Bono agregado:</b> <code>{bono_amount}</code> CUP
🎯 <b>Rollover requerido:</b> <code>{rollover_amount}</code> CUP
🏦 <b>Nuevo balance:</b> <code>{new_balance}</code> CUP
🔑 <b>Aceptado por:</b> {admin_name}
"""
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=admin_message,
            parse_mode="HTML"
        )

        # Notificar al usuario 
        user_message = f"""
<blockquote>✅ Depósito aceptado ✅</blockquote>

💰 <b>Monto acreditado:</b> <code>{amount}</code> CUP
🎁 <b>Bono agregado:</b> <code>{bono_amount}</code> CUP
🎯 <b>Rollover requerido:</b> <code>{rollover_amount}</code> CUP
🏦 <b>Nuevo balance:</b> <code>{new_balance}</code> CUP
🔑 <b>Aceptado por:</b> {admin_name}
"""
        await context.bot.send_message(
            chat_id=int(user_id),
            text=user_message,
            parse_mode="HTML"
        )

        # Limpiar el monto del depósito
        actualizar_registro('depositos', user_id, {'amount': 0})

    except Exception as e:
        logger.error(f"Error al aceptar el depósito: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=update.callback_query.from_user.id,
            text="❌ Ocurrió un error al procesar el depósito."
        )

# Función rechazar deposito
@verificar_bloqueo

async def reject_deposit(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        # Extraer el user_id del callback
        callback_data = query.data
        if callback_data.startswith('reject_deposit_'):
            user_id = callback_data.split('_')[2]  
        else:
            logger.error("El formato del callback_data es incorrecto.")
            await query.edit_message_text("❌ El formato del callback_data es incorrecto.")
            return

        # Obtener datos desde la base de datos
        deposito_data = obtener_registro('depositos', user_id)
        if not deposito_data:
            logger.error(f"No se encontraron datos de depósito para el usuario con ID {user_id}")
            await query.edit_message_text("❌ No se encontraron datos de depósito para este usuario.")
            return

        # Extraer valores (ajusta índices según tu estructura)
        amount = deposito_data[3] if len(deposito_data) > 3 else "Desconocido"  # Índice 3: amount
        payment_method = deposito_data[2] if len(deposito_data) > 2 else "Desconocido"  # Índice 2: payment
        nombre_usuario = deposito_data[1] if len(deposito_data) > 1 else "Usuario Desconocido"  # Índice 1: nombre

        # Obtener el nombre del administrador que rechazó el depósito
        admin_name = update.callback_query.from_user.first_name

        # Eliminar el mensaje anterior en el grupo
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )

        # Enviar un nuevo mensaje al grupo notificando el rechazo
        admin_message = f"""
<blockquote>❌ Depósito rechazado ❌</blockquote>

👤 <b>Usuario:</b> <a href="tg://user?id={user_id}">{nombre_usuario}</a>
🆔 <b>ID del usuario:</b> <code>{user_id}</code>
💰 <b>Monto rechazado:</b> <code>{amount}</code> CUP
💳 <b>Método de pago:</b> {payment_method}
🔑 <b>Rechazado por:</b> {admin_name}
"""
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=admin_message,
            parse_mode="HTML"
        )

        # Enviar mensaje al usuario notificando el rechazo
        user_message = f"""
<blockquote>❌ Depósito rechazado ❌</blockquote>

💰 <b>Monto rechazado:</b> <code>{amount}</code> CUP
💳 <b>Método de pago:</b> {payment_method}
🔑 <b>Rechazado por:</b> {admin_name}

ℹ️ Si tienes dudas, por favor contacta con el soporte.
"""
        await context.bot.send_message(
            chat_id=int(user_id),
            text=user_message,
            parse_mode="HTML"
        )

        # Limpiar los datos del depósito
        actualizar_registro('depositos', user_id, {
            'amount': 0,
            'payment': "Desconocido"
        })

    except Exception as e:
        logger.error(f"Error al rechazar el depósito: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=update.callback_query.from_user.id,
            text="❌ Ocurrió un error al procesar el rechazo del depósito."
        )
        
def get_db_record(table, user_id, columns="*"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"SELECT {columns} FROM {table} WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# Función botón "💰 Mi Saldo"
@verificar_bloqueo
async def show_balance(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)
        user_name = query.from_user.full_name

        # Obtener registros directamente (sin await)
        user_row = get_db_record("usuarios", user_id, "balance, referidos, medalla")
        deposit_row = get_db_record("depositos", user_id, "payment, telefono")
        bono_row = get_db_record("bono_apuesta", user_id, "bono, bono_retirable, rollover_actual, rollover_requerido")

        # Datos del usuario
        balance = user_row[0] if user_row else 0
        referidos = user_row[1] if user_row else 0
        medalla = user_row[2] if user_row else "Sin medalla"

        # Datos de depósito
        metodo_pago = deposit_row[0] if deposit_row else 0
        telefono = deposit_row[1] if deposit_row else "No registrado"

        # Formatear método de pago
        if metodo_pago in TEXTOS_METODOS:
            metodo_pago_display = TEXTOS_METODOS[metodo_pago]['nombre']
        elif metodo_pago == 0 or metodo_pago == "0":
            metodo_pago_display = "No registrado"
        else:
            metodo_pago_display = str(metodo_pago).upper()

        # Datos de bonos
        bono_actual = bono_row[0] if bono_row else 0
        bono_retirable = bono_row[1] if bono_row else 0
        rollover_actual = bono_row[2] if bono_row else 0
        rollover_requerido = bono_row[3] if bono_row else 0
        progreso_rollover = (rollover_actual / rollover_requerido * 100) if rollover_requerido > 0 else 0

        # Teclado
        keyboard = [
            [InlineKeyboardButton("📥 Depositar", callback_data="depositar"),
             InlineKeyboardButton("📤 Retirar", callback_data="retirar")],
            [InlineKeyboardButton("📝 Registrar telefono", callback_data="registrar_telefono")],
            [InlineKeyboardButton("💱 Transferir saldo", callback_data="transferencia_interna")],
            [InlineKeyboardButton("🎖️ Mi medalla", callback_data="show_medalla"),
             InlineKeyboardButton("🎁 Bonos", callback_data="gestion_bonos")],
            [InlineKeyboardButton("🔙 Menú principal", callback_data="menu_principal")]
        ]

        # Mensaje
        message = (
            f"<pre>📊 ESTADO DE CUENTA</pre>\n"
            f"┌───────────────────────────┐\n"
            f"│ 👤 <b>Usuario:</b> {user_name[:15]}{'...' if len(user_name)>15 else ''}\n"
            f"│ 🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"├───────────────────────────┤\n"
            f"│ 💰 <b>Balance disponible:</b> <code>{balance:.2f} CUP</code>\n"
            f"│ 🏦 <b>Método de pago:</b> {metodo_pago_display}\n"
            f"│ 📱 <b>Teléfono asociado:</b> <code>{telefono}</code>\n"
            f"│ 👥 <b>Referidos:</b> {referidos}\n"
            f"│ 🎖️ <b>Medalla:</b> {medalla}\n"
            f"└───────────────────────────┘\n\n"
            f"<pre>🎁 BONOS Y PROMOCIONES</pre>\n"
            f"┌───────────────────────────┐\n"
            f"│ 🎰 <b>Bono actual:</b> <code>{bono_actual:.2f} CUP</code>\n"
            f"│ 💳 <b>Bono retirable:</b> <code>{bono_retirable:.2f} CUP</code>\n"
            f"│ 📊 <b>Rollover:</b> {rollover_actual:.2f}/{rollover_requerido:.2f} ({progreso_rollover:.1f}%)\n"
            f"└───────────────────────────┘\n\n"
        )

        await query.edit_message_text(
            text=message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Error en show_balance: {str(e)}")
        if hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.edit_message_text(
                text="❌ Error al cargar tu información. Por favor intenta nuevamente."
            )



# Función para obtener un registro de bonos
def get_bono_record(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT bono, bono_retirable, rollover_actual, rollover_requerido FROM bono_apuesta WHERE id = ?", (str(user_id),))
    row = c.fetchone()
    conn.close()
    return row  # Puede ser None si no existe

async def gestion_bonos(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        bono_row = get_bono_record(user_id)

        # Datos de bonos
        if bono_row:
            bono_apuesta, bono_retirable, rollover_actual, rollover_requerido = bono_row
        else:
            bono_apuesta = bono_retirable = rollover_actual = 0
            rollover_requerido = 150  # Default si no existe

        # Calculamos el progreso
        progreso = min((rollover_actual / rollover_requerido) * 100, 100) if rollover_requerido > 0 else 0
        faltante = max(rollover_requerido - rollover_actual, 0)

        # Crear mensaje
        message = f"""
<blockquote>💎 <b>GESTIÓN DE BONOS</b></blockquote>

🎁 <b>Bono de Apuesta:</b> <code>{bono_apuesta:.2f} CUP</code>
💲 <b>Bono Retirable:</b> <code>{bono_retirable:.2f} CUP</code>

📊 <b>Rollover:</b>
├ Requerido: <code>{rollover_requerido:.2f} CUP</code>
├ Actual: <code>{rollover_actual:.2f} CUP</code>
└ Progreso: [{('▓' * int(progreso//10)).ljust(10, '░')}] {progreso:.1f}%

{f"⚠️ <i>Falta apostar {faltante:.2f} CUP para liberar el bono</i>" if faltante > 0 else "✅ <i>Bono listo para retirar</i>"}
"""

        # Botones de gestión
        keyboard = [
            [InlineKeyboardButton("🎁 Retirar Bono 🎁", callback_data="transferir_bono")],
            [InlineKeyboardButton("❓ Cómo funciona", callback_data="info_bonos")],
            [InlineKeyboardButton("🔙 Volver", callback_data="show_balance")]
        ]

        await query.edit_message_text(
            text=message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Error en gestion_bonos: {e}")
        if hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.edit_message_text(
                text="❌ Error al cargar los datos de bonos. Intenta nuevamente."
            )
async def transferir_bono(update: Update, context: CallbackContext): 
    try: 
        query = update.callback_query 
        await query.answer()

        user_id = query.from_user.id
        data = await load_data()
        bono_data = data["Bono_apuesta"].get(str(user_id), {})
        usuario = data["usuarios"].get(str(user_id), {})
        medalla_actual = usuario.get("Medalla", "Sin medalla")

        # Verificar que la medalla sea Épico ^^ o superior
        partes = medalla_actual.split()
        nombre_medalla = partes[0] if len(partes) > 0 else ""
        subnivel = partes[1] if len(partes) > 1 else ""
        medalla_permitida = False
        
        if nombre_medalla == "Epico":
            if subnivel in ["^^", "^^^"]:
                medalla_permitida = True
        elif nombre_medalla in ["Leyenda", "Mítico"]:
            medalla_permitida = True
        
        if not medalla_permitida:
            mensaje = "❌ <b>Transferencia bloqueada</b>\nDebes tener medalla Épico ^^ o superior para transferir el bono."
            await query.edit_message_text(
                text=mensaje,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="gestion_bonos")]])
            )
            return

        if bono_data.get("Rollover_actual", 0) >= bono_data.get("Rollover_requerido", 0):
            # Transferir bono retirable
            monto_transferir = bono_data.get("Bono_retirable", 0)
            data["usuarios"][str(user_id)]["Balance"] += monto_transferir
            
            # Actualizar Rollover_requerido
            bono_data["Rollover_requerido"] = bono_data["Bono"] * 5  
            
            # Resetear valores
            bono_data["Bono_retirable"] = 0
            bono_data["Rollover_actual"] = 0
            
            
            mensaje = f"✅ <b>Transferencia exitosa!</b>\nSe han transferido <code>{monto_transferir:.2f} CUP</code> a tu balance."
        else:
            faltante = bono_data["Rollover_requerido"] - bono_data["Rollover_actual"]
            mensaje = f"❌ <b>Transferencia bloqueada</b>\nNecesitas apostar <code>{faltante:.2f} CUP</code> más para liberar el bono."

        await query.edit_message_text(
            text=mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="gestion_bonos")]])
        )
        
    except Exception as e:
        logger.error(f"Error en transferir_bono: {e}")
        
# Función explicativa
async def info_bonos(update: Update, context: CallbackContext):
    info_text = """
<blockquote>📚 <b>CÓMO FUNCIONAN LOS BONOS</b></blockquote>

1. 🎁 <b>Bono de Apuesta:</b> Crédito especial para apostar
2. 💲 <b>Bono Retirable:</b> Ganancias obtenidas con el bono
3. 📊 <b>Rollover:</b> Monto que debes apostar para retirar

<u>Para retirar:</u>
1. Completa el rollover requerido apostando
2. Tus ganancias se transferirán al balance listo para ser retirado.
3. El bono inicial se mantiene para seguir usando

⚠️ <i>El dinero del bono NO se puede retirar directamente, solo las ganancias generadas con el.</i>
"""
    
    await update.callback_query.edit_message_text(
        text=info_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="gestion_bonos")]]))
        
        


# Rango de puntos para cada medalla y subniveles
MEDALLAS_RANGOS = {
    "Maestro": [(1, 150, "^"), (150, 250, "^^"), (250, 300, "^^^")],
    "Epico": [(300, 700, "^"), (700, 900, "^^"), (900, 1000, "^^^")],
    "Leyenda": [(1000, 1300, "^"), (1300, 1600, "^^"), (1600, 2000, "^^^")],
    "Mítico": [(2000, 2500, "^"), (2500, 3000, "^^"), (3000, float("inf"), "^^^")]
}

# Puntos por actividades de los usuarios
PUNTOS_BET_WIN = 0.05
PUNTOS_BET_LOS = 0.01
PUNTOS_FICH_PERDIDAS = -0.00001
PUNTOS_FICH_GANADAS = 0.02
PUNTOS_REF_TOTALES = 1
PUNTOS_PIRATAS = 0.1
PUNTOS_NIVEL_VELAS = 1
PUNTOS_NIVEL_CANONES = 1
PUNTOS_NIVEL_BARCO = 1

# Función para asignar medallas
def asignar_medalla(puntos):
    if puntos < 2:
        return "Sin medalla"
    
    for medalla, rangos in MEDALLAS_RANGOS.items():
        for rango in rangos:
            if rango[0] <= puntos < rango[1]:
                return f"{medalla} {rango[2]}"
    
    return "Sin medalla"

async def calcular_puntos(usuario_id, user_data, json_minijuegos, juego_pirata_data):
    puntos = 0

    # Puntos por minijuegos (apuestas y fichas) - Se mantiene igual desde JSON
    if isinstance(json_minijuegos, dict):
        for juego, data in json_minijuegos.items():
            if not isinstance(data, dict):
                continue

            # BetWin
            puntos += data.get("BetWin", {}).get(usuario_id, 0) * PUNTOS_BET_WIN
            # BetLost
            puntos += data.get("BetLost", {}).get(usuario_id, 0) * PUNTOS_BET_LOS
            # FichGanadas
            puntos += data.get("FichGanadas", {}).get(usuario_id, 0) * PUNTOS_FICH_GANADAS
            # FichPerdidas
            puntos += data.get("FichPerdidas", {}).get(usuario_id, 0) * PUNTOS_FICH_PERDIDAS

    # Puntos por referidos (desde user_data - ahora viene de la base de datos)
    puntos += user_data.get("Referidos", 0) * PUNTOS_REF_TOTALES

    # Puntos por piratas y mejoras (desde juego_pirata_data - ahora viene de la base de datos)
    if juego_pirata_data and isinstance(juego_pirata_data, (list, tuple)):
        # juego_pirata_data es una tupla desde la base de datos
        # Extraer el valor numérico de piratas (no la tupla completa)
        piratas = juego_pirata_data[2] if len(juego_pirata_data) > 1 else 0
        # Asegurarse de que es un número, no una tupla
        if isinstance(piratas, (int, float)):
            puntos += piratas * PUNTOS_PIRATAS
        else:
            print(f"⚠️ Valor de piratas no numérico para usuario {usuario_id}: {piratas}")

        # Obtener mejoras desde la tabla mejoras
        mejoras_barco = obtener_registro('mejoras', (usuario_id, 'barco'))
        mejoras_caniones = obtener_registro('mejoras', (usuario_id, 'cañones'))
        mejoras_velas = obtener_registro('mejoras', (usuario_id, 'velas'))
        
        # Puntos por nivel de mejoras - extraer valores numéricos
        nivel_velas = mejoras_velas[2] if mejoras_velas and len(mejoras_velas) > 2 and isinstance(mejoras_velas[2], (int, float)) else 0
        nivel_caniones = mejoras_caniones[2] if mejoras_caniones and len(mejoras_caniones) > 2 and isinstance(mejoras_caniones[2], (int, float)) else 0
        nivel_barco = mejoras_barco[2] if mejoras_barco and len(mejoras_barco) > 2 and isinstance(mejoras_barco[2], (int, float)) else 0
        
        puntos += nivel_velas * PUNTOS_NIVEL_VELAS
        puntos += nivel_caniones * PUNTOS_NIVEL_CANONES
        puntos += nivel_barco * PUNTOS_NIVEL_BARCO

    return puntos
# Lock para operaciones de archivo
minijuegos_lock = asyncio.Lock()

# Función para cargar datos de minijuegos
async def load_minijuegos_datafull():
    async with minijuegos_lock:
        try:
            with open('minijuegos.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}





async def show_medalla(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)
        user_name = query.from_user.full_name

        # Cargar datos de minijuegos desde JSON (se mantiene igual)
        json_minijuegos = await load_minijuegos_datafull()

        if not json_minijuegos:
            print("Error al cargar los datos de minijuegos.")
            await query.edit_message_text("❌ Error al cargar los datos. Inténtalo más tarde.")
            return

        # Obtener todos los usuarios desde la base de datos
        consulta_usuarios = "SELECT id, nombre, medalla FROM usuarios"
        usuarios_db = ejecutar_consulta_segura(consulta_usuarios, obtener_resultados=True)
        
        if not usuarios_db:
            await query.edit_message_text("❌ No se encontraron usuarios en la base de datos.")
            return

        # Convertir a diccionario para fácil acceso
        usuarios_data = {}
        for usuario in usuarios_db:
            usuarios_data[usuario[0]] = {
                'nombre': usuario[1],
                'medalla': usuario[2] or "Sin medalla"
            }

        # Actualizar medallas
        usuarios_notificados = []
        for u_id, u_data in usuarios_data.items():
            # Obtener datos del juego pirata desde la base de datos
            juego_pirata_data = obtener_registro('juego_pirata', u_id)
            
            # Obtener datos de usuario completos para calcular puntos
            usuario_completo = obtener_registro('usuarios', u_id)
            if usuario_completo:
                usuario_dict = {
                    'Nombre': usuario_completo[1] if len(usuario_completo) > 1 else 'Usuario',
                    'Medalla': usuario_completo[6] if len(usuario_completo) > 6 else 'Sin medalla',
                    'Referidos': usuario_completo[3] if len(usuario_completo) > 3 else 0
                }
                
                puntos = await calcular_puntos(u_id, usuario_dict, json_minijuegos, juego_pirata_data)
                nueva_medalla = asignar_medalla(puntos)
                old_medalla = u_data.get("medalla", "Sin medalla")
                
                if old_medalla != nueva_medalla:
                    # Actualizar medalla en la base de datos
                    actualizar_registro('usuarios', u_id, {'medalla': nueva_medalla})
                    usuarios_notificados.append((u_id, u_data.get("nombre", "Usuario"), nueva_medalla))

        # Notificar usuarios con mejor formato
        for u_id, nombre, medalla in usuarios_notificados:
            if medalla != "Sin medalla":
                try:
                    await context.bot.send_message(
                        chat_id=u_id,
                        text=f"""<pre>🎉 ¡LOGRO DESBLOQUEADO! 🎉</pre>

🏅 <b>Nueva Medalla:</b> {medalla}

¡Felicidades {nombre}! Tu dedicación ha sido recompensada.
Sigue participando para alcanzar mayores reconocimientos.""",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"⚠️ Error notificando a {u_id}: {str(e)}")

        # Calcular ranking mejorado
        usuarios_puntos = []
        for u_id, u_data in usuarios_data.items():
            # Obtener datos del juego pirata
            juego_pirata_data = obtener_registro('juego_pirata', u_id)
            
            # Obtener datos completos del usuario para calcular puntos
            usuario_completo = obtener_registro('usuarios', u_id)
            if usuario_completo:
                usuario_dict = {
                    'Nombre': usuario_completo[1] if len(usuario_completo) > 1 else 'Usuario',
                    'Medalla': usuario_completo[6] if len(usuario_completo) > 6 else 'Sin medalla',
                    'Referidos': usuario_completo[3] if len(usuario_completo) > 3 else 0
                }
                
                puntos = await calcular_puntos(u_id, usuario_dict, json_minijuegos, juego_pirata_data)
                usuarios_puntos.append((
                    u_data.get("nombre", "Usuario"),
                    u_data.get("medalla", "Sin medalla"),
                    puntos,
                    u_id
                ))

        usuarios_puntos.sort(key=lambda x: x[2], reverse=True)

        # Datos del usuario actual
        puesto = next((i + 1 for i, (_, _, _, uid) in enumerate(usuarios_puntos) if uid == user_id), 0)
        puntos_usuario = next((p for _, _, p, uid in usuarios_puntos if uid == user_id), 0)
        
        # Obtener medalla actual del usuario desde la base de datos
        usuario_actual = obtener_registro('usuarios', user_id)
        medalla_usuario = usuario_actual[6] if usuario_actual and len(usuario_actual) > 6 else "Sin medalla"

        # Construir mensaje mejorado
        message = f"""
<b>🌟 TU ESTADO ACTUAL 🌟</b>

👤 <b>Usuario:</b> {user_name}
🏅 <b>Medalla:</b> {medalla_usuario}
📊 <b>Posición:</b> #{puesto}
📈 <b>Tus puntos:</b> <code>{puntos_usuario}</code>

<pre>🏆 TOP 5 JUGADORES 🏆</pre>
"""
        for i, (nombre, medalla, puntos, _) in enumerate(usuarios_puntos[:5], 1):
            medal_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
            message += f"\n{medal_emoji} <b>{nombre}</b> - {medalla} (<code>{puntos}</code>)\n"

        # Botones con mejor diseño
        keyboard = [
            [InlineKeyboardButton("⁉️Cómo subir de medalla", callback_data="medallas_detalles")],
            [InlineKeyboardButton("🔚 Menú Principal", callback_data="menu_principal")]
        ]

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"⚠️ Error en show_medalla: {str(e)}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            "🔴 <b>Error en el sistema</b>\n\n"
            "No pudimos procesar tu solicitud. Por favor, inténtalo nuevamente más tarde.",
            parse_mode="HTML"
        )
    
async def medallas_detalles(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        # Mensaje detallado sobre cómo obtener puntos
        detalles_message = """
<blockquote>🏅 Detalles de cómo obtener puntos para subir de medalla:</blockquote>

📊 <b>Rangos de puntos para cada medalla:</b>
"""

        # Mostrar los rangos de puntos para cada medalla
        for medalla, rangos in MEDALLAS_RANGOS.items():
            detalles_message += f"\n🔹 <b>{medalla}</b>:\n"
            for rango in rangos:
                detalles_message += f"   - {rango[0]} a {rango[1]} puntos: {medalla} {rango[2]}\n"

        detalles_message += f"""
 <blockquote>📝Actividades que otorgan puntos:</blockquote>

🎰 <b>Minijuegos:</b>
   - Ganar una apuesta: <code>{PUNTOS_BET_WIN}</code> puntos por cada apuesta Gananda en cualquier minijuego
   - Perder una apuesta: <code>{PUNTOS_BET_LOS}</code>puntos por cada apuesta perdida en cualquier minijuego
   - Ganar CUP: <code>{PUNTOS_FICH_GANADAS}</code> puntos por cada CUP ganando.
   - Perder CUP: <code> -0.00002</code> puntos por cada CUP perdido

👥 <b>Referidos:</b>
   - Total de referidos: <b>{PUNTOS_REF_TOTALES} puntos por cada referido</b>

🏴‍☠️ <b>Juego Pirata:</b>
   - Piratas reclutados: <code>{PUNTOS_PIRATAS} puntos</code>
   - Nivel de velas: <code>{PUNTOS_NIVEL_VELAS} puntos por nivel</code>
   - Nivel de cañones: <code>{PUNTOS_NIVEL_CANONES} puntos por nivel</code>
   - Nivel del barco: <code>{PUNTOS_NIVEL_BARCO} puntos por nivel</code>
"""

        # Teclado para volver al menú principal
        keyboard = [
            [InlineKeyboardButton("🔙 Volver", callback_data="show_medalla")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Enviar el mensaje
        await query.edit_message_text(
            text=detalles_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Error en medallas_detalles: {e}")
        await query.edit_message_text(
            text="❌ Ocurrió un error al mostrar los detalles de las medallas. Inténtalo más tarde.",
            parse_mode="HTML"
        )        

 #Función para obtener el balance de un usuario desde DB
def get_user_balance(user_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT balance FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None                                                
@verificar_bloqueo
async def transferencia_interna(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    # Obtener saldo desde DB
    saldo_disponible = get_user_balance(user_id)

    if saldo_disponible is None:
        await query.edit_message_text("❌ No estás registrado en el sistema.")
        return

    print(f"Usuario {user_id} intentando transferir: {saldo_disponible} CUP")

    if saldo_disponible <= 0:
        await query.edit_message_text("❌ No tienes suficiente saldo para hacer una transferencia.")
        return

    # Pedir ID del destinatario
    await query.edit_message_text("📤 Por favor, ingresa el ID del usuario al que deseas transferir:")
    context.user_data['estado'] = 'esperando_id_destinatario'
    return "esperando_id_destinatario"


# Funciones auxiliares para SQLite
def get_user(user_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nombre, balance FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "Nombre": row[1], "Balance": row[2]}
    return None

def update_user_balance(user_id: str, new_balance: float):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET balance = ? WHERE id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()

# Manejar entrada del ID del destinatario
async def esperando_id_destinatario(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    destinatario_id = update.message.text.strip()

    # Validar que el usuario no se transfiera a sí mismo
    if user_id == destinatario_id:
        await update.effective_message.reply_text("❌ No puedes transferirte a ti mismo. Ingresa otro ID válido.")
        return  # Termina la función aquí para que vuelva a pedir el ID

    destinatario = get_user(destinatario_id)
    if not destinatario:
        await update.effective_message.reply_text("❌ El ID ingresado no existe. Intenta con un ID válido.")
        return

    usuario = get_user(user_id)
    context.user_data['destinatario_id'] = destinatario_id

    mensaje = (
        f"📛Usuario que recibe: <a href='tg://user?id={destinatario_id}'>{destinatario['Nombre']}</a>\n\n"
        f"🆔: <code>{destinatario_id}</code>\n\n"
        f"💰Balance disponible: {usuario['Balance']} \n\n"
        f"<i>🔻¿Cuánto deseas transferir?</i> 💸"
    )
    cancel_keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]]
    reply_markup = InlineKeyboardMarkup(cancel_keyboard)
    await update.effective_message.reply_text(mensaje, parse_mode='HTML', reply_markup=reply_markup)
    context.user_data['estado'] = 'esperando_monto_transferencia'
    return "esperando_monto_transferencia"

# Manejar entrada del monto
async def esperando_monto_transferencia(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    try:
        monto = float(update.message.text.strip())
    except ValueError:
        await update.effective_message.reply_text("❌ El monto ingresado no es válido. Intenta de nuevo.")
        return

    usuario = get_user(user_id)
    if monto > usuario['Balance']:
        await update.effective_message.reply_text("❌ No tienes suficiente saldo para realizar esta transferencia.")
        return

    context.user_data['monto_transferir'] = monto
    destinatario_id = context.user_data['destinatario_id']
    destinatario = get_user(destinatario_id)

    mensaje = (
        f"Vas a transferir <b>{monto} 💸</b> a <a href='tg://user?id={destinatario_id}'>{destinatario['Nombre']}</a>.\n"
        f"ID del destinatario: <code>{destinatario_id}</code>\n"
        f"Saldo disponible: <b>{usuario['Balance']} 💰</b>\n"
        f"¿Confirmas esta transferencia?"
    )
    confirm_keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_transferencia"),
         InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
    ]
    reply_markup = InlineKeyboardMarkup(confirm_keyboard)
    await update.effective_message.reply_text(mensaje, parse_mode='HTML', reply_markup=reply_markup)

# Confirmar transferencia
async def confirmar_transferencia(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    destinatario_id = context.user_data['destinatario_id']
    monto = context.user_data['monto_transferir']

    usuario = get_user(user_id)
    destinatario = get_user(destinatario_id)

    if usuario['Balance'] < monto:
        await query.edit_message_text(
            text=f"❌ Saldo insuficiente\n💰 Balance: {usuario['Balance']} CUP\n💸 Monto: {monto} CUP",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver a intentar", callback_data="transferir_dinero")]])
        )
        return

    # Procesar transferencia
    monto_descuento = monto * 0.05
    monto_recibido = monto - monto_descuento
    update_user_balance(user_id, usuario['Balance'] - monto)
    update_user_balance(destinatario_id, destinatario['Balance'] + monto_recibido)

    # Notificaciones
    usuario = get_user(user_id)
    destinatario = get_user(destinatario_id)

    await context.bot.send_message(
        user_id,
        f"<b>📤 TRANSFERENCIA REALIZADA</b>\n\n"
        f"💸➡️ <b>Enviaste:</b> <code>{monto} CUP</code>\n"
        f"👤 <b>Para:</b> <a href='tg://user?id={destinatario_id}'>{destinatario['Nombre']}</a>\n\n"
        f"📉 <b>Comisión (5%):</b> <code>{monto_descuento} CUP</code>\n"
        f"💰✅ <b>Recibirá:</b> <code>{monto_recibido} CUP</code>\n\n"
        f"🏦 <b>Tu saldo:</b> <code>{usuario['Balance']} CUP</code>",
        parse_mode='HTML'
    )

    await context.bot.send_message(
        destinatario_id,
        f"<b>📥 TRANSFERENCIA RECIBIDA</b>\n\n"
        f"💰✅ <b>Recibiste:</b> <code>{monto_recibido} CUP</code>\n"
        f"👤 <b>De:</b> <a href='tg://user?id={user_id}'>{usuario['Nombre']}</a>\n\n"
        f"📉 <b>Comisión:</b> <code>{monto_descuento} CUP</code>\n"
        f"🏦 <b>Tu saldo:</b> <code>{destinatario['Balance']} CUP</code>",
        parse_mode='HTML'
    )

    await context.bot.send_message(
        chat_id="-1002492508397",
        text=f"<b>🔔 NUEVA TRANSFERENCIA</b>\n\n"
             f"📤 <b>Emisor:</b> <a href='tg://user?id={user_id}'>{usuario['Nombre']}</a>\n"
             f"📥 <b>Receptor:</b> <a href='tg://user?id={destinatario_id}'>{destinatario['Nombre']}</a>\n\n"
             f"💸 <b>Monto enviado:</b> <code>{monto} CUP</code>\n"
             f"📉 <b>Comisión (5%):</b> <code>{monto_descuento} CUP</code>\n"
             f"💰 <b>Monto recibido:</b> <code>{monto_recibido} CUP</code>\n\n"
             f"🏦 <b>Saldo emisor:</b> <code>{usuario['Balance']} CUP</code>\n"
             f"🏦 <b>Saldo receptor:</b> <code>{destinatario['Balance']} CUP</code>",
        parse_mode='HTML'
    )

    await query.edit_message_text(
        text="✅ Transferencia completada exitosamente",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 Ver mi saldo", callback_data="show_balance")]])
    )
# Función para iniciar retiro
async def withdraw(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)

        # Obtener balance desde DB
        row = get_db_record("usuarios", user_id, "Balance, UltimoRetiro")
        user_balance = row[0] if row else 0
        ultimo_retiro_str = row[1] if row and len(row) > 1 else ""

        if user_balance < 250:
            await query.edit_message_text(
                text=(
                    "<blockquote>❌ Balance insuficiente para retirar</blockquote>\n"
                    "⚠️ Mínimo de retiro: <code>250 CUP</code>.\n\n"
                    "🌟 <i>Invita más amigos, quizás ganes un poco más.</i>"
                ),
                parse_mode="HTML"
            )
            return

        # Verificar último retiro (máximo 1 por día)
        if ultimo_retiro_str:
            ultimo_retiro = datetime.strptime(ultimo_retiro_str, '%Y-%m-%d %H:%M:%S')
            tiempo_transcurrido = datetime.now() - ultimo_retiro
            if tiempo_transcurrido.total_seconds() < 86400:  # 24 horas
                tiempo_restante = timedelta(seconds=86400) - tiempo_transcurrido
                horas, resto = divmod(int(tiempo_restante.total_seconds()), 3600)
                minutos = resto // 60
                await query.edit_message_text(
                    text=f"❌ Ya realizaste un retiro hoy. Podrás retirar nuevamente en: {horas:02d}:{minutos:02d}",
                    parse_mode="HTML"
                )
                return

        # Si pasa todas las validaciones
        context.user_data['estado'] = 'esperando_monto_retirar'

        await query.edit_message_text(
            text=f"♦️ Ingresa en un mensaje el monto que deseas retirar.\n\n"
                 f"🏦 Balance actual: {user_balance} CUP",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="show_balance")]
            ])
        )

    except Exception as e:
        logger.error(f"Error en withdraw(): {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Ocurrió un error al intentar procesar tu solicitud de retiro."
        )

@verificar_bloqueo
async def procesar_monto_retiro(update: Update, context: CallbackContext):
    try:
        user_id = str(update.message.from_user.id)
        monto_retiro = float(update.message.text)

        # Obtener datos del usuario
        row = get_db_record("usuarios", user_id, "Balance, UltimoRetiro")
        user_balance = row[0] if row else 0
        ultimo_retiro_str = row[1] if row and len(row) > 1 else ""

        if monto_retiro < 250:
            await update.message.reply_text(
                "❌ El monto mínimo para retirar es 250 CUP",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver a intentar", callback_data="withdraw")]
                ])
            )
            return

        if monto_retiro > 5000:
            await update.message.reply_text(
                "❌ El monto máximo para retirar es 5000 CUP",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver a intentar", callback_data="withdraw")]
                ])
            )
            return

        if monto_retiro > user_balance:
            await update.message.reply_text(
                f"❌ Balance insuficiente. Tu balance actual es: {user_balance} CUP",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver a intentar", callback_data="withdraw")]
                ])
            )
            return

        # Verificar último retiro (máximo 1 por día)
        if ultimo_retiro_str:
            ultimo_retiro = datetime.strptime(ultimo_retiro_str, '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - ultimo_retiro).total_seconds() < 86400:
                tiempo_restante = ultimo_retiro + timedelta(hours=24) - datetime.now()
                horas, resto = divmod(tiempo_restante.seconds, 3600)
                minutos = resto // 60
                await update.message.reply_text(
                    f"❌ Ya realizaste un retiro hoy. Podrás retirar nuevamente en: {horas:02d}:{minutos:02d}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver al menú", callback_data="menu_principal")]
                    ])
                )
                return

        context.user_data['monto_retiro'] = monto_retiro

        await update.message.reply_text(
            "🔹 Selecciona cómo deseas recibir el retiro:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Tarjeta", callback_data="withdraw_tarjeta")],
                [InlineKeyboardButton("📱 Saldo Móvil (EN MANTENIMIENTO)", callback_data="saldo_movil_mantenimiento")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="show_balance")]
            ])
        )
        context.user_data['estado'] = None

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un monto válido (ejemplo: 500)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver a intentar", callback_data="withdraw")]
            ])
        )
    except Exception as e:
        logger.error(f"Error en procesar_monto_retiro: {str(e)}")
        await update.message.reply_text(
            "❌ Ocurrió un error al procesar tu solicitud de retiro"
        )
async def procesar_retiro_saldo(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        
        # Obtener teléfono desde la base de datos usando función segura
        resultado = obtener_registro("depositos", user_id, "telefono")
        telefono = resultado[0] if resultado else "No registrado"
        
        # Obtener el monto guardado en context.user_data
        monto_retiro = context.user_data.get('monto_retiro', 0)
        
        # Verificar si hay número de teléfono registrado
        if telefono == "No registrado" or not telefono:
            await query.edit_message_text(
                text="❌ No tienes un número de teléfono registrado\n\n"
                     "Por favor registra tu teléfono primero para retirar a saldo móvil",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Registrar Teléfono", callback_data="registrar_telefono")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="withdraw")]
                ])
            )
            return
        
        # Mostrar confirmación de retiro
        await query.edit_message_text(
            text=f"📱 Vas a retirar {monto_retiro:.2f} CUP al número de teléfono:\n"
                 f"📲 {telefono}\n\n"
                 "¿Confirmas este retiro?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmar Retiro", callback_data="confirmar_retiro_saldo_movil")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="show_balance")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error en procesar_retiro_saldo: {str(e)}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Ocurrió un error al procesar tu solicitud de retiro"
        )

async def confirm_withdraw(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        
        # Extraer datos de la base de datos usando función segura
        deposito_data = obtener_registro("depositos", user_id, "Payment, telefono")
        metodo_pago = deposito_data[0] if deposito_data else "No especificado"
        
        # Obtener balance del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        user_balance = usuario_data[0] if usuario_data else 0
        
        # Extraer datos del contexto
        monto_retiro = context.user_data.get('monto_retiro', 0)
        
        # Determinar si es retiro por tarjeta o saldo móvil
        if query.data == "confirmar_retiro_tarjeta":
            tipo_retiro = "tarjeta"
            tarjeta = context.user_data.get('tarjeta_retiro', "No especificada")
            ultimos_digitos = tarjeta[-4:] if len(tarjeta) > 4 else tarjeta
            mensaje_detalle = f"💳 Tarjeta: {tarjeta}"
        else:  # confirmar_retiro_saldo
            tipo_retiro = "saldo_movil"
            telefono = deposito_data[1] if deposito_data and len(deposito_data) > 1 else "No registrado"
            mensaje_detalle = f"📱 Teléfono: {telefono}"
        
        # Verificar saldo suficiente
        if monto_retiro > user_balance:
            await query.edit_message_text(
                text=f"❌ Saldo insuficiente\n\n"
                     f"Balance actual: {user_balance:.2f} CUP",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="withdraw")]
                ])
            )
            return
            
        # Construir mensaje de confirmación
        mensaje = (
            f"🔹 <b>CONFIRMACIÓN DE RETIRO</b>\n\n"
            f"💰 <b>Monto:</b> {monto_retiro:.2f} CUP\n"
            f"📦 <b>Método:</b> {metodo_pago.upper()}\n"
            f"📝 <b>Detalles:</b> {mensaje_detalle}\n\n"
            "¿Confirmas este retiro?"
        )
        
        # Mostrar confirmación
        await query.edit_message_text(
            text=mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmar Retiro", callback_data=f"finalizar_retiro_{tipo_retiro}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="show_balance")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error en confirm_withdraw: {str(e)}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Ocurrió un error al procesar tu confirmación"
        )

async def finalizar_retiro(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        tipo_retiro = query.data.split('_')[-1]  # tarjeta o saldo_movil
        
        # Obtener todos los datos necesarios de la base de datos usando función segura
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        balance_actual = usuario_data[0] if usuario_data else 0
        nombre_usuario = usuario_data[1] if usuario_data and len(usuario_data) > 1 else "Usuario desconocido"
        
        # Obtener datos de depósito
        deposito_data = obtener_registro("depositos", user_id, "Payment, telefono, TotalDeposit, TotalRetiro")
        metodo_pago = deposito_data[0] if deposito_data else "No especificado"
        telefono = deposito_data[1] if deposito_data and len(deposito_data) > 1 else None
        total_depositado = deposito_data[2] if deposito_data and len(deposito_data) > 2 else 0
        total_retirado = deposito_data[3] if deposito_data and len(deposito_data) > 3 else 0
        
        monto_retiro = context.user_data.get('monto_retiro', 0)
        tarjeta = context.user_data.get('tarjeta_retiro', None)
        
        # Verificar saldo suficiente
        if monto_retiro > balance_actual:
            await query.edit_message_text("❌ Error: Saldo insuficiente")
            return
        
        # Actualizar balance del usuario y registrar último retiro
        nuevo_balance = balance_actual - monto_retiro
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Actualizar usuario usando función segura
        exito_usuario = actualizar_registro(
            "usuarios", 
            user_id, 
            {
                "Balance": nuevo_balance,
                "UltimoRetiro": fecha_actual
            }
        )
        
        # Actualizar datos de retiro en la tabla depositos
        nuevo_total_retirado = total_retirado + monto_retiro
        exito_deposito = actualizar_registro(
            "depositos", 
            user_id, 
            {
                "TotalRetiro": nuevo_total_retirado,
                "RetiroPendiente": monto_retiro
            }
        )
        
        if not exito_usuario or not exito_deposito:
            await query.edit_message_text("❌ Error al procesar el retiro")
            return
        
        # Mensaje al usuario (pendiente de aprobación)
        detalle = ""
        if tipo_retiro == "tarjeta" and tarjeta:
            detalle = f"💳 Tarjeta: {tarjeta}"
        elif telefono:
            detalle = f"📱 Teléfono: {telefono}"
        
        await query.edit_message_text(
            text=f"<pre>✅ SOLICITUD DE RETIRO ENVIADA</pre>\n\n"
                 f"▫️ <b>Monto:</b> {monto_retiro:.2f} CUP\n"
                 f"▫️ <b>Método:</b> {metodo_pago.upper()}\n"
                 f"▫️ <b>Detalles:</b> {detalle}\n\n"
                 f"⏳ <i>Tu retiro ha sido enviado a un administrador, será pagado según el tiempo estipulado en las reglas.</i>\n\n"
                 f"🕒 <i>Hora de solicitud:</i> {fecha_actual}",
            parse_mode="HTML"
        )
        
        # Calcular ganancia/pérdida
        ganancia_perdida = total_depositado - total_retirado
        
        # Notificación detallada al administrador
        mensaje_admin = (
            f"<pre>⚠️ NUEVA SOLICITUD DE RETIRO</pre>\n\n"
            f"▫️ <b>Usuario:</b> {nombre_usuario}\n"
            f"▫️ <b>ID:</b> <code>{user_id}</code>\n"
            f"▫️ <b>Monto:</b> {monto_retiro:.2f} CUP\n"
            f"▫️ <b>Método:</b> {metodo_pago.upper()}\n"
            f"▫️ <b>Tipo:</b> {tipo_retiro.replace('_', ' ').title()}\n"
            f"▫️ <b>Detalles:</b> <code>{detalle}</code>\n\n"
            f"📊 <b>Estadísticas del usuario:</b>\n"
            f"├ Balance anterior: {balance_actual:.2f} CUP\n"
            f"├ Nuevo balance: {nuevo_balance:.2f} CUP\n"
            f"├ Total depositado: {total_depositado:.2f} CUP\n"
            f"├ Total retirado: {nuevo_total_retirado:.2f} CUP\n"
            f"└ Ganancia/Pérdida: {ganancia_perdida - monto_retiro:.2f} CUP\n\n"
            f"🕒 <i>Hora de solicitud:</i> {fecha_actual}"
        )
        
        # Botones de aprobación para el admin
        keyboard = [
            [InlineKeyboardButton("✅ Aprobar Retiro", callback_data=f"aprobar_retiro_{user_id}")],
            [InlineKeyboardButton("❌ Rechazar Retiro", callback_data=f"rechazar_retiro_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=mensaje_admin,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
        # Limpiar datos temporales
        context.user_data.pop('monto_retiro', None)
        context.user_data.pop('tarjeta_retiro', None)
            
    except Exception as e:
        logger.error(f"Error en finalizar_retiro: {str(e)}")
        await query.edit_message_text(
            text="❌ Ocurrió un error al procesar tu solicitud de retiro. Por favor contacta al soporte."
        )
# Función para procesar el retiro por tarjeta
async def withdraw_tarjeta(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        
        # Obtener monto del retiro
        monto_retiro = context.user_data.get('monto_retiro', 0)
        
        if monto_retiro <= 0:
            await query.edit_message_text("❌ Error: Monto de retiro no válido")
            return
            
        # Obtener balance actual usando función segura
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        if not usuario_data:
            await query.edit_message_text("❌ Error: Usuario no encontrado")
            return
            
        balance_actual = usuario_data[0]
        
        if monto_retiro > balance_actual:
            await query.edit_message_text("❌ Error: Balance insuficiente")
            return
            
        # Actualizar balance y fecha de último retiro usando función segura
        nuevo_balance = balance_actual - monto_retiro
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        exito = actualizar_registro(
            "usuarios", 
            user_id, 
            {
                "Balance": nuevo_balance,
                "UltimoRetiro": fecha_actual
            }
        )
        
        if not exito:
            await query.edit_message_text("❌ Error al procesar el retiro")
            return
        
        # Mensaje de éxito
        await query.edit_message_text(
            f"✅ Retiro procesado exitosamente!\n\n"
            f"• Monto retirado: {monto_retiro} CUP\n"
            f"• Nuevo balance: {nuevo_balance} CUP\n"
            f"• Método: Tarjeta\n\n"
            f"💳 Por favor proporciona los detalles de tu tarjeta en un mensaje privado al administrador."
        )
        
        # Limpiar datos temporales
        if 'monto_retiro' in context.user_data:
            del context.user_data['monto_retiro']
            
    except Exception as e:
        logger.error(f"Error en withdraw_tarjeta: {str(e)}")
        await query.edit_message_text("❌ Ocurrió un error al procesar tu retiro")
# Nueva función para manejar el callback de saldo móvil en mantenimiento
async def saldo_movil_mantenimiento_callback(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            text="⚠️ El retiro por Saldo Móvil se encuentra actualmente desabilitado gracias a las nuevas políticas de ETECSA💩.\n\n"
                 "Por favor selecciona otra opción de retiro.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Retirar a Tarjeta", callback_data="withdraw_tarjeta")],
                [InlineKeyboardButton("🔙 Volver", callback_data="withdraw")]
            ])
        )
    except Exception as e:
        logger.error(f"Error en saldo_movil_mantenimiento_callback: {str(e)}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Ocurrió un error al procesar tu solicitud"
        )
        
        
async def tarjeta_retiro_callback(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        context.user_data['estado'] = 'esperando_tarjeta_retiro'
        
        await query.edit_message_text(
            text="💳 Por favor ingresa el número de tarjeta donde recibirás el dinero (16 dígitos):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="show_balance")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error en tarjeta_retiro_callback: {str(e)}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Ocurrió un error al procesar tu solicitud"
        )        
        
async def procesar_tarjeta_retiro(update: Update, context: CallbackContext):
    try:
        user_id = str(update.message.from_user.id)
        tarjeta = update.message.text.strip()
        
        # Validar que sea numérico y tenga 8 dígitos
        if not tarjeta.isdigit() or len(tarjeta) != 16:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ El número de tarjeta debe tener exactamente 16 dígitos numéricos",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver a intentar", callback_data="withdraw_tarjeta")]
                ])
            )
            return
            
        # Guardar tarjeta en context.user_data
        context.user_data['tarjeta_retiro'] = tarjeta
        
        # Obtener monto guardado previamente
        monto_retiro = context.user_data.get('monto_retiro', 0)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Tarjeta registrada correctamente\n\n"
                 f"♦️ Vas a recibir {monto_retiro:.2f} CUP en la tarjeta: {tarjeta}\n\n"
                 "¿Confirmas el retiro?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmar Retiro", callback_data="confirmar_retiro_tarjeta")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="show_balance")]
            ])
        )
        
        # Limpiar estado
        context.user_data['estado'] = None
        
    except Exception as e:
        logger.error(f"Error en procesar_tarjeta_retiro: {str(e)}")
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="❌ Ocurrió un error al procesar tu tarjeta"
        )        
async def accept_withdraw(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        # Extraer el user_id del callback_data
        user_id = query.data.split("_")[-1]

        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Nombre")
        deposito_data = obtener_registro("depositos", user_id, "Payment, telefono, RetiroPendiente")
        
        # Verificar que los datos existen
        if not usuario_data or not deposito_data:
            await query.edit_message_text("❌ Error: Usuario no encontrado en la base de datos")
            return
        
        user_name = usuario_data[0] if usuario_data else "Desconocido"
        payment_method = deposito_data[0] if deposito_data else "No especificado"
        monto_retiro = context.user_data.get('monto_retiro', deposito_data[2] if len(deposito_data) > 2 else 0)
        telefono = deposito_data[1] if len(deposito_data) > 1 else "No especificado"
        
        # Obtener detalles del retiro
        if "tarjeta_retiro" in context.user_data:
            detalles = f"💳 Tarjeta: {context.user_data['tarjeta_retiro']}"
        else:
            detalles = f"📱 Teléfono: {telefono}"

        # Limpiar el retiro pendiente en la base de datos
        exito = actualizar_registro(
            "depositos", 
            user_id, 
            {"RetiroPendiente": 0}
        )
        
        if not exito:
            await query.edit_message_text("❌ Error al actualizar la base de datos")
            return

        # Mensaje actualizado para el administrador (editando el mensaje existente)
        admin_message = (
            f"<pre>✅ RETIRO PAGADO</pre>\n\n"
            f"▫️ <b>Usuario:</b> {user_name}\n"
            f"▫️ <b>ID:</b> <code>{user_id}</code>\n"
            f"▫️ <b>Monto:</b> {monto_retiro:.2f} CUP\n"
            f"▫️ <b>Método:</b> {payment_method.upper()}\n"
            f"▫️ <b>Detalles:</b> {detalles}\n\n"
            f"🕒 <i>Hora de pago:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Editar el mensaje original (quitando los botones)
        await query.edit_message_text(
            text=admin_message,
            parse_mode="HTML"
        )

        # Mensaje para el usuario
        user_message = (
            f"<pre>✅ RETIRO PAGADO</pre>\n\n"
            f"▫️ <b>Monto:</b> {monto_retiro:.2f} CUP\n"
            f"▫️ <b>Método:</b> {payment_method.upper()}\n\n"
            f"🕒 <i>Hora de pago:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Gracias por usar nuestros servicios, agradecería encarecidamente que confirme qué recibió el dinero aquí."
        )

        # Crear botón para confirmar recepción
        keyboard = [[InlineKeyboardButton("✅ Dejar comentario", url="https://t.me/CubaPlayCANAL/8360")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Enviar notificación al usuario
        await context.bot.send_message(
            chat_id=user_id,
            text=user_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

        # Limpiar datos temporales
        context.user_data.pop('monto_retiro', None)
        context.user_data.pop('tarjeta_retiro', None)

    except Exception as e:
        logger.error(f"Error en accept_withdraw: {str(e)}")
        await query.edit_message_text(
            text="❌ Ocurrió un error al procesar el pago del retiro",
            parse_mode="HTML"
        )

async def reject_withdraw(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()

        user_id = query.data.split("_")[-1]
        
        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Nombre")
        deposito_data = obtener_registro("depositos", user_id, "Payment, RetiroPendiente")
        
        # Verificar que los datos existen
        if not usuario_data or not deposito_data:
            await query.edit_message_text("❌ Error: Usuario no encontrado en la base de datos")
            return
        
        user_name = usuario_data[0] if usuario_data else "Desconocido"
        payment_method = deposito_data[0] if deposito_data else "No especificado"
        monto_retiro = context.user_data.get('monto_retiro', deposito_data[1] if len(deposito_data) > 1 else 0)

        # Devolver el dinero al usuario y limpiar el retiro pendiente
        usuario_actual = obtener_registro("usuarios", user_id, "Balance")
        if usuario_actual:
            balance_actual = usuario_actual[0]
            nuevo_balance = balance_actual + monto_retiro
            
            # Actualizar balance y limpiar retiro pendiente
            exito_usuario = actualizar_registro(
                "usuarios", 
                user_id, 
                {"Balance": nuevo_balance}
            )
            
            exito_deposito = actualizar_registro(
                "depositos", 
                user_id, 
                {"RetiroPendiente": 0}
            )
            
            if not exito_usuario or not exito_deposito:
                await query.edit_message_text("❌ Error al actualizar la base de datos")
                return

        # Mensaje para admin (editando el existente)
        admin_message = (
            f"<pre>❌ RETIRO RECHAZADO</pre>\n\n"
            f"▫️ <b>Usuario:</b> {user_name}\n"
            f"▫️ <b>ID:</b> <code>{user_id}</code>\n"
            f"▫️ <b>Monto:</b> {monto_retiro:.2f} CUP\n"
            f"▫️ <b>Método:</b> {payment_method.upper()}\n\n"
            f"🕒 <i>Hora de rechazo:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await query.edit_message_text(
            text=admin_message,
            parse_mode="HTML"
        )

        # Mensaje para el usuario
        user_message = (
            f"<pre>❌ RETIRO RECHAZADO</pre>\n\n"
            f"▫️ <b>Monto:</b> {monto_retiro:.2f} CUP\n"
            f"▫️ <b>Método:</b> {payment_method.upper()}\n\n"
            f"ℹ️ <i>Tu solicitud de retiro ha sido rechazada por el administrador.</i>\n\n"
            f"💰 <i>El monto ha sido devuelto a tu balance.</i>\n\n"
            f"Para más información contacta al soporte."
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=user_message,
            parse_mode="HTML"
        )

        # Limpiar datos temporales
        context.user_data.pop('monto_retiro', None)
        context.user_data.pop('tarjeta_retiro', None)

    except Exception as e:
        logger.error(f"Error en reject_withdraw: {str(e)}")
        await query.edit_message_text(
            text="❌ Ocurrió un error al rechazar el retiro",
            parse_mode="HTML"
        )
# Función para el botón "🔙 Menu principal"
@verificar_bloqueo
@marca_tiempo
async def handle_menu_principal(update: Update, context: CallbackContext):
    try:
        query = update.callback_query  
        await query.answer()  

        # Limpiar el contexto del usuario
        context.bot_data['conversation_active'] = False  
        context.user_data['estado'] = None                        
        await query.edit_message_text(" Volviendo al menú principal...")

        keyboard = [
            [InlineKeyboardButton("💰 Mi Saldo", callback_data="Mi Saldo"),
             InlineKeyboardButton("🎰 La bolita", callback_data="La_bolita")],
            [InlineKeyboardButton("💥 Invita y Gana 💥", callback_data="Invita_Gana")],
            [InlineKeyboardButton("🎮 Minijuegos", callback_data="Minijuegos"),
             InlineKeyboardButton("⚽ Apuestas", callback_data="mostrar_tipos_apuestas")],
            [InlineKeyboardButton("👨‍💻 Tareas Pagadas 👨‍💻", callback_data="Tareas_Pagadas")],
            [InlineKeyboardButton("🆘 Soporte", callback_data="menu_soporte"),
             InlineKeyboardButton("🚔 Reglas", callback_data="Reglas")],
            [InlineKeyboardButton("🔮 Pronósticos 🔮", callback_data="Pronosticos")],
            [InlineKeyboardButton("🎁 Bono diario 🎁", callback_data="bono_diario")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        consejo_aleatorio = random.choice(consejo)

        await query.edit_message_text(
            text=f"¡Has vuelto al Menu Principal! 💫\n\n<b>Selecciona una opción del menú para empezar:</b>\n\n🌟<blockquote>{consejo_aleatorio}</blockquote>",
            parse_mode="HTML",  
            reply_markup=reply_markup
        )

        return ConversationHandler.END  

    except Exception as e:
        logger.error(f"Error al manejar el botón 'Menu principal': {e}")




# Función para cargar datos de minijuegos
async def load_minijuegos_data(user_id: str):
    try:
        with open(MINIJUEGOS_FILE, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    except Exception as e:
        print(f"Error al cargar minijuegos.json: {e}")
        data = {}

    # Lista de todos los minijuegos, incluyendo "DUELO"
    minijuegos = ["ALTA BAJA", "BUSCAMINAS", "BLACKJACK", "PIEDRA PAPEL TIJERA", "ABRE COFRES", "DUELO"]

    # Inicializar datos para cada minijuego
    for minijuego in minijuegos:
        if minijuego not in data:
            data[minijuego] = {
                "FichGanadas": {},
                "FichPerdidas": {},
                "BetLost": {},
                "BetWin": {}
            }
        if user_id not in data[minijuego]["FichGanadas"]:
            data[minijuego]["FichGanadas"][user_id] = 0
        if user_id not in data[minijuego]["FichPerdidas"]:
            data[minijuego]["FichPerdidas"][user_id] = 0
        if user_id not in data[minijuego]["BetLost"]:
            data[minijuego]["BetLost"][user_id] = 0
        if user_id not in data[minijuego]["BetWin"]:
            data[minijuego]["BetWin"][user_id] = 0

    # Guardar los datos actualizados
    await save_minijuegos_data(data)
    return data


@verificar_bloqueo
@marca_tiempo
async def minijuegos(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)

    try:
        # Obtener balance desde la base de datos
        consulta_balance = "SELECT balance FROM usuarios WHERE id = ?"
        resultado = ejecutar_consulta_segura(consulta_balance, (user_id,), obtener_resultados=True)

        balance = resultado[0][0] if resultado else 0

        # Crear botones del menú con juegos web
        keyboard = [
            [
                InlineKeyboardButton("♠️ POKER (off)", callback_data="poker"),
                InlineKeyboardButton("🏆 Fantasy Game ⚽", callback_data="killjuego_fantasy")
            ],
            [
                create_web_app_button(user_id, "/juego_alta_baja", "⬆️ Alta - Baja ⬇️"),
                InlineKeyboardButton("🚀 Crash (off)", callback_data="mantenimiento"),
            ],
            [
                create_web_app_button(user_id, "/juego_pirata", "🏴‍☠ PirateKing 🏴‍☠ (recomendado)"),
            ],
            [
                create_web_app_button(user_id, "/piedra-papel-tijera", "🪨 Piedra Papel Tijera ✂️"),
            ],
            [
                InlineKeyboardButton("💎 Abrir Cofre (off)", callback_data="mantenimiento"),
                InlineKeyboardButton("♣️ BlackJack (off)", callback_data="mantenimiento"),
            ],
            [
                InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_principal"),
            ],
        ]

        # Filtrar None values en caso de que algún botón no se genere
        keyboard = [[btn for btn in row if btn is not None] for row in keyboard]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Mensaje con formato HTML actualizado
        response_text = (
            f"<pre>🎮 MENÚ DE MINIJUEGOS</pre>\n\n"
            f"💰 <b>Saldo disponible:</b> <code>${balance:,.2f}</code>\n\n"
            "🎲 <b>Minijuegos</b> - Diversión y muchas ganancias\n\n"
            "<i>Elije una opción para comenzar:</i>"
        )

        await query.edit_message_text(
            text=response_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"Error en minijuegos: {e}")
        await query.answer("❌ Ocurrió un error al cargar el menú de minijuegos.")
        await query.edit_message_text(
            "⚡ <b>¡Error al cargar el menú de minijuegos!</b>\n\n"
            "Por favor, intenta nuevamente más tarde.",
            parse_mode="HTML"
        )



# Función para iniciar el juego
async def alta_baja(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        text=(
            "<blockquote>🎲 Juego: Alta o Baja 🎲</blockquote>\n\n"
            "🔻 <i>Elige con qué deseas jugar:</i>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Bono", callback_data="method_bono")],
            [InlineKeyboardButton("💲 Balance", callback_data="method_balance")],
            [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
        ])
    )

# Función para establecer el método de pago
async def choose_payment_method(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Guardar el método de pago seleccionado
    method_data = query.data  # "method_bono" o "method_balance"
    context.user_data["metodo_pago"] = method_data.split("_")[1]

    await query.edit_message_text(
        text=(
            "<blockquote>🎲 Juego: Alta o Baja 🎲</blockquote>\n\n"
            "<pre>Selecciona tu apuesta:\n"
            "⬆️ <b>Alta:</b> Más de 50\n"
            "⬇️ <b>Baja:</b> Menos de 50</pre>\n\n"
            "<i>Elige el monto a apostar:</i>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💲10 CUP", callback_data="bet_10"),
                InlineKeyboardButton("💲30 CUP", callback_data="bet_30"),
                InlineKeyboardButton("💲50 CUP", callback_data="bet_50"),
            ],
            [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
        ])
    )

# Función para establecer el monto de la apuesta
async def set_bet_amount(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Guardar el monto de la apuesta
    bet_data = query.data  # "bet_10", "bet_30", "bet_50"
    bet_amount = int(bet_data.split("_")[1])
    context.user_data["bet_amount"] = bet_amount

    await query.edit_message_text(
        text=(
            "<blockquote>🎲 Juego: Alta o Baja 🎲</blockquote>\n\n"
            f"💵 <b>Monto seleccionado:</b> <code>{bet_amount} CUP</code>\n\n"
            "<i>Elige tu opción:</i>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬆️ Alta", callback_data="alta"),
                InlineKeyboardButton("⬇️ Baja", callback_data="baja"),
            ],
            [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
        ])
    )

# Función principal del juego
async def handle_alta_baja(update: Update, context: CallbackContext):
   
    lock_minijuegos = asyncio.Lock()
    
    async with lock_minijuegos:  # Solo necesitamos el lock de minijuegos ahora
        query = update.callback_query
        user_id = str(query.from_user.id)
        user_name = query.from_user.first_name
        choice = query.data  # "alta" o "baja"

        # Obtener la apuesta seleccionada
        bet_amount = context.user_data.get("bet_amount", 10)
        metodo_pago = context.user_data.get("metodo_pago", "balance")  # "bono" o "balance"

        # Obtener datos del usuario desde la base de datos usando funciones auxiliares
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
        
        if not usuario_data:
            await query.answer("⚠️ No tienes datos registrados. Usa el comando /start para registrarte.", show_alert=True)
            return

        # Cargar solo datos de minijuegos desde JSON
        minijuegos_data = await load_minijuegos_datafull()
        
        balance_actual = usuario_data[0]
        bono_usuario = bono_data[0] if bono_data else 0

        # Verificar saldo según el método de pago
        if metodo_pago == "bono" and bono_usuario < bet_amount:
            await query.edit_message_text(
                text=(
                    "😞 Bono insuficiente, por favor recarga antes de jugar.\n\n"
                    f"🎁 Tu bono es de <code>{bono_usuario} CUP.</code>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Recargar", callback_data="recargar")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
                ])
            )
            return
        elif metodo_pago == "balance" and balance_actual < bet_amount:
            await query.edit_message_text(
                text=(
                    "😞 Balance insuficiente, por favor deposita antes de jugar.\n\n"
                    f"💰 Tu balance es de <code>{balance_actual} CUP.</code>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Depositar", callback_data="depositar")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
                ])
            )
            return

        # Animación simulada (conteo 3...2...1)
        try:
            await query.edit_message_text("🎲 ¡Lanzando el dado! ⚡️")
            await asyncio.sleep(0.5)
            await query.edit_message_text("🎲 ¡Prepárate! 🔥")
            await asyncio.sleep(0.5)
            await query.edit_message_text("🎲 ¡Listo! 💥")
            await asyncio.sleep(0.5)
        except Exception as e:
            await query.answer(f"⚠️ Error en la animación: {str(e)}", show_alert=True)
            return

        # Generar número aleatorio y resultado
        try:
            if choice == "alta":
                random_number = random.randint(0, 85)
            elif choice == "baja":
                random_number = random.randint(15, 100)
            else:
                await query.answer("⚠️ Error: Opción inválida.", show_alert=True)
                return
        except Exception as e:
            await query.answer(f"⚠️ Error al generar el número aleatorio: {str(e)}", show_alert=True)
            return

        result = "baja" if random_number <= 50 else "alta"
        game_result = "✅ Ganaste" if choice == result else "❌ Perdiste"

        # Inicializar estructura ALTA BAJA si no existe
        if "ALTA BAJA" not in minijuegos_data:
            minijuegos_data["ALTA BAJA"] = {
                "FichGanadas": {},
                "FichPerdidas": {},
                "BetLost": {},
                "BetWin": {}
            }

        # Obtener datos actuales o inicializar a 0
        alta_baja_data = minijuegos_data["ALTA BAJA"]
        current_ganadas = alta_baja_data["FichGanadas"].get(user_id, 0)
        current_perdidas = alta_baja_data["FichPerdidas"].get(user_id, 0)
        current_betwin = alta_baja_data["BetWin"].get(user_id, 0)
        current_betlost = alta_baja_data["BetLost"].get(user_id, 0)

        # Actualizar saldo según el método de pago usando funciones de base de datos
        if game_result == "✅ Ganaste":
            if metodo_pago == "bono":
                # Actualizar bono - ganancia
                exito_bono = actualizar_registro(
                    "bono_apuesta", 
                    user_id, 
                    {
                        "Bono": bono_usuario + bet_amount,
                        "Rollover_requerido": (bono_data[1] if bono_data and len(bono_data) > 1 else 0) + bet_amount
                    }
                )
            else:
                # Actualizar balance - ganancia
                exito_balance = actualizar_registro(
                    "usuarios", 
                    user_id, 
                    {"Balance": balance_actual + bet_amount}
                )
            
            # Actualizar estadísticas de minijuegos (ganador)
            alta_baja_data["FichGanadas"][user_id] = current_ganadas + bet_amount
            alta_baja_data["BetWin"][user_id] = current_betwin + 1
            
        else:
            if metodo_pago == "bono":
                # Actualizar bono - pérdida
                exito_bono = actualizar_registro(
                    "bono_apuesta", 
                    user_id, 
                    {"Bono": bono_usuario - bet_amount}
                )
            else:
                # Actualizar balance - pérdida
                exito_balance = actualizar_registro(
                    "usuarios", 
                    user_id, 
                    {"Balance": balance_actual - bet_amount}
                )
            
            # Actualizar estadísticas de minijuegos (perdedor)
            alta_baja_data["FichPerdidas"][user_id] = current_perdidas + bet_amount
            alta_baja_data["BetLost"][user_id] = current_betlost + 1

        # Guardar solo los datos de minijuegos en JSON
        await save_minijuegos_data(minijuegos_data)

        # Obtener el nuevo saldo actualizado desde la base de datos
        if metodo_pago == "bono":
            nuevo_bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
            saldo_restante = nuevo_bono_data[0] if nuevo_bono_data else bono_usuario
        else:
            nuevo_balance_data = obtener_registro("usuarios", user_id, "Balance")
            saldo_restante = nuevo_balance_data[0] if nuevo_balance_data else balance_actual

        # Mensaje de resultado al usuario
        message = (
            f"<blockquote>{game_result}</blockquote>\n\n"
            f"📊 Salió el número: <code>{random_number}</code>\n\n"
            f"💵 Monto apostado: <code>{bet_amount} CUP</code>\n"
            f"🎯 Método de pago: <code>{'Bono' if metodo_pago == 'bono' else 'Balance'}</code>\n"
            f"💰 Saldo restante: <code>{saldo_restante} CUP</code>\n\n"
            "<i>¿Quieres jugar otra vez?</i>"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("💲10 CUP", callback_data="bet_10"),
                    InlineKeyboardButton("💲30 CUP", callback_data="bet_30"),
                    InlineKeyboardButton("💲50 CUP", callback_data="bet_50"),
                ],
                [
                    InlineKeyboardButton("⬆️ Alta", callback_data="alta"),
                    InlineKeyboardButton("⬇️ Baja", callback_data="baja"),
                ],
                [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
            ]),
            parse_mode="HTML"
        )

        # Enviar notificación al grupo
        group_message = (
            f"<blockquote>🎮 ALTA/BAJA 🎮</blockquote>\n"
            f"👤 <a href='tg://user?id={user_id}'>{user_name}</a>\n"
            f"🎲 <b>Jugada:</b> {choice.capitalize()}\n"
            f"💵 <b>Monto:</b> {bet_amount} CUP\n"
            f"🎯 <b>Método de pago:</b> {'Bono' if metodo_pago == 'bono' else 'Balance'}\n"
            f"💰 <b>Saldo actual:</b> <code>{saldo_restante} CUP</code>\n"
            f"<b>{game_result}:</b> {bet_amount} CUP"
        )

        await context.bot.send_message(
            chat_id=REGISTRO_MINIJUEGOS,
            text=group_message,
            parse_mode="HTML"
        )
# Función principal del juego
async def Piedra_Papel_Tijera(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🎮 Elige con qué deseas jugar:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Bono", callback_data="ppt_method_bono")],
            [InlineKeyboardButton("💲 Balance", callback_data="ppt_method_balance")],
            [InlineKeyboardButton("🔙 Volver", callback_data="Minijuegos")]
        ])
    )

async def confirmar_metodo_ppt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    method = query.data.split("_")[-1]  # "bono" o "balance"
    context.user_data["metodo_pago_ppt"] = method

    # Obtener saldo desde la base de datos usando funciones auxiliares
    if method == "bono":
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
        saldo = bono_data[0] if bono_data else 0
    else:
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        saldo = usuario_data[0] if usuario_data else 0
    
    if saldo < 50:
        tipo = "bono" if method == "bono" else "balance"
        await query.edit_message_text(
            text=f"❌ No tienes suficiente {tipo} (necesitas 50 CUP)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="Minijuegos")]])
        )
        return

    await query.edit_message_text(
        text="🎮 Al buscar partida, apostarás 50 CUP.\n¿Estás de acuerdo?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_juego_ppt")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="minijuegos")]
        ])
    )
    
async def confirmar_juego_ppt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    lock_minijuegos = asyncio.Lock()
    
    async with lock_minijuegos:  # Solo necesitamos el lock de minijuegos
        try:
            if not update.callback_query:
                print("⚠️ Error: No se recibió un callback válido.")
                return

            user_id = str(update.effective_user.id)
            partidas = context.bot_data.setdefault("partidas", {})
            
            # Verificar saldo suficiente antes de crear la partida
            metodo = context.user_data.get("metodo_pago_ppt", "balance")
            
            # Obtener saldo desde la base de datos
            if metodo == "bono":
                bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
                saldo_disponible = bono_data[0] if bono_data else 0
                rollover_actual = bono_data[1] if bono_data and len(bono_data) > 1 else 0
            else:
                usuario_data = obtener_registro("usuarios", user_id, "Balance")
                saldo_disponible = usuario_data[0] if usuario_data else 0
            
            if saldo_disponible < 50:
                await update.callback_query.answer(
                    text="❌ Saldo insuficiente para jugar. Recarga tu balance primero.",
                    show_alert=True
                )
                return

            # Crear nueva partida
            partidas[user_id] = {
                "jugador_1": user_id,
                "jugador_2": "7106422817",  # ID del bot
                "jugada_1": None,
                "jugada_2": None,
                "estado": "en curso",
                "metodo_pago": metodo
            }

            # Descontar apuesta usando funciones de base de datos
            if metodo == "bono":
                # Actualizar bono y rollover
                exito = actualizar_registro(
                    "bono_apuesta", 
                    user_id, 
                    {
                        "Bono": saldo_disponible - 50,
                        "Rollover_requerido": rollover_actual + (50 * 4)
                    }
                )
            else:
                # Actualizar balance
                exito = actualizar_registro(
                    "usuarios", 
                    user_id, 
                    {"Balance": saldo_disponible - 50}
                )
            
            if not exito:
                await update.callback_query.answer(
                    text="❌ Error al procesar la apuesta. Inténtalo de nuevo.",
                    show_alert=True
                )
                return

            # Mostrar opciones de juego
            oponente_nombre = random.choice(nombres_aleatorios)
            await update.callback_query.edit_message_text(
                text=f"⚔️ Tu oponente es {oponente_nombre}\n\n💵 Apuesta: 50 CUP ({'🎁 Bono' if metodo == 'bono' else '💲 Balance'})",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🪨 Piedra", callback_data="piedra")],
                    [InlineKeyboardButton("📜 Papel", callback_data="papel")],
                    [InlineKeyboardButton("✂️ Tijera", callback_data="tijera")]
                ])
            )

        except Exception as e:
            print(f"⚠️ Error inesperado en confirmar_juego_ppt: {e}")
            await update.callback_query.answer(
                text="❌ Ocurrió un error al iniciar el juego. Inténtalo de nuevo.",
                show_alert=True
            )
def seleccionar_jugada_con_probabilidad(jugada_usuario):

    if jugada_usuario == "piedra":
        # Probabilidades si el usuario elige piedra
        jugadas = ["piedra", "papel", "tijera"]
        probabilidades = [0.20, 0.5, 0.3]
    elif jugada_usuario == "papel":
        # Probabilidades si el usuario elige papel
        jugadas = ["piedra", "papel", "tijera"]
        probabilidades = [0.3, 0.2, 0.5]
    elif jugada_usuario == "tijera":
        # Probabilidades si el usuario elige tijera
        jugadas = ["piedra", "papel", "tijera"]
        probabilidades = [0.5, 0.3, 0.2]
    else:
        # Manejo de error por elección inesperada
        return random.choice(["piedra", "papel", "tijera"])

    # Seleccionar jugada basada en las probabilidades
    return random.choices(jugadas, weights=probabilidades, k=1)[0]    


async def manejar_jugada(update, context):
    user_id = str(update.effective_user.id)
    partida = context.bot_data.get("partidas", {}).get(user_id)

    if not partida:
        await update.callback_query.edit_message_text("❌ No estás en una partida activa.")
        return

    jugada_usuario = update.callback_query.data  # Esto obtiene la jugada del usuario (piedra, papel, tijera)

    # Asigna la jugada del jugador 1
    if partida["jugador_1"] == user_id:
        partida["jugada_1"] = jugada_usuario
    else:
        partida["jugada_2"] = jugada_usuario

    # Llamar a la función para obtener la jugada del oponente con probabilidades
    jugada_oponente = seleccionar_jugada_con_probabilidad(jugada_usuario)

    # Asigna la jugada del oponente (en este caso solo si el oponente es automático)
    if partida["jugador_2"] == "7106422817":  # Oponente automático
        partida["jugada_2"] = jugada_oponente

    # Verificar si ambos jugadores han realizado su jugada
    if partida["jugada_1"] and partida["jugada_2"]:
        await finalizar_partida(context, partida)

async def finalizar_partida(context, partida):
    try:
        user_id = partida["jugador_1"]
        metodo = partida["metodo_pago"]
        
        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        if not usuario_data:
            print(f"⚠️ Usuario {user_id} no encontrado en la base de datos")
            return
            
        nombre = usuario_data[1] if len(usuario_data) > 1 else "Usuario"
        
        # Obtener datos de bono si es necesario
        if metodo == "bono":
            bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
            saldo_actual = bono_data[0] if bono_data else 0
            rollover_actual = bono_data[1] if bono_data and len(bono_data) > 1 else 0
        else:
            saldo_actual = usuario_data[0] if usuario_data else 0

        # Cargar solo datos de minijuegos desde JSON
        minijuegos_data = await load_minijuegos_datafull()
        
        # Determinar resultado
        ganador = determinar_ganador(partida["jugada_1"], partida["jugada_2"])

        # Inicializar estructura si no existe
        if "PIEDRA PAPEL TIJERA" not in minijuegos_data:
            minijuegos_data["PIEDRA PAPEL TIJERA"] = {
                "FichGanadas": {},
                "FichPerdidas": {},
                "BetLost": {},
                "BetWin": {}
            }

        # Obtener datos actuales o inicializar a 0
        ppt_data = minijuegos_data["PIEDRA PAPEL TIJERA"]
        current_ganadas = ppt_data["FichGanadas"].get(user_id, 0)
        current_perdidas = ppt_data["FichPerdidas"].get(user_id, 0)
        current_betwin = ppt_data["BetWin"].get(user_id, 0)
        current_betlost = ppt_data["BetLost"].get(user_id, 0)

        # Manejar ganador
        if ganador == 1:  # Gana usuario
            premio = 90  # Premio tanto para bono como para balance
            if metodo == "bono":
                # Actualizar bono y rollover
                exito = actualizar_registro(
                    "bono_apuesta", 
                    user_id, 
                    {
                        "Bono": saldo_actual + premio,
                        "Rollover_requerido": rollover_actual + premio
                    }
                )
                nuevo_saldo = saldo_actual + premio
            else:
                # Actualizar balance
                exito = actualizar_registro(
                    "usuarios", 
                    user_id, 
                    {"Balance": saldo_actual + premio}
                )
                nuevo_saldo = saldo_actual + premio
            
            if not exito:
                print(f"⚠️ Error al actualizar saldo para usuario {user_id}")
            
            # Actualizar estadísticas de minijuegos (ganador)
            ppt_data["FichGanadas"][user_id] = current_ganadas + 40
            ppt_data["BetWin"][user_id] = current_betwin + 1
            
            mensaje_usuario = (
                f"<blockquote>🎉 ¡Felicidades, {nombre}! 🎉</blockquote>\n\n"
                f"⚔️ <b>Jugada:</b> {partida['jugada_1'].capitalize()} 🆚 {partida['jugada_2'].capitalize()}\n\n"
                f"💰 <b>Premio:</b> <code>+{premio} CUP</code>\n"
                f"💳 <b>Saldo actual:</b> <code>{nuevo_saldo} CUP</code>\n\n"
                f"<i>¡Sigue así y gana más!</i> 🚀"
            )
            resultado_grupo = f"✅ <b>Ganó:</b> <code>+{premio} CUP</code>"
            
        elif ganador == 2:  # Pierde usuario
            # No hay que actualizar saldo porque ya se descontó al iniciar la partida
            nuevo_saldo = saldo_actual
            
            # Actualizar estadísticas de minijuegos (perdedor)
            ppt_data["FichPerdidas"][user_id] = current_perdidas + 50
            ppt_data["BetLost"][user_id] = current_betlost + 1
            
            mensaje_usuario = (
                f"<blockquote>💔 ¡Lo siento, {nombre}!</blockquote>\n\n"
                f"⚔️ <b>Jugada:</b> {partida['jugada_1'].capitalize()} 🆚 {partida['jugada_2'].capitalize()}\n\n"
                f"💸 <b>Pérdida:</b> <code>-50 CUP</code>\n"
                f"💳 <b>Saldo actual:</b> <code>{nuevo_saldo} CUP</code>\n\n"
                f"<i>¡La próxima vez será!</i> 💪"
            )
            resultado_grupo = "❌ <b>Perdió:</b> <code>-50 CUP</code>"
            
        else:  # Empate
            # En caso de empate, devolver la apuesta
            if metodo == "bono":
                exito = actualizar_registro(
                    "bono_apuesta", 
                    user_id, 
                    {"Bono": saldo_actual + 50}
                )
                nuevo_saldo = saldo_actual + 50
            else:
                exito = actualizar_registro(
                    "usuarios", 
                    user_id, 
                    {"Balance": saldo_actual + 50}
                )
                nuevo_saldo = saldo_actual + 50
            
            if not exito:
                print(f"⚠️ Error al devolver apuesta por empate para usuario {user_id}")
            
            mensaje_usuario = (
                f"<blockquote>🤝 ¡Empate, {nombre}!</blockquote>\n\n"
                f"⚔️ <b>Jugada:</b> {partida['jugada_1'].capitalize()} 🆚 {partida['jugada_2'].capitalize()}\n\n"
                f"💳 <b>Saldo actual:</b> <code>{nuevo_saldo} CUP</code>\n\n"
                f"<i>¡Inténtalo de nuevo!</i> 🔄"
            )
            resultado_grupo = "⚖️ <b>Empate</b> (Apuesta devuelta)"

        # Guardar solo estadísticas de minijuegos en JSON
        await save_minijuegos_data(minijuegos_data)

        # Mensaje al usuario
        await context.bot.send_message(
            chat_id=user_id,
            text=mensaje_usuario,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Jugar otra vez", callback_data="Piedra_Papel_Tijera")],
                [InlineKeyboardButton("🔙 Menú", callback_data="minijuegos")]
            ]),
            parse_mode="HTML"
        )

        # Notificación al grupo
        await context.bot.send_message(
            chat_id=REGISTRO_MINIJUEGOS,
            text=(
                f"<blockquote>🎮 <b>PIEDRA, PAPEL O TIJERA</b> 🎮</blockquote>\n\n"
                f"👤 <b>Jugador:</b> <a href='tg://user?id={user_id}'>{nombre}</a>\n"
                f"⚔️ <b>Jugada:</b> {partida['jugada_1'].capitalize()} 🆚 {partida['jugada_2'].capitalize()}\n"
                f"💵 <b>Método de pago:</b> {'🎁 Bono' if metodo == 'bono' else '💲 Balance'}\n"
                f"💰 <b>Saldo restante:</b> <code>{nuevo_saldo} CUP</code>\n\n"
                f"{resultado_grupo}"
            ),
            parse_mode="HTML"
        )

        # Eliminar partida
        if "partidas" in context.bot_data and user_id in context.bot_data["partidas"]:
            context.bot_data["partidas"].pop(user_id)
            
    except Exception as e:
        print(f"⚠️ Error inesperado en finalizar_partida: {e}")
        # Intentar notificar al usuario sobre el error
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Ocurrió un error al procesar tu partida. Contacta con soporte."
            )
        except:
            pass

async def obtener_nombre(context, user_id):
    try:
        chat = await context.bot.get_chat(user_id)
        return chat.first_name
    except Exception as e:
        print(f"⚠️ Error al obtener nombre del usuario {user_id}: {e}")
        return "Usuario"


def determinar_ganador(jugada_1, jugada_2):

    if jugada_1 == jugada_2:
        return 0  # Empate
    elif (jugada_1 == "piedra" and jugada_2 == "tijera") or \
         (jugada_1 == "tijera" and jugada_2 == "papel") or \
         (jugada_1 == "papel" and jugada_2 == "piedra"):
        return 1  # Gana jugador 1
    else:
        return 2  # Gana jugador 2




COFRES_BONO = {
    "coste": 100,
    "premios": [
        {"tipo": "bono", "cantidad": 150, "mensaje": "🎁 ¡Felicidades! Has ganado 150 CUP de bono.", "probabilidad": 0.2},
        {"tipo": "balance", "cantidad": 5, "mensaje": "💰 ¡Sorpresa! Has ganado 5 CUP de balance.", "probabilidad": 0.2},
        {"tipo": "bono", "cantidad": 80, "mensaje": "🔄 ¡Casi! Recuperaste 80 CUP de bono.", "probabilidad": 0.6},
    ]
}

COFRES_VIP = {
    "coste": 200,
    "premios": [
        {"tipo": "balance", "cantidad": 150, "mensaje": "🔄 ¡Casi! Recuperas 150 CUP de balance.", "probabilidad": 0.6},
        {"tipo": "balance", "cantidad": 500, "mensaje": "💰 ¡Felicidades! Has ganado 500 CUP de balance.", "probabilidad": 0.1},
        {"tipo": "bono", "cantidad": 200, "mensaje": "💔 ¡Oh no! Ganaste 200 CUP de bono.", "probabilidad": 0.3},
    ]
}

COFRES_ESPECIALES = {
    "coste": 500,
    "premios": [
        {"tipo": "bono", "cantidad": 1000, "mensaje": "🎉 ¡Increíble! Has ganado 1000 CUP de bono.", "probabilidad": 0.46},
        {"tipo": "balance", "cantidad": 1000, "mensaje": "💰 ¡Felicidades! Has ganado 1000 CUP de balance.", "probabilidad": 0.08},
        {"tipo": "bono", "cantidad": 500, "mensaje": "🔄 ¡Buen intento! Recuperas 500 CUP de bono.", "probabilidad": 0.46},
    ]
}


# Función principal del juego
async def abrir_cofre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text = (
    "<blockquote>🎮 <b>ABRIR COFRES</b> 🎮</blockquote>\n\n"
    "🔍 <b>Elige el tipo de cofre que deseas abrir:</b>\n\n"
    "🎁 <b>Cofre de Bono</b> (100 CUP de bono)\n"
    "   - Puedes ganar:\n"
    "     🎉 150 CUP de bono\n"
    "     💰 5 CUP de balance\n"
    "     🔄 Recuperas 80 CUP de bono\n\n"
    "💎 <b>Cofre VIP</b> (200 CUP de balance)\n"
    "   - Puedes ganar:\n"
    "     🔄 150 CUP de balance\n"
    "     💰 500 CUP de balance\n"
    "     💔 Recuperas 200 CUP de bono\n\n"
    "✨ <b>Cofre Especial</b> (500 CUP de balance)\n"
    "   - Puedes ganar:\n"
    "     🎉 1000 CUP de bono\n"
    "     💰 1000 CUP de balance\n"
    "     💔 Recuperas 500 CUP de bono\n\n"
    "<i>¡Cada cofre es una sorpresa! Elige sabiamente.</i> 🎲"
),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Cofre de Bono (100 CUP)", callback_data="cofre_bono")],
            [InlineKeyboardButton("💎 Cofre VIP (200 CUP)", callback_data="cofre_vip")],
            [InlineKeyboardButton("✨ Cofre Especial (500 CUP)", callback_data="cofre_especial")],
            [InlineKeyboardButton("🔙 Volver", callback_data="Minijuegos")]
        ]),
        parse_mode="HTML"
    )

async def confirmar_cofre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    tipo_cofre = query.data  # "cofre_bono", "cofre_vip", "cofre_especial"
    context.user_data["tipo_cofre"] = tipo_cofre

    user_data = await load_data()
    if tipo_cofre == "cofre_bono":
        coste = COFRES_BONO["coste"]
        saldo = user_data["Bono_apuesta"].get(user_id, {}).get("Bono", 0)
        metodo = "bono"
    elif tipo_cofre == "cofre_vip":
        coste = COFRES_VIP["coste"]
        saldo = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
        metodo = "balance"
    elif tipo_cofre == "cofre_especial":
        coste = COFRES_ESPECIALES["coste"]
        saldo = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
        metodo = "balance"

    if saldo < coste:
        await query.edit_message_text(
            text=f"❌ No tienes suficiente {'bono' if metodo == 'bono' else 'balance'} (necesitas {coste} CUP)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]])
        )
        return

    await query.edit_message_text(
        text=(
            f"<blockquote>🎮 <b>ABRIR COFRES</b> 🎮</blockquote>\n\n"
            f"🔍 <b>Estás a punto de abrir un cofre:</b>\n\n"
            f"🎁 <b>Tipo de cofre:</b> {'🎁 Cofre de Bono' if tipo_cofre == 'cofre_bono' else '💎 Cofre VIP' if tipo_cofre == 'cofre_vip' else '✨ Cofre Especial'}\n"
            f"💵 <b>Coste:</b> {coste} CUP de {'bono' if metodo == 'bono' else 'balance'}\n\n"
            f"⚠️ <b>¿Estás seguro de continuar?</b>\n\n"
            f"<i>Al confirmar, se descontarán {coste} CUP de tu {'bono' if metodo == 'bono' else 'balance'}.</i>"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_apertura")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="minijuegos")]
        ]),
        parse_mode="HTML"
    )
async def abrir_cofre_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    tipo_cofre = context.user_data.get("tipo_cofre")
    user_data = await load_data()
    minijuegos_data = await load_minijuegos_data(user_id)

    if tipo_cofre == "cofre_bono":
        coste = COFRES_BONO["coste"]
        premios = COFRES_BONO["premios"]
        metodo = "bono"
        user_data["Bono_apuesta"][user_id]["Bono"] -= coste  # Descontar costo
    elif tipo_cofre == "cofre_vip":
        coste = COFRES_VIP["coste"]
        premios = COFRES_VIP["premios"]
        metodo = "balance"
        user_data["usuarios"][user_id]["Balance"] -= coste  # Descontar costo
    elif tipo_cofre == "cofre_especial":
        coste = COFRES_ESPECIALES["coste"]
        premios = COFRES_ESPECIALES["premios"]
        metodo = "balance"
        user_data["usuarios"][user_id]["Balance"] -= coste  # Descontar costo

    # Seleccionar premio con probabilidades ajustadas
    probabilidades = [p["probabilidad"] for p in premios]
    premio = random.choices(premios, weights=probabilidades, k=1)[0]

    if premio["tipo"] == "bono":
        user_data["Bono_apuesta"][user_id]["Bono"] += premio["cantidad"]
    else:
        user_data["usuarios"][user_id]["Balance"] += premio["cantidad"]

    # Actualizar estadísticas en minijuegos.json
    if premio["cantidad"] > 0:
        minijuegos_data["ABRE COFRES"]["FichGanadas"][user_id] += premio["cantidad"]
        minijuegos_data["ABRE COFRES"]["BetWin"][user_id] += 1
    else:
        minijuegos_data["ABRE COFRES"]["FichPerdidas"][user_id] += abs(premio["cantidad"])
        minijuegos_data["ABRE COFRES"]["BetLost"][user_id] += 1

  
    await save_minijuegos_data(minijuegos_data)

    # Mensaje al usuario
    saldo_actual = user_data["Bono_apuesta"][user_id]["Bono"] if metodo == "bono" else user_data["usuarios"][user_id]["Balance"]
    await query.edit_message_text(
        text=(
            f"<blockquote>🎉 ¡Has abierto un cofre!</blockquote>\n\n"
            f"{premio['mensaje']}\n\n"
            f"💳 <b>Saldo actual:</b> <code>{saldo_actual} CUP</code>\n\n"
            f"<i>¿Quieres abrir otro cofre?</i> 🔄"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Abrir otro cofre", callback_data="abrir_cofre")],
            [InlineKeyboardButton("🔙 Volver", callback_data="minijuegos")]
        ]),
        parse_mode="HTML"
    )

    # Notificación al grupo
    nombre = user_data["usuarios"][user_id]["Nombre"]
    await context.bot.send_message(
        chat_id=GROUP_REGISTRO,
        text=(
            f"<blockquote>🎮 <b>ABRIR COFRES</b> 🎮</blockquote>\n\n"
            f"👤 <b>Jugador:</b> <a href='tg://user?id={user_id}'>{nombre}</a>\n"
            f"🎁 <b>Tipo de cofre:</b> {'🎁 Bono' if tipo_cofre == 'cofre_bono' else '💎 VIP' if tipo_cofre == 'cofre_vip' else '✨ Especial'}\n"
            f"💵 <b>Coste:</b> {coste} CUP de {'bono' if metodo == 'bono' else 'balance'}\n"
            f"💰 <b>Premio:</b> {premio['cantidad']} CUP de {'bono' if premio['tipo'] == 'bono' else 'balance'}\n"
            f"💳 <b>Saldo actual:</b> <code>{saldo_actual} CUP</code>"
        ),
        parse_mode="HTML"
    )




async def Pronosticos(update, context):
    # Mensaje a mostrar
    mensaje = (
        "🔮 <b>Nuestra tecnología utiliza inteligencia artificial</b> para analizar y procesar cientos de datos "
        "en cuestión de segundos, permitiéndonos predecir resultados tanto en deportes como en la lotería. "
        "Este sistema avanzado combina estadísticas, tendencias y algoritmos de aprendizaje para darte "
        "las mejores opciones.\n\n"
        "🤧 <i>No asumimos la responsabilidad por pérdidas de dinero. Cada usuario es libre de tomar sus "
        "decisiones y asume sus propios riesgos. Usa esta herramienta sabiamente y disfruta la experiencia.</i>"
    )

    # Botones del teclado
    keyboard = [
        [
            InlineKeyboardButton("🎰 Loterías", callback_data="pronosticos_bolita"),
            InlineKeyboardButton("⚽ Deportes", callback_data="mantenimiento"),
        ],
        [
            InlineKeyboardButton("🔙 Volver", callback_data="menu_principal"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Editar el mensaje con el texto y los botones
    await update.callback_query.edit_message_text(
        text=mensaje,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )   



# Generar 20 números únicos aleatorios del 1 al 100
def generar_numeros():
    return random.sample(range(1, 101), 20)

# Función para actualizar los números ganadores diariamente a las 9 AM
def actualizar_numeros(context):
    ahora = datetime.now()
    fecha_actual = ahora.date()

    # Verificar si ya se generaron números para hoy
    if 'ultimo_update' in context.bot_data:
        ultima_actualizacion = context.bot_data['ultimo_update']
        if ultima_actualizacion.date() == fecha_actual:
            return  # Ya se actualizaron hoy, no hacer nada

    # Generar nuevos números y almacenar en contexto global
    context.bot_data['numeros_ganadores'] = generar_numeros()
    context.bot_data['ultimo_update'] = ahora

# Función para formatear los números en el formato requerido
def formatear_numeros(numeros):
    numeros_dia = " | ".join([f"{num:02d}" for num in numeros[:10]])
    numeros_noche = " | ".join([f"{num:02d}" for num in numeros[10:]])
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    mensaje = (
        f"🎯<b>Números ganadores</b>🎯 \n"
        f"📆 <b>FECHA:</b> {fecha_actual}\n\n"
        f"🇨🇺 <b>FLORIDA [1:35 PM]</b> ☀️\n{numeros_dia}\n\n"
        f"🇨🇺 <b>FLORIDA [9:40 PM]</b> 🌛\n{numeros_noche}"
    )
    return mensaje

# Función para manejar el callback y mostrar los números ganadores
@verificar_bloqueo
@marca_tiempo
async def pronosticos_bolita(update, context):
    user_id = str(update.callback_query.from_user.id)  # Obtener ID del usuario
    ahora = datetime.now()

    # Verificar si el mensaje inicial ya se mostró en las últimas 24 horas
    if 'ultimo_mensaje' in context.user_data and context.user_data['ultimo_mensaje'] + timedelta(days=1) > ahora:
        # Mostrar directamente los números ganadores
        await mostrar_numeros_ganadores(update, context)
        return

    # Marcar que el mensaje fue mostrado
    context.user_data['ultimo_mensaje'] = ahora

    # Mostrar el proceso solo si no se ha mostrado en las últimas 24 horas
    mensaje = await update.callback_query.message.reply_text("🔍 Buscando en la web... 🌐")
    await asyncio.sleep(3)
    await mensaje.edit_text("🔎 Buscando en Canales de Telegram... 📢")
    await asyncio.sleep(3)
    await mensaje.edit_text("🕵️‍♂️ Buscando en Canales de WhatsApp... ")
    await asyncio.sleep(3)
    await mensaje.edit_text("🎱 Buscando los resultados de todos los tiempos hasta hoy... 🗃️")
    await asyncio.sleep(4)
    await mensaje.edit_text("🖥️ Calculos procesados, resultados listos")

    # Mostrar los números ganadores
    await mostrar_numeros_ganadores(update, context)

# Función para mostrar los números ganadores
async def mostrar_numeros_ganadores(update, context):
    # Asegurar que los números estén actualizados
    actualizar_numeros(context)

    # Recuperar los números ganadores del contexto
    numeros_ganadores = context.bot_data.get('numeros_ganadores', generar_numeros())

    # Crear el mensaje con los números ganadores
    mensaje_numeros = formatear_numeros(numeros_ganadores)

    # Enviar el mensaje
    await update.callback_query.message.reply_text(
        mensaje_numeros,
        parse_mode="HTML",
    )


@verificar_bloqueo
@marca_tiempo
async def menu_soporte(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📞 Contactar Admin", callback_data='contactar_admin')],
        [InlineKeyboardButton("❌ Apuesta Mal Pagada", callback_data='apuesta_mal_pagada')],
        [InlineKeyboardButton("⏳ Apuesta Atrasada", callback_data='apuesta_atrasada')],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data='menu_principal')]
    ]
    
    await query.edit_message_text(
        "🛠️ <b>Soporte Técnico</b>\n\n"
        "Seleccione el tipo de asistencia que necesita:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_soporte_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'contactar_admin':
        await contactar_admin(update, context)
    elif query.data == 'apuesta_mal_pagada':
        await pedir_ticket(update, context, 'mal_pagada')
    elif query.data == 'apuesta_atrasada':
        await pedir_ticket(update, context, 'atrasada')

async def pedir_ticket(update: Update, context: CallbackContext, tipo_consulta: str):
    query = update.callback_query
    await query.answer()
    
    context.user_data['consulta_apuesta'] = tipo_consulta
    
    await query.edit_message_text(
        "📝 Por favor ingrese el <b>ID del ticket</b> de su apuesta:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Volver", callback_data='menu_soporte')]
        ])
    )
    
    context.user_data['esperando_ticket'] = True



async def manejar_apuesta_atrasada(update: Update, context: CallbackContext, apuesta: dict):
    if apuesta['estado'] == '⌛Pendiente':
        tiempo_transcurrido = calcular_tiempo_transcurrido(apuesta['fecha_realizada'])
        
        await update.message.reply_text(
            f"⏳ <b>Apuesta Pendiente</b>\n\n"
            f"ID: <code>{apuesta['id_ticket']}</code>\n"
            f"Partido: {apuesta['partido']}\n"
            f"Tiempo en espera: {tiempo_transcurrido}\n\n"
            "Por favor sea paciente, su apuesta está siendo procesada.\n"
            "No es necesario contactar a los moderadores.",
            parse_mode="HTML"
        )
    else:
        await conectar_con_soporte(update, context, apuesta)


async def procesar_ticket(update: Update, context: CallbackContext):
    if not context.user_data.get('esperando_ticket'):
        return
        
    ticket_id = update.message.text
    tipo_consulta = context.user_data.get('consulta_apuesta')
    
    # Buscar apuesta en la base de datos
    consulta = "SELECT * FROM apuestas WHERE id_ticket = ?"
    apuesta_tuple = ejecutar_consulta_segura(consulta, (ticket_id,), obtener_resultados=True)
    
    if not apuesta_tuple:
        await update.message.reply_text("❌ No se encontró la apuesta con ese ID")
        return
    
    # Convertir tupla a diccionario
    column_names = ['id', 'usuario_id', 'user_name', 'fecha_realizada', 'fecha_inicio', 
                   'monto', 'cuota', 'ganancia', 'estado', 'bono', 'balance', 'betting', 
                   'id_ticket', 'event_id', 'deporte', 'liga', 'sport_key', 'partido', 
                   'favorito', 'tipo_apuesta', 'home_logo', 'away_logo', 'mensaje_canal_url', 
                   'mensaje_canal_id', 'minuto', 'marcador', 'completed', 'last_update', 
                   'es_combinada', 'selecciones_json', 'scores_json']
    
    apuesta = dict(zip(column_names, apuesta_tuple[0]))
    
    if tipo_consulta == 'atrasada':
        await manejar_apuesta_atrasada(update, context, apuesta)
    elif tipo_consulta == 'mal_pagada':
        await manejar_apuesta_mal_pagada(update, context, apuesta)

async def resolver_apuesta(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    ticket_id = query.data.split('_')[1]
    
    try:
        # Buscar la apuesta en la base de datos
        consulta_select = "SELECT * FROM apuestas WHERE id_ticket = ?"
        apuesta_tuple = ejecutar_consulta_segura(consulta_select, (ticket_id,), obtener_resultados=True)
        
        if not apuesta_tuple:
            await query.edit_message_text("❌ Ticket no encontrado")
            return
        
        # Convertir tupla a diccionario
        column_names = ['id', 'usuario_id', 'user_name', 'fecha_realizada', 'fecha_inicio', 
                       'monto', 'cuota', 'ganancia', 'estado', 'bono', 'balance', 'betting', 
                       'id_ticket', 'event_id', 'deporte', 'liga', 'sport_key', 'partido', 
                       'favorito', 'tipo_apuesta', 'home_logo', 'away_logo', 'mensaje_canal_url', 
                       'mensaje_canal_id', 'minuto', 'marcador', 'completed', 'last_update', 
                       'es_combinada', 'selecciones_json', 'scores_json']
        
        apuesta_resuelta = dict(zip(column_names, apuesta_tuple[0]))
        
        # Eliminar la apuesta usando la función existente
        resultado = eliminar_apuesta_de_db(apuesta_resuelta['id'])
        
        if resultado:
            # Notificar al admin
            await query.edit_message_text(
                f"✅ Apuesta resuelta:\n\n"
                f"🆔 Ticket: <code>{ticket_id}</code>\n"
                f"👤 Usuario: <code>{apuesta_resuelta['usuario_id']}</code>\n"
                f"🏆 Partido: {apuesta_resuelta.get('partido', 'Sin partido')}",
                parse_mode="HTML"
            )
            
            # Notificar al usuario
            try:
                await context.bot.send_message(
                    chat_id=apuesta_resuelta['usuario_id'],
                    text=(
                        f"📢 <b>Resolución de Apuesta</b>\n\n"
                        f"🆔 Ticket: <code>{ticket_id}</code>\n"
                        f"🏆 Partido: {apuesta_resuelta.get('partido', 'Sin partido')}\n"
                        f"💰 Monto: {apuesta_resuelta.get('monto', 0)} CUP\n\n"
                        f"ℹ️ <b>Un moderador ha resuelto tu apuesta pendiente.</b>\n\n"
                        f"Gracias por tu paciencia."
                    ),
                    parse_mode="HTML"
                )
            except Exception as user_error:
                print(f"Error notificando al usuario {apuesta_resuelta['usuario_id']}: {user_error}")
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⚠️ No se pudo notificar al usuario {apuesta_resuelta['usuario_id']} sobre la resolución del ticket {ticket_id}"
                )
        else:
            await query.edit_message_text("❌ Error al eliminar la apuesta de la base de datos")
    
    except Exception as e:
        await query.edit_message_text("⚠️ Error crítico al resolver la apuesta")
        print(f"Error en resolver_apuesta: {str(e)}")
        import traceback
        traceback.print_exc()
        # Notificar a desarrolladores
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 Error crítico al resolver ticket {ticket_id}: {str(e)}"
        )


async def manejar_apuesta_atrasada(update: Update, context: CallbackContext, apuesta: dict):
    if apuesta['estado'] != '⌛Pendiente':
        await conectar_con_soporte(update, context, apuesta)
        return

    try:
        # Obtener datos clave
        deporte = apuesta['deporte'].split('⚽')[0].strip() if '⚽' in apuesta['deporte'] else apuesta['deporte']
        tiempo_maximo = TIEMPOS_DURACION.get(deporte, 120)
        fecha_inicio = datetime.strptime(apuesta['fecha_inicio'], "%d/%m/%Y %H:%M:%S")
        ahora = datetime.now()
        diferencia = ahora - fecha_inicio
        minutos_transcurridos = diferencia.total_seconds() / 60
        hora_cuba = fecha_inicio.strftime("%I:%M %p")
        
        # Calcular tiempos importantes
        tiempo_limite = tiempo_maximo + 30
        minutos_pasados_limite = minutos_transcurridos - tiempo_limite
        
        # Determinar el estado
        if minutos_transcurridos > tiempo_limite:
            # Caso 1: Pasó el tiempo límite + 30 mins
            horas_pasadas = int(minutos_pasados_limite // 60)
            minutos_pasados = int(minutos_pasados_limite % 60)
            
            mensaje = (
                f"<pre>⚠️ Apuesta Pendiente</pre>\n\n"
                f"🏆 <b>Partido:</b> {apuesta['partido']}\n"
                f"⏰ <b>Hora inicio:</b> {hora_cuba}\n"
                f"🆔 <b>Ticket ID:</b> <code>{apuesta['id_ticket']}</code>\n\n"
                f"⌛ <b>Estado:</b> Lleva <b>{horas_pasadas}h {minutos_pasados}m</b> pasado el tiempo límite.\n\n"
                f"<i>Contacte a soporte para verificar su caso.</i>"
            )
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Enviar a Soporte", callback_data=f"soporte_{apuesta['id_ticket']}")],
                [InlineKeyboardButton("🔄 Reintentar", callback_data=f"revisar_{apuesta['id_ticket']}")]
            ])
            
        elif minutos_transcurridos > tiempo_maximo:
            # Caso 2: Dentro del período de gracia
            hora_limite = (fecha_inicio + timedelta(minutes=tiempo_limite)).strftime("%I:%M %p")
            
            mensaje = (
                f"<pre>📨 Apuesta en Proceso</pre>\n\n"
                f"🏆 <b>Partido:</b> {apuesta['partido']}\n"
                f"⏰ <b>Hora inicio:</b> {hora_cuba}\n"
                f"🆔 <b>Ticket ID:</b> <code>{apuesta['id_ticket']}</code>\n\n"
                f"⌛ <b>Estado:</b> Será pagada antes de las <b>{hora_limite}</b>.\n\n"
                f"ℹ️ <i>Estamos procesando su apuesta. Hay retrasos en este partido.</i>"
            )
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data=f"revisar_{apuesta['id_ticket']}")]
            ])
            
        else:
            # Caso 3: Dentro del tiempo normal
            minutos_restantes = int(tiempo_maximo - minutos_transcurridos)
            hora_procesamiento = (ahora + timedelta(minutes=minutos_restantes)).strftime("%I:%M %p")
            
            mensaje = (
                f"<pre>⏳ Apuesta Pendiente</pre>\n\n"
                f"🏆 <b>Partido:</b> {apuesta['partido']}\n"
                f"⏰ <b>Hora inicio:</b> {hora_cuba}\n"
                f"🆔 <b>Ticket ID:</b> <code>{apuesta['id_ticket']}</code>\n\n"
                f"⌛ <b>Estado:</b> Se pagará ~<b>{hora_procesamiento}</b> ({minutos_restantes} mins restantes).\n\n"
                f"ℹ️ <i>El sistema evaluará automáticamente al finalizar.</i>"
            )
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data=f"revisar_{apuesta['id_ticket']}")]
            ])

        # Manejo de edición/envío con protección contra errores
        try:
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        text=mensaje,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except Exception as edit_error:
                    if "Message is not modified" in str(edit_error):
                        # Enviar mensaje nuevo si no se puede editar
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="ℹ️ La información ya está actualizada:\n\n" + mensaje.split('\n\n', 1)[1],
                            parse_mode="HTML",
                            reply_markup=reply_markup
                        )
                    else:
                        raise edit_error
            else:
                await update.message.reply_text(
                    text=mensaje,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            print(f"Error al enviar mensaje: {str(e)}")
            

    except Exception as e:
        print(f"Error en manejar_apuesta_atrasada: {str(e)}")
mapeo_tipos = {
        # Mercados estándar
        'h2h': 'h2h',
        'moneyline': 'h2h',
        'match_winner': 'h2h',
        
        # Mercados de handicaps
        'spreads': 'Hándicap',
        'handicap': 'Hándicap',
        'hándicap': 'Hándicap',
        
        # Mercados de totales
        'totals': 'Total de anotaciones',
        'over_under': 'Total de anotaciones',
        
        # Mercados especiales
        'btts': 'Ambos equipos marcan',
        'both_teams_to_score': 'Ambos equipos marcan',
        'draw_no_bet': 'draw_no_bet',
        'dnb': 'draw_no_bet'
    }    
# Mapeo de tipos de apuesta a URLs de reglas
REGLA_URLS = {
    'h2h': "https://t.me/CubaPlayCANAL/176",  # URL genérica para h2h
    'Hándicap': "https://t.me/CubaPlayCANAL/478",
    'Total de anotaciones': "https://t.me/CubaPlayCANAL/176",
    'Ambos equipos marcan': "https://t.me/CubaPlayCANAL/479",
    'draw_no_bet': "https://t.me/CubaPlayCANAL/480"
}

async def manejar_apuesta_mal_pagada(update: Update, context: CallbackContext, apuesta: dict):
    try:
        # Normalizar tipo de apuesta
        tipo_normalizado = mapeo_tipos.get(apuesta['tipo_apuesta'].lower(), apuesta['tipo_apuesta'])
        url_reglas = REGLA_URLS.get(tipo_normalizado, "https://t.me/CubaPlayCANAL/176")  # URL por defecto
        
        # Calcular ganancias
        monto = apuesta['monto']
        cuota = apuesta.get('cuota', 1.0)
        ganancia_total = monto * cuota
        ganancia_neta = ganancia_total - monto
        
        # Construir mensaje base
        mensaje = (
            f"📋 <b>Verificación de Apuesta</b>\n\n"
            f"🎫 <b>Ticket ID:</b> <code>{apuesta['id_ticket']}</code>\n"
            f"🏆 <b>Partido:</b> {apuesta['partido']}\n"
            f"📊 <b>Tipo:</b> {tipo_normalizado}\n"
            f"💵 <b>Monto:</b> {monto} CUP\n"
            f"📈 <b>Cuota:</b> {cuota}\n"
            f"💰 <b>Ganancia Total:</b> {ganancia_total:.2f} CUP\n\n"
        )
        
        # Añadir información específica para apuestas con bono
        if apuesta.get('bono', 0) > 0:
            mensaje += (
                f"🎁 <b>Apuesta con Bono</b>\n\n"
                f"• El monto apostado  <b>Bono</b> fue a tu bono\n"
                f"• Ganancia neta ({ganancia_neta:.2f} CUP) fue al <b>Bono Retirable</b>\n\n"
                f"ℹ️ Recuerda que las apuestas con bono tienen condiciones especiales de retiro.\n\n"
            )
        
        mensaje += "Verifique las reglas de este tipo de apuesta para confirmar si el pago verdaderamente es incorrecto antes de contactar al soporte:"
        
        # Crear teclado con botón de reglas
        keyboard = [
            [InlineKeyboardButton(f"📜 Reglas de {tipo_normalizado}", url=url_reglas)],
            [InlineKeyboardButton("📞 Enviar a Soporte", callback_data=f"soporte_{apuesta['id_ticket']}")]
        ]
        
        await update.message.reply_text(
            text=mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        print(f"Error en manejar_apuesta_mal_pagada: {str(e)}")
        await update.message.reply_text(
            "⚠️ Error al verificar tu apuesta. Por favor contacta a soporte manualmente.",
            parse_mode="HTML"
        )

async def conectar_con_soporte(update: Update, context: CallbackContext, apuesta: dict):
    user = update.message.from_user
    tiempo_transcurrido = calcular_tiempo_transcurrido(apuesta['fecha_realizada'])
    
    # Mensaje para el admin
    mensaje_admin = (
        f"🆘 <b>Nueva consulta de apuesta</b>\n\n"
        f"👤 Usuario: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📋 Ticket: <code>{apuesta['id_ticket']}</code>\n"
        f"⏳ Tiempo: {tiempo_transcurrido}\n"
        f"🏟 Partido: {apuesta['partido']}\n"
        f"💰 Monto: {apuesta['monto']}\n"
        f"📊 Estado: {apuesta['estado']}\n\n"
        f"🔗 <a href='{apuesta['mensaje_canal_url']}'>Ver apuesta</a>"
    )
    
    await context.bot.send_message(
        chat_id=-4671516881,  # Tu ID o grupo de soporte
        text=mensaje_admin,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Responder", callback_data=f"responder_{user.id}")],
            [InlineKeyboardButton("✅ Resolver", callback_data=f"resolver_{apuesta['id_ticket']}")]
        ])
    )
    
    await update.message.reply_text(
        "✅ Hemos enviado su consulta al equipo de soporte.\n"
        "Le responderemos a la brevedad posible."
    )

def calcular_tiempo_transcurrido(fecha_str: str) -> str:
    fecha_apuesta = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
    diferencia = datetime.now() - fecha_apuesta
    
    if diferencia.days > 0:
        return f"{diferencia.days} días"
    horas = diferencia.seconds // 3600
    if horas > 0:
        return f"{horas} horas"
    minutos = diferencia.seconds // 60
    return f"{minutos} minutos"


async def contactar_admin(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Preguntar al usuario en qué puede ayudarle
    await query.edit_message_text(
        "🛠️ *Soporte*\n\n"
        "¿En qué puedo ayudarte? Por favor, describe tu problema o consulta.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data='menu_principal')]
        ])
    )

    # Establecer el estado para recibir el mensaje del usuario
    context.user_data['estado'] = 'esperando_mensaje_soporte'

async def recibir_mensaje_soporte(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.full_name
    mensaje_usuario = update.message.text

    # Verificar si el usuario está bloqueado
    if user_id in usuarios_bloqueados:
        await update.message.reply_text("❌ Has sido bloqueado y no puedes usar este bot.")
        return

    # Obtener datos del usuario desde la base de datos usando funciones auxiliares
    usuario_data = obtener_registro("usuarios", user_id, "Balance, Referidos, Nombre")
    
    # Usar datos de la base de datos o valores por defecto
    if usuario_data:
        balance = usuario_data[0]
        referidos = usuario_data[1]
        nombre = usuario_data[2] if len(usuario_data) > 2 else user_name
    else:
        balance = 0
        referidos = 0
        nombre = user_name

    # Crear el mensaje para el admin
    mensaje_admin = (
        f"🆘 <b>Nuevo mensaje de soporte</b>\n\n"
        f"👤 <b>Usuario:</b> <a href='tg://user?id={user_id}'>{nombre}</a>\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Balance:</b> <code>{balance}</code>\n"
        f"👥 <b>Referidos:</b> <code>{referidos}</code>\n\n"
        f"📝 <b>Mensaje:</b>\n"
        f"<i>{mensaje_usuario}</i>"
    )

    # Enviar el mensaje al admin (ID 7031172659)
    admin_id = "7031172659"
    await context.bot.send_message(
        chat_id=admin_id,
        text=mensaje_admin,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Responder", callback_data=f"responder_{user_id}")],
            [InlineKeyboardButton("🚫 Bloquear Usuario", callback_data=f"bloquear_{user_id}")]
        ])
    )

    # Confirmar al usuario que su mensaje fue enviado
    await update.message.reply_text(
        "✅ Tu mensaje ha sido enviado al soporte. Te responderemos pronto, no es necesario que vuelva a realizar la solicitud."
    )
    
    # Limpiar el estado
    context.user_data['estado'] = None

# Función para manejar las acciones del admin (responder o bloquear)
async def manejar_acciones_admin(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Obtener el ID del usuario y la acción (responder o bloquear)
    callback_data = query.data
    action, user_id = callback_data.split("_")

    if action == "responder":
        # Establecer el estado para recibir la respuesta del admin
        context.user_data['estado'] = 'estado_respuesta'
        context.user_data['estado_respuesta'] = user_id

        # Enviar un nuevo mensaje en lugar de editar el existente
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📤 Escribe tu respuesta para el usuario:"
        )
    elif action == "bloquear":
        # Asegúrate de que usuarios_bloqueados sea un conjunto (set)
        usuarios_bloqueados.add(user_id)
        await guardar_usuarios_bloqueados()  # Guardar los cambios en el archivo JSON

        # Enviar un nuevo mensaje en lugar de editar el existente
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🚫 El usuario con ID `{user_id}` ha sido bloqueado."
        )

async def enviar_respuesta_admin(update: Update, context: CallbackContext):
    admin_id = str(update.message.from_user.id)
    respuesta = update.message.text

    # Verificar si el admin está respondiendo a un usuario
    if 'estado_respuesta' in context.user_data:
        user_id = context.user_data['estado_respuesta']
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📨 *Respuesta del soporte:*\n\n{respuesta}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Tu respuesta ha sido enviada al usuario.")
        del context.user_data['estado_respuesta']
    else:
        await update.message.reply_text("❌ No hay un usuario esperando respuesta.")







# Variable global para almacenar los usuarios bloqueados
usuarios_bloqueados = set()

# Función para cargar usuarios bloqueados desde un archivo
async def cargar_usuarios_bloqueados():
    try:
        with open("usuarios_bloqueados.json", "r") as file:
            data = json.load(file)
            return set(data.get("bloqueados", []))
    except FileNotFoundError:
        return set()

# Función para guardar usuarios bloqueados en un archivo
async def guardar_usuarios_bloqueados():
    with open("usuarios_bloqueados.json", "w") as file:
        json.dump({"bloqueados": list(usuarios_bloqueados)}, file)

# Comando para banear usuarios
async def banear_usuario(update: Update, context: CallbackContext):
    try:
        user_id = str(update.message.from_user.id)  # Convertir a string

        if user_id not in ADMIN_IDS:  # Verificar si el ID está en la lista de admins
            await update.message.reply_text("❌ No tienes permiso para usar este comando.")
            return

        if len(context.args) == 0:
            await update.message.reply_text("⚠️ Uso incorrecto. Usa: `/ban ID`")
            return

        user_id_ban = context.args[0]

        if user_id_ban in usuarios_bloqueados:
            await update.message.reply_text(f"⚠️ El usuario {user_id_ban} ya está bloqueado.")
            return

        usuarios_bloqueados.add(user_id_ban)
        await guardar_usuarios_bloqueados()
        await update.message.reply_text(f"🚫 Usuario {user_id_ban} ha sido bloqueado.")

    except Exception as e:
        logger.error(f"Error en banear_usuario: {e}")
        await update.message.reply_text("❌ Ocurrió un error al procesar el comando.")

async def desbanear_usuario(update: Update, context: CallbackContext):
    try:
        user_id = str(update.message.from_user.id)

        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ No tienes permiso para usar este comando.")
            return

        if len(context.args) == 0:
            await update.message.reply_text("⚠️ Uso incorrecto. Usa: `/unban ID`")
            return

        user_id_unban = context.args[0]

        # Cargar la lista actual de usuarios bloqueados
        usuarios_bloqueados = await cargar_usuarios_bloqueados()

        # Asegurarse de que 'bloqueados' existe y es una lista
        if 'bloqueados' not in usuarios_bloqueados:
            usuarios_bloqueados['bloqueados'] = []
        
        if user_id_unban not in usuarios_bloqueados['bloqueados']:
            await update.message.reply_text(f"⚠️ El usuario {user_id_unban} no está bloqueado.")
            return

        # Eliminar el usuario de la lista de bloqueados
        usuarios_bloqueados['bloqueados'].remove(user_id_unban)

        # Guardar la lista actualizada
        if await guardar_usuarios_unban(usuarios_bloqueados):
            await update.message.reply_text(f"✅ Usuario {user_id_unban} ha sido desbloqueado exitosamente.")
        else:
            await update.message.reply_text("❌ Error al guardar los cambios. Contacta al desarrollador.")

    except Exception as e:
        logger.error(f"Error en desbanear_usuario: {e}")
        await update.message.reply_text("❌ Ocurrió un error al procesar el comando.")
async def guardar_usuarios_unban(data):
    try:
        with open('usuarios_bloqueados.json', 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error al guardar usuarios bloqueados: {e}")
        return False

# Función para manejar el error "bot was blocked by the user"
async def error_handler(update: Update, context: CallbackContext):
    try:
        raise context.error
    except Exception as e:
        if "bot was blocked by the user" in str(e):
            logger.warning(f"El bot fue bloqueado por el usuario: {e}")
        else:
            logger.error(f"Error no manejado: {e}")



async def enviar_reglas(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Botones para las secciones de reglas
    keyboard = [
        [InlineKeyboardButton("🎰 Bolita", callback_data='bolita_reglas'),
         InlineKeyboardButton("🎲 Apuestas", callback_data='apuestas_reglas')],
        [InlineKeyboardButton("💰 Depósitos y Retiros", callback_data='depositos_retiros_reglas')],
        [InlineKeyboardButton("🎁 Bonos", callback_data='bonos_reglas'),
         InlineKeyboardButton("🎮 Minijuegos", callback_data='minijuegos_reglas')],
        [InlineKeyboardButton("ℹ️ Versión Del Bot", callback_data='version_reglas')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Mensaje inicial con el menú de botones
    await query.edit_message_text(
        text="""<blockquote>🔹 TÉRMINOS Y CONDICIONES DE USO 🔹</blockquote>

¡Bienvenido/a al menú de reglas de <b>QvaPlay_bot</b>! 
Selecciona una opción para ver las reglas específicas de cada sección.

<i>Equipo de desarrollo:</i>
👨‍💻 <a href="https://t.me/CubaPlayAdmin">JackSparrow</a> (CEO)
👨‍💻 <a href="https://t.me/WinstomQvaplay">WistonQvaPlay</a> (Moderador)
👨‍💻 <a href="https://t.me/girlbiker_07">CrushQvaplay</a> (Moderador)

<i>Versión actual:</i> <b>1.01</b>""",
        reply_markup=reply_markup,
        parse_mode='HTML',
        disable_web_page_preview=True
    )


# Función para manejar los callbacks de los botones
async def botones_reglas(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Texto para cada sección de reglas
    if query.data == 'bolita_reglas':
        texto = """<blockquote>🎰 LOTERIAS (BOLITA)</blockquote>

🔸 No incluir el total correcto en una jugada y la jugada resulta ganadora está jugada no se pagará, tampoco podrá reclamar el dinero de esa jugada.

🔸 <b>Límites para cada jugada:</b>
🎯 Centena: 50 CUP
🔚 Fijo: 400 CUP
🔃 Parlet: 10 CUP
👀 (Si juega más de estos límites, el premio se pagará en base a estos)

🔸 <b>Pagos por 1 CUP jugado:</b>
• Fijo: 80 CUP
• Centena: 500 CUP
• Parlet: 800 CUP"""
    elif query.data == 'apuestas_reglas':
        texto = """<blockquote>🎲 REGLAS DE APUESTAS</blockquote>

🔹 <b>Cancelación de apuestas:</b>
- Las apuestas con bono <b>no se pueden cancelar</b>.
- Las apuestas con balance se pueden cancelar automáticamente, recuperando el <b>70% del monto</b> de tu apuesta si el juego está a más de <b>30 minutos</b> de comenzar.

🔹 <b>Apuestas nulas:</b>
- Si se detecta por alguna vía una apuesta a un partido ya empezado o finalizado, la apuesta se considera <b>nula</b> (es poco probable, ya que el bot muestra información actualizada).

🔹 <b>Partidos cancelados:</b>
- Si un partido es cancelado, todas las apuestas se consideran <b>nulas</b>, a menos que QvaPlay decida explícitamente tomarlas (por ejemplo, si el juego se jugó a más del 7mo inning en caso de MLB).

🔹 <b>Apuestas H2H (Cara a Cara):</b>
- Todas las apuestas H2H son válidas hasta el <b>minuto 90 o agregados</b>. No incluyen penales ni tiempo extra.

🔹 <b>Recomendación:</b>
- Apueste solo dinero que pueda perder. <b>Evite las deudas</b>."""
    elif query.data == 'depositos_retiros_reglas':
        texto = """<blockquote>💰 DEPÓSITOS Y RETIROS</blockquote>

- Los retiros pueden tardar un máximo de 48 horas en caso de haber algún problema (generalmente su dinero llegará en minutos).
- Deberá retirar por la misma vía que deposita, excluyendo las vías de depósito MLC y Criptomonedas. Si deposita por estas vías, podrá retirar por la vía que desee.
- Los depósitos son aceptados en los próximos 2 minutos ya que son completamente automáticos.
-Despues que deposite no puede retirar inmediatamente deberá esperar 24 horas.
-El límite a retirar diario es de 5000 CUP
-Puede retirar una ves al día."""
    elif query.data == 'bonos_reglas':
        texto = """<blockquote>🎁 REGLAS DE BONOS</blockquote>

🔹 <b>Retiro de bonos:</b>
- Para retirar el bono retirable, debe cumplir todas las condiciones impuestas (rollover, medalla, etc.).
- Si gana un bono por depósitos, no podrá retirar de inmediato su depósito. Deberá apostar al menos el <b>150% de su depósito</b> para evitar que el bono sea anulado.

🔹 <b>Cambios en los bonos:</b>
- Todo lo relacionado con bonos está sujeto a cambios en la funcionalidad de QvaPlay.
- Si se detecta cualquier actividad sospechosa, se puede retirar el <b>100% del bono</b>, sin reclamaciones, todo lo relacionado con bono es totalmente al criterio del equipo de desarrollo."""
    elif query.data == 'minijuegos_reglas':
        texto = """<blockquote>🎮 MINIJUEGOS</blockquote>

- Los minijuegos están sujetos a reglas específicas que se detallan en cada juego.
- No se permite el uso de trampas o exploits para obtener ventajas injustas."""
    elif query.data == 'version_reglas':
        texto = """<blockquote>ℹ️ ÚLTIMAS MEJORAS DEL BOT (VERSIÓN 1.01)</blockquote>

🔹 <b>Mejoras recientes:</b>
- Ajustes en las medallas.
- Ahora puede jugar los minijuegos tanto con bono como con balance.
- Corrección de errores y mejoras en la eficiencia de los pagos automáticos.
- Separación del bono y el balance a la hora de apostar para evitar confusiones.

🔹 <blockquote>Seguridad:</blockquote>
- Se ha mejorado el sistema de QvaPlay contra hackeos, garantizando que no se repitan incidentes pasados.
- Eliminación de <b>multicuentas</b> para mantener la integridad del sistema."""

    # Botón para volver al menú principal
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data='Reglas')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=texto,
        reply_markup=reply_markup,
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    
@marca_tiempo
async def proceso_envio_masivo(context: CallbackContext, formatted_message: str, update: Update):
    try:
        # Obtener todos los usuarios de la base de datos
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Obtener todos los IDs de usuarios
        c.execute("SELECT id FROM usuarios")
        user_ids = [row[0] for row in c.fetchall()]
        conn.close()

        total_users = len(user_ids)

        if not user_ids:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ No hay usuarios para enviar.")
            return

        progress_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔄 Preparando envío a {total_users} usuarios...")
        enviados = 0
        errores = 0
        batch_size = max(1, total_users // 10)

        for i, user_id in enumerate(user_ids, 1):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    parse_mode=ParseMode.HTML
                )
                enviados += 1
            except Exception as e:
                logger.error(f"Error enviando a {user_id}: {str(e)}")
                errores += 1

            # Actualizar progreso cada batch_size o al final
            if i % batch_size == 0 or i == total_users:
                try:
                    progress_percentage = int(100 * i / total_users)
                    progress_bar_filled = int(20 * i / total_users)
                    progress_bar_empty = 20 - progress_bar_filled
                    
                    await progress_msg.edit_text(
                        f"📤 Enviando mensajes...\n"
                        f"▰{'▰' * progress_bar_filled}▱{'▱' * progress_bar_empty}\n"
                        f"✅ {enviados} | ❌ {errores} | 📊 {i}/{total_users} ({progress_percentage}%)"
                    )
                except Exception as e:
                    logger.error(f"Error actualizando barra de progreso: {str(e)}")

        # Mensaje final de resumen
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"🎯 Envío masivo completado:\n\n"
                f"• Total de usuarios: {total_users}\n"
                f"• ✅ Mensajes enviados: {enviados}\n"
                f"• ❌ Errores: {errores}\n"
                f"• 📊 Tasa de éxito: {int(100 * enviados / total_users)}%"
            )
        )

    except Exception as e:
        logger.error(f"ERROR GLOBAL en envío masivo: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Error crítico durante el proceso de envío masivo.")
        
async def bono_diario(update: Update, context: CallbackContext):
    try:
        if not update.callback_query:
            print("⚠️ Error: No se recibió un callback válido.")
            return

        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        username = query.from_user.username or ""
        first_name = query.from_user.first_name or ""
        last_name = query.from_user.last_name or ""

        # Verificar si el usuario existe en la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Referidos, ultimo_reclamo_bono, Nombre")
        if not usuario_data:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ No estás registrado. Envía /start para comenzar."
            )
            return

        # Obtener datos del usuario
        referidos = usuario_data[0] if usuario_data else 0
        ultimo_reclamo_str = usuario_data[1] if len(usuario_data) > 1 else None
        nombre_usuario = usuario_data[2] if len(usuario_data) > 2 else first_name

        # Verificar si el usuario tiene al menos 3 referidos
        if referidos < 3:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Necesitas al menos 3 referidos para reclamar el bono diario."
            )
            return

        # Verificar si ya reclamó el bono
        if ultimo_reclamo_str:
            try:
                ultimo_reclamo = datetime.strptime(ultimo_reclamo_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    ultimo_reclamo = datetime.strptime(ultimo_reclamo_str, "%Y-%m-%d")
                except ValueError:
                    ultimo_reclamo = datetime.now() - timedelta(hours=6)  # Valor por defecto si el formato es inválido

            ahora = datetime.now()
            tiempo_transcurrido = ahora - ultimo_reclamo

            if tiempo_transcurrido < timedelta(hours=5):
                proximo_reclamo = ultimo_reclamo + timedelta(hours=5)
                tiempo_restante = proximo_reclamo - ahora
                horas, resto = divmod(tiempo_restante.seconds, 3600)
                minutos, segundos = divmod(resto, 60)
                mensaje_tiempo_restante = f"{horas}h {minutos}m {segundos}s"

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠️ Ya has reclamado tu bono recientemente. Vuelve en {mensaje_tiempo_restante}."
                )
                return

        # Verificar nombre/usuario para elegibilidad del bono
        nombre_completo = f"{first_name} {last_name}".strip().lower()
        username_lower = username.lower() if username else ""
        
        if ("qvaplay" in username_lower) or ("qvaplay" in nombre_completo):
            bono = random.randint(40, 70)
            rollover_nuevo = bono * 4

            # Obtener datos actuales del bono
            bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido, Rollover_actual, Bono_retirable")
            
            if not bono_data:
                # Crear nuevo registro de bono
                exito = actualizar_registro(
                    "bono_apuesta",
                    user_id,
                    {
                        "Bono": bono,
                        "Rollover_requerido": rollover_nuevo,
                        "Rollover_actual": 0,
                        "Bono_retirable": 0
                    }
                )
                bono_actual = bono
                rollover_actual = rollover_nuevo
                bono_retirable = 0
            else:
                # Actualizar bono existente
                bono_actual = bono_data[0] + bono
                rollover_actual = bono_data[1] + rollover_nuevo
                bono_retirable = bono_data[3] if len(bono_data) > 3 else 0
                
                exito = actualizar_registro(
                    "bono_apuesta",
                    user_id,
                    {
                        "Bono": bono_actual,
                        "Rollover_requerido": rollover_actual
                    }
                )

            # Actualizar fecha del último reclamo
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exito_usuario = actualizar_registro(
                "usuarios",
                user_id,
                {"ultimo_reclamo_bono": fecha_actual}
            )

            if not exito or not exito_usuario:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Error al procesar el bono. Inténtalo de nuevo."
                )
                return

            mensaje_usuario = (
                f"<blockquote>✅ ¡Bono reclamado!</blockquote>\n\n"
                f"💰 <b>Bono recibido:</b> <code>{bono} CUP</code>\n\n"
                f"🎁 <b>Bono de Apuesta:</b> <code>{bono_actual} CUP</code>\n"
                f"💲 <b>Bono Retirable:</b> <code>{bono_retirable} CUP</code>\n"
                f"🔄 <b>Rollover Requerido:</b> <code>{rollover_actual} CUP</code>"
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=mensaje_usuario,
                parse_mode="HTML"
            )

            mensaje_grupo = (
                f"<blockquote>📢 ¡Nuevo bono reclamado!</blockquote>\n\n"
                f"👤 <b>Usuario:</b> <a href='tg://user?id={user_id}'>{first_name}</a> {last_name} (@{username})\n"
                f"💰 <b>Bono recibido:</b> <code>{bono} CUP</code>\n"
                f"🎁 <b>Bono Total:</b> <code>{bono_actual} CUP</code>\n"
                f"🔄 <b>Rollover Requerido:</b> <code>{rollover_actual} CUP</code>"
            )

            await context.bot.send_message(
                chat_id=REGISTRO_MINIJUEGOS,
                text=mensaje_grupo,
                parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ No cumples con los requisitos para el bono.\n\n"
                    "Para reclamar el bono:\n"
                    "1. Tu nombre de usuario, nombre o apellido debe contener 'qvaplay'."
                )
            )

    except Exception as e:
        print(f"⚠️ Error en bono_diario: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Ocurrió un error al procesar tu solicitud. Inténtalo de nuevo más tarde."
        )


async def mantenimiento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje tipo show alert indicando que la función está en mantenimiento."""
    query = update.callback_query
    if query:
        await query.answer("⚙️ Esta funcionalidad está en mantenimiento.\n\n📢 Estará disponible en próximas actualizaciones.", show_alert=True)

from threading import Lock
basura_lock = Lock()
from asyncio import create_task

async def sms_global(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Acceso denegado.")
        return

    raw_message = update.message.text.replace("/sms_global ", "", 1)
    formatted_message = raw_message.replace("\\n", "\n")

    if not formatted_message:
        await update.message.reply_text("❌ Mensaje vacío.")
        return

    await update.message.reply_text("⏳ Envío iniciado en segundo plano.")
    create_task(proceso_envio_masivo(context, formatted_message, update))

async def proceso_envio_masivo(context: CallbackContext, formatted_message: str, update: Update):
    try:
        # Obtener todos los usuarios de la base de datos
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Obtener todos los IDs de usuarios
        c.execute("SELECT id FROM usuarios")
        user_ids = [row[0] for row in c.fetchall()]
        conn.close()

        total_users = len(user_ids)

        if not user_ids:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ No hay usuarios para enviar.")
            return

        progress_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔄 Preparando envío a {total_users} usuarios...")
        enviados = 0
        errores = 0
        batch_size = max(1, total_users // 10)

        for i, user_id in enumerate(user_ids, 1):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    parse_mode=ParseMode.HTML
                )
                enviados += 1
            except Exception as e:
                logger.error(f"Error enviando a {user_id}: {str(e)}")
                errores += 1

            # Actualizar progreso cada batch_size o al final
            if i % batch_size == 0 or i == total_users:
                try:
                    progress_percentage = int(100 * i / total_users)
                    progress_bar_filled = int(20 * i / total_users)
                    progress_bar_empty = 20 - progress_bar_filled
                    
                    await progress_msg.edit_text(
                        f"📤 Enviando mensajes...\n"
                        f"▰{'▰' * progress_bar_filled}▱{'▱' * progress_bar_empty}\n"
                        f"✅ {enviados} | ❌ {errores} | 📊 {i}/{total_users} ({progress_percentage}%)"
                    )
                except Exception as e:
                    logger.error(f"Error actualizando barra de progreso: {str(e)}")

        # Mensaje final de resumen
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"🎯 Envío masivo completado:\n\n"
                f"• Total de usuarios: {total_users}\n"
                f"• ✅ Mensajes enviados: {enviados}\n"
                f"• ❌ Errores: {errores}\n"
                f"• 📊 Tasa de éxito: {int(100 * enviados / total_users)}%"
            )
        )

    except Exception as e:
        logger.error(f"ERROR GLOBAL en envío masivo: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Error crítico durante el proceso de envío masivo.")

async def manejar_mensajes(update, context):
    try:
        if update.message is None:
            print("⚠️ No se recibió un mensaje válido (update.message es None)")
            return

        user = update.message.from_user
        user_id = str(user.id)
        mensaje_texto = update.message.text or "[sin texto]"
        estado_actual = context.user_data.get('estado', None)

        # Log mejorado con colores (opcional)
        print(f"\n{'='*50}")
        print(f"📩 Mensaje recibido de: {user.full_name} (ID: {user_id})")
        print(f"💬 Contenido: {mensaje_texto[:100]}...")
        print(f"🔵 Estado actual: {estado_actual}")
        print(f"{'='*50}\n")

        # Mapeo de estados a funciones (para mejor legibilidad)
        manejadores_estados = {
            # Estados existentes (manteniendo tus nombres exactos)
            'handle_amount': handle_amount,
            'esperando_monto': procesar_jugada,
            'esperando_monto_retirar':
procesar_monto_retiro,
            'esperando_tarjeta_retiro':
procesar_tarjeta_retiro,                
            'confirm_withdraw': confirm_withdraw,
            'esperando_mensaje_reenviado': handle_forwarded_message,
            'esperando_descripcion': handle_descripcion,
            'esperando_presupuesto': handle_presupuesto,
            'esperando_jugada': recibir_jugada,
            'esperando_id_destinatario': esperando_id_destinatario,
            'esperando_monto_transferencia': esperando_monto_transferencia,
            'esperando_monto_apuesta': manejar_monto_apuesta,
            'esperando_monto_combinada': manejar_monto_combinada,
            'esperando_mensaje_soporte': recibir_mensaje_soporte,
            'estado_respuesta': enviar_respuesta_admin,
            'procesar_ticket_soporte': procesar_ticket_soporte,      
            'registrando_telefono':
registrar_telefono,
            'ESPERANDO_MONTO_POKER':
manejar_monto_poker,
            'ESPERANDO_ID_POKER':
manejar_id_poker,
            'ESPERANDO_MONTO_APP_BOT': 
manejar_monto_app_bot,
            'ESPERANDO_ID_APP_BOT':
manejar_id_app_bot,
            'ESPERANDO_MONTO_OFERTA': procesar_oferta,
            'ESPERANDO_PRECIO_SUBASTA': crear_subasta,
            'ESPERANDO_PUJA': procesar_puja_subasta,
            'ESPERANDO_NOMBRE_EQUIPO':
manejar_busqueda_equipo,
            'ESPERANDO_MONTO_RETO':
procesar_monto_reto
        }

        if estado_actual in manejadores_estados:
            await manejadores_estados[estado_actual](update, context)
        elif estado_actual is None:
            await update.message.reply_text(
                "❌ No reconozco este comando sin un estado activo.\n"
                "Envía /start para comenzar."
            )
        else:
            print(f"⚠️ Estado no reconocido: {estado_actual}")
            await update.message.reply_text(
                "🔍 No puedo procesar esto ahora.\n"
                "Envía /start para reiniciar."
            )

    except Exception as e:
        error_msg = f"🚨 Error en manejar_mensajes (User: {user_id}): {str(e)}"
        print(error_msg)
        if update.message:
            await update.message.reply_text(
                "⚠️ Ocurrió un error al procesar tu mensaje. "
                "Por favor, intenta nuevamente."
            )
  



# Callback Handlers (Nuevos)
async def menu_soporte(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⏳ Apuesta pendiente", callback_data='apuesta_atrasada')],
        [InlineKeyboardButton("❌ Pago incorrecto", callback_data='apuesta_mal_pagada')],
        [InlineKeyboardButton("👤 Contactar administrador", callback_data='contactar_admin')],
        [InlineKeyboardButton("🏠 Menú principal", callback_data='menu_principal')]
    ]
    
    await query.edit_message_text(
        "🛠️ <b>Centro de Soporte</b>\n\n"
        "Seleccione el tipo de asistencia que necesita:\n\n"
        "<b>⏳ Apuesta pendiente</b>\n"
        "Para apuestas que llevan más tiempo del normal sin resolverse\n\n"
        "<b>❌ Pago incorrecto</b>\n"
        "Si el monto pagado no coincide con lo esperado\n\n"
        "<b>👤 Contactar administrador</b>\n"
        "Para consultas que no son sobre apuestas específicas\n\n"
        "¿En qué podemos ayudarte hoy?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_soporte_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'contactar_admin':
        await contactar_admin(update, context)
    elif query.data in ['apuesta_mal_pagada', 'apuesta_atrasada']:
        context.user_data['consulta_apuesta'] = query.data
        await pedir_ticket(update, context)

  


async def pedir_ticket(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 Por favor ingrese el <b>ID del ticket</b> de su apuesta:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Volver", callback_data='menu_soporte')]
        ])
    )
    
    context.user_data['estado'] = 'procesar_ticket_soporte'

async def procesar_ticket_soporte(update: Update, context: CallbackContext):
    user = update.message.from_user
    ticket_id = update.message.text
    tipo_consulta = context.user_data.get('consulta_apuesta')
    
    # Limpiar estado
    if 'estado' in context.user_data:
        del context.user_data['estado']
    
    try:
        # Buscar apuesta en la base de datos
        consulta = "SELECT * FROM apuestas WHERE id_ticket = ?"
        apuesta_tuple = ejecutar_consulta_segura(consulta, (ticket_id,), obtener_resultados=True)
        
        if not apuesta_tuple:
            await update.message.reply_text("❌ No se encontró la apuesta con ese ID")
            return
        
        # Convertir tupla a diccionario
        column_names = ['id', 'usuario_id', 'user_name', 'fecha_realizada', 'fecha_inicio', 
                       'monto', 'cuota', 'ganancia', 'estado', 'bono', 'balance', 'betting', 
                       'id_ticket', 'event_id', 'deporte', 'liga', 'sport_key', 'partido', 
                       'favorito', 'tipo_apuesta', 'home_logo', 'away_logo', 'mensaje_canal_url', 
                       'mensaje_canal_id', 'minuto', 'marcador', 'completed', 'last_update', 
                       'es_combinada', 'selecciones_json', 'scores_json']
        
        apuesta = dict(zip(column_names, apuesta_tuple[0]))

        # Manejo de combinadas
        if apuesta.get('betting') == 'COMBINADA':
            await update.message.reply_text(
                "⚠️ <b>DETECTADA APUESTA COMBINADA</b>\n\n"
                "Para consultas sobre combinadas, contacte directamente a soporte, al pulsar el botón de abajo soporte recibe tu solicitud y podrá revisar.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📞 Enviar a Soporte", callback_data=f"soporte_{apuesta.get('id_ticket')}")]
                ])
            )
            return
        
        if tipo_consulta == 'apuesta_atrasada':
            await manejar_apuesta_atrasada(update, context, apuesta)
        elif tipo_consulta == 'apuesta_mal_pagada':
            await manejar_apuesta_mal_pagada(update, context, apuesta)
        else:
            await update.message.reply_text("❌ Tipo de consulta no válido")
    
    except Exception as e:
        await update.message.reply_text("⚠️ Error al procesar el ticket")
        print(f"Error procesando ticket: {str(e)}")
        import traceback
        traceback.print_exc()
async def manejar_apuesta_atrasada(update: Update, context: CallbackContext, apuesta: dict):
    estado_apuesta = apuesta.get('estado')
    if estado_apuesta != '⌛Pendiente':
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                f"⚠️ Esta apuesta ya ha sido procesada\n\n"
                f"Estado de la apuesta: {estado_apuesta}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"⚠️ Esta apuesta ya ha sido procesada\n\n"
                f"Estado de la apuesta: {estado_apuesta}",
                parse_mode="HTML"
            )
        return

    try:
        deporte = apuesta.get('deporte', '').split('⚽')[0].strip()
        tiempo_maximo = TIEMPOS_DURACION.get(deporte, 120)
        fecha_inicio = datetime.strptime(apuesta.get('fecha_inicio'), "%d/%m/%Y %H:%M:%S")
        ahora = datetime.now()
        diferencia = ahora - fecha_inicio
        minutos_transcurridos = diferencia.total_seconds() / 60
        hora_cuba = fecha_inicio.strftime("%I:%M %p")
        
        tiempo_limite = tiempo_maximo + 30
        minutos_pasados_limite = minutos_transcurridos - tiempo_limite
        
        if minutos_transcurridos > tiempo_limite:
            horas_pasadas = int(minutos_pasados_limite // 60)
            minutos_pasados = int(minutos_pasados_limite % 60)
            
            mensaje = (
                f"<pre>⚠️ Apuesta Pendiente</pre>\n\n"
                f"🏆 <b>Partido:</b> {apuesta.get('partido')}\n"
                f"⏰ <b>Hora inicio:</b> {hora_cuba}\n"
                f"🆔 <b>Ticket ID:</b> <code>{apuesta.get('id_ticket')}</code>\n\n"
                f"⌛ <b>Estado:</b> Lleva <b>{horas_pasadas}h {minutos_pasados}m</b> pasado el tiempo límite.\n\n"
                f"<i>Contacte a soporte para verificar su caso.</i>"
            )
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Enviar a Soporte", callback_data=f"soporte_{apuesta.get('id_ticket')}")],
                [InlineKeyboardButton("🔄 Reintentar", callback_data=f"revisar_{apuesta.get('id_ticket')}")]
            ])
            
        elif minutos_transcurridos > tiempo_maximo:
            hora_limite = (fecha_inicio + timedelta(minutes=tiempo_limite)).strftime("%I:%M %p")
            
            mensaje = (
                f"<pre>📨 Apuesta en Proceso</pre>\n\n"
                f"🏆 <b>Partido:</b> {apuesta.get('partido')}\n"
                f"⏰ <b>Hora inicio:</b> {hora_cuba}\n"
                f"🆔 <b>Ticket ID:</b> <code>{apuesta.get('id_ticket')}</code>\n\n"
                f"⌛ <b>Estado:</b> Será pagada antes de las <b>{hora_limite}</b>.\n\n"
                f"ℹ️ <i>Estamos procesando su apuesta. Hay retrasos en este partido.</i>"
            )
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data=f"revisar_{apuesta.get('id_ticket')}")]
            ])
            
        else:
            minutos_restantes = int(tiempo_maximo - minutos_transcurridos)
            hora_procesamiento = (ahora + timedelta(minutes=minutos_restantes)).strftime("%I:%M %p")
            
            mensaje = (
                f"<pre>⏳ Apuesta Pendiente</pre>\n\n"
                f"🏆 <b>Partido:</b> {apuesta.get('partido')}\n"
                f"⏰ <b>Hora inicio:</b> {hora_cuba}\n"
                f"🆔 <b>Ticket ID:</b> <code>{apuesta.get('id_ticket')}</code>\n\n"
                f"⌛ <b>Estado:</b> Se pagará ~<b>{hora_procesamiento}</b> ({minutos_restantes} mins restantes).\n\n"
                f"ℹ️ <i>El sistema evaluará automáticamente al finalizar.</i>"
            )
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data=f"revisar_{apuesta.get('id_ticket')}")]
            ])

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=mensaje,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=mensaje,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
                
    except Exception as e:
        print(f"Error en manejar_apuesta_atrasada: {str(e)}")
async def manejar_apuesta_mal_pagada(update: Update, context: CallbackContext, apuesta: dict):
    # Verificar si es combinada
    if apuesta.get('betting') == 'COMBINADA':
        await update.message.reply_text(
            "⚠️ <b>DETECTADA APUESTA COMBINADA</b>\n\n"
            "Para problemas de pago en combinadas, contacte directamente a soporte, al pulsar el botón de abajo soporte recibirá tu Solicitud.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Enviar a Soporte", callback_data=f"soporte_{apuesta.get('id_ticket')}")]
            ])
        )
        return

    # Mensaje original CON botón adicional de soporte
    mensaje = (
        f"<b>📌 Apuesta Mal Pagada</b>\n\n"
        f"🏆 <b>Partido:</b> {apuesta.get('partido')}\n"
        f"🆔 <b>Ticket ID:</b> <code>{apuesta.get('id_ticket')}</code>\n"
        f"💰 <b>Monto:</b> {apuesta.get('monto')} CUP\n"
        f"📈 <b>Cuota:</b> {apuesta.get('cuota')}\n\n"
        f"<i>Por favor asegurese de que está realmente mal pagada, no nos haga perder el tiempo, en ese caso su solicitud será ignorada. ❌TENER EN CUENTA SI SU APUESTA USO BONO EL MONTO APOSTADO LO TIENE EN BONO Y LA GANANCIA EN BONO RETIRABLE❌</i>"
    )

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Enviar al Soporte", callback_data=f"soporte_{apuesta.get('id_ticket')}")],
        [InlineKeyboardButton("🔙 Volver", callback_data='menu_soporte')]
    ])

    await update.message.reply_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    # Configurar estado para recibir comprobante (manteniendo tu lógica original)
    
    context.user_data['ticket_mal_pagado_id'] = apuesta.get('id_ticket')


async def actualizar_estado(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    ticket_id = query.data.split('_')[1]
    chat_id = query.message.chat.id
    
    # Verificar límite de tiempo (5 minutos)
    last_used = context.user_data.get('last_update_time', {}).get(ticket_id)
    if last_used and (datetime.now() - datetime.fromisoformat(last_used)) < timedelta(minutes=5):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⌛ Por favor espera al menos 5 minutos entre actualizaciones del mismo ticket",
            reply_to_message_id=query.message.message_id
        )
        return
    
    try:
        # Buscar apuesta en la base de datos
        consulta = "SELECT * FROM apuestas WHERE id_ticket = ?"
        apuesta_tuple = ejecutar_consulta_segura(consulta, (ticket_id,), obtener_resultados=True)
        
        if not apuesta_tuple:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ No se encontró el ticket especificado",
                reply_to_message_id=query.message.message_id
            )
            return
        
        # Convertir tupla a diccionario
        column_names = ['id', 'usuario_id', 'user_name', 'fecha_realizada', 'fecha_inicio', 
                       'monto', 'cuota', 'ganancia', 'estado', 'bono', 'balance', 'betting', 
                       'id_ticket', 'event_id', 'deporte', 'liga', 'sport_key', 'partido', 
                       'favorito', 'tipo_apuesta', 'home_logo', 'away_logo', 'mensaje_canal_url', 
                       'mensaje_canal_id', 'minuto', 'marcador', 'completed', 'last_update', 
                       'es_combinada', 'selecciones_json', 'scores_json']
        
        apuesta = dict(zip(column_names, apuesta_tuple[0]))

        # Bloque para manejar combinadas
        if apuesta.get('betting') == 'COMBINADA':
            # Parsear selecciones JSON
            selecciones = []
            if apuesta.get('selecciones_json'):
                try:
                    selecciones = json.loads(apuesta['selecciones_json'])
                except json.JSONDecodeError:
                    selecciones = []
            
            selecciones_pendientes = [s for s in selecciones if s.get('estado') == '⌛Pendiente']
            if not selecciones_pendientes:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Esta apuesta combinada ya fue procesada completamente",
                    reply_to_message_id=query.message.message_id
                )
                return
            
            partido_pendiente = selecciones_pendientes[0]
            
            # Formatear fecha
            fecha_inicio = partido_pendiente.get('fecha_inicio', '')
            hora_formateada = fecha_inicio
            try:
                if fecha_inicio and fecha_inicio != 'Fecha no disponible':
                    fecha_obj = datetime.strptime(fecha_inicio, '%d/%m/%Y %H:%M:%S')
                    hora_formateada = fecha_obj.strftime('%I:%M %p')
            except ValueError:
                pass
            
            mensaje = (
                f"<b>⚠️ ACTUALIZACIÓN COMBINADA</b>\n\n"
                f"🎫 <b>Ticket ID:</b> <code>{ticket_id}</code>\n"
                f"⚽ <b>Partido pendiente:</b> {partido_pendiente.get('partido', 'Partido desconocido')}\n"
                f"⏰ <b>Hora inicio:</b> {hora_formateada}\n\n"
                f"📢 Contacte a soporte para actualizaciones manuales"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=mensaje,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📞 Enviar a Soporte", callback_data=f"soporte_{ticket_id}")]
                ]),
                reply_to_message_id=query.message.message_id
            )
            return

        # Flujo para apuestas simples
        try:
            await manejar_apuesta_atrasada(update, context, apuesta)
            if 'last_update_time' not in context.user_data:
                context.user_data['last_update_time'] = {}
            context.user_data['last_update_time'][ticket_id] = datetime.now().isoformat()
        except Exception as e:
            if "Message is not modified" in str(e):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="ℹ️ La información del ticket ya está completamente actualizada",
                    reply_to_message_id=query.message.message_id
                )
            else:
                print(f"Error en manejar_apuesta_atrasada: {str(e)}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Error temporal al actualizar. Por favor intenta nuevamente",
                    reply_to_message_id=query.message.message_id
                )
                
    except Exception as e:
        print(f"Error en actualizar_estado: {str(e)}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Error del sistema al actualizar. Por favor intenta más tarde",
            reply_to_message_id=query.message.message_id
        )
async def contactar_soporte_ticket(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    ticket_id = query.data.split('_')[1]
    user = query.from_user
    
    try:
        # Buscar apuesta en la base de datos
        consulta = "SELECT * FROM apuestas WHERE id_ticket = ?"
        apuesta_tuple = ejecutar_consulta_segura(consulta, (ticket_id,), obtener_resultados=True)
        
        if not apuesta_tuple:
            await query.edit_message_text(
                "❌ No se encontró la apuesta asociada a este ticket",
                parse_mode="HTML"
            )
            return
        
        # Convertir tupla a diccionario
        column_names = ['id', 'usuario_id', 'user_name', 'fecha_realizada', 'fecha_inicio', 
                       'monto', 'cuota', 'ganancia', 'estado', 'bono', 'balance', 'betting', 
                       'id_ticket', 'event_id', 'deporte', 'liga', 'sport_key', 'partido', 
                       'favorito', 'tipo_apuesta', 'home_logo', 'away_logo', 'mensaje_canal_url', 
                       'mensaje_canal_id', 'minuto', 'marcador', 'completed', 'last_update', 
                       'es_combinada', 'selecciones_json', 'scores_json']
        
        apuesta = dict(zip(column_names, apuesta_tuple[0]))

        # Manejo seguro de fecha_inicio
        fecha_inicio_str = apuesta.get('fecha_inicio')
        if fecha_inicio_str and fecha_inicio_str != 'Fecha no disponible':
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%d/%m/%Y %H:%M:%S")
                diferencia = datetime.now() - fecha_inicio
                horas = int(diferencia.total_seconds() // 3600)
                minutos = int((diferencia.total_seconds() % 3600) // 60)
                hora_formateada = fecha_inicio.strftime('%d/%m/%Y %I:%M %p')
            except ValueError:
                horas, minutos = 0, 0
                hora_formateada = "No disponible"
        else:
            horas, minutos = 0, 0
            hora_formateada = "No disponible"
        
        tipo_apuesta = "🎁 Bono" if apuesta.get('bono', 0) > 0 else "💰 Balance"
        
        # Mensaje con protección contra None
        mensaje_admin = (
            f" <pre>🚨APUESTA {apuesta.get('estado', 'PENDIENTE').upper()} - REVISIÓN REQUERIDA</pre>\n\n"
            f"🎫 <b>Ticket ID:</b> <code>{ticket_id}</code>\n"
            f"👤 <b>Usuario:</b> <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"📊 <b>Estado:</b> {apuesta.get('estado', 'N/A')}\n"
            f"🧾 <b>Tipo:</b> {tipo_apuesta}\n\n"
            f"⏳ <b>Tiempo transcurrido:</b> {horas}h {minutos}m\n"
            f"🏆 <b>Evento:</b> {apuesta.get('partido', 'N/A')}\n"
            f"📅 <b>Inicio:</b> {hora_formateada}\n"
            f"💵 <b>Monto:</b> {apuesta.get('monto', 'N/A')} CUP\n"
            f"📈 <b>Cuota:</b> {apuesta.get('cuota', 'N/A')}\n"
            f"🏅 <b>Tipo apuesta:</b> {apuesta.get('tipo_apuesta', 'N/A')}\n\n"
            f"🔗 <a href='{apuesta.get('mensaje_canal_url', '#')}'>Ver apuesta original</a>"
        )
        
        await context.bot.send_message(
            chat_id=-4671516881,  # Asegúrate de que este es el ID correcto del grupo de soporte
            text=mensaje_admin,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Eliminar apuesta❌", callback_data=f"resolver_{ticket_id}")],
                [InlineKeyboardButton("📩 Contactar Usuario", url=f"tg://user?id={user.id}")]
            ])
        )
        
        await query.edit_message_text(
            " <pre>✅Solicitud enviada a soporte</pre>\n\n"
            "Hemos notificado a nuestro equipo sobre tu apuesta pendiente.\n"
            "Recibirás una respuesta en breve.\n\n"
            "<i>No es necesario que vuelvas a consultar esta apuesta.</i>",
            parse_mode="HTML"
        )
            
    except Exception as e:
        print(f"Error en contactar_soporte_ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            "⚠️ Error al procesar tu solicitud. Por favor intenta nuevamente.",
            parse_mode="HTML"
        )
        
def calcular_tiempo_transcurrido(fecha_str: str) -> str:
    fecha_apuesta = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
    diferencia = datetime.now() - fecha_apuesta
    
    if diferencia.days > 0:
        return f"{diferencia.days} días"
    horas = diferencia.seconds // 3600
    if horas > 0:
        return f"{horas} horas"
    minutos = diferencia.seconds // 60
    return f"{minutos} minutos"

APP_DOWNLOAD_LINK = "https://play.google.com/store/apps/details?id=com.nsus.clubgg" 
async def poker(update: Update, context: CallbackContext) -> None:
    """Maneja el comando /poker y muestra el menú principal"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Cargar datos del usuario
    with open('user_data.json', 'r') as f:
        user_data = json.load(f)
    
    balance = user_data['usuarios'].get(user_id, {}).get('Balance', 0)
    
    # Crear teclado
    keyboard = [
        [
            InlineKeyboardButton("📲 Bot → App", callback_data='transfer_bot_to_app'),
            InlineKeyboardButton("📱 App → Bot", callback_data='transfer_app_to_bot')
        ],
        [
            InlineKeyboardButton("📚 Tutorial", callback_data='tutorial_poker'),
            InlineKeyboardButton("⬇️ Descargar App", url=APP_DOWNLOAD_LINK)
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Mensaje con formato HTML
    response = (
        f"<b>🎮 MENÚ PRINCIPAL DE POKER</b>\n\n"
        f"💰 <b>Saldo disponible:</b> <code>${balance:,.2f}</code>\n\n"
        "🔹 <b>Bot → App</b> - Enviar saldo a GGPoker\n"
        "🔹 <b>App → Bot</b> - Retirar saldo a Telegram\n"
        "🔹 <b>Tutorial</b> - Guía paso a paso\n"
        "🔹 <b>Descargar App</b> - Instalar GGPoker\n\n"
        "<i>Selecciona una opción:</i>"
    )
    
    await query.edit_message_text(
        text=response,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def iniciar_transferencia_poker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de transferencia de Bot a App Poker"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['estado'] = 'ESPERANDO_MONTO_POKER'
    context.user_data['tipo_transferencia'] = 'BOT_A_APP'
    
    await query.edit_message_text(
        text="<b>💳 Transferir del Bot a App de Poker</b>\n\n"
             "📝 Por favor ingresa el <b>monto</b> que deseas transferir:\n\n"
             "💲 <b>Mínimo:</b> $250.00\n"
             "💲 <b>Máximo:</b> $5,000.00\n\n"
             "<i>Ejemplo: 500</i>",
        parse_mode='HTML'
    )

async def manejar_monto_poker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el monto ingresado para transferencia Bot→App"""
    try:
        monto = float(update.message.text.replace(',', ''))
        
        # Validaciones de monto
        if monto < 250:
            await update.message.reply_text(
                "❌ <b>Monto muy bajo</b>\n\n"
                "El monto mínimo es <b>$250.00</b>. Por favor ingresa una cantidad válida:",
                parse_mode='HTML'
            )
            return
            
        if monto > 5000:
            await update.message.reply_text(
                "❌ <b>Monto muy alto</b>\n\n"
                "El monto máximo es <b>$5,000.00</b>. Por favor ingresa una cantidad válida:",
                parse_mode='HTML'
            )
            return

        async with lock_data:  
            with open('user_data.json', 'r+') as f:  
                data = json.load(f)  
                user_id = str(update.effective_user.id)  
                
                if data['usuarios'][user_id]['Balance'] < monto:  
                    await update.message.reply_text(  
                        "❌ <b>Saldo insuficiente</b>\n\n"
                        "No tienes suficiente saldo disponible. Por favor ingresa un monto menor:",
                        parse_mode='HTML'  
                    )  
                    return  
                
                context.user_data['monto_poker'] = monto  
                context.user_data['estado'] = 'ESPERANDO_ID_POKER'  
                
                await update.message.reply_text(  
                    f"💰 <b>Monto a transferir:</b> ${monto:,.2f}\n\n"  
                    "📌 Ahora ingresa tu <b>ID de jugador</b> en la app Poker:\n\n"
                    "<i>Puedes encontrarlo en tu perfil dentro de la aplicación</i>",  
                    parse_mode='HTML'  
                )  
                
    except ValueError:  
        await update.message.reply_text(  
            "❌ <b>Formato inválido</b>\n\n"
            "Por favor ingresa solo números (ejemplo: <code>500</code> o <code>1250.50</code>):",  
            parse_mode='HTML'  
        )

async def manejar_id_poker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el ID de poker y solicita confirmación al usuario"""
    try:
        id_jugador = update.message.text.strip()
        monto = float(context.user_data['monto_poker'])
        user_id = str(update.effective_user.id)

        # Validación básica del ID
        if not id_jugador.isdigit() or len(id_jugador) < 5:
            await update.message.reply_text(
                "❌ <b>ID inválido</b>\n\n"
                "El ID de jugador debe contener solo números y tener al menos 5 dígitos. "
                "Por favor ingresa tu ID correctamente:",
                parse_mode='HTML'
            )
            return

        # Guardar datos para la confirmación
        context.user_data['id_jugador'] = id_jugador
        context.user_data['estado'] = 'ESPERANDO_CONFIRMACION_POKER'

        # Crear teclado de confirmación
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar Transferencia", callback_data=f"confirmar_poker_{user_id}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="poker")]
        ])

        await update.message.reply_text(
            f"🔐 <b>Confirmación requerida</b>\n\n"
            f"💰 Monto a transferir: <b>${monto:,.2f}</b>\n"
            f"🎮 ID Poker: <code>{id_jugador}</code>\n\n"
            "⚠️ Esta acción descontará el monto de tu saldo inmediatamente para aumentar en tu cuenta en la app\n"
            "¿Deseas continuar con la transferencia?",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:  
        print(f"ERROR manejar_id_poker: {str(e)}")  
        await update.message.reply_text(
            "❌ <b>Error al procesar tu solicitud</b>\n\n"
            "Por favor intenta nuevamente o contacta soporte.",
            parse_mode='HTML'
        )
        context.user_data.clear()

async def confirmar_transferencia_poker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la confirmación del usuario y envía a administradores"""
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = str(query.from_user.id)
        
        # Verificar que tenemos todos los datos necesarios
        if 'monto_poker' not in context.user_data or 'id_jugador' not in context.user_data:
            await query.edit_message_text("❌ Datos de transferencia no encontrados. Por favor inicia el proceso nuevamente.")
            return

        monto = float(context.user_data['monto_poker'])
        id_jugador = context.user_data['id_jugador']

        # Verificar saldo antes de proceder
        async with lock_data:
            with open('user_data.json', 'r+') as f:
                data = json.load(f)
                
                if data['usuarios'][user_id]['Balance'] < monto:
                    await query.edit_message_text(
                        "❌ <b>Saldo insuficiente</b>\n\n"
                        "No tienes suficiente saldo para completar esta transferencia.",
                        parse_mode='HTML'
                    )
                    context.user_data.clear()
                    return
                
                # Descontar el monto del saldo
                data['usuarios'][user_id]['Balance'] -= monto
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

        # Preparar datos para administradores
        monto_entero = int(monto * 100)
        callback_data = f"aprobarpoker_{user_id}_{monto_entero}_{id_jugador}"

        keyboard = InlineKeyboardMarkup([  
            [InlineKeyboardButton("✅ Verificar Transferencia", callback_data=callback_data)],
            [InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{user_id}")]
        ])

        mensaje_admin = (
            f"📌 <b>Nueva Transferencia (Bot→App Poker)</b>\n\n"
            f"🆔 Usuario: <code>{user_id}</code>\n"
            f"💰 Monto: <b>${monto:,.2f}</b> (ya descontado)\n"
            f"🎮 ID Poker: <code>{id_jugador}</code>\n\n"
            f"⚠️ Aumentar en la app poker aquí ya el bot desconto"
        )

        # Notificar al usuario
        await query.edit_message_text(
            "✅ <b>Transferencia confirmada!</b>\n\n"
            f"🔹 Monto descontado: <b>${monto:,.2f}</b>\n"
            f"🔹 ID Poker: <code>{id_jugador}</code>\n\n"
            "⏳ Un administrador verificará la transferencia en la app poker.",
            parse_mode='HTML'
        )

        # Enviar a administradores
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=mensaje_admin,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

        context.user_data.clear()

    except Exception as e:
        print(f"ERROR confirmar_transferencia_poker: {str(e)}")
        try:
            await query.edit_message_text(
                "❌ <b>Error al procesar tu confirmación</b>\n\n"
                "Por favor intenta nuevamente o contacta soporte.",
                parse_mode='HTML'
            )
        except:
            pass
        context.user_data.clear()


async def aprobar_solicitud_poker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprueba la transferencia de Bot a App Poker (solo notificación)"""
    query = update.callback_query
    
    try:
        await query.answer("Procesando aprobación...")
        
        # Parsear callback_data: "aprobar_poker_[user_id]_[monto_centavos]_[id_jugador]"
        parts = query.data.split('_')
        if len(parts) != 4:
            raise ValueError(f"Formato inválido. Se recibió: {query.data} (Se esperaban 4 partes, se obtuvieron {len(parts)})")

        prefix, user_id, monto_centavos, id_jugador = parts  # Ahora son 4 componentes
        monto = int(monto_centavos) / 100  # Convertir centavos a dólares

        # Notificar al usuario
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 <b>Transferencia aprobada!</b>\n\n"
                     f"🔹 Monto transferido: <b>${monto:,.2f}</b>\n"
                     f"🔹 ID Poker: <code>{id_jugador}</code>\n\n"
                     "¡El saldo ha sido depositado en tu cuenta de poker!",
                parse_mode='HTML'
            )
        except Exception as send_error:
            raise ValueError(f"No se pudo enviar mensaje al usuario: {str(send_error)}")
        
        # Actualizar mensaje de admin (con verificación de modificación)
        try:
            new_text = (
                f"✅ <b>Notificación enviada al usuario</b>\n\n"
                f"🆔 Usuario: <code>{user_id}</code>\n"
                f"💰 Monto: <b>${monto:,.2f}</b>\n"
                f"🎮 ID Poker: <code>{id_jugador}</code>"
            )
            if query.message.text != new_text:  # Solo editar si el contenido cambió
                await query.edit_message_text(
                    text=new_text,
                    parse_mode='HTML'
                )
        except Exception as edit_error:
            if "Message is not modified" not in str(edit_error):
                raise edit_error

    except Exception as e:
        error_msg = f"Error al procesar aprobación: {str(e)}"
        print(error_msg)
        
        try:
            await query.answer("❌ Error al procesar", show_alert=True)
            current_text = query.message.text if query.message else ""
            if "Error al procesar" not in current_text:  # Evitar bucle de errores
                await query.edit_message_text(
                    f"❌ Error al procesar la aprobación\n"
                    f"Detalle: {str(e)[:100]}",
                    parse_mode='HTML'
                )
        except Exception as e2:
            print(f"Error secundario al manejar error: {str(e2)}")
async def iniciar_transferencia_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de transferencia de App a Bot"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['estado'] = 'ESPERANDO_MONTO_APP_BOT'
    context.user_data['tipo_transferencia'] = 'APP_A_BOT'
    
    await query.edit_message_text(
        text="<b>💳 Transferir de App Poker a Bot</b>\n\n"
             "📝 Por favor ingresa el <b>monto</b> que deseas transferir:\n\n"
             "💲 <b>Mínimo:</b> $250.00\n"
             "💲 <b>Máximo:</b> $5,000.00\n\n"
             "<i>Ejemplo: 500</i>",
        parse_mode='HTML'
    )

async def manejar_monto_app_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el monto ingresado para transferencia App→Bot"""
    try:
        monto = float(update.message.text.replace(',', ''))
        
        # Validaciones de monto
        if monto < 250:
            await update.message.reply_text(
                "❌ <b>Monto muy bajo</b>\n\n"
                "El monto mínimo es <b>$250.00</b>. Por favor ingresa una cantidad válida:",
                parse_mode='HTML'
            )
            return
            
        if monto > 5000:
            await update.message.reply_text(
                "❌ <b>Monto muy alto</b>\n\n"
                "El monto máximo es <b>$5,000.00</b>. Por favor ingresa una cantidad válida:",
                parse_mode='HTML'
            )
            return

        context.user_data['monto_app_bot'] = monto  
        context.user_data['estado'] = 'ESPERANDO_ID_APP_BOT'  
        
        await update.message.reply_text(  
            f"💰 <b>Monto a transferir:</b> ${monto:,.2f}\n\n"  
            "📌 Ahora ingresa tu <b>ID de jugador</b> en la app Poker:\n\n"
            "<i>Puedes encontrarlo en tu perfil dentro de la aplicación</i>",  
            parse_mode='HTML'  
        )  
            
    except ValueError:  
        await update.message.reply_text(  
            "❌ <b>Formato inválido</b>\n\n"
            "Por favor ingresa solo números (ejemplo: <code>500</code> o <code>1250.50</code>):",  
            parse_mode='HTML'  
        )

async def manejar_id_app_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el ID de poker y solicita confirmación al usuario"""
    try:
        id_jugador = update.message.text.strip()
        monto = float(context.user_data['monto_app_bot'])
        user_id = str(update.effective_user.id)

        # Validación básica del ID
        if not id_jugador.isdigit() or len(id_jugador) < 5:
            await update.message.reply_text(
                "❌ <b>ID inválido</b>\n\n"
                "El ID de jugador debe contener solo números y tener al menos 5 dígitos. "
                "Por favor ingresa tu ID correctamente:",
                parse_mode='HTML'
            )
            return

        # Guardar datos para la confirmación
        context.user_data['id_jugador_app'] = id_jugador
        context.user_data['estado'] = 'ESPERANDO_CONFIRMACION_APP_BOT'

        # Crear teclado de confirmación
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar Transferencia", callback_data=f"confirmar_app_bot_{user_id}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_app_bot")]
        ])

        await update.message.reply_text(
            f"🔐 <b>Confirmación requerida</b>\n\n"
            f"💰 Monto a transferir: <b>${monto:,.2f}</b>\n"
            f"🎮 ID Poker: <code>{id_jugador}</code>\n\n"
            "⚠️ Esta transferencia debe ser verificada por un administrador.\n"
            "¿Confirmas que has realizado el pago en la app poker?",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:  
        print(f"ERROR manejar_id_app_bot: {str(e)}")  
        await update.message.reply_text(
            "❌ <b>Error al procesar tu solicitud</b>\n\n"
            "Por favor intenta nuevamente o contacta soporte.",
            parse_mode='HTML'
        )
        context.user_data.clear()

async def confirmar_transferencia_app_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la confirmación del usuario y envía a administradores"""
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = str(query.from_user.id)
        
        # Verificar que tenemos todos los datos necesarios
        if 'monto_app_bot' not in context.user_data or 'id_jugador_app' not in context.user_data:
            await query.edit_message_text("❌ Datos de transferencia no encontrados. Por favor inicia el proceso nuevamente.")
            return

        monto = float(context.user_data['monto_app_bot'])
        id_jugador = context.user_data['id_jugador_app']

        # Preparar datos para administradores (formato: aprobarappbot_[user_id]_[monto]_[id_jugador])
        callback_data = f"aprobarappbot_{user_id}_{monto}_{id_jugador}"

        keyboard = InlineKeyboardMarkup([  
            [InlineKeyboardButton("✅ Verificar y Aprobar", callback_data=callback_data)],
            [InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_app_{user_id}")]
        ])

        mensaje_admin = (
            f"📌 <b>Nueva Solicitud (App→Bot)</b>\n\n"
            f"🆔 Usuario: <code>{user_id}</code>\n"
            f"💰 Monto: <b>${monto:,.2f}</b>\n"
            f"🎮 ID Poker: <code>{id_jugador}</code>\n\n"
            f"⚠️ Descontar en la app poker antes de aprobar"
        )

        # Notificar al usuario
        await query.edit_message_text(
            "✅ <b>Solicitud confirmada y enviada!</b>\n\n"
            f"🔹 Monto: <b>${monto:,.2f}</b>\n"
            f"🔹 ID Poker: <code>{id_jugador}</code>\n\n"
            "⏳ Un administrador verificará tu transferencia en la app.",
            parse_mode='HTML'
        )

        # Enviar a administradores
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ADMIN,
            text=mensaje_admin,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

        context.user_data.clear()

    except Exception as e:
        print(f"ERROR confirmar_transferencia_app_bot: {str(e)}")
        try:
            await query.edit_message_text(
                "❌ <b>Error al procesar tu confirmación</b>\n\n"
                "Por favor intenta nuevamente o contacta soporte.",
                parse_mode='HTML'
            )
        except:
            pass
        context.user_data.clear()

async def aprobar_transferencia_app_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprueba la transferencia de App Poker a Bot (versión corregida)"""
    try:
        query = update.callback_query
        await query.answer("Procesando aprobación...")
        
        # Parsear callback_data: "aprobarappbot_[user_id]_[monto]_[id_jugador]"
        parts = query.data.split('_')
        if len(parts) != 4:
            raise ValueError(f"Formato inválido. Recibido: {query.data}")

        prefix, user_id, monto_str, id_jugador = parts
        monto = float(monto_str)

        # Lógica de aprobación (actualizar saldo)
        async with lock_data:
            with open('user_data.json', 'r+') as f:
                data = json.load(f)
                if user_id not in data['usuarios']:
                    raise ValueError(f"Usuario {user_id} no encontrado")
                    
                data['usuarios'][user_id]['Balance'] += monto
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

        # Notificar al usuario
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 <b>Transferencia verificada!</b>\n\n"
                 f"🔹 Monto acreditado: <b>${monto:,.2f}</b>\n"
                 f"🔹 ID Poker: <code>{id_jugador}</code>\n"
                 f"🔹 Nuevo saldo: <b>${data['usuarios'][user_id]['Balance']:,.2f}</b>\n\n"
                 "¡Gracias por tu paciencia!",
            parse_mode='HTML'
        )
        
        # Actualizar mensaje de admin
        await query.edit_message_text(
            f"✅ <b>Transferencia App→Bot aprobada</b>\n\n"
            f"🆔 Usuario: <code>{user_id}</code>\n"
            f"💰 Monto: <b>${monto:,.2f}</b>\n"
            f"🎮 ID Poker: <code>{id_jugador}</code>\n\n"
            f"🔄 Saldo actualizado en el bot",
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"ERROR aprobar_transferencia_app_bot: {str(e)}")
        try:
            await query.answer("❌ Error al procesar", show_alert=True)
            await query.edit_message_text(
                f"❌ Error al aprobar transferencia\n"
                f"Detalle: {str(e)[:100]}",
                parse_mode='HTML'
            )
        except Exception as e2:
            print(f"Error secundario: {str(e2)}")




async def tutorial_poker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra un tutorial completo sobre cómo transferir fondos al poker"""
    query = update.callback_query
    await query.answer()
    
    # Crear teclado con botones de acción
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Descargar App Poker", url=APP_DOWNLOAD_LINK)],
        [InlineKeyboardButton("🔙 Volver", callback_data="poker")]
    ])
    
    tutorial_text = """
🎮 <b>TUTORIAL COMPLETO PARA TRANSFERIR INICIAR</b> 🎮

1️⃣ <b>PASO 1: DESCARGAR LA APP</b>
   👉 Presiona el botón <b>"Descargar App Poker"</b> aquí abajo
   👉 Instala la aplicación en tu dispositivo


2️⃣ <b>PASO 2: UNIRSE AL CLUB</b>
   🔹 Abre la aplicación y ve a la sección <b>"Clubs"</b>
   🔹 Busca e ingresa este ID de club exacto:
     <code>319757</code>
   🔹Selecciona el club que te aparece QvaPlay 💫 


3️⃣ <b>PASO 3: TRANSFERIR FONDOS</b>
   💰 Usa nuestro bot para transferir:
     1. Selecciona <b>"Transferir de Bot a App"</b>
     2. Ingresa el monto que deseas transferir
     3. Proporciona tu <b>ID de jugador</b> de la app
     4. Confirma la operación


✨ <b>¡Listo! Los fondos aparecerán en tu cuenta poker en minutos, a jugar poker 🤑💸</b>
"""
    
    try:
        await query.edit_message_text(
            text=tutorial_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Error al mostrar tutorial poker: {str(e)}")
        await query.message.reply_text(
            text=tutorial_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )    
        
        
        
@verificar_bloqueo
async def promocionar(update: Update, context: CallbackContext):
    try:
        keyboard = [
            [InlineKeyboardButton("📱 WhatsApp", callback_data="promo_whatsapp")],
            [InlineKeyboardButton("📘 Facebook", callback_data="promo_facebook")],
            [InlineKeyboardButton("🔙 Menú principal", callback_data="menu_principal")]
        ]
        
        await update.message.reply_text(
            "📢 <b>Promociona QvaPlay y gana recompensas</b>\n\n"
            "1. Comparte nuestro bot en tus estados de WhatsApp o Facebook\n"
            "2. Toma captura de pantalla\n"
            "3. Envíala aquí y verifica\n"
            "4. Recibe tu recompensa automáticamente\n\n"
            "🎁 <b>Recompensa:</b> 100 CUP en bono por cada tarea\n\n"
            "Comparte y luego presionas la red social donde compartiste:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        logger.error(f"Error en promocionar: {str(e)}")
        await update.message.reply_text("❌ Error al mostrar opciones de promoción")
        
async def seleccionar_red_social(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    red_social = query.data.split("_")[1]  # whatsapp o facebook
    context.user_data['promo_red_social'] = red_social
    
    await query.edit_message_text(
        f"📸 <b>Envía la captura de tu estado de {red_social.capitalize()}</b>\n\n"
        "Requisitos:\n"
        "1. Debe verse claramente que es tu estado\n"
        "2. Debe incluir el enlace a QvaPlay\n"
        "3. No pueden ser capturas editadas\n\n"
        "⚠️ Envía solo la imagen, sin texto adicional",
        parse_mode="HTML")
    
    context.user_data['esperando_captura_promo'] = True
    
                    
async def procesar_captura_promo(update: Update, context: CallbackContext):
    # Verificar si estamos esperando una captura de promoción
    if not context.user_data.get('esperando_captura_promo', False):
        return  # No hacer nada si no estamos en flujo de promoción
    
    try:
        user = update.message.from_user
        user_id = str(user.id)
        
        # Obtener la foto de mayor calidad
        photo_file = await update.message.photo[-1].get_file()
        
        # Guardar temporalmente en user_data
        context.user_data['promo_photo_id'] = photo_file.file_id
        context.user_data['promo_username'] = user.full_name
        
        # Crear teclado de confirmación
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar cumplimiento", callback_data="confirmar_promo_")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_promo")]
        ]
        
        # Responder con la misma foto y botones
        await update.message.reply_photo(
            photo=photo_file.file_id,
            caption=f"📸 <b>Captura recibida de {user.full_name}</b>\n\n"
                   "Por favor confirma que esta captura cumple con:\n"
                   "1. Se ve claramente que es tu estado\n"
                   "2. Incluye el enlace a QvaPlay\n"
                   "3. No es una edición\n\n"
                   "¿Es correcta?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Limpiar el estado de espera
        context.user_data['esperando_captura_promo'] = False
        
    except Exception as e:
        logger.error(f"Error procesando captura: {str(e)}")
        await update.message.reply_text("❌ Error al procesar tu captura. Intenta nuevamente.")
        
        
async def confirmar_promocion(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    try:
        user_data = context.user_data
        if 'promo_photo_id' not in user_data:
            try:
                await query.edit_message_text("❌ No se encontró la captura. Intenta nuevamente.")
            except BadRequest:
                await query.edit_message_caption(caption="❌ No se encontró la captura. Intenta nuevamente.")
            return
            
        user_id = str(query.from_user.id)
        red_social = user_data.get('promo_red_social', 'red social')
        
        # Verificar si ya recibió recompensa hoy
        hoy = datetime.now().strftime('%Y-%m-%d')
        promo_key = f"promo_{red_social}_{hoy}"
        
        # Verificar en base de datos si ya reclamó hoy (clave compuesta)
        promocion_existente = obtener_registro("promociones", (user_id, promo_key), "clave")
        if promocion_existente:
            try:
                await query.edit_message_text("⚠️ Ya recibiste recompensa por promocionar hoy en esta red social")
            except BadRequest:
                await query.edit_message_caption(
                    caption="⚠️ Ya recibiste recompensa por promocionar hoy en esta red social",
                    reply_markup=None
                )
            return
            
        # Verificar si el usuario tiene más de 200 referidos
        usuario_data = obtener_registro("usuarios", user_id, "Referidos")
        if usuario_data and usuario_data[0] > 200:
            try:
                await query.edit_message_text("❌ Esta promoción es válida solo para nuevos usuarios.")
            except BadRequest:
                await query.edit_message_caption(caption="❌ Esta promoción es válida solo para nuevos usuarios.")
            return
        
        # Asignar recompensas
        recompensa_bono = 100
        recompensa_rollover = 800
        
        # Obtener datos actuales del bono
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido, Rollover_actual, Bono_retirable")
        
        if not bono_data:
            # Crear nuevo registro de bono
            exito_bono = actualizar_registro(
                "bono_apuesta",
                user_id,  # Clave simple
                {
                    "Bono": recompensa_bono,
                    "Rollover_requerido": recompensa_rollover,
                    "Rollover_actual": 0,
                    "Bono_retirable": 0
                }
            )
            bono_actual = recompensa_bono
            rollover_actual = recompensa_rollover
        else:
            # Actualizar bono existente
            bono_actual = bono_data[0] + recompensa_bono
            rollover_actual = bono_data[1] + recompensa_rollover
            rollover_actual_db = bono_data[2] if len(bono_data) > 2 else 0
            bono_retirable = bono_data[3] if len(bono_data) > 3 else 0
            
            exito_bono = actualizar_registro(
                "bono_apuesta",
                user_id,  # Clave simple
                {
                    "Bono": bono_actual,
                    "Rollover_requerido": rollover_actual
                }
            )
        
        # Registrar promoción en la base de datos (clave compuesta)
        exito_promo = actualizar_registro(
            "promociones",
            (user_id, promo_key),  # Clave compuesta (id, clave)
            {
                "fecha": hoy,
                "red_social": red_social,
                "recompensa": f"{recompensa_bono} CUP bono + {recompensa_rollover} CUP rollover"
            }
        )
        
        if not exito_bono or not exito_promo:
            try:
                await query.edit_message_text("❌ Error al procesar la promoción. Intenta nuevamente.")
            except BadRequest:
                await query.edit_message_caption(caption="❌ Error al procesar la promoción. Intenta nuevamente.")
            return
        
        # Notificar al usuario
        try:
            await query.edit_message_caption(
                caption=f"🎉 <b>¡Promoción confirmada!</b>\n\n"
                       f"Has recibido:\n"
                       f"🎁 +{recompensa_bono} CUP en bono\n"
                       f"🔄 +{recompensa_rollover} CUP en rollover requerido\n\n"
                       f"¡Gracias por promocionar QvaPlay!",
                parse_mode="HTML"
            )
        except BadRequest:
            await query.edit_message_text(
                f"🎉 <b>¡Promoción confirmada!</b>\n\n"
                f"Has recibido:\n"
                f"🎁 +{recompensa_bono} CUP en bono\n"
                f"🔄 +{recompensa_rollover} CUP en rollover requerido\n\n"
                f"¡Gracias por promocionar QvaPlay!",
                parse_mode="HTML"
            )
        
        # Enviar notificación a administradores
        admin_msg = (
            f"📢 <b>Nueva promoción confirmada</b>\n\n"
            f"👤 Usuario: {user_data.get('promo_username', 'Usuario')}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📱 Red: {red_social.capitalize()}\n"
            f"💰 Recompensa: {recompensa_bono} CUP bono + {recompensa_rollover} CUP rollover\n"
            f"💎 Bono total: {bono_actual} CUP\n"
            f"🔄 Rollover total: {rollover_actual} CUP"
        )
        
        await context.bot.send_photo(
            chat_id=REGISTRO_MINIJUEGOS,
            photo=user_data['promo_photo_id'],
            caption=admin_msg,
            parse_mode="HTML"
        )
        
        # Limpiar datos temporales
        for key in ['promo_photo_id', 'promo_username', 'promo_red_social']:
            if key in user_data:
                del user_data[key]
                
    except Exception as e:
        logger.error(f"Error confirmando promoción: {str(e)}")
        try:
            await query.edit_message_text("❌ Error al confirmar tu promoción. Reporta este error.")
        except BadRequest:
            await query.edit_message_caption(caption="❌ Error al confirmar tu promoción. Reporta este error.")
async def cancelar_promocion(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Limpiar el estado
    for key in ['promo_photo_id', 'promo_username', 'promo_red_social', 'esperando_captura_promo']:
        if key in context.user_data:
            del context.user_data[key]
    
    await query.edit_message_caption(
        caption="❌ Promoción cancelada",
        reply_markup=None
    )
        
        
        
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.error and "mantenimiento" in str(context.error):
        return  # Silencia errores de mantenimiento
    
    print(f"⚠️ Error no controlado: {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("❌ Ocurrió un error inesperado")        
def run_bot():
    try:
        # Inicialización explícita del estado
        global bot_activo, tiempo_restante, motivo_mantenimiento
        bot_activo = True  # Asegurar que inicia activo
        tiempo_restante = 0
        motivo_mantenimiento = ""
        
        application = Application.builder().token(TOKEN).build()
        
        # Configura el JobQueue para limpieza de caché
        job_queue = application.job_queue
    
        if job_queue:
            # Limpieza cada 10 minutos (600 segundos)
            job_queue.run_repeating(
                limpiar_cache,                
                interval=600.0,
                first=100.0  # Primera ejecución después de 10 segundos
            )
            print("✅ Tarea periódica de limpieza de caché configurada")
                                  
            
            # Inicializar tareas del juego pirata
            init_tareas_pirata(application)
            print("✅ Tareas periódicas del juego pirata configuradas")
            
            # Reiniciar ranking semanal todos los domingos a las 12:00 AM (hora de Cuba)
            job_queue.run_daily(
                reiniciar_ranking,
                time=time(hour=9, minute=26, tzinfo=pytz.timezone("America/Havana")),  # 12 AM hora Cuba
                days=(6,)  # Domingo = 6
            )
            print("✅ Tarea de reinicio semanal de ranking configurada")
            
            job_queue.run_daily(
                revisar_inactividad_fantasy,
                time=time(hour=15, minute=00, tzinfo=pytz.timezone("America/Havana")),  # 12 AM hora Cuba
                days=(2, 5)  # Domingo = 6
            )                        
            print("✅ Tarea diaria de revisión de inactividad en fantasy configurada")
            
            
            
            
            """job_queue.run_daily(
                actualizar_jugadores,
                time=time(hour=9, minute=00, tzinfo=pytz.timezone("America/Havana"))
            )"""
            job_queue.run_repeating(backup_periodico, interval=86400, first=10)
            print("✅ Tarea diaria de backups db configurada")
            
            

        else:
            print("⚠️ JobQueue no disponible - No se configuró job")
        
        
        
        
        
        # Handler global PRIMERO (grupo -1)
        application.add_handler(TypeHandler(Update, filtro_global), group=-1)
        
        # Handlers normales DESPUÉS (grupo 0)
        application.add_handler(CommandHandler("on", encender_bot))
        application.add_handler(CommandHandler("off", apagar_bot))
        # ... otros handlers ...
        
        # Debug de estructura
        print("\n🔍 Handlers registrados:")
        for group, handlers in application.handlers.items():
            print(f"Grupo {group}:")
            for handler in handlers:
                print(f"  → {handler.__class__.__name__}")
        application.add_handler(CommandHandler("ban", banear_usuario))  # Comando /ban
        application.add_handler(CommandHandler("unban", desbanear_usuario))  # Comando /unban
        application.add_handler(CommandHandler("basura", comando_basura))
        application.add_handler(CommandHandler("basura_user", comando_basura_user))
        application.add_handler(CommandHandler("eliminar", eliminar_usuario_handler))
        
        application.add_handler(CommandHandler("regalo_on", regalo_on))
        application.add_handler(CommandHandler("regalo_off", regalo_off))
        application.add_handler(MessageHandler(filters.Chat(GROUP_CHAT_ID) & ~filters.COMMAND, contar_mensajes_para_regalo))    
    
        
              
                          
                                                  
        # Comandos
        application.add_handler(CommandHandler("start", start))
        get_handler = CommandHandler('get', get_user_data)
        application.add_handler(get_handler)
        application.add_handler(CommandHandler("balance", modify_balance))
        application.add_handler(CommandHandler("lider", modify_leader))
        application.add_handler(CommandHandler("resumen_apuestas", resumen_apuestas))
        application.add_handler(CommandHandler("invitar", Invita_Gana))
        

        
        application.add_handler(
    MessageHandler(
        filters.Regex(r'^/local\s+\d+\s+visitante\s+\d+\s+\(.+?\)$'),
        procesar_marcador
    )
)

        application.add_handler(CallbackQueryHandler(poker, pattern='^poker$'))
        # En tu función donde configuras la aplicación (donde tienes application.add_handler)
        application.add_handler(CallbackQueryHandler(iniciar_transferencia_poker, pattern='^transfer_bot_to_app$'))
        application.add_handler(CallbackQueryHandler(iniciar_transferencia_bot, pattern='^transfer_app_to_bot$'))
        application.add_handler(CallbackQueryHandler(
    aprobar_solicitud_poker,
    pattern='^aprobarpoker_'
))

        # Handlers necesarios
        application.add_handler(CallbackQueryHandler(
    confirmar_transferencia_app_bot,
    pattern='^confirmar_app_bot_'
))

        application.add_handler(CallbackQueryHandler(
    aprobar_transferencia_app_bot,
    pattern='^aprobarappbot_'
))
        # Registra los handlers en tu aplicación
        application.add_handler(CallbackQueryHandler(
    confirmar_transferencia_poker,
    pattern='^confirmar_poker_'
))
        application.add_handler(CallbackQueryHandler(
    tutorial_poker,
    pattern='^tutorial_poker'
))


    
    
        application.add_handler(CallbackQueryHandler(menu_soporte, pattern='^menu_soporte$'))
        application.add_handler(CallbackQueryHandler(handle_soporte_callback, pattern='^(contactar_admin|apuesta_mal_pagada|apuesta_atrasada)$'))
        application.add_handler(CallbackQueryHandler(contactar_soporte_ticket, pattern=r'^soporte_'))
        
        application.add_handler(CallbackQueryHandler(actualizar_estado, pattern=r'^revisar_'))
        application.add_handler(CallbackQueryHandler(resolver_apuesta, pattern=r'^resolver_'))
                         

    
    
        # Registrar los handlers en tu aplicación
        application.add_handler(CommandHandler("bono", bono_command))
        application.add_handler(CommandHandler("rollover_actual", rollover_actual_command))
        application.add_handler(CommandHandler("rollover_requerido", rollover_requerido_command))
        application.add_handler(CommandHandler("bono_retirable", bono_retirable_command))
        application.add_handler(CommandHandler("barriles", modify_barriles))
        application.add_handler(CommandHandler("referidos", modify_referidos))        
        application.add_handler(CommandHandler("resumentareas", resumen_tareas))
        application.add_handler(CommandHandler("killtarea", kill_tarea))
        application.add_handler(CommandHandler("resumen_apuestas", resumen_apuestas))
        application.add_handler(CommandHandler("sms_global", sms_global))
        
        application.add_handler(CallbackQueryHandler(detalles_partido, pattern="^detalles_"))
        application.add_handler(CallbackQueryHandler(eliminar_apuesta, pattern="^eliminar_"))
        application.add_handler(CallbackQueryHandler(reembolsar_apuestas, pattern="^reembolsar_"))
        application.add_handler(CallbackQueryHandler(reembolsar_apuesta, pattern="^reembolsarapuesta_"))
        application.add_handler(CallbackQueryHandler(ganada_apuesta, pattern="^ganada_"))
        application.add_handler(CallbackQueryHandler(perdida_apuesta, pattern="^perdida_"))
        application.add_handler(CallbackQueryHandler(pagar_apuestas_ganadoras, pattern="^win_"))
        application.add_handler(CallbackQueryHandler(bono_diario, pattern="^bono_diario$"))
        
        
        
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, manejar_mensajes))

        
# Registra el manejador de mensajes reenviados tareas pagadas
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.FORWARDED, handle_forwarded_message)) 
       
        application.add_handler(CallbackQueryHandler(mantenimiento, pattern="mantenimiento"))
                                 
# Handler para el botón "⚽ Fútbol"
        application.add_handler(CallbackQueryHandler(mostrar_deportes, pattern="^mostrar_deportes$"))
        application.add_handler(CallbackQueryHandler(mostrar_tipos_apuestas, pattern="^mostrar_tipos_apuestas$"))
        application.add_handler(CallbackQueryHandler(mostrar_futbol_live, pattern="^mostrar_futbol_live$"))
        application.add_handler(CallbackQueryHandler(mostrar_eventos_live, pattern='^ligaslive_'))
        application.add_handler(CallbackQueryHandler(manejar_navegacion_ligas_live, pattern=r"^paginalive_\d+$"))
        # En tu archivo principal (donde defines los handlers):
        application.add_handler(CallbackQueryHandler(mostrar_mercados_en_vivo, pattern="^mercado_vivo_")) 
        
        application.add_handler(CallbackQueryHandler(handle_pago_combinada, pattern="^pago_(bono|balance)_combinada$"))
        application.add_handler(CallbackQueryHandler(confirmar_combinada_handler, pattern="^confirmar_combinada$"))
        application.add_handler(CallbackQueryHandler(manejar_acciones_combinadas, pattern="^(remove_apuesta_|procesar_payment_combinada|cancelar_combinada)"))
        application.add_handler(CallbackQueryHandler(handle_combinadas_callback, pattern="^handle_combinadas_callback$"))
        application.add_handler(CallbackQueryHandler(handle_prepartido_callback, pattern="^handle_prepartido_callback$"))
        application.add_handler(CallbackQueryHandler(handle_vivo_callback, pattern="^handle_vivo_callback$"))
                              
                                           
          
        
        
       
# Añadir el CallbackQueryHandler para manejar la selección del deporte
        application.add_handler(CallbackQueryHandler(seleccionar_deporte, pattern='^deporte_'))
        
        # Registrar el manejador de navegación
        application.add_handler(CallbackQueryHandler(manejar_navegacion, pattern=r"^pagina_\d+$"))
        # manejar futbol país liga
        application.add_handler(CallbackQueryHandler(manejar_seleccion_pais, pattern="^pais_"))
        application.add_handler(CallbackQueryHandler(mostrar_ligas_principales, pattern="^mostrar_ligas_principales"))
        application.add_handler(CallbackQueryHandler(manejar_paginacion_paises, pattern="^(paises_prev|paises_next)$"))
        # Para ligas de fútbol (usa API-FOOTBALL)
        application.add_handler(CallbackQueryHandler(seleccionar_liga_futbol, pattern=r'^ligas_futbol_\d+$'))

# Para ligas de otros deportes (usa The Odds API)
        application.add_handler(CallbackQueryHandler(seleccionar_liga, pattern=r'^ligas_[a-zA-Z]'))
        application.add_handler(CallbackQueryHandler(mostrar_todos_partidos_live, pattern="^mostrar_todos_live$"))
        
        application.add_handler(CallbackQueryHandler(mostrar_todos_partidos_live, pattern="^mostrar_todos_live_prev$"))
        application.add_handler(CallbackQueryHandler(mostrar_todos_partidos_live, pattern="^mostrar_todos_live_next$"))
        
        
        
        
        application.add_handler(CallbackQueryHandler(mostrar_mercados_evento, pattern=r"^evento_"))
        # Cambia los patrones para que coincidan con lo que realmente generas
        application.add_handler(CallbackQueryHandler(mostrar_opciones_mercado_futbol, pattern=r'^load_.+'))
        
        # Asegúrate de que este sea el ÚLTIMO handler que registras para callbacks
        application.add_handler(CallbackQueryHandler(handle_market_selection, pattern="^sel_"))
        application.add_handler(CallbackQueryHandler(cargar_mercado_otros_deportes, pattern="^(loadO_mkt_|verO_mkt_|verO_grp_)"))
        application.add_handler(CallbackQueryHandler(refresh_evento, pattern=r'^refresh_'))
    
    # Handler para botones sin acción
        application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^no_action$"))
        
        application.add_handler(CallbackQueryHandler(manejar_metodo_pago, pattern="^pago_bono$"))
        application.add_handler(CallbackQueryHandler(manejar_metodo_pago, pattern="^pago_balance$"))
        application.add_handler(CallbackQueryHandler(confirmar_apuesta, pattern=r"^confirmar_apuesta"))
        application.add_handler(CallbackQueryHandler(cancelar_apuesta, pattern=r"^(confirmar_cancelar|cancelar_apuesta):.*"))
        application.add_handler(CallbackQueryHandler(handle_resumen_callback, pattern="^resumen_"))
        application.add_handler(CallbackQueryHandler(buscar_equipo, pattern="^buscar_equipo$"))
        application.add_handler(CallbackQueryHandler(mostrar_partidos_equipo, pattern="^equipo_"))
        
        
        application.add_handler(CallbackQueryHandler(show_medalla, pattern="^show_medalla$"))
        application.add_handler(CallbackQueryHandler(medallas_detalles, pattern="^medallas_detalles$"))
        application.add_handler(CallbackQueryHandler(mis_apuestas, pattern="^mis_apuestas$"))
        application.add_handler(CallbackQueryHandler(mostrar_apuestas_seleccion, pattern="^ver_apuestas:"))
        application.add_handler(CallbackQueryHandler(mostrar_apuestas_seleccion, pattern="^pagina:"))
        application.add_handler(CallbackQueryHandler(Admin_Panel, pattern="^Admin_Panel$"))
        application.add_handler(CallbackQueryHandler(resumen_minijuegos, pattern="^resumen_minijuegos$"))
        application.add_handler(CallbackQueryHandler(ejecutar_pagar, pattern="^ejecutar_pagar$"))
        application.add_handler(CallbackQueryHandler(detener_pagos, pattern="^detener_pagos$"))
        application.add_handler(CallbackQueryHandler(resumen_apuestas, pattern="^resumen_apuestas$"))
        application.add_handler(CallbackQueryHandler(transferencia_interna, pattern="^transferencia_interna$"))
        application.add_handler(CallbackQueryHandler(confirmar_transferencia, pattern="^confirmar_transferencia$"))
        application.add_handler(CallbackQueryHandler(deposit, pattern="^depositar$"))
        application.add_handler(CallbackQueryHandler(criptomonedas, pattern="^criptomonedas$"))
        application.add_handler(CallbackQueryHandler(handle_payment_method, pattern="^(banca|doge|ltc|btc|solana|trx|ton|bnb|eth|bch|dgb)$"))
        application.add_handler(CallbackQueryHandler(confirmar_datos_deposito, pattern="^(bpa|bandec|mlc|metro|saldo_movil|enzona|mi_transfer)$"))
        application.add_handler(CallbackQueryHandler(manejar_verificacion, pattern="^(verificar_deposito)$"))
        application.add_handler(CallbackQueryHandler(withdraw, pattern="^retirar$"))
        application.add_handler(CallbackQueryHandler(saldo_movil_mantenimiento_callback, pattern="^saldo_movil_mantenimiento$"))
        
        
        
        application.add_handler(CallbackQueryHandler(tarjeta_retiro_callback, pattern="^withdraw_tarjeta$"))
        application.add_handler(CallbackQueryHandler(procesar_retiro_saldo, pattern="^withdraw_saldo$"))
        application.add_handler(CallbackQueryHandler(confirm_withdraw, pattern="^confirmar_retiro_(tarjeta|saldo_movil)$"))
        application.add_handler(CallbackQueryHandler(finalizar_retiro, pattern="^finalizar_retiro_(tarjeta|saldo_movil)$"))
        
        application.add_handler(CallbackQueryHandler(accept_withdraw, pattern="^aprobar_retiro_"))
        application.add_handler(CallbackQueryHandler(reject_withdraw, pattern="^rechazar_retiro_"))
        
        application.add_handler(CallbackQueryHandler(handle_menu_principal, pattern="menu_principal"))
        application.add_handler(CallbackQueryHandler(show_balance, pattern="^Mi Saldo$"))
        application.add_handler(CallbackQueryHandler(show_balance, pattern="^show_balance$"))
        application.add_handler(CallbackQueryHandler(registrar_telefono_callback, pattern="^registrar_telefono$"))
        application.add_handler(CallbackQueryHandler(gestion_bonos, pattern="^gestion_bonos$"))
        application.add_handler(CallbackQueryHandler(transferir_bono, pattern="^transferir_bono$")) 
        application.add_handler(CallbackQueryHandler(info_bonos, pattern="^info_bonos$"))

        # Agregar el handler de minijuegos
        application.add_handler(CallbackQueryHandler(minijuegos, pattern="^Minijuegos$"))
        application.add_handler(CallbackQueryHandler(enviar_captura_deposito, pattern="^enviar_captura_deposito$"))
        application.add_handler(CallbackQueryHandler(send_to_admin, pattern=r"^send_to_admin_\d+$"))
        application.add_handler(MessageHandler(
    filters.PHOTO & ~filters.COMMAND,
    procesar_captura_promo
), group=1)

        application.add_handler(MessageHandler(
    filters.PHOTO,
    handle_captura
), group=2)  # menor prioridad
        application.add_handler(CallbackQueryHandler(accept_deposit, pattern=r"^accept_deposit_\d+$"))
        application.add_handler(CallbackQueryHandler(reject_deposit, pattern=r"^reject_deposit_\d+$"))

        application.add_handler(CallbackQueryHandler(handle_tareas_pagadas, pattern='^Tareas_Pagadas$'))
        application.add_handler(CallbackQueryHandler(mis_tareas, pattern='^mis_tareas$'))
        application.add_handler(CallbackQueryHandler(agregar_tarea, pattern='^agregar_tarea$'))
        application.add_handler(CallbackQueryHandler(confirmar_tarea, pattern='^confirmar_tarea$'))
        application.add_handler(CallbackQueryHandler(ver_tareas_disponibles, pattern='^ver_tareas_disponibles$'))
        application.add_handler(CallbackQueryHandler(verificar_tarea, pattern="^verificar_"))
        application.add_handler(CallbackQueryHandler(omitir_tarea, pattern="^omitir_tarea_"))
        application.add_handler(CallbackQueryHandler(alta_baja, pattern="alta_baja"))  # Handler para iniciar el juego
        application.add_handler(CallbackQueryHandler(choose_payment_method, pattern="method_bono|method_balance"))  # Handler para elegir método de pago
        application.add_handler(CallbackQueryHandler(set_bet_amount, pattern="bet_10|bet_30|bet_50"))  # Handler para establecer la apuesta
        application.add_handler(CallbackQueryHandler(handle_alta_baja, pattern="alta|baja")) 
        
        
 
        
        
        
        application.add_handler(CallbackQueryHandler(juego_pirata, pattern='^juego_pirata$'))
        application.add_handler(CallbackQueryHandler(comprar_piratas, pattern='^comprar_piratas$'))
        application.add_handler(CallbackQueryHandler(confirmar_compra_piratas, pattern='^confirmar_compra_piratas$'))
        # Handlers para mejoras de elementos
        # Handlers CORRECTOS para las mejoras:
        application.add_handler(CallbackQueryHandler(
    lambda update, context: mejorar_elemento(update, context, "velas"), 
    pattern="^mejorar_velas$"
))
        application.add_handler(CallbackQueryHandler(
    lambda update, context: confirmar_mejora_elemento(update, context, "velas"), 
    pattern="^confirmar_mejora_velas$"
))
        application.add_handler(CallbackQueryHandler(
    lambda update, context: mejorar_elemento(update, context, "cañones"), 
    pattern="^mejorar_cañones$"
))
        application.add_handler(CallbackQueryHandler(
    lambda update, context: confirmar_mejora_elemento(update, context, "cañones"), 
    pattern="^confirmar_mejora_cañones$"
))
        application.add_handler(CallbackQueryHandler(
    lambda update, context: mejorar_elemento(update, context, "barco"), 
    pattern="^mejorar_barco$"
))
        application.add_handler(CallbackQueryHandler(
    lambda update, context: confirmar_mejora_elemento(update, context, "barco"), 
    pattern="^confirmar_mejora_barco$"
))
        
        application.add_handler(CallbackQueryHandler(ver_balance, pattern='^ver_balance$'))
        application.add_handler(CallbackQueryHandler(reclamar_ganancias, pattern='^reclamar_ganancias$'))

        # Agregar los handlers para manejar ventas y compras
        application.add_handler(CallbackQueryHandler(vender_barriles, pattern="^vender_barriles$"))
        
        application.add_handler(CallbackQueryHandler(recibir_cantidad_vender, pattern=r"^(1000|25000|100000)$"))
        application.add_handler(CallbackQueryHandler(confirmar_vender, pattern="^confirmar_vender$"))
        application.add_handler(CallbackQueryHandler(comprar_barriles, pattern="^comprar_barriles$"))
        application.add_handler(CallbackQueryHandler(recibir_cantidad_comprar, pattern="^(100|250|1000)$"))
        application.add_handler(CallbackQueryHandler(confirmar_comprar, pattern="^confirmar_comprar$"))
        application.add_handler(CallbackQueryHandler(mostrar_eventos_activos, pattern="^ver_eventos$"))
        
        
        application.add_handler(CallbackQueryHandler(menu_combate_pvp, pattern="^menu_combate$"))
        application.add_handler(CallbackQueryHandler(mostrar_ranking_pvp, pattern="^ranking_pvp$"))
        
        
        
        # ======================
# HANDLERS PARA PVP
# ======================

# Menú principal de combate PvP
        application.add_handler(CallbackQueryHandler(menu_combate_pvp, pattern="^menu_combate$"))

# Búsqueda de oponente para combate
        application.add_handler(CallbackQueryHandler(buscar_combate, pattern="^buscar_combate$"))

# Confirmación de ataque a oponente
        application.add_handler(CallbackQueryHandler(confirmar_ataque, pattern="^confirmar_ataque$"))
        application.add_handler(CallbackQueryHandler(confirmar_combate, pattern="^confirmar_combate$"))

# Reparación de barco dañado
        application.add_handler(CallbackQueryHandler(reparar_barco, pattern="^reparar_barco$"))

# Compra de escudos (básico y premium)
      
        application.add_handler(CallbackQueryHandler(confirmar_escudo_basico, pattern='^confirmar_escudo_basico$'))
        application.add_handler(CallbackQueryHandler(confirmar_escudo_premium, pattern='^confirmar_escudo_premium$'))
        application.add_handler(CallbackQueryHandler(comprar_escudo_handler, pattern='^comprar_escudo_(basico|premium)$'))
        application.add_handler(CallbackQueryHandler(mercado_pirata, pattern="^mercado_pirata$"))
        application.add_handler(CommandHandler("top_pirata", top_pirata))
        
        


           
        
        
        application.add_handler(CallbackQueryHandler(bolita, pattern=r"^La_bolita$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🇺🇸 Florida🌞 \\[1:35 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🇺🇸 Florida🌙 \\[9:50 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🇺🇸 Florida🌚 \\[6:00 AM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🔐 Florida \\(cerrado\\)$"))

        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🍑 Georgia🌞 \\[12:30 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🍑 Georgia⛅ \\[7:00 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🍑 Georgia🌛 \\[11:35 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🔐 Georgia \\(cerrado\\)$"))

        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🗽 New_York🌞 \\[2:30 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🗽 New_York🌛 \\[10:30 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🔐 New_York \\(cerrado\\)$"))

        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🇭🇹 Haití🌞 \\[12:00 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🇭🇹 Haití🌛 \\[9:00 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🔐 Haití \\(cerrado\\)$"))

        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🏙️ Miami🌛 \\[10:00 PM\\]$"))
        application.add_handler(CallbackQueryHandler(seleccionar_loteria, pattern="^🔐 Miami \\(cerrado\\)$"))

        application.add_handler(CommandHandler("resumenloterias", resumen_loterias))
        application.add_handler(CommandHandler("refrescarloterias", refrescar_loterias))

    
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_jugada))
        application.add_handler(CallbackQueryHandler(procesar_jugada, pattern="^procesar_jugada$"))
        application.add_handler(CallbackQueryHandler(Piedra_Papel_Tijera, pattern="^Piedra_Papel_Tijera$"))
        application.add_handler(CallbackQueryHandler(confirmar_metodo_ppt, pattern="ppt_method_(bono|balance)"))
        application.add_handler(CallbackQueryHandler(manejar_jugada, pattern="^(piedra|papel|tijera)$"))
        application.add_handler(CallbackQueryHandler(confirmar_juego_ppt, pattern="^confirmar_juego_ppt$"))
        
        
        
        application.add_handler(CallbackQueryHandler(abrir_cofre_final, pattern="confirmar_apertura"))
        application.add_handler(CallbackQueryHandler(confirmar_cofre, pattern="cofre_bono|cofre_vip|cofre_especial"))
        application.add_handler(CallbackQueryHandler(abrir_cofre, pattern="abrir_cofre"))
        
        
        
        
        application.add_handler(CallbackQueryHandler(Invita_Gana, pattern="^Invita_Gana$"))
        # Definir el handler primero
        application.add_handler(CallbackQueryHandler(compartir_invitacion, pattern="^invitar$"))
        application.add_handler(CallbackQueryHandler(menu_soporte, pattern="^menu_soporte$"))
        application.add_handler(CallbackQueryHandler(enviar_reglas, pattern="^Reglas$"))        
        application.add_handler(CallbackQueryHandler(botones_reglas, pattern='^(bolita_reglas|apuestas_reglas|depositos_retiros_reglas|bonos_reglas|minijuegos_reglas|version_reglas)$'))
        application.add_handler(CallbackQueryHandler(Pronosticos, pattern="^Pronosticos$"))
        application.add_handler(CallbackQueryHandler(pronosticos_bolita, pattern="^pronosticos_bolita$"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_mensaje_soporte))
        application.add_handler(CallbackQueryHandler(manejar_acciones_admin, pattern='^(responder|bloquear)_'))
        application.add_handler(CommandHandler("get_fantasy", get_fantasy_handler))
        application.add_handler(CallbackQueryHandler(refresh_fantasy_stats, pattern='^refresh_fantasy_stats$'))
        application.add_handler(CallbackQueryHandler(show_all_users, pattern='^show_all_users$')) 
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enviar_respuesta_admin))
        
     

# Agregar al final del archivo, donde se registran los handlers
        application.add_handler(CommandHandler("promocionar", promocionar))
        application.add_handler(CallbackQueryHandler(seleccionar_red_social, pattern="^promo_(whatsapp|facebook)$"))
        application.add_handler(CallbackQueryHandler(cancelar_promocion, pattern="^cancelar_promo$"))
        application.add_handler(CallbackQueryHandler(confirmar_promocion, pattern="^confirmar_promo_"))
        application.add_handler(CallbackQueryHandler(juego_fantasy, pattern="juego_fantasy"))
        application.add_handler(CallbackQueryHandler(mostrar_ranking, pattern="ranking_fantasy"))
        application.add_handler(CallbackQueryHandler(mi_equipo_handler, pattern='^mi_equipo$'))
        application.add_handler(CallbackQueryHandler(show_market_main_menu, pattern='^mercado_menu$'))
    
    # Handlers para listar equipos y jugadores
        application.add_handler(CallbackQueryHandler(listar_equipos_mercado, pattern='^mercado_equipos$'))
        application.add_handler(CallbackQueryHandler(listar_jugadores_equipo, pattern='^mercado_equipo_'))
    
    # Handlers para comprar y vender
     
        application.add_handler(CallbackQueryHandler(confirmar_venta, pattern='^mercado_vender_'))
        application.add_handler(CallbackQueryHandler(confirmar_compra_handler, pattern='^confirmar0_compra_'))
    
    # Handlers para ofertas
        application.add_handler(CallbackQueryHandler(poner_en_venta_handler, pattern='^poner_en_venta_'))
        application.add_handler(CallbackQueryHandler(procesar_venta_manual, pattern='^venta_manual_'))
        application.add_handler(CallbackQueryHandler(confirmar_venta_jugador, pattern='^venta_precio_'))
        application.add_handler(CallbackQueryHandler(hacer_oferta_handler, pattern='^hacer_oferta_'))
        application.add_handler(CallbackQueryHandler(procesar_oferta, pattern='^oferta_'))
        # Añade estos handlers a tu aplicación
        application.add_handler(CallbackQueryHandler(manejar_respuesta_oferta, pattern='^aceptar_oferta_'))
        application.add_handler(CallbackQueryHandler(manejar_respuesta_oferta, pattern='^rechazar_oferta_'))
        
    
    # Handler para ver jugadores en venta
        application.add_handler(CallbackQueryHandler(listar_mis_ventas, pattern='^mercado_mis_ventas$'))
        application.add_handler(CallbackQueryHandler(ver_jugador, pattern='^ver_jugador_'))
        application.add_handler(CallbackQueryHandler(comprar_jugador, pattern='^comprar_'))
        
        application.add_handler(CallbackQueryHandler(cancelar_compra, pattern='^cancelar_compra$'))
        application.add_handler(CallbackQueryHandler(mercado_volver, pattern='^mercado_volver$'))
        application.add_handler(CallbackQueryHandler(mis_ofertas_handler, pattern='^mis_ofertas$'))
        application.add_handler(CallbackQueryHandler(iniciar_subasta_handler, pattern='^iniciar_subasta$'))
        application.add_handler(CallbackQueryHandler(configurar_subasta, pattern='^subasta_elegir_'))
        application.add_handler(CallbackQueryHandler(listar_subastas_activas, pattern='^listar_subastas$'))
        
        application.add_handler(CallbackQueryHandler(mis_pujas_handler, pattern='^mis_pujas$'))
        application.add_handler(CallbackQueryHandler(pujar_subasta, pattern='^pujar_subasta_'))
        application.add_handler(CallbackQueryHandler(mostrar_menu_subastas, pattern='^menu_subastas$'))
        application.add_handler(CallbackQueryHandler(mis_subastas_handler, pattern='^mis_subastas$'))
        application.add_handler(CallbackQueryHandler(gestionar_subasta, pattern='^gestionar_subasta_'))
        application.add_handler(CallbackQueryHandler(aceptar_puja_handler, pattern='^aceptar_puja_'))
        application.add_handler(CallbackQueryHandler(cancelar_subasta_handler, pattern='^cancelar_subasta_'))
        application.add_handler(CommandHandler("torneo", torneo_handler))
        
        application.add_handler(CallbackQueryHandler(mostrar_sistema_torneo, pattern='^mostrar_sistema_torneo$'))
        
        application.add_handler(CallbackQueryHandler(unirse_al_torneo, pattern='^torneo_unirse$'))
        application.add_handler(CallbackQueryHandler(mostrar_participantes, pattern='torneo_participantes'))
        application.add_handler(CallbackQueryHandler(mostrar_info_torneo_detallada, pattern='torneo_info'))
        application.add_handler(CallbackQueryHandler(cancelar_torneo_handler, pattern='cancelar_torneo'))
        application.add_handler(CallbackQueryHandler(confirmar_cancelar_torneo, pattern='confirmar_cancelar_torneo'))
        
        # Añadir estos handlers a tu aplicación
        application.add_handler(CallbackQueryHandler(mostrar_clasificacion, pattern='^progreso_torneo$'))
        application.add_handler(CallbackQueryHandler(mostrar_ultimos_resultados, pattern='^ultimos_resultados$'))
        
        application.add_handler(CallbackQueryHandler(mostrar_mis_partidos, pattern='^mis_partidos$'))
        application.add_handler(CallbackQueryHandler(mostrar_ayuda_torneo, pattern='^ayuda_torneo$'))
        
    # Handler para cambiar formación
        application.add_handler(CallbackQueryHandler(
        cambiar_formacion_handler,
        pattern='^cambiar_formacion$'
    ))
    
    # Handler para seleccionar formación
        application.add_handler(CallbackQueryHandler(
        seleccionar_formacion_handler,
        pattern='^seleccionar_formacion_'
    ))
    
    # Handler para seleccionar posición
        application.add_handler(CallbackQueryHandler(
        seleccionar_posicion_handler,
        pattern='^seleccionar_posicion_'
    ))
    
    # Handler para toggle jugador
        application.add_handler(CallbackQueryHandler(
        toggle_jugador_handler,
        pattern='^toggle_jugador_'
    ))
    
    # Handler para confirmar alineación
        application.add_handler(CallbackQueryHandler(
        confirmar_alineacion_handler,
        pattern='^confirmar_alineacion$'
    ))
    
    # Handler para reiniciar alineación
        application.add_handler(CallbackQueryHandler(
        reiniciar_alineacion_handler,
        pattern='^reiniciar_alineacion$'
    ))
    
    # Handler para volver a alineación
        application.add_handler(CallbackQueryHandler(
        volver_alineacion_handler,
        pattern='^volver_alineacion_'
    ))

    # Handler para mostrar menú alineación
        application.add_handler(CallbackQueryHandler(
        mostrar_menu_alineacion,
        pattern='^mostrar_alineacion$'
    ))
        application.add_handler(CallbackQueryHandler(estadisticas_equipo, pattern='^estadisticas_equipo$'))
        application.add_handler(CallbackQueryHandler(ver_jugador_stats, pattern='^ver2_jugador_stats_'))
        application.add_handler(CallbackQueryHandler(estadisticas_equipo, pattern='^estats_page_'))
        
        application.add_handler(CallbackQueryHandler(mostrar_rivales_retar, pattern='^mostrar_rivales$'))
        application.add_handler(CallbackQueryHandler(seleccionar_rival, pattern='^seleccionar_rival_'))
        application.add_handler(CallbackQueryHandler(procesar_aceptar_reto, pattern='^aceptar_reto_'))
        application.add_handler(CallbackQueryHandler(procesar_rechazar_reto, pattern='^rechazar_reto_'))
        
        application.add_handler(CallbackQueryHandler(cerrar_tutorial, pattern='^cerrar_tutorial$'))
        application.add_handler(CallbackQueryHandler(mostrar_tutorial_torneos, pattern='^tutorial_torneos_'))
        application.add_handler(CallbackQueryHandler(cerrar_tutorial_torneos, pattern='^cerrar_tutorial_torneos$'))   
        
        application.add_handler(CallbackQueryHandler(confirmar_eliminar_usuario, pattern='^confirmar_eliminar_'))
        application.add_handler(CallbackQueryHandler(cancelar_eliminar, pattern='^cancelar_eliminar$'))    
        
        application.add_handler(CallbackQueryHandler(vender_jugador_handler, pattern='^vender_jugador_handler$')) 
        
        application.add_handler(CallbackQueryHandler(confirmar_venta_jugador, pattern='^confirmar_venta_'))   
        application.add_handler(CallbackQueryHandler(explicar_sistema_puntos, pattern='^explicar_puntos$'))
        application.add_handler(CallbackQueryHandler(handle_eliminar_apuesta, pattern="^eliminar0_apuesta_"))
        application.add_handler(CallbackQueryHandler(handle_eliminar_todas, pattern="^eliminar0_todas_"))

      
        

        print("Robot iniciado...")        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error al ejecutar el bot: {e}")
        # Aquí puedes agregar más manejo de excepciones si es necesario

if __name__ == "__main__":
    run_bot()