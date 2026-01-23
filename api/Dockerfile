# Dockerfile para AquaAI API
FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libfontconfig1 \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Crear estructura de directorios
WORKDIR /app
RUN mkdir -p /app/api

# Copiar archivos de dependencias
COPY requirements.txt /app/api/
COPY requirements.docker.txt /app/api/

# Filtrar paquetes del sistema y usar requirements.docker.txt si existe
WORKDIR /app/api
RUN pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.docker.txt ]; then \
        pip install --no-cache-dir -r requirements.docker.txt; \
    else \
        grep -v "dbus-python\|dnf\|libcomps\|libdnf\|rpm\|systemd-python\|git-filter-repo\|annotated-doc" requirements.txt > requirements_filtered.txt && \
        pip install --no-cache-dir -r requirements_filtered.txt; \
    fi

# Copiar todo el código de la aplicación
COPY . /app/api/

# Crear directorios necesarios
RUN mkdir -p /app/api/informes_generados

# Volver al directorio raíz
WORKDIR /app

# Configurar PYTHONPATH para que encuentre el módulo api
ENV PYTHONPATH=/app

# Exponer el puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Comando para ejecutar la aplicación
CMD ["python", "api/run.py"]

# Exponer el puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Comando para ejecutar la aplicación
CMD ["python", "-m", "api.run"]
