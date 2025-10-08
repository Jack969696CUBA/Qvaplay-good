import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext, ConversationHandler, ContextTypes, JobQueue
from telegram import ChatMember
import random
import uuid
from functools import wraps  
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
import aiofiles
import asyncio
from aiogram import types
import traceback
import threading
import time as tm  
from datetime import datetime, time, timedelta
import pytz 
import json
import os
import re
import aiohttp
import requests
import shutil

lock_data = asyncio.Lock()
lock_apuestas = asyncio.Lock()
lock_minijuegos = asyncio.Lock()
has_lock = asyncio.Lock()
DB_FILE = "user_data.db"

logging.basicConfig(level=logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)





import aiofiles
import json

async def load_data():
    async with aiofiles.open(file_path, mode='r') as f:
        contents = await f.read()
        return json.loads(contents)
        
async def save_data(data):
    async with aiofiles.open(file_path, mode='r') as f:
        contents = await f.read()
        return json.loads(contents)
async def cargar_apuestas():
    async with aiofiles.open(file_path, mode='r') as f:
        contents = await f.read()
        return json.loads(contents)
        
async def guardar_apuestas(data):
    async with aiofiles.open(file_path, mode='r') as f:
        contents = await f.read()
        return json.loads(contents)




#xxxxxxxxxxxxxxx
import sqlite3
import time
import logging

def ejecutar_consulta_segura(consulta, parametros=(), reintentos=5, demora=0.1, obtener_resultados=False):
    """
    Ejecuta una consulta en SQLite con reintentos si la base de datos está bloqueada.
    
    :param consulta: Consulta SQL a ejecutar
    :param parametros: Parámetros para la consulta (tupla)
    :param reintentos: Número máximo de reintentos
    :param demora: Tiempo de espera entre reintentos en segundos
    :param obtener_resultados: Si es True, devuelve los resultados de la consulta
    :return: Si obtener_resultados es True, devuelve los resultados, de lo contrario None
    """
    for intento in range(reintentos):
        try:
            conexion = sqlite3.connect(DB_FILE)
            cursor = conexion.cursor()
            cursor.execute(consulta, parametros)
            
            if obtener_resultados:
                resultados = cursor.fetchall()
            else:
                resultados = None
                
            conexion.commit()
            conexion.close()
            
            return resultados  # Éxito, devolver resultados si se solicitaron
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning(f"Base de datos bloqueada, reintentando en {demora} segundos (intento {intento + 1}/{reintentos})")
                time.sleep(demora)  # Esperar antes de reintentar
            else:
                logger.error(f"Error operacional en la base de datos: {e}")
                raise  # Si es otro error, no reintentar y propagar la excepción
                
        except sqlite3.Error as e:
            logger.error(f"Error en la base de datos: {e}")
            raise  # Propagrar otros errores de SQLite
            
    raise Exception("No se pudo completar la operación en la base de datos después de varios intentos")

# Función auxiliar para obtener un registro específico
def obtener_registro(tabla, clave, columnas="*"):
    """
    Obtiene un registro específico de la base de datos de forma segura.
    
    :param tabla: Nombre de la tabla
    :param clave: Puede ser un valor simple (str/int) o una tupla para claves compuestas
    :param columnas: Columnas a seleccionar (por defecto todas)
    :return: Registro solicitado o None si no existe
    """
    try:
        if isinstance(clave, tuple):
            # Determinar el nombre de la segunda columna según la tabla
            if tabla == "mejoras":
                segunda_columna = "tipo"
            elif tabla == "promociones":
                segunda_columna = "clave"
            else:
                segunda_columna = "id"  # Valor por defecto, aunque debería manejarse caso por caso
                
            consulta = f"SELECT {columnas} FROM {tabla} WHERE id = ? AND {segunda_columna} = ?"
            resultado = ejecutar_consulta_segura(consulta, clave, obtener_resultados=True)
        else:
            # Clave primaria simple
            consulta = f"SELECT {columnas} FROM {tabla} WHERE id = ?"
            resultado = ejecutar_consulta_segura(consulta, (clave,), obtener_resultados=True)
        
        return resultado[0] if resultado else None
    except Exception as e:
        logger.error(f"Error al obtener registro de {tabla} para clave {clave}: {e}")
        return None


def actualizar_registro(tabla, clave, campos_valores):
    """
    Actualiza un registro específico en la base de datos de forma segura.
    
    :param tabla: Nombre de la tabla
    :param clave: Puede ser un valor simple (str/int) o una tupla para claves compuestas
    :param campos_valores: Diccionario con campos y valores a actualizar
    :return: True si la actualización fue exitosa, False en caso contrario
    """
    try:
        # Construir la parte SET de la consulta
        set_campos = ", ".join([f"{campo} = ?" for campo in campos_valores.keys()])
        valores = list(campos_valores.values())
        
        if isinstance(clave, tuple):
            # Determinar el nombre de la segunda columna según la tabla
            if tabla == "mejoras":
                segunda_columna = "tipo"
            elif tabla == "promociones":
                segunda_columna = "clave"
            else:
                segunda_columna = "id"  # Valor por defecto
                
            consulta = f"UPDATE {tabla} SET {set_campos} WHERE id = ? AND {segunda_columna} = ?"
            valores.extend(clave)  # Añadir los componentes de la clave al final
        else:
            # Clave primaria simple
            consulta = f"UPDATE {tabla} SET {set_campos} WHERE id = ?"
            valores.append(clave)  # Añadir la clave al final
        
        ejecutar_consulta_segura(consulta, tuple(valores))
        return True
    except Exception as e:
        logger.error(f"Error al actualizar registro en {tabla} para clave {clave}: {e}")
        return False


