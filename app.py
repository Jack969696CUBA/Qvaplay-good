import asyncio
from threading import Lock
import sqlite3
import subprocess
import threading
import traceback
import aiohttp
import json
import os
import requests
import uuid
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from datetime import datetime, timedelta, time as dt_time
import secrets
from markupsafe import escape
from pyngrok import ngrok 
from flask import Flask, render_template, jsonify, request,redirect, session as flask_session, flash, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS 
import re
from necesario import lock_data, lock_apuestas, ejecutar_consulta_segura, obtener_registro, actualizar_registro, obtener_apuestas_usuario, eliminar_todas_apuestas_usuario, eliminar_apuesta_de_db, insertar_registro, guardar_apuesta_en_db

from juegopirata import MEJORAS_CONFIG, calcular_costo_mejora, calcular_piratas_requeridos, calcular_ganancia_mejora

from main import TOKEN, GROUP_CHAT_ADMIN, TEXTOS_METODOS, verificar_saldo_movil, verificar_enzona, verificar_mlc, verificar_pagomovil, marcar_transferencia_completada, actualizar_datos_usuario, REGISTRO_MINIJUEGOS


from werkzeug.security import generate_password_hash, check_password_hash
from bet import (
    obtener_eventos_futbol_live_all, 
    obtener_eventos_futbol,
    obtener_ligas_futbol,
    LIGAS_PRINCIPALES, 
    API_FUTBOL_KEY,
    modificar_cuota_individual,
    obtener_api,
    buscar_equipo_por_nombre_async,
    obtener_partidos_por_equipo,
    obtener_ligas,
    obtener_eventos_futbol,
    CONFIG_MERCADOS,
    MERCADOS_CON_POINT,
    obtener_mercados_reales,
    generar_id,
    CANAL_TICKET
    
)
from bolita import load_loteria


import pytz
DB_FILE = "user_data.db"
MERCADOS_FILE = "mercados.json"
# Tamaño máximo del archivo en bytes (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 megabytes
app = Flask(__name__)
app.secret_key = 'superperro@96_kj82hf9q02n3bA!@#87sd921'
# 🔥 ESTO ES LO MÁS IMPORTANTE 🔥
CORS(app, origins=['http://localhost', 'http://127.0.0.1'], supports_credentials=True)

from domino_online import setup_domino_sockets, domino_manager


socketio = SocketIO(app, cors_allowed_origins="*")


# Configuración
LIGAS_PRINCIPALES_IDS = list(LIGAS_PRINCIPALES.keys())


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
# Diccionario global que actúa como "context.user_data"
user_context = {
    "user_data": {}
}

futbol_cache = {
    "eventos": {},
    "ligas": {},    
    "last_updated": None
}

CACHE_TTL = 300  # 5 minutos



# Ruta principal del juego de Domino
@app.route('/index_domino')
def domino_page():
    return render_template('index_domino.html')  # Si está en templates/domino/

# Archivos CSS del juego
@app.route("/domino/CSS/<path:filename>")
def domino_css(filename):
    return send_from_directory("domino/CSS", filename)

# Archivos JS del juego
@app.route("/domino/JS/<path:filename>")
def domino_js(filename):
    return send_from_directory("domino/JS", filename)

# Archivos SVG del juego
@app.route("/domino/SVG/<path:filename>")
def domino_svg(filename):
    return send_from_directory("domino/SVG", filename)



@app.route('/depositar')
def pagina_depositar():
    """Página principal de depósitos"""
    if 'user_id' not in flask_session:
        return redirect('/login')
    
    return render_template('depositar.html')
    
@app.route('/retiros')
def pagina_retirar():
    """Página principal de depósitos"""
    if 'user_id' not in flask_session:
        return redirect('/login')
    
    return render_template('retiros.html')    



class DominoRoom:
    def __init__(self, room_id, creator_id, creator_name):
        self.room_id = room_id
        self.creator_id = creator_id
        self.creator_name = creator_name
        self.players = {}  # {user_id: {name, ready, position}}
        self.status = "waiting"  # waiting, playing, finished
        self.game_state = None
        self.max_players = 4
        self.created_at = datetime.now()
        self.lock = Lock()

    def add_player(self, user_id, user_name):
        with self.lock:
            if len(self.players) >= self.max_players:
                return False, "Sala llena"
            
            if user_id in self.players:
                return False, "Ya estás en la sala"
            
            position = len(self.players)
            self.players[user_id] = {
                'name': user_name,
                'ready': False,
                'position': position
            }
            return True, "Jugador añadido"

    def remove_player(self, user_id):
        with self.lock:
            if user_id in self.players:
                del self.players[user_id]
                # Reorganizar posiciones
                for i, (pid, player) in enumerate(self.players.items()):
                    player['position'] = i
                return True
            return False

    def set_ready(self, user_id, ready):
        with self.lock:
            if user_id in self.players:
                self.players[user_id]['ready'] = ready
                return True
            return False

    def all_players_ready(self):
        with self.lock:
            if len(self.players) < 2:  # Mínimo 2 jugadores
                return False
            return all(player['ready'] for player in self.players.values())

    def can_start_game(self):
        return self.all_players_ready() and len(self.players) >= 2

class DominoManager:
    def __init__(self):
        self.rooms = {}  # {room_id: DominoRoom}
        self.user_rooms = {}  # {user_id: room_id}
        self.lock = Lock()

    def create_room(self, creator_id, creator_name):
        with self.lock:
            room_id = f"room_{creator_id}_{int(datetime.now().timestamp())}"
            
            # Si el usuario ya tiene una sala, eliminarla
            if creator_id in self.user_rooms:
                old_room_id = self.user_rooms[creator_id]
                if old_room_id in self.rooms:
                    del self.rooms[old_room_id]
            
            room = DominoRoom(room_id, creator_id, creator_name)
            self.rooms[room_id] = room
            self.user_rooms[creator_id] = room_id
            
            # Añadir al creador a la sala
            room.add_player(creator_id, creator_name)
            
            return room_id

    def join_room(self, user_id, user_name, room_id):
        with self.lock:
            if room_id not in self.rooms:
                return False, "Sala no encontrada"
            
            room = self.rooms[room_id]
            
            # Si el usuario ya está en otra sala, sacarlo
            if user_id in self.user_rooms:
                old_room_id = self.user_rooms[user_id]
                if old_room_id in self.rooms and old_room_id != room_id:
                    self.rooms[old_room_id].remove_player(user_id)
            
            success, message = room.add_player(user_id, user_name)
            if success:
                self.user_rooms[user_id] = room_id
            return success, message

    def leave_room(self, user_id):
        with self.lock:
            if user_id not in self.user_rooms:
                return False
            
            room_id = self.user_rooms[user_id]
            if room_id in self.rooms:
                room = self.rooms[room_id]
                room.remove_player(user_id)
                
                # Si la sala queda vacía, eliminarla
                if len(room.players) == 0:
                    del self.rooms[room_id]
                # Si el creador abandona, asignar nuevo creador
                elif room.creator_id == user_id and room.players:
                    new_creator_id = next(iter(room.players.keys()))
                    room.creator_id = new_creator_id
                    room.creator_name = room.players[new_creator_id]['name']
            
            del self.user_rooms[user_id]
            return True

    def get_room(self, room_id):
        return self.rooms.get(room_id)

    def get_user_room(self, user_id):
        room_id = self.user_rooms.get(user_id)
        return self.rooms.get(room_id) if room_id else None

    def set_player_ready(self, user_id, ready):
        room = self.get_user_room(user_id)
        if room:
            return room.set_ready(user_id, ready)
        return False

