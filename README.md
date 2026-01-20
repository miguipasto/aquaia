# 🌊 AquaAI - Sistema Inteligente de Gestión de Embalses

Sistema avanzado de predicción y gestión operativa de embalses que combina Deep Learning (LSTM Seq2Seq) con Inteligencia Artificial generativa (Ollama) para proporcionar predicciones precisas y recomendaciones contextualizadas.

## 🎯 Descripción

AquaAI es una plataforma completa que integra:

- **Predicción temporal**: Modelo LSTM Seq2Seq entrenado con datos históricos de niveles de embalses y meteorología (AEMET)
- **Recomendaciones inteligentes**: Generación de recomendaciones operativas usando LLMs (Phi-3.5)
- **Dashboard interactivo**: Visualización en tiempo real de predicciones, alertas y KPIs
- **Análisis de riesgo**: Evaluación automática de niveles críticos (sequía, desbordamiento)

## 🏗️ Arquitectura

```
┌─────────────────┐
│   Frontend      │  React + Vite + TailwindCSS
│   (Port 5173)   │  
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   API (FastAPI) │  Predicciones + Recomendaciones
│   (Port 8000)   │  
└────┬───────┬────┘
     │       │
     ↓       ↓
┌────────┐ ┌──────────┐
│ PostgreSQL│ │  Ollama   │  LLM (Phi-3.5)
│ (8432)  │ │  (11434)  │
└────────┘ └──────────┘
```

## 📦 Componentes

Cada componente tiene su propio README con instrucciones específicas:

- **[Frontend](frontend/README.md)** - Dashboard web interactivo
- **[API](api/README.md)** - Backend FastAPI con predicciones
- **[Database](data/database/README.md)** - PostgreSQL con Docker
- **[Recomendations](recomendations/README.md)** - Servicio Ollama LLM

## 🚀 Inicio Rápido

### 1. Base de datos

```bash
cd data/database
cp .env.template .env  # Configurar credenciales
docker-compose up -d
```

### 2. API

```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env  # Configurar variables
python run.py
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env  # Configurar API_URL
npm run dev
```

### 4. Ollama (Opcional)

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo
ollama pull phi3.5:latest

# Iniciar servicio
ollama serve
```

Acceder a: **http://localhost:5173**

## ⚙️ Variables de Configuración Importantes

### API (.env)

| Variable | Descripción | Por Defecto |
|----------|-------------|-------------|
| `DB_HOST` | Host PostgreSQL | `localhost` |
| `DB_PORT` | Puerto PostgreSQL | `8432` |
| `DB_NAME` | Nombre base de datos | `aquaia` |
| `ENABLE_LLM_RECOMENDACIONES` | Activar IA | `False` |
| `OLLAMA_URL` | URL servicio Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modelo LLM | `phi3.5:latest` |
| `MODEL_PATH` | Ruta modelo LSTM | `resources/Training_Aemet/modelo_embalses_aemet.pth` |
| `CORS_ORIGINS` | Orígenes permitidos | `http://localhost:5173` |

### Frontend (.env)

| Variable | Descripción | Por Defecto |
|----------|-------------|-------------|
| `VITE_API_URL` | URL del backend | `http://localhost:8000` |

### Database (.env)

| Variable | Descripción | Por Defecto |
|----------|-------------|-------------|
| `POSTGRES_USER` | Usuario PostgreSQL | `usr_aquaia` |
| `POSTGRES_PASSWORD` | Contraseña | *(configurar)* |
| `POSTGRES_PORT` | Puerto externo | `8432` |

## 📊 Características Técnicas

### Modelo LSTM

- **Arquitectura**: Encoder-Decoder Seq2Seq
- **Input**: 90 días históricos (nivel, precipitación, temperatura, caudal)
- **Output**: Predicción hasta 180 días
- **Métricas**: MAE, RMSE, R²

### Sistema de Recomendaciones

- **Niveles de riesgo**: ALTO, MODERADO, BAJO, SEQUÍA
- **Umbrales configurables** por embalse
- **Caché inteligente** (6 horas TTL)
- **Fallback automático** si LLM no disponible

### Dashboard

- **Visualización**: Gráficos interactivos (Recharts)
- **Simulación temporal**: Ver datos históricos
- **Alertas**: Sistema de notificaciones
- **KPIs**: Métricas agregadas del sistema

## 🔧 Dependencias Principales

### Backend
- FastAPI 0.115+
- PyTorch 2.5+
- psycopg2-binary
- pandas, numpy
- httpx (cliente Ollama)

### Frontend
- React 18
- TanStack Query
- Recharts
- TailwindCSS

## 📁 Estructura del Proyecto

```
aquaia/
├── api/                    # Backend FastAPI
│   ├── services/          # Lógica de negocio
│   ├── routers/           # Endpoints REST
│   ├── data/              # Acceso a datos
│   └── resources/         # Modelos entrenados
├── frontend/              # Dashboard React
│   └── src/
│       ├── pages/         # Vistas principales
│       ├── components/    # Componentes reutilizables
│       └── services/      # Cliente API
├── data/
│   ├── database/          # Docker PostgreSQL
│   └── aemet/            # Scripts datos AEMET
├── training/              # Notebooks entrenamiento
└── recomendations/        # Configuración Ollama
```

## 🔐 Seguridad

- API Keys configurables
- Rate limiting
- CORS configurable
- Headers de seguridad (HSTS, X-Frame-Options)
- Validación de inputs con Pydantic

## 📈 Casos de Uso

1. **Predicción de niveles**: Anticipar cambios en embalses hasta 6 meses
2. **Gestión de riesgos**: Detectar situaciones de sequía o desbordamiento
3. **Recomendaciones operativas**: Acciones sugeridas por IA contextual
4. **Análisis histórico**: Comparación de tendencias
5. **Dashboard ejecutivo**: KPIs y métricas agregadas

## 👥 Contacto

Para más información sobre el proyecto, consultar la documentación en `/docs` o los READMEs específicos de cada componente.
