import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import random
import asyncio
import time as tm  # Alias para evitar conflictos con datetime.time
from datetime import datetime
import pytz 
import json
import os
from necesario import ejecutar_consulta_segura, obtener_registro, actualizar_registro, insertar_registro
GROUP_REGISTRO = -1002261941863
GROUP_CHAT_ID = -1001929466623
REGISTRO_MINIJUEGOS = -1002566004558
# Función para convertir segundos a horas, minutos y segundos
def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

DB_FILE = "user_data.json"
lock = asyncio.Lock()
lock_data = asyncio.Lock()


# Crear un lock asincrónico para proteger el acceso a los datos
lock = asyncio.Lock()





# Diccionario de nombres de barcos con niveles representados por emojis (niveles de 0 a 10)
nombres_barcos = [
    "▫️◻️◻️◻️◻️ Balsa",             # Nivel 0
    "🔲◻️◻️◻️◻️ Goleta",            # Nivel 1
    "🔲🔲◻️◻️◻️ Barco de guerra",    # Nivel 2
    "🔲🔲🔲◻️◻️ Navío",              # Nivel 3
    "🔲🔲🔲🔲◻️ Galeón",             # Nivel 4
    "🔲🔲🔲🔲🔲 Buque de guerra",     # Nivel 5
    "⬛ 🔲🔲🔲🔲 Acorazado",           # Nivel 6
    "⬛ ⬛ 🔲🔲🔲 Crucero",             # Nivel 7
    "⬛ ⬛ ⬛ 🔲🔲 Portaaviones",         # Nivel 8
    "⬛ ⬛ ⬛ ⬛ ⬛ Barco insignia",       # Nivel 9
    "⬛ ⬛ ⬛ ⬛ ⬛ Barco insignia"        # Nivel 10
]

# Diccionario de nombres de cañones con niveles representados por emojis (niveles de 0 a 10)
nombres_cañones = [
    "▫️◻️◻️◻️◻️ Cañón de mano",     # Nivel 0
    "🔲◻️◻️◻️◻️ Cañón ligero",     # Nivel 1
    "🔲🔲◻️◻️◻️ Cañón de asedio",   # Nivel 2
    "🔲🔲🔲◻️◻️ Cañón pesado",      # Nivel 3
    "🔲🔲🔲🔲◻️ Cañón de largo alcance",  # Nivel 4
    "🔲🔲🔲🔲🔲 Cañón reforzado",    # Nivel 5
    "⬛🔲🔲🔲🔲 Cañón de hierro",    # Nivel 6
    "⬛ ⬛🔲🔲🔲 Cañón de hierro fundido",  # Nivel 7
    "⬛ ⬛ ⬛ 🔲🔲 Cañón de guerra",    # Nivel 8
    "⬛ ⬛ ⬛ ⬛ ⬛ Cañón de precisión",  # Nivel 9
    "⬛ ⬛ ⬛ ⬛ ⬛ Cañón de precisión"   # Nivel 10
]

# Diccionario de nombres de velas con niveles representados por emojis (niveles de 0 a 10)
nombres_velas = [
    "▫️◻️◻️◻️◻️ Deterioradas",    # Nivel 0
    "🔲◻️◻️◻️◻️ Gastadas",       # Nivel 1
    "🔲🔲◻️◻️◻️ Comunes",        # Nivel 2
    "🔲🔲🔲◻️◻️ Desgastadas",     # Nivel 3
    "🔲🔲🔲🔲◻️ Bajas condiciones",# Nivel 4
    "🔲🔲🔲🔲🔲 Medias",          # Nivel 5
    "⬛🔲🔲🔲🔲 Resitentes",      # Nivel 6
    "⬛ ⬛🔲🔲🔲 Suficientemente buenas", # Nivel 7
    "⬛ ⬛ ⬛🔲🔲 De buena calidad", # Nivel 8
    "⬛ ⬛ ⬛ ⬛ ⬛ De lujo",          # Nivel 9
    "⬛ ⬛ ⬛ ⬛ ⬛ De lujo"           # Nivel 10
]

async def juego_pirata(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_name = query.from_user.first_name

    try:
        # Verificar si el usuario existe en la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Nombre")
        if not usuario_data:
            await query.answer("❌ No estás registrado. Usa /start para comenzar.")
            return

        # Verificar o inicializar datos del juego pirata en la base de datos
        juego_data = obtener_registro("juego_pirata", user_id, 
                                    "nombre, barriles, piratas, tiempo_ultimo_reclamo, tiempo_para_ganar, "
                                    "ganancias_totales, hp_barco, prestigio, escudo_hasta, victorias, derrotas")
        
        if not juego_data:
            # Inicializar nuevo usuario en el juego pirata - USAR INSERTAR, NO ACTUALIZAR
            exito = insertar_registro(
                "juego_pirata",
                {
                    "id": user_id,
                    "nombre": user_name,
                    "barriles": 1500,
                    "piratas": 6,
                    "tiempo_ultimo_reclamo": 0,
                    "tiempo_para_ganar": 3600,
                    "ganancias_totales": 0,
                    "hp_barco": 100,
                    "prestigio": 0,
                    "escudo_hasta": 0,
                    "victorias": 0,
                    "derrotas": 0
                }
            )
            
            if not exito:
                await query.answer("❌ Error al inicializar el juego pirata")
                return

            # Inicializar mejoras por defecto - USAR INSERTAR PARA NUEVOS REGISTROS
            tipos_mejoras = ["barco", "cañones", "velas"]
            for tipo in tipos_mejoras:
                # Primero verificar si ya existe la mejora
                mejora_existente = obtener_registro("mejoras", (user_id, tipo))
                
                if not mejora_existente:
                    exito_mejora = insertar_registro(
                        "mejoras",
                        {
                            "id": user_id,
                            "tipo": tipo,
                            "nivel": 1
                        }
                    )
                    if not exito_mejora:
                        print(f"Error al insertar mejora {tipo} para usuario {user_id}")

        # Obtener datos actualizados para mostrar en el menú
        juego_data_actual = obtener_registro("juego_pirata", user_id, 
                                           "barriles, piratas, hp_barco, prestigio")
        
        if juego_data_actual:
            barriles, piratas, hp_barco, prestigio = juego_data_actual
        else:
            barriles, piratas, hp_barco, prestigio = 1500, 6, 100, 0

        # Crear teclado organizado con información del estado
        keyboard = [
            # Primera fila: Balance y mejoras principales
            [
                InlineKeyboardButton(f"📊 Barriles: {barriles}", callback_data='ver_balance'),
                InlineKeyboardButton(f"⚔️ Piratas: {piratas}", callback_data='menu_combate')
            ],
            # Segunda fila: Mejoras de barco
            [
                InlineKeyboardButton("🆙 Barco🚢", callback_data='mejorar_barco'),
                InlineKeyboardButton("🆙 Velas⛵", callback_data='mejorar_velas'),
                InlineKeyboardButton("🆙 Cañones🔫", callback_data='mejorar_cañones')
            ],
            # Tercera fila: Gestión de piratas
            [
                InlineKeyboardButton("🏴‍☠ Contratar Piratas", callback_data='comprar_piratas'),
                InlineKeyboardButton("💰 Mercado", callback_data='mercado_pirata')
            ],
            # Cuarta fila: Acciones principales
            [
                InlineKeyboardButton("🛒 Comprar Barriles", callback_data='comprar_barriles'),
                InlineKeyboardButton("🤑 Vender Barriles", callback_data='vender_barriles')
            ],
            # Quinta fila: Reclamar ganancias y HP
            [
                InlineKeyboardButton("🎁 Reclamar", callback_data='reclamar_ganancias'),
                InlineKeyboardButton(f"❤️ HP: {hp_barco}", callback_data='ver_hp')
            ],
            # Última fila: Menú principal
            [InlineKeyboardButton("🏠 Menú Principal", callback_data='menu_principal')]
        ]

        # Mensaje de bienvenida mejorado con información del jugador
        mensaje = (
            f"<blockquote>⚓ ¡Bienvenido de nuevo, Capitán {user_name}! ⚓</blockquote>\n\n"
            f"🏴‍☠️ <b>Tu flota pirata:</b>\n"
            f"├ 🛢️ Barriles: <b>{barriles}</b>\n"
            f"├ 👥 Piratas: <b>{piratas}</b>\n"
            f"├ ❤️ HP Barco: <b>{hp_barco}/100</b>\n"
            f"└ ⭐ Prestigio: <b>{prestigio}</b>\n\n"
            f"💡 <b>Consejo del día:</b> Mejora tu barco para aumentar tu producción.\n\n"
            f"🔻 <i>Selecciona una opción para continuar:</i>"
        )

        await query.answer()
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"Error en juego_pirata: {e}")
        await query.answer("❌ Error al cargar el menú pirata")
        await query.edit_message_text(
            "⚡ <b>¡Error al cargar el menú pirata!</b>\n\n"
            "Por favor, intenta nuevamente más tarde.",
            parse_mode="HTML"
        )

async def ver_balance(update, context: CallbackContext):
    try:
        query = update.callback_query
        user_id = str(query.from_user.id)

        # Obtener datos del juego pirata desde la base de datos
        juego_data = obtener_registro("juego_pirata", user_id, 
                                    "barriles, piratas, ganancias_totales, hp_barco, prestigio, "
                                    "escudo_hasta, victorias, derrotas, tiempo_ultimo_reclamo")
        
        if not juego_data:
            await query.answer("❌ No tienes datos en el juego pirata. Usa el juego primero.")
            return

        # Obtener niveles de mejoras desde la base de datos - USANDO TU FUNCIÓN obtener_registro
        niveles_mejoras = {}
        tipos_mejoras = ["barco", "cañones", "velas"]
        
        for tipo in tipos_mejoras:
            # Usar tu función obtener_registro con clave compuesta (user_id, tipo)
            mejora_data = obtener_registro("mejoras", (user_id, tipo), "nivel")
            niveles_mejoras[tipo] = mejora_data[0] if mejora_data else 1

        # Obtener evento actual si existe
        evento_data = obtener_registro("eventos", user_id, "nombre, efecto, expira, mensaje")
        
        # Acceder a los valores del balance
        barriles = juego_data[0]
        piratas = juego_data[1]
        ganancias_totales = juego_data[2]
        barco = niveles_mejoras.get("barco", 1)
        cañones = niveles_mejoras.get("cañones", 1)
        velas = niveles_mejoras.get("velas", 1)

        # Manejar niveles fuera del rango (con verificación de que las listas existen)
        nombre_barco = f"Barco Nvl {barco}"
        nombre_cañones = f"Cañones Nvl {cañones}"
        nombre_velas = f"Velas Nvl {velas}"
        
        if nombres_barcos and len(nombres_barcos) > 0:
            nombre_barco = nombres_barcos[min(barco - 1, len(nombres_barcos) - 1)] + f" (lvl {barco})"
        if nombres_cañones and len(nombres_cañones) > 0:
            nombre_cañones = nombres_cañones[min(cañones - 1, len(nombres_cañones) - 1)] + f" (lvl {cañones})"
        if nombres_velas and len(nombres_velas) > 0:
            nombre_velas = nombres_velas[min(velas - 1, len(nombres_velas) - 1)] + f" (lvl {velas})"

        # Calcular ganancias reales considerando eventos y mantenimiento
        ganancias_reales = ganancias_totales
        evento_info = ""
        
        # Verificar evento activo si existe - USANDO tm.time() (tu alias)
        if evento_data and len(evento_data) >= 4:
            nombre_evento, efecto, expira, mensaje = evento_data
            if expira > tm.time():  # Usando tu alias tm
                tiempo_restante = expira - tm.time()
                # Aplicar efecto del evento
                ganancias_reales = aplicar_efecto_evento(ganancias_reales, {
                    "nombre": nombre_evento,
                    "efecto": efecto,
                    "expira": expira,
                    "mensaje": mensaje
                }, juego_data)
                
                evento_info = f"\n\n🎭 <b>Evento activo:</b> {nombre_evento} ({obtener_descripcion_efecto(efecto)})\n⏳ Termina en: {format_time(tiempo_restante)}"

        message = (  
            f"<blockquote>📊 Mi barco 📊</blockquote>\n\n"  
            f"🛢️ <b>Barriles de Ron</b>: <code>{barriles}</code>\n\n"  
            f"🏴‍☠️ <b>Piratas:</b> <code>{piratas}</code>\n\n"  
            f"🚢 <b>Barco:</b> {nombre_barco}\n\n"  
            f"🔫 <b>Cañones:</b> {nombre_cañones}\n\n"  
            f"⛵ <b>Velas:</b> {nombre_velas}\n\n"  
            f"💰 <b>Ganancia base por hora</b>: <code>{ganancias_totales}</code> barriles\n"  
            f"💰 <b>Ganancia actual por hora</b>: <code>{int(ganancias_reales)}</code> barriles\n\n"  
            f"❤️ <b>HP del Barco</b>: <code>{juego_data[3]}/100</code>\n"
            f"⭐ <b>Prestigio</b>: <code>{juego_data[4]}</code>\n"
            f"🛡️ <b>Escudo activo hasta</b>: {format_time(juego_data[5]) if juego_data[5] > tm.time() else 'No activo'}\n"
            f"🏆 <b>Victorias PvP</b>: <code>{juego_data[6]}</code>\n"
            f"💔 <b>Derrotas PvP</b>: <code>{juego_data[7]}</code>\n"
            f"{evento_info}"                   
        )  

        # Solo botones de Volver y Menu Principal  
        keyboard = [  
            [InlineKeyboardButton("🔙 Volver", callback_data='juego_pirata')],  
            [InlineKeyboardButton("🔚 Menu Principal", callback_data='menu_principal')]  
        ]  

        reply_markup = InlineKeyboardMarkup(keyboard)  

        await query.answer()  
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")  

    except Exception as e:  
        print(f"Error en ver_balance: {e}")  
        await query.answer("Ha ocurrido un error al obtener tu balance. Por favor, intenta de nuevo.")
        
        
