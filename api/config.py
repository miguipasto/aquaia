"""
Configuración de la API de predicción de embalses.
"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    app_name: str = Field(
        default="AquaAI - API de Predicción de Embalses",
        description="Nombre de la aplicación"
    )
    app_version: str = Field(default="1.0.0", description="Versión de la API")
    app_description: str = Field(
        default="API REST para predicción de niveles de embalses usando LSTM Seq2Seq con datos meteorológicos AEMET",
        description="Descripción de la API"
    )
    host: str = Field(default="0.0.0.0", description="Host del servidor")
    port: int = Field(default=8000, ge=1, le=65535, description="Puerto del servidor")
    debug: bool = Field(default=False, description="Modo debug")
    reload: bool = Field(default=False, description="Auto-reload en cambios")
    log_level: str = Field(default="INFO", description="Nivel de logging")
    
    db_user: str = Field(..., description="Usuario de PostgreSQL")
    db_password: str = Field(..., description="Contraseña de PostgreSQL")
    db_host: str = Field(default="localhost", description="Host de PostgreSQL")
    db_port: int = Field(default=9432, ge=1, le=65535, description="Puerto de PostgreSQL")
    db_name: str = Field(..., description="Nombre de la base de datos")
    db_pool_min: int = Field(default=2, ge=1, description="Mínimo de conexiones en pool")
    db_pool_max: int = Field(default=10, ge=1, le=100, description="Máximo de conexiones en pool")
    db_connect_timeout: int = Field(default=30, ge=5, description="Timeout de conexión (segundos)")
    
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=32,
        description="Clave secreta para JWT"
    )
    algorithm: str = Field(default="HS256", description="Algoritmo de encriptación")
    access_token_expire_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Duración del token (minutos)"
    )
    api_keys: str = Field(default="", description="API keys permitidas (separadas por coma)")
    
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:8080",
        description="Orígenes permitidos para CORS (separados por coma)"
    )
    cors_allow_credentials: bool = Field(default=True, description="Permitir credenciales CORS")
    
    base_dir: Path = Path(__file__).parent
    model_path: str = Field(
        default="resources/Training_Aemet/modelo_embalses_aemet.pth",
        description="Ruta del modelo PyTorch"
    )
    scalers_path: str = Field(
        default="resources/Training_Aemet/artifacts/scalers.npy",
        description="Ruta de los scalers"
    )
    metrics_path: str = Field(
        default="resources/Training_Aemet/artifacts/metrics.json",
        description="Ruta de las métricas"
    )
    
    # Parámetros del modelo (se sobrescriben desde el checkpoint)
    model_lookback: int = Field(default=90, ge=1, description="Días de lookback")
    model_horizon: int = Field(default=180, ge=1, description="Horizonte de predicción")
    model_hidden_size: int = Field(default=128, ge=16, description="Tamaño de capa oculta")
    model_num_layers: int = Field(default=2, ge=1, description="Número de capas LSTM")
    model_dropout: float = Field(default=0.2, ge=0.0, le=0.9, description="Dropout")
    model_features: int = Field(default=22, ge=1, description="Número de features")
    model_sigma_forecast: float = Field(default=0.05, ge=0.0, description="Sigma del forecast")
    
    default_prediction_horizon: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Horizonte de predicción por defecto (días)"
    )
    default_risk_min_threshold: float = Field(
        default=300.0,
        ge=0.0,
        description="Umbral mínimo de riesgo (metros)"
    )
    default_risk_max_threshold: float = Field(
        default=350.0,
        ge=0.0,
        description="Umbral máximo de riesgo (metros)"
    )
    
    enable_cache: bool = Field(default=True, description="Habilitar caché")
    cache_ttl: int = Field(default=3600, ge=10, description="TTL del caché (segundos)")
    cache_max_size: int = Field(default=1000, ge=10, description="Tamaño máximo del caché")
    
    # Ollama para recomendaciones inteligentes
    ollama_url: str = Field(default="http://localhost:11434", description="URL de la API de Ollama")
    ollama_model: str = Field(default="phi3.5:latest", description="Modelo LLM a usar")
    enable_llm_recomendaciones: bool = Field(default=False, description="Usar LLM para generar textos de recomendación")
    ollama_timeout: int = Field(default=120, ge=10, le=300, description="Timeout para llamadas a Ollama (segundos)")
    ollama_max_retries: int = Field(default=2, ge=0, le=5, description="Reintentos en caso de fallo")
    ollama_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperatura del modelo")
    ollama_top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    llm_cache_ttl: int = Field(default=86400, ge=3600, description="TTL del caché de respuestas LLM (segundos)")
    llm_cache_enabled: bool = Field(default=True, description="Habilitar caché de respuestas LLM")
    
    enable_rate_limit: bool = Field(default=True, description="Habilitar rate limiting")
    rate_limit_requests: int = Field(
        default=500,
        ge=1,
        description="Peticiones permitidas por ventana"
    )
    rate_limit_window: int = Field(default=60, ge=1, description="Ventana de tiempo (segundos)")
    
    aemet_api_key: str = Field(default="", description="API Key de AEMET")
    aemet_api_url: str = Field(
        default="https://opendata.aemet.es/opendata/api",
        description="URL base de la API de AEMET"
    )
    
    enable_metrics: bool = Field(default=True, description="Habilitar métricas")
    enable_tracing: bool = Field(default=False, description="Habilitar trazas")
    sentry_dsn: str = Field(default="", description="Sentry DSN")
    
    backup_dir: str = Field(default="./backups", description="Directorio de backups")
    enable_auto_backup: bool = Field(default=False, description="Habilitar backups automáticos")
    backup_frequency_hours: int = Field(
        default=24,
        ge=1,
        description="Frecuencia de backup (horas)"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Valida que el nivel de logging sea válido."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level debe ser uno de: {", ".join(valid_levels)}')
        return v.upper()
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Valida que la secret key sea segura en producción."""
        if 'dev' in v or 'change' in v or 'your-secret' in v:
            import warnings
            warnings.warn(
                "ADVERTENCIA: Usando secret_key por defecto. "
                "Genera una clave segura para producción con: openssl rand -hex 32"
            )
        return v
    
    @property
    def database_url(self) -> str:
        """Construye la URL de conexión a PostgreSQL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def async_database_url(self) -> str:
        """Construye la URL de conexión asíncrona a PostgreSQL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte CORS origins de string a lista."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
    
    @property
    def api_keys_list(self) -> List[str]:
        """Convierte API keys de string a lista."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(',') if key.strip()]
    
    @property
    def model_path_absolute(self) -> Path:
        """Ruta absoluta del modelo."""
        path = Path(self.model_path)
        if path.is_absolute():
            return path
        return self.base_dir / path
    
    @property
    def scalers_path_absolute(self) -> Path:
        """Ruta absoluta de los scalers."""
        path = Path(self.scalers_path)
        if path.is_absolute():
            return path
        return self.base_dir / path
    
    @property
    def metrics_path_absolute(self) -> Path:
        """Ruta absoluta de las métricas."""
        path = Path(self.metrics_path)
        if path.is_absolute():
            return path
        return self.base_dir / path
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()