def insertar_registro(tabla, campos_valores):
    """
    Inserta un nuevo registro en la base de datos de forma segura.
    
    :param tabla: Nombre de la tabla
    :param campos_valores: Diccionario con campos y valores a insertar
    :return: True si la inserción fue exitosa, False en caso contrario
    """
    try:
        # Construir la parte de columnas y valores de la consulta
        columnas = ", ".join(campos_valores.keys())
        placeholders = ", ".join(["?"] * len(campos_valores))
        valores = list(campos_valores.values())
        
        consulta = f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})"
        
        ejecutar_consulta_segura(consulta, tuple(valores))
        return True
    except Exception as e:
        print(f"Error al insertar registro en {tabla}: {e}")
        return False

def guardar_apuesta_en_db(apuesta):
    """
    Guarda una apuesta en la base de datos usando las funciones de acceso seguro
    
    :param apuesta: Diccionario con los datos de la apuesta
    :return: True si se guardó correctamente, False en caso contrario
    """
    try:
        # Determinar si es apuesta combinada
        es_combinada = 'selecciones' in apuesta and len(apuesta['selecciones']) > 1
        
        # Preparar los datos para la inserción
        campos_valores = {
            'usuario_id': apuesta.get('usuario_id', ''),
            'user_name': apuesta.get('user_name', ''),
            'fecha_realizada': apuesta.get('fecha_realizada', datetime.now().strftime('%d/%m/%Y %H:%M:%S')),
            'fecha_inicio': apuesta.get('fecha_inicio'),
            'monto': apuesta.get('monto', 0),
            'cuota': apuesta.get('cuota', 0),
            'ganancia': apuesta.get('ganancia', 0),
            'estado': apuesta.get('estado', '⌛Pendiente'),
            'bono': apuesta.get('bono', 0),
            'balance': apuesta.get('balance'),
            'betting': apuesta.get('betting', 'SIMPLE'),
            'id_ticket': apuesta.get('id_ticket', ''),
            'event_id': apuesta.get('event_id'),
            'deporte': apuesta.get('deporte'),
            'liga': apuesta.get('liga'),
            'sport_key': apuesta.get('sport_key'),
            'partido': apuesta.get('partido'),
            'favorito': apuesta.get('favorito'),
            'tipo_apuesta': apuesta.get('tipo_apuesta'),
            'home_logo': apuesta.get('home_logo'),
            'away_logo': apuesta.get('away_logo'),
            'mensaje_canal_url': apuesta.get('mensaje_canal_url'),
            'mensaje_canal_id': apuesta.get('mensaje_canal_id'),
            'minuto': apuesta.get('minuto'),
            'marcador': apuesta.get('marcador'),
            'completed': apuesta.get('completed', False),
            'last_update': apuesta.get('last_update'),
            'es_combinada': es_combinada,
            'selecciones_json': json.dumps(apuesta.get('selecciones', [])),
            'scores_json': json.dumps(apuesta.get('scores', []))
        }
        
        # Insertar en la base de datos
        return insertar_registro('apuestas', campos_valores)
        
    except Exception as e:
        print(f"Error al guardar apuesta en DB: {e}")
        return False