# Menú de mercado adicional
async def mercado_pirata(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🛒 Comprar Barriles", callback_data='comprar_barriles'),
            InlineKeyboardButton("🤑 Vender Barriles", callback_data='vender_barriles')
        ],
        [
            InlineKeyboardButton("🛡️ Escudo Básico", callback_data='escudo_basico'),
            InlineKeyboardButton("🛡️ Escudo Premium", callback_data='escudo_premium')
        ],
        [InlineKeyboardButton("🔙 Volver", callback_data='juego_pirata')]
    ]
    
    await query.edit_message_text(
        "<pre>🏪 MERCADO PIRATA</pre>\n\n"
        "💰 <b>Compra y vende recursos:</b>\n\n"
        "▫️ <b>Barriles:</b> Compra/Vende con CUP\n"
        "▫️ <b>Escudos:</b> Protección contra ataques\n\n"
        "<i>Selecciona una opción para continuar:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Comprar piratas
async def comprar_piratas(update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    pirata_costo = 10000

    # Obtener datos del usuario desde la base de datos
    juego_data = obtener_registro("juego_pirata", user_id, "barriles, piratas")
    
    if not juego_data:
        await query.answer("❌ No estás registrado en el juego pirata. Usa /start para comenzar.")
        return

    barriles, piratas_actuales = juego_data

    if barriles >= pirata_costo:
        # Crear botones de confirmación y cancelación
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data='confirmar_compra_piratas')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='juego_pirata')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Responder al usuario con el mensaje de compra
        await query.answer()
        await query.edit_message_text(
            f"<blockquote> 🏴‍☠️¡Estás a punto de comprar 1 pirata! </blockquote>\n\n"
            f"💰 <b>Costo:</b> <code>{pirata_costo}</code> barriles 🛢️\n\n"
            f"💡 <b>Consejo</b>:\n ¡Puedes invitar amigos! Cada amigo invitado cuenta como un pirata y puedes obtenerlos de forma gratuita.\n\n"
            f"🔗 <i>Usa tu link de referido para ganar más piratas y aumentar tus ganancias.</i>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        # Si el usuario no tiene suficientes barriles
        await query.answer()
        await query.edit_message_text(
            "<blockquote>⚔️¡Ups!</blockquote>\n <i>No tienes suficientes barriles para comprar un pirata.</i> 😕\n\n"
            "<b>Costo:</b> <code>10 000 barriles ≈ 142</code> CUP\n\n"
            "Puedes reclutar piratas invitando amigos, cada referido cuenta como un pirata en tu tripulación (gratis). \n<i>¡No te rindas, pirata!</i> 🏴‍☠️💪\n\n",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver al Juego Pirata", callback_data='juego_pirata')],
                [InlineKeyboardButton("🔄 Menu Principal", callback_data='menu_principal')]
            ]),
            parse_mode='HTML'
        )

async def confirmar_compra_piratas(update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    pirata_costo = 10000

    try:
        # Obtener datos actuales del usuario
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, piratas")
        
        if not juego_data:
            await query.answer("❌ No estás registrado en el juego pirata. Usa /start para comenzar.")
            return

        barriles_actuales, piratas_actuales = juego_data

        # Verificar si tiene suficientes barriles
        if barriles_actuales < pirata_costo:
            await query.answer()
            await query.edit_message_text(
                "<blockquote>❌ Compra fallida</blockquote>\n"
                "<b>No tienes suficientes barriles para comprar un pirata.</b> 😕\n\n"
                "💡 Para conseguir más barriles puedes:\n"
                "- Reclamar ganancias 🎁\n"
                "- Mejorar tus elementos 🛠️\n"
                "- Comprar barriles 🛒\n\n"
                "<i>¡Sigue adelante, pirata!</i> 🏴‍☠️",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data='juego_pirata')],
                    [InlineKeyboardButton("🛒 Comprar Barriles", callback_data='comprar_barriles')],
                    [InlineKeyboardButton("🔄 Menú Principal", callback_data='menu_principal')]
                ])
            )
            return

        # Actualizar datos en la base de datos
        nuevos_barriles = barriles_actuales - pirata_costo
        nuevos_piratas = piratas_actuales + 1
        
        exito = actualizar_registro(
            "juego_pirata",
            user_id,
            {
                "barriles": nuevos_barriles,
                "piratas": nuevos_piratas
            }
        )

        if not exito:
            raise Exception("Error al actualizar la base de datos")

        # Mensaje de confirmación
        await query.answer("✅ ¡Pirata contratado con éxito!")
        await query.edit_message_text(
            f"<blockquote>✅ ¡Compra exitosa! 🏴‍☠️</blockquote>\n\n"
            f"<i>Ahora tienes {nuevos_piratas} piratas en tu tripulación.</i>\n\n"
            f"🛢️ <b>Barriles gastados:</b> {pirata_costo}\n"
            f"💰 <b>Barriles restantes:</b> {nuevos_barriles}\n\n"
            "<i>¡Que los vientos te acompañen, capitán!</i> 🌊⛵",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data='juego_pirata')],
                [InlineKeyboardButton("⏫ Mejorar Barco", callback_data='mejorar_barco')],
                [InlineKeyboardButton("🔄 Menú Principal", callback_data='menu_principal')]
            ])
        )

    except Exception as e:
        print(f"Error en confirmar_compra_piratas: {e}")
        await query.answer("❌ Ocurrió un error al procesar la compra. Intenta nuevamente.")
        await query.edit_message_text(
            "❌ <b>Error en la transacción</b>\n\n"
            "No se pudo completar la compra del pirata. Por favor, inténtalo de nuevo más tarde.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data='juego_pirata')]
            ])
        )





# Configuración mejorada con saltos de nivel y dependencias escalables
MEJORAS_CONFIG = {
    "velas": {
        "costo_base": 500,
        "multiplicador_nivel": 1.4,
        "saltos_nivel": {4: 5.0, 7: 3.0},
        "ganancia_base": 10,
        "multiplicador_ganancia": 1.3,
        "piratas_requeridos_base": 3,
        "max_nivel": 15,
        "requisitos": {},
        "factor_descuento": 0.95
    },
    "cañones": {
        "costo_base": 750,
        "multiplicador_nivel": 1.5,
        "saltos_nivel": {4: 6.0, 7: 3.5},
        "ganancia_base": 15,
        "multiplicador_ganancia": 1.4,
        "piratas_requeridos_base": 4,
        "max_nivel": 15,
        "requisitos": {"velas": 1},
        "factor_descuento": 0.93
    },
    "barco": {
        "costo_base": 1000,
        "multiplicador_nivel": 1.6,
        "saltos_nivel": {4: 7.0, 7: 4.0},
        "ganancia_base": 20,
        "multiplicador_ganancia": 1.5,
        "piratas_requeridos_base": 5,
        "max_nivel": 15,
        "requisitos": {"velas": 1, "cañones": 1},
        "factor_descuento": 0.90
    }
}

def calcular_costo_mejora(tipo_mejora, nivel_actual):
    """Calcula el costo considerando los saltos de nivel y crecimiento exponencial"""
    config = MEJORAS_CONFIG[tipo_mejora]
    costo = config["costo_base"]
    
    for nivel in range(1, nivel_actual + 1):
        multiplicador = config["multiplicador_nivel"]
        
        # Aumentar dificultad después de ciertos niveles
        if nivel > 5:
            multiplicador *= 1.2
        if nivel > 10:
            multiplicador *= 1.5
            
        # Aplicar multiplicador extra si estamos en un nivel de salto
        if nivel in config.get("saltos_nivel", {}):
            multiplicador *= config["saltos_nivel"][nivel]
            
        costo *= multiplicador
    
    return int(costo)

def calcular_ganancia_mejora(tipo_mejora, nivel):
    """Calcula la ganancia por hora con reducción progresiva en niveles altos"""
    config = MEJORAS_CONFIG[tipo_mejora]
    ganancia = config["ganancia_base"] * (config["multiplicador_ganancia"] ** (nivel - 1))
    
    # Aplicar reducción progresiva después de nivel 10
    if nivel > 10:
        reduccion = (nivel - 10) * (1 - config["factor_descuento"])
        ganancia *= (1 - reduccion)
    
    return max(1, int(ganancia))  # Nunca menos de 1
    
    

    
    
def calcular_piratas_requeridos(tipo_mejora, nivel_actual):
    """Calcula piratas requeridos con secuencia predefinida"""
    secuencia = [3, 5, 8, 12, 20, 25, 40, 50, 80, 100]  # Puedes extender esta lista
    
    if nivel_actual < len(secuencia):
        return secuencia[nivel_actual]
    else:
        # Fórmula de respaldo si se superan los niveles predefinidos
        return secuencia[-1] + (nivel_actual - len(secuencia) + 1) * 10
async def mejorar_elemento(update: Update, context: CallbackContext, tipo_mejora: str):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = str(query.from_user.id)
        
        # Obtener datos del juego pirata
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, piratas, ganancias_totales")
        if not juego_data:
            await query.edit_message_text("❌ No estás registrado en el juego pirata.")
            return
            
        barriles, piratas, ganancias_totales = juego_data
        
        # Obtener niveles de mejoras actuales
        niveles_mejoras = {}
        for mejora_tipo in ["barco", "cañones", "velas"]:
            mejora_data = obtener_registro("mejoras", (user_id, mejora_tipo), "nivel")
            niveles_mejoras[mejora_tipo] = mejora_data[0] if mejora_data else 1
        
        nivel_actual = niveles_mejoras.get(tipo_mejora, 1)
        nivel_siguiente = nivel_actual + 1
        
        # Verificar nivel máximo
        if nivel_actual >= MEJORAS_CONFIG[tipo_mejora]["max_nivel"]:
            await mostrar_maximo_nivel(update, tipo_mejora, nivel_actual)
            return
        
        # Verificar requisitos escalables
        requisitos = MEJORAS_CONFIG[tipo_mejora]["requisitos"]
        for req_tipo, req_mult in requisitos.items():
            req_nivel = nivel_siguiente * req_mult
            if niveles_mejoras.get(req_tipo, 1) < req_nivel:
                await mostrar_falta_requisitos(
                    update, tipo_mejora, nivel_siguiente, 
                    req_tipo, req_nivel, 
                    niveles_mejoras.get(req_tipo, 1)
                )
                return
        
        # Calcular valores
        piratas_requeridos = calcular_piratas_requeridos(tipo_mejora, nivel_actual)
        costo = calcular_costo_mejora(tipo_mejora, nivel_actual)
        ganancia_actual = calcular_ganancia_mejora(tipo_mejora, nivel_actual)
        ganancia_siguiente = calcular_ganancia_mejora(tipo_mejora, nivel_siguiente)
        ganancia_extra = ganancia_siguiente - ganancia_actual
        
        # Verificar si es un nivel con salto especial
        salto_info = ""
        if nivel_actual in MEJORAS_CONFIG[tipo_mejora].get("saltos_nivel", {}):
            multiplicador = MEJORAS_CONFIG[tipo_mejora]["saltos_nivel"][nivel_actual]
            salto_info = f"\n⚠️ <b>¡Nivel especial!</b> Este salto cuesta {multiplicador}x más de lo normal así como también las ganancias generadas\n"
        
        # Verificar recursos
        if piratas < piratas_requeridos:
            await mostrar_falta_piratas(update, tipo_mejora, piratas_requeridos, piratas)
            return
            
        if barriles < costo:
            await mostrar_falta_barriles(update, tipo_mejora, costo, barriles)
            return
        
        # Guardar datos temporales para la confirmación
        context.user_data['mejora_temp'] = {
            'tipo': tipo_mejora,
            'costo': costo,
            'nivel_actual': nivel_actual,
            'nivel_siguiente': nivel_siguiente
        }
        
        # Mostrar confirmación con todos los detalles
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar Mejora", callback_data=f"confirmar_mejora_{tipo_mejora}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="juego_pirata")]
        ]
        
        mensaje = (
            f"⚓ <b>Mejorar {tipo_mejora.capitalize()} a nivel {nivel_siguiente}</b>\n\n"
            f"🔢 Nivel actual: {nivel_actual} (Ganancia: {ganancia_actual}/hora)\n"
            f"🆕 Nivel siguiente: {nivel_siguiente} (Ganancia: {ganancia_siguiente}/hora)\n"
            f"📈 Ganancia adicional: +{ganancia_extra} barriles/hora\n\n"
            f"🏴‍☠️ Piratas requeridos: {piratas_requeridos}/{piratas} ✅\n"
            f"🛢️ Costo: {costo} barriles\n"
            f"{salto_info}\n"
            f"🔒 Requisitos:\n"
        )
        
        # Agregar requisitos al mensaje
        if requisitos:
            for req_tipo, req_mult in requisitos.items():
                req_nivel = nivel_siguiente * req_mult
                mensaje += f"- {req_tipo.capitalize()} nivel {req_nivel} (tienes {niveles_mejoras.get(req_tipo, 1)})\n"
        else:
            mensaje += "- Ninguno\n"
        
        mensaje += "\n💡 <i>Al mejorar, aumentarás tus ganancias por hora permanentemente!</i>"
        
        await query.edit_message_text(
            mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        print(f"Error en mejorar_{tipo_mejora}: {str(e)}")
        await mostrar_error(update, "mejorar")

async def confirmar_mejora_elemento(update: Update, context: CallbackContext, tipo_mejora: str):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = str(query.from_user.id)
        
        # Obtener datos temporales
        mejora_temp = context.user_data.get('mejora_temp', {})
        if mejora_temp.get('tipo') != tipo_mejora:
            await query.edit_message_text("❌ Datos de mejora no válidos o expirados.")
            return
            
        costo = mejora_temp['costo']
        nivel_actual = mejora_temp['nivel_actual']
        nivel_siguiente = mejora_temp['nivel_siguiente']
        
        # Obtener datos actualizados
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, piratas, ganancias_totales")
        if not juego_data:
            await query.edit_message_text("❌ No estás registrado en el juego pirata.")
            return
            
        barriles, piratas, ganancias_totales = juego_data
        
        # Obtener niveles de mejoras actuales
        niveles_mejoras = {}
        for mejora_tipo in ["barco", "cañones", "velas"]:
            mejora_data = obtener_registro("mejoras", (user_id, mejora_tipo), "nivel")
            niveles_mejoras[mejora_tipo] = mejora_data[0] if mejora_data else 1
        
        # Recalcular todo para verificar que no haya cambios
        piratas_requeridos = calcular_piratas_requeridos(tipo_mejora, nivel_actual)
        
        # Verificar requisitos escalables nuevamente
        requisitos = MEJORAS_CONFIG[tipo_mejora]["requisitos"]
        for req_tipo, req_mult in requisitos.items():
            req_nivel = nivel_siguiente * req_mult
            if niveles_mejoras.get(req_tipo, 1) < req_nivel:
                await query.edit_message_text(
                    f"❌ ¡Ya no cumples los requisitos!\n"
                    f"Necesitas {req_tipo} nivel {req_nivel} para mejorar {tipo_mejora} a nivel {nivel_siguiente}.",
                    parse_mode="HTML"
                )
                return
        
        if piratas < piratas_requeridos:
            await query.edit_message_text(
                "⚠️ ¡Alguien ha despedido piratas! Ya no tienes suficientes para mejorar.",
                parse_mode="HTML"
            )
            return
            
        if barriles < costo:
            await query.edit_message_text(
                "⚠️ ¡Has gastado barriles! Ya no tienes suficientes para mejorar.",
                parse_mode="HTML"
            )
            return
        
        # Calcular nueva ganancia total
        nueva_ganancia_total = 0
        for mejora_tipo in ["barco", "cañones", "velas"]:
            nivel = niveles_mejoras[mejora_tipo]
            if mejora_tipo == tipo_mejora:
                nivel = nivel_siguiente  # Usar el nuevo nivel para esta mejora
            nueva_ganancia_total += calcular_ganancia_mejora(mejora_tipo, nivel)
        
        # Actualizar base de datos
        exito_juego = actualizar_registro(
            "juego_pirata",
            user_id,
            {
                "barriles": barriles - costo,
                "ganancias_totales": nueva_ganancia_total
            }
        )
        
        exito_mejora = actualizar_registro(
            "mejoras",
            (user_id, tipo_mejora),
            {"nivel": nivel_siguiente}
        )
        
        if not exito_juego or not exito_mejora:
            await query.edit_message_text("❌ Error al procesar la mejora.")
            return
        
        # Mensaje de éxito con detalles extendidos
        ganancia_extra = nueva_ganancia_total - ganancias_totales
        
        mensaje_exito = (
            f" <pre>✅ ¡Mejora exitosa!</pre>\n\n"
            f"⚓ Tus {tipo_mejora} ahora son nivel {nivel_siguiente}\n"
            f"📈 Ganancia adicional: +{ganancia_extra} barriles/hora\n"
            f"💰 Ganancia total por hora: {nueva_ganancia_total} barriles\n\n"
            f"🛢️ Barriles restantes: {barriles - costo}\n\n"
        )
        
        # Información sobre el próximo nivel si no es máximo
        if nivel_siguiente < MEJORAS_CONFIG[tipo_mejora]["max_nivel"]:
            prox_costo = calcular_costo_mejora(tipo_mejora, nivel_siguiente)
            prox_ganancia = calcular_ganancia_mejora(tipo_mejora, nivel_siguiente + 1) - calcular_ganancia_mejora(tipo_mejora, nivel_siguiente)
            
            mensaje_exito += (
                f"🔮 <b>Próximo nivel ({nivel_siguiente + 1}):</b>\n"
                f"- Costo estimado: {prox_costo} barriles\n"
                f"- Ganancia estimada: +{prox_ganancia}/hora\n"
            )
        
        await query.edit_message_text(
            mensaje_exito,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏫ Mejorar Otra Cosa", callback_data="juego_pirata")],
                [InlineKeyboardButton("📊 Ver Balance", callback_data="ver_balance")]
            ])
        )
        
        # Limpiar datos temporales
        context.user_data.pop('mejora_temp', None)
            
    except Exception as e:
        print(f"Error en confirmar_mejora_{tipo_mejora}: {str(e)}")
        await mostrar_error(update, "confirmar mejora")
        
