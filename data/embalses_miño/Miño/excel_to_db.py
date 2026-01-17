#!/usr/bin/env python3
"""Script para cargar datos de embalses desde Excel a PostgreSQL.

Lee un archivo Excel con datos de embalses del Miño (provincias, municipios,
estaciones SAIH y mediciones) y los carga en la base de datos PostgreSQL.
"""

import os
import sys
import logging
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración (variables de entorno con valores por defecto)
EXCEL_FILE = './Data/Miño/Datos.xlsx'
DB_USER = os.getenv('DB_USER', 'usuario')
DB_PASS = os.getenv('DB_PASS', 'contraseña')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'nombre_base')
ID_CCAA = int(os.getenv('ID_CCAA', '5'))  # Galicia por defecto
ID_DEMARCACION = os.getenv('ID_DEMARCACION', 'ES012')  # Miño-Sil por defecto

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def read_excel(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Lee un archivo Excel y devuelve un DataFrame.

    Args:
        file_path: Ruta al archivo Excel
        sheet_name: Nombre de la hoja o None para leer la primera
        
    Returns:
        DataFrame con los datos del Excel
    """
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        logging.error(f"Error al leer Excel '{file_path}', hoja '{sheet_name}': {e}")
        raise


def build_engine():
    """Construye un engine SQLAlchemy a partir de las variables de entorno.
    
    Returns:
        Engine de SQLAlchemy
        
    Raises:
        Exception: Si no se puede conectar a la base de datos
    """
    try:
        url = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        logging.info("Conectando a la base de datos...")
        engine = create_engine(url)
        
        # Verificar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logging.info(f"Conexión establecida: {DB_NAME}@{DB_HOST}:{DB_PORT}")
        return engine
        
    except Exception as e:
        logging.error(f"Error al conectar a la base de datos: {e}")
        raise

def fetch_provincias(engine) -> List[Dict]:
    """Devuelve el conjunto de provincias en la tabla provincia.
    
    Args:
        engine: Engine de SQLAlchemy
        
    Returns:
        Lista de diccionarios con datos de provincias
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM provincia"))
            provincias = [
                {"id": row.id, "nombre": row.nombre, "id_ccaa": row.id_ccaa}
                for row in result
            ]
        return provincias
    except Exception as e:
        logging.error(f"Error al obtener provincias: {e}")
        raise

def fetch_municipios(engine) -> List[Dict]:
    """Devuelve el conjunto de municipios en la tabla municipio.
    
    Args:
        engine: Engine de SQLAlchemy
        
    Returns:
        Lista de diccionarios con datos de municipios
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM municipio"))
            municipios = [
                {"id": row.id, "nombre": row.nombre, "id_provincia": row.id_provincia}
                for row in result
            ]
        return municipios
    except Exception as e:
        logging.error(f"Error al obtener municipios: {e}")
        raise

def fetch_estacion_saih(engine) -> List[Dict]:
    """Devuelve el conjunto de estaciones SAIH en la tabla estacion_saih.
    
    Args:
        engine: Engine de SQLAlchemy
        
    Returns:
        Lista de diccionarios con datos de estaciones SAIH
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM estacion_saih"))
            estaciones = [
                {
                    "codigo_saih": row.codigo_saih,
                    "ubicacion": row.ubicacion,
                    "id_municipio": row.id_municipio,
                    "coord_x": row.coord_x,
                    "coord_y": row.coord_y,
                    "id_demarcacion": row.id_demarcacion
                }
                for row in result
            ]
        return estaciones
    except Exception as e:
        logging.error(f"Error al obtener estaciones SAIH: {e}")
        raise

def fetch_caudal_tipos(engine) -> Dict[str, int]:
    """Devuelve el conjunto de tipos de caudal de la tabla caudal_tipo.
    
    Args:
        engine: Engine de SQLAlchemy
        
    Returns:
        Diccionario {codigo: id}
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM caudal_tipo"))
            tipos = {row.codigo: row.id for row in result}
        return tipos
    except Exception as e:
        logging.error(f"Error al obtener tipos de caudal: {e}")
        raise


def insert_provincia(engine, provincias: List[str], id_ccaa: int):
    """Bulk insert de nuevas provincias en la tabla provincia.
    
    Args:
        engine: Engine de SQLAlchemy
        provincias: Lista de nombres de provincias
        id_ccaa: ID de la comunidad autónoma
    """
    if not provincias:
        return
    
    try:
        with engine.connect() as connection:
            for nombre in provincias:
                connection.execute(
                    text("INSERT INTO provincia (nombre, id_ccaa) VALUES (:nombre, :id_ccaa)"),
                    {"nombre": nombre, "id_ccaa": id_ccaa}
                )
            connection.commit()
        logging.info(f"Insertadas {len(provincias)} provincia(s) correctamente")
    except Exception as e:
        logging.error(f"Error al insertar provincias: {e}")
        raise

def insertar_municipios(engine, municipios: List[Tuple[str, int]]):
    """Bulk insert de nuevos municipios en la tabla municipio.
    
    Args:
        engine: Engine de SQLAlchemy
        municipios: Lista de tuplas (nombre_municipio, id_provincia)
    """
    if not municipios:
        return
    
    try:
        with engine.connect() as connection:
            for nombre, id_provincia in municipios:
                connection.execute(
                    text("INSERT INTO municipio (nombre, id_provincia) VALUES (:nombre, :id_provincia)"),
                    {"nombre": nombre, "id_provincia": id_provincia}
                )
            connection.commit()
        logging.info(f"Insertados {len(municipios)} municipio(s) correctamente")
    except Exception as e:
        logging.error(f"Error al insertar municipios: {e}")
        raise

def insertar_estaciones_saih(engine, estaciones: List[Dict]):
    """Bulk insert de nuevas estaciones SAIH en la tabla estacion_saih.
    
    Args:
        engine: Engine de SQLAlchemy
        estaciones: Lista de diccionarios con datos de estaciones
    """
    if not estaciones:
        return
    
    try:
        with engine.connect() as connection:
            for estacion in estaciones:
                connection.execute(
                    text("""
                        INSERT INTO estacion_saih 
                        (codigo_saih, ubicacion, id_municipio, coord_x, coord_y, id_demarcacion)
                        VALUES (:codigo_saih, :ubicacion, :id_municipio, :coord_x, :coord_y, :id_demarcacion)
                    """),
                    estacion
                )
            connection.commit()
        logging.info(f"Insertadas {len(estaciones)} estación(es) SAIH correctamente")
    except Exception as e:
        logging.error(f"Error al insertar estaciones SAIH: {e}")
        raise

def insertar_mediciones_bulk(engine, tabla: str, registros: List[Dict]) -> int:
    """Inserta o actualiza registros de mediciones en modo bulk usando UPSERT.
    
    Args:
        engine: SQLAlchemy engine
        tabla: Nombre de la tabla ('saih_nivel_embalse', 'saih_precipitacion', 'saih_temperatura')
        registros: Lista de diccionarios con {codigo_saih, fecha, valor}
        
    Returns:
        Número de registros procesados
    """
    if not registros:
        return 0
    
    # Determinar el nombre de la columna de valor según la tabla
    columna_valor = {
        'saih_nivel_embalse': 'nivel',
        'saih_precipitacion': 'precipitacion',
        'saih_temperatura': 'temperatura'
    }.get(tabla)
    
    if not columna_valor:
        logging.error(f"Tabla desconocida: {tabla}")
        return 0
    
    try:
        with engine.connect() as connection:
            query = text(f"""
                INSERT INTO {tabla} (codigo_saih, fecha, {columna_valor})
                VALUES (:codigo_saih, :fecha, :valor)
                ON CONFLICT (codigo_saih, fecha) 
                DO UPDATE SET {columna_valor} = EXCLUDED.{columna_valor}
            """)
            connection.execute(query, registros)
            connection.commit()
        return len(registros)
    except Exception as e:
        logging.error(f"Error al insertar mediciones en {tabla}: {e}")
        raise

def insertar_caudales_bulk(engine, registros: List[Dict]) -> int:
    """Inserta o actualiza registros de caudales en modo bulk usando UPSERT.
    
    Args:
        engine: SQLAlchemy engine
        registros: Lista de diccionarios con {codigo_saih, id_tipo_caudal, fecha, valor}
        
    Returns:
        Número de registros procesados
    """
    if not registros:
        return 0
    
    try:
        with engine.connect() as connection:
            query = text("""
                INSERT INTO saih_caudal (codigo_saih, id_tipo_caudal, fecha, caudal)
                VALUES (:codigo_saih, :id_tipo_caudal, :fecha, :valor)
                ON CONFLICT (codigo_saih, id_tipo_caudal, fecha) 
                DO UPDATE SET caudal = EXCLUDED.caudal
            """)
            connection.execute(query, registros)
            connection.commit()
        return len(registros)
    except Exception as e:
        logging.error(f"Error al insertar caudales: {e}")
        raise

def procesar_hoja_mediciones(engine, hoja_nombre: str, tabla_destino: str):
    """Lee una hoja del Excel con formato: Fecha | E001 | E002 | ...
    y procesa las mediciones para insertarlas en la tabla correspondiente.
    
    Args:
        engine: SQLAlchemy engine
        hoja_nombre: Nombre de la hoja del Excel a leer
        tabla_destino: Nombre de la tabla destino
    """
    logging.info("="*80)
    logging.info(f"PROCESANDO HOJA: {hoja_nombre} -> Tabla: {tabla_destino}")
    logging.info("="*80)
    
    try:
        # Obtener estaciones válidas de la base de datos
        estaciones_validas = fetch_estacion_saih(engine)
        codigos_validos = {e['codigo_saih'] for e in estaciones_validas}
        logging.info(f"Estaciones SAIH válidas en base de datos: {len(codigos_validos)}")
        
        # Leer la hoja del Excel
        df = read_excel(EXCEL_FILE, hoja_nombre)
        logging.info(f"Total de filas leídas: {len(df)}")
        
        # Verificar columna 'Fecha'
        if 'Fecha' not in df.columns:
            logging.warning(f"La hoja '{hoja_nombre}' no tiene columna 'Fecha'. Omitiendo...")
            return
        
        # Obtener columnas de estaciones
        columnas_estaciones = [
            col for col in df.columns 
            if col != 'Fecha' and not col.startswith('Unnamed')
        ]
        
        # Filtrar solo las estaciones que existen en la base de datos
        columnas_validas = [col for col in columnas_estaciones if col in codigos_validos]
        columnas_invalidas = [col for col in columnas_estaciones if col not in codigos_validos]
        
        logging.info(f"Estaciones encontradas en Excel: {len(columnas_estaciones)}")
        logging.info(f"Estaciones válidas (existen en BD): {len(columnas_validas)}")
        
        if columnas_invalidas:
            logging.warning(f"Estaciones no registradas (se omitirán): {columnas_invalidas}")
        
        columnas_estaciones = columnas_validas
        
        # Preparar registros para inserción
        registros = []
        errores = []
        
        for idx, row in df.iterrows():
            try:
                fecha_raw = row['Fecha']
                
                if pd.isna(fecha_raw):
                    continue
                
                # Parsear fecha (Excel serial date o string)
                if isinstance(fecha_raw, (int, float)):
                    fecha = pd.Timestamp('1899-12-30') + pd.Timedelta(days=fecha_raw)
                else:
                    fecha = pd.to_datetime(fecha_raw, format='%d/%m/%Y', errors='coerce')
                    if pd.isna(fecha):
                        fecha = pd.to_datetime(fecha_raw, errors='coerce')
                
                if pd.isna(fecha):
                    errores.append(f"Fila {idx}: Fecha inválida '{fecha_raw}'")
                    continue
                
                fecha_str = fecha.strftime('%Y-%m-%d')
                
                # Procesar cada estación
                for codigo_saih in columnas_estaciones:
                    valor = row[codigo_saih]
                    
                    if pd.isna(valor):
                        continue
                    
                    try:
                        registros.append({
                            'codigo_saih': codigo_saih,
                            'fecha': fecha_str,
                            'valor': float(valor)
                        })
                    except (ValueError, TypeError):
                        errores.append(
                            f"Fila {idx}, Estación {codigo_saih}: Valor inválido '{valor}'"
                        )
                        
            except Exception as e:
                errores.append(f"Fila {idx}: Error procesando fila - {str(e)}")
        
        # Mostrar errores
        if errores:
            logging.warning(f"Se encontraron {len(errores)} errores")
            for error in errores[:10]:
                logging.warning(f"  - {error}")
            if len(errores) > 10:
                logging.warning(f"  ... y {len(errores) - 10} errores más")
        
        # Insertar registros
        if registros:
            logging.info(f"Insertando {len(registros)} registro(s) en '{tabla_destino}'")
            total_insertados = insertar_mediciones_bulk(engine, tabla_destino, registros)
            logging.info(f"{total_insertados} registro(s) insertados/actualizados")
        else:
            logging.warning("No se encontraron registros válidos para insertar")
            
    except Exception as e:
        logging.error(f"ERROR procesando hoja '{hoja_nombre}': {str(e)}", exc_info=True)

def procesar_hoja_caudales(engine, hoja_nombre: str):
    """Lee la hoja de caudales del Excel con formato: Fecha | E001MACQSALR | E002MACQSALR | ...
    Las columnas son combinaciones de código SAIH + tipo de caudal.
    
    Args:
        engine: SQLAlchemy engine
        hoja_nombre: Nombre de la hoja del Excel a leer
    """
    logging.info("="*80)
    logging.info(f"PROCESANDO HOJA: {hoja_nombre} -> Tabla: saih_caudal")
    logging.info("="*80)
    
    try:
        # Obtener estaciones válidas y tipos de caudal
        estaciones_validas = fetch_estacion_saih(engine)
        codigos_validos = {e['codigo_saih'] for e in estaciones_validas}
        tipos_caudal = fetch_caudal_tipos(engine)
        
        logging.info(f"Estaciones SAIH válidas: {len(codigos_validos)}")
        logging.info(f"Tipos de caudal disponibles: {list(tipos_caudal.keys())}")
        
        # Leer la hoja del Excel
        df = read_excel(EXCEL_FILE, hoja_nombre)
        logging.info(f"Total de filas leídas: {len(df)}")
        
        # Verificar columna 'Fecha'
        if 'Fecha' not in df.columns:
            logging.warning(f"La hoja '{hoja_nombre}' no tiene columna 'Fecha'. Omitiendo...")
            return
        
        # Obtener columnas de medición
        columnas_medicion = [
            col for col in df.columns 
            if col != 'Fecha' and not col.startswith('Unnamed')
        ]
        logging.info(f"Columnas de medición encontradas: {len(columnas_medicion)}")
        
        # Parsear las columnas: extraer código SAIH y tipo de caudal
        columnas_parseadas = []
        columnas_invalidas = []
        
        for col in columnas_medicion:
            tipo_encontrado = None
            codigo_saih = None
            
            for tipo_codigo in tipos_caudal.keys():
                if col.endswith(tipo_codigo):
                    codigo_saih = col[:-len(tipo_codigo)]
                    tipo_encontrado = tipo_codigo
                    break
            
            if tipo_encontrado and codigo_saih:
                if codigo_saih in codigos_validos:
                    columnas_parseadas.append({
                        'columna': col,
                        'codigo_saih': codigo_saih,
                        'tipo_codigo': tipo_encontrado,
                        'id_tipo': tipos_caudal[tipo_encontrado]
                    })
                else:
                    columnas_invalidas.append(
                        f"{col} (estación {codigo_saih} no registrada)"
                    )
            else:
                columnas_invalidas.append(f"{col} (formato inválido)")
        
        logging.info(f"Columnas válidas: {len(columnas_parseadas)}")
        if columnas_invalidas:
            logging.warning(f"Columnas no válidas: {columnas_invalidas[:5]}")
            if len(columnas_invalidas) > 5:
                logging.warning(f"    ... y {len(columnas_invalidas) - 5} más")
        
        # Preparar registros para inserción
        registros = []
        errores = []
        
        for idx, row in df.iterrows():
            try:
                fecha_raw = row['Fecha']
                
                if pd.isna(fecha_raw):
                    continue
                
                # Parsear fecha
                if isinstance(fecha_raw, (int, float)):
                    fecha = pd.Timestamp('1899-12-30') + pd.Timedelta(days=fecha_raw)
                else:
                    fecha = pd.to_datetime(fecha_raw, format='%d/%m/%Y', errors='coerce')
                    if pd.isna(fecha):
                        fecha = pd.to_datetime(fecha_raw, errors='coerce')
                
                if pd.isna(fecha):
                    errores.append(f"Fila {idx}: Fecha inválida '{fecha_raw}'")
                    continue
                
                fecha_str = fecha.strftime('%Y-%m-%d')
                
                # Procesar cada columna parseada
                for col_info in columnas_parseadas:
                    valor = row[col_info['columna']]
                    
                    if pd.isna(valor):
                        continue
                    
                    try:
                        registros.append({
                            'codigo_saih': col_info['codigo_saih'],
                            'id_tipo_caudal': col_info['id_tipo'],
                            'fecha': fecha_str,
                            'valor': float(valor)
                        })
                    except (ValueError, TypeError):
                        errores.append(
                            f"Fila {idx}, Columna {col_info['columna']}: "
                            f"Valor inválido '{valor}'"
                        )
                        
            except Exception as e:
                errores.append(f"Fila {idx}: Error procesando fila - {str(e)}")
        
        # Mostrar errores
        if errores:
            logging.warning(f"Se encontraron {len(errores)} errores")
            for error in errores[:10]:
                logging.warning(f"  - {error}")
            if len(errores) > 10:
                logging.warning(f"  ... y {len(errores) - 10} errores más")
        
        # Insertar registros
        if registros:
            logging.info(f"Insertando {len(registros)} registro(s) en 'saih_caudal'")
            total_insertados = insertar_caudales_bulk(engine, registros)
            logging.info(f"{total_insertados} registro(s) insertados/actualizados")
        else:
            logging.warning("No se encontraron registros válidos para insertar")
            
    except Exception as e:
        logging.error(f"ERROR procesando hoja '{hoja_nombre}': {str(e)}", exc_info=True)

def main():
    """Función principal que ejecuta el proceso completo de importación."""
    if not os.path.exists(EXCEL_FILE):
        logging.error(f"No se encuentra el fichero Excel: {EXCEL_FILE}")
        sys.exit(1)

    logging.info("="*80)
    logging.info("INICIO DEL PROCESO DE IMPORTACIÓN DE DATOS")
    logging.info("="*80)
     
    try:
        # Conectar a base de datos
        engine = build_engine()

        # Leer y procesar información del Excel
        _read_information_from_excel(engine)
        
        # Procesar hojas de mediciones
        hojas_mediciones = [
            ('Datos_Nivel', 'saih_nivel_embalse'),
            ('Datos_Precipitacion', 'saih_precipitacion'),
            ('Datos_Temperatura', 'saih_temperatura')
        ]
        
        for hoja_nombre, tabla_destino in hojas_mediciones:
            try:
                procesar_hoja_mediciones(engine, hoja_nombre, tabla_destino)
            except Exception as e:
                logging.error(f"Error al procesar hoja '{hoja_nombre}': {str(e)}")
                continue
        
        # Procesar hoja de caudales
        try:
            procesar_hoja_caudales(engine, 'Datos_Caudal')
        except Exception as e:
            logging.error(f"Error al procesar hoja 'Datos_Caudal': {str(e)}")

        logging.info("="*80)
        logging.info("PROCESO COMPLETADO EXITOSAMENTE")
        logging.info("="*80)
        
    except Exception as e:
        logging.error(f"ERROR CRÍTICO: {str(e)}", exc_info=True)
        sys.exit(1)

def _read_information_from_excel(engine):
    """Lee la hoja 'Información' del Excel y procesa provincias, municipios y estaciones SAIH."""
    logging.info("Leyendo hoja 'Información' del archivo Excel...")
    df = read_excel(EXCEL_FILE, "Información")
    
    # Eliminar la primera fila si contiene encabezados duplicados
    df = df.drop(0)
    
    # Renombrar columnas
    df = df.rename(columns={
        "Coordenadas UTM ETRS89_H29N": "X",
        "Unnamed: 5": "Y",
        "Ubicación": "Ubi"
    })
    
    logging.info(f"Total de registros leídos: {len(df)}")

    # PROCESAR PROVINCIAS
    database_provincias = fetch_provincias(engine)
    db_prov_names = {p['nombre'].strip() for p in database_provincias if p.get('nombre')}
    logging.info(f"Provincias en base de datos: {sorted(db_prov_names)}")

    excel_provincias = {
        str(val).strip() 
        for val in df['Provincia'].dropna() 
        if str(val).strip()
    }
    logging.info(f"Provincias en Excel: {sorted(excel_provincias)}")

    provincias_nuevas = sorted(excel_provincias - db_prov_names)
    if provincias_nuevas:
        logging.info(
            f"Insertando {len(provincias_nuevas)} provincia(s) nueva(s): "
            f"{provincias_nuevas}"
        )
        insert_provincia(engine, provincias_nuevas, id_ccaa=ID_CCAA)
    else:
        logging.info("No hay provincias nuevas para insertar")
        
    # Refrescar provincias
    database_provincias = fetch_provincias(engine)
    prov_map = {p['nombre']: p['id'] for p in database_provincias}
    logging.info(f"Total de provincias en base de datos: {len(prov_map)}")

    # PROCESAR MUNICIPIOS
    database_municipios = fetch_municipios(engine)
    db_mun_names = {(m['nombre'], m['id_provincia']) for m in database_municipios}
    logging.info(f"Municipios en base de datos: {len(db_mun_names)}")

    excel_municipios = set()
    for _, row in df.iterrows():
        mun_name = str(row['Municipio']).strip()
        prov_name = str(row['Provincia']).strip()
        prov_id = prov_map.get(prov_name)
        if mun_name and prov_id and mun_name != 'nan':
            excel_municipios.add((mun_name, prov_id))

    logging.info(f"Municipios únicos en Excel: {len(excel_municipios)}")

    municipios_nuevos = sorted(excel_municipios - db_mun_names)
    if municipios_nuevos:
        logging.info(f"Insertando {len(municipios_nuevos)} municipio(s) nuevo(s)")
        insertar_municipios(engine, municipios=municipios_nuevos)
    else:
        logging.info("No hay municipios nuevos para insertar")
        
    # Refrescar municipios
    database_municipios = fetch_municipios(engine)
    muni_map = {(m['nombre'], m['id_provincia']): m['id'] for m in database_municipios}
    logging.info(f"Total de municipios en base de datos: {len(muni_map)}")

    # PROCESAR ESTACIONES SAIH
    logging.info("Procesando estaciones SAIH...")
    
    database_estaciones = fetch_estacion_saih(engine)
    db_estacion_codigos = {e['codigo_saih'] for e in database_estaciones}
    logging.info(f"Estaciones SAIH en base de datos: {len(db_estacion_codigos)}")

    estaciones_nuevas = []
    errores = []
    
    for idx, row in df.iterrows():
        try:
            codigo_saih = str(row['SAIH']).strip()
            ubicacion = (
                str(row['Ubi']).strip() if pd.notna(row['Ubi']) 
                else str(row['Ubicación']).strip()
            )
            municipio_nombre = str(row['Municipio']).strip()
            provincia_nombre = str(row['Provincia']).strip()
            coord_x = row['X']
            coord_y = row['Y']
            
            if codigo_saih == 'nan' or not codigo_saih:
                continue
                
            if ubicacion == 'nan':
                ubicacion = f"Estación {codigo_saih}"
            
            if pd.isna(coord_x) or pd.isna(coord_y):
                errores.append(
                    f"Fila {idx}: Coordenadas inválidas para SAIH {codigo_saih}"
                )
                continue
            
            prov_id = prov_map.get(provincia_nombre)
            if not prov_id:
                errores.append(
                    f"Fila {idx}: Provincia '{provincia_nombre}' no encontrada "
                    f"para SAIH {codigo_saih}"
                )
                continue
                
            municipio_key = (municipio_nombre, prov_id)
            municipio_id = muni_map.get(municipio_key)
            
            if not municipio_id:
                errores.append(
                    f"Fila {idx}: Municipio '{municipio_nombre}' no encontrado "
                    f"para SAIH {codigo_saih}"
                )
                continue
            
            if codigo_saih in db_estacion_codigos:
                continue
            
            estaciones_nuevas.append({
                "codigo_saih": codigo_saih,
                "ubicacion": ubicacion,
                "id_municipio": municipio_id,
                "coord_x": float(coord_x),
                "coord_y": float(coord_y),
                "id_demarcacion": ID_DEMARCACION
            })
            
        except Exception as e:
            errores.append(f"Fila {idx}: Error procesando fila - {str(e)}")
    
    if errores:
        logging.warning(f"Se encontraron {len(errores)} errores durante el procesamiento")
        for error in errores[:10]:
            logging.warning(f"  - {error}")
        if len(errores) > 10:
            logging.warning(f"  ... y {len(errores) - 10} errores más")
    
    if estaciones_nuevas:
        logging.info(f"Insertando {len(estaciones_nuevas)} estación(es) SAIH nueva(s)")
        insertar_estaciones_saih(engine, estaciones_nuevas)
    else:
        logging.info("No hay estaciones SAIH nuevas para insertar")
    
    database_estaciones = fetch_estacion_saih(engine)
    logging.info(f"Total de estaciones SAIH en base de datos: {len(database_estaciones)}")


if __name__ == '__main__':
    main()
