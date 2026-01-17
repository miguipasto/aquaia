#!/usr/bin/env python3
"""Script para cargar datos de AEMET desde CSV a PostgreSQL.

Lee el archivo CSV de datos meteorológicos de AEMET y los carga en la base de datos,
filtrando por las provincias objetivo (León, Lugo, Ourense, Zamora).
"""

import os
import sys
import argparse
import logging
import unicodedata
from typing import Set, List, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos
DB_USER = os.getenv('DB_USER', 'usuario')
DB_PASS = os.getenv('DB_PASS', 'contraseña')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'nombre_base')

# Provincias objetivo
PROVINCIAS_OBJETIVO = ['León', 'Lugo', 'Ourense', 'Zamora']

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def normalize_name(s: str) -> str:
    if s is None:
        return ''
    s = str(s).strip().lower()
    # remove accents
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s


NUMERIC_COLS = [
    'altitud', 'tmed', 'prec', 'tmin', 'tmax',
    'hrMax', 'hrMin', 'hrMedia', 'dir', 'velmedia', 'racha', 'sol', 'presMax', 'presMin'
]

TIME_COLS = ['horatmin', 'horatmax', 'horaHrMax', 'horaHrMin', 'horaracha', 'horaPresMax', 'horaPresMin']


def build_engine():
    """Construye un engine SQLAlchemy para conectar a PostgreSQL.
    
    Returns:
        Engine de SQLAlchemy
        
    Raises:
        Exception: Si no se puede conectar a la base de datos
    """
    try:
        url = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        engine = create_engine(url)
        
        # Verificar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logging.info(f"Conectado a la base de datos: {DB_NAME}@{DB_HOST}:{DB_PORT}")
        return engine
        
    except Exception as e:
        logging.error(f"Error al conectar a la base de datos: {e}")
        raise


def clean_numeric(value: str) -> Optional[float]:
    """Limpia y convierte un valor a numérico.
    
    Args:
        value: Valor string a convertir
        
    Returns:
        Valor float o None si no se puede convertir
    """
    if pd.isna(value):
        return None
    
    s = str(value).strip()
    if not s:
        return None
    
    # Valores no numéricos
    if s.lower() in ('varias', 'ip', 'acum', 'na', 'nd', 'sin dato', 'sin_dato'):
        return None
    
    # Normalizar formato numérico
    s = s.replace(' ', '').replace(',', '.')
    
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def insert_chunk(engine, records: List[dict]) -> int:
    """Inserta o actualiza un lote de registros en la base de datos.
    
    Args:
        engine: Engine de SQLAlchemy
        records: Lista de diccionarios con los datos a insertar
        
    Returns:
        Número de registros procesados
    """
    if not records:
        return 0

    insert_sql = text(
        """
        INSERT INTO aemet_diario
        (fecha, indicativo, nombre, provincia, altitud, tmed, prec, tmin, horatmin, tmax, horatmax,
         hr_max, hora_hr_max, hr_min, hora_hr_min, hr_media, dir, velmedia, racha, hora_racha,
         pres_max, hora_pres_max, pres_min, hora_pres_min, sol)
        VALUES
        (:fecha, :indicativo, :nombre, :provincia, :altitud, :tmed, :prec, :tmin, :horatmin, :tmax, :horatmax,
         :hr_max, :hora_hr_max, :hr_min, :hora_hr_min, :hr_media, :dir, :velmedia, :racha, :hora_racha,
         :pres_max, :hora_pres_max, :pres_min, :hora_pres_min, :sol)
        ON CONFLICT (indicativo, fecha)
        DO UPDATE SET
          nombre = EXCLUDED.nombre,
          provincia = EXCLUDED.provincia,
          altitud = EXCLUDED.altitud,
          tmed = EXCLUDED.tmed,
          prec = EXCLUDED.prec,
          tmin = EXCLUDED.tmin,
          horatmin = EXCLUDED.horatmin,
          tmax = EXCLUDED.tmax,
          horatmax = EXCLUDED.horatmax,
          hr_max = EXCLUDED.hr_max,
          hora_hr_max = EXCLUDED.hora_hr_max,
          hr_min = EXCLUDED.hr_min,
          hora_hr_min = EXCLUDED.hora_hr_min,
          hr_media = EXCLUDED.hr_media,
          dir = EXCLUDED.dir,
          velmedia = EXCLUDED.velmedia,
          racha = EXCLUDED.racha,
          hora_racha = EXCLUDED.hora_racha,
          pres_max = EXCLUDED.pres_max,
          hora_pres_max = EXCLUDED.hora_pres_max,
          pres_min = EXCLUDED.pres_min,
          hora_pres_min = EXCLUDED.hora_pres_min,
          sol = EXCLUDED.sol
        """
    )

    try:
        with engine.begin() as conn:
            conn.execute(insert_sql, records)
        return len(records)
    except Exception as e:
        logging.error(f"Error al insertar chunk: {e}")
        raise