async def mostrar_maximo_nivel(update, tipo_mejora, nivel_actual):
    query = update.callback_query
    await query.edit_message_text(
        f"🏆 <b>¡Felicidades!</b>\n\n"
        f"Tus {tipo_mejora} ya están al máximo nivel ({nivel_actual}).\n"
        f"¡No hay más mejoras disponibles para este elemento!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
        ])
    )

async def mostrar_falta_requisitos(update, tipo_mejora, nivel_siguiente, req_tipo, req_nivel, nivel_actual):
    query = update.callback_query
    await query.edit_message_text(
        f"⚓ <b>No puedes mejorar {tipo_mejora} a nivel {nivel_siguiente}</b>\n\n"
        f"Necesitas tener {req_tipo} en nivel <b>{req_nivel}</b>.\n"
        f"Actualmente tienes {req_tipo} nivel {nivel_actual}.\n\n"
        f"💡 <i>Recuerda que para mejorar {tipo_mejora}, primero debes mejorar {req_tipo}.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⏫ Mejorar {req_tipo}", callback_data=f"mejorar_{req_tipo}")],
            [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
        ])
    )

async def mostrar_falta_piratas(update, tipo_mejora, requeridos, actuales):
    query = update.callback_query
    await query.edit_message_text(
        f"🏴‍☠️ <b>¡Necesitas más piratas!</b>\n\n"
        f"Para mejorar {tipo_mejora} necesitas:\n"
        f"🔢 <b>{requeridos} piratas</b> (tienes {actuales})\n\n"
        "¡Contrata más piratas para poder mejorar tus elementos!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏴‍☠ Contratar Piratas", callback_data="comprar_piratas")],
            [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
        ])
    )

async def mostrar_falta_barriles(update, tipo_mejora, costo, actuales):
    query = update.callback_query
    await query.edit_message_text(
        f"🛢️ <b>¡Necesitas más barriles!</b>\n\n"
        f"Para mejorar {tipo_mejora} necesitas:\n"
        f"💰 <b>{costo} barriles</b> (tienes {actuales})\n\n"
        "¡Consigue más barriles para poder mejorar tus elementos!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Reclamar Ganancias", callback_data="reclamar_ganancias")],
            [InlineKeyboardButton("🛒 Comprar Barriles", callback_data="comprar_barriles")],
            [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
        ])
    )

async def mostrar_error(update, accion):
    query = update.callback_query
    await query.edit_message_text(
        f"❌ <b>Ocurrió un error al {accion}</b>\n\n"
        "Por favor, intenta nuevamente. Si el problema persiste, contacta con soporte.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
        ])
    )        
        
# Función para formatear el tiempo de espera
def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


async def vender_barriles(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    try:
        user_id = str(query.from_user.id)
        
        # Obtener datos del juego pirata
        juego_data = obtener_registro("juego_pirata", user_id, "barriles")
        if not juego_data:
            await query.edit_message_text(
                "❌ <b>No estás registrado en el juego pirata</b>\n\n"
                "Usa /start para comenzar tu aventura pirata.",
                parse_mode="HTML"
            )
            return

        barriles = juego_data[0]
        
        # Obtener niveles de mejoras
        niveles_mejoras = {}
        for tipo_mejora in ["barco", "cañones", "velas"]:
            mejora_data = obtener_registro("mejoras", (user_id, tipo_mejora), "nivel")
            niveles_mejoras[tipo_mejora] = mejora_data[0] if mejora_data else 0

        # Verificar requisitos de nivel 5 en todas las mejoras
        if (niveles_mejoras.get("barco", 0) < 5 or
            niveles_mejoras.get("cañones", 0) < 5 or
            niveles_mejoras.get("velas", 0) < 5):
            
            await query.edit_message_text(
                "<b>🚢 Requisitos para vender barriles:</b>\n\n"
                "⚓ Necesitas tener todos tus elementos en <b>nivel 5</b> o superior:\n\n"
                f"▪️ Barco: Nivel {niveles_mejoras.get('barco', 0)}/5\n"
                f"▪️ Cañones: Nivel {niveles_mejoras.get('cañones', 0)}/5\n"
                f"▪️ Velas: Nivel {niveles_mejoras.get('velas', 0)}/5\n\n"
                "<i>¡Sigue mejorando para desbloquear esta función!</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏫ Mejorar Barco", callback_data="mejorar_barco")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
                ])
            )
            return

        # Verificar barriles mínimos
        if barriles < 1000:
            await query.edit_message_text(
                "<b>🛢️ No tienes suficientes barriles</b>\n\n"
                f"Actualmente tienes: <b>{barriles} barriles</b>\n"
                "Se requieren al menos <b>1,000 barriles</b> para realizar una venta.\n\n"
                "<i>¡Saquea más barcos para conseguir más barriles!</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Reclamar Ganancias", callback_data="reclamar_ganancias")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
                ])
            )
            return

        # Configurar estado para venta
        context.user_data['estado_vender'] = 'esperando_cantidad_balance'
        
        # Mensaje de selección de cantidad con HTML
        await query.edit_message_text(
            "<b>🏴‍☠️ Venta de Barriles</b>\n\n"
            f"🛢️ <b>Barriles disponibles:</b> <code>{barriles:,}</code>\n\n"
            "💎 <b>Tasa de cambio:</b> 100 barriles = 1 CUP\n\n"
            "📦 <b>Opciones de venta:</b>\n"
            "▪️ 1,000 barriles = 💲10 CUP\n"
            "▪️ 25,000 barriles = 💲250 CUP\n"
            "▪️ 100,000 barriles = 💲1,000 CUP\n\n"
            "<i>Selecciona la cantidad que deseas vender:</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("1,000 🛢️ → 💲10", callback_data="1000"),
                    InlineKeyboardButton("25,000 🛢️ → 💲250", callback_data="25000")
                ],
                [
                    InlineKeyboardButton("100,000 🛢️ → 💲1,000", callback_data="100000"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="juego_pirata")
                ]
            ])
        )

    except Exception as e:
        print(f"Error en vender_barriles para {user_id}: {str(e)}")
        await query.edit_message_text(
            "<b>⚡ Error en la venta</b>\n\n"
            "Ocurrió un problema al procesar tu solicitud.\n\n"
            "<i>Por favor, intenta nuevamente más tarde.</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
            ])
        )

async def recibir_cantidad_vender(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Verificar estado de venta
    if context.user_data.get('estado_vender') != 'esperando_cantidad_balance':
        await query.edit_message_text(
            "<pre>❌ OPERACIÓN CANCELADA</pre>\n\n"
            "La sesión de venta ha expirado. Por favor, comienza de nuevo.",
            parse_mode="HTML"
        )
        return

    try:
        user_id = str(query.from_user.id)
        
        # Obtener cantidad seleccionada
        cantidad_barriles = int(query.data)
        cantidad_balance = cantidad_barriles // 100
        
        # Almacenar temporalmente
        context.user_data['cantidad_vender_balance'] = cantidad_barriles
        
        # Obtener datos actualizados
        juego_data = obtener_registro("juego_pirata", user_id, "barriles")
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        
        if not juego_data or not usuario_data:
            await query.edit_message_text(
                "<pre>❌ ERROR DE USUARIO</pre>\n\n"
                "No estás registrado en el sistema.",
                parse_mode="HTML"
            )
            return

        barriles = juego_data[0]
        balance = usuario_data[0]

        if barriles < cantidad_barriles:
            await query.edit_message_text(
                "<pre>❌ FONDOS INSUFICIENTES</pre>\n\n"
                f"<b>Barriles necesarios:</b> <code>{cantidad_barriles:,}</code>\n"
                f"<b>Barriles disponibles:</b> <code>{barriles:,}</code>\n\n"
                "💡 <i>Reclama más ganancias o mejora tu producción</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Intentar con menos", callback_data="vender_barriles")],
                    [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_principal")]
                ])
            )
            return

        # Mensaje de confirmación organizado
        await query.edit_message_text(
            "<pre>🔎 CONFIRMAR VENTA</pre>\n\n"
            "📝 <b>Resumen de transacción:</b>\n"
            f"▪️ <b>Barriles a vender:</b> <code>{cantidad_barriles:,}</code>\n"
            f"▪️ <b>Balance a recibir:</b> <code>{cantidad_balance:,}</code> CUP\n\n"
            "📊 <b>Tus recursos actuales:</b>\n"
            f"▪️ <b>Barriles:</b> <code>{barriles:,}</code>\n"
            f"▪️ <b>Balance:</b> <code>{balance:,}</code> CUP\n\n"
            "<i>¿Confirmas esta transacción?</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ CONFIRMAR", callback_data="confirmar_vender"),
                    InlineKeyboardButton("❌ CANCELAR", callback_data="juego_pirata")
                ]
            ])
        )

    except ValueError:
        await query.answer("⚠️ Cantidad no válida")
    except Exception as e:
        print(f"Error en recibir_cantidad_vender: {str(e)}")
        await query.edit_message_text(
            "<pre>❌ ERROR DEL SISTEMA</pre>\n\n"
            "Ocurrió un problema al procesar tu solicitud.",
            parse_mode="HTML"
        )


venta_cache = {}
async def confirmar_vender(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    try:
        user_id = str(query.from_user.id)
        tiempo_actual = time.time()
        
        # Verificar tiempo de espera (24 horas)
        # Necesitarías una tabla para almacenar los tiempos de venta
        ultima_venta_data = obtener_registro("ventas", user_id, "ultima_venta")
        ultima_venta = ultima_venta_data[0] if ultima_venta_data else 0

        if tiempo_actual - ultima_venta < 86400:  # 24 horas
            tiempo_restante = 86400 - (tiempo_actual - ultima_venta)
            await query.edit_message_text(
                f"⏳ <b>¡Debes esperar para vender nuevamente!</b>\n\n"
                f"Solo puedes realizar 1 venta cada 24 horas.\n"
                f"Tiempo restante: {format_time(tiempo_restante)}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
                ])
            )
            return

        cantidad_barriles = context.user_data.get('cantidad_vender_balance', 0)

        if cantidad_barriles <= 0:
            await query.edit_message_text(
                "<pre>❌ SIN SELECCIÓN</pre>\n\n"
                "No se especificó cantidad a vender.",
                parse_mode="HTML"
            )
            return

        # Obtener datos actuales
        juego_data = obtener_registro("juego_pirata", user_id, "barriles")
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        
        if not juego_data or not usuario_data:
            await query.edit_message_text(
                "<pre>❌ USUARIO NO REGISTRADO</pre>",
                parse_mode="HTML"
            )
            return

        barriles_actuales = juego_data[0]
        balance_actual = usuario_data[0]
        cantidad_balance = cantidad_barriles // 100

        if barriles_actuales < cantidad_barriles:
            await query.answer("¡No tienes suficientes barriles!")
            return

        # Actualizar base de datos
        exito_juego = actualizar_registro(
            "juego_pirata",
            user_id,
            {"barriles": barriles_actuales - cantidad_barriles}
        )
        
        exito_usuario = actualizar_registro(
            "usuarios",
            user_id,
            {"Balance": balance_actual + cantidad_balance}
        )
        
        # Registrar tiempo de venta
        exito_venta = actualizar_registro(
            "ventas",
            user_id,
            {"ultima_venta": tiempo_actual}
        )

        if not exito_juego or not exito_usuario or not exito_venta:
            await query.edit_message_text("❌ Error en la transacción")
            return

        await query.edit_message_text(
            "<pre>✅ VENTA COMPLETADA</pre>\n\n"
            "📦 <b>Detalles de la transacción:</b>\n"
            f"👤 <b>Usuario:</b> {query.from_user.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
            f"🛢️ <b>Barriles vendidos:</b> <code>{cantidad_barriles:,}</code>\n"
            f"💰 <b>Balance obtenido:</b> <code>{cantidad_balance:,}</code> CUP\n\n"
            "📊 <b>Nuevos saldos:</b>\n"
            f"▪️ <b>Barriles restantes:</b> <code>{barriles_actuales - cantidad_barriles:,}</code>\n"
            f"▪️ <b>Balance total:</b> <code>{balance_actual + cantidad_balance:,}</code> CUP\n\n"
            "⏳ <i>Podrás vender nuevamente en 24 horas</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏴‍☠️ Menú Pirata", callback_data="juego_pirata")],
                [InlineKeyboardButton("📊 Ver Barco", callback_data="ver_balance")]
            ])
        )

        # Notificaciones (opcional)
        grupo_admin = -1002492508397
        await context.bot.send_message(
            grupo_admin,
            "<pre>📢 NUEVA VENTA DE BARRILES</pre>\n\n"
            f"👤 <b>Usuario:</b> {query.from_user.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"🛢️ <b>Barriles:</b> <code>{cantidad_barriles:,}</code>\n"
            f"💰 <b>Balance:</b> <code>{cantidad_balance:,}</code> CUP",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error en confirmar_vender: {str(e)}")
        await query.edit_message_text(
            "<pre>❌ ERROR EN TRANSACCIÓN</pre>\n\n"
            "No se pudo completar la venta. Intenta nuevamente.",
            parse_mode="HTML"
        )
        
        

async def comprar_barriles(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    try:
        user_id = str(query.from_user.id)
        
        # Obtener balance del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        if not usuario_data:
            await query.edit_message_text(
                "<pre>❌ USUARIO NO REGISTRADO</pre>\n\n"
                "Debes registrarte primero con /start",
                parse_mode="HTML"
            )
            return

        balance = usuario_data[0]
        
        # Verificar balance mínimo
        if balance < 100:
            await query.edit_message_text(
                "<pre>❌ SALDO INSUFICIENTE</pre>\n\n"
                f"<b>Balance actual:</b> <code>{balance:,}</code> CUP\n"
                "<b>Mínimo requerido:</b> <code>100</code> CUP\n\n"
                "💸 <i>Necesitas más CUP para comprar barriles</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Recargar Balance", callback_data="show_balance")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
                ])
            )
            return

        # Configurar estado de compra
        context.user_data['estado_comprar'] = 'esperando_cantidad'
        
        # Mensaje de selección de cantidad
        await query.edit_message_text(
            "<pre>🛒 COMPRAR BARRILES</pre>\n\n"
            f"💰 <b>Balance disponible:</b> <code>{balance:,}</code> CUP\n\n"
            "📊 <b>Tasa de cambio:</b> 1 CUP = 70 barriles\n\n"
            "📦 <b>Opciones de compra:</b>\n"
            "▪️ 100 CUP = 7,000 barriles\n"
            "▪️ 250 CUP = 17,500 barriles\n"
            "▪️ 1,000 CUP = 70,000 barriles\n\n"
            "<i>Selecciona la cantidad que deseas comprar:</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("100 CUP → 7,000🛢️", callback_data="100"),
                    InlineKeyboardButton("250 CUP → 17,500🛢️", callback_data="250")
                ],
                [
                    InlineKeyboardButton("1,000 CUP → 70,000🛢️", callback_data="1000"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="juego_pirata")
                ]
            ])
        )

    except Exception as e:
        print(f"Error en comprar_barriles: {str(e)}")
        await query.edit_message_text(
            "<pre>❌ ERROR EN COMPRA</pre>\n\n"
            "No se pudo iniciar el proceso de compra.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
            ])
        )
        
