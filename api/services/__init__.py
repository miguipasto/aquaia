"""
Paquete de servicios de la API.
"""
from .prediction import prediction_service
from .risk import risk_service
from .recomendacion import recomendacion_service
from .llm_service import llm_service

__all__ = ['prediction_service', 'risk_service', 'recomendacion_service', 'llm_service']