def process_csv(csv_path: str, engine, chunksize: int = 20000):
    """Procesa el CSV y carga los datos en la base de datos.
    
    Args:
        csv_path: Ruta al archivo CSV
        engine: Engine de SQLAlchemy
        chunksize: Tamaño de los lotes para procesar
    """
    target_norm = {normalize_name(p) for p in PROVINCIAS_OBJETIVO}
    logging.info(f"Procesando CSV: {csv_path}")
    logging.info(f"Provincias objetivo: {', '.join(PROVINCIAS_OBJETIVO)}")
    logging.info(f"Tamaño de chunk: {chunksize}")
    
    total = 0
    chunk_no = 0

    try:
        for chunk in pd.read_csv(csv_path, dtype=str, chunksize=chunksize, header=0):
            chunk_no += 1
            chunk.columns = [c.strip() for c in chunk.columns]

            # Filtrar por provincias objetivo
            chunk['prov_norm'] = chunk['provincia'].apply(normalize_name)
            filtered = chunk[chunk['prov_norm'].isin(target_norm)].copy()
            
            if filtered.empty:
                logging.debug(f'Chunk {chunk_no}: 0 filas para provincias objetivo')
                continue

            records = []
            for _, row in filtered.iterrows():
                # Verificar campos obligatorios
                fecha = row.get('fecha')
                indicativo = row.get('indicativo')
                nombre = row.get('nombre')
                provincia = row.get('provincia')
                alt = clean_numeric(row.get('altitud'))
                
                if not all([fecha, indicativo, nombre, provincia, alt is not None]):
                    continue

                # Construir registro
                rec = {
                    'fecha': pd.to_datetime(fecha, errors='coerce').date().isoformat() 
                            if pd.notna(fecha) else None,
                    'indicativo': str(indicativo).strip(),
                    'nombre': str(nombre).strip(),
                    'provincia': str(provincia).strip(),
                    'altitud': int(alt) if alt is not None else None,
                    'tmed': clean_numeric(row.get('tmed')),
                    'prec': clean_numeric(row.get('prec')),
                    'tmin': clean_numeric(row.get('tmin')),
                    'horatmin': None if pd.isna(row.get('horatmin')) 
                               else str(row.get('horatmin')).strip(),
                    'tmax': clean_numeric(row.get('tmax')),
                    'horatmax': None if pd.isna(row.get('horatmax')) 
                               else str(row.get('horatmax')).strip(),
                    'hr_max': clean_numeric(row.get('hrMax')),
                    'hora_hr_max': None if pd.isna(row.get('horaHrMax')) 
                                  else str(row.get('horaHrMax')).strip(),
                    'hr_min': clean_numeric(row.get('hrMin')),
                    'hora_hr_min': None if pd.isna(row.get('horaHrMin')) 
                                  else str(row.get('horaHrMin')).strip(),
                    'hr_media': clean_numeric(row.get('hrMedia')),
                    'dir': clean_numeric(row.get('dir')),
                    'velmedia': clean_numeric(row.get('velmedia')),
                    'racha': clean_numeric(row.get('racha')),
                    'hora_racha': None if pd.isna(row.get('horaracha')) 
                                 else str(row.get('horaracha')).strip(),
                    'pres_max': clean_numeric(row.get('presMax')),
                    'hora_pres_max': None if pd.isna(row.get('horaPresMax')) 
                                    else str(row.get('horaPresMax')).strip(),
                    'pres_min': clean_numeric(row.get('presMin')),
                    'hora_pres_min': None if pd.isna(row.get('horaPresMin')) 
                                    else str(row.get('horaPresMin')).strip(),
                    'sol': clean_numeric(row.get('sol'))
                }

                if rec['fecha'] and rec['indicativo']:
                    records.append(rec)

            inserted = insert_chunk(engine, records)
            total += inserted
            logging.info(f'Chunk {chunk_no}: {inserted} registros insertados/actualizados')

        logging.info(f'Carga finalizada. Total: {total} registros insertados/actualizados')
        
    except Exception as e:
        logging.error(f"Error al procesar CSV: {e}")
        raise


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Cargar datos de AEMET desde CSV a PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'csv_path', 
        help='Ruta absoluta al fichero datos_aemet.csv'
    )
    parser.add_argument(
        '--chunksize', 
        type=int, 
        default=20000,
        help='Tamaño de los lotes para procesar (por defecto: 20000)'
    )
    args = parser.parse_args()

    csv_path = args.csv_path
    
    # Validaciones
    if not os.path.isabs(csv_path):
        logging.error('ERROR: Debe proporcionar una ruta absoluta al CSV')
        sys.exit(1)
        
    if not os.path.exists(csv_path):
        logging.error(f'ERROR: No existe el archivo: {csv_path}')
        sys.exit(1)

    try:
        logging.info("="*60)
        logging.info("CARGA DE DATOS AEMET A BASE DE DATOS")
        logging.info("="*60)
        
        engine = build_engine()
        process_csv(csv_path, engine, chunksize=args.chunksize)
        
        logging.info("="*60)
        logging.info("Proceso completado exitosamente")
        logging.info("="*60)
        
    except Exception as e:
        logging.error(f"Error durante el proceso: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