async def recibir_cantidad_comprar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Verificar estado de compra
    if context.user_data.get('estado_comprar') != 'esperando_cantidad':
        await query.edit_message_text(
            "<pre>❌ SESIÓN EXPIRADA</pre>\n\n"
            "La sesión de compra ha caducado. Por favor, comienza de nuevo.",
            parse_mode="HTML"
        )
        return

    try:
        user_id = str(query.from_user.id)
        
        # Obtener cantidad seleccionada
        cantidad_CUP = int(query.data)
        cantidad_barriles = cantidad_CUP * 70
        
        # Almacenar temporalmente
        context.user_data['cantidad_comprar'] = cantidad_barriles
        
        # Verificar saldo actual
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        if not usuario_data:
            await query.edit_message_text(
                "<pre>❌ USUARIO NO ENCONTRADO</pre>",
                parse_mode="HTML"
            )
            return

        balance = usuario_data[0]

        if balance < cantidad_CUP:
            await query.edit_message_text(
                "<pre>❌ SALDO INSUFICIENTE</pre>\n\n"
                f"<b>Balance necesario:</b> <code>{cantidad_CUP:,}</code> CUP\n"
                f"<b>Balance disponible:</b> <code>{balance:,}</code> CUP\n\n"
                "💳 <i>Recarga tu balance para completar esta compra</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Depositar", callback_data="show_balance")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="comprar_barriles")]
                ])
            )
            return

        # Mensaje de confirmación
        await query.edit_message_text(
            "<pre>🔎 CONFIRMAR COMPRA</pre>\n\n"
            "📝 <b>Resumen de transacción:</b>\n"
            f"▪️ <b>CUP a invertir:</b> <code>{cantidad_CUP:,}</code>\n"
            f"▪️ <b>Barriles a recibir:</b> <code>{cantidad_barriles:,}</code>\n\n"
            "📊 <b>Tus recursos actuales:</b>\n"
            f"▪️ <b>Balance:</b> <code>{balance:,}</code> CUP\n\n"
            "<i>¿Confirmas esta transacción?</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ CONFIRMAR", callback_data="confirmar_comprar"),
                    InlineKeyboardButton("❌ CANCELAR", callback_data="juego_pirata")
                ]
            ])
        )

    except ValueError:
        await query.answer("⚠️ Cantidad no válida")
    except Exception as e:
        print(f"Error en recibir_cantidad_comprar: {str(e)}")
        await query.edit_message_text(
            "<pre>❌ ERROR DEL SISTEMA</pre>\n\n"
            "Ocurrió un problema al procesar tu solicitud.",
            parse_mode="HTML"
        )

async def confirmar_comprar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    try:
        user_id = str(query.from_user.id)
        cantidad_barriles = context.user_data.get('cantidad_comprar', 0)

        if cantidad_barriles <= 0:
            await query.edit_message_text(
                "<pre>❌ SIN SELECCIÓN</pre>\n\n"
                "No se especificó cantidad a comprar.",
                parse_mode="HTML"
            )
            return

        # Obtener datos actuales
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        juego_data = obtener_registro("juego_pirata", user_id, "barriles")
        
        if not usuario_data:
            await query.edit_message_text(
                "<pre>❌ USUARIO NO REGISTRADO</pre>",
                parse_mode="HTML"
            )
            return

        balance_actual = usuario_data[0]
        barriles_actuales = juego_data[0] if juego_data else 0
        cantidad_CUP = cantidad_barriles // 70

        if balance_actual < cantidad_CUP:
            await query.answer("¡No tienes suficiente balance!")
            return

        # Actualizar base de datos
        exito_usuario = actualizar_registro(
            "usuarios",
            user_id,
            {"Balance": balance_actual - cantidad_CUP}
        )
        
        exito_juego = actualizar_registro(
            "juego_pirata",
            user_id,
            {"barriles": barriles_actuales + cantidad_barriles}
        )

        if not exito_usuario or not exito_juego:
            await query.edit_message_text("❌ Error en la transacción")
            return

        # Mensaje de confirmación
        await query.edit_message_text(
            "<pre>✅ COMPRA COMPLETADA</pre>\n\n"
            "📦 <b>Detalles de la transacción:</b>\n"
            f"👤 <b>Usuario:</b> {query.from_user.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
            f"💰 <b>CUP invertidas:</b> <code>{cantidad_CUP:,}</code>\n"
            f"🛢️ <b>Barriles obtenidos:</b> <code>{cantidad_barriles:,}</code>\n\n"
            "📊 <b>Nuevos saldos:</b>\n"
            f"▪️ <b>Balance restante:</b> <code>{balance_actual - cantidad_CUP:,}</code> CUP\n"
            f"▪️ <b>Total barriles:</b> <code>{barriles_actuales + cantidad_barriles:,}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏴‍☠️ Menú Pirata", callback_data="juego_pirata")],
                [InlineKeyboardButton("📊 Ver barco", callback_data="ver_balance")]
            ])
        )
        
            # Notificación al grupo admin
        grupo_admin = -1002492508397
        await context.bot.send_message(
            grupo_admin,
                "<pre>📢 NUEVA COMPRA DE BARRILES</pre>\n\n"
            f"👤 <b>Usuario:</b> {query.from_user.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"💰 <b>CUP invertidas:</b> <code>{cantidad_CUP:,}</code>\n"
            f"🛢️ <b>Barriles obtenidos:</b> <code>{cantidad_barriles:,}</code>",
            parse_mode="HTML"
            )        

    except Exception as e:
        print(f"Error en confirmar_comprar: {str(e)}")
        await query.edit_message_text(
            "<pre>❌ ERROR EN TRANSACCIÓN</pre>\n\n"
            "No se pudo completar la compra. Intenta nuevamente.",
            parse_mode="HTML"
        )        




async def simular_combate_epico(update: Update, context: CallbackContext, user_id: str, oponente_id: str):
    """Simula un combate épico con mensajes visuales en HTML"""
    try:
        # Obtener nombres de usuarios desde la base de datos
        user_data = obtener_registro("usuarios", user_id, "Nombre")
        oponente_data = obtener_registro("usuarios", oponente_id, "Nombre")
        
        if not user_data or not oponente_data:
            await update.message.reply_text("❌ Error: Usuario u oponente no encontrado")
            return
            
        user_nombre = user_data[0]
        oponente_nombre = oponente_data[0]

        mensajes_combate = [
            f"⚔️ <b>{user_nombre}</b> lanza un <u>ataque sorpresa</u> contra <b>{oponente_nombre}</b> con un grito de guerra ensordecedor.",
            f"💥 <b>{user_nombre}</b> ordena disparar los cañones: <i>¡Fuegoooo!</i> — ¡el océano tiembla con el estruendo!",
            f"🌀 <b>{oponente_nombre}</b> gira el timón y esquiva por poco los proyectiles que silban entre las velas.",
            f"🔥 ¡<b>Impacto directo!</b> Los mástiles de <b>{oponente_nombre}</b> arden como antorchas flotantes.",
            f"💣 <b>{oponente_nombre}</b> responde con una lluvia de metralla que atraviesa el casco del enemigo.",
            f"🛡️ La tripulación de <b>{user_nombre}</b> se cubre con barriles de ron mientras las astillas vuelan por el aire.",
            f"🌪️ El mar ruge, el cielo oscurece... ¡el duelo es <i>feroz</i>! Las olas golpean con rabia los barcos en guerra.",
            f"💀 <b>{oponente_nombre}</b> sufre bajas: humo, fuego y confusión reinan en cubierta.",
            f"🏴‍☠️ <b>{user_nombre}</b> grita: <i>¡Al abordajeee!</i> — Sus piratas saltan con cuchillos en los dientes y cuerdas en mano."
        ]

        query = update.callback_query
        mensaje_inicial = (
            "⚓ <b>¡COMIENZA EL COMBATE PIRATA!</b> ⚓\n\n"
            f"🏴‍☠️ <b>{user_nombre}</b> VS <b>{oponente_nombre}</b>\n"
            f"🌊 <i>Los barcos se alinean, el viento sopla... el destino está por decidirse.</i>"
        )

        try:
            mensaje_combate = await query.edit_message_text(
                mensaje_inicial,
                parse_mode="HTML"
            )
        except (TimedOut, RetryAfter, TelegramError) as err:
            print(f"[ERROR inicio combate] {err}")
            return

        texto_actual = mensaje_inicial

        for _ in range(random.randint(5, 7)):
            await asyncio.sleep(1.5)
            nuevo_mensaje = random.choice(mensajes_combate)
            nuevo_texto = f"{texto_actual}\n\n{nuevo_mensaje}"

            if nuevo_texto != texto_actual:  # Evitar "Message is not modified"
                try:
                    await mensaje_combate.edit_text(nuevo_texto, parse_mode="HTML")
                    texto_actual = nuevo_texto  # Actualizar texto actual
                except BadRequest as err:
                    if "message is not modified" in str(err).lower():
                        print("[SKIP] Mensaje no modificado")
                        continue
                    else:
                        print(f"[ERROR animación combate] {err}")
                except (TimedOut, RetryAfter, TelegramError) as err:
                    print(f"[ERROR animación combate] {err}")
                    continue

        await asyncio.sleep(1)
        final_texto = f"{texto_actual}\n\n💥 <b>¡EL COMBATE HA TERMINADO!</b>"
        if final_texto != texto_actual:
            try:
                await mensaje_combate.edit_text(final_texto, parse_mode="HTML")
            except (TimedOut, RetryAfter, TelegramError) as err:
                print(f"[ERROR mensaje final] {err}")

    except Exception as e:
        print(f"Error general en simular_combate_epico: {e}")








                          
async def comprar_escudo(update: Update, context: CallbackContext, tipo_escudo: str):
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    try:
        # Configuración de escudos
        escudos = {
            "basico": {"costo": 200, "duracion": 2*3600},  # 2 horas
            "premium": {"costo": 10, "duracion": 4*3600}   # 4 horas (por balance)
        }
        
        escudo = escudos.get(tipo_escudo)
        if not escudo:
            await query.answer("❌ Tipo de escudo no válido")
            return
        
        # Obtener datos del usuario
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, escudo_hasta")
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        
        if not juego_data or not usuario_data:
            await query.answer("❌ Usuario no encontrado")
            return
            
        barriles, escudo_hasta_actual = juego_data
        balance = usuario_data[0]
        
        # Verificar recursos
        if tipo_escudo == "basico" and barriles < escudo["costo"]:
            await query.answer("❌ No tienes suficientes barriles")
            return
            
        if tipo_escudo == "premium" and balance < escudo["costo"]:
            await query.answer("❌ No tienes suficiente balance")
            return
        
        # Calcular nuevo tiempo de escudo
        nuevo_escudo_hasta = tm.time() + escudo["duracion"]
        
        # Actualizar base de datos
        if tipo_escudo == "basico":
            exito = actualizar_registro("juego_pirata", user_id, {
                "escudo_hasta": nuevo_escudo_hasta,
                "barriles": barriles - escudo["costo"]
            })
        else:
            exito_juego = actualizar_registro("juego_pirata", user_id, {
                "escudo_hasta": nuevo_escudo_hasta
            })
            exito_usuario = actualizar_registro("usuarios", user_id, {
                "Balance": balance - escudo["costo"]
            })
            exito = exito_juego and exito_usuario
        
        if not exito:
            await query.answer("❌ Error al procesar la compra")
            return
        
        await query.edit_message_text(
            f"<pre>🛡️ ESCUDO ACTIVADO</pre>\n\n"
            f"✅ Has adquirido un escudo {tipo_escudo} por {format_time(escudo['duracion'])}\n\n"
            f"🛡️ <b>Protección hasta:</b> {datetime.fromtimestamp(nuevo_escudo_hasta).strftime('%H:%M')}\n\n"
            "<i>¡Ningún pirata podrá atacarte durante este tiempo!</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏴‍☠️ Volver al Menú", callback_data="juego_pirata")]
            ])
        )
        
    except Exception as e:
        print(f"Error en comprar_escudo: {str(e)}")
        await query.answer("❌ Error al comprar escudo")
        
async def reparar_barco(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    try:
        # Obtener datos del juego pirata usando obtener_registro
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, hp_barco")
        
        if not juego_data:
            await query.edit_message_text(
                "❌ <b>No estás registrado en el juego pirata</b>",
                parse_mode="HTML"
            )
            return
            
        barriles, hp_barco = juego_data
        
        # Calcular costo de reparación
        hp_faltante = 100 - hp_barco
        if hp_faltante <= 0:
            await query.answer("✅ Tu barco ya está en perfecto estado")
            return
            
        costo = hp_faltante * 5  # 5 barriles por punto de HP
        
        if barriles < costo:
            await query.edit_message_text(
                f"❌ <b>No tienes suficientes barriles</b>\n\n"
                f"Necesitas {costo} barriles para reparar tu barco.\n"
                f"Tienes: {barriles} barriles",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Reclamar ganancias", callback_data="reclamar_ganancias")],
                    [InlineKeyboardButton("🛒 Comprar barriles", callback_data="comprar_barriles")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ])
            )
            return
        
        # Realizar reparación usando actualizar_registro
        exito = actualizar_registro("juego_pirata", user_id, {
            "hp_barco": 100,
            "barriles": barriles - costo
        })
        
        if not exito:
            await query.answer("❌ Error al reparar barco")
            return
            
        await query.edit_message_text(
            f"🛠️ <b>¡Barco reparado!</b>\n\n"
            f"Tu barco ha sido completamente reparado.\n\n"
            f"💰 <b>Costo:</b> {costo} barriles\n"
            f"🛢️ <b>Barriles restantes:</b> {barriles - costo}\n"
            f"❤️ <b>HP del barco:</b> 100/100",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Menú PvP", callback_data="menu_combate")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="juego_pirata")]
            ])
        )
        
    except Exception as e:
        print(f"Error en reparar_barco: {str(e)}")
        await query.edit_message_text(
            "❌ <b>Error al reparar el barco</b>\n\n"
            "No se pudo completar la reparación.\n"
            "Intenta nuevamente más tarde.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
            ])
        )