def obtener_apuestas_usuario(user_id):
    """
    Obtiene todas las apuestas de un usuario desde la base de datos
    """
    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM apuestas WHERE usuario_id = ? ORDER BY fecha_realizada DESC", (user_id,))
        column_names = [description[0] for description in cursor.description]
        apuestas_db = cursor.fetchall()
        conn.close()
        
        if not apuestas_db:
            return []
        
        apuestas_formateadas = []
        for apuesta in apuestas_db:
            # Crear diccionario con nombres de columnas
            apuesta_dict = dict(zip(column_names, apuesta))
            
          
            
            # Procesar campos JSON - PRIMERO usar el campo betting de la base de datos
            betting = apuesta_dict.get('betting')
            
            if apuesta_dict.get('selecciones_json'):
                try:
                    selecciones_data = json.loads(apuesta_dict['selecciones_json'])
                    print(f"DEBUG - selecciones_data tipo: {type(selecciones_data)}, longitud: {len(selecciones_data) if isinstance(selecciones_data, list) else 'N/A'}")
                    
                    # DETERMINAR TIPO DE APUESTA BASADO EN EL CAMPO BETTING DE LA DB
                    if betting == "COMBINADA":
                        # Es una apuesta combinada real
                        apuesta_dict['selecciones'] = selecciones_data
                        apuesta_dict['betting'] = 'COMBINADA'
                        
                        
                    else:
                        # Es una apuesta simple - los datos están en el primer elemento
                        if isinstance(selecciones_data, list) and len(selecciones_data) > 0 and isinstance(selecciones_data[0], dict):
                            # Actualizar campos faltantes desde el JSON
                            for key, value in selecciones_data[0].items():
                                if key not in apuesta_dict or apuesta_dict[key] is None:
                                    apuesta_dict[key] = value
                            apuesta_dict['selecciones'] = []
                            print(f"DEBUG - Apuesta SIMPLE procesada")
                        else:
                            apuesta_dict['selecciones'] = []
                            
                except Exception as e:
                    print(f"Error parseando selecciones_json: {e}")
                    apuesta_dict['selecciones'] = []
                
                del apuesta_dict['selecciones_json']
            else:
                apuesta_dict['selecciones'] = []
            
            # Procesar scores JSON
            if apuesta_dict.get('scores_json'):
                try:
                    apuesta_dict['scores'] = json.loads(apuesta_dict['scores_json'])
                except:
                    apuesta_dict['scores'] = []
                del apuesta_dict['scores_json']
            else:
                apuesta_dict['scores'] = []
            
            # Asegurar que los campos críticos tengan valores
            if apuesta_dict.get('estado') is None:
                apuesta_dict['estado'] = '⌛Pendiente'
            
            if apuesta_dict.get('betting') is None:
                apuesta_dict['betting'] = 'PREPARTIDO'
            
            if apuesta_dict.get('tipo_apuesta') is None:
                apuesta_dict['tipo_apuesta'] = 'Apuesta'
            
            
            
            # Eliminar campo auxiliar
            if 'es_combinada' in apuesta_dict:
                del apuesta_dict['es_combinada']
            
            apuestas_formateadas.append(apuesta_dict)
        
        return apuestas_formateadas
        
    except Exception as e:
        print(f"Error en obtener_apuestas_usuario: {e}")
        import traceback
        traceback.print_exc()
        return []        
def obtener_apuestas_por_evento(event_id):
    """
    Obtiene todas las apuestas que contienen un event_id específico
    """
    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        
        # Buscar en apuestas simples (event_id en la columna event_id)
        cursor.execute("SELECT * FROM apuestas WHERE event_id = ?", (event_id,))
        apuestas_simples = cursor.fetchall()
        
        # Buscar en apuestas combinadas (event_id en selecciones_json)
        cursor.execute("SELECT * FROM apuestas WHERE betting = 'COMBINADA' AND selecciones_json LIKE ?", (f'%{event_id}%',))
        apuestas_combinadas = cursor.fetchall()
        
        conn.close()
        
        # Convertir a diccionarios y procesar JSON
        apuestas_formateadas = []
        
        for apuesta in apuestas_simples + apuestas_combinadas:
            apuesta_dict = dict(zip([column[0] for column in cursor.description], apuesta))
            
            # Procesar campos JSON
            if apuesta_dict.get('selecciones_json'):
                try:
                    apuesta_dict['selecciones'] = json.loads(apuesta_dict['selecciones_json'])
                except:
                    apuesta_dict['selecciones'] = []
            
            if apuesta_dict.get('scores_json'):
                try:
                    apuesta_dict['scores'] = json.loads(apuesta_dict['scores_json'])
                except:
                    apuesta_dict['scores'] = []
            
            apuestas_formateadas.append(apuesta_dict)
        
        return apuestas_formateadas
        
    except Exception as e:
        print(f"Error al obtener apuestas por evento: {e}")
        return []        
        
def obtener_todas_las_apuestas():
    """
    Obtiene todas las apuestas de la base de datos
    """
    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM apuestas")
        column_names = [description[0] for description in cursor.description]
        apuestas_db = cursor.fetchall()
        conn.close()
        
        if not apuestas_db:
            return []
        
        apuestas_formateadas = []
        for apuesta in apuestas_db:
            # Crear diccionario con nombres de columnas
            apuesta_dict = dict(zip(column_names, apuesta))
            
            # Procesar campos JSON
            if apuesta_dict.get('selecciones_json'):
                try:
                    selecciones_data = json.loads(apuesta_dict['selecciones_json'])
                    
                    # Determinar tipo de apuesta basado en el campo betting de la DB
                    betting = apuesta_dict.get('betting')
                    if betting == "COMBINADA":
                        apuesta_dict['selecciones'] = selecciones_data
                    else:
                        # Apuesta simple - los datos están en el primer elemento
                        if isinstance(selecciones_data, list) and len(selecciones_data) > 0 and isinstance(selecciones_data[0], dict):
                            for key, value in selecciones_data[0].items():
                                if key not in apuesta_dict or apuesta_dict[key] is None:
                                    apuesta_dict[key] = value
                            apuesta_dict['selecciones'] = []
                except Exception as e:
                    print(f"Error parseando selecciones_json: {e}")
                    apuesta_dict['selecciones'] = []
                
                del apuesta_dict['selecciones_json']
            
            # Procesar scores JSON
            if apuesta_dict.get('scores_json'):
                try:
                    apuesta_dict['scores'] = json.loads(apuesta_dict['scores_json'])
                except:
                    apuesta_dict['scores'] = []
                del apuesta_dict['scores_json']
            else:
                apuesta_dict['scores'] = []
            
            # Asegurar que los campos críticos tengan valores
            if apuesta_dict.get('estado') is None:
                apuesta_dict['estado'] = '⌛Pendiente'
            
            if apuesta_dict.get('betting') is None:
                apuesta_dict['betting'] = 'PREPARTIDO'
            
            if apuesta_dict.get('tipo_apuesta') is None:
                apuesta_dict['tipo_apuesta'] = 'Apuesta'
            
            # Eliminar campo auxiliar
            if 'es_combinada' in apuesta_dict:
                del apuesta_dict['es_combinada']
            
            apuestas_formateadas.append(apuesta_dict)
        
        return apuestas_formateadas
        
    except Exception as e:
        print(f"Error al obtener todas las apuestas: {e}")
        return []
        
