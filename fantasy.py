import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CallbackContext
from telegram import CallbackQuery
from telegram import InputMediaPhoto
from telegram.error import BadRequest
import random
import json
import math  
import os
import requests
import uuid
import fcntl
import traceback
from collections import defaultdict
from typing import Dict, List
import asyncio
import html
import time as tm  
from datetime import datetime, time, timedelta, timezone
import pytz 
from functools import wraps  
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext, ConversationHandler, ContextTypes, JobQueue, ApplicationHandlerStop


from necesario import load_data, save_data, marca_tiempo, comando_basura_user, lock_data, lock_apuestas, lock_minijuegos, has_lock



API_KEY = "89957a4709f62db07ef73d1d1977103c"
# Configuración de archivos (usando rutas simples)
PLAYERS_FILE = "liga_spain_jugadores.json"
USUARIOS_BLOQUEADOS_FILE = "usuarios_bloqueados.json"
USER_FANTASY_FILE = "user_fantasy.json"
GROUP_CHAT_ID = -1001929466623
REGISTRO_MINIJUEGOS = -1002566004558

RANKING_FILE = "usuarios_bloqueados.json"


API_URL_TEAMS = "https://v3.football.api-sports.io/teams"
API_URL_PLAYERS = "https://v3.football.api-sports.io/players"

TEMPORADA = "2024"
LIGAS_IDS = ["39", "140", "78"]
ARCHIVO_JSON = "liga_spain_jugadores.json"

headers = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY
}
# Constantes del juego
MAX_USERS = 200  # Añadir al inicio del archivo con las otras constantes
INITIAL_CREDITS = 1000
BASE_FORMATION = "4-4-2"  # 1 portero, 4 defensas, 4 mediocampistas, 2 delanteros
POSITION_WEIGHTS = {
    "Goalkeeper": 1.2,    # Los porteros suelen ser más valiosos
    "Defender": 1.0,
    "Midfielder": 1.1,    # Los mediocampistas suelen tener ratings más altos
    "Attacker": 1.3       # Los delanteros son los más valiosos
}
MIN_RATING = 2.0  # Rating mínimo para considerar un jugador

def initialize_files():
    """Inicializa los archivos necesarios si no existen"""
    if not os.path.exists(PLAYERS_FILE):
        raise FileNotFoundError(f"El archivo {PLAYERS_FILE} no existe. Necesitas el archivo de jugadores.")
    
    if not os.path.exists(USER_FANTASY_FILE):
        with open(USER_FANTASY_FILE, 'w') as f:
            json.dump({}, f)
            
# Lock específico para user_fantasy.json
lock_fantasy = asyncio.Lock()
lock_torneo = asyncio.Lock()


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

# Funciones para manejar user_fantasy.json
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
async def load_fantasy_data():
    """Carga los datos de user_fantasy.json sin bloqueo interno"""
    try:
        if not os.path.exists(USER_FANTASY_FILE):
            with open(USER_FANTASY_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        
        with open(USER_FANTASY_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Si el archivo está corrupto, recrearlo
        with open(USER_FANTASY_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    except Exception as e:
        logging.error(f"Error al cargar fantasy data: {str(e)}")
        traceback.print_exc()
        return {}

async def save_fantasy_data(data):
    """Guarda los datos en user_fantasy.json sin bloqueo interno"""
    try:
        with open(USER_FANTASY_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error al guardar fantasy data: {str(e)}")
        traceback.print_exc()
        return False
            

def get_normalized_position(position: str) -> str:
    """Normaliza las posiciones a categorías generales"""
    position = position.lower()
    if 'goalkeeper' in position:
        return "Goalkeeper"
    elif 'defender' in position or 'back' in position:
        return "Defender"
    elif 'midfielder' in position or 'midfield' in position:
        return "Midfielder"
    elif 'attacker' in position or 'forward' in position or 'striker' in position or 'winger' in position:
        return "Attacker"
    return "Midfielder"  # Por defecto



def select_balanced_team(players: List[Dict]) -> List[Dict]:
    """Selecciona un equipo balanceado según la formación base"""
    # Filtrar jugadores con estadísticas válidas
    valid_players = []
    for player in players:
        if player['statistics'] and player['statistics'][0]['games']['appearences'] is not None:
            stats = player['statistics'][0]
            position = get_normalized_position(stats["games"]["position"])
            rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
            if rating >= MIN_RATING:
                valid_players.append((player, position, rating))
    
    if not valid_players:
        raise ValueError("No hay jugadores válidos en el archivo.")
    
    # Organizar jugadores por posición
    position_groups = defaultdict(list)
    for player, position, rating in valid_players:
        position_groups[position].append((player, rating))
    
    # Ordenar jugadores por rating dentro de cada posición
    for position in position_groups:
        position_groups[position].sort(key=lambda x: x[1], reverse=True)
    
    # Seleccionar equipo según formación 4-4-2
    team = []
    
    # 1 Portero (el mejor disponible)
    if position_groups["Goalkeeper"]:
        team.append(position_groups["Goalkeeper"][0][0])
    
    # 4 Defensas (mezcla de buenos y regulares)
    defenders = position_groups["Defender"]
    if len(defenders) >= 4:
        # Tomar 2 mejores y 2 aleatorios de los siguientes 10
        team.extend([x[0] for x in defenders[:2]])
        team.extend([x[0] for x in random.sample(defenders[2:12], min(2, len(defenders[2:12])))])
    else:
        team.extend([x[0] for x in defenders])
    
    # 4 Mediocampistas
    midfielders = position_groups["Midfielder"]
    if len(midfielders) >= 4:
        team.extend([x[0] for x in midfielders[:2]])
        team.extend([x[0] for x in random.sample(midfielders[2:12], min(2, len(midfielders[2:12])))])
    else:
        team.extend([x[0] for x in midfielders])
    
    # 2 Delanteros
    attackers = position_groups["Attacker"]
    if len(attackers) >= 2:
        team.append(attackers[0][0])
        if len(attackers) > 1:
            team.append(random.choice(attackers[1:6])[0] if len(attackers) > 5 else attackers[1][0])
    else:
        team.extend([x[0] for x in attackers])
    
    # Si no tenemos suficientes jugadores, completar con los mejores disponibles de cualquier posición
    while len(team) < 11 and valid_players:
        # Excluir jugadores ya seleccionados
        selected_ids = {p['player']['id'] for p in team}
        available_players = [p for p in valid_players if p[0]['player']['id'] not in selected_ids]
        
        if available_players:
            # Ordenar por rating y seleccionar el mejor disponible
            available_players.sort(key=lambda x: x[2], reverse=True)
            team.append(available_players[0][0])
    
    return team[:11]  # Asegurar máximo 11 jugadores

async def assign_team_to_user(user_id):
    try:
        fantasy_data = await load_fantasy_data()
        if len(fantasy_data) >= MAX_USERS:
            logging.warning(f"Límite de usuarios alcanzado ({MAX_USERS})")
            return False

        # Cargar datos de jugadores y limpiar duplicados
        with open(PLAYERS_FILE, 'r') as f:
            players_data = json.load(f)
        
        # Limpiar duplicados en el archivo principal primero
        unique_players = {}
        for player in players_data:
            player_id = str(player["player"]["id"])
            if player_id not in unique_players:
                unique_players[player_id] = player
        players_data = list(unique_players.values())

        # Obtener jugadores ya asignados (de todos los equipos)
        assigned_players = set()
        for user_team in fantasy_data.values():
            if isinstance(user_team, dict) and 'team' in user_team:
                for player in user_team['team']:
                    assigned_players.add(str(player['id']))

        # Filtrar jugadores disponibles (no asignados + con estadísticas válidas)
        available_players = []
        seen_ids = set()  # Para evitar duplicados locales
        
        for player in players_data:
            player_id = str(player["player"]["id"])
            
            if (player_id not in assigned_players and 
                player_id not in seen_ids and
                player.get('statistics') and 
                player['statistics'] and
                player['statistics'][0]['games']['appearences'] is not None):
                
                stats = player['statistics'][0]
                rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
                
                if MIN_RATING <= rating <= 7.1:
                    available_players.append(player)
                    seen_ids.add(player_id)

        # Verificar suficientes jugadores disponibles
        if len(available_players) < 11:
            logging.error(f"No hay suficientes jugadores disponibles. Requeridos: 11, Disponibles: {len(available_players)}")
            return False

        # Seleccionar equipo balanceado con nuevo algoritmo
        selected_players = await select_balanced_team_improved(available_players)
        
        if not selected_players or len(selected_players) < 11:
            logging.error(f"No se pudo formar equipo completo. Jugadores seleccionados: {len(selected_players)}")
            return False
        
        # Crear nuevo equipo
        user_team = {
            "credits": INITIAL_CREDITS,
            "team": [],
            "formation": BASE_FORMATION,
            "value": 0,
            "name": f"Equipo de {user_id[:6]}"  # Nombre temporal
        }
        
        for player in selected_players:
            stats = player['statistics'][0]
            player_value = calculate_player_value(player, stats)
            
            user_team["team"].append({
                "id": player["player"]["id"],
                "name": player["player"]["name"],
                "is_titular": True,
                "firstname": player["player"]["firstname"],
                "lastname": player["player"]["lastname"],
                "position": stats["games"]["position"],
                "normalized_position": get_normalized_position(stats["games"]["position"]),
                "age": player["player"]["age"],
                "team": stats["team"]["name"],
                "team_id": stats["team"]["id"],
                "team_logo": stats["team"]["logo"],
                "photo": player["player"]["photo"],
                "rating": stats["games"]["rating"],
                "value": player_value,
                "goals": stats["goals"]["total"] or 0,
                "assists": stats["goals"]["assists"] or 0,
                "key_passes": stats["passes"]["key"] or 0,
                "tackles": stats["tackles"]["total"] or 0,
                "appearances": stats["games"]["appearences"] or 0
            })
            user_team["value"] += player_value
        
        # Asignar equipo al usuario (guardar con lock interno)
        fantasy_data[str(user_id)] = user_team
        success = await save_fantasy_data(fantasy_data)
        
        if not success:
            logging.error(f"Error al guardar equipo para usuario {user_id}")
            return False
            
        logging.info(f"Equipo asignado correctamente al usuario {user_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error crítico en assign_team_to_user: {str(e)}")
        traceback.print_exc()
        return False
async def select_balanced_team_improved(players: List[Dict]) -> List[Dict]:
    try:
        # Pre-procesar jugadores con estadísticas válidas y sin duplicados
        valid_players = []
        seen_ids = set()
        
        for player in players:
            player_id = str(player["player"]["id"])
            if (player_id not in seen_ids and 
                player['statistics'] and 
                player['statistics'][0]['games']['appearences'] is not None):
                
                stats = player['statistics'][0]
                position = get_normalized_position(stats["games"]["position"])
                rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
                
                if MIN_RATING <= rating <= 7.1:
                    valid_players.append((player, position, rating))
                    seen_ids.add(player_id)
        
        if not valid_players:
            raise ValueError("No hay jugadores válidos en el archivo.")

        # Organizar jugadores por posición y rating
        position_groups = defaultdict(list)
        for player, position, rating in valid_players:
            position_groups[position].append((player, rating))
        
        # Ordenar jugadores por rating dentro de cada posición
        for position in position_groups:
            position_groups[position].sort(key=lambda x: x[1])  # Orden ascendente para distribución equitativa

        # Distribución equitativa - algoritmo mejorado
        team = []
        distribution_attempts = 0
        max_attempts = 100
        
        while len(team) < 11 and distribution_attempts < max_attempts:
            distribution_attempts += 1
            team = []
            position_counts = defaultdict(int)
            
            # Seleccionar jugadores intentando mantener balance
            for position in POSITION_ORDER:
                if position in position_groups and position_groups[position]:
                    # Tomar jugadores de manera rotativa para mayor equidad
                    idx = distribution_attempts % len(position_groups[position])
                    selected = position_groups[position][idx]
                    team.append(selected[0])
                    position_counts[position] += 1
            
            # Verificar si cumplimos con una formación básica (1-4-4-2)
            if (position_counts.get("Goalkeeper", 0) >= 1 and
                position_counts.get("Defender", 0) >= 4 and
                position_counts.get("Midfielder", 0) >= 4 and
                position_counts.get("Attacker", 0) >= 2):
                break
        
        # Si no logramos formar equipo después de los intentos, usar método alternativo
        if len(team) < 11:
            team = await fallback_team_selection(valid_players)
        
        return team[:11]  # Asegurar máximo 11 jugadores
    
    except Exception as e:
        logging.error(f"Error en select_balanced_team_improved: {str(e)}")
        return await fallback_team_selection(valid_players)
        
async def fallback_team_selection(valid_players: List) -> List[Dict]:
    """Método alternativo para selección de equipo cuando el principal falla"""
    try:
        # Agrupar por posición con rating convertido a float
        position_groups = defaultdict(list)
        for player, position, rating in valid_players:
            # Convertir rating a float si es necesario
            try:
                rating_val = float(rating) if isinstance(rating, str) else rating
            except (TypeError, ValueError):
                rating_val = MIN_RATING
            position_groups[position].append((player, rating_val))
        
        # Selección mínima garantizada
        team = []
        
        # 1 Portero
        if "Goalkeeper" in position_groups:
            goalkeepers = position_groups["Goalkeeper"]
            # Ordenar por rating numérico
            goalkeepers_sorted = sorted(goalkeepers, key=lambda x: x[1])
            # Tomar uno al azar de los 3 menos valorados
            if len(goalkeepers_sorted) >= 3:
                selected = random.choice(goalkeepers_sorted[:3])[0]
            else:
                selected = goalkeepers_sorted[0][0] if goalkeepers_sorted else None
            if selected:
                team.append(selected)
        
        # 4 Defensas (con manejo de tipo numérico)
        if "Defender" in position_groups:
            defenders = position_groups["Defender"]
            defenders_sorted = sorted(defenders, key=lambda x: x[1])  # Orden ascendente
            # Tomar los 4 con menor rating
            for i in range(min(4, len(defenders_sorted))):
                team.append(defenders_sorted[i][0])
        
        # 4 Mediocampistas
        if "Midfielder" in position_groups:
            midfielders = position_groups["Midfielder"]
            midfielders_sorted = sorted(midfielders, key=lambda x: x[1])
            for i in range(min(4, len(midfielders_sorted))):
                team.append(midfielders_sorted[i][0])
        
        # 2 Delanteros
        if "Attacker" in position_groups:
            attackers = position_groups["Attacker"]
            attackers_sorted = sorted(attackers, key=lambda x: x[1])
            for i in range(min(2, len(attackers_sorted))):
                team.append(attackers_sorted[i][0])
        
        # Completar con mejores disponibles si faltan (rating más alto)
        if len(team) < 11:
            # Recopilar todos los jugadores no seleccionados
            remaining = []
            for position in position_groups.values():
                for player_info in position:
                    if player_info[0] not in team:
                        remaining.append(player_info)
            
            # Ordenar por rating descendente (mejores primero)
            remaining_sorted = sorted(remaining, key=lambda x: x[1], reverse=True)
            # Tomar los mejores disponibles
            for i in range(min(len(remaining_sorted), 11 - len(team))):
                team.append(remaining_sorted[i][0])
        
        return team[:11]  # Asegurar máximo 11 jugadores
    
    except Exception as e:
        logging.error(f"Error en fallback_team_selection: {str(e)}")
        traceback.print_exc()
        return []

async def show_user_team(user_id, is_new=False):
    """Muestra el equipo del usuario con titulares y suplentes"""
    try:
        fantasy_data = await load_fantasy_data()
        
        if str(user_id) not in fantasy_data:
            return "❌ No tienes un equipo asignado."
        
        team = fantasy_data[str(user_id)]
        
        # Eliminar duplicados en el equipo
        unique_players = []
        seen_ids = set()
        
        for player in team['team']:
            player_id = str(player['id'])
            if player_id not in seen_ids:
                seen_ids.add(player_id)
                # Asegurar estructura consistente
                player_data = {
                    "id": player.get('id'),
                    "name": player.get('name'),
                    "firstname": player.get('firstname', ''),
                    "lastname": player.get('lastname', ''),
                    "position": player.get('position'),
                    "normalized_position": player.get('normalized_position'),
                    "age": player.get('age'),
                    "team": player.get('team'),
                    "team_id": player.get('team_id'),
                    "team_logo": player.get('team_logo'),
                    "photo": player.get('photo'),
                    "rating": float(player['rating']) if isinstance(player.get('rating'), str) else player.get('rating'),
                    "value": player.get('value'),
                    "goals": player.get('goals', 0),
                    "assists": player.get('assists', 0),
                    "key_passes": player.get('key_passes', 0),
                    "tackles": player.get('tackles', 0),
                    "appearances": player.get('appearances', 0),
                    "is_titular": player.get('is_titular', False)  # Por defecto todos no son titulares
                }
                unique_players.append(player_data)
        
        # Actualizar equipo sin duplicados
        team['team'] = unique_players
        
        # Construir mensaje de visualización
        team_display = []
        
        if is_new:
            team_display.append("⭐ ¡FELICITACIONES! ⭐")
            team_display.append("¡Has recibido tu equipo de Fantasy Football!")
            team_display.append("")
            team_display.append(f"💰 Créditos iniciales: {team['credits']}")
            team_display.append(f"💎 Valor total del equipo: {team['value']}")
            team_display.append("")
        
        team_display.append("⚽ TU EQUIPO:")
        team_display.append("")
        team_display.append(f"🏟 Formación: {team['formation']}")
        team_display.append(f"💎 Valor total: {team['value']}")
        team_display.append("")
        
        # Separar titulares y suplentes
        titulares = defaultdict(list)
        suplentes = []
        
        for player in unique_players:
            if player.get('is_titular', True):
                titulares[player['normalized_position']].append(player)
            else:
                suplentes.append(player)
        
        # Mostrar titulares primero
        team_display.append("⭐ <b>TITULARES:</b>")
        display_order = ["Goalkeeper", "Defender", "Midfielder", "Attacker"]
        
        for position in display_order:
            if position in titulares:
                team_display.append(f"=== {position.upper()} ===")
                for player in sorted(titulares[position], key=lambda x: x['value'], reverse=True):
                    team_display.append(f"👤 {player['name']} ({player['team']})")
                    team_display.append(f"   ⭐ Rating: {player['rating']} | 💰 Valor: {player['value']}")
                    team_display.append(f"   🎯 Goles: {player['goals']} | 🎁 Asistencias: {player['assists']}")
                    team_display.append(f"   🎯 Pases clave: {player['key_passes']} | 🛡 Tackles: {player['tackles']}")
                    team_display.append(f"   🏟 Partidos: {player['appearances']} | 🎂 Edad: {player['age']}")
                    team_display.append("")
        
        # Mostrar suplentes si existen
        if suplentes:
            team_display.append("\n🔁 <b>SUPLENTES:</b>")
            for player in sorted(suplentes, key=lambda x: x['value'], reverse=True):
                team_display.append(f"👤 {player['name']} ({player['position']})")
                team_display.append(f"   ⭐ Rating: {player['rating']} | 💰 Valor: {player['value']}")
                team_display.append("")
        
        team_display.append(f"💰 Créditos disponibles: {team['credits']}")
        
        return "\n".join(team_display)
        
    except Exception as e:
        logging.error(f"Error en show_user_team: {str(e)}")
        return "⚠️ Error al mostrar tu equipo."


        
        

@verificar_bloqueo
async def mi_equipo_handler(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        user_id = str(user.id)
        
        # Determinar si es mensaje o callback
        if update.callback_query:
            message = update.callback_query.message
            await update.callback_query.answer()
        else:
            message = update.message
        
        # Cargar datos del equipo
        fantasy_data = await load_fantasy_data()
        
        # Verificar si el usuario ya tiene equipo
        if str(user_id) not in fantasy_data:
            # Verificar límite de usuarios antes de asignar equipo
            if len(fantasy_data) >= MAX_USERS:
                await message.reply_text(
                    "❌ El fantasy football ha alcanzado el límite máximo de 150 usuarios. "
                    "No se pueden crear más equipos en este momento."
                )
                return
            
            # Intentar asignar equipo nuevo
            success = await assign_team_to_user(user_id)
            if not success:
                await message.reply_text(
                    "❌ No se pudo crear tu equipo. Por favor intenta nuevamente más tarde."
                )
                return
            is_new = True
        else:
            is_new = False
        
        # Obtener y mostrar el equipo
        team_display = await show_user_team(user_id, is_new)
        
        # Crear teclado de opciones
        keyboard = [
            [InlineKeyboardButton("🔄 Cambiar formación", callback_data='cambiar_formacion')],
            [InlineKeyboardButton("📊 Estadísticas detalladas", callback_data='estadisticas_equipo')],
            [InlineKeyboardButton("💰 Vender Jugador", callback_data='vender_jugador_handler')],
            [InlineKeyboardButton("🏠 Menú principal", callback_data='juego_fantasy')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Dividir el mensaje si es demasiado largo (más de 4000 caracteres)
        if len(team_display) > 4000:
            # Dividir el mensaje en partes
            parts = []
            current_part = ""
            
            for line in team_display.split('\n'):
                if len(current_part) + len(line) + 1 < 4000:
                    current_part += line + '\n'
                else:
                    parts.append(current_part)
                    current_part = line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            # Enviar la primera parte con el teclado
            first_part = parts[0]
            remaining_parts = parts[1:]
            
            if update.callback_query:
                try:
                    await message.edit_text(
                        text=first_part,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except:
                    await message.reply_text(
                        text=first_part,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                await message.reply_text(
                    text=first_part,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            # Enviar las partes restantes sin teclado
            for part in remaining_parts:
                await message.reply_text(
                    text=part,
                    parse_mode='HTML'
                )
        else:
            # Mensaje normal si no excede el límite
            if update.callback_query:
                if message.text:  # Verificamos si el mensaje tiene texto
                    try:
                        await message.edit_text(
                            text=team_display,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    except:
                        await message.reply_text(
                            text=team_display,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                else:
                    await message.reply_text(
                        text=team_display,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                await message.reply_text(
                    text=team_display,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
    except Exception as e:
        logging.error(f"Error en mi_equipo_handler: {str(e)}")
        traceback.print_exc()
        
        error_msg = (
            "⚠️ Ocurrió un error al procesar tu solicitud. "
            "Por favor intenta nuevamente o contacta con soporte."
        )
        
        if update.callback_query:
            await update.callback_query.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)



async def eliminar_jugadores_repetidos(fantasy_data: Dict) -> Dict:
    """Elimina jugadores duplicados en todos los equipos, conservando solo la primera ocurrencia"""
    jugadores_vistos = set()
    cambios_realizados = False
    
    for user_id, user_data in fantasy_data.items():
        if not isinstance(user_data, dict) or 'team' not in user_data:
            continue
        
        equipo_limpio = []
        for jugador in user_data['team']:
            jugador_id = str(jugador.get('id'))
            if jugador_id and jugador_id not in jugadores_vistos:
                jugadores_vistos.add(jugador_id)
                equipo_limpio.append(jugador)
            else:
                logging.warning(f"Eliminado jugador duplicado ID {jugador_id} del usuario {user_id}")
                cambios_realizados = True
        
        # Actualizar el equipo solo si hubo cambios
        if cambios_realizados or len(equipo_limpio) != len(user_data['team']):
            user_data['team'] = equipo_limpio
            user_data['value'] = sum(jugador.get('value', 0) for jugador in equipo_limpio)
    
    if cambios_realizados:
        logging.info("Limpieza de jugadores duplicados completada")
    return fantasy_data



async def juego_fantasy(update: Update, context: CallbackContext):
    """Muestra el menú principal del juego Fantasy con verificación obligatoria de username"""
    user = update.effective_user
    user_id = str(user.id)

    # Verificar si el usuario está bloqueado en fantasy
    try:
        if os.path.exists("usuarios_bloqueados.json"):
            with open("usuarios_bloqueados.json", "r") as f:
                bloqueados_data = json.load(f)
                bloqueados_fantasy = bloqueados_data.get("bloqueo_fantasy", [])
                if user_id in bloqueados_fantasy:
                    mensaje_bloqueado = "🚫 Lo siento, fuiste eliminado del fantasy por inactividad, no puedes acceder al Fantasy. Si deseas retomar tu camino como manager debes contactar con soporte para valorar si realmente deseas participar"
                    if update.callback_query:
                        await update.callback_query.answer()
                        await update.callback_query.message.edit_text(mensaje_bloqueado)
                    else:
                        await update.message.reply_text(mensaje_bloqueado)
                    return
    except Exception as e:
        print(f"⚠️ Error al verificar usuarios bloqueados: {e}")

    # Verificación obligatoria de username
    if not user.username:
        error_msg = """
⚠️ <b>CONFIGURACIÓN REQUERIDA</b> ⚠️

Para jugar al Fantasy necesitas tener un <b>@username</b> configurado en Telegram.

Por favor:
1. Ve a <b>Configuración</b> de Telegram
2. Selecciona <b>Editar perfil</b>
3. Establece un <b>@nombredeusuario</b>
4. Vuelve a intentarlo

Este dato es necesario para que otros jugadores puedan retarte.
"""
        if update.callback_query:
            await update.callback_query.message.reply_text(error_msg, parse_mode='HTML')
            await update.callback_query.answer()
        else:
            await update.message.reply_text(error_msg, parse_mode='HTML')
        return

    # Actualización del username con lock
    async with lock_data:
        user_data = await load_data()

        if user_id not in user_data.get("usuarios", {}):
            # Crear entrada si no existe
            user_data.setdefault("usuarios", {})[user_id] = {
                "username": user.username.lower(),
                "Nombre": user.full_name,
                "Balance": 0,
                "marca": datetime.now().strftime("%Y-%m-%d %H:%M:%S %p")
            }
            await save_data(user_data)
        else:
            # Actualizar si cambió el username
            current_username = user_data["usuarios"][user_id].get("username", "").lower()
            new_username = user.username.lower()

            if current_username != new_username:
                user_data["usuarios"][user_id]["username"] = new_username
                user_data["usuarios"][user_id]["marca"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %p")
                await save_data(user_data)
                logging.info(f"Username actualizado para {user_id}: {new_username}")

    # Validación y limpieza de jugadores duplicados
    async with lock_fantasy:
        try:
            fantasy_data = await load_fantasy_data()
            fantasy_data_limpio = await eliminar_jugadores_repetidos(fantasy_data)

            # Guardar solo si hubo cambios
            if fantasy_data != fantasy_data_limpio:
                await save_fantasy_data(fantasy_data_limpio)
                logging.info("Limpieza de jugadores duplicados completada")
        except Exception as e:
            logging.error(f"Error al limpiar jugadores duplicados: {str(e)}")

    # Resto de la función (menú principal)
    if update.message:
        message = update.message
    elif update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        return

    keyboard = [
        [
            InlineKeyboardButton("🛒 Mercado", callback_data='mercado_menu'),
            InlineKeyboardButton("⚽ Mi Equipo", callback_data='mi_equipo')
        ],
        [
            InlineKeyboardButton("🏆 Torneo", callback_data='mostrar_sistema_torneo'),
            InlineKeyboardButton("💰 Subastas", callback_data='menu_subastas')
        ],
        [
            InlineKeyboardButton("📊 Ranking", callback_data='ranking_fantasy'),
            InlineKeyboardButton("Jugador🆚Jugador", callback_data='mostrar_rivales')
        ],
        [
            InlineKeyboardButton("🔙 Menu principal", callback_data='menu_principal')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    mensaje = """
<b>🎮✨ <i>FANTASY GAME</i> ✨🎮</b>

¡Bienvenido al emocionante mundo del Fantasy! 

Elige una opción para comenzar tu aventura:

🛒 <b>Mercado</b>: Compra/vende jugadores para fortalecer tu equipo  
⚽ <b>Mi Equipo</b>: Gestiona tus jugadores y formación actual  
🏆 <b>Torneo</b>: Participa en competiciones contra otros managers  
💰 <b>Subastas</b>: Ofertas exclusivas por estrellas del juego  
📊 <b>Ranking</b>: Clasificación de los mejores equipos  
🆚 <b>Jugador vs Jugador</b>: ¡Rétate con otros managers!
"""

    if update.callback_query:
        await message.edit_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await message.reply_text(
            text=mensaje,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


# Constantes para el mercado
MARKET_TAX = 0.10  # 10% de impuesto
JUGADORES_POR_PAGINA = 8

# Modificar el mercado_handler para manejar correctamente las compras
async def mercado_handler(update: Update, context: CallbackContext):
    """Manejador principal del mercado"""
    user_id = str(update.effective_user.id)
    
    if update.callback_query:
        data = update.callback_query.data
        if data.startswith('comprar_'):
            _, player_id = data.split('_')
            await comprar_jugador(update, context, user_id, player_id)
            return
        elif data.startswith('vender_'):
            _, player_id = data.split('_')
            await vender_jugador(update, context, user_id, player_id)
            return
    
    await show_market_main_menu(update, context)



async def show_market_main_menu(update: Update, context: CallbackContext):
    """Muestra el menú principal del mercado con botones mejorados"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Cargar datos sin locks (solo lectura)
    user_data = await load_data()
    user_fantasy = await load_fantasy_data()
    
    # Obtener saldos del usuario
    balance = user_data.get("usuarios", {}).get(user_id, {}).get("Balance", 0)
    bono = user_data.get("Bono_apuesta", {}).get(user_id, {}).get("Bono", 0)
    credito = user_fantasy.get(user_id, {}).get("credits", 0)

    # Teclado con botones mejorados (sin "Ver Bote")
    keyboard = [
        [InlineKeyboardButton("💹 Mercado de Jugadores", callback_data='mercado_equipos')],
        [InlineKeyboardButton("💰 Mis Jugadores en Venta", callback_data='mercado_mis_ventas')],
        [InlineKeyboardButton("🔙 Volver al Menú", callback_data='juego_fantasy')]
    ]
    
    # Mensaje con formato HTML mejorado
    mensaje = f"""
<b>🏪 MERCADO FANTASY</b>
━━━━━━━━━━━━━━━━━━
<b>💰 Tus Fondos Disponibles:</b>
├ <b>Balance:</b> <code>${balance:,.2f}</code>
├ <b>Bonos:</b> <code>{bono}</code>
└ <b>Créditos Fantasy:</b> <code>{credito}</code>

<b>📊 Sistema de Compra:</b>
• Todos los jugadores disponibles con cualquier método de pago
• Impuesto de mercado: <code>{MARKET_TAX*100}%</code>

<i>Selecciona una opción para comenzar:</i>
    """
    
    # Enviar mensaje con teclado
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def listar_equipos_mercado(update: Update, context: CallbackContext):
    """Lista los equipos disponibles en el mercado con botones"""
    try:
        query = update.callback_query
        await query.answer()
        
        async with lock_data:
            with open(PLAYERS_FILE, 'r') as f:
                players_data = json.load(f)
        
        # Obtener equipos únicos
        equipos = {}
        for player in players_data:
            if player.get('statistics'):
                team = player['statistics'][0]['team']
                if team['id'] not in equipos:
                    equipos[team['id']] = team['name']
        
        # Si no hay equipos, mostrar mensaje apropiado
        if not equipos:
            await query.edit_message_text(
                text="⚠️ No se encontraron equipos disponibles en este momento.",
                parse_mode='HTML'
            )
            return
        
        # Crear teclado con equipos (2 botones por fila)
        keyboard = []
        temp_row = []
        for team_id, team_name in equipos.items():
            temp_row.append(InlineKeyboardButton(team_name, callback_data=f'mercado_equipo_{team_id}'))
            if len(temp_row) == 2:
                keyboard.append(temp_row)
                temp_row = []
        if temp_row:
            keyboard.append(temp_row)
        
        # Añadir botón de volver
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='mercado_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Verificar si el mensaje existe y tiene texto
        try:
            await query.edit_message_text(
                text="🏆 Selecciona un equipo para ver sus jugadores disponibles:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except BadRequest as e:
            if "no text in the message" in str(e):
                # Si no hay mensaje para editar, enviar uno nuevo
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="🏆 Selecciona un equipo para ver sus jugadores disponibles:",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                raise
    
    except Exception as e:
        logging.error(f"Error en listar_equipos_mercado: {str(e)}")
        traceback.print_exc()
        if 'query' in locals():
            await query.edit_message_text(
                text="⚠️ Ocurrió un error al cargar los equipos. Por favor intenta nuevamente.",
                parse_mode='HTML'
            )
    
async def listar_jugadores_equipo(update: Update, context: CallbackContext):
    """Lista jugadores con clasificación, métodos de pago y paginación mejorada"""
    query = update.callback_query
    await query.answer()
    
    # Obtener team_id y page del contexto o del callback_data
    if query.data.startswith('mercado_equipo_'):
        parts = query.data.split('_')
        team_id = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 1
    else:
        team_id = context.user_data.get('current_team')
        page = context.user_data.get('current_page', 1)
    
    # Guardar contexto para volver
    context.user_data['last_market_page'] = {'team_id': team_id, 'page': page}
    
    async with lock_data:
        with open(PLAYERS_FILE, 'r') as f:
            players_data = json.load(f)
        fantasy_data = await load_fantasy_data()
    
    # Obtener información de jugadores ya comprados
    jugadores_comprados = {}
    for user_id, user_team in fantasy_data.items():
        if isinstance(user_team, dict) and 'team' in user_team:
            for player in user_team['team']:
                jugadores_comprados[str(player['id'])] = {
                    'owner_id': user_id,
                    'owner_name': fantasy_data.get(user_id, {}).get('name', 'Usuario Desconocido'),
                    'value': player['value']
                }
    
    # Filtrar jugadores únicos del equipo solicitado
    jugadores_vistos = set()
    team_players = []
    team_name = ""
    team_logo = ""
    
    for player in players_data:
        if player.get('statistics') and player['statistics']:
            stats = player['statistics'][0]
            if str(stats['team']['id']) == team_id:
                team_name = stats['team']['name']
                team_logo = stats['team']['logo']
                player_id = str(player["player"]["id"])
                
                if player_id not in jugadores_vistos:
                    jugadores_vistos.add(player_id)
                    
                    rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
                    if rating >= MIN_RATING:
                        value = calculate_player_value(player, stats)
                        
                        # Clasificación por rating
                        if rating > 7.1:
                            player_type = "💎 TOP"
                            payment_type = "💵 SOLO BALANCE"
                        elif rating > 6.5:
                            player_type = "🔹 MEDIO"
                            payment_type = "💳 BONO/BALANCE"
                        else:
                            player_type = "⚪ NORMAL"
                            payment_type = "🪙 CRÉDITOS/BONO/BALANCE"
                        
                        # Verificar si está comprado
                        comprado_por = jugadores_comprados.get(player_id)
                        if comprado_por:
                            player_type += " (🛒 COMPRADO)"
                            payment_type = f"💼 Dueño: {comprado_por['owner_name']}"
                        
                        team_players.append({
                            "id": player_id,
                            "name": player["player"]["name"],
                            "position": stats["games"]["position"],
                            "rating": rating,
                            "value": value,
                            "type": player_type,
                            "payment": payment_type,
                            "photo": player["player"].get("photo", ""),
                            "comprado": bool(comprado_por),
                            "owner_id": comprado_por['owner_id'] if comprado_por else None
                        })
    
    # Ordenar por valor descendente
    team_players.sort(key=lambda x: x['value'], reverse=True)
    
    # Paginación (10 jugadores por página)
    jugadores_por_pagina = 10
    total_paginas = max(1, (len(team_players) + jugadores_por_pagina - 1) // jugadores_por_pagina)
    page = max(1, min(page, total_paginas))
    inicio = (page - 1) * jugadores_por_pagina
    jugadores_pagina = team_players[inicio:inicio + jugadores_por_pagina]
    
    # Construir mensaje
    message_lines = [
        f"<b>⚽ Jugadores de {team_name} - Página {page}/{total_paginas}</b>",
        f"🔹 Mostrando todos los jugadores (disponibles y comprados)",
        ""
    ]
    
    for player in jugadores_pagina:
        message_lines.append(
            f"{player['type']} <b>{player['name']}</b> ({player['position']})"
        )
        message_lines.append(f"⭐ {player['rating']:.1f} | 💰 {player['value']} | {player['payment']}")
        message_lines.append("")
    
    # Construir teclado con 2 botones por fila
    keyboard = []
    temp_row = []
    
    for i, player in enumerate(jugadores_pagina, 1):
        btn_text = f"🔍 {player['name'][:10]}"  # Nombre corto para el botón
        if player['comprado']:
            btn_text += "🛒"  # Indicador de comprado
            
        callback_data = f"ver_jugador_{player['id']}"
        
        temp_row.append(InlineKeyboardButton(
            btn_text,
            callback_data=callback_data
        ))
        
        if i % 2 == 0 or i == len(jugadores_pagina):
            keyboard.append(temp_row)
            temp_row = []
    
    # Botones de paginación (2 por fila)
    pagination_row = []
    if page > 1:
        pagination_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f'mercado_equipo_{team_id}_{page-1}'))
    if page < total_paginas:
        pagination_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f'mercado_equipo_{team_id}_{page+1}'))
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Botón de volver
    keyboard.append([InlineKeyboardButton("🔙 Volver a equipos", callback_data='mercado_equipos')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviar mensaje con logo del equipo si está disponible
    try:
        if team_logo:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=team_logo,
                caption="\n".join(message_lines),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            await query.delete_message()
        else:
            await query.edit_message_text(
                text="\n".join(message_lines),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    except Exception as e:
        logging.error(f"Error al mostrar jugadores: {str(e)}")
        await query.edit_message_text(
            text="\n".join(message_lines),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )




async def ver_jugador(update: Update, context: CallbackContext):
    """Muestra detalles del jugador con información de precios y saldos"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    async with lock_data:
        user_data = await load_data()
        fantasy_data = await load_fantasy_data()
        with open(PLAYERS_FILE, 'r') as f:
            players_data = json.load(f)
    
    # Obtener saldos del usuario
    balance = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
    bono = user_data["Bono_apuesta"].get(user_id, {}).get("Bono", 0)
    credito = fantasy_data.get(user_id, {}).get("credits", 0)
    
    # Buscar jugador en datos base
    player_info = None
    for player in players_data:
        if str(player["player"]["id"]) == player_id and player.get('statistics'):
            stats = player['statistics'][0]
            rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
            if rating >= MIN_RATING:
                player_info = {
                    "id": player["player"]["id"],
                    "name": player["player"]["name"],
                    "position": stats["games"]["position"],
                    "rating": rating,
                    "value": calculate_player_value(player, stats),
                    "team": stats["team"]["name"],
                    "team_logo": stats["team"]["logo"],
                    "photo": player["player"].get("photo", ""),
                    "age": player["player"].get("age", "N/A"),
                    "nationality": player["player"].get("nationality", "N/A"),
                    "height": player["player"].get("height", "N/A"),
                    "weight": player["player"].get("weight", "N/A"),
                    "goals": stats["goals"]["total"] or 0,
                    "assists": stats["goals"]["assists"] or 0,
                    "key_passes": stats["passes"]["key"] or 0,
                    "tackles": stats["tackles"]["total"] or 0,
                    "interceptions": stats["tackles"]["interceptions"] or 0,
                    "minutes": stats["games"]["minutes"] or 0
                }
                break
    
    if not player_info:
        await query.edit_message_text("❌ Jugador no disponible.")
        return
    
    # Buscar si el jugador está en algún equipo
    owner_info = None
    for uid, user_team in fantasy_data.items():
        if isinstance(user_team, dict) and 'team' in user_team:
            for player in user_team['team']:
                if str(player['id']) == player_id:
                    owner_data = user_data["usuarios"].get(uid, {})
                    owner_info = {
                        "user_id": uid,
                        "name": owner_data.get("Nombre", "Usuario Desconocido"),
                        "team_value": user_team.get("value", 0)
                    }
                    break
            if owner_info:
                break
    
    # Construir mensaje
    message_lines = [
        f"<b>{player_info['name']}</b>",
        f"📌 {player_info['position']} | ⭐ {player_info['rating']:.1f} | 🏟 {player_info['team']}",
        f"🎂 {player_info['age']} | 🌍 {player_info['nationality']} | 📏 {player_info['height']}",
        "",
        f"<b>💰 Valor de mercado:</b> {player_info['value']}",
    ]
    
    # Añadir información del propietario si existe
    if owner_info:
        message_lines.extend([
            "",
            f"<b>👤 Propietario actual:</b> {owner_info['name']}",
            f"<b>💎 Valor de su equipo:</b> {owner_info['team_value']}",
            "",
            "<b>🛒 Este jugador tiene dueño, pero puedes hacer una oferta:</b>"
        ])
    else:
        # Determinar categoría y métodos de pago solo si no tiene dueño
        if player_info["rating"] > 7.5:
            player_type = "💎 TOP"
            payment_type = "💵 Balance"
        elif player_info["rating"] > 6.5:
            player_type = "🔹 MEDIO"
            payment_type = "💳 Bono o Balance"
        else:
            player_type = "⚪ NORMAL"
            payment_type = "🪙 Créditos, Bono o Balance"
        
        message_lines.append(f"<b>📋 Categoría:</b> {player_type} ({payment_type})")
    
    message_lines.extend([
        "",
        f"<b>📊 Estadísticas esta temporada:</b>",
        f"⚽ Goles: {player_info['goals']} | 🎯 Asistencias: {player_info['assists']}",
        f"🔑 Pases clave: {player_info['key_passes']} | 🛡 Tackles: {player_info['tackles']}",
        f"🔄 Intercepciones: {player_info['interceptions']} | ⏱ Minutos: {player_info['minutes']}",
        "",
        f"<b>💳 Tus saldos disponibles:</b>",
        f"- 💵 Balance: ${balance:.2f}",
        f"- 💳 Bono: {bono}",
        f"- 🪙 Créditos: {credito}"
    ])
    
    # Construir teclado según si tiene dueño o no
    keyboard = []
    
    if owner_info:
        # Jugador tiene dueño - opción de hacer oferta
        if owner_info["user_id"] != user_id:  # No permitir ofertar por tu propio jugador
            # Calcular precio mínimo de oferta (110% del valor)
            min_offer = player_info["value"] * 1.1
            
            if balance >= min_offer:
                keyboard.append([InlineKeyboardButton(
                    f"💵 Ofertar (${min_offer:.2f} mínimo)", 
                    callback_data=f'hacer_oferta_{player_id}'
                )])
            else:
                message_lines.append(f"❌ Necesitas al menos ${min_offer:.2f} en balance para ofertar")
    else:
        # Jugador disponible para compra normal
        message_lines.append("\n<b>🛒 Opciones de compra:</b>")
        payment_options = []
        player_value = player_info['value']
        
        if player_info["rating"] > 7.5:  # TOP - solo balance
            required = player_value * (1 + MARKET_TAX)
            if balance >= required:
                payment_options.append((f"💵 Balance (${required:.2f})", f"comprar_balance_{player_id}"))
        elif player_info["rating"] > 6.5:  # MEDIO - bono o balance
            if bono >= player_value:
                payment_options.append((f"💳 Bono ({player_value})", f"comprar_bono_{player_id}"))
            required = player_value * (1 + MARKET_TAX)
            if balance >= required:
                payment_options.append((f"💵 Balance (${required:.2f})", f"comprar_balance_{player_id}"))
        else:  # NORMAL - créditos, bono o balance
            if credito >= player_value:
                payment_options.append((f"🪙 Créditos ({player_value})", f"comprar_creditos_{player_id}"))
            if bono >= player_value:
                payment_options.append((f"💳 Bono ({player_value})", f"comprar_bono_{player_id}"))
            required = player_value * (1 + MARKET_TAX)
            if balance >= required:
                payment_options.append((f"💵 Balance (${required:.2f})", f"comprar_balance_{player_id}"))
        
        for method, callback_data in payment_options:
            keyboard.append([InlineKeyboardButton(method.split(' (')[0], callback_data=callback_data)])
        
        if not payment_options:
            message_lines.append("❌ No tienes fondos suficientes para comprar este jugador")
    
    # Botón de volver
    keyboard.append([InlineKeyboardButton("🔙 Volver al listado", callback_data='mercado_volver')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviar mensaje
    try:
        if player_info['photo']:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=player_info['photo'],
                caption="\n".join(message_lines),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            await query.delete_message()
        else:
            await query.edit_message_text(
                text="\n".join(message_lines),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    except Exception as e:
        logging.error(f"Error al mostrar jugador: {str(e)}")
        await query.edit_message_text(
            text="\n".join(message_lines),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        
async def mercado_volver(update: Update, context: CallbackContext):
    """Regresa al listado anterior de jugadores"""
    query = update.callback_query
    await query.answer()
    
    # Recuperar el último contexto de listado desde user_data
    if 'last_market_page' in context.user_data:
        team_id = context.user_data['last_market_page']['team_id']
        page = context.user_data['last_market_page']['page']
        
        # Actualizar el contexto antes de llamar a listar_jugadores_equipo
        context.user_data['current_team'] = team_id
        context.user_data['current_page'] = page
        
        await listar_jugadores_equipo(update, context)
    else:
        await show_market_main_menu(update, context)

async def comprar_jugador(update: Update, context: CallbackContext):
    """Procesa la compra con manejo correcto de JSON y fotos"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    method = data_parts[1]
    player_id = data_parts[2]
    user_id = str(query.from_user.id)
    
    try:
        async with lock_data:
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
            
            with open(PLAYERS_FILE, 'r') as f:
                players_data = json.load(f)
        
        # Buscar jugador
        player_info = None
        for player in players_data:
            if str(player["player"]["id"]) == player_id and player.get('statistics'):
                stats = player['statistics'][0]
                rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
                if rating >= MIN_RATING:
                    player_info = {
                        "player_data": player,
                        "stats": stats,
                        "rating": rating,
                        "value": calculate_player_value(player, stats),
                        "photo": player["player"].get("photo", "")
                    }
                    break
        
        if not player_info:
            await query.edit_message_text("❌ Jugador no disponible.")
            return
        
        # Verificar si ya fue comprado
        for uid, user_team in fantasy_data.items():
            if isinstance(user_team, dict) and 'team' in user_team:
                if any(str(p.get('id')) == player_id for p in user_team['team']):
                    await query.edit_message_text("❌ Este jugador ya ha sido adquirido.")
                    return
        
        # Calcular valores de compra
        player_value = player_info["value"]
        impuesto = 0
        payment_msg = ""
        
        if method == "balance":
            required = player_value * (1 + MARKET_TAX)
            payment_msg = f"💵 ${required:.2f} (Balance Real)"
            impuesto = required - player_value
        elif method == "bono":
            required = player_value
            payment_msg = f"💳 {required} (Bono)"
        elif method == "creditos":
            required = player_value
            payment_msg = f"🪙 {required} (Créditos)"
        
        # Mostrar mensaje de confirmación
        confirm_message = (
            f"🛒 <b>CONFIRMAR COMPRA</b>\n\n"
            f"Estás a punto de comprar:\n"
            f"👤 <b>{player_info['player_data']['player']['name']}</b>\n"
            f"📌 Posición: {player_info['stats']['games']['position']}\n"
            f"⭐ Rating: {player_info['rating']:.1f}\n"
            f"💰 Valor: {player_value}\n"
            f"💳 Método de pago: {payment_msg}\n"
            f"{f'💸 Impuesto: {impuesto:.2f}' if impuesto > 0 else ''}\n\n"
            f"¿Confirmas esta compra?"
        )
        
        # Crear teclado de confirmación
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmar", callback_data=f'confirmar0_compra_{method}_{player_id}'),
                InlineKeyboardButton("❌ Cancelar", callback_data='cancelar_compra')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Manejo de la foto del jugador para la confirmación
        if player_info['photo']:
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=player_info['photo'],
                        caption=confirm_message,
                        parse_mode='HTML'
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.warning(f"No se pudo editar mensaje con foto: {str(e)}")
                try:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=player_info['photo'],
                        caption=confirm_message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                    await query.delete_message()
                except Exception as e:
                    logging.error(f"Error al enviar foto: {str(e)}")
                    await query.edit_message_text(
                        text=confirm_message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
        else:
            await query.edit_message_text(
                text=confirm_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    
    except Exception as e:
        logging.error(f"Error en comprar_jugador: {str(e)}")
        await query.edit_message_text("❌ Error al procesar la compra.")

async def confirmar_compra_handler(update: Update, context: CallbackContext):
    """Procesa la confirmación de compra con manejo robusto de mensajes"""
    query = update.callback_query
    await query.answer()
    
    
    
    try:
        # Extraer datos del callback
        data_parts = query.data.split('_')
        method = data_parts[2]
        player_id = data_parts[3]
        user_id = str(query.from_user.id)
        
        # Verificar que player_id sea numérico
        if not player_id.isdigit():
            await safe_edit_or_reply(context, query, "❌ ID de jugador inválido.")
            return

# Verificar que el método de pago sea válido
        if method not in ["balance", "bono", "creditos"]:
            await safe_edit_or_reply(context, query, "❌ Método de pago no válido.")
            return
        
        async with lock_data:
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
            
            with open(PLAYERS_FILE, 'r') as f:
                players_data = json.load(f)
        
        # Modificar esta parte del código
        player_in_file = None
        for p in players_data:
            try:
                if str(p["player"]["id"]) == player_id:
                    player_in_file = p
                    break
            except (KeyError, TypeError):
                continue

        if not player_in_file:
            logging.error(f"Jugador no encontrado. ID buscado: {player_id}")
            logging.error(f"Ejemplo de IDs disponibles: {[str(p.get('player', {}).get('id')) for p in players_data[:5]]}")
            await safe_edit_or_reply(context, query, "❌ Error: Jugador no encontrado en el sistema.")
            return
        
        # 2. Verificar si cumple requisitos
        if not (player_in_file.get('statistics') and player_in_file['statistics']):
            await safe_edit_or_reply(context, query, "❌ Jugador no tiene estadísticas disponibles.")
            return
            
        stats = player_in_file['statistics'][0]
        rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
        if rating < MIN_RATING:
            await safe_edit_or_reply(context, query, f"❌ Rating del jugador ({rating}) es menor al mínimo requerido ({MIN_RATING}).")
            return
            
            # Validación adicional para créditos (límite de 15 jugadores)
        if method == "creditos":
            user_fantasy = fantasy_data.get(user_id, {})
            current_players = user_fantasy.get('team', [])
        
        # Contar jugadores únicos (por ID)
            unique_player_ids = set()
            for player in current_players:
                player_id_str = str(player.get('id'))
                if player_id_str:
                    unique_player_ids.add(player_id_str)
        
            if len(unique_player_ids) >= 15:  # Límite alcanzado
                await safe_edit_or_reply(
                context,
                query,
                "❌ <b>LÍMITE DE JUGADORES EXCEDIDO</b>\n\n"
                "No puedes comprar más jugadores con créditos porque ya tienes 15 jugadores en tu equipo.\n\n"
                "💡 Opciones:\n"
                "- Vende algunos jugadores primero\n"
                "- Usa otro método de pago (Balance/Bono)"
            )
                return
            
            
        
        player_info = {
            "player_data": player_in_file,
            "stats": stats,
            "rating": rating,
            "value": calculate_player_value(player_in_file, stats),
            "photo": player_in_file["player"].get("photo", "")
        }
        
        # 3. Verificar si ya fue comprado
        for uid, user_team in fantasy_data.items():
            if isinstance(user_team, dict) and 'team' in user_team:
                if any(str(p.get('id')) == player_id for p in user_team['team']):
                    owner_name = user_data["usuarios"].get(uid, {}).get("Nombre", "otro usuario")
                    await safe_edit_or_reply(
                        context, 
                        query,
                        f"❌ {player_in_file['player']['name']} ya fue adquirido por {owner_name}.\n\n"
                        f"ℹ️ Puedes intentar hacer una oferta si está en venta."
                    )
                    return
        
        # 4. Procesar el pago
        player_value = player_info["value"]
        success = False
        impuesto = 0
        
        if method == "balance":
            required = player_value * (1 + MARKET_TAX)
            if user_data["usuarios"].get(user_id, {}).get("Balance", 0) >= required:
                user_data["usuarios"][user_id]["Balance"] -= required
                success = True
                payment_msg = f"💵 ${required:.2f} (Balance Real)"
                impuesto = required - player_value
        elif method == "bono":
            if user_data["Bono_apuesta"].get(user_id, {}).get("Bono", 0) >= player_value:
                user_data["Bono_apuesta"][user_id]["Bono"] -= player_value
                success = True
                payment_msg = f"💳 {player_value} (Bono)"
        elif method == "creditos":
            if fantasy_data.get(user_id, {}).get("credits", 0) >= player_value:
                fantasy_data[user_id]["credits"] -= player_value
                success = True
                payment_msg = f"🪙 {player_value} (Créditos)"
        
        if not success:
            await safe_edit_or_reply(context, query, "❌ Fondos insuficientes para completar la compra.")
            return
        
        # 5. Añadir jugador al equipo
        new_player = {
            "id": int(player_id),
            "name": player_in_file["player"]["name"],
            "is_titular": False,
            "firstname": player_in_file["player"].get("firstname", ""),
            "lastname": player_in_file["player"].get("lastname", ""),
            "position": stats["games"]["position"],
            "normalized_position": get_normalized_position(stats["games"]["position"]),
            "age": player_in_file["player"].get("age"),
            "team": stats["team"]["name"],
            "team_id": stats["team"]["id"],
            "team_logo": stats["team"]["logo"],
            "photo": player_in_file["player"].get("photo", ""),
            "rating": rating,
            "value": player_value,
            "goals": stats["goals"]["total"] or 0,
            "assists": stats["goals"]["assists"] or 0,
            "key_passes": stats["passes"]["key"] or 0,
            "tackles": stats["tackles"]["total"] or 0,
            "appearances": stats["games"]["appearences"] or 0
        }
        
        # Configurar como titular si hay espacio
        if user_id in fantasy_data:
            titulares = sum(1 for p in fantasy_data[user_id]['team'] if p.get('is_titular', False))
            if titulares < 11:
                new_player['is_titular'] = True
        else:
            fantasy_data[user_id] = {
                "credits": 0,
                "team": [],
                "formation": BASE_FORMATION,
                "value": 0
            }
        
        fantasy_data[user_id]["team"].append(new_player)
        fantasy_data[user_id]["value"] += player_value
        
        if impuesto > 0:
            fantasy_data["bote"] = fantasy_data.get("bote", 0) + impuesto
        
        # 6. Guardar cambios
        await save_data(user_data)
        await save_fantasy_data(fantasy_data)
        
        # 7. Notificar al grupo de registro
        registro_msg = (
            f"🛒 <b>NUEVA COMPRA REGISTRADA</b>\n\n"
            f"👤 <b>Usuario:</b> {user_data['usuarios'].get(user_id, {}).get('Nombre', 'Usuario')}\n"
            f"⚽ <b>Jugador:</b> {new_player['name']}\n"
            f"🏟 <b>Equipo:</b> {new_player['team']}\n"
            f"💰 <b>Valor:</b> {player_value}\n"
            f"💳 <b>Método de pago:</b> {payment_msg}\n"
            f"🕒 <b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        try:
            if player_info['photo']:
                await context.bot.send_photo(
                    chat_id=REGISTRO_MINIJUEGOS,
                    photo=player_info['photo'],
                    caption=registro_msg,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=REGISTRO_MINIJUEGOS,
                    text=registro_msg,
                    parse_mode='HTML'
                )
        except Exception as e:
            logging.error(f"Error notificando al grupo: {str(e)}")
        
        # 8. Mostrar confirmación al usuario
        success_msg = (
            f"✅ <b>¡Compra exitosa!</b>\n\n"
            f"<b>Jugador:</b> {new_player['name']}\n"
            f"<b>Posición:</b> {new_player['position']}\n"
            f"<b>Valor:</b> {player_value}\n"
            f"<b>Método de pago:</b> {payment_msg}\n"
            f"{f'<b>Impuesto:</b> {impuesto:.2f}' if impuesto > 0 else ''}"
        )
        
        keyboard = [
            [InlineKeyboardButton("👀 Ver Mi Equipo", callback_data='mi_equipo')],
            [InlineKeyboardButton("🛒 Seguir Comprando", callback_data='mercado_volver')]
        ]
        
        await safe_edit_or_reply(
            context,
            query,
            success_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            photo=player_info['photo'] if player_info['photo'] else None
        )
    
    except Exception as e:
        logging.error(f"Error crítico en confirmar_compra_handler: {str(e)}")
        traceback.print_exc()
        await safe_edit_or_reply(
            context,
            query,
            "⚠️ Error crítico al procesar tu compra. Por favor intenta nuevamente."
        )

async def safe_edit_or_reply(context, query, text, reply_markup=None, photo=None):
    """Función segura para editar o responder mensajes"""
    try:
        if photo:
            # Si hay foto, intentamos editar el mensaje existente como foto
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=photo, caption=text, parse_mode='HTML'),
                    reply_markup=reply_markup
                )
                return
            except Exception as e:
                logging.warning(f"No se pudo editar mensaje con foto: {str(e)}")
                # Si falla, enviamos nuevo mensaje con foto
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                await query.delete_message()
                return
        
        # Para mensajes sin foto
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            if "no text in the message" in str(e):
                # Si el mensaje original no tiene texto, enviamos uno nuevo
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                await query.delete_message()
            else:
                raise
    except Exception as e:
        logging.error(f"Error en safe_edit_or_reply: {str(e)}")
        # Último intento de enviar mensaje sin formato
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text[:4000]  # Limitamos por si acaso
            )
        except Exception as e:
            logging.error(f"Error crítico al enviar mensaje de fallback: {str(e)}")

async def cancelar_compra(update: Update, context: CallbackContext):
    """Maneja la cancelación de la compra"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Compra cancelada.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Volver al mercado", callback_data='mercado_volver')]
        ]),
        parse_mode='HTML'
    )

        
def calculate_player_value(player_data: Dict, stats: Dict) -> int:
    """Calcula el valor de un jugador entre 50 y 300 considerando múltiples factores"""
    try:
        # 1. Obtener rating base (asegurar que está entre 3.0 y 10.0)
        rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
        rating = max(MIN_RATING, min(10.0, rating))
        
        # 2. Normalizar posición
        position = get_normalized_position(stats["games"]["position"])
        
        # 3. Obtener estadísticas básicas
        age = player_data["player"]["age"]
        appearances = stats["games"]["appearences"] or 0
        goals = stats["goals"]["total"] or 0
        assists = stats["goals"]["assists"] or 0
        key_passes = stats["passes"]["key"] or 0
        tackles = stats["tackles"]["total"] or 0
        
        # 4. Cálculo del valor con nuevos parámetros ajustados
        # Valor base ajustado (rango más pequeño)
        base_value = rating * 20 * POSITION_WEIGHTS.get(position, 1.0)  # Reducido de 50 a 20
        
        # Bonificaciones por rendimiento (impacto reducido)
        performance_bonus = (goals * 5) + (assists * 3) + (key_passes * 0.5) + (tackles * 0.3)
        
        # Ajuste por edad (menor impacto)
        age_factor = 1.2 if age < 21 else (1.1 if age < 25 else 1.0)
        
        # Ajuste por participación (menor impacto)
        participation_factor = min(1.3, 0.8 + (appearances / 20)) if appearances > 0 else 0.6
        
        # Cálculo del valor crudo
        raw_value = (base_value + performance_bonus) * age_factor * participation_factor
        
        # 5. Normalizar el valor al rango deseado (50-300)
        # Usamos una función logística para suavizar la distribución
        min_val = 50
        max_val = 300
        normalized_value = min_val + (max_val - min_val) * (1 / (1 + 10 ** (-(raw_value - 150)/50)))
        
        # Redondear y asegurar los límites
        final_value = int(round(max(min_val, min(max_val, normalized_value))))
        
        return final_value
        
    except (KeyError, TypeError):
        return 50  # Valor mínimo por defecto        
    
async def confirmar_venta(update: Update, context: CallbackContext):
    """Muestra la confirmación para vender un jugador con botones"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    async with lock_data:
        user_fantasy = await load_data()
        
        # Verificar si el jugador existe en el equipo del usuario
        player_info = None
        if user_id in user_fantasy and 'team' in user_fantasy[user_id]:
            for player in user_fantasy[user_id]['team']:
                if str(player['id']) == player_id:
                    player_info = player
                    break
    
    if not player_info:
        await query.edit_message_text(
            "<pre>❌ ERROR</pre>\n"
            "El jugador no se encuentra en tu equipo.",
            parse_mode='HTML'
        )
        return
    
    # Calcular valor de venta después de impuestos
    valor_venta = player_info['value'] * (1 - MARKET_TAX)
    impuesto = player_info['value'] * MARKET_TAX
    
    # Verificar si el jugador tiene ofertas pendientes
    tiene_ofertas = False
    if 'ofertas' in user_fantasy:
        for oferta in user_fantasy['ofertas'].values():
            if str(oferta.get('player_id')) == player_id and oferta['vendedor_id'] == user_id:
                tiene_ofertas = True
                break
    
    # Crear mensaje de confirmación
    message = (
        f"<pre>💰 CONFIRMAR VENTA</pre>\n\n"
        f"<b>Jugador:</b> {player_info['name']}\n"
        f"<b>Posición:</b> {player_info['position']}\n"
        f"<b>Valor actual:</b> <code>${player_info['value']:.2f}</code>\n"
        f"<b>Recibirás:</b> <code>${valor_venta:.2f}</code> (créditos)\n"
        f"<b>Impuesto:</b> <code>${impuesto:.2f}</code>\n\n"
    )
    
    if tiene_ofertas:
        message += "⚠️ <i>Este jugador tiene ofertas pendientes que se cancelarán si lo vendes.</i>\n\n"
    
    message += "¿Confirmas que deseas vender este jugador?"
    
    # Crear teclado con opciones
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar Venta", callback_data=f'procesar_venta_{player_id}'),
            InlineKeyboardButton("🔙 Cancelar", callback_data='mercado_mis_ventas')
        ]
    ]
    
    if tiene_ofertas:
        keyboard.insert(0, [
            InlineKeyboardButton("📊 Ver Ofertas", callback_data=f'ver_ofertas_{player_id}')
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )    
async def cancelar_oferta(update: Update, context: CallbackContext):
    """Cancela el proceso de oferta"""
    query = update.callback_query
    await query.answer()
    
    # Limpiar estado
    context.user_data['estado'] = None
    if 'oferta_player_id' in context.user_data:
        del context.user_data['oferta_player_id']
    
    await query.edit_message_text("❌ Oferta cancelada.")

async def listar_mis_ventas(update: Update, context: CallbackContext):
    """Lista los jugadores que el usuario tiene en venta"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    async with lock_data:
        user_fantasy = await load_data()
    
    if user_id not in user_fantasy or 'team' not in user_fantasy[user_id]:
        await query.edit_message_text("❌ No tienes jugadores en tu equipo.")
        return
    
    # Construir lista de jugadores con botones para vender
    keyboard = []
    message_lines = ["💰 *Mis Jugadores Disponibles para Venta:*\n"]
    
    for player in user_fantasy[user_id]["team"]:
        # Verificar si ya tiene ofertas
        tiene_ofertas = False
        if 'ofertas' in user_fantasy:
            for oferta in user_fantasy['ofertas'].values():
                if oferta['vendedor_id'] == user_id and str(oferta.get('player_id', '')) == str(player['id']):
                    tiene_ofertas = True
                    break
        
        message_lines.append(
            f"👤 *{player['name']}* ({player['position']})\n"
            f"⭐ {player['rating']} | 💰 Valor: {player['value']}\n"
            f"🔄 Valor de venta: {player['value'] * (1 - MARKET_TAX):.2f}\n"
            f"{'⚠️ Tiene ofertas pendientes' if tiene_ofertas else ''}\n"
        )
        
        row_buttons = [
            InlineKeyboardButton(
                f"Vender {player['name']}",
                callback_data=f'mercado_vender_{player["id"]}'
            )
        ]
        
        if tiene_ofertas:
            row_buttons.append(
                InlineKeyboardButton(
                    "Ver Ofertas",
                    callback_data=f'ver_ofertas_{player["id"]}'
                )
            )
        
        keyboard.append(row_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🔙 Volver", callback_data='mercado_menu'),
        InlineKeyboardButton("🔄 Actualizar", callback_data='mercado_mis_ventas')
    ])
    
    await query.edit_message_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
async def ver_ofertas_jugador(update: Update, context: CallbackContext):
    """Muestra las ofertas recibidas por un jugador específico"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    async with lock_data:
        user_fantasy = await load_data()
    
    if 'ofertas' not in user_fantasy:
        await query.edit_message_text("❌ No hay ofertas para este jugador.")
        return
    
    # Filtrar ofertas para este jugador y usuario
    ofertas_jugador = []
    for oferta_id, oferta in user_fantasy['ofertas'].items():
        if str(oferta.get('player_id', '')) == player_id and oferta['vendedor_id'] == user_id:
            ofertas_jugador.append(oferta)
    
    if not ofertas_jugador:
        await query.edit_message_text("❌ No hay ofertas para este jugador.")
        return
    
    # Obtener información del jugador
    player_info = None
    for player in user_fantasy[user_id]['team']:
        if str(player['id']) == player_id:
            player_info = player
            break
    
    if not player_info:
        await query.edit_message_text("❌ Jugador no encontrado en tu equipo.")
        return
    
    # Construir mensaje
    message_lines = [
        f"📊 *Ofertas para {player_info['name']}*\n",
        f"Valor actual: 💰 {player_info['value']}\n"
    ]
    
    keyboard = []
    
    for i, oferta in enumerate(ofertas_jugador, 1):
        message_lines.append(
            f"\n{i}. Oferta: 💰 {oferta['monto']:.2f}\n"
            f"   Fecha: {oferta['fecha']}\n"
            f"   Estado: {oferta['estado']}"
        )
        
        if oferta['estado'] == 'pendiente':
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Aceptar oferta #{i}",
                    callback_data=f'aceptar_oferta_{oferta_id}'
                ),
                InlineKeyboardButton(
                    f"❌ Rechazar oferta #{i}",
                    callback_data=f'rechazar_oferta_{oferta_id}'
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Volver", callback_data='mercado_mis_ventas')
    ])
    
    await query.edit_message_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )    
async def mostrar_formulario_oferta(update: Update, context: CallbackContext):
    """Muestra el formulario para hacer una oferta por un jugador (versión con HTML)"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    
    # Guardar información en user_data para el próximo mensaje
    context.user_data['estado'] = 'ESPERANDO_MONTO_OFERTA'
    context.user_data['oferta_player_id'] = player_id
    
    # Obtener información del jugador
    async with lock_data:
        user_fantasy = await load_data()
        player_info = None
        for user_team in user_fantasy.values():
            if isinstance(user_team, dict) and 'team' in user_team:
                for player in user_team['team']:
                    if str(player['id']) == player_id:
                        player_info = player
                        break
                if player_info:
                    break
    
    if not player_info:
        await query.edit_message_text(
            "<pre>❌ NO DISPONIBLE</pre>\n"
            "Este jugador ya no está disponible para ofertas.",
            parse_mode='HTML'
        )
        context.user_data['estado'] = None
        return
    
    # Crear mensaje con formato HTML
    mensaje = (
        f"<pre>💵 OFERTA POR {player_info['name'].upper()}</pre>\n\n"
        f"<b>Valor actual:</b> <code>${player_info['value']:.2f}</code>\n"
        f"<b>Oferta mínima requerida:</b> <code>${player_info['value'] * 1.1:.2f}</code>\n\n"
        "Por favor, envía el monto que deseas ofertar (en Balance Real).\n\n"
        "Ejemplo: <code>150.00</code>"
    )
    
    # Teclado con botón de cancelar
    keyboard = [
        [InlineKeyboardButton("❌ Cancelar Oferta", callback_data='cancelar_oferta')]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    


    


async def poner_en_venta_handler(update: Update, context: CallbackContext):
    """Manejador para poner un jugador en venta"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    async with lock_data:
        fantasy_data = await load_fantasy_data()
        
        # Buscar el jugador en el equipo del usuario
        player_info = None
        for player in fantasy_data.get(user_id, {}).get('team', []):
            if str(player['id']) == player_id:
                player_info = player
                break
    
    if not player_info:
        await query.edit_message_text("❌ Jugador no encontrado en tu equipo.")
        return
    
    # Crear teclado con opciones de precio de venta (basado en valor actual)
    base_value = player_info['value']
    min_price = base_value * 0.9  # 90% del valor
    suggested_price = base_value * 1.5  # 150% del valor
    
    keyboard = [
        [InlineKeyboardButton(f"💰 ${base_value:.2f} (Valor actual)", callback_data=f'venta_precio_{player_id}_{base_value}')],
        [InlineKeyboardButton(f"💎 ${suggested_price:.2f} (Recomendado)", callback_data=f'venta_precio_{player_id}_{suggested_price}')],
        [InlineKeyboardButton("🔢 Ingresar precio manual", callback_data=f'venta_manual_{player_id}')],
        [InlineKeyboardButton("🔙 Cancelar", callback_data='mi_equipo')]
    ]
    
    message = (
        f"⚽ <b>Poner en venta a {player_info['name']}</b>\n\n"
        f"⭐ Rating: {player_info['rating']}\n"
        f"💰 Valor actual: ${base_value:.2f}\n\n"
        f"<b>Opciones de precio:</b>\n"
        f"- Mínimo permitido: ${min_price:.2f}\n"
        f"- Recomendado: ${suggested_price:.2f}\n\n"
        f"Selecciona una opción o ingresa un precio manualmente:"
    )
    
    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def procesar_venta_manual(update: Update, context: CallbackContext):
    """Procesa el precio manual para poner un jugador en venta"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    context.user_data['venta_player_id'] = player_id
    context.user_data['estado'] = 'ESPERANDO_PRECIO_VENTA'
    
    await query.edit_message_text(
        "📝 Ingresa el precio al que deseas vender este jugador (ejemplo: 1500.50):",
        parse_mode='HTML'
    )

async def confirmar_venta_jugador(update: Update, context: CallbackContext):
    """Confirma la venta de un jugador con el precio establecido"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    player_id = data[2]
    precio = float(data[3])
    user_id = str(query.from_user.id)
    
    async with lock_data:
        fantasy_data = await load_fantasy_data()
        
        # Verificar que el jugador sigue en el equipo
        player_info = None
        for player in fantasy_data.get(user_id, {}).get('team', []):
            if str(player['id']) == player_id:
                player_info = player
                break
    
    if not player_info:
        await query.edit_message_text("❌ Jugador no encontrado en tu equipo.")
        return
    
    # Verificar precio mínimo (90% del valor)
    min_price = player_info['value'] * 0.9
    if precio < min_price:
        await query.edit_message_text(f"❌ El precio mínimo permitido es ${min_price:.2f}")
        return
    
    # Crear entrada de jugador en venta
    if 'jugadores_venta' not in fantasy_data:
        fantasy_data['jugadores_venta'] = {}
    
    fantasy_data['jugadores_venta'][player_id] = {
        'vendedor_id': user_id,
        'precio': precio,
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'jugador_info': player_info
    }
    
    await save_fantasy_data(fantasy_data)
    
    await query.edit_message_text(
        f"✅ <b>{player_info['name']} ha sido puesto en venta por ${precio:.2f}</b>\n\n"
        f"Los demás usuarios ahora pueden hacer ofertas por este jugador.",
        parse_mode='HTML'
    )

async def hacer_oferta_handler(update: Update, context: CallbackContext):
    """Manejador para hacer una oferta por un jugador en venta"""
    query = update.callback_query
    await query.answer()
    
    try:
        player_id = query.data.split('_')[-1]
        user_id = str(query.from_user.id)
        
        async with lock_data:
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
            
            # Verificar que el jugador está en algún equipo (tiene dueño)
            player_in_team = False
            owner_info = None
            for uid, user_team in fantasy_data.items():
                if isinstance(user_team, dict) and 'team' in user_team:
                    for player in user_team['team']:
                        if str(player['id']) == player_id:
                            player_in_team = True
                            owner_data = user_data["usuarios"].get(uid, {})
                            owner_info = {
                                "user_id": uid,
                                "name": owner_data.get("Nombre", "Usuario Desconocido"),
                                "team_value": user_team.get("value", 0)
                            }
                            break
                    if owner_info:
                        break
            
            if not player_in_team:
                # Intenta enviar un nuevo mensaje en lugar de editar
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ Este jugador ya no está disponible para ofertas."
                )
                return
            
            # Verificar que no es el dueño
            if owner_info["user_id"] == user_id:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ No puedes hacer oferta por tu propio jugador."
                )
                return
            
            # Obtener información del jugador
            player_info = None
            for player in user_team['team']:
                if str(player['id']) == player_id:
                    player_info = player
                    break
            
            if not player_info:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ Jugador no encontrado."
                )
                return
        
        # Obtener saldos del usuario
        balance = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
        
        # Calcular precio mínimo de oferta (110% del valor)
        min_offer = player_info['value'] * 1.1
        
        # Construir mensaje
        message_text = (
            f"⚽ <b>Oferta por {player_info['name']}</b>\n"
            f"⭐ Rating: {player_info['rating']} | 💰 Valor: {player_info['value']}\n"
            f"🏟 Equipo: {player_info['team']} | 🎂 Edad: {player_info['age']}\n"
            f"👤 Dueño actual: {owner_info['name']}\n\n"
            f"<b>Oferta mínima requerida:</b> ${min_offer:.2f}\n"
            f"<b>Tu balance disponible:</b> ${balance:.2f}\n\n"
            "Por favor, envía el monto que deseas ofertar:"
        )
        
        # Guardar información en user_data para el próximo mensaje
        context.user_data['estado'] = 'ESPERANDO_MONTO_OFERTA'
        context.user_data['oferta_player_id'] = player_id
        context.user_data['oferta_minima'] = min_offer
        context.user_data['owner_id'] = owner_info['user_id']
        
        # Teclado con botón de cancelar
        keyboard = [
            [InlineKeyboardButton("❌ Cancelar", callback_data='cancelar_oferta')]
        ]
        
        # Intenta editar el mensaje, si falla envía uno nuevo
        try:
            await query.edit_message_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.warning(f"No se pudo editar mensaje: {str(e)}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            await query.delete_message()
    
    except Exception as e:
        logging.error(f"Error en hacer_oferta_handler: {str(e)}")
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ocurrió un error al procesar tu oferta."
            )
        except Exception as e2:
            logging.error(f"Error al enviar mensaje de error: {str(e2)}")
            
            
async def procesar_oferta(update: Update, context: CallbackContext):
    """Procesa el monto de oferta ingresado por el usuario"""
    user_id = str(update.message.from_user.id)
    monto_texto = update.message.text
    
    try:
        # Verificar estado y datos del contexto
        if context.user_data.get('estado') != 'ESPERANDO_MONTO_OFERTA':
            await update.message.reply_text("❌ No hay una oferta en proceso.")
            return
            
        player_id = context.user_data.get('oferta_player_id')
        min_offer = context.user_data.get('oferta_minima')
        owner_id = context.user_data.get('owner_id')
        
        if not all([player_id, min_offer, owner_id]):
            await update.message.reply_text("❌ Error en los datos. Intenta nuevamente.")
            return

        # Validar monto
        try:
            monto = float(monto_texto)
            if monto < min_offer:
                await update.message.reply_text(f"❌ Mínimo requerido: ${min_offer:.2f}")
                return
        except ValueError:
            await update.message.reply_text("❌ Ingresa un número válido (ej: 1500.50)")
            return

        async with lock_data:
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
            
            # Verificar saldo
            balance_actual = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
            if balance_actual < monto:
                await update.message.reply_text(f"❌ Saldo insuficiente. Disponible: ${balance_actual:.2f}")
                return
            
            # Bloquear el monto (descontar temporalmente)
            user_data["usuarios"][user_id]["Balance"] -= monto
            await save_data(user_data)

            # Buscar información del jugador
            jugador_info = None
            for uid, user_team in fantasy_data.items():
                if isinstance(user_team, dict) and 'team' in user_team:
                    for player in user_team['team']:
                        if str(player['id']) == player_id and uid == owner_id:
                            jugador_info = player
                            break
                    if jugador_info:
                        break
            
            if not jugador_info:
                # Devolver dinero si el jugador no está disponible
                user_data["usuarios"][user_id]["Balance"] += monto
                await save_data(user_data)
                await update.message.reply_text("❌ Jugador ya no disponible. Se ha devuelto tu dinero.")
                return

            # Registrar oferta con timestamp de expiración (5 horas)
            oferta_id = str(uuid.uuid4())
            expiration_time = (datetime.now() + timedelta(hours=5)).timestamp()
            
            fantasy_data.setdefault('ofertas', {})[oferta_id] = {
                'player_id': player_id,
                'comprador_id': user_id,
                'vendedor_id': owner_id,
                'precio': monto,
                'metodo': 'balance',
                'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'expira': expiration_time,
                'estado': 'pendiente',
                'jugador_info': jugador_info,
                'saldo_bloqueado': True
            }
            
            await save_fantasy_data(fantasy_data)

        # Notificar al vendedor
        try:
            nombre_comprador = user_data["usuarios"].get(user_id, {}).get("Nombre", "Usuario")
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Aceptar Oferta", callback_data=f'aceptar_oferta_{oferta_id}'),
                    InlineKeyboardButton("❌ Rechazar Oferta", callback_data=f'rechazar_oferta_{oferta_id}')
                ]
            ]
            
            expiracion_str = (datetime.fromtimestamp(expiration_time)).strftime("%d/%m %H:%M")
            
            message_text = (
                f"⚠️ <b>NUEVA OFERTA RECIBIDA</b> (Válida hasta {expiracion_str})\n\n"
                f"⚽ <b>Jugador:</b> {jugador_info['name']}\n"
                f"📌 <b>Posición:</b> {jugador_info['position']}\n"
                f"⭐ <b>Rating:</b> {jugador_info['rating']}\n"
                f"💰 <b>Oferta:</b> ${monto:.2f}\n"
                f"👤 <b>Comprador:</b> {nombre_comprador}\n\n"
                f"Tienes hasta {expiracion_str} para responder."
            )
            
            await context.bot.send_message(
                chat_id=owner_id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error notificando al vendedor: {str(e)}")
            await update.message.reply_text("⚠️ No se pudo notificar al vendedor. Contacta con soporte.")

        # Confirmar al comprador
        await update.message.reply_text(
            f"✅ <b>Oferta enviada correctamente</b>\n\n"
            f"Has ofertado <b>${monto:.2f}</b> por {jugador_info['name']}.\n"
            f"• Se ha bloqueado este monto de tu saldo\n"
            f"• El vendedor tiene hasta {expiracion_str} para responder\n"
            f"• Si es rechazada o expira, se devolverá tu dinero",
            parse_mode='HTML'
        )

        # Limpiar estado
        context.user_data.clear()

    except Exception as e:
        logging.error(f"Error en procesar_oferta: {str(e)}")
        try:
            # Intentar devolver el dinero si hubo error
            async with lock_data:
                user_data = await load_data()
                user_data["usuarios"][user_id]["Balance"] += monto
                await save_data(user_data)
        except:
            pass
        
        await update.message.reply_text(
            "❌ Ocurrió un error al procesar tu oferta. Se ha devuelto tu dinero.",
            parse_mode='HTML'
        )

async def manejar_respuesta_oferta(update: Update, context: CallbackContext):
    """Maneja la respuesta del vendedor a una oferta"""
    query = update.callback_query
    await query.answer()
    
    try:
        print(f"\n=== INICIO manejar_respuesta_oferta ===")
        print(f"Callback data recibido: {query.data}")
        
        # Parsear callback_data correctamente
        if query.data.startswith('aceptar_oferta_'):
            accion = 'aceptar'
            oferta_id = query.data.replace('aceptar_oferta_', '')
        elif query.data.startswith('rechazar_oferta_'):
            accion = 'rechazar'
            oferta_id = query.data.replace('rechazar_oferta_', '')
        else:
            print(f"ERROR: Formato de callback_data no reconocido: {query.data}")
            await query.edit_message_text("❌ Error en el formato de la oferta.")
            return
        
        print(f"Acción: {accion}, Oferta ID: {oferta_id}")
        
        async with lock_data:
            print("Cargando datos...")
            fantasy_data = await load_fantasy_data()
            user_data = await load_data()
            
            print(f"Ofertas existentes: {list(fantasy_data.get('ofertas', {}).keys())}")
            
            # Verificar que la oferta existe
            if 'ofertas' not in fantasy_data or oferta_id not in fantasy_data['ofertas']:
                print(f"ERROR: Oferta {oferta_id} no encontrada")
                await query.edit_message_text("❌ Esta oferta ya no existe.")
                return
                
            oferta = fantasy_data['ofertas'][oferta_id]
            print(f"Oferta encontrada: {oferta}")
            
            # Verificar si la oferta ya expiró
            tiempo_actual = datetime.now().timestamp()
            print(f"Tiempo actual: {tiempo_actual}, Expira: {oferta.get('expira', 0)}")
            
            if tiempo_actual > oferta.get('expira', 0):
                print("Oferta expirada")
                # Devolver dinero si está bloqueado
                if oferta.get('saldo_bloqueado', False):
                    print(f"Devolviendo {oferta['precio']} a {oferta['comprador_id']}")
                    if oferta['comprador_id'] in user_data["usuarios"]:
                        user_data["usuarios"][oferta['comprador_id']]["Balance"] += oferta['precio']
                        await save_data(user_data)
                
                oferta['estado'] = 'expirada'
                await save_fantasy_data(fantasy_data)
                
                await query.edit_message_text("❌ Esta oferta ya ha expirado.")
                return
            
            if oferta['estado'] != 'pendiente':
                print(f"Oferta ya procesada (estado: {oferta['estado']})")
                await query.edit_message_text("❌ Esta oferta ya fue procesada.")
                return
            
            jugador_info = oferta.get('jugador_info', {})
            jugador_nombre = jugador_info.get('name', 'el jugador')
            precio = oferta['precio']
            vendedor_id = oferta['vendedor_id']
            comprador_id = oferta['comprador_id']
            
            print(f"\nProcesando {accion} para jugador: {jugador_nombre}")
            print(f"Precio: {precio}")
            print(f"Vendedor: {vendedor_id}")
            print(f"Comprador: {comprador_id}")
            
            if accion == 'aceptar':
                try:
                    print("\n=== ACEPTANDO OFERTA ===")
                    
                    # 1. Verificar y preparar datos del vendedor
                    if vendedor_id not in fantasy_data:
                        print(f"ERROR: Vendedor {vendedor_id} no tiene equipo")
                        await query.edit_message_text("❌ Error: Vendedor no tiene equipo registrado.")
                        return
                    
                    if 'team' not in fantasy_data[vendedor_id]:
                        print(f"ERROR: Vendedor {vendedor_id} no tiene lista de jugadores")
                        await query.edit_message_text("❌ Error: El equipo del vendedor no tiene jugadores.")
                        return
                    
                    # 2. Quitar jugador del vendedor (con verificación de tipo)
                    equipo_vendedor = fantasy_data[vendedor_id]['team']
                    print(f"Equipo del vendedor antes: {len(equipo_vendedor)} jugadores")
                    print(f"Buscando jugador ID {oferta['player_id']} para eliminar")
                    
                    # Convertir todos los IDs a string para comparación segura
                    equipo_actualizado = [
                        p for p in equipo_vendedor 
                        if str(p.get('id')) != str(oferta['player_id'])
                    ]
                    
                    if len(equipo_actualizado) == len(equipo_vendedor):
                        print("ERROR: Jugador no encontrado en el equipo del vendedor")
                        await query.edit_message_text("❌ Error: El jugador no está en el equipo del vendedor.")
                        return
                    
                    fantasy_data[vendedor_id]['team'] = equipo_actualizado
                    fantasy_data[vendedor_id]['value'] -= jugador_info.get('value', 0)
                    print(f"Equipo del vendedor después: {len(equipo_actualizado)} jugadores")
                    
                    # 3. Añadir jugador al comprador (con creación de equipo si no existe)
                    if comprador_id not in fantasy_data:
                        print(f"Creando nuevo equipo para comprador {comprador_id}")
                        fantasy_data[comprador_id] = {
                            'credits': 0,
                            'team': [],
                            'formation': BASE_FORMATION,
                            'value': 0
                        }
                    
                    print(f"Equipo del comprador antes: {len(fantasy_data[comprador_id]['team'])} jugadores")
                    fantasy_data[comprador_id]['team'].append(jugador_info)
                    fantasy_data[comprador_id]['value'] += jugador_info.get('value', 0)
                  
                    
                    # 4. Transferir dinero al vendedor (con verificación de existencia)
                    if 'usuarios' not in user_data:
                        user_data['usuarios'] = {}
                    if vendedor_id not in user_data['usuarios']:
                        user_data['usuarios'][vendedor_id] = {'Balance': 0}
                    
                 
                    user_data["usuarios"][vendedor_id]["Balance"] = user_data["usuarios"].get(vendedor_id, {}).get("Balance", 0) + precio
                 
                    
                    # 5. Aplicar impuesto
                    impuesto = precio * MARKET_TAX
                    
                    
                    # 6. Actualizar estado
                    oferta['estado'] = 'aceptada'
                    
                    # Guardar cambios
                    print("\nGuardando cambios...")
                    await save_data(user_data)
                    await save_fantasy_data(fantasy_data)
                    print("Datos guardados correctamente")
                    
                    # Notificar al comprador
                    try:
                        print(f"Enviando notificación a comprador {comprador_id}")
                        await context.bot.send_message(
                            chat_id=int(comprador_id),
                            text=f"🎉 <b>¡OFERTA ACEPTADA!</b>\n\n"
                                 f"Has adquirido a {jugador_nombre} por ${precio:.2f}",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        print(f"ERROR al notificar al comprador: {str(e)}")
                    
                    # Actualizar mensaje original
                    print("Actualizando mensaje original")
                    await query.edit_message_text(
                        f"✅ <b>Oferta aceptada</b>\n\n"
                        f"Has vendido a {jugador_nombre} por ${precio:.2f}\n"
                        f"Se aplicó un impuesto de ${impuesto:.2f}.",
                        parse_mode='HTML'
                    )
                    print("=== OFERTA ACEPTADA CON ÉXITO ===")
                    
                except Exception as e:
                    print(f"\nERROR al aceptar oferta: {str(e)}")
                    traceback.print_exc()
                    await query.edit_message_text("❌ Error al aceptar la oferta")
            
            elif accion == 'rechazar':
                try:
                    print("\n=== RECHAZANDO OFERTA ===")
                    
                    # 1. Devolver dinero al comprador (si estaba bloqueado)
                    if oferta.get('saldo_bloqueado', False):
                        print(f"Devolviendo {precio} a comprador {comprador_id}")
                        if 'usuarios' not in user_data:
                            user_data['usuarios'] = {}
                        if comprador_id not in user_data['usuarios']:
                            user_data['usuarios'][comprador_id] = {'Balance': 0}
                        
                        print(f"Balance antes: {user_data['usuarios'].get(comprador_id, {}).get('Balance', 0)}")
                        user_data["usuarios"][comprador_id]["Balance"] = user_data["usuarios"].get(comprador_id, {}).get("Balance", 0) + precio
                        print(f"Balance después: {user_data['usuarios'][comprador_id]['Balance']}")
                    
                    # 2. Actualizar estado
                    oferta['estado'] = 'rechazada'
                    
                    # Guardar cambios
                    print("\nGuardando cambios...")
                    await save_data(user_data)
                    await save_fantasy_data(fantasy_data)
                    print("Datos guardados correctamente")
                    
                    # Notificar al comprador
                    try:
                        print(f"Enviando notificación a comprador {comprador_id}")
                        await context.bot.send_message(
                            chat_id=int(comprador_id),
                            text=f"❌ <b>OFERTA RECHAZADA</b>\n\n"
                                 f"Tu oferta de ${precio:.2f} por {jugador_nombre} "
                                 f"fue rechazada. Se ha devuelto tu dinero.",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        print(f"ERROR al notificar al comprador: {str(e)}")
                    
                    # Actualizar mensaje original
                    print("Actualizando mensaje original")
                    await query.edit_message_text(
                        f"❌ <b>Oferta rechazada</b>\n\n"
                        f"Has rechazado la oferta de ${precio:.2f} por {jugador_nombre}",
                        parse_mode='HTML'
                    )
                    print("=== OFERTA RECHAZADA CON ÉXITO ===")
                    
                except Exception as e:
                    print(f"\nERROR al rechazar oferta: {str(e)}")
                    traceback.print_exc()
                    await query.edit_message_text("❌ Error al rechazar la oferta")
    
    except Exception as e:
        print(f"\nERROR GLOBAL en manejar_respuesta_oferta: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text("❌ Error al procesar tu acción")
        
        
        
        
async def mis_ofertas_handler(update: Update, context: CallbackContext):
    """Muestra las ofertas activas del usuario (jugadores en venta y ofertas recibidas)"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    fantasy_data = await load_fantasy_data()
    
    # Obtener jugadores en venta del usuario
    jugadores_venta = []
    if 'jugadores_venta' in fantasy_data:
        jugadores_venta = [j for j in fantasy_data['jugadores_venta'].values() 
                          if j['vendedor_id'] == user_id]
    
    # Obtener ofertas recibidas
    ofertas_recibidas = []
    if 'ofertas' in fantasy_data:
        ofertas_recibidas = [o for o in fantasy_data['ofertas'].values() 
                            if o['vendedor_id'] == user_id and o['estado'] == 'pendiente']
    
    # Construir mensaje
    message_lines = [
        "<b>💰 MIS OFERTAS ACTIVAS</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"<b>🎯 Jugadores en Venta:</b> {len(jugadores_venta)}",
        f"<b>📨 Ofertas Recibidas:</b> {len(ofertas_recibidas)}",
        "",
        "<i>Selecciona una opción para gestionar:</i>"
    ]
    
    # Crear teclado
    keyboard = []
    
    if jugadores_venta:
        keyboard.append([InlineKeyboardButton(
            "📤 Mis Jugadores en Venta", 
            callback_data='mis_subastas'
        )])
    
    if ofertas_recibidas:
        keyboard.append([InlineKeyboardButton(
            "📩 Ofertas Recibidas", 
            callback_data='ver_ofertas_recibidas'
        )])
    
    keyboard.append([
        InlineKeyboardButton("➕ Poner Jugador en Venta", callback_data='elegir_jugador_venta'),
        InlineKeyboardButton("🔙 Volver", callback_data='mercado_menu')
    ])
    
    await query.edit_message_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
async def iniciar_subasta_handler(update: Update, context: CallbackContext):
    """Inicia el proceso para poner un jugador en subasta"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    fantasy_data = await load_fantasy_data()
    
    # Verificar que el usuario tiene jugadores
    if user_id not in fantasy_data or not fantasy_data[user_id].get('team', []):
        await query.edit_message_text(
            "❌ No tienes jugadores en tu equipo para poner en subasta.",
            parse_mode='HTML'
        )
        return
    
    # Mostrar lista de jugadores
    keyboard = []
    for player in fantasy_data[user_id]['team']:
        keyboard.append([InlineKeyboardButton(
            f"⚽ {player['name']} (Valor: {player['value']})",
            callback_data=f'subasta_elegir_{player["id"]}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='mis_ofertas')])
    
    await query.edit_message_text(
        text="<b>🎯 SELECCIONA JUGADOR PARA SUBASTA</b>\n\n"
             "Elige qué jugador deseas poner en subasta:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def configurar_subasta(update: Update, context: CallbackContext):
    """Configura los parámetros de la subasta"""
    query = update.callback_query
    await query.answer()
    
    player_id = query.data.split('_')[-1]
    context.user_data['subasta_player_id'] = player_id
    context.user_data['estado'] = 'ESPERANDO_PRECIO_SUBASTA'
    
    await query.edit_message_text(
        "💰 <b>CONFIGURAR SUBASTA</b>\n\n"
        "Ingresa el precio inicial de la subasta (ejemplo: 500.50):\n\n"
        "<i>Los demás usuarios podrán pujar por encima de este precio.</i>",
        parse_mode='HTML'
    )

async def crear_subasta(update: Update, context: CallbackContext):
    """Crea la subasta con el precio inicial y aplica el costo de 10 CUP"""
    user_id = str(update.message.from_user.id)
    precio_texto = update.message.text
    
    try:
        # Verificar formato del precio
        precio = float(precio_texto)
        if precio <= 0:
            raise ValueError
        if precio > 300:
            await update.message.reply_text(
                "❌ El precio inicial no puede ser mayor a 300 CUP.",
                parse_mode='HTML'
            )
            return
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un número válido mayor a 0 (ejemplo: 1500)",
            parse_mode='HTML'
        )
        return
    
    player_id = context.user_data.get('subasta_player_id')
    if not player_id:
        await update.message.reply_text(
            "❌ Error: No se encontró el jugador. Por favor comienza nuevamente.",
            parse_mode='HTML'
        )
        return
    
    async with lock_data, lock_fantasy:  # Bloqueamos ambos archivos
        try:
            # Cargar datos
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
            
            # Verificar que el usuario existe en user_data
            if user_id not in user_data.get("usuarios", {}):
                await update.message.reply_text(
                    "❌ No tienes una cuenta registrada.",
                    parse_mode='HTML'
                )
                return
            
            # Verificar balance del usuario
            costo_subasta = 10  # CUP
            balance_actual = user_data["usuarios"][user_id].get("Balance", 0)
            
            if balance_actual < costo_subasta:
                await update.message.reply_text(
                    f"❌ No tienes suficiente balance. Necesitas {costo_subasta} CUP para crear una subasta.",
                    parse_mode='HTML'
                )
                return
            
            # Verificar que el usuario tiene equipo en fantasy_data
            if user_id not in fantasy_data or 'team' not in fantasy_data[user_id]:
                await update.message.reply_text(
                    "❌ No tienes un equipo registrado.",
                    parse_mode='HTML'
                )
                return
            
            # Contar jugadores únicos (evitando duplicados por ID)
            user_team = fantasy_data[user_id]['team']
            jugadores_unicos = {str(player['id']) for player in user_team}
            
            if len(jugadores_unicos) <= 9:  # Si tiene 9 o menos jugadores únicos
                await update.message.reply_text(
                    "❌ No puedes crear subastas si tienes 9 jugadores o menos en tu equipo.\n",
                    parse_mode='HTML'
                )
                return
            
            # Verificar que el jugador sigue en el equipo del usuario
            player_info = None
            for player in user_team:
                if str(player['id']) == player_id:
                    player_info = player
                    break
            
            if not player_info:
                await update.message.reply_text(
                    "❌ Este jugador ya no está en tu equipo.",
                    parse_mode='HTML'
                )
                return
            
            # Cobrar costo de la subasta (CORRECCIÓN: Descuento directo en user_data)
            user_data["usuarios"][user_id]["Balance"] -= costo_subasta
            user_data["usuarios"][user_id]["marca"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %p")
            
            # Crear la subasta
            subasta_id = str(uuid.uuid4())
            expiration_time = (datetime.now() + timedelta(hours=5)).timestamp()
            
            fantasy_data.setdefault('subastas', {})[subasta_id] = {
                'player_id': player_id,
                'vendedor_id': user_id,
                'precio_actual': precio,
                'precio_inicial': precio,
                'ultimo_postor_id': None,
                'fecha_inicio': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'fecha_fin': expiration_time,
                'estado': 'activa',
                'pujas': [],
                'jugador_info': player_info,
                'costo_subasta': costo_subasta
            }
            
            # Quitar jugador del equipo del vendedor (eliminando duplicados)
            fantasy_data[user_id]['team'] = [p for p in user_team if str(p['id']) != player_id]
            fantasy_data[user_id]['value'] = sum(p['value'] for p in fantasy_data[user_id]['team'])
            
            # Guardar cambios
            await save_data(user_data)
            await save_fantasy_data(fantasy_data)
            
            # Crear teclado con opciones
            keyboard = [
                [InlineKeyboardButton("📤 Ver Mis Subastas", callback_data='mis_subastas')],
                [InlineKeyboardButton("💹 Ver Subastas Activas", callback_data='listar_subastas')],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data='juego_fantasy')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Notificar al usuario
            await update.message.reply_text(
                f"✅ <b>SUBASTA CREADA</b>\n\n"
                f"⚽ Jugador: {player_info['name']}\n"
                f"💰 Precio inicial: {precio:.2f}\n"
                f"💸 Costo de subasta: -{costo_subasta} CUP (nuevo balance: {user_data['usuarios'][user_id]['Balance']:.2f})\n"
                f"⏳ Finaliza: {(datetime.fromtimestamp(expiration_time)).strftime('%d/%m %H:%M')}\n\n"
                f"Los demás usuarios ya pueden pujar por este jugador.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
           
            nombre_usuario = user_data["usuarios"][user_id].get("Nombre", "Usuario")
            
            # Mensaje bonito para el grupo con formato HTML (sin teclado)
            mensaje_grupo = f"""
🎉 <b>¡NUEVA SUBASTA DISPONIBLE!</b> 🎉

<b>⚽ JUGADOR:</b> <code>{player_info['name']}</code>
<b>🏆 EQUIPO:</b> <code>{player_info['team']}</code>
<b>📍 POSICIÓN:</b> <code>{player_info['position']}</code>
<b>⭐ RATING:</b> <code>{player_info['rating']}</code>

<b>💰 PRECIO INICIAL:</b> <code>${precio:.2f}</code>
<b>⏳ FINALIZA EN:</b> <code>5 horas</code>
<b>👤 VENDEDOR:</b> <code>{nombre_usuario}</code>

<b>📊 ESTADÍSTICAS:</b>
├ 🎯 <b>Goles:</b> <code>{player_info.get('goals', 0)}</code>
├ 🎁 <b>Asistencias:</b> <code>{player_info.get('assists', 0)}</code>
├ 🔑 <b>Pases clave:</b> <code>{player_info.get('key_passes', 0)}</code>
└ 🛡 <b>Tackles:</b> <code>{player_info.get('tackles', 0)}</code>

<b>💡 ¡No pierdas esta oportunidad!</b>
"""
            
            try:
                # Intentar enviar con foto del jugador si está disponible
                if player_info.get('photo'):
                    await context.bot.send_photo(
                        chat_id=GROUP_CHAT_ID,
                        photo=player_info['photo'],
                        caption=mensaje_grupo,
                        parse_mode='HTML'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=mensaje_grupo,
                        parse_mode='HTML'
                    )
            except Exception as e:
                logging.error(f"Error al enviar mensaje al grupo: {str(e)}")
                # Fallback: enviar solo texto si falla con foto
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=mensaje_grupo,
                    parse_mode='HTML'
                )
            
        except Exception as e:
            logging.error(f"Error crítico en crear_subasta: {str(e)}")
            traceback.print_exc()
            await update.message.reply_text(
                "⚠️ Ocurrió un error al crear la subasta. Por favor intenta nuevamente.",
                parse_mode='HTML'
            )
        finally:
            # Limpiar estado independientemente del resultado
            context.user_data.clear()
async def pujar_subasta(update: Update, context: CallbackContext):
    """Manejador para realizar una puja en una subasta"""
    query = update.callback_query
    await query.answer()
    
    subasta_id = query.data.split('_')[-1]
    context.user_data['subasta_id'] = subasta_id
    context.user_data['estado'] = 'ESPERANDO_PUJA'
    
    fantasy_data = await load_fantasy_data()
    
    if subasta_id not in fantasy_data.get('subastas', {}):
        await query.edit_message_text(
            "❌ Esta subasta ya no está disponible.",
            parse_mode='HTML'
        )
        return
    
    subasta = fantasy_data['subastas'][subasta_id]
    precio_actual = subasta['precio_actual']
    min_puja = precio_actual * 1.05  # Puja mínima 5% más que el precio actual
    
    await query.edit_message_text(
        f"💰 <b>REALIZAR PUJA</b>\n\n"
        f"⚽ Jugador: {subasta['jugador_info']['name']}\n"
        f"🏷 Valor: {subasta['jugador_info']['value']}\n"
        f"💰 Precio actual: {precio_actual:.2f}\n"
        f"📈 Puja mínima requerida: {min_puja:.2f}\n\n"
        "Ingresa el monto que deseas pujar:",
        parse_mode='HTML'
    )

async def procesar_puja(update: Update, context: CallbackContext):
    """Procesa el monto de la puja ingresado por el usuario"""
    user_id = str(update.message.from_user.id)
    monto_texto = update.message.text
    
    try:
        monto = float(monto_texto)
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un número válido (ejemplo: 1500.50)",
            parse_mode='HTML'
        )
        return
    
    subasta_id = context.user_data.get('subasta_id')
    if not subasta_id:
        await update.message.reply_text(
            "❌ Error: No se encontró la subasta. Por favor comienza nuevamente.",
            parse_mode='HTML'
        )
        return
    
    fantasy_data = await load_fantasy_data()
    user_data = await load_data()
    
    # Verificar que la subasta sigue activa
    if subasta_id not in fantasy_data.get('subastas', {}):
        await update.message.reply_text(
            "❌ Esta subasta ya no está disponible.",
            parse_mode='HTML'
        )
        return
    
    subasta = fantasy_data['subastas'][subasta_id]
    
    # Verificar fondos
    balance = user_data.get("usuarios", {}).get(user_id, {}).get("Balance", 0)
    if balance < monto:
        await update.message.reply_text(
            f"❌ Saldo insuficiente. Disponible: {balance:.2f}",
            parse_mode='HTML'
        )
        return
    
    # Verificar puja mínima
    min_puja = subasta['precio_actual'] * 1.05
    if monto < min_puja:
        await update.message.reply_text(
            f"❌ Puja mínima requerida: {min_puja:.2f}",
            parse_mode='HTML'
        )
        return
    
    # Registrar la puja
    subasta['precio_actual'] = monto
    subasta['ultimo_postor_id'] = user_id
    subasta['pujas'].append({
        'postor_id': user_id,
        'monto': monto,
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Bloquear fondos del postor
    user_data["usuarios"][user_id]["Balance"] -= monto
    
    # Devolver fondos al postor anterior si existe
    if subasta['pujas'] and len(subasta['pujas']) > 1:
        postor_anterior = subasta['pujas'][-2]['postor_id']
        monto_anterior = subasta['pujas'][-2]['monto']
        user_data["usuarios"][postor_anterior]["Balance"] += monto_anterior
    
    await save_data(user_data)
    await save_fantasy_data(fantasy_data)
    
    # Notificar al vendedor
    try:
        await context.bot.send_message(
            chat_id=subasta['vendedor_id'],
            text=f"⚠️ <b>NUEVA PUJA EN TU SUBASTA</b>\n\n"
                 f"⚽ Jugador: {subasta['jugador_info']['name']}\n"
                 f"💰 Nueva puja: {monto:.2f}\n"
                 f"👤 Postor: {await obtener_nombre_usuario(user_id)}\n"
                 f"⏳ Finaliza: {(datetime.fromtimestamp(subasta['fecha_fin'])).strftime('%d/%m %H:%M')}",
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error notificando al vendedor: {str(e)}")
    
    await update.message.reply_text(
        f"✅ <b>PUJA REALIZADA</b>\n\n"
        f"Has pujado <b>{monto:.2f}</b> por {subasta['jugador_info']['name']}.\n"
        f"Si alguien supera tu puja, se te devolverá el dinero automáticamente.",
        parse_mode='HTML'
    )
    
    # Limpiar estado
    context.user_data.pop('estado', None)

async def finalizar_subastas(context: ContextTypes.DEFAULT_TYPE):
    """Tarea programada para finalizar subastas expiradas"""
    fantasy_data = await load_fantasy_data()
    user_data = await load_data()
    
    if 'subastas' not in fantasy_data:
        return
    
    ahora = datetime.now().timestamp()
    subastas_finalizadas = []
    
    for subasta_id, subasta in list(fantasy_data['subastas'].items()):
        if subasta['estado'] == 'activa' and subasta['fecha_fin'] <= ahora:
            # Finalizar la subasta
            subasta['estado'] = 'finalizada'
            subastas_finalizadas.append(subasta)
            
            # Procesar resultado
            if subasta['ultimo_postor_id']:  # Hubo pujas
                # Transferir jugador al ganador
                if subasta['ultimo_postor_id'] not in fantasy_data:
                    fantasy_data[subasta['ultimo_postor_id']] = {
                        'credits': 0,
                        'team': [],
                        'formation': BASE_FORMATION,
                        'value': 0
                    }
                
                fantasy_data[subasta['ultimo_postor_id']]['team'].append(subasta['jugador_info'])
                fantasy_data[subasta['ultimo_postor_id']]['value'] += subasta['jugador_info']['value']
                
                # Transferir dinero al vendedor (con impuesto)
                impuesto = subasta['precio_actual'] * MARKET_TAX
                monto_vendedor = subasta['precio_actual'] - impuesto
                
                user_data["usuarios"][subasta['vendedor_id']]["Balance"] = user_data["usuarios"].get(
                    subasta['vendedor_id'], {}).get("Balance", 0) + monto_vendedor
                
               
                
                # Notificar a las partes
                await notificar_final_subasta(context, subasta, True)
            else:  # No hubo pujas
                # Devolver jugador al vendedor
                if subasta['vendedor_id'] in fantasy_data:
                    fantasy_data[subasta['vendedor_id']]['team'].append(subasta['jugador_info'])
                    fantasy_data[subasta['vendedor_id']]['value'] += subasta['jugador_info']['value']
                
                await notificar_final_subasta(context, subasta, False)
    
    if subastas_finalizadas:
        await save_data(user_data)
        await save_fantasy_data(fantasy_data)

async def notificar_final_subasta(context, subasta, vendido):
    """Notifica a vendedor y comprador sobre el resultado de la subasta"""
    try:
        if vendido:
            # Notificar al comprador
            await context.bot.send_message(
                chat_id=subasta['ultimo_postor_id'],
                text=f"🎉 <b>¡GANASTE LA SUBASTA!</b>\n\n"
                     f"Has adquirido a {subasta['jugador_info']['name']} "
                     f"por {subasta['precio_actual']:.2f}.\n"
                     f"El jugador ha sido añadido a tu equipo.",
                parse_mode='HTML'
            )
            
            # Notificar al vendedor
            await context.bot.send_message(
                chat_id=subasta['vendedor_id'],
                text=f"🏁 <b>SUBASTA FINALIZADA</b>\n\n"
                     f"Has vendido a {subasta['jugador_info']['name']} "
                     f"por {subasta['precio_actual']:.2f}.\n"
                     f"Se ha depositado {subasta['precio_actual'] - (subasta['precio_actual'] * MARKET_TAX):.2f} "
                     f"en tu balance (impuesto del {MARKET_TAX*100}% aplicado).",
                parse_mode='HTML'
            )
        else:
            # Notificar al vendedor (sin pujas)
            await context.bot.send_message(
                chat_id=subasta['vendedor_id'],
                text=f"ℹ️ <b>SUBASTA FINALIZADA SIN PUJAS</b>\n\n"
                     f"Tu subasta para {subasta['jugador_info']['name']} "
                     f"ha finalizado sin recibir pujas.\n"
                     f"El jugador ha sido devuelto a tu equipo.",
                parse_mode='HTML'
            )
    except Exception as e:
        logging.error(f"Error notificando final de subasta: {str(e)}")

async def obtener_nombre_usuario(user_id):
    """Obtiene el nombre de usuario desde user_data"""
    user_data = await load_data()
    return user_data.get("usuarios", {}).get(user_id, {}).get("Nombre", "Usuario Desconocido")    
    
async def verificar_subastas_finalizadas(context: ContextTypes.DEFAULT_TYPE = None):
    """Verifica y finaliza subastas expiradas"""
    try:
        fantasy_data = await load_fantasy_data()
        user_data = await load_data()
        
        if 'subastas' not in fantasy_data:
            return
        
        ahora = datetime.now().timestamp()
        subastas_finalizadas = []
        
        for subasta_id, subasta in list(fantasy_data['subastas'].items()):
            if subasta['estado'] == 'activa' and subasta['fecha_fin'] <= ahora:
                # Finalizar la subasta
                subasta['estado'] = 'finalizada'
                subastas_finalizadas.append(subasta)
                
                # Procesar resultado
                if subasta['ultimo_postor_id']:  # Hubo pujas
                    # Transferir jugador al ganador
                    if subasta['ultimo_postor_id'] not in fantasy_data:
                        fantasy_data[subasta['ultimo_postor_id']] = {
                            'credits': 0,
                            'team': [],
                            'formation': BASE_FORMATION,
                            'value': 0
                        }
                    
                    fantasy_data[subasta['ultimo_postor_id']]['team'].append(subasta['jugador_info'])
                    fantasy_data[subasta['ultimo_postor_id']]['value'] += subasta['jugador_info']['value']
                    
                    # Transferir dinero al vendedor (con impuesto)
                    impuesto = subasta['precio_actual'] * MARKET_TAX
                    monto_vendedor = subasta['precio_actual'] - impuesto
                    
                    user_data["usuarios"][subasta['vendedor_id']]["Balance"] = user_data["usuarios"].get(
                        subasta['vendedor_id'], {}).get("Balance", 0) + monto_vendedor
                    
                 
                    
                    # Notificar a las partes
                    await notificar_final_subasta(context, subasta, True)
                else:  # No hubo pujas
                    # Devolver jugador al vendedor
                    if subasta['vendedor_id'] in fantasy_data:
                        fantasy_data[subasta['vendedor_id']]['team'].append(subasta['jugador_info'])
                        fantasy_data[subasta['vendedor_id']]['value'] += subasta['jugador_info']['value']
                    
                    await notificar_final_subasta(context, subasta, False)
        
        if subastas_finalizadas:
            await save_data(user_data)
            await save_fantasy_data(fantasy_data)
            return True
        
        return False

    except Exception as e:
        print(f"❌ Error en verificar_subastas_finalizadas: {str(e)}")
        traceback.print_exc()
        return False
        
async def procesar_puja_subasta(update, context):
    """Procesa el monto de puja ingresado por el usuario"""
    try:
        user_id = str(update.message.from_user.id)
        monto_texto = update.message.text
        
        try:
            monto = float(monto_texto)
        except ValueError:
            await update.message.reply_text(
                "❌ Por favor ingresa un número válido (ejemplo: 1500.50)",
                parse_mode='HTML'
            )
            return
        
        subasta_id = context.user_data.get('subasta_id')
        if not subasta_id:
            await update.message.reply_text(
                "❌ Error: No se encontró la subasta. Por favor comienza nuevamente.",
                parse_mode='HTML'
            )
            return
        
        fantasy_data = await load_fantasy_data()
        user_data = await load_data()
        
        # Verificar que la subasta sigue activa
        if subasta_id not in fantasy_data.get('subastas', {}):
            await update.message.reply_text(
                "❌ Esta subasta ya no está disponible.",
                parse_mode='HTML'
            )
            return
        
        subasta = fantasy_data['subastas'][subasta_id]
        
        # Verificar si la subasta ya expiró
        if datetime.now().timestamp() > subasta['fecha_fin']:
            await update.message.reply_text(
                "❌ Esta subasta ya ha finalizado.",
                parse_mode='HTML'
            )
            return
        
        # Verificar fondos
        balance = user_data.get("usuarios", {}).get(user_id, {}).get("Balance", 0)
        if balance < monto:
            await update.message.reply_text(
                f"❌ Saldo insuficiente. Disponible: {balance:.2f}",
                parse_mode='HTML'
            )
            return
        
        # Verificar puja mínima
        min_puja = subasta['precio_actual'] * 1.05
        if monto < min_puja:
            await update.message.reply_text(
                f"❌ Puja mínima requerida: {min_puja:.2f}",
                parse_mode='HTML'
            )
            return
        
        # Registrar la puja
        subasta['precio_actual'] = monto
        subasta['ultimo_postor_id'] = user_id
        subasta['pujas'].append({
            'postor_id': user_id,
            'monto': monto,
            'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Bloquear fondos del postor
        user_data["usuarios"][user_id]["Balance"] -= monto
        
        # Devolver fondos al postor anterior si existe
        if len(subasta['pujas']) > 1:
            postor_anterior = subasta['pujas'][-2]['postor_id']
            monto_anterior = subasta['pujas'][-2]['monto']
            user_data["usuarios"][postor_anterior]["Balance"] += monto_anterior
        
        await save_data(user_data)
        await save_fantasy_data(fantasy_data)
        
        # Verificar si la subasta debe extenderse (últimos 5 minutos)
        tiempo_restante = subasta['fecha_fin'] - datetime.now().timestamp()
        if tiempo_restante < 300:  # 5 minutos
            subasta['fecha_fin'] += 300  # Extender 5 minutos más
            await save_fantasy_data(fantasy_data)
        
        # Notificar al vendedor
        try:
            await context.bot.send_message(
                chat_id=subasta['vendedor_id'],
                text=f"⚠️ <b>NUEVA PUJA EN TU SUBASTA</b>\n\n"
                     f"⚽ Jugador: {subasta['jugador_info']['name']}\n"
                     f"💰 Nueva puja: {monto:.2f}\n"
                     f"👤 Postor: {await obtener_nombre_usuario(user_id)}\n"
                     f"⏳ Finaliza: {(datetime.fromtimestamp(subasta['fecha_fin'])).strftime('%d/%m %H:%M')}",
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"⚠️ Error notificando al vendedor: {str(e)}")
        
        await update.message.reply_text(
            f"✅ <b>PUJA REALIZADA</b>\n\n"
            f"Has pujado <b>{monto:.2f}</b> por {subasta['jugador_info']['name']}.\n"
            f"Si alguien supera tu puja, se te devolverá el dinero automáticamente.",
            parse_mode='HTML'
        )
        
        # Verificar si la subasta debe finalizar ahora
        await verificar_subastas_finalizadas(context)

    except Exception as e:
        print(f"❌ Error en procesar_puja_subasta: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            "⚠️ Ocurrió un error al procesar tu puja. Por favor intenta nuevamente.",
            parse_mode='HTML'
        )



async def mostrar_menu_subastas(update: Update, context: CallbackContext):
    """Muestra el menú principal de subastas con todas las opciones disponibles"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    fantasy_data = await load_fantasy_data()
    
    # Verificar subastas pendientes primero
    await verificar_subastas_finalizadas(context)
    
    # Obtener estadísticas
    subastas_activas = [s for s in fantasy_data.get('subastas', {}).values() 
                       if s['estado'] == 'activa']
    
    mis_subastas = [s for s in subastas_activas if s['vendedor_id'] == user_id]
    pujas_activas = [p for s in subastas_activas 
                    for p in s['pujas'] if p['postor_id'] == user_id]

    # Construir mensaje
    mensaje = f"""
<b>🏆 MERCADO DE SUBASTAS</b>
━━━━━━━━━━━━━━━━━━
<b>📊 Estadísticas:</b>
├ 🏷 Subastas activas: <code>{len(subastas_activas)}</code>
├ 📤 Mis subastas: <code>{len(mis_subastas)}</code>
└ 💰 Mis pujas activas: <code>{len(pujas_activas)}</code>

<b>💡 Sistema de subastas:</b>
• Duración: <code>5 horas</code> (se extiende con pujas finales)
• Puja mínima: <code>5%</code> sobre el precio actual
• Impuesto: <code>{MARKET_TAX*100}%</code> para el mantenimiento del juego.

<i>Selecciona una opción:</i>
"""
    # Crear teclado interactivo sin "🏆 Bote Acumulado"
    teclado = [
        [InlineKeyboardButton("💹 Ver Subastas Activas", callback_data='listar_subastas')],
        [
            InlineKeyboardButton("📤 Mis Subastas", callback_data='mis_subastas'),
            InlineKeyboardButton("💰 Mis Pujas", callback_data='mis_pujas')
        ],
        [InlineKeyboardButton("➕ Crear Subasta", callback_data='iniciar_subasta')],
        [InlineKeyboardButton("📜 Historial", callback_data='historial_subastas')],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data='juego_fantasy')]
    ]

    # Enviar mensaje con foto de portada (opcional)
    try:
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(teclado),
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Error al mostrar menú de subastas: {str(e)}")
        await query.message.reply_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(teclado),
            parse_mode='HTML'
        )



async def mis_pujas_handler(update: Update, context: CallbackContext):
    """Muestra las pujas activas del usuario"""
    
    try:
        query = update.callback_query
        print(f"Tipo de update: {type(update)}")
        print(f"Query data: {query.data if query else 'None'}")
        await query.answer()
        print("Query answered")
        
        user_id = str(query.from_user.id)
        print(f"User ID: {user_id}")
        fantasy_data = await load_fantasy_data()
        
        
        # Verificar y finalizar subastas expiradas primero
        
        await verificar_subastas_finalizadas(context)
        
        # Encontrar todas las subastas donde el usuario tiene pujas activas
        print("Buscando pujas del usuario...")
        mis_pujas = []
        
        for subasta_id, subasta in fantasy_data.get('subastas', {}).items():
            if subasta['estado'] == 'activa':
                for puja in subasta['pujas']:
                    if puja['postor_id'] == user_id:
                        es_ultima_puja = subasta['pujas'][-1]['postor_id'] == user_id
                        mis_pujas.append({
                            'subasta_id': subasta_id,
                            'subasta_data': subasta,
                            'puja_data': puja,
                            'es_ultima': es_ultima_puja
                        })
        
        
        if not mis_pujas:
            print("No hay pujas activas")
            await query.edit_message_text(
                "ℹ️ No tienes pujas activas en este momento.",
                parse_mode='HTML'
            )
            return
        
        mensaje = "<b>💰 MIS PUJAS ACTIVAS</b>\n━━━━━━━━━━━━━━━━━━\n"
        teclado = []
        
        for i, puja in enumerate(mis_pujas[:5], 1):
            subasta = puja['subasta_data']
            tiempo_restante = datetime.fromtimestamp(subasta['fecha_fin']) - datetime.now()
            horas, resto = divmod(tiempo_restante.seconds, 3600)
            minutos = resto // 60
            
            estado = "✅ Última puja" if puja['es_ultima'] else "⚠️ Superada"
            print(f"Procesando puja {i}: {subasta['jugador_info']['name']} - {estado}")
            
            mensaje += (
                f"\n<b>{i}. ⚽ {subasta['jugador_info']['name']}</b>\n"
                f"├ 💰 Mi puja: <code>{puja['puja_data']['monto']:.2f}</code>\n"
                f"├ 🏷 Precio actual: <code>{subasta['precio_actual']:.2f}</code>\n"
                f"├ 📅 Fecha puja: <code>{puja['puja_data']['fecha']}</code>\n"
                f"├ 🏁 Estado: <code>{estado}</code>\n"
                f"└ ⏳ Tiempo restante: <code>{horas}h {minutos}m</code>\n"
            )
            
            btn_text = f"🔍 Ver subasta de {subasta['jugador_info']['name'][:10]}..."
            callback_data = f'ver_subasta_{puja["subasta_id"]}'
            print(f"Creando botón: {btn_text} -> {callback_data}")
            teclado.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        
        teclado.append([InlineKeyboardButton("🔄 Actualizar", callback_data='mis_pujas')])
        teclado.append([InlineKeyboardButton("🔙 Volver", callback_data='menu_subastas')])
        
        print("Mensaje construido, enviando...")
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(teclado),
            parse_mode='HTML'
        )
        print("=== mis_pujas_handler FIN ===")
        
    except Exception as e:
        print(f"\n❌ ERROR en mis_pujas_handler: {str(e)}")
        traceback.print_exc()
        if query:
            await query.edit_message_text(
                "⚠️ Ocurrió un error al cargar tus pujas. Por favor intenta nuevamente.",
                parse_mode='HTML'
            )
async def listar_subastas_activas(update: Update, context: CallbackContext):
    """Lista todas las subastas activas disponibles"""
    
    try:
        query = update.callback_query
        await query.answer()
        
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
            user_id = str(query.from_user.id)
            
            await verificar_subastas_finalizadas(context)
            
            # Mostrar todas las subastas activas sin excluir las del usuario
            subastas_activas = [
                {'id': subasta_id, **subasta} 
                for subasta_id, subasta in fantasy_data.get('subastas', {}).items()
                if subasta['estado'] == 'activa'
            ]
            
            if not subastas_activas:
                await query.edit_message_text(
                    "ℹ️ No hay subastas activas disponibles en este momento.",
                    parse_mode='HTML'
                )
                return
            
            subastas_activas.sort(key=lambda x: x['fecha_fin'])
            
            mensaje = "<b>🏆 TODAS LAS SUBASTAS ACTIVAS</b>\n━━━━━━━━━━━━━━━━━━\n"
            teclado = []
            
            for i, subasta in enumerate(subastas_activas[:5], 1):
                tiempo_restante = datetime.fromtimestamp(subasta['fecha_fin']) - datetime.now()
                horas, resto = divmod(tiempo_restante.seconds, 3600)
                minutos = resto // 60
                
                es_mia = subasta['vendedor_id'] == user_id
                prefijo = "⭐ TU SUBASTA" if es_mia else "⚽ Subasta"
                
                mensaje += (
                    f"\n<b>{i}. {prefijo} - {subasta['jugador_info']['name']}</b>\n"
                    f"├ 🏷 Valor: <code>{subasta['jugador_info']['value']}</code>\n"
                    f"├ 💰 Precio actual: <code>{subasta['precio_actual']:.2f}</code>\n"
                    f"├ 🏁 Pujas: <code>{len(subasta['pujas'])}</code>\n"
                    f"├ ⏳ Finaliza en: <code>{horas}h {minutos}m</code>\n"
                    f"└ 👤 Vendedor: <code>{await obtener_nombre_usuario(subasta['vendedor_id'])}</code>\n"
                )
                
                if es_mia:
                    btn_text = f"🔍 Gestionar mi subasta"
                    callback_data = f'gestionar_subasta_{subasta["id"]}'
                else:
                    btn_text = f"💰 Pujar (${subasta['precio_actual']:.2f})"
                    callback_data = f'pujar_subasta_{subasta["id"]}'
                
                teclado.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
            
            teclado.append([InlineKeyboardButton("📤 Mis Subastas", callback_data='mis_subastas')])
            teclado.append([
                InlineKeyboardButton("🔄 Actualizar", callback_data='listar_subastas'),
                InlineKeyboardButton("🔙 Volver", callback_data='menu_subastas')
            ])
            
            await query.edit_message_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error en listar_subastas_activas: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text("⚠️ Error al listar subastas")

async def mis_subastas_handler(update: Update, context: CallbackContext):
    """Muestra las subastas creadas por el usuario"""
    print("\n=== mis_subastas_handler INICIO ===")
    try:
        query = update.callback_query
        await query.answer()
        
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
            user_id = str(query.from_user.id)
            
            await verificar_subastas_finalizadas(context)
            
            mis_subastas = [
                {'id': subasta_id, **subasta}
                for subasta_id, subasta in fantasy_data.get('subastas', {}).items()
                if subasta['vendedor_id'] == user_id and subasta['estado'] == 'activa'
            ]
            
            if not mis_subastas:
                await query.edit_message_text(
                    "ℹ️ No tienes subastas activas en este momento.",
                    parse_mode='HTML'
                )
                return
            
            mensaje = "<b>⭐ MIS SUBASTAS ACTIVAS</b>\n━━━━━━━━━━━━━━━━━━\n"
            teclado = []
            
            for i, subasta in enumerate(mis_subastas, 1):
                tiempo_restante = datetime.fromtimestamp(subasta['fecha_fin']) - datetime.now()
                horas, resto = divmod(tiempo_restante.seconds, 3600)
                minutos = resto // 60
                
                mensaje += (
                    f"\n<b>{i}. ⚽ {subasta['jugador_info']['name']}</b>\n"
                    f"├ 💰 Precio actual: <code>{subasta['precio_actual']:.2f}</code>\n"
                    f"├ 🏁 Pujas recibidas: <code>{len(subasta['pujas'])}</code>\n"
                    f"├ ⏳ Finaliza en: <code>{horas}h {minutos}m</code>\n"
                    f"└ 💸 Coste subasta: <code>{subasta.get('costo_subasta', 10)} CUP</code>\n"
                )
                
                # Botón para gestionar cada subasta
                teclado.append([InlineKeyboardButton(
                    f"🔍 {subasta['jugador_info']['name'][:15]}... (${subasta['precio_actual']:.2f})",
                    callback_data=f'gestionar_subasta_{subasta["id"]}'
                )])
            
            teclado.append([InlineKeyboardButton("➕ Nueva Subasta", callback_data='iniciar_subasta')])
            teclado.append([
                InlineKeyboardButton("🔄 Actualizar", callback_data='mis_subastas'),
                InlineKeyboardButton("🔙 Volver", callback_data='menu_subastas')
            ])
            
            await query.edit_message_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error en mis_subastas_handler: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text("⚠️ Error al cargar tus subastas")

async def gestionar_subasta(update: Update, context: CallbackContext):
    """Permite al vendedor gestionar una subasta activa"""
    query = update.callback_query
    await query.answer()
    
    subasta_id = query.data.split('_')[-1]
    
    try:
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
            
            if subasta_id not in fantasy_data.get('subastas', {}):
                await query.edit_message_text("❌ Esta subasta ya no existe")
                return
                
            subasta = fantasy_data['subastas'][subasta_id]
            
            if subasta['vendedor_id'] != str(query.from_user.id):
                await query.edit_message_text("❌ No eres el propietario de esta subasta")
                return
                
            if subasta['estado'] != 'activa':
                await query.edit_message_text("ℹ️ Esta subasta ya ha finalizado")
                return
            
            # Construir mensaje detallado
            tiempo_restante = datetime.fromtimestamp(subasta['fecha_fin']) - datetime.now()
            horas, resto = divmod(tiempo_restante.seconds, 3600)
            minutos = resto // 60
            
            mensaje = f"""
<b>🔧 GESTIONAR SUBASTA</b>
━━━━━━━━━━━━━━━━━━
<b>⚽ Jugador:</b> {subasta['jugador_info']['name']}
<b>💰 Precio actual:</b> <code>{subasta['precio_actual']:.2f}</code>
<b>🏁 Pujas recibidas:</b> <code>{len(subasta['pujas'])}</code>
<b>⏳ Tiempo restante:</b> <code>{horas}h {minutos}m</code>

<b>📊 Últimas pujas:</b>
"""
            
            if subasta['pujas']:
                for i, puja in enumerate(subasta['pujas'][-3:], 1):
                    mensaje += (
                        f"\n{i}. <code>{puja['monto']:.2f}</code> por "
                        f"{await obtener_nombre_usuario(puja['postor_id'])} "
                        f"({puja['fecha']})"
                    )
            else:
                mensaje += "\nℹ️ No hay pujas aún"
            
            # Crear teclado de opciones
            teclado = []
            
            if subasta['pujas']:
                teclado.append([InlineKeyboardButton(
                    "✅ Aceptar mejor puja ahora",
                    callback_data=f'aceptar_puja_{subasta_id}'
                )])
            
            teclado.append([InlineKeyboardButton(
                "❌ Cancelar subasta",
                callback_data=f'cancelar_subasta_{subasta_id}'
            )])
            
            teclado.append([
                InlineKeyboardButton("🔄 Actualizar", callback_data=f'gestionar_subasta_{subasta_id}'),
                InlineKeyboardButton("🔙 Mis Subastas", callback_data='mis_subastas')
            ])
            
            await query.edit_message_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error en gestionar_subasta: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text("⚠️ Error al gestionar la subasta")
        
async def aceptar_puja_handler(update: Update, context: CallbackContext):
    """Manejador para aceptar una puja manualmente antes del tiempo"""
    query = update.callback_query
    await query.answer()
    
    subasta_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    try:
        async with lock_data, lock_fantasy:
            # Cargar datos
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
            
            # Verificar que la subasta existe
            if subasta_id not in fantasy_data.get('subastas', {}):
                await query.edit_message_text("❌ Esta subasta ya no existe")
                return
                
            subasta = fantasy_data['subastas'][subasta_id]
            
            # Validaciones
            if subasta['vendedor_id'] != user_id:
                await query.edit_message_text("❌ No eres el propietario de esta subasta")
                return
                
            if subasta['estado'] != 'activa':
                await query.edit_message_text("ℹ️ Esta subasta ya ha finalizado")
                return
                
            if not subasta['pujas']:
                await query.edit_message_text("ℹ️ No hay pujas para aceptar")
                return
            
            # Obtener la mejor puja
            mejor_puja = max(subasta['pujas'], key=lambda x: x['monto'])
            comprador_id = mejor_puja['postor_id']
            monto = mejor_puja['monto']
            
            # Procesar la transacción
            # 1. Transferir jugador al comprador
            if comprador_id not in fantasy_data:
                fantasy_data[comprador_id] = {
                    'credits': 0,
                    'team': [],
                    'formation': BASE_FORMATION,
                    'value': 0
                }
            
            fantasy_data[comprador_id]['team'].append(subasta['jugador_info'])
            fantasy_data[comprador_id]['value'] += subasta['jugador_info']['value']
            
            # 2. Transferir dinero al vendedor (con impuesto)
            impuesto = monto * MARKET_TAX
            monto_vendedor = monto - impuesto
            
            user_data["usuarios"][user_id]["Balance"] = user_data["usuarios"].get(user_id, {}).get("Balance", 0) + monto_vendedor
            
           
            
            # 4. Marcar subasta como finalizada
            subasta['estado'] = 'finalizada'
            subasta['precio_actual'] = monto
            subasta['ultimo_postor_id'] = comprador_id
            subasta['fecha_fin'] = datetime.now().timestamp()  # Finalizar ahora
            
            # Guardar cambios
            await save_data(user_data)
            await save_fantasy_data(fantasy_data)
            
            # Notificar a las partes
            await context.bot.send_message(
                chat_id=comprador_id,
                text=f"🎉 <b>¡EL VENDEDOR HA ACEPTADO TU PUJA!</b>\n\n"
                     f"Has adquirido a {subasta['jugador_info']['name']} "
                     f"por {monto:.2f}.\n"
                     f"El jugador ha sido añadido a tu equipo.",
                parse_mode='HTML'
            )
            
            # Mensaje de confirmación al vendedor
            keyboard = [
                [InlineKeyboardButton("📤 Mis Subastas", callback_data='mis_subastas')],
                [InlineKeyboardButton("💹 Ver Subastas", callback_data='listar_subastas')]
            ]
            
            await query.edit_message_text(
                text=f"✅ <b>PUJA ACEPTADA</b>\n\n"
                     f"Has vendido a {subasta['jugador_info']['name']} "
                     f"por {monto:.2f}.\n"
                     f"Se ha depositado {monto_vendedor:.2f} "
                     f"en tu balance (impuesto del {MARKET_TAX*100}% aplicado).",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error en aceptar_puja_handler: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text(
            "⚠️ Ocurrió un error al aceptar la puja. Por favor intenta nuevamente.",
            parse_mode='HTML'
        )

async def cancelar_subasta_handler(update: Update, context: CallbackContext):
    """Manejador para cancelar una subasta activa"""
    query = update.callback_query
    await query.answer()
    
    subasta_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    try:
        async with lock_data, lock_fantasy:
            fantasy_data = await load_fantasy_data()
            
            # Verificar que la subasta existe
            if subasta_id not in fantasy_data.get('subastas', {}):
                await query.edit_message_text("❌ Esta subasta ya no existe")
                return
                
            subasta = fantasy_data['subastas'][subasta_id]
            
            # Validaciones
            if subasta['vendedor_id'] != user_id:
                await query.edit_message_text("❌ No eres el propietario de esta subasta")
                return
                
            if subasta['estado'] != 'activa':
                await query.edit_message_text("ℹ️ Esta subasta ya ha finalizado")
                return
            
            # 1. Devolver jugador al vendedor
            if user_id in fantasy_data:
                fantasy_data[user_id]['team'].append(subasta['jugador_info'])
                fantasy_data[user_id]['value'] += subasta['jugador_info']['value']
            
            # 2. Devolver dinero a los postores
            user_data = await load_data()
            for puja in subasta['pujas']:
                if puja['postor_id'] in user_data["usuarios"]:
                    user_data["usuarios"][puja['postor_id']]["Balance"] += puja['monto']
            
            # 3. Marcar como cancelada
            subasta['estado'] = 'cancelada'
            
            # Guardar cambios
            await save_data(user_data)
            await save_fantasy_data(fantasy_data)
            
            # Notificar a los postores
            for puja in subasta['pujas']:
                try:
                    await context.bot.send_message(
                        chat_id=puja['postor_id'],
                        text=f"ℹ️ <b>SUBASTA CANCELADA</b>\n\n"
                             f"La subasta para {subasta['jugador_info']['name']} "
                             f"ha sido cancelada por el vendedor.\n"
                             f"Se te ha devuelto {puja['monto']:.2f}.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Error notificando al postor {puja['postor_id']}: {str(e)}")
            
            # Mensaje de confirmación al vendedor
            keyboard = [
                [InlineKeyboardButton("📤 Mis Subastas", callback_data='mis_subastas')],
                [InlineKeyboardButton("➕ Nueva Subasta", callback_data='iniciar_subasta')]
            ]
            
            await query.edit_message_text(
                text=f"❌ <b>SUBASTA CANCELADA</b>\n\n"
                     f"Has cancelado la subasta de {subasta['jugador_info']['name']}.\n"
                     f"El jugador ha sido devuelto a tu equipo.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error en cancelar_subasta_handler: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text(
            "⚠️ Ocurrió un error al cancelar la subasta. Por favor intenta nuevamente.",
            parse_mode='HTML'
        )

async def ver_historial_subasta(update: Update, context: CallbackContext):
    """Muestra el historial completo de una subasta"""
    query = update.callback_query
    await query.answer()
    
    subasta_id = query.data.split('_')[-1]
    
    try:
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
            
            if subasta_id not in fantasy_data.get('subastas', {}):
                await query.edit_message_text("❌ Esta subasta ya no existe")
                return
                
            subasta = fantasy_data['subastas'][subasta_id]
            
            # Construir mensaje del historial
            mensaje = f"""
<b>📜 HISTORIAL COMPLETO DE SUBASTA</b>
━━━━━━━━━━━━━━━━━━
<b>⚽ Jugador:</b> {subasta['jugador_info']['name']}
<b>💰 Precio final:</b> <code>{subasta['precio_actual']:.2f}</code>
<b>🏁 Estado:</b> <code>{subasta['estado'].capitalize()}</code>
<b>👤 Vendedor:</b> {await obtener_nombre_usuario(subasta['vendedor_id'])}
<b>📅 Fecha inicio:</b> {subasta['fecha_inicio']}
<b>📅 Fecha fin:</b> {datetime.fromtimestamp(subasta['fecha_fin']).strftime('%Y-%m-%d %H:%M:%S')}

<b>📊 Todas las pujas:</b>
"""
            if subasta['pujas']:
                for i, puja in enumerate(subasta['pujas'], 1):
                    mensaje += (
                        f"\n{i}. <code>{puja['monto']:.2f}</code> por "
                        f"{await obtener_nombre_usuario(puja['postor_id'])} "
                        f"({puja['fecha']})"
                    )
            else:
                mensaje += "\nℹ️ No se recibieron pujas"
            
            # Botones de navegación
            keyboard = []
            
            if str(query.from_user.id) == subasta['vendedor_id']:
                keyboard.append([InlineKeyboardButton(
                    "📤 Volver a Mis Subastas",
                    callback_data='mis_subastas'
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    "💹 Volver a Subastas",
                    callback_data='listar_subastas'
                )])
            
            await query.edit_message_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error en ver_historial_subasta: {str(e)}")
        traceback.print_exc()
        await query.edit_message_text(
            "⚠️ Ocurrió un error al cargar el historial. Por favor intenta nuevamente.",
            parse_mode='HTML'
        )        
        
        


# Variables globales al inicio del archivo
TORNEO_FILE = "torneo_actual.json"
TORNEO_ACTIVO = False
TORNEO_CONFIG = {
    "tipo_premio": None,
    "monto_entrada": 0,
    "admin_id": "7031172659",
    "participantes": {},
    "premios": {},
    "estado": "inactivo",
    "hora_inicio": None,
    "hora_fin_inscripciones": None,
    "partidos": [],
    "programados": [],
    "configuracion": {
        "max_participantes": 20,
        "min_participantes": 4
    }
}



async def torneo_handler(update: Update, context: CallbackContext):
    global TORNEO_ACTIVO, TORNEO_CONFIG
    user_id = str(update.effective_user.id)
    
    # Verificar si es el admin
    if user_id != TORNEO_CONFIG["admin_id"]:
        await update.message.reply_text("❌ Solo el administrador puede iniciar torneos.")
        return

    # Inicializar bote si no existe
    if os.path.exists(RANKING_FILE):
        with open(RANKING_FILE, 'r') as f:
            ranking_data = json.load(f)
    else:
        ranking_data = {}

    if "bote" not in ranking_data:
        ranking_data["bote"] = {
            "balance": 0,
            "creditos": 0,
            "bono": 0,
            "barriles": 0
        }

    # Guardar nuevamente el archivo con el campo bote añadido (si se agregó)
    with open(RANKING_FILE, 'w') as f:
        json.dump(ranking_data, f, indent=2)

    
    tipo_premio = context.args[0].lower()
    if tipo_premio not in ['bono', 'balance', 'creditos']:
        await update.message.reply_text("❌ Tipo de premio inválido. Usa: bono, balance o creditos")
        return
    
    try:
        monto = int(context.args[1])
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Monto debe ser un número positivo")
        return
    
    # Configurar torneo
    TORNEO_CONFIG = {
        "tipo_premio": tipo_premio,
        "monto_entrada": monto,
        "admin_id": user_id,
        "participantes": {},
        "premios": {
            "primer_lugar": 0,
            "segundo_lugar": 0,
            "tercer_lugar": 0
        },
        "estado": "inscripcion",
        "hora_inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hora_fin_inscripciones": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
        "partidos": [],  # Todos los partidos jugados
        "programados": []
    }
    TORNEO_ACTIVO = True
    
    # Guardar torneo
    with open(TORNEO_FILE, 'w') as f:
        json.dump(TORNEO_CONFIG, f)
    
    # Notificar a todos los jugadores
    await notificar_inicio_torneo(context, tipo_premio, monto)
    
    # Mensaje de confirmación
    keyboard = [
        [InlineKeyboardButton("🔍 Ver Torneo", callback_data='torneo_info')],
        [InlineKeyboardButton("📊 Participantes (0)", callback_data='torneo_participantes')]
    ]
    
    await update.message.reply_text(
        f"🎉 <b>TORNEO INICIADO</b> 🎉\n\n"
        f"🏆 <b>Tipo:</b> {tipo_premio.upper()}\n"
        f"💰 <b>Entrada:</b> {monto}\n"
        f"⏳ <b>Inscripciones abiertas por 3 horas</b>\n\n"
        f"¡Los jugadores recibieron notificaciones!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    # Programar finalización de inscripciones
    context.job_queue.run_once(finalizar_inscripciones, 3600, name="finalizar_inscripciones")

async def notificar_inicio_torneo(context: CallbackContext, tipo_premio: str, monto: int):
    fantasy_data = await load_fantasy_data()
    
    for user_id in fantasy_data.keys():
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Participar", callback_data='torneo_unirse')],
                [InlineKeyboardButton("📊 Ver Detalles", callback_data='torneo_info')]
            ]
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 <b>¡NUEVO TORNEO DISPONIBLE!</b> 🎉\n\n"
                     f"🏆 <b>Tipo de premio:</b> {tipo_premio.upper()}\n"
                     f"💰 <b>Costo de entrada:</b> {monto}\n"
                     f"⏳ <b>Tienes 1 hora para inscribirte</b>\n\n"
                     f"¡Participa y gana grandes premios!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"No se pudo notificar al usuario {user_id}: {str(e)}")

async def mostrar_info_torneo(query):
    global TORNEO_CONFIG
    
    # Verificar si el torneo está configurado
    if TORNEO_CONFIG["tipo_premio"] is None:
        await query.edit_message_text(
            text="ℹ️ No hay ningún torneo activo en este momento.",
            parse_mode='HTML'
        )
        return
    
    participantes_count = len(TORNEO_CONFIG["participantes"])
    premio_total = participantes_count * TORNEO_CONFIG["monto_entrada"]
    premio_neto = premio_total * 0.9  # 10% para la casa
    
    # Calcular premios
    primer_lugar = premio_neto * 0.5
    segundo_lugar = premio_neto * 0.3
    tercer_lugar = premio_neto * 0.2
    
    # Actualizar premios en config
    TORNEO_CONFIG["premios"] = {
        "primer_lugar": primer_lugar,
        "segundo_lugar": segundo_lugar,
        "tercer_lugar": tercer_lugar
    }
    
    mensaje = f"""
🏆 <b>INFORMACIÓN DEL TORNEO</b> 🏆
━━━━━━━━━━━━━━━━━━
<b>Tipo de premio:</b> {TORNEO_CONFIG["tipo_premio"].upper() if TORNEO_CONFIG["tipo_premio"] else 'No definido'}
<b>Costo de entrada:</b> {TORNEO_CONFIG["monto_entrada"]}
<b>Participantes:</b> {participantes_count}

💰 <b>Premios:</b>
🥇 1er Lugar: {int(primer_lugar)} {TORNEO_CONFIG["tipo_premio"].upper() if TORNEO_CONFIG["tipo_premio"] else ''}
🥈 2do Lugar: {int(segundo_lugar)} {TORNEO_CONFIG["tipo_premio"].upper() if TORNEO_CONFIG["tipo_premio"] else ''}
🥉 3er Lugar: {int(tercer_lugar)} {TORNEO_CONFIG["tipo_premio"].upper() if TORNEO_CONFIG["tipo_premio"] else ''}

⏳ <b>Estado:</b> {TORNEO_CONFIG["estado"].replace('_', ' ').title() if TORNEO_CONFIG["estado"] else 'Inactivo'}
"""
    if TORNEO_CONFIG["estado"] == "inscripcion":
        fin_inscripciones = datetime.strptime(TORNEO_CONFIG["hora_fin_inscripciones"], "%Y-%m-%d %H:%M:%S")
        ahora = datetime.now()
        diferencia = fin_inscripciones - ahora
        horas, resto = divmod(diferencia.seconds, 3600)
        minutos = resto // 60
        mensaje += f"\n🕒 <b>Tiempo restante para inscribirse:</b> {horas}h {minutos}m"

    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar", callback_data='torneo_info')],
        [InlineKeyboardButton("📊 Participantes", callback_data='torneo_participantes')]
    ]
    
    if TORNEO_CONFIG["estado"] == "inscripcion":
        keyboard[0].append(InlineKeyboardButton("✅ Unirse", callback_data=f'torneo_unirse_{query.from_user.id}'))
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
                
                
async def unirse_al_torneo(update: Update, context: CallbackContext):
    try:
        
        query = update.callback_query
        await query.answer()
        user_id = str(update.effective_user.id)

        # Verificar si el usuario tiene 11 titulares configurados
        fantasy_data = await load_fantasy_data()
        if user_id in fantasy_data:
            # Usar la nueva función de validación
            if not validar_titulares(fantasy_data[user_id]):
                await query.edit_message_text(
                    "❌ Debes configurar exactamente 11 titulares antes de unirte al torneo.\n\n"
                    "Por favor ve a 'Mi Equipo' > 'Cambiar formación' y selecciona tus 11 jugadores titulares.",
                    parse_mode='HTML'
                )
                # Mostrar botón para ir a configurar alineación
                keyboard = [
                    [InlineKeyboardButton("⚽ Configurar Alineación", callback_data='mi_equipo')],
                    [InlineKeyboardButton("🏆 Ver Torneo", callback_data='torneo_info')]
                ]
                await query.message.reply_text(
                    text="¿Necesitas ayuda para configurar tu alineación?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
                return
       

        if TORNEO_CONFIG["estado"] != "inscripcion":
            msg = "❌ Las inscripciones están cerradas."
            print(msg)
            await query.message.reply_text(msg)
            return

        if user_id in TORNEO_CONFIG["participantes"]:
            msg = "✅ Ya estás inscrito en el torneo."
            print(msg)
            await query.message.reply_text(msg)
            return

        async with lock_data:
            user_data = await load_data()
            

        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
            
        monto = TORNEO_CONFIG["monto_entrada"]
        tipo = TORNEO_CONFIG["tipo_premio"]

        suficiente = False
        if tipo == "bono":
            bono = user_data["Bono_apuesta"].get(user_id, {}).get("Bono", 0)
            suficiente = bono >= monto
        elif tipo == "balance":
            balance = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
            suficiente = balance >= monto
        elif tipo == "creditos":
            creditos = fantasy_data.get(user_id, {}).get("credits", 0)
            suficiente = creditos >= monto

        if not suficiente:
            msg = f"❌ Fondos insuficientes en {tipo}"
            print(msg)
            await query.message.reply_text(msg)
            return

        if tipo == "bono":
            user_data["Bono_apuesta"][user_id]["Bono"] -= monto
        elif tipo == "balance":
            user_data["usuarios"][user_id]["Balance"] -= monto
        elif tipo == "creditos":
            fantasy_data[user_id]["credits"] -= monto

        nombre = user_data["usuarios"].get(user_id, {}).get("Nombre", f"Usuario {user_id[:5]}")
        print(f"\n👤 Registrando participante: {nombre}")

        # Inicializar datos del participante con estadísticas
        TORNEO_CONFIG["participantes"][user_id] = {
            "nombre": nombre,
            "pago": monto,
            "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "equipo": fantasy_data.get(user_id, {}).get("team", []),
            "estadisticas": {
                "puntos": 0,
                "diferencia_goles": 0,
                "goles_favor": 0,
                "goles_contra": 0,
                "partidos_jugados": 0,
                "victorias": 0,
                "derrotas": 0,
                "empates": 0
            }
        }

        async with lock_data:
            await save_data(user_data)

        async with lock_fantasy:
            await save_fantasy_data(fantasy_data)

        with open(TORNEO_FILE, 'w') as f:
            json.dump(TORNEO_CONFIG, f)
        print("Torneo guardado en archivo")

        nuevo_texto = (
            "🎟️ <b>¡INSCRIPCIÓN CONFIRMADA!</b>\n\n"
            f"• Has pagado: {monto} {tipo}\n"
            f"• Estado: <b>Inscrito</b>\n"
            f"• Participantes totales: {len(TORNEO_CONFIG['participantes'])}"
        )
        await query.edit_message_text(
            text=nuevo_texto,
            parse_mode='HTML'
        )

        participantes_count = len(TORNEO_CONFIG["participantes"])
        msg_admin = (f"📢 Nuevo participante en el torneo!\n\n"
                    f"👤 {nombre}\n"
                    f"💰 Pagó {monto} {tipo}\n"
                    f"👥 Total participantes: {participantes_count}")
        
        try:
            await context.bot.send_message(
                chat_id=TORNEO_CONFIG["admin_id"],
                text=msg_admin,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"❌ Error notificando al admin: {str(e)}")

        print("=== INSCRIPCIÓN EXITOSA ===")

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO en unirse_al_torneo: {str(e)}")
        traceback.print_exc()
        if 'query' in locals():
            await query.message.reply_text("⚠️ Error al procesar tu inscripción")

async def mostrar_participantes(update: Update, context: CallbackContext):
    """Muestra los participantes del torneo con más logging para diagnóstico"""
    query = update.callback_query
    await query.answer()
    
    try:
        # 1. Verificar acceso al archivo
        if not os.path.exists(TORNEO_FILE):
            logging.error(f"Archivo no encontrado: {TORNEO_FILE}")
            await query.edit_message_text("ℹ️ No hay torneo activo (archivo no encontrado)", parse_mode='HTML')
            return

        # 2. Cargar datos con más información de diagnóstico
        try:
            with open(TORNEO_FILE, 'r') as f:
                contenido = f.read()  # Leer primero como texto para logging
                logging.debug(f"Contenido del archivo: {contenido[:200]}...")  # Log parcial
                
                torneo_data = json.loads(contenido)
                logging.debug(f"Datos cargados: {torneo_data.keys()}")
                
        except json.JSONDecodeError as je:
            logging.error(f"Error decodificando JSON: {str(je)}")
            await query.edit_message_text("❌ Error en formato del torneo", parse_mode='HTML')
            return
        except Exception as e:
            logging.error(f"Error leyendo archivo: {str(e)}")
            await query.edit_message_text("❌ Error técnico al leer datos", parse_mode='HTML')
            return

        # 3. Verificar participantes con más logging
        participantes = torneo_data.get("participantes", {})
        logging.debug(f"Participantes encontrados: {len(participantes)}")
        
        if not participantes:
            logging.debug("No hay participantes en los datos")
            await query.edit_message_text("ℹ️ No hay participantes aún", parse_mode='HTML')
            return

        # 4. Construir mensaje con verificación
        mensaje = "👥 <b>PARTICIPANTES DEL TORNEO</b> 👥\n━━━━━━━━━━━━━━━━━━\n"
        
        for i, (user_id, datos) in enumerate(participantes.items(), 1):
            nombre = datos.get('nombre', f'Usuario {user_id[:5]}')
            pago = datos.get('pago', 0)
            tipo_premio = torneo_data.get('tipo_premio', '')
            
            linea = f"\n{i}. {nombre} - Pagó {pago} {tipo_premio.upper()}"
            mensaje += linea
            logging.debug(f"Añadido participante: {linea.strip()}")

        # 5. Envío con verificación de cambios
        try:
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data='torneo_participantes')],
                [InlineKeyboardButton("🔙 Volver", callback_data='torneo_info')]
            ]
            
            await query.edit_message_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            logging.debug("Mensaje actualizado correctamente")
            
        except Exception as e:
            if "Message is not modified" in str(e):
                logging.debug("El mensaje no requería cambios")
                await query.answer("✅ La información está actualizada", show_alert=False)
            else:
                logging.error(f"Error editando mensaje: {str(e)}")
                await query.edit_message_text(
                    "⚠️ Error al actualizar la lista de participantes",
                    parse_mode='HTML'
                )

    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}", exc_info=True)
        await query.edit_message_text(
            "⚠️ Error crítico al mostrar datos de participantes",
            parse_mode='HTML'
        )
async def mostrar_info_torneo_detallada(update: Update, context: CallbackContext):
    """Muestra TODA la información del torneo de forma estructurada"""
    # Obtener el query correctamente
    query = update.callback_query if hasattr(update, 'callback_query') else update
    message = query.message if hasattr(query, 'message') else query
    await query.answer() if hasattr(query, 'answer') else None
    
    try:
        # Cargar datos del torneo
        with open(TORNEO_FILE, 'r') as f:
            torneo = json.load(f)

        # Crear mensaje principal
        msg = "<b>🏆 PANEL COMPLETO DEL TORNEO</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🔹 <b>Estado:</b> {}\n".format(torneo.get('estado', 'Desconocido').replace('_', ' ').title())
        msg += "💰 <b>Tipo Premio:</b> {} | 🎫 <b>Entrada:</b> {}\n".format(
            torneo.get('tipo_premio', 'N/A').upper(),
            torneo.get('monto_entrada', 0)
        )
        msg += "⏳ <b>Inicio:</b> {} | 🏁 <b>Fin Inscripciones:</b> {}\n\n".format(
            torneo.get('hora_inicio', 'N/A'),
            torneo.get('hora_fin_inscripciones', 'N/A')
        )

        # Sección de participantes (CORREGIDO - sin duplicación)
        participantes = torneo.get('participantes', {})
        if participantes:
            msg += "👥 <b>PARTICIPANTES ({})</b>\n".format(len(participantes))
            
            
            for i, (user_id, data) in enumerate(participantes.items(), 1):
                msg += "│ {:2d}. {:<22} {} │\n".format(
                    i, 
                    data.get('nombre', user_id[:6])[:22],  # Limitar a 22 caracteres
                    "✅" if data.get('activo', True) else "❌"
                )
            

      

        # Sección de premios (ejemplo)
        if torneo.get('premios'):
            msg += "💰 <b>DISTRIBUCIÓN DE PREMIOS</b>\n"
            msg += "├ 🥇 1er lugar: {} {}\n".format(
                torneo['premios'].get('primer_lugar', 0),
                torneo.get('tipo_premio', '').upper()
            )
            msg += "├ 🥈 2do lugar: {} {}\n".format(
                torneo['premios'].get('segundo_lugar', 0),
                torneo.get('tipo_premio', '').upper()
            )
            msg += "└ 🥉 3er lugar: {} {}\n\n".format(
                torneo['premios'].get('tercer_lugar', 0),
                torneo.get('tipo_premio', '').upper()
            )

        # Teclado interactivo
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='torneo_info')],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data='juego_fantasy')]
        ]

        # Enviar mensaje
        try:
            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            else:
                await message.reply_text(
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            logging.error(f"Error al enviar mensaje: {str(e)}")

    except Exception as e:
        logging.error(f"Error en mostrar_info_torneo_detallada: {str(e)}")
        error_msg = "⚠️ Error al cargar la información del torneo"
        if hasattr(query, 'edit_message_text'):
            await query.edit_message_text(error_msg, parse_mode='HTML')
        else:
            await message.reply_text(error_msg, parse_mode='HTML')

        # Sección de premios
        if torneo.get('premios'):
            msg += "💰 <b>DISTRIBUCIÓN DE PREMIOS</b>\n"
            msg += "├ 🥇 1er lugar: {} {}\n".format(
                torneo['premios'].get('primer_lugar', 0),
                torneo.get('tipo_premio', '').upper()
            )
            msg += "├ 🥈 2do lugar: {} {}\n".format(
                torneo['premios'].get('segundo_lugar', 0),
                torneo.get('tipo_premio', '').upper()
            )
            msg += "└ 🥉 3er lugar: {} {}\n\n".format(
                torneo['premios'].get('tercer_lugar', 0),
                torneo.get('tipo_premio', '').upper()
            )

        # Sección de grupos (si existe)
        if 'grupos' in torneo:
            msg += "📋 <b>TABLA DE GRUPOS</b>\n"
            for grupo, datos in torneo['grupos'].items():
                msg += "\n<b>Grupo {}</b>\n".format(grupo)
                sorted_players = sorted(
                    datos.items(),
                    key=lambda x: (-x[1]['puntos'], -x[1]['diferencia_goles'])
                )
                
                for i, (user_id, stats) in enumerate(sorted_players, 1):
                    nombre = participantes[user_id]['nombre']
                    msg += "├ {:2d}. {:<15} Pts: {:2d} | DG: {:2d}\n".format(
                        i, nombre[:15], 
                        stats['puntos'], 
                        stats['diferencia_goles']
                    )

        # Crear teclado interactivo
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar Todo", callback_data='ver_torneo_completo')],
            [
                InlineKeyboardButton("👥 Solo Participantes", callback_data='torneo_participantes'),
                InlineKeyboardButton("📊 Solo Estadísticas", callback_data='ver_estadisticas')
            ],
            [
                InlineKeyboardButton("⚽ Últimos Partidos", callback_data='ver_partidos'),
                InlineKeyboardButton("🔜 Próximos Enfrentamientos", callback_data='ver_proximos')
            ],
            [InlineKeyboardButton("🏆 Menú Torneo", callback_data='mostrar_sistema_torneo')]
        ]

        # Enviar mensaje (con paginación si es muy largo)
        if len(msg) > 4000:  # Límite de Telegram
            partes = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for i, parte in enumerate(partes, 1):
                if i == 1:
                    await query.edit_message_text(
                        text=parte,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=parte,
                        parse_mode='HTML'
                    )
        else:
            await query.edit_message_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    except Exception as e:
        logging.error(f"Error en ver_torneo_completo: {str(e)}")
        await query.edit_message_text(
            "⚠️ Error al cargar la información completa del torneo",
            parse_mode='HTML'
        )                                                 
async def mostrar_sistema_torneo(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    try:
        if not os.path.exists(TORNEO_FILE):
            torneo_data = {
                "tipo_premio": None,
                "monto_entrada": 0,
                "admin_id": "7031172659",
                "participantes": {},
                "premios": {},
                "estado": "inactivo",
                "hora_inicio": None,
                "hora_fin_inscripciones": None,
                "fase_actual": None,
                "partidos": [],
                "proximos_partidos": []
            }
        else:
            with open(TORNEO_FILE, 'r') as f:
                torneo_data = json.load(f)

        torneo_activo = torneo_data.get("estado") in ["inscripcion", "en_progreso"]
        participantes_count = len(torneo_data.get("participantes", {}))
        fase_actual = torneo_data.get("fase_actual", "No iniciada")

        mensaje_principal = f"""
🏆 <b>SISTEMA DE TORNEOS</b> 🏆
━━━━━━━━━━━━━━━━━━
{'🔵 <b>Torneo Activo</b>' if torneo_activo else '🔴 <b>Sin torneo activo</b>'}
"""

        if torneo_activo:
            tiempo_restante = ""
            if torneo_data["estado"] == "inscripcion" and torneo_data.get("hora_fin_inscripciones"):
                fin_insc = datetime.strptime(torneo_data["hora_fin_inscripciones"], "%Y-%m-%d %H:%M:%S")
                diferencia = fin_insc - datetime.now()
                horas, resto = divmod(diferencia.seconds, 3600)
                minutos = resto // 60
                tiempo_restante = f"\n⏳ <b>Tiempo restante inscripciones:</b> {horas}h {minutos}m"

            mensaje_principal += f"""
📋 <b>Información Actual:</b>
├ Tipo: {torneo_data.get("tipo_premio", "").upper()}
├ Entrada: {torneo_data.get("monto_entrada", 0)}
├ Participantes: {participantes_count}
├ Estado: {torneo_data.get("estado", "").replace('_', ' ').title()}
└ Fase: {fase_actual}
{tiempo_restante}
"""

            if torneo_data["estado"] == "en_progreso":
                partidos_jugados = len(torneo_data.get("partidos", []))
                partidos_pendientes = len(torneo_data.get("proximos_partidos", []))
                
                mensaje_principal += f"""
📊 <b>Progreso del Torneo:</b>
├ Partidos jugados: {partidos_jugados}
└ Partidos pendientes: {partidos_pendientes}
"""

                if partidos_jugados > 0:
                    goles_totales = sum(p.get("goles1", 0) + p.get("goles2", 0) for p in torneo_data.get("partidos", []))
                    promedio_goles = goles_totales / partidos_jugados if partidos_jugados > 0 else 0
                    
                    mensaje_principal += f"""
⚽ <b>Estadísticas:</b>
├ Goles totales: {goles_totales}
└ Promedio goles/partido: {promedio_goles:.1f}
"""

        teclado = []

        # Admin
        if str(update.effective_user.id) == torneo_data.get("admin_id", ""):
            if not torneo_activo:
                teclado.append([
                    InlineKeyboardButton("➕ Crear Torneo", callback_data='crear_torneo_menu')
                ])
            else:
                teclado.append([
                    InlineKeyboardButton("🛑 Finalizar Torneo", callback_data='cancelar_torneo'),
                    InlineKeyboardButton("📊 Estadísticas", callback_data='admin_estadisticas')
                ])

        if torneo_activo:
            teclado.extend([
                [
                    InlineKeyboardButton("📋 Información Completa", callback_data='torneo_info'),
                    InlineKeyboardButton("👥 Participantes", callback_data='torneo_participantes')
                ],
                [
                    InlineKeyboardButton("📅 Progreso", callback_data='progreso_torneo'),
                    InlineKeyboardButton("⚽ Últimos Resultados", callback_data='ultimos_resultados')
                ]
            ])

            if torneo_data.get("estado") == "inscripcion":
                teclado.append([InlineKeyboardButton("✅ Unirse al Torneo", callback_data='torneo_unirse')])

            elif torneo_data.get("estado") == "en_progreso":
                teclado.append([
                    InlineKeyboardButton("🏆 Tabla de Posiciones", callback_data='progreso_torneo'),
                    InlineKeyboardButton("🔍 Mis Partidos", callback_data='mis_partidos')
                ])

        # Utilidad y ayuda
        teclado.append([
            InlineKeyboardButton("📚 Tutorial", callback_data='tutorial_torneos_0'),
            InlineKeyboardButton("❓ Ayuda", callback_data='tutorial_torneos_0')
        ])

        teclado.append([
            InlineKeyboardButton("🔄 Actualizar", callback_data='actualizar_torneo_menu')
        ])

        # Botón volver
        if query:
            teclado.append([InlineKeyboardButton("🔙 Menú Principal", callback_data='juego_fantasy')])

        reply_markup = InlineKeyboardMarkup(teclado)

        try:
            if query:
                await message.edit_text(
                    text=mensaje_principal,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await message.reply_text(
                    text=mensaje_principal,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        except Exception as e:
            logging.error(f"Error mostrando sistema de torneos: {str(e)}")
            error_msg = "⚠️ Ocurrió un error al mostrar el sistema de torneos."
            if "Message is not modified" in str(e):
                error_msg = "✅ La información ya está actualizada."
            await message.reply_text(error_msg, parse_mode='HTML')

    except json.JSONDecodeError:
        await message.reply_text(
            "❌ Error al leer los datos del torneo. El archivo podría estar corrupto.",
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error en mostrar_sistema_torneo: {str(e)}")
        traceback.print_exc()
        await message.reply_text(
            "⚠️ Ocurrió un error al cargar la información del torneo.",
            parse_mode='HTML'
        )



async def mostrar_menu_creacion_torneo(query):
    """Muestra el menú de creación de torneo para administradores"""
    keyboard = [
        [InlineKeyboardButton("💰 Premio en Bono", callback_data='crear_torneo_bono')],
        [InlineKeyboardButton("💵 Premio en Balance", callback_data='crear_torneo_balance')],
        [InlineKeyboardButton("🪙 Premio en Créditos", callback_data='crear_torneo_creditos')],
        [InlineKeyboardButton("🔙 Volver", callback_data='actualizar_torneo_menu')]
    ]
    
    await query.edit_message_text(
        text="🎮 <b>CREAR NUEVO TORNEO</b>\n\n"
             "Selecciona el tipo de premio para el torneo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


        
async def finalizar_inscripciones(context: CallbackContext):
    global TORNEO_ACTIVO, TORNEO_CONFIG

    participantes_count = len(TORNEO_CONFIG["participantes"])
    if participantes_count < 2:
        TORNEO_CONFIG["estado"] = "cancelado"
        mensaje = "❌ Torneo cancelado por falta de participantes (mínimo 4)"
        
        # Devolver fondos
        await devolver_fondos_inscripciones()
    else:
        TORNEO_CONFIG["estado"] = "en_progreso"
        mensaje = "🏆 ¡El torneo ha comenzado! Los partidos se jugarán automáticamente."

        # ✅ Notificar antes de iniciar torneo
        await notificar_fin_inscripciones(context, mensaje)

        # ✅ Iniciar torneo después de notificar
        await iniciar_torneo(context)

        return  # Ya se notificó

    # Guardar estado
    with open(TORNEO_FILE, 'w') as f:
        json.dump(TORNEO_CONFIG, f)

    # Solo notificar en caso de cancelación
    if participantes_count < 2:
        await notificar_fin_inscripciones(context, mensaje)



async def devolver_fondos_inscripciones():
    global TORNEO_CONFIG

    tipo = TORNEO_CONFIG["tipo_premio"]

    # Cargar datos protegidos por locks
    async with lock_data:
        user_data = await load_data()
    async with lock_fantasy:
        fantasy_data = await load_fantasy_data()

    # Devolver fondos según el tipo
    for user_id, datos in TORNEO_CONFIG["participantes"].items():
        monto = datos["pago"]

        if tipo == "bono":
            if user_id in user_data["Bono_apuesta"]:
                user_data["Bono_apuesta"][user_id]["Bono"] += monto
        elif tipo == "balance":
            if user_id in user_data["usuarios"]:
                user_data["usuarios"][user_id]["Balance"] += monto
        elif tipo == "creditos":
            if user_id in fantasy_data:
                fantasy_data[user_id]["credits"] += monto

    # Guardar datos protegidos por locks
    async with lock_data:
        await save_data(user_data)
    async with lock_fantasy:
        await save_fantasy_data(fantasy_data)

async def notificar_fin_inscripciones(context: CallbackContext, mensaje: str):
    global TORNEO_CONFIG
    
    for user_id in TORNEO_CONFIG["participantes"].keys():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=mensaje,
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"No se pudo notificar al usuario {user_id}: {str(e)}")
    
    # Notificar al admin
    try:
        participantes_count = len(TORNEO_CONFIG["participantes"])
        await context.bot.send_message(
            chat_id=TORNEO_CONFIG["admin_id"],
            text=f"🏁 INSCRIPCIONES FINALIZADAS\n\n"
                 f"🔹 Estado: {TORNEO_CONFIG['estado'].replace('_', ' ').title()}\n"
                 f"👥 Participantes: {participantes_count}\n"
                 f"💰 Recaudación total: {participantes_count * TORNEO_CONFIG['monto_entrada']} {TORNEO_CONFIG['tipo_premio']}",
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error notificando al admin: {str(e)}")
        

async def iniciar_torneo(context: CallbackContext):
    """Inicia un torneo con sistema de todos contra todos"""
    print("\n=== INICIANDO TORNEO ===")
    
    try:
        async with lock_torneo:
            with open(TORNEO_FILE, 'r') as f:
                torneo_data = json.load(f)
            
            participantes = list(torneo_data["participantes"].keys())
            if len(participantes) < 2:
                print("❌ Menos de 2 participantes. Cancelando...")
                torneo_data["estado"] = "cancelado"
                await guardar_torneo(torneo_data)
                return
            
            # ✅ Generar ida y vuelta si no se ha hecho ya
            if not torneo_data.get("programados"):
                partidos = generar_emparejamientos(participantes)  # ← Esto debe dar 2 partidos ida/vuelta
                torneo_data["programados"] = partidos
                torneo_data["proximos_partidos"] = partidos.copy()
                print(f"✅ Partidos generados: {len(partidos)}")

            torneo_data.update({
                "estado": "en_progreso",
                "fase_actual": "Liga Todos contra Todos",
                "partidos": torneo_data.get("partidos", [])
            })
            
            await guardar_torneo(torneo_data)

            print(f"DEBUG - Programados: {len(torneo_data.get('programados', []))}")
            print(f"DEBUG - Próximos: {len(torneo_data.get('proximos_partidos', []))}")
        
        print("⏳ Iniciando primer partido...")
        await jugar_siguiente_partido(context)

    except Exception as e:
        print(f"🔥 ERROR: {str(e)}")
        traceback.print_exc()
        
        
async def guardar_torneo(data):
    """Guarda los datos del torneo asegurando consistencia"""
    with open(TORNEO_FILE, 'w') as f:
        json.dump(data, f)
    print("💾 Torneo guardado correctamente")
async def jugar_siguiente_partido(context: CallbackContext):
    """Juega el siguiente partido programado y actualiza estadísticas"""
    print("\n=== jugar_siguiente_partido ===")

    try:
        # 1. Leer fuera del lock para tener acceso luego
        with open(TORNEO_FILE, 'r') as f:
            torneo = json.load(f)

        if not torneo.get("proximos_partidos"):
            print("🏁 No hay más partidos por jugar")
            await finalizar_torneo(context)
            return

        partido = torneo["proximos_partidos"][0]  # ← solo visualización
        print("📂 PARTIDOS ANTES DE JUGAR:")
        print(f"- Total programados: {len(torneo.get('programados', []))}")
        print(f"- Total próximos: {len(torneo.get('proximos_partidos', []))}")
        for p in torneo.get("proximos_partidos", []):
            print(f"  • {p['local_id']} vs {p['visitante_id']} ({p.get('tipo', '-')})")

        # 2. Tomar y jugar partido dentro del lock
        async with lock_torneo:
            partido = torneo["proximos_partidos"].pop(0)
            local_id = partido["local_id"]
            visitante_id = partido["visitante_id"]

            print(f"⚽ Simulando partido: {local_id} vs {visitante_id}")

            try:
                resultado = await simular_partido(local_id, visitante_id, context)
                if not resultado:
                    raise ValueError("Resultado vacío")
            except Exception as e:
                print(f"⚠️ Error en simulación: {e}, usando resultado 0-0")
                resultado = {"goles_local": 0, "goles_visitante": 0}

            print(f"📊 Resultado simulado: {resultado}")

            partido_registrado = {
                "local": local_id,
                "visitante": visitante_id,
                "tipo": partido.get("tipo", "ida"),
                "resultado": resultado,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            torneo.setdefault("partidos", []).append(partido_registrado)

            # 3. Actualizar estadísticas
            def actualizar_estadisticas(user_id, gf, gc):
                stats = torneo["participantes"][user_id]["estadisticas"]
                stats["goles_favor"] += gf
                stats["goles_contra"] += gc
                stats["diferencia_goles"] = stats["goles_favor"] - stats["goles_contra"]
                stats["partidos_jugados"] += 1
                stats["puntos"] += 3 if gf > gc else 1 if gf == gc else 0
                key = "victorias" if gf > gc else "empates" if gf == gc else "derrotas"
                stats[key] += 1

            actualizar_estadisticas(local_id, resultado["goles_local"], resultado["goles_visitante"])
            actualizar_estadisticas(visitante_id, resultado["goles_visitante"], resultado["goles_local"])

            with open(TORNEO_FILE, 'w') as f:
                json.dump(torneo, f, indent=2)

            print("✅ Partido guardado y estadísticas actualizadas")
            print("📂 PARTIDOS DESPUÉS DE JUGAR:")
            print(f"- Total programados: {len(torneo.get('programados', []))}")
            print(f"- Total próximos: {len(torneo.get('proximos_partidos', []))}")
            for p in torneo.get("proximos_partidos", []):
                print(f"  • {p['local_id']} vs {p['visitante_id']} ({p.get('tipo', '-')})")

            await notificar_resultado_partido(context, partido_registrado)

        # 4. Ya fuera del lock, decidir si continuar
        if torneo.get("proximos_partidos"):
            print("⏳ Programando siguiente partido en 10 segundos...")
            await asyncio.sleep(15)
            await jugar_siguiente_partido(context)
        else:
            print("🏁 Torneo completado!")
            await finalizar_torneo(context)

    except Exception as e:
        print(f"❌ Error crítico en jugar_siguiente_partido: {str(e)}")
        traceback.print_exc()
                
async def simular_partido(local_id, visitante_id, context: CallbackContext):
    """Simula un partido entre dos equipos considerando solo titulares"""
    try:
        fantasy_data = await load_fantasy_data()

        equipo_local = [p for p in fantasy_data.get(local_id, {}).get("team", []) if p.get('is_titular', True)]
        equipo_visitante = [p for p in fantasy_data.get(visitante_id, {}).get("team", []) if p.get('is_titular', True)]

        if len(equipo_local) != 11 or len(equipo_visitante) != 11:
            for user_id, count in [(local_id, len(equipo_local)), (visitante_id, len(equipo_visitante))]:
                if count != 11:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"⚠️ <b>ALINEACIÓN INCOMPLETA</b>\n\n"
                                 f"Tu equipo tiene solo {count} titulares configurados.\n"
                                 f"Ve a 'Mi Equipo' > 'Cambiar formación' y selecciona tus 11 titulares.",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logging.error(f"No se pudo notificar al usuario {user_id}: {str(e)}")
            return None

        def calcular_puntuacion(equipo):
            total = 0
            for jugador in equipo:
                rating = float(jugador.get("rating") or 6.0)
                valor = float(jugador.get("value") or 50.0)
                goles = int(jugador.get("goals") or 0)
                asistencias = int(jugador.get("assists") or 0)
                partidos = int(jugador.get("appearances") or 1)

                contribucion = (rating * 2) + (valor * 0.01) + (goles * 0.5) + (asistencias * 0.3) + (partidos * 0.1)

                posicion = jugador.get("normalized_position", "Midfielder")
                if posicion == "Goalkeeper":
                    contribucion *= 1.1
                elif posicion == "Attacker":
                    contribucion *= 1.05

                total += contribucion

            return total * random.uniform(0.9, 1.1)

        puntuacion_local = calcular_puntuacion(equipo_local)
        puntuacion_visitante = calcular_puntuacion(equipo_visitante)
        diferencia = abs(puntuacion_local - puntuacion_visitante)

        if diferencia < 10:
            goles_local = random.randint(0, 2)
            goles_visitante = random.randint(0, 2)
        elif diferencia < 30:
            if puntuacion_local > puntuacion_visitante:
                goles_local = random.randint(1, 3)
                goles_visitante = random.randint(0, 2)
            else:
                goles_local = random.randint(0, 2)
                goles_visitante = random.randint(1, 3)
        else:
            if puntuacion_local > puntuacion_visitante:
                goles_local = random.randint(2, 5)
                goles_visitante = random.randint(0, 2)
            else:
                goles_local = random.randint(0, 2)
                goles_visitante = random.randint(2, 5)

        if diferencia < 15 and random.random() < 0.15:
            empate = max(goles_local, goles_visitante)
            goles_local = goles_visitante = empate

        return {
            "local_id": local_id,
            "visitante_id": visitante_id,
            "goles_local": goles_local,
            "goles_visitante": goles_visitante,
            "ganador": local_id if goles_local > goles_visitante else visitante_id if goles_visitante > goles_local else None,
            "timestamp": datetime.now().isoformat()
        }


    except Exception as e:
        logging.error(f"Error en simular_partido: {str(e)}")
        return None
                        
def generar_emparejamientos(participantes):
    """Genera todos los partidos posibles con ida y vuelta de forma estructurada"""
    emparejamientos = []
    n = len(participantes)
    
    if n < 2:
        return emparejamientos
    
    # Generar partidos de ida
    for i in range(n):
        for j in range(i+1, n):
            emparejamientos.append({
                "local_id": participantes[i],
                "visitante_id": participantes[j],
                "tipo": "ida"
            })
    
    # Generar partidos de vuelta
    for i in range(n):
        for j in range(i+1, n):
            emparejamientos.append({
                "local_id": participantes[j],
                "visitante_id": participantes[i],
                "tipo": "vuelta"
            })

    return emparejamientos        
        
async def verificar_partidos():
    async with lock_torneo:
        with open(TORNEO_FILE, 'r') as f:
            data = json.load(f)
            
        print("\n=== ESTADO ACTUAL ===")
        print(f"Total programados: {len(data.get('programados', []))}")
        print(f"Total jugados: {len(data.get('partidos', []))}")
        print(f"Primeros 2 programados: {data.get('programados', [])[:2]}")        

async def notificar_inicio_torneo_simplificado(context, num_participantes):
    """Notifica el inicio del torneo en formato todos contra todos"""
    mensaje = (
        "🏆 <b>¡COMIENZA EL TORNEO!</b> 🏆\n\n"
        f"🔹 Formato: Liga todos contra todos (ida y vuelta)\n"
        f"👥 Participantes: {num_participantes}\n"
        f"⚽ Partidos totales: {num_participantes * (num_participantes - 1)}\n\n"
        "Los partidos se jugarán automáticamente cada poco tiempo."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💹 Ver información", callback_data='torneo_info')]
    ])
    
    # Enviar a todos los participantes
    with open(TORNEO_FILE, 'r') as f:
        torneo_data = json.load(f)
    
    for user_id in torneo_data["participantes"]:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=mensaje,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"No se pudo notificar a {user_id}: {str(e)}")     


async def actualizar_estado_torneo():
    """Sincroniza la variable global con el archivo del torneo"""
    async with lock_torneo:
        try:
            # Cargar datos actuales del archivo
            if os.path.exists(TORNEO_FILE):
                with open(TORNEO_FILE, 'r') as f:
                    torneo_data = json.load(f)
            else:
                torneo_data = {
                    "participantes": {},
                    "partidos": [],
                    "premios": {},
                    "estado": "inactivo"
                }

            # Actualizar la variable global
            global TORNEO_CONFIG
            TORNEO_CONFIG.update(torneo_data)
            
            # Guardar cambios (para asegurar consistencia)
            with open(TORNEO_FILE, 'w') as f:
                json.dump(TORNEO_CONFIG, f, indent=2)
                
            return True
        except Exception as e:
            logging.error(f"Error en actualizar_estado_torneo: {str(e)}")
            return False
async def actualizar_resultados_torneo(local_id, visitante_id, goles_local, goles_visitante):
    """Actualiza los resultados en el sistema de torneos"""
    try:
        # Sincronizar estado actual primero
        if not await actualizar_estado_torneo():
            return False

        async with lock_torneo:
            # Crear registro del partido
            partido = {
                "local_id": local_id,
                "visitante_id": visitante_id,
                "goles_local": goles_local,
                "goles_visitante": goles_visitante,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Añadir a la lista de partidos
            TORNEO_CONFIG["partidos"].append(partido)

            # Actualizar estadísticas para ambos jugadores
            participantes = TORNEO_CONFIG["participantes"]
            
            # Función auxiliar para actualizar un participante
            def actualizar_participante(user_id, gf, gc):
                if user_id in participantes:
                    stats = participantes[user_id].setdefault("estadisticas", {
                        "puntos": 0,
                        "diferencia_goles": 0,
                        "goles_favor": 0,
                        "goles_contra": 0,
                        "partidos_jugados": 0,
                        "victorias": 0,
                        "derrotas": 0,
                        "empates": 0
                    })
                    
                    stats["partidos_jugados"] += 1
                    stats["goles_favor"] += gf
                    stats["goles_contra"] += gc
                    stats["diferencia_goles"] = stats["goles_favor"] - stats["goles_contra"]
                    
                    if gf > gc:
                        stats["victorias"] += 1
                        stats["puntos"] += 3
                    elif gf < gc:
                        stats["derrotas"] += 1
                    else:
                        stats["empates"] += 1
                        stats["puntos"] += 1

            # Actualizar ambos participantes
            actualizar_participante(local_id, goles_local, goles_visitante)
            actualizar_participante(visitante_id, goles_visitante, goles_local)

            # Guardar cambios definitivos
            with open(TORNEO_FILE, 'w') as f:
                json.dump(TORNEO_CONFIG, f, indent=2)
                
            return True

    except Exception as e:
        logging.error(f"Error en actualizar_resultados_torneo: {str(e)}")
        return False
        
                                                                
async def cargar_datos_torneo():
    """Carga los datos del torneo sincronizando archivo y variable global"""
    async with lock_torneo:
        try:
            if os.path.exists(TORNEO_FILE):
                with open(TORNEO_FILE, 'r') as f:
                    global TORNEO_CONFIG
                    TORNEO_CONFIG = json.load(f)
                    return TORNEO_CONFIG.copy()
            return None
        except Exception as e:
            logging.error(f"Error cargando datos del torneo: {str(e)}")
            return None                                                                

async def guardar_datos_torneo():
    """Guarda los datos del torneo asegurando consistencia"""
    async with lock_torneo:
        try:
            with open(TORNEO_FILE, 'w') as f:
                json.dump(TORNEO_CONFIG, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error guardando datos del torneo: {str(e)}")
            return False

        
async def notificar_resultado_partido(context, partido):
    """Notifica el resultado de un partido usando la estructura local/visitante"""
    try:
        # Cargar datos necesarios
        user_data = await load_data()
        fantasy_data = await load_fantasy_data()
        
        local_nombre = user_data["usuarios"].get(partido["local"], {}).get("Nombre", "Jugador Local")
        visitante_nombre = user_data["usuarios"].get(partido["visitante"], {}).get("Nombre", "Jugador Visitante")
        
        resultado = partido["resultado"]
        mensaje = f"⚽ <b>RESULTADO DEL PARTIDO</b> ⚽\n\n"
        mensaje += f"🏠 <b>Local:</b> {local_nombre}\n"
        mensaje += f"✈️ <b>Visitante:</b> {visitante_nombre}\n"
        mensaje += f"📌 <b>Tipo:</b> {partido.get('tipo', 'ida').capitalize()}\n\n"
        mensaje += f"🎯 <b>Resultado:</b> {resultado['goles_local']} - {resultado['goles_visitante']}\n"
        
        if resultado['ganador']:
            ganador_nombre = local_nombre if resultado['ganador'] == partido["local"] else visitante_nombre
            mensaje += f"🏆 <b>Ganador:</b> {ganador_nombre}\n"
        else:
            mensaje += "⚖️ <b>Empate</b>\n"
        
        # Enviar notificación a ambos jugadores
        for jugador_id in [partido["local"], partido["visitante"]]:
            try:
                await context.bot.send_message(
                    chat_id=jugador_id,
                    text=mensaje,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"No se pudo notificar a {jugador_id}: {str(e)}")
                
    except Exception as e:
        print(f"Error en notificar_partido: {str(e)}")
        traceback.print_exc()        
                
    


async def notificar_cambio_fase(context: ContextTypes.DEFAULT_TYPE):
    """Notifica el cambio de fase del torneo a todos los participantes"""
    try:
        with open(TORNEO_FILE, 'r') as f:
            torneo_data = json.load(f)
        
        mensaje = f"🔄 <b>CAMBIO DE FASE EN EL TORNEO</b>\n\n"
        mensaje += f"El torneo ha avanzado a la fase: <b>{torneo_data['fase_actual']}</b>\n\n"
        
        if torneo_data["fase_actual"] == "Eliminatorias":
            mensaje += "🏆 Los mejores equipos avanzan a las eliminatorias!\n"
            mensaje += "Cada partido es decisivo, no hay segundas oportunidades.\n"
        elif torneo_data["fase_actual"] == "Finalizado":
            mensaje += "🎉 ¡El torneo ha concluido! Pronto anunciaremos los ganadores.\n"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Ver progreso", callback_data='progreso_torneo')]
        ])

        # Enviar a todos los participantes
        for user_id in torneo_data["participantes"].keys():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=mensaje,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"No se pudo notificar al usuario {user_id}: {str(e)}")
                
    except Exception as e:
        logging.error(f"Error en notificar_cambio_fase: {str(e)}")
        traceback.print_exc()    
        
                              
async def mostrar_ayuda_torneo(update: Update, context: CallbackContext):
    """Muestra información de ayuda sobre el sistema de torneos"""
    query = update.callback_query
    await query.answer()
    
    mensaje = """
📚 <b>AYUDA DEL SISTEMA DE TORNEOS</b> 📚
━━━━━━━━━━━━━━━━━━

<u>Cómo participar:</u>
1. Únete al torneo durante la fase de inscripción
2. Paga la entrada requerida (en bonos, balance o créditos)
3. Sigue tus partidos y resultados

<u>Fases del torneo:</u>
- <b>Fase de Grupos:</b> Todos contra todos en grupos
- <b>Eliminatorias:</b> Partidos de eliminación directa
- <b>Final:</b> Definición del campeón

<u>Sistema de puntuación:</u>
- <b>Victoria:</b> 3 puntos
- <b>Empate:</b> 1 punto
- <b>Derrota:</b> 0 puntos

<u>Desempates:</u>
1. Diferencia de goles
2. Goles a favor
3. Enfrentamiento directo

<u>Premios:</u>
🥇 1er lugar: 50% del pozo
🥈 2do lugar: 30% del pozo
🥉 3er lugar: 20% del pozo

Usa los botones para navegar y consultar toda la información disponible.
"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Menú Principal", callback_data='mostrar_sistema_torneo')],
        [InlineKeyboardButton("❓ Contactar Soporte", url='https://t.me/tu_soporte')]
    ]
    
    await query.edit_message_text(
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
async def mostrar_mis_partidos(update: Update, context: CallbackContext):
    """Muestra los partidos de un usuario específico"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    try:
        with open(TORNEO_FILE, 'r') as f:
            torneo_data = json.load(f)
        
        if user_id not in torneo_data.get("participantes", {}):
            await query.edit_message_text("ℹ️ No estás participando en el torneo actual.")
            return
        
        mensaje = f"⚽ <b>TUS PARTIDOS EN EL TORNEO</b> ⚽\n━━━━━━━━━━━━━━━━━━\n"
        mensaje += f"\n👤 Participante: {torneo_data['participantes'][user_id]['nombre']}\n"
        
        # Buscar partidos del usuario
        partidos_usuario = []
        for partido in torneo_data.get("partidos", []):
            if user_id in [partido["jugador1"], partido["jugador2"]]:
                partidos_usuario.append(partido)
        
        if not partidos_usuario:
            mensaje += "\nℹ️ Aún no has jugado ningún partido."
        else:
            mensaje += f"\n📅 <b>Partidos jugados:</b> {len(partidos_usuario)}\n"
            
            for partido in partidos_usuario[-10:]:  # Mostrar últimos 10
                oponente_id = partido["jugador2"] if partido["jugador1"] == user_id else partido["jugador1"]
                goles_usuario = partido["goles1"] if partido["jugador1"] == user_id else partido["goles2"]
                goles_oponente = partido["goles2"] if partido["jugador1"] == user_id else partido["goles1"]
                
                resultado = ""
                if "ganador" in partido:
                    if partido["ganador"] == user_id:
                        resultado = "✅ Ganaste"
                    elif partido["ganador"] is None:
                        resultado = "⚖ Empate"
                    else:
                        resultado = "❌ Perdiste"
                
                mensaje += (
                    f"\n🆚 vs {torneo_data['participantes'][oponente_id]['nombre']}"
                    f"\n📊 {goles_usuario}-{goles_oponente} {resultado}"
                    f"\n🏆 Fase: {partido.get('fase', 'No especificada')}"
                    f"\n━━━━━━━━━━\n"
                )
        
        # Mostrar próximos partidos si existen
        proximos_partidos = []
        for partido in torneo_data.get("proximos_partidos", []):
            if user_id in [partido["jugador1"], partido["jugador2"]]:
                proximos_partidos.append(partido)
        
        if proximos_partidos:
            mensaje += "\n🔜 <b>Próximos partidos:</b>\n"
            for partido in proximos_partidos[:3]:  # Mostrar próximos 3
                oponente_id = partido["jugador2"] if partido["jugador1"] == user_id else partido["jugador1"]
                mensaje += f"\n🆚 vs {torneo_data['participantes'][oponente_id]['nombre']}"
                mensaje += f"\n🏆 Fase: {partido.get('fase', 'No especificada')}\n"
        
        # Teclado interactivo
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='mis_partidos')],
            [InlineKeyboardButton("📊 Tabla de Posiciones", callback_data='progreso_torneo')],
            [InlineKeyboardButton("🔙 Volver", callback_data='mostrar_sistema_torneo')]
        ]
        
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"Error en mostrar_mis_partidos: {str(e)}")
        await query.edit_message_text(
            "⚠️ Ocurrió un error al mostrar tus partidos.",
            parse_mode='HTML'
        )
        

        
async def mostrar_ultimos_resultados(update: Update, context: CallbackContext):
    """Muestra los últimos resultados de partidos con detalles"""
    query = update.callback_query
    await query.answer()
    
    try:
        with open(TORNEO_FILE, 'r') as f:
            torneo_data = json.load(f)
        
        if "partidos" not in torneo_data or not torneo_data["partidos"]:
            await query.edit_message_text("ℹ️ No hay resultados disponibles aún.")
            return
        
        mensaje = "📋 <b>ÚLTIMOS RESULTADOS</b> 📋\n━━━━━━━━━━━━━━━━━━\n"
        
        # Mostrar últimos 10 resultados con más detalles
        for partido in torneo_data["partidos"][-10:]:
            nombre1 = torneo_data["participantes"][partido["jugador1"]]["nombre"]
            nombre2 = torneo_data["participantes"][partido["jugador2"]]["nombre"]
            
            mensaje += f"\n⚔️ <b>{nombre1} vs {nombre2}</b>"
            mensaje += f"\n📅 {partido.get('fecha', 'Fecha no disponible')}"
            mensaje += f"\n🏟 {partido.get('fase', 'Fase no especificada')}"
            mensaje += f"\n🔢 <b>Resultado:</b> {partido['goles1']}-{partido['goles2']}"
            
            if "ganador" in partido:
                ganador = torneo_data["participantes"][partido["ganador"]]["nombre"] if partido["ganador"] else "Empate"
                mensaje += f"\n⭐ <b>Ganador:</b> {ganador}"
            
            mensaje += "\n━━━━━━━━━━\n"
        
        # Teclado interactivo
        keyboard = [
            [InlineKeyboardButton("📊 Ver Estadísticas", callback_data='estadisticas_torneo')],
            [InlineKeyboardButton("📅 Progreso Completo", callback_data='progreso_torneo')],
            [InlineKeyboardButton("🔙 Volver", callback_data='mostrar_sistema_torneo')]
        ]
        
        await query.edit_message_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"Error en mostrar_ultimos_resultados: {str(e)}")
        await query.edit_message_text(
            "⚠️ Ocurrió un error al mostrar los resultados.",
            parse_mode='HTML'
        )
        



async def mostrar_clasificacion(update: Update, context: CallbackContext):
    """Muestra la clasificación con todos los criterios y formato correcto"""
    try:
        # Manejo de mensajes/callbacks
        query = update.callback_query
        if query:
            await query.answer()
            message = query.message
            is_callback = True
        else:
            message = update.message
            is_callback = False

        # 1. Cargar datos del torneo con verificación exhaustiva
        try:
            with open(TORNEO_FILE, 'r') as f:
                torneo_data = json.load(f)
            
            # Verificar estructura básica
            if not isinstance(torneo_data, dict):
                raise ValueError("Datos del torneo inválidos")
                
            participantes = torneo_data.get("participantes", {})
            if not isinstance(participantes, dict):
                raise ValueError("Estructura de participantes inválida")
                
        except Exception as e:
            logging.error(f"Error cargando datos: {str(e)}")
            error_msg = "⚠️ Error al cargar datos del torneo"
            if is_callback:
                await message.edit_text(error_msg, parse_mode='HTML')
            else:
                await message.reply_text(error_msg, parse_mode='HTML')
            return

        # 2. Verificar si hay participantes
        if not participantes:
            no_data_msg = "ℹ️ No hay participantes registrados aún."
            if is_callback:
                await message.edit_text(no_data_msg, parse_mode='HTML')
            else:
                await message.reply_text(no_data_msg, parse_mode='HTML')
            return

        # 3. Ordenar con todos los criterios FIFA
        def clave_ordenamiento(item):
            stats = item[1].get("estadisticas", {})
            return (
                -stats.get("puntos", 0),            # 1. Puntos (descendente)
                -stats.get("diferencia_goles", 0),  # 2. Diferencia de goles
                -stats.get("goles_favor", 0),       # 3. Goles a favor
                stats.get("partidos_jugados", 0)    # 4. Menos partidos jugados (si hay empate)
            )

        clasificacion = sorted(participantes.items(), key=clave_ordenamiento)

        # 4. Construir mensaje con formato mejorado
        mensaje = [
            "🏆 <b>CLASIFICACIÓN OFICIAL</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔹 <b>Estado:</b> {torneo_data.get('estado', 'Desconocido').replace('_', ' ').title()}",
            f"🔹 <b>Participantes:</b> {len(participantes)}",
            f"🔹 <b>Tipo:</b> {torneo_data.get('tipo_premio', '').upper()}",
            ""
        ]

        # 5. Añadir premios si el torneo está activo/finalizado
        if torneo_data.get("estado") in ["inscripcion", "en_progreso", "finalizado"]:
            total_recaudado = len(participantes) * torneo_data.get("monto_entrada", 0)
            premio_total = total_recaudado * 0.9  # 10% para la casa
            
            mensaje.extend([
                "💰 <b>PREMIOS ESTIMADOS:</b>",
                f"🥇 1°: {int(premio_total * 0.5)} {torneo_data.get('tipo_premio', '').upper()}",
                f"🥈 2°: {int(premio_total * 0.3)}",
                f"🥉 3°: {int(premio_total * 0.2)}",
                ""
            ])

        # 6. Lista de participantes con estadísticas completas
        mensaje.append("📊 <b>POSICIONES ACTUALES:</b>")
        for pos, (jugador_id, datos) in enumerate(clasificacion, 1):
            stats = datos.get("estadisticas", {})
            nombre = html.escape(datos.get("nombre", f"Jugador {jugador_id[:6]}"))
            
            # Emoji de podio
            emoji_pos = ""
            if pos == 1: emoji_pos = "🥇"
            elif pos == 2: emoji_pos = "🥈"
            elif pos == 3: emoji_pos = "🥉"
            
            linea = (
                f"\n{emoji_pos}{pos}. <b>{nombre}</b>\n"
                f"   ⚽ Pts: {stats.get('puntos', 0)} | "
                f"📈 DG: {stats.get('diferencia_goles', 0)}\n"
                f"   ✅ V: {stats.get('victorias', 0)} | "
                f"⚖️ E: {stats.get('empates', 0)} | "
                f"❌ D: {stats.get('derrotas', 0)}\n"
                f"   ⚽ GF: {stats.get('goles_favor', 0)} | "
                f"🛡️ GC: {stats.get('goles_contra', 0)}"
            )
            mensaje.append(linea)

        # 7. Ganadores finales si el torneo terminó
        if torneo_data.get("estado") == "finalizado":
            mensaje.extend([
                "\n🏁 <b>RESULTADOS FINALES</b>",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ])
            
            premios = torneo_data.get("premios", {})
            for pos, (titulo, campo) in enumerate([
                ("🥇 CAMPEÓN", "primer_lugar"),
                ("🥈 SUBCAMPEÓN", "segundo_lugar"),
                ("🥉 TERCER PUESTO", "tercer_lugar")
            ], 1):
                jugador_id = torneo_data.get("ganadores", {}).get(campo)
                if jugador_id and jugador_id in participantes:
                    nombre = html.escape(participantes[jugador_id].get("nombre", ""))
                    mensaje.append(
                        f"{titulo}: {nombre} (+{premios.get(campo, 0)} "
                        f"{torneo_data.get('tipo_premio', '').upper()})"
                    )

        # 8. Unir todo el mensaje
        mensaje_final = "\n".join(mensaje)

        # 9. Teclado interactivo
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='progreso_torneo')],
            [InlineKeyboardButton("📊 Estadísticas", callback_data='estadisticas_torneo')],
            [InlineKeyboardButton("🏠 Menú", callback_data='mostrar_sistema_torneo')]
        ]

        # 10. Enviar/actualizar mensaje con manejo de errores
        try:
            if is_callback:
                await message.edit_text(
                    text=mensaje_final,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            else:
                await message.reply_text(
                    text=mensaje_final,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await query.answer("✅ La clasificación ya está actualizada")
            else:
                raise

    except Exception as e:
        logging.error(f"Error crítico en mostrar_clasificacion: {str(e)}")
        error_msg = "⚠️ Error grave al generar la clasificación"
        if is_callback:
            try:
                await message.edit_text(error_msg, parse_mode='HTML')
            except:
                await query.answer(error_msg)
        else:
            await message.reply_text(error_msg, parse_mode='HTML')
        


async def cancelar_torneo_handler(update: Update, context: CallbackContext):
    print("✅ Se activó cancelar_torneo_handler")

    try:
        # Manejo de datos
        if isinstance(update, CallbackQuery):
            query = update
            await query.answer()
            user_id = str(query.from_user.id)
            message = query.message  # Puede ser None
            chat = query.message.chat if query.message else update.effective_chat
        else:
            message = update.message
            user_id = str(update.effective_user.id)
            chat = update.effective_chat

        if not os.path.exists(TORNEO_FILE):
            await context.bot.send_message(chat_id=chat.id, text="ℹ️ No hay ningún torneo activo para cancelar.")
            return

        with open(TORNEO_FILE, 'r') as f:
            torneo_data = json.load(f)

        if user_id != torneo_data.get("admin_id"):
            await context.bot.send_message(chat_id=chat.id, text="❌ Solo el administrador del torneo puede cancelarlo.")
            return

        texto_confirmacion = (
            "⚠️ <b>CONFIRMAR CANCELACIÓN DE TORNEO</b>\n\n"
            f"Estás a punto de cancelar el torneo con:\n"
            f"• {len(torneo_data['participantes'])} participantes\n"
            f"• Premio en {torneo_data['tipo_premio']}\n"
            f"• Entrada de {torneo_data['monto_entrada']}\n\n"
            "¿Estás seguro que deseas cancelarlo?"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar Cancelación", callback_data='confirmar_cancelar_torneo')],
            [InlineKeyboardButton("❌ No Cancelar", callback_data='torneo_info')]
        ]

        if message:
            if isinstance(update, CallbackQuery):
                await message.edit_text(
                    text=texto_confirmacion,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            else:
                await message.reply_text(
                    text=texto_confirmacion,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        else:
            # Si no hay mensaje, enviar uno nuevo
            await context.bot.send_message(
                chat_id=chat.id,
                text=texto_confirmacion,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    except Exception as e:
        logging.error(f"Error en cancelar_torneo_handler: {str(e)}", exc_info=True)
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Ocurrió un error al intentar cancelar el torneo.")
        except Exception as inner_e:
            logging.error(f"Fallo al enviar mensaje de error: {str(inner_e)}")

async def confirmar_cancelar_torneo(update: CallbackQuery, context: CallbackContext):
    """Confirma y ejecuta la cancelación del torneo"""
    query = update.callback_query
    await query.answer()

    try:
        # Cargar datos del torneo
        with open(TORNEO_FILE, 'r') as f:
            torneo_data = json.load(f)

        # 1. Devolver fondos a los participantes
        tipo_premio = torneo_data["tipo_premio"]
        participantes = torneo_data["participantes"]
        
        async with lock_data:
            user_data = await load_data()
            for user_id, datos in participantes.items():
                monto = datos["pago"]
                
                if tipo_premio == "bono":
                    if user_id in user_data["Bono_apuesta"]:
                        user_data["Bono_apuesta"][user_id]["Bono"] += monto
                elif tipo_premio == "balance":
                    if user_id in user_data["usuarios"]:
                        user_data["usuarios"][user_id]["Balance"] += monto
                elif tipo_premio == "creditos":
                    fantasy_data = await load_fantasy_data()
                    if user_id in fantasy_data:
                        fantasy_data[user_id]["credits"] += monto
                    await save_fantasy_data(fantasy_data)
            
            await save_data(user_data)

        # 2. Notificar a los participantes
        for user_id in participantes.keys():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ <b>TORNEO CANCELADO</b>\n\n"
                         "El administrador ha cancelado el torneo.\n"
                         f"Se te ha devuelto el pago de {torneo_data['monto_entrada']} {tipo_premio}.",
                    parse_mode='HTML'
                )
            except Exception as e:
                logging.error(f"No se pudo notificar al usuario {user_id}: {str(e)}")

        # 3. Eliminar archivo de torneo
        os.remove(TORNEO_FILE)
        global TORNEO_CONFIG
        TORNEO_CONFIG = {
            "tipo_premio": None,
            "monto_entrada": 0,
            "admin_id": "7031172659",
            "participantes": {},
            "premios": {},
            "estado": "inactivo",
            "hora_inicio": None,
            "hora_fin_inscripciones": None
        }

        # 4. Confirmación al admin
        keyboard = [[InlineKeyboardButton("🏠 Menú Principal", callback_data='juego_fantasy')]]
        
        await query.edit_message_text(
            "✅ <b>TORNEO CANCELADO</b>\n\n"
            f"• Se devolvieron fondos a {len(participantes)} participantes\n"
            f"• Se eliminaron todos los datos del torneo",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        logging.error(f"Error en confirmar_cancelar_torneo: {str(e)}")
        await query.edit_message_text(
            "⚠️ Ocurrió un error al cancelar el torneo. Por favor verifica manualmente.",
            parse_mode='HTML'
        )
        





async def finalizar_torneo(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza el torneo, calcula clasificación y distribuye premios"""
    try:
        # Cargar datos del torneo
        with open(TORNEO_FILE, 'r') as f:
            torneo_data = json.load(f)
        
        participantes = torneo_data["participantes"]
        
        # Asegurar que todos tengan estadísticas
        for user_id in participantes:
            if "estadisticas" not in participantes[user_id]:
                participantes[user_id]["estadisticas"] = {
                    "puntos": 0,
                    "diferencia_goles": 0,
                    "goles_favor": 0
                }
        
        # Calcular clasificación final con manejo seguro
        clasificacion = sorted(
            participantes.items(),
            key=lambda x: (
                -x[1]["estadisticas"].get("puntos", 0),
                -x[1]["estadisticas"].get("diferencia_goles", 0),
                -x[1]["estadisticas"].get("goles_favor", 0)
            )
        )
        
     
        # 2. Determinar ganadores
        ganadores = {
            "primer_lugar": clasificacion[0][0] if len(clasificacion) >= 1 else None,
            "segundo_lugar": clasificacion[1][0] if len(clasificacion) >= 2 else None,
            "tercer_lugar": clasificacion[2][0] if len(clasificacion) >= 3 else None
        }
        
        # 3. Calcular premios
        total_recaudado = len(participantes) * torneo_data["monto_entrada"]
        premio_total = total_recaudado * 0.8  # 10% para la casa
        
        
        tipo_premio = torneo_data["tipo_premio"]
        aporte_bote = total_recaudado * 0.1  # 10% para el bote

        # Agregar al bote del archivo ranking.json
        if os.path.exists(RANKING_FILE):
            with open(RANKING_FILE, 'r') as f:
                ranking_data = json.load(f)
        else:
            ranking_data = {}

        # Asegurar que exista la estructura del bote
        if "bote" not in ranking_data:
            ranking_data["bote"] = {
                "balance": 0,
                "creditos": 0,
                "bono": 0,
                "barriles": 0
            }

        # Sumar el aporte al tipo de moneda usado en este torneo
        if tipo_premio in ranking_data["bote"]:
            ranking_data["bote"][tipo_premio] += aporte_bote
        else:
            # Si el tipo_premio no existe, lo crea para evitar errores
            ranking_data["bote"][tipo_premio] = aporte_bote

        # Guardar el ranking actualizado
        with open(RANKING_FILE, 'w') as f:
            json.dump(ranking_data, f, indent=2)
        
        
        
        
        premios = {
            "primer_lugar": premio_total * 0.4 if ganadores["primer_lugar"] else 0,
            "segundo_lugar": premio_total * 0.3 if ganadores["segundo_lugar"] else 0,
            "tercer_lugar": premio_total * 0.1 if ganadores["tercer_lugar"] else 0
        }
        
        # 4. Actualizar datos del torneo
        torneo_data.update({
            "estado": "finalizado",
            "premios": premios,
            "ganadores": ganadores,
            "clasificacion": {jugador_id: pos+1 for pos, (jugador_id, _) in enumerate(clasificacion)}  # Diccionario con {user_id: posición}
        })
        
        with open(TORNEO_FILE, 'w') as f:
            json.dump(torneo_data, f)
        
        # 5. Distribuir premios y notificar
        await distribuir_premios(context, torneo_data, ganadores, premios)
        await notificar_resultados_finales(context, torneo_data, clasificacion)
        
        # 6. Actualizar ranking con TODOS los participantes y sus posiciones
        await actualizar_ranking_torneo(torneo_data["clasificacion"])
        
    except Exception as e:
        logging.error(f"Error en finalizar_torneo: {str(e)}")
        traceback.print_exc()

async def distribuir_premios(context: ContextTypes.DEFAULT_TYPE, torneo_data, ganadores, premios):
    """Distribuye los premios a los ganadores"""
    try:
        tipo_premio = torneo_data["tipo_premio"]
        
        # Cargar datos de usuarios
        async with lock_data:
            user_data = await load_data()
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
        
        # Asignar premios según el tipo
        for posicion, jugador_id in ganadores.items():
            if not jugador_id or premios[posicion] <= 0:
                continue
                
            monto = int(premios[posicion])  # Usamos enteros para evitar decimales
            
            if tipo_premio == "bono":
                if jugador_id not in user_data["Bono_apuesta"]:
                    user_data["Bono_apuesta"][jugador_id] = {"Bono": 0}
                user_data["Bono_apuesta"][jugador_id]["Bono"] += monto
            elif tipo_premio == "balance":
                if jugador_id not in user_data["usuarios"]:
                    user_data["usuarios"][jugador_id] = {"Balance": 0}
                user_data["usuarios"][jugador_id]["Balance"] += monto
            elif tipo_premio == "creditos":
                if jugador_id not in fantasy_data:
                    fantasy_data[jugador_id] = {"credits": 0}
                fantasy_data[jugador_id]["credits"] += monto
        
        # Guardar cambios
        async with lock_data:
            await save_data(user_data)
        async with lock_fantasy:
            await save_fantasy_data(fantasy_data)
        
        # Actualizar estado en torneo_data
        torneo_data["premios_distribuidos"] = True
        with open(TORNEO_FILE, 'w') as f:
            json.dump(torneo_data, f)
            
    except Exception as e:
        logging.error(f"Error en distribuir_premios: {str(e)}")
        traceback.print_exc()

async def notificar_resultados_finales(context: ContextTypes.DEFAULT_TYPE, torneo_data, clasificacion):
    """Notifica los resultados finales a todos los participantes"""
    try:
        participantes = torneo_data["participantes"]
        tipo_premio = torneo_data["tipo_premio"]
        premios = torneo_data["premios"]
        ganadores = torneo_data.get("ganadores", {})
        
        # Construir mensaje de resultados
        mensaje = "🏁 <b>RESULTADOS FINALES DEL TORNEO</b> 🏁\n\n"
        mensaje += f"🔹 Tipo: {tipo_premio.upper()}\n"
        mensaje += f"🔹 Participantes: {len(participantes)}\n"
        mensaje += f"🔹 Partidos jugados: {len(torneo_data.get('partidos', []))}\n\n"
        
        mensaje += "🏆 <b>Ganadores:</b>\n"
        if ganadores.get("primer_lugar"):
            nombre = participantes[ganadores["primer_lugar"]].get("nombre", "Anónimo")
            mensaje += f"🥇 1er lugar: {nombre} - {int(premios['primer_lugar'])} {tipo_premio}\n"
        if ganadores.get("segundo_lugar"):
            nombre = participantes[ganadores["segundo_lugar"]].get("nombre", "Anónimo")
            mensaje += f"🥈 2do lugar: {nombre} - {int(premios['segundo_lugar'])} {tipo_premio}\n"
        if ganadores.get("tercer_lugar"):
            nombre = participantes[ganadores["tercer_lugar"]].get("nombre", "Anónimo")
            mensaje += f"🥉 3er lugar: {nombre} - {int(premios['tercer_lugar'])} {tipo_premio}\n"
        
        mensaje += "\n📊 <b>Top 5 de la clasificación:</b>\n"
        for i, (jugador_id, datos) in enumerate(clasificacion[:5], 1):
            nombre = datos.get("nombre", f"Jugador {i}")
            pts = datos["estadisticas"]["puntos"]
            mensaje += f"{i}. {nombre} - {pts} pts\n"
        
        # Notificar a todos los participantes
        for user_id in participantes.keys():
            try:
                # Mensaje personalizado para ganadores
                if user_id in ganadores.values():
                    posicion = list(ganadores.values()).index(user_id) + 1
                    emoji = ["🥇", "🥈", "🥉"][posicion-1]
                    premio = [premios["primer_lugar"], premios["segundo_lugar"], premios["tercer_lugar"]][posicion-1]
                    
                    mensaje_personal = (
                        f"{emoji} <b>¡FELICIDADES!</b> {emoji}\n\n"
                        f"Has quedado en {posicion}° lugar y ganaste {int(premio)} {tipo_premio}!\n\n"
                        f"{mensaje}"
                    )
                    await context.bot.send_message(user_id, mensaje_personal, parse_mode='HTML')
                else:
                    await context.bot.send_message(user_id, mensaje, parse_mode='HTML')
            except Exception as e:
                logging.error(f"No se pudo notificar a {user_id}: {str(e)}")
                
    except Exception as e:
        logging.error(f"Error en notificar_resultados_finales: {str(e)}")
        traceback.print_exc()         
        
          
# Añadir estas constantes al inicio del archivo
FORMATION_OPTIONS = {
    "4-4-2": [1, 4, 4, 2],
    "4-3-3": [1, 4, 3, 3],
    "3-5-2": [1, 3, 5, 2],
    "5-3-2": [1, 5, 3, 2],
    "4-5-1": [1, 4, 5, 1]
}
POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Attacker"]

async def cambiar_formacion_handler(update: Update, context: CallbackContext):
    """Muestra las opciones de formación disponibles"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Cargar datos del equipo
    fantasy_data = await load_fantasy_data()
    if user_id not in fantasy_data:
        await query.edit_message_text("❌ Primero necesitas crear un equipo.")
        return
    
    # Crear teclado con formaciones
    keyboard = []
    for formation in FORMATION_OPTIONS:
        # Resaltar la formación actual
        is_current = "(ACTUAL)" if formation == fantasy_data[user_id]["formation"] else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{formation} {is_current}", 
                callback_data=f'seleccionar_formacion_{formation}'
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='mi_equipo')])
    
    await query.edit_message_text(
        text="⚙️ <b>SELECCIONA UNA FORMACIÓN</b>\n\n"
             "Cada formación tiene diferente número de jugadores por posición:\n"
             "• 4-4-2: 1 Portero, 4 Defensas, 4 Mediocampistas, 2 Delanteros\n"
             "• 4-3-3: 1 Portero, 4 Defensas, 3 Mediocampistas, 3 Delanteros\n"
             "• 3-5-2: 1 Portero, 3 Defensas, 5 Mediocampistas, 2 Delanteros\n"
             "• 5-3-2: 1 Portero, 5 Defensas, 3 Mediocampistas, 2 Delanteros\n"
             "• 4-5-1: 1 Portero, 4 Defensas, 5 Mediocampistas, 1 Delantero",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def seleccionar_formacion_handler(update: Update, context: CallbackContext):
    """Maneja la selección de formación y muestra jugadores para alinear"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    formation = query.data.split('_')[-1]
    
    # Cargar datos del equipo
    fantasy_data = await load_fantasy_data()
    if user_id not in fantasy_data:
        await query.edit_message_text("❌ Primero necesitas crear un equipo.")
        return
    
    # Inicializar datos de alineación
    context.user_data['nueva_formacion'] = formation
    context.user_data['alineacion_temporal'] = {pos: [] for pos in POSITION_ORDER}
    context.user_data['titulares_seleccionados'] = set()
    
    # Preparar jugadores por posición, marcando los titulares actuales
    position_groups = defaultdict(list)
    current_titulares = set()
    
    for player in fantasy_data[user_id]["team"]:
        pos = player.get('normalized_position', 'Midfielder')
        position_groups[pos].append(player)
        
        # Si el jugador es titular actual, agregarlo a la selección temporal
        if player.get('is_titular', False):
            context.user_data['alineacion_temporal'][pos].append(player)
            context.user_data['titulares_seleccionados'].add(str(player['id']))
            current_titulares.add(str(player['id']))
    
    # Ordenar jugadores por posición y valor
    for pos in position_groups:
        position_groups[pos].sort(key=lambda x: x.get('value', 0), reverse=True)
    
    context.user_data['jugadores_por_posicion'] = position_groups
    context.user_data['current_titulares'] = current_titulares
    
    await mostrar_menu_alineacion(update, context, user_id, formation)

async def mostrar_menu_alineacion(update: Update, context: CallbackContext, user_id: str, formation: str):
    """Muestra la interfaz para seleccionar los jugadores titulares"""
    query = update.callback_query
    
    alineacion_temp = context.user_data['alineacion_temporal']
    titulares = context.user_data['titulares_seleccionados']
    formation_req = FORMATION_OPTIONS[formation]
    
    # Construir mensaje
    message_lines = [
        f"⚙️ <b>CONFIGURANDO ALINEACIÓN: {formation}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"🧤 Porteros: {len(alineacion_temp['Goalkeeper'])}/{formation_req[0]}",
        f"🛡️ Defensas: {len(alineacion_temp['Defender'])}/{formation_req[1]}",
        f"⚙️ Mediocampistas: {len(alineacion_temp['Midfielder'])}/{formation_req[2]}",
        f"⚽ Delanteros: {len(alineacion_temp['Attacker'])}/{formation_req[3]}",
        "",
        f"Titulares seleccionados: {len(titulares)}/11",
        "",
        "<b>Selecciona una posición para elegir titulares:</b>"
    ]
    
    # Crear teclado
    keyboard = []
    for position in POSITION_ORDER:
        icon = ""
        if position == "Goalkeeper":
            icon = "🧤"
        elif position == "Defender":
            icon = "🛡️"
        elif position == "Midfielder":
            icon = "⚙️"
        else:
            icon = "⚽"
            
        count = len(alineacion_temp[position])
        required = formation_req[POSITION_ORDER.index(position)]
        disabled = count >= required
        
        btn_text = f"{icon} {position} ({count}/{required})"
        if disabled:
            btn_text = f"✅ {btn_text}"
        
        keyboard.append([
            InlineKeyboardButton(
                btn_text,
                callback_data=f'seleccionar_posicion_{position}'
            )
        ])
    
    # Botones de acción
    action_row = []
    if len(titulares) == 11:
        action_row.append(InlineKeyboardButton(
            "✅ CONFIRMAR ALINEACIÓN", 
            callback_data='confirmar_alineacion'
        ))
    else:
        action_row.append(InlineKeyboardButton(
            "🔄 Reiniciar", 
            callback_data='reiniciar_alineacion'
        ))
    
    action_row.append(InlineKeyboardButton(
        "🔙 Volver", 
        callback_data='cambiar_formacion'
    ))
    keyboard.append(action_row)
    
    # Actualizar mensaje
    try:
        await query.edit_message_text(
            text="\n".join(message_lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="\n".join(message_lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
def validar_titulares(team_data):
    """Valida que el equipo tenga exactamente 11 titulares"""
    if 'team' not in team_data:
        return False
        
    titulares = sum(1 for p in team_data['team'] if p.get('is_titular', False))
    return titulares == 11        
        
async def seleccionar_posicion_handler(update: Update, context: CallbackContext):
    """Muestra jugadores disponibles para una posición específica"""
    query = update.callback_query
    await query.answer()
    
    position = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    formation = context.user_data.get('nueva_formacion', '4-4-2')

    # CORRECCIÓN: No reiniciar los datos existentes
    # Obtener jugadores para esta posición DESDE EL CONTEXTO EXISTENTE
    position_groups = context.user_data.get('jugadores_por_posicion', {})
    
    # Si no existen datos, cargarlos desde la base (no reiniciar a vacío)
    if not position_groups:
        # Cargar datos reales del usuario
        fantasy_data = await load_fantasy_data()
        user_team = fantasy_data.get(user_id, {}).get("team", [])
        
        # Agrupar jugadores por posición
        position_groups = {
            "Goalkeeper": [],
            "Defender": [],
            "Midfielder": [],
            "Attacker": []
        }
        for player in user_team:
            norm_pos = player.get('normalized_position', 'Midfielder')
            if norm_pos in position_groups:
                position_groups[norm_pos].append(player)
        
        # Guardar en contexto
        context.user_data['jugadores_por_posicion'] = position_groups
    
    jugadores_posicion = position_groups.get(position, [])
    alineacion_temp = context.user_data['alineacion_temporal']
    titulares = context.user_data['titulares_seleccionados']
    
    # Crear mensaje
    message_lines = [
        f"👥 <b>SELECCIONA JUGADORES: {position.upper()}</b>",
        f"Formación: {formation} | Disponibles: {len(jugadores_posicion)}",
        ""
    ]
    
    # Crear teclado con jugadores
    keyboard = []
    for player in jugadores_posicion:
        player_id = str(player['id'])
        player_name = player.get('name', 'Jugador')
        is_selected = player_id in titulares
        
        # Limitar longitud del nombre
        display_name = player_name if len(player_name) <= 15 else player_name[:12] + "..."
        btn_text = f"{'✅' if is_selected else '⬜'} {display_name}"
        
        keyboard.append([
            InlineKeyboardButton(
                btn_text,
                callback_data=f'toggle_jugador_{player_id}_{position}'
            )
        ])
    
    # Botones de navegación
    keyboard.append([
        InlineKeyboardButton("🔙 Volver", callback_data=f'volver_alineacion_{formation}'),
        InlineKeyboardButton("✅ He terminado", callback_data=f'volver_alineacion_{formation}')
    ])
    
    # Enviar mensaje
    try:
        await query.edit_message_text(
            text="\n".join(message_lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="\n".join(message_lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

async def toggle_jugador_handler(update: Update, context: CallbackContext):
    """Agrega o quita un jugador de la alineación temporal"""
    query = update.callback_query
    # Eliminado: await query.answer()
    
    data = query.data.split('_')
    player_id = data[2]
    position = data[3]
    
    alineacion_temp = context.user_data['alineacion_temporal']
    titulares = context.user_data['titulares_seleccionados']
    formation = context.user_data['nueva_formacion']
    formation_req = FORMATION_OPTIONS[formation]
    max_por_posicion = formation_req[POSITION_ORDER.index(position)]
    jugadores_posicion = context.user_data.get('jugadores_por_posicion', {}).get(position, [])
    
    # Buscar jugador en los disponibles
    player_info = next((p for p in jugadores_posicion if str(p['id']) == player_id), None)
    if not player_info:
        await query.message.reply_text("❌ Jugador no disponible")
        return
    
    # Si el jugador ya está seleccionado, quitarlo
    if player_id in titulares:
        titulares.remove(player_id)
        alineacion_temp[position] = [p for p in alineacion_temp[position] if str(p['id']) != player_id]
    else:
        # Verificar límites
        if len(alineacion_temp[position]) >= max_por_posicion:
            await query.message.reply_text(f"❌ Máximo {max_por_posicion} {position}(s) permitidos")
            return
        
        if len(titulares) >= 11:
            await query.message.reply_text("❌ Ya tienes 11 titulares seleccionados")
            return
        
        # Agregar jugador
        titulares.add(player_id)
        alineacion_temp[position].append(player_info)
    
    # Actualizar datos en contexto
    context.user_data['alineacion_temporal'] = alineacion_temp
    context.user_data['titulares_seleccionados'] = titulares
    
    # Actualizar la vista
    await seleccionar_posicion_handler(update, context)

async def confirmar_alineacion_handler(update: Update, context: CallbackContext):
    """Guarda la alineación seleccionada en la base de datos"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    formation = context.user_data.get('nueva_formacion', '4-4-2')
    alineacion_temp = context.user_data.get('alineacion_temporal', {})
    titulares = context.user_data.get('titulares_seleccionados', set())
    
    # Validar que se hayan seleccionado exactamente 11 titulares
    if len(titulares) != 11:
        await query.message.reply_text("❌ Debes seleccionar exactamente 11 jugadores titulares")
        return
    
    # Validar que la formación sea correcta
    formation_req = FORMATION_OPTIONS.get(formation, [1, 4, 4, 2])
    position_counts = {
        'Goalkeeper': len(alineacion_temp.get('Goalkeeper', [])),
        'Defender': len(alineacion_temp.get('Defender', [])),
        'Midfielder': len(alineacion_temp.get('Midfielder', [])),
        'Attacker': len(alineacion_temp.get('Attacker', []))
    }
    
    if (position_counts['Goalkeeper'] != formation_req[0] or
        position_counts['Defender'] != formation_req[1] or
        position_counts['Midfielder'] != formation_req[2] or
        position_counts['Attacker'] != formation_req[3]):
        await query.message.reply_text("❌ La cantidad de jugadores por posición no coincide con la formación")
        return
    
    # Cargar y actualizar datos del equipo
    fantasy_data = await load_fantasy_data()
    if user_id not in fantasy_data:
        await query.edit_message_text("❌ Error: No se encontró tu equipo")
        return
    
    # Actualizar todos los jugadores
    for player in fantasy_data[user_id]["team"]:
        player_id = str(player['id'])
        # Asegurarse de que todos los jugadores tengan el campo is_titular
        if 'is_titular' not in player:
            player['is_titular'] = False
        # Actualizar estado según selección
        player['is_titular'] = player_id in titulares
    
    # Actualizar formación
    fantasy_data[user_id]["formation"] = formation
    
    # Guardar cambios
    await save_fantasy_data(fantasy_data)
    
    # Limpiar contexto
    for key in ['nueva_formacion', 'alineacion_temporal', 'titulares_seleccionados', 
               'jugadores_por_posicion', 'current_titulares']:
        context.user_data.pop(key, None)
    
    # Mostrar confirmación
    await query.edit_message_text(
        "✅ <b>ALINEACIÓN ACTUALIZADA</b>\n\n"
        f"Formación: {formation}\n"
        f"Titulares: 11/11\n\n"
        "Los cambios se han guardado correctamente.",
        parse_mode='HTML'
    )
    
    # Mostrar el equipo actualizado después de un breve retraso
    await asyncio.sleep(1)
    await mi_equipo_handler(update, context)

async def reiniciar_alineacion_handler(update: Update, context: CallbackContext):
    """Reinicia la selección de alineación actual"""
    query = update.callback_query
    await query.answer()
    
    formation = context.user_data.get('nueva_formacion', '4-4-2')
    
    # Resetear selección
    context.user_data['alineacion_temporal'] = {pos: [] for pos in POSITION_ORDER}
    context.user_data['titulares_seleccionados'] = set()
    
    await mostrar_menu_alineacion(update, context, str(query.from_user.id), formation)

async def volver_alineacion_handler(update: Update, context: CallbackContext):
    """Vuelve al menú principal de alineación"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    formation = data[2] if len(data) > 2 else '4-4-2'
    
    await mostrar_menu_alineacion(update, context, str(query.from_user.id), formation)        
    
async def estadisticas_equipo(update: Update, context: CallbackContext):
    """Muestra estadísticas detalladas de cada jugador del equipo con paginación"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
        
        # Cargar datos del equipo del usuario
        fantasy_data = await load_fantasy_data()
        if user_id not in fantasy_data or not fantasy_data[user_id].get('team'):
            await safe_edit_message(query, "❌ No tienes un equipo asignado.")
            return
            
        team = fantasy_data[user_id]['team']
        
        # Cargar todos los jugadores para obtener estadísticas completas
        try:
            with open(PLAYERS_FILE, 'r') as f:
                all_players = json.load(f)
        except Exception as e:
            logging.error(f"Error al cargar jugadores: {str(e)}")
            await safe_edit_message(query, "❌ Error al cargar datos de jugadores.")
            return
        
        # Crear lista de jugadores con sus estadísticas completas
        detailed_players = []
        for player in team:
            # Buscar jugador en el archivo completo
            for p in all_players:
                if str(p['player']['id']) == str(player['id']) and p.get('statistics'):
                    detailed_player = {
                        'id': player['id'],
                        'name': player['name'],
                        'photo': player.get('photo', ''),
                        'position': player['position'],
                        'team': player['team'],
                        'stats': p['statistics'][0] if p['statistics'] else {},
                        'player_info': p['player']
                    }
                    detailed_players.append(detailed_player)
                    break
        
        if not detailed_players:
            await safe_edit_message(query, "❌ No se encontraron estadísticas para tu equipo.")
            return
        
        # Paginación
        players_per_page = 1  # Mostrar un jugador por página
        total_pages = len(detailed_players)
        page = max(1, min(page, total_pages))
        current_player = detailed_players[page-1]
        
        # Construir mensaje con estadísticas detalladas
        stats = current_player['stats']
        player_info = current_player['player_info']
        
        message = [
            f"📊 <b>ESTADÍSTICAS DETALLADAS</b>",
            f"━━━━━━━━━━━━━━━━━━",
            f"👤 <b>{current_player['name']}</b> ({current_player['position']})",
            f"🏟 <b>Equipo:</b> {current_player['team']}",
            f"🎂 <b>Edad:</b> {player_info.get('age', 'N/A')}",
            f"🌍 <b>Nacionalidad:</b> {player_info.get('nationality', 'N/A')}",
            f"📏 <b>Altura:</b> {player_info.get('height', 'N/A')}",
            f"⚖️ <b>Peso:</b> {player_info.get('weight', 'N/A')}",
            f"",
            f"⭐ <b>Rendimiento General</b>",
            f"├ Partidos jugados: {stats.get('games', {}).get('appearences', 0)}",
            f"├ Minutos: {stats.get('games', {}).get('minutes', 0)}",
            f"└ Rating: {stats.get('games', {}).get('rating', 'N/A')}",
            f"",
            f"⚽ <b>Ataque</b>",
            f"├ Goles: {stats.get('goals', {}).get('total', 0)}",
            f"├ Asistencias: {stats.get('goals', {}).get('assists', 0)}",
            f"├ Tiros totales: {stats.get('shots', {}).get('total', 0)}",
            f"└ Tiros al arco: {stats.get('shots', {}).get('on', 0)}",
            f"",
            f"🎯 <b>Pases</b>",
            f"├ Pases totales: {stats.get('passes', {}).get('total', 0)}",
            f"├ Pases clave: {stats.get('passes', {}).get('key', 0)}",
            f"└ Precisión: {stats.get('passes', {}).get('accuracy', 0)}%",
            f"",
            f"🛡️ <b>Defensa</b>",
            f"├ Tackles: {stats.get('tackles', {}).get('total', 0)}",
            f"├ Intercepciones: {stats.get('tackles', {}).get('interceptions', 0)}",
            f"└ Bloqueos: {stats.get('tackles', {}).get('blocks', 0)}",
            f"",
            f"🤺 <b>Duelos</b>",
            f"├ Duelos totales: {stats.get('duels', {}).get('total', 0)}",
            f"├ Duelos ganados: {stats.get('duels', {}).get('won', 0)}",
            f"├ Faltas cometidas: {stats.get('fouls', {}).get('committed', 0)}",
            f"└ Faltas recibidas: {stats.get('fouls', {}).get('drawn', 0)}",
            f"",
            f"🟨 <b>Tarjetas</b>",
            f"├ Amarillas: {stats.get('cards', {}).get('yellow', 0)}",
            f"└ Rojas: {stats.get('cards', {}).get('red', 0) + stats.get('cards', {}).get('yellowred', 0)}",
            f"",
            f"📅 <b>Página {page}/{total_pages}</b>"
        ]
        
        # Crear teclado de navegación
        keyboard = []
        
        # Botones de jugadores (máximo 4 por fila)
        player_buttons = []
        for i, player in enumerate(detailed_players, 1):
            player_buttons.append(InlineKeyboardButton(
                f"{i} {player['name'][:10]}",
                callback_data=f'ver2_jugador_stats_{player["id"]}_{i}'
            ))
            
            if len(player_buttons) == 4:
                keyboard.append(player_buttons)
                player_buttons = []
        
        if player_buttons:
            keyboard.append(player_buttons)
        
        # Botones de navegación
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f'estats_page_{page-1}'))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f'estats_page_{page+1}'))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Volver al equipo", callback_data='mi_equipo')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Manejo seguro del mensaje con foto
        if current_player.get('photo'):
            try:
                # Primero intentamos editar el mensaje existente con la foto
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=current_player['photo'],
                        caption="\n".join(message),
                        parse_mode='HTML'
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.warning(f"No se pudo editar mensaje con foto: {str(e)}")
                try:
                    # Si falla, enviamos nuevo mensaje con foto
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=current_player['photo'],
                        caption="\n".join(message),
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                    await query.delete_message()
                except Exception as e:
                    logging.error(f"Error al enviar foto: {str(e)}")
                    # Fallback a solo texto
                    await safe_edit_message(query, "\n".join(message), reply_markup)
        else:
            # Si no hay foto, solo editamos el texto
            await safe_edit_message(query, "\n".join(message), reply_markup)
            
    except Exception as e:
        logging.error(f"Error en estadisticas_equipo: {str(e)}")
        traceback.print_exc()
        await safe_edit_message(query, "⚠️ Error al mostrar estadísticas del equipo")

async def safe_edit_message(query, text, reply_markup=None):
    """Función segura para editar mensajes que maneja diferentes casos de error"""
    try:
        if query.message.text:  # Si el mensaje tiene texto
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            # Si no tiene texto (solo foto u otro media), enviamos nuevo mensaje
            await query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            await query.delete_message()
    except Exception as e:
        logging.error(f"Error en safe_edit_message: {str(e)}")
        try:
            # Último intento de enviar mensaje nuevo
            await query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error crítico al enviar mensaje: {str(e)}")


        
async def ver_jugador_stats(update: Update, context: CallbackContext):
    """Muestra estadísticas detalladas de un jugador con mejor formato y organización"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extraer datos del callback
        data = query.data.split('_')
        player_id = int(data[3])
        page = int(data[4]) if len(data) > 4 else 1
        
        # Cargar datos necesarios
        async with lock_data:
            user_data = await load_data()
            fantasy_data = await load_fantasy_data()
        
        with open(PLAYERS_FILE, 'r') as f:
            players_data = json.load(f)
        
        # Buscar jugador en datos base
        player_info = None
        stats_data = None
        for player in players_data:
            if str(player["player"]["id"]) == str(player_id) and player.get('statistics'):
                stats = player['statistics'][0]
                rating = float(stats["games"]["rating"]) if stats["games"]["rating"] else MIN_RATING
                if rating >= MIN_RATING:
                    player_info = {
                        "id": player["player"]["id"],
                        "name": player["player"]["name"],
                        "firstname": player["player"].get("firstname", ""),
                        "lastname": player["player"].get("lastname", ""),
                        "position": stats["games"]["position"],
                        "rating": rating,
                        "value": calculate_player_value(player, stats),
                        "team": stats["team"]["name"],
                        "team_logo": stats["team"]["logo"],
                        "photo": player["player"].get("photo", ""),
                        "age": player["player"].get("age", "N/A"),
                        "nationality": player["player"].get("nationality", "N/A"),
                        "height": player["player"].get("height", "N/A"),
                        "weight": player["player"].get("weight", "N/A"),
                        "birth_date": player["player"].get("birth", {}).get("date", "N/A"),
                        "birth_place": player["player"].get("birth", {}).get("place", "N/A")
                    }
                    stats_data = stats
                    break
        
        if not player_info or not stats_data:
            await safe_edit_message(query, "❌ Jugador no disponible.")
            return
        
        # Preparar datos seguros
        penales_marcados = stats_data['penalty'].get('scored') or 0
        penales_fallados = stats_data['penalty'].get('missed') or 0
        penales_totales = penales_marcados + penales_fallados

        # Construir mensaje
        message = [
            f"📊 <b>ESTADÍSTICAS COMPLETAS - {player_info['name'].upper()}</b>",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"👤 <b>INFORMACIÓN PERSONAL</b>",
            f"├ Nombre completo: {player_info['firstname']} {player_info['lastname']}",
            f"├ Posición: {player_info['position']}",
            f"├ Edad: {player_info['age']} años",
            f"├ Nacionalidad: {player_info['nationality']}",
            f"├ Altura: {player_info['height']}",
            f"├ Peso: {player_info['weight']}",
            f"├ Fecha nacimiento: {player_info['birth_date']}",
            f"└ Lugar nacimiento: {player_info['birth_place']}",
            f"",
            f"🏟 <b>INFORMACIÓN DE EQUIPO</b>",
            f"├ Equipo actual: {player_info['team']}",
            f"├ Valor de mercado: {player_info['value']}",
            f"└ Rating actual: {player_info['rating']:.1f}/10",
            f"",
            f"⚽ <b>RENDIMIENTO OFENSIVO</b>",
            f"├ Partidos jugados: {stats_data['games']['appearences'] or 0}",
            f"├ Partidos como titular: {stats_data['games']['lineups'] or 0}",
            f"├ Minutos jugados: {stats_data['games']['minutes'] or 0}",
            f"├ Goles: {stats_data['goals']['total'] or 0}",
            f"├ Asistencias: {stats_data['goals']['assists'] or 0}",
            f"├ Pases clave: {stats_data['passes']['key'] or 0}",
            f"├ Precisión de pases: {stats_data['passes']['accuracy'] or 0}%",
            f"└ Tiros al arco: {stats_data['shots']['on'] or 0}/{stats_data['shots']['total'] or 0}",
            f"",
            f"🛡️ <b>RENDIMIENTO DEFENSIVO</b>",
            f"├ Tackles completados: {stats_data['tackles']['total'] or 0}",
            f"├ Bloqueos: {stats_data['tackles']['blocks'] or 0}",
            f"├ Intercepciones: {stats_data['tackles']['interceptions'] or 0}",
            f"├ Duelos ganados: {stats_data['duels']['won'] or 0}/{stats_data['duels']['total'] or 0}",
            f"├ Faltas cometidas: {stats_data['fouls']['committed'] or 0}",
            f"└ Faltas recibidas: {stats_data['fouls']['drawn'] or 0}",
            f"",
            f"📋 <b>ESTADÍSTICAS ADICIONALES</b>",
            f"├ Regates intentados: {stats_data['dribbles']['attempts'] or 0}",
            f"├ Regates exitosos: {stats_data['dribbles']['success'] or 0}",
            f"├ Tarjetas amarillas: {stats_data['cards']['yellow'] or 0}",
            f"├ Tarjetas rojas: {stats_data['cards']['red'] or 0}",
            f"└ Penales marcados: {penales_marcados}/{penales_totales}",
            f"",
            f"📅 <b>Página {page}</b>"
        ]
        
        # Crear teclado de navegación
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Volver", callback_data=f'estats_page_{page}')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mostrar con imagen si hay
        if player_info.get('photo'):
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=player_info['photo'],
                        caption="\n".join(message),
                        parse_mode='HTML'
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.warning(f"No se pudo editar mensaje con foto: {str(e)}")
                try:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=player_info['photo'],
                        caption="\n".join(message),
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                    await query.delete_message()
                except Exception as e:
                    logging.error(f"Error al enviar foto: {str(e)}")
                    await safe_edit_message(query, "\n".join(message), reply_markup)
        else:
            await safe_edit_message(query, "\n".join(message), reply_markup)
            
    except Exception as e:
        logging.error(f"Error en ver_jugador_stats: {str(e)}")
        await safe_edit_message(query, "⚠️ Error al mostrar estadísticas del jugador")      
        
        
        
# Agregar al inicio del archivo
RETOS_FILE = "retos_pendientes.json"
RETO_TIMEOUT = 300  # 5 minutos en segundos

# Inicializar archivo de retos
def initialize_retos_file():
    if not os.path.exists(RETOS_FILE):
        with open(RETOS_FILE, 'w') as f:
            json.dump({}, f)

# Lock para retos
lock_retos = asyncio.Lock()

async def load_retos_data():
    """Carga datos de retos pendientes"""
    try:
        if not os.path.exists(RETOS_FILE):
            return {}
        
        with open(RETOS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

async def save_retos_data(data):
    """Guarda datos de retos"""
    try:
        with open(RETOS_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except:
        return False

async def mostrar_rivales_retar(update: Update, context: CallbackContext):
    """Muestra lista de rivales disponibles para retar con botones"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Cargar datos de usuarios y fantasy
    async with lock_data, lock_fantasy:
        user_data = await load_data()
        fantasy_data = await load_fantasy_data()
        
        if user_id not in fantasy_data or not fantasy_data[user_id].get("team"):
            await query.message.reply_text(
    "❌ Primero debes crear tu equipo y configurar 11 titulares",
                parse_mode='HTML'
)
            return
    
    # Filtrar usuarios válidos con equipos fantasy
    rivales = []
    for uid, data in user_data["usuarios"].items():
        if (uid != user_id and 
            uid in fantasy_data and 
            fantasy_data[uid].get("team") and 
            data.get("Nombre")):  # Ahora verificamos que tenga Nombre
            
            # Verificar que tenga 11 titulares configurados
            if validar_titulares(fantasy_data[uid]):
                nombre = data["Nombre"]
                # Recortar nombre si es muy largo (max 15 caracteres)
                nombre_display = nombre[:15] + "..." if len(nombre) > 15 else nombre
                rivales.append({
                    "id": uid,
                    "nombre": nombre,
                    "nombre_display": nombre_display,
                    "username": data.get("username", "")  # Lo guardamos por si acaso
                })
                
                
            
    
    if not rivales:
        await query.edit_message_text(
            "ℹ️ No hay rivales disponibles en este momento",
            parse_mode='HTML'
        )
        return
    
    # Crear teclado con botones de rivales mostrando el nombre recortado
    keyboard = []
    for rival in rivales:
        keyboard.append([
            InlineKeyboardButton(
                f"⚔️ Retar a {rival['nombre_display']}",
                callback_data=f'seleccionar_rival_{rival["id"]}'
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Actualizar lista", callback_data='mostrar_rivales'),
        InlineKeyboardButton("🔙 Volver", callback_data='juego_fantasy')
    ])
    
    await query.edit_message_text(
        "👥 <b>SELECCIONA UN RIVAL PARA RETAR</b>\n\n"
        "Estos son los managers disponibles:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
@verificar_bloqueo    
async def seleccionar_rival(update: Update, context: CallbackContext):
    """Guarda el rival seleccionado y pide el monto de la apuesta"""
    query = update.callback_query
    await query.answer()
    
    rival_id = query.data.split('_')[-1]
    context.user_data['rival_id'] = rival_id
    
    # Guardar nombre del rival para mostrar
    async with lock_data:
        user_data = await load_data()
        rival_nombre = user_data["usuarios"].get(rival_id, {}).get("Nombre", "Rival")
    
    context.user_data['rival_nombre'] = rival_nombre
    
    await query.edit_message_text(
        f"⚔️ <b>RETANDO A {rival_nombre.upper()}</b>\n\n"
        "💰 <b>Ingresa el monto de la apuesta:</b>\n"
        "(Ejemplo: <code>50.00</code>)",
        parse_mode='HTML'
    )
    
    # Establecer estado para capturar el monto
    context.user_data['estado'] = 'ESPERANDO_MONTO_RETO'

async def procesar_monto_reto(update: Update, context: CallbackContext):
    """Procesa el monto ingresado y crea el reto"""
    user_id = str(update.message.from_user.id)
    monto_texto = update.message.text
    
    try:
        # Validar formato del monto
        monto = float(monto_texto)
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un número válido y positivo\n"
            "(Ejemplo: <code>50.00</code>)",
            parse_mode='HTML'
        )
        return

    # ✅ Esta validación debe estar FUERA del try
    if monto < 5:
        await update.message.reply_text(
            "⚠️ El monto mínimo para crear un reto es <b>5 CUP</b>.",
            parse_mode='HTML'
        )
        return
    
    # Obtener datos del contexto
    rival_id = context.user_data.get('rival_id')
    rival_nombre = context.user_data.get('rival_nombre', 'Rival')
    
    if not rival_id:
        await update.message.reply_text("❌ Error: No se seleccionó rival")
        return
    
    # Verificar fondos del retador
    async with lock_data:
        user_data = await load_data()
        balance_retador = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
        
        if balance_retador < monto:
            await update.message.reply_text(
                f"❌ Fondos insuficientes. Dispones de ${balance_retador:.2f}",
                parse_mode='HTML'
            )
            return
        
        # Bloquear fondos del retador
        user_data["usuarios"][user_id]["Balance"] -= monto
        await save_data(user_data)
    
    # Crear reto
    reto_id = str(uuid.uuid4())
    expiration_time = datetime.now().timestamp() + 300  # 5 minutos
    
    reto_data = {
        "desafiante_id": user_id,
        "desafiante_name": user_data["usuarios"][user_id].get("Nombre", "Tú"),
        "desafiado_id": rival_id,
        "desafiado_name": rival_nombre,
        "monto": monto,
        "estado": "pendiente",
        "hora_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hora_expiracion": expiration_time
    }
    
    # Guardar reto
    async with lock_retos:
        retos_data = await load_retos_data()
        retos_data[reto_id] = reto_data
        await save_retos_data(retos_data)
    
    # Notificar al rival
    try:
        keyboard = [
            [
                InlineKeyboardButton("✅ Aceptar Reto", callback_data=f'aceptar_reto_{reto_id}'),
                InlineKeyboardButton("❌ Rechazar", callback_data=f'rechazar_reto_{reto_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        expiracion_str = datetime.fromtimestamp(expiration_time).strftime("%H:%M:%S")
        
        await context.bot.send_message(
            chat_id=rival_id,
            text=f"⚔️ <b>¡NUEVO RETO DE FANTASY!</b> ⚔️\n\n"
                 f"👤 <b>Retador:</b> {update.message.from_user.full_name}\n"
                 f"💰 <b>Apuesta:</b> ${monto:.2f}\n"
                 f"⏳ <b>Válido hasta:</b> {expiracion_str}\n\n"
                 f"¿Aceptas el desafío?",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error notificando al rival: {str(e)}")
        # Devolver fondos si falla la notificación
        async with lock_data:
            user_data = await load_data()
            user_data["usuarios"][user_id]["Balance"] += monto
            await save_data(user_data)
        
        await update.message.reply_text("❌ No se pudo enviar el reto. Intenta nuevamente.")
        return
    
    # Confirmación al retador
    await update.message.reply_text(
        f"🎯 <b>¡Reto enviado a {rival_nombre}!</b>\n\n"
        f"💰 <b>Apuesta:</b> ${monto:.2f}\n"
        f"⏳ <b>Tiempo para respuesta:</b> 5 minutos\n\n"
        f"Esperando confirmación...",
        parse_mode='HTML'
    )
    
    # Programar expiración
    context.job_queue.run_once(
        callback=cancelar_reto_por_tiempo, 
        when=300,
        data=reto_id,
        name=f"reto_timeout_{reto_id}"
    )
    
    # Limpiar estado
    context.user_data.pop('estado', None)
    context.user_data.pop('rival_id', None)
    context.user_data.pop('rival_nombre', None)




async def cancelar_reto_por_tiempo(context: ContextTypes.DEFAULT_TYPE):
    """Cancela un reto por tiempo agotado"""
    reto_id = context.job.data  # ✅ CORREGIDO

    async with lock_retos:
        retos_data = await load_retos_data()
        if reto_id not in retos_data:
            return

        reto = retos_data[reto_id]
        if reto["estado"] != "pendiente":
            return

        # Actualizar estado
        reto["estado"] = "expirado"
        retos_data[reto_id] = reto
        await save_retos_data(retos_data)

    # Devolver fondos al retador
    async with lock_data:
        user_data = await load_data()
        user_id = reto["desafiante_id"]
        user_data["usuarios"][user_id]["Balance"] += reto["monto"]
        await save_data(user_data)

    # Notificar a ambos
    try:
        await context.bot.send_message(
            chat_id=reto["desafiante_id"],
            text=f"⌛ Reto a {reto['desafiado_name']} ha expirado\n"
                 f"💰 Se te ha devuelto ${reto['monto']:.2f}"
        )

        await context.bot.send_message(
            chat_id=reto["desafiado_id"],
            text=f"⌛ Reto de {reto['desafiante_name']} ha expirado"
        )
    except Exception as e:
        logging.error(f"Error notificando expiración de reto: {str(e)}")
async def procesar_respuesta_reto(update: Update, context: CallbackContext, accion: str):
    """Procesa aceptación o rechazo de un reto"""
    query = update.callback_query
    await query.answer()
    
    reto_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    async with lock_retos:
        retos_data = await load_retos_data()
        if reto_id not in retos_data:
            await query.edit_message_text("❌ Este reto ya no existe")
            return
        
        reto = retos_data[reto_id]
        
        # Validar que el usuario es el retado
        if user_id != reto["desafiado_id"]:
            await query.edit_message_text("❌ No eres el usuario retado")
            return
        
        if reto["estado"] != "pendiente":
            await query.edit_message_text("❌ Este reto ya fue procesado")
            return
        
        # Cancelar job de expiración
        for job in context.job_queue.jobs():
            if job.name == f"reto_timeout_{reto_id}":
                job.schedule_removal()
                break
    
    if accion == "rechazar":
        # Devolver fondos al retador
        async with lock_data:
            user_data = await load_data()
            user_data["usuarios"][reto["desafiante_id"]]["Balance"] += reto["monto"]
            await save_data(user_data)
        
        # Actualizar estado
        async with lock_retos:
            reto["estado"] = "rechazado"
            retos_data[reto_id] = reto
            await save_retos_data(retos_data)
        
        # Notificar
        await query.edit_message_text("❌ Has rechazado el reto")
        try:
            await context.bot.send_message(
                chat_id=reto["desafiante_id"],
                text=f"❌ {reto['desafiado_name']} ha rechazado tu reto\n"
                     f"💰 Se te ha devuelto ${reto['monto']:.2f}"
            )
        except:
            pass
        
        return
    
    # Aceptación del reto
    async with lock_data:
        user_data = await load_data()
        balance_retado = user_data["usuarios"].get(user_id, {}).get("Balance", 0)
        
        if balance_retado < reto["monto"]:
            await query.edit_message_text("❌ Fondos insuficientes para aceptar el reto")
            
            # Devolver fondos al retador
            user_data["usuarios"][reto["desafiante_id"]]["Balance"] += reto["monto"]
            await save_data(user_data)
            return
        
        # Bloquear fondos del retado
        user_data["usuarios"][user_id]["Balance"] -= reto["monto"]
        await save_data(user_data)
    
    # Actualizar estado del reto
    async with lock_retos:
        reto["estado"] = "aceptado"
        retos_data[reto_id] = reto
        await save_retos_data(retos_data)
    
    await query.edit_message_text("✅ ¡Reto aceptado! Preparando partido...")
    
    # Iniciar partido
    await iniciar_partido(update, context, reto_id)

async def iniciar_partido(update: Update, context: CallbackContext, reto_id: str):
    """Inicia la simulación del partido con mensaje profesional"""
    async with lock_retos:
        retos_data = await load_retos_data()
        reto = retos_data[reto_id]
    
    # Obtener equipos
    async with lock_fantasy:
        fantasy_data = await load_fantasy_data()
        equipo1 = [p for p in fantasy_data[reto["desafiante_id"]]["team"] if p.get("is_titular", False)]
        equipo2 = [p for p in fantasy_data[reto["desafiado_id"]]["team"] if p.get("is_titular", False)]
    
    # Calcular valor promedio de los equipos
    valor1 = sum(p["value"] for p in equipo1) / len(equipo1) if equipo1 else 0
    valor2 = sum(p["value"] for p in equipo2) / len(equipo2) if equipo2 else 0
    
    # Determinar probabilidades
    total_valor = valor1 + valor2
    prob1 = valor1 / total_valor * 100 if total_valor > 0 else 50
    prob2 = valor2 / total_valor * 100 if total_valor > 0 else 50
    
    # Seleccionar alineaciones destacadas (3 jugadores por equipo)
    destacados1 = sorted(equipo1, key=lambda x: x["value"], reverse=True)[:3]
    destacados2 = sorted(equipo2, key=lambda x: x["value"], reverse=True)[:3]
    
    # Construir mensaje inicial profesional
    msg_inicial = (
        f"⚽ <b>PARTIDO DE FANTASY - ALINEACIONES OFICIALES</b> ⚽\n\n"
        f"🏟 <b>{reto['desafiante_name']}</b> vs <b>{reto['desafiado_name']}</b>\n"
        f"💰 <b>Apuesta:</b> ${reto['monto']:.2f} CUP\n\n"
        f"📊 <b>Probabilidades:</b>\n"
        f"• {reto['desafiante_name']}: {prob1:.1f}%\n"
        f"• {reto['desafiado_name']}: {prob2:.1f}%\n\n"
        f"🌟 <b>Jugadores destacados:</b>\n"
        f"<b>{reto['desafiante_name']}:</b> {', '.join(p['name'] for p in destacados1)}\n"
        f"<b>{reto['desafiado_name']}:</b> {', '.join(p['name'] for p in destacados2)}\n\n"
        f"⏳ <b>El partido comenzará en breve...</b>"
    )
    
    try:
        # Enviar mensaje con formato profesional
        await context.bot.send_message(
            chat_id=reto["desafiante_id"],
            text=msg_inicial,
            parse_mode='HTML'
        )
        await context.bot.send_message(
            chat_id=reto["desafiado_id"],
            text=msg_inicial,
            parse_mode='HTML'
        )
        
        # Pequeña pausa antes de comenzar
        await asyncio.sleep(2)
        
        # Mensaje de inicio
        inicio_msg = "🔄 <b>El árbitro hace sonar su silbato! Comienza el partido!</b> ⚽"
        await context.bot.send_message(
            chat_id=reto["desafiante_id"],
            text=inicio_msg,
            parse_mode='HTML'
        )
        await context.bot.send_message(
            chat_id=reto["desafiado_id"],
            text=inicio_msg,
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error iniciando partido: {str(e)}")
    
    # Iniciar simulación (cada 30 segundos)
    context.job_queue.run_once(
        callback=simular_eventos_partido, 
        when=30,  # Primer evento a los 30 segundos
        data={
            "reto_id": reto_id,
            "minuto_partido": 0,
            "minuto_real": 0,
            "goles1": 0,
            "goles2": 0,
            "eventos": []
        },
        name=f"partido_{reto_id}"
    )

async def simular_eventos_partido(context: ContextTypes.DEFAULT_TYPE):
    """Simula eventos del partido cada 10 segundos reales (3 minutos de partido)"""
    job_data = context.job.data
    reto_id = job_data["reto_id"]
    minuto_partido = job_data["minuto_partido"]  # Minutos de juego (0-90)
    minuto_real = job_data["minuto_real"]        # Minutos reales transcurridos (0-5)
    goles1 = job_data["goles1"]
    goles2 = job_data["goles2"]
    eventos = job_data["eventos"]

    async with lock_retos:
        retos_data = await load_retos_data()
        if reto_id not in retos_data or retos_data[reto_id]["estado"] != "aceptado":
            return
        reto = retos_data[reto_id]

    # Obtener equipos
    async with lock_fantasy:
        fantasy_data = await load_fantasy_data()
        equipo1 = [p for p in fantasy_data[reto["desafiante_id"]]["team"] if p.get("is_titular", False)]
        equipo2 = [p for p in fantasy_data[reto["desafiado_id"]]["team"] if p.get("is_titular", False)]

    # Calcular valor promedio de los equipos
    valor1 = sum(p["value"] for p in equipo1) / len(equipo1) if equipo1 else 0
    valor2 = sum(p["value"] for p in equipo2) / len(equipo2) if equipo2 else 0

    # Avanzar el tiempo (10 segundos reales = 3 minutos de partido)
    minuto_real += 0.1667
    minuto_partido += 3

    # Simular evento (60% de probabilidad cada 10 segundos reales)
    if random.random() < 0.7:
        tipo_evento = random.choices(
            ["gol", "falta", "tarjeta_amarilla", "tarjeta_roja", "ocasion", "esquina", "cambio", "lesion"],
            weights=[30, 15, 10, 3, 15, 12, 7, 5],
            k=1
        )[0]

        equipo_evento = "1" if random.random() < valor1 / (valor1 + valor2) else "2"
        nombre_equipo = reto["desafiante_name"] if equipo_evento == "1" else reto["desafiado_name"]
        equipo = equipo1 if equipo_evento == "1" else equipo2
        jugador = random.choice(equipo)
        nombre_jugador = jugador["name"]

        if tipo_evento == "gol":
            equipo_atacante = equipo1 if equipo_evento == "1" else equipo2
            posibles_atacantes = [p for p in equipo_atacante if p["normalized_position"] in ["Attacker", "Midfielder"]]
            if not posibles_atacantes:
                posibles_atacantes = equipo_atacante
            atacante = random.choice(posibles_atacantes)

            equipo_defensor = equipo2 if equipo_evento == "1" else equipo1
            posibles_defensores = [p for p in equipo_defensor if p["normalized_position"] in ["Goalkeeper", "Defender"]]
            if not posibles_defensores:
                posibles_defensores = equipo_defensor
            defensor = random.choice(posibles_defensores)

            prob_gol = await calcular_probabilidad_gol(atacante, defensor)
            rating_atacante = atacante.get('rating') or 0.0
            rating_defensor = defensor.get('rating') or 0.0

            if random.random() < prob_gol:
                if equipo_evento == "1":
                    goles1 += 1
                else:
                    goles2 += 1

                evento = (
                    f"<pre>⚽GOOOOOOL DE {atacante['name']}!⚽</pre>\n"
                    f"⏱️ Minuto {int(minuto_partido)}'\n\n"
                    f"👤 <b>Atacante:</b> {atacante['name']} ({rating_atacante}⭐) \n🆚\n"
                    f"<b>Defensor:</b> {defensor['name']} ({rating_defensor}⭐)\n\n"
                    f"┏━━━━━━━━━━━━━━━━┓\n"
                    f"  {reto['desafiante_name'][:5].upper()}  <b>{goles1}-{goles2}</b> {reto['desafiado_name'][:5].upper()}  \n"
                    f"┗━━━━━━━━━━━━━━━━┛"
                )
            else:
                evento = (
                    f"<pre>🧤¡PARADA DE {defensor['name']}!🧤</pre> \n"
                    f"⏱️ Minuto {int(minuto_partido)}'\n"
                    f"👤 Atacante: {atacante['name']} ({rating_atacante}⭐) 🆚 "
                    f"Defensor: {defensor['name']} ({rating_defensor}⭐)\n\n"
                    f"┏━━━━━━━━━━━━━━━━┓\n"
                    f"  {reto['desafiante_name'][:5].upper()} <b>{goles1}-{goles2}</b> {reto['desafiado_name'][:5].upper()}  \n"
                    f"┗━━━━━━━━━━━━━━━━┛"
                )

        elif tipo_evento == "falta":
            evento = (
                f"<pre>⚠️Falta</pre> min {int(minuto_partido)}'\n"
                f"👤 {nombre_jugador} ({nombre_equipo})\n\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()}  <b>{goles1}-{goles2}</b>  {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        elif tipo_evento == "tarjeta_amarilla":
            evento = (
                f"<pre>🟨Tarjeta amarilla</pre> min {int(minuto_partido)}'\n"
                f"👤 {nombre_jugador} ({nombre_equipo})\n\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()} <b>{goles1}-{goles2}</b> {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        elif tipo_evento == "tarjeta_roja":
            evento = (
                f"<pre>🟥TARJETA ROJA!</pre> min {int(minuto_partido)}'\n\n"
                f"👤 {nombre_jugador} ({nombre_equipo})\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()} <b>{goles1}-{goles2}</b>  {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        elif tipo_evento == "ocasion":
            evento = (
                f"<pre>🎯Ocasión clara</pre> min {int(minuto_partido)}'\n"
                f"👤 {nombre_jugador} ({nombre_equipo})\n\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()}  <b>{goles1}-{goles2}</b> {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        elif tipo_evento == "esquina":
            evento = (
                f"<pre>🚩Saque de esquina</pre> min {int(minuto_partido)}'\n"
                f"⚽{nombre_equipo}\n\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()} <b>{goles1}-{goles2}</b>  {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        elif tipo_evento == "cambio":
            jugador_sale = random.choice(equipo)
            jugador_entra = random.choice([p for p in equipo if p != jugador_sale])
            evento = (
                f"<pre>🔄Cambio</pre> min {int(minuto_partido)}'\n"
                f"⬅️ <b>Sale:</b> {jugador_sale['name']}\n"
                f"➡️ <b>Entra:</b> {jugador_entra['name']}\n"
                f"({nombre_equipo})\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()} <b>{goles1}-{goles2}</b>   {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        elif tipo_evento == "lesion":
            evento = (
                f"<pre>🏥¡Lesión!</pre> min {int(minuto_partido)}'\n\n"
                f"👤 {nombre_jugador} ({nombre_equipo})\n"
                f"┏━━━━━━━━━━━━━━━━┓\n"
                f"  {reto['desafiante_name'][:5].upper()} <b>{goles1}-{goles2}</b> {reto['desafiado_name'][:5].upper()}  \n"
                f"┗━━━━━━━━━━━━━━━━┛"
            )

        eventos.append(evento)

        try:
            await context.bot.send_message(
                chat_id=reto["desafiante_id"],
                text=evento,
                parse_mode='HTML'
            )
            await context.bot.send_message(
                chat_id=reto["desafiado_id"],
                text=evento,
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error enviando evento: {str(e)}")

    # Actualizar marcador cada 15 minutos de partido
    if minuto_partido % 15 < 3:
        marcador_msg = (
            f"📊 <b>MARCADOR ACTUAL</b> ⏱️ {int(minuto_partido)}'\n\n"
            f"⚽ <b>{reto['desafiante_name']}</b> {goles1} - {goles2} <b>{reto['desafiado_name']}</b>"
        )
        try:
            await context.bot.send_message(
                chat_id=reto["desafiante_id"],
                text=marcador_msg,
                parse_mode='HTML'
            )
            await context.bot.send_message(
                chat_id=reto["desafiado_id"],
                text=marcador_msg,
                parse_mode='HTML'
            )
        except:
            pass

    # Actualizar job si no ha terminado
    if minuto_real < 5:
        context.job.data = {
            "reto_id": reto_id,
            "minuto_partido": minuto_partido,
            "minuto_real": minuto_real,
            "goles1": goles1,
            "goles2": goles2,
            "eventos": eventos
        }
        context.job_queue.run_once(
            callback=simular_eventos_partido,
            when=10,
            data=context.job.data,
            name=f"partido_{reto_id}"
        )
    else:
        minuto_partido = 90
        await finalizar_partido(context, reto_id, goles1, goles2, eventos)
async def calcular_probabilidad_gol(atacante: dict, defensor: dict) -> float:
    """Calcula la probabilidad de gol basada principalmente en el rating comparado"""

    # Obtener ratings reales, sin limitar
    atk_rating = float(atacante.get("rating") or 0.0)
    def_rating = float(defensor.get("rating") or 0.0)

    # Si el atacante tiene más rating → gol seguro
    if atk_rating > def_rating:
        return 1.0

    # Si tienen igual rating → probabilidad media (50%)
    elif atk_rating == def_rating:
        return 0.5

    # Si el defensor tiene más rating → reducir probabilidad
    else:
        diferencia = def_rating - atk_rating
        penalizacion = diferencia * 0.1  # cada punto de diferencia baja 10%
        probabilidad = 0.5 - penalizacion
        return max(0.1, min(0.99, probabilidad))  # límite inferior 10%
    
async def finalizar_partido(context: ContextTypes.DEFAULT_TYPE, reto_id: str, goles1: int, goles2: int, eventos: list):
    """Finaliza el partido con resumen profesional y notifica al grupo"""
    async with lock_retos:
        retos_data = await load_retos_data()
        if reto_id not in retos_data:
            return
        
        reto = retos_data[reto_id]
        reto["estado"] = "completado"
        reto["resultado"] = f"{goles1}-{goles2}"
        retos_data[reto_id] = reto
        await save_retos_data(retos_data)
    
    # Determinar ganador
    if goles1 > goles2:
        ganador_id = reto["desafiante_id"]
        ganador_nombre = reto["desafiante_name"]
        perdedor_id = reto["desafiado_id"]
        perdedor_nombre = reto["desafiado_name"]
        resultado = f"🏆 <b>{ganador_nombre} gana!</b>"
    elif goles2 > goles1:
        ganador_id = reto["desafiado_id"]
        ganador_nombre = reto["desafiado_name"]
        perdedor_id = reto["desafiante_id"]
        perdedor_nombre = reto["desafiante_name"]
        resultado = f"🏆 <b>{ganador_nombre} gana!</b>"
    else:
        ganador_id = None
        ganador_nombre = None
        resultado = "🤝 <b>¡Empate!</b>"
    
    # Procesar pagos
    async with lock_data:
        user_data = await load_data()
        monto = reto["monto"]
        
        if ganador_id:
            # Ganador recibe el 90% del pozo (10% para la casa)
            premio = monto * 1.8  # 90% de 2 montos
            user_data["usuarios"][ganador_id]["Balance"] += premio
        else:
            # Empate: ambos recuperan su dinero
            user_data["usuarios"][reto["desafiante_id"]]["Balance"] += monto
            user_data["usuarios"][reto["desafiado_id"]]["Balance"] += monto
        
        await save_data(user_data)
        
        
        
        # Calcular aportes al bote
        total_aporte = monto * 2
        aporte_bote = total_aporte * 0.02  # 2 % al balance
        aporte_bono = 3  # siempre 3 de bono

        # Cargar archivo de ranking para actualizar el bote
        if os.path.exists(RANKING_FILE):
            with open(RANKING_FILE, 'r') as f:
                ranking_data = json.load(f)
        else:
            ranking_data = {}

        if "bote" not in ranking_data:
            ranking_data["bote"] = {
                "balance": 0,
                "creditos": 0,
                "bono": 0,
                "barriles": 0
            }

        ranking_data["bote"]["balance"] += aporte_bote
        ranking_data["bote"]["bono"] += aporte_bono

        # Guardar cambios en el archivo de ranking
        with open(RANKING_FILE, 'w') as f:
            json.dump(ranking_data, f, indent=2)
    
    # Actualizar ranking PvP (solo si no es empate)
    if ganador_id and perdedor_id:
        await actualizar_ranking_pvp(
            ganador_id=ganador_id,
            perdedor_id=perdedor_id,
            goles_ganador=max(goles1, goles2),
            goles_perdedor=min(goles1, goles2)
        )
    
    # Construir resumen profesional para jugadores
    resumen = (
        f"🏁 <b>FINAL DEL PARTIDO</b> 🏁\n\n"
        f"⚽ <b>{reto['desafiante_name']} {goles1}-{goles2} {reto['desafiado_name']}</b>\n\n"
        f"{resultado}\n"
    )
    
    if ganador_id:
        resumen += f"💰 <b>Premio:</b> ${premio:.2f}\n\n"
    else:
        resumen += f"💰 <b>Cada jugador recupera:</b> ${monto:.2f}\n\n"
    
    # Añadir estadísticas
    resumen += "📊 <b>Estadísticas del partido:</b>\n"
    resumen += f"- Total goles: {goles1 + goles2}\n"
    resumen += f"- Eventos registrados: {len(eventos)}\n\n"
    
    # Añadir últimos 3 eventos si existen
    if eventos:
        resumen += "📝 <b>Últimos eventos:</b>\n"
        for evento in eventos[-3:]:
            resumen += f"• {evento}\n"
    
    # Construir mensaje para el grupo (más completo)
    mensaje_grupo = (
        f"🏟️ <b>RESULTADO FINAL - PARTIDO #{reto_id[:6]}</b> 🏟️\n\n"
        f"⚽ <b>{reto['desafiante_name']} {goles1}-{goles2} {reto['desafiado_name']}</b>\n\n"
        f"📌 <b>Detalles:</b>\n"
        f"├ 🎮 Tipo: {'Amistoso' if reto.get('tipo') == 'amistoso' else 'Competitivo'}\n"
        f"├ 💰 Monto apostado: ${monto:.2f} cada jugador\n"
    )
    
    if ganador_id:
        mensaje_grupo += (
            f"├ 🏆 Ganador: {ganador_nombre}\n"
            f"└ 🎁 Premio obtenido: ${premio:.2f}\n\n"
        )
    else:
        mensaje_grupo += "└ 🎁 Resultado: Empate (dinero devuelto)\n\n"
    
    mensaje_grupo += (
        f"📊 <b>Estadísticas:</b>\n"
        f"├ ⚽ Goles totales: {goles1 + goles2}\n"
        f"└ 📝 Eventos registrados: {len(eventos)}\n\n"
    )
    
    if eventos:
        mensaje_grupo += "🔥 <b>Momentos destacados:</b>\n"
        for evento in eventos[-3:]:
            mensaje_grupo += f"• {evento}\n"
    
    # Enviar resumen a los jugadores
    try:
        await context.bot.send_message(
            chat_id=reto["desafiante_id"],
            text=resumen,
            parse_mode='HTML'
        )
        await context.bot.send_message(
            chat_id=reto["desafiado_id"],
            text=resumen,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"Error enviando resumen: {str(e)}")
    
    # Enviar mensaje al grupo de registro
    try:
        await context.bot.send_message(
            chat_id=REGISTRO_MINIJUEGOS,
            text=mensaje_grupo,
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error enviando mensaje al grupo: {str(e)}")


# Funciones para los callbacks
async def procesar_aceptar_reto(update: Update, context: CallbackContext):
    await procesar_respuesta_reto(update, context, "aceptar")

async def procesar_rechazar_reto(update: Update, context: CallbackContext):
    await procesar_respuesta_reto(update, context, "rechazar")

# Llamar a initialize_retos_file en initialize_files()
def initialize_files():
    
    initialize_retos_file()                                   
async def mostrar_tutorial_partidos(update: Update, context: CallbackContext):
    """Muestra un tutorial interactivo sobre el sistema de partidos"""
    query = update.callback_query
    await query.answer()
    
    # Definir las páginas del tutorial
    paginas = [
        {
            'titulo': "🎮 <b>TUTORIAL - SISTEMA DE PARTIDOS</b> 🎮",
            'contenido': (
                "¡Bienvenido al sistema de partidos pvp de Fantasy Football!\n\n"
                "Aquí podrás desafiar a otros jugadores, competir por premios y mejorar tu equipo.\n\n"
                "🔹 <b>Tipos de partidos:</b>\n"
                "├ <b>Amistosos</b>: Sin apuesta, solo diversión\n"
                "└ <b>Competitivos</b>: Con apuesta y premios\n\n"
                "📖 Usa los botones para navegar por la guía."
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_partidos_1')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial')]
            ]
        },
        {
            'titulo': "💰 <b>CÓMO APOSTAR</b> 💰",
            'contenido': (
                "📌 <b>Pasos para crear un partido con apuesta:</b>\n\n"
                "1. Elige a un rival (usando @username)\n"
                "2. Selecciona el tipo <b>Competitivo</b>\n"
                "3. Establece el monto de apuesta (ej: 50)\n"
                "4. Espera a que el rival acepte\n\n"
                "💡 <b>Ejemplo:</b>\n"
                "<code>/reto 50 @username</code>\n\n"
                "🪧Al usar este comando 50 representa el monto de apuesta y @username a quien vas a retar."
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_partidos_0')],
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_partidos_2')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial')]
            ]
        },
        {
            'titulo': "⏱️ <b>DURACIÓN DEL PARTIDO</b> ⏱️",
            'contenido': (
                "⌛ <b>Tiempos del partido:</b>\n\n"
                "⏳ <b>Vida real:</b> 5 minutos\n"
                "⏱️ <b>Tiempo de juego:</b> 90 minutos\n\n"
                "📊 <b>Equivalencia:</b>\n"
                "├ 1 minuto real = 18 minutos de juego\n"
                "└ 10 segundos reales = 3 minutos de juego\n\n"
                "⚽ <b>Ejemplo:</b>\n"
                "Si un gol ocurre a los 2 minutos reales,\n"
                "se mostrará como minuto 36' en el juego para reducir el tiempo en resumen 90 minutos del partido se resuelve en 5 minutos."
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_partidos_1')],
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_partidos_3')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial')]
            ]
        },
        {
            'titulo': "⚽ <b>EVENTOS DURANTE EL PARTIDO</b> ⚽",
            'contenido': (
                "📢 <b>Eventos que pueden ocurrir:</b>\n\n"
                "⚽ <b>Gol</b> (25% probabilidad)\n"
                "🟨 <b>Tarjeta amarilla</b> (10%)\n"
                "🟥 <b>Tarjeta roja</b> (3%)\n"
                "⚠️ <b>Falta</b> (20%)\n"
                "🎯 <b>Ocasión clara</b> (15%)\n\n"
                "📌 <b>Ejemplo real:</b>\n"
                "⚽ <b>GOOOL!</b> min 45'\n"
                "👤 Messi (Tu Equipo)\n"
                "📊 MARCADOR: Tu Equipo 1-0 Rival\n\n"
                "🪧Todos los eventos ocurridos en el partido dependen completamente de la calidad de tus jugadores y la alineación que tengas"
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_partidos_2')],
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_partidos_4')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial')]
            ]
        },
        {
            'titulo': "🏆 <b>FINAL Y PREMIOS</b> 🏆",
            'contenido': (
                "🏁 <b>Al terminar el partido:</b>\n\n"
                "1. Sistema calcula automáticamente al ganador\n"
                "2. Premios se distribuyen:\n"
                "├ 🥇 Ganador: 90% del pozo\n"
                "└ 🏦 Casa: 10% comisión\n\n"
                "💰 <b>Ejemplo con apuesta de $50:</b>\n"
                "├ Pozo total: $100 (50x2)\n"
                "└ Ganador recibe: $90\n\n"
                "📢 Todos los resultados se revisan por un administrador."
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_partidos_3')],
                [InlineKeyboardButton("✅ Entendido", callback_data='cerrar_tutorial')]
            ]
        }
    ]
    
    # Obtener la página actual (por defecto primera página)
    pagina_actual = 0
    if query.data.startswith('tutorial_partidos_'):
        pagina_actual = int(query.data.split('_')[2])
    
    # Construir mensaje
    pagina = paginas[pagina_actual]
    mensaje = f"{pagina['titulo']}\n━━━━━━━━━━━━━━━━━━\n{pagina['contenido']}"
    
    # Construir teclado
    teclado = pagina['botones']
    
    # Enviar mensaje (editar si ya existe)
    try:
        if query.message.photo:
            # Si el mensaje anterior tenía foto
            await query.message.edit_media(
                media=InputMediaPhoto(
                    media=pagina['imagen'] if pagina['imagen'] else 'https://i.imgur.com/JyxUStL.png',  # Imagen por defecto
                    caption=mensaje,
                    parse_mode='HTML'
                ),
                reply_markup=InlineKeyboardMarkup(teclado)
            )
        else:
            # Mensaje normal sin foto
            await query.message.edit_text(
                text=mensaje,
                reply_markup=InlineKeyboardMarkup(teclado),
                parse_mode='HTML'
            )
    except Exception as e:
        logging.error(f"Error en tutorial: {str(e)}")
        await query.message.reply_text(
            "⚠️ Error al mostrar el tutorial. Intenta nuevamente.",
            parse_mode='HTML'
        )

async def cerrar_tutorial(update: Update, context: CallbackContext):
    """Cierra el mensaje del tutorial"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()        
    
async def mostrar_tutorial_torneos(update: Update, context: CallbackContext):
    """Muestra un tutorial interactivo sobre el sistema de torneos"""
    query = update.callback_query
    await query.answer()
    
    # Definir las páginas del tutorial
    paginas = [
        {
            'titulo': "🏆 <b>TUTORIAL - SISTEMA DE TORNEOS</b> 🏆",
            'contenido': (
                "¡Bienvenido al emocionante sistema de torneos de Fantasy Football!\n\n"
                "Aquí competirás contra otros managers en una liga justa y equilibrada.\n\n"
                "🔹 <b>Características principales:</b>\n"
                "├ <b>Formato</b>: Todos contra todos (ida y vuelta)\n"
                "├ <b>Premios</b>: En bonos, balance o créditos\n"
                "└ <b>Duración</b>:  Depende de cuantos participantes hallan no dura más de 5 horas\n\n"
                "📖 Usa los botones para navegar por la guía."
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_torneos_1')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial_torneos')]
            ]
        },
        {
            'titulo': "📝 <b>CÓMO PARTICIPAR</b> 📝",
            'contenido': (
                "📌 <b>Requisitos para unirte a un torneo:</b>\n\n"
                "1. Tener un equipo completo con 11 titulares\n"
                "2. Fondos suficientes para la entrada\n"
                "3. No estar en otro torneo activo\n\n"
                "💡 <b>Proceso de inscripción:</b>\n"
                "1. Ve al menú de Torneos cuando haya uno activo\n"
                "2. Haz clic en 'Unirse al Torneo'\n"
                "3. Paga la entrada (automático)\n"
                "4. ¡Listo! El torneo comenzará cuando se cierren las inscripciones\n\n"
                
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_torneos_0')],
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_torneos_2')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial_torneos')]
            ]
        },
        {
            'titulo': "⚽ <b>FORMATO DE COMPETICIÓN</b> ⚽",
            'contenido': (
                "🏟️ <b>Sistema de juego:</b>\n\n"
                "🔹 <b>Fase de grupos</b> (si hay +8 participantes):\n"
                "├ Todos contra todos (ida y vuelta)\n"
                "└ Clasifican los mejores de cada grupo\n\n"
                "🔹 <b>Fase final</b> (eliminatorias directas):\n"
                "├ Cuartos, semifinales y final\n"
                "└ Partido único (mejor de 1)\n\n"
                "⏱️ <b>Duración de partidos:</b>\n"
                "├ 5 minutos reales = 90 minutos de juego\n"
                "└ Sistema automático de eventos (goles, tarjetas, etc.)"
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_torneos_1')],
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_torneos_3')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial_torneos')]
            ]
        },
        {
            'titulo': "📊 <b>SISTEMA DE PUNTUACIÓN</b> 📊",
            'contenido': (
                "🏅 <b>Puntos por partido:</b>\n\n"
                "🥇 <b>Victoria</b>: 3 puntos\n"
                "🤝 <b>Empate</b>: 1 punto\n"
                "🥈 <b>Derrota</b>: 0 puntos\n\n"
                "📌 <b>Desempates:</b>\n"
                "1. Diferencia de goles\n"
                "2. Goles a favor\n"
                "3. Resultado entre equipos empatados\n\n"
                "⚽ <b>Ejemplo de tabla:</b>\n"
                "1. Equipo A - 9 pts (DG +5)\n"
                "2. Equipo B - 6 pts (DG +2)\n"
                "3. Equipo C - 3 pts (DG -3)\n"
                "4. Equipo D - 0 pts (DG -4)"
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_torneos_2')],
                [InlineKeyboardButton("➡️ Siguiente", callback_data='tutorial_torneos_4')],
                [InlineKeyboardButton("❌ Cerrar", callback_data='cerrar_tutorial_torneos')]
            ]
        },
        {
            'titulo': "💰 <b>PREMIOS Y RECOMPENSAS</b> 💰",
            'contenido': (
                "🏆 <b>Distribución de premios:</b>\n\n"
                "🥇 <b>1er lugar</b>: 50% del pozo\n"
                "🥈 <b>2do lugar</b>: 30% del pozo\n"
                "🥉 <b>3er lugar</b>: 20% del pozo\n\n"
                "💸 <b>Ejemplo con 10 participantes (entrada $100):</b>\n"
                "├ Pozo total: $1000\n"
                "├ Ganador: $500\n"
                "├ Segundo: $300\n"
                "└ Tercero: $200\n\n"
                "📢 Los premios se pagan según la inscripción (bonos, balance o créditos)"
            ),
            'imagen': None,
            'botones': [
                [InlineKeyboardButton("⬅️ Anterior", callback_data='tutorial_torneos_3')],
                [InlineKeyboardButton("✅ Entendido", callback_data='cerrar_tutorial_torneos')]
            ]
        }
    ]
    
    # Obtener la página actual
    pagina_actual = 0
    if query.data.startswith('tutorial_torneos_'):
        pagina_actual = int(query.data.split('_')[2])
    
    # Construir mensaje
    pagina = paginas[pagina_actual]
    mensaje = f"{pagina['titulo']}\n━━━━━━━━━━━━━━━━━━\n{pagina['contenido']}"
    
    # Construir teclado
    teclado = pagina['botones']
    
    # Enviar mensaje
    try:
        await query.message.edit_text(
            text=mensaje,
            reply_markup=InlineKeyboardMarkup(teclado),
            parse_mode='HTML'
        )
    except Exception as e:
        logging.error(f"Error en tutorial torneos: {str(e)}")
        await query.message.reply_text(
            "⚠️ Error al mostrar el tutorial. Intenta nuevamente.",
            parse_mode='HTML'
        )

async def cerrar_tutorial_torneos(update: Update, context: CallbackContext):
    """Cierra el mensaje del tutorial de torneos"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

async def eliminar_usuario_handler(update: Update, context: CallbackContext):
    try:
        print("🔧 INICIO: eliminar_usuario_handler activado")

        # resto del código...
        # Verificar que el comando viene de un administrador
        admin_id = "7031172659"  # ID del administrador
        user_id = str(update.effective_user.id)
        
        if user_id != admin_id:
            await update.message.reply_text("❌ Solo el administrador puede usar este comando.")
            return
            
        # Verificar que se proporcionó un user_id
        if not context.args:
            await update.message.reply_text("❌ Uso: /eliminar <user_id>")
            return
            
        target_user_id = context.args[0]
        
        # Confirmar con el administrador
        confirm_keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data=f'confirmar_eliminar_{target_user_id}')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='cancelar_eliminar')]
        ]
        
        await update.message.reply_text(
            f"⚠️ ¿Estás seguro de eliminar al usuario {target_user_id} y todo su equipo?",
            reply_markup=InlineKeyboardMarkup(confirm_keyboard)
        )
        
    except Exception as e:
        logging.error(f"Error en eliminar_usuario_handler: {str(e)}")
        await update.message.reply_text("❌ Error al procesar el comando.")

async def confirmar_eliminar_usuario(update: Update, context: CallbackContext):
    """Confirma y ejecuta la eliminación del usuario"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extraer el user_id del callback_data
        target_user_id = query.data.split('_')[-1]
        
        # Cargar datos con lock
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()
            
            # Verificar si el usuario existe
            if target_user_id not in fantasy_data:
                await query.edit_message_text(f"❌ El usuario {target_user_id} no existe en el juego.")
                return
                
            # Eliminar al usuario
            del fantasy_data[target_user_id]
            
            # Guardar cambios
            await save_fantasy_data(fantasy_data)
            
            await query.edit_message_text(f"✅ Usuario {target_user_id} eliminado correctamente.")
            
            
                
    except Exception as e:
        logging.error(f"Error en confirmar_eliminar_usuario: {str(e)}")
        await query.edit_message_text("❌ Error al eliminar el usuario.")

async def cancelar_eliminar(update: Update, context: CallbackContext):
    """Cancela la eliminación del usuario"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ Eliminación cancelada.")


async def get_fantasy_handler(update: Update, context: CallbackContext):
    """Muestra un resumen completo del estado del Fantasy con detalles por usuario"""
    try:
        # Cargar todos los datos necesarios
        with open(PLAYERS_FILE, 'r') as f:
            all_players = json.load(f)
        
        fantasy_data = await load_fantasy_data()
        
        # 1. Estadísticas generales
        users_data = {k: v for k, v in fantasy_data.items() if isinstance(v, dict) and 'team' in v}
        total_users = len(users_data)
        total_creditos = sum(user['credits'] for user in users_data.values())
        
        # 2. Estadísticas de jugadores
        all_player_ids = {str(p['player']['id']) for p in all_players if 'player' in p and 'id' in p['player']}
        assigned_player_ids = set()
        team_values = []
        titular_values = []
        
        # 3. Detalles por usuario
        user_details = []
        for user_id, user_data in users_data.items():
            # Info básica del usuario
            num_players = len(user_data['team'])
            team_value = user_data.get('value', 0)
            titulares = [p for p in user_data['team'] if p.get('is_titular', False)]
            titular_value = sum(p['value'] for p in titulares)
            
            # Agregar a estadísticas globales
            team_values.append(team_value)
            titular_values.append(titular_value)
            assigned_player_ids.update(str(p['id']) for p in user_data['team'])
            
            nombre = await obtener_nombre_usuario(user_id)
            
            # Detalle para este usuario
            user_details.append(
                f"👤 <b>{nombre}</b> (ID: <code>{user_id}</code>)\n"
                f"├ 💰 Valor equipo: {team_value}\n"
                f"├ ⭐ Valor titulares: {titular_value}\n"
                f"├ 👥 Jugadores: {num_players} ({len(titulares)} titulares)\n"
                f"└ 💎 Créditos: {user_data.get('credits', 0)}"
            )
        
        available_players = len(all_player_ids - assigned_player_ids)
        avg_team_value = sum(team_values) / len(team_values) if team_values else 0
        avg_titular_value = sum(titular_values) / len(titular_values) if titular_values else 0
        
        # 4. Estadísticas de mercado
        active_auctions = len(fantasy_data.get('subastas', {}))
        
        # 5. Top equipos
        top_users = sorted(
            [(data.get('name', f"Usuario {uid[:6]}"), data.get('value', 0), len(data['team']), uid) 
             for uid, data in users_data.items()],
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # 6. Construir el mensaje
        message = [
            "⚽ <b>REPORTE COMPLETO DEL FANTASY</b> ⚽",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 <b>Usuarios activos:</b> {total_users}",
            f"💰 <b>Créditos totales:</b> {total_creditos}",
            "",
            "📈 <b>Estadísticas globales:</b>",
            f"├ 🏷 Jugadores totales: {len(all_player_ids)}",
            f"├ 🛒 Jugadores disponibles: {available_players}",
            f"├ 💎 Valor promedio equipos: {avg_team_value:.2f}",
            f"└ ⭐ Valor promedio titulares: {avg_titular_value:.2f}",
            "",
            "🏷 <b>Mercado:</b>",
            f"├ 🔨 Subastas activas: {active_auctions}",
          
            "",
            "🏆 <b>Top 5 Equipos:</b>"
        ]
        
        for i, (name, value, players, _) in enumerate(top_users, 1):
            message.append(f"{i}. {name} - 💰 {value} (👤 {players} jugadores)")
        
        message.extend([
            "",
            "👥 <b>Detalle por Usuario:</b>",
            *user_details[:3],  # Mostrar primeros 3 para no saturar
            "",
            f"🔄 <i>Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        ])
        
        # 7. Teclado interactivo
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='refresh_fantasy_stats'),
             InlineKeyboardButton("📊 Ver Todos", callback_data='show_all_users')],
            [InlineKeyboardButton("⚽ Jugadores Libres", callback_data='show_free_players'),
             InlineKeyboardButton("💎 Top Equipos", callback_data='show_top_teams')]
        ]
        
        # Enviar mensaje paginado si es muy largo
        full_message = "\n".join(message)
        if len(full_message) > 4000:
            parts = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
            await update.message.reply_text(
                text=parts[0],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            for part in parts[1:]:
                await update.message.reply_text(text=part, parse_mode='HTML')
        else:
            await update.message.reply_text(
                text=full_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
    except Exception as e:
        error_msg = "❌ Error al generar el reporte del Fantasy"
        logging.error(f"{error_msg}: {str(e)}")
        await update.message.reply_text(error_msg)
async def show_all_users(update: Update, context: CallbackContext):
    """Muestra la lista completa de usuarios"""
    query = update.callback_query
    await query.answer()

    try:
        fantasy_data = await load_fantasy_data()

        # Cargar usernames desde user_data.json
        with open("user_data.json", "r") as f:
            user_data = json.load(f).get("usuarios", {})

        # Cargar ranking semanal
        try:
            with open("ranking_semanal.json", "r") as f:
                ranking_data = json.load(f).get("ranking", {})
        except:
            ranking_data = {}

        users_data = {k: v for k, v in fantasy_data.items() if isinstance(v, dict) and 'team' in v}

        message_parts = []
        current_part = "<b>👥 LISTA COMPLETA DE USUARIOS</b>\n━━━━━━━━━━━━━━━━━━"

        for user_id, user_fantasy in users_data.items():
            team = user_fantasy.get('team', [])
            if not isinstance(team, list):
                team = []

            titulares = sum(1 for p in team if isinstance(p, dict) and p.get('is_titular', False))
            suplentes = sum(1 for p in team if isinstance(p, dict) and not p.get('is_titular', False))

            username = user_data.get(user_id, {}).get('username')
            username_text = f"@{username}" if username else "Sin username"

            user_text = (
                f"\n\n👤 <b>{user_fantasy.get('name', f'Usuario {user_id}')}</b> ({username_text})\n"
                f"├ ID: <code>{user_id}</code>\n"
                f"├ 💰 Valor: {user_fantasy.get('value', 0)}\n"
                f"├ ⭐ Titulares: {titulares} | 🪑 Suplentes: {suplentes}\n"
                f"└ 💎 Créditos: {user_fantasy.get('credits', 0)}"
            )

            if user_id in ranking_data:
                r = ranking_data[user_id]
                user_text += (
                    f"\n📊 Torneos: {r.get('puntos_torneos', 0)} pts"
                    f" | ⚔️ PvP: {r.get('victorias_pvp', 0)}V - {r.get('derrotas_pvp', 0)}D"
                )

            # Agregar el texto al bloque actual o iniciar nuevo si se pasa del límite
            if len(current_part + user_text) > 3900:
                message_parts.append(current_part)
                current_part = ""

            current_part += user_text

        # Añadir la última parte
        if current_part:
            message_parts.append(current_part)

        # Enviar el primer mensaje editando el actual
        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data='refresh_fantasy_stats')]]
        await query.edit_message_text(
            text=message_parts[0],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

        # Enviar los demás como mensajes nuevos
        for part in message_parts[1:]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=part,
                parse_mode='HTML'
            )

    except Exception as e:
        await query.edit_message_text("❌ Error al cargar la lista de usuarios")
        print("Error en show_all_users:", e)
async def refresh_fantasy_stats(update: Update, context: CallbackContext):
    """Actualiza las estadísticas del fantasy"""
    query = update.callback_query
    await query.answer()
    await get_fantasy_handler(update, context)

    
async def mostrar_ranking(update: Update, context: CallbackContext):
    """Muestra el ranking semanal con el formato solicitado"""
    query = update.callback_query
    await query.answer()

    try:  
        # Cargar ranking  
        ranking_data = await cargar_ranking()  
        usuarios = sorted(  
            ranking_data["ranking"].values(),  
            key=lambda x: x["puntos_totales"],  
            reverse=True  
        )[:15]  # Top 15  

        mensaje = "🏆 <b>RANKING SEMANAL</b>\n"  
        mensaje += "━━━━━━━━━━━━━━━━━━━━━━\n"  
        mensaje += "<i>Actualizado: {}</i>\n\n".format(  
            ranking_data.get("ultima_actualizacion", "Desconocida")  
        )  

        for i, usuario in enumerate(usuarios, 1):  
            mensaje += (  
                f"{i}. <pre>{usuario['nombre']}</pre>\n"  
                f"   ⭐ Puntos Totales: <code>{usuario['puntos_totales']}</code>\n"  
                f"   🏅 Torneos: <code>{usuario['puntos_torneos']}</code> "  
                f"(en {usuario.get('torneos_jugados', 0)} torneos)\n"  
                f"   ⚔️ PvP: <code>{usuario['victorias_pvp']}V/{usuario['derrotas_pvp']}D</code>\n"
                f"   🏟️ Puntos  de Equipo: <code>{usuario.get('puntos_equipo', 0)}</code>\n\n"  
            )  

        # Agregar resumen del bote acumulado  
        bote = ranking_data.get("bote", {})  
        if bote:  
            mensaje += "💰 <b>PREMIO ACUMULADO</b>\n"  
            mensaje += "━━━━━━━━━━━━━━━━━━━━━━\n"  
            if bote.get("balance", 0): mensaje += f"• 🪙 Balance: <b>{round(bote['balance'], 2)}</b>\n"  
            if bote.get("creditos", 0): mensaje += f"• 💎 Créditos: <b>{round(bote['creditos'], 2)}</b>\n"  
            if bote.get("bono", 0): mensaje += f"• 🎁 Bono: <b>{round(bote['bono'], 2)}</b>\n"  
            if bote.get("barriles", 0): mensaje += f"• 🛢️ Barriles: <b>{round(bote['barriles'], 2)}</b>\n"  

        # Botones adicionales  
        keyboard = [  
            [InlineKeyboardButton("📊 ¿Cómo se calculan los puntos?", callback_data='explicar_puntos')],  
            [InlineKeyboardButton("🔄 Actualizar", callback_data='ranking_fantasy')],  
            [InlineKeyboardButton("🏠 Menú Principal", callback_data='juego_fantasy')]  
        ]  

        if query.message.text:  
            await query.edit_message_text(  
                text=mensaje,  
                reply_markup=InlineKeyboardMarkup(keyboard),  
                parse_mode='HTML'  
            )  
        else:  
            await query.message.reply_text(  
                text=mensaje,  
                reply_markup=InlineKeyboardMarkup(keyboard),  
                parse_mode='HTML'  
            )  

    except Exception as e:  
        logging.error(f"Error en mostrar_ranking: {str(e)}")  
        await query.message.reply_text("❌ Error al cargar el ranking. Intenta nuevamente más tarde.")
async def explicar_sistema_puntos(update: Update, context: CallbackContext):
    """Explica detalladamente cómo se calculan los puntos"""
    query = update.callback_query
    await query.answer()
    
    explicacion = """
📊 <b>SISTEMA DE PUNTUACIÓN FANTASY</b> 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━
Tus puntos se calculan <b>diariamente</b> según el rendimiento de tus <b>11 titulares</b>:

⚽ <b>Goles:</b> +5 pts cada uno
🎯 <b>Asistencias:</b> +3 pts cada una
🛡️ <b>Defensa sólida:</b>
  • Portero: +4 pts por partido sin goles
  • Defensa: +2 pts por partido sin goles
🔄 <b>Acciones defensivas:</b>
  • Intercepciones: +0.7 pts cada una
  • Tackles exitosos: +0.6 pts cada uno
🔑 <b>Pases clave:</b> +0.5 pts cada uno
⚠️ <b>Faltas:</b>
  • Cometidas: -0.3 pts cada una
  • Recibidas: +0.2 pts cada una
🟨 <b>Tarjeta amarilla:</b> -1 pt
🟥 <b>Tarjeta roja:</b> -3 pts
🧤 <b>Porteros:</b>
  • Parada de penalty: +3 pts
  • Penalty fallado: -2 pts

<b>Adicionalmente ganas puntos por:</b>
🏆 Torneos: Puntos según posición final
⚔️ PvP: +5 pts por victoria

<i>Los puntos se suman a tu total general que determina tu posición en el ranking.</i>

<pre>🎁Como se reparten los premios?</pre>
Los premios son repartidos entre los 10 primeros lugares de mayor a menor
"""

    keyboard = [
        [InlineKeyboardButton("🔙 Volver al Ranking", callback_data='ranking_fantasy')],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data='juego_fantasy')]
    ]

    await query.edit_message_text(
        text=explicacion,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def cargar_ranking():
    """Carga los datos del ranking semanal o crea el archivo si no existe."""
    try:
        if not os.path.exists("ranking_semanal.json"):
            # Crear el archivo con estructura inicial
            datos_iniciales = {
                "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d"),
                "ranking": {}
            }
            with open("ranking_semanal.json", "w") as f:
                json.dump(datos_iniciales, f, indent=2)
            return datos_iniciales
        
        # Si el archivo existe, cargarlo
        with open("ranking_semanal.json", "r") as f:
            return json.load(f)
    
    except Exception as e:
        logging.error(f"Error al cargar/crear el ranking: {str(e)}")
        # Retorna una estructura vacía como fallback
        return {
            "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d"),
            "ranking": {}
        }

async def guardar_ranking(data):
    """Guarda los datos del ranking"""
    try:
        with open("ranking_semanal.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Error guardando ranking: {str(e)}")
        
async def reiniciar_ranking(context: ContextTypes.DEFAULT_TYPE):
    """Reparte premios a los 10 primeros lugares y reinicia el ranking con mejor diseño visual"""
    try:
        print("🚀 Ejecutando reiniciar_ranking (versión mejorada)...") 
        # Cargar datos necesarios
        ranking_data = await cargar_ranking()
        user_data = await load_data()
        fantasy_data = await load_fantasy_data()
        admin_id = 7031172659
        
        # Verificar que hay suficientes participantes
        participantes = ranking_data.get("ranking", {})
        total_participantes = len(participantes)
        
        if total_participantes < 3:  # Mínimo 3 participantes para repartir premios
            await context.bot.send_message(
                chat_id=admin_id,
                text="⚠️ <b>No se repartieron premios</b> - Solo hay {} participantes".format(total_participantes),
                parse_mode='HTML'
            )
            return await reiniciar_ranking_suave(ranking_data)

        # Ordenar participantes por puntos totales
        sorted_participantes = sorted(
            participantes.items(),
            key=lambda x: x[1]["puntos_totales"],
            reverse=True
        )[:10]  # Tomar los 10 primeros

        # Nueva distribución de premios para 10 lugares
        # 1ro: 30%, 2do: 20%, 3ro: 15%, 4to: 10%, 5to: 8%, 
        # 6to: 6%, 7mo: 5%, 8vo: 3%, 9no: 2%, 10mo: 1%
        distribucion = [0.30, 0.20, 0.15, 0.10, 0.08, 0.06, 0.05, 0.03, 0.02, 0.01]
        bote_balance = ranking_data.get("bote", {}).get("balance", 0)
        bote_creditos = ranking_data.get("bote", {}).get("creditos", 0)
        bote_bono = ranking_data.get("bote", {}).get("bono", 0)

        # Repartir premios
        mensaje_admin = """
✨ <b>🏆 RESUMEN DE PREMIOS REPARTIDOS 🏆</b> ✨

💰 <b>Bote Total:</b>
   • Dinero: <code>${:,.2f}</code>
   • Créditos: <code>{:,}</code>
   • Bonos: <code>{:,}</code>

📊 <b>Distribución a los 10 primeros:</b>
""".format(bote_balance, bote_creditos, bote_bono)

        emojis_posicion = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, (user_id, data) in enumerate(sorted_participantes):
            premio_balance = bote_balance * distribucion[i] if i < len(distribucion) else 0
            premio_creditos = bote_creditos * distribucion[i] if i < len(distribucion) else 0
            premio_bono = bote_bono * distribucion[i] if i < len(distribucion) else 0

            # Asignar premios según posición
            if premio_balance > 0:
                if str(user_id) in user_data["usuarios"]:
                    user_data["usuarios"][str(user_id)]["Balance"] += premio_balance
                else:
                    logging.warning(f"Usuario {user_id} no encontrado en user_data")

            if premio_creditos > 0:
                if str(user_id) in fantasy_data:
                    fantasy_data[str(user_id)]["credits"] += premio_creditos
                else:
                    logging.warning(f"Usuario {user_id} no encontrado en fantasy_data")

            if premio_bono > 0:
                if str(user_id) in user_data["Bono_apuesta"]:
                    user_data["Bono_apuesta"][str(user_id)]["Bono"] += premio_bono
                else:
                    logging.warning(f"Usuario {user_id} no encontrado en Bono_apuesta")

            # Preparar mensajes
            posicion_str = f"{emojis_posicion[i]} {i+1}° LUGAR" if i < 10 else f"{i+1}° LUGAR"
            
            # Mensaje para el admin
            mensaje_admin += (
                f"\n<b>{posicion_str}:</b> <code>{data['nombre']}</code>\n"
                f"   • 💵 Balance: <code>+${premio_balance:,.2f}</code>\n"
                f"   • 🪙 Créditos: <code>+{premio_creditos:,}</code>\n"
                f"   • 💎 Bonos: <code>+{premio_bono:,}</code>\n"
            )

            # Notificar al ganador (solo si recibió premios)
            if premio_balance > 0 or premio_creditos > 0 or premio_bono > 0:
                mensaje_ganador = f"""
🎉 <b>¡FELICIDADES!</b> 🎉

Has obtenido el <b>{posicion_str}</b> en el ranking semanal con <b>{data['puntos_totales']:,} puntos</b>!

<b>🏆 Premios recibidos:</b>
   • <b>Dinero:</b> <code>+${premio_balance:,.2f}</code>
   • <b>Créditos:</b> <code>+{premio_creditos:,}</code>
   • <b>Bonos:</b> <code>+{premio_bono:,}</code>

✨ <i>Sigue participando para ganar aún más la próxima semana!</i>
"""
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=mensaje_ganador,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logging.error(f"No se pudo notificar a {user_id}: {str(e)}")
                    mensaje_admin += f"   ⚠️ <i>No se pudo notificar al usuario</i>\n"

        # Añadir footer al mensaje del admin
        mensaje_admin += f"\n<b>Total participantes:</b> <code>{total_participantes:,}</code>"

        # Notificar al admin
        await context.bot.send_message(
            chat_id=admin_id,
            text=mensaje_admin,
            parse_mode='HTML'
        )

        # Guardar todos los cambios
        await save_data(user_data)
        await save_fantasy_data(fantasy_data)

        # Reiniciar ranking (versión suave)
        await reiniciar_ranking_suave(ranking_data)

    except Exception as e:
        logging.error(f"Error en reiniciar_ranking: {str(e)}")
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"❌ <b>Error crítico al repartir premios:</b>\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )
async def reiniciar_ranking_suave(ranking_data):
    """Reinicia el ranking manteniendo la estructura básica"""
    try:
        # Mantener solo datos esenciales
        nuevo_ranking = {
            "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ranking": {},
            "bote": {
                "balance": 0,
                "creditos": 0,
                "bono": 0,
                "barriles": 0
            }
        }

        # Guardar histórico
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"ranking_historico_{fecha}.json", "w") as f:
            json.dump(ranking_data, f)

        # Guardar nuevo ranking
        with open(RANKING_FILE, "w") as f:
            json.dump(nuevo_ranking, f, indent=2)

    except Exception as e:
        logging.error(f"Error en reiniciar_ranking_suave: {str(e)}")
        raise



                                                                 
async def actualizar_ranking_pvp(ganador_id: str, perdedor_id: str, goles_ganador: int, goles_perdedor: int):
    """Actualiza el ranking después de un partido PvP"""
    try:
        ranking_data = await cargar_ranking()
        
        # Calcular puntos basados en diferencia de goles
        diferencia = goles_ganador - goles_perdedor
        puntos_base = 20
        puntos_extra = min(10, diferencia * 2)  # Máximo 10 puntos extra por diferencia
        
        # Para el ganador
        if ganador_id not in ranking_data["ranking"]:
            ranking_data["ranking"][ganador_id] = {
                "nombre": await obtener_nombre_usuario(ganador_id),
                "puntos_torneos": 0,
                "victorias_pvp": 0,
                "derrotas_pvp": 0,
                "puntos_totales": 0,
                "torneos_jugados": 0
            }
        
        ranking_data["ranking"][ganador_id]["victorias_pvp"] += 1
        ranking_data["ranking"][ganador_id]["puntos_totales"] += (puntos_base + puntos_extra)
        
        # Para el perdedor
        if perdedor_id not in ranking_data["ranking"]:
            ranking_data["ranking"][perdedor_id] = {
                "nombre": await obtener_nombre_usuario(perdedor_id),
                "puntos_torneos": 0,
                "victorias_pvp": 0,
                "derrotas_pvp": 0,
                "puntos_totales": 0,
                "torneos_jugados": 0
            }
        
        ranking_data["ranking"][perdedor_id]["derrotas_pvp"] += 1
        ranking_data["ranking"][perdedor_id]["puntos_totales"] += max(5, 10 - diferencia)  # Mínimo 5 puntos
        
        ranking_data["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await guardar_ranking(ranking_data)
        return True
    
    except Exception as e:
        logging.error(f"Error en actualizar_ranking_pvp: {str(e)}")
        return False
    
async def actualizar_ranking_torneo(clasificacion):
    """
    Actualiza el ranking con los puntos de TODOS los participantes del torneo.
    clasificacion: Diccionario con {user_id: posición_final}
    """
    try:
        ranking_data = await cargar_ranking()
        total_participantes = len(clasificacion)
        
        for user_id, posicion in clasificacion.items():
            # Fórmula de puntos: (total_participantes - posición + 1) * 10
            puntos = (total_participantes - posicion + 1) * 10
            
            if user_id not in ranking_data["ranking"]:
                ranking_data["ranking"][user_id] = {
                    "nombre": await obtener_nombre_usuario(user_id),
                    "puntos_torneos": 0,
                    "victorias_pvp": 0,
                    "derrotas_pvp": 0,
                    "puntos_totales": 0,
                    "torneos_jugados": 0
                }
            
            ranking_data["ranking"][user_id]["puntos_torneos"] += puntos
            ranking_data["ranking"][user_id]["puntos_totales"] += puntos
            ranking_data["ranking"][user_id]["torneos_jugados"] += 1
        
        ranking_data["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await guardar_ranking(ranking_data)
        return True

    except Exception as e:
        logging.error(f"Error en actualizar_ranking_torneo: {str(e)}")
        return False
        
        
        
# ===============================
# 🧹 Revisión inicial de inactividad
# ===============================

async def revisar_inactividad_fantasy(context: CallbackContext):
    """Revisa usuarios inactivos basado en puntos de torneo y PVP"""
    print("🔍 Iniciando revisión de inactividad para usuarios con 0 puntos")

    try:
        # Cargar datos necesarios
        async with lock_fantasy:
            fantasy_data = await load_fantasy_data()

        # Cargar ranking semanal
        try:
            with open("ranking_semanal.json", "r") as f:
                ranking_data = json.load(f).get("ranking", {})
            print(f"✅ Ranking cargado. Usuarios en ranking: {len(ranking_data)}")
        except Exception as e:
            print(f"❌ Error al cargar ranking: {e}")
            return

        usuarios_inactivos = []

        for user_id, user_data in fantasy_data.items():
            user_id_str = str(user_id)
            
            if not isinstance(user_data, dict) or "team" not in user_data:
                print(f"ℹ️ Estructura inválida para usuario {user_id_str}")
                continue

            user_rank = ranking_data.get(user_id_str, None)
            
            if user_rank is None:
                print(f"➡️ Usuario {user_id_str} no está en ranking, omitiendo")
                continue

            puntos_torneo = user_rank.get("puntos_torneos", 0)
            victorias_pvp = user_rank.get("victorias_pvp", 0)
            
            print(f"👤 {user_id_str} | 🏆 {puntos_torneo} | ⚔️ {victorias_pvp}")

            if puntos_torneo <= 0 and victorias_pvp <= 0:
                print(f"⚠️ Usuario {user_id_str} marcado como inactivo")
                usuarios_inactivos.append(user_id_str)
                
                try:
                    # Enviar notificación
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="⚠️ <b>¡ALERTA DE ELIMINACION DEL FANTASY!</b> ⚠️\n\nNo has participado en torneos ni en combates PVP.\n\nTienes 2 horas para participar o serás eliminado <b>DEFINITIVAMENTE del fantasy</b>.",
                        parse_mode='HTML'
                    )
                    
                    # Programar eliminación con parámetros seguros
                    context.job_queue.run_once(
                        callback=lambda ctx, uid=user_id: asyncio.create_task(eliminar_usuario_inactivo(ctx, uid)),
                        when=7200,  # 2 horas
                        name=f"elim_{user_id_str}"
                    )
                    
                except Exception as e:
                    print(f"❌ Error notificando a {user_id_str}: {str(e)}")
                    continue

        # Resultados
        print(f"\n📊 Resumen Final:")
        print(f"• Usuarios totales: {len(fantasy_data)}")
        print(f"• En ranking: {len(ranking_data)}")
        print(f"• Inactivos detectados: {len(usuarios_inactivos)}")
        
        if usuarios_inactivos:
            print("🔍 Usuarios inactivos detectados:")
            for uid in usuarios_inactivos:
                print(f"→ {uid}")

    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {str(e)}")
        traceback.print_exc()

async def eliminar_usuario_inactivo(context: CallbackContext, user_id):
    """Elimina definitivamente a un usuario inactivo"""
    try:
        user_id_str = str(user_id)
        print(f"\n🚀 Ejecutando eliminación para {user_id_str}")

        # 1. Verificar si el usuario sigue siendo inactivo
        try:
            with open("ranking_semanal.json", "r") as f:
                ranking = json.load(f).get("ranking", {}).get(user_id_str, {})
            
            puntos = ranking.get("puntos_torneos", 0)
            victorias = ranking.get("victorias_pvp", 0)
            
            print(f"🔍 Verificación final - Puntos: {puntos}, Victorias: {victorias}")

            if puntos > 0 or victorias > 0:
                print(f"✅ Usuario {user_id_str} reactivado, cancelando eliminación")
                return
        except Exception as e:
            print(f"❌ Error al verificar ranking: {e}")
            return

        # 2. Eliminar del sistema
        async with lock_fantasy:
            try:
                # Cargar datos actuales
                with open("user_fantasy.json", "r") as f:
                    data = json.load(f)
                
                if user_id_str not in data:
                    print(f"ℹ️ Usuario {user_id_str} no existe en fantasy_data")
                    return
                
                # Eliminar usuario
                del data[user_id_str]
                
                # Guardar cambios
                with open("user_fantasy.json", "w") as f:
                    json.dump(data, f, indent=2)
                
                print(f"✅ Usuario {user_id_str} eliminado correctamente")
                
                # 3. Bloquear usuario
                await bloquear_usuario_fantasy(user_id_str)
                
                # 4. Notificaciones
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="❌ Has sido eliminado del Fantasy por inactividad de forma permanente",
                        parse_mode='HTML'
                    )
                    await context.bot.send_message(
                        chat_id=REGISTRO_MINIJUEGOS,
                        text=f"🗑️ Usuario {user_id_str} eliminado por inactividad",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"⚠️ Error en notificaciones: {e}")

            except Exception as e:
                print(f"❌ Error crítico al procesar eliminación: {e}")
                traceback.print_exc()

    except Exception as e:
        print(f"💥 ERROR GRAVE: {e}")
        traceback.print_exc()
async def bloquear_usuario_fantasy(user_id: str):
    """Bloquea a un usuario para que no pueda volver a registrarse"""
    try:
        bloqueados = {"bloqueados": [], "bloqueo_fantasy": []}
        
        if os.path.exists(USUARIOS_BLOQUEADOS_FILE):
            with open(USUARIOS_BLOQUEADOS_FILE, "r") as f:
                bloqueados = json.load(f)
        
        if "bloqueo_fantasy" not in bloqueados:
            bloqueados["bloqueo_fantasy"] = []
        
        if user_id not in bloqueados["bloqueo_fantasy"]:
            bloqueados["bloqueo_fantasy"].append(user_id)
            with open(USUARIOS_BLOQUEADOS_FILE, "w") as f:
                json.dump(bloqueados, f, indent=2)
            print(f"🔒 Usuario {user_id} bloqueado en fantasy")
            
    except Exception as e:
        print(f"❌ Error al bloquear usuario {user_id}: {str(e)}") 
        
           
# Añadir esta función para manejar la venta de jugadores
async def vender_jugador_handler(update: Update, context: CallbackContext):
    """Maneja el proceso de venta de jugadores por créditos"""
    user_id = str(update.effective_user.id)
    
    # Verificar si es mensaje o callback
    if update.callback_query:
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        message = update.message
    
    async with lock_fantasy:
        fantasy_data = await load_fantasy_data()
        
        # Verificar si el usuario tiene equipo
        if user_id not in fantasy_data or not fantasy_data[user_id].get('team', []):
            await message.reply_text("❌ No tienes jugadores para vender.")
            return
        
        # Crear lista de jugadores con botones
        keyboard = []
        for player in fantasy_data[user_id]['team']:
            valor_neto = player['value'] * (1 - MARKET_TAX)
            btn_text = f"💰 {player['name']} (Valor: {valor_neto:.0f} créditos)"
            callback_data = f'confirmar_venta_{player["id"]}'
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='mi_equipo')])
        
        await message.reply_text(
            "⚽ SELECCIONA JUGADOR PARA VENDER:\n\n"
            "Recibirás el 90% del valor de mercado en créditos",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Función para confirmar la venta
async def confirmar_venta_jugador(update: Update, context: CallbackContext):
    """Confirma y procesa la venta de un jugador"""
    query = update.callback_query
    await query.answer()
    player_id = query.data.split('_')[-1]
    user_id = str(query.from_user.id)
    
    async with lock_fantasy:
        fantasy_data = await load_fantasy_data()
        user_team = fantasy_data.get(user_id, {})
        
        # Buscar jugador en el equipo
        player_info = None
        for idx, player in enumerate(user_team.get('team', [])):
            if str(player['id']) == player_id:
                player_info = player
                player_index = idx
                break
        
        if not player_info:
            await query.edit_message_text("❌ Jugador no encontrado en tu equipo")
            return
        
        # Calcular créditos a recibir (con impuesto del 10%)
        creditos_recibidos = int(player_info['value'] * (1 - MARKET_TAX))
        
        # Actualizar datos
        user_team['credits'] += creditos_recibidos
        user_team['value'] -= player_info['value']
        user_team['team'].pop(player_index)
        
        # Guardar cambios
        await save_fantasy_data(fantasy_data)
        
        await query.edit_message_text(
            f"✅ VENTA REALIZADA!\n\n"
            f"Has vendido a {player_info['name']} por {creditos_recibidos} créditos\n"
            f"💎 Nuevos créditos: {user_team['credits']}"
        )

                 
  
                                                   
                                                                                                    
                                                                                                                                                     
                                                                                                                                                                                                                                 
import json
import os
from collections import defaultdict
import asyncio

# Archivos

USER_FANTASY_FILE = "user_fantasy.json"
RANKING_FILE = "ranking_semanal.json"
ESTADISTICAS_PREVIAS = "estadisticas_previas.json"

# Sistema de puntuación (ajustable)
SISTEMA_PUNTUACION = {
    "gol": 5,
    "asistencia": 3,
    "gol_encajado_portero": -1,
    "gol_encajado_defensa": -0.5,
    "tarjeta_amarilla": -1,
    "tarjeta_roja": -3,
    "porteria_cero_portero": 4,
    "porteria_cero_defensa": 2,
    "penalty_parado": 3,
    "penalty_fallado": -2,
    "falta_cometida": -0.3,
    "falta_recibida": 0.2,
    "pase_clave": 0.5,
    "intercepcion": 0.7,
    "tackle_exitoso": 0.6
}



def calcular_puntos_jugador(jugador_stats):
    """Calcula los puntos para un jugador basado en sus estadísticas"""
    if not jugador_stats:
        return 0

    posicion = jugador_stats.get("games", {}).get("position", "")
    puntos = 0

    # Función auxiliar para obtener valores numéricos seguros
    def safe_get(dic, *keys):
        for key in keys:
            if not isinstance(dic, dict):
                return 0
            dic = dic.get(key, {})
        return dic if isinstance(dic, (int, float)) else 0

    # Sistema de puntuación
    puntos += safe_get(jugador_stats, "goals", "total") * SISTEMA_PUNTUACION["gol"]
    puntos += safe_get(jugador_stats, "goals", "assists") * SISTEMA_PUNTUACION["asistencia"]
    
    # Goles encajados
    goles_concedidos = safe_get(jugador_stats, "goals", "conceded")
    if "Goalkeeper" in posicion:
        puntos += goles_concedidos * SISTEMA_PUNTUACION["gol_encajado_portero"]
    elif "Defender" in posicion:
        puntos += goles_concedidos * SISTEMA_PUNTUACION["gol_encajado_defensa"]

    # Tarjetas
    puntos += safe_get(jugador_stats, "cards", "yellow") * SISTEMA_PUNTUACION["tarjeta_amarilla"]
    puntos += safe_get(jugador_stats, "cards", "red") * SISTEMA_PUNTUACION["tarjeta_roja"]

    # Faltas
    puntos += safe_get(jugador_stats, "fouls", "committed") * SISTEMA_PUNTUACION["falta_cometida"]
    puntos += safe_get(jugador_stats, "fouls", "drawn") * SISTEMA_PUNTUACION["falta_recibida"]

    # Pases y defensa
    puntos += safe_get(jugador_stats, "passes", "key") * SISTEMA_PUNTUACION["pase_clave"]
    puntos += safe_get(jugador_stats, "tackles", "interceptions") * SISTEMA_PUNTUACION["intercepcion"]
    puntos += safe_get(jugador_stats, "tackles", "total") * SISTEMA_PUNTUACION["tackle_exitoso"]

    # Penaltis
    puntos += safe_get(jugador_stats, "penalty", "missed") * SISTEMA_PUNTUACION["penalty_fallado"]
    puntos += safe_get(jugador_stats, "penalty", "saved") * SISTEMA_PUNTUACION["penalty_parado"]

    # Portería a cero (solo si no encajó goles)
    if goles_concedidos == 0:
        if "Goalkeeper" in posicion:
            puntos += SISTEMA_PUNTUACION["porteria_cero_portero"]
        elif "Defender" in posicion:
            puntos += SISTEMA_PUNTUACION["porteria_cero_defensa"]

    return puntos




async def tarea_actualizacion_diaria(context: ContextTypes.DEFAULT_TYPE):
    """Tarea programada para actualización diaria de puntos y ranking"""
    print("\n⏰ INICIANDO ACTUALIZACIÓN DIARIA")
    
    # Paso 1: Actualizar puntos de los equipos
    if await actualizar_puntos_equipos(context):
        # Paso 2: (removido)
        # Paso 3: Notificar a los usuarios
        pass  # Aquí puedes agregar lógica adicional si es necesario

    print("✅ ACTUALIZACIÓN DIARIA COMPLETADA")
async def actualizar_puntos_equipos(context: ContextTypes.DEFAULT_TYPE):
    """Actualiza los puntos de los equipos y notifica con detalles por jugador"""
    try:
        # 1. Cargar datos necesarios
        with open(PLAYERS_FILE, 'r') as f:
            players_data = json.load(f)

        # Crear mapeo de estadísticas
        stats_map = {str(p["player"]["id"]): p["statistics"][0] if p["statistics"] else {} 
                   for p in players_data}

        # 2. Cargar ranking existente
        ranking_data = {"ranking": {}}
        if os.path.exists(RANKING_FILE):
            with open(RANKING_FILE, 'r') as f:
                ranking_data = json.load(f)

        # 3. Cargar datos fantasy
        fantasy_data = await load_fantasy_data()

        equipos_actualizados = 0

        for user_id, equipo in fantasy_data.items():
            if not isinstance(equipo, dict) or not equipo.get("team"):
                continue

            # Obtener puntos anteriores
            puntos_anteriores = ranking_data["ranking"].get(user_id, {}).get("puntos_equipo", 0)
            
            # Calcular nuevos puntos
            jugadores_puntos = []
            puntos_hoy = 0
            
            for jugador in equipo["team"]:
                if jugador.get("is_titular", False) and "id" in jugador:
                    jugador_id = str(jugador["id"])
                    puntos_jugador = calcular_puntos_jugador(stats_map.get(jugador_id, {}))
                    puntos_hoy += puntos_jugador
                    jugadores_puntos.append({
                        "nombre": jugador["name"],
                        "puntos": puntos_jugador,
                        "equipo": jugador.get("team", "Desconocido")
                    })

            # Calcular diferencia (puntos nuevos - puntos anteriores)
            diferencia_puntos = puntos_hoy - puntos_anteriores
            
            # Actualizar ranking
            nombre = await obtener_nombre_usuario(user_id)
            
            if user_id not in ranking_data["ranking"]:
                ranking_data["ranking"][user_id] = {
                    "nombre": nombre,
                    "puntos_torneos": 0,
                    "victorias_pvp": 0,
                    "derrotas_pvp": 0,
                    "torneos_jugados": 0,
                    "puntos_totales": 0
                }

            # Actualizar puntos (sumar solo la diferencia)
            ranking_data["ranking"][user_id]["puntos_equipo"] = puntos_hoy
            ranking_data["ranking"][user_id]["puntos_totales"] += diferencia_puntos
            ranking_data["ranking"][user_id]["nombre"] = nombre

            # Notificar usuario con detalles
            try:
                await notificar_actualizacion(
                    context, 
                    int(user_id), 
                    jugadores_puntos, 
                    diferencia_puntos, 
                    ranking_data["ranking"][user_id]["puntos_totales"]
                )
            except Exception as e:
                logging.warning(f"No se pudo notificar a {user_id}: {e}")

            equipos_actualizados += 1

        # Guardar cambios
        ranking_data["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(RANKING_FILE, 'w') as f:
            json.dump(ranking_data, f, indent=2)

        print(f"✅ Puntos actualizados para {equipos_actualizados} equipos")
        return True

    except Exception as e:
        print(f"❌ Error en actualizar_puntos_equipos: {str(e)}")
        return False

async def notificar_actualizacion(context: ContextTypes.DEFAULT_TYPE, user_id: int, 
                                jugadores_puntos: list, diferencia_puntos: int, 
                                puntos_totales: int):
    """Envía notificación detallada con puntos por jugador"""
    try:
        # Obtener nombre de usuario
        user_data = await load_data()
        nombre = user_data["usuarios"].get(str(user_id), {}).get("Nombre", f"Usuario {user_id}")
        
        # Construir mensaje de jugadores
        jugadores_msg = "\n".join(
            f"⚽ {j['nombre']} ({j['equipo']}): {j['puntos']} pts"
            for j in sorted(jugadores_puntos, key=lambda x: x['puntos'], reverse=True)
        )
        
        # Mensaje completo
        mensaje = f"""
📊 <b>ACTUALIZACIÓN DE PUNTOS - {datetime.now().strftime('%d/%m')}</b>

👋 Hola <b>{nombre}</b>, hoy tu equipo ha sumado:
⭐ <b>{diferencia_puntos} puntos nuevos</b>

<b>DESGLOSE POR JUGADOR:</b>
{jugadores_msg}

🏆 <b>TOTAL ACUMULADO:</b> {puntos_totales} pts

¡<i>❓ Este es el resumen de los puntos obtenidos según las estadísticas reales de tus jugadores</i>! 
"""
        # Enviar mensaje
        await context.bot.send_message(
            chat_id=user_id,
            text=mensaje,
            parse_mode='HTML'
        )
        return True
        
    except Exception as e:
        logging.error(f"Error notificando a {user_id}: {str(e)}")
        return False   
        





async def actualizar_jugadores(context: ContextTypes.DEFAULT_TYPE):
    print(f"⏳ Iniciando actualización de jugadores...")

    jugadores_actualizados = []

    for liga_id in LIGAS_IDS:
        print(f"\n{'='*50}")
        print(f"PROCESANDO LIGA ID: {liga_id}")
        print(f"{'='*50}")

        params_teams = {
            "league": liga_id,
            "season": TEMPORADA
        }

        response_teams = requests.get(API_URL_TEAMS, headers=headers, params=params_teams)
        if response_teams.status_code != 200:
            print(f"❌ Error al obtener equipos: {response_teams.status_code}")
            continue

        equipos = response_teams.json().get("response", [])
        print(f"✔️ Equipos encontrados: {len(equipos)}")

        for equipo in equipos:
            team_id = equipo["team"]["id"]
            team_name = equipo["team"]["name"]
            print(f"\n➡️ Procesando equipo: {team_name} (ID: {team_id})")

            pagina = 1
            tiene_mas_paginas = True

            while tiene_mas_paginas:
                params_players = {
                    "team": team_id,
                    "season": TEMPORADA,
                    "page": pagina
                }

                response_players = requests.get(API_URL_PLAYERS, headers=headers, params=params_players)
                if response_players.status_code != 200:
                    print(f"❌ Error al obtener jugadores: {response_players.status_code}")
                    break

                nuevos_jugadores = response_players.json().get("response", [])
                if not nuevos_jugadores:
                    break

                jugadores_actualizados.extend(nuevos_jugadores)
                print(f"✅ Página {pagina}: {len(nuevos_jugadores)} jugadores agregados")

                paginacion = response_players.json().get("paging", {})
                pagina_actual = paginacion.get("current", pagina)
                total_paginas = paginacion.get("total", pagina)

                if pagina_actual >= total_paginas:
                    tiene_mas_paginas = False
                else:
                    pagina += 1

                await asyncio.sleep(1)  # ✅ Usamos asyncio.sleep en vez de time.sleep

    # Guardar los datos (reemplazando el archivo anterior)
    with open(ARCHIVO_JSON, "w") as f:
        json.dump(jugadores_actualizados, f, indent=2)

    print(f"\n{'='*50}")
    print(f"🎉 TOTAL DE JUGADORES GUARDADOS: {len(jugadores_actualizados)}")
    print(f"📁 Archivo actualizado: {ARCHIVO_JSON}")
    print(f"{'='*50}")

    # Ejecutar tarea posterior
    await tarea_actualizacion_diaria(context)      