async def menu_combate_pvp(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    try:
        # Obtener datos del usuario
        juego_data = obtener_registro("juego_pirata", user_id, 
                                    "hp_barco, escudo_hasta, prestigio, victorias, derrotas")
        
        if not juego_data:
            await query.answer("❌ Usuario no encontrado")
            return
            
        hp_barco, escudo_hasta, prestigio, victorias, derrotas = juego_data
        
        # Obtener nivel del barco
        barco_data = obtener_registro("mejoras", (user_id, "barco"), "nivel")
        nivel_barco = barco_data[0] if barco_data else 1
        
        # Verificar escudo activo
        escudo_activo = escudo_hasta > tm.time() if escudo_hasta else False
        
        # Crear mensaje
        mensaje = "<pre>⚔️ COMBATE PvP</pre>\n\n"
        mensaje += f"🚢 <b>Barco:</b> Nivel {nivel_barco}\n"
        mensaje += f"❤️ <b>HP del barco:</b> {hp_barco}/100\n"
        
        if escudo_activo:
            tiempo_escudo = escudo_hasta - tm.time()
            mensaje += f"🛡️ <b>Escudo activo:</b> {format_time(tiempo_escudo)} restantes\n\n"
        else:
            mensaje += "🛡️ <b>Escudo:</b> Inactivo\n\n"
        
        mensaje += "🏆 <b>Estadísticas PvP:</b>\n"
        mensaje += f"▪️ Prestigio: {prestigio}\n"
        mensaje += f"▪️ Victorias: {victorias}\n"
        mensaje += f"▪️ Derrotas: {derrotas}\n\n"
        
        # Botones
        teclado = []
        
        if hp_barco > 0 and not escudo_activo and nivel_barco >= 3:
            teclado.append([InlineKeyboardButton("⚔️ Buscar Combate", callback_data="buscar_combate")])
        
        if hp_barco < 100:
            teclado.append([InlineKeyboardButton("🛠️ Reparar Barco", callback_data="reparar_barco")])
        
        teclado.append([
            InlineKeyboardButton("🛡️ Escudo Básico (200🛢️)", callback_data="escudo_basico"),
            InlineKeyboardButton("🛡️ Escudo Premium (10💲)", callback_data="escudo_premium")
        ])
        
        teclado.append([InlineKeyboardButton("🏆 Ranking PvP", callback_data="ranking_pvp")])
        teclado.append([InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")])
        
        await query.edit_message_text(
            mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(teclado)
        )
        
    except Exception as e:
        print(f"Error en menu_combate_pvp: {str(e)}")
        await query.answer("❌ Error al mostrar menú de combate")        
                        
async def mostrar_ranking_pvp(update: Update, context: CallbackContext):
    query = update.callback_query

    try:
        # Consulta para obtener el ranking usando ejecutar_consulta_segura
        consulta = """
            SELECT u.id, u.Nombre, j.prestigio, j.victorias, j.derrotas, 
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'barco') as nivel_barco
            FROM usuarios u
            JOIN juego_pirata j ON u.id = j.id
            WHERE j.prestigio > 0
            ORDER BY j.prestigio DESC
            LIMIT 10
        """
        
        ranking_data = ejecutar_consulta_segura(consulta, obtener_resultados=True)
        
        if not ranking_data:
            await query.edit_message_text(
                "📊 <b>Ranking PvP</b>\n\n"
                "No hay jugadores con prestigio aún.\n"
                "¡Sé el primero en ganar prestigio en combates!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚔️ Buscar Combate", callback_data="buscar_combate")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ])
            )
            return

        # Crear lista de jugadores para ranking
        ranking = []
        for row in ranking_data:
            user_id, nombre, prestigio, victorias, derrotas, nivel_barco = row
            ranking.append({
                "nombre": nombre or "Desconocido",
                "prestigio": prestigio,
                "victorias": victorias,
                "derrotas": derrotas,
                "nivel_barco": nivel_barco or 1
            })

        # Crear mensaje visualmente atractivo
        mensaje = "<b>🏴‍☠️ RANKING PvP - Top 10 Piratas</b>\n"
        mensaje += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        mensaje += "<pre> #  Nombre        🏆  ⚔️  🚢</pre>\n"
        mensaje += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        for i, jugador in enumerate(ranking, 1):
            # Formatear el nombre para que quepa en el espacio
            nombre_formateado = jugador['nombre'][:12].ljust(12)
            mensaje += (
                f"<pre>{str(i).rjust(2)}. {nombre_formateado} "
                f"{str(jugador['prestigio']).rjust(3)}  "
                f"{str(jugador['victorias']).rjust(2)}  "
                f"{'N'+str(jugador['nivel_barco'])}</pre>\n"
            )

        mensaje += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        mensaje += "🏆 <b>Prestigio</b> | ⚔️ <b>Victorias</b> | 🚢 <b>Nivel Barco</b>"

        await query.edit_message_text(
            mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data="ranking_pvp")],
                [InlineKeyboardButton("⚔️ Menú Combate", callback_data="menu_combate")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="juego_pirata")]
            ])
        )

    except Exception as e:
        print(f"Error en mostrar_ranking_pvp: {str(e)}")
        await query.edit_message_text(
            "❌ <b>Error al cargar el ranking</b>\n\n"
            "No se pudo obtener la información del ranking.\n"
            "Intenta nuevamente más tarde.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
            ])
        )


async def encontrar_oponente(user_id: str, nivel_barco: int, data: dict, oponente_previo: str = None) -> str:
    """Encuentra un oponente aleatorio para el jugador, excluyendo solo los que tienen escudo activo"""
    oponentes_validos = []
    
    for oponente_id, oponente_data in data["juego_pirata"].items():
        # Excluir al usuario actual, oponente previo y barcos no aptos
        if (oponente_id == user_id or 
            oponente_id == oponente_previo or
            oponente_data.get("mejoras", {}).get("barco", {}).get("nivel", 0) < 3 or  # Barco nivel mínimo 1
            oponente_data.get("hp_barco", 0) <= 0 or  # Barco no destruido
            oponente_data.get("escudo_hasta", 0) > tm.time()):  # Sin escudo activo
            continue
        
        oponentes_validos.append(oponente_id)
    
    # Si hay oponentes válidos, elegir uno al azar
    if oponentes_validos:
        return random.choice(oponentes_validos)
    
    return None
    
    
async def buscar_combate(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    try:
        # Verificar cooldown usando la base de datos
        juego_data = obtener_registro("juego_pirata", user_id, "ultimo_ataque, hp_barco, escudo_hasta")
        
        if not juego_data:
            await query.edit_message_text("❌ No estás registrado en el juego pirata.", parse_mode="HTML")
            return
            
        ultimo_ataque, hp_barco, escudo_hasta = juego_data
        
        # Verificar cooldown
        tiempo_actual = tm.time()
        
        if ultimo_ataque and tiempo_actual - ultimo_ataque < PVP_COOLDOWN:
            tiempo_restante = PVP_COOLDOWN - (tiempo_actual - ultimo_ataque)
            await query.edit_message_text(
                f"⏳ <b>Enfriamiento de combate</b>\n\n"
                f"Debes esperar {format_time(tiempo_restante)} antes de atacar de nuevo.\n\n"
                f"🕒 Puedes atacar nuevamente a las {datetime.fromtimestamp(ultimo_ataque + PVP_COOLDOWN).strftime('%H:%M')}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ])
            )
            return

        # Obtener nivel del barco
        barco_data = obtener_registro("mejoras", (user_id, "barco"), "nivel")
        nivel_barco = barco_data[0] if barco_data else 0
        
        if nivel_barco < 1:
            await query.edit_message_text(
                "❌ <b>Barco muy novato</b>\n\n"
                "Necesitas un barco nivel 1+ para combatir.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏫ Mejorar Barco", callback_data="mejorar_barco")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ])
            )
            return
            
        if hp_barco <= 0:
            await query.edit_message_text(
                "💀 <b>Barco destruido</b>\n\n"
                "Repara tu barco antes de combatir.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛠️ Reparar Barco", callback_data="reparar_barco")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ])
            )
            return
            
        if escudo_hasta and escudo_hasta > tm.time():
            tiempo_escudo = escudo_hasta - tm.time()
            await query.edit_message_text(
                "🛡️ <b>Escudo activo</b>\n\n"
                f"No puedes atacar mientras tu escudo esté activo.\n"
                f"Tiempo restante: {format_time(tiempo_escudo)}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ])
            )
            return

        # Obtener oponente anterior para excluirlo
        oponente_anterior = context.user_data.get('oponente_pvp')
        
        # Buscar nuevo oponente
        oponente_id = await encontrar_oponente_db(user_id, nivel_barco, oponente_previo=oponente_anterior)
        
        if not oponente_id:
            # No se encontró oponente
            mensaje = (
                "🔎 <b>No hay más oponentes disponibles</b>\n\n"
                "No hemos encontrado otros piratas para combatir.\n\n"
            )
            
            if oponente_anterior:
                mensaje += "💡 Puedes intentar atacar al oponente anterior o volver más tarde."
                keyboard = [
                    [InlineKeyboardButton("⚔️ Atacar anterior", callback_data="confirmar_ataque")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ]
            else:
                mensaje += "💡 Intenta nuevamente más tarde cuando más jugadores estén activos."
                keyboard = [
                    [InlineKeyboardButton("🔄 Reintentar", callback_data="buscar_combate")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
                ]
                
            await query.edit_message_text(
                mensaje,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Si encontramos oponente, mostrarlo
        context.user_data['oponente_pvp'] = oponente_id
        
        # Obtener datos del oponente
        oponente_nombre_data = obtener_registro("usuarios", oponente_id, "Nombre")
        oponente_juego_data = obtener_registro("juego_pirata", oponente_id, "hp_barco, prestigio, victorias, derrotas")
        oponente_barco_data = obtener_registro("mejoras", (oponente_id, "barco"), "nivel")
        
        if not oponente_nombre_data or not oponente_juego_data or not oponente_barco_data:
            await query.edit_message_text("❌ Error al cargar datos del oponente")
            return
            
        oponente_nombre = oponente_nombre_data[0]
        oponente_hp, oponente_prestigio, oponente_victorias, oponente_derrotas = oponente_juego_data
        oponente_nivel_barco = oponente_barco_data[0]

        # Mensaje detallado del oponente
        await query.edit_message_text(
            f"⚔️ <b>¡Nuevo oponente encontrado!</b>\n\n"
            f"🏴‍☠️ <b>Capitán:</b> {oponente_nombre}\n"
            f"🚢 <b>Barco:</b> Nivel {oponente_nivel_barco}\n"
            f"❤️ <b>HP:</b> {oponente_hp}/100\n"
            f"🏆 <b>Prestigio:</b> {oponente_prestigio}\n\n"
            f"⚔️ <b>Victorias:</b> {oponente_victorias}\n"
            f"💀 <b>Derrotas:</b> {oponente_derrotas}\n\n"
            "<i>¿Quieres atacar a este pirata?</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ ATACAR", callback_data="confirmar_ataque")],
                [InlineKeyboardButton("🔁 Buscar otro", callback_data="buscar_combate")],
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
            ])
        )

    except Exception as e:
        print(f"Error en buscar_combate: {str(e)}")
        # Mensaje de error específico
        mensaje_error = (
            "⚡ <b>Error al buscar otro oponente</b>\n\n"
            "No se pudo encontrar un nuevo pirata para combatir.\n\n"
        )
        
        if context.user_data.get('oponente_pvp'):
            mensaje_error += "💡 Puedes intentar atacar al oponente anterior o volver más tarde."
            keyboard = [
                [InlineKeyboardButton("⚔️ Atacar anterior", callback_data="confirmar_ataque")],
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
            ]
        else:
            mensaje_error += "💡 Intenta nuevamente más tarde."
            keyboard = [
                [InlineKeyboardButton("🔄 Reintentar", callback_data="buscar_combate")],
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
            ]
            
        await query.edit_message_text(
            mensaje_error,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
async def confirmar_ataque(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    oponente_id = context.user_data.get('oponente_pvp')
    
    if not oponente_id:
        await query.answer("❌ Oponente no disponible")
        return
    
    try:
        # Obtener datos del atacante desde la base de datos
        atacante_juego_data = obtener_registro("juego_pirata", user_id, "hp_barco, prestigio")
        if not atacante_juego_data:
            await query.answer("❌ Datos del atacante no encontrados")
            return
            
        # Obtener mejoras del atacante
        atacante_mejoras = {}
        tipos_mejoras = ["barco", "cañones", "velas"]
        for tipo in tipos_mejoras:
            mejora_data = obtener_registro("mejoras", (user_id, tipo), "nivel")
            atacante_mejoras[tipo] = mejora_data[0] if mejora_data else 1
        
        # Obtener datos del defensor desde la base de datos
        defensor_juego_data = obtener_registro("juego_pirata", oponente_id, "hp_barco, prestigio")
        if not defensor_juego_data:
            await query.answer("❌ Datos del defensor no encontrados")
            return
            
        # Obtener mejoras del defensor
        defensor_mejoras = {}
        for tipo in tipos_mejoras:
            mejora_data = obtener_registro("mejoras", (oponente_id, tipo), "nivel")
            defensor_mejoras[tipo] = mejora_data[0] if mejora_data else 1
        
        # Obtener nombres de los jugadores
        atacante_nombre_data = obtener_registro("usuarios", user_id, "Nombre")
        defensor_nombre_data = obtener_registro("usuarios", oponente_id, "Nombre")
        
        if not atacante_nombre_data or not defensor_nombre_data:
            await query.answer("❌ Nombres de jugadores no encontrados")
            return
            
        atacante_nombre = atacante_nombre_data[0]
        defensor_nombre = defensor_nombre_data[0]
        
        # Calcular probabilidades preliminares
        def calcular_puntaje(mejoras):
            return (
                mejoras["barco"] * 5 +
                mejoras["cañones"] * 3 +
                mejoras["velas"] * 1
            )
        
        puntaje_atacante = calcular_puntaje(atacante_mejoras)
        puntaje_defensor = calcular_puntaje(defensor_mejoras)
        total = puntaje_atacante + puntaje_defensor
        prob_atacante = int((puntaje_atacante / total) * 100) if total > 0 else 50
        
        # Mostrar información de probabilidades
        await query.edit_message_text(
            f"⚔️ <b>PROBABILIDADES DE COMBATE</b>\n\n"
            f"🏴‍☠️ <b>Atacante:</b> {atacante_nombre}\n"
            f"🛡️ <b>Defensor:</b> {defensor_nombre}\n\n"
            f"📊 <b>Probabilidades de victoria:</b>\n"
            f"▫️ Tus probabilidades: {prob_atacante}%\n"
            f"▫️ Probabilidades del oponente: {100-prob_atacante}%\n\n"
            f"🎯 <b>Tu puntuación:</b>\n"
            f"▪️ Barco: Nivel {atacante_mejoras['barco']} (x5) = {atacante_mejoras['barco']*5}\n"
            f"▪️ Cañones: Nivel {atacante_mejoras['cañones']} (x3) = {atacante_mejoras['cañones']*3}\n"
            f"▪️ Velas: Nivel {atacante_mejoras['velas']} (x1) = {atacante_mejoras['velas']*1}\n"
            f"▫️ <b>Total:</b> {puntaje_atacante} puntos\n\n"
            f"🎯 <b>Puntuación del oponente:</b>\n"
            f"▪️ Barco: Nivel {defensor_mejoras['barco']} = {defensor_mejoras['barco']*5}\n"
            f"▪️ Cañones: Nivel {defensor_mejoras['cañones']} = {defensor_mejoras['cañones']*3}\n"
            f"▪️ Velas: Nivel {defensor_mejoras['velas']} = {defensor_mejoras['velas']*1}\n"
            f"▫️ <b>Total:</b> {puntaje_defensor} puntos\n\n"
            f"⚠️ <i>Las probabilidades son estimadas y pueden variar</i>\n\n"
            f"¿Quieres proceder con el ataque?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ CONFIRMAR ATAQUE", callback_data="confirmar_combate")],
                [InlineKeyboardButton("🔁 BUSCAR OTRO OPONENTE", callback_data="buscar_combate")],
                [InlineKeyboardButton("🔙 CANCELAR", callback_data="menu_combate")]
            ])
        )
            
    except Exception as e:
        print(f"Error en confirmar_ataque: {str(e)}")
        await query.edit_message_text(
            "⚡ Error al calcular probabilidades. Intenta nuevamente.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_combate")]
            ])
        )        
        