# Inicializar el gestor de dominó
domino_manager = DominoManager()
@app.route('/api/domino/rooms', methods=['GET'])
def get_rooms():
    """Obtener lista de salas disponibles"""
    try:
        rooms_info = []
        for room_id, room in domino_manager.rooms.items():
            if room.status == "waiting":
                rooms_info.append({
                    'room_id': room_id,
                    'creator': room.creator_name,
                    'players_count': len(room.players),
                    'max_players': room.max_players,
                    'created_at': room.created_at.isoformat()
                })
        return jsonify({'success': True, 'rooms': rooms_info})
    except Exception as e:
        print(f"❌ Error obteniendo salas: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/domino/create_room', methods=['POST'])
def create_room():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'})
        
        room_id = domino_manager.create_room(user_id, session.get('user_name', 'Usuario'))
        print(f"✅ Sala creada: {room_id}")
        return jsonify({'success': True, 'room_id': room_id})
    except Exception as e:
        print(f"❌ Error creando sala: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/domino/join_room', methods=['POST'])
def join_room_http():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'})
        
        data = request.get_json()
        room_id = data.get('room_id')
        
        if not room_id:
            return jsonify({'success': False, 'error': 'ID de sala requerido'})
        
        success, message = domino_manager.join_room(
            user_id, 
            session.get('user_name', 'Usuario'), 
            room_id
        )
        
        if success:
            return jsonify({'success': True, 'room_id': room_id})
        else:
            return jsonify({'success': False, 'error': message})
            
    except Exception as e:
        print(f"❌ Error uniéndose a sala: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/domino/leave_room', methods=['POST'])
def leave_room():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'})
        
        success = domino_manager.leave_room(user_id)
        return jsonify({'success': success})
        
    except Exception as e:
        print(f"❌ Error abandonando sala: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/domino/my_room', methods=['GET'])
def get_my_room():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'})
        
        room = domino_manager.get_user_room(user_id)
        if room:
            room_info = {
                'room_id': room.room_id,
                'creator': room.creator_name,
                'players_count': len(room.players),
                'max_players': room.max_players,
                'players': room.players,
                'status': room.status
            }
            return jsonify({'success': True, 'room': room_info})
        else:
            return jsonify({'success': True, 'room': None})
            
    except Exception as e:
        print(f"❌ Error obteniendo mi sala: {e}")
        return jsonify({'success': False, 'error': str(e)})





@socketio.on('create_room')
def handle_create_room(data):
    user_id = flask_session.get('user_id')
    # ✅ Obtener el nombre REAL del usuario desde los datos de la sesión o de la API
    user_name = flask_session.get('user_name') or data.get('user_name') or 'Jugador'
    
    if not user_id:
        emit('error', {'message': 'No autenticado'})
        return
    
    print(f'📢 Solicitud de crear sala desde: {user_id} - {user_name}')
    
    room_id = domino_manager.create_room(user_id, user_name)
    room = domino_manager.get_room(room_id)
    
    # 🤖 Añadir 3 bots automáticamente
    bot_ids = [1001, 1002, 1003]
    bot_names = ['🤖 Bot Alice', '🤖 Bot Bob', '🤖 Bot Charlie']
    
    for bot_id, bot_name in zip(bot_ids, bot_names):
        success, message = room.add_player(bot_id, bot_name)
        if success:
            room.set_ready(bot_id, True)  # Bots siempre listos
            print(f'✅ {bot_name} añadido a la sala')
    
    print(f'🤖 Añadidos {len(bot_ids)} bots a la sala {room_id}')
    print(f'👥 Jugadores en sala: {room.players}')
    
    # Unir al usuario a la sala de Socket.IO
    join_room(room_id)
    
    emit('room_created', {
        'room_id': room_id,
        'players': room.players
    })
    
    # Notificar actualización a TODOS en la sala
    socketio.emit('room_updated', {
        'room_id': room_id,
        'players': room.players
    }, room=room_id)
    
    socketio.emit('rooms_updated')

@socketio.on('join_room')
def handle_join_room(data):
    user_id = flask_session.get('user_id')
    user_name = flask_session.get('user_name', 'Usuario')
    room_id = data.get('room_id')
    
    if not user_id:
        emit('error', {'message': 'No autenticado'})
        return
    
    success, message = domino_manager.join_room(user_id, user_name, room_id)
    
    if success:
        room = domino_manager.get_room(room_id)
        join_room(room_id)  # ✅ Unir al usuario a la sala de Socket.IO
        
        emit('joined_room', {
            'room_id': room_id,
            'players': room.players
        })
        
        # Notificar a otros jugadores en la sala
        socketio.emit('room_updated', {
            'room_id': room_id,
            'players': room.players
        }, room=room_id)
        
        # Notificar actualización de lista de salas
        socketio.emit('rooms_updated')
    else:
        emit('error', {'message': message})

@socketio.on('leave_room')
def handle_leave_room():
    user_id = flask_session.get('user_id')
    
    if not user_id:
        emit('error', {'message': 'No autenticado'})
        return
    
    room = domino_manager.get_user_room(user_id)
    if room:
        room_id = room.room_id
        domino_manager.leave_room(user_id)
        leave_room(room_id)  # ✅ Ahora funciona correctamente
        
        emit('left_room', {'room_id': room_id})
        
        # Notificar a los jugadores restantes
        if room_id in domino_manager.rooms:
            socketio.emit('room_updated', {
                'room_id': room_id,
                'players': domino_manager.rooms[room_id].players
            }, room=room_id)
        
        socketio.emit('rooms_updated')

@socketio.on('set_ready')
def handle_set_ready(data):
    user_id = flask_session.get('user_id')  # ✅ Usar flask_session
    ready = data.get('ready', False)
    
    if not user_id:
        emit('error', {'message': 'No autenticado'})
        return
    
    success = domino_manager.set_player_ready(user_id, ready)
    
    if success:
        room = domino_manager.get_user_room(user_id)
        if room:
            emit('ready_updated', {
                'user_id': user_id,
                'ready': ready
            })
            
            socketio.emit('room_updated', {
                'room_id': room.room_id,
                'players': room.players
            }, room=room.room_id)

@socketio.on('start_game')
def handle_start_game():
    user_id = flask_session.get('user_id')
    
    if not user_id:
        emit('error', {'message': 'No autenticado'})
        return
    
    room = domino_manager.get_user_room(user_id)
    if not room:
        emit('error', {'message': 'No estás en una sala'})
        return
    
    if room.creator_id != user_id:
        emit('error', {'message': 'Solo el creador puede iniciar el juego'})
        return
    
    if not room.can_start_game():
        emit('error', {'message': 'No se puede iniciar el juego. Verifica que todos estén listos'})
        return
    
    # Cambiar estado de la sala
    room.status = "playing"
    
    # 🎲 INICIALIZAR JUEGO DE DOMINÓ CON ESTADO COMPLETO
    game_state = {
        'room_id': room.room_id,
        'players': room.players,
        'jugadores': list(room.players.keys()),  # Lista de IDs de jugadores en orden
        'turno_actual': 0,  # El jugador en posición 0 empieza
        'jugador_actual': 0,
        'fichas_jugadores': {},  # Aquí irán las fichas de cada jugador
        'tablero': [],
        'estado': 'iniciado',
        'mano': 1,
        'puntos_equipo1': 0,
        'puntos_equipo2': 0
    }
    
    # 🎯 ASIGNAR FICHAS A LOS JUGADORES
    # Crear y barajar todas las fichas del dominó
    todas_las_fichas = []
    for i in range(7):
        for j in range(i, 7):
            todas_las_fichas.append((i, j))
    
    import random
    random.shuffle(todas_las_fichas)
    
    # Asignar 7 fichas a cada jugador
    jugadores_orden = list(room.players.keys())
    for idx, jugador_id in enumerate(jugadores_orden):
        fichas_jugador = todas_las_fichas[idx*7:(idx+1)*7]
        game_state['fichas_jugadores'][jugador_id] = [
            i for i in range(idx*7, (idx+1)*7)
        ]
    
    room.game_state = game_state
    
    print(f'🎮 Juego iniciado en sala {room.room_id}')
    print(f'📊 Estado del juego: {game_state}')
    
    socketio.emit('game_started', game_state, room=room.room_id)
    
    
@app.route('/api/retiros/solicitar', methods=['POST'])
async def api_solicitar_retiro():
    """Solicitar un retiro desde la web"""
    try:
        
        if 'user_id' not in flask_session:
            print("❌ No autenticado")
            return jsonify({'error': 'No autenticado'}), 401

        user_id = flask_session['user_id']
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se recibieron datos JSON'}), 400
            
        monto = data.get('monto')
        metodo = data.get('metodo')
        tarjeta = data.get('tarjeta', '')

        # Validaciones iniciales
        if not monto:
            return jsonify({'error': 'El monto es requerido'}), 400
            
        try:
            monto = float(monto)
        except (ValueError, TypeError):
            return jsonify({'error': 'El monto debe ser un número válido'}), 400

        if monto < 250 or monto > 5000:
            return jsonify({'error': 'Monto inválido. Mínimo: 250 CUP, Máximo: 5000 CUP'}), 400

        if not metodo:
            return jsonify({'error': 'El método es requerido'}), 400

        # Obtener datos del usuario
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Obtener balance y último retiro
        c.execute("SELECT Balance, UltimoRetiro, Nombre FROM usuarios WHERE id = ?", (user_id,))
        usuario_data = c.fetchone()
        
        if not usuario_data:
            conn.close()
            return jsonify({'error': 'Usuario no encontrado'}), 404

        balance_actual, ultimo_retiro_str, nombre_usuario = usuario_data

        # Validar balance
        if monto > balance_actual:
            conn.close()
            return jsonify({'error': f'Balance insuficiente. Balance actual: {balance_actual} CUP'}), 400

        # Validar último retiro (1 por día)
        if ultimo_retiro_str:
            try:
                ultimo_retiro = datetime.strptime(ultimo_retiro_str, '%Y-%m-%d %H:%M:%S')
                tiempo_transcurrido = datetime.now() - ultimo_retiro
                if tiempo_transcurrido.total_seconds() < 86400:
                    tiempo_restante = timedelta(seconds=86400) - tiempo_transcurrido
                    horas, resto = divmod(int(tiempo_restante.total_seconds()), 3600)
                    minutos = resto // 60
                    conn.close()
                    return jsonify({
                        'error': f'Ya realizaste un retiro hoy. Podrás retirar nuevamente en: {horas:02d}:{minutos:02d}'
                    }), 400
            except ValueError as e:
                print(f"⚠️ Error parseando fecha: {e}")
                # Continuar si hay error en la fecha

        # Obtener datos de depósito
        c.execute("SELECT Payment, telefono, TotalDeposit, TotalRetiro FROM depositos WHERE id = ?", (user_id,))
        deposito_data = c.fetchone()
        metodo_pago = deposito_data[0] if deposito_data else "No especificado"
        telefono = deposito_data[1] if deposito_data else None
        total_depositado = deposito_data[2] if deposito_data else 0
        total_retirado = deposito_data[3] if deposito_data else 0

       

        # Actualizar balance y registrar último retiro
        nuevo_balance = balance_actual - monto
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Actualizar usuario
        c.execute(
            "UPDATE usuarios SET Balance = ?, UltimoRetiro = ? WHERE id = ?",
            (nuevo_balance, fecha_actual, user_id)
        )

        # Actualizar datos de retiro en depositos
        nuevo_total_retirado = total_retirado + monto
        c.execute(
            "UPDATE depositos SET TotalRetiro = ?, RetiroPendiente = ? WHERE id = ?",
            (nuevo_total_retirado, monto, user_id)
        )

        conn.commit()
        conn.close()

        # Preparar detalles para el mensaje
        detalles = f"💳 Tarjeta: {tarjeta}" if metodo == 'tarjeta' else f"📱 Teléfono: {telefono}"

        # Calcular ganancia/pérdida
        ganancia_perdida = total_depositado - total_retirado

        # Notificación al administrador
        mensaje_admin = (
            f"<pre>⚠️ NUEVA SOLICITUD DE RETIRO (WEB)</pre>\n\n"
            f"▫️ <b>Usuario:</b> {nombre_usuario}\n"
            f"▫️ <b>ID:</b> <code>{user_id}</code>\n"
            f"▫️ <b>Monto:</b> {monto:.2f} CUP\n"
            f"▫️ <b>Método:</b> {metodo_pago.upper()}\n"
            f"▫️ <b>Tipo:</b> {metodo.replace('_', ' ').title()}\n"
            f"▫️ <b>Detalles:</b> <code>{detalles}</code>\n\n"
            f"📊 <b>Estadísticas del usuario:</b>\n"
            f"├ Balance anterior: {balance_actual:.2f} CUP\n"
            f"├ Nuevo balance: {nuevo_balance:.2f} CUP\n"
            f"├ Total depositado: {total_depositado:.2f} CUP\n"
            f"├ Total retirado: {nuevo_total_retirado:.2f} CUP\n"
            f"└ Ganancia/Pérdida: {ganancia_perdida - monto:.2f} CUP\n\n"
            f"🕒 <i>Hora de solicitud:</i> {fecha_actual}"
        )

        # Botones de aprobación
        keyboard = [
            [InlineKeyboardButton("✅ Aprobar Retiro", callback_data=f"aprobar_retiro_{user_id}")],
            [InlineKeyboardButton("❌ Rechazar Retiro", callback_data=f"rechazar_retiro_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Enviar mensaje al canal de administración
        try:
            await enviar_mensaje_al_canal(
                TOKEN, 
                GROUP_CHAT_ADMIN, 
                mensaje_admin, 
                reply_markup=reply_markup
            )
         
        except Exception as e:
            print(f"⚠️ Error enviando a Telegram: {e}")

        return jsonify({
            'success': True,
            'monto': monto,
            'metodo': metodo_pago.upper(),
            'detalles': detalles,
            'nuevo_balance': nuevo_balance,
            'fecha': fecha_actual
        })

    except Exception as e:
        print(f"❌ Error en api_solicitar_retiro: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@app.route('/api/deposito/info')
async def api_deposito_info():
    """Obtiene información del usuario para depósitos"""
    try:
        if 'user_id' not in flask_session:
            return jsonify({'error': 'No autenticado'}), 401

        user_id = flask_session['user_id']
        
        # Verificar si tiene teléfono registrado
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT telefono FROM depositos WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()

        tiene_telefono = bool(row and row[0])
        
        return jsonify({
            'tiene_telefono': tiene_telefono,
            'telefono': row[0] if tiene_telefono else None,
            'metodos_pago': TEXTOS_METODOS
        })

    except Exception as e:
        print(f"❌ Error en api_deposito_info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/registrar-telefono', methods=['POST'])
async def api_registrar_telefono():
    """Registra el teléfono del usuario"""
    try:
        
        if 'user_id' not in flask_session:
            print(f"❌ [DEBUG] Usuario no autenticado")
            return jsonify({'error': 'No autenticado'}), 401

        user_id = flask_session['user_id']
        
        
        data = request.get_json()
        
        
        telefono = data.get('telefono', '').strip()
        

        # Validar formato del teléfono
        if not telefono.isdigit() or len(telefono) not in (8, 9):
            
            return jsonify({'error': 'Formato inválido. Ingresa un número de 8 dígitos'}), 400

        # Verificar si ya existe un registro para este usuario
        
        registro_existente = obtener_registro('depositos', user_id)
        
        
        if registro_existente:
            
            # Actualizar teléfono existente
            actualizado = actualizar_registro('depositos', user_id, {'telefono': telefono})
            
            if not actualizado:
                print(f"❌ [DEBUG] Error al actualizar teléfono")
                return jsonify({'error': 'Error al actualizar teléfono'}), 500
            else:
                print(f"✅ [DEBUG] Teléfono actualizado exitosamente")
        else:
          
            # Insertar nuevo registro
            nuevo_registro = {
                'id': user_id,
                'nombre': 'Usuario',
                'telefono': telefono,
                'Payment': 0,
                'Amount': 0,
                'TotalDeposit': 0
            }
          
            insertado = insertar_registro('depositos', nuevo_registro)
         
            if not insertado:
                print(f"❌ [DEBUG] Error al insertar teléfono")
                return jsonify({'error': 'Error al registrar teléfono'}), 500
            else:
                print(f"api_registrar_telefono")
                
        return jsonify({'success': True, 'message': 'Teléfono registrado correctamente'})

    except Exception as e:
        print(f"❌ [DEBUG] Error en api_registrar_telefono: {str(e)}")
        import traceback
        print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/deposito/verificar', methods=['POST'])
async def api_verificar_deposito():
    """Verifica un depósito usando la lógica real del bot"""
    try:
        if 'user_id' not in flask_session:
            return jsonify({'error': 'No autenticado'}), 401

        user_id = flask_session['user_id']
        data = request.get_json()
        metodo_pago = data.get('metodo_pago')
        
        # Obtener teléfono y nombre del usuario
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT telefono, nombre FROM depositos WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()

        if not row or not row[0]:
            return jsonify({'error': 'No se encontró el número de teléfono asociado a tu cuenta'}), 400

        telefono = row[0]
        user_name = row[1] if row[1] else "Usuario Web"
        
        # Diccionario de verificadores
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
            return jsonify({'error': f'Método de pago no soportado: {metodo_pago}'}), 400
        
        metodo_nombre, verificador = verificadores[metodo_pago]
        
        # Ejecutar verificación con tiempo de espera
        try:
            resultado = await asyncio.wait_for(verificador(telefono), timeout=30)
            detalles_verificacion = resultado.get('detalles', "Sin detalles adicionales")
            monto_encontrado = resultado.get('monto', 0)
        except asyncio.TimeoutError:
            # Reportar timeout como fallo
            await enviar_reporte_fallo_web(
                user_id, user_name, metodo_pago, 0, telefono,
                "Timeout: Tiempo de espera agotado al verificar"
            )
            return jsonify({'error': 'Tiempo de espera agotado al verificar el depósito'}), 408
        
        if not resultado['encontrado']:
            # REPORTAR FALLO AL CANAL
            await enviar_reporte_fallo_web(
                user_id, user_name, metodo_pago, 0, telefono,
                detalles_verificacion
            )
            return jsonify({
                'error': 'No se encontró el depósito',
                'detalles': detalles_verificacion
            }), 404
        
        # Proceso de marcado como completado
        marcado_ok = await marcar_transferencia_completada(
            resultado['seccion'],
            resultado['transferencia'],
            user_id
        )
        
        if not marcado_ok:
            await enviar_reporte_fallo_web(
                user_id, user_name, metodo_pago, monto_encontrado, telefono,
                "Error al marcar transferencia como completada"
            )
            return jsonify({
                'error': 'Transferencia verificada pero no se pudo marcar como completada'
            }), 500
        
        # Actualizar datos del usuario
        update_result = await actualizar_datos_usuario(user_id, metodo_pago, monto_encontrado)
        
        if not update_result.get('success'):
            await enviar_reporte_fallo_web(
                user_id, user_name, metodo_pago, monto_encontrado, telefono,
                f"Error actualizando saldo: {update_result.get('error', 'Sin detalles')}"
            )
            return jsonify({
                'error': 'Error actualizando saldo del usuario',
                'detalles': update_result.get('error', 'Sin detalles')
            }), 500
        
        # ENVIAR REPORTE EXITOSO AL CANAL
        await enviar_reporte_exitoso_web(
            user_id, user_name, metodo_pago, monto_encontrado, 
            telefono, detalles_verificacion, resultado['seccion'],
            update_result
        )
        
        # Preparar respuesta exitosa
        bono = round(float(monto_encontrado) * 0.20, 2)  # 20% de bono
        if metodo_pago == 'saldo_movil':
            monto_aplicado = monto_encontrado * 3  # +200% para saldo móvil
        else:
            monto_aplicado = monto_encontrado * 1.10  # +10% para otros métodos
        
        return jsonify({
            'success': True,
            'monto_verificado': monto_encontrado,
            'bono_recibido': bono,
            'monto_aplicado': monto_aplicado,
            'nuevo_balance': update_result['new_values']['balance'],
            'detalles': detalles_verificacion
        })

    except Exception as e:
        print(f"❌ Error en api_verificar_deposito: {str(e)}")
        
        # Reportar error interno como fallo
        try:
            user_name = "Usuario Web"
            telefono = "No disponible"
            await enviar_reporte_fallo_web(
                user_id, user_name, metodo_pago, 0, telefono,
                f"Error interno: {str(e)}"
            )
        except:
            pass
            
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

# Función auxiliar para enviar reportes exitosos en la web
async def enviar_reporte_exitoso_web(user_id, user_name, metodo_pago, monto_verificado, telefono, detalles, seccion, update_data):
    """Versión web del reporte exitoso - ENVÍA A TELEGRAM"""
    try:
        cambios_texto = (
            f"💵 Balance: {update_data['old_values']['balance']} → {update_data['new_values']['balance']} CUP\n"
            f"📊 Total depositado: {update_data['old_values']['TotalDeposit']} → {update_data['new_values']['TotalDeposit']} CUP\n"
            f"🎁 Bono: {update_data['old_values']['bono']} → {update_data['new_values']['bono']} CUP\n"
            f"🔄 Rollover: {update_data['old_values']['rollover']} → {update_data['new_values']['rollover']} CUP"
        )
        
        mensaje_canal = (
            f"<pre>✅ DEPÓSITO VERIFICADO (WEB)</pre>\n\n"
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
        
        # ENVÍO REAL AL CANAL DE TELEGRAM
        await enviar_mensaje_al_canal(TOKEN, GROUP_CHAT_ADMIN, mensaje_canal)
        
    except Exception as e:
        print(f"Error enviando reporte web a Telegram: {e}")

# Función auxiliar para reportes de fallo en web
async def enviar_reporte_fallo_web(user_id, user_name, metodo_pago, monto, telefono, motivo):
    """Versión web del reporte de fallo - ENVÍA A TELEGRAM"""
    try:
        if "No se encontró transferencia desde el teléfono" in motivo:
            motivo_formateado = f"El teléfono {telefono} no tiene transferencias registradas por {TEXTOS_METODOS.get(metodo_pago, {}).get('nombre', metodo_pago)}"
        elif "Error en verificación" in motivo:
            motivo_formateado = f"Error técnico al verificar: {motivo.split(':')[-1].strip()}"
        else:
            motivo_formateado = motivo

        mensaje_canal = (
            f"<pre>❌ DEPÓSITO FALSO RECHAZADO (WEB)</pre>\n\n"
            f"👤 Usuario: {user_name} (ID: <code>{user_id}</code>)\n"
            f"🏦 Método: {TEXTOS_METODOS.get(metodo_pago, {}).get('nombre', metodo_pago)}\n"
            f"📱 Teléfono: <code>{telefono}</code>\n"
            f"📛 Motivo: {motivo_formateado}\n"
            f"🕒 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # ENVÍO REAL AL CANAL DE TELEGRAM
        await enviar_mensaje_al_canal(TOKEN, REGISTRO_MINIJUEGOS, mensaje_canal)
        
    except Exception as e:
        print(f"Error enviando reporte de fallo web a Telegram: {e}")


@app.before_request
def before_request():
    """Middleware mejorado para capturar user_id y redirigir si es necesario"""
    user_id = request.args.get('user_id')
    
    if user_id:
        session['user_id'] = user_id
        flask_session['user_id'] = user_id  # Ambas formas
        session.permanent = True
        
        # Si estamos en la raíz y tenemos user_id, redirigir al endpoint solicitado
        current_path = request.path
        
        # Si el path es solo "/" y tenemos user_id, redirigir a main
        if current_path == '/' and user_id:
            return redirect('/index')
        
        # Si llegamos aquí, el usuario ya está en la ruta correcta
        # solo necesitamos procesar la página normalmente
        
        
# Modificar la ruta del admin panel para usar el tracking real
@app.route('/admin')
async def admin_panel():
    # Verificar si el usuario es el administrador
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        flash('Acceso denegado. Solo administradores pueden acceder.', 'error')
        return redirect(url_for('index'))
    
    # Cargar datos de forma asíncrona
    user_data = await load_data()
    apuestas = await cargar_apuestas()
    
    # Obtener usuarios en línea REALES
    usuarios_en_linea_ids = obtener_usuarios_en_linea()
    usuarios_online_count = len(usuarios_en_linea_ids)
    
    # Obtener información detallada de los usuarios en línea
    usuarios_en_linea_detalles = {}
    for user_id in usuarios_en_linea_ids:
        if user_id in user_data['usuarios']:
            usuarios_en_linea_detalles[user_id] = user_data['usuarios'][user_id]
    
    # Obtener nombres de usuarios para mostrar en lugar de IDs
    usuarios_dict = user_data['usuarios']
    bono_apuesta_dict = user_data.get('Bono_apuesta', {})
    
    # Calcular estadísticas
    total_usuarios = len(usuarios_dict)
    
    # Balance total
    balance_total = sum(usuario.get('Balance', 0) for usuario in usuarios_dict.values())
    
    # Balance en apuestas pendientes
    balance_apuestas_pendientes = sum(apuesta['monto'] for apuesta in apuestas if apuesta['estado'] == '⌛Pendiente')
    
    return render_template('admin.html', 
                         usuarios=usuarios_dict,
                         bono_apuesta=bono_apuesta_dict,
                         usuarios_en_linea=usuarios_en_linea_detalles,
                         total_usuarios=total_usuarios,
                         usuarios_online=usuarios_online_count,
                         balance_total=balance_total,
                         balance_apuestas_pendientes=balance_apuestas_pendientes,
                         apuestas=apuestas)

# Agregar una ruta para obtener estadísticas en tiempo real
@app.route('/admin/estadisticas_tiempo_real')
async def admin_estadisticas_tiempo_real():
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    # Obtener estadísticas en tiempo real
    usuarios_en_linea = obtener_usuarios_en_linea()
    
    # Cargar datos adicionales
    user_data = await load_data()
    apuestas = await cargar_apuestas()
    
    # Calcular estadísticas
    balance_total = sum(usuario.get('Balance', 0) for usuario in user_data['usuarios'].values())
    balance_apuestas_pendientes = sum(apuesta['monto'] for apuesta in apuestas if apuesta['estado'] == '⌛Pendiente')
    
    return jsonify({
        'success': True,
        'usuarios_online': len(usuarios_en_linea),
        'balance_total': balance_total,
        'balance_apuestas_pendientes': balance_apuestas_pendientes,
        'usuarios_en_linea_ids': list(usuarios_en_linea.keys())
    })
@app.route('/admin/actualizar_balance', methods=['POST'])
async def admin_actualizar_balance():
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    user_id = request.form.get('user_id')
    nuevo_balance = request.form.get('balance')
    
    if not user_id or not nuevo_balance:
        return jsonify({'success': False, 'message': 'Datos incompletos'})
    
    try:
        nuevo_balance = float(nuevo_balance)
    except ValueError:
        return jsonify({'success': False, 'message': 'El balance debe ser un número válido'})
    
    # Cargar y actualizar datos de forma asíncrona
    async with lock_data:
        data = await load_data()
        if user_id not in data['usuarios']:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})
        
        data['usuarios'][user_id]['Balance'] = nuevo_balance
        await save_data(data)
    
    return jsonify({'success': True, 'message': 'Balance actualizado correctamente'})

@app.route('/admin/actualizar_bono', methods=['POST'])
async def admin_actualizar_bono():
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    user_id = request.form.get('user_id')
    nuevo_bono = request.form.get('bono')
    
    if not user_id or not nuevo_bono:
        return jsonify({'success': False, 'message': 'Datos incompletos'})
    
    try:
        nuevo_bono = float(nuevo_bono)
    except ValueError:
        return jsonify({'success': False, 'message': 'El bono debe ser un número válido'})
    
    # Cargar y actualizar datos de forma asíncrona
    async with lock_data:
        data = await load_data()
        if user_id not in data.get('Bono_apuesta', {}):
            # Crear entrada si no existe
            if 'Bono_apuesta' not in data:
                data['Bono_apuesta'] = {}
            data['Bono_apuesta'][user_id] = {
                "Bono": 0,
                "Rollover_requerido": 0,
                "Rollover_actual": 0,
                "Bono_retirable": 0
            }
        data['Bono_apuesta'][user_id]['Bono'] = nuevo_bono
        await save_data(data)
    
    return jsonify({'success': True, 'message': 'Bono actualizado correctamente'})

@app.route('/admin/eliminar_apuesta', methods=['POST'])


async def admin_eliminar_apuesta():
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    apuesta_id = request.form.get('apuesta_id')
    
    if not apuesta_id:
        return jsonify({'success': False, 'message': 'ID de apuesta no proporcionado'})
   
    apuestas = await cargar_apuestas()
        
        # Buscar y eliminar la apuesta
    apuestas_actualizadas = [apuesta for apuesta in apuestas if apuesta.get('id_ticket') != apuesta_id]
        
        # Guardar apuestas actualizadas
    await guardar_apuestas(apuestas_actualizadas)
    
    return jsonify({'success': True, 'message': 'Apuesta eliminada correctamente'})

@app.route('/admin/buscar_apuestas', methods=['GET'])

async def admin_buscar_apuestas():
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'ID de usuario no proporcionado'})
    
    # Cargar apuestas de forma asíncrona
    apuestas = await cargar_apuestas()
    
    # Filtrar apuestas por usuario
    apuestas_usuario = [apuesta for apuesta in apuestas if apuesta.get('usuario_id') == user_id]
    
    return jsonify({'success': True, 'apuestas': apuestas_usuario})

@app.route('/admin/detalles_usuario/<user_id>')

async def admin_detalles_usuario(user_id):
    if 'user_id' not in flask_session or flask_session['user_id'] != '7031172659':
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    # Cargar datos de forma asíncrona
    data = await load_data()
    
    if user_id not in data['usuarios']:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'})
    
    usuario = data['usuarios'][user_id]
    bono_info = data.get('Bono_apuesta', {}).get(user_id, {})
    deposito_info = data.get('depositos', {}).get(user_id, {})
    
    # Obtener apuestas del usuario
    apuestas = await cargar_apuestas()
    apuestas_usuario = [apuesta for apuesta in apuestas if apuesta.get('usuario_id') == user_id]
    
    # Calcular estadísticas de apuestas
    apuestas_ganadas = sum(1 for a in apuestas_usuario if a.get('estado') == '✅ Ganada')
    apuestas_perdidas = sum(1 for a in apuestas_usuario if a.get('estado') == '❌ Perdida')
    apuestas_pendientes = sum(1 for a in apuestas_usuario if a.get('estado') == '⌛Pendiente')
    
    return jsonify({
        'success': True,
        'usuario': usuario,
        'bono_info': bono_info,
        'deposito_info': deposito_info,
        'estadisticas_apuestas': {
            'total': len(apuestas_usuario),
            'ganadas': apuestas_ganadas,
            'perdidas': apuestas_perdidas,
            'pendientes': apuestas_pendientes
        }
    })



@app.context_processor
def inject_leagues():
    return dict(LIGAS_PRINCIPALES=LIGAS_PRINCIPALES)




@app.route('/')
def home():
    if 'user_id' not in flask_session:
        return redirect('/login')
    return redirect('/index')
    
@app.route('/index')
def index():
    if 'user_id' not in flask_session:
        return redirect('/login')
    return render_template('index.html')    
    

    
@app.route('/mi_cuenta')
def mi_cuenta():
    return render_template('mi_cuenta.html')
        
@app.route('/crash.html')
def crash_game():
    return render_template('crash.html') 
       
@app.route('/minijuegos')
def minijuegos():
    return render_template('minijuegos.html')
  
@app.route('/prematch')
def prematch_events():
    return render_template('prematch.html')
 
@app.route("/logout")
def logout():
    flask_session.pop('user_id', None)
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))    
    
USER_DATA_FILE = 'user_data.json'

from flask import session
import secrets
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validaciones básicas
        if not all([user_id, username, email, password, confirm_password]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template("register.html")
            
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template("register.html")
        
        # Validar formato de user_id (debe ser numérico)
        if not user_id.isdigit():
            flash('El ID de usuario debe ser numérico', 'error')
            return render_template("register.html")
            
        # Validar formato de email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Por favor ingresa un email válido', 'error')
            return render_template("register.html")
        
        # Verificar en la base de datos
        try:
            # Verificar si el email ya está registrado en OTRO usuario
            consulta_email = "SELECT id FROM usuarios WHERE Email = ? AND id != ?"
            resultado_email = ejecutar_consulta_segura(consulta_email, (email.lower(), user_id), obtener_resultados=True)
            
            if resultado_email:
                flash('Este email ya tiene una cuenta asociada', 'error')
                return render_template("register.html")
            
            # Verificar si el user_id existe en la base de datos
            usuario = obtener_registro("usuarios", user_id, "nombre, Username, Email, RegistroCompleto")
            
            if usuario:
                nombre, db_username, db_email, registro_completo = usuario
                
                # Verificar si ya tiene registro completo
                if registro_completo:
                    flash('Este usuario ya tiene una cuenta registrada. Inicia sesión.', 'error')
                    return redirect(url_for('login'))
                
                # Si existe pero no tiene registro completo, guardar datos en DB temporal
                exito = actualizar_registro("usuarios", user_id, {
                    'Username_temp': username,
                    'Email_temp': email,
                    'Password_temp': generate_password_hash(password),
                    'RegistroPendiente': True
                })
                
                if not exito:
                    flash('Error al guardar datos temporales', 'error')
                    return render_template("register.html")
                
            else:
                # Si NO existe el user_id, mostrar error
                flash(f'El ID {user_id} no está registrado. Por favor inicia primero con el bot de Telegram @QvaPlay_bot usando el comando /start', 'error')
                return render_template("register.html", user_id_not_found=True, user_id=user_id)
            
        except Exception as e:
            print(f"Error en register: {e}")
            flash('Error interno del sistema', 'error')
            return render_template("register.html")
        
        # GENERAR CÓDIGO DE VERIFICACIÓN Y GUARDAR EN DB
        verification_code = secrets.randbelow(900000) + 100000
        expiration_time = datetime.now() + timedelta(minutes=10)
        
        # Guardar código en base de datos en lugar de sesión
        exito = actualizar_registro("usuarios", user_id, {
            'VerificationCode': str(verification_code),
            'VerificationExpiry': expiration_time.isoformat()
        })
        
        if not exito:
            flash('Error al guardar código de verificación', 'error')
            return render_template("register.html")
        
        # Guardar solo el ID en la sesión (muy pequeño)
        session['pending_user_id'] = user_id
        
        # Enviar código de verificación por Telegram
        if enviar_mensaje_verificacion(user_id, verification_code):
            flash('Código de verificación enviado a tu cuenta de Telegram', 'success')
            return redirect(url_for('register_verify'))
        else:
            flash('Error al enviar el código de verificación. Intenta nuevamente.', 'error')
            return render_template("register.html")
    
    # Para GET requests, mostrar el formulario
    user_id_not_found = request.args.get('user_id_not_found', False)
    user_id = request.args.get('user_id', '')
    
    return render_template("register.html", user_id_not_found=user_id_not_found, user_id=user_id)

@app.route("/register/verify", methods=["GET", "POST"])
def register_verify():
    if 'pending_user_id' not in session:
        flash('No hay registro pendiente de verificación', 'error')
        return redirect(url_for('register'))

    user_id = session['pending_user_id']

    try:
        # Obtener datos de verificación desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id, 
                                      "VerificationCode, VerificationExpiry, Username_temp, Email_temp, Password_temp")
        
        if not usuario_data or not usuario_data[0] or not usuario_data[1]:
            session.pop('pending_user_id', None)
            flash('Registro pendiente no encontrado o expirado', 'error')
            return redirect(url_for('register'))

        verification_code_db, expiry_db, username_temp, email_temp, password_temp = usuario_data

        # Verificar si el código expiró
        expiration_time = datetime.fromisoformat(expiry_db)
        if datetime.now() > expiration_time:
            # Limpiar datos temporales
            actualizar_registro("usuarios", user_id, {
                'VerificationCode': None,
                'VerificationExpiry': None,
                'Username_temp': None,
                'Email_temp': None,
                'Password_temp': None,
                'RegistroPendiente': False
            })
            session.pop('pending_user_id', None)
            flash('El código de verificación ha expirado. Por favor regístrate nuevamente.', 'error')
            return redirect(url_for('register'))

        if request.method == "POST":
            verification_code = request.form.get('verification_code')

            if not verification_code:
                flash('Por favor ingresa el código de verificación', 'error')
                return render_template("register_verify.html", user_id=user_id)

            if verification_code != verification_code_db:
                flash('Código de verificación incorrecto', 'error')
                return render_template("register_verify.html", user_id=user_id)

            # CÓDIGO CORRECTO - COMPLETAR REGISTRO
            campos_actualizar = {
                'Username': username_temp,
                'Email': email_temp,
                'Password': password_temp,
                'RegistroCompleto': True,
                'FechaRegistro': datetime.now().isoformat(),
                # Limpiar campos temporales
                'VerificationCode': None,
                'VerificationExpiry': None,
                'Username_temp': None,
                'Email_temp': None,
                'Password_temp': None,
                'RegistroPendiente': False
            }

            exito = actualizar_registro("usuarios", user_id, campos_actualizar)
            if not exito:
                flash('Error al completar el registro. Intenta nuevamente.', 'error')
                return render_template("register_verify.html", user_id=user_id)

            # Limpiar sesión
            session.pop('pending_user_id', None)

            # Iniciar sesión automáticamente
            flask_session['user_id'] = user_id
            flash('¡Registro completado exitosamente!', 'success')
            return redirect(url_for('index'))

    except Exception as e:
        print(f"Error en register_verify: {e}")
        flash('Error interno del sistema. Por favor intenta nuevamente.', 'error')
        return redirect(url_for('register'))

    return render_template("register_verify.html", user_id=user_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validaciones
        if not all([username, password]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template("login.html")
        
        # Buscar usuario en la base de datos
        try:
            consulta = """
                SELECT id, nombre, Username, Email, Password, RegistroCompleto 
                FROM usuarios 
                WHERE Username = ? OR Email = ?
            """
            resultado = ejecutar_consulta_segura(consulta, (username, username), obtener_resultados=True)
            
            if resultado:
                user_id, nombre, db_username, db_email, db_password, registro_completo = resultado[0]
                
                # Verificar contraseña y registro completo
                if db_password and check_password_hash(db_password, password):
                    if not registro_completo:
                        flash('Por favor completa tu registro primero', 'error')
                        return render_template("login.html")
                    
                    flask_session['user_id'] = user_id
                    flash('Inicio de sesión exitoso', 'success')
                    return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Error en login: {e}")
            flash('Error interno del sistema', 'error')
            return render_template("login.html")
        
        flash('Credenciales incorrectas', 'error')
        return render_template("login.html")
    
    return render_template("login.html")
    
def enviar_mensaje_verificacion(user_id, verification_code):
    """
    Envía un mensaje de verificación al usuario a través del bot de Telegram (HTML mode)
    """
    try:
        mensaje = (
            "<b>🔐 Código de Verificación QvaPlay</b>\n\n"
            f"Tu código de verificación es: <code>{escape(str(verification_code))}</code>\n\n"
            "Este código expirará en 10 minutos. "
            "Si no solicitaste este código, por favor ignora este mensaje."
        )

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": user_id,
            "text": mensaje,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json().get("ok", False)

    except Exception as e:
        print(f"Error enviando mensaje de verificación: {e}")
        return False
        


@app.route('/api/verificar-autenticacion')
def verificar_autenticacion():
    if 'user_id' in flask_session:
        user_id = flask_session['user_id']
        print(f"✅ Usuario autenticado en sesión: {user_id}")
        return jsonify({'autenticado': True, 'user_id': user_id})
    
    print("❌ Usuario no autenticado en sesión")
    return jsonify({'autenticado': False})
    
@app.route('/api/user-info')
async def user_info():
    if 'user_id' not in flask_session:
        return jsonify({'error': 'No autenticado'}), 401

    user_id = flask_session['user_id']
    user = await obtener_datos_usuario(user_id)

    if user:
        return jsonify({
            'user_id': user.get('user_id'),
            'nombre': user.get('nombre'), 
            'email': user.get('Email', ''),
            'password': user.get('Password', ''),
            'balance': user.get('balance', 0),
            'bono': user.get('bono', 0),
            'referido_por': user.get('referido_por'),
            'referidos': user.get('referidos', 0),
            'total_ganado_ref': user.get('total_ganado_ref', 0),
            'medalla': user.get('medalla', 'Sin medalla'),
            'rollover_requerido': user.get('rollover_requerido', 0),
            'rollover_actual': user.get('rollover_actual', 0),
            'bono_retirable': user.get('bono_retirable', 0)
        })

    return jsonify({'error': 'Usuario no encontrado'}), 404

    
@app.route('/api/debug-session')
def debug_session():
    return jsonify(dict(flask_session))            
    
@app.route('/leagues')
def leagues():
    return render_template('leagues.html')

@app.route('/events/<int:league_id>')
def league_events(league_id):
    return render_template('events.html', league_id=league_id)

@app.route('/bet/<event_id>')
def bet_event(event_id):
    return render_template('bets.html', event_id=event_id)


@app.route('/api/saldo')
async def api_saldo():
    try:
        
        if 'user_id' not in flask_session:
            return jsonify({'error': 'No autenticado'}), 401

        user_id = flask_session['user_id']
        user = await obtener_datos_usuario(user_id)

        # Obtener el teléfono del usuario desde la tabla depositos
        telefono = None
        try:
            
            registro = obtener_registro('depositos', user_id)
            if registro:
                # El teléfono está en el índice 2 (tercera columna)
                telefono = registro[2] if len(registro) > 2 else None
               
            else:
                print(f"🔍 [DEBUG] No se encontró registro de teléfono")
        except Exception as e:
            print(f"⚠️ [DEBUG] Error al obtener teléfono: {str(e)}")

        # Calcular total ganado por referidos
        referidos = user.get('referidos', 0)
        total_ganado_ref = referidos * 7

        return jsonify({
            'user_id': user.get('user_id'),
            'nombre': user.get('nombre'),
            'email': user.get('email'),
            'balance': user.get('balance', 0),
            'bono': user.get('bono', 0),
            'referido_por': user.get('referido_por'),
            'referidos': referidos,
            'total_ganado_ref': total_ganado_ref,
            'medalla': user.get('medalla', 'Sin medalla'),
            'rollover_requerido': user.get('rollover_requerido', 0),
            'rollover_actual': user.get('rollover_actual', 0),
            'bono_retirable': user.get('bono_retirable', 0),
            'telefono': telefono,  # ✅ Teléfono incluido aquí
            'currency': 'CUP'
        })

    except Exception as e:
        print(f"❌ [DEBUG] Error en api_saldo: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/deposito/registrar-telefono', methods=['POST'])
async def registrar_telefono():
    try:
        if 'user_id' not in flask_session:
            return jsonify({'error': 'No autenticado'}), 401

        data = await request.get_json()
        telefono = data.get('telefono', '').strip()

        # Validar teléfono
        if not telefono.isdigit() or len(telefono) != 8:
            return jsonify({'error': 'Teléfono inválido. Debe tener 8 dígitos'}), 400

        user_id = flask_session['user_id']
        
        # Registrar en la base de datos
        conn = await get_db_connection()
        await conn.execute(
            "INSERT OR REPLACE INTO depositos (user_id, telefono) VALUES (?, ?)",
            (user_id, telefono)
        )
        await conn.commit()
        await conn.close()

        return jsonify({'success': True, 'telefono': telefono})
        limpiar_cache_buscar_equipo(context)

    except Exception as e:
        print(f"❌ Error al registrar teléfono: {str(e)}")
        return jsonify({'error': str(e)}), 500        
def get_telegram_user_id():
    """Obtiene el user_id directamente desde la sesión de Flask"""
    try:
        user_id = flask_session.get('user_id')
        if user_id:
            
            return str(user_id)
        else:
            print("⚠️ No hay user_id en la sesión")
            return None
    except Exception as e:
        print(f"⚠️ Error al obtener user_id de la sesión: {e}")
        return None        
        
@app.route('/api/eventos-vivos')
async def api_eventos_vivos():
    try:
        eventos = await obtener_eventos_futbol_live_all()
        if isinstance(eventos, str):
            return jsonify({'error': eventos}), 500
        
        eventos_formateados = []
        for evento in eventos[:20]:
            eventos_formateados.append({
                'id': evento['fixture']['id'],
                'teams': {
                    'home': {
                        'name': evento['teams']['home']['name'],
                        'logo': evento['teams']['home']['logo'] if 'logo' in evento['teams']['home'] else ''
                    },
                    'away': {
                        'name': evento['teams']['away']['name'],
                        'logo': evento['teams']['away']['logo'] if 'logo' in evento['teams']['away'] else ''
                    }
                },
                'fixture': {
                    'date': evento['fixture']['date'],
                    'status': evento['fixture']['status'],
                    'venue': evento['fixture']['venue']
                },
                'goals': evento['goals'],
                'league': {
                    'id': evento['league']['id'],
                    'name': evento['league']['name'],
                    'logo': evento['league']['logo'],
                    'country': evento['league']['country']
                }
            })
        
        return jsonify(eventos_formateados)
    except Exception as e:
        print(f"Error en eventos vivos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/eventos-prematch')
async def api_eventos_prematch():
    try:
        todos_eventos = []
        for league_id in LIGAS_PRINCIPALES_IDS[:2]:
            eventos = await obtener_eventos_futbol(str(league_id))
            if eventos and not isinstance(eventos, str):
                for evento in eventos:
                    evento['league_id'] = league_id
                    todos_eventos.append(evento)
        
        todos_eventos.sort(key=lambda x: x['fixture']['date'])
        
        eventos_formateados = []
        for evento in todos_eventos[:50]:
            eventos_formateados.append({
                'id': evento['fixture']['id'],
                'teams': {
                    'home': {
                        'name': evento['teams']['home']['name'],
                        'logo': evento['teams']['home']['logo'] if 'logo' in evento['teams']['home'] else ''
                    },
                    'away': {
                        'name': evento['teams']['away']['name'],
                        'logo': evento['teams']['away']['logo'] if 'logo' in evento['teams']['away'] else ''
                    }
                },
                'fixture': {
                    'date': evento['fixture']['date'],
                    'status': evento['fixture']['status'],
                    'venue': evento['fixture']['venue']
                },
                'league': {
                    'id': evento['league']['id'],
                    'name': evento['league']['name'],
                    'logo': evento['league']['logo'],
                    'country': evento['league']['country']
                },
                'league_id': evento['league_id']
            })
        
        return jsonify(eventos_formateados)
    except Exception as e:
        print(f"Error en eventos prematch: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ligas')
async def api_ligas():
    try:
        # Abrimos el archivo local
        with open('ligas.json', 'r', encoding='utf-8') as f:
            ligas_data = json.load(f)

        ligas = ligas_data.get("soccer", [])

        ligas_principales = []
        for liga_id, nombre in LIGAS_PRINCIPALES.items():
            # Buscamos la liga por id en el archivo
            liga = next((l for l in ligas if l.get('id') == liga_id), None)
            if liga:
                ligas_principales.append({
                    'id': liga_id,
                    'name': liga.get('league_data', {}).get('name', nombre),
                    'logo': liga.get('league_data', {}).get('logo', ''),
                    'country': liga.get('country_data', {}).get('name', ''),
                    'type': liga.get('type', '')
                })
            else:
                # Si no está en el archivo, podemos devolver al menos el nombre del diccionario
                ligas_principales.append({
                    'id': liga_id,
                    'name': nombre,
                    'logo': '',
                    'country': '',
                    'type': ''
                })

        return jsonify(ligas_principales)

    except Exception as e:
        print(f"Error en ligas: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/ligas-deporte.html')
def ligas_deporte():
    """Renderiza la página de ligas para deportes específicos"""
    deporte = request.args.get('deporte')
    return render_template('ligas-deporte.html', deporte=deporte)        
        

@app.route('/api/ligas-deporte/<deporte>')
async def api_ligas_deporte(deporte):
    """Obtiene ligas por deporte"""
    try:
        if deporte.lower() in ['soccer', 'fútbol', 'futbol']:
            # Para fútbol usar nuestro endpoint existente
            ligas = await obtener_ligas_futbol()
            if not ligas:
                return jsonify({'error': 'No se pudieron obtener las ligas de fútbol'}), 500
            
            ligas_formateadas = []
            for liga in ligas:
                ligas_formateadas.append({
                    'id': liga['id'],
                    'name': liga['title'],
                    'logo': liga.get('league_data', {}).get('logo', ''),
                    'country': liga.get('country_data', {}).get('name', ''),
                    'type': liga.get('type', '')
                })
            
            return jsonify(ligas_formateadas)
        else:
            # Para otros deportes, usar la misma lógica que el bot de Telegram
            api_key = await obtener_api()
            if not api_key:
                return jsonify({'error': 'No hay API key disponible'}), 500
            
            # Usar el endpoint correcto para obtener todos los deportes y filtrar
            sports_url = "https://api.the-odds-api.com/v4/sports/"
            params = {"api_key": api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(sports_url, params=params) as response:
                    if response.status == 200:
                        todos_deportes = await response.json()
                        
                        # Filtrar ligas por el grupo del deporte (igual que en el bot)
                        ligas_filtradas = [
                            liga for liga in todos_deportes 
                            if liga.get("group", "").lower() == deporte.lower()
                        ]
                        
                        # Formatear datos para consistencia
                        ligas_formateadas = []
                        for liga in ligas_filtradas:
                            ligas_formateadas.append({
                                'id': liga.get('key', ''),
                                'name': liga.get('title', ''),
                                'logo': '',
                                'country': '',
                                'sport_key': liga.get('key', ''),
                                'type': liga.get('description', '')
                            })
                        
                        return jsonify(ligas_formateadas)
                    else:
                        error_text = await response.text()
                        print(f"Error API odds: {response.status} - {error_text}")
                        return jsonify({'error': f'Error {response.status} from API'}), 500
                        
    except Exception as e:
        print(f"Error en api_ligas_deporte: {str(e)}")
        return jsonify({'error': str(e)}), 500
        


# Cache simple en memoria 0ara busqueda de equipos
search_cache = {}
CACHE_DURATION = timedelta(minutes=15)  # Cache por 15 minutos
@app.route('/api/buscar-equipos', methods=['GET'])
async def buscar_equipos():
    nombre_equipo = request.args.get('nombre', '').strip().lower()
    
    if not nombre_equipo or len(nombre_equipo) < 3:  
        return jsonify({"error": "El término de búsqueda debe tener al menos 3 caracteres"}), 400
    
    # Verificar cache
    cache_key = f"search_{nombre_equipo}"
    now = datetime.now()
    
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if now - timestamp < CACHE_DURATION:
            print(f"✅ BUSCAR EQUIPO Devolviendo resultados desde cache para: {nombre_equipo}")
            return jsonify(cached_data)
        else:
            # Eliminar entrada expirada del cache
            del search_cache[cache_key]
    
    try:  
        
        equipos = await buscar_equipo_por_nombre_async(nombre_equipo)  
          
        equipos_formateados = []  
        for team_id, team_name, logo in equipos:  
            equipos_formateados.append({  
                "id": team_id,  
                "nombre": team_name,  
                "logo": logo  
            })  
        
        # Guardar en cache
        search_cache[cache_key] = (equipos_formateados, now)
       
          
        return jsonify(equipos_formateados)  
    except Exception as e:  
        print(f"❌ Error en búsqueda de equipos: {e}")  
        return jsonify({"error": "Error interno del servidor"}), 500
def limpiar_cache_buscar_equipo(context):
    """Limpia las entradas expiradas del cache de búsqueda de equipos"""
    try:
        now = datetime.now()
        keys_a_eliminar = []
        
        for cache_key, (data, timestamp) in search_cache.items():
            if now - timestamp >= CACHE_DURATION:
                keys_a_eliminar.append(cache_key)
        
        # Eliminar entradas expiradas
        for key in keys_a_eliminar:
            del search_cache[key]
        
        # Log solo si se eliminó algo
        if keys_a_eliminar:
            print(f"🧹 Cache limpiado: {len(keys_a_eliminar)} entradas expiradas")
        else:
            print("✅ Cache verificado: sin entradas expiradas")
            
        
        
    except Exception as e:
        print(f"❌ Error limpiando cache: {e}")

@app.route('/api/equipo-partidos', methods=['GET'])
async def obtener_partidos_equipo():
    team_id = request.args.get('id', type=int)
    
    if not team_id:
        return jsonify({"error": "ID de equipo no proporcionado"}), 400
    
    try:
        partidos = await obtener_partidos_por_equipo(team_id)
        return jsonify(partidos)
    except Exception as e:
        print(f"Error obteniendo partidos del equipo: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/mis-apuestas')
def api_mis_apuestas():
    try:
        user_id = get_telegram_user_id() 
        
        # Obtener apuestas desde la base de datos usando la función existente
        apuestas_usuario = obtener_apuestas_usuario(user_id)
        
        return jsonify(apuestas_usuario)
    except Exception as e:
        print(f"Error en mis apuestas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/deportes')
async def api_deportes():
    try:
        # Deportes por defecto en caso de error
        deportes_por_defecto = [
            {
                "key": "soccer",
                "title": "Fútbol",
                "group": "Soccer"
            },
            {
                "key": "basketball", 
                "title": "Baloncesto",
                "group": "Basketball"
            },
            {
                "key": "tennis",
                "title": "Tenis", 
                "group": "Tennis"
            },
            {
                "key": "icehockey",
                "title": "Hockey", 
                "group": "Ice Hockey"
            }
        ]
        
        # Usar la misma lógica que en tu bot
        api_key = await obtener_api()
        if not api_key:
            print("🚨 No hay APIs disponibles con créditos suficientes.")
            return jsonify(deportes_por_defecto)
        
        url = "https://api.the-odds-api.com/v4/sports/"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"api_key": api_key}) as response:
                if response.status == 200:
                    deportes = await response.json()
                    remaining_credits = response.headers.get("x-requests-remaining", "No disponible")
                    
                    print(f"✅ Datos obtenidos. Créditos restantes: {remaining_credits}")
                    
                    # Filtrar solo deportes con partidos activos
                    deportes_activos = [d for d in deportes if d.get('active', False)]
                    return jsonify(deportes_activos)
                else:
                    print(f"❌ Error API deportes: {response.status}")
                    return jsonify(deportes_por_defecto)
                    
    except Exception as e:
        print(f"❌ Error en api/deportes: {e}")
        # Devolver deportes por defecto en caso de error
        return jsonify(deportes_por_defecto)
        
# Nuevos endpoints para deportes
@app.route('/api/ligas-futbol')
async def api_ligas_futbol():
    """Obtiene todas las ligas de fútbol"""
    try:
        ligas = await obtener_ligas_futbol()
        if not ligas:
            return jsonify({'error': 'No se pudieron obtener las ligas de fútbol'}), 500
        
        return jsonify(ligas)
    except Exception as e:
        print(f"Error en api/ligas-futbol: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/paises-futbol')
async def api_paises_futbol():
    """Obtiene países con ligas de fútbol - USANDO ARCHIVO LOCAL como bet.py"""
    print("🔍 [DEBUG] /api/paises-futbol llamado (usando archivo local)")
    
    try:
        # Cargar desde archivo local primero (igual que bet.py)
        try:
            with open('ligas.json', 'r', encoding='utf-8') as f:
                ligas_data = json.load(f)
                ligas = ligas_data.get("soccer", [])
                
            if not ligas:
                raise ValueError("No hay ligas en el archivo")
                
            print(f"✅ [DEBUG] Ligas cargadas desde archivo: {len(ligas)} ligas")
            
        except (FileNotFoundError, ValueError) as e:
            print(f"⚠️ [DEBUG] Error cargando archivo local: {e}, usando API")
            # Si falla el archivo, usar API como respaldo
            return await api_paises_futbol_from_api()
        
        # Procesar países únicos desde el archivo local
        paises = {}
        for liga in ligas:
            country_data = liga.get('country_data', {})
            country_name = country_data.get('name', 'Sin país')
            
            if country_name not in paises:
                paises[country_name] = {
                    'nombre': country_name,
                    'code': country_data.get('code', '').lower(),
                    'flag': country_data.get('flag', '🌍'),
                    'count': 0
                }
            paises[country_name]['count'] += 1
        
        paises_lista = list(paises.values())
        paises_lista.sort(key=lambda x: x['nombre'])
        
        print(f"✅ [DEBUG] Devolviendo {len(paises_lista)} países desde archivo local")
        return jsonify(paises_lista)
        
    except Exception as e:
        print(f"❌ [DEBUG] Error en api/paises-futbol: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/paises.html')
def paises():
    return render_template('paises.html')
@app.route('/ligas.html')
def ligas():
    deporte = request.args.get('deporte')
    pais = request.args.get('pais')
    tipo = request.args.get('tipo')
    
    # Aquí puedes pasar estos parámetros a tu template
    return render_template('ligas.html', deporte=deporte, pais=pais, tipo=tipo)    

async def api_paises_futbol_from_api():
    """Función de respaldo que usa la API (solo si falla el archivo local)"""
    try:
        url = "https://v3.football.api-sports.io/leagues"
        headers = {
            "x-rapidapi-key": API_FUTBOL_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        params = {"current": "true"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    return jsonify({'error': f'Error {response.status} from API'}), 500
                
                data = await response.json()
                
                if data.get("errors") or not data.get("response"):
                    return jsonify({'error': 'No hay ligas disponibles'}), 404
                
                # Procesar países únicos
                paises = {}
                for liga_data in data.get("response", []):
                    country_data = liga_data.get("country", {})
                    country_name = country_data.get('name', 'Sin país')
                    
                    if country_name not in paises:
                        paises[country_name] = {
                            'nombre': country_name,
                            'code': country_data.get('code', '').lower(),
                            'flag': country_data.get('flag', '🌍'),
                            'count': 0
                        }
                    paises[country_name]['count'] += 1
                
                paises_lista = list(paises.values())
                paises_lista.sort(key=lambda x: x['nombre'])
                
                return jsonify(paises_lista)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ligas-por-pais/<nombre_pais>')
async def api_ligas_por_pais(nombre_pais):
    """Obtiene ligas por país - USANDO ARCHIVO LOCAL como bet.py"""
    print(f"🔍 [DEBUG] /api/ligas-por-pais/{nombre_pais} llamado (usando archivo local)")
    
    try:
        # Cargar desde archivo local primero (igual que bet.py)
        try:
            with open('ligas.json', 'r', encoding='utf-8') as f:
                ligas_data = json.load(f)
                ligas = ligas_data.get("soccer", [])
                
            if not ligas:
                raise ValueError("No hay ligas en el archivo")
                
            print(f"✅ [DEBUG] Ligas cargadas desde archivo: {len(ligas)} ligas")
            
        except (FileNotFoundError, ValueError) as e:
            print(f"⚠️ [DEBUG] Error cargando archivo local: {e}, usando API")
            # Si falla el archivo, usar API como respaldo
            return await api_ligas_por_pais_from_api(nombre_pais)
        
        # Filtrar ligas por país desde el archivo local
        ligas_pais = []
        for liga in ligas:
            country_data = liga.get('country_data', {})
            country_name = country_data.get('name', '')
            
            if country_name and country_name.lower() == nombre_pais.lower():
                ligas_pais.append(liga)
                
        
        # Búsqueda parcial si no hay resultados exactos
        if not ligas_pais:
            print(f"⚠️ [DEBUG] No hay coincidencia exacta, buscando parcial...")
            for liga in ligas:
                country_data = liga.get('country_data', {})
                country_name = country_data.get('name', '')
                
                if country_name and nombre_pais.lower() in country_name.lower():
                    ligas_pais.append(liga)
                    print(f"✅ [DEBUG] Liga encontrada (parcial): {liga.get('title', '')}")
        
        if not ligas_pais:
            print(f"❌ [DEBUG] No se encontraron ligas para {nombre_pais}")
            return jsonify({'error': f'No se encontraron ligas para {nombre_pais}'}), 404
        
        print(f"✅ [DEBUG] Devolviendo {len(ligas_pais)} ligas para {nombre_pais}")
        return jsonify(ligas_pais)
        
    except Exception as e:
        print(f"❌ [DEBUG] Error en api/ligas-por-pais: {str(e)}")
        return jsonify({'error': str(e)}), 500


async def api_ligas_por_pais_from_api(nombre_pais):
    """Función de respaldo que usa la API (solo si falla el archivo local)"""
    try:
        url = "https://v3.football.api-sports.io/leagues"
        headers = {
            "x-rapidapi-key": API_FUTBOL_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        params = {"current": "true"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    return jsonify({'error': f'Error {response.status} from API'}), 500
                
                data = await response.json()
                
                if data.get("errors") or not data.get("response"):
                    return jsonify({'error': 'No hay ligas disponibles'}), 404
                
                # Filtrar ligas por país
                ligas_pais = []
                for liga_data in data.get("response", []):
                    country = liga_data.get("country", {})
                    country_name = country.get('name', '')
                    
                    if country_name and country_name.lower() == nombre_pais.lower():
                        league = liga_data.get("league", {})
                        
                        liga_procesada = {
                            "title": f"{league.get('name', '')} ({country_name})",
                            "key": f"futbol_{league.get('id', '')}",
                            "id": league.get('id', ''),
                            "group": "Soccer",
                            "type": league.get('type', 'Unknown'),
                            "league_data": league,
                            "country_data": country,
                            "seasons": liga_data.get("seasons", [])
                        }
                        ligas_pais.append(liga_procesada)
                
                # Búsqueda parcial si no hay resultados exactos
                if not ligas_pais:
                    for liga_data in data.get("response", []):
                        country = liga_data.get("country", {})
                        country_name = country.get('name', '')
                        
                        if country_name and nombre_pais.lower() in country_name.lower():
                            league = liga_data.get("league", {})
                            
                            liga_procesada = {
                                "title": f"{league.get('name', '')} ({country_name})",
                                "key": f"futbol_{league.get('id', '')}",
                                "id": league.get('id', ''),
                                "group": "Soccer", 
                                "type": league.get('type', 'Unknown'),
                                "league_data": league,
                                "country_data": country,
                                "seasons": liga_data.get("seasons", [])
                            }
                            ligas_pais.append(liga_procesada)
                
                if not ligas_pais:
                    return jsonify({'error': f'No se encontraron ligas para {nombre_pais}'}), 404
                
                return jsonify(ligas_pais)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/info-liga/<liga_id>')
async def api_info_liga(liga_id):
    """Obtiene información de una liga específica (para otros deportes)"""
    try:
        api_key = await obtener_api()
        if not api_key:
            return jsonify({'error': 'No hay API key disponible'}), 500
        
        # Buscar información de la liga en todos los deportes
        sports_url = "https://api.the-odds-api.com/v4/sports/"
        async with aiohttp.ClientSession() as session:
            async with session.get(sports_url, params={"api_key": api_key}) as response:
                if response.status == 200:
                    deportes = await response.json()
                    liga = next((d for d in deportes if d.get('key') == liga_id), None)
                    
                    if liga:
                        return jsonify({
                            'id': liga.get('key'),
                            'name': liga.get('title'),
                            'type': liga.get('description'),
                            'logo': ''
                        })
                    return jsonify({'error': 'Liga no encontrada'}), 404
                return jsonify({'error': 'Error al obtener información'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/eventos.html')
def eventos():
    """Renderiza la página de eventos"""
    league_id = request.args.get('liga')
    deporte = request.args.get('deporte', 'soccer')
    return render_template('eventos.html', league_id=league_id, deporte=deporte)

@app.route('/api/eventos-liga-odds/<liga_id>') 
async def api_eventos_liga_odds(liga_id):
    """Obtiene eventos para ligas de otros deportes"""
    try:
        api_key = await obtener_api()
        if not api_key:
            return jsonify({'error': 'No hay API key disponible'}), 500
        
        url = f"https://api.the-odds-api.com/v4/sports/{liga_id}/odds"
        params = {
            "api_key": api_key,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    eventos = await response.json()
                    return jsonify(eventos)
                return jsonify({'error': f'Error {response.status} from API'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/partidos.html')
def partidos():
    """Renderiza la página de partidos"""
    league_id = request.args.get('liga')
    deporte = request.args.get('deporte', 'soccer')
    return render_template('partidos.html', league_id=league_id, deporte=deporte)                
@app.route('/api/eventos-liga/<int:liga_id>')
async def api_eventos_liga(liga_id):
    """Obtiene eventos para una liga de fútbol específica"""
    try:
        # Usa tu función existente para obtener eventos de fútbol
        eventos = await obtener_eventos_futbol(str(liga_id))
        
        if isinstance(eventos, str) and eventos.startswith('Error'):
            return jsonify({'error': eventos}), 500
            
        return jsonify(eventos)
    except Exception as e:
        print(f"Error en api_eventos_liga: {str(e)}")
        return jsonify({'error': str(e)}), 500        
        
@app.route('/log', methods=['POST'])
def log():
    data = request.json
    log_message = data.get('log')
    if log_message:
        print(f"LOG: {log_message}")
    else:
        print("No log message received.")
    return '', 200     
    
@app.route('/mercados.html')
def mercados():
    """Renderiza la página de mercados"""
    event_id= request.args.get('evento')
    deporte = request.args.get('deporte', 'soccer')
    return render_template('mercados.html', event_id=event_id, deporte=deporte)

@app.route('/api/info-evento/<event_id>')
async def api_info_evento(event_id):
    """
    Obtiene información básica del evento directamente desde la API
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://v3.football.api-sports.io/fixtures",
                headers={"x-rapidapi-key": API_FUTBOL_KEY},
                params={"id": event_id}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()  # ¡Convertir a JSON aquí!
                    if data and data.get('response'):
                        return data['response'][0]
                else:
                    print(f"[ERROR] API fixtures status: {response.status}")
        
        return None
        
    except Exception as e:
        print(f"Error obteniendo info evento: {e}")
        return None
@app.route('/api/info-evento-otros/<event_id>')
async def api_info_evento_otros(event_id):
    """Devuelve solo la información básica del evento desde el archivo"""
    try:
        # Actualiza los mercados primero
        await api_mercados_odds(event_id)

        # Cargar el archivo de mercados
        todos_mercados = cargar_mercados()
        evento_key = f"evento_{event_id}"

        if evento_key not in todos_mercados:
            return {"error": f"No se encontró el evento {event_id}"}, 404

        api_response = todos_mercados[evento_key]["api_response"]

        # Devolver solo los campos que quieres
        result = {
            "sport_key": api_response.get("sport_key"),
            "sport_title": api_response.get("sport_title"),
            "commence_time": api_response.get("commence_time"),
            "home_team": api_response.get("home_team"),
            "away_team": api_response.get("away_team")
        }

        return result

    except Exception as e:
        print(f"❌ [DEBUG] Error en api_info_evento_otros: {str(e)}")
        return {"error": str(e)}, 500
# Función auxiliar para manejar el archivo JSON
def cargar_mercados():
    """Carga los mercados desde el archivo JSON"""
    try:
        if not os.path.exists(MERCADOS_FILE):
            return {}
            
        # Verificar tamaño del archivo
        if os.path.getsize(MERCADOS_FILE) > MAX_FILE_SIZE:
            print(f"[INFO] Archivo {MERCADOS_FILE} excede el tamaño máximo, reiniciando...")
            with open(MERCADOS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
            
        with open(MERCADOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Error cargando mercados: {e}")
        return {}

def guardar_mercados(mercados):
    """Guarda los mercados en el archivo JSON"""
    try:
        with open(MERCADOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(mercados, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Error guardando mercados: {e}")
        return False

        
                        


# 🔒 Lock global
lock_mercados = asyncio.Lock()
#obtener_mercados
@app.route('/api/mercados-futbol/<event_id>')
async def api_mercados_futbol(event_id):
    try:
        print(f"[DEBUG] Obteniendo mercados para evento {event_id}")
        
        # 1. Primero obtener la información básica del evento (SIEMPRE desde la API)
        evento_info = await api_info_evento(event_id)
        if not evento_info:
            return jsonify({'error': 'Evento no encontrado'}), 404
        
        # 2. Determinar si es LIVE
        status_short = evento_info.get('fixture', {}).get('status', {}).get('short', '')
        is_live = status_short in ["LIVE", "1H", "2H", "HT"]
        print(f"[DEBUG] Estado del evento: {status_short}, LIVE: {is_live}")
        
        # 3. LÓGICA DE CACHÉ PARA PREPARTIDO
        if not is_live:
            session_key = f"evento_{event_id}"
            
            # Cargar mercados existentes del archivo
            todos_mercados = cargar_mercados()
            evento_guardado = todos_mercados.get(session_key)
            
            if evento_guardado:
                timestamp_guardado = evento_guardado.get('timestamp', 0)
                tiempo_transcurrido = datetime.now().timestamp() - timestamp_guardado
                max_tiempo_cache = 60 * 60  # 60 minutos en segundos
                
                print(f"[CACHE] Datos encontrados en archivo. Tiempo transcurrido: {tiempo_transcurrido/60:.1f} minutos")
                
                if tiempo_transcurrido < max_tiempo_cache:
                    print(f"[CACHE] Usando datos cacheados (menos de 60 minutos)")
                    return jsonify(evento_guardado.get('mercados', []))
                else:
                    print(f"[CACHE] Datos muy antiguos, consultando API...")
            else:
                print(f"[CACHE] No hay datos cacheados para este evento")
        
        # 4. Obtener los mercados desde la API (solo si es LIVE o cache expirado/no existe)
        endpoint = "odds/live" if is_live else "odds"
        
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(
                f"https://v3.football.api-sports.io/{endpoint}",
                headers={"x-rapidapi-key": API_FUTBOL_KEY},
                params={"fixture": event_id}
            ) as response:

                print(f"[API] Código de estado: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"[API ERROR] Status: {response.status}, Response: {error_text}")
                    return jsonify({'error': f'Error API: {response.status}'}), 500

                api_data = await response.json()
                print(f"[DEBUG] API Data keys: {list(api_data.keys()) if api_data else 'None'}")
                
                if not api_data or 'response' not in api_data:
                    print("[API WARNING] Respuesta vacía o sin 'response'")
                    # Si hay datos cacheados y la API falla, usar los cacheados incluso si son viejos
                    if not is_live and evento_guardado:
                        print("[CACHE] API falló, usando datos cacheados como respaldo")
                        return jsonify(evento_guardado.get('mercados', []))
                    return jsonify({'error': 'No hay datos de mercados disponibles para este evento'}), 404

                response_data = api_data['response']
                if not response_data:
                    print("[API WARNING] Response vacío")
                    if not is_live and evento_guardado:
                        print("[CACHE] API vacía, usando datos cacheados como respaldo")
                        return jsonify(evento_guardado.get('mercados', []))
                    return jsonify({'error': 'No hay datos de mercados disponibles para este evento'}), 404
                
                event_data = response_data[0]
                print(f"[DEBUG] Event data keys: {list(event_data.keys()) if event_data else 'None'}")
                
                # 5. Procesar los bookmakers - MÉTODO MEJORADO
                mercados_formateados = []
                
                if is_live:
                    # Para eventos en vivo
                    odds_data = event_data.get('odds', [])
                    print(f"[DEBUG] Odds data length: {len(odds_data)}")
                    
                    # Procesar mercados en vivo
                    for market in odds_data:
                        market_name = market.get('name')
                        if not market_name:
                            continue

                        market_config = CONFIG_MERCADOS.get(market_name)
                        if not market_config:
                            continue

                        odds_formateadas = []
                        for item in market.get('values', []):
                            if item.get('suspended', False):
                                continue

                            odd_original = item.get("odd")
                            if odd_original is not None:
                                try:
                                    odd_modificada = modificar_cuota_individual(odd_original)
                                except Exception as e:
                                    print(f"[WARNING] Error modificando cuota {odd_original}: {e}")
                                    odd_modificada = odd_original
                            else:
                                odd_modificada = None

                            odds_formateadas.append({
                                "value": item.get("value"),
                                "odd": odd_modificada,
                                "point": item.get('handicap'),
                                "suspended": False
                            })

                        if odds_formateadas:
                            mercado_formateado = {
                                "key": market_name,
                                "name": market_config["nombre"],
                                "emoji": market_config.get("emoji", "📊"),
                                "odds": odds_formateadas,
                                "is_live": is_live
                            }
                            mercados_formateados.append(mercado_formateado)
                else:
                    # Para eventos próximos - MÉTODO MEJORADO
                    bookmakers = event_data.get('bookmakers', [])
                    print(f"[DEBUG] Bookmakers length: {len(bookmakers)}")
                    
                    # Buscar bookmakers con datos
                    for bookmaker in bookmakers:
                        bets = bookmaker.get('bets', [])
                        print(f"[DEBUG] Bets for {bookmaker.get('name')}: {len(bets)}")
                        
                        if not bets:
                            continue
                            
                        # Procesar cada mercado
                        for bet in bets:
                            market_name = bet.get('name')
                            if not market_name:
                                continue

                            market_config = CONFIG_MERCADOS.get(market_name)
                            if not market_config:
                                continue

                            odds_formateadas = []
                            for item in bet.get('values', []):
                                if item.get('suspended', False):
                                    continue

                                odd_original = item.get("odd")
                                if odd_original is not None:
                                    try:
                                        odd_modificada = modificar_cuota_individual(odd_original)
                                    except Exception as e:
                                        print(f"[WARNING] Error modificando cuota {odd_original}: {e}")
                                        odd_modificada = odd_original
                                else:
                                    odd_modificada = None

                                odds_formateadas.append({
                                    "value": item.get("value"),
                                    "odd": odd_modificada,
                                    "point": item.get('point'),
                                    "suspended": False
                                })

                            if odds_formateadas:
                                mercado_formateado = {
                                    "key": market_name,
                                    "name": market_config["nombre"],
                                    "emoji": market_config.get("emoji", "📊"),
                                    "odds": odds_formateadas,
                                    "is_live": is_live
                                }
                                mercados_formateados.append(mercado_formateado)
                        
                        # Si encontramos mercados, dejar de buscar en otros bookmakers
                        if mercados_formateados:
                            break

                print(f"[DEBUG] Total mercados formateados: {len(mercados_formateados)}")

                if not mercados_formateados:
                    print("[API WARNING] No se encontraron mercados después de procesar")
                    # Si no hay mercados en API pero hay cacheados, usar los cacheados
                    if not is_live and evento_guardado:
                        print("[CACHE] API sin mercados, usando datos cacheados como respaldo")
                        return jsonify(evento_guardado.get('mercados', []))
                    return jsonify({'error': 'No hay mercados disponibles para este evento'}), 404

                # 6. Guardar en el archivo JSON (siempre para mantener actualizado)
                async with lock_mercados:  # 🔒 Sección crítica
                    session_key = f"evento_{event_id}"
                    
                    # Cargar mercados existentes
                    todos_mercados = cargar_mercados()
                    
                    # Actualizar/agregar el evento
                    todos_mercados[session_key] = {
                        'evento_info': evento_info,  # Se actualiza con la info más reciente
                        'mercados': mercados_formateados,
                        'timestamp': datetime.now().timestamp(),
                        'is_live': is_live
                    }
                    
                    # Guardar de vuelta al archivo
                    if guardar_mercados(todos_mercados):
                        print(f"[INFO] Mercados guardados para evento {event_id}")
                    else:
                        print(f"[ERROR] Error guardando mercados para evento {event_id}")

                return jsonify(mercados_formateados)

    except Exception as e:
        print(f"Error en api_mercados_futbol: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/mercados-odds/<event_id>')
async def api_mercados_odds(event_id):
    """Obtiene mercados para otros deportes y guarda la respuesta completa API"""
    try:
        # Obtener el sport_key del parámetro 'sportKey'
        sport_key = request.args.get('sportKey')
        print(f"🔍 [DEBUG] Sport key recibido: {sport_key}")
        
        if not sport_key:
            return jsonify({'error': 'Parámetro sportKey requerido'}), 400
            
        api_key = await obtener_api()
        if not api_key:
            return jsonify({'error': 'No hay API key disponible'}), 500
        
        # 1. Obtener datos de la API de odds
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": api_key,
            "regions": "us",
            "bookmakers": "bovada",
            "markets": "h2h,spreads,totals"
        }
        
        print(f"🌐 [DEBUG] Llamando a API: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ [DEBUG] Respuesta API exitosa")
                    
                    # 2. Procesar los mercados (solo Bovada)
                    mercados_procesados = procesar_mercados_odds(data)
                    
                    if "error" in mercados_procesados:
                        return jsonify(mercados_procesados), 500
                    
                    # 3. Guardar la respuesta completa + mercados procesados
                    session_key = f"evento_{event_id}"
                    todos_mercados = cargar_mercados()
                    
                    todos_mercados[session_key] = {
                        'api_response': data,                  # 🔹 aquí se guarda la respuesta completa
                        'mercados_procesados': mercados_procesados,  # 🔹 y los procesados
                        'timestamp': datetime.now().timestamp(),
                        'is_live': False
                    }
                    
                    if guardar_mercados(todos_mercados):
                        print(f"[INFO] Mercados guardados para evento {event_id}")
                    else:
                        print(f"[ERROR] Error guardando mercados para evento {event_id}")
                    
                    # 🔹 EL RETURN QUEDA COMO ESTÁ
                    return jsonify(mercados_procesados)
                else:
                    error_text = await response.text()
                    print(f"❌ [DEBUG] Error API odds: {response.status} - {error_text}")
                    return jsonify({'error': f'Error {response.status} from API'}), 500
          
    except Exception as e:
        print(f"❌ [DEBUG] Error en api_mercados_odds: {str(e)}")
        return jsonify({'error': str(e)}), 500

def procesar_mercados_odds(data):
    """Procesa los datos de mercados de la API de Odds para otros deportes (solo Bovada)"""
    try:
        print(f"🔍 [DEBUG] Procesando mercados odds - datos recibidos: {type(data)}")
        
        if not data:
            return {"error": "Datos vacíos"}
        
        # Si la API devuelve un array, tomar el primer elemento
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        
        mercados_procesados = []
        mercados_vistos = set()  # Para evitar duplicados
        
        # Extraer SOLO el bookmaker Bovada (como hace el bot)
        bookmakers = data.get('bookmakers', [])
        bovada_bookmaker = None
        
        for bookmaker in bookmakers:
            if bookmaker.get('title') == 'Bovada':
                bovada_bookmaker = bookmaker
                break
        
        if not bovada_bookmaker:
            print("⚠️ [DEBUG] No se encontró bookmaker Bovada")
            return {"error": "No hay datos de Bovada disponibles"}
        
        # Procesar solo los mercados de Bovada
        markets = bovada_bookmaker.get('markets', [])
        
        for market in markets:
            market_key = market.get('key')
            
            # Evitar procesar el mismo mercado múltiples veces
            if market_key in mercados_vistos:
                continue
                
            mercados_vistos.add(market_key)
            
            # Buscar configuración para este mercado
            config = CONFIG_MERCADOS.get(market_key, {})
            nombre_mostrar = config.get('nombre', market_key)
            emoji = config.get('emoji', '📊')
            
            # Procesar outcomes (opciones de apuesta)
            outcomes = market.get('outcomes', [])
            odds_procesadas = []
            
            for outcome in outcomes:
                odd_value = outcome.get('price')
                outcome_name = outcome.get('name')
                point = outcome.get('point')
                
                # Solo agregar outcomes válidos
                if odd_value is not None:
                    odds_procesadas.append({
                        'name': outcome_name,
                        'odd': odd_value,
                        'point': point
                    })
            
            # Solo agregar mercados que tengan odds válidas
            if odds_procesadas:
                mercados_procesados.append({
                    'key': market_key,
                    'name': market_key,
                    'display_name': nombre_mostrar,
                    'emoji': emoji,
                    'odds': odds_procesadas,
                    'bookmaker': 'Bovada'
                })
        
        print(f"✅ [DEBUG] Mercados procesados: {len(mercados_procesados)}")
        return mercados_procesados
        
    except Exception as e:
        print(f"❌ [ERROR] procesar_mercados_odds: {str(e)}")
        return {"error": f"Error procesando mercados: {str(e)}"}


   
    
        
            
                
                    
                        
                            

async def obtener_datos_usuario(user_id=None):
    """Obtiene datos completos del usuario desde la base de datos"""
    
    if user_id is None:
        return {
            'user_id': '0',
            'nombre': 'Usuario no encontrado',
            'email': '',
            'password': '',
            'balance': 0,
            'bono': 0,
            'referido_por': None,
            'referidos': 0,
            'total_ganado_ref': 0,
            'medalla': 'Sin medalla',
            'rollover_requerido': 0,
            'rollover_actual': 0,
            'bono_retirable': 0
        }
    
    user_id_str = str(user_id)

    try:
        # Obtener datos del usuario desde la tabla usuarios
        usuario_info = obtener_registro("usuarios", user_id_str, 
                                      "nombre, Email, Password, Balance, Lider, Referidos, "
                                      "total_ganado_ref, Medalla, Username")
        
        # Obtener datos del bono de apuesta desde la tabla bono_apuesta
        bono_info = obtener_registro("bono_apuesta", user_id_str,
                                   "bono, rollover_requerido, rollover_actual, bono_retirable")
        
        # Procesar datos del usuario
        if usuario_info:
            nombre, email, password, balance, lider, referidos, total_ganado_ref, medalla, username = usuario_info
        else:
            # Usuario no encontrado, devolver valores por defecto
            nombre = f'Usuario{user_id_str}'
            email = ''
            password = ''
            balance = 0
            lider = None
            referidos = 0
            total_ganado_ref = 0
            medalla = 'Sin medalla'
        
        # Procesar datos del bono
        if bono_info:
            bono, rollover_requerido, rollover_actual, bono_retirable = bono_info
        else:
            bono = 0
            rollover_requerido = 0
            rollover_actual = 0
            bono_retirable = 0
        
        resultado = {
            'user_id': user_id_str,
            'nombre': nombre or f'Usuario{user_id_str}',
            'email': email or '',
            'password': password or '',
            'balance': balance or 0,
            'bono': bono or 0,
            'referido_por': lider,
            'referidos': referidos or 0,
            'total_ganado_ref': total_ganado_ref or 0,
            'medalla': medalla or 'Sin medalla',
            'rollover_requerido': rollover_requerido or 0,
            'rollover_actual': rollover_actual or 0,
            'bono_retirable': bono_retirable or 0
        }
        
        return resultado
        
    except Exception as e:
        print(f"Error en obtener_datos_usuario: {e}")
        # Devolver estructura básica en caso de error
        return {
            'user_id': user_id_str,
            'nombre': f'Usuario{user_id_str}',
            'email': '',
            'password': '',
            'balance': 0,
            'bono': 0,
            'referido_por': None,
            'referidos': 0,
            'total_ganado_ref': 0,
            'medalla': 'Sin medalla',
            'rollover_requerido': 0,
            'rollover_actual': 0,
            'bono_retirable': 0
        }
@app.route('/api/realizar-apuesta', methods=['POST'])
async def realizar_apuesta():
    """Endpoint para realizar apuestas - VERSIÓN MEJORADA"""
    try:
        # Obtener datos de la solicitud
        data = request.get_json()
        
        
        # Verificar si es una apuesta combinada
        es_combinada = 'selecciones' in data and len(data['selecciones']) > 1
        
        if es_combinada:
            # Validar datos requeridos para apuesta combinada
            required_fields = ['monto', 'metodo_pago', 'cuotaTotal']
            selecciones = data.get('selecciones', [])
            
            # Validar cada selección
            for i, seleccion in enumerate(selecciones):
                seleccion_required = ['event_id', 'deporte', 'market', 'selection', 'odd']
                for field in seleccion_required:
                    if field not in seleccion:
                        return jsonify({
                            'success': False,
                            'message': f'Campo requerido faltante en selección {i+1}: {field}'
                        }), 400
        else:
            # Validar datos requeridos para apuesta simple
            required_fields = ['event_id', 'deporte', 'market', 'selection', 'odd', 'monto', 'metodo_pago']
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        # Obtener user_id 
        user_id = get_telegram_user_id() 
        
        # ✅ AGREGAR ESTA LÍNEA DE VALIDACIÓN
        if not user_id or user_id == 'N/A':
            return jsonify({'success': False, 'message': 'Error al procesar la apuesta. Intenta nuevamente.'}), 400
        

        
        
        # 1. Verificar disponibilidad de fondos
        
        monto = float(data['monto'])
        metodo_pago = data['metodo_pago']
        
        verificacion_fondos = await verificar_fondos_usuario(user_id, monto, metodo_pago)
        
        
       
        if not verificacion_fondos['success']:
            return jsonify(verificacion_fondos), 400
        
        # 2. Procesar el pago
        resultado_pago = await procesar_pago(user_id, monto, metodo_pago)
       
        if not resultado_pago['success']:
            return jsonify(resultado_pago), 400
        
        user_data = await obtener_datos_usuario(user_id)
        
        
        # 4. Crear y guardar la apuesta según el tipo        
        if es_combinada:
            # Procesar apuesta combinada
            apuesta_guardada = await crear_apuesta_combinada(data, user_id, user_data)
        else:
            # Procesar apuesta simple
            # Obtener información del evento según el deporte
            evento_info = {}
            deporte = data['deporte']
            
            if deporte.lower() in ['soccer', 'fútbol', 'futbol']:
                # Para fútbol, usar la API de fútbol
                evento_info = await api_info_evento(data['event_id'])
            else:
                # Para otros deportes, usar la API de odds
                evento_info = await api_info_evento_otros(data['event_id'])
                        
            # Crear la estructura de apuesta simple
            apuesta_data = {
                'event_id': data['event_id'],
                'market': data['market'],
                'selection': data['selection'],
                'odd': float(data['odd']),
                'monto': monto,
                'point': data.get('point'),
                'deporte': deporte,
                'evento_data': evento_info,
                'betting_type': 'PREPARTIDO',
                'metodo_pago': metodo_pago
            }
            
            apuesta_guardada = await crear_apuesta_web(apuesta_data, user_id, user_data)
        
        print(f"📝 Apuesta guardada: {apuesta_guardada}")
        
        # 5. Aplicar bonificación por referido (si aplica)
        print("🔄 Aplicando bonificación por referido...")
        await aplicar_bono_referido(user_id, monto, metodo_pago)
        
        # 6. Enviar notificación (opcional)
        print("🔄 Enviando notificación...")
        await enviar_notificacion_apuesta_web(apuesta_guardada, user_data)
        
        # 7. Preparar respuesta exitosa
        return jsonify({
            'success': True,
            'message': '✅ Apuesta realizada con éxito',
            'data': apuesta_guardada,
            'nuevo_balance': resultado_pago.get('nuevo_balance'),
            'nuevo_bono': resultado_pago.get('nuevo_bono')
        }), 200
        
    except Exception as e:
        print(f"❌ Error en realizar_apuesta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor al procesar la apuesta'
        }), 500
        
def generar_id():
    """Genera un ID único para apuestas"""
    return str(uuid.uuid4())[:8].upper()  # 
    
async def enviar_notificacion_apuesta_web(apuesta, user_data):
    """Envía notificaciones por la web en formato HTML profesional para Telegram"""
    try:
        # Extraer datos de la apuesta
        user_id = apuesta.get('usuario_id', 'N/A')
        user_name = apuesta.get('user_name', 'Usuario')
        id_ticket = apuesta.get('id_ticket', 'N/A')
        monto = apuesta.get('monto', 0)
        cuota = apuesta.get('cuota', 1)
        ganancia = round(monto * cuota, 2)
        
        # Determinar tipo de apuesta - CORREGIDO: usar campo de la DB
        betting_type = apuesta.get('betting', 'PREPARTIDO')
        es_combinada = betting_type == "COMBINADA"  # ✅ CORRECCIÓN IMPORTANTE
        
        # Separador
        separador = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        
        # Emojis según tipo de apuesta
        ticket_emoji = {
            "LIVE": "🔴 𝙇𝙄𝙑𝙀 𝘼𝙋𝙐𝙀𝙎𝙏𝘼 🔴",
            "COMBINADA": "🔵 𝘾𝙊𝙈𝘽𝙄𝙉𝘼𝘿𝘼 🔵",
            "PREPARTIDO": "🕓 𝙋𝙍𝙀𝙋𝘼𝙍𝙏𝙄𝘿𝙊 🕓"
        }.get(betting_type, "🎟️ 𝙏𝙄𝘾𝙆𝙀𝙏 🎟️")
        
        # Método de pago
        bono = apuesta.get('bono', 0)
        balance = apuesta.get('balance', 0)
        metodo_pago = f"🎁 𝘽𝙤𝙣𝙤: {bono} 𝘾𝙐𝙋" if bono > 0 else f"💰 𝘽𝙖𝙡𝙖𝙣𝙘𝙚: {balance} 𝘾𝙐𝙋"
        
        if es_combinada:
            # ✅ APUESTA COMBINADA - CORREGIDO
            selecciones = apuesta.get('selecciones', [])
            print(f"🔍 Detectada apuesta combinada con {len(selecciones)} selecciones")
            
            mensaje_canal = f"""
<b>{ticket_emoji}</b>
{separador}
👤 <b>Usuario:</b> {user_name}
🆔 <b>ID:</b> <code>{user_id}</code>

{metodo_pago}

⚽ <b>Deporte:</b> 
└ Combinada ({len(selecciones)} eventos)

💵 <b>Monto:</b> <code>{monto} 𝘾𝙐𝙋</code>
📈 <b>Cuota:</b> <code>{cuota:.2f}</code>
💰 <b>Ganancia:</b> <code>{ganancia:.2f} 𝘾𝙐𝙋</code>

{separador}
<blockquote>📋 𝙎𝙀𝙇𝙀𝘾𝘾𝙄𝙊𝙉𝙀𝙎:</blockquote>
"""
            
            for i, seleccion in enumerate(selecciones, 1):
                deporte = seleccion.get('deporte', 'Desconocido')
                partido = seleccion.get('partido', 'Partido desconocido')
                liga = seleccion.get('liga', 'Liga desconocida')
                mercado = seleccion.get('mercado', 'Mercado')  # ✅ Usar 'mercado' en lugar de 'tipo_apuesta'
                favorito = seleccion.get('favorito', 'selection')
                cuota_individual = seleccion.get('cuota_individual', 1)
                
                mensaje_canal += f"""
<pre>🔹 𝙀𝙫𝙚𝙣𝙩𝙤 {i}
├ 🏅 {deporte}
├ ⚽ {partido}
├ 🏟 {liga}
├ 📌 {mercado.upper()}
├ 🎯 {favorito}
└ 📈 {cuota_individual:.2f}</pre>
"""
            
        else:
            # APUESTA SIMPLE
            partido = apuesta.get('partido', 'Partido desconocido')
            favorito = apuesta.get('favorito', 'Selección desconocida')
            liga = apuesta.get('liga', 'Liga desconocida')
            deporte = apuesta.get('deporte', 'Desconocido')
            tipo_apuesta = apuesta.get('tipo_apuesta', 'Mercado')
            
            # Bloque de minuto y marcador (si está disponible)
            bloque_minuto_marcador = ""
            minuto = apuesta.get('minuto', '')
            marcador = apuesta.get('marcador', '')
            if minuto and marcador:
                bloque_minuto_marcador = f"""
<pre>┌───────────────────────┐
│ ⏱️  𝙈𝙞𝙣𝙪𝙩𝙤: {minuto}'
│ 📊  𝙈𝙖𝙧𝙘𝙖𝙙𝙤𝙧: {marcador}
└───────────────────────┘</pre>

"""
            
            mensaje_canal = f"""
<b>{ticket_emoji}</b>
{separador}
👤 <b>Usuario:</b> {user_name}
🆔 <b>ID:</b> <code>{user_id}</code>

🎯 <b>Tipo:</b> 
└ {tipo_apuesta}

{metodo_pago}

{bloque_minuto_marcador}

⚽ <b>Deporte:</b> 
└ {deporte}

🏆 <b>Liga:</b> 
└ {liga}

⚔️ <b>Partido:</b> 
└ {partido}

🎯 <b>Selección:</b> 
└ {favorito}

💵 <b>Monto:</b> <code>{monto} 𝘾𝙐𝙋</code>
📈 <b>Cuota:</b> <code>{cuota:.2f}</code>
💰 <b>Ganancia:</b> <code>{ganancia:.2f} 𝘾𝙐𝙋</code>
"""
        
        mensaje_canal += f"""
{separador}
🆔 <b>Ticket ID:</b> <code>{id_ticket}</code>
"""
        
        print(f"📤 Enviando mensaje al canal (combinada: {es_combinada})")
        # Enviar mensaje al canal
        response = await enviar_mensaje_al_canal(TOKEN, CANAL_TICKET, mensaje_canal)
        
        if response and response.get('ok'):
            print("✔️ Mensaje enviado correctamente al canal")
            return True
        else:
            error_desc = response.get('description', 'Desconocido') if response else 'No response'
            print(f"❌ Error al enviar mensaje: {error_desc}")
            return False
    
    except Exception as e:
        print(f"❌ Error en notificación web: {e}")
        import traceback
        traceback.print_exc()
        return False
async def enviar_mensaje_al_canal(token, chat_id, mensaje, reply_markup=None):
    """Envía un mensaje al canal de Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Preparar los parámetros base
    params = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "html"
    }
    
    # Si hay reply_markup, convertirlo a JSON y agregarlo
    if reply_markup is not None:
        # Convertir el objeto InlineKeyboardMarkup a diccionario JSON
        reply_markup_dict = reply_markup.to_dict()
        params["reply_markup"] = json.dumps(reply_markup_dict)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:  # Cambiado a POST y json
                result = await response.json()
                if not result.get('ok'):
                    print(f"❌ Error Telegram API: {result}")
                return result
    except Exception as e:
        print(f"❌ Error enviando mensaje al canal: {e}")
        return {"ok": False, "description": str(e)}
# Función asíncrona para verificar fondos
async def verificar_fondos_usuario(user_id, monto, metodo_pago):
    """Verifica que el usuario tenga fondos suficientes en user_data.json"""
    try:
        # Obtener datos actuales del usuario
        usuario_data = await obtener_datos_usuario(user_id)

        if metodo_pago == 'balance':
            balance_actual = usuario_data['balance']
            if monto > balance_actual:
                return {
                    'success': False,
                    'message': f'Fondos insuficientes. Balance disponible: {balance_actual}CUP'
                }

        elif metodo_pago == 'bono':
            bono_actual = usuario_data['bono']
            if monto > bono_actual:
                return {
                    'success': False,
                    'message': f'Fondos insuficientes. Bono disponible: {bono_actual}CUP'
                }

        return {'success': True}

    except Exception as e:
        print(f"Error verificando fondos: {str(e)}")
        return {
            'success': False,
            'message': 'Error al verificar fondos del usuario'
        }
        
@app.route('/live')
def live():
    return render_template('live.html')  # o el nombre de tu archivo        
async def procesar_pago(user_id, monto, metodo_pago):
    """Procesa el pago y actualiza los fondos del usuario en user_data.json"""
    try:
        # Obtener datos actuales del usuario
        usuario_data = await obtener_datos_usuario(user_id)
        
        if metodo_pago == 'balance':
            nuevo_balance = usuario_data['balance'] - monto
            await actualizar_balance_usuario(user_id, nuevo_balance)
            return {
                'success': True,
                'nuevo_balance': nuevo_balance,
                'nuevo_bono': usuario_data['bono']
            }
            
        elif metodo_pago == 'bono':
            nuevo_bono = usuario_data['bono'] - monto
            await actualizar_bono_usuario(user_id, nuevo_bono)
            return {
                'success': True,
                'nuevo_balance': usuario_data['balance'],
                'nuevo_bono': nuevo_bono
            }
            
    except Exception as e:
        print(f"Error procesando pago: {str(e)}")
        return {
            'success': False,
            'message': 'Error al procesar el pago'
        }




async def aplicar_bono_referido(user_id, monto, metodo_pago):
    """Aplica bonificación por referido si aplica"""
    try:
        # Obtener datos del usuario
        usuario_data = await obtener_datos_usuario(user_id)
        referido_id = usuario_data.get('referido_por')
        
        if referido_id:
            if metodo_pago == 'bono':
                # 10% de bono para el referidor
                bono_referidor = monto * 0.10
                datos_referidor = await obtener_datos_usuario(referido_id)
                nuevo_bono = datos_referidor['bono'] + bono_referidor
                await actualizar_bono_usuario(referido_id, nuevo_bono)
                
            elif metodo_pago == 'balance':
                # 1% de balance para el referidor
                balance_referidor = monto * 0.01
                datos_referidor = await obtener_datos_usuario(referido_id)
                nuevo_balance = datos_referidor['balance'] + balance_referidor
                await actualizar_balance_usuario(referido_id, nuevo_balance)
                
    except Exception as e:
        print(f"Error aplicando bono referido: {str(e)}")

async def actualizar_balance_usuario(user_id, nuevo_balance):
    """Actualiza el balance de un usuario en la base de datos"""
    try:
        user_id_str = str(user_id)
        
        # Verificar si el usuario existe
        usuario_existente = obtener_registro("usuarios", user_id_str, "Balance")
        
        if usuario_existente:
            # Actualizar balance existente
            exito = actualizar_registro("usuarios", user_id_str, {"Balance": nuevo_balance})
            if not exito:
                print(f"Error al actualizar balance para usuario {user_id_str}")
        else:
            # Crear usuario básico si no existe
            campos_usuario = {
                'id': user_id_str,
                'nombre': f'Usuario{user_id_str}',
                'Balance': nuevo_balance,
                'Referidos': 0,
                'Lider': 0,
                'total_ganado_ref': 0,
                'Medalla': 'Sin medalla',
                'marca': ''
            }
            exito = insertar_registro("usuarios", campos_usuario)
            if not exito:
                print(f"Error al crear usuario {user_id_str}")
                
    except Exception as e:
        print(f"Error en actualizar_balance_usuario: {str(e)}")

async def actualizar_bono_usuario(user_id, nuevo_bono):
    """Actualiza el bono de apuesta de un usuario en la base de datos"""
    try:
        user_id_str = str(user_id)
        
        # Verificar si el bono existe
        bono_existente = obtener_registro("bono_apuesta", user_id_str, "bono")
        
        if bono_existente:
            # Actualizar bono existente
            exito = actualizar_registro("bono_apuesta", user_id_str, {"bono": nuevo_bono})
            if not exito:
                print(f"Error al actualizar bono para usuario {user_id_str}")
        else:
            # Crear registro de bono si no existe
            campos_bono = {
                'id': user_id_str,
                'bono': nuevo_bono,
                'rollover_requerido': 0,
                'rollover_actual': 0,
                'bono_retirable': 0
            }
            exito = insertar_registro("bono_apuesta", campos_bono)
            if not exito:
                print(f"Error al crear bono para usuario {user_id_str}")
                
    except Exception as e:
        print(f"Error en actualizar_bono_usuario: {str(e)}")

@app.route('/confirmar_apuesta')
def confirmar_apuesta():
    return render_template('confirmar_apuesta.html')                                
    

@app.route('/api/verificar-apuesta', methods=['POST'])
async def api_verificar_apuesta():
    """Verifica una apuesta antes de confirmarla - VERSIÓN MEJORADA"""
    try:
        data = request.get_json()
        print(f"📨 Datos de verificación recibidos: {data}")
        
        # Validar datos requeridos
        required_fields = ['eventoId', 'market', 'selection', 'odd', 'deporte']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        # Extraer datos
        event_id = data['eventoId']
        market_key = data['market']
        selection_text = data['selection']
        cuota_original = float(data['odd'])
        deporte = data['deporte']
        point = data.get('point')
        
        print(f"🔍 Verificando apuesta - Deporte: {deporte}, Evento: {event_id}")
        
        # Crear estructura de apuesta
        apuesta_seleccionada = {
            'event_id': event_id,
            'tipo_apuesta': market_key,
            'seleccion': selection_text,
            'cuota': cuota_original,
            'point': point
        }

        # Verificar si 'deporte' es un nombre de deporte o un número (como sportKey)
        if isinstance(deporte, str) and deporte.lower() in ['soccer', 'fútbol', 'futbol']:
            resultado = await verificar_apuesta_futbol_web(apuesta_seleccionada)
        elif deporte.isdigit():  # Si es un número (sportKey)
            resultado = await verificar_apuesta_futbol_web(apuesta_seleccionada)
        else:
            resultado = await verificar_apuesta_odds_web(apuesta_seleccionada, deporte)
        
        print(f"🔍 Resultado de verificación: {resultado}")
    
 
        
        if resultado.get('status') == 'ok':
            return jsonify({
                'success': True,
                'message': resultado.get('message', '✅ Apuesta verificada'),
                'cuota_actual': resultado.get('cuota_actual'),
                'detalles': resultado.get('detalles', {})
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', '❌ La apuesta no se ha podido verificar')
            })
        
    except Exception as e:
        print(f"❌ Error en api_verificar-apuesta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error interno al verificar la apuesta',
            'error': str(e)
        }), 500

async def verificar_apuesta_futbol_web(apuesta_seleccionada: dict) -> dict:
    TOLERANCIA_CUOTA = 0.05
    TOLERANCIA_POINT = 0.01  
    print(f"🔍🔍🔍 VERIFICAR_APUESTA_FUTBOL_WEB - INICIO 🔍🔍🔍")
    print(f"✅✅✅ Apuesta seleccionada recibida: {apuesta_seleccionada}")

    def normalizar_seleccion_simple(market_key, selection_text, home_team, away_team):
        """
        Normalización simplificada que mantiene el texto original para mercados con punto
        """
        def eliminar_emojis(texto):
            return re.sub(r'[\U00010000-\U0010ffff]', '', texto)

        clean_text = eliminar_emojis(selection_text).strip()
        
        # Para mercados con punto, mantener el texto original
        if market_key in MERCADOS_CON_POINT:
            return clean_text
        
        # Para otros mercados, aplicar normalización existente
        clean_text = clean_text.lower()
        
        # Caso especial para Double Chance
        if market_key.lower() in ["double chance", "doble oportunidad"]:
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
                    if part == '1x':
                        normalized_parts.extend(['home', 'draw'])
                    elif part == 'x2':
                        normalized_parts.extend(['draw', 'away'])
                    elif part == '12':
                        normalized_parts.extend(['home', 'away'])
                    else:
                        normalized_parts.append(part)
            
            order = {'home': 0, 'draw': 1, 'away': 2}
            normalized_parts.sort(key=lambda x: order.get(x, 3))
            
            return '/'.join(normalized_parts)
        
        if clean_text in home_team.lower():
            return 'home'
        if clean_text in away_team.lower():
            return 'away'

        mapeo = {
            'home': 'home', 'local': 'home', '1': 'home',
            'away': 'away', 'visitante': 'away', '2': 'away',
            'draw': 'draw', 'empate': 'draw', 'x': 'draw', 'tie': 'draw'
        }

        return mapeo.get(clean_text, clean_text)

    try:
        
        # Obtener datos de la apuesta
        event_id = apuesta_seleccionada.get('event_id')
        #actuslizar los mercados
        resultado_actualizacion = await api_mercados_futbol(event_id)
        if isinstance(resultado_actualizacion, dict) and 'error' in resultado_actualizacion:
            return {'status': 'error', 'message': "❌ Error al actualizar mercados"}
        
        # Pequeña pausa para asegurar que el archivo se haya escrito
        await asyncio.sleep(2)

        event_key = f"evento_{event_id}"  
        
        market_key = apuesta_seleccionada.get('tipo_apuesta')  
        selection_text = apuesta_seleccionada.get('seleccion', '')  

        if not market_key or not selection_text:  
            return {'status': 'error', 'message': "❌ Datos incompletos de la apuesta vuelve a intentarlo"}  

        # Obtener evento desde el archivo JSON
        todos_mercados = cargar_mercados()
        evento = todos_mercados.get(event_key)
        
        if not evento:  
            return {'status': 'error', 'message': "❌ Evento no encontrado en los datos almacenados"}  
            
        # Verificación del estado del partido
        match_status = evento.get("evento_info", {}).get("fixture", {}).get("status", {})
        status_long = str(match_status.get("long", "")).lower()
        status_short = str(match_status.get("short", "")).lower()
        elapsed = match_status.get("elapsed", 0)
        print(f"[DEBUG] Estado: {status_long} | Short: {status_short} | Minuto: {elapsed}")

        # Verificar si el partido está avanzado
        if elapsed is not None and elapsed >= 90:
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
            
            
            
        # Obtener nombres de equipos
        home_team = evento.get("evento_info", {}).get("teams", {}).get("home", {}).get("name", "Home")  
        away_team = evento.get("evento_info", {}).get("teams", {}).get("away", {}).get("name", "Away")  
        # Verificar si el partido ha finalizado
        if (any(estado in status_long.lower() for estado in ESTADOS_FINALIZADOS) or
            any(estado in status_short.lower() for estado in ESTADOS_FINALIZADOS)):
            return {
        	    'status': 'error', 
           	 'message': f"⛔ Partido finalizado: {home_team} vs {away_team}"
        }
        
        # Usar la nueva normalización simplificada
        normalized_selection = normalizar_seleccion_simple(  
            market_key,   
            selection_text,  
            home_team,  
            away_team  
        )  
        
        point = apuesta_seleccionada.get('point')

        print(f"\n[DEBUG] DATOS DE BÚSQUEDA MEJORADOS:")  
        print(f"Market: {market_key}")  
        print(f"Original: '{selection_text}'")  
        print(f"Normalized: '{normalized_selection}'")  
        print(f"Point: {point}")  
        print(f"Teams: {home_team} vs {away_team}")  

        # BUSCAR EN LOS MERCADOS ALMACENADOS
        match_found = None
        mercado_encontrado = None
        
        # Buscar el mercado en la lista de mercados formateados
        for mercado in evento.get("mercados", []):
            if mercado.get("key", "").lower() == market_key.lower():
                mercado_encontrado = mercado
                break
                
        if not mercado_encontrado:
            print(f"[DEBUG] Mercado {market_key} no encontrado en mercados formateados")
            # Listar mercados disponibles para debug
            disponibles = [m.get("key") for m in evento.get("mercados", [])]
            print(f"[DEBUG] Mercados disponibles: {disponibles}")
            return {  
                'status': 'error',  
                'message': "🔒 Mercado no disponible. Intenta nuevamente en unos minutos.",  
                'debug_info': {  
                    'normalized': normalized_selection,  
                    'point': point,  
                    'teams': f"{home_team} vs {away_team}",
                    'mercados_disponibles': disponibles
                }  
            }  

        # Buscar la selección específica en las odds del mercado
        for odd in mercado_encontrado.get("odds", []):
            print(f"[DEBUG COMPARACIÓN] Analizando odd: {odd.get('value')} (point: {odd.get('point')})")  
            
            # Para mercados con point (Over/Under, Handicap)
            if market_key in MERCADOS_CON_POINT:
                # Comparación directa sin normalización excesiva
                odd_value = odd.get("value", "")
                
                # Si los valores coinciden exactamente
                if odd_value == normalized_selection:
                    match_found = odd
                    break
                    
                # Si no coinciden exactamente, intentar comparación flexible
                if (odd_value.lower() == normalized_selection.lower() or 
                    odd_value.replace(" ", "") == normalized_selection.replace(" ", "")):
                    match_found = odd
                    break
            # Para mercados sin point (Match Winner, etc.)
            else:
                if str(odd.get("value", "")).lower() == str(normalized_selection).lower():  
                    match_found = odd  
                    break  

        if not match_found:  
            # Debug: mostrar todas las odds disponibles en este mercado
            odds_disponibles = [f"{odd.get('value')} ({odd.get('point')})" for odd in mercado_encontrado.get("odds", [])]
            print(f"[DEBUG] Odds disponibles en {market_key}: {odds_disponibles}")
            return {  
                'status': 'error',  
                'message': "🔒 Selección no disponible en el mercado. Intenta nuevamente.",  
                'debug_info': {  
                    'normalized': normalized_selection,  
                    'point': point,  
                    'teams': f"{home_team} vs {away_team}",
                    'odds_disponibles': odds_disponibles
                }  
            }  

        if match_found.get('suspended', False):  
            return {  
                'status': 'error',  
                'message': "⛔ Cuota suspendida temporalmente.",  
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
        # 1. Extraer datos básicos del evento - CORREGIDO
        evento_info = evento.get("evento_info", {})
        if not evento_info:
            return {'anomalia': False, 'message': "Datos del evento incompletos"}
            
        fixture = evento_info.get("fixture", {})
        status = fixture.get("status", {})
        elapsed = status.get("elapsed")
        
        # Obtener marcador de teams o goals
        teams = evento_info.get("teams", {})
        goals = evento_info.get("goals", {})
        
        home_score = goals.get("home")
        away_score = goals.get("away")
        home_team = teams.get("home", {}).get("name", "")
        away_team = teams.get("away", {}).get("name", "")
        
        # 2. Validaciones básicas
        if not all([home_team, away_team]):
            return {'anomalia': False, 'message': "Nombres de equipos no disponibles"}
            
        if None in [elapsed, home_score, away_score]:
            return {'anomalia': False, 'message': "Datos del marcador incompletos"}

        print(f"[ANOMALIA DEBUG] Partido: {home_team} {home_score}-{away_score} {away_team} | Minuto: {elapsed}")
        print(f"[ANOMALIA DEBUG] Apuesta a: {apuesta_selection}")

        # 3. Determinar equipo líder
        leader_team = None
        if home_score > away_score:
            leader_team = home_team
        elif away_score > home_score:
            leader_team = away_team
        else:
            return {'anomalia': False, 'message': "Partido está empatado"}

        print(f"[ANOMALIA DEBUG] Líder actual: {leader_team}")

        # 4. Buscar cuota del líder en los mercados formateados
        def buscar_cuota_equipo(team_name):
            # Buscar en mercados formateados
            for mercado in evento.get("mercados", []):
                if mercado.get("key", "").lower() in ["fulltime result", "match winner", "ganador del partido"]:
                    for odd in mercado.get("odds", []):
                        odd_value = odd.get("value", "").lower()
                        team_name_lower = team_name.lower()
                        
                        # Comparar directamente o con mapeo home/away
                        if (odd_value == team_name_lower or 
                            (team_name_lower == home_team.lower() and odd_value == "home") or
                            (team_name_lower == away_team.lower() and odd_value == "away")):
                            return float(odd.get("odd", 0))
            return None

        leader_odds = buscar_cuota_equipo(leader_team)

        if leader_odds is None:
            # Intentar búsqueda alternativa
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

        print(f"[ANOMALIA DEBUG] Cuota del líder {leader_team}: {leader_odds}")

        # 5. Detección de anomalía - AJUSTAR UMBRAL SEGÚN NECESIDAD
        ANOMALIA_THRESHOLD = 1.9  # Ajustado para detectar cuotas muy bajas
        is_apuesta_al_lider = (
            str(apuesta_selection).lower() == str(leader_team).lower() or
            (apuesta_selection.lower() == "home" and leader_team == home_team) or
            (apuesta_selection.lower() == "away" and leader_team == away_team)
        )
        
        is_anomalia = is_apuesta_al_lider and leader_odds >= ANOMALIA_THRESHOLD

        debug_info = {
            'current_score': f"{home_score}-{away_score}",
            'minute': elapsed,
            'leader_team': leader_team,
            'apuesta_a': apuesta_selection,
            'leader_odds': leader_odds,
            'threshold': ANOMALIA_THRESHOLD,
            'is_apuesta_al_lider': is_apuesta_al_lider,
            'is_anomaly': is_anomalia
        }

        print(f"[ANOMALIA DEBUG] Resultado: {debug_info}")

        return {
            'anomalia': is_anomalia,
            'message': (
                f"⚠️ ANOMALÍA DETECTADA: {leader_team} va ganando {home_score}-{away_score} al minuto {elapsed} con cuota SUSPECHOSAMENTE BAJA {leader_odds}" 
                if is_anomalia else 
                f"✅ Apuesta válida - {apuesta_selection} (Líder: {leader_team} con cuota {leader_odds})"
            ),
            'debug_info': debug_info
        }

    except Exception as e:
        error_msg = f"Error en verificación de anomalía: {str(e)}"
        print(f"[ERROR] detectar_anomalia_favorito: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'anomalia': False,
            'message': error_msg,
            'debug_info': {'error': str(e)}
        }
async def verificar_apuesta_odds_web(apuesta_seleccionada: dict, deporte: str) -> dict:
    TOLERANCIA_CUOTA = 0.05
    TOLERANCIA_POINT = 0.01  
    print(f"🔍🔍🔍 VERIFICAR_APUESTA_ODDS_WEB - INICIO 🔍🔍🔍")
    print(f"✅✅✅ Apuesta seleccionada recibida: {apuesta_seleccionada}")

    try:
        event_id = apuesta_seleccionada.get('event_id')
        market_key = apuesta_seleccionada.get('tipo_apuesta')
        selection_text = apuesta_seleccionada.get('seleccion', '')
        point = apuesta_seleccionada.get('point')

        if not event_id or not market_key or not selection_text:
            return {'status': 'error', 'message': "❌ Datos incompletos de la apuesta"}

        # PRIMERO: Obtener el sport_key del archivo mercados.json
        event_key = f"evento_{event_id}"
        todos_mercados = cargar_mercados()
        evento = todos_mercados.get(event_key, {})
        
        # Verificar si el evento existe y tiene api_response
        if not evento or 'api_response' not in evento:
            return {'status': 'error', 'message': "❌ Evento no encontrado en los datos almacenados"}
        
        sport_key = evento['api_response'].get('sport_key')
        if not sport_key:
            return {'status': 'error', 'message': "❌ No se pudo determinar el sport_key del evento"}
        
        print(f"🔍 [DEBUG] Sport key obtenido del archivo: {sport_key}")

        # ACTUALIZAR los mercados usando el sport_key que acabamos de obtener
        resultado_actualizacion = await api_mercados_odds(event_id)
        if isinstance(resultado_actualizacion, dict) and 'error' in resultado_actualizacion:
            return {'status': 'error', 'message': "❌ Error al actualizar mercados"}
        
        # Pequeña pausa para asegurar que el archivo se haya escrito
        await asyncio.sleep(0.1)

        # Obtener datos desde el archivo mercados.json (ahora actualizado)
        todos_mercados = cargar_mercados()
        evento = todos_mercados.get(event_key)
        
        if not evento:
            return {'status': 'error', 'message': "❌ Evento no encontrado en los datos almacenados"}

        # BUSCAR EN LOS MERCADOS ACTUALIZADOS
        mercados_disponibles = []
        
        # Para deportes no-fútbol (estructura con mercados_procesados)
        if 'mercados_procesados' in evento:
            print("🔍 Estructura detectada: DEPORTES NO-FÚTBOL")
            for mercado_procesado in evento.get('mercados_procesados', []):
                if mercado_procesado.get('key') == market_key:
                    mercados_disponibles = mercado_procesado.get('odds', [])
                    break
        
        if not mercados_disponibles:
            print(f"[DEBUG] Mercado {market_key} no encontrado en mercados procesados")
            # Listar mercados disponibles para debug
            disponibles = [m.get("key") for m in evento.get('mercados_procesados', [])]
            print(f"[DEBUG] Mercados disponibles: {disponibles}")
            return {  
                'status': 'error',  
                'message': f"🔒 Mercado {market_key} no disponible",  
                'debug_info': {  
                    'mercados_disponibles': disponibles
                }  
            }  

        # Buscar la selección en el mercado
        seleccion_encontrada = None
        
        for outcome in mercados_disponibles:
            # Para estructura de otros deportes
            if 'name' in outcome:
                nombre_outcome = outcome.get('name', '')
            else:
                continue
                
            # Comparar nombres (case insensitive para mayor flexibilidad)
            if nombre_outcome.lower() == selection_text.lower():
                # Para mercados con point (spreads, totals)
                if market_key in ['spreads', 'totals']:
                    punto_outcome = outcome.get('point')
                    if point and abs(float(punto_outcome or 0) - float(point)) <= TOLERANCIA_POINT:
                        seleccion_encontrada = outcome
                        break
                else:
                    seleccion_encontrada = outcome
                    break

        if not seleccion_encontrada:
            # Debug: mostrar todas las odds disponibles en este mercado
            odds_disponibles = [f"{outcome.get('name')}" for outcome in mercados_disponibles]
            print(f"[DEBUG] Odds disponibles en {market_key}: {odds_disponibles}")
            return {  
                'status': 'error',  
                'message': f"❌ Selección '{selection_text}' no disponible en el mercado {market_key}",  
                'debug_info': {  
                    'odds_disponibles': odds_disponibles
                }  
            }  

        # Obtener la cuota actual
        if 'price' in seleccion_encontrada:
            cuota_actual = float(seleccion_encontrada.get('price', 0))
        elif 'odd' in seleccion_encontrada:
            cuota_actual = float(seleccion_encontrada.get('odd', 0))
        else:
            return {'status': 'error', 'message': "❌ No se pudo obtener la cuota actual"}

        # Comparar cuotas
        cuota_original = float(apuesta_seleccionada.get('cuota', 0))
        diferencia = abs(cuota_actual - cuota_original)
        cambio = cuota_actual - cuota_original
        porcentaje = (diferencia / cuota_original) * 100

        if diferencia > TOLERANCIA_CUOTA:
            if cambio > 0:
                return {
                    'status': 'ok',
                    'message': f"📈 Cuota mejoró a {cuota_actual:.2f} (+{porcentaje:.1f}%)",
                    'cuota_actual': cuota_actual
                }
            else:
                return {
                    'status': 'error',
                    'message': f"⛔ La cuota cambió a {cuota_actual:.2f} (-{porcentaje:.1f}%). Vuelve a intentarlo",
                    'cuota_actual': cuota_actual
                }

        return {
            'status': 'ok',
            'message': "✅ Apuesta verificada",
            'cuota_actual': cuota_actual,
            'detalles': seleccion_encontrada
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
async def verificar_combinada_interna(apuesta_data):
    """Lógica interna para verificar una apuesta combinada"""
    try:
        # Validar datos requeridos
        if 'selecciones' not in apuesta_data or len(apuesta_data['selecciones']) < 2:
            return {
                'success': False,
                'message': 'Se requieren al menos 2 selecciones para una combinada'
            }
        
        if 'monto' not in apuesta_data or apuesta_data['monto'] <= 0:
            return {
                'success': False, 
                'message': 'Monto de apuesta inválido'
            }
        
        selecciones = apuesta_data['selecciones']
        monto = float(apuesta_data['monto'])
        cuota_total = float(apuesta_data.get('cuotaTotal', 1))
        
        resultados = []
        selecciones_invalidas = []
        selecciones_finalizadas = []  # ← NUEVA LISTA PARA PARTIDOS FINALIZADOS
        
        # Verificar cada selección individualmente
        for i, seleccion in enumerate(selecciones):
            try:
                required_fields = ['eventoId', 'market', 'selection', 'odd', 'deporte']
                for field in required_fields:
                    if field not in seleccion:
                        raise ValueError(f'Campo requerido faltante: {field}')
                
                apuesta_seleccionada = {
                    'event_id': seleccion['eventoId'],
                    'tipo_apuesta': seleccion['market'],
                    'seleccion': seleccion['selection'],
                    'cuota': float(seleccion['odd']),
                    'point': seleccion.get('point')
                }
                
                deporte = seleccion['deporte']
                
                # Verificar según el tipo de deporte
                if isinstance(deporte, str) and deporte.lower() in ['soccer', 'fútbol', 'futbol']:
                    resultado = await verificar_apuesta_futbol_web(apuesta_seleccionada)
                elif isinstance(deporte, str) and deporte.isdigit():
                    resultado = await verificar_apuesta_futbol_web(apuesta_seleccionada)
                else:
                    resultado = await verificar_apuesta_odds_web(apuesta_seleccionada, deporte)
                
                # DIFERENCIAR ENTRE ERRORES Y PARTIDOS FINALIZADOS
                if resultado.get('status') == 'error':
                    mensaje_error = resultado.get('message', '').lower()
                    
                    # DETECTAR SI ES POR PARTIDO FINALIZADO
                    if any(palabra in mensaje_error for palabra in ['finalizado', 'finished', 'cancelado', 'canceled', 'avanzado']):
                        selecciones_finalizadas.append({
                            'index': i,
                            'market': seleccion['market'],
                            'selection': seleccion['selection'],
                            'reason': resultado.get('message', 'Partido finalizado'),
                            'event_id': seleccion['event_id']
                        })
                    else:
                        # ERROR REAL (cuota cambiada, mercado no disponible, etc.)
                        selecciones_invalidas.append({
                            'index': i,
                            'market': seleccion['market'],
                            'selection': seleccion['selection'],
                            'reason': resultado.get('message', 'Error en la verificación'),
                            'event_id': seleccion['event_id']
                        })
                
                # Si está ok, la selección es válida
                resultados.append(resultado)
                
            except Exception as e:
                print(f"❌ Error verificando selección {i}: {str(e)}")
                selecciones_invalidas.append({
                    'index': i,
                    'market': seleccion.get('market', ''),
                    'selection': seleccion.get('selection', ''),
                    'reason': f'Error de verificación: {str(e)}',
                    'event_id': seleccion.get('event_id', '')
                })
        
        # VERIFICAR SI HAY SELECCIONES CON PROBLEMAS
        if selecciones_invalidas or selecciones_finalizadas:
            return {
                'success': False,
                'message': 'Problemas con algunas selecciones',
                'seleccionesInvalidas': selecciones_invalidas,
                'seleccionesFinalizadas': selecciones_finalizadas,  # ← INFORMAR PARTIDOS FINALIZADOS POR SEPARADO
                'totalSelecciones': len(selecciones),
                'seleccionesValidas': len(selecciones) - len(selecciones_invalidas) - len(selecciones_finalizadas)
            }

        
        # Todas las verificaciones pasaron
        return {
            'success': True,
            'message': 'Combinada verificada correctamente',
            'data': {
                'monto': monto,
                'cuotaTotal': cuota_total,
                'gananciaPotencial': monto * cuota_total,
                'numeroSelecciones': len(selecciones),
                'timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Error general en verificación de combinada: {str(e)}")
        return {
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }

async def _crear_estructura_apuesta_no_futbol(apuesta_data, user_id, user_data):
    """Crea la estructura completa de datos de la apuesta para deportes no-fútbol"""
    
    try:
        # Obtener el nombre real del usuario desde la base de datos
        user_id_str = str(user_id)
        usuario_db = obtener_registro("usuarios", user_id_str, "nombre")
        
        if usuario_db:
            nombre_usuario = usuario_db[0] or "Usuario"
        else:
            nombre_usuario = user_data.get('Nombre', 'Usuario')
        
        # Datos de la apuesta desde el frontend
        market_key = apuesta_data.get('market')
        selection = apuesta_data.get('selection')
        odd = float(apuesta_data.get('odd', 1))
        monto = apuesta_data.get('monto', 0)
        point = apuesta_data.get('point', '')
        event_id = apuesta_data.get('event_id')
        deporte = apuesta_data.get('deporte', '')
        evento_data = apuesta_data.get('evento_data', {})
        betting_type = apuesta_data.get('betting_type', 'PREPARTIDO')
        metodo_pago = apuesta_data.get('metodo_pago', 'balance')
        
        # Obtener datos del archivo mercados.json
        try:
            with open("mercados.json", "r") as file:
                mercados = json.load(file)
        except Exception as e:
            print(f"❌ Error cargando mercados.json: {e}")
            mercados = {}
        
        evento_key = f"evento_{event_id}"
        
        if evento_key not in mercados:
            return {"error": "Evento no encontrado en mercados.json"}
        
        evento = mercados[evento_key]
        
        # Para no-fútbol, la información del evento está en 'api_response'
        evento_info = evento.get("api_response", {})
        if not evento_info:
            return {"error": "Información del evento no disponible."}
        
        # Extraer información del evento
        sport_title = evento_info.get("sport_title", "Deporte Desconocido")
        sport_key = (
            evento_data.get("sport_key") 
            or evento_info.get("sport_key") 
            or deporte
        )
        home_team = evento_info.get("home_team", "Local")
        away_team = evento_info.get("away_team", "Visitante")
        commence_time = evento_info.get("commence_time", "")
        
        # Formatear fecha
        fecha_inicio = "Fecha inválida"
        if commence_time:
            try:
                fecha_dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                fecha_inicio = fecha_dt.strftime("%d/%m/%Y %H:%M:%S")
                fecha_inicio_cuba = fecha_dt - timedelta(hours=4)
                fecha_inicio = fecha_inicio_cuba.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                pass
        
        partido = f"{home_team} 🆚 {away_team}"
        
        config_mercado = CONFIG_MERCADOS.get(market_key, {})
        tipo_apuesta_desc = config_mercado.get('nombre', market_key)  # Nombre del mercado
        emoji_mercado = config_mercado.get('emoji', '🎯')
        print(f"🔧 Configuración del mercado: {config_mercado}")
        
        # Formatear selección según tipo de mercado
        if point == '':
            point = None
            
        if market_key in ['spreads', 'totals'] and point:
            favorito_desc = f"{selection} {point}"
        else:
            favorito_desc = selection

        # Añadir emoji del mercado al inicio
        favorito_desc = f"{emoji_mercado} {favorito_desc}"
        print(f"🎯 Selección formateada: {favorito_desc}")

        # Betting Type (siempre PREPARTIDO para no-fútbol en este ejemplo)
        betting_type = "PREPARTIDO"
        
        id_ticket = generar_id()     

        # Crear la estructura final de la apuesta
        apuesta_estructura = {
            "event_id": event_id,
            "usuario_id": user_id_str,
            "fecha_realizada": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "fecha_inicio": fecha_inicio,
            "liga": sport_title,  # Usamos el nombre del deporte como liga
            "partido": partido,
            "favorito": favorito_desc,
            "monto": monto,
            "cuota": odd,
            "ganancia": round(monto * odd, 2),
            "estado": "⌛Pendiente",
            "bono": 0 if metodo_pago != "bono" else monto,
            "balance": monto if metodo_pago != "bono" else 0,
            "id_ticket": id_ticket,
            "betting": betting_type,
            "home_logo": "",  # No hay logos en la estructura de no-fútbol por ahora
            "away_logo": "",
            "mensaje_canal_url": "https://t.me/taskCUBA",
            "user_name": nombre_usuario,  # ✅ NOMBRE CORRECTO DESDE LA DB
            "deporte": deporte,   # Deporte textual
            "sport_key": sport_key,  # ✅ Nuevo campo agregado
            "tipo_apuesta": tipo_apuesta_desc,  # ✅ NUEVO CAMPO AGREGADO - Nombre del mercado
            "selecciones": [],  # Campo necesario para la estructura de la base de datos
            "scores": []  # Campo necesario para la estructura de la base de datos
        }

        return apuesta_estructura

    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return {"error": f"Error inesperado: {str(e)}"}
async def crear_apuesta_web(apuesta_data, user_id, user_data):
    """Crea y guarda una apuesta en la base de datos (similar al bot)"""
    try:
        # Obtener el deporte de los datos de la apuesta
        deporte = apuesta_data.get('deporte', 'soccer').lower()
        
        # Elegir la función de estructura basada en el deporte
        if deporte in ['soccer', 'fútbol', 'futbol']:
            apuesta = await _crear_estructura_apuesta_futbol(apuesta_data, user_id, user_data)
        else:
            apuesta = await _crear_estructura_apuesta_no_futbol(apuesta_data, user_id, user_data)
        
        # Verificar si hubo error en la creación
        if 'error' in apuesta:
            print(f"❌ Error creando estructura: {apuesta['error']}")
            return {'status': 'error', 'message': "❌ Error creando estructura"}

        # Guardar en la base de datos
        exito = guardar_apuesta_en_db(apuesta)
        
        if not exito:
            print("❌ Error guardando apuesta en la base de datos")
            return {'status': 'error', 'message': "❌ Error guardando apuesta"}
        
        print(f"✅ Apuesta guardada en base de datos - ID Ticket: {apuesta.get('id_ticket')}")
        return apuesta
        
    except Exception as e:
        print(f"❌ Error guardando apuesta: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}
async def _crear_estructura_apuesta_futbol(apuesta_data, user_id, user_data):
    """Crea la estructura completa de datos de la apuesta (versión FUTBOL)"""
    
    try:
        # Obtener el nombre real del usuario desde la base de datos
        user_id_str = str(user_id)
        usuario_db = obtener_registro("usuarios", user_id_str, "nombre")
        
        if usuario_db:
            nombre_usuario = usuario_db[0] or "Usuario"
        else:
            nombre_usuario = user_data.get('Nombre', 'Usuario')

        # Datos de la apuesta desde el frontend
        market_key = apuesta_data.get('market')
        selection = apuesta_data.get('selection')
        odd = float(apuesta_data.get('odd', 1))
        monto = apuesta_data.get('monto', 0)
        point = apuesta_data.get('point', '')
        event_id = apuesta_data.get('event_id')
        evento_data = apuesta_data.get('evento_data', {})
        betting_type = apuesta_data.get('betting_type', 'PREPARTIDO')
        metodo_pago = apuesta_data.get('metodo_pago', 'balance')
        
        # PRIMERO intentar obtener datos del archivo mercados.json
        print("🔄 Obteniendo datos del evento desde mercados.json...")
        try:
            with open("mercados.json", "r") as file:
                mercados = json.load(file)
        except Exception as e:
            print(f"❌ Error cargando mercados.json: {e}")
            mercados = {}
        
        evento_key = f"evento_{event_id}"
        
        # SI no encontramos en el archivo, usar los datos que ya tenemos
        if evento_key not in mercados:
            print(f"⚠️ Evento no encontrado en mercados.json, usando datos de la API")
            evento_info = evento_data
        else:
            evento_info = mercados[evento_key].get("evento_info", {})
        
        if not evento_info:
            return {"error": "Información del evento no disponible."}
        
        # Fecha de inicio
        fecha_inicio = evento_info.get("fixture", {}).get("date", "")
        if fecha_inicio:
            try:
                fecha_dt = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
                fecha_inicio_cuba = fecha_dt - timedelta(hours=4)
        
        
                fecha_inicio = fecha_inicio_cuba.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                fecha_inicio = "Fecha inválida"
        
        # Liga
        liga = evento_info.get("league", {}).get("name", "Liga Desconocida")
        
        # Equipos y partido
        home_team = evento_info.get("teams", {}).get("home", {}).get("name", "Local")
        away_team = evento_info.get("teams", {}).get("away", {}).get("name", "Visitante")
        partido = f"{home_team} 🆚 {away_team}"
        
        config_mercado = CONFIG_MERCADOS.get(market_key, {})
        tipo_apuesta_desc = config_mercado.get('nombre', market_key)  # Nombre del mercado
        emoji_mercado = config_mercado.get('emoji', '🎯')
        print(f"🔧 Configuración del mercado: {config_mercado}")
        
        # Formatear selección según tipo de mercado
        print("🔄 Formateando selección según el tipo de mercado...")
        
        # ✅ NUEVO: Reemplazar "home" y "away" con nombres reales de equipos
        selection_formateada = selection
        if selection.lower() == 'home':
            selection_formateada = home_team
        elif selection.lower() == 'away':
            selection_formateada = away_team
        elif selection.lower() == 'draw':
            selection_formateada = 'Empate'
        
        # CORRECCIÓN: Manejar point vacío o nulo
        if point == '':
            point = None
            
        # CORRECCIÓN: Usar favorito_desc en lugar de favorito (que no existe)
        if market_key in MERCADOS_CON_POINT and point:
            favorito_desc = f"{selection_formateada} {point}"
        elif market_key == "btts":
            favorito_desc = "Sí" if selection_formateada.lower() == "yes" else "No"
        elif market_key in ["player_goal_scorer_anytime", 
                           "player_first_goal_scorer",
                           "player_last_goal_scorer"]:
            favorito_desc = selection_formateada
        else:
            favorito_desc = selection_formateada

        # Añadir emoji del mercado al inicio
        favorito_desc = f"{emoji_mercado} {favorito_desc}"
        print(f"🎯 Selección formateada: {favorito_desc}")

        
        # Obtener logo de los equipos
        home_logo = evento_info.get("teams", {}).get("home", {}).get("logo", "")
        away_logo = evento_info.get("teams", {}).get("away", {}).get("logo", "")
        
        # Betting Type (LIVE o PREPARTIDO)
        status = evento_info.get("fixture", {}).get("status", {}).get("short", "PREPARTIDO")
        betting_type = "LIVE" if status in ["LIVE", "1H", "2H", "HT"] else "PREPARTIDO"
        
        # Obtener minuto y marcador si el evento está en vivo
        minuto = ""
        marcador = ""
        if betting_type == "LIVE":
            # Obtener minuto del partido
            minuto = evento_info.get('fixture', {}).get('status', {}).get('elapsed', '')
            # Obtener marcador
            home_goals = evento_info.get('goals', {}).get('home', 0)
            away_goals = evento_info.get('goals', {}).get('away', 0)
            marcador = f"{home_goals}-{away_goals}"
        
        id_ticket = generar_id()     

        # Crear la estructura final de la apuesta
        apuesta_estructura = {
            "event_id": event_id,
            "usuario_id": user_id_str,
            "fecha_realizada": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "fecha_inicio": fecha_inicio,
            "liga": liga,
            "deporte": "FUTBOL⚽",
            "sport_key": "soccer",
            "partido": partido,
            "favorito": favorito_desc,
            "monto": monto,
            "cuota": odd,
            "ganancia": round(monto * odd, 2),
            "estado": "⌛Pendiente",
            "bono": 0 if metodo_pago != "bono" else monto,
            "balance": monto if metodo_pago != "bono" else 0,
            "id_ticket": id_ticket,
            "betting": betting_type,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "mensaje_canal_url": "https://t.me/taskCUBA",
            "user_name": nombre_usuario,  # ✅ NOMBRE CORRECTO DESDE LA DB
            "tipo_apuesta": tipo_apuesta_desc,
            "minuto": minuto,
            "marcador": marcador,
            "selecciones": [],  
            "scores": []  
        }        
        return apuesta_estructura

    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return {"error": f"Error inesperado: {str(e)}"}

async def _crear_estructura_apuesta_combinada(apuesta_data, user_id, user_data, selecciones):
    """Crea la estructura completa de datos de la apuesta combinada"""
    print("🔄 Iniciando creación de estructura de apuesta combinada...")

    try:
        # Obtener el nombre real del usuario desde la base de datos
        user_id_str = str(user_id)
        usuario_db = obtener_registro("usuarios", user_id_str, "nombre")
        
        if usuario_db:
            nombre_usuario = usuario_db[0] or "Usuario"
        else:
            nombre_usuario = user_data.get('Nombre', 'Usuario')

        # Datos de la apuesta desde el frontend
        monto = apuesta_data.get('monto', 0)
        cuota_total = float(apuesta_data.get('cuotaTotal', 1))
        metodo_pago = apuesta_data.get('metodo_pago', 'balance')
        
        # Procesar cada selección
        selecciones_procesadas = []
        
        for seleccion in selecciones:
            event_id = seleccion.get('eventoId')
            market_key = seleccion.get('market')
            selection_text = seleccion.get('selection')
            point = seleccion.get('point') or ''  # si es None → string vacío
            cuota_individual = float(seleccion.get('odd', 1))
            deporte = seleccion.get('deporte', 'Desconocido')
            
            # Asegurarse que market_key sea string
            market_key_str = str(market_key) if market_key is not None else "desconocido"
            
            # Obtener información del evento según el tipo de deporte
            evento_key = f"evento_{event_id}"
            todos_mercados = cargar_mercados()
            evento = todos_mercados.get(evento_key, {})
            
            # OBTENER EL SPORT_KEY CORRECTO
            sport_key = "unknown"
            if 'api_response' in evento:  # Deportes no-fútbol
                evento_info = evento.get('api_response', {})
                sport_key = evento_info.get('sport_key', deporte)
                liga = evento_info.get('sport_title', 'Liga Desconocida')
                home_team = evento_info.get('home_team', 'Local')
                away_team = evento_info.get('away_team', 'Visitante')
                commence_time = evento_info.get('commence_time', '')
                
                # Formatear fecha
                fecha_inicio = "Fecha inválida"
                if commence_time:
                    try:
                        fecha_dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                        fecha_inicio = fecha_dt.strftime("%d/%m/%Y %H:%M:%S")
                        fecha_inicio_cuba = fecha_dt - timedelta(hours=4)
                        fecha_inicio = fecha_inicio_cuba
                    except ValueError:
                        pass
            else:  # Fútbol
                evento_info = evento.get('evento_info', {})
                sport_key = "soccer"
                liga = evento_info.get('league', {}).get('name', 'Liga Desconocida')
                home_team = evento_info.get('teams', {}).get('home', {}).get('name', 'Local')
                away_team = evento_info.get('teams', {}).get('away', {}).get('name', 'Visitante')
                fecha_fixture = evento_info.get('fixture', {}).get('date', '')
                
                # Formatear fecha
                fecha_inicio = "Fecha inválida"
                if fecha_fixture:
                    try:
                        fecha_dt = datetime.fromisoformat(fecha_fixture.replace("Z", "+00:00"))
                        fecha_inicio_cuba = fecha_dt - timedelta(hours=4)   # ✅ Restar al datetime, no al string
                        fecha_inicio = fecha_inicio_cuba.strftime("%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        pass
            
            partido = f"{home_team} vs {away_team}"
            
            # Obtener nombre del mercado
            config_mercado = CONFIG_MERCADOS.get(market_key_str, {})
            nombre_mercado = config_mercado.get('nombre', market_key_str)
            
            # Formatear selección
            if market_key_str in MERCADOS_CON_POINT and point:
                favorito = f"{selection_text} {point}"
            else:
                favorito = selection_text
            
            # Añadir emoji del mercado
            emoji_mercado = config_mercado.get('emoji', '🎯')
            favorito = f"{emoji_mercado} {favorito}"
            
            # Crear estructura de selección
            seleccion_procesada = {
                "event_id": event_id,
                "sport_key": sport_key,
                "deporte": deporte,
                "liga": liga,
                "partido": partido,
                "mercado": nombre_mercado,
                "favorito": favorito,
                "cuota_individual": cuota_individual,
                "fecha_inicio": fecha_inicio,
                "estado": "⌛Pendiente"
            }
            
            selecciones_procesadas.append(seleccion_procesada)
        
        # Generar ID único para el ticket
        id_ticket = generar_id()
        
        # Crear la estructura final de la apuesta combinada
        apuesta_estructura = {
            "usuario_id": user_id_str,
            "user_name": nombre_usuario,  # ✅ NOMBRE CORRECTO DESDE LA DB
            "fecha_realizada": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "monto": monto,
            "cuota": cuota_total,
            "ganancia": round(monto * cuota_total, 2),
            "estado": "⌛Pendiente",
            "bono": 0 if metodo_pago != "bono" else monto,
            "balance": monto if metodo_pago != "bono" else 0,
            "betting": "COMBINADA",
            "id_ticket": id_ticket,
            "selecciones": selecciones_procesadas,
            "scores": []  # ✅ CAMPO NECESARIO PARA LA DB
        }

        
        return apuesta_estructura

    except Exception as e:
        print(f"❌ Error inesperado creando apuesta combinada: {str(e)}")
        return {"error": f"Error inesperado: {str(e)}"}
        
@app.route('/api/realizar-combinada', methods=['POST'])
async def realizar_apuesta_combinada():
    """Crea y guarda una apuesta combinada con flujo completo"""
    try:
        data = request.get_json()
        print(f"📨 Datos de combinada recibidos: {json.dumps(data, indent=2)}")
        
        # Validar datos requeridos
        if 'selecciones' not in data or len(data['selecciones']) < 2:
            return jsonify({
                'success': False,
                'message': 'Se requieren al menos 2 selecciones para una combinada'
            }), 400
        
        # Obtener user_id
        user_id = get_telegram_user_id()
        if not user_id:
            return jsonify({'success': False, 'message': 'Usuario no identificado'}), 401
            
        # Obtener datos del usuario
        user_data = await obtener_datos_usuario(user_id)
        
        # ✅ VERIFICAR PRIMERO LA COMBINADA ANTES DE PROCESAR
        verificacion = await verificar_combinada_interna(data)
        if not verificacion['success']:
            return jsonify(verificacion), 400
        
        # 1. Verificar disponibilidad de fondos
        monto = float(data['monto'])
        metodo_pago = data['metodo_pago']
        
        verificacion_fondos = await verificar_fondos_usuario(user_id, monto, metodo_pago)
        if not verificacion_fondos['success']:
            return jsonify(verificacion_fondos), 400

        # 2. Procesar el pago
        resultado_pago = await procesar_pago(user_id, monto, metodo_pago)
        if not resultado_pago['success']:
            return jsonify(resultado_pago), 400

        # 3. Crear estructura de apuesta
        apuesta = await _crear_estructura_apuesta_combinada(data, user_id, user_data, data['selecciones'])
        if 'error' in apuesta:
            return jsonify({'success': False, 'message': apuesta['error']}), 400

        # ✅ CORREGIDO: Guardar en base de datos en lugar de JSON
        exito = guardar_apuesta_en_db(apuesta)
        if not exito:
            return jsonify({
                'success': False, 
                'message': 'Error al guardar la apuesta en la base de datos'
            }), 500

        # Aplicar bono de referido
        await aplicar_bono_referido(user_id, monto, metodo_pago)

        # Enviar notificación
        await enviar_notificacion_apuesta_web(apuesta, user_data)

        return jsonify({
            'success': True,
            'message': '✅ Apuesta combinada realizada con éxito',
            'data': apuesta,
            'nuevo_balance': resultado_pago.get('nuevo_balance'),
            'nuevo_bono': resultado_pago.get('nuevo_bono')
        }), 200
        
    except Exception as e:
        print(f"❌ Error en realizar_apuesta_combinada: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor al procesar la apuesta combinada'
        }), 500
# Función auxiliar síncrona para obtener datos del usuario
def obtener_datos_usuario_sync(user_id):
    """Versión síncrona de obtener_datos_usuario"""
    try:
        user_id_str = str(user_id)
        usuario_data = obtener_registro("usuarios", user_id_str, 
                                      "nombre, Email, Password, Balance, Lider, Referidos, "
                                      "total_ganado_ref, Medalla, Username")
        
        bono_data = obtener_registro("bono_apuesta", user_id_str,
                                   "bono, rollover_requerido, rollover_actual, bono_retirable")
        
        if usuario_data:
            nombre, email, password, balance, lider, referidos, total_ganado_ref, medalla, username = usuario_data
        else:
            nombre, email, password, balance, lider, referidos, total_ganado_ref, medalla, username = (
                f'Usuario{user_id_str}', '', '', 0, None, 0, 0, 'Sin medalla', ''
            )
        
        if bono_data:
            bono, rollover_requerido, rollover_actual, bono_retirable = bono_data
        else:
            bono, rollover_requerido, rollover_actual, bono_retirable = 0, 0, 0, 0
        
        return {
            'user_id': user_id_str,
            'nombre': nombre or f'Usuario{user_id_str}',
            'email': email or '',
            'password': password or '',
            'balance': balance or 0,
            'bono': bono or 0,
            'referido_por': lider,
            'referidos': referidos or 0,
            'total_ganado_ref': total_ganado_ref or 0,
            'medalla': medalla or 'Sin medalla',
            'rollover_requerido': rollover_requerido or 0,
            'rollover_actual': rollover_actual or 0,
            'bono_retirable': bono_retirable or 0
        }
        
    except Exception as e:
        print(f"Error en obtener_datos_usuario_sync: {e}")
        return {
            'user_id': str(user_id),
            'nombre': f'Usuario{user_id}',
            'email': '',
            'password': '',
            'balance': 0,
            'bono': 0,
            'referido_por': None,
            'referidos': 0,
            'total_ganado_ref': 0,
            'medalla': 'Sin medalla',
            'rollover_requerido': 0,
            'rollover_actual': 0,
            'bono_retirable': 0
        }

# Función auxiliar síncrona para crear estructura de apuesta combinada
def crear_estructura_apuesta_combinada_sync(apuesta_data, user_id, user_data, selecciones):
    """Versión síncrona de _crear_estructura_apuesta_combinada"""
    try:
        # Obtener el nombre real del usuario desde la base de datos
        user_id_str = str(user_id)
        usuario_db = obtener_registro("usuarios", user_id_str, "nombre")
        
        if usuario_db:
            nombre_usuario = usuario_db[0] or "Usuario"
        else:
            nombre_usuario = user_data.get('nombre', 'Usuario')

        # Datos de la apuesta desde el frontend
        monto = apuesta_data.get('monto', 0)
        cuota_total = float(apuesta_data.get('cuotaTotal', 1))
        metodo_pago = apuesta_data.get('metodo_pago', 'balance')
        
        # Procesar cada selección (código igual que antes)
        selecciones_procesadas = []
        for seleccion in selecciones:
            # ... (mismo código de procesamiento de selecciones)
            pass
        
        # Generar ID único para el ticket
        id_ticket = generar_id()
        
        # Crear la estructura final de la apuesta combinada
        apuesta_estructura = {
            "usuario_id": user_id_str,
            "user_name": nombre_usuario,
            "fecha_realizada": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "monto": monto,
            "cuota": cuota_total,
            "ganancia": round(monto * cuota_total, 2),
            "estado": "⌛Pendiente",
            "bono": 0 if metodo_pago != "bono" else monto,
            "balance": monto if metodo_pago != "bono" else 0,
            "betting": "COMBINADA",
            "id_ticket": id_ticket,
            "selecciones": selecciones_procesadas,
            "scores": []
        }

        print(f"✅ Estructura de apuesta combinada creada: {apuesta_estructura}")
        return apuesta_estructura

    except Exception as e:
        print(f"❌ Error inesperado creando apuesta combinada: {str(e)}")
        return {"error": f"Error inesperado: {str(e)}"}



# Endpoints para el juego de dominó
@app.route('/domino')
def domino():
    return render_template('domino.html')
                        
# Ruta para la página de la ruleta
@app.route('/ruleta')
def ruleta():
    return render_template('ruleta.html')


# Función para obtener un premio aleatorio basado en probabilidades
def obtener_premio_ruleta():
    premios = [
        {'id': 1, 'tipo': 'balance', 'cantidad': 5, 'probabilidad': 10, 'nombre': '+5 Balance'},
        {'id': 2, 'tipo': 'balance', 'cantidad': 500, 'probabilidad': 0, 'nombre': '+500 Balance'},
        {'id': 3, 'tipo': 'balance', 'cantidad': 50, 'probabilidad': 1, 'nombre': '+50 Balance'},
        {'id': 4, 'tipo': 'bono', 'cantidad': 100, 'probabilidad': 20, 'nombre': '+100 Bono'},
        {'id': 5, 'tipo': 'bono', 'cantidad': 50, 'probabilidad': 20, 'nombre': '+50 Bono'},
        {'id': 6, 'tipo': 'tiros', 'cantidad': 1, 'probabilidad': 20, 'nombre': '+1 Tiro Gratis'},
        {'id': 7, 'tipo': 'tiros', 'cantidad': 3, 'probabilidad': 10, 'nombre': '+3 Tiros Gratis'},
        {'id': 8, 'tipo': 'nada', 'cantidad': 0, 'probabilidad': 16, 'nombre': 'Sin Premio'}
    ]
    
    # Calcular el total de probabilidades
    total_prob = sum(p['probabilidad'] for p in premios)
    
    # Generar un número aleatorio
    rand = random.randint(1, total_prob)
    
    # Encontrar el premio correspondiente
    acumulado = 0
    for premio in premios:
        acumulado += premio['probabilidad']
        if rand <= acumulado:
            return premio
    
    # Por defecto, devolver "Sin premio"
    return premios[-1]



# Función auxiliar específica para la tabla ruleta
def obtener_ruleta_usuario(user_id):
    """Obtiene los datos de ruleta para un usuario específico"""
    try:
        user_id_str = str(user_id)
        consulta = "SELECT tiros_restantes, ultimo_giro, proximo_reinicio FROM ruleta WHERE user_id = ?"
        resultado = ejecutar_consulta_segura(consulta, (user_id_str,), obtener_resultados=True)
        
        if resultado and len(resultado) > 0:
            return resultado[0]  # Devuelve la primera fila
        return None
    except Exception as e:
        print(f"Error en obtener_ruleta_usuario: {e}")
        return None

def actualizar_ruleta_usuario(user_id, campos_valores):
    """Actualiza los datos de ruleta para un usuario específico"""
    try:
        user_id_str = str(user_id)
        
        # Verificar si existe el registro
        existe = obtener_ruleta_usuario(user_id_str)
        
        if existe:
            # Actualizar registro existente
            set_campos = ", ".join([f"{campo} = ?" for campo in campos_valores.keys()])
            valores = list(campos_valores.values())
            consulta = f"UPDATE ruleta SET {set_campos} WHERE user_id = ?"
            valores.append(user_id_str)
            
            ejecutar_consulta_segura(consulta, tuple(valores))
            return True
        else:
            # Insertar nuevo registro
            campos_valores['user_id'] = user_id_str
            columnas = ", ".join(campos_valores.keys())
            placeholders = ", ".join(["?"] * len(campos_valores))
            valores = list(campos_valores.values())
            
            consulta = f"INSERT INTO ruleta ({columnas}) VALUES ({placeholders})"
            ejecutar_consulta_segura(consulta, tuple(valores))
            return True
            
    except Exception as e:
        print(f"Error en actualizar_ruleta_usuario: {e}")
        return False

# Función auxiliar para verificar y crear registro de ruleta si no existe
def verificar_ruleta_usuario(user_id):
    """Verifica si existe registro de ruleta para el usuario, si no existe lo crea"""
    try:
        user_id_str = str(user_id)
        ruleta_data = obtener_ruleta_usuario(user_id_str)
        
        print(f"🔍 Datos obtenidos de ruleta para {user_id_str}: {ruleta_data}")
        
        if ruleta_data is None:
            
            # Crear registro de ruleta nuevo
            proximo_reinicio = (datetime.now() + timedelta(hours=24)).isoformat()
            campos_ruleta = {
                'tiros_restantes': 3,
                'proximo_reinicio': proximo_reinicio
            }
            resultado = actualizar_ruleta_usuario(user_id_str, campos_ruleta)
            
            return resultado
        else:
            print("📋 Registro existente encontrado")
            # Verificar si es hora de reiniciar los tiros
            tiros_restantes, ultimo_giro, proximo_reinicio_str = ruleta_data
            
            if proximo_reinicio_str:
                try:
                    proximo_reinicio = datetime.fromisoformat(proximo_reinicio_str)
                    if datetime.now() >= proximo_reinicio:
                        
                        nuevo_proximo_reinicio = (datetime.now() + timedelta(hours=24)).isoformat()
                        resultado = actualizar_ruleta_usuario(user_id_str, {
                            'tiros_restantes': 3,
                            'proximo_reinicio': nuevo_proximo_reinicio,
                            'ultimo_giro': None
                        })
                        
                        return resultado
                except ValueError as e:
                    print(f"⚠️ Error parsing date {proximo_reinicio_str}: {e}")
                    # Si el formato es inválido, corregirlo
                    nuevo_proximo_reinicio = (datetime.now() + timedelta(hours=24)).isoformat()
                    resultado = actualizar_ruleta_usuario(user_id_str, {
                        'proximo_reinicio': nuevo_proximo_reinicio,
                        'tiros_restantes': 3
                    })
                    
                    return resultado
            
        return True
        
    except Exception as e:
        print(f"❌ Error en verificar_ruleta_usuario: {e}")
        import traceback
        traceback.print_exc()
        return False

# API para obtener el estado de la ruleta del usuario
@app.route('/api/ruleta/estado')
def api_ruleta_estado():
    if 'user_id' not in flask_session:
        return jsonify({'error': 'No autenticado'}), 401
    
    user_id = flask_session['user_id']
    user_id_str = str(user_id)
    

    try:
      
        if not verificar_ruleta_usuario(user_id_str):
            print("❌ Error al verificar ruleta")
            return jsonify({'error': 'Error al cargar ruleta'}), 500

        
        ruleta_data = obtener_ruleta_usuario(user_id_str)
        
        print(f"📋 Datos crudos de ruleta: {ruleta_data}")
        
        if ruleta_data is None:
            print("❌ No se encontraron datos de ruleta después de verificación")
            return jsonify({'error': 'No se pudo crear registro de ruleta'}), 500
            
        tiros_restantes, ultimo_giro, proximo_reinicio_str = ruleta_data
                
        # Calcular tiempo restante
        tiempo_restante = 86400  # Valor por defecto: 24 horas
        
        if proximo_reinicio_str:
            try:
                proximo_reinicio = datetime.fromisoformat(proximo_reinicio_str)
                segundos_restantes = (proximo_reinicio - datetime.now()).total_seconds()
                tiempo_restante = max(0, int(segundos_restantes))
                
            except ValueError as e:
                print(f"⚠️ Error parsing date {proximo_reinicio_str}: {e}")
                # Formato inválido, establecer nuevo reinicio
                nuevo_reinicio = (datetime.now() + timedelta(hours=24)).isoformat()
                actualizar_ruleta_usuario(user_id_str, {'proximo_reinicio': nuevo_reinicio})
                tiempo_restante = 86400
    
      
        return jsonify({
            'tiros_restantes': tiros_restantes,
            'tiempo_restante': tiempo_restante
        })
        
    except Exception as e:
        print(f"💥 Error crítico en api_ruleta_estado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error interno del servidor'}), 500

# API para reiniciar tiros manualmente (si es necesario)
@app.route('/api/ruleta/reiniciar', methods=['POST'])
def api_ruleta_reiniciar():
    if 'user_id' not in flask_session:
        return jsonify({'error': 'No autenticado'}), 401
    
    user_id = flask_session['user_id']
    user_id_str = str(user_id)

    try:
        # Establecer nuevo reinicio para 24 horas después
        nuevo_reinicio = (datetime.now() + timedelta(hours=24)).isoformat()
        
        exito = actualizar_ruleta_usuario(user_id_str, {
            'tiros_restantes': 3,
            'proximo_reinicio': nuevo_reinicio,
            'ultimo_giro': None
        })
        
        if not exito:
            return jsonify({'error': 'Error al reiniciar ruleta'}), 500

        return jsonify({'success': True, 'tiros_restantes': 3})
        
    except Exception as e:
        print(f"Error en api_ruleta_reiniciar: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/ruleta/girar', methods=['POST'])
def api_ruleta_girar():
    if 'user_id' not in flask_session:
        return jsonify({'error': 'No autenticado'}), 401
    
    user_id = flask_session['user_id']
    user_id_str = str(user_id)

    try:
        # Verificar y actualizar ruleta primero
        if not verificar_ruleta_usuario(user_id_str):
            return jsonify({'error': 'Error al cargar ruleta'}), 500

        # Obtener tiros actuales
        ruleta_data = obtener_ruleta_usuario(user_id_str)
        
        if not ruleta_data:
            return jsonify({'error': 'Datos de ruleta no encontrados'}), 500
        
        tiros_restantes, ultimo_giro, proximo_reinicio = ruleta_data
        
        # Verificar tiros disponibles
        if tiros_restantes <= 0:
            return jsonify({'error': 'No tienes tiros disponibles'}), 400
        
        # Decrementar tiros y registrar giro
        nuevo_tiros = tiros_restantes - 1
        exito_ruleta = actualizar_ruleta_usuario(user_id_str, {
            'tiros_restantes': nuevo_tiros,
            'ultimo_giro': datetime.now().isoformat()
        })
        
        if not exito_ruleta:
            return jsonify({'error': 'Error al registrar giro'}), 500
        
        # Obtener premio
        premio = obtener_premio_ruleta()
        
        # Aplicar premio
        if premio['tipo'] == 'balance':
            # Sumar al balance
            usuario_data = obtener_registro("usuarios", user_id_str, "Balance")
            if usuario_data:
                nuevo_balance = (usuario_data[0] or 0) + premio['cantidad']
                actualizar_registro("usuarios", user_id_str, {"Balance": nuevo_balance})
        
        elif premio['tipo'] == 'bono':
            # Sumar al bono
            bono_data = obtener_registro("bono_apuesta", user_id_str, "bono, rollover_requerido")
            if bono_data:
                nuevo_bono = (bono_data[0] or 0) + premio['cantidad']
                nuevo_rollover = (bono_data[1] or 0) + (premio['cantidad'] * 3)
                actualizar_registro("bono_apuesta", user_id_str, {
                    "bono": nuevo_bono,
                    "rollover_requerido": nuevo_rollover
                })
        
        elif premio['tipo'] == 'tiros':
            # Sumar tiros extras
            nuevo_tiros += premio['cantidad']
            actualizar_ruleta_usuario(user_id_str, {"tiros_restantes": nuevo_tiros})
        
        return jsonify({
            'premio': premio,
            'tiros_restantes': nuevo_tiros
        })
        
    except Exception as e:
        print(f"Error en api_ruleta_girar: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/ruleta/comprar-tiro', methods=['POST'])
def api_ruleta_comprar_tiro():
    if 'user_id' not in flask_session:
        return jsonify({'error': 'No autenticado'}), 401
    
    user_id = flask_session['user_id']
    user_id_str = str(user_id)

    try:
        # Verificar ruleta primero
        if not verificar_ruleta_usuario(user_id_str):
            return jsonify({'error': 'Error al cargar ruleta'}), 500

        # Obtener balance del usuario
        usuario_data = obtener_registro("usuarios", user_id_str, "Balance")
        if not usuario_data:
            return jsonify({'error': 'Usuario no encontrado'}), 400
        
        balance_actual = usuario_data[0] or 0
        if balance_actual < 10:
            return jsonify({'error': 'Balance insuficiente'}), 400
        
        # Restar 10 CUP del balance
        nuevo_balance = balance_actual - 10
        exito_balance = actualizar_registro("usuarios", user_id_str, {"Balance": nuevo_balance})
        
        if not exito_balance:
            return jsonify({'error': 'Error al actualizar balance'}), 500
        
        # Obtener tiros actuales de la ruleta
        ruleta_data = obtener_ruleta_usuario(user_id_str)
        
        if ruleta_data:
            tiros_actuales = ruleta_data[0] or 0
            nuevos_tiros = tiros_actuales + 1
            exito_ruleta = actualizar_ruleta_usuario(user_id_str, {"tiros_restantes": nuevos_tiros})
        else:
            # Esto no debería pasar porque ya verificamos arriba, pero por si acaso
            nuevos_tiros = 1
            exito_ruleta = actualizar_ruleta_usuario(user_id_str, {"tiros_restantes": nuevos_tiros})
        
        if not exito_ruleta:
            return jsonify({'error': 'Error al actualizar ruleta'}), 500

        return jsonify({
            'nuevo_balance': nuevo_balance,
            'tiros_restantes': nuevos_tiros
        })
        
    except Exception as e:
        print(f"Error en api_ruleta_comprar_tiro: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/bolita')
def loteria():
    return render_template('bolita.html')
    

    
@app.route('/juego_pirata')
def juego_pirata():
    if 'user_id' not in flask_session:
        return redirect('/login')
        
    return render_template('juego_pirata.html')    

# Función para verificar si la hora actual está dentro de un rango
def time_in_range(start, end, current):
    """Return true if current is in the range [start, end]"""
    if start <= end:
        return start <= current <= end
    else:
        # Para rangos que cruzan la medianoche
        return current >= start or current <= end

# Función auxiliar para calcular tiempo restante
def calcular_tiempo_restante(current, end):
    """Calcula el tiempo restante entre la hora actual y la hora de fin"""
    # Convertir a segundos desde medianoche
    current_sec = current.hour * 3600 + current.minute * 60 + current.second
    end_sec = end.hour * 3600 + end.minute * 60
    
    # Si el tiempo de fin es menor que el actual, asumimos que es al día siguiente
    if end_sec < current_sec:
        end_sec += 24 * 3600  # Añadir 24 horas en segundos
        
    diff_sec = end_sec - current_sec
    
    # Si ya pasó el tiempo, devolver 0
    if diff_sec <= 0:
        return "00:00:00"
        
    hours = diff_sec // 3600
    minutes = (diff_sec % 3600) // 60
    seconds = diff_sec % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Endpoint para obtener loterías disponibles
@app.route('/api/loterias-disponibles')
async def api_loterias_disponibles():
    try:
        cuba_tz = pytz.timezone("America/Havana")
        now = datetime.now(cuba_tz)
        current_time = now.time()
        
        loterias = []
        
        # Florida
        if time_in_range(dt_time(8, 30), dt_time(13, 15), current_time):
            loterias.append({
                "id": "florida_manana",
                "name": "🇺🇸 Florida🌞 [1:35 PM]",
                "description": "Sorteo de la mañana de Florida",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(13, 15))
            })
        elif time_in_range(dt_time(14, 0), dt_time(21, 20), current_time):
            loterias.append({
                "id": "florida_tarde",
                "name": "🇺🇸 Florida🌙 [9:50 PM]",
                "description": "Sorteo de la tarde de Florida",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(21, 20))
            })
        elif (current_time >= dt_time(22, 0) or current_time <= dt_time(5, 45)):
            loterias.append({
                "id": "florida_noche",
                "name": "🇺🇸 Florida🌚 [6:00 AM]",
                "description": "Sorteo de la noche de Florida",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(5, 45))
            })
        else:
            loterias.append({
                "id": "florida_cerrada",
                "name": "🔐 Florida (cerrado)",
                "description": "Loteria cerrada en este momento",
                "closed": True
            })
            
        # Georgia
        if time_in_range(dt_time(8, 30), dt_time(12, 15), current_time):
            loterias.append({
                "id": "georgia_manana",
                "name": "🍑 Georgia🌞 [12:30 PM]",
                "description": "Sorteo de la mañana de Georgia",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(12, 15))
            })
        elif time_in_range(dt_time(14, 0), dt_time(18, 45), current_time):
            loterias.append({
                "id": "georgia_tarde",
                "name": "🍑 Georgia⛅ [7:00 PM]",
                "description": "Sorteo de la tarde de Georgia",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(18, 45))
            })
        elif time_in_range(dt_time(19, 30), dt_time(23, 20), current_time):
            loterias.append({
                "id": "georgia_noche",
                "name": "🍑 Georgia🌛 [11:35 PM]",
                "description": "Sorteo de la noche de Georgia",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(23, 20))
            })
        else:
            loterias.append({
                "id": "georgia_cerrada",
                "name": "🔐 Georgia (cerrado)",
                "description": "Loteria cerrada en este momento",
                "closed": True
            })
            
        # New York
        if time_in_range(dt_time(11, 0), dt_time(14, 15), current_time):
            loterias.append({
                "id": "newyork_manana",
                "name": "🗽 New_York🌞 [2:30 PM]",
                "description": "Sorteo de la mañana de New York",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(14, 15))
            })
        elif time_in_range(dt_time(17, 30), dt_time(22, 15), current_time):
            loterias.append({
                "id": "newyork_tarde",
                "name": "🗽 New_York🌛 [10:30 PM]",
                "description": "Sorteo de la tarde de New York",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(22, 15))
            })
        else:
            loterias.append({
                "id": "newyork_cerrada",
                "name": "🔐 New_York (cerrado)",
                "description": "Loteria cerrada en este momento",
                "closed": True
            })
            
        # Haití
        if time_in_range(dt_time(11, 0), dt_time(11, 45), current_time):
            loterias.append({
                "id": "haiti_manana",
                "name": "🇭🇹 Haití🌞 [12:00 PM]",
                "description": "Sorteo de la mañana de Haití",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(11, 45))
            })
        elif time_in_range(dt_time(20, 0), dt_time(20, 45), current_time):
            loterias.append({
                "id": "haiti_tarde",
                "name": "🇭🇹 Haití🌛 [9:00 PM]",
                "description": "Sorteo de la tarde de Haití",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(20, 45))
            })
        else:
            loterias.append({
                "id": "haiti_cerrada",
                "name": "🔐 Haití (cerrado)",
                "description": "Loteria cerrada en este momento",
                "closed": True
            })
            
        # Miami
        if time_in_range(dt_time(21, 0), dt_time(21, 45), current_time):
            loterias.append({
                "id": "miami_noche",
                "name": "🏙️ Miami🌛 [10:00 PM]",
                "description": "Sorteo de la noche de Miami",
                "timeRemaining": calcular_tiempo_restante(current_time, dt_time(21, 45))
            })
        else:
            loterias.append({
                "id": "miami_cerrada",
                "name": "🔐 Miami (cerrado)",
                "description": "Loteria cerrada en este momento",
                "closed": True
            })
        
        return jsonify(loterias)
        
    except Exception as e:
        print(f"Error en api_loterias-disponibles: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error al obtener loterías'}), 500
        
# Función para guardar jugada en la base de datos
def guardar_jugada_loteria(user_id, nombre_usuario, loteria, jugada, total):
    """Guarda una jugada de lotería en la base de datos"""
    try:
        campos_valores = {
            'user_id': str(user_id),
            'nombre_usuario': nombre_usuario,
            'loteria': loteria,
            'jugada': jugada,
            'total': total
        }
        
        return insertar_registro('loterias', campos_valores)
        
    except Exception as e:
        print(f"Error al guardar jugada en DB: {e}")
        return False

# Endpoint para realizar jugadas
@app.route('/api/realizar-jugada', methods=['POST'])
async def api_realizar_jugada():
    try:
        if 'user_id' not in flask_session:
            return jsonify({'success': False, 'message': 'Usuario no autenticado'}), 401
            
        data = request.get_json()
        user_id = flask_session['user_id']
        user_id_str = str(user_id)
        
        # Validar datos recibidos
        required_fields = ['lottery', 'type', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Campo requerido faltante: {field}'}), 400
                
        # Obtener datos del usuario desde la base de datos
        usuario_data = obtener_registro("usuarios", user_id_str, "nombre, Balance")
        if not usuario_data:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
            
        nombre_usuario, balance_actual = usuario_data
        
        # Verificar balance
        if (balance_actual or 0) < data['amount']:
            return jsonify({'success': False, 'message': 'Balance insuficiente'}), 400
            
        # Formatear la jugada según el tipo
        jugada_texto = ""
        if data['type'] == 'fijo':
            jugada_texto = f"Fijo: {data['number']}"
        elif data['type'] == 'centena':
            jugada_texto = f"Centena: {data['number']}"
        elif data['type'] == 'terminal':
            jugada_texto = f"Terminal: {', '.join(data['terminals'])}"
        elif data['type'] == 'decena':
            jugada_texto = f"Decena: {', '.join(data['decenas'])}"
        else:
            return jsonify({'success': False, 'message': 'Tipo de jugada no válido'}), 400
        
        # Procesar la jugada
        # 1. Actualizar balance del usuario
        nuevo_balance = (balance_actual or 0) - data['amount']
        exito_balance = actualizar_registro("usuarios", user_id_str, {"Balance": nuevo_balance})
        
        if not exito_balance:
            return jsonify({'success': False, 'message': 'Error al actualizar balance'}), 500
            
        # 2. Guardar jugada en la tabla loterias
        exito_jugada = guardar_jugada_loteria(
            user_id=user_id_str,
            nombre_usuario=nombre_usuario or "Usuario",
            loteria=data['lottery'],
            jugada=jugada_texto,
            total=data['amount']
        )
        
        if not exito_jugada:
            # Revertir el balance si falla el guardado
            actualizar_registro("usuarios", user_id_str, {"Balance": balance_actual})
            return jsonify({'success': False, 'message': 'Error al guardar la jugada'}), 500
        
        # Enviar mensaje al canal de Telegram
        mensaje_canal = (
            f"<blockquote>{data['lottery']}</blockquote> \n"
            f"<b>👤 Usuario</b>: {nombre_usuario}\n"                    
            f"🎯 <b>Jugada:</b>\n {jugada_texto}\n"
            f"💰 <b>Total:</b> <code>{data['amount']}</code> CUP"
        )
        
        response = await enviar_mensaje_al_canal(TOKEN, CANAL_TICKET, mensaje_canal)
        
        return jsonify({
            'success': True,
            'message': 'Jugada realizada con éxito',
            'newBalance': nuevo_balance
        })
        
    except Exception as e:
        print(f"Error en api_realizar_jugada: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al procesar la jugada'}), 500      
        


@app.route('/api/datos-pirata', methods=['GET'])
def obtener_datos_pirata():
    """Obtiene todos los datos del juego pirata para el usuario actual"""
    user_id = flask_session.get('user_id')
    if not user_id:
        return jsonify({"error": "Se requiere user_id"}), 400

    try:
        # Obtener datos básicos del juego pirata
        juego_data = obtener_registro("juego_pirata", user_id,
                                    "barriles, piratas, hp_barco, prestigio, ganancias_totales, nombre")
        if not juego_data:
            return jsonify({"error": "Usuario no encontrado en juego pirata"}), 404
        
        barriles, piratas, hp_barco, prestigio, ganancias_totales, nombre = juego_data

        # Obtener niveles de mejoras
        mejoras = {}
        tipos = ["barco", "cañones", "velas"]
        for tipo in tipos:
            mejora_data = obtener_registro("mejoras", (user_id, tipo), "nivel")
            nivel = mejora_data[0] if mejora_data else 1
            mejoras[tipo] = {"nivel": nivel}

        # --- NUEVO: Obtener estadísticas de combates ---
        estadisticas_combate = ejecutar_consulta_segura(
            """SELECT 
                COUNT(*) as combates_totales,
                SUM(CASE WHEN ganador = 'jugador' THEN 1 ELSE 0 END) as victorias,
                SUM(CASE WHEN ganador = 'oponente' THEN 1 ELSE 0 END) as derrotas
                FROM historial_combate 
                WHERE jugador_id = ?""",
            (user_id,), obtener_resultados=True
        )
        
        # Procesar estadísticas
        if estadisticas_combate and estadisticas_combate[0]:
            combates_totales = estadisticas_combate[0][0] or 0
            victorias = estadisticas_combate[0][1] or 0
            derrotas = estadisticas_combate[0][2] or 0
        else:
            combates_totales = 0
            victorias = 0
            derrotas = 0

        # Obtener datos del usuario (Nombre y Balance)
        usuario_data = obtener_registro("usuarios", user_id, "Nombre, Balance")
        nombre_usuario = nombre  # Valor por defecto
        balance_cup = 0.0        # Valor por defecto

        if usuario_data:
            nombre_usuario, balance_cup = usuario_data

        # Obtener último combate
        ultimo_combate_data = ejecutar_consulta_segura(
            "SELECT MAX(fecha_combate) FROM historial_combate WHERE jugador_id = ?",
            (user_id,), obtener_resultados=True
        )
        ultimo_combate = ultimo_combate_data[0][0] if ultimo_combate_data and ultimo_combate_data[0][0] else None

        # Respuesta
        respuesta = {
            "barriles": barriles,
            "piratas": piratas,
            "hp_barco": hp_barco,
            "prestigio": prestigio,
            "ganancias_totales": ganancias_totales,
            "nivel_barco": mejoras["barco"]["nivel"],
            "mejoras": mejoras,
            "estadisticas": {  # <--- NUEVO OBJETO CON ESTADÍSTICAS
                "combates_totales": combates_totales,
                "victorias": victorias,
                "derrotas": derrotas,
                "porcentaje_victorias": round((victorias / combates_totales * 100), 1) if combates_totales > 0 else 0
            },
            "nombre": nombre_usuario,
            "balance_cup": balance_cup,
            "user_id": user_id,
            "ultimo_combate": ultimo_combate
        }
        
        return jsonify(respuesta)
        
    except Exception as e:
        import traceback
        print(f"❌ ERROR EXCEPCIÓN en obtener_datos_pirata: {str(e)}")
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return jsonify({"error": "Error interno del servidor", "detalle": str(e)}), 500

@app.route('/api/mejoras-pirata', methods=['GET'])
def obtener_mejoras():
    """Obtiene la información de mejoras disponibles"""
    print("=== INICIO obtener_mejoras ===")
    print(f"Parámetros recibidos: {request.args}")
    
    user_id = flask_session['user_id']
    print(f"user_id obtenido: {user_id}")
    
    if not user_id:
        print("❌ ERROR: user_id no proporcionado")
        return jsonify({"error": "Se requiere user_id"}), 400
    
    try:
        mejoras = []
        tipos_config = [
            {"tipo": "barco", "nombre": "🚢 Barco", "costo_base": 1000},
            {"tipo": "cañones", "nombre": "🔫 Cañones", "costo_base": 750},
            {"tipo": "velas", "nombre": "⛵ Velas", "costo_base": 500}
        ]
        
        print(f"🔍 Procesando {len(tipos_config)} tipos de mejoras para user_id: {user_id}")
        
        for tipo_info in tipos_config:
            tipo = tipo_info["tipo"]
            print(f"  🔍 Procesando mejora: {tipo}")
            
            # Obtener nivel actual
            mejora_data = obtener_registro("mejoras", (user_id, tipo), "nivel")
            print(f"  📊 Resultado de obtener_registro (mejoras, {tipo}): {mejora_data}")
            
            nivel_actual = mejora_data[0] if mejora_data else 1
            print(f"  ✅ Nivel actual de {tipo}: {nivel_actual}")
            
            # Calcular costo
            costo = tipo_info["costo_base"] * (nivel_actual ** 1.5)
            costo_entero = int(costo)
            print(f"  💰 Costo calculado: {costo} -> {costo_entero}")
            
            mejora_info = {
                "tipo": tipo,
                "nombre": tipo_info["nombre"],
                "nivel_actual": nivel_actual,
                "costo": costo_entero,
                "nivel_siguiente": nivel_actual + 1,
                "debug": {
                    "user_id": user_id,
                    "tipo_mejora": tipo,
                    "nivel_obtenido": nivel_actual,
                    "costo_calculado": costo_entero
                }
            }
            
            mejoras.append(mejora_info)
            print(f"  ✅ Mejora {tipo} procesada correctamente")
        
        print(f"✅ Total de mejoras procesadas: {len(mejoras)}")
        print(f"📊 Respuesta final: {mejoras}")
        print("=== FIN obtener_mejoras ===")
        
        return jsonify({
            "mejoras": mejoras,
            "debug": {
                "user_id_recibido": user_id,
                "total_mejoras": len(mejoras),
                "tipos_procesados": [m["tipo"] for m in mejoras]
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR EXCEPCIÓN en obtener_mejoras: {str(e)}")
        import traceback
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return jsonify({"error": "Error interno del servidor", "detalle": str(e)}), 500
        
@app.route('/api/mejorar-pirata', methods=['POST'])
def mejorar_pirata():
    """Mejora un elemento del barco - ENDPOINT CORREGIDO"""
    try:
        data = request.get_json()
        user_id = flask_session['user_id']
        tipo = data.get('tipo')
        
        if not user_id or not tipo:
            return jsonify({"exito": False, "mensaje": "Se requiere user_id y tipo"}), 400
        
        # Obtener datos actuales del usuario
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, piratas, ganancias_totales")
        if not juego_data:
            return jsonify({"exito": False, "mensaje": "Usuario no encontrado"}), 404
        
        barriles, piratas, ganancias_totales = juego_data
        
        # Obtener niveles actuales de todas las mejoras
        niveles_mejoras = {}
        for mejora_tipo in ["barco", "cañones", "velas"]:
            mejora_data = obtener_registro("mejoras", (user_id, mejora_tipo), "nivel")
            niveles_mejoras[mejora_tipo] = mejora_data[0] if mejora_data else 1
        
        nivel_actual = niveles_mejoras.get(tipo, 1)
        nivel_siguiente = nivel_actual + 1
        
        # Verificar nivel máximo
        if nivel_actual >= 15:  # Máximo nivel
            return jsonify({
                "exito": False, 
                "mensaje": f"¡{tipo.capitalize()} ya está al máximo nivel (15)!"
            })
        
        # Calcular costo y requisitos usando tu configuración
        costo = calcular_costo_mejora(tipo, nivel_actual)
        piratas_requeridos = calcular_piratas_requeridos(tipo, nivel_actual)
        
        # Verificar requisitos de otras mejoras
        requisitos = MEJORAS_CONFIG[tipo]["requisitos"]
        for req_tipo, req_mult in requisitos.items():
            req_nivel = nivel_siguiente * req_mult
            if niveles_mejoras.get(req_tipo, 1) < req_nivel:
                return jsonify({
                    "exito": False,
                    "mensaje": f"Necesitas {req_tipo} nivel {req_nivel} para mejorar {tipo} a nivel {nivel_siguiente}"
                })
        
        # Verificar recursos
        if piratas < piratas_requeridos:
            return jsonify({
                "exito": False,
                "mensaje": f"Necesitas {piratas_requeridos} piratas (tienes {piratas})"
            })
            
        if barriles < costo:
            return jsonify({
                "exito": False, 
                "mensaje": f"Necesitas {costo} barriles (tienes {barriles})"
            })
        
        # Calcular nueva ganancia total
        nueva_ganancia_total = 0
        for mejora_tipo in ["barco", "cañones", "velas"]:
            nivel = niveles_mejoras[mejora_tipo]
            if mejora_tipo == tipo:
                nivel = nivel_siguiente
            nueva_ganancia_total += calcular_ganancia_mejora(mejora_tipo, nivel)
        
        # Actualizar base de datos
        exito_mejora = actualizar_registro(
            "mejoras", 
            (user_id, tipo),
            {"nivel": nivel_siguiente}
        )
        
        exito_juego = actualizar_registro(
            "juego_pirata",
            user_id,
            {
                "barriles": barriles - costo,
                "ganancias_totales": nueva_ganancia_total
            }
        )
        
        if exito_mejora and exito_juego:
            ganancia_extra = nueva_ganancia_total - ganancias_totales
            return jsonify({
                "exito": True, 
                "mensaje": f"¡{tipo.capitalize()} mejorado a nivel {nivel_siguiente}!",
                "nuevo_nivel": nivel_siguiente,
                "costo": costo,
                "barriles_restantes": barriles - costo,
                "ganancia_extra": ganancia_extra,
                "ganancia_total": nueva_ganancia_total
            })
        else:
            return jsonify({"exito": False, "mensaje": "Error al actualizar la base de datos"})
            
    except Exception as e:
        print(f"Error en mejorar_pirata: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor"}), 500
@app.route('/api/mejoras-detalladas', methods=['GET'])
def mejoras_detalladas():
    """Obtiene información detallada de las mejoras para mostrar en el modal"""
    try:
        user_id = flask_session['user_id']
        if not user_id:
            return jsonify({"error": "Se requiere user_id"}), 400
        
        # Obtener datos del juego
        juego_data = obtener_registro("juego_pirata", user_id, "barriles, piratas, ganancias_totales")
        if not juego_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        barriles, piratas, ganancias_totales = juego_data
        
        # Obtener niveles actuales
        niveles_mejoras = {}
        for tipo in ["barco", "cañones", "velas"]:
            mejora_data = obtener_registro("mejoras", (user_id, tipo), "nivel")
            niveles_mejoras[tipo] = mejora_data[0] if mejora_data else 1
        
        # Calcular información detallada para cada mejora
        mejoras_detalladas = []
        
        for tipo, config in MEJORAS_CONFIG.items():
            nivel_actual = niveles_mejoras.get(tipo, 1)
            nivel_siguiente = nivel_actual + 1
            
            # Solo procesar si no está en nivel máximo
            if nivel_actual < config["max_nivel"]:
                costo = calcular_costo_mejora(tipo, nivel_actual)
                piratas_requeridos = calcular_piratas_requeridos(tipo, nivel_actual)
                ganancia_actual = calcular_ganancia_mejora(tipo, nivel_actual)
                ganancia_siguiente = calcular_ganancia_mejora(tipo, nivel_siguiente)
                ganancia_extra = ganancia_siguiente - ganancia_actual
                
                # Verificar requisitos
                requisitos_cumplidos = True
                requisitos_info = []
                for req_tipo, req_mult in config["requisitos"].items():
                    req_nivel = nivel_siguiente * req_mult
                    tiene_nivel = niveles_mejoras.get(req_tipo, 1)
                    requisitos_info.append({
                        "tipo": req_tipo,
                        "requerido": req_nivel,
                        "actual": tiene_nivel,
                        "cumplido": tiene_nivel >= req_nivel
                    })
                    if tiene_nivel < req_nivel:
                        requisitos_cumplidos = False
                
                mejoras_detalladas.append({
                    "tipo": tipo,
                    "nombre": tipo.capitalize(),
                    "nivel_actual": nivel_actual,
                    "nivel_siguiente": nivel_siguiente,
                    "costo": costo,
                    "piratas_requeridos": piratas_requeridos,
                    "ganancia_actual": ganancia_actual,
                    "ganancia_siguiente": ganancia_siguiente,
                    "ganancia_extra": ganancia_extra,
                    "puede_mejorar": barriles >= costo and piratas >= piratas_requeridos and requisitos_cumplidos,
                    "requisitos": requisitos_info,
                    "es_salto_nivel": nivel_actual in config.get("saltos_nivel", {}),
                    "multiplicador_salto": config.get("saltos_nivel", {}).get(nivel_actual, 1)
                })
        
        return jsonify({
            "mejoras": mejoras_detalladas,
            "recursos": {
                "barriles": barriles,
                "piratas": piratas,
                "ganancia_total": ganancias_totales
            }
        })
        
    except Exception as e:
        print(f"Error en mejoras_detalladas: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500        
        
@app.route('/api/buscar-combate-pirata', methods=['GET'])
def buscar_combate():
    """Busca un oponente para combate con emparejamiento estricto por nivel"""
    user_id = flask_session.get('user_id')

    if not user_id:  
        return jsonify({"error": "Se requiere user_id"}), 400  
    
    try:  
        # Obtener datos del jugador
        jugador_data = obtener_registro("juego_pirata", user_id,   
                                      "hp_barco, prestigio, victorias, derrotas, barriles")  
        jugador_nombre_data = obtener_registro("usuarios", user_id, "Nombre")  
          
        if not jugador_data:  
            return jsonify({"error": "Jugador no encontrado"}), 404  
          
        hp_barco, prestigio, victorias, derrotas, barriles = jugador_data  
        jugador_nombre = jugador_nombre_data[0] if jugador_nombre_data else "Pirata"  
          
        # Obtener niveles desde mejoras
        nivel_barco_data = ejecutar_consulta_segura(  
            "SELECT nivel FROM mejoras WHERE id = ? AND tipo = 'barco'",  
            (user_id,), obtener_resultados=True  
        )  
        nivel_barco = nivel_barco_data[0][0] if nivel_barco_data else 1  
          
        nivel_canon_data = ejecutar_consulta_segura(  
            "SELECT nivel FROM mejoras WHERE id = ? AND tipo = 'cañones'",  
            (user_id,), obtener_resultados=True  
        )  
        nivel_canon = nivel_canon_data[0][0] if nivel_canon_data else 1  
          
        nivel_velas_data = ejecutar_consulta_segura(  
            "SELECT nivel FROM mejoras WHERE id = ? AND tipo = 'velas'",  
            (user_id,), obtener_resultados=True  
        )  
        nivel_velas = nivel_velas_data[0][0] if nivel_velas_data else 1  
          
        # Obtener último combate desde historial_combate  
        ultimo_combate_data = ejecutar_consulta_segura(  
            "SELECT MAX(fecha_combate) FROM historial_combate WHERE jugador_id = ?",  
            (user_id,), obtener_resultados=True  
        )  
        ultimo_combate = ultimo_combate_data[0][0] if ultimo_combate_data and ultimo_combate_data[0][0] else None  
          
        print(f"🔍 Datos jugador: nivel_barco={nivel_barco}, barriles={barriles}, último_combate={ultimo_combate}")  
          
        # Verificar si tiene barriles suficientes  
        if barriles < 50:  
            return jsonify({"error": "Necesitas 50 barriles para buscar combate"}), 400  
          
        # Verificar cooldown de 15 minutos  
        if ultimo_combate:  
            # Convertir a timestamp si es string  
            from datetime import datetime  
            if isinstance(ultimo_combate, str):  
                # Manejar formato de fecha de SQLite  
                ultimo_combate_dt = datetime.strptime(ultimo_combate, '%Y-%m-%d %H:%M:%S')  
            else:  
                ultimo_combate_dt = datetime.fromtimestamp(ultimo_combate)  
              
            tiempo_actual = datetime.now()  
            tiempo_espera_minutos = 15  
            tiempo_diferencia = tiempo_actual - ultimo_combate_dt  
            minutos_transcurridos = tiempo_diferencia.total_seconds() / 60  
            
            if minutos_transcurridos < tiempo_espera_minutos:  
                tiempo_restante = tiempo_espera_minutos - minutos_transcurridos  
                minutos = int(tiempo_restante)  
                segundos = int((tiempo_restante - minutos) * 60)  
                return jsonify({  
            "error": f"Debes esperar {minutos}:{segundos:02d} minutos para el próximo combate"  
        }), 400
              
            
        
        # EMPAREJAMIENTO ESTRICTO - Solo máximo 1 nivel de diferencia
        nivel_min = max(1, nivel_barco - 1)
        nivel_max = min(10, nivel_barco + 1)
        
        print(f"🔍 Buscando oponente en rango estricto: nivel {nivel_min}-{nivel_max}")
        
        consulta_emparejamiento = """  
            SELECT u.id, u.Nombre, jp.hp_barco, jp.prestigio, jp.victorias, jp.derrotas, jp.barriles,
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'barco') as nivel_barco,  
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'cañones') as nivel_canon,  
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'velas') as nivel_velas  
            FROM usuarios u  
            JOIN juego_pirata jp ON u.id = jp.id  
            WHERE u.id != ?   
            AND jp.hp_barco > 0   
            AND jp.barriles > 100
            AND (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'barco') BETWEEN ? AND ?  
            
            ORDER BY RANDOM()  
            LIMIT 1  
        """  
          
        resultados = ejecutar_consulta_segura(consulta_emparejamiento, (user_id, nivel_min, nivel_max), obtener_resultados=True)
        
        # Si no encuentra oponente en el rango estricto, usar el oponente específico 7031172659
        if not resultados:
            print(f"❌ No se encontraron oponentes en rango {nivel_min}-{nivel_max}, buscando oponente específico 7031172659")
            
            consulta_oponente_especifico = """  
                SELECT u.id, u.Nombre, jp.hp_barco, jp.prestigio, jp.victorias, jp.derrotas, jp.barriles,
                       (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'barco') as nivel_barco,  
                       (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'cañones') as nivel_canon,  
                       (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'velas') as nivel_velas  
                FROM usuarios u  
                JOIN juego_pirata jp ON u.id = jp.id  
                WHERE u.id = 7031172659
                AND jp.hp_barco > 0   
                AND jp.barriles > 100
                
            """  
            
            resultados = ejecutar_consulta_segura(consulta_oponente_especifico, (), obtener_resultados=True)
            
            if resultados:
                print("✅ Usando oponente específico 7031172659")
            else:
                print("❌ El oponente específico 7031172659 no está disponible")
                return jsonify({  
                    "error": "No se encontraron oponentes disponibles en tu rango de nivel. Intenta más tarde.",
                    "detalles": f"No hay jugadores nivel {nivel_min}-{nivel_max} con más de 100 barriles"
                }), 400
        
        if resultados:
            oponente_id, oponente_nombre, oponente_hp, oponente_prestigio, oponente_victorias, oponente_derrotas, oponente_barriles, oponente_nivel_barco, oponente_nivel_canon, oponente_nivel_velas = resultados[0]  
              
            # Asegurar valores por defecto si son None  
            oponente_nivel_barco = oponente_nivel_barco or 1  
            oponente_nivel_canon = oponente_nivel_canon or 1  
            oponente_nivel_velas = oponente_nivel_velas or 1  
              
            print(f"✅ Oponente confirmado: {oponente_nombre} (ID: {oponente_id}), Nivel: {oponente_nivel_barco}, Barriles: {oponente_barriles}")
              
            # Descontar 50 barriles al jugador  
            nuevos_barriles = barriles - 50  
            ejecutar_consulta_segura(  
                "UPDATE juego_pirata SET barriles = ? WHERE id = ?",  
                (nuevos_barriles, user_id)  
            )  
              
            return jsonify({  
                "jugador": {  
                    "id": user_id,  
                    "nombre": jugador_nombre,  
                    "hp_barco": hp_barco,  
                    "prestigio": prestigio,  
                    "victorias": victorias,  
                    "derrotas": derrotas,  
                    "nivel_barco": nivel_barco,  
                    "nivel_canon": nivel_canon,  
                    "nivel_velas": nivel_velas,  
                    "barriles_restantes": nuevos_barriles,
                    "rango_emparejamiento": 0 if oponente_id != 7031172659 else 1  # 0=normal, 1=específico
                },  
                "oponente": {  
                    "id": oponente_id,  
                    "nombre": oponente_nombre,  
                    "hp": oponente_hp,  
                    "prestigio": oponente_prestigio,  
                    "victorias": oponente_victorias,  
                    "derrotas": oponente_derrotas,  
                    "nivel": oponente_nivel_barco,  
                    "nivel_barco": oponente_nivel_barco,  
                    "nivel_canon": oponente_nivel_canon,  
                    "nivel_velas": oponente_nivel_velas  
                },  
                "costo_combate": 50  
            })  
        else:
            return jsonify({  
                "error": "No se encontraron oponentes disponibles. Intenta más tarde.",
                "detalles": "No hay jugadores con más de 100 barriles en tu rango de nivel"
            }), 400  
          
    except Exception as e:  
        print(f"❌ Error en buscar_combate: {str(e)}")  
        import traceback  
        print(f"📋 Stack trace: {traceback.format_exc()}")  
        return jsonify({"error": "Error interno del servidor"}), 500
@app.route('/api/atacar-pirata', methods=['POST'])
def atacar_pirata():
    """Realiza un ataque en el combate"""
    try:
        data = request.get_json()
        user_id = flask_session.get('user_id')  # <--- CORRECCIÓN: usar get()
        oponente_id = data.get('oponente_id')
        
        if not user_id or not oponente_id:
            return jsonify({"error": "Se requiere user_id y oponente_id"}), 400
        
        print(f"⚔️ Atacando: {user_id} vs {oponente_id}")
        
        # Si es un bot, usar lógica simplificada
        if oponente_id.startswith('bot_'):
            return jsonify({
                "estado": "continuar",
                "mensaje": "¡Ataque exitoso! El barco mercante ha sido dañado",
                "jugador": {"hp": 85},  # Pérdida mínima
                "oponente": {"hp": 30}  # Daño significativo
            })
        
        # Obtener datos de ambos jugadores (para oponentes reales)
        atacante_data = obtener_registro("juego_pirata", user_id, 
                                       "hp_barco, prestigio, victorias, derrotas, barriles")
        defensor_data = obtener_registro("juego_pirata", oponente_id, 
                                       "hp_barco, prestigio, victorias, derrotas, barriles")
        
        if not atacante_data or not defensor_data:
            return jsonify({"error": "Jugadores no encontrados"}), 404
        
        # Simular combate
        daño_base = 20
        botin_base = 100
        
        atacante_gana = random.random() < 0.7
        
        if atacante_gana:
            nuevo_hp_defensor = max(0, defensor_data[0] - daño_base)
            botin = min(botin_base, defensor_data[4])
            
            # Actualizar datos
            actualizar_registro("juego_pirata", oponente_id, {
                "hp_barco": nuevo_hp_defensor,
                "barriles": defensor_data[4] - botin
            })
            
            actualizar_registro("juego_pirata", user_id, {
                "barriles": atacante_data[4] + botin,
                "victorias": atacante_data[2] + 1,
                "prestigio": atacante_data[1] + 10
            })
            
            actualizar_registro("juego_pirata", oponente_id, {
                "derrotas": defensor_data[3] + 1
            })
            
            mensaje = f"¡Victoria! Has robado {botin} barriles"
            estado = "continuar" if nuevo_hp_defensor > 0 else "finalizado"
            
        else:
            nuevo_hp_atacante = max(0, atacante_data[0] - daño_base)
            
            actualizar_registro("juego_pirata", user_id, {
                "hp_barco": nuevo_hp_atacante,
                "derrotas": atacante_data[3] + 1
            })
            
            actualizar_registro("juego_pirata", oponente_id, {
                "victorias": defensor_data[2] + 1,
                "prestigio": defensor_data[1] + 10
            })
            
            mensaje = "¡Derrota! El oponente ha contraatacado"
            estado = "continuar" if nuevo_hp_atacante > 0 else "finalizado"
        
        # Obtener datos actualizados
        atacante_actualizado = obtener_registro("juego_pirata", user_id, "hp_barco")
        defensor_actualizado = obtener_registro("juego_pirata", oponente_id, "hp_barco")
        
        return jsonify({
            "estado": estado,
            "mensaje": mensaje,
            "jugador": {"hp": atacante_actualizado[0] if atacante_actualizado else 0},
            "oponente": {"hp": defensor_actualizado[0] if defensor_actualizado else 0}
        })
        
    except Exception as e:
        print(f"❌ Error en atacar_pirata: {str(e)}")
        import traceback
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return jsonify({"error": "Error interno del servidor"}), 500        
        
@app.route('/api/reclamar-ganancias-pirata', methods=['POST'])
def reclamar_ganancias():
    """Reclama las ganancias del juego pirata"""
    try:
        data = request.get_json()
        user_id = flask_session.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Se requiere user_id"}), 400
        
        # Obtener datos del usuario
        juego_data = obtener_registro("juego_pirata", user_id, 
                                    "barriles, ganancias_totales, tiempo_ultimo_reclamo, tiempo_para_ganar")
        
        if not juego_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        barriles, ganancias_totales, ultimo_reclamo, tiempo_ganar = juego_data
        
        # Calcular ganancias (simplificado)
        import time
        tiempo_actual = time.time()
        
        if ultimo_reclamo and (tiempo_actual - ultimo_reclamo) >= tiempo_ganar:
            ganancia = ganancias_totales
            
            # Actualizar barriles y tiempo
            actualizar_registro("juego_pirata", user_id, {
                "barriles": barriles + ganancia,
                "tiempo_ultimo_reclamo": tiempo_actual
            })
            
            return jsonify({
                "exito": True,
                "ganancia": ganancia,
                "barriles_totales": barriles + ganancia
            })
        else:
            tiempo_restante = tiempo_ganar - (tiempo_actual - ultimo_reclamo) if ultimo_reclamo else tiempo_ganar
            return jsonify({
                "exito": False,
                "mensaje": f"Debes esperar {int(tiempo_restante/60)} minutos más"
            })
            
    except Exception as e:
        print(f"Error en reclamar_ganancias: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500
@app.route('/api/estado-ganancias-pirata', methods=['GET'])
def estado_ganancias_pirata():
    """Verifica el estado de las ganancias del usuario"""
    try:
        user_id = flask_session.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Usuario no autenticado"}), 401
        
        # Obtener datos del usuario (usando los mismos campos que reclamar_ganancias)
        juego_data = obtener_registro("juego_pirata", user_id, 
                                    "barriles, ganancias_totales, tiempo_ultimo_reclamo, tiempo_para_ganar")
        
        if not juego_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        barriles, ganancias_totales, ultimo_reclamo, tiempo_ganar = juego_data
        
        import time
        tiempo_actual = time.time()
        
        # Si nunca ha reclamado, puede reclamar inmediatamente
        if not ultimo_reclamo:
            return jsonify({
                "puede_reclamar": True,
                "ganancias_disponibles": ganancias_totales,
                "tiempo_restante": "0:00",
                "tiempo_restante_segundos": 0,
                "mensaje": f"Puedes reclamar {ganancias_totales} barriles"
            })
        
        # Calcular tiempo transcurrido
        tiempo_transcurrido = tiempo_actual - ultimo_reclamo
        
        if tiempo_transcurrido >= tiempo_ganar:
            # Puede reclamar
            return jsonify({
                "puede_reclamar": True,
                "ganancias_disponibles": ganancias_totales,
                "tiempo_restante": "0:00",
                "tiempo_restante_segundos": 0,
                "mensaje": f"Puedes reclamar {ganancias_totales} barriles"
            })
        else:
            # Calcular tiempo restante
            tiempo_restante = tiempo_ganar - tiempo_transcurrido
            minutos_restantes = int(tiempo_restante // 60)
            segundos_restantes = int(tiempo_restante % 60)
            tiempo_restante_formateado = f"{minutos_restantes}:{segundos_restantes:02d}"
            
            return jsonify({
                "puede_reclamar": False,
                "ganancias_disponibles": 0,
                "tiempo_restante": tiempo_restante_formateado,
                "tiempo_restante_segundos": int(tiempo_restante),
                "mensaje": f"Próximo reclamo en {tiempo_restante_formateado}"
            })
            
    except Exception as e:
        print(f"Error en estado_ganancias_pirata: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500
        
@app.route('/api/reparar-barco-pirata', methods=['POST'])
def reparar_barco():
    """Repara el barco del usuario según su nivel máximo"""
    try:
        user_id = flask_session.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Usuario no autenticado"}), 401
        
        # ✅ OBTENER DATOS CORRECTAMENTE - HP de juego_pirata, nivel de mejoras
        juego_data = obtener_registro("juego_pirata", user_id, "hp_barco, barriles")
        
        if not juego_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        hp_actual, barriles = juego_data
        
        # ✅ OBTENER NIVEL DEL BARCO DESDE LA TABLA MEJORAS
        nivel_barco = obtener_nivel_mejora(user_id, "barco")
        
        # ✅ CALCULAR HP MÁXIMO SEGÚN NIVEL usando la misma constante del frontend
        niveles_barco = {
            1: 100, 2: 150, 3: 220, 4: 300, 5: 400,
            6: 520, 7: 660, 8: 820, 9: 1000, 10: 1200
        }
        
        hp_maximo = niveles_barco.get(nivel_barco, 100)
        
        if hp_actual >= hp_maximo:
            return jsonify({"exito": False, "mensaje": "Tu barco ya está en perfecto estado"})
        
        # ✅ CALCULAR COSTO SEGÚN HP REAL QUE FALTA
        hp_faltante = hp_maximo - hp_actual
        costo = hp_faltante * 5  # 5 barriles por punto de HP
        
        if barriles < costo:
            return jsonify({
                "exito": False, 
                "mensaje": f"No tienes suficientes barriles. Necesitas {costo}, tienes {barriles}"
            })
        
        # ✅ REALIZAR REPARACIÓN AL MÁXIMO SEGÚN NIVEL
        actualizar_registro("juego_pirata", user_id, {
            "hp_barco": hp_maximo,
            "barriles": barriles - costo
        })
        
        return jsonify({
            "exito": True,
            "mensaje": f"¡Barco reparado por {costo} barriles! (HP: {hp_actual} → {hp_maximo})",
            "costo": costo,
            "hp_anterior": hp_actual,
            "hp_nuevo": hp_maximo,
            "nivel_barco": nivel_barco,
            "barriles_restantes": barriles - costo
        })
            
    except Exception as e:
        print(f"Error en reparar_barco: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500
        
        
        
        
        
        
def calcular_botin_unificado(nivel_oponente, turnos, hp_jugador, hp_maximo_jugador, ganador):
    """Función unificada de cálculo de botín - MISMOS CÁLCULOS QUE EL FRONTEND"""
    if ganador != 'jugador':
        return 0
    
    # BASE del botín según nivel del oponente
    botin_base = nivel_oponente * 50
    
    # BONUS por victoria rápida (menos turnos = más botín)
    bonus_rapidez = max(0, 10 - turnos) * 10
    
    # BONUS por HP restante (más HP = más botín)
    porcentaje_hp = (hp_jugador / hp_maximo_jugador) * 100
    bonus_hp = round(porcentaje_hp * 0.5)  # 0.5% por cada punto de HP
    
    # BOTÍN TOTAL
    botin_total = botin_base + bonus_rapidez + bonus_hp
    
    # MÍNIMO GARANTIZADO
    botin_minimo = nivel_oponente * 40
    botin_total = max(botin_total, botin_minimo)
    
    print("💰 Cálculo de botín unificado (Backend):")
    print(f"- Nivel oponente: {nivel_oponente} → Base: {botin_base}")
    print(f"- Turnos: {turnos} → Bonus rapidez: {bonus_rapidez}")
    print(f"- HP: {hp_jugador}/{hp_maximo_jugador} ({round(porcentaje_hp)}%) → Bonus HP: {bonus_hp}")
    print(f"- Mínimo garantizado: {botin_minimo}")
    print(f"- TOTAL: {botin_total}")
    
    return round(botin_total)
configCombate = {
    "nivelesBarco": {
        1: {"hp": 100, "defensa": 0},
        2: {"hp": 150, "defensa": 5},
        3: {"hp": 220, "defensa": 10},
        4: {"hp": 300, "defensa": 15},
        5: {"hp": 400, "defensa": 20},
        6: {"hp": 520, "defensa": 25},
        7: {"hp": 660, "defensa": 30},
        8: {"hp": 820, "defensa": 35},
        9: {"hp": 1000, "defensa": 40},
        10: {"hp": 1200, "defensa": 50}
    }
}    
    
@app.route('/api/guardar-resultado-combate', methods=['POST'])  
def guardar_resultado_combate():  
    """Guarda el resultado del combate - CON HISTORIAL USANDO insertar_registro"""  
    try:  
        data = request.get_json()  
        jugador_id = data.get('jugador_id')  
        oponente_id = data.get('oponente_id')  
        ganador = data.get('ganador')  
        hp_final_jugador = data.get('hp_final_jugador')  
        hp_final_oponente = data.get('hp_final_oponente')  
        botin_frontend = data.get('botin', 0)
        turnos = data.get('turnos', 1)  
          
        print(f"🔍 DEBUG /api/guardar-resultado-combate - Datos recibidos:")
        print(f"🔍 jugador_id: {jugador_id}, oponente_id: {oponente_id}")
        print(f"🔍 ganador: {ganador}, hp_final_jugador: {hp_final_jugador}")
        print(f"🔍 botin_frontend: {botin_frontend}, turnos: {turnos}")
          
        # Verificar autenticación  
        user_id = flask_session.get('user_id')  
        if not user_id or str(user_id) != str(jugador_id):  
            print(f"❌ ERROR - Usuario no autorizado")
            return jsonify({"error": "Usuario no autorizado"}), 401  
          
        # Obtener datos
        jugador_data = obtener_registro("juego_pirata", jugador_id, "barriles, prestigio, victorias, derrotas, hp_barco")
        oponente_data = obtener_registro("juego_pirata", oponente_id, "barriles, prestigio, victorias, derrotas, hp_barco")
        
        # Obtener nombres de usuarios
        nombre_jugador_data = obtener_registro("usuarios", jugador_id, "Nombre")
        nombre_oponente_data = obtener_registro("usuarios", oponente_id, "Nombre")
        
        nombre_jugador = nombre_jugador_data[0] if nombre_jugador_data else f"Jugador {jugador_id}"
        nombre_oponente = nombre_oponente_data[0] if nombre_oponente_data else f"Oponente {oponente_id}"
        
        # Obtener niveles
        nivel_barco_jugador = obtener_nivel_mejora(jugador_id, "barco")
        nivel_barco_oponente = obtener_nivel_mejora(oponente_id, "barco")
          
        print(f"🔍 DEBUG - Datos de BD:")
        print(f"🔍 Jugador: {jugador_data}, Nivel barco: {nivel_barco_jugador}")
        print(f"🔍 Oponente: {oponente_data}, Nivel barco: {nivel_barco_oponente}")
          
        if not jugador_data or not oponente_data:  
            print("❌ ERROR - Datos de jugadores no encontrados")
            return jsonify({"error": "Datos de jugadores no encontrados"}), 404  
          
        # Desempaquetar datos  
        barriles_jugador, prestigio_jugador, victorias_jugador, derrotas_jugador, hp_actual_jugador = jugador_data  
        barriles_oponente, prestigio_oponente, victorias_oponente, derrotas_oponente, hp_actual_oponente = oponente_data  
        
        # CALCULAR BOTÍN UNIFICADO
        botin_calculado = calcular_botin_unificado(
            nivel_barco_oponente, 
            turnos, 
            hp_final_jugador, 
            configCombate["nivelesBarco"][nivel_barco_jugador]["hp"],
            ganador
        )
        
        print(f"💰 Botín calculado backend: {botin_calculado}")
        print(f"💰 Botín recibido frontend: {botin_frontend}")
        
        botin_final = max(botin_calculado, botin_frontend)
        
        # Variables para el mensaje del grupo
        botin_real = 0
        botin_efectivo = 0
        impuesto_casa = 0
        
        if ganador == 'jugador':  
            # JUGADOR GANA  
            print("🎯 Jugador GANA el combate")
              
            botin_maximo = max(int(barriles_oponente * 0.2), botin_final * 0.5)
            botin_real = min(botin_final, botin_maximo)
            botin_efectivo = int(botin_real * 0.9)
            impuesto_casa = botin_real - botin_efectivo
              
            print(f"💰 Botín final: calculado={botin_final}, real={botin_real}, efectivo={botin_efectivo}, impuesto={impuesto_casa}")
              
            # Actualizar JUGADOR (ganador)  
            actualizar_registro("juego_pirata", jugador_id, {  
                "barriles": barriles_jugador + botin_efectivo,  
                "prestigio": prestigio_jugador + 5,
                "victorias": victorias_jugador + 1,  
                "hp_barco": hp_final_jugador
            })  
              
            # Actualizar OPONENTE (perdedor)  
            actualizar_registro("juego_pirata", oponente_id, {  
                "barriles": max(0, barriles_oponente - botin_real),  
                "prestigio": max(0, prestigio_oponente - 2),
                "derrotas": derrotas_oponente + 1,  
                "hp_barco": hp_final_oponente
            })  
              
            mensaje = f"¡Victoria! Saqueaste {botin_efectivo} barriles (+5 prestigio)"  
              
        else:  
            # OPONENTE GANA  
            print("💀 Oponente GANA el combate")
              
            botin_maximo = max(int(barriles_jugador * 0.2), botin_final * 0.5)
            botin_real = min(botin_final, botin_maximo)
            botin_efectivo = int(botin_real * 0.9)
            impuesto_casa = botin_real - botin_efectivo
              
            print(f"💸 Botín perdido: calculado={botin_final}, real={botin_real}, efectivo={botin_efectivo}, impuesto={impuesto_casa}")
              
            # Actualizar OPONENTE (ganador)  
            actualizar_registro("juego_pirata", oponente_id, {  
                "barriles": barriles_oponente + botin_efectivo,  
                "prestigio": prestigio_oponente + 5,
                "victorias": victorias_oponente + 1  
            })  
              
            # Actualizar JUGADOR (perdedor)  
            actualizar_registro("juego_pirata", jugador_id, {  
                "barriles": max(0, barriles_jugador - botin_real),  
                "prestigio": max(0, prestigio_jugador - 2),
                "derrotas": derrotas_jugador + 1,  
                "hp_barco": hp_final_jugador
            })  
              
            mensaje = f"Derrota. Perdiste {botin_real} barriles (-2 prestigio)"  
        
        # 🔥🔥🔥 GUARDAR EN HISTORIAL_COMBATE USANDO insertar_registro
        try:
            # Primero crear la tabla si no existe
            ejecutar_consulta_segura('''
                CREATE TABLE IF NOT EXISTS historial_combate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jugador_id INTEGER NOT NULL,
                    oponente_id INTEGER NOT NULL,
                    ganador TEXT NOT NULL,
                    hp_final_jugador INTEGER NOT NULL,
                    hp_final_oponente INTEGER NOT NULL,
                    botin INTEGER NOT NULL,
                    turnos INTEGER NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insertar el registro del combate usando insertar_registro
            datos_historial = {
                "jugador_id": jugador_id,
                "oponente_id": oponente_id,
                "ganador": ganador,
                "hp_final_jugador": hp_final_jugador,
                "hp_final_oponente": hp_final_oponente,
                "botin": botin_real,
                "turnos": turnos,
                "fecha_combate": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            exito = insertar_registro("historial_combate", datos_historial)
            
            if exito:
                print("📚 Combate guardado en historial_combate correctamente")
            else:
                print("❌ Error al guardar en historial_combate")
            
        except Exception as e:
            print(f"❌ Error guardando en historial_combate: {str(e)}")
            # No es crítico si falla, continuar
        
        # 📢 ENVIAR MENSAJE AL GRUPO CON EL RESUMEN DEL COMBATE
        try:
            enviar_resumen_combate_grupo(
                ganador=ganador,
                nombre_ganador=nombre_jugador if ganador == 'jugador' else nombre_oponente,
                nombre_perdedor=nombre_oponente if ganador == 'jugador' else nombre_jugador,
                id_ganador=jugador_id if ganador == 'jugador' else oponente_id,
                id_perdedor=oponente_id if ganador == 'jugador' else jugador_id,
                botin_total=botin_real,
                botin_ganador=botin_efectivo,
                impuesto_casa=impuesto_casa,
                turnos=turnos,
                nivel_barco_ganador=nivel_barco_jugador if ganador == 'jugador' else nivel_barco_oponente,
                nivel_barco_perdedor=nivel_barco_oponente if ganador == 'jugador' else nivel_barco_jugador
            )
        except Exception as e:
            print(f"❌ Error enviando resumen al grupo: {str(e)}")
        
        # Verificar cambios después
        jugador_despues = obtener_registro("juego_pirata", jugador_id, "barriles, prestigio, victorias, derrotas, hp_barco")
        oponente_despues = obtener_registro("juego_pirata", oponente_id, "barriles, prestigio, victorias, derrotas, hp_barco")
        
        print(f"🔍 DEBUG - Datos de BD DESPUES:")
        print(f"🔍 Jugador después: {jugador_despues}")
        print(f"🔍 Oponente después: {oponente_despues}")
          
        return jsonify({  
            "exito": True,  
            "mensaje": mensaje,  
            "botin_efectivo": botin_efectivo if ganador == 'jugador' else -botin_real,  
            "hp_actualizado": hp_final_jugador,
            "botin_calculado": botin_final,
            "botin_aplicado": botin_real,
            "guardado_historial": True
        })  
          
    except Exception as e:  
        print(f"❌ ERROR guardando resultado del combate: {str(e)}")  
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Error interno del servidor"}), 500

def enviar_resumen_combate_grupo(ganador, nombre_ganador, nombre_perdedor, id_ganador, id_perdedor,
                               botin_total, botin_ganador, impuesto_casa, turnos, nivel_barco_ganador, nivel_barco_perdedor):
    """
    Envía un resumen del combate al grupo de administradores
    """
    try:
        global TOKEN, REGISTRO_MINIJUEGOS
        
        from datetime import datetime
        
        emoji_ganador = "🏆" if ganador == 'jugador' else "💀"
        titulo = "COMBATE PIRATA - RESULTADO"
        
        # Formatear el mensaje
        mensaje = f"""
⚔️ <b>{titulo}</b>

{emoji_ganador} <b>GANADOR:</b>
├─ Nombre: {nombre_ganador}
├─ ID: <code>{id_ganador}</code>
└─ Nivel Barco: {nivel_barco_ganador}

💔 <b>PERDEDOR:</b>
├─ Nombre: {nombre_perdedor}
├─ ID: <code>{id_perdedor}</code>
└─ Nivel Barco: {nivel_barco_perdedor}

💰 <b>RESUMEN BARRILES:</b>
├─ Botín total: {botin_total:,} 🛢️
├─ Al ganador: {botin_ganador:,} 🛢️
├─ Impuesto casa: {impuesto_casa:,} 🛢️
└─ <i>(10% del botín total)</i>

📊 <b>ESTADÍSTICAS:</b>
├─ Turnos del combate: {turnos}
├─ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
└─ Diferencia: {botin_total} - {botin_ganador} = {impuesto_casa} 🛢️

💡 <i>El impuesto del 10% se queda la casa por servicios de intermediación.</i>
        """
        
        # Enviar mensaje
        import requests
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {
            "chat_id": REGISTRO_MINIJUEGOS,
            "text": mensaje,
            "parse_mode": "html"
        }
        
        response = requests.get(url, params=params)
        print(f"📢 Resumen de combate enviado al grupo. Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Mensaje de resumen de combate enviado exitosamente")
                return True
        else:
            print(f"❌ Error HTTP enviando resumen: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error enviando resumen de combate al grupo: {e}")
    
    return False
# FUNCIÓN AUXILIAR PARA OBTENER NIVELES DE MEJORAS
def obtener_nivel_mejora(user_id, tipo_mejora):
    """Obtiene el nivel de una mejora específica para un usuario"""
    try:
        mejora_data = obtener_registro("mejoras", (user_id, tipo_mejora), "nivel")
        return mejora_data[0] if mejora_data else 1
    except Exception as e:
        print(f"❌ Error obteniendo nivel de {tipo_mejora} para {user_id}: {e}")
        return 1
@app.route('/api/comprar-barriles-pirata', methods=['POST'])
def comprar_barriles_pirata():
    """
    Permite a un usuario comprar barriles usando su balance de CUP.
    Tasa: 1 CUP = 70 barriles
    """
    try:
        data = request.get_json()
        user_id = flask_session.get('user_id')
        cantidad_cup = data.get('cantidad_cup')

        if not user_id or not isinstance(cantidad_cup, (int, float)) or cantidad_cup <= 0:
            return jsonify({"exito": False, "mensaje": "Datos inválidos."}), 400

        # 1. Obtener balance actual y nombre del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        if not usuario_data:
            return jsonify({"exito": False, "mensaje": "Usuario no encontrado."}), 404
        
        balance_actual = usuario_data[0]
        nombre_usuario = usuario_data[1] if len(usuario_data) > 1 else "Usuario"

        # 2. Verificar si tiene suficiente balance
        if balance_actual < cantidad_cup:
            return jsonify({
                "exito": False, 
                "mensaje": f"Saldo insuficiente. Tienes {balance_actual:,.2f} CUP."
            }), 400
            
        # 3. Obtener barriles actuales
        juego_data = obtener_registro("juego_pirata", user_id, "barriles")
        barriles_actuales = juego_data[0] if juego_data else 0

        # 4. Calcular la transacción
        barriles_comprados = int(cantidad_cup * 70)
        nuevo_balance = balance_actual - cantidad_cup
        nuevos_barriles = barriles_actuales + barriles_comprados

        # 5. Actualizar la base de datos
        exito_usuario = actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
        exito_juego = actualizar_registro("juego_pirata", user_id, {"barriles": nuevos_barriles})

        if exito_usuario and exito_juego:
            # 6. Enviar notificación al canal de administradores
            enviar_notificacion_transaccion_barriles(
                tipo_operacion="compra",
                user_id=user_id,
   			 nombre_usuario=nombre_usuario,
  			  balance_anterior=balance_actual,
    			balance_nuevo=nuevo_balance,
 			   barriles_anterior=barriles_actuales,
   			 barriles_nuevo=nuevos_barriles,
   			 cantidad_principal=cantidad_cup,
    			cantidad_secundaria=barriles_comprados
			)

            
            return jsonify({
                "exito": True,
                "mensaje": f"¡Compraste {barriles_comprados:,} barriles por {cantidad_cup:,.2f} CUP!",
                "nuevo_balance_cup": nuevo_balance,
                "nuevo_total_barriles": nuevos_barriles,
                "detalles": {
                    "cup_gastados": cantidad_cup,
                    "barriles_obtenidos": barriles_comprados,
                    "tasa": "1 CUP = 70 barriles"
                }
            })
        else:
            return jsonify({"exito": False, "mensaje": "Error crítico al actualizar la base de datos."}), 500

    except Exception as e:
        print(f"Error en comprar_barriles_pirata: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor."}), 500


@app.route('/api/vender-barriles-pirata', methods=['POST'])
def vender_barriles_pirata():
    """
    Permite a un usuario vender barriles para obtener CUP.
    Tasa: 100 barriles = 1 CUP
    Condiciones:
    - Mínimo 1000 barriles por venta
    - Nivel de barco mínimo: 5
    """
    try:
        data = request.get_json()
        user_id = flask_session.get('user_id')
        cantidad_barriles = data.get('cantidad_barriles')

        if not user_id or not isinstance(cantidad_barriles, int) or cantidad_barriles <= 0:
            return jsonify({"exito": False, "mensaje": "Datos inválidos."}), 400
        
        # 1. Verificar cantidad mínima de barriles
        if cantidad_barriles < 10000:
            return jsonify({
                "exito": False, 
                "mensaje": "Debes vender al menos 10,000 barriles por transacción."
            }), 400

        # 2. Verificar nivel mínimo del barco (nivel 5)
        nivel_barco_data = obtener_registro("mejoras", (user_id, "barco"), "nivel")
        if not nivel_barco_data:
            return jsonify({
                "exito": False, 
                "mensaje": "No se encontraron datos de tu barco."
            }), 404
            
        nivel_barco = nivel_barco_data[0]
        if nivel_barco < 5:
            return jsonify({
                "exito": False, 
                "mensaje": f"Necesitas barco nivel 5 para vender barriles. Tu barco es nivel {nivel_barco}."
            }), 400

        # 3. Obtener barriles actuales
        juego_data = obtener_registro("juego_pirata", user_id, "barriles")
        if not juego_data:
            return jsonify({"exito": False, "mensaje": "Datos del juego no encontrados."}), 404
            
        barriles_actuales = juego_data[0]

        # 4. Verificar si tiene suficientes barriles
        if barriles_actuales < cantidad_barriles:
            return jsonify({
                "exito": False, 
                "mensaje": f"Barriles insuficientes. Tienes {barriles_actuales:,}, intentas vender {cantidad_barriles:,}."
            }), 400

        # 5. Obtener balance actual y nombre del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        balance_actual = usuario_data[0] if usuario_data else 0
        nombre_usuario = usuario_data[1] if usuario_data else "Usuario"

        # 6. Calcular la transacción
        cup_obtenidos = cantidad_barriles / 100.0
        nuevos_barriles = barriles_actuales - cantidad_barriles
        nuevo_balance = balance_actual + cup_obtenidos

        # 7. Verificar que no quede en negativo (seguridad adicional)
        if nuevos_barriles < 0:
            return jsonify({
                "exito": False, 
                "mensaje": "Error: La transacción dejaría barriles en negativo."
            }), 400

        # 8. Actualizar la base de datos
        exito_juego = actualizar_registro("juego_pirata", user_id, {"barriles": nuevos_barriles})
        exito_usuario = actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
        
        if exito_juego and exito_usuario:
            # 9. Enviar mensaje al canal de administradores
            enviar_notificacion_transaccion_barriles(
                tipo_operacion="venta",
                user_id=user_id,
 			   nombre_usuario=nombre_usuario,
  			  balance_anterior=balance_actual,
    			balance_nuevo=nuevo_balance,
   			 barriles_anterior=barriles_actuales,
  			  barriles_nuevo=nuevos_barriles,
   			 cantidad_principal=cantidad_barriles,
  			  cantidad_secundaria=cup_obtenidos,
			    nivel_barco=nivel_barco
			)
            
            return jsonify({
                "exito": True,
                "mensaje": f"¡Venta exitosa! Vendiste {cantidad_barriles:,} barriles por {cup_obtenidos:,.2f} CUP.",
                "nuevo_balance_cup": nuevo_balance,
                "nuevo_total_barriles": nuevos_barriles,
                "detalles": {
                    "barriles_vendidos": cantidad_barriles,
                    "cup_obtenidos": cup_obtenidos,
                    "tasa": "100 barriles = 1 CUP",
                    "nivel_barco_requerido": 5,
                    "nivel_barco_actual": nivel_barco
                }
            })
        else:
            return jsonify({"exito": False, "mensaje": "Error crítico al actualizar la base de datos."}), 500

    except Exception as e:
        print(f"Error en vender_barriles_pirata: {str(e)}")
        return jsonify({"exito": False, "mensaje": "Error interno del servidor."}), 500

def enviar_notificacion_transaccion_barriles(tipo_operacion, user_id, nombre_usuario, balance_anterior, 
                                           balance_nuevo, barriles_anterior, barriles_nuevo, 
                                           cantidad_principal, cantidad_secundaria, nivel_barco=None):
    """
    Envía una notificación al canal de administradores sobre transacciones de barriles
    tipo_operacion: "compra" o "venta"
    """
    try:
        global TOKEN, GROUP_CHAT_ADMIN
        
        from datetime import datetime
        
        if tipo_operacion == "compra":
            emoji = "🛒"
            titulo = "COMPRA DE BARRILES"
            desc_principal = f"├─ CUP gastados: {cantidad_principal:,.2f} 💰"
            desc_secundaria = f"├─ Barriles recibidos: {cantidad_secundaria:,} 🛢️"
            tasa = "1 CUP = 70 barriles"
            diff_cup = f"-{cantidad_principal:,.2f}"
            diff_barriles = f"+{cantidad_secundaria:,}"
            
        elif tipo_operacion == "venta":
            emoji = "🛢️"
            titulo = "VENTA DE BARRILES"
            desc_principal = f"├─ Barriles vendidos: {cantidad_principal:,} 🛢️"
            desc_secundaria = f"├─ CUP recibidos: {cantidad_secundaria:,.2f} 💰"
            tasa = "100 barriles = 1 CUP"
            diff_cup = f"+{cantidad_secundaria:,.2f}"
            diff_barriles = f"-{cantidad_principal:,}"
        
        # Formatear el mensaje base
        mensaje = f"""
{emoji} <b>{titulo} - JUEGO PIRATA</b>

👤 <b>Usuario:</b> {nombre_usuario}
🆔 <b>ID:</b> <code>{user_id}</code>
"""
        
        # Agregar nivel de barco solo para ventas
        if tipo_operacion == "venta" and nivel_barco:
            mensaje += f"⚓ <b>Nivel Barco:</b> {nivel_barco}\n\n"
        else:
            mensaje += "\n"
            
        mensaje += f"""💰 <b>TRANSACCIÓN:</b>
{desc_principal}
{desc_secundaria}
└─ Tasa: {tasa}

📊 <b>BALANCE ANTES:</b>
├─ CUP: {balance_anterior:,.2f} 💰
└─ Barriles: {barriles_anterior:,} 🛢️

📈 <b>BALANCE DESPUÉS:</b>
├─ CUP: {balance_nuevo:,.2f} 💰
└─ Barriles: {barriles_nuevo:,} 🛢️

🔢 <b>RESUMEN:</b>
├─ Diferencia CUP: {diff_cup} 💰
└─ Diferencia Barriles: {diff_barriles} 🛢️

⏰ <b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # Enviar mensaje
        import requests
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {
            "chat_id": GROUP_CHAT_ADMIN,
            "text": mensaje,
            "parse_mode": "html"
        }
        
        response = requests.get(url, params=params)
        print(f"📢 Notificación de {tipo_operacion.upper()} enviada. Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Mensaje de {tipo_operacion.upper()} enviado exitosamente")
                return True
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error enviando notificación de {tipo_operacion}: {e}")
    
    return False
@app.route('/api/top-jugadores-pirata', methods=['GET'])
def obtener_top_jugadores_pirata():
    """Obtiene el top 10 de jugadores por prestigio en el juego pirata"""
    try:
        # Obtener todos los usuarios de juego_pirata
        query = "SELECT id FROM juego_pirata ORDER BY prestigio DESC LIMIT 10"
        resultados = ejecutar_consulta_segura(query, obtener_resultados=True)
        
        if not resultados:
            return jsonify([])
        
        top_jugadores = []
        for idx, (id,) in enumerate(resultados, 1):
            # Obtener datos de cada jugador usando obtener_registro
            juego_data = obtener_registro("juego_pirata", id, 
                                        "nombre, prestigio, barriles, piratas")
            
            if juego_data:
                nombre, prestigio, barriles, piratas = juego_data
                
                # Obtener nivel del barco usando obtener_registro
                nivel_data = obtener_registro("mejoras", (id, "barco"), "nivel")
                nivel_barco = nivel_data[0] if nivel_data else 1
                
                top_jugadores.append({
                    "posicion": idx,
                    "user_id": id,
                    "nombre": nombre,
                    "prestigio": prestigio or 0,
                    "barriles": barriles or 0,
                    "piratas": piratas or 0,
                    "nivel_barco": nivel_barco
                })
        
        return jsonify(top_jugadores)
        
    except Exception as e:
        print(f"Error en obtener_top_jugadores_pirata: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500
        
@app.route('/api/obtener-ataques-recientes', methods=['GET'])
def obtener_ataques_recientes():
    """Obtiene los ataques recientes no vistos donde el usuario fue atacado"""
    user_id = flask_session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    try:
        # Buscar en historial_combate los ataques donde el usuario FUE ATACADO (es oponente_id)
        consulta = """
            SELECT 
                hc.combate_id,
                hc.jugador_id,
                hc.oponente_id,
                hc.ganador,
                hc.hp_final_jugador,
                hc.hp_final_oponente,
                hc.botin,
                hc.turnos,
                hc.fecha_combate,
                u.Nombre as nombre_atacante,
                (SELECT nivel FROM mejoras WHERE id = hc.jugador_id AND tipo = 'barco') as nivel_atacante,
                hc.visto
            FROM historial_combate hc
            JOIN usuarios u ON hc.jugador_id = u.id  -- El atacante es el jugador_id
            WHERE hc.oponente_id = ?  -- El usuario actual fue atacado (es oponente_id)
            AND (hc.visto = 0 OR hc.visto IS NULL)
            AND DATE(hc.fecha_combate) >= DATE('now', '-1 day')  -- Últimas 24 horas
            ORDER BY hc.fecha_combate DESC
            LIMIT 5
        """
        
        resultados = ejecutar_consulta_segura(consulta, (user_id,), obtener_resultados=True)
        
        ataques = []
        for row in resultados:
            ataque = {
                "combate_id": row[0],
                "jugador_id": row[1],  # ID del atacante
                "oponente_id": row[2],  # ID del usuario (atacado)
                "ganador": row[3],
                "hp_final_jugador": row[4],  # HP final del atacante
                "hp_final_oponente": row[5],  # HP final del usuario (atacado)
                "botin": row[6],  # Barriles robados al usuario
                "turnos": row[7],
                "fecha_combate": row[8],
                "nombre_atacante": row[9],  # Nombre del que atacó
                "nivel_atacante": row[10] or 1,
                "visto": row[11]
            }
            ataques.append(ataque)
        
        print(f"🔍 Ataques encontrados para usuario {user_id}: {len(ataques)}")
        return jsonify(ataques)
        
    except Exception as e:
        print(f"❌ Error obteniendo ataques recientes: {str(e)}")
        import traceback
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return jsonify({"error": "Error interno del servidor"}), 500
@app.route('/api/marcar-ataques-leidos', methods=['POST'])
def marcar_ataques_leidos():
    """Marca los ataques como vistos"""
    user_id = flask_session.get('user_id')
    data = request.get_json()
    
    if not user_id:
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    try:
        combate_ids = data.get('combate_ids', [])
        
        print(f"🔍 Marcando como leídos: {combate_ids} para usuario {user_id}")
        
        if combate_ids and combate_ids[0] is not None:
            placeholders = ','.join(['?' for _ in combate_ids])
            consulta = f"""
                UPDATE historial_combate 
                SET visto = 1 
                WHERE combate_id IN ({placeholders}) AND oponente_id = ?
            """
            
            parametros = combate_ids + [user_id]
            ejecutar_consulta_segura(consulta, parametros)
            print(f"✅ Combates marcados como leídos: {combate_ids}")
        else:
            print("⚠️ No hay combate_ids válidos para marcar")
        
        return jsonify({"exito": True, "mensaje": "Ataques marcados como leídos"})
        
    except Exception as e:
        print(f"❌ Error marcando ataques como leídos: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/buscar-combate-venganza', methods=['GET'])
def buscar_combate_venganza():
    """Busca combate específico contra un oponente para vengarse"""
    user_id = flask_session.get('user_id')
    oponente_id = request.args.get('oponente_id')
    
    if not user_id:
        print("❌ [VENGANZA DEBUG] Usuario no autenticado")
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    if not oponente_id:
        print("❌ [VENGANZA DEBUG] No se proporcionó oponente_id")
        return jsonify({"error": "Se requiere ID del oponente"}), 400
    
    try:
        
        # Obtener datos del jugador
        jugador_data = obtener_registro("juego_pirata", user_id,   
                                      "hp_barco, prestigio, victorias, derrotas, barriles")  
        jugador_nombre_data = obtener_registro("usuarios", user_id, "Nombre")  
        
        if not jugador_data:  
            print("❌ [VENGANZA DEBUG] Jugador no encontrado en juego_pirata")
            return jsonify({"error": "Jugador no encontrado"}), 404  
        
        hp_barco, prestigio, victorias, derrotas, barriles = jugador_data  
        jugador_nombre = jugador_nombre_data[0] if jugador_nombre_data else "Pirata"  
        
        nivel_barco = obtener_nivel_mejora(user_id, "barco")
        nivel_canon = obtener_nivel_mejora(user_id, "cañones")
        nivel_velas = obtener_nivel_mejora(user_id, "velas")
        
        
        
        # Verificar si tiene barriles suficientes  
        if barriles < 50:  
            
            return jsonify({"error": "Necesitas 50 barriles para buscar combate"}), 400
        
        # Verificar cooldown de 15 minutos (igual que en buscar_combate_pirata)
        
        ultimo_combate_data = ejecutar_consulta_segura(  
            "SELECT MAX(fecha_combate) FROM historial_combate WHERE jugador_id = ?",  
            (user_id,), obtener_resultados=True  
        )  
        ultimo_combate = ultimo_combate_data[0][0] if ultimo_combate_data and ultimo_combate_data[0][0] else None  
        
        
        
        if ultimo_combate:  
            from datetime import datetime  
            if isinstance(ultimo_combate, str):  
                ultimo_combate_dt = datetime.strptime(ultimo_combate, '%Y-%m-%d %H:%M:%S')  
            else:  
                ultimo_combate_dt = datetime.fromtimestamp(ultimo_combate)  
            
            tiempo_actual = datetime.now()  
            tiempo_espera_minutos = 15  
            tiempo_diferencia = tiempo_actual - ultimo_combate_dt  
            minutos_transcurridos = tiempo_diferencia.total_seconds() / 60  
            
            
            
            if minutos_transcurridos < tiempo_espera_minutos:
                minutos_restantes = tiempo_espera_minutos - minutos_transcurridos
                print(f"❌ [VENGANZA DEBUG] Cooldown activo - Faltan {minutos_restantes:.1f} minutos")
                return jsonify({"error": f"Debes esperar {minutos_restantes:.1f} minutos para el próximo combate"}), 400
        
        # Buscar oponente específico
        
        consulta_oponente = """
            SELECT u.id, u.Nombre, jp.hp_barco, jp.prestigio, jp.victorias, jp.derrotas, jp.barriles,
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'barco') as nivel_barco,  
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'cañones') as nivel_canon,  
                   (SELECT nivel FROM mejoras WHERE id = u.id AND tipo = 'velas') as nivel_velas  
            FROM usuarios u  
            JOIN juego_pirata jp ON u.id = jp.id  
            WHERE u.id = ?
            AND jp.hp_barco > 0
            AND jp.barriles > 100
            AND u.id != ?
        """
        
        
        resultados = ejecutar_consulta_segura(consulta_oponente, (oponente_id, user_id), obtener_resultados=True)
        
        
        if not resultados:
            print(f"❌ [VENGANZA DEBUG] No se encontró oponente {oponente_id} o no cumple condiciones")
            return jsonify({"error": "El oponente no está disponible para combatir (puede que no tenga suficientes barriles o esté derrotado)"}), 400
        
        # Datos del oponente
        oponente_id_db, oponente_nombre, oponente_hp, oponente_prestigio, oponente_victorias, oponente_derrotas, oponente_barriles, oponente_nivel_barco, oponente_nivel_canon, oponente_nivel_velas = resultados[0]
        
        
        # Asegurar valores por defecto
        oponente_nivel_barco = oponente_nivel_barco or 1  
        oponente_nivel_canon = oponente_nivel_canon or 1  
        oponente_nivel_velas = oponente_nivel_velas or 1  
        
        
        
        # Descontar 50 barriles al jugador  
        nuevos_barriles = barriles - 50  
        
        
        ejecutar_consulta_segura(  
            "UPDATE juego_pirata SET barriles = ? WHERE id = ?",  
            (nuevos_barriles, user_id)  
        )  
        
        print(f"✅ [VENGANZA DEBUG] Combate de venganza preparado exitosamente")
        
        return jsonify({  
            "jugador": {  
                "id": user_id,  
                "nombre": jugador_nombre,  
                "hp_barco": hp_barco,  
                "prestigio": prestigio,  
                "victorias": victorias,  
                "derrotas": derrotas,  
                "nivel_barco": nivel_barco,  
                "nivel_canon": nivel_canon,  
                "nivel_velas": nivel_velas,  
                "barriles_restantes": nuevos_barriles,
                "es_venganza": True
            },  
            "oponente": {  
                "id": oponente_id_db,  
                "nombre": oponente_nombre,  
                "hp": oponente_hp,  
                "prestigio": oponente_prestigio,  
                "victorias": oponente_victorias,  
                "derrotas": oponente_derrotas,  
                "nivel": oponente_nivel_barco,  
                "nivel_barco": oponente_nivel_barco,  
                "nivel_canon": oponente_nivel_canon,  
                "nivel_velas": oponente_nivel_velas  
            },  
            "costo_combate": 50,
            "es_venganza": True
        })  
        
    except Exception as e:
        print(f"❌ [VENGANZA DEBUG] Error en buscar_combate_venganza: {str(e)}")
        import traceback  
        print(f"📋 [VENGANZA DEBUG] Stack trace: {traceback.format_exc()}")  
        return jsonify({"error": "Error interno del servidor"}), 500



@app.route('/juego_alta_baja')
def juego_alta_baja():
    """Página principal del juego Alta o Baja"""
    return render_template('alta_baja.html')
    
@app.route('/api/datos-alta-baja')
def obtener_datos_alta_baja():
    """Obtiene datos del usuario para Alta o Baja"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    try:
        # Obtener datos del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
        
        if not usuario_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        balance_actual = usuario_data[0]
        nombre_usuario = usuario_data[1]
        bono_usuario = bono_data[0] if bono_data else 0
        rollover_requerido = bono_data[1] if bono_data and len(bono_data) > 1 else 0
        
        # Cargar estadísticas del juego
        minijuegos_data = cargar_minijuegos_data()
        alta_baja_stats = minijuegos_data.get("ALTA BAJA", {})
        
        return jsonify({
            "usuario": {
                "id": user_id,
                "nombre": nombre_usuario,
                "balance": balance_actual,
                "bono": bono_usuario,
                "rollover_requerido": rollover_requerido
            },
            "estadisticas": {
                "fichas_ganadas": alta_baja_stats.get("FichGanadas", {}).get(str(user_id), 0),
                "fichas_perdidas": alta_baja_stats.get("FichPerdidas", {}).get(str(user_id), 0),
                "apuestas_ganadas": alta_baja_stats.get("BetWin", {}).get(str(user_id), 0),
                "apuestas_perdidas": alta_baja_stats.get("BetLost", {}).get(str(user_id), 0)
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo datos Alta/Baja: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/jugar-alta-baja', methods=['POST'])
def jugar_alta_baja():
    """Procesa una jugada de Alta o Baja"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    try:
        data = request.get_json()
        eleccion = data.get('eleccion')  # 'alta' o 'baja'
        monto = data.get('monto', 10)    # 10, 30, 50
        metodo_pago = data.get('metodo_pago', 'balance')  # 'bono' o 'balance'
        
        if eleccion not in ['alta', 'baja']:
            return jsonify({"error": "Elección inválida"}), 400
        
        if monto not in [10, 30, 50]:
            return jsonify({"error": "Monto inválido"}), 400
        
        # Obtener datos del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
        
        if not usuario_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        balance_actual = usuario_data[0]
        nombre_usuario = usuario_data[1]
        bono_usuario = bono_data[0] if bono_data else 0
        
        # Verificar saldo según método de pago
        if metodo_pago == 'bono' and bono_usuario < monto:
            return jsonify({
                "error": "Bono insuficiente",
                "saldo_actual": bono_usuario,
                "tipo": "bono"
            }), 400
            
        if metodo_pago == 'balance' and balance_actual < monto:
            return jsonify({
                "error": "Balance insuficiente", 
                "saldo_actual": balance_actual,
                "tipo": "balance"
            }), 400
        
        # Generar número aleatorio (con sesgo según elección)
        if eleccion == "alta":
            numero_aleatorio = random.randint(0, 85)
        else:  # baja
            numero_aleatorio = random.randint(15, 100)
        
        # Determinar resultado
        resultado = "baja" if numero_aleatorio <= 50 else "alta"
        ganador = eleccion == resultado
        
        # Cargar y actualizar estadísticas
        minijuegos_data = cargar_minijuegos_data()
        
        if "ALTA BAJA" not in minijuegos_data:
            minijuegos_data["ALTA BAJA"] = {
                "FichGanadas": {},
                "FichPerdidas": {},
                "BetWin": {},
                "BetLost": {}
            }
        
        alta_baja_data = minijuegos_data["ALTA BAJA"]
        user_id_str = str(user_id)
        
        # Actualizar saldo según resultado
        if ganador:
            if metodo_pago == 'bono':
                # Ganar con bono
                nuevo_bono = bono_usuario + monto
                nuevo_rollover = (bono_data[1] if bono_data and len(bono_data) > 1 else 0) + monto
                actualizar_registro("bono_apuesta", user_id, {
                    "Bono": nuevo_bono,
                    "Rollover_requerido": nuevo_rollover
                })
                saldo_final = nuevo_bono
            else:
                # Ganar con balance
                nuevo_balance = balance_actual + monto
                actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
                saldo_final = nuevo_balance
            
            # Actualizar estadísticas (ganador)
            alta_baja_data["FichGanadas"][user_id_str] = alta_baja_data["FichGanadas"].get(user_id_str, 0) + monto
            alta_baja_data["BetWin"][user_id_str] = alta_baja_data["BetWin"].get(user_id_str, 0) + 1
            
        else:
            if metodo_pago == 'bono':
                # Perder con bono
                nuevo_bono = bono_usuario - monto
                actualizar_registro("bono_apuesta", user_id, {"Bono": nuevo_bono})
                saldo_final = nuevo_bono
            else:
                # Perder con balance
                nuevo_balance = balance_actual - monto
                actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
                saldo_final = nuevo_balance
            
            # Actualizar estadísticas (perdedor)
            alta_baja_data["FichPerdidas"][user_id_str] = alta_baja_data["FichPerdidas"].get(user_id_str, 0) + monto
            alta_baja_data["BetLost"][user_id_str] = alta_baja_data["BetLost"].get(user_id_str, 0) + 1
        
        # Guardar estadísticas
        guardar_minijuegos_data(minijuegos_data)
        
        # Registrar en historial
        registrar_historial_juego(user_id, "ALTA BAJA", monto, ganador, metodo_pago)
        
        return jsonify({
            "exito": True,
            "resultado": {
                "numero": numero_aleatorio,
                "eleccion_usuario": eleccion,
                "resultado_real": resultado,
                "ganador": ganador,
                "monto": monto,
                "metodo_pago": metodo_pago,
                "saldo_final": saldo_final
            },
            "estadisticas_actualizadas": {
                "fichas_ganadas": alta_baja_data["FichGanadas"].get(user_id_str, 0),
                "fichas_perdidas": alta_baja_data["FichPerdidas"].get(user_id_str, 0),
                "apuestas_ganadas": alta_baja_data["BetWin"].get(user_id_str, 0),
                "apuestas_perdidas": alta_baja_data["BetLost"].get(user_id_str, 0)
            }
        })
        
    except Exception as e:
        print(f"❌ Error en juego Alta/Baja: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

def cargar_minijuegos_data():
    """Carga datos de minijuegos desde JSON"""
    try:
        with open('minijuegos_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_minijuegos_data(data):
    """Guarda datos de minijuegos en JSON"""
    try:
        with open('minijuegos_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error guardando datos minijuegos: {str(e)}")
        return False

def registrar_historial_juego(user_id, juego, monto, ganador, metodo_pago):
    """Registra jugada en el historial"""
    try:
        ejecutar_consulta_segura(
            """INSERT INTO historial_juegos 
               (user_id, juego, monto, resultado, metodo_pago, fecha) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, juego, monto, 'GANADO' if ganador else 'PERDIDO', metodo_pago, datetime.now())
        )
    except Exception as e:
        print(f"❌ Error registrando historial: {str(e)}")        
@app.route('/piedra-papel-tijera')
def piedra_papel_tijera():
    """Página principal del juego Piedra, Papel o Tijera"""
    return render_template('piedra_papel_tijera.html')

@app.route('/api/datos-piedra-papel-tijera')
def datos_piedra_papel_tijera():
    """Obtiene datos del usuario para Piedra, Papel o Tijera"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    try:
        # Obtener datos del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
        
        if not usuario_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        balance_actual = usuario_data[0]
        nombre_usuario = usuario_data[1]
        bono_usuario = bono_data[0] if bono_data else 0
        rollover_requerido = bono_data[1] if bono_data and len(bono_data) > 1 else 0
        
        # Cargar estadísticas del juego
        minijuegos_data = cargar_minijuegos_data()
        ppt_stats = minijuegos_data.get("PIEDRA PAPEL TIJERA", {})
        
        return jsonify({
            "usuario": {
                "id": user_id,
                "nombre": nombre_usuario,
                "balance": balance_actual,
                "bono": bono_usuario,
                "rollover_requerido": rollover_requerido
            },
            "estadisticas": {
                "fichas_ganadas": ppt_stats.get("FichGanadas", {}).get(str(user_id), 0),
                "fichas_perdidas": ppt_stats.get("FichPerdidas", {}).get(str(user_id), 0),
                "apuestas_ganadas": ppt_stats.get("BetWin", {}).get(str(user_id), 0),
                "apuestas_perdidas": ppt_stats.get("BetLost", {}).get(str(user_id), 0)
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo datos PPT: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/jugar-ppt', methods=['POST'])
def jugar_ppt():
    """Procesa una jugada de Piedra, Papel o Tijera"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuario no autenticado"}), 401
    
    try:
        data = request.get_json()
        jugada_usuario = data.get('jugada')  # 'piedra', 'papel', 'tijera'
        metodo_pago = data.get('metodo_pago', 'balance')  # 'bono' o 'balance'
        
        if jugada_usuario not in ['piedra', 'papel', 'tijera']:
            return jsonify({"error": "Jugada inválida"}), 400
        
        # Monto fijo de 50 CUP
        monto_apuesta = 50
        
        # Obtener datos del usuario
        usuario_data = obtener_registro("usuarios", user_id, "Balance, Nombre")
        bono_data = obtener_registro("bono_apuesta", user_id, "Bono, Rollover_requerido")
        
        if not usuario_data:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        balance_actual = usuario_data[0]
        nombre_usuario = usuario_data[1]
        bono_usuario = bono_data[0] if bono_data else 0
        rollover_actual = bono_data[1] if bono_data and len(bono_data) > 1 else 0
        
        # Verificar saldo según método de pago
        if metodo_pago == 'bono' and bono_usuario < monto_apuesta:
            return jsonify({
                "error": "Bono insuficiente",
                "saldo_actual": bono_usuario,
                "tipo": "bono"
            }), 400
            
        if metodo_pago == 'balance' and balance_actual < monto_apuesta:
            return jsonify({
                "error": "Balance insuficiente", 
                "saldo_actual": balance_actual,
                "tipo": "balance"
            }), 400
        
        # Descontar apuesta primero
        if metodo_pago == 'bono':
            nuevo_bono = bono_usuario - monto_apuesta
            nuevo_rollover = rollover_actual + (monto_apuesta * 4)
            actualizar_registro("bono_apuesta", user_id, {
                "Bono": nuevo_bono,
                "Rollover_requerido": nuevo_rollover
            })
            saldo_temporal = nuevo_bono
        else:
            nuevo_balance = balance_actual - monto_apuesta
            actualizar_registro("usuarios", user_id, {"Balance": nuevo_balance})
            saldo_temporal = nuevo_balance
        
        # Generar jugada del oponente con probabilidades sesgadas
        jugada_oponente = seleccionar_jugada_con_probabilidad(jugada_usuario)
        
        # Determinar resultado
        resultado = determinar_ganador_ppt(jugada_usuario, jugada_oponente)
        
        # Cargar y actualizar estadísticas
        minijuegos_data = cargar_minijuegos_data()
        
        if "PIEDRA PAPEL TIJERA" not in minijuegos_data:
            minijuegos_data["PIEDRA PAPEL TIJERA"] = {
                "FichGanadas": {},
                "FichPerdidas": {},
                "BetWin": {},
                "BetLost": {}
            }
        
        ppt_data = minijuegos_data["PIEDRA PAPEL TIJERA"]
        user_id_str = str(user_id)
        
        # Manejar resultado final
        if resultado == 1:  # Gana usuario
            premio = 90
            if metodo_pago == 'bono':
                saldo_final = nuevo_bono + premio
                actualizar_registro("bono_apuesta", user_id, {
                    "Bono": saldo_final,
                    "Rollover_requerido": nuevo_rollover + premio
                })
            else:
                saldo_final = nuevo_balance + premio
                actualizar_registro("usuarios", user_id, {"Balance": saldo_final})
            
            # Estadísticas ganador
            ppt_data["FichGanadas"][user_id_str] = ppt_data["FichGanadas"].get(user_id_str, 0) + 40
            ppt_data["BetWin"][user_id_str] = ppt_data["BetWin"].get(user_id_str, 0) + 1
            
        elif resultado == 2:  # Pierde usuario
            saldo_final = saldo_temporal  # Ya se descontó al inicio
            # Estadísticas perdedor
            ppt_data["FichPerdidas"][user_id_str] = ppt_data["FichPerdidas"].get(user_id_str, 0) + monto_apuesta
            ppt_data["BetLost"][user_id_str] = ppt_data["BetLost"].get(user_id_str, 0) + 1
            
        else:  # Empate
            # Devolver apuesta
            if metodo_pago == 'bono':
                saldo_final = nuevo_bono + monto_apuesta
                actualizar_registro("bono_apuesta", user_id, {
                    "Bono": saldo_final,
                    "Rollover_requerido": nuevo_rollover
                })
            else:
                saldo_final = nuevo_balance + monto_apuesta
                actualizar_registro("usuarios", user_id, {"Balance": saldo_final})
        
        # Guardar estadísticas
        guardar_minijuegos_data(minijuegos_data)
        
        # Registrar en historial
        registrar_historial_juego(user_id, "PIEDRA PAPEL TIJERA", monto_apuesta, resultado == 1, metodo_pago)
        
        return jsonify({
            "exito": True,
            "resultado": {
                "jugada_usuario": jugada_usuario,
                "jugada_oponente": jugada_oponente,
                "resultado": resultado,  # 1=gana, 2=pierde, 0=empate
                "monto_apuesta": monto_apuesta,
                "premio": 90 if resultado == 1 else 0,
                "metodo_pago": metodo_pago,
                "saldo_final": saldo_final
            },
            "estadisticas_actualizadas": {
                "fichas_ganadas": ppt_data["FichGanadas"].get(user_id_str, 0),
                "fichas_perdidas": ppt_data["FichPerdidas"].get(user_id_str, 0),
                "apuestas_ganadas": ppt_data["BetWin"].get(user_id_str, 0),
                "apuestas_perdidas": ppt_data["BetLost"].get(user_id_str, 0)
            }
        })
        
    except Exception as e:
        print(f"❌ Error en juego PPT: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

def seleccionar_jugada_con_probabilidad(jugada_usuario):
    """Selecciona la jugada del oponente con probabilidades sesgadas"""
    if jugada_usuario == "piedra":
        jugadas = ["piedra", "papel", "tijera"]
        probabilidades = [0.20, 0.5, 0.3]  # Más probabilidad de papel
    elif jugada_usuario == "papel":
        jugadas = ["piedra", "papel", "tijera"]
        probabilidades = [0.3, 0.2, 0.5]  # Más probabilidad de tijera
    elif jugada_usuario == "tijera":
        jugadas = ["piedra", "papel", "tijera"]
        probabilidades = [0.5, 0.3, 0.2]  # Más probabilidad de piedra
    else:
        return random.choice(["piedra", "papel", "tijera"])
    
    return random.choices(jugadas, weights=probabilidades, k=1)[0]

def determinar_ganador_ppt(jugada1, jugada2):
    """Determina el ganador del juego"""
    if jugada1 == jugada2:
        return 0  # Empate
    elif (jugada1 == "piedra" and jugada2 == "tijera") or \
         (jugada1 == "tijera" and jugada2 == "papel") or \
         (jugada1 == "papel" and jugada2 == "piedra"):
        return 1  # Gana jugador 1
    else:
        return 2  # Gana jugador 2                
                                
                                
@app.route('/forgot_password')
def forgot_password():
    """Renderiza la página de recuperación de contraseña"""
    return render_template('forgot_password.html')




@app.route('/api/solicitar-recuperacion', methods=['POST'])
def api_solicitar_recuperacion():
    """Solicita el proceso de recuperación de contraseña usando columnas existentes"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'ID de usuario requerido'}), 400
        
        # Verificar si el usuario existe y tiene registro completo
        usuario_data = obtener_registro("usuarios", user_id, "Email, RegistroCompleto")
        
        if not usuario_data:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        email, registro_completo = usuario_data
        
        if not registro_completo:
            return jsonify({'success': False, 'message': 'Usuario no tiene registro completo'}), 400
        
        # Generar código de verificación
        verification_code = secrets.randbelow(900000) + 100000
        expiration_time = datetime.now() + timedelta(minutes=10)
        
        # Guardar código en base de datos USANDO COLUMNAS EXISTENTES del registro
        exito = actualizar_registro("usuarios", user_id, {
            'VerificationCode': str(verification_code),  # Usar misma columna que registro
            'VerificationExpiry': expiration_time.isoformat(),  # Usar misma columna que registro
            'RegistroPendiente': True  # Usar esta columna para indicar recuperación pendiente
        })
        
        if not exito:
            return jsonify({'success': False, 'message': 'Error al guardar código de recuperación'}), 500
        
        # Enviar código por Telegram
        if enviar_mensaje_recuperacion(user_id, verification_code):
            return jsonify({'success': True, 'message': 'Código de verificación enviado a tu Telegram'})
        else:
            return jsonify({'success': False, 'message': 'Error al enviar código de verificación'}), 500
            
    except Exception as e:
        print(f"Error en solicitar recuperación: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@app.route('/api/verificar-codigo-recuperacion', methods=['POST'])
def api_verificar_codigo_recuperacion():
    """Verifica el código de recuperación usando columnas existentes"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        verification_code = data.get('verification_code')
        
        if not user_id or not verification_code:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        # Obtener datos de verificación (usando columnas del registro)
        usuario_data = obtener_registro("usuarios", user_id, 
                                      "VerificationCode, VerificationExpiry, RegistroPendiente")
        
        if not usuario_data:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        verification_code_db, expiry_db, registro_pendiente = usuario_data
        
        if not registro_pendiente:
            return jsonify({'success': False, 'message': 'No hay recuperación pendiente'}), 400
        
        # Verificar expiración
        expiration_time = datetime.fromisoformat(expiry_db)
        if datetime.now() > expiration_time:
            # Limpiar datos de verificación
            actualizar_registro("usuarios", user_id, {
                'VerificationCode': None,
                'VerificationExpiry': None,
                'RegistroPendiente': False
            })
            return jsonify({'success': False, 'message': 'El código ha expirado'}), 400
        
        # Verificar código
        if verification_code != verification_code_db:
            return jsonify({'success': False, 'message': 'Código incorrecto'}), 400
        
        # Marcar como verificado (usamos Email_temp para indicar que está verificado para recuperación)
        actualizar_registro("usuarios", user_id, {
            'Email_temp': 'RECOVERY_VERIFIED'  # Usar esta columna para marcar verificación
        })
        
        return jsonify({'success': True, 'message': 'Código verificado correctamente'})
        
    except Exception as e:
        print(f"Error en verificar código recuperación: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@app.route('/api/cambiar-contrasena', methods=['POST'])
def api_cambiar_contrasena():
    """Cambia la contraseña del usuario después de verificación"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_password = data.get('new_password')
        
        if not user_id or not new_password:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        # Verificar que la recuperación está verificada (usando Email_temp)
        usuario_data = obtener_registro("usuarios", user_id, "Email_temp")
        
        if not usuario_data or usuario_data[0] != 'RECOVERY_VERIFIED':
            return jsonify({'success': False, 'message': 'Recuperación no verificada'}), 400
        
        # Cambiar contraseña
        hashed_password = generate_password_hash(new_password)
        exito = actualizar_registro("usuarios", user_id, {
            'Password': hashed_password,
            # Limpiar datos temporales
            'VerificationCode': None,
            'VerificationExpiry': None,
            'RegistroPendiente': False,
            'Email_temp': None  # Limpiar marca de verificación
        })
        
        if not exito:
            return jsonify({'success': False, 'message': 'Error al cambiar contraseña'}), 500
        
        return jsonify({'success': True, 'message': 'Contraseña cambiada exitosamente'})
        
    except Exception as e:
        print(f"Error en cambiar contraseña: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@app.route('/api/reenviar-codigo-recuperacion', methods=['POST'])
def api_reenviar_codigo_recuperacion():
    """Reenvía el código de recuperación usando columnas existentes"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'ID de usuario requerido'}), 400
        
        # Verificar que hay una recuperación pendiente
        usuario_data = obtener_registro("usuarios", user_id, "RegistroPendiente")
        
        if not usuario_data or not usuario_data[0]:
            return jsonify({'success': False, 'message': 'No hay recuperación pendiente'}), 400
        
        # Generar nuevo código
        verification_code = secrets.randbelow(900000) + 100000
        expiration_time = datetime.now() + timedelta(minutes=10)
        
        # Actualizar código en base de datos (usando columnas existentes)
        exito = actualizar_registro("usuarios", user_id, {
            'VerificationCode': str(verification_code),
            'VerificationExpiry': expiration_time.isoformat()
        })
        
        if not exito:
            return jsonify({'success': False, 'message': 'Error al actualizar código'}), 500
        
        # Reenviar por Telegram
        if enviar_mensaje_recuperacion(user_id, verification_code):
            return jsonify({'success': True, 'message': 'Código reenviado correctamente'})
        else:
            return jsonify({'success': False, 'message': 'Error al reenviar código'}), 500
            
    except Exception as e:
        print(f"Error en reenviar código: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

def enviar_mensaje_recuperacion(user_id, verification_code):
    """
    Envía un mensaje de recuperación al usuario a través del bot de Telegram
    """
    try:
        mensaje = (
            "🔐 <b>Recuperación de Contraseña QvaPlay</b>\n\n"
            f"Tu código de verificación para recuperar tu contraseña es: <code>{verification_code}</code>\n\n"
            "Este código expirará en 10 minutos. "
            "Si no solicitaste recuperar tu contraseña, por favor ignora este mensaje."
        )

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": user_id,
            "text": mensaje,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json().get("ok", False)

    except Exception as e:
        print(f"Error enviando mensaje de recuperación: {e}")
        return False
                                


import subprocess
import threading


def save_url_to_json(url):
    """Guarda la URL en un archivo JSON"""
    try:
        # Asegurar que la URL no termine con /
        url = url.rstrip('/')
        
        data = {
            "tunnel_url": url,
            "local_url": "http://localhost:5001",
            "status": "active"
        }
        
        with open("tunnel_urls.json", "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 URL guardada en: tunnel_urls.json")
        return True
    except Exception as e:
        print(f"❌ Error guardando URL: {e}")
        return False

def load_previous_url():
    """Carga la URL anterior si existe"""
    try:
        if os.path.exists("tunnel_urls.json"):
            with open("tunnel_urls.json", "r") as f:
                data = json.load(f)
                return data.get("tunnel_url")
    except:
        pass
    return None

def start_cloudflared_with_url():
    """Inicia cloudflared y captura la URL"""
    try:
        print("🚀 Iniciando Cloudflare Tunnel...")
        
        # Cargar URL anterior si existe
        previous_url = load_previous_url()
        if previous_url:
            print(f"📖 URL anterior: {previous_url}")
        
        # Ejecutar cloudflared
        process = subprocess.Popen([
            "cloudflared", "tunnel",
            "--url", "http://127.0.0.1:5001",
            "--no-autoupdate"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        url_found = threading.Event()
        tunnel_url = [None]
        
        def read_output():
            while True:
                # Leer de stderr (donde está la URL)
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line:
                    line = line.strip()
                    # Mostrar logs normales
                    if "INF" in line or "ERR" in line:
                        print(f"🔧 {line}")
                    
                    # BUSCAR PATRONES DE URL MÁS FLEXIBLES
                    if ".trycloudflare.com" in line:
                        # Usar regex para encontrar la URL completa
                        url_pattern = r'https://[a-zA-Z0-9-]+\.trycloudflare\.com'
                        matches = re.findall(url_pattern, line)
                        if matches:
                            tunnel_url[0] = matches[0]
                            print(f"\n🎯🎯🎯 URL PÚBLICA ENCONTRADA: {tunnel_url[0]}")
                            print("📢 ¡Comparte este link para acceso público!")
                            
                            # GUARDAR URL EN JSON
                            if save_url_to_json(tunnel_url[0]):
                                print("✅ URL guardada exitosamente")
                            
                            url_found.set()
                            break
                        
                        # Si no encuentra con https://, buscar solo el dominio
                        domain_pattern = r'[a-zA-Z0-9-]+\.trycloudflare\.com'
                        domain_matches = re.findall(domain_pattern, line)
                        if domain_matches and not tunnel_url[0]:
                            tunnel_url[0] = f"https://{domain_matches[0]}"
                            print(f"\n🎯🎯🎯 URL PÚBLICA ENCONTRADA: {tunnel_url[0]}")
                            print("📢 ¡Comparte este link para acceso público!")
                            
                            # GUARDAR URL EN JSON
                            if save_url_to_json(tunnel_url[0]):
                                print("✅ URL guardada exitosamente")
                            
                            url_found.set()
                            break
        
        # Leer salida en hilo separado
        reader_thread = threading.Thread(target=read_output, daemon=True)
        reader_thread.start()
        
        # Esperar máximo 20 segundos por la URL
        url_found.wait(timeout=20)
        
        if tunnel_url[0]:
            return process, tunnel_url[0]
        else:
            print("⏰ Timeout: Revisando logs manualmente...")
            # Intentar buscar la URL en los logs acumulados
            if "collectors-spin-robert-liability.trycloudflare.com" in str(process.stderr):
                manual_url = "https://collectors-spin-robert-liability.trycloudflare.com"
                print(f"🔍 URL encontrada manualmente: {manual_url}")
                
                # GUARDAR URL EN JSON
                if save_url_to_json(manual_url):
                    print("✅ URL guardada exitosamente")
                
                return process, manual_url
            return process, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

if __name__ == "__main__":
    print("🌐 INICIANDO SERVIDOR + CLOUDFLARE TUNNEL")
    print("=" * 60)
    
    # Verificar si existe archivo anterior
    if os.path.exists("tunnel_urls.json"):
        print("📁 Archivo JSON anterior encontrado (será actualizado)")
    
    tunnel_process, public_url = start_cloudflared_with_url()
    
    if public_url:
        print(f"\n" + "=" * 60)
        print(f"✅ TUNNEL ACTIVO: {public_url}")
        print("=" * 60)
        
        # Verificar que se guardó correctamente
        if os.path.exists("tunnel_urls.json"):
            try:
                with open("tunnel_urls.json", "r") as f:
                    saved_data = json.load(f)
                    print(f"💾 URL guardada: {saved_data['tunnel_url']}")
            except Exception as e:
                print(f"⚠️  Error leyendo archivo guardado: {e}")
    else:
        print(f"\n⚠️  URL no obtenida automáticamente, pero el tunnel está activo")
        print("💡 La URL debería ser: https://collectors-spin-robert-liability.trycloudflare.com")
        
        # Intentar guardar la URL manualmente si se conoce
        manual_url = "https://collectors-spin-robert-liability.trycloudflare.com"
        if save_url_to_json(manual_url):
            print("✅ URL manual guardada en JSON")
    
    print(f"🚀 Servidor local: http://localhost:5001")
    print(f"🌐 Servidor red: http://38.146.27.86:5001")
    print("=" * 60)
    
    # Iniciar servidor Flask
    # Iniciar servidor con SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5001, use_reloader=False)