def obtener_todos_los_resultados():
    """
    Obtiene todos los resultados de la base de datos
    """
    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM resultados")
        column_names = [description[0] for description in cursor.description]
        resultados_db = cursor.fetchall()
        conn.close()
        
        if not resultados_db:
            return {}
        
        # Convertir a diccionario con event_id como clave
        resultados_dict = {}
        for resultado in resultados_db:
            resultado_dict = dict(zip(column_names, resultado))
            resultados_dict[resultado_dict['event_id']] = resultado_dict
        
        return resultados_dict
        
    except Exception as e:
        print(f"Error al obtener resultados: {e}")
        return {}
# Y estas son las funciones para eliminar de la base de datos
def eliminar_apuesta_de_db(apuesta_id):
    """
    Elimina una apuesta específica de la base de datos
    """
    try:
        consulta = "DELETE FROM apuestas WHERE id = ?"
        ejecutar_consulta_segura(consulta, (apuesta_id,))
        return True
    except Exception as e:
        print(f"Error al eliminar apuesta {apuesta_id}: {e}")
        return False

def eliminar_todas_apuestas_usuario(user_id):
    """
    Elimina todas las apuestas pendientes de un usuario
    """
    try:
        consulta = "DELETE FROM apuestas WHERE usuario_id = ? AND estado IN ('⌛Pendiente', '🔚 Finalizado')"
        ejecutar_consulta_segura(consulta, (user_id,))
        return True
    except Exception as e:
        print(f"Error al eliminar apuestas del usuario {user_id}: {e}")
        return False


async def backup_periodico(context: ContextTypes.DEFAULT_TYPE):
    if hacer_backup_db():
        print("Backup automático realizado con éxito")
    else:
        print("Error en backup automático")

import shutil
import os
def hacer_backup_db():
    # Crear directorio de backups si no existe
    backup_dir = "backups_db"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Nombre del archivo de backup con timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(backup_dir, f"user_data_backup_{timestamp}.db")
    
    try:
        # Conexión a la base de datos original
        conn = sqlite3.connect('user_data.db')
        
        # Crear backup usando la API de SQLite
        backup_conn = sqlite3.connect(backup_file)
        conn.backup(backup_conn)
        
        # Cerrar conexiones
        backup_conn.close()
        conn.close()
        
        # Mantener solo los últimos 7 backups
        backups = [f for f in os.listdir(backup_dir) if f.startswith('user_data_backup_')]
        backups.sort(reverse=True)
        
        for old_backup in backups[7:]:
            os.remove(os.path.join(backup_dir, old_backup))
            
        return True
        
    except Exception as e:
        print(f"Error en backup: {e}")
        return False        
        
  #xxxxxxxxxxxxxxxx
  
  
  
  
  
  
  

# Claves requeridas para inicializar el JSON
REQUIRED_KEYS = {
    "usuarios": {},
    "depositos": {},
    "juego_pirata": {},
    "tareas": {},
    "Bono_apuesta": {}
}

def hacer_copia_seguridad_apuestas():
    archivo_original = apuestas.json
    directorio_respaldo = 'backups_apuestas'

    if not os.path.exists(directorio_respaldo):
        os.makedirs(directorio_respaldo)

    if os.path.exists(archivo_original):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        archivo_respaldo = os.path.join(directorio_respaldo, f'apuestas_backup_{timestamp}.json')

        shutil.copy(archivo_original, archivo_respaldo)

        respaldos = [f for f in os.listdir(directorio_respaldo) if f.startswith('apuestas_backup_')]
        respaldos.sort()
        while len(respaldos) > 2000:
            archivo_a_borrar = os.path.join(directorio_respaldo, respaldos.pop(0))
            os.remove(archivo_a_borrar)

        logger.info(f'Copia de seguridad creada: {archivo_respaldo}')
    else:
        logger.error(f'El archivo {archivo_original} no existe. No se puede hacer copia de seguridad.')
        