async def confirmar_combate(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    oponente_id = context.user_data.get('oponente_pvp')
    
    try:
        # Simular combate épico
        await simular_combate_epico(update, context, user_id, oponente_id)
        
        # Resolver combate usando la base de datos
        resultado = await resolver_combate(user_id, oponente_id, context)
        
        # Obtener nombres de usuarios
        atacante_nombre_data = obtener_registro("usuarios", user_id, "Nombre")
        defensor_nombre_data = obtener_registro("usuarios", oponente_id, "Nombre")
        
        if not atacante_nombre_data or not defensor_nombre_data:
            await query.edit_message_text("❌ Error: No se pudieron obtener los datos de los jugadores")
            return
            
        atacante_nombre = atacante_nombre_data[0]
        defensor_nombre = defensor_nombre_data[0]
        
        # Obtener datos actualizados después del combate
        atacante_data = obtener_registro("juego_pirata", user_id, "barriles, hp_barco, prestigio, victorias, derrotas")
        defensor_data = obtener_registro("juego_pirata", oponente_id, "barriles, hp_barco, prestigio, victorias, derrotas")
        
        if not atacante_data or not defensor_data:
            await query.edit_message_text("❌ Error: No se pudieron obtener los datos del juego")
            return
            
        atacante_barriles, atacante_hp, atacante_prestigio, atacante_victorias, atacante_derrotas = atacante_data
        defensor_barriles, defensor_hp, defensor_prestigio, defensor_victorias, defensor_derrotas = defensor_data
        
        # Notificar combate al grupo de registro
        try:
            reporte_combate = (
                f"📜 <b>REPORTE DE COMBATE</b> 📜\n\n"
                f"⚔️ <b>Contendientes:</b>\n"
                f"• Atacante: {atacante_nombre}\n"
                f"• Defensor: {defensor_nombre}\n\n"
                f"🏆 <b>Ganador:</b> {atacante_nombre if resultado['ganador'] == user_id else defensor_nombre}\n"
                f"💰 <b>Botín:</b> {resultado['botin']} barriles\n"
                f"⭐ <b>Prestigio:</b> +{resultado['prestigio']}\n\n"
                f"⚓ <b>Estado final:</b>\n"
                f"• {atacante_nombre}: {atacante_hp}/100 HP\n"
                f"• {defensor_nombre}: {defensor_hp}/100 HP"
            )
            
            await context.bot.send_message(
                chat_id=REGISTRO_MINIJUEGOS,
                text=reporte_combate,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error al enviar reporte de combate: {str(e)}")
        
        # Preparar mensajes según el resultado
        if resultado['ganador'] == user_id:
            # Atacante ganó
            mensaje_atacante = (
                f"🏆 <b>¡SAQUEO EXITOSO!</b>\n\n"
                f"Has derrotado a {defensor_nombre} y saqueaste su barco!\n\n"
                f"🛢️ <b>Barriles robados:</b> +{resultado['botin']}\n"
                f"🏆 <b>Prestigio ganado:</b> +{resultado['prestigio']}\n"
                f"❤️ <b>HP de tu barco:</b> {atacante_hp}/100\n\n"
                f"💸 <b>Botín total:</b> {atacante_barriles} barriles"
            )
            
            mensaje_defensor = (
                f"💀 <b>¡HAS SIDO SAQUEADO!</b>\n\n"
                f"{atacante_nombre} ha vencido a tu barco y te ha robado!\n\n"
                f"🛢️ <b>Barriles perdidos:</b> -{resultado['botin']}\n"
                f"🏆 <b>Prestigio perdido:</b> -{resultado['prestigio']}\n"
                f"💔 <b>Daño recibido:</b> -{resultado['dano']} HP\n"
                f"❤️ <b>HP de tu barco:</b> {defensor_hp}/100\n\n"
                f"💸 <b>Barriles restantes:</b> {defensor_barriles}\n\n"
                f"⚔️ <i>¡Prepárate para vengarte cuando repares tu barco!</i>"
            )
        else:
            # Defensor ganó
            mensaje_atacante = (
                f"💀 <b>¡ATAQUE FALLIDO!</b>\n\n"
                f"{defensor_nombre} ha repelido tu ataque.\n\n"
                f"💔 <b>Daño recibido:</b> -{resultado['dano']} HP\n"
                f"❤️ <b>HP de tu barco:</b> {atacante_hp}/100\n\n"
                f"⚔️ <i>¡Mejora tu barco para el próximo combate!</i>"
            )
            
            mensaje_defensor = (
                f"🏆 <b>¡DEFENSA EXITOSA!</b>\n\n"
                f"Has repelido el ataque de {atacante_nombre} y capturaste sus recursos!\n\n"
                f"🛢️ <b>Barriles capturados:</b> +{resultado['botin']}\n"
                f"🏆 <b>Prestigio ganado:</b> +{resultado['prestigio']}\n"
                f"❤️ <b>HP de tu barco:</b> {defensor_hp}/100\n\n"
                f"💸 <b>Botín total:</b> {defensor_barriles} barriles\n\n"
                f"🛡️ <i>¡Tu tripulación celebra la victoria!</i>"
            )
        
        # Enviar mensaje al atacante
        await query.edit_message_text(
            mensaje_atacante,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Nuevo Combate", callback_data="buscar_combate")],
                [InlineKeyboardButton("🔙 Menú Pirata", callback_data="juego_pirata")]
            ])
        )
        
        # Enviar mensaje al defensor
        try:
            await context.bot.send_message(
                chat_id=oponente_id,
                text=mensaje_defensor,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚔️ Vengarse", callback_data=f"buscar_combate")],
                    [InlineKeyboardButton("🛠️ Reparar Barco", callback_data="reparar_barco")],
                    [InlineKeyboardButton("🛡️ Comprar Escudo", callback_data="menu_combate")]
                ])
            )
        except Exception as e:
            print(f"Error al notificar al defensor: {str(e)}")
            # Si falla, intentar enviar un mensaje más simple
            try:
                await context.bot.send_message(
                    chat_id=oponente_id,
                    text=f"⚔️ {atacante_nombre} te atacó! Revisa tu barco en /pirata",
                    parse_mode="HTML"
                )
            except:
                pass
        
        # Actualizar tiempo del último ataque
        actualizar_registro("juego_pirata", user_id, {
            "ultimo_ataque": tm.time()
        })
        
    except Exception as e:
        print(f"Error en confirmar_combate: {str(e)}")
        await query.edit_message_text(
            "⚡ <b>Error en el combate</b>\n\n"
            "El resultado no pudo procesarse correctamente.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_combate")]
            ])
        )
async def encontrar_oponente_db(user_id, nivel_barco, oponente_previo=None):
    """Encuentra un oponente adecuado en la base de datos usando funciones seguras"""
    try:
        # Buscar oponentes con nivel de barco similar y que no sean el usuario actual
        query = """
            SELECT u.id 
            FROM usuarios u
            JOIN juego_pirata j ON u.id = j.id
            JOIN mejoras m ON u.id = m.id AND m.tipo = 'barco'
            WHERE u.id != ? 
            AND j.hp_barco > 0 
            AND (j.escudo_hasta IS NULL OR j.escudo_hasta < ?)
            AND m.nivel BETWEEN ? AND ?
            ORDER BY RANDOM()
            LIMIT 1
        """
        
        # Rango de niveles aceptable (±2 niveles)
        nivel_min = max(1, nivel_barco - 2)
        nivel_max = nivel_barco + 2
        
        # Usar ejecutar_consulta_segura en lugar de conexión directa
        resultado = ejecutar_consulta_segura(
            query, 
            (user_id, tm.time(), nivel_min, nivel_max), 
            obtener_resultados=True
        )
        
        return resultado[0][0] if resultado else None
        
    except Exception as e:
        print(f"Error en encontrar_oponente_db: {str(e)}")
        return None

            
            

async def destruir_barco(user_id: str, context: CallbackContext):
    """Procesa la destrucción de un barco"""
    try:
        # Obtener nivel actual del barco
        barco_data = obtener_registro("mejoras", (user_id, "barco"), "nivel")
        if not barco_data:
            return
            
        nivel_actual = barco_data[0]
        
        # Reducir nivel aleatoriamente (30% de chance)
        if random.random() < 0.8:
            nuevo_nivel = max(1, nivel_actual - 1)
            actualizar_registro("mejoras", (user_id, "barco"), {"nivel": nuevo_nivel})
        
        # Reparación parcial
        hp_parcial = random.randint(20, 40)
        actualizar_registro("juego_pirata", user_id, {"hp_barco": hp_parcial})
        
        # Obtener nombre del usuario para la notificación
        usuario_data = obtener_registro("usuarios", user_id, "Nombre")
        if usuario_data:
            nombre_usuario = usuario_data[0]
            # Notificación al grupo
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"💥 ¡El barco de {nombre_usuario} ha sido destruido en combate!",
                parse_mode="HTML"
            )
            
    except Exception as e:
        print(f"Error en destruir_barco: {str(e)}")

async def resolver_combate(atacante_id: str, defensor_id: str, context: CallbackContext) -> dict:
    """Resuelve el resultado de un combate con nuevo sistema de puntuación"""
    try:
        # Obtener datos de ambos jugadores
        atacante_data = obtener_registro("juego_pirata", atacante_id, 
                                       "barriles, prestigio, victorias, derrotas, hp_barco")
        defensor_data = obtener_registro("juego_pirata", defensor_id, 
                                       "barriles, prestigio, victorias, derrotas, hp_barco")
        
        if not atacante_data or not defensor_data:
            raise Exception("Datos de jugadores no encontrados")
        
        # Obtener niveles de mejoras
        atacante_mejoras = {}
        defensor_mejoras = {}
        tipos_mejoras = ["barco", "cañones", "velas"]
        
        for tipo in tipos_mejoras:
            atacante_mejora = obtener_registro("mejoras", (atacante_id, tipo), "nivel")
            defensor_mejora = obtener_registro("mejoras", (defensor_id, tipo), "nivel")
            atacante_mejoras[tipo] = atacante_mejora[0] if atacante_mejora else 1
            defensor_mejoras[tipo] = defensor_mejora[0] if defensor_mejora else 1
        
        # Calcular puntaje con nuevo sistema ponderado
        def calcular_puntaje(mejoras):
            return (
                mejoras["barco"] * 5 +  # Barco vale 5 puntos por nivel
                mejoras["cañones"] * 3 +  # Cañones 3 puntos
                mejoras["velas"] * 1  # Velas 1 punto
            )
        
        puntaje_atacante = calcular_puntaje(atacante_mejoras)
        puntaje_defensor = calcular_puntaje(defensor_mejoras)
        
        # Calcular probabilidad de victoria (no es determinista)
        total_puntos = puntaje_atacante + puntaje_defensor
        prob_atacante = puntaje_atacante / total_puntos if total_puntos > 0 else 0.5
        prob_defensor = 1 - prob_atacante
        
        # Introducir un 10% de aleatoriedad para sorpresas
        factor_suerte = random.uniform(-0.1, 0.1)
        prob_atacante += factor_suerte
        prob_defensor -= factor_suerte
        
        # Determinar ganador
        ganador_id = atacante_id if random.random() < prob_atacante else defensor_id
        perdedor_id = defensor_id if ganador_id == atacante_id else atacante_id
        
        # Calcular daño basado en diferencia de niveles
        diferencia_niveles = abs(puntaje_atacante - puntaje_defensor)
        dano_base = 20 + (diferencia_niveles * 0.5)
        
        # Calcular botín basado en nivel de cañones y diferencia
        botin_base = 100 + (atacante_mejoras["cañones"] * 10 if ganador_id == atacante_id 
                          else defensor_mejoras["cañones"] * 10)
        
        # Aplicar bonificación por diferencia de niveles
        botin = int(botin_base * (1 + diferencia_niveles * 0.02))
        
        # Limitar botín al 20% de los barriles del perdedor
        barriles_perdedor = defensor_data[0] if ganador_id == atacante_id else atacante_data[0]
        botin_real = min(botin, max(0, int(barriles_perdedor * 0.2)))
        
        # 🔥 CAMBIO: Aplicar descuento del 10% al botín recibido
        botin_efectivo = int(botin_real * 0.9)  # El ganador recibe el 90%
        
        # Calcular prestigio ganado (más por vencer a oponente más fuerte)
        prestigio = 5 + int(diferencia_niveles * 0.5)
        
        # Aplicar resultados
        if ganador_id == atacante_id:
            # Atacante gana
            nuevo_barriles_atacante = atacante_data[0] + botin_efectivo
            nuevo_barriles_defensor = defensor_data[0] - botin_real
            nuevo_prestigio_atacante = atacante_data[1] + prestigio
            nuevo_prestigio_defensor = max(0, defensor_data[1] - int(prestigio/2))
            nuevo_hp_defensor = max(0, defensor_data[4] - dano_base)
            nuevas_victorias_atacante = atacante_data[2] + 1
            nuevas_derrotas_defensor = defensor_data[3] + 1
            
            # Actualizar atacante
            actualizar_registro("juego_pirata", atacante_id, {
                "barriles": nuevo_barriles_atacante,
                "prestigio": nuevo_prestigio_atacante,
                "victorias": nuevas_victorias_atacante,
                "ultimo_ataque": tm.time()
            })
            
            # Actualizar defensor
            actualizar_registro("juego_pirata", defensor_id, {
                "barriles": nuevo_barriles_defensor,
                "prestigio": nuevo_prestigio_defensor,
                "derrotas": nuevas_derrotas_defensor,
                "hp_barco": nuevo_hp_defensor
            })
            
        else:
            # Defensor gana
            nuevo_barriles_defensor = defensor_data[0] + botin_efectivo
            nuevo_barriles_atacante = atacante_data[0] - botin_real
            nuevo_prestigio_defensor = defensor_data[1] + prestigio
            nuevo_prestigio_atacante = max(0, atacante_data[1] - int(prestigio/2))
            nuevo_hp_atacante = max(0, atacante_data[4] - dano_base)
            nuevas_victorias_defensor = defensor_data[2] + 1
            nuevas_derrotas_atacante = atacante_data[3] + 1
            
            # Actualizar defensor
            actualizar_registro("juego_pirata", defensor_id, {
                "barriles": nuevo_barriles_defensor,
                "prestigio": nuevo_prestigio_defensor,
                "victorias": nuevas_victorias_defensor
            })
            
            # Actualizar atacante
            actualizar_registro("juego_pirata", atacante_id, {
                "barriles": nuevo_barriles_atacante,
                "prestigio": nuevo_prestigio_atacante,
                "derrotas": nuevas_derrotas_atacante,
                "hp_barco": nuevo_hp_atacante,
                "ultimo_ataque": tm.time()
            })
        
        # Verificar si algún barco fue destruido
        if ganador_id == atacante_id and nuevo_hp_defensor <= 0:
            await destruir_barco(defensor_id, context)
        elif ganador_id == defensor_id and nuevo_hp_atacante <= 0:
            await destruir_barco(atacante_id, context)
        
        return {
            'ganador': ganador_id,
            'botin': botin_efectivo,  # 🔥 Retorna el valor con descuento
            'prestigio': prestigio,
            'dano': dano_base,
            'prob_atacante': int(prob_atacante * 100),
            'prob_defensor': int(prob_defensor * 100)
        }
        
    except Exception as e:
        print(f"Error en resolver_combate: {str(e)}")
        raise
