# Recomendations Service - Ollama

Servicio de generación de recomendaciones inteligentes usando Ollama con modelo Phi-3.5.

## Requisitos

- Ollama instalado
- GPU recomendada (opcional pero acelera inferencia)

## Instalación de Ollama

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS

```bash
brew install ollama
```

### Windows

Descargar desde: https://ollama.com/download

## Configuración

### Descargar modelo Phi-3.5

```bash
ollama pull phi3.5:latest
```

### Verificar modelos disponibles

```bash
ollama list
```

## Ejecución

### Iniciar servicio Ollama

```bash
ollama serve
```

Servicio disponible en: http://localhost:11434

### Probar modelo

```bash
ollama run phi3.5:latest
```

## Integración con API

En el archivo `.env` de la API, configurar:

```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=phi3.5:latest
ENABLE_LLM_RECOMENDACIONES=True
LLM_TIMEOUT=30
LLM_TEMPERATURE=0.7
```

## Configuración de Prompts

Los prompts del sistema se configuran en `api/services/llm_service.py`:

- **Recomendaciones**: Prompt estructurado con datos del embalse
- **Informes**: Prompt de resumen ejecutivo
- **Formato**: JSON obligatorio para parseo automático
- **Validación**: Verificación de estructura y coherencia

## Testing

Ver notebook `test_model.ipynb` para pruebas del modelo.

## Modelos Alternativos

Otros modelos compatibles:
- `llama3.2:latest`
- `mistral:latest`
- `gemma2:latest`

Cambiar en configuración: `OLLAMA_MODEL=nombre_modelo`
