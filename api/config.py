"""
Configuración de la API de predicción de embalses.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    # Información de la API
    app_name: str = "AquaAI - API de Predicción de Embalses"
    app_version: str = "1.0.0"
    app_description: str = "API REST para predicción de niveles de embalses usando LSTM Seq2Seq con datos meteorológicos AEMET"
    
    # Rutas de archivos del modelo (relativas al directorio de la API)
    base_dir: Path = Path(__file__).parent
    model_path: Path = base_dir / "resources" / "Training_Aemet" / "modelo_embalses_aemet.pth"
    scalers_path: Path = base_dir / "resources" / "Training_Aemet" / "artifacts" / "scalers.npy"
    
    # Nota: Los archivos CSV solo se usan para entrenamiento, no para la API
    # La API obtiene datos desde PostgreSQL
    
    # Parámetros del modelo (se sobrescriben desde el checkpoint)
    lookback: int = 90
    horizon: int = 180
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.2
    features: int = 22
    sigma_forecast: float = 0.05
    
    # Parámetros de predicción por defecto
    default_prediction_horizon: int = 90
    default_risk_min_threshold: float = 300.0
    default_risk_max_threshold: float = 350.0
    
    # Configuración de servidor
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:3001"]
    
    # Base de datos PostgreSQL (desde .env)
    db_user: str = "usraquaai"
    db_pass: str = "app_password"
    db_host: str = "localhost"
    db_port: int = 9432
    db_name: str = "aquaai"
    
    @property
    def database_url(self) -> str:
        """Construye la URL de conexión a PostgreSQL."""
        return f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def async_database_url(self) -> str:
        """Construye la URL de conexión asíncrona a PostgreSQL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


settings = Settings()