async def notificar_combate(context: CallbackContext, data: dict, atacante_id: str, defensor_id: str, resultado: dict):
    """Envía:
    - Mensajes motivacionales aleatorios al grupo público (GROUP_CHAT_ID)
    - Reporte detallado al grupo de registro (GROUP_REGISTRO)
    """
    atacante_nombre = data["usuarios"][atacante_id]["Nombre"]
    defensor_nombre = data["usuarios"][defensor_id]["Nombre"]
    atacante_data = data["juego_pirata"][atacante_id]
    defensor_data = data["juego_pirata"][defensor_id]
    ganador_id = resultado['ganador']

    # =============================================
    # [1] MENSAJE ALEATORIO PARA GRUPO PÚBLICO (GROUP_CHAT_ID)
    # =============================================
    mensajes_aleatorios = [
        # Cuando el atacante gana
        [
            f"⚔️ <b>¡Incursión exitosa!</b> {atacante_nombre} ha dominado a {defensor_nombre} en alta mar",
            f"🏴‍☠️ <b>¡Botín capturado!</b> {atacante_nombre} regresa victorioso tras enfrentar a {defensor_nombre}",
            f"💥 <b>¡Victoria pirata!</b> {atacante_nombre} ha dejado su marca en {defensor_nombre}",
            f"🌪️ <b>¡Combate épico!</b> {atacante_nombre} demostró su superioridad frente a {defensor_nombre}",
            f"🔥 <b>¡Saquear es ganar!</b> {atacante_nombre} ha humillado a {defensor_nombre}"
        ],
        # Cuando el defensor gana
        [
            f"🛡️ <b>¡Defensa legendaria!</b> {defensor_nombre} ha repelido a {atacante_nombre}",
            f"⚓ <b>¡Contraataque!</b> {defensor_nombre} ha vuelto las tornas contra {atacante_nombre}",
            f"🏆 <b>¡Victoria defensiva!</b> {defensor_nombre} protegió su botín de {atacante_nombre}",
            f"💪 <b>¡Revés inesperado!</b> {atacante_nombre} subestimó a {defensor_nombre}",
            f"🌊 <b>¡Derrota pirata!</b> {atacante_nombre} no pudo contra {defensor_nombre}"
        ]
    ]

    # Seleccionar mensaje aleatorio
    indice = 0 if ganador_id == atacante_id else 1
    mensaje_publico = random.choice(mensajes_aleatorios[indice]) + "\n\n" + "🏴‍☠️ <i>¡Anímate a desafiar otros capitanes!</i>"

    try:
        await context.bot.send_message(
            chat_id=REGISTRO_MINIJUEGOS,
            text=mensaje_publico,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error al enviar mensaje público: {str(e)}")

    # =============================================
    # [2] REPORTE DETALLADO PARA GRUPO REGISTRO (GROUP_REGISTRO)
    # =============================================
    ganador_nombre = atacante_nombre if ganador_id == atacante_id else defensor_nombre
    perdedor_nombre = defensor_nombre if ganador_id == atacante_id else atacante_nombre

    reporte_combate = (
        f"📜 <b>REPORTE DE COMBATE DETALLADO</b> 📜\n\n"
        f"⚔️ <b>Contendientes:</b>\n"
        f"• Atacante: {atacante_nombre} (Nvl {atacante_data['mejoras']['barco']['nivel']})\n"
        f"• Defensor: {defensor_nombre} (Nvl {defensor_data['mejoras']['barco']['nivel']})\n\n"
        f"🏆 <b>Ganador:</b> {ganador_nombre}\n"
        f"💀 <b>Perdedor:</b> {perdedor_nombre}\n\n"
        f"📊 <b>Estadísticas:</b>\n"
        f"• Barriles robados: {resultado['botin']}\n"
        f"• Prestigio ganado: {resultado['prestigio']}\n"
        f"• Daño infligido: {resultado['dano']}\n\n"
        f"⚓ <b>Estado final:</b>\n"
        f"• {atacante_nombre}: {atacante_data['hp_barco']}/100 HP\n"
        f"• {defensor_nombre}: {defensor_data['hp_barco']}/100 HP\n\n"
        f"⏱️ <b>Hora del combate:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        await context.bot.send_message(
            chat_id=REGISTRO_MINIJUEGOS,
            text=reporte_combate,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error al enviar reporte de registro: {str(e)}")

# ------------ [4] FUNCIONES DE GESTIÓN PVP ------------


        
async def confirmar_escudo_basico(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirmar Compra", callback_data='comprar_escudo_basico')],
        [InlineKeyboardButton("❌ Cancelar", callback_data='mercado_pirata')]
    ]
    
    await query.edit_message_text(
        "<pre>🛡️ CONFIRMAR COMPRA DE ESCUDO</pre>\n\n"
        "Estás a punto de comprar un <b>Escudo Básico</b> por <b>200 barriles</b>.\n\n"
        "🔒 <b>Protección:</b> 2 horas contra ataques PvP\n\n"
        "¿Confirmas la compra?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def confirmar_escudo_premium(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirmar Compra", callback_data='comprar_escudo_premium')],
        [InlineKeyboardButton("❌ Cancelar", callback_data='mercado_pirata')]
    ]
    
    await query.edit_message_text(
        "<pre>🛡️ CONFIRMAR COMPRA DE ESCUDO</pre>\n\n"
        "Estás a punto de comprar un <b>Escudo Premium</b> por <b>10 CUP</b>.\n\n"
        "🔒 <b>Protección:</b> 4 horas contra ataques PvP\n\n"
        "¿Confirmas la compra?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def comprar_escudo_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    tipo_escudo = query.data.replace('comprar_escudo_', '')  # 'basico' o 'premium'
    await comprar_escudo(update, context, tipo_escudo)
    
                    
async def mercado_pirata(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🛒 Comprar Barriles", callback_data='comprar_barriles'),
            InlineKeyboardButton("🤑 Vender Barriles", callback_data='vender_barriles')
        ],
        [
            InlineKeyboardButton("🛡️ Escudo Básico (200🛢️)", callback_data='confirmar_escudo_basico'),
            InlineKeyboardButton("🛡️ Escudo Premium (10💲)", callback_data='confirmar_escudo_premium')
        ],
        [InlineKeyboardButton("🔙 Volver", callback_data='juego_pirata')]
    ]
    
    await query.edit_message_text(
        "<pre>🏪 MERCADO PIRATA</pre>\n\n"
        "💰 <b>Compra y vende recursos:</b>\n\n"
        "▫️ <b>Barriles:</b> Compra/Vende con CUP\n"
        "▫️ <b>Escudos:</b> Protección contra ataques\n\n"
        "<i>Selecciona una opción para continuar:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard))        



EVENTOS_PIRATA = [
    {
        "nombre": "Tormenta tropical",
        "efecto": "reducir_30",
        "duracion": 3600,
        "mensaje": "🌪️ ¡Una tormenta reduce tus ganancias en 30% por 1 hora!",
        "probabilidad": 0.15
    },
    {
        "nombre": "Vientos favorables",
        "efecto": "aumentar_30",
        "duracion": 3600,
        "mensaje": "🍃 ¡Vientos favorables aumentan tus ganancias en 30% por 1 hora!",
        "probabilidad": 0.15
    },
    {
        "nombre": "Ataque pirata",
        "efecto": "reducir_50",
        "duracion": 1800,
        "mensaje": "🏴‍☠️ ¡Otros piratas te atacaron! Ganancias reducidas 50% por 30 minutos.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Botín encontrado",
        "efecto": "aumentar_50",
        "duracion": 2700,
        "mensaje": "💰 ¡Encontraste un botín abandonado! Ganancias +50% por 45 minutos.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Marea baja",
        "efecto": "reducir_20",
        "duracion": 5400,
        "mensaje": "🌊 Marea baja ralentiza tus operaciones. Ganancias -20% por 1.5 horas.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Tripulación unida",
        "efecto": "bonus_piratas",
        "duracion": 3600,
        "mensaje": "👥 ¡Tu tripulación trabaja en equipo! Ganas +0.1 barriles por cada pirata.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Sequía extrema",
        "efecto": "reducir_10",
        "duracion": 7200,
        "mensaje": "☀️ ¡Sequía reduce la producción de ron! Ganancias -10% por 2 horas.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Capitán ebrio",
        "efecto": "reducir_5",
        "duracion": 3600,
        "mensaje": "🍺 ¡El capitán bebió demasiado! Ganancias -5% por 1 hora.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Abundancia",
        "efecto": "aumentar_7",
        "duracion": 3600,
        "mensaje": "🎉 ¡Temporada de abundancia! Ganancias +7% por 1 hora.",
        "probabilidad": 0.1
    },
    {
        "nombre": "Pescadores",
        "efecto": "aumentar_8",
        "duracion": 3600,
        "mensaje": "🎣 ¡Pescadores aliados comparten su botín! Ganancias +8% por 1 hora.",
        "probabilidad": 0.1
    }
]






def init_tareas_pirata(app: Application):
    """Inicializa las tareas programadas para el juego pirata"""
    if not app.job_queue:
        print("⚠️ JobQueue no disponible - No se configuraron tareas pirata")
        return
    
    
    # Eventos aleatorios cada 4-8 horas (versión sin jitter)
    # Calculamos un intervalo aleatorio entre 4 y 8 horas (14400 a 28800 segundos)
    intervalo_eventos = random.randint(14400, 28800)
    
    app.job_queue.run_repeating(
        aplicar_evento_aleatorio,
        interval=intervalo_eventos,
        first=60
    )
    
    
    

# Funciones auxiliares para reclamar_ganancias
def aplicar_efecto_evento(ganancia, evento, user_data):
    """Aplica el efecto del evento a las ganancias"""
    efecto = evento["efecto"]
    
    if efecto == "reducir_30":
        return ganancia * 0.7
    elif efecto == "aumentar_30":
        return ganancia * 1.3
    elif efecto == "reducir_50":
        return ganancia * 0.5
    elif efecto == "aumentar_50":
        return ganancia * 1.5
    elif efecto == "reducir_20":
        return ganancia * 0.8
    elif efecto == "bonus_piratas":
        return ganancia + (user_data.get("piratas", 0) * 0.1)
    elif efecto == "reducir_10":
        return ganancia * 0.9
    elif efecto == "reducir_5":
        return ganancia * 0.95
    elif efecto == "aumentar_7":
        return ganancia * 1.07
    elif efecto == "aumentar_8":
        return ganancia * 1.08
    else:
        return ganancia

def calcular_impuestos(ganancia, user_data):
    """Calcula impuestos basados en nivel de mejoras"""
    nivel_total = sum(m["nivel"] for m in user_data["mejoras"].values())
    tasa = min(0.20, 0.05 + (nivel_total * 0.005))
    impuesto = int(ganancia * tasa)
    return impuesto, tasa

async def mostrar_sin_ganancias(query):
    await query.edit_message_text(
        "🔄 <b>No hay ganancias disponibles</b>\n\n"
        "💡 Mejora tu barco o contrata más piratas.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⛵ Mejorar Barco", callback_data="mejorar_barco")],
            [InlineKeyboardButton("🏴‍☠ Contratar Piratas", callback_data="comprar_piratas")],
            [InlineKeyboardButton("🔙 Volver", callback_data="juego_pirata")]
        ])
    )

async def mostrar_ganancias_reclamadas(query, bruta, neta, impuesto, tasa, total, evento_info):
    await query.edit_message_text(
        f"<b>💰 ¡Ganancias Reclamadas!</b>\n\n"
        f"▫️ <b>Ganancia bruta:</b> {bruta}🛢️\n"
        f"▫️ <b>Impuesto ({tasa*100:.1f}%):</b> -{impuesto}🛢️\n"
        f"▫️ <b>Ganancia neta:</b> +{neta}🛢️{evento_info}\n\n"
        f"💼 <b>Total barriles:</b> {total}🛢️",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Ver Barco", callback_data="ver_balance")],
            [InlineKeyboardButton("🌊 Eventos Activos", callback_data="ver_eventos")],
            [InlineKeyboardButton("🔙 Menú Pirata", callback_data="juego_pirata")]
        ])
    )

async def mostrar_tiempo_restante(query, tiempo_restante, user_data):
    """Muestra el tiempo restante para reclamar ganancias con todos los detalles"""
    try:
        # Preparar información adicional
        info_extra = []
        
        # Verificar evento activo
        if "evento_actual" in user_data and user_data["evento_actual"]["expira"] > tm.time():
            evento = user_data["evento_actual"]
            tiempo_restante_evento = evento["expira"] - tm.time()
            
            info_extra.append(
                f"\n\n🎭 <b>Evento activo:</b> {evento['nombre']}\n"
                f"⏳ Termina en: {format_time(tiempo_restante_evento)}"
            )
        
        
        
        # Verificar estado del barco
        if user_data.get("hp_barco", 100) < 100:
            info_extra.append(
                f"\n⚓ <b>Barco dañado:</b> {user_data['hp_barco']}/100 HP\n"
                f"🛠️ Repáralo para mejor rendimiento"
            )
        
        # Crear mensaje final
        mensaje = (
            f"⏳ <b>¡Aún no, Capitán!</b>\n\n"
            f"Tus piratas necesitan más tiempo para reunir el botín.\n\n"
            f"🕒 <b>Tiempo restante:</b> {format_time(tiempo_restante)}"
            f"{''.join(info_extra)}"
        )
        
        # Crear teclado
        teclado = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="reclamar_ganancias")],
            [InlineKeyboardButton("🌊 Evento Activo", callback_data="ver_eventos")],
            [InlineKeyboardButton("📊 Ver Barco", callback_data="ver_balance")]
        ]
        
        # Añadir botones adicionales si hay problemas
        if user_data.get("ganancias_totales", 1.0) < 1.0:
            teclado.insert(0, [InlineKeyboardButton("💸 Pagar Mantenimiento", callback_data="pagar_mantenimiento")])
        
        if user_data.get("hp_barco", 100) < 100:
            teclado.insert(0, [InlineKeyboardButton("🛠️ Reparar Barco", callback_data="reparar_barco")])
        
        teclado.append([InlineKeyboardButton("🔙 Menú Pirata", callback_data="juego_pirata")])
        
        await query.edit_message_text(
            text=mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(teclado)
        )
        
    except Exception as e:
        print(f"Error en mostrar_tiempo_restante: {e}")
        await query.edit_message_text(
            text="⏳ Tus piratas están trabajando... Vuelve a intentarlo pronto.",
            parse_mode="HTML"
        )
        
        
