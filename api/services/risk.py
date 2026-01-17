"""
Servicio de análisis de riesgo y recomendaciones operativas.
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional

from ..config import settings
from .prediction import prediction_service


class RiskService:
    """Servicio de análisis de riesgo para embalses."""
    
    @staticmethod
    def analizar_riesgo(
        codigo_saih: str,
        fecha_inicio: Optional[str] = None,
        horizonte_dias: int = 90,
        umbral_minimo: Optional[float] = None,
        umbral_maximo: Optional[float] = None
    ) -> Dict:
        """Analiza el riesgo de un embalse basándose en predicciones operativas."""
        from ..data import data_loader
        if umbral_minimo is None:
            umbral_minimo = settings.default_risk_min_threshold
        if umbral_maximo is None:
            umbral_maximo = settings.default_risk_max_threshold
        
        # Si no se proporciona fecha, usar la última disponible menos el horizonte
        if fecha_inicio is None:
            fecha_max = data_loader.get_fecha_maxima(codigo_saih)
            fecha_dt = pd.to_datetime(fecha_max) - pd.Timedelta(days=horizonte_dias)
            fecha_inicio = fecha_dt.strftime('%Y-%m-%d')
        
        # Obtener predicción operativa
        df_pred = prediction_service.predecir_embalse(
            codigo_saih=codigo_saih,
            fecha=fecha_inicio,
            horizonte=horizonte_dias
        )
        
        niveles_pred = df_pred['pred'].values
        
        nivel_min = float(np.min(niveles_pred))
        nivel_max = float(np.max(niveles_pred))
        nivel_medio = float(np.mean(niveles_pred))
        
        n_total = len(niveles_pred)
        n_bajo = np.sum(niveles_pred < umbral_minimo)
        n_alto = np.sum(niveles_pred > umbral_maximo)
        n_medio = n_total - n_bajo - n_alto
        
        prob_bajo = n_bajo / n_total
        prob_alto = n_alto / n_total
        prob_medio = n_medio / n_total
        
        categoria, mensaje = RiskService._clasificar_riesgo(
            prob_bajo=prob_bajo,
            prob_alto=prob_alto,
            prob_medio=prob_medio,
            nivel_medio=nivel_medio,
            nivel_min=nivel_min,
            nivel_max=nivel_max,
            umbral_minimo=umbral_minimo,
            umbral_maximo=umbral_maximo
        )
        
        return {
            'codigo_saih': codigo_saih,
            'fecha_analisis': fecha_inicio,
            'horizonte_dias': horizonte_dias,
            'nivel_minimo_predicho': nivel_min,
            'nivel_maximo_predicho': nivel_max,
            'nivel_medio_predicho': nivel_medio,
            'prob_riesgo_bajo': prob_bajo,
            'prob_riesgo_alto': prob_alto,
            'prob_riesgo_medio': prob_medio,
            'categoria_riesgo': categoria,
            'mensaje': mensaje,
            'umbral_minimo': umbral_minimo,
            'umbral_maximo': umbral_maximo
        }
    
    @staticmethod
    def _clasificar_riesgo(
        prob_bajo: float,
        prob_alto: float,
        prob_medio: float,
        nivel_medio: float,
        nivel_min: float,
        nivel_max: float,
        umbral_minimo: float,
        umbral_maximo: float
    ) -> tuple:
        """
        Clasifica el nivel de riesgo y genera mensaje de recomendación.
        
        Args:
            prob_bajo: Probabilidad de nivel bajo
            prob_alto: Probabilidad de nivel alto
            prob_medio: Probabilidad de nivel medio
            nivel_medio: Nivel medio predicho
            nivel_min: Nivel mínimo predicho
            nivel_max: Nivel máximo predicho
            umbral_minimo: Umbral mínimo
            umbral_maximo: Umbral máximo
            
        Returns:
            Tupla (categoria, mensaje)
        """
        # Definir categoría según probabilidades
        if prob_medio >= 0.80:
            categoria = "BAJO"
            mensaje = (
                f"Niveles estables dentro del rango seguro ({umbral_minimo:.1f} - {umbral_maximo:.1f} hm³). "
                f"Situación favorable. Nivel medio esperado: {nivel_medio:.1f} hm³."
            )
        
        elif prob_bajo > 0.30:
            categoria = "ALTO"
            mensaje = (
                f"ALERTA: Alta probabilidad ({prob_bajo*100:.1f}%) de niveles por debajo del umbral mínimo "
                f"({umbral_minimo:.1f} hm³). Se recomienda aumentar aportes o reducir desembalses. "
                f"Nivel mínimo esperado: {nivel_min:.1f} hm³."
            )
        
        elif prob_alto > 0.30:
            categoria = "ALTO"
            mensaje = (
                f"ALERTA: Alta probabilidad ({prob_alto*100:.1f}%) de niveles por encima del umbral máximo "
                f"({umbral_maximo:.1f} hm³). Se recomienda aumentar desembalses preventivos. "
                f"Nivel máximo esperado: {nivel_max:.1f} hm³."
            )
        
        elif prob_bajo > 0.15 or prob_alto > 0.15:
            categoria = "MEDIO"
            if prob_bajo > prob_alto:
                mensaje = (
                    f"Riesgo moderado de niveles bajos ({prob_bajo*100:.1f}% de probabilidad). "
                    f"Monitorear evolución y considerar ajustes en la gestión. "
                    f"Nivel medio esperado: {nivel_medio:.1f} hm³."
                )
            else:
                mensaje = (
                    f"Riesgo moderado de niveles altos ({prob_alto*100:.1f}% de probabilidad). "
                    f"Monitorear evolución y considerar ajustes en la gestión. "
                    f"Nivel medio esperado: {nivel_medio:.1f} hm³."
                )
        
        else:
            categoria = "BAJO"
            mensaje = (
                f"Niveles mayormente dentro del rango seguro. "
                f"Situación controlada. Nivel medio esperado: {nivel_medio:.1f} hm³."
            )
        
        return categoria, mensaje
    
    @staticmethod
    def recomendacion_rapida(codigo_saih: str) -> Dict:
        """
        Genera una recomendación rápida con parámetros por defecto.
        
        Args:
            codigo_saih: Código del embalse
            
        Returns:
            Diccionario con análisis de riesgo
        """
        return RiskService.analizar_riesgo(
            codigo_saih=codigo_saih,
            fecha_inicio=None,  # Usa fecha automática
            horizonte_dias=settings.default_prediction_horizon,
            umbral_minimo=settings.default_risk_min_threshold,
            umbral_maximo=settings.default_risk_max_threshold
        )


# Instancia global del servicio de riesgo
risk_service = RiskService()