def hacer_copia_seguridad():
    # Definir el nombre del archivo original y el directorio de las copias de seguridad
    archivo_original = 'user_data.json'
    directorio_respaldo = 'backups'  # Carpeta donde se guardarán las copias

    # Crear el directorio de respaldo si no existe
    if not os.path.exists(directorio_respaldo):
        os.makedirs(directorio_respaldo)

    # Verificar si el archivo original existe
    if os.path.exists(archivo_original):
        # Crear una marca de tiempo para el nombre del archivo de la copia de seguridad
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        archivo_respaldo = os.path.join(directorio_respaldo, f'user_data_backup_{timestamp}.json')

        # Hacer una copia del archivo original
        shutil.copy(archivo_original, archivo_respaldo)

        # Obtener todas las copias de seguridad en el directorio de respaldos
        respaldos = [f for f in os.listdir(directorio_respaldo) if f.startswith('user_data_backup_')]
        
        # Ordenar las copias por fecha (ascendente) y mantener solo las 3 más recientes
        respaldos.sort()
        while len(respaldos) > 1000:
            archivo_a_borrar = os.path.join(directorio_respaldo, respaldos.pop(0))  # Eliminar la más antigua
            try:
                os.remove(archivo_a_borrar)
            except FileNotFoundError:
                print(f"⚠️ No se pudo borrar backup, no existe: {archivo_a_borrar}")
        
    else:
        print(f'El archivo {archivo_original} no existe. No se puede hacer copia de seguridad.')
        
def obtener_nombre(user_id):
    """
    Obtiene el nombre del usuario a partir del user_id en los datos proporcionados.
    """
    return user_data.get('usuarios', {}).get(str(user_id), {}).get('Nombre', 'Usuario')
            
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

        # Si no encontramos un user_id, no hay usuario identificado
        if not user_id:
            return await func(update, context, *args, **kwargs)  # Continuar normalmente si no hay user_id

        # Cargar los usuarios bloqueados
        usuarios_bloqueados = cargar_usuarios_bloqueados()

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






async def comando_basura_user(update: Update, context: CallbackContext):
    try:
        async with lock_data:
            # Cargar datos principales
            user_data = await load_data0()
            
            # Cargar basura existente o crear estructura vacía
            try:
                with open('basura_user.json', 'r', encoding='utf-8') as f:
                    basura = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                basura = {
                    "usuarios": {},
                    "depositos": {},
                    "juego_pirata": {},
                    "Bono_apuesta": {},
                    "retiros": {}
                }

            # Configuración
            dias_inactividad = 7
            cuba_tz = pytz.timezone('America/Havana')
            fecha_limite = datetime.now(cuba_tz) - timedelta(days=dias_inactividad)
            
            # Contadores y datos para el reporte
            stats = {
                'total_usuarios': len(user_data.get("usuarios", {})),
                'con_marca': 0,
                'sin_marca': 0,
                'movidos': 0,
                'balance_total': 0.0,
                'usuarios_movidos': []
            }

            # Procesar usuarios
            for user_id in list(user_data.get("usuarios", {}).keys()):
                usuario = user_data["usuarios"][user_id]
                mover_usuario = False
                tiempo_inactivo = "Sin marca"
                balance = usuario.get("Balance", 0)
                
                # Verificar marca de tiempo
                if "marca" in usuario:
                    try:
                        marca_dt = datetime.strptime(usuario["marca"], "%Y-%m-%d %I:%M:%S %p")
                        marca_dt = cuba_tz.localize(marca_dt)
                        stats['con_marca'] += 1
                        
                        # Calcular tiempo inactivo
                        tiempo_inactivo_delta = datetime.now(cuba_tz) - marca_dt
                        tiempo_inactivo = str(tiempo_inactivo_delta).split(".")[0]  # Remover microsegundos
                        
                        # Verificar si está inactivo
                        if marca_dt <= fecha_limite:
                            mover_usuario = True
                            
                    except ValueError:
                        # Marca en formato incorrecto
                        mover_usuario = True
                        tiempo_inactivo = "Marca inválida"
                else:
                    # Usuario sin marca
                    stats['sin_marca'] += 1
                    mover_usuario = True
                
                if mover_usuario:
                    # Preparar datos para el reporte
                    usuario_info = {
                        'id': user_id,
                        'nombre': usuario.get("Nombre", "Sin nombre"),
                        'balance': balance,
                        'tiempo_inactivo': tiempo_inactivo
                    }
                    stats['usuarios_movidos'].append(usuario_info)
                    stats['balance_total'] += float(balance)
                    
                    # Mover datos del usuario a basura
                    for seccion in ["usuarios", "depositos", "juego_pirata", "Bono_apuesta"]:
                        if seccion in user_data and user_id in user_data[seccion]:
                            if seccion not in basura:
                                basura[seccion] = {}
                            basura[seccion][user_id] = user_data[seccion].pop(user_id)
                            stats['movidos'] += 1
                    
                    # Mover retiros asociados (si existen)
                    if "retiros" in user_data:
                        if "retiros" not in basura:
                            basura["retiros"] = {}
                            
                        for retiro_id in list(user_data["retiros"].keys()):
                            retiro = user_data["retiros"][retiro_id]
                            if str(retiro["user_id"]) == str(user_id):
                                basura["retiros"][retiro_id] = user_data["retiros"].pop(retiro_id)

            # Guardar cambios
            with open('basura_user.json', 'w', encoding='utf-8') as f:
                json.dump(basura, f, ensure_ascii=False, indent=2)
            
            

            # Generar reporte
            reporte = await generar_reporte(stats)
            
            # Enviar reporte en partes si es muy largo
            max_length = 4000  # Límite de Telegram
            for i in range(0, len(reporte), max_length):
                parte = reporte[i:i+max_length]
                await update.message.reply_text(parte, parse_mode="HTML")

    except Exception as e:
        error_msg = f"Error en comando_basura_user: {str(e)}"
        logging.error(error_msg, exc_info=True)
        await update.message.reply_text("⚠️ Error crítico al limpiar usuarios. Ver logs.")
        await context.bot.send_message(
            chat_id=7031172659,  # ID del administrador
            text=f"🚨 Error en comando_basura_user:\n\n{error_msg}"
        )

