"""
Script para preparar datos AEMET agregados por provincia-fecha
y enriquecer el dataset de embalses.
"""
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('.env')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'aquaia')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

AEMET_CSV = "aemet/datos_aemet.csv"
EMBALSES_CSV = "embalses_miño/Miño/dataset_embalses.csv"
OUTPUT_CSV = "dataset_embalses_aemet.csv"

print("Cargando datos AEMET...")
aemet = pd.read_csv(AEMET_CSV, low_memory=False)
aemet['fecha'] = pd.to_datetime(aemet['fecha'], errors='coerce')

# Limpiar y convertir columnas numéricas
numeric_cols = ['tmed', 'prec', 'tmin', 'tmax', 'hrMedia', 'velmedia', 'racha']
for col in numeric_cols:
    if col in aemet.columns:
        aemet[col] = aemet[col].astype(str).str.replace(',', '.', regex=False)
        aemet[col] = pd.to_numeric(aemet[col], errors='coerce')

aemet = aemet.rename(columns={'hrMedia': 'hr_media'})
print(f"Registros AEMET: {len(aemet)}")

# Agregar por provincia-fecha
aemet_prov = aemet.groupby(['provincia', 'fecha']).agg({
    'tmed': 'mean',
    'prec': 'sum',
    'tmin': 'min',
    'tmax': 'max',
    'hr_media': 'mean',
    'velmedia': 'mean',
    'racha': 'max'
}).reset_index()

print(f"Agregado provincial: {len(aemet_prov)} registros")

# Cargar dataset de embalses
print("Cargando dataset de embalses...")
embalses = pd.read_csv(EMBALSES_CSV)
embalses['fecha'] = pd.to_datetime(embalses['fecha'], errors='coerce')

# Verificar que existe la columna provincia
if 'provincia' not in embalses.columns:
    print("⚠️ ADVERTENCIA: dataset_embalses.csv no tiene columna 'provincia'")
    print("Obteniendo provincias desde la BD...")
    try:
        engine = create_engine(DB_URI)
        query = """
        SELECT DISTINCT e.codigo_saih, p.nombre as provincia
        FROM estacion_saih e
        JOIN municipio m ON e.id_municipio = m.id
        JOIN provincia p ON m.id_provincia = p.id
        WHERE e.codigo_saih IS NOT NULL
        """
        mapeo_prov = pd.read_sql(query, engine)
        print(f"Mapeo obtenido: {len(mapeo_prov)} estaciones")
        embalses = embalses.merge(mapeo_prov, on='codigo_saih', how='left')
    except Exception as e:
        print(f"❌ Error: {e}")
        raise ValueError("No se pudo obtener información de provincias")
else:
    print(f"✓ Columna 'provincia' encontrada en dataset")

print(f"Provincias en dataset: {embalses['provincia'].nunique()} únicas")
print(f"Estaciones en dataset: {embalses['codigo_saih'].nunique()}")

# Normalizar nombres de provincia
embalses['provincia'] = embalses['provincia'].str.upper().str.strip()
aemet_prov['provincia'] = aemet_prov['provincia'].str.upper().str.strip()

# Merge con datos AEMET
print("Fusionando datos AEMET con embalses...")
result = embalses.merge(
    aemet_prov,
    on=['provincia', 'fecha'],
    how='left'
)

print(f"\nDataset final: {len(result)} registros")
print(f"Columnas: {list(result.columns)}")

# Estadísticas de cobertura
cov = {}
for col in ['tmed', 'prec', 'tmin', 'tmax', 'hr_media', 'velmedia', 'racha']:
    if col in result.columns:
        cov[col] = (result[col].notna().sum() / len(result)) * 100

print("\nCobertura de datos AEMET:")
for col, pct in cov.items():
    print(f"  {col}: {pct:.1f}%")

# Guardar
result.to_csv(OUTPUT_CSV, index=False)
print(f"\n{'='*60}")
print(f"✓ Dataset enriquecido guardado en: {OUTPUT_CSV}")
print(f"{'='*60}")
print(f"\nColumnas finales ({len(result.columns)}): {list(result.columns)}")
print(f"\nSIGUIENTE PASO:")
print(f"  cd /home/migui/master/TFM/aquaia/training")
print(f"  jupyter notebook training_model.ipynb")
print(f"{'='*60}")