async def aplicar_evento_aleatorio(context: CallbackContext):
    """Aplica un evento aleatorio a todos los jugadores activos usando las funciones de acceso a DB"""
    try:
        # Seleccionar un evento aleatorio basado en probabilidades
        evento = None
        r = random.random()
        acumulado = 0.0
        
        for e in EVENTOS_PIRATA:
            acumulado += e["probabilidad"]
            if r <= acumulado:
                evento = e
                break
        
        if not evento:
            print("No se seleccionó ningún evento esta vez")
            return

        print(f"Evento seleccionado: {evento['nombre']}")

        # Obtener todos los usuarios con juego pirata activo usando la función segura
        try:
            # Usar ejecutar_consulta_segura directamente para obtener IDs de usuarios activos
            consulta = "SELECT id FROM juego_pirata WHERE piratas > 0"
            resultados = ejecutar_consulta_segura(consulta, obtener_resultados=True)
            usuarios_activos = [row[0] for row in resultados] if resultados else []
        except Exception as e:
            print(f"Error al obtener usuarios activos: {e}")
            usuarios_activos = []

        total_jugadores = len(usuarios_activos)
        usuarios_afectados = 0
        
        if total_jugadores == 0:
            print("No hay jugadores activos para aplicar el evento")
            return

        # Preparar datos del evento
        evento_guardar = {
            "nombre": evento["nombre"],
            "efecto": evento["efecto"],
            "expira": tm.time() + evento["duracion"],
            "mensaje": evento["mensaje"]
        }

        # Aplicar evento a cada usuario activo usando actualizar_registro
        for user_id in usuarios_activos:
            try:
                # Usar actualizar_registro para insertar/actualizar el evento
                exito = actualizar_registro("eventos", user_id, evento_guardar)
                if exito:
                    usuarios_afectados += 1
                else:
                    print(f"Error al aplicar evento al usuario {user_id}")
                    
            except Exception as e:
                print(f"Excepción al aplicar evento al usuario {user_id}: {e}")

        print(f"Total jugadores activos: {total_jugadores}, Afectados: {usuarios_afectados}")

        if usuarios_afectados > 0:
            # Notificación al grupo
            try:
                await context.bot.send_message(
                    chat_id=REGISTRO_MINIJUEGOS,
                    text=f"⚡ ¡NUEVO EVENTO PIRATA! ⚡\n\n"
                         f"🏴‍☠️ <b>{evento['nombre']}</b>\n"
                         f"📝 {evento['mensaje']}\n\n"
                         f"⏳ Duración: {format_time(evento['duracion'])}\n"
                         f"👥 Jugadores afectados: {usuarios_afectados}",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error al notificar evento: {e}")

    except Exception as e:
        print(f"Error crítico en aplicar_evento_aleatorio: {e}")
        # Informar del error al administrador
        try:
            await context.bot.send_message(
                chat_id=REGISTRO_MINIJUEGOS,
                text=f"❌ ERROR EN EVENTO PIRATA:\n{str(e)}",
                parse_mode="HTML"
            )
        except:
            pass
        
async def reclamar_ganancias(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    try:
        user_id = str(query.from_user.id)
        
        # Obtener datos del usuario - SOLO las columnas necesarias
        juego_data = obtener_registro("juego_pirata", user_id, 
                                    "tiempo_ultimo_reclamo, barriles, ganancias_totales, tiempo_para_ganar, piratas")
        
        if not juego_data:
            await query.edit_message_text("❌ No estás registrado en el juego pirata.", parse_mode="HTML")
            return

        # Desempaquetado correcto
        tiempo_ultimo_reclamo = juego_data[0]
        barriles = juego_data[1]
        ganancias_totales = juego_data[2]  # Esta es la ganancia por hora
        tiempo_para_ganar = juego_data[3]
        piratas = juego_data[4]

        # Verificar si hay ganancias disponibles
        if ganancias_totales <= 0 or piratas <= 0:
            await mostrar_sin_ganancias(query)
            return

        # Calcular tiempo y ganancias
        tiempo_actual = tm.time()
        tiempo_transcurrido = tiempo_actual - tiempo_ultimo_reclamo
        
        if tiempo_transcurrido >= tiempo_para_ganar:
            # Calcular ganancia base (ganancia por hora * horas transcurridas)
            horas_transcurridas = tiempo_transcurrido / 3600
            ganancia_base = ganancias_totales
            
            # Aplicar efecto de evento si existe
            evento_info = ""
            evento_data = obtener_registro("eventos", user_id, "nombre, efecto, expira")
            if evento_data:
                nombre_evento = evento_data[0]
                efecto = evento_data[1]
                expira = evento_data[2]
                if expira > tiempo_actual:
                    # Crear diccionario para el evento
                    evento_dict = {
                        "nombre": nombre_evento,
                        "efecto": efecto,
                        "expira": expira
                    }
                    ganancia_base = aplicar_efecto_evento(ganancia_base, evento_dict, {
                        "piratas": piratas,
                        "ganancias_totales": ganancias_totales
                    })
                    evento_info = f"\n🎭 Evento: {nombre_evento}"
            
            # Calcular impuestos (necesitas obtener los niveles de mejoras reales)
            # Primero obtener los niveles de mejoras
            niveles_mejoras = {}
            for tipo in ["barco", "cañones", "velas"]:
                mejora_data = obtener_registro("mejoras", (user_id, tipo), "nivel")
                niveles_mejoras[tipo] = mejora_data[0] if mejora_data else 1
            
            impuesto, tasa_impuesto = calcular_impuestos(ganancia_base, {"mejoras": {
                "barco": {"nivel": niveles_mejoras.get("barco", 1)},
                "cañones": {"nivel": niveles_mejoras.get("cañones", 1)},
                "velas": {"nivel": niveles_mejoras.get("velas", 1)}
            }})
            
            ganancia_neta = int(ganancia_base - impuesto)
            
            # Actualizar datos en la base de datos
            exito = actualizar_registro("juego_pirata", user_id, {
                "barriles": barriles + ganancia_neta,
                "tiempo_ultimo_reclamo": tiempo_actual
            })
            
            if not exito:
                await query.edit_message_text("❌ Error al actualizar ganancias")
                return
            
            # Mostrar resultados
            await mostrar_ganancias_reclamadas(
                query,
                int(ganancia_base),
                ganancia_neta,
                int(impuesto),
                tasa_impuesto,
                barriles + ganancia_neta,
                evento_info
            )
        else:
            await mostrar_tiempo_restante(
                query,
                tiempo_para_ganar - tiempo_transcurrido,
                {"hp_barco": 100}  # Valor por defecto
            )

    except Exception as e:
        print(f"Error en reclamar_ganancias: {e}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            "⚡ Error al reclamar ganancias. Intenta nuevamente.",
            parse_mode="HTML"
        )
async def mostrar_eventos_activos(update: Update, context: CallbackContext):
    """Muestra todos los eventos disponibles y resalta el activo"""
    query = update.callback_query
    await query.answer()

    try:
        user_id = str(query.from_user.id)
        
        # Obtener evento activo del usuario
        evento_data = obtener_registro("eventos", user_id, "nombre, efecto, expira, mensaje")
        
        # Construir mensaje de eventos
        mensaje = "<b>🌊 EVENTOS PIRATA DISPONIBLES</b>\n\n"
        
        # Verificar evento activo
        evento_activo = None
        tiempo_restante_evento = 0
        
        if evento_data and len(evento_data) >= 4:
            nombre, efecto, expira, mensaje_evento = evento_data
            if expira > tm.time():
                evento_activo = {
                    "nombre": nombre,
                    "efecto": efecto,
                    "expira": expira,
                    "mensaje": mensaje_evento
                }
                tiempo_restante_evento = expira - tm.time()
        
        # Listar todos los eventos
        for evento in EVENTOS_PIRATA:
            emoji = "⚡" if evento_activo and evento["nombre"] == evento_activo["nombre"] else "▫️"
            
            mensaje += (
                f"{emoji} <b>{evento['nombre']}</b>\n"
                f"┣ <i>Efecto:</i> {obtener_descripcion_efecto(evento['efecto'])}\n"
                f"┣ <i>Duración:</i> {format_time(evento['duracion'])}\n"
                f"┗ <i>Probabilidad:</i> {evento['probabilidad']*100}%\n\n"
            )
        
        # Añadir información del evento activo si existe
        if evento_activo:
            mensaje += (
                f"\n🎯 <b>EVENTO ACTUALMENTE ACTIVO</b>\n"
                f"┏ <b>{evento_activo['nombre']}</b>\n"
                f"┣ <i>Efecto aplicado:</i> {obtener_descripcion_efecto(evento_activo['efecto'])}\n"
                f"┣ <i>Tiempo restante:</i> {format_time(tiempo_restante_evento)}\n"
                f"┗ <i>Mensaje:</i> {evento_activo['mensaje']}\n"
            )
        else:
            mensaje += "\nℹ️ No hay ningún evento activo actualmente."
        
        # Crear teclado
        keyboard = [
            [InlineKeyboardButton("📊 Ver Barco", callback_data="ver_balance")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="juego_pirata")]
        ]
        
        await query.edit_message_text(
            text=mensaje,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        print(f"Error en mostrar_eventos_activos: {e}")
        await query.edit_message_text(
            text="⚠️ Error al cargar los eventos. Intenta nuevamente.",
            parse_mode="HTML"
        )        
        
def obtener_descripcion_efecto(codigo_efecto):
    """Devuelve una descripción legible del efecto"""
    efectos = {
        "reducir_30": "Reduce ganancias en 30%",
        "aumentar_30": "Aumenta ganancias en 30%",
        "reducir_50": "Reduce ganancias en 50%",
        "aumentar_50": "Aumenta ganancias en 50%",
        "reducir_20": "Reduce ganancias en 20%",
        "bonus_piratas": "Bonus de +0.1 barriles por pirata",
        "reducir_10": "Reduce ganancias en 10%",
        "reducir_5": "Reduce ganancias en 5%",
        "aumentar_7": "Aumenta ganancias en 7%",
        "aumentar_8": "Aumenta ganancias en 8%"
    }
    return efectos.get(codigo_efecto, "Efecto desconocido")    
    
        
async def top_pirata(update: Update, context: CallbackContext):
    """Muestra el top de jugadores y distribuye recompensas semanales al top 10"""
    try:
        # Verificar si el comando lo ejecuta un administrador
        if str(update.effective_user.id) != "7031172659":  # ID del admin
            await update.message.reply_text("❌ Comando restringido a administradores.")
            return

        # Obtener y ordenar jugadores por prestigio desde la base de datos
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Consulta para obtener el top de jugadores
        c.execute("""
            SELECT u.id, u.Nombre, j.prestigio, j.victorias, j.barriles,
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'barco') as nivel_barco,
                   j.ganancias_totales
            FROM usuarios u
            JOIN juego_pirata j ON u.id = j.id
            WHERE j.prestigio > 0
            ORDER BY j.prestigio DESC
            LIMIT 10
        """)
        
        jugadores = []
        for row in c.fetchall():
            user_id, nombre, prestigio, victorias, barriles, nivel_barco, ganancias_totales = row
            jugadores.append({
                "id": user_id,
                "nombre": nombre or "Pirata",
                "prestigio": prestigio,
                "victorias": victorias,
                "nivel_barco": nivel_barco or 0,
                "ganancias": ganancias_totales or 0,
                "barriles_actuales": barriles or 0
            })
        
        conn.close()

        # Recompensas para top 10 (total 10,000 barriles)
        recompensas = [3000, 2000, 1500, 1000, 800, 700, 500, 300, 200, 200]
        
        # Distribuir premios y preparar notificaciones
        mensaje_global = "🏆 <b>TOP 10 PIRATAS - RECOMPENSAS SEMANALES</b>\n\n"
        notificaciones = []

        for i in range(min(10, len(jugadores))):
            jugador = jugadores[i]
            premio = recompensas[i]
            
            # Obtener barriles actuales para actualizar
            barriles_data = obtener_registro("juego_pirata", jugador["id"], "barriles")
            if barriles_data:
                nuevos_barriles = barriles_data[0] + premio
                # Asignar premio
                exito = actualizar_registro("juego_pirata", jugador["id"], {
                    "barriles": nuevos_barriles
                })
                
                if exito:
                    # Mensaje para el grupo
                    mensaje_global += (
                        f"{i+1}º: {jugador['nombre']} - "
                        f"🏆{jugador['prestigio']} | "
                        f"+{premio}🛢️\n"
                    )
                    
                    # Mensaje personalizado para cada ganador
                    notificaciones.append({
                        "chat_id": jugador["id"],
                        "text": (
                            f"🎉 <b>¡FELICIDADES, CAPITÁN!</b> 🎉\n\n"
                            f"Has quedado en el <b>top {i+1}</b> esta semana:\n"
                            f"🏆 <b>Prestigio:</b> {jugador['prestigio']}\n"
                            f"💰 <b>Recompensa:</b> +{premio} barriles\n\n"
                            f"¡Sigue saqueando para mantener tu posición!\n"
                            f"🔹 <i>Barriles totales ahora:</i> {nuevos_barriles}"
                        ),
                        "reply_markup": InlineKeyboardMarkup([
                            [InlineKeyboardButton("⚓ Ver Barco", callback_data="ver_balance")],
                            [InlineKeyboardButton("🏆 Ranking", callback_data="ranking_pvp")]
                        ])
                    })

        # Enviar mensaje al grupo
        mensaje_global += "\n💰 <b>Total distribuido:</b> 10,000 barriles\n"
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=mensaje_global,
            parse_mode="HTML"
        )
        
        # Notificar individualmente a los ganadores
        for notif in notificaciones:
            try:
                await context.bot.send_message(
                    chat_id=notif["chat_id"],
                    text=notif["text"],
                    parse_mode="HTML",
                    reply_markup=notif["reply_markup"]
                )
            except Exception as e:
                print(f"Error al notificar a {notif['chat_id']}: {e}")

        # Confirmación al admin
        await update.message.reply_text(
            "✅ Recompensas distribuidas y notificaciones enviadas.",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error en top_pirata: {e}")
        await update.message.reply_text(
            "⚡ Error al procesar el top. Verifica los logs.",
            parse_mode="HTML"
        )