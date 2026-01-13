"""
Modelos Pydantic para request/response de la API.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime


class EmbalseInfo(BaseModel):
    """Información completa de un embalse."""
    codigo_saih: str = Field(..., description="Código SAIH del embalse")
    ubicacion: str = Field(..., description="Nombre/ubicación del embalse")
    municipio: Optional[str] = Field(None, description="Municipio")
    provincia: Optional[str] = Field(None, description="Provincia")
    comunidad_autonoma: Optional[str] = Field(None, description="Comunidad Autónoma")
    demarcacion: Optional[str] = Field(None, description="Demarcación hidrográfica")
    organismo_gestor: Optional[str] = Field(None, description="Organismo gestor")
    tipo_gestion: Optional[str] = Field(None, description="Tipo de gestión (Estatal/Autonómica)")
    coord_x: Optional[float] = Field(None, description="Coordenada X (UTM ETRS89)")
    coord_y: Optional[float] = Field(None, description="Coordenada Y (UTM ETRS89)")
    nivel_maximo: Optional[float] = Field(None, description="Nivel máximo del embalse (hm³)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo_saih": "E001",
                "ubicacion": "Belesar",
                "municipio": "Portomarín",
                "provincia": "Lugo",
                "comunidad_autonoma": "Galicia",
                "demarcacion": "Demarcación Hidrográfica Galicia-Costa",
                "organismo_gestor": "Augas de Galicia",
                "tipo_gestion": "Autonómica",
                "coord_x": 612345.67,
                "coord_y": 4756789.12,
                "nivel_maximo": 654.0
            }
        }


class SerieHistoricaPunto(BaseModel):
    """Punto de datos históricos."""
    fecha: str = Field(..., description="Fecha en formato ISO (YYYY-MM-DD)")
    nivel: float = Field(..., description="Nivel del embalse (hm³)")
    precipitacion: Optional[float] = Field(None, description="Precipitación (mm)")
    temperatura: Optional[float] = Field(None, description="Temperatura (°C)")
    caudal_promedio: Optional[float] = Field(None, description="Caudal promedio (m³/s)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2024-02-01",
                "nivel": 306.13,
                "precipitacion": 5.2,
                "temperatura": 8.4,
                "caudal_promedio": 14.69
            }
        }


class PrediccionPunto(BaseModel):
    """Punto de predicción con dos escenarios."""
    fecha: str = Field(..., description="Fecha de la predicción")
    pred_hist: float = Field(..., description="Predicción solo con datos históricos")
    pred_aemet_ruido: float = Field(..., description="Predicción con datos AEMET + ruido (operativa)")
    nivel_real: Optional[float] = Field(None, description="Nivel real observado (si disponible)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2024-03-01",
                "pred_hist": 305.5,
                "pred_aemet_ruido": 306.8,
                "nivel_real": 306.5
            }
        }


class PrediccionRequest(BaseModel):
    """Request para generar predicción."""
    fecha_inicio: str = Field(..., description="Fecha de inicio de la predicción (YYYY-MM-DD)")
    horizonte_dias: int = Field(90, ge=1, le=180, description="Horizonte de predicción en días (1-180)")
    
    @field_validator('fecha_inicio')
    @classmethod
    def validate_fecha(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Formato de fecha inválido. Use YYYY-MM-DD')
    
    class Config:
        json_schema_extra = {
            "example": {
                "fecha_inicio": "2024-02-01",
                "horizonte_dias": 90
            }
        }


class PrediccionResponse(BaseModel):
    """Response de predicción completa."""
    codigo_saih: str
    fecha_inicio: str
    horizonte_dias: int
    predicciones: List[PrediccionPunto]
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo_saih": "E001",
                "fecha_inicio": "2024-02-01",
                "horizonte_dias": 90,
                "predicciones": [
                    {
                        "fecha": "2024-02-02",
                        "pred_hist": 305.5,
                        "pred_aemet_ruido": 306.8,
                        "nivel_real": 306.5
                    }
                ]
            }
        }


class RiesgoRequest(BaseModel):
    """Request para análisis de riesgo."""
    fecha_inicio: Optional[str] = Field(None, description="Fecha de inicio (si no se proporciona, usa la última disponible)")
    horizonte_dias: int = Field(90, ge=1, le=180, description="Horizonte de predicción en días")
    umbral_minimo: Optional[float] = Field(None, description="Umbral mínimo de nivel (hm³)")
    umbral_maximo: Optional[float] = Field(None, description="Umbral máximo de nivel (hm³)")
    
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
                "fecha_inicio": "2024-02-01",
                "horizonte_dias": 90,
                "umbral_minimo": 300.0,
                "umbral_maximo": 350.0
            }
        }


class RiesgoEmbalse(BaseModel):
    """Evaluación de riesgo del embalse."""
    codigo_saih: str
    fecha_analisis: str
    horizonte_dias: int
    nivel_minimo_predicho: float = Field(..., description="Nivel mínimo previsto en el horizonte")
    nivel_maximo_predicho: float = Field(..., description="Nivel máximo previsto en el horizonte")
    nivel_medio_predicho: float = Field(..., description="Nivel medio previsto")
    prob_riesgo_bajo: float = Field(..., ge=0.0, le=1.0, description="Probabilidad de nivel bajo (0-1)")
    prob_riesgo_alto: float = Field(..., ge=0.0, le=1.0, description="Probabilidad de nivel alto (0-1)")
    prob_riesgo_medio: float = Field(..., ge=0.0, le=1.0, description="Probabilidad de nivel dentro del rango seguro (0-1)")
    categoria_riesgo: str = Field(..., description="BAJO | MEDIO | ALTO")
    mensaje: str = Field(..., description="Mensaje de recomendación operativa")
    umbral_minimo: float
    umbral_maximo: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo_saih": "E001",
                "fecha_analisis": "2024-02-01",
                "horizonte_dias": 90,
                "nivel_minimo_predicho": 302.5,
                "nivel_maximo_predicho": 315.8,
                "nivel_medio_predicho": 308.2,
                "prob_riesgo_bajo": 0.15,
                "prob_riesgo_alto": 0.05,
                "prob_riesgo_medio": 0.80,
                "categoria_riesgo": "BAJO",
                "mensaje": "Niveles estables dentro del rango seguro. Situación favorable.",
                "umbral_minimo": 300.0,
                "umbral_maximo": 350.0
            }
        }


class EmbalseResumen(BaseModel):
    """Resumen estadístico de un embalse."""
    codigo_saih: str
    ultimo_nivel: float = Field(..., description="Último nivel registrado")
    fecha_ultimo_registro: str = Field(..., description="Fecha del último registro")
    nivel_medio_anual: Optional[float] = Field(None, description="Nivel medio en el último año")
    nivel_min_anual: Optional[float] = Field(None, description="Nivel mínimo en el último año")
    nivel_max_anual: Optional[float] = Field(None, description="Nivel máximo en el último año")
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo_saih": "E001",
                "ultimo_nivel": 308.5,
                "fecha_ultimo_registro": "2024-12-14",
                "nivel_medio_anual": 306.2,
                "nivel_min_anual": 295.3,
                "nivel_max_anual": 318.7
            }
        }


class PrediccionLoteRequest(BaseModel):
    """Request para predicciones de múltiples embalses."""
    codigos_saih: List[str] = Field(..., description="Lista de códigos SAIH")
    fecha_inicio: str = Field(..., description="Fecha de inicio común")
    horizonte_dias: int = Field(90, ge=1, le=180, description="Horizonte común")
    
    @field_validator('fecha_inicio')
    @classmethod
    def validate_fecha(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Formato de fecha inválido. Use YYYY-MM-DD')
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigos_saih": ["E001", "E002", "E003"],
                "fecha_inicio": "2024-02-01",
                "horizonte_dias": 90
            }
        }


class HealthCheck(BaseModel):
    """Estado de salud de la API."""
    status: str
    version: str
    model_loaded: bool
    scalers_loaded: bool
    data_loaded: bool
    num_embalses: int

class Demarcacion(BaseModel):
    """Información de una demarcación hidrográfica."""
    id: str = Field(..., description="Código oficial de la demarcación (ej: ES090)")
    nombre: str = Field(..., description="Nombre de la demarcación")
    organismo_gestor: str = Field(..., description="Organismo responsable")
    tipo_gestion: str = Field(..., description="Tipo de gestión (Estatal/Autonómica)")
    comunidades: List[str] = Field(..., description="Comunidades autónomas que atraviesa")
    num_embalses: int = Field(..., description="Número de embalses en la demarcación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "ES090",
                "nombre": "Demarcación Hidrográfica Galicia-Costa",
                "organismo_gestor": "Augas de Galicia",
                "tipo_gestion": "Autonómica",
                "comunidades": ["Galicia"],
                "num_embalses": 15
            }
        }


class OrganismoGestor(BaseModel):
    """Información de un organismo gestor."""
    id: int = Field(..., description="ID del organismo")
    nombre: str = Field(..., description="Nombre del organismo")
    tipo_gestion: str = Field(..., description="Tipo de gestión (Estatal/Autonómica)")
    num_demarcaciones: int = Field(..., description="Número de demarcaciones gestionadas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nombre": "Confederación Hidrográfica del Miño-Sil",
                "tipo_gestion": "Estatal",
                "num_demarcaciones": 1
            }
        }


class Geografia(BaseModel):
    """Información geográfica (CCAA, provincia o municipio)."""
    id: int = Field(..., description="ID de la entidad")
    nombre: str = Field(..., description="Nombre de la entidad")
    tipo: str = Field(..., description="Tipo: 'ccaa', 'provincia' o 'municipio'")
    padre: Optional[str] = Field(None, description="Nombre de la entidad padre")
    num_embalses: int = Field(0, description="Número de embalses en esta ubicación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 15,
                "nombre": "Galicia",
                "tipo": "ccaa",
                "padre": None,
                "num_embalses": 45
            }
        }


class EstadisticasRegion(BaseModel):
    """Estadísticas agregadas de una región."""
    region_nombre: str = Field(..., description="Nombre de la región")
    region_tipo: str = Field(..., description="Tipo de región (ccaa/provincia/demarcacion)")
    num_embalses: int = Field(..., description="Número de embalses")
    nivel_total_actual: float = Field(..., description="Nivel total actual (hm³)")
    capacidad_total: float = Field(..., description="Capacidad total (hm³)")
    porcentaje_llenado: float = Field(..., description="Porcentaje de llenado promedio")
    nivel_promedio: float = Field(..., description="Nivel promedio (hm³)")
    nivel_min: float = Field(..., description="Nivel mínimo (hm³)")
    nivel_max: float = Field(..., description="Nivel máximo (hm³)")
    ultima_actualizacion: str = Field(..., description="Fecha de última actualización")
    
    class Config:
        json_schema_extra = {
            "example": {
                "region_nombre": "Galicia",
                "region_tipo": "ccaa",
                "num_embalses": 45,
                "nivel_total_actual": 12500.5,
                "capacidad_total": 15000.0,
                "porcentaje_llenado": 83.3,
                "nivel_promedio": 277.8,
                "nivel_min": 45.2,
                "nivel_max": 654.0,
                "ultima_actualizacion": "2024-12-14"
            }
        }


class ComparacionEmbalse(BaseModel):
    """Datos de un embalse para comparación."""
    codigo_saih: str
    ubicacion: str
    nivel_actual: float
    nivel_hace_30d: Optional[float] = None
    nivel_hace_90d: Optional[float] = None
    variacion_30d: Optional[float] = None
    variacion_90d: Optional[float] = None
    porcentaje_capacidad: Optional[float] = None
    tendencia: str = Field(..., description="Tendencia: 'subiendo', 'bajando' o 'estable'")


class ComparacionResponse(BaseModel):
    """Respuesta de comparación de múltiples embalses."""
    fecha_consulta: str
    embalses: List[ComparacionEmbalse]
    resumen: dict = Field(..., description="Resumen estadístico de la comparación")