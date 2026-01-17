#!/usr/bin/env python3
"""Script para descargar datos climatológicos diarios de AEMET.

Descarga datos históricos de todas las estaciones meteorológicas de AEMET
en intervalos configurables y los guarda en CSV de forma incremental.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple

import requests
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración desde variables de entorno
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    logging.error("ERROR: No se encontró API_KEY en el archivo .env")
    sys.exit(1)

# Configuración de la API
BASE_URL = "https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos"

# Configuración de descarga
FECHA_INICIO = datetime(2015, 1, 1)
FECHA_FIN = datetime(2025, 9, 4)
INTERVALO_DIAS = 15
OUTPUT_FILE = "datos_aemet.csv"

# Configuración de reintentos
MAX_REINTENTOS = 3
TIEMPO_ESPERA_REINTENTO = 5
TIEMPO_ESPERA_429 = 60  # Tiempo de espera cuando hay demasiadas peticiones

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def cargar_datos_existentes() -> Tuple[pd.DataFrame, Set[str], List[str]]:
    """Carga el CSV existente si existe.
    
    Returns:
        Tuple con:
            - DataFrame con los datos existentes
            - Set con identificadores únicos (fecha_indicativo)
            - Lista con fechas existentes ordenadas
    """
    if not os.path.exists(OUTPUT_FILE):
        logging.info(f"No se encontró archivo existente. Se creará {OUTPUT_FILE}")
        return pd.DataFrame(), set(), []
    
    try:
        df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
        logging.info(f"Cargados {len(df)} registros existentes desde {OUTPUT_FILE}")
        
        if 'fecha' not in df.columns or 'indicativo' not in df.columns:
            logging.warning("El CSV no tiene las columnas esperadas")
            return df, set(), []
        
        # Crear set de identificadores únicos
        registros_existentes = set(
            df['fecha'].astype(str) + '_' + df['indicativo'].astype(str)
        )
        
        # Obtener fechas existentes ordenadas
        fechas_existentes = sorted(df['fecha'].unique())
        
        if fechas_existentes:
            logging.info(f"Identificados {len(registros_existentes)} registros únicos")
            logging.info(f"Rango de fechas: {fechas_existentes[0]} a {fechas_existentes[-1]}")
        
        return df, registros_existentes, fechas_existentes
        
    except Exception as e:
        logging.error(f"Error al cargar CSV existente: {e}")
        logging.info("Se creará un archivo nuevo")
        return pd.DataFrame(), set(), []

def periodo_ya_descargado(
    fecha_inicio: datetime, 
    fecha_fin: datetime, 
    fechas_existentes: List[str]
) -> bool:
    """Verifica si un periodo ya está completamente descargado.
    
    Args:
        fecha_inicio: Fecha de inicio del periodo
        fecha_fin: Fecha de fin del periodo
        fechas_existentes: Lista de fechas ya descargadas
    
    Returns:
        True si todas las fechas del periodo están descargadas
    """
    if not fechas_existentes:
        return False
    
    fechas_str = set(fechas_existentes)
    
    # Verificar todas las fechas del periodo
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        if fecha_actual.strftime("%Y-%m-%d") not in fechas_str:
            return False
        fecha_actual += timedelta(days=1)
    
    return True

def guardar_datos_incrementales(
    nuevos_datos: List[Dict], 
    registros_existentes: Set[str]
) -> int:
    """Guarda nuevos datos al CSV, evitando duplicados.
    
    Args:
        nuevos_datos: Lista de diccionarios con los datos a guardar
        registros_existentes: Set de identificadores ya existentes (fecha_indicativo)
    
    Returns:
        Número de registros nuevos guardados
    """
    if not nuevos_datos:
        return 0
    
    # Filtrar registros duplicados
    datos_filtrados = []
    for registro in nuevos_datos:
        if 'fecha' not in registro or 'indicativo' not in registro:
            continue
            
        identificador = f"{registro['fecha']}_{registro['indicativo']}"
        if identificador not in registros_existentes:
            datos_filtrados.append(registro)
            registros_existentes.add(identificador)
    
    if not datos_filtrados:
        return 0
    
    # Guardar al CSV
    df_nuevos = pd.DataFrame(datos_filtrados)
    mode = 'a' if os.path.exists(OUTPUT_FILE) else 'w'
    header = not os.path.exists(OUTPUT_FILE)
    
    df_nuevos.to_csv(
        OUTPUT_FILE, 
        mode=mode, 
        header=header, 
        index=False, 
        encoding='utf-8-sig'
    )
    
    return len(datos_filtrados)

def obtener_datos_periodo(
    fecha_inicio: datetime, 
    fecha_fin: datetime, 
    intento: int = 1
) -> List[Dict]:
    """Obtiene datos de AEMET para un periodo específico.
    
    Args:
        fecha_inicio: Fecha de inicio del periodo
        fecha_fin: Fecha de fin del periodo
        intento: Número de intento actual
    
    Returns:
        Lista de diccionarios con los datos obtenidos
    """
    fecha_ini_str = fecha_inicio.strftime("%Y-%m-%dT00:00:00UTC")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%dT00:00:00UTC")
    url = f"{BASE_URL}/fechaini/{fecha_ini_str}/fechafin/{fecha_fin_str}/todasestaciones"
    
    headers = {
        'Accept': 'application/json',
        'api_key': API_KEY
    }
    
    try:
        # Obtener enlace a los datos
        prefijo = f"[Intento {intento}/{MAX_REINTENTOS}] " if intento > 1 else ""
        logging.info(f"{prefijo}Solicitando datos del {fecha_inicio.date()} al {fecha_fin.date()}")
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            resultado = response.json()
            
            if resultado.get('estado') == 200 and 'datos' in resultado:
                # Descargar datos desde el enlace
                time.sleep(1)  # Evitar saturar la API
                datos_response = requests.get(resultado['datos'], timeout=30)
                
                if datos_response.status_code == 200:
                    datos = datos_response.json()
                    logging.info(f"  Obtenidos {len(datos)} registros de la API")
                    return datos
                else:
                    logging.warning(f"  Error al descargar datos: {datos_response.status_code}")
                    
            elif resultado.get('estado') == 404:
                logging.warning("  No hay datos disponibles para este periodo")
                return []
            else:
                logging.warning(f"  Error en la respuesta: {resultado}")
                
        elif response.status_code == 429:
            logging.warning("  Demasiadas peticiones (429). Esperando...")
            time.sleep(TIEMPO_ESPERA_429)
            return obtener_datos_periodo(fecha_inicio, fecha_fin, intento)
        else:
            logging.warning(f"  Error en la petición: {response.status_code}")
        
        # Reintentar si no se alcanzó el máximo
        if intento < MAX_REINTENTOS:
            logging.info(f"  Reintentando en {TIEMPO_ESPERA_REINTENTO} segundos...")
            time.sleep(TIEMPO_ESPERA_REINTENTO)
            return obtener_datos_periodo(fecha_inicio, fecha_fin, intento + 1)
        
        return []
        
    except requests.exceptions.RequestException as e:
        logging.error(f"  Error de conexión: {e}")
        if intento < MAX_REINTENTOS:
            logging.info(f"  Reintentando en {TIEMPO_ESPERA_REINTENTO} segundos...")
            time.sleep(TIEMPO_ESPERA_REINTENTO)
            return obtener_datos_periodo(fecha_inicio, fecha_fin, intento + 1)
        return []
        
    except json.JSONDecodeError as e:
        logging.error(f"  Error al parsear JSON: {e}")
        if intento < MAX_REINTENTOS:
            logging.info(f"  Reintentando en {TIEMPO_ESPERA_REINTENTO} segundos...")
            time.sleep(TIEMPO_ESPERA_REINTENTO)
            return obtener_datos_periodo(fecha_inicio, fecha_fin, intento + 1)
        return []

def main():
    """Función principal que descarga todos los datos y los guarda en CSV incrementalmente."""
    logging.info("="*60)
    logging.info("DESCARGA DE DATOS AEMET")
    logging.info("="*60)
    logging.info(f"Periodo: {FECHA_INICIO.date()} a {FECHA_FIN.date()}")
    logging.info(f"Intervalo: {INTERVALO_DIAS} días")
    logging.info(f"Archivo de salida: {OUTPUT_FILE}")
    logging.info("="*60)
    
    # Cargar datos existentes
    df_existente, registros_existentes, fechas_existentes = cargar_datos_existentes()
    logging.info("="*60)
    
    total_nuevos_guardados = 0
    periodos_omitidos = 0
    fecha_actual = FECHA_INICIO
    
    try:
        while fecha_actual < FECHA_FIN:
            fecha_siguiente = min(fecha_actual + timedelta(days=INTERVALO_DIAS), FECHA_FIN)
            
            # Verificar si el periodo ya está descargado
            if periodo_ya_descargado(fecha_actual, fecha_siguiente, fechas_existentes):
                logging.info(
                    f"Periodo {fecha_actual.date()} al {fecha_siguiente.date()} "
                    f"ya descargado (omitido)"
                )
                periodos_omitidos += 1
            else:
                # Obtener y guardar datos
                datos_periodo = obtener_datos_periodo(fecha_actual, fecha_siguiente)
                
                if datos_periodo:
                    nuevos_guardados = guardar_datos_incrementales(
                        datos_periodo, 
                        registros_existentes
                    )
                    
                    if nuevos_guardados > 0:
                        logging.info(f"  Guardados {nuevos_guardados} registros nuevos")
                        total_nuevos_guardados += nuevos_guardados
                        
                        # Actualizar fechas existentes
                        nuevas_fechas = {
                            registro['fecha'] 
                            for registro in datos_periodo 
                            if 'fecha' in registro
                        }
                        fechas_existentes = list(set(fechas_existentes) | nuevas_fechas)
                    else:
                        logging.info("  Todos los registros ya existían")
                
                time.sleep(2)  # Evitar saturar la API
            
            fecha_actual = fecha_siguiente + timedelta(days=1)
    
    except KeyboardInterrupt:
        logging.warning("\nProceso interrumpido por el usuario")
    
    # Mostrar resumen final
    logging.info("="*60)
    logging.info(f"Periodos omitidos: {periodos_omitidos}")
    logging.info(f"Registros nuevos guardados: {total_nuevos_guardados}")
    
    if os.path.exists(OUTPUT_FILE):
        df_final = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
        logging.info(f"Total de registros en {OUTPUT_FILE}: {len(df_final)}")
        
        if 'fecha' in df_final.columns:
            logging.info(
                f"Rango de fechas: {df_final['fecha'].min()} a {df_final['fecha'].max()}"
            )
        if 'provincia' in df_final.columns:
            logging.info(f"Provincias únicas: {df_final['provincia'].nunique()}")
    else:
        logging.warning("No se obtuvieron datos")
    
    logging.info("="*60)

if __name__ == "__main__":
    main()

