"""
Modelos Pydantic adicionales para el sistema de recomendaciones operativas.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# =================================================================================
# ENUMS Y CONSTANTES
# =================================================================================

class NivelRiesgo(str, Enum):
    """Niveles de riesgo para embalses."""
    BAJO = "BAJO"
    MODERADO = "MODERADO"
    ALTO = "ALTO"
    SEQUIA = "SEQUIA"


class TendenciaNivel(str, Enum):
    """Tendencia del nivel del embalse."""
    SUBIENDO = "subiendo"
    BAJANDO = "bajando"
    ESTABLE = "estable"


# =================================================================================
# MODELOS DE CONFIGURACIÓN
# =================================================================================

class RecomendacionConfigCreate(BaseModel):
    """Modelo para crear configuración de recomendaciones."""
    codigo_saih: Optional[str] = Field(None, description="Código SAIH del embalse (NULL para config global)")
    nombre: str = Field(..., description="Nombre descriptivo de la configuración")
    descripcion: Optional[str] = Field(None, description="Descripción detallada")
    umbral_alto_relativo: float = Field(0.95, ge=0.0, le=1.0, description="Umbral para riesgo alto (% de nivel_maximo)")
    umbral_moderado_relativo: float = Field(0.80, ge=0.0, le=1.0, description="Umbral para riesgo moderado")
    umbral_minimo_relativo: float = Field(0.30, ge=0.0, le=1.0, description="Umbral mínimo para sequía")
    horizonte_dias: int = Field(7, ge=1, le=180, description="Horizonte de predicción en días")
    k_sigma: float = Field(2.0, ge=0.0, le=5.0, description="Multiplicador para intervalo de confianza")
    prob_umbral_moderado: float = Field(0.30, ge=0.0, le=1.0, description="Probabilidad umbral para alerta moderada")
    prob_umbral_alto: float = Field(0.50, ge=0.0, le=1.0, description="Probabilidad umbral para alerta alta")
    activo: bool = Field(True, description="Si la configuración está activa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo_saih": "E001",
                "nombre": "Config Embalse Belesar",
                "descripcion": "Configuración específica para Belesar con umbrales ajustados",
                "umbral_alto_relativo": 0.93,
                "umbral_moderado_relativo": 0.78,
                "umbral_minimo_relativo": 0.25,
                "horizonte_dias": 14,
                "k_sigma": 2.5,
                "activo": True
            }
        }


class RecomendacionConfigResponse(RecomendacionConfigCreate):
    """Modelo de respuesta con configuración completa."""
    id: int
    fecha_creacion: datetime
    fecha_modificacion: datetime
    
    class Config:
        from_attributes = True


# =================================================================================
# MODELOS DE RECOMENDACIONES OPERATIVAS
# =================================================================================

class RecomendacionRequest(BaseModel):
    """Request para generar recomendación operativa."""
    fecha_inicio: Optional[str] = Field(None, description="Fecha de inicio (YYYY-MM-DD). Si es None, usa hoy")
    horizonte_dias: Optional[int] = Field(None, ge=1, le=180, description="Horizonte de predicción. Si es None, usa config del embalse")
    forzar_regeneracion: bool = Field(False, description="Forzar regeneración aunque exista una reciente")
    
    @field_validator('fecha_inicio')
    @classmethod
    def validate_fecha(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Formato de fecha inválido. Use YYYY-MM-DD')
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha_inicio": "2024-12-14",
                "horizonte_dias": 7,
                "forzar_regeneracion": False
            }
        }


class RecomendacionOperativaDTO(BaseModel):
    """DTO completo de recomendación operativa."""
    id: Optional[int] = None
    codigo_saih: str = Field(..., description="Código SAIH del embalse")
    ubicacion: Optional[str] = Field(None, description="Nombre del embalse")
    
    # Temporalidad
    fecha_generacion: datetime = Field(..., description="Fecha y hora de generación")
    fecha_inicio: date = Field(..., description="Fecha de inicio de la predicción")
    horizonte_dias: int = Field(..., description="Horizonte de predicción en días")
    
    # Clasificación
    nivel_riesgo: NivelRiesgo = Field(..., description="Nivel de riesgo calculado")
    nivel_severidad: int = Field(..., ge=1, le=4, description="Severidad numérica (1-4)")
    color_hex: Optional[str] = Field(None, description="Color para visualización")
    
    # Niveles
    nivel_actual: Optional[float] = Field(None, description="Nivel actual del embalse (msnm)")
    nivel_predicho_min: Optional[float] = Field(None, description="Nivel predicho mínimo (msnm)")
    nivel_predicho_max: Optional[float] = Field(None, description="Nivel predicho máximo (msnm)")
    nivel_predicho_medio: Optional[float] = Field(None, description="Nivel predicho medio (msnm)")
    nivel_maximo: Optional[float] = Field(None, description="Capacidad máxima del embalse (msnm)")
    
    # Métricas
    mae_historico: Optional[float] = Field(None, description="MAE histórico del modelo para este embalse")
    rmse_historico: Optional[float] = Field(None, description="RMSE histórico del modelo")
    
    # Probabilidades y timing
    probabilidad_superar_umbral: Optional[float] = Field(None, ge=0.0, le=1.0, description="Prob. de superar umbral crítico")
    dias_hasta_umbral: Optional[int] = Field(None, description="Días hasta alcanzar umbral crítico")
    
    # Textos de recomendación
    motivo: str = Field(..., description="Explicación del riesgo asignado")
    accion_recomendada: str = Field(..., description="Acciones operativas recomendadas")
    
    # Metadata
    config_id: Optional[int] = Field(None, description="ID de configuración utilizada")
    version_modelo: Optional[str] = Field(None, description="Versión del modelo de predicción")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123,
                "codigo_saih": "E001",
                "ubicacion": "Belesar",
                "fecha_generacion": "2024-12-14T10:30:00",
                "fecha_inicio": "2024-12-14",
                "horizonte_dias": 7,
                "nivel_riesgo": "MODERADO",
                "nivel_severidad": 2,
                "color_hex": "#FFC107",
                "nivel_actual": 520.5,
                "nivel_predicho_min": 515.2,
                "nivel_predicho_max": 542.8,
                "nivel_predicho_medio": 528.3,
                "nivel_maximo": 654.0,
                "mae_historico": 8.5,
                "rmse_historico": 12.3,
                "probabilidad_superar_umbral": 0.35,
                "dias_hasta_umbral": 5,
                "motivo": "El nivel predicho se situará en 81% de capacidad (528.3 hm³) dentro de 7 días. Tendencia: subiendo. Incertidumbre: ±8.5 hm³.",
                "accion_recomendada": "Incrementar frecuencia de monitoreo a cada 12 horas. Evaluar posibilidad de desembalses graduales de 15.0 hm³ para mantener margen de seguridad.",
                "config_id": 1,
                "version_modelo": "1.0.0"
            }
        }


class RecomendacionResumen(BaseModel):
    """Resumen simplificado de recomendación para listados."""
    codigo_saih: str
    ubicacion: str
    nivel_riesgo: NivelRiesgo
    nivel_severidad: int
    color_hex: str
    nivel_actual: Optional[float]
    nivel_predicho_medio: Optional[float]
    porcentaje_llenado: Optional[float] = Field(None, description="% de llenado actual")
    fecha_generacion: datetime
    accion_recomendada: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo_saih": "E001",
                "ubicacion": "Belesar",
                "nivel_riesgo": "MODERADO",
                "nivel_severidad": 2,
                "color_hex": "#FFC107",
                "nivel_actual": 520.5,
                "nivel_predicho_medio": 528.3,
                "porcentaje_llenado": 79.6,
                "fecha_generacion": "2024-12-14T10:30:00",
                "accion_recomendada": "Incrementar frecuencia de monitoreo..."
            }
        }


# =================================================================================
# MODELOS AGREGADOS POR REGIÓN
# =================================================================================

class RiesgoDemarcacionDTO(BaseModel):
    """Resumen de riesgos agregados por demarcación."""
    id_demarcacion: str = Field(..., description="Código de demarcación (ej: ES090)")
    demarcacion: str = Field(..., description="Nombre de la demarcación")
    organismo_gestor: str = Field(..., description="Organismo responsable")
    total_embalses: int = Field(..., description="Total de embalses en la demarcación")
    embalses_riesgo_alto: int = Field(0, description="Embalses con riesgo ALTO")
    embalses_riesgo_moderado: int = Field(0, description="Embalses con riesgo MODERADO")
    embalses_riesgo_sequia: int = Field(0, description="Embalses con riesgo SEQUÍA")
    embalses_riesgo_bajo: int = Field(0, description="Embalses con riesgo BAJO")
    porcentaje_criticos: float = Field(0.0, description="% de embalses en situación crítica (ALTO o SEQUÍA)")
    ultima_actualizacion: Optional[datetime] = Field(None, description="Última actualización de recomendaciones")
    embalses_criticos: List[RecomendacionResumen] = Field(default_factory=list, description="Detalle de embalses críticos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_demarcacion": "ES090",
                "demarcacion": "Galicia-Costa",
                "organismo_gestor": "Augas de Galicia",
                "total_embalses": 15,
                "embalses_riesgo_alto": 2,
                "embalses_riesgo_moderado": 5,
                "embalses_riesgo_sequia": 0,
                "embalses_riesgo_bajo": 8,
                "porcentaje_criticos": 13.33,
                "ultima_actualizacion": "2024-12-14T10:30:00",
                "embalses_criticos": []
            }
        }


class RiesgoOrganismoDTO(BaseModel):
    """Resumen de riesgos agregados por organismo gestor."""
    id_organismo: int = Field(..., description="ID del organismo")
    organismo: str = Field(..., description="Nombre del organismo")
    tipo_gestion: str = Field(..., description="Estatal o Autonómica")
    num_demarcaciones: int = Field(..., description="Número de demarcaciones gestionadas")
    total_embalses: int = Field(..., description="Total de embalses bajo gestión")
    embalses_riesgo_alto: int = Field(0, description="Embalses con riesgo ALTO")
    embalses_riesgo_moderado: int = Field(0, description="Embalses con riesgo MODERADO")
    embalses_riesgo_sequia: int = Field(0, description="Embalses con riesgo SEQUÍA")
    embalses_riesgo_bajo: int = Field(0, description="Embalses con riesgo BAJO")
    porcentaje_criticos: float = Field(0.0, description="% de embalses críticos")
    ultima_actualizacion: Optional[datetime] = Field(None, description="Última actualización")
    demarcaciones: List[RiesgoDemarcacionDTO] = Field(default_factory=list, description="Detalle por demarcaciones")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_organismo": 1,
                "organismo": "Augas de Galicia",
                "tipo_gestion": "Autonómica",
                "num_demarcaciones": 1,
                "total_embalses": 15,
                "embalses_riesgo_alto": 2,
                "embalses_riesgo_moderado": 5,
                "embalses_riesgo_sequia": 0,
                "embalses_riesgo_bajo": 8,
                "porcentaje_criticos": 13.33,
                "ultima_actualizacion": "2024-12-14T10:30:00",
                "demarcaciones": []
            }
        }


class ListaRecomendacionesResponse(BaseModel):
    """Respuesta para listado de recomendaciones."""
    total: int = Field(..., description="Total de recomendaciones")
    recomendaciones: List[RecomendacionOperativaDTO] = Field(..., description="Lista de recomendaciones")
    filtros_aplicados: dict = Field(default_factory=dict, description="Filtros aplicados en la consulta")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 15,
                "recomendaciones": [],
                "filtros_aplicados": {
                    "nivel_riesgo": "ALTO",
                    "fecha_inicio": "2024-12-14"
                }
            }
        }


class EstadisticasRecomendaciones(BaseModel):
    """Estadísticas generales del sistema de recomendaciones."""
    total_embalses_monitorizados: int
    embalses_con_recomendaciones: int
    recomendaciones_totales_generadas: int
    ultima_generacion: Optional[datetime]
    distribucion_riesgos: dict = Field(..., description="Distribución de niveles de riesgo")
    promedio_dias_horizonte: float
    promedio_mae: Optional[float]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_embalses_monitorizados": 50,
                "embalses_con_recomendaciones": 45,
                "recomendaciones_totales_generadas": 1523,
                "ultima_generacion": "2024-12-14T10:30:00",
                "distribucion_riesgos": {
                    "BAJO": 30,
                    "MODERADO": 12,
                    "ALTO": 2,
                    "SEQUIA": 1
                },
                "promedio_dias_horizonte": 8.5,
                "promedio_mae": 9.3
            }
        }
