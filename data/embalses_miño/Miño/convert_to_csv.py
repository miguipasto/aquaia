"""
Script para generar dataset_embalses.csv desde la base de datos PostgreSQL.
Este dataset se usa como base para entrenar el modelo antes de enriquecerlo con datos AEMET.
"""
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('/home/migui/master/TFM/aquaia/data/.env')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'aquaia')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

OUTPUT_CSV = "dataset_embalses.csv"

print("Conectando a la base de datos...")
engine = create_engine(DB_URI)

# Query para obtener todos los datos de embalses con provincia incluida
query = """
SELECT 
    n.codigo_saih,
    n.fecha,
    n.nivel,
    COALESCE(p.precipitacion, 0.0) as precipitacion,
    COALESCE(t.temperatura, 0.0) as temperatura,
    COALESCE(AVG(c.caudal), 0.0) as caudal_promedio,
    prov.nombre as provincia
FROM saih_nivel_embalse n
LEFT JOIN saih_precipitacion p 
    ON n.codigo_saih = p.codigo_saih AND n.fecha = p.fecha
LEFT JOIN saih_temperatura t 
    ON n.codigo_saih = t.codigo_saih AND n.fecha = t.fecha
LEFT JOIN saih_caudal c 
    ON n.codigo_saih = c.codigo_saih AND n.fecha = c.fecha
LEFT JOIN estacion_saih e 
    ON n.codigo_saih = e.codigo_saih
LEFT JOIN municipio m 
    ON e.id_municipio = m.id
LEFT JOIN provincia prov 
    ON m.id_provincia = prov.id
WHERE n.nivel IS NOT NULL
GROUP BY n.codigo_saih, n.fecha, n.nivel, p.precipitacion, t.temperatura, prov.nombre
ORDER BY n.codigo_saih, n.fecha
"""

print("Extrayendo datos de embalses...")
df = pd.read_sql(query, engine)

# Normalizar nombre de provincia (mayúsculas y sin espacios extra)
if 'provincia' in df.columns:
    df['provincia'] = df['provincia'].str.upper().str.strip()

print(f"\n{'='*60}")
print(f"Dataset generado:")
print(f"{'='*60}")
print(f"  - Total de registros: {len(df):,}")
print(f"  - Estaciones únicas: {df['codigo_saih'].nunique()}")
print(f"  - Rango de fechas: {df['fecha'].min()} a {df['fecha'].max()}")
print(f"  - Provincias únicas: {df['provincia'].nunique() if 'provincia' in df.columns else 'N/A'}")
print(f"  - Columnas ({len(df.columns)}): {list(df.columns)}")

# Mostrar cobertura de datos
print(f"\n{'='*60}")
print("Cobertura de datos:")
print(f"{'='*60}")
for col in df.columns:
    if col not in ['codigo_saih', 'fecha', 'provincia']:
        pct = (df[col].notna().sum() / len(df)) * 100
        non_zero = ((df[col] != 0.0) & (df[col].notna())).sum()
        print(f"  {col:20s}: {pct:6.2f}% completo | {non_zero:,} valores no-cero")

# Guardar CSV
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n{'='*60}")
print(f"✓ Dataset guardado en: {OUTPUT_CSV}")
print(f"{'='*60}")

# Mostrar estadísticas por estación
print(f"\nRegistros por estación (Top 10):")
stats = df.groupby('codigo_saih').size().sort_values(ascending=False)
for station, count in stats.head(10).items():
    prov = df[df['codigo_saih'] == station]['provincia'].iloc[0] if 'provincia' in df.columns else 'N/A'
    print(f"  {station} ({prov}): {count:,} registros")

# Mostrar estadísticas por provincia
if 'provincia' in df.columns:
    print(f"\nRegistros por provincia:")
    prov_stats = df.groupby('provincia').agg({
        'codigo_saih': 'nunique',
        'nivel': 'count'
    }).rename(columns={'codigo_saih': 'estaciones', 'nivel': 'registros'})
    prov_stats = prov_stats.sort_values('registros', ascending=False)
    for prov, row in prov_stats.iterrows():
        print(f"  {prov}: {row['estaciones']} estaciones | {row['registros']:,} registros")

print(f"\n{'='*60}")
print("SIGUIENTE PASO:")
print("Ejecuta: python3 /home/migui/master/TFM/old/Data/prepare_aemet_embalses.py")
print(f"{'='*60}")