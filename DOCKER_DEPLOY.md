# 🐳 AquaAI - Despliegue con Docker

Guía simple para desplegar la plataforma AquaAI utilizando Docker.

## 📋 Requisitos

- Docker Engine 20.10+ ([Instalar Docker](https://docs.docker.com/engine/install/))
- Docker Compose v2.0+ (incluido con Docker Desktop)
- 8 GB RAM mínimo
- 20 GB espacio en disco

## 🚀 Despliegue Paso a Paso

### Paso 1: Configurar Variables de Entorno

El proyecto incluye un archivo `.env` preconfigurado. Si es tu primera vez o necesitas personalizar:

**Opción A: Usar el .env existente (recomendado)**
```bash
# Ya está configurado, solo revisa los valores
nano .env
```

**Opción B: Crear desde cero**
```bash
# Copiar desde el ejemplo
cp .env.example .env
nano .env
```

**Variables importantes a configurar:**

```env
# Credenciales de PostgreSQL
POSTGRES_USER=admin_aquaia
POSTGRES_PASSWORD=Aquaia2025TFM!    # ⚠️ Cambiar en producción

# Clave secreta de la API
SECRET_KEY=dev-secret-key...        # ⚠️ Generar una nueva

# Usuario/contraseña para la API (deben coincidir con PostgreSQL)
DB_USER=admin_aquaia
DB_PASSWORD=Aquaia2025TFM!

# API Key de AEMET (si necesitas actualizar datos meteorológicos)
AEMET_API_KEY=tu_api_key_aqui
```

**Para generar claves seguras en producción:**
```bash
# Generar SECRET_KEY
openssl rand -hex 32

# O con Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **Nota importante:** El `.env` contiene credenciales reales. No lo subas a Git (ya está en `.gitignore`).

### Paso 2: Construir las Imágenes

```bash
docker compose build
```

Este proceso puede tardar varios minutos la primera vez.

### Paso 3: Levantar los Servicios

```bash
docker compose up -d
```

Esto iniciará todos los servicios en segundo plano.

### Paso 4: Descargar el Modelo LLM

```bash
# Descargar modelo phi3.5 (tarda 5-10 minutos)
docker compose exec ollama ollama pull phi3.5:latest

# Verificar descarga
docker compose exec ollama ollama list
```

### Paso 5: Verificar que Todo Funciona

```bash
# Ver estado de los servicios
docker compose ps

# Ver logs
docker compose logs -f

# Deberías ver todos los servicios como "Up" y "healthy"
```

### Paso 6: Acceder a la Aplicación

- **Frontend**: http://localhost
- **API**: http://localhost:8000
- **Documentación API**: http://localhost:8000/docs
- **WebUI Ollama**: http://localhost:3333

## 📊 Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `frontend` | 80 | Interfaz web (React + Nginx) |
| `api` | 8000 | API REST (FastAPI) |
| `postgres` | 5432 | Base de datos PostgreSQL |
| `redis` | 6379 | Cache de datos |
| `ollama` | 11434 | Motor LLM (phi3.5) |
| `webui` | 3333 | Gestión de Ollama |

Todos los datos se guardan en volúmenes Docker persistentes:
- `aquaia_postgres_data` - Datos de la base de datos
- `aquaia_ollama_data` - Modelos LLM (~4GB)
- `aquaia_redis_data` - Cache
- `aquaia_webui_data` - Configuración WebUI

### 📝 Nota sobre archivos .env individuales

Docker Compose usa un único archivo `.env` en la raíz del proyecto. Los archivos `.env` en subdirectorios (`api/.env`, `data/.env`, etc.) son para desarrollo local sin Docker y no afectan al despliegue con Docker.

## 🔧 Comandos Comunes

### Ver estado y logs

```bash
# Ver estado de todos los servicios
docker compose ps

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f api
docker compose logs -f frontend
```

### Gestión de servicios

```bash
# Detener servicios
docker compose stop

# Reiniciar servicios
docker compose restart

# Reiniciar un servicio específico
docker compose restart api

# Detener y eliminar contenedores (mantiene datos)
docker compose down

# Detener y eliminar TODO incluyendo datos (¡CUIDADO!)
docker compose down -v
```

### Acceso a servicios

```bash
# Acceder a PostgreSQL
docker compose exec postgres psql -U aquaia_user -d aquaia

# Acceder a la API
docker compose exec api bash

# Ver modelos LLM instalados
docker compose exec ollama ollama list
```

## 🔄 Actualizar el Sistema

Si haces cambios en el código:

```bash
# 1. Detener servicios
docker compose stop

# 2. Reconstruir imágenes
docker compose build

# 3. Levantar de nuevo
docker compose up -d
```

## � Backup de la Base de Datos

```bash
# Crear backup
docker compose exec -T postgres pg_dump -U aquaia_user aquaia > backup.sql

# Restaurar backup
cat backup.sql | docker compose exec -T postgres psql -U aquaia_user -d aquaia
```

## 🐛 Problemas Comunes

### Puerto ya en uso

Si ves un error como "port is already in use":

```bash
# Ver qué usa el puerto
sudo lsof -i :8000

# Cambiar el puerto en .env
nano .env
# Editar: API_PORT=8001

# Reiniciar
docker compose down
docker compose up -d
```

### PostgreSQL no arranca

```bash
# Ver logs
docker compose logs postgres

# Si el volumen está corrupto, recrearlo (¡pierdes datos!)
docker compose down -v
docker compose up -d
```

### Ollama no descargó el modelo

```bash
# Descargar manualmente
docker compose exec ollama ollama pull phi3.5:latest

# Verificar
docker compose exec ollama ollama list
```

### Frontend muestra página en blanco

```bash
# Ver logs del navegador (F12 > Console)
# Verificar que VITE_API_URL en .env es correcto

# Reconstruir
docker compose build frontend
docker compose up -d frontend
```

## 🔒 Notas de Seguridad para Producción

- ✅ Cambia `POSTGRES_PASSWORD` y `SECRET_KEY` en `.env`
- ✅ Asegúrate que `DEBUG=False` en producción
- ✅ Configura HTTPS con nginx/traefik
- ✅ Configura CORS solo para tus dominios
- ✅ No expongas puertos internos (PostgreSQL, Redis) públicamente
- ✅ Haz backups regulares de PostgreSQL

---

**¡Listo! Tu plataforma AquaAI está funcionando 🚀💧**
