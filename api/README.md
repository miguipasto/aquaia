# API - AquaAI Backend

API REST para predicción de niveles de embalses usando LSTM Seq2Seq con datos meteorológicos.

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

- `/health` - Estado del sistema
- `/embalses` - Lista de embalses
- `/predicciones/{codigo}` - Predicciones LSTM
- `/recomendaciones/{codigo}` - Recomendaciones operativas
- `/dashboard/kpis` - KPIs del sistema

## Tecnologías

- FastAPI
- PyTorch (LSTM)
- PostgreSQL
- Ollama (LLM)
