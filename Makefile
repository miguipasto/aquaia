# AquaAI - Makefile para gestión Docker
# ====================================

.PHONY: help build up down restart logs status clean deploy dev

# Colores para output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# Variables
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_DEV := docker compose -f docker-compose.dev.yml

help: ## Mostrar esta ayuda
	@echo "$(BLUE)AquaAI - Comandos disponibles:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ====================
# PRODUCCIÓN
# ====================

deploy: ## 🚀 Desplegar todo el sistema (producción)
	@echo "$(BLUE)Desplegando AquaAI...$(NC)"
	@chmod +x deploy.sh
	@./deploy.sh

build: ## 🔨 Construir todas las imágenes
	@echo "$(BLUE)Construyendo imágenes...$(NC)"
	@$(DOCKER_COMPOSE) build

build-no-cache: ## 🔨 Construir sin caché (fuerza reconstrucción)
	@echo "$(BLUE)Construyendo imágenes sin caché...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache

up: ## ▶️  Levantar todos los servicios
	@echo "$(BLUE)Levantando servicios...$(NC)"
	@$(DOCKER_COMPOSE) up -d

down: ## ⏹️  Detener y eliminar contenedores
	@echo "$(BLUE)Deteniendo servicios...$(NC)"
	@$(DOCKER_COMPOSE) down

stop: ## ⏸️  Detener servicios sin eliminar
	@echo "$(BLUE)Deteniendo servicios...$(NC)"
	@$(DOCKER_COMPOSE) stop

restart: ## 🔄 Reiniciar todos los servicios
	@echo "$(BLUE)Reiniciando servicios...$(NC)"
	@$(DOCKER_COMPOSE) restart

logs: ## 📋 Ver logs de todos los servicios
	@$(DOCKER_COMPOSE) logs -f

logs-api: ## 📋 Ver logs de la API
	@$(DOCKER_COMPOSE) logs -f api

logs-frontend: ## 📋 Ver logs del Frontend
	@$(DOCKER_COMPOSE) logs -f frontend

logs-db: ## 📋 Ver logs de PostgreSQL
	@$(DOCKER_COMPOSE) logs -f postgres

status: ## 📊 Ver estado de los servicios
	@echo "$(BLUE)Estado de los servicios:$(NC)"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@chmod +x check-status.sh
	@./check-status.sh

health: ## 🏥 Verificar salud de los servicios
	@chmod +x check-status.sh
	@./check-status.sh

ps: ## 📋 Lista de contenedores
	@$(DOCKER_COMPOSE) ps

# ====================
# DESARROLLO
# ====================

dev: ## 💻 Levantar servicios de desarrollo (DB + Redis)
	@echo "$(BLUE)Levantando servicios de desarrollo...$(NC)"
	@$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN)✓ Base de datos y Redis listos$(NC)"
	@echo "$(YELLOW)Ahora ejecuta la API y Frontend manualmente:$(NC)"
	@echo "  API:      cd api && python run.py"
	@echo "  Frontend: cd frontend && npm run dev"

dev-full: ## 💻 Levantar servicios de desarrollo con LLM
	@echo "$(BLUE)Levantando servicios de desarrollo (con LLM)...$(NC)"
	@$(DOCKER_COMPOSE_DEV) --profile with-llm up -d

dev-down: ## ⏹️  Detener servicios de desarrollo
	@echo "$(BLUE)Deteniendo servicios de desarrollo...$(NC)"
	@$(DOCKER_COMPOSE_DEV) down

dev-logs: ## 📋 Ver logs de desarrollo
	@$(DOCKER_COMPOSE_DEV) logs -f

# ====================
# BASE DE DATOS
# ====================

db-shell: ## 🐘 Acceder a PostgreSQL shell
	@$(DOCKER_COMPOSE) exec postgres psql -U aquaia_user -d aquaia

db-backup: ## 💾 Crear backup de la base de datos
	@echo "$(BLUE)Creando backup...$(NC)"
	@mkdir -p backups
	@$(DOCKER_COMPOSE) exec -T postgres pg_dump -U aquaia_user aquaia > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup creado en backups/$(NC)"

db-restore: ## 📥 Restaurar backup (usar: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "$(YELLOW)Uso: make db-restore FILE=backup.sql$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restaurando backup $(FILE)...$(NC)"
	@$(DOCKER_COMPOSE) exec -T postgres psql -U aquaia_user -d aquaia < $(FILE)
	@echo "$(GREEN)✓ Backup restaurado$(NC)"

# ====================
# OLLAMA
# ====================

ollama-pull: ## 🤖 Descargar modelo LLM
	@echo "$(BLUE)Descargando modelo phi3.5...$(NC)"
	@$(DOCKER_COMPOSE) exec ollama ollama pull phi3.5:latest
	@echo "$(GREEN)✓ Modelo descargado$(NC)"

ollama-list: ## 📋 Listar modelos instalados
	@$(DOCKER_COMPOSE) exec ollama ollama list

ollama-shell: ## 🤖 Acceder a shell de Ollama
	@$(DOCKER_COMPOSE) exec ollama sh

# ====================
# LIMPIEZA
# ====================

clean: ## 🧹 Detener y eliminar todo (mantiene volúmenes)
	@echo "$(YELLOW)⚠️  Deteniendo y eliminando contenedores...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Limpieza completada (volúmenes preservados)$(NC)"

clean-all: ## 🗑️  Eliminar TODO incluyendo volúmenes (¡PELIGRO!)
	@echo "$(YELLOW)⚠️  ¡ATENCIÓN! Esto eliminará TODOS los datos$(NC)"
	@read -p "¿Estás seguro? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		docker volume rm -f aquaia_postgres_data aquaia_ollama_data aquaia_redis_data aquaia_webui_data 2>/dev/null || true; \
		echo "$(GREEN)✓ Todo eliminado$(NC)"; \
	else \
		echo "$(BLUE)Cancelado$(NC)"; \
	fi

clean-images: ## 🗑️  Eliminar imágenes de AquaAI
	@echo "$(BLUE)Eliminando imágenes...$(NC)"
	@docker rmi -f $$(docker images | grep aquaia | awk '{print $$3}') 2>/dev/null || true
	@echo "$(GREEN)✓ Imágenes eliminadas$(NC)"

# ====================
# MONITORIZACIÓN
# ====================

stats: ## 📊 Uso de recursos en tiempo real
	@docker stats

top: ## 📊 Procesos de los contenedores
	@$(DOCKER_COMPOSE) top

exec-api: ## 🔧 Acceder a shell de la API
	@$(DOCKER_COMPOSE) exec api bash

exec-frontend: ## 🔧 Acceder a shell del Frontend
	@$(DOCKER_COMPOSE) exec frontend sh

# ====================
# TESTING
# ====================

test-api: ## 🧪 Ejecutar tests de la API
	@echo "$(BLUE)Ejecutando tests de la API...$(NC)"
	@$(DOCKER_COMPOSE) exec api pytest -v

test-health: ## 🏥 Test rápido de endpoints
	@echo "$(BLUE)Testeando endpoints...$(NC)"
	@curl -s http://localhost:8000/health && echo "$(GREEN)✓ API OK$(NC)" || echo "$(YELLOW)✗ API Error$(NC)"
	@curl -s http://localhost/ -o /dev/null && echo "$(GREEN)✓ Frontend OK$(NC)" || echo "$(YELLOW)✗ Frontend Error$(NC)"

# ====================
# UTILIDADES
# ====================

env: ## 📝 Crear archivo .env desde ejemplo
	@if [ -f .env ]; then \
		echo "$(YELLOW)⚠️  .env ya existe. No se sobrescribirá.$(NC)"; \
	else \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env creado. Edítalo antes de continuar.$(NC)"; \
	fi

update: ## 🔄 Actualizar y reconstruir
	@echo "$(BLUE)Actualizando AquaAI...$(NC)"
	@git pull
	@$(DOCKER_COMPOSE) build --no-cache
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Actualización completada$(NC)"

info: ## ℹ️  Información del sistema
	@echo "$(BLUE)Información del sistema:$(NC)"
	@echo ""
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@docker compose version
	@echo ""
	@echo "Volúmenes AquaAI:"
	@docker volume ls | grep aquaia || echo "  No hay volúmenes"
	@echo ""
	@echo "Redes AquaAI:"
	@docker network ls | grep aquaia || echo "  No hay redes"

# Por defecto mostrar ayuda
.DEFAULT_GOAL := help
