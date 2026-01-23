# 🌊 AquaIA - Sistema Inteligente de Gestión de Embalses

Sistema avanzado de predicción y gestión operativa de embalses que combina Deep Learning (LSTM Seq2Seq) con Inteligencia Artificial generativa (Ollama) para proporcionar predicciones precisas, recomendaciones contextualizadas e informes automáticos.

## 🎯 Descripción

AquaIA es una plataforma completa que integra:

- **Predicción temporal**: Modelo LSTM Seq2Seq entrenado con datos históricos de niveles de embalses y meteorología (AEMET)
- **Recomendaciones inteligentes**: Generación de recomendaciones operativas usando LLMs (Phi-3.5)
- **Generación de informes**: Informes diarios y semanales automáticos con análisis contextualizado
- **Dashboard interactivo**: Visualización en tiempo real de predicciones, alertas y KPIs
- **Análisis de riesgo**: Evaluación automática de niveles críticos (sequía, desbordamiento)
- **Sistema de validación**: Suite completa de tests para validar precisión y rendimiento

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

- **[Frontend](frontend/README.md)** - Dashboard web interactivo con React
- **[API](api/README.md)** - Backend FastAPI con predicciones, recomendaciones e informes
- **[Database](data/database/README.md)** - PostgreSQL con Docker
- **[Recomendations](recomendations/README.md)** - Servicio Ollama LLM
- **[Training](training/)** - Notebooks de entrenamiento del modelo LSTM
- **[Validation](validation/)** - Suite de tests de precisión y rendimiento

## 🚀 Inicio Rápido

### 🐳 Con Docker

```bash
# 1. Configurar variables de entorno
cp .env.example .env
nano .env  # Cambiar POSTGRES_PASSWORD y SECRET_KEY

# 2. Construir y levantar servicios
docker compose build
docker compose up -d

# 3. Descargar modelo LLM
docker compose exec ollama ollama pull phi3.5:latest

# 4. Acceder
Frontend: http://localhost
API: http://localhost:8000/docs
```

**Ver [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md) para la guía completa.**

---

### 💻 Instalación Manual (Desarrollo Local)

#### 1. Base de datos

```bash
cd data/database
cp .env.template .env  # Configurar credenciales
docker-compose up -d
```

#### 2. API

```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env  # Configurar variables
python run.py
```

#### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env  # Configurar API_URL
npm run dev
```

#### 4. Ollama (Opcional)

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo
ollama pull phi3.5:latest

# Iniciar servicio
ollama serve
```

Acceder a: **http://localhost:3000**

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
| `ENABLE_INFORMES` | Activar generación de informes | `True` |
| `INFORMES_DIR` | Directorio de informes | `informes_generados` |

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

- **Arquitectura**: LSTM Seq2Vec (2 capas, 64 unidades)
- **Input**: 360 días históricos + 11 variables meteorológicas AEMET
- **Output**: Predicción hasta 180 días
- **Métricas**: MAE 1.73 hm³, RMSE 2.20 hm³, R² 0.18 (test)
- **Hiperparámetros**: Lookback 360, Horizon 180, Dropout 0.4

### Sistema de Recomendaciones

- **Niveles de riesgo**: ALTO, MODERADO, BAJO, SEQUÍA
- **Umbrales configurables** por embalse
- **Caché inteligente** (6 horas TTL)
- **Fallback automático** si LLM no disponible

### Generación de Informes

- **Tipos**: Diarios y semanales
- **Formato**: HTML con estilos integrados (Tailwind)
- **Contenido**: Análisis automático, métricas, recomendaciones
- **LLM**: Resúmenes narrativos generados con Phi-3.5
- **Plantillas**: Jinja2 con diseño responsive

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
│   ├── services/          # Lógica de negocio (prediction, recomendacion, informe, llm_service, risk)
│   ├── routers/           # Endpoints REST (dashboard, evaluaciones, informes, recomendaciones)
│   ├── middleware/        # Cache, rate limiting, seguridad
│   ├── data/              # Acceso a datos y loaders
│   ├── templates/         # Plantillas HTML para informes
│   ├── informes_generados/# Informes HTML generados
│   └── resources/         # Modelos entrenados LSTM
├── frontend/              # Dashboard React
│   └── src/
│       ├── pages/         # Vistas principales
│       ├── components/    # Componentes reutilizables
│       └── services/      # Cliente API
├── data/
│   ├── database/          # Docker PostgreSQL
│   ├── aemet/            # Scripts datos AEMET
│   └── embalses_miño/    # Datos históricos Miño-Sil
├── training/              # Notebooks entrenamiento
│   ├── training_model.ipynb
│   ├── verify_real_metrics.py
│   └── Models/           # Modelos entrenados guardados
├── validation/            # Suite de tests
│   ├── model/            # Tests de precisión y ablación
│   ├── api/              # Tests de latencia y carga
│   ├── informes/         # Tests de generación
│   ├── recomendaciones/  # Tests de calidad
│   └── results/          # Resultados de validación
└── recomendations/        # Configuración Ollama
```

## 🔐 Seguridad

- API Keys configurables
- Rate limiting
- CORS configurable
- Headers de seguridad (HSTS, X-Frame-Options)
- Validación de inputs con Pydantic

## 📈 Casos de Uso

1. **Predicción de niveles**: Anticipar cambios en embalses hasta 6 meses (horizonte 180 días)
2. **Gestión de riesgos**: Detectar situaciones de sequía o desbordamiento con alertas automáticas
3. **Recomendaciones operativas**: Acciones sugeridas por IA contextual (LLM Phi-3.5)
4. **Generación de informes**: Informes diarios/semanales automáticos en HTML con resúmenes narrativos
5. **Análisis histórico**: Comparación de tendencias y simulación temporal
6. **Dashboard ejecutivo**: KPIs y métricas agregadas en tiempo real
7. **Validación continua**: Suite de tests automatizados de precisión y rendimiento
