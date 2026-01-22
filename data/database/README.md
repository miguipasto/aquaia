# Database - PostgreSQL

Base de datos PostgreSQL para almacenamiento de datos de embalses, predicciones y recomendaciones.

## Requisitos

- Docker & Docker Compose

## Configuración

Crear archivo `.env` en base a `.env.template`:

```bash
cp .env.template .env
```

Variables:
- `POSTGRES_DB`: Nombre de la base de datos (por defecto: `aquaia`)
- `POSTGRES_USER`: Usuario (por defecto: `usr_aquaia`)
- `POSTGRES_PASSWORD`: Contraseña
- `POSTGRES_PORT`: Puerto externo (por defecto: `8432`)

## Ejecución

```bash
# Iniciar base de datos
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## Conexión

```bash
psql -h localhost -p 8432 -U usr_aquaia -d aquaia
```

## Esquema de Base de Datos

El esquema incluye las siguientes tablas principales:

- **embalses**: Catálogo de embalses (código, nombre, capacidad, ubicación)
- **datos_historicos**: Series temporales de niveles y variables
- **predicciones**: Predicciones generadas por el modelo
- **recomendaciones**: Recomendaciones operativas con histórico
- **tipos_riesgo**: Catálogo de niveles de riesgo
- **umbrales_embalse**: Umbrales configurables por embalse
- **llm_cache_recomendaciones**: Caché de respuestas LLM
- **informes**: Registro de informes generados

## Migración Inicial

El esquema se carga automáticamente desde `init.sql` en el primer arranque.

Para aplicar migraciones adicionales:

```bash
psql -h localhost -p 8432 -U usr_aquaia -d aquaia -f migration.sql
```

## Backup

```bash
# Exportar
docker exec aquaia_postgres_db pg_dump -U usr_aquaia aquaia > backup.sql

# Importar
docker exec -i aquaia_postgres_db psql -U usr_aquaia aquaia < backup.sql
```
