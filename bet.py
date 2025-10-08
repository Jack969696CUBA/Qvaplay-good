import logging
import httpx
from typing import Optional
from typing import Union
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update, CallbackQuery
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext, ConversationHandler, ContextTypes
from telegram import ChatMember
import random
import string
from collections import defaultdict
import uuid
from functools import wraps  
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
import aiofiles
import requests
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
import math
import aiohttp
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler
import hashlib  
from telegram.error import BadRequest
from necesario import hacer_copia_seguridad, hacer_copia_seguridad_apuestas, marca_tiempo, lock_apuestas, has_lock,  guardar_usuarios_bloqueados, cargar_usuarios_bloqueados, verificar_bloqueo, guardar_apuesta_en_db, insertar_registro, ejecutar_consulta_segura, obtener_registro, actualizar_registro, obtener_apuestas_usuario, obtener_todas_las_apuestas, obtener_todos_los_resultados, obtener_apuestas_por_evento



lock = asyncio.Lock()
CANAL_TICKET = "-1002309255787"
GROUP_REGISTRO = -1002261941863
GROUP_CHAT_ADMIN = -1002492508397
ADMIN_IDS = ["5266566202", "7031172659"]
REQUIRED_CHANNEL_ID = "-1002128871685"

logging.basicConfig(level=logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
lock = asyncio.Lock()

futbol_cache = {
    "eventos": {},  # Para mercados (cuotas) PREMATCH: {"mercados_12345": {"data": [...], "timestamp": 123456}}
    "ligas": {},    # Para listados de eventos: {"liga_123": {"data": [...], "timestamp": 123456}}
    "last_updated": None
}

CACHE_TTLP = 900  # 5 minutos para PREMATCH

# Tiempo de vida del caché en segundos (1 segundo)
CACHE_TTL = 3


DB_FILE = "user_data.db"
CUBA_TZ = pytz.timezone("America/Havana")
# Configuración de la API (usando tus constantes originales)
API_FUTBOL_BASE_URL = "https://v3.football.api-sports.io"
API_FUTBOL_KEY = "89957a4709f62db07ef73d1d1977103c"
API_FUTBOL_HEADERS = {
    "x-apisports-key": API_FUTBOL_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}
# Variables globales

api_index = 0  # Índice de la API en uso
api_uso = None  # API en uso actualmente
creditos_api = {}  # Créditos restantes por API
# Inicialización de variables globales (debe estar en tu código principal)
api_index = 0
api_uso = None
creditos_api = {}


lock = asyncio.Lock()

#agregar Emois en liga
banderas = {
    "España": "🇪🇸",
    "México": "🇲🇽",
    "Argentina": "🇦🇷",
    "Brasil": "🇧🇷",
    "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Italia": "🇮🇹",
    "Francia": "🇫🇷",
    "Alemania": "🇩🇪",
    "Portugal": "🇵🇹",
    "Países Bajos": "🇳🇱",
    "Bélgica": "🇧🇪",
    "Estados Unidos": "🇺🇸",
    "Canadá": "🇨🇦",
    "Australia": "🇦🇺",
    "Japón": "🇯🇵",
    "Corea del Sur": "🇰🇷",
    "Escocia": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Irlanda": "🇮🇪",
    "Turquía": "🇹🇷",
    "China": "🇨🇳",
    "Austria": "🇦🇹",
    "Grecia": "🇬🇷",
    "Chile": "🇨🇱",
    "Polonia": "🇵🇱",
    "Dinamarca": "🇩🇰",
    "Noruega": "🇳🇴",
    "Suecia": "🇸🇪",
    "Sweden": "🇸🇪",
    "Suiza": "🇨🇭",
    "Escocia": "🏴󠁧󠁢󠁳󠁣󠁴󠁿"
}

paises = {
    "España": ["Spain", "España", "Spanish"],
    "México": ["Mexico", "MX", "México", "Mexican"],
    "Suiza": ["Swiss"],
    "Suecia": ["Sweden"],
    "Noruega": ["Norway"],
    "Argentina": ["Argentina", "Argentine"],
    "Brasil": ["Brazil", "Brasil", "Brazilian"],
    "Inglaterra": ["England", "Inglaterra", "English"],
    "Italia": ["Italy", "Italia", "Italian"],
    "Francia": ["France", "Francia", "French"],
    "Alemania": ["Germany", "Alemania", "German"],
    "Portugal": ["Portugal", "Portuguese"],
    "Países Bajos": ["Netherlands", "Países Bajos", "Holland", "Dutch"],
    "Bélgica": ["Belgium", "Bélgica", "Belgian"],
    "Estados Unidos": ["United States", "USA", "EEUU", "American"],
    "Canadá": ["Canada", "Canadá", "Canadian"],
    "Australia": ["Australia", "Aussie"],
    "Japón": ["Japan", "Japón", "Japanese"],
    "China": ["China"],
    "Corea del Sur": ["South Korea", "Corea del Sur", "Korean"],
    "Escocia": ["Scotland", "Escocia", "Scottish"],
    "Irlanda": ["Ireland", "Irlanda", "Irish"],
    "Turquía": ["Turkey", "Turquía", "Turkish"],
    "Austria": ["Austrian"],
    "Chile": ["Chile"],
    "Dinamarca": ["Denmark", "Dinamarca"],
    "Polonia": ["Polonia", "Poland"],
    "Grecia": ["Greece", "Grecia", "Greek"]
}
#cambiar nombre botones
deportes_personalizados = {
    'soccer': ('FUTBOL⚽', '⚽'),
    'basketball': ('Baloncesto🤾', '🏀'),
    'tennis': ('Tenis', '🎾'),
    'americanfootball': ('Fútbol Americano🏈', '🏈'),
    'baseball': ('Béisbol⚾', '⚾'),
    'hockey': ('Hockey🏒', '🏒'),
    'icehockey': ('Hockey🏒', '🏒'),
    'boxing': ('Boxeo🥊', '🥊'),
    'golf': ('Golf🏑', '⛳'),
    'lacrosse': ('Lacrosse🥍', '🥍'),
    'mixed_martial_arts': ('Artes Marciales Mixtas', '🥋'),
    'rugbyleague': ('Rugbi League', '🏉'),
    'rugbyunion': ('Rugbi Union', '🏉'),
    'aussierules': ('Aussie Rules', '🥅 '),
    'cricket': ('Cricket🏏', '🏏'),
}
# Definir tiempos de duración por deporte (en minutos)
TIEMPOS_DURACION = {
    'FUTBOL⚽': 107,  # Fútbol
    'Baloncesto🤾': 135,  # Baloncesto
    'Tenis': 120,  # Tenis (aproximado)
    'Fútbol Americano🏈': 60,  # Fútbol Americano
    'Béisbol⚾': 100,  # Béisbol
    'Hockey🏒': 60,  # Hockey
    'Boxeo🥊': 60,  # Boxeo
    'Golf🏑': 240,  # Golf
    'Lacrosse🥍': 60,  # Lacrosse
    'Artes Marciales Mixtas': 60,  # Artes Marciales Mixtas
    'Rugbi League': 80,  # Rugby League
    'Rugbi Union': 80,  # Rugby Union
    'Aussie Rules': 80,  # Aussie Rules
    'Cricket🏏': 360,  # Cricket
}


ESTADOS_FINALIZADOS = [
    # Estados regulares
    'P', 'ET', 'AET', 'PEN', 'BT', 'SUSP', 'ABD', 'WO',
    # Estados en inglés
    'FINISHED', 'COMPLETED', 'ENDED', 'POSTPONED', 'CANCELLED', 'AWARDED',
    'MATCH FINISHED', 'MATCH_ENDED', 'GAME_OVER', 'FULL_TIME', 'HALF_TIME',
    'EXTRA_TIME', 'PENALTIES', 'ABANDONED', 'SUSPENDED', 'WALKOVER',
    # Estados en español
    'FINALIZADO', 'TERMINADO', 'COMPLETADO', 'APLAZADO', 'CANCELADO',
    'SUSPENDIDO', 'ABANDONADO', 'TIEMPO_COMPLETO',
    'TIEMPO_EXTRA', 'PENALES', 'PRORROGA',
    # Variaciones de texto
    'Extra Time', 'Penalty Shootout', 'After Extra Time', 'Break Time', 'Match Finished', 'Full Time', 'Penalty Series',
    # Variaciones en minúsculas
    'ft', 'p', 'et', 'aet', 'pen', 'bt', 'susp', 'abd', 'wo',
    'finished', 'completed', 'match finished', 'extra time',
    # Estados compuestos
    'FINISHED_AFTER_EXTRA_TIME', 'FINISHED_AFTER_PENALTIES',
    'AWARDED_AFTER_WALKOVER'
]
CONFIG_MERCADOS = {
    # Mercados principales (para todos los deportes)
    "Match Winner": { "emoji": "🏆", "nombre": "Ganador del Partido", "deporte": "soccer", "categoria": "Principales" },
    "draw_no_bet": { "emoji": "🔄", "nombre": "Empate no Bet", "deporte": "soccer", "categoria": "Principales" },
    "h2h": { "emoji": "🏆", "nombre": "Ganador del Partido", "deporte": "todos", "categoria": "Principales" },

    # Mercados de fútbol específicos
    "Both Teams Score": {
        "emoji": "⚽",
        "nombre": "Ambos Equipos Marcan",
        "deporte": "soccer",
        "categoria": "Principales"
    },
    "Exact Score": {
        "emoji": "🔢",
        "nombre": "Marcador Exacto",
        "deporte": "soccer",
        "categoria": "Principales"
    },
    "Double Chance": {
        "emoji": "🍻",
        "nombre": "Doble oportunidad",
        "deporte": "soccer",
        "categoria": "Principales"
    },
    
    "Team To Score First": {
        "emoji": "🥅",
        "nombre": "Equipo Marcará Primer Gol",
        "deporte": "soccer",
        "categoria": "Principales"
    },
    
    
  
    "Goals Over/Under": {
        "emoji": "🔢",
        "nombre": "Total Anotaciones",
        "deporte": "soccer",
        "categoria": "Principales"
    },

    # Mercados alternativos (para futbol)
    
    
    "Goal Line": {
        "emoji": "🔢",
        "nombre": "Total Anotaciones",
        "deporte": "soccer",
        "categoria": "Mas opciones"
    },

    # Mercados por tiempos (fútbol)
    "First Half Winner": {
        "emoji": "⏱️",
        "nombre": "Ganador 1ra Mitad",
        "deporte": "soccer",
        "categoria": "Por Tiempos"
    },
    "Second Half Winner": {
        "emoji": "⏱️",
        "nombre": "Ganador 2da Mitad",
        "deporte": "soccer",
        "categoria": "Por Tiempos"
    },
    "Goals Over/Under First Half": {
        "emoji": "📊",
        "nombre": "Total 1ra Mitad",
        "deporte": "soccer",
        "categoria": "Por Tiempos"
    },
    
    """Total Corners": {
        "emoji": "🌽",
        "nombre": "Total Córners",
        "deporte": "soccer",
        "categoria": "Principales"
    },"""

    # Mercados de jugadores (fútbol)
    "Anytime Goal Scorer": {
        "emoji": "👟",
        "nombre": "Anotador en el Partido",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "First Goal Scorer": {
        "emoji": "🥇",
        "nombre": "Primer Anotador",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "Last Goal Scorer": {
        "emoji": "🥉",
        "nombre": "Último Anotador",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "player_to_receive_card": {
        "emoji": "🟨",
        "nombre": "Jugador Amonestado",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "RCARD": {
        "emoji": "🟥",
        "nombre": "Jugador Expulsado",
        "deporte": "soccer",
        "categoria": "Especiales"
    
    },
    "Cards European": {
        "emoji": "🔄",
        "nombre": "Hándicap de Tarjetas",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "Cards Over/Under": {
        "emoji": "🔢",
        "nombre": "Total de Tarjetas",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    
    "Total ShotOnGoal": {
        "emoji": "🎯",
        "nombre": "Total Disparos a Puerta",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    
    #LIVE
    "Fulltime Result": {
        "emoji": "🏆",
        "nombre": "Ganador del Partido",
        "deporte": "soccer",
        "categoria": "Principales"
    },   
    
    "1x2 (1st Half)": {
    "emoji": "⏱️",
    "nombre": "Ganador 1ra Mitad",
    "deporte": "soccer",
    "categoria": "Por Tiempos"
    },
    "To Win 2nd Half": {
    "emoji": "⏱️",
    "nombre": "Ganador 2da Mitad",
    "deporte": "soccer",
    "categoria": "Principales"
    },
    "Over/Under Line": {
    "emoji": "🔢",
    "nombre": "Total Anotaciones",
    "deporte": "soccer",
    "categoria": "Principales"
    },
    "Total - Home": {
    "emoji": "🔢",
    "nombre": "Total - Equipo Local",
    "deporte": "soccer",
    "categoria": "Mas opciones"
    },
    "Total - Away": {
    "emoji": "🔢",
    "nombre": "Total - Equipo Visitante",
    "deporte": "soccer",
    "categoria": "Mas opciones"
    },
    "Over/Under Line (1st Half)": {
    "emoji": "📊",
    "nombre": "Total 1ra Mitad",
    "deporte": "soccer",
    "categoria": "Por Tiempos"
    },
    "Correct Score (1st Half)": {
    "emoji": "🔢",
    "nombre": "Marcador Exacto (1ª Mitad)",
    "deporte": "soccer",
    "categoria": "Por Tiempos"
    },
    """Away Team Clean Sheet": {
    "emoji": "🧼",
    "nombre": "Visitante No Recibe Gol",
    "deporte": "soccer",
    "categoria": "Especiales"
    },"""
    "Goals Odd/Even": {
    "emoji": "🔢",
    "nombre": "Goles Par/Impar",
    "deporte": "soccer",
    "categoria": "Especiales"
    },
    "Which team will score the 1st goal?": {
    "emoji": "🥇",
    "nombre": "Primer Equipo en Marcar",
    "deporte": "soccer",
    "categoria": "Especiales"
    },
    
    "Home Team to Score in Both Halves": {
    "emoji": "🔄",
    "nombre": "Local Marca en Ambas Partes",
    "deporte": "soccer",
    "categoria": "Especiales"
    },
    "Home Team Score a Goal (2nd Half)": {
    "emoji": "⏳",
    "nombre": "Gol Local en 2ª Parte",
    "deporte": "soccer",
    "categoria": "Por Tiempos"
    },
    "Both Teams To Score (1st Half)": {
    "emoji": "✅",
    "nombre": "Ambos Marcan (1ª Parte)",
    "deporte": "soccer",
    "categoria": "Por Tiempos"
    },
    "Both Teams To Score - Second Half": {
        "emoji": "✅",
        "nombre": "Ambos Marcan (2da Mitad)",
        "deporte": "soccer",
        "categoria": "Por Tiempos"
    },
    "Correct Score - First Half": {
        "emoji": "🔢",
        "nombre": "Marcador Exacto 1ra Mitad",
        "deporte": "soccer",
        "categoria": "Por Tiempos"
    },
    "Home Team Exact Goals Number": {
        "emoji": "🏠",
        "nombre": "Goles Exactos Local",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "Away Team Exact Goals Number": {
        "emoji": "✈️",
        "nombre": "Goles Exactos Visitante",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "To Score Two or More Goals": {
        "emoji": "🌟",
        "nombre": "2+ Goles de Jugador",
        "deporte": "soccer",
        "categoria": "Jugadores"
    },
    "First Goal Method": {
        "emoji": "⚽",
        "nombre": "Método Primer Gol",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "Draw No Bet (1st Half)": {
        "emoji": "🔄⏱️",
        "nombre": "Empate No Bet 1ra Mitad",
        "deporte": "soccer",
        "categoria": "Por Tiempos"
    },
    "Draw No Bet": {
        "emoji": "🔄⏱️",
        "nombre": "Empate No Bet",
        "deporte": "soccer",
        "categoria": "Principales"
    },
    "Penalty Awarded": {
        "emoji": "🅿️",
        "nombre": "Habrá Penal?",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    "Clean Sheet": {
        "emoji": "🧼",
        "nombre": "Portería a Cero",
        "deporte": "soccer",
        "categoria": "Especiales"
    },
    #basquet y béisbol
    "alternate_spreads": {
    "emoji": "📊",
    "nombre": "Hándicap",
    "deporte": "basketball",
    "categoria": "Principales"
    },
    "alternate_totals": {
    "emoji": "🔢",
    "nombre": "Total Anotaciones",
    "deporte": "basketball",
    "categoria": "Principales"
    },
    
    
    
}
  
  

MERCADOS_CON_POINT = [
    # --- EXISTENTES ---
    "Asian Handicap",
    "Total - Away",
    "Total - Home",
    "Over/Under Line",
    "Over/Under Line (1st Half)",
    "totals",
    "alternate_spreads",
    "alternate_totals",
    "alternate_team_totals",
    "spreads_h1",
    "spreads_h2",
    "totals_h1",
    "totals_h2",
    "alternate_team_totals_h1",
    "alternate_team_totals_h2",
    "alternate_spreads_cards",
    "alternate_totals_cards",
    "alternate_spreads_1st_1_innings",
    "alternate_spreads_1st_3_innings",
    "alternate_spreads_1st_5_innings",
    "alternate_spreads_1st_7_innings",
    "alternate_totals_1st_1_innings",
    "alternate_totals_1st_3_innings",
    "alternate_totals_1st_5_innings",
    "alternate_totals_1st_7_innings",
    "alternate_spreads_q1",
    "spreads_q2",
    "spreads_q3",
    "spreads_q4",
    "spreads_h1",
    "spreads_h2",
    "totals_q1",
    "totals_q2",
    "totals_q3",
    "totals_q4",
    "totals_h1",
    "totals_h2",
    
    # --- NUEVOS MERCADOS CON POINT (FALTANTES EN TU CONFIG) ---
    # Totals (Over/Under)
    "Goals Over/Under",                # Total goles (partido completo)
    "Goals Over/Under First Half",     # Total goles (1ª mitad)
    "Goal Line",                       # Línea de goles (alternativa)
    "Total Corners",                   # Total de córners
    "Cards Over/Under",                # Total de tarjetas
    "Total ShotOnGoal",                # Total disparos a puerta
    "Over/Under Line",                 # Total goles (línea dinámica)
    "Over/Under (1st Half)",           # Total goles (1ª mitad, línea dinámica)
    
    # Handicaps
    "Cards European",                  # Hándicap de tarjetas
    "3-Way Handicap",                  # Hándicap europeo (3 vías)
    "European Handicap (1st Half)",    # Hándicap europeo (1ª mitad)
    
    # Especiales (totals con puntos)
    "Home Team Goals",                 # Goles del equipo local (puede ser hándicap)
    "Away Team Goals",                 # Goles del equipo visitante (puede ser hándicap)
    "How many goals will Home Team score?",  # Total específico para local
    "How many goals will Away Team score?",  # Total específico para visitante
]


cuba_tz = pytz.timezone("America/Havana")
lock = asyncio.Lock()


# Variables globales

api_index = 0  # Índice de la API en uso
api_uso = None  # API en uso actualmente
creditos_api = {}  # Créditos restantes por API
# Inicialización de variables globales (debe estar en tu código principal)
api_index = 0
api_uso = None
creditos_api = {}

@marca_tiempo
@marca_tiempo
async def mostrar_tipos_apuestas(update: Update, context: CallbackContext):
    """Muestra los tipos de apuestas con nueva opción de búsqueda"""
    texto = (
        " <blockquote>🎲 <b>Tipos de apuestas </b> </blockquote> \n\n"
        "⚽ <b>Prepartido</b>: Apuesta antes de que el evento deportivo comience.\n\n"
        "📡 <b>En Vivo</b>: Apuesta mientras el evento está en curso, con cuotas en tiempo real.\n\n"
        "🔗 <b>Combinada</b>: Combina varias apuestas en una sola para aumentar las ganancias.\n\n"
        "🔍 <b>Buscar Equipo</b>: Encuentra eventos por nombre de equipo\n\n"
        "🔽 <i>Elige el tipo de apuesta que deseas realizar:</i>"
    )

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Combinada", callback_data="handle_combinadas_callback")],
        [InlineKeyboardButton("⚽ Prepartido", callback_data="handle_prepartido_callback"),
         InlineKeyboardButton("📡 En Vivo", callback_data="handle_vivo_callback")],
        [InlineKeyboardButton("🔍 Buscar Equipo", callback_data="buscar_equipo")],
        [InlineKeyboardButton("🎟️ Mis Apuestas", callback_data="mis_apuestas")],
        [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
    ])

    await update.callback_query.message.edit_text(texto, reply_markup=botones, parse_mode="HTML")

def cargar_apis():
    try:
        with open("api.json", "r") as file:
            apis = json.load(file)
        return apis["API_KEYS"]
    except Exception as e:
        print(f"Error cargando api.json: {e}")
        return []
API_KEYS = cargar_apis()    
        

async def obtener_api(reintentos=3):
    global api_index, api_uso, API_KEYS, creditos_api
    
    # Inicialización del sistema (solo primera vez)
    if not hasattr(obtener_api, '_inicializado'):
        obtener_api._inicializado = True
        obtener_api._api_keys_original = API_KEYS.copy()
        print(f"⚙️ Sistema inicializado con {len(API_KEYS)} APIs registradas")
    
    # Función interna para generar estadísticas CORRECTAS
    def generar_estadisticas():
        total_registradas = len(API_KEYS)
        verificadas = len(creditos_api)
        agotadas = sum(1 for v in creditos_api.values() if v <= 5)
        disponibles = total_registradas - agotadas  # ¡CÁLCULO CORRECTO!
        
        return {
            'total': total_registradas,
            'verificadas': verificadas,
            'agotadas': agotadas,
            'disponibles': disponibles,
            'no_verificadas': total_registradas - verificadas
        }

    # Reintentos con manejo de errores robusto
    for intento in range(1, reintentos + 1):
        try:
            # 1. Verificar API actual si existe y tiene créditos
            if api_uso and api_uso in creditos_api and creditos_api[api_uso] > 5:
                if intento > 1:
                    print(f"✅ Sesión recuperada. API actual: {api_uso[:8]}... (Créditos: {creditos_api[api_uso]})")
                return api_uso
            elif api_uso:
                print(f"🔄 API {api_uso[:8]}... agotada (Créditos: {creditos_api.get(api_uso, 0)})")

            # 2. Búsqueda optimizada de API válida
            for _ in range(len(API_KEYS)):
                api_actual = API_KEYS[api_index]
                
                try:
                    # Verificación eficiente de créditos
                    if api_actual not in creditos_api:
                        creditos_api[api_actual] = await verificar_creditos(api_actual)
                    
                    # Selección si cumple requisitos
                    if creditos_api[api_actual] > 5:
                        api_uso = api_actual
                        stats = generar_estadisticas()
                        
                        print(f"🔄 Nueva API activada: {api_uso[:8]}... (Créditos: {creditos_api[api_uso]})")
                        print(f"📊 Estado actual del sistema:")
                        print(f"- Total registradas: {stats['total']}")
                        print(f"- Verificadas: {stats['verificadas']}")
                        print(f"- Agotadas: {stats['agotadas']}")
                        print(f"- Disponibles: {stats['disponibles']} (Total - Agotadas)")
                        print(f"- Por verificar: {stats['no_verificadas']}")
                        return api_uso
                
                except Exception as e:
                    print(f"⚠️ Error en API {api_actual[:8]}...: {str(e)[:50]}...")
                
                finally:
                    # Rotación segura del índice
                    api_index = (api_index + 1) % len(API_KEYS)
            
            # 3. Manejo cuando no encuentra API válida
            stats = generar_estadisticas()
            print("⚠️ Búsqueda completada sin API válida")
            print(f"🔍 Resumen final:")
            print(f"Total APIs: {stats['total']}")
            print(f"Verificadas: {stats['verificadas']}")
            print(f"Agotadas: {stats['agotadas']}")
            print(f"Disponibles: {stats['disponibles']} (calculado como Total - Agotadas)")
            print(f"No verificadas: {stats['no_verificadas']}")
            
            return None
            
        except Exception as e:
            print(f"🚨 Error crítico (intento {intento}/{reintentos}): {str(e)}")
            if intento == reintentos:
                print("❌ Máximo de reintentos alcanzado")
                # Restauración de emergencia
                API_KEYS = obtener_api._api_keys_original.copy()
                api_index = 0
                return None
            await asyncio.sleep(min(intento, 3))  # Espera progresiva        
            
            
# Función para verificar créditos de una API específica
async def verificar_creditos(api_key):
    url = "https://api.the-odds-api.com/v4/sports/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"api_key": api_key}) as response:
                if response.status == 200:
                    remaining_credits = response.headers.get("x-requests-remaining", "0")
                    return int(remaining_credits)
                else:
                    print(f"❌ Error verificando créditos de {api_key}: {response.status}")
                    return 0
    except Exception as e:
        print(f"❌ Error de conexión con API {api_key}: {e}")
        return 0

# Función que usa la API obtenida
async def realizar_solicitud_deportes():
    api_key = await obtener_api()
    if not api_key:
        print("🚨 No hay APIs disponibles con créditos suficientes.")
        return None

    url = "https://api.the-odds-api.com/v4/sports/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"api_key": api_key}) as response:
                if response.status == 200:
                    deportes = await response.json()
                    remaining_credits = response.headers.get("x-requests-remaining", "No disponible")

                    # Actualizar los créditos en cache
                    if remaining_credits.isdigit():
                        creditos_api[api_key] = int(remaining_credits)

                    
                    return deportes
                else:
                    print(f"❌ Error {response.status}: {await response.text()}")
                    return None
    except Exception as e:
        print(f"❌ Error en la solicitud: {e}")
        return None


# Función asincrónica para obtener los deportes
async def obtener_deportes():
    deportes = await realizar_solicitud_deportes()  # Llamar a la función asincrónica para obtener los deportes
    return deportes  # Devuelve los deportes obtenidos          
    
    
#funcion botones emois
def detectar_pais(nombre_liga):
    for pais, nombres in paises.items():
        for nombre in nombres:
            if nombre.lower() in nombre_liga.lower():
                return pais
    return None

def obtener_bandera(pais):
   
    return banderas.get(pais, "🏆")          
def obtener_bandera_por_nombre(nombre_pais: str) -> str:
    """Obtiene el emoji de bandera por el nombre de un país desde el archivo JSON"""
    try:
        # Cargar ligas desde el archivo JSON
        with open('ligas.json', 'r', encoding='utf-8') as f:
            ligas_data = json.load(f)
            ligas = ligas_data.get("soccer", [])

        # Buscar el país en las ligas
        for liga in ligas:
            country_data = liga.get('country_data', {})
            if country_data.get('name') == nombre_pais:
                # Obtener código de país y convertirlo a emoji
                country_code = country_data.get('code', '').upper()
                if country_code:
                    # Convertir código de país a emoji de bandera
                    # Ejemplo: 'AR' -> 🇦🇷
                    return f"{chr(ord(country_code[0]) + 127397)}{chr(ord(country_code[1]) + 127397)}"
        
        # Si no se encuentra el país, devolver una bandera genérica
        return "🌍"
    
    except Exception as e:
        print(f"Error al obtener la bandera para {nombre_pais}: {e}")
        return "🌍"          
            

@verificar_bloqueo
async def mostrar_deportes(update: Update, context: CallbackContext):
    # Mensaje de encabezado
    mensaje = "<blockquote>🏆Deportes Disponibles 🏆</blockquote>\n"
    mensaje += "<i>🔽 Selecciona un deporte para ver las ligas disponibles</i>:\n\n"

    # Obtener los deportes de la API de manera asincrónica
    deportes = await obtener_deportes()
    

    if context.user_data.get("betting") == "LIVE":
        # Filtrar solo fútbol - CORREGIDO: buscar por "group" en lugar de "nombre"
        deportes = [deporte for deporte in deportes if deporte.get("group") == "Soccer"]
        
        # Agregar mensaje informativo para LIVE
        mensaje = "<blockquote>⚽ Deportes EN VIVO Disponibles ⚽</blockquote>\n"
        mensaje += "<i>🔽 Selecciona fútbol para ver partidos en vivo</i>\n\n"
        mensaje += "⚠️ <i>Otros deportes en vivo están en mantenimiento</i>\n\n"

    # Si no se obtienen deportes, mostrar un mensaje de error
    if not deportes:
        mensaje = "❌ No se pudieron obtener los deportes en este momento."
        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")]]
    else:
        # Conjuntos para evitar duplicados por clave y nombre
        claves_vistas = set()
        nombres_vistos = set()
        keyboard = []
        fila = []
        fila_siguiente_es_2 = False  # Variable para alternar entre 1 y 2 botones por fila

        for deporte in deportes:
            clave_deporte = deporte.get("key")  # Clave única de la API
            
            nombre_deporte = deporte.get("group", deporte.get("sport", deporte.get("title", "Desconocido")))

            # Evitar nombres y claves duplicados
            if clave_deporte in claves_vistas or nombre_deporte.lower() in nombres_vistos:
                continue

            # Registrar clave y nombre para evitar duplicados
            claves_vistas.add(clave_deporte)
            nombres_vistos.add(nombre_deporte.lower())  

            # Buscar nombre personalizado por coincidencia parcial
            nombre_personalizado = nombre_deporte  
            emoji = "🏅"
            for clave, (nombre, icono) in deportes_personalizados.items():
                if clave in clave_deporte:  # Verifica si la clave base está contenida en clave_deporte
                    nombre_personalizado, emoji = nombre, icono
                    break  # Si encuentra una coincidencia, la usa y sale del bucle

            # Crear el botón con el nombre personalizado y el emoji
            fila.append(InlineKeyboardButton(f"{emoji} {nombre_personalizado}", callback_data=f"deporte_{nombre_deporte}"))
            
            # Comprobar si la fila debe tener 1 o 2 botones
            if fila_siguiente_es_2:
                if len(fila) == 2:  # Fila con 2 botones
                    keyboard.append(fila)
                    fila = []
                    fila_siguiente_es_2 = False  # Cambiar a la siguiente fila de 1 botón
            else:
                if len(fila) == 1:  # Fila con 1 botón
                    keyboard.append(fila)
                    fila = []
                    fila_siguiente_es_2 = True  # Cambiar a la siguiente fila de 2 botones

        # Si hay una fila incompleta, agregarla
        if fila:
            keyboard.append(fila)

        # Agregar el botón de volver
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")])

    # Definir el markup para los botones
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Editar el mensaje en lugar de responder
    await update.callback_query.message.edit_text(mensaje, reply_markup=reply_markup, parse_mode="HTML")


async def obtener_ligas(deporte):
    sports_url = "https://api.the-odds-api.com/v4/sports/"
    api_key = await obtener_api()
    if not api_key:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(sports_url, params={"api_key": api_key}) as response:
                if response.status == 200:
                    deportes = await response.json()
                    
                    # Filtrar ligas por deporte
                    ligas = [liga for liga in deportes if liga.get("group") == deporte]
                    
                    return ligas
                else:
                    print(f"❌ Error {response.status}: {await response.text()}")
    except Exception as e:
        print(f"⚠️ Error en la solicitud: {e}")
    return None



async def seleccionar_deporte(update: Update, context: CallbackContext):
    """Función corregida que maneja la selección de deporte y ligas"""
    try:
        # 1. Verificación básica
        if not update or not update.callback_query:
            print("❌ Error: update o callback_query es None")
            return

        query = update.callback_query
        await query.answer()
        callback_data = query.data        

        # 3. OBTENCIÓN DEL DEPORTE
        if callback_data.startswith("pagina_"):
            page = int(callback_data.replace("pagina_", ""))
            context.user_data["page"] = page
            deporte = context.user_data.get("deporte_actual")
        else:
            deporte = callback_data.replace("deporte_", "")
            context.user_data["deporte_actual"] = deporte
            page = 0
            
            if context.user_data.get('betting') == 'LIVE' and context.user_data.get('deporte_actual') != 'Soccer':
                await mostrar_futbol_live(update, context)
                return

        # 4. Validación mínima del deporte
        if not deporte:
            print("⚠️ Deporte es None, usando hockey como valor por defecto")
            deporte = "Soccer"

        # 5. FLUJO DIFERENCIADO (FÚTBOL vs OTROS DEPORTES)
        if deporte.lower() in ["soccer", "fútbol", "futbol"]:
            # Cargar desde archivo local primero
            try:
                with open('ligas.json', 'r', encoding='utf-8') as f:
                    ligas_data = json.load(f)
                    ligas = ligas_data.get("soccer", [])
                    
                if not ligas:
                    raise ValueError("No hay ligas en el archivo")
                    
                await mostrar_paises_futbol(update, context, ligas)
                
            except Exception as e:
                print(f"⚠️ Error al cargar ligas.json: {e}")
                # Fallback a la API si el archivo falla
                ligas = await obtener_ligas_futbol()
                if ligas:
                    await mostrar_paises_futbol(update, context, ligas)
                else:
                    await query.edit_message_text(
                        "⚠️ No hay ligas de fútbol disponibles ahora.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                        ])
                    )
        else:
            # Resto del código para otros deportes (se mantiene igual)
            try:
                ligas = await obtener_ligas(deporte)
            except Exception as e:
                print(f"Error al obtener ligas de {deporte}: {e}")
                ligas = None

            if not ligas:
                await query.edit_message_text(
                    f"⚠️ No hay ligas de {deporte} disponibles ahora.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                    ])
                )
                return

            
            # Crear teclado con botones de ligas (usando prefijo 'ligas_' para otros deportes)
            keyboard = []
            fila = []
            ligas_por_pagina = 20
            inicio = page * ligas_por_pagina
            fin = inicio + ligas_por_pagina
            
            for liga in ligas[inicio:fin]:
                try:
                    nombre_liga = liga.get('title', liga.get('name', 'Liga sin nombre'))
                    clave_liga = liga.get('key', liga.get('id', 'liga_sin_clave'))
                    
                    # Para otros deportes usamos el prefijo 'ligas_' y aceptamos IDs alfanuméricos
                    pais = detectar_pais(nombre_liga)
                    bandera = obtener_bandera(pais) if pais else "🏆"

                    if pais:
                        for nombre in paises[pais]:
                            nombre_liga = nombre_liga.replace(nombre, pais)

                    fila.append(InlineKeyboardButton(
                        f"{bandera} {nombre_liga}",
                        callback_data=f"ligas_{clave_liga}"  # Prefijo 'ligas_' para otros deportes
                    ))

                    if len(fila) == 2:
                        keyboard.append(fila)
                        fila = []
                except Exception as e:
                    print(f"Error al procesar liga: {e}")
                    continue

            if fila:
                keyboard.append(fila)

            # Controles de paginación
            navegacion = []
            if page > 0:
                navegacion.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"pagina_{page - 1}"))
            if fin < len(ligas):
                navegacion.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"pagina_{page + 1}"))

            if navegacion:
                keyboard.append(navegacion)

            keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")])

            await query.edit_message_text(
                f"🔽 Selecciona la liga de {deporte.capitalize()}:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"💥 ERROR en seleccionar_deporte: {e}")
        await query.edit_message_text(
            "⚠️ Ocurrió un error inesperado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
            ])
        )
              



async def mostrar_paises_futbol(update: Update, context: CallbackContext, ligas: list):
    """Muestra países con botón de ligas principales solo en primera página"""
    try:
        if not ligas or not isinstance(ligas, list):
            try:
                await update.callback_query.edit_message_text(
                    "⚠️ No hay datos de ligas disponibles.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                    ])
                )
            except:
                await update.callback_query.edit_message_caption(
                    caption="⚠️ No hay datos de ligas disponibles.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                    ])
                )
            return

        # Procesar todos los países disponibles
        paises = {}
        for liga in ligas:
            country_data = liga.get('country_data', {})
            if country_name := country_data.get('name'):
                if country_name not in paises:
                    paises[country_name] = {
                        'code': country_data.get('code', '').lower(),
                        'flag': country_data.get('flag', '🌍')
                    }

        if not paises:
            try:
                await update.callback_query.edit_message_text(
                    "⚠️ No se encontraron países disponibles.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                    ])
                )
            except:
                await update.callback_query.edit_message_caption(
                    caption="⚠️ No se encontraron países disponibles.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                    ])
                )
            return

        # Configuración de paginación
        paises_ordenados = sorted(paises.items())
        items_por_pagina = 30  # Mostrar 30 países por página (10 filas de 3)
        pagina_actual = context.user_data.get("paises_pagina", 0)
        total_paginas = (len(paises_ordenados) + items_por_pagina - 1) // items_por_pagina

        # Construir teclado
        keyboard = []

        # Solo mostrar botón de ligas principales en la primera página
        if pagina_actual == 0:
            keyboard.append([
                InlineKeyboardButton("⭐ LIGAS PRINCIPALES ⭐", callback_data="mostrar_ligas_principales")
            ])

        # Agregar países en filas de 3
        inicio = pagina_actual * items_por_pagina
        fin = min(inicio + items_por_pagina, len(paises_ordenados))
        
        fila_actual = []
        for nombre_pais, datos in paises_ordenados[inicio:fin]:
            bandera = obtener_bandera_por_nombre(nombre_pais)
            fila_actual.append(
                InlineKeyboardButton(
                    f"{bandera} {nombre_pais}",
                    callback_data=f"pais_{nombre_pais}"
                )
            )
            if len(fila_actual) == 3:
                keyboard.append(fila_actual)
                fila_actual = []
        
        if fila_actual:
            keyboard.append(fila_actual)

        # Controles de paginación
        controles = []
        if pagina_actual > 0:
            controles.append(InlineKeyboardButton("⬅️ Anterior", callback_data="paises_prev"))
        if fin < len(paises_ordenados):
            controles.append(InlineKeyboardButton("➡️ Siguiente", callback_data="paises_next"))
        
        if controles:
            keyboard.append(controles)

        # Botón de volver
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")])

        texto = f"🌍 Selecciona un país (Página {pagina_actual + 1}/{total_paginas}):"

        try:
            await update.callback_query.edit_message_text(
                text=texto,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            await update.callback_query.edit_message_caption(
                caption=texto,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        print(f"💥 Error en mostrar_paises_futbol: {e}")
        try:
            await update.callback_query.edit_message_text(
                "⚠️ Ocurrió un error al mostrar los países.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                ])
            )
        except:
            await update.callback_query.edit_message_caption(
                caption="⚠️ Ocurrió un error al mostrar los países.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
                ])
            )

async def manejar_paginacion_paises(update: Update, context: CallbackContext):
    """Maneja la paginación manteniendo el estado correcto"""
    try:
        query = update.callback_query
        await query.answer()

        # Manejar acción especial para ligas principales
        if query.data == "mostrar_ligas_principales":
            await mostrar_ligas_principales(update, context)
            return

        # Actualizar página según acción
        pagina_actual = context.user_data.get("paises_pagina", 0)
        
        if query.data == "paises_prev" and pagina_actual > 0:
            context.user_data["paises_pagina"] = pagina_actual - 1
        elif query.data == "paises_next":
            context.user_data["paises_pagina"] = pagina_actual + 1

        # Volver a cargar y mostrar los países
        with open('ligas.json', 'r', encoding='utf-8') as f:
            ligas = json.load(f).get("soccer", [])
        
        await mostrar_paises_futbol(update, context, ligas)

    except Exception as e:
        print(f"💥 Error en manejar_paginacion_paises: {e}")
        await query.edit_message_text(
            "⚠️ Ocurrió un error al cambiar de página.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_deportes")]
            ])
        )

LIGAS_PRINCIPALES = {
    2: "Champions League",
    140: "🇪🇸 La Liga",
    39: "🏴 Premier League",
    32: "Eliminatorias Copa del Mundo",    
    135: "🇮🇹 Serie A",              # Italia
    78: "🇩🇪 Bundesliga",            # Alemania
    61: "🇫🇷 Ligue 1",               # Francia    
    3: "Europa League",
    253: "🇺🇸 Major League Soccer",
    1002: "Copa Libertadores",
    88: "🇳🇱 Países bajos",           # Países Bajos
    94: "🇵🇹 Primeira Liga",        # Portugal
    262: "🇲🇽 Liga MX",             # México
    128: "🇦🇷 Liga Profesional",    # Argentina
    152: "🇸🇦 Saudi Pro League",    # Arabia Saudita
    15: "Mundial de Clubes",            
    5: "Liga de Naciones UEFA"
}


async def mostrar_ligas_principales(update: Update, context: CallbackContext):
    """Muestra las ligas principales en un menú separado"""
    try:
        with open('ligas.json', 'r', encoding='utf-8') as f:
            ligas = json.load(f).get("soccer", [])

        # Lista de IDs de ligas principales (copas primero, luego ligas)
        
        keyboard = []
        fila_actual = []

        for liga_id, nombre in LIGAS_PRINCIPALES.items():
            liga = next((l for l in ligas if l.get('id') == liga_id), None)
            if liga:
                emoji = "🏆" if liga.get('type') != 'League' else ""
                fila_actual.append(
                    InlineKeyboardButton(
                        f"{emoji} {nombre}".strip(),
                        callback_data=f"ligas_futbol_{liga_id}"
                    )
                )

                if len(fila_actual) == 2:
                    keyboard.append(fila_actual)
                    fila_actual = []

        if fila_actual:
            keyboard.append(fila_actual)

        # Botón para volver
        keyboard.append([
            InlineKeyboardButton("🔙 Volver a países", callback_data="deporte_soccer")
        ])

        await update.callback_query.message.edit_text(
            "LIGAS PRINCIPALES DISPONIBLES:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print(f"💥 Error en mostrar_ligas_principales: {e}")
        await update.callback_query.message.edit_text(
            "⚠️ Error al cargar las ligas principales.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
            ])
        )
async def manejar_seleccion_pais(update: Update, context: CallbackContext):
    """Maneja la selección de un país específico"""
    query = update.callback_query
    await query.answer("🔄 Cargando ligas...")
    
    pais_seleccionado = query.data.replace("pais_", "")
    await mostrar_ligas_por_pais(update, context, pais_seleccionado)



async def mostrar_ligas_por_pais(update: Update, context: CallbackContext, pais_seleccionado: str):
    """Muestra las ligas de un país con mejoras visuales"""
    try:
        # Cargar ligas desde el archivo JSON
        try:
            with open('ligas.json', 'r', encoding='utf-8') as f:
                ligas_data = json.load(f)
                ligas = ligas_data.get("soccer", [])
        except Exception as e:
            print(f"Error al cargar ligas.json: {e}")
            await update.callback_query.message.edit_text(
                "⚠️ No hay datos de ligas disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
                ])
            )
            return

        # Filtrar ligas por país
        ligas_pais = [
            liga for liga in ligas 
            if liga.get('country_data', {}).get('name') == pais_seleccionado
        ]

        if not ligas_pais:
            await update.callback_query.message.edit_text(
                f"⚠️ No se encontraron ligas para {pais_seleccionado}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
                ])
            )
            return

        # Ordenar ligas: primero ligas, luego copas
        ligas_pais.sort(key=lambda x: 0 if x.get('type') == 'League' else 1)

        # Crear teclado con las ligas en filas de 2 botones
        keyboard = []
        fila_actual = []
        
        for liga in ligas_pais:
            try:
                # Obtener datos de la liga
                nombre_completo = liga.get('title', liga.get('league_data', {}).get('name', 'Liga sin nombre'))
                # Quitar el nombre del país del botón
                nombre_liga = nombre_completo.split('(')[0].strip()
                tipo = liga.get('type', '').lower()
                league_id = liga.get('id')
                logo_url = liga.get('league_data', {}).get('logo', '')
                
                if not league_id:
                    print(f"⚠️ Liga sin ID: {nombre_completo}")
                    continue
                
                icono = "🏆" if tipo == 'cup' else "⚽" if tipo == 'league' else "🏟️"
                
                # Agregar botón a la fila actual
                fila_actual.append(
                    InlineKeyboardButton(
                        f"{icono} {nombre_liga}",
                        callback_data=f"ligas_futbol_{league_id}"
                    )
                )
                
                # Si la fila tiene 2 botones, agregar al teclado y reiniciar fila
                if len(fila_actual) == 2:
                    keyboard.append(fila_actual)
                    fila_actual = []
                    
            except Exception as e:
                print(f"⚠️ Error procesando liga: {e}")
                continue

        # Agregar última fila si no está completa
        if fila_actual:
            keyboard.append(fila_actual)

        # Botón para volver (centrado)
        keyboard.append([
            InlineKeyboardButton("🔙 Volver a países", callback_data="deporte_soccer")
        ])

        # Obtener bandera del país
        bandera = obtener_bandera_por_nombre(pais_seleccionado)
        
        # Enviar mensaje con imagen de la primera liga (si existe)
        primera_liga = ligas_pais[0] if ligas_pais else None
        logo_url = primera_liga.get('league_data', {}).get('logo') if primera_liga else None
        
        if logo_url:
            try:
                # Primero enviar la foto
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=logo_url,
                    caption=f"{bandera} Ligas disponibles en {pais_seleccionado}:",
                    reply_markup=InlineKeyboardMarkup(keyboard))
                
                # Eliminar el mensaje anterior
                await update.callback_query.message.delete()
                return
                
            except Exception as e:
                print(f"⚠️ Error al enviar foto: {e}")
                # Fallback a mensaje sin foto si hay error

        # Versión sin foto si no hay logo disponible
        await update.callback_query.message.edit_text(
            f"{bandera} Ligas disponibles en {pais_seleccionado}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print(f"💥 Error en mostrar_ligas_por_pais: {e}")
        await update.callback_query.message.edit_text(
            "⚠️ Ocurrió un error al mostrar las ligas.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
            ])
        )



async def manejar_navegacion(update: Update, context: CallbackContext):
    # Obtener el callback_data
    callback_data = update.callback_query.data

    # Verificar si el callback_data es de paginación
    if callback_data.startswith("pagina_"):
        # Llamar a la función seleccionar_deporte para actualizar la página
        await seleccionar_deporte(update, context)

async def obtener_ligas_futbol() -> Optional[list]:
    """
    Obtiene las ligas de fútbol activas desde API-FOOTBALL con manejo mejorado de errores
    """
    url = "https://v3.football.api-sports.io/leagues"
    headers = {
        "x-rapidapi-key": API_FUTBOL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    params = {
        "current": "true",
        "type": "league"  # Solo ligas regulares (puedes añadir 'cup' si necesitas copas)
    }

    try:
        # Intento principal con timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            # Verificar si la respuesta fue exitosa
            if response.status_code != 200:
                error_msg = f"❌ Error en la API: {response.status_code} - {response.text}"
                print(error_msg)
                return None
                
            data = response.json()
            
            # Verificar si la API devolvió errores
            if data.get("errors"):
                print(f"⚠️ Errores de la API: {data['errors']}")
                return None

            # Verificar si 'response' está vacío
            if not data.get("response"):
                print("⚠️ No se encontraron ligas. Respuesta vacía.")
                return None

            # Procesar las ligas obtenidas
            ligas_procesadas = []
            for liga_data in data.get("response", []):
                try:
                    league = liga_data.get("league", {})
                    country = liga_data.get("country", {})
                    
                    # Solo incluir ligas con ID válido
                    if not league.get('id'):
                        continue
                        
                    liga = {
                        "title": f"{league.get('name', '')} ({country.get('name', '')})",
                        "key": f"futbol_{league['id']}",  # Prefijo 'futbol_' para identificarlas
                        "id": league['id'],  # ID numérico real para la API
                        "group": "Soccer",
                        "type": league.get('type', 'Unknown'),
                        "league_data": league,
                        "country_data": country
                    }
                    ligas_procesadas.append(liga)
                except KeyError as e:
                    print(f"⚠️ Error procesando liga: Falta clave {e}")
                    continue

          
            return ligas_procesadas

    except httpx.TimeoutException:
        print("⚠️ Timeout al conectar con API-FOOTBALL")
        return None
    except httpx.NetworkError:
        print("⚠️ Error de red al conectar con API-FOOTBALL")
        return None
    except Exception as e:
        print(f"💥 Error inesperado al obtener ligas: {str(e)}")
        return None

# obtener PREPARTIDOS
async def obtener_eventos_futbol(league_id: str) -> Union[list, str]:
    """Obtiene eventos PREMATCH con caché (no aplica para LIVE)"""
    cache_key = f"liga_{league_id}"
    
    # Verificar caché (solo para PREMATCH)
    if cache_key in futbol_cache["ligas"]:
        cached = futbol_cache["ligas"][cache_key]
        edad_cache = datetime.now().timestamp() - cached["timestamp"]
        if edad_cache < CACHE_TTLP:
            print(f"[CACHE] ✅ Liga {league_id} servida desde caché (edad {edad_cache:.2f} segundos)")
            return cached["data"]
        else:
            print(f"[CACHE] ⚠️ Liga {league_id} vencida (edad {edad_cache:.2f} segundos), refrescando...")

    clean_id = league_id.replace("ligas_futbol_", "").replace("futbol_", "")
    
    if not clean_id.isdigit():
        return f"Error: ID de liga inválido '{league_id}'"

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-key": API_FUTBOL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    async def fetch_eventos(season: int):
        params = {
            "league": clean_id,
            "season": season,
            "status": "NS",  # Solo No Iniciados (PREMATCH)
            "timezone": "America/Havana",
            "next": "15"  # Próximos 15 partidos
        }
        print(f"[API] 🌐 Solicitando liga={clean_id}, temporada={season}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[API] ✅ Respuesta OK ({len(data.get('response', []))} eventos)")
                    return data.get("response", [])
                else:
                    print(f"[API] ❌ Error {response.status} en solicitud a temporada {season}")
                return None

    try:
        # 🔹 SOLO temporada 2024
        eventos = await fetch_eventos(2025)
        
        if not eventos:
            print(f"[API] ⚠️ Ningún evento encontrado para liga {clean_id}, temporada 2024")
            return []

        # Actualizar caché (solo PREMATCH)
        futbol_cache["ligas"][cache_key] = {
            "data": eventos,
            "timestamp": datetime.now().timestamp()
        }
        print(f"[CACHE] ♻️ Caché actualizada para liga {league_id} ({len(eventos)} eventos)")
        return eventos

    except Exception as e:
        print(f"[ERROR] 🚨 en obtener_eventos_futbol: {str(e)}")
        return f"Error: {str(e)}"
        
async def limpiar_cache(context: ContextTypes.DEFAULT_TYPE):
    """Tarea periódica para limpiar el caché"""
    try:
        now = datetime.now().timestamp()
        # Limpiar eventos viejos
        
        for key in list(futbol_cache["eventos"].keys()):
            if now - futbol_cache["eventos"][key]["timestamp"] > CACHE_TTLP:
                del futbol_cache["eventos"][key]
        # Limpiar ligas viejas
        for key in list(futbol_cache["ligas"].keys()):
            if now - futbol_cache["ligas"][key]["timestamp"] > CACHE_TTLP:
                del futbol_cache["ligas"][key]
        print(f"[CACHE] Limpieza completada. Eventos: {len(futbol_cache['eventos'])}, Ligas: {len(futbol_cache['ligas'])}")
    except Exception as e:
        print(f"[ERROR] En limpieza de caché: {str(e)}")
    
              
async def obtener_eventos_futbol_live(league_id: str) -> Union[list, str]:
    cache_key = f"live_{league_id}"
    
    # Verificar caché (con TTL más corto para eventos en vivo)
    cached = futbol_cache["ligas"].get(cache_key)
    if cached and (datetime.now().timestamp() - cached["timestamp"]) < 300:  # 5 minuto para live
        
        return cached["data"]

    clean_id = league_id.replace("ligas_futbol_", "").replace("futbol_", "")
    
    if not clean_id.isdigit():
        error_msg = f"Error: ID de liga inválido '{league_id}'"
        print(f"[DEBUG] {error_msg}")
        return error_msg

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-key": API_FUTBOL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    params = {
        "live": "all",
        "timezone": "America/Havana"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()

                if response.status == 200:
                    todos_eventos = data.get("response", [])
                    eventos_filtrados = [
                        evento for evento in todos_eventos
                        if str(evento["league"]["id"]) == clean_id
                    ]
                    
                    # Actualizar caché
                    futbol_cache["ligas"][cache_key] = {
                        "data": eventos_filtrados,
                        "timestamp": datetime.now().timestamp()
                    }
                    
                    return eventos_filtrados
                else:
                    print(f"[DEBUG] Error API ({response.status}): {data.get('errors', 'Error desconocido')}")
                    return []
    except Exception as e:
        error_msg = f"Error de conexión: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        return error_msg

async def obtener_eventos_futbol_live_all() -> Union[list, str]:
    """
    Obtiene TODOS los eventos EN VIVO de fútbol sin filtrar por liga con caché.

    Returns:
        Union[list, str]: Lista de eventos en vivo o mensaje de error
    """
    cache_key = "live_all_events"
    
    # Verificar caché (TTL más corto para eventos en vivo - 10 minuto)
    if cache_key in futbol_cache["ligas"]:
        cached_data = futbol_cache["ligas"][cache_key]
        if (datetime.now().timestamp() - cached_data["timestamp"]) < 600:
            print(f"[CACHE] Todos los eventos en vivo obtenidos de caché")
            return cached_data["data"]

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-key": API_FUTBOL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    params = {
        "live": "all",
        "timezone": "America/Havana"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()

                if response.status == 200:
                    eventos = data.get("response", [])
                    
                    # Actualizar caché
                    futbol_cache["ligas"][cache_key] = {
                        "data": eventos,
                        "timestamp": datetime.now().timestamp()
                    }
                    
                    return eventos
                
                error_msg = data.get('message', 'Error desconocido en la API')
                print(f"❌ [DEBUG] Error API ({response.status}): {error_msg}")
                return f"Error en la API: {error_msg}"

    except aiohttp.ClientError as e:
        error_msg = f"Error de conexión: {str(e)}"
        print(f"💥 [DEBUG] {error_msg}")
        return error_msg
        
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        print(f"💥 [DEBUG] {error_msg}")
        return error_msg



async def seleccionar_liga_futbol(update: Update, context: CallbackContext):
    """Maneja la selección de liga y muestra partidos (live o prematch)"""
    try:
        query = update.callback_query
        await query.answer()
        callback_data = query.data

        if not callback_data.startswith("ligas_futbol_"):
            await query.message.reply_text("❌ Liga inválida")
            return

        league_id = callback_data.replace("ligas_futbol_", "")
        
        # Elegir función según el tipo de apuesta
        tipo_apuesta = context.user_data.get("betting")
        
        if tipo_apuesta == "LIVE":
            
            eventos = await obtener_eventos_futbol_live(league_id)  # Función que ya tienes
        else:
            eventos = await obtener_eventos_futbol(league_id)  # Función que ya tienes
        
        if isinstance(eventos, str):
            await query.message.reply_text(f"⚠️ {eventos}")
            return
            
        if not eventos:
            if tipo_apuesta == "LIVE":
                await query.message.reply_text(
                    "ℹ️ No hay partidos en vivo en la liga seleccionada.\n\n¿Quieres que busque por ti y te muestre algunos disponibles en vivo?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Buscar LIVE", callback_data="mostrar_todos_live")],
                        [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
                    ])
                )
            else:
                await query.message.reply_text(
                    "ℹ️ No hay partidos disponibles para esta liga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
                    ])
                )
            return

        # Construir mensaje con los eventos
        mensaje = "<b>⚽ Partidos Disponibles:</b>\n\n" if tipo_apuesta != "LIVE" else "<b>🔴 Partidos en Vivo:</b>\n\n"
        ahora = datetime.now(pytz.timezone('America/Havana'))
        
        for evento in eventos[:3]:  # Mostrar máximo 3 en selección de liga
            try:
                home = evento['teams']['home']['name']
                away = evento['teams']['away']['name']
                fecha = datetime.strptime(evento['fixture']['date'], "%Y-%m-%dT%H:%M:%S%z")
                fecha_cuba = fecha.astimezone(pytz.timezone('America/Havana'))
                venue = evento['fixture']['venue']['name']
                estado = evento['fixture']['status']['short']

                if tipo_apuesta == "LIVE":
                    mitad = "1er Tiempo" if estado == "1H" else "2do Tiempo" if estado == "2H" else "Descanso"
                    mensaje += (
                        f"<b>{home}</b>\n"
                        f"🆚\n"
                        f"<b>{away}</b>\n"
                        f"⏰ <b>Hora:</b> {fecha_cuba.strftime('%I:%M %p')}\n"
                        f"🔴 <b>¡EN VIVO!</b> - {mitad}\n"
                        f"🏟️ {venue}\n"
                        f"------------------------\n"
                    )
                else:
                    horas_restantes = (fecha_cuba - ahora).seconds // 3600
                    minutos_restantes = ((fecha_cuba - ahora).seconds % 3600) // 60
                    mensaje += (
                        f"<b>{home}</b>\n"
                        f"🆚\n"
                        f"<b>{away}</b>\n"
                        f"⏰ <b>Hora:</b> {fecha_cuba.strftime('%I:%M %p')}\n"
                        f"⏳ <b>Comienza en:</b> {horas_restantes}h {minutos_restantes}m\n"
                        f"🏟️ {venue}\n"
                        f"------------------------\n"
                    )
            except KeyError as e:
                print(f"⚠️ Error formateando evento: {e}")
                continue

        # Crear teclado con botones
        keyboard = []
        row = []
        for i, evento in enumerate(eventos):
            try:
                home = evento['teams']['home']['name']
                away = evento['teams']['away']['name']
                row.append(InlineKeyboardButton(
                    f"{home[:15]} vs {away[:15]}",
                    callback_data=f"evento_futbol_{evento['fixture']['id']}"
                ))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            except KeyError as e:
                print(f"⚠️ Error creando botón: {e}")
                continue

        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")])

        await query.message.reply_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"💥 Error en seleccionar_liga_futbol: {e}")
        await query.message.reply_text(
            "⚠️ Error al mostrar partidos.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
            ])
        )

async def mostrar_todos_partidos_live(update: Update, context: CallbackContext):
    """Muestra TODOS los partidos en vivo con paginación (5 en mensaje, 20 en botones)"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Obtener datos de paginación si existen
        page = int(context.user_data.get('live_page', 0))
        action = query.data.split('_')[-1] if '_' in query.data else None
        
        # Manejar acciones de paginación
        if action == 'prev':
            page = max(0, page - 1)
        elif action == 'next':
            page += 1
        
        # Obtener todos los partidos en vivo
        eventos = await obtener_eventos_futbol_live_all()
        
        # Manejar errores
        if isinstance(eventos, str):
            await query.edit_message_text(
                f"⚠️ Error al obtener partidos: {eventos}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
                ])
            )
            return
            
        if not eventos or not isinstance(eventos, list):
            await query.edit_message_text(
                "ℹ️ No hay partidos en vivo en este momento.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Actualizar", callback_data="mostrar_todos_live")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
                ])
            )
            return

        # Configuración de paginación
        PARTIDOS_EN_MENSAJE = 5
        BOTONES_POR_PAGINA = 20
        total_pages = (len(eventos) - 1) // BOTONES_POR_PAGINA
        start_idx = page * BOTONES_POR_PAGINA
        end_idx = (page + 1) * BOTONES_POR_PAGINA
        eventos_botones = eventos[start_idx:end_idx]
        eventos_mensaje = eventos[start_idx:start_idx + PARTIDOS_EN_MENSAJE]
        
        # Construir mensaje (solo 5 partidos)
        mensaje = (
            f"<b>🔴 PARTIDOS EN VIVO - Página {page+1}/{total_pages+1}</b>\n\n"
            f"📊 <i>Mostrando {min(PARTIDOS_EN_MENSAJE, len(eventos_mensaje))} de {len(eventos)} partidos disponibles</i>\n"
            "────────────────────\n"
        )
        
        for i, evento in enumerate(eventos_mensaje, 1):
            try:
                if not all(key in evento for key in ['teams', 'fixture']):
                    continue
                    
                home = evento['teams']['home']['name']
                away = evento['teams']['away']['name']
                fecha_str = evento['fixture']['date']
                
                # Formateo de fecha y hora
                try:
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M:%S%z")
                    fecha_cuba = fecha.astimezone(pytz.timezone('America/Havana'))
                    hora_str = fecha_cuba.strftime('%I:%M %p')
                except:
                    hora_str = "Hora no disponible"
                
                # Estado del partido
                estado = evento['fixture']['status']['short']
                estado_str = {
                    '1H': '1️⃣ 1er Tiempo',
                    '2H': '2️⃣ 2do Tiempo',
                    'HT': '⏸ Descanso',
                    'FT': '🏁 Finalizado',
                    'NS': '🔜 Por comenzar'
                }.get(estado, estado)

                # Marcador si está disponible
                goles = evento.get('goals', {})
                marcador = (
                    f" ({goles.get('home', 0)}-{goles.get('away', 0)})" 
                    if goles and estado != 'NS' 
                    else ""
                )

                mensaje += (
                    f"<b>📌 Partido {i + start_idx}</b>\n"
                    f"🏠 <b>{home}</b> {marcador}\n"
                    f"🆚 <b>{away}</b>\n"
                    f"⏰ <b>Hora:</b> {hora_str}\n"
                    f"📡 <b>Estado:</b> {estado_str}\n"
                    f"🏟 <i>{evento['fixture']['venue'].get('name', 'Estadio no disponible')}</i>\n"
                    f"────────────────────\n"
                )
            except Exception as e:
                print(f"⚠️ Error formateando evento: {e}")
                continue

        # Crear teclado con 20 botones (en filas de 2)
        keyboard = []
        row = []
        
        for i, evento in enumerate(eventos_botones, 1):
            try:
                home = evento['teams']['home']['name'][:12]
                away = evento['teams']['away']['name'][:12]
                row.append(
                    InlineKeyboardButton(
                        f"{home} 🆚 {away}",
                        callback_data=f"evento_futbol_{evento['fixture']['id']}"
                    )
                )
                
                if len(row) == 2 or i == len(eventos_botones):
                    keyboard.append(row)
                    row = []
            except Exception as e:
                print(f"⚠️ Error creando botón: {e}")
                continue

        # Botones de navegación
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data="mostrar_todos_live_prev"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages+1}", callback_data="none"))
        
        if (page + 1) * BOTONES_POR_PAGINA < len(eventos):
            nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data="mostrar_todos_live_next"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Botones de acción
        keyboard.append([
            InlineKeyboardButton("🔄 Actualizar", callback_data="mostrar_todos_live"),
            InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")
        ])

        # Guardar página actual
        context.user_data['live_page'] = page
        
        # Enviar mensaje
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"💥 Error crítico en mostrar_todos_partidos_live: {e}")
        await query.message.reply_text(
            "⚠️ Error al procesar los partidos en vivo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="deporte_soccer")]
            ])
        )


URL_EVENTOS = "https://api.the-odds-api.com/v4/sports/{}/events/"

# Zona horaria de Cuba
CUBA_TZ = pytz.timezone("America/Havana")


async def obtener_eventos_liga(sport_key, context: CallbackContext):
    """
    Obtiene eventos de una liga deportiva según los criterios especificados.
    Usa la API obtenida de la función obtener_api.
    """
    api_key = await obtener_api()

    if not api_key:
        return "❌ No hay claves API disponibles con suficientes créditos."

    ahora_utc = datetime.utcnow()

    # Intervalo de tiempo para filtrar eventos (últimas 72 horas)
    inicio_desde = ahora_utc.isoformat() + "Z"
    inicio_hasta = (ahora_utc + timedelta(hours=140)).isoformat() + "Z"

    params = {
        "apiKey": api_key,
        "startTimeFrom": inicio_desde,
        "startTimeTo": inicio_hasta,
        "dateFormat": "iso"
    }

    url = URL_EVENTOS.format(sport_key)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    eventos = await response.json()
                    context.user_data["sport_key"] = sport_key

                    # Si no hay eventos
                    if not eventos:
                        return "No hay eventos próximos en esta liga."

                    return eventos

                else:
                    print(f"Error {response.status}: {await response.text()}")
                    return f"❌ Error {response.status} al obtener eventos."

    except Exception as e:
        print(f"⚠️ Error en la solicitud: {e}")
        return "❌ Error al obtener los eventos."

async def seleccionar_liga(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        callback_data = query.data

        # Verificar que el callback_data sea válido
        if callback_data.startswith("ligas_"):
            sport_key = callback_data.replace("ligas_", "")  # Extraemos el sport_key de la liga
            context.user_data["liga_actual"] = sport_key  # Guardamos la liga seleccionada
            

            # Llamar a la función para obtener los eventos de la liga seleccionada
            eventos = await obtener_eventos_liga(sport_key, context)

            # Comprobar si la respuesta es válida
            if isinstance(eventos, str):  # Si la respuesta es un mensaje de error
                await query.answer(eventos)  # Enviamos el mensaje de error
                return

            # Obtener la hora actual
            ahora = datetime.now(pytz.utc)
            limite_inferior = ahora + timedelta(minutes=10)  # No mostrar eventos que comiencen en los próximos 30 minutos
            limite_superior = ahora + timedelta(hours=120)  # Mostrar eventos que comiencen en las próximas 240 horas

            # Filtrar eventos
            eventos_filtrados = []
            for evento in eventos:
                try:
                    hora_evento = datetime.fromisoformat(evento['commence_time'].replace("Z", "+00:00")).astimezone(pytz.utc)
                    if limite_inferior < hora_evento <= limite_superior:
                        eventos_filtrados.append(evento)
                except (KeyError, ValueError) as e:
                    print(f"Error al procesar el evento: {e}")
                    continue

            # Ordenar eventos por fecha más cercana
            eventos_filtrados.sort(key=lambda x: datetime.fromisoformat(x['commence_time'].replace("Z", "+00:00")))

            # Mostrar solo los 3 eventos más próximos en el mensaje
            texto_eventos = f"<b>Próximos eventos para la liga: {sport_key}</b>\n\n"
            for evento in eventos_filtrados[:3]:
                try:
                    team1 = evento['home_team']
                    team2 = evento['away_team']
                    hora_evento = datetime.fromisoformat(evento['commence_time'].replace("Z", "+00:00")).astimezone(pytz.utc)
                    hora_evento_cuba = hora_evento.astimezone(CUBA_TZ)
                    tiempo_restante = hora_evento_cuba - datetime.now(CUBA_TZ)

                    # Formatear el tiempo restante
                    dias = tiempo_restante.days
                    horas, minutos = divmod(tiempo_restante.seconds // 60, 60)
                    tiempo_restante_formateado = f"{dias}d {horas}h:{minutos:02d}m"

                    # Formatear la hora del evento en AM/PM
                    hora_evento_formateada = hora_evento_cuba.strftime('%I:%M %p')

                    # Construir el mensaje con el formato solicitado
                    texto_eventos += (
                        f"<blockquote>{team1}</blockquote>\n"
                        f"🆚\n"
                        f"<blockquote>{team2}</blockquote>\n"
                        f"🕒 {hora_evento_formateada} (en {tiempo_restante_formateado})\n"
                        f"-----------------------------------------------\n"
                    )
                except KeyError as e:
                    print(f"Error al procesar el evento: falta la clave {e}")
                    continue

            # Crear teclado con botones para todos los eventos filtrados
            keyboard = []
            fila = []

            for evento in eventos_filtrados:
                try:
                    team1 = evento['home_team']
                    team2 = evento['away_team']

                    # Texto del botón sin la hora
                    texto_boton = f"{team1} vs {team2}"
                    fila.append(InlineKeyboardButton(texto_boton, callback_data=f"evento_{evento['id']}"))

                    if len(fila) == 2:
                        keyboard.append(fila)
                        fila = []
                except KeyError as e:
                    print(f"Error al procesar el evento: falta la clave {e}")
                    continue

            # Agregar la última fila si no está completa
            if fila:
                keyboard.append(fila)

            # Botón para volver al menú principal
            keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=texto_eventos, reply_markup=reply_markup, parse_mode="HTML")

        else:
            await query.answer("❌ Ocurrió un error al procesar la liga seleccionada.")
            await query.edit_message_text(text="❌ Selección inválida. Intenta de nuevo.")

    except Exception as e:
        print(f"Error al seleccionar la liga: {e}")
        await query.answer("❌ Ocurrió un error inesperado.")
        await query.edit_message_text(text="❌ Ocurrió un error inesperado.")
def guardar_datos_evento(context, evento_data, market_key=None):
    """Guarda los datos del evento de forma estandarizada"""
    event_id = evento_data.get('id')
    if not event_id:
        return None
    
    # Datos base del evento
    evento_info = {
        'sport_key': evento_data.get('sport_key'),
        'sport_title': evento_data.get('sport_title', evento_data.get('league', '')),
        'home_team': evento_data.get('home_team'),
        'away_team': evento_data.get('away_team'),
        'commence_time': evento_data.get('commence_time'),
        'bookmakers': evento_data.get('bookmakers', []),
        'complete_data': evento_data  # Guardar todos los datos originales
    }
    
    # Si se especifica un market_key, lo añadimos
    if market_key:
        evento_info['market_key'] = market_key
        # Guardar también los outcomes específicos de este mercado
        for bookmaker in evento_data.get('bookmakers', []):
            if bookmaker['title'] == 'Bovada':
                for market in bookmaker['markets']:
                    if market['key'] == market_key:
                        evento_info['outcomes'] = market['outcomes']
                        break
    
    context.user_data[f'evento_{event_id}'] = evento_info
    return event_id    


# Funciones para formatear nombres de outcomes
def formato_h2h(outcome, local, visitante, *args):
    return "Equipo 1" if outcome["name"] == local else "Equipo 2" if outcome["name"] == visitante else "Empate"

def formato_spreads(outcome, local, visitante, *args):
    return f"Equipo 1 ({outcome['point']})" if outcome["name"] == local else f"Equipo 2 ({outcome['point']})"

def formato_totals(outcome, *args):
    return f"⬆️ Over ({outcome['point']})" if outcome["name"] == "Over" else f"⬇️ Under ({outcome['point']})"

def formato_team_totals(outcome, local, visitante, *args):
    return f"{'Equipo 1' if outcome['name'] == local else 'Equipo 2'} ({outcome['point']})"

def formato_jugador_simple(outcome, *args):
    return outcome["name"]

# Asignar funciones de formato
for mercado in CONFIG_MERCADOS:
    if "spread" in mercado:
        CONFIG_MERCADOS[mercado]["formato_nombre"] = formato_spreads
    elif "total" in mercado and "team" not in mercado:
        CONFIG_MERCADOS[mercado]["formato_nombre"] = formato_totals
    elif "team" in mercado and "total" in mercado:
        CONFIG_MERCADOS[mercado]["formato_nombre"] = formato_team_totals
    elif mercado.startswith("h2h"):
        CONFIG_MERCADOS[mercado]["formato_nombre"] = formato_h2h
    elif "player" in mercado:
        CONFIG_MERCADOS[mercado]["formato_nombre"] = formato_jugador_simple
    else:
        CONFIG_MERCADOS[mercado]["formato_nombre"] = lambda o, *_: o["name"]






def actualizar_mercados_en_contexto(context: CallbackContext, event_id: str, nuevo_evento: dict, mercado: str):
    """Actualiza los mercados en el contexto"""
    if "bookmakers" not in context.user_data[event_id]["data"]:
        context.user_data[event_id]["data"]["bookmakers"] = []
    
    # Buscar bookmaker Bovada
    bovada_existente = next(
        (b for b in context.user_data[event_id]["data"]["bookmakers"] if b["title"] == "Bovada"),
        None
    )
    
    bovada_nuevo = next(
        (b for b in nuevo_evento.get("bookmakers", []) if b["title"] == "Bovada"),
        None
    )
    
    if bovada_nuevo:
        if not bovada_existente:
            context.user_data[event_id]["data"]["bookmakers"].append(bovada_nuevo)
        else:
            # Actualizar mercados
            for market in bovada_nuevo["markets"]:
                existente = next(
                    (m for m in bovada_existente["markets"] if m["key"] == market["key"]),
                    None
                )
                if existente:
                    existente["outcomes"] = market["outcomes"]
                else:
                    bovada_existente["markets"].append(market)
    
    # Actualizar lista de mercados cargados
    if "loaded_markets" not in context.user_data[event_id]:
        context.user_data[event_id]["loaded_markets"] = []
    if mercado not in context.user_data[event_id]["loaded_markets"]:
        context.user_data[event_id]["loaded_markets"].append(mercado)

def extraer_mercados_disponibles(evento: dict) -> dict:
    """Extrae los mercados disponibles del evento"""
    apuestas = {}
    for bookmaker in evento.get("bookmakers", []):
        if bookmaker["title"] == "Bovada":
            for market in bookmaker["markets"]:
                # Verificar que el mercado esté en nuestra configuración
                if market["key"] in CONFIG_MERCADOS:
                    apuestas[market["key"]] = market["outcomes"]
    return apuestas

def formatear_hora_evento(hora_evento: str) -> tuple:
    """Formatea la hora del evento y tiempo restante"""
    if not hora_evento:
        return "No disponible", "No disponible"
    
    try:
        hora_dt = datetime.strptime(hora_evento, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        hora_dt = hora_dt.astimezone(cuba_tz)
        hora_str = hora_dt.strftime("%d/%m/%Y %I:%M %p")
        
        ahora = datetime.now(cuba_tz)
        tiempo_restante = hora_dt - ahora
        dias = tiempo_restante.days
        horas, segundos = divmod(tiempo_restante.seconds, 3600)
        minutos = segundos // 60
        tiempo_str = f"{dias} días, {horas}hrs:{minutos:02d}min"
        
        return hora_str, tiempo_str
    except Exception as e:
        print(f"Error formateando hora: {e}")
        return hora_evento, "Error calculando"

            

async def cargar_mercado_otros_deportes(update: Update, context: CallbackContext):
    """Manejador para cargar mercados bajo demanda"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Verificar si es un comando de carga (load_)
        if not query.data.startswith("loadO_"):
            await query.answer("❌ Acción no válida")
            return
            
        mercado_id = query.data.replace("loadO_", "")
        mercado_data = context.user_data.get(mercado_id)
        
        if not mercado_data:
            await query.answer("⚠️ Los datos del mercado han expirado")
            return
            
        # Mostrar mensaje de carga (ahora usando send_message en vez de edit)
        loading_msg = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"⏳ Cargando {CONFIG_MERCADOS.get(mercado_data['market_key'], {}).get('nombre', 'mercado')}..."
)
        
        # Obtener el mercado específico con manejo de timeout
        try:
            evento = await asyncio.wait_for(
                obtener_mercados_evento(
                    mercado_data["event_id"],
                    mercado_data["sport_key"],
                    markets=mercado_data["market_key"]
                ),
                timeout=20  # Aumentamos el timeout a 20 segundos
            )
        except asyncio.TimeoutError:
            await query.answer("❌ Tiempo de espera agotado")
            await loading_msg.edit_text("⌛ El servidor tardó demasiado en responder. Por favor intenta nuevamente.")
            return
            
        if isinstance(evento, str):  # Si hay un error
            await query.answer(f"❌ {evento}")
            await loading_msg.edit_text(f"⚠️ Error al cargar el mercado: {evento}")
            return
            
        # Procesar los resultados del mercado
        market_key = mercado_data["market_key"]
        outcomes = []
        
        # Buscar en todos los bookmakers y mercados
        for bookmaker in evento.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == market_key:
                    outcomes = market["outcomes"]
                    break
            if outcomes:
                break
                
        if not outcomes:
            await query.answer("ℹ️ No hay cuotas disponibles")
            await loading_msg.edit_text(f"⚠️ No se encontraron opciones para {CONFIG_MERCADOS[market_key]['nombre']}")
            return
            
        # Actualizar los datos en el contexto
        mercado_data.update({
            "outcomes": outcomes,
            "loaded": True,
            "last_updated": datetime.now(),
            "expires": datetime.now() + timedelta(minutes=3)
        })
        
        # Mostrar las opciones del mercado
        await mostrar_opciones_mercado_otros_deportes(update, context, mercado_id)
        
    except Exception as e:
        print(f"Error en cargar_mercado_especifico: {e}")
        try:
            await query.answer("❌ Error al cargar el mercado")
            await loading_msg.edit_text("⚠️ Ocurrió un error inesperado al cargar el mercado para otros deportes")
        except:
            pass
        
async def mostrar_opciones_mercado_otros_deportes(update: Update, context: CallbackContext, mercado_id: str):
    """Muestra las opciones disponibles para un mercado específico con diseño mejorado"""
    try:
        query = update.callback_query
        mercado_data = context.user_data.get(mercado_id)
        current_event = context.user_data.get("current_event", {})
        
        if not mercado_data or not current_event:
            await query.answer("❌ Los datos del mercado no están disponibles")
            return
            
        # Datos del evento
        home_team = current_event.get("home_team", "Local")
        away_team = current_event.get("away_team", "Visitante")
        
        # Configuración del mercado desde tu variable
        config = CONFIG_MERCADOS.get(mercado_data["market_key"], {})
        emoji_mercado = config.get("emoji", "📊")
        nombre_mercado = config.get("nombre", "Mercado")
        
        # Construir mensaje con emoji del mercado
        texto = f"""
{emoji_mercado} <b>{nombre_mercado}</b>

<blockquote>{home_team} 🆚 {away_team}</blockquote>
🔽 Selecciona una opción:
"""
        keyboard = []
        
        # Caso especial para mercados de jugadores
        if mercado_data["market_key"] in ["player_goal_scorer_anytime", 
                                        "player_first_goal_scorer",
                                        "player_last_goal_scorer",
                                        "player_to_receive_card",
                                        "player_to_receive_red_card"]:
            # Agrupar jugadores por equipos
            home_players = []
            away_players = []
            
            for i, outcome in enumerate(mercado_data["outcomes"]):
                opcion_id = f"opc_{hashlib.md5(f'{mercado_id}_{i}'.encode()).hexdigest()[:8]}"
                
                context.user_data[opcion_id] = {
                    "type": "market_outcome",
                    "event_id": mercado_data["event_id"],
                    "sport_key": mercado_data["sport_key"],
                    "market_key": mercado_data["market_key"],
                    "outcome_index": i,
                    "outcome_data": outcome,
                    "parent_market": mercado_id,
                    "expires": datetime.now() + timedelta(minutes=30)
                }
                
                player_desc = outcome.get('description', '')
                if home_team.lower() in player_desc.lower():
                    home_players.append((player_desc, outcome['price'], opcion_id))
                else:
                    away_players.append((player_desc, outcome['price'], opcion_id))
            
            # Añadir sección de jugadores locales
            keyboard.append([InlineKeyboardButton(
                f"🏠 {home_team}", 
                callback_data="info_team_home")])
            
            # Mostrar 3 jugadores por fila para mejor legibilidad
            for i in range(0, len(home_players), 3):
                row = home_players[i:i+3]
                keyboard.append([
                    InlineKeyboardButton(
                        f"{p[0].split()[-1]} {p[1]}", 
                        callback_data=f"sel_{p[2]}")
                    for p in row
                ])
            
            # Añadir separador visual
            keyboard.append([InlineKeyboardButton("─"*20, callback_data="none")])
            
            # Añadir sección de jugadores visitantes
            keyboard.append([InlineKeyboardButton(
                f"🛫 {away_team}", 
                callback_data="info_team_away")])
            
            for i in range(0, len(away_players), 3):
                row = away_players[i:i+3]
                keyboard.append([
                    InlineKeyboardButton(
                        f"{p[0].split()[-1]} {p[1]}", 
                        callback_data=f"sel_{p[2]}")
                    for p in row
                ])
            
        # Mercados con muchas opciones (como alternate_totals)
        elif len(mercado_data["outcomes"]) > 6:
            # Agrupar por tipo (Over/Under) si es un mercado de totals
            if "totals" in mercado_data["market_key"]:
                overs = []
                unders = []
                
                for i, outcome in enumerate(mercado_data["outcomes"]):
                    opcion_id = f"opc_{hashlib.md5(f'{mercado_id}_{i}'.encode()).hexdigest()[:8]}"
                    
                    context.user_data[opcion_id] = {
                        "type": "market_outcome",
                        "event_id": mercado_data["event_id"],
                        "sport_key": mercado_data["sport_key"],
                        "market_key": mercado_data["market_key"],
                        "outcome_index": i,
                        "outcome_data": outcome,
                        "parent_market": mercado_id,
                        "expires": datetime.now() + timedelta(minutes=30)
                    }
                    
                    if "Over" in outcome["name"]:
                        overs.append((outcome["point"], outcome['price'], opcion_id))
                    else:
                        unders.append((outcome["point"], outcome['price'], opcion_id))
                
                # Sección Over
                keyboard.append([InlineKeyboardButton(
                    f"⬆️ Alta", 
                    callback_data="info_over")])
                
                for i in range(0, len(overs), 2):
                    row = overs[i:i+2]
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Más({o[0]})  💰{o[1]}", 
                            callback_data=f"sel_{o[2]}")
                        for o in row
                    ])
                
                # Separador
                keyboard.append([InlineKeyboardButton("─"*15, callback_data="none")])
                
                # Sección Under
                keyboard.append([InlineKeyboardButton(
                    f"⬇️ Baja", 
                    callback_data="info_under")])
                
                for i in range(0, len(unders), 2):
                    row = unders[i:i+2]
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Menos({u[0]})  💰{u[1]}", 
                            callback_data=f"sel_{u[2]}")
                        for u in row
                    ])
            
            else:
                # Para otros mercados con muchas opciones
                for i, outcome in enumerate(mercado_data["outcomes"]):
                    opcion_id = f"opc_{hashlib.md5(f'{mercado_id}_{i}'.encode()).hexdigest()[:8]}"
                    
                    context.user_data[opcion_id] = {
                        "type": "market_outcome",
                        "event_id": mercado_data["event_id"],
                        "sport_key": mercado_data["sport_key"],
                        "market_key": mercado_data["market_key"],
                        "outcome_index": i,
                        "outcome_data": outcome,
                        "parent_market": mercado_id,
                        "expires": datetime.now() + timedelta(minutes=30)
                    }
                    
                    nombre_opcion = config["formato_nombre"](outcome, home_team, away_team)
                    callback_data = f"sel_{opcion_id}"
                    
                    # Mostrar 2 opciones por fila
                    if i % 2 == 0:
                        keyboard.append([])
                    keyboard[-1].append(InlineKeyboardButton(
                        f"{nombre_opcion} {outcome['price']}", 
                        callback_data=callback_data
                    ))
        
        # Mercados estándar (h2h, btts, etc.)
        else:
            row = []
            for i, outcome in enumerate(mercado_data["outcomes"]):
                opcion_id = f"opc_{hashlib.md5(f'{mercado_id}_{i}'.encode()).hexdigest()[:8]}"
                
                context.user_data[opcion_id] = {
                    "type": "market_outcome",
                    "event_id": mercado_data["event_id"],
                    "sport_key": mercado_data["sport_key"],
                    "market_key": mercado_data["market_key"],
                    "outcome_index": i,
                    "outcome_data": outcome,
                    "parent_market": mercado_id,
                    "expires": datetime.now() + timedelta(minutes=3)
                }
                
                nombre_opcion = config["formato_nombre"](outcome, home_team, away_team)
                callback_data = f"sel_{opcion_id}"
                
                # Usar emoji del mercado para cada opción
                button_text = f"{emoji_mercado} {nombre_opcion} {outcome['price']}"
                
                # Para mercados con pocas opciones (2-3), mostrarlas en una sola fila
                if len(mercado_data["outcomes"]) <= 3:
                    row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
                else:
                    # Para más opciones, mostrar en filas de 2
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                    row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            if row:
                keyboard.append(row)
        
        # Botón para volver con estilo consistente
        volver_callback = f"evento_{mercado_data['event_id']}"
        keyboard.append([
            InlineKeyboardButton(
                f"◀️ Volver a {nombre_mercado.split()[0]}", 
                callback_data=volver_callback)
        ])
        
        await query.edit_message_text(
            text=texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Error en mostrar_opciones_mercado_otros_deportes: {e}")
        await query.edit_message_text("❌ Error al mostrar las opciones del mercado")       
        
#otros deportes                          
def modificar_cuotas(evento):
    """
    Modifica las cuotas aplicando reducciones según rangos específicos.
    Las reducciones se aplican de forma estratégica para mantener el equilibrio en las apuestas.
    """
    if not evento:
        return evento
    
    def aplicar_reduccion(cuota_original):
        """Aplica la reducción correspondiente según el rango de la cuota"""
        cuota = float(cuota_original)
        
        if cuota < 1.1:
            return cuota  # No se modifican cuotas menores a 1.1
        
        elif 1.1 <= cuota < 1.5:
            return round(cuota - 0.1, 2)
        
        elif 1.5 <= cuota < 1.8:
            return round(cuota - 0.15, 2)
        
        elif 1.8 <= cuota < 2.1:
            return round(cuota - 0.1, 2)
        
        elif 2.1 <= cuota < 2.8:
            return round(cuota - 0.2, 2)
        
        elif 2.8 <= cuota < 3.5:
            return round(cuota - 0.25, 2)
        
        elif 3.5 <= cuota < 5.0:
            return round(cuota - 0.3, 2)
        
        elif 5.0 <= cuota < 8.0:
            return round(cuota - 0.5, 2)
        
        else:  # Para cuotas de 8.0 en adelante
            return round(cuota - 0.8, 2)
    
    # Procesamiento de las cuotas del evento
    if "bookmakers" in evento:
        for bookmaker in evento["bookmakers"]:
            if "markets" in bookmaker:
                for market in bookmaker["markets"]:
                    if "outcomes" in market:
                        for outcome in market["outcomes"]:
                            if "price" in outcome:
                                try:
                                    # Aplicar la reducción y redondear a 2 decimales
                                    outcome["price"] = aplicar_reduccion(outcome["price"])
                                except (TypeError, ValueError):
                                    # En caso de error, mantener la cuota original
                                    continue
    
    return evento
              
         
async def mostrar_mercados_evento(update: Update, context: CallbackContext):
    """Función principal que redirige a la lógica específica según el deporte"""
    try:
        query = update.callback_query
        await query.answer()
        
        if not query.data.startswith("evento_"):
            await query.answer("❌ Acción no válida")
            return

        # Obtener el deporte actual del contexto
        deporte = context.user_data.get("deporte_actual", "").lower()
        
        # Detección más robusta de fútbol
        es_futbol = deporte in ["soccer", "fútbol", "futbol", "Soccer"] or \
                   any(key in query.data.lower() for key in ["futbol", "soccer"])
        
        # Extraer el event_id correctamente (quitando prefijos)
        callback_data = query.data.replace("evento_", "")
        
        if es_futbol:
            # Para fútbol, limpiar el event_id (ej: "futbol_123" -> "123")
            event_id = callback_data.replace("futbol_", "") if callback_data.startswith("futbol_") else callback_data
            
            await mostrar_mercados_futbol(update, context, event_id, deporte)
        else:
            # Para otros deportes, usar el callback_data directamente
            event_id = callback_data
         
            await mostrar_mercados_otros_deportes_original(update, context, event_id)
            
    except Exception as e:
        print(f"Error en mostrar_mercados_evento: {e}")
        await query.edit_message_text("❌ Ocurrió un error al mostrar los mercados")

        

        

                                
        

async def mostrar_mercados_otros_deportes_original(update: Update, context: CallbackContext, event_id: str):
    try:
        query = update.callback_query
        await query.answer("🔄Cargando..")
        
        sport_key = context.user_data.get("sport_key", "")
        sport_title = context.user_data.get("sport_title", "")
        
        # Determinar el deporte actual (usando la primera parte del sport_key si es compuesto)
        deporte_actual = sport_key.split('_')[0].lower() if sport_key else ""
        
        # Verificar si es apuesta COMBINADA
        es_combinada = context.user_data.get("betting") == "COMBINADA"
        
        # Obtener datos completos del evento
        evento = await obtener_mercados_evento(event_id, sport_key)
        if isinstance(evento, str):  # Si hay error
            await query.answer(evento)
            return
            
        # Aplicar modificación de cuotas
        evento = modificar_cuotas(evento)
            
        # Guardar datos completos del evento
        saved_event_id = guardar_datos_evento(context, evento)
        
        # Estructura mejorada para current_event
        context.user_data["current_event"] = {
            "event_id": saved_event_id,
            "sport_key": sport_key,
            "sport_title": sport_title or evento.get('sport_title', ''),
            "home_team": evento.get('home_team', 'Local'),
            "away_team": evento.get('away_team', 'Visitante'),
            "commence_time": evento.get('commence_time', ''),
            "loaded_markets": ["h2h"],
            "complete_data": evento  # Guardar todos los datos
        }
        
        # Obtener mercados básicos inicialmente
        basic_markets = "h2h"  # Mercados básicos para todos los deportes
        evento = await obtener_mercados_evento(event_id, sport_key, markets=basic_markets)
        
        
        if isinstance(evento, str):  # Si hay error
            await query.answer(evento)
            return

        # Aplicar modificación de cuotas nuevamente para los mercados básicos
        evento = modificar_cuotas(evento)

        # Procesar datos del evento
        home_team = evento["home_team"]
        away_team = evento["away_team"]
        hora_evento = evento.get("commence_time", None)
        hora_str, tiempo_str = formatear_hora_evento(hora_evento)
        
        context.user_data["current_event"].update({
            "home_team": home_team,
            "away_team": away_team
        })

        # Construir mensaje principal
        texto = f"""
<blockquote>{home_team} 🆚 {away_team}</blockquote>
📅 <b>Fecha:</b> <code>{hora_str}</code>
⏳ <b>Comienza en:</b> <code>{tiempo_str}</code>

🔢 <i>Selecciona un mercado:</i>
"""

        keyboard = []
        apuestas = {}
        for bookmaker in evento.get("bookmakers", []):
            if bookmaker["title"] == "Bovada":
                for market in bookmaker["markets"]:
                    if market["key"] in CONFIG_MERCADOS:
                        apuestas[market["key"]] = market["outcomes"]

        # H2H (siempre disponible para todos los deportes)
        if "h2h" in apuestas:
            # Mostrar directamente las opciones de apuestas para h2h
            grupo_id = f"grp_{event_id[:6]}_h2h"
            context.user_data[grupo_id] = {
                "type": "market_group",
                "event_id": event_id,
                "sport_key": sport_key,
                "market_key": "h2h",
                "outcomes": apuestas["h2h"],
                "home_team": home_team,
                "away_team": away_team,
                "expires": datetime.now() + timedelta(minutes=5)
            }

            # Mostrar título del mercado h2h
            keyboard.append([InlineKeyboardButton(
                f"⚽ Ganador del Partido",
                callback_data="ignore"
            )])

            # Mostrar las opciones de apuestas (G1, X, G2)
            opciones_h2h = []
            for i, outcome in enumerate(apuestas["h2h"]):
                opcion_id = f"opc_{hashlib.md5(f'{grupo_id}_{i}'.encode()).hexdigest()[:8]}"
                callback_opcion = f"sel_{opcion_id}"
                
                context.user_data[opcion_id] = {
                    "type": "market_outcome",
                    "event_id": event_id,
                    "sport_key": sport_key,
                    "market_key": "h2h",
                    "outcome_index": i,
                    "outcome_data": outcome,
                    "home_team": home_team,
                    "away_team": away_team,
                    "expires": datetime.now() + timedelta(minutes=5)
                }

                # Formatear nombre según el tipo de outcome
                nombre_original = outcome.get("name", "").strip()
                precio = outcome.get("price", "🔒")
                
                if nombre_original.lower() == "home":
                    nombre = f"G1 💰({precio})"
                elif nombre_original.lower() == "away":
                    nombre = f"G2 💰({precio})"
                elif nombre_original.lower() == "draw":
                    nombre = f"X 💰({precio})"
                else:
                    nombre = f"{nombre_original} 💰({precio})"
                
                opciones_h2h.append(InlineKeyboardButton(
                    nombre,
                    callback_data=callback_opcion
                ))

            # Organizar las opciones en filas de 3 (G1, X, G2)
            keyboard.append(opciones_h2h[:3])  # Mostrar solo las primeras 3 opciones (Home, Draw, Away)

        # Organizar mercados por categoría según CONFIG_MERCADOS
        categorias_disponibles = set()
        mercados_por_categoria = {}
        
        # Agrupar mercados disponibles por categoría
        for mercado_key, config in CONFIG_MERCADOS.items():
            # Mostrar mercado si es para todos los deportes o específico del deporte actual
            if config['deporte'] == 'todos' or deporte_actual in config['deporte'].lower():
                # Si es combinada, solo mostrar mercados de categoría "Principales"
                if not es_combinada or (es_combinada and config['categoria'] == "Principales"):
                    categoria = config['categoria']
                    if categoria not in mercados_por_categoria:
                        mercados_por_categoria[categoria] = []
                    mercados_por_categoria[categoria].append((mercado_key, config))
                    categorias_disponibles.add(categoria)
        
        # Ordenar categorías para mostrar (Principales primero, luego otras)
        orden_categorias = ['Principales'] + sorted([c for c in categorias_disponibles if c != 'Principales'])
        
        # Mostrar mercados organizados por categoría
        for categoria in orden_categorias:
            if categoria not in mercados_por_categoria:
                continue
                
            # Agregar título de categoría (excepto para Principales que ya mostramos h2h)
            if categoria != "Principales":
                keyboard.append([InlineKeyboardButton(
                    f"📌 {categoria}",
                    callback_data="ignore"
                )])
            
            # Mostrar mercados de esta categoría
            botones_categoria = []
            for mercado_key, config in mercados_por_categoria[categoria]:
                # Saltar h2h ya que ya lo mostramos al principio
                if mercado_key == "h2h":
                    continue
                    
                if mercado_key in apuestas:
                    # Mercado ya cargado - mostrar directamente
                    grupo_id = f"grp_{event_id[:6]}_{mercado_key[:4]}"
                    callback_ver = f"verO_{grupo_id}"
                    
                    context.user_data[grupo_id] = {
                        "type": "market_group",
                        "event_id": event_id,
                        "sport_key": sport_key,
                        "market_key": mercado_key,
                        "outcomes": apuestas[mercado_key],
                        "expires": datetime.now() + timedelta(minutes=3)
                    }

                    boton = InlineKeyboardButton(
                        f"{config['emoji']} {config['nombre']}",
                        callback_data=callback_verO
                    )
                    botones_categoria.append(boton)
                else:
                    # Mercado no cargado - botón para cargarlo bajo demanda
                    mercado_id = f"mkt_{hashlib.md5(f'{event_id}_{mercado_key}'.encode()).hexdigest()[:8]}"
                    callback_load = f"loadO_{mercado_id}"
                    
                    context.user_data[mercado_id] = {
                        "type": "market_request",
                        "event_id": event_id,
                        "sport_key": sport_key,
                        "market_key": mercado_key,
                        "expires": datetime.now() + timedelta(minutes=3)
                    }

                    boton = InlineKeyboardButton(
                        f"{config['emoji']} {config['nombre']}",
                        callback_data=callback_load
                    )
                    botones_categoria.append(boton)
            
            # Organizar botones en filas de 2
            for i in range(0, len(botones_categoria), 2):
                keyboard.append(botones_categoria[i:i+2])

        callback_volver = f"ligas_{sport_key}"
        
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=callback_volver)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=texto, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        print(f"Error en mostrar_mercados_evento: {e}")
        await query.edit_message_text("❌ Ocurrió un error al mostrar los mercados")



"""
==============================
LOGICA APUESTAS FUTBOL
=============================="""

async def mostrar_mercados_futbol(update: Update, context: CallbackContext, event_id: str, sport_key: str):
    """Muestra mercados usando la nueva función de mensaje"""
    query = update.callback_query
    
    try:
        # 1. Obtener y procesar detalles del evento
        evento, home_team, away_team, hora_str, tiempo_str, match_status = await obtener_y_procesar_evento(event_id)
        
        # 2. Configurar evento en el contexto (estructura completa)
        event_key = f"evento_{event_id}"
        evento_data = {
            "event_id": event_id,
            "sport_key": sport_key,
            "sport_title": evento.get("league", {}).get("name", "Liga Desconocida"),
            "home_team": home_team,
            "away_team": away_team,
            "commence_time": evento.get("fixture", {}).get("date", ""),
            "match_status": match_status,
            "complete_data": evento,
            "bookmakers": []
        }
        context.user_data[event_key] = evento_data
        
        # 3. Obtener mercados reales
        api_success = await obtener_mercados_reales(event_id, context)
        
        # 4. Construir mensaje - FORMA CORRECTA DE LLAMAR
        texto = await construir_mensaje_partido(
            evento_data=evento_data,  # Pasar el diccionario completo
            context=context           # Pasar el contexto
        )
        
        # 5. Construir teclado de mercados
        keyboard = await construir_teclado_mercados(event_id, context, api_success)
        
        # 6. Verificar si el mensaje actual es diferente al nuevo
        current_text = query.message.text_html if hasattr(query.message, 'text_html') else query.message.text
        current_keyboard = query.message.reply_markup
        new_keyboard = InlineKeyboardMarkup(keyboard)
        
        # Solo actualizar si hay cambios
        if current_text != texto or str(current_keyboard) != str(new_keyboard):
            await query.edit_message_text(
                text=texto,
                reply_markup=new_keyboard,
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"[CRITICAL] Error en mostrar_mercados_futbol: {str(e)}")
        await query.answer("❌ Error al cargar mercados", show_alert=True)
async def obtener_y_procesar_evento(event_id: str):
    """Función optimizada para obtener y procesar detalles del evento"""
    try:
        evento = await obtener_detalles_evento(event_id)
        if not evento or isinstance(evento, str):
            raise ValueError("Evento no válido")
            
        home_team = evento.get("teams", {}).get("home", {}).get("name", "Local")
        away_team = evento.get("teams", {}).get("away", {}).get("name", "Visitante")
        commence_time = evento.get("fixture", {}).get("date", "")
        
        # Procesar estado del partido
        match_status = evento.get("fixture", {}).get("status", {}).get("short", "NS")
        elapsed = evento.get("fixture", {}).get("status", {}).get("elapsed")
        score = evento.get("score", {})
        
        # Formatear tiempo y estado
        hora_str, tiempo_str = formatear_tiempo(commence_time)
        
        return evento, home_team, away_team, hora_str, tiempo_str, {
            "status": match_status,
            "elapsed": elapsed,
            "score": score
        }
        
    except Exception as e:
        print(f"[ERROR] obtener_y_procesar_evento: {str(e)}")
        raise        
        
#hace la solicitud para obtener detalles de un partido 
async def obtener_detalles_evento(fixture_id: int) -> dict | None:
    # Verificar si el evento está en caché y es reciente
    cached_event = futbol_cache["eventos"].get(str(fixture_id))
    if cached_event and (datetime.now().timestamp() - cached_event["timestamp"]) < CACHE_TTL:
        print(f"[CACHE] Evento {fixture_id} obtenido de caché")
        return cached_event["data"]

    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"id": fixture_id}
    headers = {
        "x-rapidapi-key": API_FUTBOL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            data = response.json()

            if data.get("errors"):
                print(f"[DEBUG] Errores de la API: {data['errors']}")
                return None

            if not data.get("response"):
                print(f"[DEBUG] No se encontraron detalles del partido.")
                return None

            fixture_info = data["response"][0]
            
            
            # Actualizar caché
            futbol_cache["eventos"][str(fixture_id)] = {
                "data": fixture_info,
                "timestamp": datetime.now().timestamp()
            }
            
            return fixture_info

    except Exception as e:
        print(f"[DEBUG] Error inesperado: {e}")
        return None

async def construir_teclado_opciones(mercado_id: str, mercado_data: dict, context):
    """Versión corregida que usa event_data para estado del partido"""
    keyboard = []
    outcomes = mercado_data.get("outcomes", [])
    market_key = mercado_data["market_key"]
    
    # 1. Obtener datos del evento desde event_data
    event_data = mercado_data.get("event_data", {})
    match_status = event_data.get("match_status", {})
    status_short = match_status.get("status", "NS")
    elapsed = match_status.get("elapsed", 0)
    
    # 2. Determinar estado LIVE (misma lógica que construir_mensaje_partido)
    is_live = status_short in ["1H", "2H", "HT", "LIVE"]
    
    # 3. Obtener marcador (igual que construir_mensaje_partido)
    home_score = (
        match_status.get("score", {}).get("fulltime", {}).get("home") or
        event_data.get("complete_data", {}).get("goals", {}).get("home")
    )
    away_score = (
        match_status.get("score", {}).get("fulltime", {}).get("away") or
        event_data.get("complete_data", {}).get("goals", {}).get("away")
    )
    
    
    

    # 4. Determinar si es mercado con point
    es_mercado_con_point = any(
        mercado.lower() in market_key.lower() 
        for mercado in MERCADOS_CON_POINT
    )
    print(f"¿Mercado con point? {'SÍ' if es_mercado_con_point else 'NO'}")

    for i, outcome in enumerate(outcomes):
        opcion_id = f"opc_{hashlib.md5(f'{mercado_id}_{i}'.encode()).hexdigest()[:8]}"
        
        # 5. Extraer valores con depuración
        name = outcome.get("name", "")
        value = outcome.get("value", name)  # Usar name como fallback para value
        price = outcome.get("price", "🔒")
        point = outcome.get("point")
        handicap = outcome.get("handicap")
        
        
        # 6. Lógica de extracción mejorada para LIVE
        if es_mercado_con_point and is_live:
            point = handicap if point is None else point
            
        # 7. Formateo según reglas estrictas
        if es_mercado_con_point:
            if is_live:
                nombre_opcion = f"{value} {point} ({price})" if point else f"{value} ({price})"
                
            else:
                nombre_opcion = f"{value} ({price})"
                
        else:
            nombre_opcion = formatear_nombre_opcion_estandar(outcome, market_key, price)
            
        # 8. Guardar datos con estado y marcador
        context.user_data[opcion_id] = {
            "type": "market_outcome",
            "event_id": mercado_data["event_id"],
            "market_key": market_key,
            "outcome_index": i,
            "outcome_data": outcome,
            "parent_market": mercado_id,
            "expires": datetime.now() + timedelta(minutes=30),
            "disponible": True,
            "home_team": event_data.get("home_team", ""),
            "away_team": event_data.get("away_team", ""),
            "sport_title": event_data.get("sport_title", ""),
            "commence_time": event_data.get("commence_time", ""),
            "sport_key": event_data.get("sport_key", ""),
            "tipo_apuesta": market_key,
            "seleccion": name,
            "cuota": price,
            "point": point,
            "value": value,
            "is_live": is_live,
            "match_status": status_short,
            "elapsed_time": elapsed,
            "home_score": home_score,
            "away_score": away_score,
            "original_data": outcome
        }
        
        # 9. Agregar al teclado
        if i % 2 == 0:
            keyboard.append([])
        keyboard[-1].append(InlineKeyboardButton(nombre_opcion, callback_data=f"sel_{opcion_id}"))
    
    # 10. Botón para volver con marcador/estado
    if is_live:
        marcador = f"{home_score}-{away_score}" if home_score is not None else f"{elapsed}'"
        texto_boton = f"◀️ Volver ({marcador} {status_short})"
    else:
        texto_boton = "◀️ Volver a mercados"
    
    keyboard.append([InlineKeyboardButton(
        texto_boton,
        callback_data=f"evento_{mercado_data['event_id']}"
    )])
    # Guardar datos LIVE en el contexto para recuperarlos después
    evento_key = f"evento_{mercado_data['event_id']}"
    if evento_key not in context.user_data:
        context.user_data[evento_key] = {}
    context.user_data[evento_key].update({
        "elapsed_time": elapsed,      # Minuto actual (ej: 31)
        "home_score": home_score,     # Goles local (ej: 0)
        "away_score": away_score      # Goles visitante (ej: 0)
})
    
    
    return keyboard


def formatear_nombre_opcion_estandar(outcome, market_key, price):
    """Formateo para mercados sin point"""
    name = outcome.get("name", "")
    
    if market_key.lower() in ["h2h", "match winner"]:
        if name.lower() == "home":
            return f"🏠 Local ({price})"
        elif name.lower() == "away":
            return f"✈️ Visitante ({price})"
        elif name.lower() == "draw":
            return f"⚽ Empate ({price})"
    
    return f"{name} ({price})"



#refrescar, actualizar todos los datos, contexto, botones, mercados, mensajes 
async def refresh_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actualiza los datos del evento con mejor feedback visual"""
    query = update.callback_query
    user_id = query.from_user.id
    original_message = query.message
    await query.answer()
    
    try:
        # 1. Extraer event_id del callback
        event_id = query.data.replace("refresh_", "")
        event_key = f"evento_{event_id}"
        
        # 2. Verificar existencia del evento
        if event_key not in context.user_data:
            await original_message.edit_text("❌ Evento no encontrado")
            return

        # 3. Control de tiempo entre actualizaciones
        last_update = context.user_data.get(f"last_update_{event_key}")
        if last_update and (datetime.now() - last_update).total_seconds() < 60:
            segundos_restantes = int(60 - (datetime.now() - last_update).total_seconds())
            
            # Mensaje temporal de espera
            temp_msg = await original_message.reply_text(
                f"⏳ Actualización disponible en {segundos_restantes}s...",
                reply_to_message_id=original_message.message_id
            )
            
            # Eliminar después de 3 segundos
            await asyncio.sleep(2)
            await temp_msg.delete()
            return

        # 4. Registrar el momento de actualización
        context.user_data[f"last_update_{event_key}"] = datetime.now()
        
        # 5. Bloquear múltiples actualizaciones
        evento_data = context.user_data[event_key]
        if evento_data.get("is_updating", False):
            temp_msg = await original_message.reply_text("🔄 Actualización en curso...")
            await asyncio.sleep(2)
            await temp_msg.delete()
            return
            
        # Marcar como en actualización
        evento_data["is_updating"] = True
        
        # 6. Feedback visual de carga
        loading_msg = await original_message.reply_text(
            "🔄 <b>Actualizando datos...</b>\n"
            "⚽ " + evento_data.get("home_team", "Local") + " vs " + evento_data.get("away_team", "Visitante"),
            parse_mode="HTML"
        )
        
        try:
            # 7. Obtener datos actualizados
            start_time = datetime.now()
            nuevo_evento, home_team, away_team, hora_str, tiempo_str, nuevo_status = await obtener_y_procesar_evento(event_id)
            api_success = await obtener_mercados_reales(event_id, context)
            processing_time = (datetime.now() - start_time).total_seconds()

            # 8. Actualizar contexto
            evento_data.update({
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": nuevo_evento.get("fixture", {}).get("date", ""),
                "match_status": nuevo_status,
                "complete_data": nuevo_evento,
                "refresh_count": evento_data.get("refresh_count", 0) + 1,
                "is_updating": False
            })

            # 9. Actualizar interfaz
            await mostrar_mercados_futbol(update, context, event_id, evento_data["sport_key"])
            
            # 10. Feedback de éxito temporal
            success_msg = await original_message.reply_text(
                f"✅ <b>Actualizado en {processing_time:.1f}s</b>\n"
                f"🕒 {datetime.now().strftime('%H:%M:%S')}",
                parse_mode="HTML"
            )
            await asyncio.sleep(3)
            await success_msg.delete()
            
        except Exception as update_error:
            print(f"[ERROR] Durante la actualización: {str(update_error)}")
            evento_data["is_updating"] = False
            
            # Mensaje de error temporal
            error_msg = await original_message.reply_text(
                "❌ <b>Error al actualizar</b>\n"
                "Intenta nuevamente más tarde",
                parse_mode="HTML"
            )
            await asyncio.sleep(3)
            await error_msg.delete()
            
        finally:
            if 'loading_msg' in locals():
                await loading_msg.delete()
            
    except Exception as e:
        print(f"[ERROR GENERAL] refresh_evento: {str(e)}")
        if "evento_data" in locals():
            evento_data["is_updating"] = False
        
        # Mensaje de error crítico persistente
        await original_message.reply_text(
            "⚠️ <b>Error crítico al actualizar</b>\n"
            "Contacta con soporte si el problema persiste",
            parse_mode="HTML"
        )

    
#muestra las opciones de un mercado en especifico 
async def mostrar_opciones_mercado_futbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Versión definitiva con manejo correcto de event_data"""
    try:
        # 1. Validación básica de objetos
        if not update or not context:
            print("[ERROR] Update o Context no definidos")
            return

        query = update.callback_query
        if not query or not query.data:
            print("[ERROR] Callback_query o data no válidos")
            await query.answer("❌ Acción inválida")
            return

        # 2. Extraer ID de mercado de forma segura
        mercado_id = query.data.replace("load_", "")
        if not mercado_id or not context.user_data.get(mercado_id):
            print(f"[ERROR] Mercado {mercado_id} no encontrado")
            await query.answer("🔒 Mercado no disponible")
            return

        # 3. Mostrar mensaje de carga
        loading_msg = await query.message.reply_text("⏳ Cargando opciones...")
        await query.answer()

        # 4. Cargar datos del mercado
        if not await cargar_mercado_especifico_futbol(update, context, mercado_id):
            raise Exception("Fallo al cargar mercado")

        # 5. Obtener datos combinados del mercado y evento padre
        mercado_data = context.user_data.get(mercado_id, {})
        parent_event_key = mercado_data.get("parent_event")
        parent_event_data = context.user_data.get(parent_event_key, {})
        
        # Combinar datos manteniendo prioridad en mercado_data
        combined_data = {
            **parent_event_data,  # Datos generales del evento
            **mercado_data,       # Datos específicos del mercado
            "match_status": parent_event_data.get("match_status", {}),  # Estado siempre del evento padre
            "complete_data": parent_event_data.get("complete_data", {}) # Datos completos del evento
        }

        # 6. Construir mensaje y teclado con datos combinados
        texto = await construir_mensaje_partido(combined_data, context)
        
        keyboard = await construir_teclado_opciones(
            mercado_id=mercado_id,
            mercado_data={
                **mercado_data,
                "event_data": combined_data  # Pasamos todos los datos del evento
            },
            context=context
        )

        if not texto or not keyboard:
            raise Exception("Contenido vacío")

        # 7. Verificar si el mensaje actual es diferente al nuevo
        current_text = query.message.text_html if hasattr(query.message, 'text_html') else query.message.text
        current_keyboard = query.message.reply_markup

        # Convertir el nuevo teclado a objeto InlineKeyboardMarkup para comparación
        new_keyboard = InlineKeyboardMarkup(keyboard)
        
        # Solo actualizar si hay cambios
        if current_text != texto or str(current_keyboard) != str(new_keyboard):
            try:
                await query.edit_message_text(
                    text=texto,
                    reply_markup=new_keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"[ERROR] Al actualizar mensaje: {str(e)}")
                await query.message.reply_text(
                    text=texto,
                    reply_markup=new_keyboard,
                    parse_mode="HTML"
                )
        else:
            print("[INFO] El mensaje no ha cambiado, no se actualiza")

    except Exception as e:
        print(f"[ERROR] En mostrar_opciones: {str(e)}")
        await query.answer("❌ Error al cargar opciones", show_alert=True)
    finally:
        if 'loading_msg' in locals() and loading_msg:
            await loading_msg.delete()


#construir mensaje del mercado en especifico
async def construir_mensaje_partido(evento_data: dict, context: CallbackContext) -> str:
    """Versión mejorada que maneja todos los estados del partido incluyendo 2H"""
    try:
        # Datos básicos
        home_team = evento_data.get("home_team", "Local")
        away_team = evento_data.get("away_team", "Visitante")
        league_name = evento_data.get("sport_title", "Partido")
        market_config = CONFIG_MERCADOS.get(evento_data.get("market_key", ""), {})
        
        # Procesar estado del partido
        match_status = evento_data.get("match_status", {})
        status_short = match_status.get("status", "NS")
        elapsed = match_status.get("elapsed", 0)
        status_info = ""
        
        # Manejo de todos los estados posibles
        if status_short in ["HT"]:
            home_score = match_status.get("score", {}).get("halftime", {}).get("home", 0)
            away_score = match_status.get("score", {}).get("halftime", {}).get("away", 0)
            status_info = (
                f"🟡 <b>MEDIO TIEMPO</b> | ⏱️ Min. {elapsed}\n"
                f"📊 <b>Marcador:</b> {home_score} - {away_score}\n\n"
            )
        
        elif status_short in ["1H", "2H", "LIVE"]:  # Primer tiempo, Segundo tiempo o En vivo
            # Obtener el marcador actual (usando goals como fallback)
            home_score = (
                match_status.get("score", {}).get("fulltime", {}).get("home") or
                evento_data.get("complete_data", {}).get("goals", {}).get("home", 0)
            )
            away_score = (
                match_status.get("score", {}).get("fulltime", {}).get("away") or
                evento_data.get("complete_data", {}).get("goals", {}).get("away", 0)
            )
            
            if status_short == "1H":
                status_text = "PRIMER TIEMPO"
            elif status_short == "2H":
                status_text = "SEGUNDO TIEMPO"
            else:
                status_text = "EN VIVO"
            
            status_info = (
                f"🔴 <b>{status_text}</b> | ⏱️ Min. {elapsed}\n"
                f"📊 <b>Marcador:</b> {home_score} - {away_score}\n\n"
            )
        
        elif status_short == "FT":
            home_score = match_status.get("score", {}).get("fulltime", {}).get("home", 0)
            away_score = match_status.get("score", {}).get("fulltime", {}).get("away", 0)
            status_info = (
                f"🟢 <b>FINALIZADO</b>\n"
                f"📊 <b>Resultado:</b> {home_score} - {away_score}\n\n"
            )
        
        else:  # NS (No comenzado) u otros estados
            commence_time = evento_data.get("commence_time", "")
            if commence_time:
                try:
                    hora_dt = datetime.strptime(commence_time, "%Y-%m-%dT%H:%M:%S%z")
                    hora_str = hora_dt.strftime("%d/%m/%Y %H:%M")
                    delta = hora_dt - datetime.now(pytz.utc)
                    if delta.total_seconds() > 0:
                        dias = delta.days
                        horas, segundos = divmod(delta.seconds, 3600)
                        minutos = segundos // 60
                        status_info = f"⏳ <b>Comienza en:</b> {dias}d {horas}h:{minutos:02d}m\n\n"
                    else:
                        status_info = "🟢 El partido comenzará pronto\n\n"
                except:
                    status_info = "⏳ Hora desconocida\n\n"
            else:
                status_info = "⏳ Hora no disponible\n\n"

        # Construir mensaje final
        return (
            f"{market_config.get('emoji', '⚽')} <b>{market_config.get('nombre', 'Mercado')}</b>\n\n"
            f"<blockquote>🏠 {home_team} 🆚 {away_team} ✈️</blockquote>\n"
            f"🏆 <b>Liga:</b> {league_name}\n"
            f"{status_info}"
            f"🔽 Selecciona una opción:"
        )

    except Exception as e:
        print(f"[ERROR] construir_mensaje_partido: {str(e)}")
        # Mensaje de fallback mínimo
        return (
            f"⚽ <b>{evento_data.get('sport_title', 'Partido')}</b>\n\n"
            f"<blockquote>🏠 {home_team} 🆚 {away_team} ✈️</blockquote>\n"
            f"🔽 Selecciona una opción:"
        )
                        




             
async def obtener_mercados_reales(event_id: str, context) -> bool:
    try:
        event_key = f"evento_{event_id}"
        evento = context.user_data.get(event_key)
        if not evento:
            print("[ERROR] Evento no encontrado en el contexto")
            return False

        is_live = evento.get("match_status", {}).get("status") in ["LIVE", "1H", "2H", "HT"]
        cache_key = f"mercados_{event_id}"

        # SOLO CAMBIO: Eliminado el uso de caché para LIVE (siempre consultar API)
        if not is_live:
            cached_data = await get_cached_data(cache_key)
            if cached_data:
                print("[INFO] Datos cargados desde caché")
                evento["bookmakers"] = cached_data
                context.user_data[event_key] = evento
                return True

        print(f"[INFO] Solicitando datos a la API. LIVE: {is_live}")
        endpoint = "odds/live" if is_live else "odds"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://v3.football.api-sports.io/{endpoint}",
                headers={"x-rapidapi-key": API_FUTBOL_KEY},
                params={"fixture": event_id}
            ) as response:

                print(f"[API] Código de estado: {response.status}")
                print(f"[API] Créditos restantes: {response.headers.get('x-ratelimit-requests-remaining')}")

                if response.status != 200:
                    print(f"[API ERROR] Status: {response.status}")
                    return False

                api_data = await response.json()
                if not api_data.get('response'):
                    print("[API WARNING] Respuesta vacía")
                    return False

                response_data = api_data['response'][0]
                
                # NUEVO: Mostrar todos los mercados disponibles de la API
                print("\n" + "="*50)
                print("📊 MERCADOS DISPONIBLES EN LA API:")
                print("="*50)
                
                if is_live:
                    print("🎯 MODO LIVE - Mercados disponibles:")
                    for i, market in enumerate(response_data.get('odds', [])):
                        market_name = market.get('name', 'Sin nombre')
                        market_id = market.get('id')
                        values_count = len(market.get('values', []))
                        print(f"  {i+1}. {market_name} (ID: {market_id}) - {values_count} opciones")
                else:
                    print("📈 MODO PRE-MATCH - Bookmakers disponibles:")
                    for i, bookmaker in enumerate(response_data.get('bookmakers', [])):
                        bookmaker_name = bookmaker.get('name', 'Sin nombre')
                        bookmaker_id = bookmaker.get('id')
                        bets_count = len(bookmaker.get('bets', []))
                        print(f"  {i+1}. {bookmaker_name} (ID: {bookmaker_id}) - {bets_count} mercados")
                        
                        # Mostrar mercados específicos de cada bookmaker
                        for j, bet in enumerate(bookmaker.get('bets', [])[:5]):  # Mostrar primeros 5
                            bet_name = bet.get('name', 'Sin nombre')
                            bet_id = bet.get('id')
                            values_count = len(bet.get('values', []))
                            print(f"     └─ {bet_name} (ID: {bet_id}) - {values_count} opciones")
                        if len(bookmaker.get('bets', [])) > 5:
                            print(f"     └─ ... y {len(bookmaker.get('bets', [])) - 5} mercados más")
                
                print("="*50)

                if is_live:
                    bookmakers = [{
                        'id': 1,
                        'name': 'LiveOdds',
                        'bets': [{
                            'id': market.get('id'),
                            'name': market.get('name'),
                            'values': [{
                                'value': item.get('value'),
                                'odd': item.get('odd'),
                                'point': item.get('handicap'),
                                'suspended': item.get('suspended', False)
                            } for item in market.get('values', [])]
                        } for market in response_data.get('odds', [])]
                    }]
                else:
                    bookmakers = response_data.get('bookmakers', [])

                if not bookmakers:
                    print("[API WARNING] No hay bookmakers")
                    return False

                bookmaker = next(
                    (bm for bm in bookmakers if bm.get('name') == 'Bet365'),
                    bookmakers[0]
                )

                # NUEVO: Mostrar mercados que se están procesando
                print("\n🔄 MERCADOS QUE SE ESTÁN PROCESANDO:")
                print("-" * 30)
                
                mercados_procesados = [{
                    "title": bookmaker.get("name", "LiveOdds"),
                    "outcomes": []
                }]

                mercados_encontrados = []
                mercados_no_encontrados = []

                for bet in bookmaker.get('bets', []):
                    market_name = bet.get('name')
                    if not market_name:
                        continue

                    market_config = next(
                        (cfg for key, cfg in CONFIG_MERCADOS.items() 
                         if key.lower() == market_name.lower()), None)

                    if market_config:
                        mercados_encontrados.append(market_name)
                    else:
                        mercados_no_encontrados.append(market_name)
                        continue

                    odds = []
                    for item in bet.get('values', []):
                        if item.get('suspended', False):
                            continue

                        point = item.get('point')
                        if point is None and 'handicap' in item:
                            point = item['handicap']

                        if point is None and any(x in market_name.lower() for x in ['over', 'under', 'total']):
                            if item.get('value'):
                                try:
                                    point = float(item['value'].split()[1])
                                except (IndexError, ValueError):
                                    pass

                        odd_original = item.get("odd")
                        if odd_original is not None:
                            try:
                                odd_modificada = modificar_cuota_individual(odd_original)
                            except Exception as e:
                                print(f"[WARNING] Error modificando cuota {odd_original}: {e}")
                                odd_modificada = odd_original
                        else:
                            odd_modificada = None

                        odds.append({
                            "value": item.get("value"),
                            "odd": odd_modificada,
                            "point": str(point) if point is not None else None,
                            "suspended": False
                        })

                    mercados_procesados[0]["outcomes"].append({
                        "key": market_name,
                        "name": market_config["nombre"],
                        "odds": odds,
                        "market_id": bet.get('id'),
                        "is_live": is_live
                    })

                # Mostrar resumen de mercados procesados
                print(f"✅ PROCESADOS ({len(mercados_encontrados)}):")
                for mercado in mercados_encontrados:
                    print(f"   ✓ {mercado}")
                
                print(f"❌ NO CONFIGURADOS ({len(mercados_no_encontrados)}):")
                for mercado in mercados_no_encontrados:
                    print(f"   ✗ {mercado}")
                
                print(f"📊 TOTAL: {len(mercados_encontrados) + len(mercados_no_encontrados)} mercados encontrados")
                print("-" * 30)

                evento["bookmakers"] = mercados_procesados
                context.user_data[event_key] = evento

                if not is_live:
                    futbol_cache["eventos"][cache_key] = {
                        "data": mercados_procesados,
                        "timestamp": datetime.now().timestamp()
                    }
                    print("[CACHE] Datos guardados en caché")

                return True

    except Exception as e:
        print(f"[ERROR] obtener_mercados_reales: {str(e)}")
        traceback.print_exc()
        return False
        
async def get_cached_data(cache_key, is_live=False):
    if not is_live and cache_key in futbol_cache["eventos"]:
        cached = futbol_cache["eventos"][cache_key]
        if (datetime.now().timestamp() - cached["timestamp"]) < CACHE_TTLP:
            return cached["data"]
    return None





      
        
            
async def construir_teclado_mercados(event_id, context, api_success):
    """Construye el teclado mostrando SOLO mercados disponibles en API y configurados"""
    event_key = f"evento_{event_id}"
    evento_data = context.user_data.get(event_key, {})
    bookmakers = evento_data.get("bookmakers", [])
    
    # 1. Extraer mercados disponibles en API (en minúsculas para comparación)
    api_markets = set()
    for bookmaker in bookmakers:
        for outcome in bookmaker.get("outcomes", []):
            market_key = outcome.get("key", "").lower()
            if market_key:  # Solo agregar si tiene key válida
                api_markets.add(market_key)
    
    # 2. Organizar mercados CONFIGURADOS y DISPONIBLES por categorías
    categorias_validas = {}
    for market_key, config in CONFIG_MERCADOS.items():
        # Filtrar por deporte y disponibilidad
        if config.get('deporte') in ['soccer'] and market_key.lower() in api_markets:
            categoria = config.get('categoria', 'Otros')
            categorias_validas.setdefault(categoria, []).append((market_key, config))
    
    # 3. Construir teclado solo con categorías que tienen mercados
    keyboard = []
    for categoria, mercados in categorias_validas.items():
        # Solo agregar categoría si tiene mercados
        if mercados:
            keyboard.append([InlineKeyboardButton(
                f"📌 {categoria}",
                callback_data="ignore")])
            
            fila = []
            for market_key, config in mercados:
                mercado_id = f"mkt_{hashlib.md5(f'{event_id}_{market_key}'.encode()).hexdigest()[:8]}"
                
                # Configurar datos del mercado (siempre disponible aquí)
                context.user_data[mercado_id] = {
                    "type": "futbol_market",
                    "event_id": event_id,
                    "sport_key": evento_data["sport_key"],
                    "market_key": market_key,
                    "home_team": evento_data["home_team"],
                    "away_team": evento_data["away_team"],
                    "expires": datetime.now() + timedelta(minutes=3),
                    "parent_event": event_key,
                    "disponible": True  # Todos los que llegan aquí están disponibles
                }
                
                # Crear botón (sin 🔒, solo disponibles)
                fila.append(InlineKeyboardButton(
                    f"{config.get('emoji', '📊')} {config.get('nombre', market_key)}",
                    callback_data=f"load_{mercado_id}"))
                
                if len(fila) == 2:
                    keyboard.append(fila)
                    fila = []
            
            if fila:
                keyboard.append(fila)
    
    # 4. Mensaje si no hay mercados
    if not keyboard:
        keyboard.append([InlineKeyboardButton(
            "⚠️ No hay mercados disponibles actualmente",
            callback_data="ignore")])
    
    # 5. Botones de acción (siempre visibles)
    keyboard.append([
        InlineKeyboardButton("🔄 Actualizar", callback_data=f"refresh_{event_id}"),
        InlineKeyboardButton("🔙 Volver", callback_data=f"deporte_{evento_data['sport_key']}")
    ])
    
    return keyboard        
async def cargar_mercado_especifico_futbol(update: Update, context: CallbackContext, mercado_id: str) -> bool:
    """Versión optimizada que funciona CON TU ESTRUCTURA EXACTA de la API"""
    try:
        # 1. Verificar que el mercado existe en el contexto
        mercado_data = context.user_data.get(mercado_id)
        if not mercado_data:
            print(f"[ERROR] Mercado {mercado_id} no encontrado en user_data")
            return False

        # 2. Obtener datos FRESCOS de la API (usando TU función que sí funciona)
        event_id = mercado_data["event_id"]
        if not await obtener_mercados_reales(event_id, context):  # <-- Usamos TU función original
            print(f"[ERROR] Fallo al obtener mercados para evento {event_id}")
            return False

        # 3. Buscar las cuotas ACTUALIZADAS en la estructura QUE TU API GENERA
        event_key = f"evento_{event_id}"
        evento_actualizado = context.user_data.get(event_key)
        if not evento_actualizado:
            print(f"[ERROR] Evento {event_key} no encontrado después de actualización")
            return False

        # Buscar en bookmakers -> outcomes (estructura de TU API)
        cuotas_reales = None
        market_key = mercado_data["market_key"]
        
        for bookmaker in evento_actualizado.get("bookmakers", []):
            for outcome in bookmaker.get("outcomes", []):
                if outcome["key"] == market_key:
                    cuotas_reales = outcome["odds"]
                    break
            if cuotas_reales:
                break

        if not cuotas_reales:
            print(f"[ERROR] No se encontraron cuotas para {market_key} en bookmakers")
            return False

        # 4. Actualizar el mercado específico MANTENIENDO TU ESTRUCTURA
        mercado_data.update({
            "cuotas_reales": cuotas_reales,  # <-- Exactamente como lo necesitas
            "outcomes": [{
                "name": cuota["value"],
                "price": cuota["odd"],
                "point": cuota.get("point"),
                "description": ""
            } for cuota in cuotas_reales],
            "loaded": True,
            "disponible": True,
            "last_updated": datetime.now().isoformat()
        })

        
        return True

    except Exception as e:
        print(f"[CRITICAL] Error en cargar_mercado_especifico_futbol: {str(e)}")
        return False         
        

    
# futbol
def modificar_cuota_individual(cuota_original):
    """
    Modifica una cuota individual según los rangos establecidos.
    Si la cuota original excede 50, se ajusta a 50 antes de aplicar el descuento.
    El resultado siempre estará entre 1.001 y 50.
    Devuelve la cuota modificada como string con 2 decimales.
    """
    try:
        cuota = float(cuota_original)
        
        # Limitar la cuota máxima a 50 antes de aplicar reducción
        if cuota > 50:
            cuota = 50.0

        if cuota < 1.1:
            nueva_cuota = cuota
        elif 1.1 <= cuota < 1.5:
            nueva_cuota = cuota - 0.1
        elif 1.5 <= cuota < 1.8:
            nueva_cuota = cuota - 0.15
        elif 1.8 <= cuota < 2.1:
            nueva_cuota = cuota - 0.1
        elif 2.1 <= cuota < 2.8:
            nueva_cuota = cuota - 0.2
        elif 2.8 <= cuota < 3.5:
            nueva_cuota = cuota - 0.25
        elif 3.5 <= cuota < 5.0:
            nueva_cuota = cuota - 0.3
        elif 5.0 <= cuota < 8.0:
            nueva_cuota = cuota - 0.5
        else:
            nueva_cuota = cuota - 0.8

        # Asegurar un mínimo de 1.01
        nueva_cuota = max(1.01, nueva_cuota)
        

        return f"{nueva_cuota:.2f}"

    except (TypeError, ValueError):
        return cuota_original



    
async def manejar_error(query: CallbackQuery, mensaje: str = "❌ Ocurrió un error", delay: int = 2):
    """
    Maneja errores mostrando un mensaje al usuario y registrando el error.
    
    Args:
        query (CallbackQuery): Objeto de callback_query de Telegram.
        mensaje (str): Mensaje a mostrar al usuario (puede incluir emojis).
        delay (int): Segundos antes de ocultar la notificación (opcional).
    """
    try:
        # Notificar al usuario (con mensaje breve en la pantalla)
        await query.answer(mensaje, show_alert=False)
        
        # Opcional: Si el error es crítico, puedes enviar un mensaje completo
        if "crítico" in mensaje.lower():
            await query.message.reply_text(
                f"🚨 No puedo procesar esto ahora por: {mensaje}\n\n"
                "Por favor, inténtalo de nuevo más tarde o contacta al soporte.",
                parse_mode="Markdown"
            )
            
        # Registro detallado en consola (opcional)
        print(f"[ERROR MANEJADO] {mensaje} | Query: {query.data}")
        
    except Exception as e:
        # Fallback en caso de que falle incluso el manejo de errores
        print(f"[ERROR NO MANEJADO] {str(e)} | Query original: {query.data if query else 'N/A'}")    
        
def formatear_tiempo(commence_time: str) -> tuple:
    """
    Formatea el tiempo del partido y calcula el tiempo restante.
    Devuelve:
    - hora_formateada (str): Fecha/hora legible (ej. "02/05/2025 05:30 PM")
    - tiempo_restante (str): Tiempo hasta el partido (ej. "3d 2h:45m") o estado si ya comenzó
    """
    try:
        if not commence_time:
            return "Fecha no disponible", ""

        # Parsear la fecha (maneja múltiples formatos)
        if "T" in commence_time:
            hora_dt = datetime.strptime(commence_time, "%Y-%m-%dT%H:%M:%S%z")
        else:
            hora_dt = datetime.strptime(commence_time, "%Y-%m-%d %H:%M:%S%z")

        # Formatear fecha legible (ej. "02/05/2025 05:30 PM")
        hora_str = hora_dt.strftime("%d/%m/%Y %I:%M %p")

        # Calcular tiempo restante
        ahora = datetime.now(pytz.utc)
        if hora_dt > ahora:
            delta = hora_dt - ahora
            dias = delta.days
            horas, segundos = divmod(delta.seconds, 3600)
            minutos = segundos // 60
            tiempo_str = f"{dias}d {horas}h:{minutos:02d}m"
        else:
            tiempo_str = "En curso ⏱️"  # Para partidos ya iniciados

        return hora_str, tiempo_str

    except ValueError as e:
        print(f"[WARNING] Error formateando tiempo ({commence_time}): {str(e)}")
        # Intento alternativo para formatos diferentes
        try:
            hora_dt = datetime.fromisoformat(commence_time)
            return hora_dt.strftime("%d/%m/%Y %I:%M %p"), "Próximamente"
        except:
            return commence_time, "Horario no disponible"

    except Exception as e:
        print(f"[ERROR] Error inesperado en formatear_tiempo: {str(e)}")
        return "Fecha inválida", ""        
        
        
""" 
==============================
      FIN LOGICA MERCADOS FUTBOL
=============================="""    
    
    
    
    
    
        
        
async def obtener_mercados_evento(event_id, sport_key, markets=None):
    """Obtiene los mercados de apuestas para un evento específico otros deportes"""
    api_key = await obtener_api()
    if not api_key:
        return "❌ No hay APIs disponibles con créditos suficientes."

    params = {
        "apiKey": api_key,
        "regions": "us",
        "bookmakers": "bovada"
    }
    
    # Agregar markets a los parámetros si se especificó
    if markets:
        params["markets"] = markets

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    evento = await response.json()
                    
                    return modificar_cuotas(evento)
                else:
                    error_msg = await response.text()
                    return f"❌ Error {response.status}: {error_msg}"
    except Exception as e:
        print(f"Error en obtener_mercados_evento: {str(e)}")
        return f"❌ Error de conexión: {str(e)}"


async def handle_market_selection(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        opcion_id = query.data.replace("sel_", "")
        
        # Buscar en todas las estructuras posibles
        apuesta_data = None
        posibles_claves = [k for k in context.user_data.keys() if k.startswith(('grp_', 'mkt_'))]
        
        for clave in posibles_claves:
            data = context.user_data[clave]
            if isinstance(data, dict) and data.get("outcomes"):
                for i, outcome in enumerate(data["outcomes"]):
                    current_opcion_id = f"opc_{hashlib.md5(f'{clave}_{i}'.encode()).hexdigest()[:8]}"
                    if current_opcion_id == opcion_id:
                        apuesta_data = {
                            "market_key": data["market_key"],
                            "outcome_data": outcome,
                            "event_id": data["event_id"],
                            "sport_key": data["sport_key"],
                            "parent_key": clave,
                            "outcome_index": i,
                            **{k: v for k, v in context.user_data.get(f"evento_{data['event_id']}", {}).items() 
                               if k in ['sport_title', 'home_team', 'away_team', 'commence_time', 'elapsed_time','away_score', 'home_score']}
                        }
                        break
            if apuesta_data:
                break
            
        if not apuesta_data:
            await query.answer("❌ No se encontraron los datos de la apuesta")
            return

        # Obtener el point del outcome_data
        point = apuesta_data["outcome_data"].get("point")
        
        # Obtener el nombre original de la selección SIN MODIFICARLO
        seleccion_name = apuesta_data["outcome_data"]["name"]

        # Construir datos de la apuesta SIN FORMATEAR LA SELECCIÓN
        apuesta_seleccionada = {
            "tipo_apuesta": apuesta_data["market_key"],
            "seleccion": seleccion_name,  # Mantenemos el nombre original
            "cuota": float(apuesta_data["outcome_data"]["price"]),
            "point": point,  # Guardamos el point por separado
            "description": apuesta_data["outcome_data"].get("description", ""),
            "event_id": apuesta_data["event_id"],
            "sport_key": apuesta_data["sport_key"],
            "sport_title": apuesta_data.get("sport_title", ""),
            "home_team": apuesta_data.get("home_team", "Local"),
            "away_team": apuesta_data.get("away_team", "Visitante"),
            "commence_time": apuesta_data.get("commence_time", ""),
            "opcion_id": opcion_id,
            "parent_key": apuesta_data["parent_key"],
            "outcome_index": apuesta_data["outcome_index"],
            "elapsed_time": apuesta_data.get("elapsed_time"),
            "home_score": apuesta_data.get("home_score"),
            "away_score": apuesta_data.get("away_score"),
            "complete_data": apuesta_data
        }
        
        context.user_data["apuesta_seleccionada"] = apuesta_seleccionada
        
        if context.user_data.get("betting") == "COMBINADA":
            if "apuestas_combinadas" not in context.user_data:
                context.user_data["apuestas_combinadas"] = []
            
            context.user_data["apuestas_combinadas"].append(apuesta_seleccionada)
            
            await query.answer(f"✅ Selección agregada a apuesta combinada ({len(context.user_data['apuestas_combinadas'])})")
            await seleccion_apuesta_combinada(update, context)
        else:
            await seleccionar_apuesta(update, context, apuesta_data, opcion_id)
        
    except Exception as e:
        logger.error(f"Error en handle_market_selection: {str(e)}")
        await query.answer("❌ Error crítico al procesar")
        
        
async def seleccionar_apuesta(update: Update, context: CallbackContext, apuesta_data: dict, opcion_id: str):
    query = update.callback_query
    user = update.effective_user
    
    # Obtener datos actualizados del contexto
    apuesta_seleccionada = context.user_data.get("apuesta_seleccionada", {})
    
    if not apuesta_seleccionada:
        await query.answer("❌ Los datos de la apuesta se perdieron")
        return

    # Obtener nombres de equipos (para reemplazar Home/Away)
    home_team = apuesta_seleccionada.get('home_team', 'Home')
    away_team = apuesta_seleccionada.get('away_team', 'Away')
    seleccion_original = apuesta_seleccionada.get('seleccion', '')
    
    # Reemplazar Home/Away si aplica
    seleccion_actualizada = seleccion_original
    if 'Home' in seleccion_original:
        seleccion_actualizada = seleccion_original.replace('Home', home_team)
    elif 'Away' in seleccion_original:
        seleccion_actualizada = seleccion_original.replace('Away', away_team)
    
    # --- LÓGICA PRINCIPAL DE FORMATEO ---
    seleccion_formateada = seleccion_actualizada  # Valor por defecto

    # Configurar el mercado según el tipo de apuesta
    market_key = apuesta_seleccionada.get("tipo_apuesta", "")
    config_mercado = CONFIG_MERCADOS.get(market_key, {})
    nombre_mercado = config_mercado.get('nombre', market_key)
    emoji_mercado = config_mercado.get('emoji', '🎯')

    # Caso 1: Mercados con "point" (Over/Under, Handicap, etc.)
    if market_key in MERCADOS_CON_POINT and apuesta_seleccionada.get("point"):
        point = str(apuesta_seleccionada["point"])
        
        # Verificar si el point NO está ya en la selección
        if point not in seleccion_actualizada:
            # Limpiar cualquier número existente primero
            seleccion_limpia = re.sub(r'[\d\.\+\-]+', '', seleccion_actualizada).strip()
            seleccion_formateada = f"{seleccion_limpia} {point}"
    
    # Caso 2: Mercados de jugadores (ej: "Anytime Goal Scorer")
    elif "player" in market_key.lower():
        seleccion_formateada = apuesta_seleccionada.get("description", seleccion_actualizada)

    # Actualizar el contexto con la selección formateada
    apuesta_seleccionada['seleccion'] = seleccion_formateada
    context.user_data["apuesta_seleccionada"] = apuesta_seleccionada

    # Obtener datos del usuario desde la base de datos
    user_id = str(user.id)
    
    # Obtener balance del usuario
    usuario_data = obtener_registro("usuarios", user_id, "Balance")
    if not usuario_data:
        await query.answer("❌ No estás registrado")
        return
    
    balance_usuario = usuario_data[0]  # El balance está en la primera posición

    # Obtener bono de apuesta
    bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
    bono_disponible = bono_data[0] if bono_data else 0

    # Añadir emoji al inicio
    seleccion_formateada = f"{emoji_mercado} {seleccion_formateada}"
    
    # Construir mensaje final
    mensaje = f"""
📊 <b>SELECCIONA EL MÉTODO DE PAGO</b>

{emoji_mercado} <b>Tipo:</b> {nombre_mercado}
🏆 <b>Evento:</b> {home_team} vs {away_team}
🎯 <b>Selección:</b> {seleccion_formateada}
💰 <b>Cuota:</b> {apuesta_seleccionada.get('cuota', 'N/A')}

💳 <b>Balance disponible:</b> {balance_usuario} CUP
🎁 <b>Bono disponible:</b> {bono_disponible} CUP

🔻 Seleccione método de pago:
"""

    # Teclado de confirmación
    keyboard = [
        [InlineKeyboardButton("🎁 Usar Bono", callback_data="pago_bono"),
         InlineKeyboardButton("💲 Usar Balance", callback_data="pago_balance")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"evento_{apuesta_seleccionada['event_id']}")]
    ]
    
    # Enviar mensaje y guardar su ID
    msg = await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    # Guardar estado
    context.user_data["estado"] = "esperando_metodo_pago"
    context.user_data["last_msg_id"] = msg.message_id  # Guardar ID del mensaje
    
    # Temporizador para auto-eliminación (30 segundos)
    async def auto_eliminar_mensaje():
        await asyncio.sleep(30)  # Esperar 30 segundos
        
        # Verificar si el estado sigue siendo el mismo (no se ha avanzado)
        if context.user_data.get("estado") == "esperando_metodo_pago":
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=msg.message_id
                )
                # Opcional: enviar mensaje de que el tiempo expiró
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="⌛ Tiempo expirado para seleccionar método de pago",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Volver al menú", callback_data="menu_principal")]
                    ])
                )
                context.user_data["estado"] = None  # Resetear estado
            except Exception as e:
                print(f"Error al auto-eliminar mensaje: {e}")

    # Iniciar temporizador en segundo plano
    asyncio.create_task(auto_eliminar_mensaje())

async def manejar_metodo_pago(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        metodo_pago = query.data.replace("pago_", "")
        context.user_data["metodo_pago"] = metodo_pago
        
        # Obtener el user_id del usuario
        user_id = str(update.effective_user.id)

        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        if not usuario_data:
            await query.edit_message_text(
                "❌ No estás registrado. Usa /start para registrarte.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return

        balance = usuario_data[0]  # El balance está en la primera posición

        # Obtener bono de apuesta
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
        bono = bono_data[0] if bono_data else 0

        # Verificar si es apuesta LIVE con bono
        if context.user_data.get("betting") == "LIVE" and metodo_pago == "bono":
            await query.edit_message_text(
                "⚠️ Los partidos en vivo solo están disponibles con balance por favor recarga tu cuenta.\n\nPronto estarán disponibles con Bono.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Depositar", callback_data="show_balance")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return

        # Añadir espera solo para LIVE
        if context.user_data.get("betting") == "LIVE":
            await query.edit_message_text("⏳ Espere por favor...")
            await asyncio.sleep(1)

        # Límites de apuesta
        LIMITE_BONO = 1000
        LIMITE_BALANCE = 3000

        # Verificar si el tipo de apuesta es COMBINADA
        if context.user_data.get("betting") == "COMBINADA":
            if "apuestas_combinadas" not in context.user_data:
                await query.edit_message_text(
                    "❌ Error: No se encontraron las selecciones combinadas. Por favor, comienza de nuevo.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                    ])
                )
                return

            mensaje = (
                "<pre>🎯 Has elegido un tipo de apuesta <b>COMBINADA</b>:</pre>\n\n"
                f"📊 <b>Selecciones:</b> {len(context.user_data['apuestas_combinadas'])}\n"
                "⚠️ Asegúrate de que todas las selecciones sean correctas.\n"
                "🔻 Ingresa el monto total a apostar: \n"
                f"\n💰 <b>Tu balance disponible:</b> <code>{balance} CUP</code>"
            )
            
            msg = await query.edit_message_text(
                text=mensaje,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
        else:
            # Mensaje estándar para apuestas normales
            if metodo_pago == "bono":
                mensaje = (
                    f"<pre>🔻 Ingresa el monto a apostar con 🎁 Bono:</pre>\n\n"
                    f"😒 El monto <b>mínimo</b> es de <code>50 CUP</code>.\n"
                    f"🈷️ El monto <b>máximo</b> es de <code>{LIMITE_BONO} CUP</code>.\n\n"
                    f"💰 <b>Tu bono disponible:</b> <code>{bono} CUP</code>."
                )
            elif metodo_pago == "balance":
                mensaje = (
                    f"<pre>🔻 Ingresa el monto a apostar con 💲 Balance:</pre>\n\n"
                    f"😒 El monto <b>mínimo</b> is de <code>50 CUP</code>.\n"
                    f"🈷️ El monto <b>máximo</b> es de <code>{LIMITE_BALANCE} CUP</code>.\n\n"
                    f"💰 <b>Tu balance disponible:</b> <code>{balance} CUP</code>."
                )
            else:
                mensaje = "🔻 Ingresa el monto a apostar (mínimo 50 CUP):"

            msg = await query.edit_message_text(
                text=mensaje,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )

        # Cambiar el estado para esperar el monto de la apuesta
        context.user_data["estado"] = "esperando_monto_apuesta"
        
        # Temporizador para auto-cancelación (15 segundos)
        async def auto_cancelar():
            await asyncio.sleep(15)
            if context.user_data.get("estado") == "esperando_monto_apuesta":
                try:
                    await context.bot.delete_message(
                        chat_id=query.message.chat_id,
                        message_id=msg.message_id
                    )
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="⌛ Tiempo expirado para ingresar el monto",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Intentar nuevamente", callback_data="menu_apuestas")]
                        ])
                    )
                    context.user_data["estado"] = None
                except Exception as e:
                    print(f"Error en auto-cancelación: {e}")

        asyncio.create_task(auto_cancelar())

    except Exception as e:
        print(f"Error en manejar_metodo_pago: {e}")
        await query.edit_message_text(
            "❌ Error al procesar método de pago",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ])
        )
async def manejar_monto_apuesta(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    # Obtener datos del usuario desde la base de datos
    usuario_data = obtener_registro("usuarios", user_id, "Balance")
    if not usuario_data:
        await update.message.reply_text(
            "❌ No estás registrado. Usa /start para registrarte.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ])
        )
        return

    balance = usuario_data[0]  # El balance está en la primera posición

    # Obtener bono de apuesta
    bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
    bono = bono_data[0] if bono_data else 0

    # Obtener el método de pago seleccionado PRIMERO
    metodo_pago = context.user_data.get("metodo_pago")
    if not metodo_pago:
        await update.message.reply_text(
            "❌ Error: Selecciona un método de pago primero.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ])
        )
        return

    # Obtener el monto ingresado por el usuario
    try:
        monto = int(update.message.text)
        
        # Validar monto mínimo según método de pago
        if metodo_pago == "bono" and monto < 200:
            await update.message.reply_text(
                "❌ El mínimo para apostar con bono es de 200 CUP.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return
        elif metodo_pago == "balance" and monto < 50:
            await update.message.reply_text(
                "❌ El mínimo para apostar con balance es de 50 CUP.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return
            
    except ValueError:
        await update.message.reply_text(
            "❌ Ingresa un número válido para apostar.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ])
        )
        return

    # Límites de apuesta
    LIMITE_BONO = 1000
    LIMITE_BALANCE = 3000

    # Validar límites y fondos según el método de pago
    if metodo_pago == "bono":
        if monto > LIMITE_BONO:
            await update.message.reply_text(
                f"❌ El monto máximo para apostar con bono es de {LIMITE_BONO} CUP.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return
        if monto > bono:
            await update.message.reply_text(
                f"❌ Bono insuficiente.\n\nDisponible: {bono} CUP",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 Invitar amigos", callback_data="invitar")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return
    elif metodo_pago == "balance":
        if monto > LIMITE_BALANCE:
            await update.message.reply_text(
                f"❌ El monto máximo para apostar con balance es de {LIMITE_BALANCE} CUP.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return
        if monto > balance:
            await update.message.reply_text(
                f"❌ Balance insuficiente.\n\nDisponible: {balance} CUP",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Depositar", callback_data="show_balance")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
                ])
            )
            return

    # Guardar monto apostado
    context.user_data["monto_apostado"] = monto

    # Obtener datos de la apuesta seleccionada
    apuesta_seleccionada = context.user_data.get("apuesta_seleccionada")
    if not apuesta_seleccionada:
        await update.message.reply_text(
            "❌ Error: No se encontró la apuesta seleccionada.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ])
        )
        return

    event_id = apuesta_seleccionada.get("event_id")
    if not event_id:
        await update.message.reply_text(
            "❌ Error: No se encontró el ID del evento.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_principal")]
            ])
        )
        return

    # Obtener datos del evento según tipo de apuesta
    betting_type = context.user_data.get("betting", "PREPARTIDO")
    
    if betting_type in ["COMBINADA"]:
        evento = context.user_data.get(event_id)
        if not evento or "data" not in evento:
            await update.message.reply_text(
                "❌ Error: No se encontró la información del evento.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
                ])
            )
            return
        datos_evento = evento["data"]
    else:
        # Para PREPARTIDO - buscar en context.user_data
        evento_encontrado = None
        
        for key, data in context.user_data.items():
            if isinstance(data, dict) and data.get("event_id") == event_id:
                evento_encontrado = data
                break
        
        if not evento_encontrado:
            await update.message.reply_text(
                "❌ Error: No se encontró la información del evento.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
                ])
            )
            return
        
        # Crear estructura compatible usando siempre sport_title
        datos_evento = {
            "sport_key": evento_encontrado.get("sport_key", ""),
            "sport_title": evento_encontrado.get("sport_title", evento_encontrado.get("league", "Liga Desconocida")),
            "home_team": evento_encontrado.get("home_team", "Local"),
            "away_team": evento_encontrado.get("away_team", "Visitante"),
            "commence_time": evento_encontrado.get("commence_time", "")
        }

    # Validar datos esenciales de la apuesta
    tipo_apuesta = apuesta_seleccionada.get("tipo_apuesta")
    seleccion = apuesta_seleccionada.get("seleccion")
    cuota = apuesta_seleccionada.get("cuota")

    if not all([tipo_apuesta, seleccion, cuota]):
        await update.message.reply_text(
            "❌ Error en datos de la apuesta. Intenta nuevamente.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="menu_principal")]
            ])
        )
        return

    # Animación de carga
    loading_msg = await update.message.reply_text("🔍 Verificando datos...")
    await asyncio.sleep(1.5)
    await loading_msg.edit_text("⏳ Procesando tu apuesta...")
    await asyncio.sleep(2)

    # Preparar datos para confirmación
    context.user_data["sport_key_original"] = datos_evento['sport_key']
    sport_key = datos_evento['sport_key'].split('_')[0]
    deporte_nombre, deporte_emoji = deportes_personalizados.get(sport_key, ('FUTBOL', '⚽'))
    
    ganancia = round(monto * float(cuota), 2)
    context.user_data["ganancia"] = ganancia
    context.user_data["sport_key"] = sport_key

    # Formatear selección según tipo de mercado
    config_mercado = CONFIG_MERCADOS.get(tipo_apuesta, {})
    emoji_mercado = config_mercado.get('emoji', '🎯')
    nombre_mercado = config_mercado.get('nombre', tipo_apuesta)
    
    if tipo_apuesta in ["totals", "spreads", "alternate_totals", "alternate_spreads"] and apuesta_seleccionada.get("point"):
        seleccion_formateada = f"{seleccion} {apuesta_seleccionada.get('point')}"
    elif tipo_apuesta == "btts":
        seleccion_formateada = "Sí" if seleccion.lower() == "yes" else "No"
    elif tipo_apuesta in ["player_goal_scorer_anytime", "player_first_goal_scorer", "player_last_goal_scorer"]:
        seleccion_formateada = apuesta_seleccionada.get("description", seleccion)
    else:
        seleccion_formateada = seleccion

    seleccion_formateada = f"{emoji_mercado} {seleccion_formateada}"

    # Construir mensaje de confirmación
    mensaje = f"""
📊 <b>CONFIRMAR APUESTA</b>

{deporte_emoji} <b>Evento:</b> {datos_evento['home_team']} vs {datos_evento['away_team']}
🏆 <b>Liga:</b> {datos_evento['sport_title']}

🎯 <b>Tipo:</b> {nombre_mercado}
🔹 <b>Selección:</b> {seleccion_formateada}
💰 <b>Monto:</b> {monto} CUP ({metodo_pago.capitalize()})
📈 <b>Cuota:</b> {cuota}

🤑 <b>Ganancia potencial:</b> {ganancia} CUP
"""

    # Teclado de confirmación
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRMAR", callback_data="confirmar_apuesta")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="menu_principal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar confirmación
    confirm_msg = await loading_msg.edit_text(
        text=mensaje,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    # Temporizador para auto-cancelación
    context.user_data["confirm_msg_id"] = confirm_msg.message_id
    
    async def auto_cancelar():
        await asyncio.sleep(15)
        if "apuesta_confirmada" not in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.message.chat_id,
                    message_id=confirm_msg.message_id
                )
                await update.message.reply_text(
                    "⌛ Apuesta no confirmada (tiempo expirado)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Intentar nuevamente", callback_data="menu_apuestas")]
                    ])
                )
            except Exception as e:
                print(f"Error al auto-cancelar: {e}")

    asyncio.create_task(auto_cancelar())
    context.user_data["estado"] = None




def generar_id():
    # Obtener los últimos 4 dígitos del timestamp
    timestamp = str(int(tm.time()))[-4:]
    
    # Generar 4 letras mayúsculas aleatorias
    letras = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    # Combinar y mezclar
    id_unico = ''.join(random.sample(letras + timestamp, 6))
    
    return id_unico


async def confirmar_apuesta(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    context.user_data["apuesta_confirmada"] = True

    try:
        await _mostrar_animacion_carga(query)
        
        # Verificación inicial
        apuesta_seleccionada = context.user_data.get("apuesta_seleccionada")
        if not apuesta_seleccionada:
            await query.edit_message_text(text="❌ No se encontró la apuesta seleccionada.")
            return

        # Verificación mediante función dedicada
        event_id = apuesta_seleccionada.get("event_id")
        sport_key = apuesta_seleccionada.get("sport_key")

        if sport_key == "soccer":
            verificacion = await verificar_apuesta_futbol(context, apuesta_seleccionada)
        else:
            verificacion = await verificar_apuesta(context, user_id, apuesta_seleccionada)

        if verificacion['status'] == 'error':
            await query.edit_message_text(text=verificacion['message'])
            await asyncio.sleep(1)
            await mostrar_mercados_futbol(update, context, event_id, sport_key)
            return
            
        if verificacion['status'] == 'changed':
            await query.edit_message_text(text=verificacion['message'], parse_mode='HTML')
            
            await asyncio.sleep(1)
            await mostrar_mercados_futbol(update, context, event_id, sport_key)
            return

        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        if not usuario_data:
            await query.edit_message_text(text="❌ No estás registrado. Usa /start para registrarte.")
            return

        balance_actual, nombre_usuario = usuario_data

        # Obtener bono de apuesta
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono")
        bono_actual = bono_data[0] if bono_data else 0

        # Obtener datos esenciales del contexto
        monto = context.user_data.get("monto_apostado")
        ganancia = context.user_data.get("ganancia", 0)
        sport_key_original = context.user_data.get("sport_key_original")
        betting_type = context.user_data.get("betting", "PREPARTIDO")
        metodo_pago = context.user_data.get("metodo_pago", "")

        # Obtener datos del evento
        datos_evento = await _obtener_datos_evento(context, apuesta_seleccionada, betting_type, sport_key_original)
        if not datos_evento:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Error: No se encontró la información del evento."
            )
            return

        # Procesar pago y bonificaciones
        resultado_pago = await _procesar_pago_y_bonos_db(user_id, monto, metodo_pago, context, query)
        if not resultado_pago["success"]:
            return

        # Crear estructura de apuesta
        apuesta = await _crear_estructura_apuesta(
            context, apuesta_seleccionada, datos_evento, 
            monto, ganancia, betting_type, sport_key_original,
            resultado_pago["descuento_bono"], resultado_pago["descuento_balance"],
            user_id, nombre_usuario
        )

        # Enviar mensaje al canal y guardar apuesta
        await _enviar_notificaciones_y_guardar_apuesta_db(
            context, query, apuesta, resultado_pago["nuevo_balance"], 
            resultado_pago["nuevo_bono"], betting_type, user_id
        )

    except Exception as e:
        print(f"[ERROR] confirmar_apuesta: {str(e)}")
        await query.edit_message_text(
            "❌ Ocurrió un error al confirmar la apuesta. Por favor intenta nuevamente."
        )
# ---------------------- FUNCIONES AUXILIARES ----------------------

async def _mostrar_animacion_carga(query):
    """Muestra animación de carga mientras se procesa la apuesta"""
    loading_steps = [
        ("🔄 Preparando para confirmar tu apuesta...", 0.5),
        ("📡 Conectando con servidores...", 0.5),
        ("🔍 Validando datos...", 0.5),
        ("📊 Analizando apuesta...", 0.5),
        ("⏳ Un momento por favor...", 0.5)
    ]
    
    loading_message = await query.edit_message_text(text=loading_steps[0][0])
    for step, delay in loading_steps[1:]:
        await asyncio.sleep(delay)
        await loading_message.edit_text(text=step)

async def _limpiar_contexto_apuesta(context):
    """Elimina datos temporales de apuesta del contexto"""
    context.user_data.pop("procesando_apuesta", None)
    context.user_data.pop("apuesta_seleccionada", None)
    context.user_data.pop("monto_apostado", None)



async def _obtener_datos_evento(context, apuesta_seleccionada, betting_type, sport_key_original):
    """Obtiene los datos del evento según el tipo de apuesta (LIVE/PREPARTIDO)"""
    event_id = apuesta_seleccionada.get("event_id")
    
    # Buscar en toda la estructura de user_data
    for key, data in context.user_data.items():
        if isinstance(data, dict) and data.get("event_id") == event_id:
            # Para LIVE y PREPARTIDO usamos la misma estructura
            return {
                "sport_key": data.get("sport_key", sport_key_original),
                "sport_title": data.get("sport_title", 
                                      data.get("liga", 
                                              sport_key_original.split('_')[-1].title())),
                "home_team": data.get("home_team", "Local"),
                "away_team": data.get("away_team", "Visitante"),
                "commence_time": data.get("commence_time", ""),
                "complete_data": data  # Mantenemos todos los datos originales
            }
    
    return None
async def _procesar_pago_y_bonos_db(user_id, monto, metodo_pago, context, query):
    """Maneja toda la lógica de descuentos y bonificaciones usando la base de datos"""
    resultado = {
        "success": False,
        "descuento_bono": 0,
        "descuento_balance": 0,
        "nuevo_balance": 0,
        "nuevo_bono": 0
    }

    try:
        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre, Lider")
        if not usuario_data:
            await query.answer("❌ Usuario no encontrado en la base de datos")
            return resultado
            
        balance_actual, nombre_usuario, lider_id = usuario_data

        # Obtener bono de apuesta desde la tabla bono_apuesta
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
        bono_actual = bono_data[0] if bono_data else 0
        rollover_actual = bono_data[1] if bono_data else 0

        # Lógica de descuento  
        if metodo_pago == "bono":    
            if monto > bono_actual:  
                await context.bot.send_message(  
                    chat_id=query.from_user.id,  
                    text=f"❌ Fondos insuficientes. Bono disponible: {bono_actual} CUP",  
                    parse_mode='HTML'  
                )  
                return resultado  
              
            resultado["descuento_bono"] = monto  
            nuevo_bono = bono_actual - monto
            
            # Actualizar bono en la base de datos
            actualizar_registro("bono_apuesta", user_id, {
                "Bono": nuevo_bono,
                "Rollover_requerido": rollover_actual
            })
            resultado["nuevo_bono"] = nuevo_bono
            
        elif metodo_pago == "balance":    
            if monto > balance_actual:  
                await query.answer(  
                    f"❌ Fondos insuficientes. Balance disponible: {balance_actual} CUP",   
                    show_alert=True  
                )  
                return resultado  
              
            resultado["descuento_balance"] = monto  
            nuevo_balance = balance_actual - monto
            
            # Actualizar balance en la base de datos
            actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
            resultado["nuevo_balance"] = nuevo_balance
            
        else:    
            await query.answer("❌ Error: Método de pago no válido.")    
            return resultado  

        # Bono para el líder (si existe)
        if lider_id and lider_id != user_id:
            # Obtener datos del líder
            lider_data = obtener_registro("usuarios", str(lider_id), "Nombre, Balance")
            if lider_data:
                nombre_lider, balance_lider_actual = lider_data
                
                if metodo_pago == "bono":    
                    bono_lider = monto * 0.10
                    
                    # Obtener bono actual del líder
                    bono_lider_data = obtener_registro("bono_apuesta", str(lider_id), "Bono, Rollover_requerido")
                    bono_lider_actual = bono_lider_data[0] if bono_lider_data else 0
                    rollover_lider_actual = bono_lider_data[1] if bono_lider_data else 0
                    
                    nuevo_bono_lider = bono_lider_actual + bono_lider
                    nuevo_rollover_lider = rollover_lider_actual + (bono_lider * 4)
                    
                    # Actualizar bono del líder
                    actualizar_registro("bono_apuesta", str(lider_id), {
                        "Bono": nuevo_bono_lider,
                        "Rollover_requerido": nuevo_rollover_lider
                    })

                    # Notificación al líder
                    mensaje_lider = (  
                        f"🎉¡Bono por referido activo!🎉\n\n"  
                        f"👤 <b>Tu referido:</b> {nombre_usuario} ha hecho una apuesta con 🎁 Bono.\n"  
                        f"💰 <b>Monto apostado:</b> <code>{monto} CUP</code>\n"  
                        f"🎁 <b>Bono recibido (10%):</b> <code>{bono_lider:.2f} CUP</code>\n\n"  
                        f"💳 <b>Nuevo bono acumulado:</b> <code>{nuevo_bono_lider:.2f} CUP</code>"  
                    )  
                    await context.bot.send_message(  
                        chat_id=lider_id,  
                        text=mensaje_lider,  
                        parse_mode='HTML'  
                    )  

                elif metodo_pago == "balance":    
                    balance_lider = monto * 0.01
                    nuevo_balance_lider = balance_lider_actual + balance_lider
                    
                    # Actualizar balance del líder
                    actualizar_registro("usuarios", str(lider_id), {"Balance": nuevo_balance_lider})

                    # Notificación al líder
                    mensaje_lider = (  
                        f"🎉¡Bono por referido activo!🎉\n\n"  
                        f"👤 <b>Tu referido:</b> {nombre_usuario} ha hecho una apuesta con 💲 Balance.\n"  
                        f"💰 <b>Monto apostado:</b> <code>{monto} CUP</code>\n"  
                        f"💵 <b>Balance recibido (1%):</b> <code>{balance_lider:.2f} CUP</code>\n\n"  
                    )  
                    await context.bot.send_message(  
                        chat_id=lider_id,  
                        text=mensaje_lider,  
                        parse_mode='HTML'  
                    )  

        resultado["success"] = True
        return resultado

    except Exception as e:
        print(f"Error en _procesar_pago_y_bonos_db: {e}")
        await query.answer("❌ Error al procesar el pago.")
        return resultado


async def _crear_estructura_apuesta(context, apuesta_seleccionada, datos_evento, monto, 
                                   ganancia, betting_type, sport_key_original,
                                   descuento_bono, descuento_balance, user_id, nombre_usuario):
    """Crea la estructura completa de datos de la apuesta"""
    # Procesar tipo de apuesta
    tipo_apuesta = apuesta_seleccionada.get("tipo_apuesta")
    seleccion = apuesta_seleccionada.get("seleccion")
    point = apuesta_seleccionada.get("point")
    description = apuesta_seleccionada.get("description", "")
    
    
   

    # Obtener configuración del mercado
    config_mercado = CONFIG_MERCADOS.get(tipo_apuesta, {})
    tipo_apuesta_desc = config_mercado.get('nombre', tipo_apuesta)
    emoji_mercado = config_mercado.get('emoji', '🎯')

    # Formatear selección según tipo de mercado
    if tipo_apuesta in MERCADOS_CON_POINT and point:
        favorito_desc = f"{seleccion} {point}"
    elif tipo_apuesta == "btts":
        favorito_desc = "Sí" if seleccion.lower() == "yes" else "No"
    elif tipo_apuesta in ["player_goal_scorer_anytime", 
                         "player_first_goal_scorer",
                         "player_last_goal_scorer"]:
        favorito_desc = f"{description}" if description else seleccion
    elif tipo_apuesta in ["player_to_receive_card", 
                         "player_to_receive_red_card"]:
        emoji = "🟨" if tipo_apuesta == "player_to_receive_card" else "🟥"
        favorito_desc = f"{emoji} {description}" if description else f"{emoji} {seleccion}"
    elif tipo_apuesta in ["player_shots_on_target", 
                         "player_shots",
                         "player_assists"]:
        stat_name = {
            "player_shots_on_target": "Tiros al arco",
            "player_shots": "Tiros totales",
            "player_assists": "Asistencias"
        }.get(tipo_apuesta, "Estadística")
        favorito_desc = f"{description} - {stat_name}" if description else f"{seleccion} - {stat_name}"
    else:
        favorito_desc = seleccion

    # Añadir emoji del mercado al inicio
    favorito_desc = f"{emoji_mercado} {seleccion}"

    # Deporte y emoji
    sport_key = sport_key_original.split('_')[0]
    deporte_nombre, deporte_emoji = deportes_personalizados.get(
        sport_key, 
        ('FUTBOL', '⚽')
    )
    
    # Usar siempre sport_title para la liga
    nombre_liga = datos_evento.get("sport_title", "Liga Desconocida")
    
    fecha_inicio = datos_evento.get("commence_time", "No hay hora guardada")
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            # Convertir la fecha a hora local de Cuba (UTC-4)
            fecha_inicio_cuba = fecha_inicio - timedelta(hours=4)
            # Formatear la fecha para guardarla en el formato adecuado
            fecha_inicio = fecha_inicio_cuba.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            fecha_inicio = "Formato de fecha inválido"
    if isinstance(fecha_inicio, datetime):    
        print("COMMENCE TIME a guardar", fecha_inicio)
   
    

    return {
        "event_id": apuesta_seleccionada.get("event_id"),
        "usuario_id": user_id,
        "fecha_realizada": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "fecha_inicio": fecha_inicio,
        "deporte": f"{deporte_nombre}",
        "liga": nombre_liga,
        "partido": f"{datos_evento.get('home_team', 'Desconocido')} 🆚 {datos_evento.get('away_team', 'Desconocido')}",
        "tipo_apuesta": tipo_apuesta_desc,
        "sport_key": sport_key_original,
        "favorito": favorito_desc,
        "monto": monto,
        "cuota": apuesta_seleccionada.get("cuota"),
        "ganancia": ganancia,
        "estado": "⌛Pendiente",
        "bono": descuento_bono,
        "balance": descuento_balance,
        "id_ticket": generar_id(),
        "betting": betting_type,
        "mensaje_canal_url": "",
        "mensaje_canal_id": ""
    }
    

async def _enviar_notificaciones_y_guardar_apuesta_db(context, query, apuesta, nuevo_balance, nuevo_bono, betting_type, user_id):
    """Envía las notificaciones al canal y al usuario con formato profesional"""
    # Configuración inicial
    separador = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    
    # Emojis según tipo de apuesta
    ticket_emoji = {
        "LIVE": "🔴 𝙇𝙄𝙑𝙀 𝘼𝙋𝙐𝙀𝙎𝙏𝘼 🔴",
        "COMBINADA": "🔵 𝘾𝙊𝙈𝘽𝙄𝙉𝘼𝘿𝘼 🔵",
        "PREPARTIDO": "🕓 𝙋𝙍𝙀𝙋𝘼𝙍𝙏𝙄𝘿𝙊 🕓"
    }.get(betting_type, "🎟️ 𝙏𝙄𝘾𝙆𝙀𝙏 🎟️")

    # Emoji del tipo de apuesta
    config_mercado = CONFIG_MERCADOS.get(apuesta["tipo_apuesta"].lower(), {})  
    emoji_apuesta = config_mercado.get('emoji', '🎯')

    # Método de pago
    metodo_pago = f"🎁 𝘽𝙤𝙣𝙤: {apuesta['bono']} 𝘾𝙐𝙋" if apuesta['bono'] > 0 else f"💰 𝘽𝙖𝙡𝙖𝙣𝙘𝙚: {apuesta['balance']} 𝘾𝙐𝙋"

    # Bloque LIVE (si aplica)
    live_box = ""
    if betting_type == "LIVE" and "apuesta_seleccionada" in context.user_data:
        apuesta_sel = context.user_data["apuesta_seleccionada"]
        if apuesta_sel.get("elapsed_time") or apuesta_sel.get("home_score"):
            live_box = f"""
┌───────────────────────┐
│ ⏱️  𝙈𝙞𝙣𝙪𝙩𝙤: {apuesta_sel.get('elapsed_time', '--')}'
│ 📊  𝙈𝙖𝙧𝙘𝙖𝙙𝙤𝙧: {apuesta_sel.get('home_score', '?')}-{apuesta_sel.get('away_score', '?')}
└───────────────────────┘
"""

    # Mensaje para el canal (formato profesional)
    mensaje_canal = f"""
<b>{ticket_emoji}</b>
{separador}
👤 <b>Usuario:</b> {query.from_user.first_name}
🆔 <b>ID:</b> <code>{query.from_user.id}</code>

{emoji_apuesta} <b>Tipo:</b> 
└ {apuesta['tipo_apuesta']}

{metodo_pago}

{live_box if betting_type == "LIVE" else ""}
⚽ <b>Deporte:</b> 
└ {apuesta['deporte']}

🏆 <b>Liga:</b> 
└ {apuesta['liga']}

⚔️ <b>Partido:</b> 
└ {apuesta['partido']}

🎯 <b>Selección:</b> 
└ {apuesta['favorito']}

💵 <b>Monto:</b> <code>{apuesta['monto']} 𝘾𝙐𝙋</code>
📈 <b>Cuota:</b> <code>{apuesta['cuota']}</code>
💰 <b>Ganancia:</b> <code>{apuesta['ganancia']} 𝘾𝙐𝙋</code>

{separador}
🆔 <b>Ticket ID:</b> <code>{apuesta['id_ticket']}</code>
"""

    # Envío al canal
    mensaje_canal_obj = await context.bot.send_message(  
        chat_id=CANAL_TICKET,  
        text=mensaje_canal,  
        parse_mode="HTML"  
    )

    # Guardar URL del mensaje
    chat_id_str = str(CANAL_TICKET).replace('-100', '')  
    apuesta["mensaje_canal_url"] = f"https://t.me/c/{chat_id_str}/{mensaje_canal_obj.message_id}"  
    apuesta["mensaje_canal_id"] = mensaje_canal_obj.message_id  

    # Guardar en historial
    # Ahora (usando DB):
    exito = guardar_apuesta_en_db(apuesta)
    if exito:
        print("✅ Apuesta guardada correctamente")
    else:
        print("❌ Error al guardar la apuesta")

    # Mensaje para el usuario
    mensaje_usuario = f"""
<b>✅ 𝘼𝙋𝙐𝙀𝙎𝙏𝘼 𝘾𝙊𝙉𝙁𝙄𝙍𝙈𝘼𝘿𝘼</b>
{separador}
{emoji_apuesta} <b>Tipo:</b> {apuesta['tipo_apuesta']}

{live_box if betting_type == "LIVE" else ""}
⚽ <b>Deporte:</b> {apuesta['deporte']}
🏆 <b>Liga:</b> {apuesta['liga']}
⚔️ <b>Partido:</b> {apuesta['partido']}
🎯 <b>Selección:</b> {apuesta['favorito']}

📊 <b>Detalles:</b>
└ 💰 <b>Monto:</b> {apuesta['monto']} 𝘾𝙐𝙋
└ 📈 <b>Cuota:</b> {apuesta['cuota']}
└ 💵 <b>Ganancia:</b> {apuesta['ganancia']} 𝘾𝙐𝙋

{separador}
💳 <b>Balance restante:</b> <code>{nuevo_balance} 𝘾𝙐𝙋</code>
🎁 <b>Bono restante:</b> <code>{nuevo_bono} 𝘾𝙐𝙋</code>

🆔 <b>Ticket ID:</b> <code>{apuesta['id_ticket']}</code>
🍀 <i>¡Buena suerte!</i>
"""

    # Teclado para el usuario
    keyboard = [  
        [InlineKeyboardButton("🗃️ Mis Apuestas", callback_data="mis_apuestas"),  
         InlineKeyboardButton("🚩 Ver en Canal", url=apuesta["mensaje_canal_url"])],  
        [InlineKeyboardButton("🔄 Volver a apostar", callback_data="mostrar_tipos_apuestas")]  
    ]  
    
    await query.answer(f"✅ Apuesta confirmada: {apuesta['monto']} CUP")  
    await query.edit_message_text(  
        text=mensaje_usuario,  
        reply_markup=InlineKeyboardMarkup(keyboard),  
        parse_mode="HTML"  
    )

    
            
async def verificar_apuesta_futbol(context: CallbackContext, apuesta_seleccionada: dict) -> dict:  
    
    TOLERANCIA_CUOTA = 0.05
    TOLERANCIA_POINT = 0.01  

    def normalizar_seleccion(market_key, selection_text, home_team, away_team):
        def eliminar_emojis(texto):
            return re.sub(r'[\U00010000-\U0010ffff]', '', texto)

        clean_text = eliminar_emojis(selection_text).strip().lower()
        
        # Caso especial para Double Chance (todas sus variaciones)
        if market_key.lower() in ["double chance", "doble oportunidad"]:
            # Primero normalizamos los separadores (convertir todos a '/')
            clean_text = clean_text.replace(' or ', '/').replace(' y ', '/')
            
            parts = [p.strip() for p in clean_text.split('/')]
            normalized_parts = []
            
            for part in parts:
                if part in home_team.lower():
                    normalized_parts.append('home')
                elif part in away_team.lower():
                    normalized_parts.append('away')
                elif part in ['draw', 'empate', 'x', 'tie']:
                    normalized_parts.append('draw')
                else:
                    # Intenta reconocer patrones como "1X", "X2", etc.
                    if part == '1x':
                        normalized_parts.extend(['home', 'draw'])
                    elif part == 'x2':
                        normalized_parts.extend(['draw', 'away'])
                    elif part == '12':
                        normalized_parts.extend(['home', 'away'])
                    else:
                        normalized_parts.append(part)
            
            # Ordenar las partes para consistencia (home siempre primero, luego draw, luego away)
            order = {'home': 0, 'draw': 1, 'away': 2}
            normalized_parts.sort(key=lambda x: order.get(x, 3))
            
            return '/'.join(normalized_parts)
        
        # Resto de la lógica original para otros mercados...
        if clean_text in home_team.lower():
            return 'home'
        if clean_text in away_team.lower():
            return 'away'

        if market_key in MERCADOS_CON_POINT:
            if any(x in clean_text for x in ['over', 'under']):
                return clean_text.split()[0]
            match = re.search(r'([+-]?\d+\.?\d*)', clean_text)
            return match.group(1) if match else None

        mapeo = {
            'home': 'home', 'local': 'home', '1': 'home',
            'away': 'away', 'visitante': 'away', '2': 'away',
            'draw': 'draw', 'empate': 'draw', 'x': 'draw', 'tie': 'draw'
        }

        return mapeo.get(clean_text, clean_text)

    def debug_markets(evento, market_filter=None):  
        print("\n[DEBUG] MERCADOS DISPONIBLES:")  
        for bookmaker in evento.get("bookmakers", []):  
            print(f"\nBookmaker: {bookmaker.get('title')}")  
            for outcome in bookmaker.get("outcomes", []):  
                if market_filter and outcome.get('key').lower() != market_filter.lower():  
                    continue  
                print(f"\n  [MARKET] {outcome.get('key')} (ID:{outcome.get('market_id')})")  
                print(f"  Nombre: {outcome.get('name')}")  
                for odd in outcome.get("odds", []):  
                    print(f"    - {odd.get('value')}: {odd.get('odd')} " +   
                          f"(Point: {odd.get('point')}, Susp: {odd.get('suspended')})")  

    try:  
    
        
        
        event_id = apuesta_seleccionada.get('event_id')  
        if not event_id:  
            return {'status': 'error', 'message': "❌ Falta ID del evento"}  

        event_key = f"evento_{event_id}"  
        market_key = apuesta_seleccionada.get('tipo_apuesta')  
        selection_text = apuesta_seleccionada.get('seleccion', '')  

        if not market_key or not selection_text:  
            return {'status': 'error', 'message': "❌ Datos incompletos de la apuesta vuelve a intentarlo"}  

        if not await obtener_mercados_reales(event_id, context):  
            return {'status': 'error', 'message': "❌ Error actualizando mercados"}  

        evento = context.user_data.get(event_key)  
        
        if not evento:  
            return {'status': 'error', 'message': "❌ Evento no encontrado"}  
            
            
        # Verificación robusta del estado del partido
        

# Bloque de verificación (colocar al INICIO de tu función)
        match_status = evento.get("complete_data", {}).get("fixture", {}).get("status", {})
        status_long = str(match_status.get("long", "")).lower()
        status_short = str(match_status.get("short", "")).lower()
        elapsed = match_status.get("elapsed", 0)
        print(f"[DEBUG] Estado: {match_status} | Long: {status_long} | Short: {status_short} | Minuto: {elapsed}")

# Verificación combinada
        # Primero verifica si elapsed es None (partido no comenzado)
        if elapsed is None:
    # Partido no ha comenzado, no está avanzado
            pass
        elif elapsed >= 90:
            return {'status': 'error', 'message': "⛔ No puedes apostar, partido muy avanzado"}
            
        
        # --- NUEVA VERIFICACIÓN: Detectar anomalías en cuotas del favorito ---
        if elapsed and elapsed > 0:  # Solo si el partido ha comenzado
            print("[DEBUG] Ejecutando verificación de anomalía...")
            anomalia_result = await detectar_anomalia_favorito(
                evento,
                apuesta_seleccionada.get('tipo_apuesta'),
    "",  # No es necesario pasar selection_text si no se usa
                apuesta_seleccionada.get('seleccion')  # Ya normalizado
)
            print(f"[DEBUG] Resultado anomalía: {anomalia_result}")

            if anomalia_result.get('anomalia'):
                print(f"[ANOMALIA] {anomalia_result.get('message')}")
                return {
                    'status': 'error',
                    'message': "⚠️ Anomalía detectada. No se puede apostar a este partido en este momento.",
                    'debug_info': anomalia_result.get('debug_info', {})
        }


        if (any(estado in status_long.lower() for estado in ESTADOS_FINALIZADOS) or
    any(estado in status_short.lower() for estado in ESTADOS_FINALIZADOS)):
            return {'status': 'error', 'message': "⛔ Partido finalizado o cancelado"}

        

        home_team = evento.get("home_team", "Home")  
        away_team = evento.get("away_team", "Away")  

        normalized_selection = normalizar_seleccion(  
            market_key,   
            selection_text,  
            home_team,  
            away_team  
        )  
        point = apuesta_seleccionada.get('point') or (  
            normalized_selection if market_key in MERCADOS_CON_POINT else None  
        )  

        print(f"\n[DEBUG] DATOS DE BÚSQUEDA:")  
        print(f"Market: {market_key}")  
        print(f"Original: '{selection_text}'")  
        print(f"Normalized: '{normalized_selection}'")  
        print(f"Point: {point}")  
        print(f"Teams: {home_team} vs {away_team}")  

        match_found = None  
        for bookmaker in evento.get("bookmakers", []):  
            for outcome in bookmaker.get("outcomes", []):  
                if outcome.get("key", "").lower() == market_key.lower():  
                    for odd in outcome.get("odds", []):  
                        print(f"\n[DEBUG COMPARACIÓN] Analizando odd: {odd.get('value')} (point: {odd.get('point')})")  
                        if market_key in MERCADOS_CON_POINT:  
                            try:  
                                odd_point = float(odd.get("point", 0)) if odd.get("point") else None  
                                apuesta_point = float(point) if point else None  
                                if (odd_point is not None and apuesta_point is not None and   
                                    abs(odd_point - apuesta_point) <= TOLERANCIA_POINT and  
                                    str(odd.get("value", "")).lower() == str(normalized_selection).lower()):  
                                    match_found = odd  
                                    break  
                            except (ValueError, TypeError):  
                                if (str(odd.get("point")) == str(point) and   
                                    str(odd.get("value", "")).lower() == str(normalized_selection).lower()):  
                                    match_found = odd  
                                    break  
                        elif str(odd.get("value", "")).lower() == str(normalized_selection).lower():  
                            match_found = odd  
                            break  
                    if match_found:  
                        break  
            if match_found:  
                break  

        if not match_found:  
            debug_markets(evento, market_key)  
            return {  
                'status': 'error',  
                'message': "🔒 Mercado no disponible. Intenta nuevamente en unos minutos, 🔄 CARGANDO MERCADOS....",  
                'debug_info': {  
                    'normalized': normalized_selection,  
                    'point': point,  
                    'teams': f"{home_team} vs {away_team}"  
                }  
            }  

        if match_found.get('suspended', False):  
            return {  
                'status': 'error',  
                'message': "⛔ Cuota suspendida temporalmente... 🔄Cargando mercados disponibles",  
                'detalles': match_found  
            }  

        cuota_original = float(apuesta_seleccionada.get('cuota', 0))  
        cuota_actual = float(match_found.get('odd', 0))  
        diferencia = abs(cuota_actual - cuota_original)  
        cambio = cuota_actual - cuota_original  
        porcentaje = (diferencia / cuota_original) * 100  

        if diferencia > TOLERANCIA_CUOTA:  
            if cambio > 0:  
                return {  
                    'status': 'ok',  
                    'message': f"📈 Cuota mejoró a {cuota_actual:.2f} (+{porcentaje:.1f}%)",  
                    'nueva_cuota': cuota_actual  
                }  
            else:  
                return {  
                    'status': 'error',  
                    'message': f"⛔ La cuota cambió a {cuota_actual:.2f} (-{porcentaje:.1f}%). Vuelve a intentarlo",  
                    'nueva_cuota': cuota_actual  
                }  

        return {  
            'status': 'ok',  
            'message': "✅ Apuesta verificada",  
            'cuota_actual': cuota_actual,  
            'detalles': match_found  
        }  

    except Exception as e:  
        print(f"\n[ERROR] {str(e)}")  
        import traceback  
        traceback.print_exc()  
        return {  
            'status': 'error',  
            'message': "🔧 Error técnico al verificar",  
            'error': str(e)  
        }    
    
async def detectar_anomalia_favorito(evento: dict, market_key: str, selection_text: str, apuesta_selection: str) -> dict:
    """
    Detecta anomalías cuando se apuesta al equipo que va ganando con cuota muy baja
    Utiliza el mismo método de búsqueda de cuotas que verificar_apuesta_futbol
    """
    try:
        # 1. Extraer datos básicos del evento
        complete_data = evento.get("complete_data", {})
        if not complete_data:
            return {'anomalia': False, 'message': "Datos del evento incompletos"}
            
        fixture = complete_data.get("fixture", {})
        status = fixture.get("status", {})
        elapsed = status.get("elapsed")
        home_score = complete_data.get("goals", {}).get("home")
        away_score = complete_data.get("goals", {}).get("away")
        teams = complete_data.get("teams", {})
        home_team = teams.get("home", {}).get("name", "")
        away_team = teams.get("away", {}).get("name", "")
        
        # 2. Validaciones básicas
        if not all([home_team, away_team]):
            return {'anomalia': False, 'message': "Nombres de equipos no disponibles"}
            
        if None in [elapsed, home_score, away_score]:
            return {'anomalia': False, 'message': "Datos del marcador incompletos"}

        # 3. Determinar equipo líder
        leader_team = None
        if home_score > away_score:
            leader_team = home_team
        elif away_score > home_score:
            leader_team = away_team
        else:
            return {'anomalia': False, 'message': "Partido está empatado"}

        # 4. Buscar cuota del líder usando el mismo método que verificar_apuesta_futbol
        def buscar_cuota_equipo(team_name):
            for bookmaker in evento.get("bookmakers", []):
                for outcome in bookmaker.get("outcomes", []):
                    if outcome.get("key", "").lower() in ["h2h", "match winner", "fulltime result"]:
                        for odd in outcome.get("odds", []):
                            if str(odd.get("value", "")).lower() == str(team_name).lower():
                                return float(odd.get("odd", 0)) if odd.get("odd") else None
            return None

        leader_odds = buscar_cuota_equipo(leader_team)

        if leader_odds is None:
            # Intentar buscar con nombre normalizado (home/away) como fallback
            normalized_leader = "home" if leader_team == home_team else "away"
            leader_odds = buscar_cuota_equipo(normalized_leader)
            
            if leader_odds is None:
                return {
                    'anomalia': False,
                    'message': f"No se encontraron cuotas para {leader_team}",
                    'debug_info': {
                        'current_score': f"{home_score}-{away_score}",
                        'minute': elapsed,
                        'leader_team': leader_team,
                        'error': 'Cuotas no encontradas'
                    }
                }

        # 5. Detección de anomalía
        ANOMALIA_THRESHOLD = 1.9  # Ajustar según necesidad
        is_anomalia = (
            str(apuesta_selection).lower() == str(leader_team).lower() and 
            leader_odds >= ANOMALIA_THRESHOLD
        )

        debug_info = {
            'current_score': f"{home_score}-{away_score}",
            'minute': elapsed,
            'leader_team': leader_team,
            'apuesta_a': apuesta_selection,
            'leader_odds': leader_odds,
            'threshold': ANOMALIA_THRESHOLD,
            'is_anomaly': is_anomalia,
            'search_method': 'same_as_verification'
        }

        return {
            'anomalia': is_anomalia,
            'message': (
                f"⚠️ Anomalía: {leader_team} va ganando {home_score}-{away_score} con cuota {leader_odds}" 
                if is_anomalia else 
                f"✅ Apuesta válida ({apuesta_selection})"
            ),
            'debug_info': debug_info
        }

    except Exception as e:
        error_msg = f"Error en verificación: {str(e)}"
        print(f"[ERROR] detectar_anomalia_favorito: {error_msg}")
        return {
            'anomalia': False,
            'message': error_msg,
            'debug_info': {'error': str(e)}
        }
async def verificar_apuesta(context: CallbackContext, user_id: str, apuesta_seleccionada: dict) -> dict:
    """
    Verifica todos los aspectos de una apuesta antes de confirmarla.
    Devuelve un dict con:
    - 'status': 'ok'|'error'|'changed'
    - 'message': Mensaje para el usuario
    - 'evento_actualizado': Datos actualizados del evento (si hubo cambios)
    - 'nueva_cuota': Nueva cuota (si hubo cambios)
    """
    try:
        betting_type = context.user_data.get("betting", "PREPARTIDO").upper()
        
        # Si es apuesta prepartido, omitir verificación y aprobar directamente
        if betting_type == "PREPARTIDO":
            return {
                'status': 'ok',
                'message': "✅ Apuesta prepartido: verificación omitida."
            }

        # Obtener datos básicos
        event_id = apuesta_seleccionada.get("event_id")
        sport_key_original = context.user_data.get("sport_key_original")
        
        if not event_id or not sport_key_original:
            return {
                'status': 'error',
                'message': "❌ Error: No se pudo obtener la información del evento."
            }

        # 1. Buscar datos del evento en el contexto - nueva forma unificada
        evento = None
        event_key = f"evento_{event_id}"
        
        # Primero buscar en la estructura directa
        if event_key in context.user_data:
            evento = context.user_data[event_key]
        else:
            # Buscar en toda la estructura de user_data por event_id
            for key, data in context.user_data.items():
                if isinstance(data, dict) and data.get("event_id") == event_id:
                    evento = data
                    break

        if not evento:
            return {
                'status': 'error',
                'message': "❌ Error: La información del evento ha expirado."
            }

        # 2. Obtener datos actualizados de la API solo para LIVE
        evento_actualizado = None
        if betting_type == "LIVE":
            evento_actualizado = await obtener_mercados_evento(event_id, sport_key_original)
            
            # Verificar si la API devolvió un error
            if isinstance(evento_actualizado, str):
                return {
                    'status': 'error',
                    'message': evento_actualizado
                }
                    
            # 3. Verificar estado del evento
            if evento_actualizado.get("completed", False):
                return {
                    'status': 'error',
                    'message': "❌ El evento ya ha finalizado. No puedes apostar."
                }
        else:
            # Para PREPARTIDO usamos los datos del contexto
            evento_actualizado = evento

        # 4. Verificar datos específicos de la apuesta
        cuota_original = apuesta_seleccionada.get("cuota")
        tipo_apuesta = apuesta_seleccionada.get("tipo_apuesta")
        seleccion = apuesta_seleccionada.get("seleccion")
        point = apuesta_seleccionada.get("point", None)
        
        # 5. Buscar la cuota actual (solo para LIVE)
        cuota_actual, mercado_actual = None, None
        
        if betting_type == "LIVE":
            for bookmaker in evento_actualizado.get("bookmakers", []):
                if "bovada" not in bookmaker.get("title", "").lower():
                    continue
                    
                for market in bookmaker.get("markets", []):
                    if market.get("key") != tipo_apuesta:
                        continue
                        
                    for outcome in market.get("outcomes", []):
                        # Verificación para mercados con puntos (totals, spreads)
                        if tipo_apuesta in ["totals", "spreads"]:
                            if (outcome.get("name") == seleccion and 
                                outcome.get("point") == point):
                                cuota_actual = outcome.get("price")
                                mercado_actual = market
                                break
                        # Verificación para otros mercados
                        elif outcome.get("name") == seleccion:
                            cuota_actual = outcome.get("price")
                            mercado_actual = market
                            break
                            
                    if cuota_actual:
                        break
                if cuota_actual:
                    break
            
            # 6. Validar que el mercado sigue disponible (solo LIVE)
            if cuota_actual is None:
                return {
                    'status': 'error',
                    'message': "❌ El mercado seleccionado ya no está disponible."
                }
            
            # 7. Comparar cuotas exactamente (con tolerancia para floats)
            if not (abs(float(cuota_actual) - float(cuota_original)) < 0.0001):
                # Si la cuota mejoró (aumentó), permitir continuar sin notificar
                if float(cuota_actual) > float(cuota_original):
                    return {
                        'status': 'ok',
                        'message': "✅ La cuota ha mejorado. Puedes continuar con la apuesta.",
                        'evento_actualizado': evento_actualizado,
                        'nueva_cuota': cuota_actual
                    }
                # Si la cuota empeoró (disminuyó), notificar al usuario
                else:
                    diferencia = float(cuota_original) - float(cuota_actual)
                    return {
                        'status': 'changed',
                        'message': (
                            f"⚠️ La cuota ha cambiado dinámicamente.\n\n"
                            f"Original: {cuota_original}\n"
                            f"Actual: {cuota_actual}\n"
                            f"Diferencia: {diferencia:.2f}\n\n"
                            f"Envia /start y vuelve a intentarlo"
                        ),
                        'evento_actualizado': evento_actualizado,
                        'nueva_cuota': cuota_actual
                    }
        
        # 8. Verificar que todos los datos coinciden exactamente
        # Obtener datos del evento original (del contexto)
        datos_originales = {
            'home_team': evento.get('home_team'),
            'away_team': evento.get('away_team'),
            'commence_time': evento.get('commence_time'),
            'sport_title': evento.get('sport_title', evento.get('league', ''))
        }
        
        # Obtener datos actualizados (de la API o del contexto)
        datos_actualizados = {
            'home_team': evento_actualizado.get('home_team'),
            'away_team': evento_actualizado.get('away_team'),
            'commence_time': evento_actualizado.get('commence_time'),
            'sport_title': evento_actualizado.get('sport_title', evento_actualizado.get('league', ''))
        }
        
        if datos_originales != datos_actualizados:
            return {
                'status': 'changed',
                'message': "⚠️ Los detalles del evento han cambiado. ¿Deseas continuar con la información actualizada?",
                'evento_actualizado': evento_actualizado
            }
        
        # Si todo está correcto
        return {
            'status': 'ok',
            'message': "✅ La apuesta está lista para confirmar."
        }

    except Exception as e:
        print(f"Error en verificar_apuesta: {str(e)}")
        return {
            'status': 'error',
            'message': f"❌ Error al verificar la apuesta: {str(e)}"
        }
async def verificar_apuesta(context: CallbackContext, user_id: str, apuesta_seleccionada: dict) -> dict:
    """
    Verifica todos los aspectos de una apuesta antes de confirmarla.
    Devuelve un dict con:
    - 'status': 'ok'|'error'|'changed'
    - 'message': Mensaje para el usuario
    - 'evento_actualizado': Datos actualizados del evento (si hubo cambios)
    - 'nueva_cuota': Nueva cuota (si hubo cambios)
    """
    try:
        betting_type = context.user_data.get("betting", "PREPARTIDO").upper()
        
        # Si es apuesta prepartido, omitir verificación y aprobar directamente
        if betting_type == "PREPARTIDO":
            return {
                'status': 'ok',
                'message': "✅ Apuesta prepartido: verificación omitida."
            }

        # Obtener datos básicos
        event_id = apuesta_seleccionada.get("event_id")
        sport_key_original = context.user_data.get("sport_key_original")
        
        if not event_id or not sport_key_original:
            return {
                'status': 'error',
                'message': "❌ Error: No se pudo obtener la información del evento."
            }

        # 1. Buscar datos del evento en el contexto - nueva forma unificada
        evento = None
        event_key = f"evento_{event_id}"
        
        # Primero buscar en la estructura directa
        if event_key in context.user_data:
            evento = context.user_data[event_key]
        else:
            # Buscar en toda la estructura de user_data por event_id
            for key, data in context.user_data.items():
                if isinstance(data, dict) and data.get("event_id") == event_id:
                    evento = data
                    break

        if not evento:
            return {
                'status': 'error',
                'message': "❌ Error: La información del evento ha expirado."
            }

        # 2. Obtener datos actualizados de la API solo para LIVE
        evento_actualizado = None
        if betting_type == "LIVE":
            evento_actualizado = await obtener_mercados_evento(event_id, sport_key_original)
            
            # Verificar si la API devolvió un error
            if isinstance(evento_actualizado, str):
                return {
                    'status': 'error',
                    'message': evento_actualizado
                }
                    
            # 3. Verificar estado del evento
            if evento_actualizado.get("completed", False):
                return {
                    'status': 'error',
                    'message': "❌ El evento ya ha finalizado. No puedes apostar."
                }
        else:
            # Para PREPARTIDO usamos los datos del contexto
            evento_actualizado = evento

        # 4. Verificar datos específicos de la apuesta
        cuota_original = apuesta_seleccionada.get("cuota")
        tipo_apuesta = apuesta_seleccionada.get("tipo_apuesta")
        seleccion = apuesta_seleccionada.get("seleccion")
        point = apuesta_seleccionada.get("point", None)
        
        # 5. Buscar la cuota actual (solo para LIVE)
        cuota_actual, mercado_actual = None, None
        
        if betting_type == "LIVE":
            for bookmaker in evento_actualizado.get("bookmakers", []):
                if "bovada" not in bookmaker.get("title", "").lower():
                    continue
                    
                for market in bookmaker.get("markets", []):
                    if market.get("key") != tipo_apuesta:
                        continue
                        
                    for outcome in market.get("outcomes", []):
                        # Verificación para mercados con puntos (totals, spreads)
                        if tipo_apuesta in ["totals", "spreads"]:
                            if (outcome.get("name") == seleccion and 
                                outcome.get("point") == point):
                                cuota_actual = outcome.get("price")
                                mercado_actual = market
                                break
                        # Verificación para otros mercados
                        elif outcome.get("name") == seleccion:
                            cuota_actual = outcome.get("price")
                            mercado_actual = market
                            break
                            
                    if cuota_actual:
                        break
                if cuota_actual:
                    break
            
            # 6. Validar que el mercado sigue disponible (solo LIVE)
            if cuota_actual is None:
                return {
                    'status': 'error',
                    'message': "❌ El mercado seleccionado ya no está disponible."
                }
            
            # 7. Comparar cuotas exactamente (con tolerancia para floats)
            if not (abs(float(cuota_actual) - float(cuota_original)) < 0.0001):
                # Si la cuota mejoró (aumentó), permitir continuar sin notificar
                if float(cuota_actual) > float(cuota_original):
                    return {
                        'status': 'ok',
                        'message': "✅ La cuota ha mejorado. Puedes continuar con la apuesta.",
                        'evento_actualizado': evento_actualizado,
                        'nueva_cuota': cuota_actual
                    }
                # Si la cuota empeoró (disminuyó), notificar al usuario
                else:
                    diferencia = float(cuota_original) - float(cuota_actual)
                    return {
                        'status': 'changed',
                        'message': (
                            f"⚠️ La cuota ha cambiado dinámicamente.\n\n"
                            f"Original: {cuota_original}\n"
                            f"Actual: {cuota_actual}\n"
                            f"Diferencia: {diferencia:.2f}\n\n"
                            f"Envia /start y vuelve a intentarlo"
                        ),
                        'evento_actualizado': evento_actualizado,
                        'nueva_cuota': cuota_actual
                    }
        
        # 8. Verificar que todos los datos coinciden exactamente
        # Obtener datos del evento original (del contexto)
        datos_originales = {
            'home_team': evento.get('home_team'),
            'away_team': evento.get('away_team'),
            'commence_time': evento.get('commence_time'),
            'sport_title': evento.get('sport_title', evento.get('league', ''))
        }
        
        # Obtener datos actualizados (de la API o del contexto)
        datos_actualizados = {
            'home_team': evento_actualizado.get('home_team'),
            'away_team': evento_actualizado.get('away_team'),
            'commence_time': evento_actualizado.get('commence_time'),
            'sport_title': evento_actualizado.get('sport_title', evento_actualizado.get('league', ''))
        }
        
        if datos_originales != datos_actualizados:
            return {
                'status': 'changed',
                'message': "⚠️ Los detalles del evento han cambiado. ¿Deseas continuar con la información actualizada?",
                'evento_actualizado': evento_actualizado
            }
        
        # Si todo está correcto
        return {
            'status': 'ok',
            'message': "✅ La apuesta está lista para confirmar."
        }

    except Exception as e:
        print(f"Error en verificar_apuesta: {str(e)}")
        return {
            'status': 'error',
            'message': f"❌ Error al verificar la apuesta: {str(e)}"
        }
        
        
async def mis_apuestas(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    try:
        # Obtener apuestas recientes desde la base de datos
        apuestas_recientes = obtener_apuestas_usuario(user_id)
        
        # Obtener apuestas históricas (puedes crear una tabla historial_apuestas o usar un campo de estado)
        # Por ahora, asumiremos que las apuestas completadas se marcan con estado diferente a "⌛Pendiente"
        apuestas_historicas = [a for a in apuestas_recientes if a.get('estado') != '⌛Pendiente']
        apuestas_recientes = [a for a in apuestas_recientes if a.get('estado') == '⌛Pendiente']

        # Generar resumen estadístico
        total_recientes = len(apuestas_recientes)
        total_historicas = len(apuestas_historicas)
        
        estados_recientes = {
            "⌛Pendiente": 0,
            "✅ Ganada": 0,
            "❌ Perdida": 0,
            "🔄 Reembolso": 0
        }
        
        estados_historicas = {
            "✅ Ganada": 0,
            "❌ Perdida": 0,
            "🔄 Reembolso": 0
        }

        for apuesta in apuestas_recientes:
            estado = apuesta.get('estado', '⌛Pendiente')
            estados_recientes[estado] = estados_recientes.get(estado, 0) + 1

        for apuesta in apuestas_historicas:
            estado = apuesta.get('estado', '❌ Perdida')
            estados_historicas[estado] = estados_historicas.get(estado, 0) + 1

        # Crear mensaje principal con estadísticas
        mensaje_principal = f"""
📊 <b>RESUMEN DE TUS APUESTAS</b>

<pre>🔄 Apuestas Recientes ({total_recientes})</pre>
├ ⌛ Pendientes: {estados_recientes["⌛Pendiente"]}
├ ✅ Ganadas: {estados_recientes["✅ Ganada"]}
├ ❌ Perdidas: {estados_recientes["❌ Perdida"]}
└ 🔄 Reembolsos: {estados_recientes["🔄 Reembolso"]}

<pre>🗃️ Apuestas Históricas ({total_historicas})</pre>
├ ✅ Ganadas: {estados_historicas["✅ Ganada"]}
├ ❌ Perdidas: {estados_historicas["❌ Perdida"]}
└ 🔄 Reembolsos: {estados_historicas["🔄 Reembolso"]}

<blockquote>🔍 Selecciona qué apuestas deseas visualizar:</blockquote>
• <b>Recientes</b>: Apuestas activas o recién finalizadas
• <b>Historial</b>: Todas tus apuestas pasadas archivadas
"""

        # Crear teclado interactivo
        keyboard = [
            [InlineKeyboardButton("🔄 RECIENTES", callback_data=f"ver_apuestas:recientes:{user_id}")],
            [InlineKeyboardButton("🗃️ HISTORIAL", callback_data=f"ver_apuestas:historicas:{user_id}")],
            [InlineKeyboardButton("❌ CERRAR", callback_data="cerrar_apuestas")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Editar mensaje original o enviar nuevo
        try:
            await query.edit_message_text(
                text=mensaje_principal,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except:
            await query.message.reply_text(
                text=mensaje_principal,
                parse_mode="HTML",
                reply_markup=reply_markup
            )

    except Exception as e:
        print(f"Error en mis_apuestas: {str(e)}")
        await query.message.reply_text("⚠️ Ocurrió un error al cargar tus apuestas. Intenta nuevamente.")
        

async def cancelar_apuesta(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data.split(":", 1)  # Dividir solo en el primer ":"
    action = data[0]
    fecha_realizada = data[1] if len(data) > 1 else None

    # Buscar la apuesta a cancelar en la base de datos
    apuesta_a_cancelar = None
    try:
        # Obtener todas las apuestas del usuario
        apuestas_usuario = obtener_apuestas_usuario(user_id)
        
        for apuesta in apuestas_usuario:
            if (apuesta["fecha_realizada"] == fecha_realizada 
                and apuesta.get("betting") != "COMBINADA"):  # Excluir combinadas
                apuesta_a_cancelar = apuesta
                break

        if not apuesta_a_cancelar:
            # Verificar si era una combinada
            for apuesta in apuestas_usuario:
                if apuesta["fecha_realizada"] == fecha_realizada:
                    if apuesta.get("betting") == "COMBINADA":
                        await query.answer("❌ No puedes cancelar apuestas combinadas.", show_alert=True)
                        return
                        
            await query.answer("❌ No se encontró la apuesta.", show_alert=True)
            return

    except Exception as e:
        print(f"Error al buscar apuesta: {e}")
        await query.answer("❌ Error al buscar la apuesta.", show_alert=True)
        return

    # Verificar si la apuesta usó bono
    if apuesta_a_cancelar.get("bono", 0) != 0:
        await query.answer("❌ No puedes cancelar una apuesta que usó bono.", show_alert=True)
        return

    # Verificar si la fecha de inicio está a menos de 30 minutos o ya pasó
    try:
        fecha_inicio = datetime.strptime(apuesta_a_cancelar["fecha_inicio"], "%d/%m/%Y %H:%M:%S")
        ahora = datetime.now()
        tiempo_restante = (fecha_inicio - ahora).total_seconds() / 60  # Tiempo restante en minutos

        if tiempo_restante <= 30 or fecha_inicio <= ahora:
            await query.answer("❌ No puedes cancelar esta apuesta, el evento está por comenzar o ya comenzó.", show_alert=True)
            return
    except Exception as e:
        print(f"Error al verificar fecha: {e}")
        await query.answer("❌ Error al verificar la fecha del evento.", show_alert=True)
        return

    if action == "confirmar_cancelar":
        # Mostrar confirmación con botones
        monto = apuesta_a_cancelar["monto"]
        monto_devolver = monto * 0.7
        ganancia_casa = monto * 0.3

        mensaje_confirmacion = (
            f"<blockquote>⚠️ ¿Estás seguro de cancelar esta apuesta?</blockquote>\n\n"
            f"💰 <b>Monto apostado:</b> <code>{monto}</code> CUP\n"
            f"🔄 Se te devolverá: <code>{monto_devolver}</code> CUP (70%)\n\n"
            f"✅ <i>Confirmar cancelación</i> 👇"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Sí, cancelar", callback_data=f"cancelar_apuesta:{fecha_realizada}")],
            [InlineKeyboardButton("❌ No, volver", callback_data="menu_principal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(mensaje_confirmacion, parse_mode="HTML", reply_markup=reply_markup)
        await query.answer()

    elif action == "cancelar_apuesta":
        # Calcular el 70% del monto a devolver y el 30% de ganancia para la casa
        monto = apuesta_a_cancelar["monto"]
        monto_devolver = monto * 0.7
        ganancia_casa = monto * 0.3

        # Obtener el balance actual del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, "Balance")
        if not usuario_data:
            await query.answer("❌ Usuario no encontrado.", show_alert=True)
            return

        balance_actual = usuario_data[0]
        nuevo_balance = balance_actual + monto_devolver

        # Actualizar el balance del usuario en la base de datos
        exito = actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
        if not exito:
            await query.answer("❌ Error al actualizar el balance.", show_alert=True)
            return

        # Eliminar la apuesta de la base de datos
        exito_eliminacion = eliminar_apuesta_por_fecha(user_id, fecha_realizada)
        if not exito_eliminacion:
            await query.answer("❌ Error al eliminar la apuesta.", show_alert=True)
            return

        # Notificar en GROUP_REGISTRO con un botón para ver el ticket
        mensaje_registro = (
            f"<blockquote>🚨 Apuesta cancelada por el usuario {user_id}:</blockquote>\n\n"
            f"💰 <b>Monto devuelto:</b> <code>{monto_devolver}</code> CUP\n"
            f"✅ <b>Ganancia para la casa:</b> <code>{ganancia_casa}</code> CUP"
        )

        # Crear botón con el enlace al ticket
        if "mensaje_canal_url" in apuesta_a_cancelar:
            keyboard = [
                [InlineKeyboardButton("📄 Ver ticket", url=apuesta_a_cancelar["mensaje_canal_url"])]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        await context.bot.send_message(
            chat_id=GROUP_REGISTRO,
            text=mensaje_registro,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

        # Confirmar al usuario
        await query.edit_message_text(f"✅ Apuesta cancelada. Se te ha devuelto {monto_devolver} CUP.", parse_mode="HTML")
        await query.answer()


async def mostrar_apuestas_seleccion(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    tipo = data[1]
    user_id = data[2]

    try:
        # Obtener apuestas desde la base de datos
        apuestas_usuario = obtener_apuestas_usuario(user_id)
        
        if not apuestas_usuario:
            await query.edit_message_text("🎯 No tienes apuestas registradas.")
            return

        if tipo == "recientes":
            # Filtrar solo apuestas recientes
            apuestas_recientes = [a for a in apuestas_usuario if a.get("estado") in ["⌛Pendiente", "EN JUEGO", "PENDIENTE"]]
            
            if not apuestas_recientes:
                await query.edit_message_text("🎯 No tienes apuestas recientes registradas.")
                return

            # Estructura para apuestas recientes
            for apuesta in apuestas_recientes:
                betting_type = apuesta.get("betting", "")
                
                if betting_type in ["PREPARTIDO", "LIVE"]:
                    # APUESTA SIMPLE
                    tipo_apuesta = apuesta.get('tipo_apuesta', 'Apuesta')
                    if tipo_apuesta:
                        tipo_apuesta = tipo_apuesta.upper()
                    else:
                        tipo_apuesta = "APUESTA"
                    
                    mensaje = f"""
<blockquote>📌 {apuesta.get('estado', '')} - {tipo_apuesta}</blockquote>
<pre>📊 Detalles de la Apuesta</pre>
┌────────────────────────
├ ⚽ <b>Deporte:</b> {apuesta.get('deporte', '')}
├ 🏆 <b>Liga:</b> {apuesta.get('liga', '')}
├ ⚔️ <b>Partido:</b> {apuesta.get('partido', '')}
├ 🎯 <b>Apuesta:</b> {apuesta.get('favorito', '')}
├ 💹 <b>Cuota:</b> <code>{apuesta.get('cuota', 0)}</code>
├ 💰 <b>Monto:</b> <code>{apuesta.get('monto', 0)} CUP</code>
├ 🤑 <b>Ganancia:</b> <code>{apuesta.get('ganancia', 0)} CUP</code>
└ 📅 <b>Fecha:</b> {apuesta.get('fecha_realizada', '')}
"""

                    if apuesta.get("scores"):
                        mensaje += """
<blockquote>📊 Resultado Final</blockquote>
"""
                        for score in apuesta["scores"]:
                            mensaje += f"<pre>   • {score.get('name', '')}: {score.get('score', '')}</pre>\n"

                    # Botón de cancelación
                    reply_markup = None
                    try:
                        fecha_inicio_str = apuesta.get("fecha_inicio")
                        if fecha_inicio_str:
                            fecha_inicio = datetime.strptime(fecha_inicio_str, "%d/%m/%Y %H:%M:%S")
                            ahora = datetime.now()
                            tiempo_restante = (fecha_inicio - ahora).total_seconds() / 60

                            if tiempo_restante > 30 and fecha_inicio > ahora and apuesta.get("bono", 0) == 0:
                                keyboard = [[InlineKeyboardButton("❌ CANCELAR APUESTA", callback_data=f"confirmar_cancelar:{apuesta['fecha_realizada']}")]]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                    except:
                        pass

                elif betting_type == "COMBINADA":
                    # APUESTA COMBINADA
                    mensaje = f"""
<blockquote>📌 {apuesta.get('estado', '')} - COMBINADA</blockquote>
<pre>📊 Detalles de la Apuesta</pre>
┌────────────────────────
├ 💰 <b>Monto:</b> <code>{apuesta.get('monto', 0)} CUP</code>
├ 📈 <b>Cuota Total:</b> <code>{apuesta.get('cuota', 0):.2f}</code>
├ 🏆 <b>Ganancia Potencial:</b> <code>{apuesta.get('ganancia', 0):.2f} CUP</code>
└ 📅 <b>Fecha:</b> {apuesta.get('fecha_realizada', '')}
"""

                    # Mostrar selecciones
                    selecciones = apuesta.get("selecciones", [])
                    
                    if selecciones:
                        mensaje += "<blockquote>📋 Selecciones:</blockquote>"
                        for i, sel in enumerate(selecciones, 1):
                            estado = sel.get("estado", "🕒 PENDIENTE")
                            tipo_apuesta_sel = sel.get('tipo_apuesta', sel.get('mercado', '')).upper()
                            cuota_individual = sel.get('cuota', sel.get('cuota_individual', 0))
                            
                            mensaje += f"""
<pre>🔹 Evento {i}
├ ⚽ <b>{sel.get('partido', '')}</b>
├ 🏟 <i>{sel.get('liga', '')}</i>
├ 📌 Mercado: <b>{tipo_apuesta_sel}</b>
├ 🎯 Favorito: {sel.get('favorito', '')}
├ 💹 Cuota: <code>{cuota_individual:.2f}</code>
└ 📌 Estado: {estado}</pre>
"""

                            if sel.get("scores"):
                                mensaje += "📊 Resultado:\n"
                                for score in sel["scores"]:
                                    mensaje += f"   • {score.get('name', '')}: {score.get('score', '')}\n"
                    else:
                        mensaje += "<blockquote>📋 Selecciones: No disponibles</blockquote>"

                    reply_markup = None  # No cancelación para combinadas

                else:
                    # Tipo desconocido, tratar como simple
                    tipo_apuesta = apuesta.get('tipo_apuesta', 'Apuesta').upper()
                    mensaje = f"""
<blockquote>📌 {apuesta.get('estado', '')} - {tipo_apuesta}</blockquote>
<pre>📊 Detalles de la Apuesta</pre>
┌────────────────────────
├ ⚽ <b>Deporte:</b> {apuesta.get('deporte', '')}
├ 🏆 <b>Liga:</b> {apuesta.get('liga', '')}
├ ⚔️ <b>Partido:</b> {apuesta.get('partido', '')}
├ 🎯 <b>Apuesta:</b> {apuesta.get('favorito', '')}
├ 💹 <b>Cuota:</b> <code>{apuesta.get('cuota', 0)}</code>
├ 💰 <b>Monto:</b> <code>{apuesta.get('monto', 0)} CUP</code>
├ 🤑 <b>Ganancia:</b> <code>{apuesta.get('ganancia', 0)} CUP</code>
└ 📅 <b>Fecha:</b> {apuesta.get('fecha_realizada', '')}
"""
                    reply_markup = None

                # Enviar mensaje
                await query.message.reply_text(
                    mensaje, 
                    parse_mode="HTML", 
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )

        else:  # Historial
            # Filtrar solo apuestas del historial (finalizadas)
            apuestas_historial = [a for a in apuestas_usuario if a.get("estado") in ["GANADA", "PERDIDA", "CANCELADA", "✅ Ganada", "❌ Perdida", "🔚 Finalizado"]]
            
            if not apuestas_historial:
                await query.edit_message_text("🗃️ No tienes apuestas en tu historial.")
                return

            # Ordenar por fecha (más reciente primero)
            apuestas_historial.sort(
                key=lambda x: datetime.strptime(x["fecha_realizada"], "%d/%m/%Y %H:%M:%S"), 
                reverse=True
            )

            # Paginación
            offset = int(data[3]) if len(data) > 3 else 0
            batch = apuestas_historial[offset:offset+10]
            
            mensaje = f"<b>🗃️ TU HISTORIAL DE APUESTAS</b>\n\n"
            for apuesta in batch:
                estado = apuesta.get('estado', '❌ Perdida')
                fecha = apuesta.get("fecha_realizada", "")
                monto = apuesta.get("monto", 0)
                
                if apuesta.get("betting") == "COMBINADA":
                    tipo_apuesta = "COMBINADA"
                    cuota = apuesta.get("cuota", 0)
                    ganancia = apuesta.get("ganancia", 0)
                    mensaje += f"""
📌 <b>{estado}</b> - {tipo_apuesta}
├ 💰 {monto} CUP → 🏆 {ganancia} CUP
├ 📈 Cuota: {cuota:.2f}
└ 📅 {fecha}\n
"""
                else:
                    tipo_apuesta = apuesta.get("tipo_apuesta", "").upper()
                    ganancia_apuesta = apuesta.get("ganancia", 0)
                    mensaje += f"""
📌 <b>{estado}</b> - {tipo_apuesta}
├ ⚽ {apuesta.get('partido', '')}
├ 💰 {monto} CUP → 🏆 {ganancia_apuesta} CUP
└ 📅 {fecha}\n
"""

            # Botones de navegación
            buttons = []
            if len(apuestas_historial) > offset+10:
                buttons.append(InlineKeyboardButton("➡️ SIGUIENTE", callback_data=f"pagina:historicas:{user_id}:{offset+10}"))
            
            if offset > 0:
                buttons.insert(0, InlineKeyboardButton("⬅️ ANTERIOR", callback_data=f"pagina:historicas:{user_id}:{offset-10}"))
            
            buttons.append(InlineKeyboardButton("🔙 VOLVER", callback_data="mis_apuestas"))
            
            reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

            await query.edit_message_text(
                text=mensaje,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

    except Exception as e:
        print(f"Error en mostrar_apuestas_seleccion: {str(e)}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text("⚠️ Error al cargar las apuestas. Intenta nuevamente.")  
def eliminar_apuesta_por_fecha(user_id, fecha_realizada):
    """Elimina una apuesta por fecha de realización"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("DELETE FROM apuestas WHERE usuario_id = ? AND fecha_realizada = ?", 
                 (user_id, fecha_realizada))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error al eliminar apuesta: {e}")
        return False

        
async def resumen_evento_no_encontrado(context, event_id):
    """Genera resumen de apuestas para un evento cuando no se encuentra en el cache"""
    try:
        # Obtener apuestas desde la base de datos
        consulta = "SELECT * FROM apuestas"
        todas_apuestas = ejecutar_consulta_segura(consulta, obtener_resultados=True)
        
        if not todas_apuestas:
            mensaje = f"❌ No se encontraron apuestas en la base de datos."
            await context.bot.send_message(chat_id=GROUP_REGISTRO, text=mensaje, parse_mode="HTML")
            return

        # Filtrar apuestas que pertenecen al event_id dado (tanto PREPARTIDO como COMBINADAS)
        apuestas_evento = []
        apuestas_combinadas_relacionadas = []
        
        for apuesta_tuple in todas_apuestas:
            try:
                # Convertir tupla a diccionario basado en la estructura de guardar_apuesta_en_db
                apuesta = {
                    'id': apuesta_tuple[0],
                    'usuario_id': apuesta_tuple[1],
                    'user_name': apuesta_tuple[2],
                    'fecha_realizada': apuesta_tuple[3],
                    'fecha_inicio': apuesta_tuple[4],
                    'monto': float(apuesta_tuple[5] or 0),
                    'cuota': float(apuesta_tuple[6] or 0),
                    'ganancia': float(apuesta_tuple[7] or 0),
                    'estado': apuesta_tuple[8] or "Desconocido",
                    'bono': float(apuesta_tuple[9] or 0),
                    'balance': float(apuesta_tuple[10] or 0),
                    'betting': apuesta_tuple[11] or "Desconocido",
                    'id_ticket': apuesta_tuple[12] or "",
                    'event_id': apuesta_tuple[13] or "",
                    'deporte': apuesta_tuple[14] or "Desconocido",
                    'liga': apuesta_tuple[15] or "Desconocido",
                    'sport_key': apuesta_tuple[16] or "",
                    'partido': apuesta_tuple[17] or "Partido desconocido",
                    'favorito': apuesta_tuple[18] or "Desconocido",
                    'tipo_apuesta': apuesta_tuple[19] or "Desconocido",
                    'home_logo': apuesta_tuple[20],
                    'away_logo': apuesta_tuple[21],
                    'mensaje_canal_url': apuesta_tuple[22],
                    'mensaje_canal_id': apuesta_tuple[23],
                    'minuto': apuesta_tuple[24],
                    'marcador': apuesta_tuple[25],
                    'completed': bool(apuesta_tuple[26]),
                    'last_update': apuesta_tuple[27],
                    'es_combinada': bool(apuesta_tuple[28]),
                    'selecciones_json': apuesta_tuple[29] or "[]",
                    'scores_json': apuesta_tuple[30] or "[]"
                }
                # Apuestas PREPARTIDO directas
                if (apuesta.get("event_id") == event_id and 
                    apuesta.get("betting") in ["PREPARTIDO", "LIVE"]):
                    apuestas_evento.append(apuesta)
                
                # Buscar en COMBINADAS que contengan este event_id en sus selecciones
                if (apuesta.get("betting") == "COMBINADA" and 
                    apuesta.get("selecciones_json")):
                    try:
                        selecciones = json.loads(apuesta["selecciones_json"])
                        for seleccion in selecciones:
                            if seleccion.get("event_id") == event_id:
                                apuestas_combinadas_relacionadas.append(apuesta)
                                break
                    except json.JSONDecodeError:
                        continue
            except (TypeError, ValueError, IndexError) as e:
                print(f"⚠️ Error procesando apuesta: {e}")
                continue

        if not apuestas_evento and not apuestas_combinadas_relacionadas:
            mensaje = f"❌ No se encontraron apuestas para el evento <code>{event_id}</code>."
            await context.bot.send_message(chat_id=7031172659, text=mensaje, parse_mode="HTML")
            return

        # Obtener detalles del evento
        partido = "Partido desconocido"
        deporte = "Desconocido"
        
        if apuestas_evento:
            partido = apuestas_evento[0].get("partido", "Partido desconocido")
            deporte = apuestas_evento[0].get("deporte", "Desconocido")
        elif apuestas_combinadas_relacionadas:
            # Buscar el partido en las selecciones de la primera combinada
            try:
                selecciones = json.loads(apuestas_combinadas_relacionadas[0]["selecciones_json"])
                for seleccion in selecciones:
                    if seleccion.get("event_id") == event_id:
                        partido = seleccion.get("partido", "Partido desconocido")
                        deporte = seleccion.get("deporte", "Desconocido")
                        break
            except json.JSONDecodeError:
                pass

        # Agrupar información de apuestas PREPARTIDO
        total_apostado_pre = sum(apuesta["monto"] for apuesta in apuestas_evento)
        apuestas_agrupadas_pre = {}
        apuesta_mayor_pre = {"monto": 0, "favorito": ""}

        for apuesta in apuestas_evento:
            favorito = apuesta["favorito"]
            monto = apuesta["monto"]
            apuestas_agrupadas_pre[favorito] = apuestas_agrupadas_pre.get(favorito, 0) + monto

            if monto > apuesta_mayor_pre["monto"]:
                apuesta_mayor_pre = {"monto": monto, "favorito": favorito}

        # Agrupar información de apuestas COMBINADAS
        total_apostado_comb = sum(apuesta["monto"] for apuesta in apuestas_combinadas_relacionadas)
        apuestas_agrupadas_comb = {"COMBINADAS": total_apostado_comb}
        apuesta_mayor_comb = {"monto": 0, "favorito": "COMBINADA"}

        for apuesta in apuestas_combinadas_relacionadas:
            monto = apuesta["monto"]
            if monto > apuesta_mayor_comb["monto"]:
                apuesta_mayor_comb = {"monto": monto, "favorito": "COMBINADA"}

        # Formatear las apuestas individuales
        apuestas_formateadas = []
        
        # Apuestas PREPARTIDO
        if apuestas_agrupadas_pre:
            apuestas_formateadas.append("<b>🎯 Apuestas PREPARTIDO y LIVE:</b>")
            apuestas_formateadas.extend([
                f"<blockquote>• {tipo_apuesta}:</blockquote> <code>{monto:>6} CUP</code>"
                for tipo_apuesta, monto in apuestas_agrupadas_pre.items()
            ])
        
        # Apuestas COMBINADAS
        if apuestas_agrupadas_comb:
            apuestas_formateadas.append("\n<b>🎲 Apuestas COMBINADAS:</b>")
            apuestas_formateadas.extend([
                f"<blockquote>• {tipo_apuesta}:</blockquote> <code>{monto:>6} CUP</code>"
                for tipo_apuesta, monto in apuestas_agrupadas_comb.items()
            ])

        total_apostado = total_apostado_pre + total_apostado_comb

        mensaje = (
            f"<code>🏆 {partido}</code>\n"
            f"<b>🏅 Deporte:</b> {deporte}\n"
            f"<b>💰 Total Apostado:</b> <code>{total_apostado:>6} CUP</code>\n"
            f"<b>📅 Event ID:</b> <code>{event_id}</code>\n\n"
            + "\n".join(apuestas_formateadas) + "\n\n"
            f"<b>🔥 Apuesta Mayor PREPARTIDO:</b> <code>{apuesta_mayor_pre['monto']:>6} CUP</code> en <i>{apuesta_mayor_pre['favorito']}</i>\n"
            f"<b>🎰 Apuesta Mayor COMBINADA:</b> <code>{apuesta_mayor_comb['monto']:>6} CUP</code>"
        )

        # ✅ ENVIAR SOLO EL MENSAJE SIN BOTONES
        await context.bot.send_message(chat_id=7031172659, text=mensaje, parse_mode="HTML")

    except Exception as e:
        print(f"Error en resumen_evento_no_encontrado: {str(e)}")
        import traceback
        traceback.print_exc()


def decidir_resultado_apuesta(tipo_apuesta, scores, favorito, home_team, away_team, sport_key='', event_id=None, handicap=None, total=None):
    """Función principal que usa exactamente los nombres de CONFIG_MERCADOS"""
    
    # Mapeo directo de nombres de mercado a funciones decisoras
    DECISORES = {
        # Mercados principales
        "Ganador del Partido": decidir_h2h,
        "h2h": decidir_h2h,
        "Empate no Bet": decidir_dnb,
        
        # Mercados de fútbol
        "Ambos Equipos Marcan": decidir_btts,
        "Anotador en el Partido": lambda s, f, h, a, sk, eid: decidir_anotador_partido(s, f, h, a, sk, event_id=eid),
        "Primer Anotador": lambda s, f, h, a, sk, eid: decidir_primer_anotador(s, f, h, a, sk, event_id=eid),
        "Último Anotador": lambda s, f, h, a, sk, eid: decidir_ultimo_anotador(s, f, h, a, sk, event_id=eid),
        "Jugador Amonestado": lambda s, f, h, a, sk, eid: decidir_jugador_amonestado(s, f, h, a, sk, event_id=eid),
        "Jugador Expulsado": lambda s, f, h, a, sk, eid: decidir_jugador_expulsado(s, f, h, a, sk, event_id=eid),
        "Hándicap de Tarjetas": lambda s, f, h, a, sk, eid: decidir_handicap_tarjetas(s, f, h, a, sk, event_id=eid, handicap=handicap),
        "Total de Tarjetas": lambda s, f, h, a, sk, eid: decidir_total_tarjetas(s, f, h, a, sk, event_id=eid),
        "Total Disparos a Puerta": lambda s, f, h, a, sk, eid: decidir_shots_on_goal(s, f, h, a, sk, event_id=eid),
        "Equipo Marcará Primer Gol": lambda s, f, h, a, sk, eid: decidir_primer_gol(s, f, h, a, sk, event_id=eid),
        "Doble oportunidad": lambda s, f, h, a, sk, eid: decidir_doble_oportunidad(s, f, h, a, sk, event_id=eid),
        "Marcador Exacto": lambda s, f, h, a, sk, eid: decidir_marcador_exacto(s, f, h, a, sk, event_id=eid),
        "Total Córners": lambda s, f, h, a, sk, eid: decidir_total_corners(s, f, h, a, sk, event_id=eid),
        
        # Mercados por tiempos (fútbol)
        "Ganador 1ra Mitad": lambda s, f, h, a, sk, eid: decidir_h2h_mitad(s, f, h, a, sk, event_id=eid, mitad=1),
        "Ganador 2da Mitad": lambda s, f, h, a, sk, eid: decidir_h2h_mitad(s, f, h, a, sk, event_id=eid, mitad=2),
        "Gol Local en 2ª Parte": lambda s, f, h, a, sk, eid: decidir_gol_local_2parte(s, f, h, a, sk, event_id=eid, mitad=2),
        "Hándicap 1ra Mitad": lambda s, f, h, a, sk, eid: decidir_handicap_mitad(s, f, h, a, sk, event_id=eid, handicap=handicap, mitad=1),
        "Hándicap 2da Mitad": lambda s, f, h, a, sk, eid: decidir_handicap_mitad(s, f, h, a, sk, event_id=eid, handicap=handicap, mitad=2),
        "Total 1ra Mitad": lambda s, f, h, a, sk, eid: decidir_total_mitad(s, f, h, a, sk, event_id=eid, total=total, mitad=1),
        "Total 2da Mitad": lambda s, f, h, a, sk, eid: decidir_total_mitad(s, f, h, a, sk, event_id=eid, total=total, mitad=2),
        "Marcador Exacto (1ª Mitad)": lambda s, f, h, a, sk, eid: decidir_marcador_exacto_mitad(s, f, h, a, sk, event_id=eid, mitad=1),
        "Total - Equipo Local": lambda s, f, h, a, sk, eid: decidir_total_local(s, f, h, a, sk, event_id=eid),
        "Total - Equipo Visitante": lambda s, f, h, a, sk, eid: decidir_total_visitante(s, f, h, a, sk, event_id=eid),
        "Ambos Marcan (1ª Parte)": lambda s, f, h, a, sk, eid: decidir_ambos_marcan_mitad(s, f, h, a, sk, event_id=eid, mitad=1),
        "Ambos Marcan (2da Mitad)": lambda s, f, h, a, sk, eid: decidir_ambos_marcan_mitad(s, f, h, a, sk, event_id=eid, mitad=2),
        
        # Mercados genéricos (totales y handicaps)
        "Hándicap": lambda s, f, h, a, sk, eid=None: decidir_handicap(s, f, h, a, sk, handicap=handicap),
        "Total Anotaciones": lambda s, f, h, a, sk, eid=None: decidir_total(s, f, h, a, sk, total=total),
        
        # Baseball
        "Hándicap Alternativo 1ra Entrada": lambda s, f, h, a, sk, eid: decidir_handicap_baseball(s, f, h, a, sk, event_id=eid, handicap=handicap, entradas=1),
        "Hándicap Alternativo 1ras 3 Entradas": lambda s, f, h, a, sk, eid: decidir_handicap_baseball(s, f, h, a, sk, event_id=eid, handicap=handicap, entradas=3),
        "Hándicap Alternativo 1ras 5 Entradas": lambda s, f, h, a, sk, eid: decidir_handicap_baseball(s, f, h, a, sk, event_id=eid, handicap=handicap, entradas=5),
        "Hándicap Alternativo 1ras 7 Entradas": lambda s, f, h, a, sk, eid: decidir_handicap_baseball(s, f, h, a, sk, event_id=eid, handicap=handicap, entradas=7),
        "Total 1ra Entrada": lambda s, f, h, a, sk, eid: decidir_total_baseball(s, f, h, a, sk, event_id=eid, total=total, entradas=1),
        "Total 1ras 3 Entradas": lambda s, f, h, a, sk, eid: decidir_total_baseball(s, f, h, a, sk, event_id=eid, total=total, entradas=3),
        "Total 1ras 5 Entradas": lambda s, f, h, a, sk, eid: decidir_total_baseball(s, f, h, a, sk, event_id=eid, total=total, entradas=5),
        "Total 1ras 7 Entradas": lambda s, f, h, a, sk, eid: decidir_total_baseball(s, f, h, a, sk, event_id=eid, total=total, entradas=7),
        
        # Baloncesto
        "Hándicap 1er Cuarto": lambda s, f, h, a, sk, eid: decidir_handicap_baloncesto(s, f, h, a, sk, event_id=eid, handicap=handicap, periodo='Q1'),
        "Hándicap 2do Cuarto": lambda s, f, h, a, sk, eid: decidir_handicap_baloncesto(s, f, h, a, sk, event_id=eid, handicap=handicap, periodo='Q2'),
        "Hándicap 3er Cuarto": lambda s, f, h, a, sk, eid: decidir_handicap_baloncesto(s, f, h, a, sk, event_id=eid, handicap=handicap, periodo='Q3'),
        "Hándicap 4to Cuarto": lambda s, f, h, a, sk, eid: decidir_handicap_baloncesto(s, f, h, a, sk, event_id=eid, handicap=handicap, periodo='Q4'),
        "Total 1er Cuarto": lambda s, f, h, a, sk, eid: decidir_total_baloncesto(s, f, h, a, sk, event_id=eid, total=total, periodo='Q1'),
        "Total 2do Cuarto": lambda s, f, h, a, sk, eid: decidir_total_baloncesto(s, f, h, a, sk, event_id=eid, total=total, periodo='Q2'),
        "Total 3er Cuarto": lambda s, f, h, a, sk, eid: decidir_total_baloncesto(s, f, h, a, sk, event_id=eid, total=total, periodo='Q3'),
        "Total 4to Cuarto": lambda s, f, h, a, sk, eid: decidir_total_baloncesto(s, f, h, a, sk, event_id=eid, total=total, periodo='Q4')
    }
    
    # Verificar si el tipo de apuesta está en los decisores
    if tipo_apuesta not in DECISORES:
        print(f"⚠️ Tipo de apuesta no reconocido: '{tipo_apuesta}'")
        print("Opciones válidas:", ", ".join(sorted(DECISORES.keys())))
        return "Perdedora"
    
    try:
        print(f"🔍 Procesando apuesta tipo: {tipo_apuesta}")
        
        # Determinar si necesita event_id
        necesita_event_id = 'eid' in str(DECISORES[tipo_apuesta].__code__.co_varnames)
        
        if necesita_event_id:
            if not event_id:
                print("❌ Error: Esta apuesta requiere event_id pero no se proporcionó")
                return "Perdedora"
            return DECISORES[tipo_apuesta](scores, favorito, home_team, away_team, sport_key, event_id)
        else:
            return DECISORES[tipo_apuesta](scores, favorito, home_team, away_team, sport_key)
            
    except Exception as e:
        print(f"❌ Error en decidir_resultado_apuesta ({tipo_apuesta}): {str(e)}")
        return "Perdedora"
        
def decidir_ambos_marcan_mitad(scores, favorito, home_team, away_team, sport_key='', event_id=None, mitad=1):
    """
    Determina si ambos equipos marcaron en la mitad especificada (1ª o 2ª parte).
    Args:
        favorito: "✅ Yes" o "✅ No"
        mitad: 1 (1ª parte) o 2 (2ª parte)
    Returns:
        "Ganadora" si coincide con la predicción, "Perdedora" si no
    """
    if not event_id:
        print(f"❌ Error: Se requiere event_id para Ambos Marcan en {'1ª' if mitad == 1 else '2ª'} parte")
        return "Perdedora"

    # Obtener datos del evento
    datos_evento = obtener_datos_evento(event_id)
    if not datos_evento or 'datos' not in datos_evento or 'periodos' not in datos_evento['datos']:
        print("❌ Error: Datos del evento no disponibles")
        return "Perdedora"

    # Extraer periodo correspondiente
    periodo = '1T' if mitad == 1 else '2T'
    periodo_data = datos_evento['datos']['periodos'].get(periodo, {})
    if not periodo_data:
        print(f"❌ Error: No hay datos para la {'1ª' if mitad == 1 else '2ª'} parte")
        return "Perdedora"

    # Obtener goles de cada equipo en esa mitad
    goles_local = int(periodo_data.get('local', 0))
    goles_visitante = int(periodo_data.get('visitante', 0))

    # Determinar si ambos marcaron
    ambos_marcaron = goles_local > 0 and goles_visitante > 0
    prediccion = favorito.replace("✅", "").strip().lower()

    print(f"🔢 {periodo} - Local: {goles_local} | Visitante: {goles_visitante} | Predicción: {prediccion}")

    # Evaluar predicción
    if prediccion == "yes":
        return "Ganadora" if ambos_marcaron else "Perdedora"
    elif prediccion == "no":
        return "Ganadora" if not ambos_marcaron else "Perdedora"
    else:
        print("❌ Error: Predicción debe ser '✅ Yes' o '✅ No'")
        return "Perdedora"    
        
        
def decidir_total_visitante(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Determina si se cumple la predicción de total para el equipo visitante (Over/Under).
    Args:
        favorito: "🔢 Over 1.5" o "🔢 Under 2.5"
    Returns:
        "Ganadora" si se cumple la condición, "Perdedora" si no.
    """
    try:
        # Obtener puntaje del equipo visitante
        away_score = next((int(score['score']) for score in scores if score['name'] == away_team), 0)
        
        # Extraer condición y valor numérico del favorito
        import re
        match = re.search(r"(\d+\.?\d*)", favorito)
        if not match:
            print("❌ No se encontró valor numérico en 'favorito'")
            return "Perdedora"
        
        linea = float(match.group(1))
        condicion = favorito.split()[1].lower()  # "over" o "under"
        
        print(f"🔢 Total Visitante: {away_score} | Predicción: {condicion} {linea}")
        
        # Evaluar condición
        if condicion == "over":
            return "Ganadora" if away_score > linea else "Perdedora"
        elif condicion == "under":
            return "Ganadora" if away_score < linea else "Perdedora"
        else:
            print(f"❌ Condición no reconocida: {condicion}. Debe ser 'Over' o 'Under'")
            return "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_total_visitante: {str(e)}")
        return "Perdedora"        
        
def decidir_total_local(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Determina si se cumple la predicción de total para el equipo local (Over/Under).
    Args:
        favorito: "🔢 Over 2.5" o "🔢 Under 1.5"
    Returns:
        "Ganadora" si se cumple la condición, "Perdedora" si no.
    """
    try:
        # Obtener puntaje del equipo local
        home_score = next((int(score['score']) for score in scores if score['name'] == home_team), 0)
        
        # Extraer condición y valor numérico del favorito
        import re
        match = re.search(r"(\d+\.?\d*)", favorito)
        if not match:
            print("❌ No se encontró valor numérico en 'favorito'")
            return "Perdedora"
        
        linea = float(match.group(1))
        condicion = favorito.split()[1].lower()  # "over" o "under"
        
        print(f"🔢 Total Local: {home_score} | Predicción: {condicion} {linea}")
        
        # Evaluar condición
        if condicion == "over":
            return "Ganadora" if home_score > linea else "Perdedora"
        elif condicion == "under":
            return "Ganadora" if home_score < linea else "Perdedora"
        else:
            print(f"❌ Condición no reconocida: {condicion}. Debe ser 'Over' o 'Under'")
            return "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_total_local: {str(e)}")
        return "Perdedora"        
        
        
def decidir_total_corners(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Determina si se cumple la predicción de total de córners (Over/Under/Exactly).
    Args:
        favorito: "🌽 Over 9.5", "🌽 Under 9.5", "🌽 Exactly 9.5"
    Returns:
        "Ganadora" si se cumple la condición, "Perdedora" si no.
    """
    if not event_id:
        print("❌ Error: Se requiere event_id para Total de Córners")
        return "Perdedora"

    # Obtener datos del evento
    datos_evento = obtener_datos_evento(event_id)
    if not datos_evento or 'datos' not in datos_evento or 'estadisticas' not in datos_evento['datos']:
        print("❌ Error: Datos del evento no disponibles")
        return "Perdedora"

    # Obtener estadísticas de córners
    estadisticas = datos_evento['datos']['estadisticas']
    corners_local = estadisticas.get('Corner Kicks', {}).get('local', 0)
    corners_visitante = estadisticas.get('Corner Kicks', {}).get('visitante', 0)
    
    # Si no hay datos de córners, intentar con "Corner Kicks" (alternativa en inglés)
    if corners_local == 0 and corners_visitante == 0:
        corners_local = estadisticas.get('Corners', {}).get('local', 0)
        corners_visitante = estadisticas.get('Corners', {}).get('visitante', 0)

    total_corners = corners_local + corners_visitante
    print(f"🌽 Córners Totales: {total_corners} (Local: {corners_local}, Visitante: {corners_visitante}) | Predicción: {favorito}")

    # Extraer número y condición de la predicción (ej. "🌽 Over 9.5" → ("Over", 9.5))
    try:
        partes = favorito.replace("🌽", "").strip().split()
        condicion = partes[0].lower()
        numero = float(partes[1])
    except:
        print("❌ Error: Formato de predicción inválido. Debe ser '🌽 Over/Under/Exactly X.X'")
        return "Perdedora"

    # Evaluar condición
    if condicion == "over":
        return "Ganadora" if total_corners > numero else "Perdedora"
    elif condicion == "under":
        return "Ganadora" if total_corners < numero else "Perdedora"
    elif condicion == "exactly":
        return "Ganadora" if total_corners == numero else "Perdedora"
    else:
        print(f"❌ Error: Condición no reconocida ('{condicion}'). Use Over/Under/Exactly")
        return "Perdedora"        
        
        
def decidir_marcador_exacto(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Determina si el marcador exacto al final del partido coincide con la predicción.
    Args:
        favorito: Formato "🔢 X-Y" o "🔢 X:Y" (ej. "🔢 2-1" o "🔢 2:1").
    Returns:
        "Ganadora" si coincide, "Perdedora" si no.
    """
    if not event_id:
        print("❌ Error: Se requiere event_id para Marcador Exacto")
        return "Perdedora"

    # Obtener datos del evento
    datos_evento = obtener_datos_evento(event_id)
    if not datos_evento or 'datos' not in datos_evento or 'marcador' not in datos_evento['datos']:
        print("❌ Error: Datos del evento no disponibles")
        return "Perdedora"

    # Marcador final - CONVERTIR A INT
    marcador = datos_evento['datos']['marcador']
    real_local = int(marcador.get('local', 0))
    real_visitante = int(marcador.get('visitante', 0))
    print(f"🔢 Marcador Final: {real_local}-{real_visitante} | Predicción: {favorito}")

    # Procesar predicción (acepta "🔢 2-1" o "🔢 2:1")
    pred = favorito.replace("🔢", "").strip()
    try:
        # Reemplazar ":" por "-" para estandarizar
        pred_std = pred.replace(":", "-")
        pred_local, pred_visitante = map(int, pred_std.split('-'))
    except:
        print("❌ Error: Formato de predicción inválido. Debe ser '🔢 X-Y' o '🔢 X:Y'")
        return "Perdedora"

    # Comparar
    if real_local == pred_local and real_visitante == pred_visitante:
        print(f"🎯 Marcador Exacto: GANADORA! {real_local}-{real_visitante} = {pred_local}-{pred_visitante}")
        return "Ganadora"
    else:
        print(f"❌ Marcador Exacto: PERDEDORA! Real: {real_local}-{real_visitante} vs Pred: {pred_local}-{pred_visitante}")
        return "Perdedora"
        
def decidir_doble_oportunidad(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Determina si se cumple la doble oportunidad (EquipoA/Draw, EquipoB/Draw, o EquipoA/EquipoB).
    Args:
        favorito: "🍻 Paris Saint Germain/Draw", "🍻 Auxerre or Draw", etc.
    Returns:
        "Ganadora" si se cumple la condición, "Perdedora" si no.
    """
    if not event_id:
        print("❌ Error: Se requiere event_id para Doble Oportunidad")
        return "Perdedora"

    # Obtener datos del evento
    datos_evento = obtener_datos_evento(event_id)
    if not datos_evento or 'datos' not in datos_evento or 'marcador' not in datos_evento['datos']:
        print("❌ Error: Datos del evento no disponibles")
        return "Perdedora"

    # Marcador final
    marcador = datos_evento['datos']['marcador']
    local_score = int(marcador.get('local', 0))
    away_score = int(marcador.get('visitante', 0))
    print(f"🔢 Marcador Final: {local_score}-{away_score} | Predicción: {favorito}")

    # Limpieza de nombres MEJORADA - PRESERVAR "draw"
    def clean_name(name):
        # Primero reemplazar "/" por " / " para mantener separación
        name = name.replace("/", " / ")
        # Eliminar emojis pero mantener espacios, letras y la palabra "draw"
        cleaned = ''.join(c for c in name if c.isalpha() or c.isspace() or c == '/' or c == '-').strip().lower()
        # Reemplazar múltiples espacios por uno solo
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned
    
    # Limpiar nombres de equipos
    clean_home = clean_name(home_team)
    clean_away = clean_name(away_team)
    
    # Limpiar y procesar la predicción
    clean_pred = clean_name(favorito)
    
    print(f"🔍 Predicción limpia: '{clean_pred}' | Home: '{clean_home}' | Away: '{clean_away}'")
    
    # NUEVO: Manejar caso específico "draw / real madrid"
    if "draw /" in clean_pred or "/ draw" in clean_pred:
        # Extraer el equipo después del "draw /"
        if "draw /" in clean_pred:
            predicted_team = clean_pred.split("draw /")[1].strip()
        else:
            predicted_team = clean_pred.split("/ draw")[0].strip()
        
        print(f"🔍 Equipo predicho (formato Draw/Equipo): '{predicted_team}'")
        
        if predicted_team == clean_home:
            # Apuesta: Draw or Local
            print(f"✅ Apuesta: Draw or Local - {local_score}-{away_score}")
            if local_score == away_score or local_score > away_score:
                print("🎯 Resultado: Ganadora (Empate o Local gana)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Local pierde)")
                return "Perdedora"
        elif predicted_team == clean_away:
            # Apuesta: Draw or Visitante
            print(f"✅ Apuesta: Draw or Visitante - {local_score}-{away_score}")
            if away_score == local_score or away_score > local_score:
                print("🎯 Resultado: Ganadora (Empate o Visitante gana)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Visitante pierde)")
                return "Perdedora"
    
    # Formato 1: "equipo / draw" o "equipo/draw"
    elif "/ draw" in clean_pred or clean_pred.endswith("/draw"):
        # Extraer el nombre del equipo (eliminar " / draw")
        predicted_team = clean_pred.replace("/ draw", "").replace("/draw", "").strip()
        
        print(f"🔍 Equipo predicho (formato Equipo/Draw): '{predicted_team}'")
        
        if predicted_team == clean_home:
            # Apuesta: Local or Draw
            print(f"✅ Apuesta: Local or Draw - {local_score}-{away_score}")
            if local_score > away_score or local_score == away_score:
                print("🎯 Resultado: Ganadora (Local gana o empata)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Local pierde)")
                return "Perdedora"
        elif predicted_team == clean_away:
            # Apuesta: Visitante or Draw
            print(f"✅ Apuesta: Visitante or Draw - {local_score}-{away_score}")
            if away_score > local_score or away_score == local_score:
                print("🎯 Resultado: Ganadora (Visitante gana o empata)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Visitante pierde)")
                return "Perdedora"
    
    # Formato 2: "equipo or draw"
    elif " or draw" in clean_pred:
        # Extraer el nombre del equipo (eliminar " or draw")
        predicted_team = clean_pred.replace(" or draw", "").strip()
        
        print(f"🔍 Equipo predicho (formato or): '{predicted_team}'")
        
        if predicted_team == clean_home:
            # Apuesta: Local or Draw
            print(f"✅ Apuesta: Local or Draw - {local_score}-{away_score}")
            if local_score > away_score or local_score == away_score:
                print("🎯 Resultado: Ganadora (Local gana o empata)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Local pierde)")
                return "Perdedora"
        elif predicted_team == clean_away:
            # Apuesta: Visitante or Draw
            print(f"✅ Apuesta: Visitante or Draw - {local_score}-{away_score}")
            if away_score > local_score or away_score == local_score:
                print("🎯 Resultado: Ganadora (Visitante gana o empata)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Visitante pierde)")
                return "Perdedora"
    
    # Formato 3: "draw or equipo" (nuevo caso)
    elif "draw or " in clean_pred:
        # Extraer el nombre del equipo después de "draw or"
        predicted_team = clean_pred.split("draw or")[1].strip()
        
        print(f"🔍 Equipo predicho (formato Draw or): '{predicted_team}'")
        
        if predicted_team == clean_home:
            # Apuesta: Draw or Local
            print(f"✅ Apuesta: Draw or Local - {local_score}-{away_score}")
            if local_score == away_score or local_score > away_score:
                print("🎯 Resultado: Ganadora (Empate o Local gana)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Local pierde)")
                return "Perdedora"
        elif predicted_team == clean_away:
            # Apuesta: Draw or Visitante
            print(f"✅ Apuesta: Draw or Visitante - {local_score}-{away_score}")
            if away_score == local_score or away_score > local_score:
                print("🎯 Resultado: Ganadora (Empate o Visitante gana)")
                return "Ganadora"
            else:
                print("❌ Resultado: Perdedora (Visitante pierde)")
                return "Perdedora"
    
    # Formato 4: "equipo1 or equipo2" (sin empate)
    elif " or " in clean_pred and "draw" not in clean_pred:
        parts = [p.strip() for p in clean_pred.split(" or ")]
        if len(parts) == 2:
            team1, team2 = parts
            print(f"🔍 Doble oportunidad sin empate: {team1} o {team2}")
            
            # Verificar que los equipos coincidan con home/away (en cualquier orden)
            if ((team1 == clean_home and team2 == clean_away) or 
                (team1 == clean_away and team2 == clean_home)):
                if local_score != away_score:
                    print("🎯 Resultado: Ganadora (No hay empate)")
                    return "Ganadora"
                else:
                    print("❌ Resultado: Perdedora (Empate)")
                    return "Perdedora"
    
    print(f"❌ Error: Formato de doble oportunidad no reconocido: '{favorito}' -> '{clean_pred}'")
    print(f"🔍 Home: '{clean_home}' | Away: '{clean_away}'")
    return "Perdedora"
        
def decidir_marcador_exacto_mitad(scores, favorito, home_team, away_team, sport_key='', event_id=None, mitad=1):
    """
    Determina si el marcador exacto de la mitad (1ª o 2ª) coincide con la predicción.
    Args:
        favorito: 🔢 0-0, 🔢 1:0, etc. (acepta tanto '-' como ':' como separador)
        mitad: 1 (1ª mitad) o 2 (2ª mitad).
    """
    if not event_id:
        print(f"❌ Error: Se requiere event_id para Marcador Exacto en {'1ª' if mitad == 1 else '2ª'} mitad")
        return "Perdedora"

    # Obtener datos del evento
    datos_evento = obtener_datos_evento(event_id)
    if not datos_evento or 'datos' not in datos_evento or 'periodos' not in datos_evento['datos']:
        print("❌ Error: Datos del evento no disponibles")
        return "Perdedora"

    # Extraer periodo (1T o 2T)
    periodo = '1T' if mitad == 1 else '2T'
    periodo_data = datos_evento['datos']['periodos'].get(periodo, {})
    if not periodo_data:
        print(f"❌ Error: No hay datos para la {'1ª' if mitad == 1 else '2ª'} mitad")
        return "Perdedora"

    # Marcador real de la mitad
    real_local = periodo_data.get('local', 0)
    real_visitante = periodo_data.get('visitante', 0)
    print(f"🔢 Marcador Real ({periodo}): {real_local}-{real_visitante} | Predicción: {favorito}")

    # Extraer y estandarizar predicción (acepta "🔢 1-0" o "🔢 1:0")
    pred = favorito.replace("🔢", "").strip()
    try:
        # Reemplazar : por - para estandarizar
        pred_std = pred.replace(":", "-")
        pred_local, pred_visitante = map(int, pred_std.split('-'))
    except:
        print("❌ Error: Formato de predicción inválido. Debe ser '🔢 X-Y' o '🔢 X:Y'")
        return "Perdedora"

    # Comparar
    return "Ganadora" if (real_local == pred_local and real_visitante == pred_visitante) else "Perdedora"
        
        
def decidir_gol_local_2parte(scores, favorito, home_team, away_team, sport_key='', event_id=None, mitad=2):
    """
    Función para determinar si hubo Gol Local en la 2ª Parte (segunda mitad).
    Args:
        favorito: ⏳ Yes (si se espera gol local) o ⏳ No (si no se espera gol local)
    Returns:
        "Ganadora" si se cumple la predicción, "Perdedora" si no.
    """
    if not event_id:
        print("❌ Error: Se requiere event_id para verificar Gol Local en 2ª Parte")
        return "Perdedora"
    
    # Obtener datos del evento  
    datos_evento = obtener_datos_evento(event_id)  
    
    if not datos_evento or 'datos' not in datos_evento or 'periodos' not in datos_evento['datos']:  
        print("❌ Error: No se encontraron datos del evento o información de periodos")  
        return "Perdedora"  
    
    periodos = datos_evento['datos']['periodos']  
    
    # Obtener marcador de la 2ª Parte (2T)
    if '2T' in periodos:  
        marcador_2T = periodos['2T']  
        goles_local = marcador_2T.get('local', 0)  
    else:  
        print("❌ Error: No se encontraron datos para la segunda mitad (2T)")  
        return "Perdedora"  
    
    print(f"🔢 Gol(es) Local en 2ª Parte: {home_team} {goles_local}")  

    # Verificar si hubo gol local en la 2ª Parte
    hubo_gol_local = (goles_local > 0)
    
    # Comparar con la predicción (⏳ Yes = se espera gol local, ⏳ No = no se espera)
    if "⏳ Yes" in favorito:
        return "Ganadora" if hubo_gol_local else "Perdedora"
    elif "⏳ No" in favorito:
        return "Ganadora" if not hubo_gol_local else "Perdedora"
    else:
        print("❌ Error: Formato de favorito no reconocido. Debe ser '⏳ Yes' o '⏳ No'")
        return "Perdedora"        
        
        
#Equipo Marcará Primer Gol        
def decidir_primer_gol(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    try:
        if not event_id:
            print("❌ Error: Se requiere event_id para verificar el primer gol")
            return "Perdedora"
        
        datos_evento = obtener_datos_evento(event_id)
        
        if not datos_evento or 'datos' not in datos_evento or 'eventos' not in datos_evento['datos']:
            print("❌ Error: No se encontraron datos del evento o información de eventos")
            return "Perdedora"
        
        eventos = datos_evento['datos']['eventos']
        
        # Limpiar nombres para comparación (eliminar emojis y normalizar)
        def clean_name(name):
            return ''.join(c for c in name.lower() if c.isalpha() or c.isspace()).strip()
        
        clean_fav = clean_name(favorito.replace("🥅", ""))  # "central cordoba de santiago"
        clean_home = clean_name(home_team)  # "central cordoba de santiago"
        clean_away = clean_name(away_team)  # "independ. rivadavia"
        
        # Buscar el primer gol
        primer_gol = next((e for e in eventos if e.get('tipo') == 'goal'), None)
        
        if not primer_gol:
            return "Perdedora"  # No hubo goles
        
        # Determinar equipo del primer gol
        equipo_gol = primer_gol.get('equipo')  # "local" o "visitante"
        
        # Comparar con el favorito
        if (equipo_gol == "local" and clean_fav == clean_home) or (equipo_gol == "visitante" and clean_fav == clean_away):
            return "Ganadora"
        else:
            return "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_primer_gol: {str(e)}")
        return "Perdedora"

def decidir_h2h(scores, favorito, home_team, away_team, sport_key=''):
    """
    Decide resultado h2h con manejo especial para empates según deporte
    """
    def clean_name(name):
        return ''.join(c for c in name if c.isalpha() or c.isspace()).strip()
    
    try:
        home_score = next((int(score['score']) for score in scores 
                         if clean_name(score['name']) == clean_name(home_team)), 0)
        away_score = next((int(score['score']) for score in scores 
                         if clean_name(score['name']) == clean_name(away_team)), 0)
        
        print(f"🔢 Scores: {home_team} {home_score}-{away_score} {away_team}")

        clean_fav = clean_name(favorito)
        clean_home = clean_name(home_team)
        clean_away = clean_name(away_team)

        # Primero verificar si la predicción era empate (Draw)
        if "draw" or "Empate" in clean_fav.lower():  # Maneja "🏆 Draw", "Draw", etc.
            return "Ganadora" if home_score == away_score else "Perdedora"
        
        # Luego el resto de la lógica
        if home_score > away_score:
            return "Ganadora" if clean_fav == clean_home else "Perdedora"
        elif away_score > home_score:
            return "Ganadora" if clean_fav == clean_away else "Perdedora"
        else:
            # Solo llega aquí si hay empate y NO se predijo empate
            if sport_key.startswith(('baseball', 'tennis')):
                return "Reembolso"
            else:
                return "Perdedora"
                
    except Exception as e:
        print(f"❌ Error en decidir_h2h: {str(e)}")
        return "Perdedora"
        
        
def decidir_h2h_mitad(scores, favorito, home_team, away_team, sport_key='', event_id=None, mitad=None):
    """
    Función unificada para decidir ganador de 1ra o 2da mitad
    Args:
        mitad: 1 para primera mitad, 2 para segunda mitad
        favorito: Puede ser el nombre de un equipo o "⏱️ Draw"
    """
    if not event_id:
        print(f"❌ Error: Se requiere event_id para determinar el ganador de la {'1ra' if mitad == 1 else '2da'} mitad")
        return "Perdedora"
    
    # Obtener datos del evento  
    datos_evento = obtener_datos_evento(event_id)  
    
    if not datos_evento or 'datos' not in datos_evento or 'periodos' not in datos_evento['datos']:  
        print("❌ Error: No se encontraron datos del evento o información de periodos")  
        return "Perdedora"  
    
    periodos = datos_evento['datos']['periodos']  
    
    # Determinar el periodo a evaluar
    periodo = '1T' if mitad == 1 else '2T'
    
    # Obtener marcador del periodo especificado
    if periodo in periodos:  
        marcador = periodos[periodo]  
        home_score = marcador.get('local', 0)  
        away_score = marcador.get('visitante', 0)  
    else:  
        print(f"❌ Error: No se encontraron datos para el {'primer' if mitad == 1 else 'segundo'} tiempo")  
        return "Perdedora"  
    
    print(f"🔢 Scores {'1ra' if mitad == 1 else '2da'} mitad: {home_team} {home_score}-{away_score} {away_team}")  

    def clean_name(name):  
        return ''.join(c for c in name if c.isalpha() or c.isspace()).strip().lower()  
    
    clean_fav = clean_name(favorito)  
    clean_home = clean_name(home_team)  
    clean_away = clean_name(away_team)  

    if home_score > away_score:  
        return "Ganadora" if clean_fav == clean_home else "Perdedora"  
    elif away_score > home_score:  
        return "Ganadora" if clean_fav == clean_away else "Perdedora"  
    else:  
        # Caso de empate: solo gana si el favorito es "Draw"
        return "Ganadora" if "draw" in clean_fav else "Perdedora"
        
#total de disparos a puerta        
def decidir_shots_on_goal(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Función para determinar si una apuesta de Total Disparos a Puerta (Shots on Goal) es ganadora.
    
    Args:
        scores: Lista de scores (no se usa directamente aquí, pero se mantiene por consistencia)
        favorito: String con el formato "🎯 Over X.5" o "🎯 Under X.5" (ej: "🎯 Over 8.5")
        home_team: Nombre del equipo local
        away_team: Nombre del equipo visitante
        sport_key: Clave del deporte (opcional)
        event_id: ID del evento para obtener estadísticas
    
    Returns:
        "Ganadora" si la apuesta es correcta, "Perdedora" si no
    """
    try:
        # Verificar si tenemos event_id para obtener estadísticas
        if not event_id:
            print("❌ Error: Se requiere event_id para verificar disparos a puerta")
            return "Perdedora"
        
        # Obtener datos del evento
        datos_evento = obtener_datos_evento(event_id)
        
        if not datos_evento or 'datos' not in datos_evento or 'estadisticas' not in datos_evento['datos']:
            print("❌ Error: No se encontraron datos del evento o estadísticas")
            return "Perdedora"
        
        estadisticas = datos_evento['datos']['estadisticas']
        
        # Obtener disparos a puerta de ambos equipos
        shots_on_goal = estadisticas.get('Shots on Goal', {})
        home_shots = int(shots_on_goal.get('local', 0))
        away_shots = int(shots_on_goal.get('visitante', 0))
        total_shots = home_shots + away_shots
        
        print(f"🎯 Total disparos a puerta: {total_shots} (Local: {home_shots} - Visitante: {away_shots})")
        
        # Extraer el número y el tipo de apuesta (Over/Under)
        if "Over" in favorito:
            apuesta_tipo = "Over"
            # Extraer el número (ej: "🎯 Over 8.5" -> 8.5)
            apuesta_valor = float(favorito.split("Over")[1].strip().split()[0])
        elif "Under" in favorito:
            apuesta_tipo = "Under"
            apuesta_valor = float(favorito.split("Under")[1].strip().split()[0])
        else:
            print(f"❌ Formato de favorito no reconocido: {favorito}")
            return "Perdedora"
        
        # Determinar resultado
        if apuesta_tipo == "Over":
            return "Ganadora" if total_shots > apuesta_valor else "Perdedora"
        else:  # Under
            return "Ganadora" if total_shots < apuesta_valor else "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_shots_on_goal: {str(e)}")
        return "Perdedora"        
                
def decidir_anotador_partido(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    if not event_id:
        print("❌ Error: Se requiere event_id para verificar anotador")
        return "Perdedora"
    
    event_id = str(event_id)
    print(f"🔍 Buscando goles para el evento con event_id: {event_id}")
    
    datos_evento = obtener_datos_evento(event_id)
    
    if not datos_evento or 'datos' not in datos_evento or 'eventos' not in datos_evento['datos']:
        print("❌ Error: No se encontraron datos del evento o información de eventos")
        return "Perdedora"
    
    def limpiar_nombre(nombre):
        nombre_limpio = ''.join(c for c in nombre if c.isalpha() or c.isspace() or c in "'-.")
        nombre_limpio = nombre_limpio.replace('.', '').split()
        if len(nombre_limpio) > 1:
            nombre_limpio = nombre_limpio[-1]  # Solo el apellido
        else:
            nombre_limpio = nombre_limpio[0] if nombre_limpio else ""
        return nombre_limpio.lower().strip()
    
    jugador_buscado = limpiar_nombre(favorito)
    print(f"🔍 Buscando goles para: '{favorito}' (normalizado: '{jugador_buscado}')")
    
    goles_encontrados = []
    for evento in datos_evento['datos']['eventos']:
        if evento.get('tipo') == 'goal' and evento.get('tipo_gol') != 'own goal':
            jugador_gol = limpiar_nombre(evento.get('jugador', ''))
            print(f"⚽ Revisando gol de: '{evento.get('jugador')}' (normalizado: '{jugador_gol}')")
            if jugador_gol == jugador_buscado:
                goles_encontrados.append(evento)
                print(f"✅ Gol coincidente encontrado al minuto {evento.get('minuto')}")
    
    if goles_encontrados:
        print(f"🏆 El jugador {favorito} marcó {len(goles_encontrados)} gol(es):")
        for gol in goles_encontrados:
            print(f"   - Min {gol['minuto']}' ({gol.get('tipo_gol', 'tipo no especificado')})")
        return "Ganadora"
    else:
        print(f"❌ No se encontraron goles para {favorito}")
        goleadores = set()
        for evento in datos_evento['datos']['eventos']:
            if evento.get('tipo') == 'goal' and evento.get('tipo_gol') != 'own goal':
                goleadores.add(evento.get('jugador', 'Desconocido'))
        print(f"ℹ️ Goleadores en el partido: {', '.join(goleadores)}")
        return "Perdedora"



def decidir_total_mitad(scores, favorito, home_team, away_team, sport_key, event_id, total=None, mitad=1):
    """Decide totales para primera o segunda mitad"""
    try:
        if total is None:
            match = re.search(r"[-+]?\d+(\.\d+)?", favorito)
            if match:
                total = float(match.group())
                print(f"ℹ️ Total extraído de 'favorito': {total}")
            else:
                print("❌ No se especificó la línea del total y no se pudo extraer")
                return "Perdedora"

        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento or 'datos' not in datos_evento or 'periodos' not in datos_evento['datos']:
            print("❌ No se encontraron datos del evento o de los periodos")
            return "Perdedora"
        
        periodos = datos_evento['datos']['periodos']
        home_score = away_score = 0

        # Detectar si es fútbol (mitades) o básquet (cuartos)
        if '1T' in periodos or '2T' in periodos:
            periodo = '1T' if mitad == 1 else '2T'
            periodo_data = periodos.get(periodo, {})
            if not periodo_data:
                print(f"❌ No hay datos para el tiempo {periodo}")
                return "Perdedora"
            home_score = periodo_data.get('local', 0)
            away_score = periodo_data.get('visitante', 0)
        else:
            # Básquet: sumar cuartos
            cuartos = ['1Q', '2Q'] if mitad == 1 else ['3Q', '4Q']
            for q in cuartos:
                marcador = periodos.get(q, {})
                home_score += marcador.get('local', 0)
                away_score += marcador.get('visitante', 0)
            print("⛹️ Detectado deporte con cuartos (probablemente básquet)")

        total_goles = home_score + away_score
        print(f"🔢 Total {'1ra' if mitad == 1 else '2da'} mitad: {total_goles} | Línea: {total}")
        
        if "over" in favorito.lower():
            return "Ganadora" if total_goles > total else "Perdedora"
        elif "under" in favorito.lower():
            return "Ganadora" if total_goles < total else "Perdedora"
        else:
            print("❌ No se pudo determinar si es over o under")
            return "Perdedora"

    except Exception as e:
        print(f"❌ Error en decidir_total_mitad: {str(e)}")
        return "Perdedora"

#Aplica al futbol x tiempo y al básquet por 2 tiempos
def decidir_handicap_mitad(scores, favorito, home_team, away_team, sport_key='', event_id=None, handicap=None, mitad=1):
    if not event_id:
        print(f"❌ Error: Se requiere event_id para el hándicap de la {'1ra' if mitad == 1 else '2da'} mitad")
        return "Perdedora"

    if handicap is None:
        match = re.search(r"[-+]?\d+(\.\d+)?", favorito)
        if match:
            handicap = float(match.group())
            print(f"ℹ️ Valor del hándicap extraído de 'favorito': {handicap}")
        else:
            print("❌ Error: No se especificó el valor del hándicap")
            return "Perdedora"

    datos_evento = obtener_datos_evento(event_id)
    if not datos_evento or 'datos' not in datos_evento or 'periodos' not in datos_evento['datos']:
        print("❌ Error: No se encontraron datos del evento o información de periodos")
        return "Perdedora"

    periodos = datos_evento['datos']['periodos']
    home_score = away_score = 0

    if '1T' in periodos or '2T' in periodos:
        # Fútbol u otro deporte con mitades
        periodo = '1T' if mitad == 1 else '2T'
        if periodo in periodos:
            marcador = periodos[periodo]
            home_score = marcador.get('local', 0)
            away_score = marcador.get('visitante', 0)
        else:
            print(f"❌ Error: No se encontraron datos para el {'primer' if mitad == 1 else 'segundo'} tiempo (fútbol)")
            return "Perdedora"
    else:
        # Básquet o deportes con cuartos
        cuartos = ['1Q', '2Q'] if mitad == 1 else ['3Q', '4Q']
        for q in cuartos:
            marcador = periodos.get(q, {})
            home_score += marcador.get('local', 0)
            away_score += marcador.get('visitante', 0)
        print(f"⛹️ Detectado deporte con cuartos (probablemente básquet)")

    print(f"📊 Marcador {'1ra' if mitad == 1 else '2da'} mitad (sin hándicap): {home_team} {home_score}-{away_score} {away_team}")
    print(f"🔧 Hándicap aplicado: {handicap}")

    if home_team in favorito:
        home_score += handicap
        print(f"➕ Aplicando hándicap {handicap} al local ({home_team})")
    elif away_team in favorito:
        away_score += handicap
        print(f"➕ Aplicando hándicap {handicap} al visitante ({away_team})")
    else:
        print(f"❌ No se pudo determinar el equipo del favorito: {favorito}")
        return "Perdedora"

    print(f"📈 Marcador con hándicap: {home_team} {home_score}-{away_score} {away_team}")

    if home_score > away_score:
        return "Ganadora" if home_team in favorito else "Perdedora"
    elif away_score > home_score:
        return "Ganadora" if away_team in favorito else "Perdedora"
    else:
        print("⚖️ Empate exacto después de aplicar hándicap")
        return "Perdedora"              

                
                
                
                
                
# ---------- Funciones para mercados principales ----------
def decidir_total(scores, favorito, home_team, away_team, sport_key, total=None, alternate=False):
    """Decide apuestas de totales (over/under) extrayendo el valor de la línea del texto 'favorito'"""
    try:
        home_score = next((int(score['score']) for score in scores if score['name'] == home_team), 0)
        away_score = next((int(score['score']) for score in scores if score['name'] == away_team), 0)
        total_goles = home_score + away_score
        
        # Extraer el valor numérico de la línea (ej: "Under 1.5" → 1.5)
        import re
        match = re.search(r"\d+\.?\d*", favorito)  # Busca números enteros o decimales
        if not match:
            print("❌ No se encontró un valor numérico en 'favorito'")
            return "Perdedora"
        
        linea = float(match.group())  # Convertir a número (ej: "1.5" → 1.5)
        
        print(f"🔢 Total real: {total_goles} | Línea extraída: {linea}")
        
        if "over" in favorito.lower():
            return "Ganadora" if total_goles > linea else "Perdedora"
        elif "under" in favorito.lower():
            return "Ganadora" if total_goles < linea else "Perdedora"
        else:
            print("❌ No se pudo determinar si es Over o Under en 'favorito'")
            return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_total: {str(e)}")
        return "Perdedora"

def decidir_handicap(scores, favorito, home_team, away_team, sport_key, handicap=None, alternate=False):
    """Decide apuestas de handicap"""
    try:
        home_score = next((int(score['score']) for score in scores if score['name'] == home_team), 0)
        away_score = next((int(score['score']) for score in scores if score['name'] == away_team), 0)
        
        # Aplicar handicap
        if home_team in favorito:
            home_score += handicap
        else:
            away_score += handicap
        
        print(f"📊 Marcador con handicap: {home_score}-{away_score}")
        
        if home_score > away_score:
            return "Ganadora" if home_team in favorito else "Perdedora"
        elif away_score > home_score:
            return "Ganadora" if away_team in favorito else "Perdedora"
        else:
            return "Perdedora" if alternate else "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_handicap: {str(e)}")
        return "Perdedora"

# ---------- Funciones para mercados por tiempos ----------


def decidir_team_total_mitad(scores, favorito, home_team, away_team, sport_key, event_id, total=None, team=None, mitad=1):
    """Decide total por equipo en una mitad específica"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        periodo = '1T' if mitad == 1 else '2T'
        periodo_data = datos_evento.get('datos', {}).get('periodos', {}).get(periodo, {})
        
        if not periodo_data:
            print(f"❌ No hay datos para {periodo}")
            return "Perdedora"
            
        # Determinar si el equipo es local o visitante
        if team == home_team:
            team_score = periodo_data.get('local', 0)
        elif team == away_team:
            team_score = periodo_data.get('visitante', 0)
        else:
            print(f"❌ Equipo no reconocido: {team}")
            return "Perdedora"
        
        print(f"🔰 Total {team} en {periodo}: {team_score} | Línea: {total}")
        
        if "over" in favorito.lower():
            return "Ganadora" if team_score > total else "Perdedora"
        elif "under" in favorito.lower():
            return "Ganadora" if team_score < total else "Perdedora"
        else:
            print("❌ No se pudo determinar si es over o under")
            return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_team_total_mitad: {str(e)}")
        return "Perdedora"

# ---------- Funciones para mercados de jugadores ----------
def decidir_primer_anotador(scores, favorito, home_team, away_team, sport_key, event_id):
    """Decide apuestas de primer anotador"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        eventos = datos_evento.get('datos', {}).get('eventos', [])
        goles = [e for e in eventos if e.get('tipo') == 'goal']
        
        if not goles:
            print("❌ No hubo goles en el partido")
            return "Perdedora"
            
        primer_gol = min(goles, key=lambda x: x.get('minuto', 999))
        jugador_primer_gol = primer_gol.get('jugador', '')
        
        # Limpiar nombres para comparación
        def limpiar_nombre(nombre):
            return ''.join(c for c in nombre if c.isalpha() or c.isspace()).strip().lower()
        
        if limpiar_nombre(jugador_primer_gol) == limpiar_nombre(favorito):
            print(f"🥇 Primer gol: {jugador_primer_gol} (min {primer_gol.get('minuto')})")
            return "Ganadora"
        else:
            print(f"❌ Primer gol lo marcó {jugador_primer_gol}, no {favorito}")
            return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_primer_anotador: {str(e)}")
        return "Perdedora"

def decidir_ultimo_anotador(scores, favorito, home_team, away_team, sport_key, event_id):
    """Decide apuestas de último anotador"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        eventos = datos_evento.get('datos', {}).get('eventos', [])
        goles = [e for e in eventos if e.get('tipo') == 'goal']
        
        if not goles:
            print("❌ No hubo goles en el partido")
            return "Perdedora"
            
        ultimo_gol = max(goles, key=lambda x: x.get('minuto', 0))
        jugador_ultimo_gol = ultimo_gol.get('jugador', '')
        
        # Limpiar nombres para comparación
        def limpiar_nombre(nombre):
            return ''.join(c for c in nombre if c.isalpha() or c.isspace()).strip().lower()
        
        if limpiar_nombre(jugador_ultimo_gol) == limpiar_nombre(favorito):
            print(f"🥉 Último gol: {jugador_ultimo_gol} (min {ultimo_gol.get('minuto')})")
            return "Ganadora"
        else:
            print(f"❌ Último gol lo marcó {jugador_ultimo_gol}, no {favorito}")
            return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_ultimo_anotador: {str(e)}")
        return "Perdedora"

def decidir_jugador_amonestado(scores, favorito, home_team, away_team, sport_key, event_id):
    """Decide apuestas de jugador amonestado (tarjeta amarilla)"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        eventos = datos_evento.get('datos', {}).get('eventos', [])
        
        # Limpiar nombres para comparación
        def limpiar_nombre(nombre):
            return ''.join(c for c in nombre if c.isalpha() or c.isspace()).strip().lower()
        
        tarjetas = [e for e in eventos if e.get('tipo') == 'card' and e.get('tipo_tarjeta', '').lower() == 'yellow']
        
        for tarjeta in tarjetas:
            if limpiar_nombre(tarjeta.get('jugador', '')) == limpiar_nombre(favorito):
                print(f"🟨 Tarjeta amarilla a {favorito} en min {tarjeta.get('minuto')}")
                return "Ganadora"
        
        print(f"❌ {favorito} no recibió tarjeta amarilla")
        return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_jugador_amonestado: {str(e)}")
        return "Perdedora"

def decidir_jugador_expulsado(scores, favorito, home_team, away_team, sport_key, event_id):
    """Decide apuestas de jugador expulsado (tarjeta roja)"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        eventos = datos_evento.get('datos', {}).get('eventos', [])
        
        # Limpiar nombres para comparación
        def limpiar_nombre(nombre):
            return ''.join(c for c in nombre if c.isalpha() or c.isspace()).strip().lower()
        
        tarjetas = [e for e in eventos if e.get('tipo') == 'card' and e.get('tipo_tarjeta', '').lower() == 'red']
        
        for tarjeta in tarjetas:
            if limpiar_nombre(tarjeta.get('jugador', '')) == limpiar_nombre(favorito):
                print(f"🟥 Tarjeta roja a {favorito} en min {tarjeta.get('minuto')}")
                return "Ganadora"
        
        print(f"❌ {favorito} no recibió tarjeta roja")
        return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_jugador_expulsado: {str(e)}")
        return "Perdedora"

# ---------- Funciones para mercados especiales ----------
#Total de Tarjetas
def decidir_total_tarjetas(scores, favorito, home_team, away_team, sport_key='', event_id=None):
    """
    Función para determinar si una apuesta de Total de Tarjetas (Over/Under) es ganadora.
    Considera todas las tarjetas (amarillas y rojas) sin distinción.
    
    Args:
        scores: Lista de scores (no se usa directamente aquí, pero se mantiene por consistencia)
        favorito: String con el formato "🔢 Over X.5" o "🔢 Under X.5" (ej: "🔢 Over 3.5")
        home_team: Nombre del equipo local (no necesario para esta apuesta)
        away_team: Nombre del equipo visitante (no necesario para esta apuesta)
        sport_key: Clave del deporte (opcional)
        event_id: ID del evento para obtener los eventos del partido
    
    Returns:
        "Ganadora" si la apuesta es correcta, "Perdedora" si no
    """
    try:
        # Verificar si tenemos event_id para obtener datos
        if not event_id:
            print("❌ Error: Se requiere event_id para verificar tarjetas")
            return "Perdedora"
        
        # Obtener datos del evento
        datos_evento = obtener_datos_evento(event_id)
        
        if not datos_evento or 'datos' not in datos_evento or 'eventos' not in datos_evento['datos']:
            print("❌ Error: No se encontraron datos del evento o información de eventos")
            return "Perdedora"
        
        eventos = datos_evento['datos']['eventos']
        
        # Contar todas las tarjetas (amarillas y rojas)
        total_tarjetas = 0
        for evento in eventos:
            if evento.get('tipo') == 'card':
                total_tarjetas += 1
        
        print(f"🟨🔴 Total de tarjetas en el partido: {total_tarjetas}")
        
        # Extraer el número y el tipo de apuesta (Over/Under)
        if "Over" in favorito:
            apuesta_tipo = "Over"
            # Extraer el número (ej: "🔢 Over 3.5" -> 3.5)
            apuesta_valor = float(favorito.split("Over")[1].strip().split()[0])
        elif "Under" in favorito:
            apuesta_tipo = "Under"
            apuesta_valor = float(favorito.split("Under")[1].strip().split()[0])
        else:
            print(f"❌ Formato de favorito no reconocido: {favorito}")
            return "Perdedora"
        
        # Determinar resultado
        if apuesta_tipo == "Over":
            return "Ganadora" if total_tarjetas > apuesta_valor else "Perdedora"
        else:  # Under
            return "Ganadora" if total_tarjetas < apuesta_valor else "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_total_tarjetas: {str(e)}")
        return "Perdedora"
                
def decidir_handicap_tarjetas(scores, favorito, home_team, away_team, sport_key, event_id, handicap=None):
    """Decide apuestas de handicap de tarjetas con manejo mejorado"""
    try:
        # Verificación de parámetros esenciales
        if not event_id:
            print("❌ Error: event_id es requerido")
            return "Perdedora"
            
        if handicap is None:
            print("❌ Error: No se especificó el handicap")
            return "Perdedora"
        
        # Obtener datos del evento
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento or 'datos' not in datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        eventos = datos_evento['datos'].get('eventos', [])
        
        # Función para calcular puntos de tarjetas por equipo
        def calcular_puntos_tarjetas(equipo):
            puntos = 0
            for evento in eventos:
                if evento.get('tipo') == 'card' and evento.get('equipo') == equipo:
                    tipo_tarjeta = evento.get('tipo_tarjeta', '').lower()
                    if tipo_tarjeta == 'yellow':
                        puntos += 1
                    elif tipo_tarjeta == 'red':
                        puntos += 2
            return puntos
        
        # Calcular puntos para ambos equipos
        puntos_local = calcular_puntos_tarjetas('local')
        puntos_visitante = calcular_puntos_tarjetas('visitante')
        
        print(f"📊 Puntos tarjetas brutos: Local {puntos_local}-{puntos_visitante} Visitante")
        
        # Determinar a qué equipo aplicar el handicap
        if home_team in favorito:
            puntos_local += handicap
            print(f"➕ Aplicando handicap {handicap} al local ({home_team})")
        elif away_team in favorito:
            puntos_visitante += handicap
            print(f"➕ Aplicando handicap {handicap} al visitante ({away_team})")
        else:
            print(f"❌ No se pudo determinar el equipo del favorito: {favorito}")
            return "Perdedora"
        
        print(f"📈 Puntos tarjetas con handicap: Local {puntos_local}-{puntos_visitante} Visitante")
        
        # Determinar resultado
        if puntos_local > puntos_visitante:
            return "Ganadora" if home_team in favorito else "Perdedora"
        elif puntos_visitante > puntos_local:
            return "Ganadora" if away_team in favorito else "Perdedora"
        else:
            print("⚖️ Empate exacto en puntos de tarjetas")
            return "Perdedora"  # O "Reembolso" según reglas de la casa de apuestas
            
    except Exception as e:
        print(f"❌ Error crítico en decidir_handicap_tarjetas: {str(e)}")
        return "Perdedora"                
                
                
      
def decidir_handicap_baseball(scores, favorito, home_team, away_team, sport_key, event_id, handicap=None, entradas=1):
    """Decide apuestas de handicap para baseball por entradas específicas"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        # Obtener datos de las entradas especificadas
        entradas_data = datos_evento.get('datos', {}).get('entradas', {})
        if not entradas_data:
            print("❌ No hay datos de entradas en el partido")
            return "Perdedora"
            
        # Calcular puntuación acumulada hasta las entradas especificadas
        home_score = 0
        away_score = 0
        
        for i in range(1, entradas + 1):
            entrada_key = f"{i}E"
            if entrada_key in entradas_data:
                home_score += entradas_data[entrada_key].get('local', 0)
                away_score += entradas_data[entrada_key].get('visitante', 0)
        
        print(f"⚾ Marcador hasta {entradas} entradas: {home_team} {home_score}-{away_score} {away_team}")
        
        # Aplicar handicap
        if home_team in favorito:
            home_score += handicap
        else:
            away_score += handicap
        
        print(f"📊 Marcador con handicap: {home_score}-{away_score}")
        
        if home_score > away_score:
            return "Ganadora" if home_team in favorito else "Perdedora"
        elif away_score > home_score:
            return "Ganadora" if away_team in favorito else "Perdedora"
        else:
            return "Reembolso"
            
    except Exception as e:
        print(f"❌ Error en decidir_handicap_baseball: {str(e)}")
        return "Perdedora"

def decidir_total_baseball(scores, favorito, home_team, away_team, sport_key, event_id, total=None, entradas=1):
    """Decide apuestas de total para baseball por entradas específicas"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        if total is None:
            print("❌ No se especificó el total para la apuesta")
            return "Perdedora"
            
        # Obtener datos de las entradas especificadas
        entradas_data = datos_evento.get('datos', {}).get('entradas', {})
        if not entradas_data:
            print("❌ No hay datos de entradas en el partido")
            return "Perdedora"
            
        # Calcular total de carreras hasta las entradas especificadas
        total_carreras = 0
        for i in range(1, entradas + 1):
            entrada_key = f"{i}E"
            if entrada_key in entradas_data:
                total_carreras += entradas_data[entrada_key].get('local', 0)
                total_carreras += entradas_data[entrada_key].get('visitante', 0)
        
        print(f"⚾ Total carreras hasta {entradas} entradas: {total_carreras} | Línea: {total}")
        
        if "over" in favorito.lower():
            return "Ganadora" if total_carreras > total else "Perdedora"
        elif "under" in favorito.lower():
            return "Ganadora" if total_carreras < total else "Perdedora"
        else:
            print("❌ No se pudo determinar si es over o under")
            return "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_total_baseball: {str(e)}")
        return "Perdedora"

def decidir_handicap_baloncesto(scores, favorito, home_team, away_team, sport_key, event_id, handicap=None, periodo='Q1'):
    """Decide apuestas de handicap para baloncesto por cuartos específicos"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        # Obtener datos del periodo especificado
        periodos_data = datos_evento.get('datos', {}).get('periodos', {})
        if periodo not in periodos_data:
            print(f"❌ No hay datos para el periodo {periodo}")
            return "Perdedora"
            
        periodo_data = periodos_data[periodo]
        home_score = periodo_data.get('local', 0)
        away_score = periodo_data.get('visitante', 0)
        
        print(f"🏀 Marcador en {periodo}: {home_team} {home_score}-{away_score} {away_team}")
        
        # Aplicar handicap
        if home_team in favorito:
            home_score += handicap
        else:
            away_score += handicap
        
        print(f"📊 Marcador con handicap: {home_score}-{away_score}")
        
        if home_score > away_score:
            return "Ganadora" if home_team in favorito else "Perdedora"
        elif away_score > home_score:
            return "Ganadora" if away_team in favorito else "Perdedora"
        else:
            return "Reembolso"
            
    except Exception as e:
        print(f"❌ Error en decidir_handicap_baloncesto: {str(e)}")
        return "Perdedora"

def decidir_total_baloncesto(scores, favorito, home_team, away_team, sport_key, event_id, total=None, periodo='Q1'):
    """Decide apuestas de total para baloncesto por cuartos específicos"""
    try:
        datos_evento = obtener_datos_evento(event_id)
        if not datos_evento:
            print("❌ No se encontraron datos del evento")
            return "Perdedora"
            
        if total is None:
            print("❌ No se especificó el total para la apuesta")
            return "Perdedora"
            
        # Obtener datos del periodo especificado
        periodos_data = datos_evento.get('datos', {}).get('periodos', {})
        if periodo not in periodos_data:
            print(f"❌ No hay datos para el periodo {periodo}")
            return "Perdedora"
            
        periodo_data = periodos_data[periodo]
        home_score = periodo_data.get('local', 0)
        away_score = periodo_data.get('visitante', 0)
        total_puntos = home_score + away_score
        
        print(f"🏀 Total puntos en {periodo}: {total_puntos} | Línea: {total}")
        
        if "over" in favorito.lower():
            return "Ganadora" if total_puntos > total else "Perdedora"
        elif "under" in favorito.lower():
            return "Ganadora" if total_puntos < total else "Perdedora"
        else:
            print("❌ No se pudo determinar si es over o under")
            return "Perdedora"
            
    except Exception as e:
        print(f"❌ Error en decidir_total_baloncesto: {str(e)}")
        return "Perdedora"                
                          
                                    
                                                        
                
def decidir_team_total(scores, favorito, home_team, away_team, sport_key, total=None, team=None):
    """Decide total por equipo"""
    try:
        if team == home_team:
            team_score = next((int(score['score']) for score in scores if score['name'] == home_team), 0)
        elif team == away_team:
            team_score = next((int(score['score']) for score in scores if score['name'] == away_team), 0)
        else:
            print(f"❌ Equipo no reconocido: {team}")
            return "Perdedora"
        
        print(f"🔰 Total {team}: {team_score} | Línea: {total}")
        
        if "over" in favorito.lower():
            return "Ganadora" if team_score > total else "Perdedora"
        elif "under" in favorito.lower():
            return "Ganadora" if team_score < total else "Perdedora"
        else:
            print("❌ No se pudo determinar si es over o under")
            return "Perdedora"
    except Exception as e:
        print(f"❌ Error en decidir_team_total: {str(e)}")
        return "Perdedora"


    
def decidir_total_anotaciones(scores, favorito, home_team, away_team, sport_key=''):
    """Versión mejorada con manejo de empates exactos"""
    try:
        home_score = int(next((score['score'] for score in scores if score['name'] == home_team), 0))
        away_score = int(next((score['score'] for score in scores if score['name'] == away_team), 0))
        total = home_score + away_score

        # Extraer el número del favorito (ej: "Over 2.25" → 2.25)
        try:
            numero = float(''.join(filter(lambda x: x.isdigit() or x == '.', favorito)))
        except ValueError:
            return "Perdedora"

        # Manejo especial para empates exactos
        if total == numero and numero.is_integer():
            print("⚖️ Empate exacto en Total de Anotaciones -> Reembolso")
            return "Reembolso"

        if "Over" in favorito:
            return "Ganadora" if total > numero else "Perdedora"
        elif "Under" in favorito:
            return "Ganadora" if total < numero else "Perdedora"
        else:
            return "Perdedora"

    except Exception as e:
        print(f"❌ Error en decidir_total_anotaciones: {str(e)}")
        return "Perdedora"


def decidir_btts(scores, favorito, home_team, away_team, sport_key=''):
    """
    Versión corregida que maneja "⚽ Yes" y "⚽ No" como valores de favorito.
    También maneja "Ambos marcan: Yes" y los casos tradicionales "Sí"/"No".
    """
    try:
        home_score = int(next((score['score'] for score in scores if score['name'] == home_team), 0))
        away_score = int(next((score['score'] for score in scores if score['name'] == away_team), 0))

        # Caso especial: 0-0
        if home_score == 0 and away_score == 0:
            # Para empate 0-0, todas las apuestas BTTS pierden excepto "No" o "⚽ No"
            if favorito in ["No", "⚽ No"]:
                return "Ganadora"
            else:
                return "Perdedora"

        ambos_anotaron = home_score > 0 and away_score > 0

        # Normalizar el valor de favorito
        if favorito in ["Sí", "Yes", "⚽ Yes", "Ambos marcan: Yes"]:
            # Casos donde se apuesta que ambos marcarán
            return "Ganadora" if ambos_anotaron else "Perdedora"
        elif favorito in ["No", "⚽ No"]:
            # Casos donde se apuesta que NO ambos marcarán
            return "Ganadora" if not ambos_anotaron else "Perdedora"
        else:
            # Valor de favorito no reconocido, considerar como perdedora
            return "Perdedora"

    except Exception as e:
        print(f"❌ Error en decidir_btts: {str(e)}")
        return "Perdedora"
        
def decidir_dnb(scores, favorito, home_team, away_team, sport_key=''):
    """Versión con depuración para analizar el problema"""
    try:
        # Extraer solo el nombre del equipo favorito
        favorito = favorito.replace("Sin empate: ", "").strip()

        # Obtener los puntajes del partido
        home_score = int(next((score['score'] for score in scores if score['name'] == home_team), 0))
        away_score = int(next((score['score'] for score in scores if score['name'] == away_team), 0))

        # Determinar el ganador
        if home_score > away_score:
            ganador = home_team
        elif away_score > home_score:
            ganador = away_team
        else:
            print(f"🟡 Empate detectado: {home_team} {home_score} - {away_score} {away_team} → Reembolso")
            return "Reembolso"

        

        # Verificar si el ganador coincide con el favorito
        resultado = "Ganadora" if ganador == favorito else "Perdedora"
        print(f"   - Resultado Final: {resultado}")

        return resultado

    except Exception as e:
        print(f"❌ Error en decidir_dnb: {str(e)}")
        return "Perdedora"                        
                                
                                        
                                                
                                                        


def obtener_datos_evento(event_id):
    """
    Busca en el archivo resultados.json los datos del evento con el event_id especificado
    y los devuelve exactamente como están en el archivo.
    
    Args:
        event_id (str): El ID del evento a buscar
        
    Returns:
        dict: Los datos del evento si se encuentra, None si no se encuentra
    """
    try:
        # Abrir y cargar el archivo JSON
        with open('resultados.json', 'r', encoding='utf-8') as file:
            datos = json.load(file)
        
        # Buscar el evento en todas las categorías (como 'football')
        for categoria in datos.values():
            if event_id in categoria:
                return categoria[event_id]
                
        # Si no se encontró el evento
        return None
        
    except FileNotFoundError:
        print("Error: El archivo resultados.json no se encontró.")
        return None
    except json.JSONDecodeError:
        print("Error: El archivo resultados.json no tiene un formato JSON válido.")
        return None
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return None

async def notificar_combinada_finalizada(context, combinada):
    """Notificaciones premium con estilo mejorado y desglose de bono/balance"""
    try:
        usuario_id = str(combinada["usuario_id"])
        estado = combinada['estado']
        emoji_estado = "🎉" if estado == "✅ Ganada" else "💔"
        
        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro('usuarios', usuario_id)
        if not usuario_data:
            print(f"Usuario {usuario_id} no encontrado para notificación")
            return
            
        # Extraer nombre del usuario (ajusta el índice según tu estructura)
        nombre_usuario = usuario_data[1] if len(usuario_data) > 1 else f'Usuario {usuario_id}'  # Índice 1: nombre
        
        user_link = f'<a href="tg://user?id={usuario_id}">{nombre_usuario}</a>'
        
        # Calcular proporciones de pago
        monto = float(combinada['monto'])
        bono = float(combinada.get('bono', 0))
        balance = max(monto - bono, 0)
        proporcion_bono = (bono/monto)*100 if monto > 0 else 0
        proporcion_balance = 100 - proporcion_bono

        # --- Mensaje para GRUPO REGISTRO ---
        msg_grupo = f"""
<blockquote>🔮 RESULTADO COMBINADA 🔮</blockquote>

👤 <b>Usuario:</b> {user_link}
🆔 <b>ID:</b> <code>{usuario_id}</code>

<blockquote>📊 Detalles Financieros:</blockquote>
┌──────────────────────
├ 💰 <b>Monto Total:</b> <code>{monto:.2f} CUP</code>
├   ├ 🎁 <i>Bono:</i> <code>{bono:.2f} CUP</code> ({proporcion_bono:.0f}%)
├   └ 💳 <i>Balance:</i> <code>{balance:.2f} CUP</code> ({proporcion_balance:.0f}%)
├ 📈 <b>Cuota:</b> <code>{combinada['cuota']:.2f}</code>
└ 🏆 <b>Ganancia:</b> <code>{combinada.get('ganancia', 0):.2f} CUP</code>

<blockquote>🎯 Resultado Final:</blockquote>
{emoji_estado} <b>{estado.replace("✅ ", "").replace("❌ ", "").upper()}</b> {emoji_estado}

<blockquote>📋 Detalle de Selecciones:</blockquote>
"""

        # --- Mensaje para USUARIO ---
        msg_usuario = f"""
<blockquote>🎰 RESULTADO DE TU COMBINADA</blockquote>

{emoji_estado} <b>{'¡FELICIDADES, GANASTE!' if estado == '✅ Ganada' else 'LO SENTIMOS, PERDISTE'}</b> {emoji_estado}

<blockquote>💸 Inversión:</blockquote>
┌──────────────────────
├ 💰 <b>Total:</b> <code>{monto:.2f} CUP</code>
├   ├ 🎁 <i>Bono:</i> <code>{bono:.2f} CUP</code>
├   └ 💳 <i>Balance:</i> <code>{balance:.2f} CUP</code>
├ 📊 <b>Cuota:</b> <code>{combinada['cuota']:.2f}</code>
└ 🏦 <b>Ganancia:</b> <code>{combinada.get('ganancia', 0):.2f} CUP</code>

<blockquote>🔍 Tus Resultados:</blockquote>
"""

        # Construir detalles de selecciones
        for idx, sel in enumerate(combinada['selecciones'], 1):
            score_home = next((s['score'] for s in sel.get('scores', []) if s['name'] == sel.get('home_team')), '?')
            score_away = next((s['score'] for s in sel.get('scores', []) if s['name'] == sel.get('away_team')), '?')
            
            # Iconos y colores según estado
            icono_estado = {
                "✅ Ganada": "🟢",
                "❌ Perdida": "🔴",
                "🔄 Reembolsada": "🟠",
                "⌛Pendiente": "⚪"
            }.get(sel.get('estado'), "⚪")
            
            detalle = f"""
<pre>🔹 Selección {idx} {icono_estado}
├ ⚽ <b>Partido:</b> {sel['partido']} ({score_home}-{score_away})
├ 🏆 <b>Liga:</b> {sel.get('liga', '')}
├ 📌 <b>Mercado:</b> {sel['mercado']}
├ 🎯 <b>Selección:</b> {sel['favorito']} @{sel['cuota_individual']:.2f}
└ 💡 <b>Estado:</b> {sel.get('estado', 'Pendiente')}</pre>
"""
            msg_grupo += detalle
            msg_usuario += detalle

        # Mensaje final personalizado
        if estado == "✅ Ganada":
            msg_usuario += "\n<blockquote>💰 <b>El pago se ha acreditado a tu cuenta</b></blockquote>"
        else:
            msg_usuario += "\n<blockquote>💪 <b>Sigue intentándolo, ¡la próxima será!</b></blockquote>"

        # --- Envío de notificaciones ---
        # 1. Al grupo de registro
        await context.bot.send_message(
            chat_id=GROUP_REGISTRO,
            text=msg_grupo,
            parse_mode="HTML"
        )

        # 2. Al usuario (con manejo de errores)
        try:
            await context.bot.send_message(
                chat_id=usuario_id,
                text=msg_usuario,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error notificando a {usuario_id}: {str(e)}")

    except Exception as e:
        print(f"Error crítico en notificación: {str(e)}")
        import traceback
        traceback.print_exc()

async def enviar_resumen_evento(context, resumen):
    """Envía el resumen completo por evento con el cálculo correcto de ganancia neta"""
    # Cálculo CORRECTO de ganancia neta:
    # (Perdidos) - (Pagados - Montos de apuestas ganadoras)
    ganancia_neta_balance = resumen['total_perdido_balance'] - (resumen['total_pagado_balance'] - resumen['total_pagado_balance_montos'])
    ganancia_neta_bono = resumen['total_perdido_bono'] - (resumen['total_pagado_bono'] - resumen['total_pagado_bono_montos'])
    ganancia_neta_total = ganancia_neta_balance + ganancia_neta_bono

    # Símbolos para indicar ganancia/pérdida
    simbolo_balance = "✅" if ganancia_neta_balance >= 0 else "❌"
    simbolo_bono = "✅" if ganancia_neta_bono >= 0 else "❌"
    simbolo_total = "✅" if ganancia_neta_total >= 0 else "❌"

    mensaje = f"""
📊 <b>RESUMEN FINAL - {resumen['partido']}</b>

🏆 <b>Liga:</b> {resumen['liga']}
🔢 <b>Total Apuestas:</b> {len(resumen['detalles_ganadores']) + len(resumen['detalles_perdedores']) + len(resumen['detalles_reembolsos'])}

💸 <b>Movimientos:</b>
┌ 📈 <b>Pagado a ganadores:</b>
│  ├ Balance: <code>{resumen['total_pagado_balance']:.2f} CUP</code>
│  └ Bono: <code>{resumen['total_pagado_bono']:.2f} CUP</code>
│
├ 📉 <b>Perdidas de usuarios:</b>
│  ├ Balance: <code>{resumen['total_perdido_balance']:.2f} CUP</code>
│  └ Bono: <code>{resumen['total_perdido_bono']:.2f} CUP</code>
│
└ 📌 <b>Ganancia Neta Casa:</b>
   ├ Balance: {simbolo_balance} <code>{abs(ganancia_neta_balance):.2f} CUP</code>
   └ Bono: {simbolo_bono} <code>{abs(ganancia_neta_bono):.2f} CUP</code>
   └ Total: {simbolo_total} <code>{abs(ganancia_neta_total):.2f} CUP</code>

📝 <b>Detalles:</b>
"""

    # Detalles de ganadores, perdedores y reembolsos
    if resumen['detalles_ganadores']:
        mensaje += "\n🏅 <b>GANADORES:</b>\n" + "\n".join(resumen['detalles_ganadores'])
    if resumen['detalles_perdedores']:
        mensaje += "\n\n💸 <b>PERDEDORES:</b>\n" + "\n".join(resumen['detalles_perdedores'])
    if resumen['detalles_reembolsos']:
        mensaje += "\n\n🔄 <b>REEMBOLSOS:</b>\n" + "\n".join(resumen['detalles_reembolsos'])

    # División del mensaje si es muy largo
    partes = [mensaje[i:i+4096] for i in range(0, len(mensaje), 4096)]
    
    for parte in partes:
        try:
            await context.bot.send_message(chat_id=GROUP_REGISTRO, text=parte, parse_mode="HTML")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error al enviar resumen: {str(e)}")


        
async def reportar_error(context, error_msg, apuesta=None):
    """Función para reportar errores de manera consistente"""
    try:
        mensaje = f"⚠️ ERROR CRÍTICO: {error_msg}"
        if apuesta:
            mensaje += f"\nApuesta ID: {apuesta.get('event_id', 'Desconocido')}"
            mensaje += f"\nUsuario: {apuesta.get('usuario_id', 'Desconocido')}"
        
        
        await context.bot.send_message(
            chat_id=7031172659,
            text=mensaje,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Error al reportar error: {str(e)}")
            
                                    


async def decidir_apuesta_ganada(context, event_id):
    """Procesa apuestas PREPARTIDO en estado '🔚 Finalizado' y COMBINADAS pendientes usando la base de datos"""
    try:
        print(f"[decidir_apuesta_ganada] Procesando evento: {event_id}")
        
        # Obtener todas las apuestas de la base de datos
        apuestas = obtener_todas_las_apuestas()
        if not isinstance(apuestas, list):
            await reportar_error(context, "Apuestas no es una lista")
            return

        combinadas_completadas = []
        eventos_procesados = set()
        resumen_por_evento = {}

        for apuesta in apuestas:
            try:
                # --- LÓGICA PARA PREPARTIDO Y LIVE ---
                if (
                    apuesta.get("betting") in ["PREPARTIDO", "LIVE"]
                    and apuesta.get('event_id') == event_id
                    and apuesta.get('estado') == "🔚 Finalizado"
                    and apuesta.get('scores')
                ):
                    resultado = decidir_resultado_apuesta(
                        tipo_apuesta=apuesta['tipo_apuesta'],
                        scores=apuesta['scores'],
                        favorito=apuesta['favorito'],
                        home_team=apuesta['home_team'],
                        away_team=apuesta['away_team'],
                        sport_key=apuesta['sport_key'],
                        event_id=apuesta['event_id']
                    )

                    if resultado == "Ganadora":
                        apuesta['estado'] = "✅ Ganada"
                    elif resultado == "Perdedora":
                        apuesta['estado'] = "❌ Perdida"
                    else:
                        apuesta['estado'] = "🔄 Reembolso"

                    # Cambio aquí: eliminar user_data del llamado
                    await procesar_prepartido(context, apuesta, resultado, resumen_por_evento)
                    eventos_procesados.add(apuesta['event_id'])
                    
                    # Actualizar la apuesta en la base de datos
                    actualizar_apuesta_en_db(apuesta)
                    continue

                # --- LÓGICA PARA COMBINADAS ---
                elif apuesta.get('betting') == 'COMBINADA' and apuesta.get('estado') == "⌛Pendiente":

                    selecciones_actualizadas = False
                    todas_completas = all(
                        sel.get('estado') in ["✅ Ganada", "❌ Perdida", "🔄 Reembolsada"]
                        for sel in apuesta.get('selecciones', [])
                    )
                    alguna_perdida = any(
                        sel.get('estado') == "❌ Perdida"
                        for sel in apuesta.get('selecciones', [])
                    )

                    for seleccion in apuesta.get('selecciones', []):
                        if (
                            seleccion.get('event_id') == event_id
                            and seleccion.get('estado') == "🔚 Finalizado"
                            and seleccion.get('scores')
                        ):
                            resultado_seleccion = decidir_resultado_apuesta(
                                tipo_apuesta=seleccion['mercado'],
                                scores=seleccion['scores'],
                                favorito=seleccion['favorito'],
                                home_team=seleccion['home_team'],
                                away_team=seleccion['away_team'],
                                sport_key=seleccion['sport_key'],
                                event_id=seleccion['event_id']
                            )

                            if resultado_seleccion == "Ganadora":
                                seleccion['estado'] = "✅ Ganada"
                            elif resultado_seleccion == "Perdedora":
                                seleccion['estado'] = "❌ Perdida"
                                alguna_perdida = True
                            else:
                                seleccion['estado'] = "🔄 Reembolsada"

                            selecciones_actualizadas = True

                    todas_completas = all(
                        sel.get('estado') in ["✅ Ganada", "❌ Perdida", "🔄 Reembolsada"]
                        for sel in apuesta.get('selecciones', [])
                    )
                    alguna_perdida = any(
                        sel.get('estado') == "❌ Perdida"
                        for sel in apuesta.get('selecciones', [])
                    )
                    algun_reembolso = any(
                        sel.get('estado') == "🔄 Reembolsada"
                        for sel in apuesta.get('selecciones', [])
                    )

                    if todas_completas:
                        if alguna_perdida:
                            apuesta['estado'] = "❌ Perdida"
                        elif algun_reembolso:
                            apuesta['estado'] = "🔄 Reembolso"
                        else:
                            apuesta['estado'] = "✅ Ganada"

                        if apuesta['estado'] == "✅ Ganada":
                            # Cambio aquí: eliminar user_data del llamado
                            
                            actualizar_apuesta_en_db(apuesta)
                            await procesar_combinada_ganadora(context, apuesta)
                        combinadas_completadas.append(apuesta)

                    elif selecciones_actualizadas:
                        # Actualizar solo si hubo cambios en las selecciones
                        actualizar_apuesta_en_db(apuesta)

            except Exception as e:
                await reportar_error(context, f"Error procesando apuesta {apuesta.get('id')}: {str(e)}")
                continue

        # Guardar cambios en las apuestas
        for event_id_procesado, resumen in resumen_por_evento.items():
            await enviar_resumen_evento(context, resumen)

        for combinada in combinadas_completadas:
            await notificar_combinada_finalizada(context, combinada)

        print(f"[decidir_apuesta_ganada] Procesamiento completado para evento: {event_id}")

    except Exception as e:
        await reportar_error(context, f"ERROR en decidir_apuesta_ganada: {str(e)}")

def obtener_datos_usuario(user_id):
    """
    Obtiene los datos del usuario y su bono de apuesta usando la estructura correcta de la base de datos
    """
    try:
        # Obtener datos del usuario - usando los nombres exactos de las columnas
        usuario_data = obtener_registro("usuarios", user_id, "balance, Nombre, lider")
        if not usuario_data:
            print(f"Usuario {user_id} no encontrado en la tabla 'usuarios'")
            return None, None
        
        # Desempaquetar la tupla (balance, Nombre, lider)
        balance_actual, nombre_usuario, lider_id = usuario_data
        
        # Crear diccionario con los datos del usuario
        usuario_dict = {
            'id': user_id,
            'nombre': nombre_usuario,
            'balance': balance_actual,
            'lider': lider_id
        }
        
        # Obtener datos del bono - usando los nombres exactos de las columnas
        bono_data = obtener_registro("bono_apuesta", user_id, "bono, rollover_requerido, rollover_actual, bono_retirable")
        bono_dict = None
        
        if bono_data:
            # Desempaquetar la tupla del bono
            bono, rollover_requerido, rollover_actual, bono_retirable = bono_data
            bono_dict = {
                'id': user_id,
                'bono': bono,
                'rollover_requerido': rollover_requerido,
                'rollover_actual': rollover_actual,
                'bono_retirable': bono_retirable
            }
        else:
            print(f"Usuario {user_id} no tiene registro en 'bono_apuesta'")
            # Crear un bono por defecto si no existe
            bono_dict = {
                'id': user_id,
                'bono': 0,
                'rollover_requerido': 0,
                'rollover_actual': 0,
                'bono_retirable': 0
            }
        
        return usuario_dict, bono_dict
        
    except Exception as e:
        print(f"Error al obtener datos del usuario {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None, None
        
async def procesar_prepartido(context, apuesta, resultado, resumen_por_evento):
    """Procesa apuestas PREPARTIDO y acumula datos para el resumen FINAL"""
    try:
        event_id = apuesta['event_id']
        user_id = apuesta['usuario_id']
        monto = float(apuesta['monto'])
        ganancia = float(apuesta.get('ganancia', 0))
        bono_usado = float(apuesta.get('bono', 0))
        balance_usado = max(monto - bono_usado, 0)
        ganancia_neta_usuario = ganancia - monto

        # Obtener datos del usuario y bono
        usuario_data, bono_data = obtener_datos_usuario(user_id)
        if not usuario_data:
            print(f"Usuario {user_id} no encontrado")
            return

        # Inicializar resumen si no existe
        if event_id not in resumen_por_evento:
            resumen_por_evento[event_id] = {
                "liga": apuesta.get('liga', 'Sin liga'),
                "partido": f"{apuesta['home_team']} vs {apuesta['away_team']}",
                "total_pagado_balance": 0,
                "total_pagado_bono": 0,
                "total_pagado_balance_montos": 0,
                "total_pagado_bono_montos": 0,
                "total_perdido_balance": 0,
                "total_perdido_bono": 0,
                "detalles_ganadores": [],
                "detalles_perdedores": [],
                "detalles_reembolsos": []
            }

        resumen = resumen_por_evento[event_id]
        usuario = usuario_data.get('nombre', 'Usuario desconocido')

        # LÓGICA DE GANADORAS
        if resultado == "Ganadora":
            proporcion_balance = balance_usado / monto if monto > 0 else 0
            proporcion_bono = bono_usado / monto if monto > 0 else 0
            
            ganancia_balance = ganancia * proporcion_balance
            ganancia_bono = ganancia * proporcion_bono

            resumen['total_pagado_balance_montos'] += balance_usado
            resumen['total_pagado_bono_montos'] += bono_usado

            # Actualizar balance del usuario - usando nombres de columna exactos
            nuevo_balance = usuario_data.get('balance', 0) + ganancia_balance
            actualizar_registro('usuarios', user_id, {'balance': nuevo_balance})
            
            # Actualizar bono si existe - usando nombres de columna exactos
            if bono_data:
                nuevo_bono = bono_data.get('bono', 0) + bono_usado
                nuevo_rollover = bono_data.get('rollover_actual', 0) + bono_usado
                campos_bono = {
                    'bono': nuevo_bono, 
                    'rollover_actual': nuevo_rollover
                }
                
                if (ganancia_bono - bono_usado) > 0:
                    bono_retirable = bono_data.get('bono_retirable', 0) + (ganancia_bono - bono_usado)
                    campos_bono['bono_retirable'] = bono_retirable
                
                actualizar_registro('bono_apuesta', user_id, campos_bono)

            resumen['total_pagado_balance'] += ganancia_balance
            resumen['total_pagado_bono'] += ganancia_bono
            resumen['detalles_ganadores'].append(f"👤 {usuario} | ✅ +{ganancia_neta_usuario:.2f} CUP")

        # LÓGICA DE PERDEDORAS
        elif resultado == "Perdedora":
            resumen['total_perdido_balance'] += balance_usado
            resumen['total_perdido_bono'] += bono_usado
            resumen['detalles_perdedores'].append(f"👤 {usuario} | ❌ -{monto:.2f} CUP")

        # LÓGICA DE REEMBOLSOS
        elif resultado == "Reembolso":
            # Devolver el balance usado
            nuevo_balance = usuario_data.get('balance', 0) + balance_usado
            actualizar_registro('usuarios', user_id, {'balance': nuevo_balance})
            
            # Devolver el bono usado si existe
            if bono_data and bono_usado > 0:
                nuevo_bono = bono_data.get('bono', 0) + bono_usado
                actualizar_registro('bono_apuesta', user_id, {'bono': nuevo_bono})
                
            resumen['detalles_reembolsos'].append(f"👤 {usuario} | 🔄 {monto:.2f} CUP")

        # Notificaciones individuales AL USUARIO
        await notificar_usuario(context, user_id, apuesta, resultado, usuario_data)
        
        # Notificación al grupo de registro
        await enviar_notificacion_individual(context, apuesta, resultado, usuario_data)
        await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Error en procesar_prepartido: {str(e)}")
        import traceback
        traceback.print_exc()
        
        
                      
async def procesar_combinada_ganadora(context, combinada):
    """Procesa pagos de combinadas ganadoras/reembolsadas"""
    try:
        user_id = str(combinada["usuario_id"])
        monto = float(combinada["monto"])
        estado = combinada['estado']
        
        # Obtener datos del usuario y bono
        usuario_data, bono_data = obtener_datos_usuario(user_id)
        if not usuario_data:
            print(f"Usuario {user_id} no encontrado")
            return

        # Caso 1: Reembolso (devolución completa)
        if estado == "🔄 Reembolso":
            bono_usado = float(combinada.get("bono", 0))
            
            # Devolver monto a balance (parte no bono)
            nuevo_balance = usuario_data.get('balance', 0) + (monto - bono_usado)
            actualizar_registro('usuarios', user_id, {"balance": nuevo_balance})
            
            # Devolver bono si existió
            if bono_usado > 0 and bono_data:
                nuevo_bono = bono_data.get('bono', 0) + bono_usado
                actualizar_registro('Bono_apuesta', user_id, {"bono": nuevo_bono})
            
            return

        # Caso 2: Apuesta ganadora - CONFÍA en el estado ya determinado
        if estado == "✅ Ganada":
            ganancia = float(combinada["ganancia"])
            bono_usado = float(combinada.get("bono", 0))
            
            # ✅ ELIMINAR ESTA VALIDACIÓN REDUNDANTE ✅
            # if any(sel.get('estado') != "✅ Ganada" for sel in combinada.get('selecciones', [])):
            #    return

            # Calcular proporciones
            proporcion_balance = (monto - bono_usado) / monto if monto > 0 else 0
            proporcion_bono = bono_usado / monto if monto > 0 else 0
            
            # Distribuir ganancia
            ganancia_balance = ganancia * proporcion_balance
            ganancia_bono = ganancia * proporcion_bono

            # Actualizar saldos
            nuevo_balance = usuario_data.get('balance', 0) + ganancia_balance
            actualizar_registro('usuarios', user_id, {"balance": nuevo_balance})
            
            if bono_data:
                nuevo_bono = bono_data.get('bono', 0) + ganancia_bono
                campos_actualizar = {"bono": nuevo_bono}
                # Calcular bono retirable (ganancia neta)
                ganancia_neta_bono = ganancia_bono - bono_usado
                if ganancia_neta_bono > 0:
                    bono_retirable = bono_data.get('bono_retirable', 0) + ganancia_neta_bono
                    campos_actualizar["bono_retirable"] = bono_retirable
                actualizar_registro('Bono_apuesta', user_id, campos_actualizar)

            print(f"✅ Combinada {combinada.get('id_ticket', 'N/A')} pagada al usuario {user_id}")

    except Exception as e:
        print(f"Error en procesar_combinada_ganadora: {str(e)}")
        import traceback
        traceback.print_exc()  
        
async def notificar_usuario(context, user_id, apuesta, resultado, usuario_data):
    """
    Notifica al usuario sobre el resultado de su apuesta con diseño mejorado.
    Versión SIN botón de apuesta original y estructura visual clara.
    """
    # Configurar botón SOLO de resumen si es fútbol
    keyboard = []
    
    if apuesta.get('deporte', '').startswith('FUTBOL') or apuesta.get('sport_key') == 'soccer':  
        keyboard.append([InlineKeyboardButton("📊 Ver resumen del partido", callback_data=f"resumen_{apuesta['event_id']}")])  
  
    # Construir encabezado según resultado  
    emoji = "✅" if resultado == "Ganadora" else "❌" if resultado == "Perdedora" else "🔄"  
    mensaje = f"""

<pre>{emoji} {'APUESTA GANADA' if resultado == 'Ganadora' else 'APUESTA PERDIDA' if resultado == 'Perdedora' else 'REEMBOLSO'} {emoji} </pre>  
┌ 🏆 <b>Evento:</b> {apuesta.get('liga', 'Sin liga')} - {apuesta['partido']}
├ 🎯 <b>Tipo:</b> {apuesta['tipo_apuesta']}
├ ⚖️ <b>Favorito:</b> {apuesta['favorito']}
└ 💹 <b>Cuota:</b> <code>{apuesta.get('cuota', 0):.2f}</code>
"""

    # Detalles financieros  
    bono_usado = float(apuesta.get('bono', 0))  
    balance_usado = float(apuesta['monto']) - bono_usado  
  
    mensaje += f"""

<b>💰 MONTO APOSTADO:</b> <code>{float(apuesta['monto']):.2f} CUP</code>
┌ 🎁 <b>Bono:</b> <code>{bono_usado:.2f} CUP</code>
└ 💳 <b>Balance:</b> <code>{balance_usado:.2f} CUP</code>
"""

    # Sección de resultados  
    if resultado == "Ganadora":  
        mensaje += f"""

<b>🎉 GANANCIA:</b> <code>{float(apuesta.get('ganancia', 0)):.2f} CUP</code>
"""
    elif resultado == "Reembolso":
        mensaje += f"""
<b>🔄 REEMBOLSADO:</b> <code>{float(apuesta['monto']):.2f} CUP</code>
"""

    # Información de saldo actualizado  
    if bono_usado > 0 and 'bono' in usuario_data:  
        mensaje += f"""

<b>🎁 ESTADO DE BONO:</b>
┌ 📊 <b>Retirable:</b> <code>{usuario_data.get('bono_retirable', 0):.2f} CUP</code>
└ 🔄 <b>Rollover:</b> <code>{usuario_data.get('rollover_actual', 0):.2f} CUP</code>
"""
    else:
        nuevo_balance = usuario_data.get('balance', 0)
        mensaje += f"""
<b>💳 BALANCE ACTUAL:</b> <code>{nuevo_balance:.2f} CUP</code>
"""

    # Mensaje final según resultado  
    if resultado == "Ganadora":  
        mensaje += "\n<i>¡Felicidades! Sigue apostando con responsabilidad.</i> 🚀"  
    elif resultado == "Perdedora":  
        mensaje += "\n<i>La próxima vez será mejor. ¡Sigue intentándolo!</i> 💪"  
    else:  
        mensaje += "\n<i>El monto ha sido reembolsado a tu cuenta.</i> 🔄"  

    # Envío con reintentos  
    max_intentos = 2  
    for intento in range(max_intentos):  
        try:  
            await context.bot.send_message(  
                chat_id=user_id,  
                text=mensaje,  
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,  
                parse_mode="HTML"  
            )  
            break  
        except Exception as e:  
            print(f"⚠️ Error notificando a {user_id} (Intento {intento+1}): {str(e)}")  
            if intento < max_intentos - 1:  
                await asyncio.sleep(5)  
            else:  
                await reportar_error(context, f"Error notificando a {user_id}: {str(e)}")
                
async def enviar_notificacion_individual(context, apuesta, resultado, usuario_data):
    """Notificación original para el grupo"""
    # Obtener datos del usuario directamente desde la base de datos
    usuario_registro = obtener_registro('usuarios', apuesta["usuario_id"])
    
    # Extraer el nombre de la tupla (asumiendo que la columna 'Nombre' está en una posición específica)
    # Necesitamos saber la estructura de la tupla devuelta
    nombre_usuario = 'Usuario'
    if usuario_registro:
        # Suponiendo que la estructura es: (id, Nombre, ...otros campos)
        # Ajusta el índice según la posición real de la columna 'Nombre'
        if len(usuario_registro) > 1:
            nombre_usuario = usuario_registro[1]  # Segundo elemento (índice 1)
    
    # Crear teclado inicial con el botón de ver apuesta
    keyboard = [[InlineKeyboardButton("📎 Ver Apuesta", url=apuesta.get('mensaje_canal_url', '#'))]]
    
    # Añadir botón de resumen solo si es fútbol
    if apuesta.get('deporte', '').startswith('FUTBOL') or apuesta.get('sport_key') == 'soccer':
        keyboard.append([InlineKeyboardButton("📊 Ver resumen del partido", callback_data=f"resumen_{apuesta['event_id']}")])
    
    mensaje = f"""
{'✅' if resultado == 'Ganadora' else '❌' if resultado == 'Perdedora' else '🔄'} <b>{resultado.upper()}</b>

┌ 🆔 <b>ID:</b> <code>{apuesta['usuario_id']}</code>
├ 👤 <b>Usuario:</b> {nombre_usuario}
├ 🏆 <b>Evento:</b> {apuesta['partido']}
├ ⚖️ <b>Favorito:</b> {apuesta['favorito']}
└ 💰 <b>Monto:</b> <code>{apuesta['monto']:.2f} CUP</code>
"""
    if resultado == "Ganadora":
        mensaje += f"\n📈 <b>Ganancia:</b> <code>{apuesta['ganancia']:.2f} CUP</code>"
    elif resultado == "Reembolso":
        mensaje += f"\n🔄 <b>Reembolsado:</b> <code>{apuesta['monto']:.2f} CUP</code>"

    await context.bot.send_message(
        chat_id=GROUP_REGISTRO,
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    await asyncio.sleep(3)
                
#resoonder al botón para el resumen del partido resultado ect.
async def handle_resumen_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    # Extraer el event_id del callback_data (formato "resumen_12345")
    event_id = query.data.split('_')[1]
    
    # Generar el resumen usando la función que creamos antes
    resumen = generar_resumen_partido(event_id)
    
    # Enviar el resumen como mensaje
    await query.message.reply_text(resumen, parse_mode="HTML")

         
                
def generar_resumen_partido(event_id):
    datos_evento = obtener_datos_evento(event_id)
    
    if not datos_evento:
        return "No se encontraron datos para este partido."
    
    partido = datos_evento
    nombre_partido = partido["nombre_partido"]
    estado = partido["datos"]["estado"]
    marcador = partido["datos"]["marcador"]
    periodos = partido["datos"]["periodos"]
    eventos = partido["datos"]["eventos"]
    estadisticas = partido["datos"]["estadisticas"]
    
    # Traducción de estados del partido
    estados_traduccion = {
        "FT": "Finalizado",
        "AET": "Final (Prórroga)",
        "PEN": "Final (Penales)",
        "HT": "Medio Tiempo",
        "PST": "Aplazado",
        "CANC": "Cancelado",
        "NS": "No Empezado"
    }
    estado_mostrar = estados_traduccion.get(estado, estado)
    
    # Emojis para equipos y eventos
    emojis = {
        "local": "🏠",  # Casa para equipo local
        "visitante": "✈️",  # Avión para equipo visitante
        "goal": "⚽",
        "card": "🟨",
        "yellow card": "🟨",
        "red card": "🟥",
        "penalty": "🧿",  # Nuevo emoji para penal
        "own_goal": "🤦",
        "substitution": "🔄"
    }
    
    # Construir el encabezado del partido
    resumen = f"<b>📌 PARTIDO: {nombre_partido}</b>\n"
    resumen += f"🏟 <b>Estado:</b> {estado_mostrar}\n"
    resumen += f"📊 <b>Resultado Final:</b> <code>{marcador['local']} | {marcador['visitante']}</code>\n\n"
    
    # Resultado por periodos
    resumen += "<b>⏳ RESULTADO POR TIEMPOS:</b>\n"
    for periodo, resultado in periodos.items():
        periodo_nombre = {
            "1T": "1° Tiempo",
            "2T": "2° Tiempo",
            "Prorroga": "Prórroga",
            "1H": "1° Tiempo",
            "2H": "2° Tiempo"
        }.get(periodo, periodo)
        resumen += f"• {periodo_nombre}: <code>{resultado['local']} | {resultado['visitante']}</code>\n"
    resumen += "\n"
    
    # Eventos del partido (goles y tarjetas)
    resumen += "<b>🗒 CRONOLOGÍA DEL PARTIDO:</b>\n"
    for evento in sorted(eventos, key=lambda x: x["minuto"]):
        minuto = evento["minuto"]
        equipo_emoji = emojis[evento["equipo"]]
        jugador = evento["jugador"]
        
        if evento["tipo"] == "goal":
            tipo_gol = evento.get("tipo_gol", "gol normal")
            if tipo_gol == "penalty":
                emoji_evento = emojis["penalty"]
                desc_gol = "(de penal)"
            elif tipo_gol == "own_goal":
                emoji_evento = emojis["own_goal"]
                desc_gol = "(gol en propia)"
            else:
                emoji_evento = emojis["goal"]
                desc_gol = ""
                
            resumen += f"<code>{minuto}′</code> {emoji_evento} {equipo_emoji} {jugador} {desc_gol}\n"
            
        elif evento["tipo"] == "card":
            tipo_tarjeta = evento.get("tipo_tarjeta", "yellow card")
            emoji_evento = emojis[tipo_tarjeta]
            tipo_txt = "amarilla" if tipo_tarjeta == "yellow card" else "roja"
            resumen += f"<code>{minuto}′</code> {emoji_evento} {equipo_emoji} {jugador} (tarjeta {tipo_txt})\n"
    
    resumen += "\n"
    
    # Estadísticas principales (versión modificada)
    resumen += "<b>📊 ESTADÍSTICAS DEL PARTIDO:</b>\n"
    stats_principales = [
        ("Posesión", "Ball Possession"),
        ("Tiros al arco", "Shots on Goal"),
        ("Tiros desviados", "Shots off Goal"),
        ("Tiros totales", "Total Shots"),
        ("Tiros bloqueados", "Blocked Shots"),
        ("Faltas", "Fouls"),
        ("Corners", "Corner Kicks"),
        ("Offsides", "Offsides"),
        ("Tarjetas amarillas", "Yellow Cards"),
        ("Precisión pases", "Passes %"),
        ("xG (Expected Goals)", "expected_goals")
    ]
    
    for nombre, stat in stats_principales:
        if stat in estadisticas:
            local = estadisticas[stat]["local"]
            visitante = estadisticas[stat]["visitante"]
            resumen += f"• <b>{nombre}:</b> <code>{local}</code> | <code>{visitante}</code>\n"
    
    # Pie de mensaje
    resumen += f"\n⏰ <i>Última actualización:</i> {partido['ultima_actualizacion']}"
    
    return resumen
                


async def buscar_apuestas_finalizadas(context: CallbackContext):
    """Función que busca apuestas finalizadas con procesamiento diferenciado por deporte usando base de datos"""
    print("🔍 Ejecutando buscar_apuestas_finalizadas...")

    try:
        # Obtener apuestas desde la base de datos
        apuestas = obtener_todas_las_apuestas()
        
    except Exception as e:
        print(f"❌ Error al cargar apuestas desde la base de datos: {str(e)}")
        return

    zona_horaria_cuba = pytz.timezone('America/Havana')
    ahora = datetime.now(zona_horaria_cuba)

    # Separamos los eventos desde el principio
    eventos_futbol = []
    eventos_otros_deportes = []
    eventos_procesados = set()

    # Procesar PREPARTIDO y COMBINADAS (manteniendo lógica original)
    for apuesta in apuestas:
        if apuesta.get('betting') in ['PREPARTIDO', 'LIVE'] and apuesta.get('estado') in ["⌛Pendiente", "🔚 Finalizado", None]:
            try:
                deporte = apuesta.get('deporte', 'FUTBOL⚽')
                if isinstance(deporte, list):
                    deporte = deporte[0]

                duracion = TIEMPOS_DURACION.get(deporte, 107)
                fecha_inicio = datetime.strptime(apuesta['fecha_inicio'], "%d/%m/%Y %H:%M:%S")
                fecha_inicio = zona_horaria_cuba.localize(fecha_inicio)
                fecha_finalizacion = fecha_inicio + timedelta(minutes=duracion)

                if ahora >= fecha_finalizacion and apuesta['event_id'] not in eventos_procesados:
                    evento = {
                        'event_id': apuesta['event_id'],
                        'sport_key': apuesta['sport_key'],
                        'deporte': deporte,
                        'is_combinada': False,
                        'apuesta_data': apuesta
                    }
                    
                    if deporte == 'FUTBOL⚽' or str(apuesta['event_id']).isdigit():
                        eventos_futbol.append(evento)
                    else:
                        eventos_otros_deportes.append(evento)
                    
                    eventos_procesados.add(apuesta['event_id'])
                    
                    # Actualizar estado a "🔚 Finalizado" en la base de datos
                    actualizar_apuesta_en_db({
                        'id': apuesta['id'],
                        'estado': '🔚 Finalizado',
                        'last_update': ahora.strftime('%d/%m/%Y %H:%M:%S')
                    })
                    
            except Exception as e:
                print(f"❌ Error procesando PREPARTIDO: {str(e)}")

    # Procesamiento separado
    print(f"\n📊 Eventos a procesar:")
    print(f"⚽ Fútbol: {len(eventos_futbol)} eventos")
    print(f"🏀 Otros deportes: {len(eventos_otros_deportes)} eventos")

    # 1. Procesar eventos de fútbol (flujo original completo)
    if eventos_futbol:
        print("\n🔵 Procesando eventos de FÚTBOL...")
        event_ids_futbol = []
        
        for evento in eventos_futbol:
            nombre_partido = evento['apuesta_data']['partido']
            fecha_partido = evento['apuesta_data']['fecha_inicio']
            
            event_id_procesado = await get_match_data(
                event_id=evento['event_id'],
                nombre_partido=nombre_partido,
                fecha_partido=fecha_partido,
                context=context,
                deporte='football'  # Siempre football para la API
            )
            
            if event_id_procesado:
                event_ids_futbol.append(event_id_procesado)

        if event_ids_futbol:
            await obtener_resultados_eventos(
                [{'event_id': eid, 'sport_key': 'football'} for eid in event_ids_futbol],
                context
            )

    # 2. Procesar otros deportes (flujo directo a theodds)
    if eventos_otros_deportes:
        print("\n🟠 Procesando otros deportes...")
        eventos_procesados_otros = [{'event_id': evento['event_id'], 'sport_key': evento['sport_key']} for evento in eventos_otros_deportes]
        
        await obtener_resultados_theodds(
            eventos_procesados_otros,
            context
        )

    print("\n✅ APUESTAS FINALIZADAS PROCESO COMPLETADO✅")
# Configuración de deportes y sus estructuras de tiempo
SPORT_CONFIG = {
    'football': {
        'periods': ['1T', '2T', 'Prorroga'],
        'default_duration': 107,
        'incident_types': ['goal', 'card', 'substitution']
    },
    'basketball': {
        'periods': ['1Q', '2Q', '3Q', '4Q', 'OT'],
        'default_duration': 48,
        'incident_types': ['point', 'foul', 'timeout']
    },
    'tennis': {
        'periods': ['Set 1', 'Set 2', 'Set 3', 'Set 4', 'Set 5'],
        'default_duration': None,
        'incident_types': ['game', 'point', 'break']
    },
    'baseball': {
        'periods': ['Inning 1', 'Inning 2', 'Inning 3', 'Inning 4', 'Inning 5', 
                   'Inning 6', 'Inning 7', 'Inning 8', 'Inning 9'],
        'default_duration': None,
        'incident_types': ['run', 'hit', 'strikeout']
    },
    'boxing': {
        'periods': ['Round 1', 'Round 2', 'Round 3', 'Round 4', 'Round 5',
                   'Round 6', 'Round 7', 'Round 8', 'Round 9', 'Round 10', 'Round 11', 'Round 12'],
        'default_duration': None,
        'incident_types': ['knockdown', 'foul', 'timeout']
    }
}

URL_RESULTADOS = "https://api.the-odds-api.com/v4/sports/{sport_key}/scores"
async def obtener_resultados_theodds(eventos_finalizados, context):
    global api_index

    if api_index >= len(API_KEYS):
        print("❌ No hay claves API disponibles.")
        return "❌ No hay claves API disponibles."

    # Deduplicar eventos por event_id y sport_key
    unique_events = {(evento['event_id'], evento['sport_key']) for evento in eventos_finalizados if 'event_id' in evento and 'sport_key' in evento}
    print(f"📊 Eventos finalizados a buscar: {len(unique_events)} eventos únicos.")

    if not unique_events:
        print("ℹ️ No hay eventos únicos para buscar.")
        return "ℹ️ No hay eventos únicos para buscar."

    try:
        async with aiohttp.ClientSession() as session:
            # Obtener apuestas desde la base de datos
            apuestas = obtener_todas_las_apuestas()
            print("📂 Apuestas cargadas correctamente desde la base de datos.")

            updates_made = False
            eventos_procesados = set()
            eventos_actualizados = []

            for event_id, sport_key in unique_events:
                if event_id in eventos_procesados:
                    print(f"ℹ️ Evento {event_id} ya procesado. Saltando...")
                    continue

                # Bucle para reintentar con diferentes claves API
                success = False
                while not success and api_index < len(API_KEYS):
                    api_key = await obtener_api()
                    params = {
                        "apiKey": api_key,
                        "dateFormat": "iso",
                        "daysFrom": 2,
                        "eventIds": event_id
                    }

                    url = URL_RESULTADOS.format(sport_key=sport_key)
                    print(f"🔍 Buscando evento {event_id} con clave API {api_key}...")

                    try:
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                eventos_api = await response.json()
                                print(f"✅ Respuesta de la API para el evento {event_id}: {eventos_api}")

                                remaining = int(response.headers.get('x-requests-remaining', '0'))
                                used = response.headers.get('x-requests-used', 'N/A')
                                print(f"🔑 Créditos restantes: {remaining}, usados: {used}")

                                if remaining == 0:
                                    print(f"⚠️ Clave API {api_key} agotada. Cambiando a la siguiente...")
                                    api_index += 1
                                    continue

                                evento_encontrado = next((e for e in eventos_api if e['id'] == event_id), None)
                                if not evento_encontrado:
                                    print(f"❌ Evento {event_id} no encontrado en la API.")
                                    try:
                                        await resumen_evento_no_encontrado(context, event_id)
                                    except Exception as e:
                                        print(f"⚠️ Error al notificar evento no encontrado: {str(e)}")
                                    await asyncio.sleep(5)
                                    success = True
                                    break

                                if not evento_encontrado.get('completed', False):
                                    print(f"⚠️ Evento {event_id} aún no finalizado.")
                                    success = True
                                    break

                                # Actualizar apuestas en la base de datos
                                for apuesta in apuestas:
                                    # Para apuestas PREPARTIDO
                                    if apuesta.get("betting") in ["PREPARTIDO", "LIVE"] and apuesta.get("event_id") == event_id:
                                        # Actualizar en la base de datos
                                        campos_actualizados = {
                                            'id': apuesta['id'],
                                            'completed': True,
                                            'scores_json': json.dumps(evento_encontrado.get('scores', [])),
                                            'home_team': evento_encontrado.get('home_team', ''),
                                            'away_team': evento_encontrado.get('away_team', ''),
                                            'last_update': evento_encontrado.get('last_update', ''),
                                            'estado': "🔚 Finalizado"
                                        }
                                        
                                        if actualizar_apuesta_en_db(campos_actualizados):
                                            updates_made = True
                                            eventos_procesados.add(event_id)
                                            eventos_actualizados.append(event_id)
                                            print(f"✅ Apuesta {apuesta['id']} actualizada en la base de datos")
                                    
                                    # Para selecciones de COMBINADAS
                                    if apuesta.get('betting') == 'COMBINADA':
                                        selecciones_actualizadas = False
                                        for seleccion in apuesta.get('selecciones', []):
                                            if seleccion.get('event_id') == event_id:
                                                print(f"📝 Actualizando selección de COMBINADA {event_id}...")
                                                
                                                # Actualizar la selección
                                                seleccion.update({
                                                    'completed': True,
                                                    'scores': evento_encontrado.get('scores', []),
                                                    'home_team': evento_encontrado.get('home_team', ''),
                                                    'away_team': evento_encontrado.get('away_team', ''),
                                                    'last_update': evento_encontrado.get('last_update', ''),
                                                    'estado': "🔚 Finalizado"
                                                })
                                                
                                                selecciones_actualizadas = True
                                        
                                        # Si se actualizaron selecciones, guardar la apuesta combinada completa
                                        if selecciones_actualizadas:
                                            campos_actualizados = {
                                                'id': apuesta['id'],
                                                'selecciones_json': json.dumps(apuesta.get('selecciones', [])),
                                                'last_update': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                                            }
                                            
                                            if actualizar_apuesta_en_db(campos_actualizados):
                                                updates_made = True
                                                eventos_procesados.add(event_id)
                                                eventos_actualizados.append(event_id)
                                                print(f"✅ Apuesta combinada {apuesta['id']} actualizada en la base de datos")

                                success = True

                            elif response.status == 401:
                                print(f"⚠️ Clave API {api_key} agotada. Cambiando a la siguiente...")
                                api_index += 1
                                continue

                            else:
                                print(f"❌ Error {response.status} al buscar evento {event_id}: {await response.text()}")
                                success = True
                                break

                    except aiohttp.ClientError as e:
                        print(f"⚠️ Error de conexión al buscar evento {event_id}: {str(e)}")
                        success = True
                        break

            # Procesar eventos actualizados
            if updates_made:
                print(f"📤 Procesando eventos actualizados: {list(set(eventos_actualizados))}")
                for event_id in set(eventos_actualizados):
                    await decidir_apuesta_ganada(context, event_id)
                
                return "✅ Resultados actualizados correctamente."
            else:
                print("ℹ️ No hubo eventos nuevos para actualizar.")
                return "ℹ️ No hubo eventos nuevos para actualizar."

    except Exception as e:
        print(f"⚠️ Error en obtener_resultados_theodds: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"⚠️ Error: {str(e)}"
        

async def obtener_resultados_eventos(eventos_finalizados, context):
    """Función que actualiza apuestas con resultados y mantiene resultados.json actualizado"""
    print("🔍 Procesando apuestas actualizadas con resultados...")

    try:
        eventos_actualizados = set()
        
        for evento in eventos_finalizados:
            event_id = evento['event_id']
            eventos_actualizados.add(event_id)

        # Procesar eventos actualizados en la base de datos
        if eventos_actualizados:
            print(f"📤 Procesando eventos actualizados: {list(eventos_actualizados)}")
            for event_id in eventos_actualizados:
                await decidir_apuesta_ganada(context, event_id)
            
            
            
            return "✅ Resultados procesados correctamente y resultados.json actualizado."
        else:
            print("ℹ️ No hubo eventos nuevos para procesar.")
            return "ℹ️ No hubo eventos nuevos para procesar."

    except Exception as e:
        print(f"⚠️ Error en obtener_resultados_eventos: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"⚠️ Error: {str(e)}"

def save_match_result(event_id: str, nombre_partido: str, fecha_partido: str, deporte: str, match_data: dict):
    """Guarda los resultados en el archivo JSON con la estructura organizada"""
    try:
        # Cargar resultados existentes o crear nuevo diccionario
        if os.path.exists('resultados.json'):
            with open('resultados.json', 'r', encoding='utf-8') as f:
                resultados = json.load(f)
        else:
            resultados = {}
        
        # Asegurar que existe la estructura para el deporte
        if deporte not in resultados:
            resultados[deporte] = {}
        
        # Crear/actualizar entrada para este partido
        resultados[deporte][event_id] = {
            'nombre_partido': nombre_partido,
            'fecha_partido': fecha_partido,
            'ultima_actualizacion': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'datos': match_data
        }
        
        # Guardar los resultados
        with open('resultados.json', 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar resultados: {str(e)}")
        return False
async def get_match_data(event_id: str, nombre_partido: str, fecha_partido: str, deporte: str = "football", context=None) -> Optional[dict]:
    """
    Versión modificada que actualiza directamente las apuestas en la base de datos
    """
    print(f"\n{'='*50}")
    print(f"🚀 INICIANDO BÚSQUEDA PARA PARTIDO: {nombre_partido}")
    
    try:
        # 1. Obtener detalles del evento usando el event_id (fixture_id)
        fixture_info = await obtener_detalles_evento(int(event_id))
        
        if not fixture_info:
            print(f"❌ FALLO CRÍTICO: No se pudieron obtener los detalles del partido.")
            if context:
                try:
                    apuestas = obtener_todas_las_apuestas()
                    await resumen_evento_no_encontrado(context, event_id)
                except Exception as e:
                    print(f"⚠️ Error al notificar evento no encontrado: {str(e)}")
            return None

        # ===== VALIDACIÓN =====
        status_short = fixture_info['fixture']['status']['short'].upper()
        status_long = fixture_info['fixture']['status']['long'].upper()
        if status_short not in ESTADOS_FINALIZADOS and status_long not in ESTADOS_FINALIZADOS:
            print(f"⏳ Partido NO está finalizado. Estado actual: {status_long} ({status_short})")
            return None

        home_team = fixture_info["teams"]["home"]["name"]
        away_team = fixture_info["teams"]["away"]["name"]
        local_id = fixture_info["teams"]["home"]["id"]
        visitante_id = fixture_info["teams"]["away"]["id"]
        
        print(f"✅ Partido encontrado (FT):")
        print(f"   Local: {home_team} (ID: {local_id})")
        print(f"   Visitante: {away_team} (ID: {visitante_id})")
        print(f"   Fecha: {fixture_info['fixture']['date']}")
        print(f"   Estado: {fixture_info['fixture']['status']['long']}")

        # 2. Procesamiento de datos del partido
        print("\n🔍 Procesamiento de datos del partido")
        fixture = fixture_info['fixture']
        goals = fixture_info['goals']
        score = fixture_info.get('score', {})

        # 3. Crear estructura de datos del partido para resultados.json
        match_data = {
            'estado': fixture['status']['short'],
            'marcador': {
                'local': goals.get('home', '?'),
                'visitante': goals.get('away', '?')
            },
            'periodos': {},
            'eventos': [],
            'estadisticas': {},
            'api_football_id': fixture['id'],
            'home_team': home_team,
            'away_team': away_team,
            'commence_time': fecha_partido
        }

        # Procesar periodos
        sport_config = SPORT_CONFIG.get(deporte.lower(), SPORT_CONFIG['football'])
        for period in sport_config['periods']:
            if period == '1T':
                match_data['periodos'][period] = {
                    'local': score.get('halftime', {}).get('home', '?'),
                    'visitante': score.get('halftime', {}).get('away', '?')
                }
            elif period == '2T':
                match_data['periodos'][period] = {
                    'local': int(goals.get('home', 0)) - int(score.get('halftime', {}).get('home', 0)) if str(goals.get('home', '?')).isdigit() else '?',
                    'visitante': int(goals.get('away', 0)) - int(score.get('halftime', {}).get('away', 0)) if str(goals.get('away', '?')).isdigit() else '?'
                }
            else:
                match_data['periodos'][period] = {
                    'local': '?',
                    'visitante': '?'
                }

        # 4. Obtener eventos del partido
        url_events = f"{API_FUTBOL_BASE_URL}/fixtures/events"
        params_events = {"fixture": fixture['id']}

        try:
            events_response = requests.get(url_events, headers=API_FUTBOL_HEADERS, params=params_events)
            
            if events_response.status_code == 200:
                events_data = events_response.json()

                for evento in events_data.get('response', []):
                    event_type = evento.get('type', '').lower()
                    if event_type in sport_config['incident_types']:
                        event_data = {
                            'tipo': event_type,
                            'jugador': evento.get('player', {}).get('name', 'Desconocido'),
                            'minuto': evento.get('time', {}).get('elapsed', '?'),
                            'equipo': 'local' if evento.get('team', {}).get('id') == local_id else 'visitante'
                        }
                        
                        if event_type == 'card':
                            event_data['tipo_tarjeta'] = evento.get('detail', 'desconocido').lower()
                        if event_type == 'goal':
                            event_data['tipo_gol'] = evento.get('detail', 'normal').lower()
                        
                        match_data['eventos'].append(event_data)
            
            else:
                print(f"⚠️ Error al obtener eventos: HTTP {events_response.status_code}")

        except Exception as e:
            print(f"⚠️ Excepción al obtener eventos: {str(e)}")

        # 5. Obtener estadísticas
        url_stats = f"{API_FUTBOL_BASE_URL}/fixtures/statistics"
        params_stats = {"fixture": fixture['id']}

        try:
            stats_response = requests.get(url_stats, headers=API_FUTBOL_HEADERS, params=params_stats)

            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                print(f"📊 Estadísticas recibidas para {len(stats_data.get('response', []))} categorías")

                for stat in stats_data.get('response', []):
                    if stat.get('team', {}).get('id') == local_id:
                        for item in stat.get('statistics', []):
                            if item.get('type') and item.get('value'):
                                match_data['estadisticas'][item['type']] = {
                                    'local': item['value'],
                                    'visitante': '?'
                                }
                    elif stat.get('team', {}).get('id') == visitante_id:
                        for item in stat.get('statistics', []):
                            if item.get('type') and item.get('value') and item['type'] in match_data['estadisticas']:
                                match_data['estadisticas'][item['type']]['visitante'] = item['value']
            else:
                print(f"⚠️ Error al obtener estadísticas: HTTP {stats_response.status_code}")

        except Exception as e:
            print(f"⚠️ Excepción al obtener estadísticas: {str(e)}")

        # 6. ✅ GUARDAR EN RESULTADOS.JSON - AQUÍ ESTÁ LA LLAMADA QUE NECESITAS
        try:
            if save_match_result(event_id, nombre_partido, fecha_partido, deporte, match_data):
                print(f"🗃️ Datos guardados correctamente en resultados.json")
            else:
                print(f"❌ Error al guardar en resultados.json")
        except Exception as e:
            print(f"⚠️ Error al guardar en resultados.json: {str(e)}")

        # 7. Actualizar directamente las apuestas en la base de datos
        try:
            # Obtener todas las apuestas que contienen este event_id
            apuestas = obtener_apuestas_por_evento(event_id)
            
            if not apuestas:
                print(f"ℹ️ No se encontraron apuestas para el evento {event_id}")
                return event_id

            for apuesta in apuestas:
                # Para apuestas PREPARTIDO/LIVE
                if apuesta.get("betting") in ["PREPARTIDO", "LIVE"]:
                    campos_actualizados = {
                        'id': apuesta['id'],
                        'completed': True,
                        'scores_json': json.dumps([
                            {
                                "name": home_team,
                                "score": str(goals.get('home', '?'))
                            },
                            {
                                "name": away_team,
                                "score": str(goals.get('away', '?'))
                            }
                        ]),
                        'home_team': home_team,
                        'away_team': away_team,
                        'last_update': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                        'estado': "🔚 Finalizado"
                    }
                    
                    if actualizar_apuesta_en_db(campos_actualizados):
                        print(f"✅ Apuesta {apuesta['id']} actualizada en la base de datos")
                
                # Para apuestas COMBINADAS
                elif apuesta.get('betting') == 'COMBINADA':
                    selecciones_actualizadas = False
                    for seleccion in apuesta.get('selecciones', []):
                        if seleccion.get('event_id') == event_id:
                            seleccion.update({
                                'completed': True,
                                'scores': [
                                    {
                                        "name": home_team,
                                        "score": str(goals.get('home', '?'))
                                    },
                                    {
                                        "name": away_team,
                                        "score": str(goals.get('away', '?'))
                                    }
                                ],
                                'home_team': home_team,
                                'away_team': away_team,
                                'last_update': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                                'estado': "🔚 Finalizado"
                            })
                            selecciones_actualizadas = True
                    
                    if selecciones_actualizadas:
                        campos_actualizados = {
                            'id': apuesta['id'],
                            'selecciones_json': json.dumps(apuesta.get('selecciones', [])),
                            'last_update': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                        }
                        
                        if actualizar_apuesta_en_db(campos_actualizados):
                            print(f"✅ Apuesta combinada {apuesta['id']} actualizada en la base de datos")

            return event_id

        except Exception as e:
            print(f"🚨 ERROR AL ACTUALIZAR APUESTAS: {str(e)}")
            return None

    except Exception as e:
        print(f"\n{'='*50}")
        print(f"🚨 ERROR CRÍTICO NO MANEJADO: {str(e)}")
        print(f"{'='*50}")
        return None


def actualizar_apuesta_en_db(campos_actualizados):
    """
    Actualiza una apuesta en la base de datos con los campos proporcionados
    """
    try:
        # Extraer el ID de la apuesta
        apuesta_id = campos_actualizados['id']
        
        # Filtrar campos que no existen en la base de datos
        campos_validos = {}
        for campo, valor in campos_actualizados.items():
            if campo == 'id':
                continue
                
            # Convertir campos especiales a nombres de columna correctos
            if campo == 'scores':
                campos_validos['scores_json'] = json.dumps(valor)
            elif campo == 'selecciones':
                campos_validos['selecciones_json'] = json.dumps(valor)
            else:
                campos_validos[campo] = valor
        
        # Actualizar el registro
        return actualizar_registro('apuestas', apuesta_id, campos_validos)
        
    except Exception as e:
        print(f"Error al actualizar apuesta en DB: {e}")
        return False


async def ejecutar_pagar(update: Update, context: CallbackContext):
    """Comando que inicia la ejecución automática cada 5 minutos."""
    query = update.callback_query
    await query.answer()  # Evita que Telegram muestre "cargando..."

    job_queue = context.job_queue

    if job_queue is None:
        await query.message.reply_text("⚠️ JobQueue no está disponible.")
        return

    # Agregar la tarea en `JobQueue`
    job_queue.run_repeating(buscar_apuestas_finalizadas, interval=300, first=5, name="buscar_apuestas")

    await query.message.reply_text("🔄 El proceso de búsqueda de apuestas finalizadas se ejecutará cada 5 minutos.")
    
async def detener_pagos(update: Update, context: CallbackContext):
    """Detiene la ejecución automática de la búsqueda de apuestas."""
    query = update.callback_query
    await query.answer()  # Evita que Telegram muestre "cargando..."

    job_queue = context.job_queue

    if job_queue is None:
        await query.message.reply_text("⚠️ JobQueue no está disponible.")
        return

    # Buscar y eliminar la tarea programada
    jobs = job_queue.get_jobs_by_name("buscar_apuestas")
    if jobs:
        for job in jobs:
            job.schedule_removal()
        await query.message.reply_text("✅ El proceso de búsqueda de apuestas ha sido detenido.")
    else:
        await query.message.reply_text("⚠️ No hay procesos activos en ejecución.")
        
async def procesar_marcador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actualiza el marcador en PREPARTIDO, LIVE y COMBINADAS en la base de datos"""
    try:
        # Validar comando
        texto = update.message.text
        match = re.match(r'^/local\s+(\d+)\s+visitante\s+(\d+)\s+\((.*?)\)$', texto.strip())
        if not match:
            await update.message.reply_text("❌ Formato incorrecto. Usa: /local [goles_local] visitante [goles_visitante] (event_id)")
            return

        local_score, visitante_score, event_id = match.groups()
        updates_made = False
        partido_info = None

        try:
            # 1. Actualizar apuestas PREPARTIDO y LIVE
            consulta_prepartido = """
                SELECT id, partido, home_team, away_team 
                FROM apuestas 
                WHERE event_id = ? AND betting IN ('PREPARTIDO', 'LIVE')
            """
            apuestas_prepartido = ejecutar_consulta_segura(consulta_prepartido, (event_id,), obtener_resultados=True)
            
            for apuesta in apuestas_prepartido:
                try:
                    # Obtener nombres de equipos (las tuplas vienen en orden: id, partido, home_team, away_team)
                    apuesta_id = apuesta[0]  # Primer elemento: id
                    partido_str = apuesta[1]  # Segundo elemento: partido
                    home_team = apuesta[2] or partido_str.split(' 🆚 ')[0].strip()  # Tercer elemento: home_team
                    away_team = apuesta[3] or partido_str.split(' 🆚 ')[1].strip()  # Cuarto elemento: away_team
                    
                    # Preparar datos para actualizar
                    scores_data = [{"name": home_team, "score": local_score}, 
                                  {"name": away_team, "score": visitante_score}]
                    
                    campos_actualizados = {
                        'id': apuesta_id,
                        'scores': scores_data,
                        'completed': True,
                        'estado': "🔚 Finalizado",
                        'home_team': home_team,
                        'away_team': away_team,
                        'last_update': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Actualizar usando la función existente
                    if actualizar_apuesta_en_db(campos_actualizados):
                        updates_made = True
                        partido_info = f"{home_team} {local_score}-{visitante_score} {away_team}"
                    
                except Exception as e:
                    print(f"⚠️ Error al procesar PREPARTIDO/LIVE: {str(e)}")
                    continue

            # 2. Actualizar COMBINADAS
            consulta_combinadas = "SELECT id, selecciones_json FROM apuestas WHERE betting = 'COMBINADA'"
            apuestas_combinadas = ejecutar_consulta_segura(consulta_combinadas, obtener_resultados=True)
            
            for apuesta in apuestas_combinadas:
                try:
                    apuesta_id = apuesta[0]  # Primer elemento: id
                    selecciones_json_str = apuesta[1]  # Segundo elemento: selecciones_json
                    
                    if not selecciones_json_str:
                        continue
                        
                    selecciones = json.loads(selecciones_json_str)
                    updated = False
                    
                    for seleccion in selecciones:
                        if seleccion.get('event_id') == event_id:
                            # Extraer equipos de múltiples formas
                            partido = seleccion.get('partido', '')
                            home_team = seleccion.get('home_team', partido.split(' vs ')[0].strip() if ' vs ' in partido else "Local")
                            away_team = seleccion.get('away_team', partido.split(' vs ')[1].strip() if ' vs ' in partido else "Visitante")
                            
                            # Actualizar selección
                            seleccion.update({
                                'scores': [{"name": home_team, "score": local_score}, 
                                          {"name": away_team, "score": visitante_score}],
                                'completed': True,
                                'estado': "🔚 Finalizado",
                                'home_team': home_team,
                                'away_team': away_team,
                                'last_update': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            updated = True
                            if partido_info is None:
                                partido_info = f"{home_team} {local_score}-{visitante_score} {away_team}"
                    
                    if updated:
                        # Actualizar usando la función existente
                        campos_actualizados = {
                            'id': apuesta_id,
                            'selecciones': selecciones
                        }
                        if actualizar_apuesta_en_db(campos_actualizados):
                            updates_made = True
                        
                except Exception as e:
                    print(f"⚠️ Error al procesar COMBINADA: {str(e)}")
                    continue

            # Notificar éxito
            if updates_made:
                try:
                    await decidir_apuesta_ganada(context, event_id)
                    await update.message.reply_text(
                        f"✅ Marcador actualizado:\n🏆 {partido_info}\n📌 Event ID: {event_id}"
                    )
                except Exception as e:
                    print(f"⚠️ Error al decidir apuesta ganada: {str(e)}")
                    await update.message.reply_text(
                        f"✅ Marcador actualizado (verificación pendiente):\n🏆 {partido_info}\n📌 Event ID: {event_id}"
                    )
            else:
                await update.message.reply_text("⚠️ Evento no encontrado en apuestas activas")

        except Exception as e:
            print(f"❌ Error al procesar base de datos: {str(e)}")
            await update.message.reply_text("⚠️ Error interno al procesar apuestas")

    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        await update.message.reply_text("⚠️ Error al procesar el comando")
async def resumen_apuestas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    # Obtener apuestas desde la base de datos
    consulta = "SELECT * FROM apuestas"
    todas_apuestas_tuples = ejecutar_consulta_segura(consulta, obtener_resultados=True)
    
    if not todas_apuestas_tuples:
        await update.message.reply_text("No hay apuestas en la base de datos.")
        return

    # Convertir tuplas a diccionarios
    apuestas = []
    for apuesta_tuple in todas_apuestas_tuples:
        try:
            apuesta = {
                'id': apuesta_tuple[0],
                'usuario_id': apuesta_tuple[1],
                'user_name': apuesta_tuple[2],
                'fecha_realizada': apuesta_tuple[3],
                'fecha_inicio': apuesta_tuple[4],
                'monto': float(apuesta_tuple[5] or 0),
                'cuota': float(apuesta_tuple[6] or 0),
                'ganancia': float(apuesta_tuple[7] or 0),
                'estado': apuesta_tuple[8] or "Desconocido",
                'bono': float(apuesta_tuple[9] or 0),
                'balance': float(apuesta_tuple[10] or 0),
                'betting': apuesta_tuple[11] or "Desconocido",
                'id_ticket': apuesta_tuple[12] or "",
                'event_id': apuesta_tuple[13] or "",
                'deporte': apuesta_tuple[14] or "Desconocido",
                'liga': apuesta_tuple[15] or "Desconocido",
                'sport_key': apuesta_tuple[16] or "",
                'partido': apuesta_tuple[17] or "Partido desconocido",
                'favorito': apuesta_tuple[18] or "Desconocido",
                'tipo_apuesta': apuesta_tuple[19] or "Desconocido",
                'selecciones_json': apuesta_tuple[29] or "[]",
                'scores_json': apuesta_tuple[30] or "[]"
            }
            apuestas.append(apuesta)
        except (TypeError, ValueError, IndexError) as e:
            print(f"⚠️ Error procesando apuesta: {e}")
            continue

    # Separar apuestas PREPARTIDO y COMBINADA
    prepartido_apuestas = [a for a in apuestas if a.get("betting") in ["PREPARTIDO", "LIVE"]]
    combinada_apuestas = [a for a in apuestas if a.get("betting") == "COMBINADA"]

    # Procesar apuestas PREPARTIDO
    resumen_prepartido = {}
    for apuesta in prepartido_apuestas:
        event_id = apuesta["event_id"]
        partido = apuesta["partido"]
        deporte = apuesta["deporte"][0] if apuesta["deporte"] else "❓"
        monto = apuesta["monto"]
        favorito = apuesta["favorito"]

        if (event_id, partido) not in resumen_prepartido:
            resumen_prepartido[(event_id, partido)] = {
                "deporte": deporte,
                "total_apostado": 0,
                "apuestas": {},
                "apuesta_mayor": {"monto": 0, "favorito": ""},
                "event_id": event_id,
                "partido": partido,
            }

        resumen = resumen_prepartido[(event_id, partido)]
        resumen["total_apostado"] += monto

        if favorito in resumen["apuestas"]:
            resumen["apuestas"][favorito] += monto
        else:
            resumen["apuestas"][favorito] = monto

        if monto > resumen["apuesta_mayor"]["monto"]:
            resumen["apuesta_mayor"] = {"monto": monto, "favorito": favorito}

    # Procesar apuestas COMBINADA
    resumen_combinadas = {}
    for apuesta in combinada_apuestas:
        # Generar event_id único si no existe
        event_id = apuesta.get("event_id")
        if not event_id:
            unique_str = f"{apuesta['usuario_id']}_{apuesta['fecha_realizada']}_{apuesta['monto']}"
            event_id = hashlib.md5(unique_str.encode()).hexdigest()[:8]

        # Parsear selecciones JSON
        selecciones = []
        try:
            if apuesta.get("selecciones_json"):
                selecciones = json.loads(apuesta["selecciones_json"])
        except json.JSONDecodeError:
            selecciones = []

        if event_id not in resumen_combinadas:
            resumen_combinadas[event_id] = {
                "monto": apuesta["monto"],
                "cuota": apuesta["cuota"],
                "ganancia": apuesta["ganancia"],
                "estado": apuesta["estado"],
                "selecciones": selecciones,
                "fecha_realizada": apuesta["fecha_realizada"],
                "event_id": event_id,
            }

    # Mostrar resumen PREPARTIDO
    if resumen_prepartido:
        for key in resumen_prepartido:
            event_id, partido = key
            datos = resumen_prepartido[key]
            
            apuestas_formateadas = [
                f"<blockquote>• {tipo}:</blockquote> <code>{monto:>6} CUP</code>"
                for tipo, monto in datos["apuestas"].items()
            ]

            mensaje = (
                f"<blockquote>🏆 {datos['partido']}</blockquote>\n"
                f"<b>🏅 Deporte:</b> {datos['deporte']}\n"
                f"<b>💰 Total Apostado:</b> <code>{datos['total_apostado']:>6} CUP</code>\n"
                f"<b>📅 Event ID:</b> <code>{datos['event_id']}</code>\n\n"
                f"<b>📈 Apuestas:</b>\n" + "\n".join(apuestas_formateadas) + "\n\n"
                f"<b>🔥 Apuesta Mayor:</b> <code>{datos['apuesta_mayor']['monto']:>6} CUP</code> en <i>{datos['apuesta_mayor']['favorito']}</i>"
            )

            equipos = datos['partido'].split(" 🆚 ")
            keyboard = []
            if len(equipos) >= 2:
                keyboard = [
                    [InlineKeyboardButton("📋 Ver Detalles", callback_data=f"detalles_{event_id}"),
                     InlineKeyboardButton("🔄 Reembolsar", callback_data=f"reembolsar_{event_id}")],
                    [InlineKeyboardButton(f"🏆 {equipos[0]}", callback_data=f"win_{event_id}_{equipos[0]}"),
                     InlineKeyboardButton(f"🏆 {equipos[1]}", callback_data=f"win_{event_id}_{equipos[1]}")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("📋 Ver Detalles", callback_data=f"detalles_{event_id}"),
                     InlineKeyboardButton("🔄 Reembolsar", callback_data=f"reembolsar_{event_id}")]
                ]
            
            await update.message.reply_text(mensaje, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("No hay apuestas PREPARTIDO pendientes.")

    # Mostrar resumen COMBINADA
    if resumen_combinadas:
        for event_id, datos in resumen_combinadas.items():
            selecciones_texto = ""
            for s in datos['selecciones']:
                selecciones_texto += f"<blockquote>• {s.get('partido', 'Partido')} - {s.get('favorito', 'Favorito')} ({s.get('cuota_individual', '0')})</blockquote>"

            mensaje = (
                f"<b>🎰 Apuesta COMBINADA</b>\n"
                f"<b>📅 Fecha:</b> {datos['fecha_realizada']}\n"
                f"<b>💰 Monto:</b> <code>{datos['monto']} CUP</code>\n"
                f"<b>📈 Cuota:</b> {datos['cuota']}\n"
                f"<b>🏆 Ganancia:</b> {datos['ganancia']} CUP\n"
                f"<b>🔍 Selecciones:</b>\n" + selecciones_texto
            )

            keyboard = [
                [InlineKeyboardButton("✅ Ganada", callback_data=f"comb_ganada_{event_id}"),
                 InlineKeyboardButton("❌ Perdida", callback_data=f"comb_perdida_{event_id}")]
            ]
            await update.message.reply_text(mensaje, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("No hay apuestas COMBINADAS pendientes.")
async def pagar_apuestas_ganadoras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_", 1)  # Dividimos en 2 partes: "win" y "equipo_ganador"

    if len(data) < 2:  # Verificamos que el callback_data tenga el formato correcto
        await query.message.reply_text("⚠️ Error al procesar la apuesta.")
        return

    _, equipo_ganador = data  # Extraemos el equipo ganador

    # Usar ambos locks para todo el proceso
    async with lock_data:
        # Cargar apuestas y datos de usuarios
        apuestas = await cargar_apuestas()
        usuarios_data = await load_data()

        # Filtrar solo apuestas h2h donde el favorito es el equipo ganador y están pendientes
        apuestas_ganadoras = [
            a for a in apuestas
            if a["favorito"].strip() == equipo_ganador.strip()  # Comparar el favorito con el equipo ganador
            and a["tipo_apuesta"] == "h2h"
            and a["estado"] == "⌛Pendiente"
        ]

        resumen_ganadores = []
        resumen_perdedores = []
        totales = {"bono": 0, "balance": 0, "rollover": 0}

        for apuesta in apuestas_ganadoras:
            usuario_id = apuesta["usuario_id"]
            favorito = apuesta["favorito"]
            es_ganador = (favorito == equipo_ganador)  # Siempre será True en este caso

            monto_bono = apuesta["bono"]
            monto_balance = apuesta["balance"]
            cuota = apuesta["cuota"]
            rollover = monto_bono + monto_balance

            # Actualizar ROLLOVER para todos
            usuarios_data["Bono_apuesta"][usuario_id]["Rollover_actual"] += monto_bono

            if es_ganador:
                # Calcular ganancias
                ganancia_bono = monto_bono * (cuota - 1)
                ganancia_balance = monto_balance * (cuota - 1)

                # Actualizar saldos
                usuarios_data["Bono_apuesta"][usuario_id]["Bono"] += monto_bono  # Devuelve bono apostado
                usuarios_data["Bono_apuesta"][usuario_id]["Bono_retirable"] += ganancia_bono
                usuarios_data["usuarios"][usuario_id]["Balance"] += monto_balance + ganancia_balance

                # Actualizar estado
                apuesta["estado"] = "✅  Ganada"

                # Acumular totales
                totales["bono"] += ganancia_bono
                totales["balance"] += ganancia_balance
                totales["rollover"] += rollover

                # Preparar mensaje para ganador
                mensaje = (
                    " <blockquote> ✅¡APUESTA GANADA!✅ </blockquote> \n\n"
                    f"🏆 <b>Liga:</b> {apuesta['liga']}\n"
                    f"🔰 <b>Partido:</b> <code>{apuesta['partido']}</code>\n\n"
                    f"💰 <b>Monto total:</b> <code>{monto_bono + monto_balance}</code> CUP\n"
                    f"💹 <b>Cuota:</b> {cuota}\n\n"
                    f"💰 <b>Ganancias:</b>\n"
                    f"  ├ 🎁 <b>Bono retirable:</b> +<code>{ganancia_bono}</code> CUP\n"
                    f"  └ 💲 <b>Balance:</b> +<code>{ganancia_balance}</code> CUP\n\n"
                    f"🏦 <b>Nuevo balance:</b> <code>{usuarios_data['usuarios'][usuario_id]['Balance']}</code> CUP\n\n"
                    "<i>¡Felicidades! Sigue apostando con inteligencia. 💪</i>"
                )
                resumen_ganadores.append(f"🆔 {usuario_id} | +{ganancia_bono + ganancia_balance} CUP")
            else:
                apuesta["estado"] = "❌ Perdida"
                mensaje = (
                    f"<blockquote>❌ APUESTA PERDIDA ❌</blockquote>\n\n"
                    f"🏆 <b>Liga:</b> {apuesta['liga']}\n"
                    f"🔰 <b>Partido:</b> {apuesta['partido']}\n"
                    f"💰 <b>Monto Apostado:</b> {monto_bono + monto_balance} CUP\n"
                    f"💳 <b>Balance Actual:</b> {usuarios_data['usuarios'][usuario_id]['Balance']} CUP\n"
                )
                resumen_perdedores.append(f"🆔 {usuario_id} | -{monto_bono + monto_balance} CUP")

        # Guardar TODOS los cambios ANTES de enviar mensajes
        

    # Enviar notificaciones a usuarios FUERA del bloqueo
    for apuesta in apuestas_ganadoras:
        usuario_id = apuesta["usuario_id"]
        es_ganador = (apuesta["favorito"] == equipo_ganador)
        
        if es_ganador:
            mensaje = (
                " <blockquote> ✅¡APUESTA GANADA!✅ </blockquote> \n\n"
                f"🏆 <b>Liga:</b> {apuesta['liga']}\n"
                f"🔰 <b>Partido:</b> <code>{apuesta['partido']}</code>\n\n"
                f"💰 <b>Monto total:</b> <code>{apuesta['bono'] + apuesta['balance']}</code> CUP\n"
                f"💹 <b>Cuota:</b> {apuesta['cuota']}\n\n"
                f"💰 <b>Ganancias:</b>\n"
                f"  ├ 🎁 <b>Bono retirable:</b> +<code>{apuesta['bono'] * (apuesta['cuota'] - 1)}</code> CUP\n"
                f"  └ 💲 <b>Balance:</b> +<code>{apuesta['balance'] * (apuesta['cuota'] - 1)}</code> CUP\n\n"
                "<i>¡Felicidades! Sigue apostando con inteligencia. 💪</i>"
            )
        else:
            mensaje = (
                f"<blockquote>❌ APUESTA PERDIDA ❌</blockquote>\n\n"
                f"🏆 <b>Liga:</b> {apuesta['liga']}\n"
                f"🔰 <b>Partido:</b> {apuesta['partido']}\n"
                f"💰 <b>Monto Apostado:</b> {apuesta['bono'] + apuesta['balance']} CUP\n"
            )

        try:
            await context.bot.send_message(
                chat_id=usuario_id,
                text=mensaje,
                parse_mode='HTML'
            )
            await asyncio.sleep(3)  # Esperar 1 segundo para no saturar el servidor
        except Exception as e:
            print(f"Error enviando mensaje a {usuario_id}: {e}")

    # Resumen para admin
    mensaje_admin = (
        f"🏆 Ganador seleccionado: {equipo_ganador}\n\n"
        f"✅ Ganadores ({len(resumen_ganadores)}):\n" + "\n".join(resumen_ganadores) + "\n\n"
        f"❌ Perdedores ({len(resumen_perdedores)}):\n" + "\n".join(resumen_perdedores) + "\n\n"
        f"📈 Totales:\n"
        f"  • Bono retirable: {totales['bono']} CUP\n"
        f"  • Balance pagado: {totales['balance']} CUP\n"
        f"  • Rollover añadido: {totales['rollover']} CUP"
    )

    await query.message.reply_text(mensaje_admin)
    await query.answer()


async def reembolsar_apuestas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    partido = query.data.split("_")[1]

    # Variables para el resumen
    usuarios_reembolsados = []
    bono_total_reembolsado = 0
    balance_total_reembolsado = 0
    resumen_por_usuario = []

    async with lock_data:  # Bloquear TODO el proceso de reembolso
        try:
            # Cargar apuestas y datos de usuarios
            apuestas = await cargar_apuestas()
            usuarios_data = await load_data()

            # Filtrar apuestas del partido seleccionado
            apuestas_partido = [a for a in apuestas if a["partido"] == partido and a["estado"] == "⌛Pendiente"]

            for apuesta in apuestas_partido:
                usuario_id = apuesta["usuario_id"]
                monto_bono = apuesta["bono"]
                monto_balance = apuesta["balance"]

                # Reembolsar el monto correspondiente
                if usuario_id in usuarios_data["usuarios"]:
                    usuarios_data["usuarios"][usuario_id]["Balance"] += monto_balance
                    if usuario_id in usuarios_data["Bono_apuesta"]:
                        usuarios_data["Bono_apuesta"][usuario_id]["Bono"] += monto_bono

                # Actualizar el estado de la apuesta
                apuesta["estado"] = "🔄 Reembolsada"

                # Acumular totales
                bono_total_reembolsado += monto_bono
                balance_total_reembolsado += monto_balance

                # Agregar al resumen por usuario
                resumen_por_usuario.append(
                    f"🆔 Usuario: <code> {usuario_id}</code>\n"
                    f"  - Bono reembolsado: {monto_bono} CUP\n"
                    f"  - Balance reembolsado: {monto_balance} CUP\n\n"
                )
                usuarios_reembolsados.append(usuario_id)

            # Guardar TODOS los cambios al final
           

        except Exception as e:
            print(f"Error en el proceso de reembolso: {e}")
            await query.answer("❌ Error al procesar reembolsos", show_alert=True)
            return

    # Notificar a los usuarios (fuera del bloqueo para no mantenerlo por mucho tiempo)
    for usuario_id in usuarios_reembolsados:
        try:
            await context.bot.send_message(
                chat_id=usuario_id,
                text=f"""
<blockquote>🔄 REEMBOLSO DE APUESTA 🔄</blockquote>

<b>⚽ Evento:</b>
🏆 Partido: {partido}


<b>💰 Montos Reembolsados:</b>
  ┌ 🎁 <b>Bono:</b> <code>{monto_bono}</code> CUP
  └ 💰 <b>Balance:</b> <code>{monto_balance}</code> CUP

<i>Los fondos han sido devueltos a tu cuenta.</i>
                """,
                parse_mode="HTML"
            )
            await asyncio.sleep(3)  # Esperar entre notificaciones
        except Exception as e:
            print(f"No se pudo notificar al usuario {usuario_id}: {e}")

    # Crear y enviar resumen
    mensaje_resumen = [
        f"✅ <b>REEMBOLSOS REALIZADOS</b> ✅",
        f"⚽ Partido: {partido}",
        f"👤 Usuarios afectados: {len(usuarios_reembolsados)}",
        f"💰 Total reembolsado:",
        f"  ├ 🎁 Bono: {bono_total_reembolsado} CUP",
        f"  └ 💰 Balance: {balance_total_reembolsado} CUP",
        "",
        "<b>📝 Detalle por usuario:</b>"
    ]

    # Enviar mensaje principal
    await query.message.reply_text("\n".join(mensaje_resumen), parse_mode="HTML")

    # Enviar detalles por usuario en chunks
    chunk = []
    for detalle in resumen_por_usuario:
        if len("\n".join(chunk + [detalle])) > 4000:
            await query.message.reply_text("\n".join(chunk))
            chunk = [detalle]
        else:
            chunk.append(detalle)
    
    if chunk:
        await query.message.reply_text("\n".join(chunk))

    await query.answer("✅ Proceso de reembolso completado")     

async def eliminar_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fecha_realizada = query.data.split("_")[1]  # Obtener la fecha_realizada desde el callback_data

    async with lock_data:  # Bloqueo para acceso seguro a los datos
        try:
            # Cargar las apuestas actuales
            apuestas = await cargar_apuestas()
            
            # Buscar la apuesta a eliminar
            apuesta_a_eliminar = next((a for a in apuestas if a["fecha_realizada"] == fecha_realizada), None)
            
            if not apuesta_a_eliminar:
                await query.answer("⚠️ Apuesta no encontrada")
                return

            # Eliminar apuestas relacionadas si es combinada
            if apuesta_a_eliminar.get("betting") == "COMBINADA":
                # Eliminar todas las selecciones de esta combinada (si existen en la lista principal)
                apuestas = [a for a in apuestas 
                          if not (a.get("parent_combinada") == apuesta_a_eliminar.get("fecha_realizada"))]
            
            # Filtrar y eliminar la apuesta principal
            nuevas_apuestas = [a for a in apuestas if a["fecha_realizada"] != fecha_realizada]

            # Guardar las apuestas actualizadas
            await guardar_apuestas(nuevas_apuestas)

            # Notificar al usuario
            await query.answer("✅ Apuesta eliminada correctamente")
            
            # Eliminar el mensaje de la apuesta
            try:
                await query.message.delete()
            except Exception as e:
                print(f"⚠️ Error al eliminar mensaje: {e}")

        except Exception as e:
            print(f"⚠️ Error al eliminar la apuesta: {e}")
            await query.answer("❌ Error al eliminar la apuesta", show_alert=True)
# Manejar partidos individuales manualmente
async def detalles_partido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    event_id = query.data.split("_")[1]  # Ahora obtenemos el event_id desde el callback_data
    apuestas = await cargar_apuestas()

    # Filtrar TODAS las apuestas del evento (sin filtrar por estado)
    apuestas_evento = []
    apuestas_combinadas_relacionadas = []
    
    for apuesta in apuestas:
        # Apuestas directas del evento
        if apuesta.get("event_id") == event_id and apuesta.get("betting") in ["PREPARTIDO", "LIVE"]:
            apuestas_evento.append(apuesta)
        
        # Buscar en combinadas que contengan este evento
        if apuesta.get("betting") == "COMBINADA" and "selecciones" in apuesta:
            for seleccion in apuesta["selecciones"]:
                if seleccion.get("event_id") == event_id:
                    apuestas_combinadas_relacionadas.append(apuesta)
                    break  # No necesitamos revisar más selecciones de esta combinada

    if not apuestas_evento and not apuestas_combinadas_relacionadas:
        await query.answer("⏳ No hay apuestas para este evento.")
        return

    formato_fecha = "%d/%m/%Y %H:%M:%S"
    zona_origen = pytz.utc
    zona_cuba = pytz.timezone("America/Havana")

    def formatear_fecha(fecha_str):
        try:
            fecha_naive = datetime.strptime(fecha_str, formato_fecha)
            fecha_utc = zona_origen.localize(fecha_naive)
            fecha_cuba = fecha_utc.astimezone(zona_cuba)
            dia = str(fecha_cuba.day)
            mes_anio = fecha_cuba.strftime("%m/%Y")
            hora = fecha_cuba.strftime("%I:%M %p").lstrip("0")
            return f"{dia}/{mes_anio} {hora}"
        except Exception:
            return "🕒 Hora no disponible"

    def separador(titulo=None):
        if titulo:
            return f"┏━━━ {titulo} ━━━\n"
        return "┗" + "━"*30 + "\n"

    # Mostrar apuestas PREPARTIDO primero
    for apuesta in apuestas_evento:
        # Obtener datos básicos del evento una sola vez
        partido = apuesta.get("partido", "N/A")
        deporte = apuesta.get("deporte", "N/A")
        liga = apuesta.get("liga", "N/A")
        
        bono = apuesta.get('bono', 0)
        balance = apuesta.get('balance', 0)
        origen_line = (
            f"💎 Bono: {bono} CUP" if bono > 0 
            else f"💰 Balance: {balance} CUP" if balance > 0 
            else "⚠️ Origen desconocido"
        )

        # Determinar marcador
        if 'scores' in apuesta and len(apuesta['scores']) >= 2:
            score1 = apuesta['scores'][0]
            score2 = apuesta['scores'][1]
            marcador = f"🏁 {score1['name']} {score1['score']} - {score2['name']} {score2['score']}"
        elif 'scores' in apuesta:
            marcador = "🏁 " + " - ".join([f"{s['name']} {s.get('score', '?')}" for s in apuesta['scores']])
        else:
            marcador = "⏳ No disponible"

        fecha_formateada = formatear_fecha(apuesta.get('fecha_inicio', 'No disponible'))

        mensaje = (
            f"{separador('APUESTA INDIVIDUAL')}"
            f"🎲 <b>Tipo:</b> <code>PREPARTIDO_LIVE</code>\n"
            f"👤 <b>Usuario:</b> <code>{apuesta['usuario_id']}</code>\n"
            f"📅 <b>Inicio:</b> <code>{fecha_formateada}</code>\n"
            f"⚽ <b>Deporte:</b> <code>{deporte}</code>\n"
            f"🏆 <b>Liga:</b> <code>{liga}</code>\n"
            f"⚔️ <b>Partido:</b> <code>{partido}</code>\n\n"
            f"❤️ <b>Favorito:</b> <code>{apuesta.get('favorito', 'N/A')}</code>\n"
            f"🎯 <b>Tipo Apuesta:</b> <code>{apuesta.get('tipo_apuesta', 'N/A')}</code>\n"
            f"📈 <b>Cuota:</b> <code>{apuesta.get('cuota', 'N/A')}</code>\n"
            f"💵 <b>Monto:</b> <code>{apuesta.get('monto', 'N/A')} CUP</code>\n"
            f"{origen_line}\n"
            f"{marcador}\n"
            f"🔄 <b>Estado:</b> <code>{apuesta.get('estado', 'N/A')}</code>\n"
            f"💰 <b>Ganancia:</b> <code>{apuesta.get('ganancia', 'N/A')} CUP</code>\n"
            f"{separador()}"
        )

        keyboard = [
            [
                InlineKeyboardButton("❌ Eliminar", callback_data=f"eliminar_{apuesta['fecha_realizada']}"),
                InlineKeyboardButton("🔄 Reembolsar", callback_data=f"reembolsar_{apuesta['fecha_realizada']}")
            ],
            [
                InlineKeyboardButton("✅ Ganada", callback_data=f"ganada_{apuesta['fecha_realizada']}"),
                InlineKeyboardButton("❌ Perdida", callback_data=f"perdida_{apuesta['fecha_realizada']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)

    # Mostrar apuestas COMBINADAS relacionadas
    for apuesta in apuestas_combinadas_relacionadas:
        bono = apuesta.get('bono', 0)
        balance = apuesta.get('balance', 0)
        origen_line = (
            f"💎 Bono: {bono} CUP" if bono > 0 
            else f"💰 Balance: {balance} CUP" if balance > 0 
            else "⚠️ Origen desconocido"
        )

        # Obtener información de las selecciones
        selecciones_info = []
        for i, seleccion in enumerate(apuesta.get("selecciones", []), 1):
            # Solo mostrar marcador para la selección del evento actual
            if seleccion.get("event_id") == event_id:
                marcador = " - ".join([f"{s['name']} {s.get('score', '?')}" for s in seleccion.get('scores', [])]) if 'scores' in seleccion else "⏳ No disponible"
                
                seleccion_info = (
                    f"┌─── <b>SELECCIÓN RELACIONADA</b> ───\n"
                    f"├ ⚽ <b>Partido:</b> {seleccion.get('partido', 'N/A')}\n"
                    f"├ ❤️ <b>Favorito:</b> {seleccion.get('favorito', 'N/A')}\n"
                    f"├ 🎯 <b>Tipo:</b> {seleccion.get('mercado', 'N/A')}\n"
                    f"├ 📈 <b>Cuota:</b> {seleccion.get('cuota_individual', 'N/A')}\n"
                    f"└ 🏁 <b>Marcador:</b> {marcador}\n"
                )
                selecciones_info.append(seleccion_info)

        fecha_formateada = formatear_fecha(apuesta.get('fecha_realizada', 'No disponible'))

        mensaje = (
            f"{separador('APUESTA COMBINADA')}"
            f"🎰 <b>Tipo:</b> <code>COMBINADA ({len(apuesta.get('selecciones', []))} selecciones)</code>\n"
            f"👤 <b>Usuario:</b> <code>{apuesta['usuario_id']}</code>\n"
            f"📅 <b>Fecha:</b> <code>{fecha_formateada}</code>\n"
            f"💵 <b>Monto:</b> <code>{apuesta.get('monto', 'N/A')} CUP</code>\n"
            f"{origen_line}\n"
            f"📊 <b>Cuota Total:</b> <code>{apuesta.get('cuota', 'N/A')}</code>\n"
            f"💰 <b>Ganancia:</b> <code>{apuesta.get('ganancia', 'N/A')} CUP</code>\n"
            f"🔄 <b>Estado:</b> <code>{apuesta.get('estado', 'N/A')}</code>\n\n"
            f"<b>📌 SELECCIÓN DE ESTE EVENTO:</b>\n"
            f"<pre>" + "\n".join(selecciones_info) + "</pre>\n"
            f"{separador()}"
        )

        keyboard = [
            [
                InlineKeyboardButton("❌ Eliminar", callback_data=f"eliminar_{apuesta['fecha_realizada']}"),
                InlineKeyboardButton("🔄 Reembolsar", callback_data=f"reembolsar_{apuesta['fecha_realizada']}")
            ],
            [
                InlineKeyboardButton("✅ Ganada", callback_data=f"ganada_{apuesta['fecha_realizada']}"),
                InlineKeyboardButton("❌ Perdida", callback_data=f"perdida_{apuesta['fecha_realizada']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)
     
#Rembolsar apuesta individual 
async def reembolsar_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    async with lock_data:
        query = update.callback_query
        fecha_realizada = query.data.split("_")[1]  # Obtener la fecha_realizada desde el callback_data

        try:
            # Cargar las apuestas actuales
            apuestas = await cargar_apuestas()
            usuarios_data = await load_data()

            # Buscar la apuesta correspondiente
            apuesta = next((a for a in apuestas if a["fecha_realizada"] == fecha_realizada), None)
            if not apuesta:
                await query.answer("⚠️ Apuesta no encontrada.", show_alert=True)
                return

            # Obtener el usuario y montos
            usuario_id = apuesta["usuario_id"]
            monto_bono = apuesta.get("bono", 0)
            monto_balance = apuesta.get("balance", 0)

            # Reembolsar al usuario
            if usuario_id in usuarios_data["usuarios"]:
                usuarios_data["usuarios"][usuario_id]["Balance"] += monto_balance
                if usuario_id in usuarios_data["Bono_apuesta"]:
                    usuarios_data["Bono_apuesta"][usuario_id]["Bono"] += monto_bono

            # Actualizar el estado de la apuesta
            apuesta["estado"] = "🔄 Reembolso"

            # Guardar los cambios
           

            # Notificar al usuario con mejor formato
            try:
                await context.bot.send_message(
                    chat_id=usuario_id,
                    text=f"""
<b>🔄 REEMBOLSO DE APUESTA 🔄</b>

<b>⚽ Evento:</b>
┌ 🏆 <b>Liga:</b> {apuesta.get('liga', 'No especificada')}
└ ⚔️ <b>Partido:</b> {apuesta['partido']}

<b>💰 Montos Reembolsados:</b>
┌ 🎁 <b>Bono:</b> <code>{monto_bono}</code> CUP
└ 💰 <b>Balance:</b> <code>{monto_balance}</code> CUP

<b>🏦 Saldo Actualizado:</b>
┌ 💰 <b>Balance Total:</b> <code>{usuarios_data['usuarios'][usuario_id]['Balance']}</code> CUP
└ 🎁 <b>Bono Total:</b> <code>{usuarios_data['Bono_apuesta'].get(usuario_id, {}).get('Bono', 0)}</code> CUP

<i>Los fondos han sido devueltos a tu cuenta. ¡Gracias por usar QvaPlay!</i>
                    """,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"⚠️ Error notificando al usuario {usuario_id}: {e}")

            # Notificar al administrador con mejor formato
            mensaje_admin = f"""
<b>📌 APUESTA REEMBOLSADA</b>

<b>👤 Usuario ID:</b> <code>{usuario_id}</code>
<b>📅 Fecha:</b> <code>{fecha_realizada}</code>

<b>⚽ Evento:</b>
┌ 🏆 <b>Liga:</b> {apuesta.get('liga', 'No especificada')}
└ ⚔️ <b>Partido:</b> {apuesta['partido']}

<b>💵 Montos Reembolsados:</b>
┌ 🎁 <b>Bono:</b> <code>{monto_bono}</code> CUP
└ 💰 <b>Balance:</b> <code>{monto_balance}</code> CUP

<b>🔄 Estado:</b> {apuesta['estado']}
            """
            await query.message.reply_text(mensaje_admin, parse_mode="HTML")

            # Eliminar el mensaje original
            await query.message.delete()
            
        except Exception as e:
            print(f"⚠️ Error al reembolsar la apuesta: {e}")
            await query.answer("❌ Error al procesar el reembolso. Inténtalo de nuevo.", show_alert=True)
        
                    
#pagar apuesta individual 
async def ganada_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    async with lock_data:
        query = update.callback_query
        fecha_realizada = query.data.split("_")[1]  # Obtener la fecha_realizada desde el callback_data

        try:
            # Cargar las apuestas actuales
            apuestas = await cargar_apuestas()
            usuarios_data = await load_data()

            # Buscar la apuesta correspondiente
            apuesta = next((a for a in apuestas if a["fecha_realizada"] == fecha_realizada), None)
            if not apuesta:
                await query.answer("⚠️ Apuesta no encontrada.")
                return

            # Obtener el usuario y montos
            usuario_id = apuesta["usuario_id"]
            monto_bono = apuesta.get("bono", 0)
            monto_balance = apuesta.get("balance", 0)
            cuota = apuesta.get("cuota", 1)

            # Calcular ganancias
            ganancia_bono = monto_bono * (cuota - 1)
            ganancia_balance = monto_balance * (cuota - 1)

            # Actualizar saldos
            if usuario_id in usuarios_data["Bono_apuesta"]:
                usuarios_data["Bono_apuesta"][usuario_id]["Bono"] += monto_bono  # Devuelve bono apostado
                usuarios_data["Bono_apuesta"][usuario_id]["Bono_retirable"] += ganancia_bono
            usuarios_data["usuarios"][usuario_id]["Balance"] += monto_balance + ganancia_balance

            # Actualizar el estado de la apuesta
            apuesta["estado"] = "✅ Ganada"

            # Guardar los cambios
           

            # Notificar al usuario con mejor formato
            try:
                await context.bot.send_message(
                    chat_id=usuario_id,
                    text=f"""
<b>🎉 ¡FELICIDADES! APUESTA GANADA 🎉</b>

<b>📌 Detalles del Evento:</b>
┌ 🏆 <b>Liga:</b> {apuesta['liga']}
├ ⚽ <b>Partido:</b> {apuesta['partido']}
└ 📈 <b>Cuota:</b> <code>{cuota}</code>

<b>💰 Monto Apostado:</b>
┌ 🎁 <b>Bono:</b> <code>{monto_bono}</code> CUP
└ 💰 <b>Balance:</b> <code>{monto_balance}</code> CUP

<b>💸 Ganancias Obtenidas:</b>
┌ 🎁 <b>Bono Retirable:</b> <code>+{ganancia_bono}</code> CUP
└ 💰 <b>Balance:</b> <code>+{ganancia_balance}</code> CUP

<b>🏦 Nuevos Saldos:</b>
┌ 🎁 <b>Bono Total:</b> <code>{usuarios_data['Bono_apuesta'][usuario_id]['Bono']}</code> CUP
└ 💰 <b>Balance Total:</b> <code>{usuarios_data['usuarios'][usuario_id]['Balance']}</code> CUP

<i>¡Sigue apostando con responsabilidad! 🚀</i>
                    """,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"⚠️ Error notificando al usuario {usuario_id}: {e}")

            # Notificar al administrador con mejor formato
            mensaje_admin = f"""
<b>📌 APUESTA MARCADA COMO GANADA</b>

<b>👤 Usuario ID:</b> <code>{usuario_id}</code>
<b>📅 Fecha:</b> <code>{fecha_realizada}</code>

<b>⚽ Evento:</b>
┌ 🏆 <b>Liga:</b> {apuesta['liga']}
└ ⚔️ <b>Partido:</b> {apuesta['partido']}

<b>💵 Montos:</b>
┌ 🎁 <b>Bono:</b> <code>{monto_bono}</code> CUP
└ 💰 <b>Balance:</b> <code>{monto_balance}</code> CUP

<b>💰 Ganancias:</b>
┌ 🎁 <b>Bono Retirable:</b> <code>+{ganancia_bono}</code> CUP
└ 💰 <b>Balance:</b> <code>+{ganancia_balance}</code> CUP

<b>✅ Estado:</b> {apuesta['estado']}
            """
            await query.message.reply_text(mensaje_admin, parse_mode="HTML")

            # Eliminar el mensaje original
            await query.message.delete()
            
        except Exception as e:
            print(f"⚠️ Error al marcar la apuesta como ganada: {e}")
            await query.answer("❌ Error al procesar la apuesta. Inténtalo de nuevo.", show_alert=True)
        
              
#apuesta perdida individual 
async def perdida_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    fecha_realizada = query.data.split("_")[1]  # Obtener la fecha_realizada desde el callback_data

    try:
        # Cargar las apuestas actuales
        apuestas = await cargar_apuestas()
        usuarios_data = await load_data()

        # Buscar la apuesta correspondiente
        apuesta = next((a for a in apuestas if a["fecha_realizada"] == fecha_realizada), None)
        if not apuesta:
            await query.answer("⚠️ Apuesta no encontrada.")
            return

        # Obtener el usuario
        usuario_id = apuesta["usuario_id"]

        # Actualizar el estado de la apuesta
        apuesta["estado"] = "❌ Perdida"

        # Guardar los cambios
        await guardar_apuestas(apuestas)

        # Notificar al usuario
        try:
            await context.bot.send_message(
                chat_id=usuario_id,
                text=f"❌ APUESTA PERDIDA ❌\n"
                     f"🏆 {apuesta['liga']}\n"
                     f"⚽ {apuesta['partido']}\n"
                     f"💰 Monto: {apuesta.get('monto', 'N/A')} CUP\n"
                     f"💳 Balance actual: {usuarios_data['usuarios'][usuario_id]['Balance']} CUP"
            )
        except Exception as e:
            print(f"⚠️ Error notificando al usuario {usuario_id}: {e}")

        # Notificar al administrador
        mensaje_admin = (
            f"📝 <blockquote>Apuesta Marcada como Perdida</blockquote>\n"
            f"👤 <b>ID Usuario:</b> <code>{usuario_id}</code>\n"
            f"⚔️ <b>Partido:</b> {apuesta['partido']}\n"
            f"💵 <b>Monto Apostado:</b> {apuesta.get('monto', 'N/A')} CUP\n"
            f"❌ <b>Estado Actual:</b> {apuesta['estado']}"
        )
        await query.message.reply_text(mensaje_admin, parse_mode="HTML")

        # Eliminar el mensaje original
        await query.message.delete()
    except Exception as e:
        print(f"⚠️ Error al marcar la apuesta como perdida: {e}")
        await query.answer("Hubo un error al marcar la apuesta como perdida. Inténtalo de nuevo.")

    
     
async def mostrar_futbol_live(update: Update, context: CallbackContext):
    try:
        callback_data = update.callback_query.data
        context.user_data["betting"] = "LIVE"

        # Manejar paginación
        if callback_data.startswith("paginalive_"):
            page = int(callback_data.replace("paginalive_", ""))
            context.user_data["page"] = page  # Guardar la página actual
            deporte = context.user_data.get("deporte_actual")  # Recuperar el deporte guardado
        else:
            context.user_data["page"] = 0  # Inicializar en la primera página
            deporte = callback_data.replace("deporte_", "")  # Extraer el deporte
            context.user_data["deporte_actual"] = deporte  # Guardarlo correctamente
            page = 0

        try:
            ligas = await obtener_ligas(deporte)  # Buscar ligas en la API
        except Exception as e:
            print(f"Error al obtener las ligas de {deporte}: {e}")
            ligas = None

        mensaje = "🔽 Selecciona la liga para la que deseas apostar:"

        if not ligas:
            mensaje = "❌ No se pudieron obtener las ligas en este momento."
            keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")]]
        else:
            # Paginación
            ligas_por_pagina = 20
            inicio = page * ligas_por_pagina
            fin = inicio + ligas_por_pagina
            ligas_pagina = ligas[inicio:fin]

            keyboard = []
            fila = []

            for liga in ligas_pagina:
                try:
                    nombre_liga = liga.get('title', liga.get('name', 'Liga sin nombre'))
                    clave_liga = liga.get('key', liga.get('id', 'Liga sin clave'))

                    pais = detectar_pais(nombre_liga)
                    bandera = obtener_bandera(pais) if pais else "🏆"

                    if pais:
                        for nombre in paises[pais]:
                            nombre_liga = nombre_liga.replace(nombre, pais)

                    texto_boton = f"{bandera} {nombre_liga}"
                    fila.append(InlineKeyboardButton(texto_boton, callback_data=f"ligaslive_{clave_liga}"))

                    if len(fila) == 2:
                        keyboard.append(fila)
                        fila = []
                except Exception as e:
                    print(f"Error al procesar la liga: {e}")
                    continue

            if fila:
                keyboard.append(fila)

            # Botones de paginación
            navegacion = []
            if page > 0:
                navegacion.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"paginalive_{page - 1}"))
            if fin < len(ligas):
                navegacion.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"paginalive_{page + 1}"))

            if navegacion:
                keyboard.append(navegacion)

            # Botón para volver al menú principal
            keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(mensaje, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        print(f"Error general en mostrar_futbol_live: {e}")
        await update.callback_query.message.edit_text("❌ Ocurrió un error inesperado.",
                                                      reply_markup=InlineKeyboardMarkup([
                                                          [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")]
                                                      ]), parse_mode="HTML")
                                                      
async def manejar_navegacion_ligas_live(update: Update, context: CallbackContext):
    try:
        callback_data = update.callback_query.data
        deporte = context.user_data.get("deporte", "")

        # Extraer el número de página desde el callback_data
        if callback_data.startswith("paginalive_"):
            page = int(callback_data.replace("paginalive_", ""))
            context.user_data["page"] = page  # Actualizar la página actual
            await mostrar_futbol_live(update, context)  # Mostrar la página correspondiente
    except Exception as e:
        print(f"Error en manejar_navegacion_ligas_live: {e}")
        await update.callback_query.answer("❌ Ocurrió un error al navegar.", show_alert=True)                                                      
                
async def obtener_scores_evento(event_id, sport_key):
    global api_index
    if api_index >= len(API_KEYS):
        return "❌ No hay claves API disponibles."

    api_key = await obtener_api()
    url_scores = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/"
    
    params = {"apiKey": api_key, "daysFrom": 1}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url_scores, params=params) as response:
                if response.status == 200:
                    eventos = await response.json()
                   
                    evento = next((e for e in eventos if e["id"] == event_id), None)
                    if not evento:
                        print(f"⚠️ No se encontró el evento con ID {event_id}")
                        return "❌ No se encontró el evento."

                    

                    home_team = evento.get("home_team", "Desconocido")
                    away_team = evento.get("away_team", "Desconocido")

                    if "scores" in evento and isinstance(evento["scores"], list):
                        scores = {s["name"]: s["score"] for s in evento["scores"]}
                    else:
                        scores = {home_team: "Desconocido", away_team: "Desconocido"}

                    return scores

                elif response.status == 401:
                    print(f"❌ Créditos agotados para la clave API: {api_key}")
                    
                    return await obtener_scores_evento(event_id, sport_key)

                else:
                    print(f"❌ Error {response.status}: {await response.text()}")
                    return f"❌ Error {response.status} al obtener el score."

    except Exception as e:
        print(f"⚠️ Error en la solicitud: {e}")
        return "❌ Ocurrió un error inesperado. Por favor, contacta a un administrador."

async def mostrar_eventos_live(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        callback_data = query.data
       
        sport_key = callback_data.replace("ligaslive_", "")
     
        eventos = await obtener_eventos_liga(sport_key, context)
       
        if isinstance(eventos, str):
            print(f"[ERROR] Error al obtener eventos: {eventos}")
            await query.answer(eventos)
            return

        if not isinstance(eventos, list):
            print(f"[ERROR] Respuesta inesperada de la API: {eventos}")
            await query.answer("❌ Error al obtener eventos.")
            return

        ahora = datetime.now(pytz.utc)
        
        # Filtrar eventos en vivo (eventos que ya han comenzado pero con menos de 90 minutos transcurridos)
        eventos_filtrados = []
        for evento in eventos:
            try:
                hora_evento = datetime.fromisoformat(evento['commence_time'].replace("Z", "+00:00")).astimezone(pytz.utc)
                context.user_data["time_inicio"] = hora_evento.astimezone(cuba_tz).strftime("%d/%m/%Y %H:%M:%S")
                
                tiempo_transcurrido = (ahora - hora_evento).total_seconds() / 60  # en minutos
                
                if 0 <= tiempo_transcurrido < 90:  # Menos de 90 minutos
                    eventos_filtrados.append(evento)
            except (KeyError, ValueError) as e:
                print(f"[ERROR] Error al procesar el evento {evento.get('id', 'desconocido')}: {e}")
                continue

        eventos_filtrados.sort(key=lambda x: datetime.fromisoformat(x['commence_time'].replace("Z", "+00:00")))
    
        if not eventos_filtrados:
            await query.answer(text="🙁 No hay eventos en vivo para la liga seleccionada.")
            return

        texto_eventos = f"<b>📡 Eventos en vivo - {sport_key.replace('_', ' ').title()}</b>\n\n"
        
        for evento in eventos_filtrados[:3]:  # Mostrar máximo 3 eventos
            try:
                team1 = evento['home_team']
                team2 = evento['away_team']
                hora_evento = datetime.fromisoformat(evento['commence_time'].replace("Z", "+00:00")).astimezone(cuba_tz)
                hora_formateada = hora_evento.strftime("%d/%m %H:%M")
                
                tiempo_transcurrido = (ahora - hora_evento).total_seconds() / 60
                
                # Estado genérico para cualquier deporte
                if tiempo_transcurrido < 0:
                    estado = "🕒 Por comenzar"
                else:
                    estado = f"⏱️ En juego ({int(tiempo_transcurrido)}')"

                texto_eventos += (
                    f"⚔️ <b>{team1} vs {team2}</b>\n"
                    f"🕰️ <i>{hora_formateada} (Hora Cuba)</i>\n"
                    f"📊 {estado}\n"
                    f"--------------------------------\n"
                )
            except KeyError as e:
                print(f"[ERROR] Falta la clave {e} en el evento {evento.get('id', 'desconocido')}")
                continue

        # Construir el teclado con botones para cada evento
        keyboard = []
        fila = []
        for evento in eventos_filtrados:
            try:
                team1 = evento['home_team']
                team2 = evento['away_team']
                event_id = evento['id']
                texto_boton = f"{team1} vs {team2}"
                print(f"[DEBUG] Creando botón para evento {event_id}: {texto_boton}")
                fila.append(InlineKeyboardButton(texto_boton, callback_data=f"mercado_vivo_{event_id}"))
                if len(fila) == 2:
                    keyboard.append(fila)
                    fila = []
            except KeyError as e:
                print(f"[ERROR] Falta la clave {e} al crear botón para el evento")
                continue

        if fila:
            keyboard.append(fila)

        # Botón para volver al menú anterior
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuesta")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Editar el mensaje original con el texto y el teclado creado
        print("[DEBUG] Enviando mensaje editado con eventos en vivo.")
        await query.edit_message_text(text=texto_eventos, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        print(f"[EXCEPTION] Error en mostrar_eventos_live: {e}")
        await query.answer("❌ Ocurrió un error inesperado.", show_alert=True)
async def mostrar_mercados_en_vivo(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        if not query.data.startswith("mercado_vivo_"):
            await query.answer("❌ Acción no válida")
            return

        event_id = query.data.replace("mercado_vivo_", "")
        sport_key = context.user_data.get("sport_key", "")
        
        # Verificar rate limiting
        last_update = context.user_data.get(f"last_update_{event_id}")
        if last_update and (datetime.now() - last_update).total_seconds() < 10:
            await query.answer("⏳ Espera 10 segundos entre actualizaciones", show_alert=True)
            return
        
        context.user_data[f"last_update_{event_id}"] = datetime.now()

        # Obtener datos del evento
        evento = await obtener_mercados_evento(event_id, sport_key)
        if isinstance(evento, str):  # Si hay error
            await query.answer(evento)
            return
            
        # Guardar datos completos del evento (EXACTAMENTE IGUAL QUE EN mostrar_mercados_evento)
        saved_event_id = guardar_datos_evento(context, evento)
        
        # Estructura IDÉNTICA a mostrar_mercados_evento
        context.user_data["current_event"] = {
            "event_id": saved_event_id,
            "sport_key": sport_key,
            "sport_title": evento.get('sport_title', ''),
            "home_team": evento.get('home_team', 'Local'),
            "away_team": evento.get('away_team', 'Visitante'),
            "commence_time": evento.get('commence_time', ''),
            "loaded_markets": ["h2h", "draw_no_bet", "spreads"],  # Solo estos 3 mercados
            "complete_data": evento
        }

        # Obtener hora y marcador (para mostrar en vivo)
        hora_actual = datetime.now().strftime("%I:%M %p")
        nombre_local = evento.get("home_team", "Local")
        nombre_visitante = evento.get("away_team", "Visitante")

        # Obtener scores en vivo
        scores = await obtener_scores_evento(event_id, sport_key)
        marcador_local = scores.get(nombre_local, "0")
        marcador_visitante = scores.get(nombre_visitante, "0")

        # Calcular tiempo transcurrido
        hora_evento = evento.get("commence_time")
        ahora = datetime.now(pytz.utc)
        tiempo_transcurrido = 0

        if hora_evento:
            hora_evento = datetime.strptime(hora_evento, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
            tiempo_transcurrido = (ahora - hora_evento).total_seconds() / 60

        if tiempo_transcurrido < 0:
            estado = "🕒 Por comenzar"
        elif tiempo_transcurrido <= 90:
            estado = f"⏱️ En juego ({int(tiempo_transcurrido)}')"
        else:
            estado = "🏁 Finalizando"

        # Construir mensaje (con información en vivo)
        texto_evento = f"""
<blockquote>{nombre_local} 🆚 {nombre_visitante}</blockquote>
⚽ <b>Marcador:</b> {marcador_local} - {marcador_visitante}
⏳ <b>Estado:</b> {estado}
🔄 <i>Última actualización: {hora_actual}</i>

🔢 <i>Selecciona un mercado:</i>
"""

        keyboard = []
        apuestas = {}

        # Procesar SOLO los 3 mercados que necesitamos
        mercados_permitidos = ["h2h", "draw_no_bet", "spreads"]
        
        for bookmaker in evento.get("bookmakers", []):
            if bookmaker["title"] == "Bovada":
                for market in bookmaker["markets"]:
                    if market["key"] in mercados_permitidos:
                        apuestas[market["key"]] = market["outcomes"]

        # Organización IDÉNTICA a mostrar_mercados_evento
        # 1. Mercado h2h (Ganador del Partido)
        if "h2h" in apuestas:
            grupo_id = f"grp_{event_id[:6]}_h2h"
            context.user_data[grupo_id] = {
                "type": "market_group",
                "event_id": event_id,
                "sport_key": sport_key,
                "market_key": "h2h",
                "outcomes": apuestas["h2h"],
                "expires": datetime.now() + timedelta(minutes=5)
            }

            keyboard.append([InlineKeyboardButton(
                f"{CONFIG_MERCADOS['h2h']['emoji']} {CONFIG_MERCADOS['h2h']['nombre']}",
                callback_data=f"ver_{grupo_id}"
            )])

            # Botones de opciones (EXACTAMENTE IGUAL)
            opciones_h2h = []
            for i, outcome in enumerate(apuestas["h2h"]):
                opcion_id = f"opc_{hashlib.md5(f'{grupo_id}_{i}'.encode()).hexdigest()[:8]}"
                
                context.user_data[opcion_id] = {
                    "type": "market_outcome",
                    "event_id": event_id,
                    "sport_key": sport_key,
                    "market_key": "h2h",
                    "outcome_index": i,
                    "outcome_data": outcome,
                    "expires": datetime.now() + timedelta(minutes=5)
                }

                nombre_opcion = CONFIG_MERCADOS["h2h"]["formato_nombre"](outcome, nombre_local, nombre_visitante)
                opciones_h2h.append(InlineKeyboardButton(
                    f"{nombre_opcion} {outcome['price']}💰",
                    callback_data=f"sel_{opcion_id}"
                ))

            # Misma organización de botones
            for i in range(0, len(opciones_h2h), 3):
                keyboard.append(opciones_h2h[i:i+3])

        # 2. Mercado draw_no_bet (Empate no Bet)
        if "draw_no_bet" in apuestas:
            grupo_id = f"grp_{event_id[:6]}_dnb"
            context.user_data[grupo_id] = {
                "type": "market_group",
                "event_id": event_id,
                "sport_key": sport_key,
                "market_key": "draw_no_bet",
                "outcomes": apuestas["draw_no_bet"],
                "expires": datetime.now() + timedelta(minutes=5)
            }

            keyboard.append([InlineKeyboardButton(
                f"{CONFIG_MERCADOS['draw_no_bet']['emoji']} {CONFIG_MERCADOS['draw_no_bet']['nombre']}",
                callback_data=f"ver_{grupo_id}"
            )])

            # Botones de opciones (IGUAL QUE EN mostrar_mercados_evento)
            opciones_dnb = []
            for i, outcome in enumerate(apuestas["draw_no_bet"]):
                opcion_id = f"opc_{hashlib.md5(f'{grupo_id}_{i}'.encode()).hexdigest()[:8]}"
                
                context.user_data[opcion_id] = {
                    "type": "market_outcome",
                    "event_id": event_id,
                    "sport_key": sport_key,
                    "market_key": "draw_no_bet",
                    "outcome_index": i,
                    "outcome_data": outcome,
                    "expires": datetime.now() + timedelta(minutes=5)
                }

                nombre_opcion = CONFIG_MERCADOS["draw_no_bet"]["formato_nombre"](outcome, nombre_local, nombre_visitante)
                opciones_dnb.append(InlineKeyboardButton(
                    f"{nombre_opcion} {outcome['price']}💰",
                    callback_data=f"sel_{opcion_id}"
                ))

            for i in range(0, len(opciones_dnb), 2):
                keyboard.append(opciones_dnb[i:i+2])

        # 3. Mercado spreads (Hándicap)
        if "spreads" in apuestas:
            grupo_id = f"grp_{event_id[:6]}_spr"
            context.user_data[grupo_id] = {
                "type": "market_group",
                "event_id": event_id,
                "sport_key": sport_key,
                "market_key": "spreads",
                "outcomes": apuestas["spreads"],
                "expires": datetime.now() + timedelta(minutes=5)
            }

            keyboard.append([InlineKeyboardButton(
                f"{CONFIG_MERCADOS['spreads']['emoji']} {CONFIG_MERCADOS['spreads']['nombre']}",
                callback_data=f"ver_{grupo_id}"
            )])

            # Botones de opciones (MISMA ESTRUCTURA)
            opciones_spr = []
            for i, outcome in enumerate(apuestas["spreads"]):
                opcion_id = f"opc_{hashlib.md5(f'{grupo_id}_{i}'.encode()).hexdigest()[:8]}"
                
                context.user_data[opcion_id] = {
                    "type": "market_outcome",
                    "event_id": event_id,
                    "sport_key": sport_key,
                    "market_key": "spreads",
                    "outcome_index": i,
                    "outcome_data": outcome,
                    "expires": datetime.now() + timedelta(minutes=5)
                }

                nombre_opcion = CONFIG_MERCADOS["spreads"]["formato_nombre"](outcome, nombre_local, nombre_visitante)
                opciones_spr.append(InlineKeyboardButton(
                    f"{nombre_opcion} {outcome['price']}💰",
                    callback_data=f"sel_{opcion_id}"
                ))

            for i in range(0, len(opciones_spr), 2):
                keyboard.append(opciones_spr[i:i+2])

        # Botón de volver (IGUAL QUE EN mostrar_mercados_evento)
        callback_volver = f"ligaslive_{sport_key}"
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=callback_volver)])

        # Botón de actualizar (específico para live)
        keyboard.append([InlineKeyboardButton("🔄 Actualizar", callback_data=f"mercado_vivo_{event_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Editar mensaje (MISMO MÉTODO)
        await query.edit_message_text(
            text=texto_evento,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error en mostrar_mercados_en_vivo: {str(e)}")
        if query:
            await query.edit_message_text(
                text="❌ Ocurrió un error al mostrar los mercados en vivo",
                parse_mode="HTML"
            )

async def handle_combinadas_callback(update: Update, context: CallbackContext):
    """Maneja el callback para apuestas combinadas."""
    context.user_data["betting"] = "COMBINADA"
    
    await mostrar_deportes(update, context)

async def handle_prepartido_callback(update: Update, context: CallbackContext):
    """Maneja el callback para apuestas combinadas."""
    context.user_data["betting"] = "PREPARTIDO"
    
    await mostrar_deportes(update, context)
    
async def handle_vivo_callback(update: Update, context: CallbackContext):
    """Maneja el callback para apuestas combinadas."""
    context.user_data["betting"] = "LIVE"
    
    await mostrar_deportes(update, context)
async def seleccion_apuesta_combinada(update: Update, context: CallbackContext):
    """Maneja la adición de apuestas individuales a una combinada con formato estandarizado"""
    
    try:
        # Verificar datos esenciales
        if "apuesta_seleccionada" not in context.user_data:
            print("❌ No hay apuesta seleccionada en el contexto")
            await update.callback_query.answer("Error: No hay apuesta para agregar", show_alert=True)
            return

        apuesta_actual = context.user_data["apuesta_seleccionada"]
        current_event = context.user_data.get("current_event", {})
        
        # Usar apuesta_actual como fallback si current_event está vacío
        if not current_event:
            current_event = {
                "sport_key": apuesta_actual.get("sport_key"),
                "sport_title": apuesta_actual.get("sport_title"),
                "commence_time": apuesta_actual.get("commence_time"),
                # Agrega otros campos necesarios
            }
            context.user_data["current_event"] = current_event  # Actualizar el contexto        
        
        # Validar campos mínimos
        campos_requeridos = ["event_id", "tipo_apuesta", "seleccion", "cuota", "home_team", "away_team"]
        if not all(campo in apuesta_actual for campo in campos_requeridos):
            print(f"❌ Faltan campos: {[c for c in campos_requeridos if c not in apuesta_actual]}")
            await update.callback_query.answer("Error: Datos incompletos", show_alert=True)
            return

        # Verificar si el evento ya ha comenzado o ha pasado
        commence_time_str = current_event.get("commence_time", "")
        if commence_time_str:
            try:
                # Convertir el commence_time a datetime (ajusta el formato según tus datos)
                commence_time = datetime.strptime(commence_time_str, "%Y-%m-%dT%H:%M:%SZ")
                current_time = datetime.utcnow()
                
                if commence_time <= current_time:
                    print(f"⚠️ Evento ya comenzó o pasó: {commence_time_str}")
                    await update.callback_query.answer("La selección ha expirado (el evento ya comenzó)", show_alert=True)
                    return
            except ValueError:
                pass

        
        # Obtener nombre de mercado estandarizado
        market_key = apuesta_actual["tipo_apuesta"]
        config_mercado = CONFIG_MERCADOS.get(market_key, {})
        nombre_mercado = config_mercado.get("nombre", market_key)
        
        # Obtener nombres de equipos
        home_team = apuesta_actual['home_team']
        away_team = apuesta_actual['away_team']
        seleccion_original = apuesta_actual['seleccion']
        
        # REEMPLAZO SIMPLE DE HOME/AWAY MANTENIENDO TODO LO DEMÁS
        seleccion_actualizada = seleccion_original
        if 'Home' in seleccion_original:
            seleccion_actualizada = seleccion_original.replace('Home', home_team)
        elif 'Away' in seleccion_original:
            seleccion_actualizada = seleccion_original.replace('Away', away_team)
        
        # ACTUALIZAR EL CONTEXTO con la selección formateada
        apuesta_actual['seleccion'] = seleccion_actualizada
        seleccion = apuesta_actual['seleccion']  # Usamos la versión actualizada

        # Formatear descripción con la selección modificada
        descripcion = CONFIG_MERCADOS[market_key]["formato_nombre"](
            {"name": seleccion, "point": apuesta_actual.get("point")},
            home_team,
            away_team
        )

        # Resto del código original SIN MODIFICAR
        if "apuestas_combinadas" not in context.user_data:
            context.user_data["apuestas_combinadas"] = []

        ahora = datetime.now().timestamp()
        context.user_data["apuestas_combinadas"] = [
            a for a in context.user_data["apuestas_combinadas"] 
            if ahora - a.get("timestamp", 0) < 1800
        ]

        # Verificar si ya existe alguna apuesta para este mismo partido (event_id)
        for apuesta_existente in context.user_data["apuestas_combinadas"]:
            if apuesta_existente["event_id"] == apuesta_actual["event_id"]:
                
                await update.callback_query.message.reply_text("⚠️Ya tienes una selección en este partido")
                print("⚠️ Apuesta duplicada detectada para el mismo partido")        
                return

        if len(context.user_data["apuestas_combinadas"]) >= 8:
            await update.callback_query.answer("Límite: Máximo 8 selecciones", show_alert=True)
            return

        nueva_apuesta = {
            "event_id": apuesta_actual["event_id"],
            "sport_key": current_event.get("sport_key", ""),
            "home_team": home_team,
            "away_team": away_team,
            "evento": f"{home_team} vs {away_team}",
            "market_key": market_key,
            "market": nombre_mercado,
            "descripcion": descripcion,
            "cuota": float(apuesta_actual["cuota"]),
            "point": apuesta_actual.get("point"),
            "timestamp": ahora,
            "liga": current_event.get("sport_title", "Desconocido"),
            "commence_time": current_event.get("commence_time", "")
        }

        context.user_data["apuestas_combinadas"].append(nueva_apuesta)
        print(f"📥 Apuesta agregada. Total: {len(context.user_data['apuestas_combinadas'])}")

        cuotas = [a["cuota"] for a in context.user_data["apuestas_combinadas"]]
        context.user_data["cuota_combinada"] = calcular_cuota_combinada(cuotas)

        await mostrar_apuestas_combinadas(update, context)

    except Exception as e:
        print(f"🔥 Error crítico: {str(e)}")
        traceback.print_exc()
        await update.callback_query.answer("❌ Error al procesar", show_alert=True)

def calcular_cuota_combinada(cuotas: list) -> float:
    """Calcula la cuota combinada con ajustes inteligentes, aplicando límites antes del cálculo"""

    n = len(cuotas)
    if n == 0:
        return 1.0

    # Ajustar individualmente las cuotas al rango [0.01, 50.0]
    cuotas_ajustadas = [min(max(c, 0.01), 50.0) for c in cuotas]

    # 1. Probabilidad implícita base
    prob_product = math.prod(1 / c for c in cuotas_ajustadas)

    # 2. Factores de ajuste
    factor_n = 1.0 - (0.02 * n)
    factor_dispersion = 1.0 - (0.01 * (max(cuotas_ajustadas) - min(cuotas_ajustadas))) if n > 1 else 1.0
    compression = min(max(factor_n * factor_dispersion, 0.85), 0.98)

    # 3. Margen dinámico
    margen = 1.03 + (n * 0.01)

    # 4. Cálculo final con reducción del 1%
    cuota_ajustada = 1 / ((prob_product ** compression) * margen)
    cuota_final = cuota_ajustada * 0.99

    # Limitar resultado final también entre [0.01, 50.0]
    cuota_final = min(max(cuota_final, 0.01), 50.0)

    return round(cuota_final, 2)

async def mostrar_apuestas_combinadas(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer('✅ Selección agregada a tu combinada')
    chat_id = update.effective_chat.id
    apuestas = context.user_data.get("apuestas_combinadas", [])
    cuota_total = context.user_data.get("cuota_combinada", 1.0)

    # Construir mensaje con formato mejorado
    mensaje = "<blockquote>🎲 APUESTA COMBINADA 🎲</blockquote>\n\n"
    mensaje += "📦 <b><u>Selecciones actuales:</u></b>\n\n"
    
    for idx, apuesta in enumerate(apuestas, 1):
        point_info = f" ({apuesta['point']})" if apuesta.get("point") else ""
        emoji_mercado = CONFIG_MERCADOS.get(apuesta["market_key"], {}).get("emoji", "🎯")
        
        mensaje += (
            f"<pre>▫️ <b>Apuesta {idx}:</b>\n"
            f"├─ {emoji_mercado} <b>MERCADO:</b> {apuesta['market']}{point_info}\n"
            f"├─ ⚽ <b>PARTIDO:</b> {apuesta['evento']}\n"
            f"├─ ❤️ <b>SELECCIÓN:</b> {apuesta['descripcion']}\n"
            f"└─ 💰 <b>CUOTA:</b> {apuesta['cuota']:.2f}</pre>\n"
            "───────────────────────────────────────\n"
        )
    
    mensaje += f"\n🧮 <b>Cuota Total:</b> <code>{cuota_total:.2f}</code>\n\n"
    mensaje += "🔰 <i>Selecciona una acción:</i>"

    # Construir teclado
    teclado = []
    
    # Botones para eliminar apuestas individuales
    for i in range(len(apuestas)):
        teclado.append([InlineKeyboardButton(
            f"🗑️ Eliminar Apuesta {i+1}", 
            callback_data=f"remove_apuesta_{i}"
        )])
    
    # Botón de confirmación o advertencia
    if len(apuestas) < 3:
        teclado.append([InlineKeyboardButton(
            f"⚠️ Mínimo 3 selecciones ({len(apuestas)}/3)", 
            callback_data="no_action"
        )])
    else:
        teclado.append([InlineKeyboardButton(
            "✅ Confirmar Combinada", 
            callback_data="procesar_payment_combinada"
        )])
    
    # Botones de navegación
    teclado.append([
        InlineKeyboardButton("➕ Seguir agregando", callback_data="handle_combinadas_callback"),
        InlineKeyboardButton("❌ Cancelar todo", callback_data="cancelar_combinada")
    ])

    # Manejo del mensaje (editar o enviar nuevo)
    message_id = context.user_data.get("combinada_message_id")
    
    try:
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode="HTML"
            )
        else:
            new_message = await context.bot.send_message(
                chat_id=chat_id,
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode="HTML"
            )
            context.user_data["combinada_message_id"] = new_message.message_id
    except Exception as e:
        print(f"Error al mostrar combinada: {e}")
        # Fallback: enviar nuevo mensaje
        new_message = await context.bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(teclado),
            parse_mode="HTML"
        )
        context.user_data["combinada_message_id"] = new_message.message_id

async def procesar_payment_combinada(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    apuestas = context.user_data.get("apuestas_combinadas", [])
    
    if not apuestas:
        await query.edit_message_text(text="❌ No hay apuestas para confirmar")
        return
    
    # Obtener datos del usuario desde la base de datos
    user_id = str(update.effective_user.id)
    
    # Obtener datos de usuario y bono
    usuario_data = obtener_registro('usuarios', user_id)
    bono_data = obtener_registro('bono_apuesta', user_id)
    
    if not usuario_data:
        await query.edit_message_text(text="❌ Error al obtener datos de usuario")
        return
    
    # Extraer datos (ajusta los índices según tu estructura de base de datos)
    # Suponiendo: usuario_data = (id, nombre, balance, ...)
    # Suponiendo: bono_data = (id, bono, ...)
    balance = usuario_data[2] if len(usuario_data) > 2 else 0  # Índice 2: balance
    bono = bono_data[1] if bono_data and len(bono_data) > 1 else 0  # Índice 1: bono
    
    # Construir mensaje
    mensaje = (
        "<pre>🔻SELECCIÓN DE PAGO PARA COMBINADA🔻</pre>\n\n"
        f"💰 <b>Balance disponible:</b> <code>{balance}</code> CUP\n"
        f"🎁 <b>Bono disponible:</b> <code>{bono}</code> CUP\n\n"        
    )
    
    # Teclado modificado con sufijo _combinada
    keyboard = [
        [InlineKeyboardButton("🎁 Usar Bono", callback_data="pago_bono_combinada"),
         InlineKeyboardButton("💲 Usar Balance", callback_data="pago_balance_combinada")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_combinada")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
async def manejar_acciones_combinadas(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("remove_apuesta_"):
        indice = int(data.split("_")[-1])
        if 0 <= indice < len(context.user_data["apuestas_combinadas"]):
            del context.user_data["apuestas_combinadas"][indice]
            
            # Recalcular la cuota después de eliminar
            if "apuestas_combinadas" in context.user_data and len(context.user_data["apuestas_combinadas"]) > 0:
                cuotas = [a["cuota"] for a in context.user_data["apuestas_combinadas"]]
                context.user_data["cuota_combinada"] = calcular_cuota_combinada(cuotas)
            else:
                context.user_data["cuota_combinada"] = 1.0  # Resetear si no hay apuestas
            
            await mostrar_apuestas_combinadas(update, context)            
    
    elif data == "procesar_payment_combinada":
        if len(context.user_data["apuestas_combinadas"]) >= 3:
            await procesar_payment_combinada(update, context)
        else:
            await query.answer("⚠️ Mínimo 3 selecciones requeridas", show_alert=True)
    
    elif data == "cancelar_combinada":
        if "apuestas_combinadas" in context.user_data:
            del context.user_data["apuestas_combinadas"]
        await query.delete_message()
        await query.message.reply_text("❌ Apuesta combinada cancelada")
    
    
    
    else:
        await query.answer("❌ Acción no reconocida")


def obtener_descripcion_apuesta(market, outcome, home_team, away_team):
    descripciones = {
        "h2h": lambda: f"{outcome['name']}",
        "btts": lambda: f"Ambos marcan: {outcome['name']}",
        "spreads": lambda: f"Hándicap ({outcome['point']}): {outcome['name']}",
        "totals": lambda: f"Total de goles ({outcome['name']} {outcome['point']})",
        "draw_no_bet": lambda: f"Sin empate: {outcome['name']}"
    }
    return descripciones.get(market, lambda: "Apuesta especial")()


async def handle_pago_combinada(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Esto limpia el estado del botón
    
    # Verificar si seleccionó bono
    if query.data == "pago_bono_combinada":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ <b>Las combinadas solo están disponibles con balance temporalmente.</b>\n\nPronto estarán disponibles con Bono.",
            parse_mode="HTML"
        )
        return  # Salir de la función

    user_id = str(update.effective_user.id)
    
    # Obtener datos desde la base de datos
    usuario_data = obtener_registro('usuarios', user_id)
    bono_data = obtener_registro('bono_apuesta', user_id)
    
    if not usuario_data:
        await query.edit_message_text("❌ Error al cargar datos financieros")
        return
    
    # Extraer datos (ajusta índices según tu estructura)
    balance = usuario_data[2] if len(usuario_data) > 2 else 0  # Índice 2: balance
    bono = bono_data[1] if bono_data and len(bono_data) > 1 else 0  # Índice 1: bono
    
    context.user_data['estado'] = 'esperando_monto_combinada'
    
    # Resto de la lógica para balance...
    metodo_pago = query.data.split("_")[1]
    context.user_data["metodo_pago_combinada"] = metodo_pago
    
    mensaje = (
        "💵 <pre>MONTO PARA COMBINADA</pre>\n\n"
        f"💰 Balance: <code>{balance}</code> CUP\n"
        f"🎁 Bono: <code>{bono}</code> CUP\n\n"
        "📢 Ingresa el monto (límites: 50-300 CUP):\n"
        "Ejemplo: <code>100</code>"
    )
    
    keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_combinada")]]
    
    await query.edit_message_text(
        text=mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard))
    
        
async def manejar_monto_combinada(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    
    # Obtener datos desde la base de datos
    usuario_data = obtener_registro('usuarios', user_id)
    bono_data = obtener_registro('bono_apuesta', user_id)
    
    if not usuario_data:
        await update.message.reply_text("❌ Error al cargar datos de usuario")
        return
    
    try:
        monto = int(update.message.text)
        if monto < 50 or monto > 300:
            await update.message.reply_text("❌ Monto fuera del limite (50-300 CUP)")
            return
    except ValueError:
        await update.message.reply_text("❌ Solo números permitidos")
        return
    
    metodo_pago = context.user_data.get("metodo_pago_combinada")
    if not metodo_pago:
        await update.message.reply_text("❌ Primero selecciona método de pago")
        return
    
    # Extraer datos (ajusta índices según tu estructura)
    balance = usuario_data[2] if len(usuario_data) > 2 else 0  # Índice 2: balance
    bono = bono_data[1] if bono_data and len(bono_data) > 1 else 0  # Índice 1: bono
    
    # Validar fondos
    if (metodo_pago == "bono" and monto > bono) or (metodo_pago == "balance" and monto > balance):
        await update.message.reply_text(f"❌ Fondos insuficientes en {'bono' if metodo_pago == 'bono' else 'balance'}")
        return
    
    context.user_data["monto_combinada"] = monto
    
    # Construir confirmación detallada
    apuestas = context.user_data["apuestas_combinadas"]
    cuota_total = context.user_data["cuota_combinada"]
    
    mensaje = (
        "✅ <b>CONFIRMAR COMBINADA</b>\n\n"
        f"🔢 Selecciones: {len(apuestas)}\n"
        f"💰 Monta: {monto} CUP\n"
        f"📈 Cuota Total: {cuota_total:.2f}\n"
        f"🤑 Ganancia Potencial: {monto * cuota_total:.2f} CUP\n\n"
        "📚 <b>Detalles:</b>\n"
    )
    
    for idx, apuesta in enumerate(apuestas, 1):
        sport_key = apuesta.get("sport_key", "desconocido").split('_')[0]
        deporte_nombre, emoji = deportes_personalizados.get(sport_key, (sport_key, "🏅"))
        
        mensaje += (
            f"\n▫️ <b>Apuesta {idx}:</b>\n"
            f"{emoji} Deporte: {deporte_nombre}\n"
            f"🏆 Evento: {apuesta['evento']}\n"
            f"🎯 Mercado: {apuesta['market'].upper()}\n"
            f"❤️ Favorito: {apuesta['descripcion']}\n"
            f"📈 Cuota: {apuesta['cuota']:.2f}\n"
            "----------------------------------"
        )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_combinada"),
         InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_combinada")]
    ]
    
    await update.message.reply_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    context.user_data["estado"] = None
     
async def confirmar_combinada_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    user_id = str(user.id)

    try:
        await query.answer("⏳ Confirmando combinada...")
        
        # Validación de datos requeridos
        required = ["apuestas_combinadas", "monto_combinada", "metodo_pago_combinada", "cuota_combinada"]
        if any(key not in context.user_data for key in required):
            await query.answer("❌ Error: Datos incompletos", show_alert=True)
            return

        apuestas = context.user_data["apuestas_combinadas"]
        monto = context.user_data["monto_combinada"]
        metodo_pago = context.user_data["metodo_pago_combinada"]
        cuota_total = context.user_data["cuota_combinada"]
        ganancia = monto * cuota_total

        # Obtener datos de usuario desde la base de datos
        usuario_data = obtener_registro('usuarios', user_id)
        bono_data = obtener_registro('bono_apuesta', user_id)

        if not usuario_data:
            await query.answer("❌ Usuario no encontrado", show_alert=True)
            return

        # Validar fondos
        if metodo_pago == "bono":
            if not bono_data or bono_data[1] < monto:  # Suponiendo que bono está en índice 1
                await query.answer("❌ Bono insuficiente", show_alert=True)
                return
        elif metodo_pago == "balance" and usuario_data[2] < monto:  # Suponiendo que balance está en índice 2
            await query.answer("❌ Balance insuficiente", show_alert=True)
            return

        # Aplicar descuentos
        descuento_bono = monto if metodo_pago == "bono" else 0
        descuento_balance = monto if metodo_pago == "balance" else 0

        # Actualizar saldos en base de datos
        if metodo_pago == "bono":
            nuevo_bono = bono_data[1] - monto  # Índice 1: bono
            actualizar_registro('bono_apuesta', user_id, {'bono': nuevo_bono})
        else:
            nuevo_balance = usuario_data[2] - monto  # Índice 2: balance
            actualizar_registro('usuarios', user_id, {'balance': nuevo_balance})

        # ============= BONO LÍDER =============
        try:
            lider_id = str(usuario_data[4]) if len(usuario_data) > 3 else None  # Suponiendo que lider está en índice 3
            
            if lider_id and lider_id != user_id:
                lider_data = obtener_registro('usuarios', lider_id)
                if lider_data:
                    if metodo_pago == "bono":
                        porcentaje = 0.10
                        bono_lider = monto * porcentaje
                        
                        # Obtener bono del líder
                        bono_lider_data = obtener_registro('bono_apuesta', lider_id)
                        if bono_lider_data:
                            nuevo_bono_lider = bono_lider_data[1] + bono_lider  # Índice 1: bono
                            nuevo_rollover = bono_lider_data[3] + (bono_lider * 4)  # Suponiendo rollover en índice 3
                            
                            actualizar_registro('bono_apuesta', lider_id, {
                                'bono': nuevo_bono_lider,
                                'rollover_requerido': nuevo_rollover
                            })
                            
                            mensaje = (
                                f"🎉¡Bono por referido activo!🎉\n\n"
                                f"👤 Referido: {usuario_data[1]}\n"  # Suponiendo nombre en índice 1
                                f"💰 Monto apostado: <code>{monto} CUP</code>\n"
                                f"🎁 Bono (10%): <code>{bono_lider:.2f} CUP</code>\n"
                                f"💳 Nuevo total: <code>{nuevo_bono_lider:.2f} CUP</code>"
                            )
                        else:
                            # Crear registro de bono si no existe
                            actualizar_registro('bono_apuesta', lider_id, {
                                'bono': bono_lider,
                                'rollover_requerido': bono_lider * 4,
                                'rollover_actual': 0,
                                'bono_retirable': 0
                            })
                            mensaje = f"🎉¡Nuevo bono por referido!🎉\n\nMonto: <code>{bono_lider:.2f} CUP</code>"

                    elif metodo_pago == "balance":
                        porcentaje = 0.01
                        balance_lider = monto * porcentaje
                        nuevo_balance_lider = lider_data[2] + balance_lider  # Índice 2: balance
                        
                        actualizar_registro('usuarios', lider_id, {'balance': nuevo_balance_lider})
                        
                        mensaje = (
                            f"<pre>Tu referido ha hecho una apuesta!🎉</pre>\n\n"
                            f"👤 <b>Referido:</b> {usuario_data[1]}\n"
                            f"💰 <b>Monto:</b> <code>{monto} CUP</code>\n\n"
                            f"💵 Recibido en <b>Balance</b>(1%): <code>{balance_lider:.2f} CUP</code>"
                        )

                    await context.bot.send_message(  
                        chat_id=lider_id,  
                        text=mensaje,  
                        parse_mode='HTML'  
                    )  
        except (IndexError, KeyError, TypeError) as e:
            print(f"⚠️ Error en bono líder: {e}")
        # ============= FIN BONO LÍDER =============

        # Generar ID de ticket
        id_ticket = generar_id()
        
        # Preparar selecciones para la base de datos
        selecciones = []
        for apuesta in apuestas:
            sport_key = apuesta.get("sport_key", "")
            
            deporte_nombre = "Desconocido"
            if sport_key:
                base_sport = sport_key.split("_")[0]
                if base_sport in deportes_personalizados:
                    deporte_nombre = deportes_personalizados[base_sport][0]
            
            commence_time = apuesta.get("commence_time", "")
            fecha_formateada = "Fecha no disponible"
            if commence_time:
                try:
                    fecha_obj = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                    fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M:%S")
                except (ValueError, AttributeError):
                    pass

            seleccion = {
                "event_id": apuesta["event_id"],
                "sport_key": sport_key,
                "deporte": deporte_nombre,
                "liga": apuesta["liga"],
                "partido": apuesta["evento"],
                "mercado": apuesta["market"],
                "favorito": apuesta["descripcion"],
                "cuota_individual": apuesta["cuota"],
                "fecha_inicio": fecha_formateada,
                "estado": "⌛Pendiente"
            }
            selecciones.append(seleccion)

        # Crear apuesta combinada en base de datos
        apuesta_data = {
            'usuario_id': user_id,
            'fecha_realizada': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'monto': monto,
            'cuota': cuota_total,
            'ganancia': ganancia,
            'estado': "⌛Pendiente",
            'bono': descuento_bono,
            'balance': descuento_balance,
            'betting': "COMBINADA",
            'id_ticket': id_ticket,
            'selecciones_json': json.dumps(selecciones),
            'completed': False
        }

        # Insertar apuesta en base de datos
        columnas = ', '.join(apuesta_data.keys())
        placeholders = ', '.join(['?'] * len(apuesta_data))
        consulta = f"INSERT INTO apuestas ({columnas}) VALUES ({placeholders})"
        
        ejecutar_consulta_segura(consulta, tuple(apuesta_data.values()))

        # Preparar mensaje para el usuario
        mensaje_usuario = f"""
<blockquote>✅ COMBINADA CONFIRMADA</blockquote>

<pre>📊 Detalles de la Apuesta</pre>
┌────────────────────────
├ 💰 <b>Monto:</b> <code>{monto} CUP</code>
├ 📈 <b>Cuota Total:</b> <code>{cuota_total:.2f}</code>
├ 🏆 <b>Ganancia Potencial:</b> <code>{ganancia:.2f} CUP</code>
├ 🆔 <b>Ticket ID:</b> <code>{id_ticket}</code>
└ 📅 <b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}

<blockquote>📋 Selecciones:</blockquote>"""

        for i, seleccion in enumerate(selecciones, 1):
            mensaje_usuario += f"""
<pre>🔹 Evento {i}
├ 🏅<b>Deporte:</b> {seleccion['deporte']}
├ ⚽<b>Partido:</b> {seleccion['partido']}
├ 🏟<i>Liga:</i> {seleccion['liga']}
├ 📌Mercado: <b>{seleccion['mercado'].upper()}</b>
├ 🎯Favorito: {seleccion['favorito']}</pre>
"""

        await query.edit_message_text(
            text=mensaje_usuario,
            parse_mode="HTML"
        )

        # Enviar mensaje al canal
        user_link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        channel_message = f"""
<blockquote>Apuesta: 🔗COMBINADA🔗</blockquote>

👤 <b>Usuario:</b> {user_link} 
🆔 <b>ID:</b><code> {user_id} </code>
🆔 <b>Ticket ID:</b> <code>{id_ticket}</code>

<blockquote>📊 Detalles:</blockquote>
┌──────────────────────
├ 💰 <b>Monto:</b> <code>{monto} CUP</code>
├ 📈 <b>Cuota:</b> <code>{cuota_total:.2f}</code>
└ 🏆 <b>Ganancia:</b> <code>{ganancia:.2f} CUP</code>

<blockquote>📋 Selecciones:</blockquote>"""

        for i, seleccion in enumerate(selecciones, 1):
            channel_message += f"""
<pre>🔹Evento {i}
├ 🏅Deporte: {seleccion['deporte']}
├ ⚽Partido: {seleccion['partido']}
├ 🏟Liga: {seleccion['liga']}
├ 📌{seleccion['mercado'].upper()}
├ 🎯{seleccion['favorito']} </pre>
"""

        await context.bot.send_message(
            chat_id=CANAL_TICKET,
            text=channel_message,
            parse_mode="HTML"
        )

        # Limpiar el contexto
        context.user_data.clear()

    except Exception as e:
        print(f"Error en confirmar_combinada_handler: {str(e)}")
        import traceback
        traceback.print_exc()
        await query.answer("❌ Error al procesar", show_alert=True)
            
async def comando_basura(update: Update, context: CallbackContext):
    """Limpia apuestas finalizadas moviéndolas a bet_basura.json con reporte detallado y elimina de la DB"""
    try:
        # Obtener apuestas desde la base de datos
        apuestas = obtener_todas_las_apuestas()
        
        try:
            with open('bet_basura.json', 'r', encoding='utf-8') as f:
                basura_existente = json.load(f)
                if not isinstance(basura_existente, list):
                    basura_existente = []
        except (FileNotFoundError, json.JSONDecodeError):
            basura_existente = []

        # Filtrar apuestas finalizadas
        apuestas_a_mover = [
            apuesta for apuesta in apuestas 
            if any(
                estado in apuesta.get('estado', '') 
                for estado in ["Ganada", "Perdida", "Reembolso", "Reembolsada"]
            )
        ]
        
        if not apuestas_a_mover:
            await update.message.reply_text("♻️ No hay apuestas para limpiar (0 apuestas movidas)")
            return

        # Contador más flexible
        contador = {
            "Ganadas": 0,
            "Perdidas": 0,
            "Reembolsos": 0,
            "TOTAL": len(apuestas_a_mover)
        }

        for apuesta in apuestas_a_mover:
            estado = apuesta.get('estado', '')
            if "Ganada" in estado:
                contador["Ganadas"] += 1
            elif "Perdida" in estado:
                contador["Perdidas"] += 1
            else:
                contador["Reembolsos"] += 1

        # Mover apuestas al JSON de basura
        nueva_basura = basura_existente + apuestas_a_mover
        
        with open('bet_basura.json', 'w', encoding='utf-8') as f:
            json.dump(nueva_basura, f, ensure_ascii=False, indent=2)

        # ELIMINAR APUESTAS DE LA BASE DE DATOS
        apuestas_eliminadas_db = 0
        try:
            conn = sqlite3.connect('user_data.db')
            cursor = conn.cursor()
            
            for apuesta in apuestas_a_mover:
                # Buscar por ID único de la apuesta
                if 'id' in apuesta:
                    cursor.execute("DELETE FROM apuestas WHERE id = ?", (apuesta['id'],))
                # Si no hay ID, buscar por combinación de campos únicos
                elif 'id_ticket' in apuesta and apuesta['id_ticket']:
                    cursor.execute("DELETE FROM apuestas WHERE id_ticket = ?", (apuesta['id_ticket'],))
                elif 'event_id' in apuesta and 'usuario_id' in apuesta:
                    cursor.execute(
                        "DELETE FROM apuestas WHERE event_id = ? AND usuario_id = ? AND tipo_apuesta = ?", 
                        (apuesta['event_id'], apuesta['usuario_id'], apuesta.get('tipo_apuesta', ''))
                    )
                
                if cursor.rowcount > 0:
                    apuestas_eliminadas_db += 1
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error eliminando apuestas de la DB: {e}")
            # Continuar con el proceso aunque falle la eliminación de la DB

        # Obtener apuestas activas restantes desde la DB
        apuestas_activas = [
            apuesta for apuesta in apuestas 
            if not any(
                estado in apuesta.get('estado', '') 
                for estado in ["Ganada", "Perdida", "Reembolso", "Reembolsada"]
            )
        ]

        fecha_limpieza = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        mensaje = (
            f"🗑️ <b>LIMPIEZA DE APUESTAS COMPLETADA</b>\n"
            f"⏰ <i>Fecha:</i> {fecha_limpieza}\n\n"
            f"📊 <b>Total movidas:</b> {contador['TOTAL']}\n"
            f"├ ✅ Ganadas: {contador['Ganadas']}\n"
            f"├ ❌ Perdidas: {contador['Perdidas']}\n"
            f"└ 🔄 Reembolsos: {contador['Reembolsos']}\n\n"
            f"🗄️ <b>Eliminadas de DB:</b> {apuestas_eliminadas_db}\n"
            f"📂 <i>Apuestas activas restantes:</i> {len(apuestas_activas)}"
        )

        await update.message.reply_text(mensaje, parse_mode="HTML")

    except Exception as e:
        error_msg = f"❌ Error en comando /basura: {str(e)}"
        print(error_msg)
        await update.message.reply_text("⚠️ Ocurrió un error al procesar el comando. Verifica logs.")                      
                        
                                  

async def buscar_equipo_por_nombre_async(nombre_equipo: str) -> list:
    """Busca equipos usando la API de Football"""
    url = "https://v3.football.api-sports.io/teams"
    headers = {"x-rapidapi-key": API_FUTBOL_KEY}
    params = {"search": nombre_equipo}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()
                return [
                    (team['team']['id'], team['team']['name'], team['team']['logo']) 
                    for team in data.get('response', [])
                ]
    except Exception as e:
        print(f"Error buscando equipo: {e}")
        return []

async def obtener_partidos_por_equipo(team_id: int) -> list:
    """Obtiene partidos de un equipo específicos (NS y LIVE)"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_FUTBOL_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1️⃣ Próximos partidos no iniciados
            params_ns = {"team": team_id, "next": 10, "status": "NS"}
            async with session.get(url, headers=headers, params=params_ns) as response:
                data_ns = await response.json()
                partidos_ns = data_ns.get("response", [])

            # 2️⃣ Partidos en vivo
            params_live = {"team": team_id, "live": "all"}
            async with session.get(url, headers=headers, params=params_live) as response:
                data_live = await response.json()
                partidos_live = data_live.get("response", [])

            # 3️⃣ Unir ambos resultados
            return partidos_live + partidos_ns

    except Exception as e:
        print(f"Error obteniendo partidos: {e}")
        return []
@verificar_bloqueo
async def buscar_equipo(update: Update, context: CallbackContext):
    """Inicia el proceso de búsqueda de equipo"""
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        "🔍 <b>Buscar por nombre de equipo</b>\n\n"
        "Escribe el nombre del equipo que deseas buscar:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")]
        ])
    )
    context.user_data["estado"] = "ESPERANDO_NOMBRE_EQUIPO"
    
async def manejar_busqueda_equipo(update: Update, context: CallbackContext):
    """Procesa el nombre de equipo ingresado"""
    nombre_equipo = update.message.text
    context.user_data["estado"] = None
    
    # Buscar equipos
    equipos = await buscar_equipo_por_nombre_async(nombre_equipo)
    
    if not equipos:
        await update.message.reply_text(
            "❌ No se encontraron equipos. Intenta con otro nombre:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")]
            ])
        )
        return

    # Mostrar resultados
    keyboard = []
    for team_id, team_name, logo in equipos[:5]:  # Máximo 5 resultados
        keyboard.append([InlineKeyboardButton(
            f"🏆 {team_name}", 
            callback_data=f"equipo_{team_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="mostrar_tipos_apuestas")])
    
    await update.message.reply_text(
        f"🔍 Resultados para: <b>{nombre_equipo}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
async def mostrar_partidos_equipo(update: Update, context: CallbackContext):
    """Muestra los partidos de un equipo específico"""
    query = update.callback_query
    await query.answer()

    # Obtener el ID del equipo desde el callback_data
    callback_data = query.data  # ejemplo: equipo_1234
    team_id_str = callback_data.split("_")[1]
    team_id = int(team_id_str)

    partidos = await obtener_partidos_por_equipo(team_id)

    if not partidos:
        await query.edit_message_text(
            "ℹ️ No hay partidos próximos para este equipo",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="buscar_equipo")]
            ])
        )
        return

    # Construir mensaje con los partidos
    mensaje = "⚽ <b>Próximos Partidos:</b>\n\n"
    keyboard = []

    for partido in partidos:
        fixture = partido['fixture']
        home = partido['teams']['home']['name']
        away = partido['teams']['away']['name']
        fecha = datetime.strptime(fixture['date'], "%Y-%m-%dT%H:%M:%S%z")
        fecha_cuba = fecha.astimezone(pytz.timezone("America/Havana"))
        hora_str = fecha_cuba.strftime("%d/%m %H:%M")

        evento_id = fixture['id']
        mensaje += f"• {home} vs {away} - {hora_str}\n"

        keyboard.append([InlineKeyboardButton(
            f"{home} vs {away}",
            callback_data=f"evento_futbol_{evento_id}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="buscar_equipo")])

    await query.edit_message_text(
        mensaje,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )