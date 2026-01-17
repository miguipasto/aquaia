# AquaIA - Sistema Inteligente de Gestión de Embalses

## 🚀 Guía Rápida de Instalación y Ejecución

Este documento te guiará paso a paso para levantar todo el sistema AquaIA.

## 📋 Prerrequisitos

- **Python 3.9+** (con pip)
- **Node.js 18+** (con npm)
- **PostgreSQL 13+**
- **Git**

## 🗂️ Estructura del Proyecto

```
aquaia/
├── api/                 # Backend FastAPI
├── data/               # Scripts y datos
├── frontend/           # Dashboard React
└── training/           # Notebooks de entrenamiento
```

## 🔧 Paso 1: Configurar Base de Datos

### 1.1 Iniciar PostgreSQL

```bash
cd aquaia/data/database
docker-compose up -d
```

Esto levantará PostgreSQL en el puerto **8432**.

### 1.2 Verificar la conexión

```bash
psql -h localhost -p 8432 -U usr_aquaia -d aquaia
# Password: (ver en aquaia/data/database/.env)
```

## 🐍 Paso 2: Configurar Backend (API)

### 2.1 Crear entorno virtual

```bash
cd aquaia/api
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2.2 Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2.3 Configurar variables de entorno

El archivo `.env` ya existe en `aquaia/api/.env`. Verifica que la configuración de base de datos coincida con el docker-compose:

```env
DB_HOST=localhost
DB_PORT=8432
DB_NAME=aquaia
DB_USER=usr_aquaia
DB_PASSWORD=V0ybLRzx3ihiko1NvqAk
```

### 2.4 Verificar que el modelo está presente

Asegúrate de que existen estos archivos:
- `aquaia/api/resources/Training_Aemet/modelo_embalses_aemet.pth`
- `aquaia/api/resources/Training_Aemet/artifacts/scalers.npy`
- `aquaia/api/resources/Training_Aemet/artifacts/metrics.json`

### 2.5 Iniciar el servidor API

```bash
python run.py
```

O alternativamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en: **http://localhost:8000**
- Documentación interactiva: **http://localhost:8000/docs**

## ⚛️ Paso 3: Configurar Frontend (Dashboard)

### 3.1 Instalar dependencias

```bash
cd aquaia/frontend
npm install
```

### 3.2 Configurar variables de entorno

Crea un archivo `.env` en `aquaia/frontend/`:

```bash
cp .env.example .env
```

El contenido de `.env`:

```env
VITE_API_URL=http://localhost:8000
```

### 3.3 Iniciar servidor de desarrollo

```bash
npm run dev
```

El dashboard estará disponible en: **http://localhost:3000**

## ✅ Verificación del Sistema

### 1. Verificar que la API funciona

Abre tu navegador y ve a:
- http://localhost:8000/health

Deberías ver algo como:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "scalers_loaded": true,
  "data_loaded": true,
  "num_embalses": 25
}
```

### 2. Verificar endpoints clave

```bash
# Lista de embalses
curl http://localhost:8000/embalses

# KPIs del dashboard
curl http://localhost:8000/dashboard/kpis

# Alertas
curl http://localhost:8000/dashboard/alertas
```

### 3. Verificar el dashboard

1. Abre http://localhost:3000
2. Deberías ver el dashboard con KPIs
3. Prueba a navegar por las diferentes secciones:
   - Dashboard (inicio)
   - Predicciones
   - Alertas
   - Recomendaciones

## 🎯 Usando el Sistema

### Simulación Temporal

1. Haz clic en el botón **"Fecha: Actual"** en la esquina superior derecha
2. Selecciona una fecha histórica (ej: 2024-06-01)
3. Haz clic en **"Aplicar"**
4. El dashboard ahora simula que estás en esa fecha
5. No verás datos posteriores a la fecha seleccionada

### Ver Predicciones

1. Ve a la sección **"Predicciones"**
2. Haz clic en cualquier embalse
3. Verás:
   - Gráfico de evolución histórica
   - Predicción a 90 días (configurable)
   - Recomendación operativa
4. Haz clic en **"Mostrar lo que pasó realmente"** para comparar

### Revisar Alertas

1. Ve a la sección **"Alertas"**
2. Verás todas las alertas activas del sistema
3. Puedes filtrar por:
   - Severidad (Critical, Warning, Info)
   - Tipo de alerta
   - Demarcación hidrográfica

### Consultar Recomendaciones

1. Ve a la sección **"Recomendaciones"**
2. Verás recomendaciones operativas para cada embalse
3. Clasificadas por nivel de riesgo:
   - ALTO (≥ 95% capacidad)
   - MODERADO (80-95%)
   - BAJO (30-80%)
   - SEQUÍA (≤ 30%)

## 🛠️ Comandos Útiles

### Backend

```bash
# Reiniciar servidor
Ctrl+C
python run.py

# Ver logs
tail -f logs/api.log

# Limpiar caché
curl -X POST http://localhost:8000/admin/cache/clear

# Ver métricas
curl http://localhost:8000/metrics
```

### Frontend

```bash
# Reconstruir
npm run build

# Limpiar caché y node_modules
rm -rf node_modules package-lock.json
npm install

# Lint
npm run lint
```

### Base de Datos

```bash
# Conectar a PostgreSQL
psql -h localhost -p 8432 -U usr_aquaia -d aquaia

# Ver tablas
\dt

# Ver embalses
SELECT codigo_saih, ubicacion, provincia FROM estacion_saih LIMIT 10;

# Ver últimos niveles
SELECT n.codigo_saih, e.ubicacion, n.fecha, n.nivel 
FROM saih_nivel_embalse n
JOIN estacion_saih e ON n.codigo_saih = e.codigo_saih
ORDER BY n.fecha DESC
LIMIT 20;
```

## 🐛 Solución de Problemas Comunes

### Error: "Connection refused" al iniciar la API

**Problema**: No puede conectar con PostgreSQL

**Solución**:
```bash
# Verificar que PostgreSQL está corriendo
docker ps

# Si no está corriendo
cd aquaia/data/database
docker-compose up -d

# Esperar 10 segundos y reintentar
python run.py
```

### Error: "Model file not found"

**Problema**: No encuentra el archivo del modelo

**Solución**:
```bash
# Verificar que existen los archivos
ls -la aquaia/api/resources/Training_Aemet/
ls -la aquaia/api/resources/Training_Aemet/artifacts/

# Si no existen, copiarlos desde training/Models/
cp aquaia/training/Models/model_20260114_193518/model_20260114_193518.pth \
   aquaia/api/resources/Training_Aemet/modelo_embalses_aemet.pth

cp aquaia/training/Models/model_20260114_193518/scalers_20260114_193518.npy \
   aquaia/api/resources/Training_Aemet/artifacts/scalers.npy
```

### Error: "Cannot GET /api/..."

**Problema**: El frontend no puede conectar con la API

**Solución**:
1. Verificar que la API está corriendo en http://localhost:8000
2. Verificar el archivo `.env` en frontend: `VITE_API_URL=http://localhost:8000`
3. Reiniciar el servidor de desarrollo: `npm run dev`

### Gráficos no se muestran

**Problema**: Los gráficos aparecen vacíos

**Solución**:
1. Abre la consola del navegador (F12)
2. Busca errores en la pestaña "Console"
3. Verifica que hay datos disponibles:
   ```bash
   curl "http://localhost:8000/embalses/E001/historico?start_date=2024-01-01&end_date=2024-12-31"
   ```

## 📊 Datos de Ejemplo

Para probar el sistema rápidamente, aquí hay algunos códigos de embalses:

- **E001**: Belesar (Lugo)
- **E002**: Castrelo (Pontevedra)
- **E003**: Velle (Ourense)
- **E004**: Frieira (Ourense)

Prueba con estos en la sección de predicciones.

## 🎓 Más Información

- **Documentación de la API**: http://localhost:8000/docs
- **Frontend README**: `aquaia/frontend/README.md`
- **API README**: `aquaia/api/README.md` (si existe)

## 📞 Soporte

Si encuentras algún problema no cubierto aquí, revisa:
1. Los logs del backend
2. La consola del navegador (F12)
3. Los logs de PostgreSQL: `docker logs aquaia-postgres`

---

**¡Listo!** Ahora tienes todo el sistema AquaIA funcionando. Disfruta explorando las predicciones y recomendaciones del sistema inteligente. 🌊