async def generar_reporte(stats):
    """Genera el reporte en formato HTML dividido en partes"""
    from html import escape
    from datetime import datetime

    # Función mejorada para formatear valores
    def format_value(value, is_currency=False):
        try:
            if is_currency:
                return f"{float(value):.2f}"
            return str(value)
        except (ValueError, TypeError):
            return "N/A" if not is_currency else "0.00"

    # Función para escapar HTML y formatear
    def esc(text, is_currency=False):
        return escape(format_value(text, is_currency))

    # Cabecera del reporte
    reporte = f"""
🔍 <b>LIMPIEZA DE USUARIOS INACTIVOS</b>
┌─────────────────────────────
├ 📅 <i>Fecha:</i> {esc(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))}
├ ⏳ <i>Inactividad:</i> 7+ días
├
├ 👥 <b>Usuarios totales:</b> {esc(stats['total_usuarios'])}
├ 🕒 <b>Con marca temporal:</b> {esc(stats['con_marca'])}
├ ❓ <b>Sin marca temporal:</b> {esc(stats['sin_marca'])}
├
├ 🗑️ <b>Usuarios movidos:</b> {esc(len(stats['usuarios_movidos']))}
├ 💰 <b>Balance total movido:</b> {esc(stats['balance_total'], is_currency=True)} CUP
└─────────────────────────────

<b>USUARIOS MOVIDOS A BASURA:</b>\n
"""
    
    # Detalle de usuarios movidos
    detalles = []
    for usuario in stats['usuarios_movidos']:
        detalles.append(
            f"├ 🔹 <b>{esc(usuario['nombre'])}</b>\n"
            f"├ ⚙️ ID: {esc(usuario['id'])}\n"
            f"├ 💰 Balance: {esc(usuario['balance'], is_currency=True)} CUP\n"
            f"└ ⏱ Inactivo: {esc(usuario['tiempo_inactivo'])}\n"
        )
    
    # Unir todo el reporte
    reporte += "\n".join(detalles)
    reporte += "\n\n<blockquote>ℹ️ Usuarios movidos a basura_user.json</blockquote>"
    
    # Validación final de etiquetas HTML
    def validate_html_tags(text):
        from html.parser import HTMLParser
        class TagValidator(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
            def handle_endtag(self, tag):
                if not self.tags or self.tags[-1] != tag:
                    raise ValueError(f"Etiqueta {tag} sin cerrar apropiadamente")
                self.tags.pop()
        
        validator = TagValidator()
        validator.feed(text)
        if validator.tags:
            raise ValueError(f"Etiquetas sin cerrar: {validator.tags}")

    validate_html_tags(reporte)
    
    return reporte

def marca_tiempo(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext):
        try:
            user_id = str(update.effective_user.id)
            cuba_tz = pytz.timezone('America/Havana')
            timestamp = datetime.now(cuba_tz).strftime("%Y-%m-%d %I:%M:%S %p")
            
            # Verificar si el usuario existe en la base de datos
            usuario_data = obtener_registro("usuarios", user_id, "marca, Nombre")
            
            if usuario_data:
                # Usuario existe, actualizar marca de tiempo
                exito = actualizar_registro(
                    "usuarios",
                    user_id,
                    {"marca": timestamp}
                )
                
                if not exito:
                    logging.warning(f"No se pudo actualizar marca de tiempo para usuario {user_id}")
            else:
                # Usuario no existe, intentar restaurar desde "basura" si es necesario
                user_name = update.effective_user.first_name or "Usuario"
                
                # Primero verificar si existe en la tabla de usuarios
                usuario_existente = obtener_registro("usuarios", user_id, "id")
                
                if not usuario_existente:
                    # El usuario no existe en absoluto, crear uno nuevo básico
                    exito = actualizar_registro(
                        "usuarios",
                        user_id,
                        {
                            "Nombre": user_name,
                            "Balance": 0,
                            "Referidos": 0,
                            "Lider": 0,
                            "total_ganado_ref": 0,
                            "Medalla": "",
                            "marca": timestamp
                        }
                    )
                    
                    if not exito:
                        logging.warning(f"No se pudo crear usuario {user_id} en marca_tiempo")
            
            return await func(update, context)
            
        except Exception as e:
            logging.error(f"Error en @marca_tiempo: {str(e)}", exc_info=True)
            # Continuar con la función original incluso si hay error en el decorador
            return await func(update, context)
    return wrapper
    
    
async def restaurar_usuario_desde_basura(user_id: str, user_name: str, context: CallbackContext = None):
    """
    Restaura un usuario desde basura_user.json a la base de datos SQLite con la estructura correcta
    """
    try:
        # Cargar datos de basura
        try:
            with open('basura_user.json', 'r', encoding='utf-8') as f:
                basura = json.load(f)
                if not isinstance(basura, dict):
                    basura = {
                        "usuarios": {},
                        "depositos": {},
                        "juego_pirata": {},
                        "Bono_apuesta": {},
                        "tareas": {},
                        "promociones": {}
                    }
        except FileNotFoundError:
            return False
        except json.JSONDecodeError:
            logging.error("Archivo basura_user.json corrupto")
            basura = {
                "usuarios": {},
                "depositos": {},
                "juego_pirata": {},
                "Bono_apuesta": {},
                "tareas": {},
                "promociones": {}
            }

        # Verificar si el usuario existe en basura
        if user_id not in basura.get("usuarios", {}):
            return False

        restored = False

        # 1. Restaurar usuario a la tabla usuarios
        if user_id in basura.get("usuarios", {}):
            usuario_data = basura["usuarios"][user_id]
            
            campos_valores = {
                'id': user_id,
                'nombre': usuario_data.get('Nombre', user_name),
                'balance': usuario_data.get('Balance', 0),
                'referidos': usuario_data.get('Referidos', 0),
                'lider': usuario_data.get('Lider', 0),
                'total_ganado_ref': usuario_data.get('TotalGanadoRef', 0),
                'medalla': usuario_data.get('Medalla', ''),
                'marca': usuario_data.get('marca', ''),
                'UltimoRetiro': usuario_data.get('UltimoRetiro', '')
            }
            
            # Verificar si el usuario ya existe
            usuario_existente = obtener_registro("usuarios", user_id)
            
            if usuario_existente:
                exito = actualizar_registro("usuarios", user_id, campos_valores)
            else:
                exito = insertar_registro("usuarios", campos_valores)
            
            if exito:
                del basura["usuarios"][user_id]
                restored = True

        # 2. Restaurar depósitos
        if user_id in basura.get("depositos", {}):
            deposito_data = basura["depositos"][user_id]
            
            campos_valores = {
                'id': user_id,
                'nombre': deposito_data.get('Nombre', ''),
                'telefono': deposito_data.get('telefono', ''),
                'payment': deposito_data.get('Payment', 0),
                'amount': deposito_data.get('Amount', 0),
                'TotalDeposit': deposito_data.get('TotalDeposit', 0),
                'UltimoDeposito': deposito_data.get('UltimoDeposito', ''),
                'TotalRetiro': deposito_data.get('TotalRetiro', 0),
                'RetiroPendiente': deposito_data.get('RetiroPendiente', 0)
            }
            
            # Verificar si ya existe
            deposito_existente = obtener_registro("depositos", user_id)
            
            if deposito_existente:
                exito = actualizar_registro("depositos", user_id, campos_valores)
            else:
                exito = insertar_registro("depositos", campos_valores)
            
            if exito:
                del basura["depositos"][user_id]
                restored = True

        # 3. Restaurar juego_pirata (CORREGIDO - con la estructura correcta)
        if user_id in basura.get("juego_pirata", {}):
            juego_data = basura["juego_pirata"][user_id]
            
            campos_valores = {
                'id': user_id,
                'nombre': juego_data.get('nombre', user_name),
                'barriles': juego_data.get('barriles', 0),
                'piratas': juego_data.get('piratas', 0),
                'tiempo_ultimo_reclamo': juego_data.get('tiempo_ultimo_reclamo', 0),
                'tiempo_para_ganar': juego_data.get('tiempo_para_ganar', 3600),
                'ganancias_totales': juego_data.get('ganancias_totales', 0),
                'hp_barco': juego_data.get('hp_barco', 0),
                'ultimo_ataque': juego_data.get('ultimo_ataque', 0),
                'prestigio': juego_data.get('prestigio', 0),
                'escudo_hasta': juego_data.get('escudo_hasta', 0),
                'victorias': juego_data.get('victorias', 0),
                'derrotas': juego_data.get('derrotas', 0)
            }
            
            # Verificar si ya existe
            juego_existente = obtener_registro("juego_pirata", user_id)
            
            if juego_existente:
                exito = actualizar_registro("juego_pirata", user_id, campos_valores)
            else:
                exito = insertar_registro("juego_pirata", campos_valores)
            
            # Restaurar mejoras del juego pirata
            if 'mejoras' in juego_data:
                for tipo_mejora, mejora_data in juego_data['mejoras'].items():
                    nivel = mejora_data.get('nivel', 0)
                    
                    # Verificar si la mejora ya existe
                    mejora_existente = obtener_registro("mejoras", (user_id, tipo_mejora))
                    
                    if mejora_existente:
                        exito_mejora = actualizar_registro("mejoras", (user_id, tipo_mejora), {'nivel': nivel})
                    else:
                        exito_mejora = insertar_registro("mejoras", {
                            'id': user_id,
                            'tipo': tipo_mejora,
                            'nivel': nivel
                        })
            
            if exito:
                del basura["juego_pirata"][user_id]
                restored = True

        # 4. Restaurar Bono_apuesta
        if user_id in basura.get("Bono_apuesta", {}):
            bono_data = basura["Bono_apuesta"][user_id]
            
            campos_valores = {
                'id': user_id,
                'bono': bono_data.get('Bono', 0),
                'rollover_requerido': bono_data.get('Rollover_requerido', 0),
                'rollover_actual': bono_data.get('Rollover_actual', 0),
                'bono_retirable': bono_data.get('Bono_retirable', 0)
            }
            
            # Verificar si ya existe
            bono_existente = obtener_registro("bono_apuesta", user_id)
            
            if bono_existente:
                exito = actualizar_registro("bono_apuesta", user_id, campos_valores)
            else:
                exito = insertar_registro("bono_apuesta", campos_valores)
            
            if exito:
                del basura["Bono_apuesta"][user_id]
                restored = True

        # 5. Restaurar tareas
        if user_id in basura.get("tareas", {}):
            tareas_data = basura["tareas"][user_id]
            
            for tarea_id, tarea_data in tareas_data.items():
                campos_valores = {
                    'id': user_id,
                    'descripcion': tarea_data.get('descripcion', ''),
                    'estado': tarea_data.get('estado', '')
                }
                
                # Insertar tarea (no hay clave única definida, así que insertamos siempre)
                exito = insertar_registro("tareas", campos_valores)
                if exito:
                    restored = True
            
            # Eliminar del basura después de procesar todas las tareas
            del basura["tareas"][user_id]

        # 6. Restaurar promociones
        if user_id in basura.get("promociones", {}):
            promociones_data = basura["promociones"][user_id]
            
            for clave_promo, promo_data in promociones_data.items():
                campos_valores = {
                    'id': user_id,
                    'clave': clave_promo,
                    'fecha': promo_data.get('fecha', ''),
                    'red_social': promo_data.get('red_social', ''),
                    'recompensa': promo_data.get('recompensa', '')
                }
                
                # Verificar si ya existe
                promo_existente = obtener_registro("promociones", (user_id, clave_promo))
                
                if promo_existente:
                    exito = actualizar_registro("promociones", (user_id, clave_promo), campos_valores)
                else:
                    exito = insertar_registro("promociones", campos_valores)
                
                if exito:
                    restored = True
            
            # Eliminar del basura después de procesar todas las promociones
            del basura["promociones"][user_id]

        # Limpiar secciones vacías
        for seccion in ["usuarios", "depositos", "juego_pirata", "Bono_apuesta", "tareas", "promociones"]:
            if seccion in basura and not basura[seccion]:
                del basura[seccion]

        # Guardar archivo basura actualizado
        try:
            with open('basura_user.json', 'w', encoding='utf-8') as f:
                json.dump(basura, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error al guardar basura_user.json: {str(e)}")

        # Notificación
        if context and restored:
            try:
                usuario_actualizado = obtener_registro("usuarios", user_id, "balance")
                balance = usuario_actualizado[0] if usuario_actualizado else 0
                
                await context.bot.send_message(
                    chat_id=7031172659,
                    text=f"♻️ <b>Usuario restaurado a DB</b>\n\n"
                         f"👤 Nombre: {user_name}\n"
                         f"🆔 ID: <code>{user_id}</code>\n"
                         f"💰 Balance: {balance} CUP\n"
                         f"✅ Datos migrados correctamente",
                    parse_mode='HTML'
                )
            except Exception as e:
                logging.error(f"Error al notificar restauración: {str(e)}")

        return restored

    except Exception as e:
        logging.error(f"Error crítico al restaurar usuario {user_id}: {str(e)}", exc_info=True)
        if context:
            try:
                await context.bot.send_message(
                    chat_id=7031172659,
                    text=f"⚠️ <b>Error al restaurar usuario</b>\n\n"
                         f"ID: <code>{user_id}</code>\n"
                         f"Error: {str(e)[:200]}...",
                    parse_mode='HTML'
                )
            except:
                pass
        return False
def cargar_usuarios_bloqueados():
    try:
        with open("usuarios_bloqueados.json", "r") as file:
            data = json.load(file)
            if isinstance(data, list):  
                return data
            else:
                return []  
    except (FileNotFoundError, json.JSONDecodeError):
        return []  
        
def guardar_usuarios_bloqueados():
    with open("usuarios_bloqueados.json", "w") as f:
        json.dump(list(usuarios_bloqueados), f)  

usuarios_bloqueados = set(cargar_usuarios_bloqueados())  

# Cargar las API Keys desde el archivo JSON
