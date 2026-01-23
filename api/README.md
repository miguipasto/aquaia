# API - AquaIA Backend

API REST completa para predicción de niveles de embalses usando LSTM Seq2Seq con datos meteorológicos AEMET, generación de recomendaciones inteligentes con LLM y creación automática de informes.

## Requisitos

- Python 3.9+
- PostgreSQL (ver `/data/database`)
- Ollama (opcional, para recomendaciones con IA)

## Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Crear archivo `.env` en base a `.env.template`:

```bash
cp .env.template .env
```

**Variables**
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Conexión PostgreSQL
- `OLLAMA_URL`: URL de Ollama (por defecto: `http://localhost:11434`)
- `ENABLE_LLM_RECOMENDACIONES`: Activar/desactivar IA (True/False)
- `MODEL_PATH`: Ruta al modelo LSTM entrenado

## Ejecución

### Desarrollo

```bash
python run.py
```

### Producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Documentación API: http://localhost:8000/docs

## Endpoints Principales

### Core
- `GET /api/health` - Estado del sistema (modelo, BD, LLM)
- `GET /api/embalses` - Lista de embalses disponibles
- `GET /api/embalses/{codigo}/historico` - Histórico de datos

### Predicciones
- `POST /api/predicciones/{codigo}` - Predicciones LSTM (horizonte configurable)
- `GET /api/predicciones/{codigo}/estado` - Estado actual del embalse

### Recomendaciones
- `GET /api/recomendaciones/{codigo}` - Recomendación operativa (con caché)
- `POST /api/recomendaciones/{codigo}` - Forzar nueva recomendación

### Informes
- `POST /api/informes/{codigo}/generar` - Generar informe (diario/semanal)
- `GET /api/informes/{codigo}/listar` - Listar informes generados
- `GET /api/informes/{codigo}/descargar/{informe_id}` - Descargar informe HTML

### Dashboard
- `GET /api/dashboard/kpis` - KPIs agregados del sistema
- `GET /api/dashboard/alertas` - Alertas activas

### Evaluación
- `POST /api/evaluaciones/precision` - Evaluar precisión del modelo
- `POST /api/evaluaciones/comparar` - Comparar configuraciones

## Estructura de Servicios

```
api/
├── services/
│   ├── prediction.py      # Predicciones LSTM
│   ├── recomendacion.py   # Generación de recomendaciones
│   ├── llm_service.py     # Integración con Ollama
│   ├── informe.py         # Generación de informes HTML
│   └── risk.py            # Evaluación de riesgos
├── routers/
│   ├── dashboard.py       # Endpoints dashboard
│   ├── evaluaciones.py    # Endpoints evaluación
│   ├── informes.py        # Endpoints informes
│   └── recomendaciones.py # Endpoints recomendaciones
├── middleware/
│   ├── cache.py           # Sistema de caché
│   ├── rate_limit.py      # Rate limiting
│   └── security.py        # Headers seguridad
└── templates/
    ├── informe_diario_template.html
    └── informe_semanal_template.html
```

## Tecnologías

- FastAPI 0.115+
- PyTorch 2.5+ (LSTM Seq2Vec)
- PostgreSQL con psycopg2
- Ollama (LLM Phi-3.5)
- Jinja2 (plantillas HTML)
- Pydantic (validación)
