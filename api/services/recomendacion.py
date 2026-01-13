"""
Servicio de generación de recomendaciones operativas basadas en predicciones.

Este módulo implementa la lógica de negocio para:
- Evaluar riesgos de embalses basándose en predicciones del modelo LSTM
- Clasificar niveles de riesgo (BAJO, MODERADO, ALTO, SEQUÍA)
- Generar recomendaciones operativas automáticas
- Calcular probabilidades y métricas de riesgo
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
import numpy as np
import pandas as pd

from ..config import settings
from ..data import data_loader, db_connection
from ..models_recomendaciones import (
    NivelRiesgo,
    TendenciaNivel,
    RecomendacionOperativaDTO,
    RecomendacionResumen,
    RiesgoDemarcacionDTO,
    RiesgoOrganismoDTO,
    RecomendacionConfigResponse,
    EstadisticasRecomendaciones
)

logger = logging.getLogger(__name__)


class RecomendacionService:
    """Servicio para generación y gestión de recomendaciones operativas."""
    
    def __init__(self):
        """Inicializa el servicio de recomendaciones."""
        # Importación tardía para evitar importación circular
        from ..services import prediction_service
        self.prediction_service = prediction_service
        self.db = db_connection
    
    # =========================================================================
    # FUNCIONES DE CONFIGURACIÓN
    # =========================================================================
    
    def obtener_configuracion_embalse(self, codigo_saih: str) -> Dict:
        """
        Obtiene la configuración efectiva para un embalse.
        Usa configuración específica si existe, o global si no.
        
        Args:
            codigo_saih: Código SAIH del embalse
            
        Returns:
            Diccionario con parámetros de configuración
        """
        query = """
            SELECT * FROM obtener_config_embalse(%s)
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (codigo_saih,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            else:
                # Configuración por defecto si no existe en BD
                logger.warning(f"No se encontró configuración para {codigo_saih}, usando valores por defecto")
                return {
                    'id': None,
                    'umbral_alto_relativo': 0.95,
                    'umbral_moderado_relativo': 0.80,
                    'umbral_minimo_relativo': 0.30,
                    'horizonte_dias': 7,
                    'k_sigma': 2.0,
                    'prob_umbral_moderado': 0.30,
                    'prob_umbral_alto': 0.50
                }
    
    # =========================================================================
    # FUNCIONES DE EVALUACIÓN DE RIESGO
    # =========================================================================
    
    def evaluar_riesgo_embalse(
        self,
        codigo_saih: str,
        fecha_inicio: Optional[date] = None,
        horizonte: Optional[int] = None,
        forzar_regeneracion: bool = False
    ) -> RecomendacionOperativaDTO:
        """
        Evalúa el riesgo de un embalse y genera recomendación operativa.
        
        Proceso:
        1. Verifica si existe recomendación reciente (< 6 horas)
        2. Obtiene configuración específica del embalse
        3. Genera predicción operativa (AEMET + ruido)
        4. Calcula niveles esperados con intervalo de confianza
        5. Clasifica el riesgo según umbrales
        6. Genera textos de motivo y acción
        7. Persiste en BD y retorna DTO
        
        Args:
            codigo_saih: Código SAIH del embalse
            fecha_inicio: Fecha de inicio de predicción (None = hoy)
            horizonte: Horizonte en días (None = usar config)
            forzar_regeneracion: Si True, regenera aunque exista una reciente
            
        Returns:
            RecomendacionOperativaDTO con la evaluación completa
        """
        # 1. Verificar si existe recomendación reciente
        if not forzar_regeneracion:
            recomendacion_existente = self._obtener_recomendacion_reciente(
                codigo_saih, fecha_inicio, horizonte
            )
            if recomendacion_existente:
                logger.info(f"Usando recomendación existente para {codigo_saih}")
                return recomendacion_existente
        
        # 2. Obtener configuración
        config = self.obtener_configuracion_embalse(codigo_saih)
        if horizonte is None:
            horizonte = config['horizonte_dias']
        
        # 3. Obtener información del embalse
        info_embalse = self._obtener_info_embalse(codigo_saih)
        if not info_embalse:
            raise ValueError(f"No se encontró información para embalse {codigo_saih}")
        
        nivel_maximo = info_embalse.get('nivel_maximo')
        if not nivel_maximo:
            raise ValueError(f"Embalse {codigo_saih} no tiene nivel_maximo definido")
        
        # Convertir a float si es Decimal (desde PostgreSQL)
        nivel_maximo = float(nivel_maximo)
        
        # 4. Generar predicción operativa
        if fecha_inicio is None:
            fecha_inicio = date.today()
        elif isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        
        try:
            # Usar el método predecir_embalse del servicio de predicción
            df_prediccion = self.prediction_service.predecir_embalse(
                codigo_saih=codigo_saih,
                fecha=fecha_inicio.strftime('%Y-%m-%d'),
                horizonte=horizonte
            )
            
            # Convertir DataFrame a formato de diccionario compatible
            prediccion = {
                'codigo_saih': codigo_saih,
                'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'horizonte_dias': horizonte,
                'predicciones': []
            }
            
            for _, row in df_prediccion.iterrows():
                punto = {
                    'fecha': row['fecha'].strftime('%Y-%m-%d') if hasattr(row['fecha'], 'strftime') else str(row['fecha']),
                    'pred_hist': float(row['pred_hist']) if pd.notna(row['pred_hist']) else None,
                    'pred_aemet_ruido': float(row['pred_aemet_ruido']) if pd.notna(row['pred_aemet_ruido']) else None,
                    'nivel_real': float(row['nivel_real']) if pd.notna(row['nivel_real']) else None
                }
                prediccion['predicciones'].append(punto)
                
        except Exception as e:
            logger.error(f"Error generando predicción para {codigo_saih}: {e}")
            raise
        
        # 5. Calcular métricas y niveles
        metricas = self._calcular_metricas_prediccion(prediccion, config, nivel_maximo)
        
        # 6. Clasificar riesgo
        clasificacion = self._clasificar_riesgo(metricas, config, nivel_maximo)
        
        # 7. Generar textos de recomendación
        textos = self._generar_textos_recomendacion(
            clasificacion,
            metricas,
            info_embalse,
            horizonte
        )
        
        # 8. Crear DTO de recomendación
        recomendacion_dto = RecomendacionOperativaDTO(
            codigo_saih=codigo_saih,
            ubicacion=info_embalse.get('ubicacion'),
            fecha_generacion=datetime.now(),
            fecha_inicio=fecha_inicio,
            horizonte_dias=horizonte,
            nivel_riesgo=clasificacion['nivel_riesgo'],
            nivel_severidad=clasificacion['nivel_severidad'],
            color_hex=clasificacion['color_hex'],
            nivel_actual=metricas['nivel_actual'],
            nivel_predicho_min=metricas['nivel_min'],
            nivel_predicho_max=metricas['nivel_max'],
            nivel_predicho_medio=metricas['nivel_medio'],
            nivel_maximo=nivel_maximo,
            mae_historico=metricas.get('mae'),
            rmse_historico=metricas.get('rmse'),
            probabilidad_superar_umbral=clasificacion.get('probabilidad_superar'),
            dias_hasta_umbral=clasificacion.get('dias_hasta_umbral'),
            motivo=textos['motivo'],
            accion_recomendada=textos['accion'],
            config_id=config.get('id'),
            version_modelo=settings.app_version
        )
        
        # 9. Persistir en base de datos
        recomendacion_id = self._persistir_recomendacion(recomendacion_dto)
        recomendacion_dto.id = recomendacion_id
        
        logger.info(f"Recomendación generada para {codigo_saih}: {clasificacion['nivel_riesgo']}")
        
        return recomendacion_dto
    
    def _obtener_recomendacion_reciente(
        self,
        codigo_saih: str,
        fecha_inicio: Optional[date],
        horizonte: Optional[int]
    ) -> Optional[RecomendacionOperativaDTO]:
        """
        Busca una recomendación generada recientemente (últimas 6 horas).
        """
        query = """
            SELECT 
                r.*,
                e.ubicacion,
                e.nivel_maximo,
                tr.nombre AS nombre_riesgo,
                tr.color_hex
            FROM recomendacion_operativa r
            JOIN estacion_saih e ON r.codigo_saih = e.codigo_saih
            JOIN tipo_riesgo tr ON r.nivel_riesgo = tr.codigo
            WHERE r.codigo_saih = %s
              AND r.fecha_generacion > NOW() - INTERVAL '6 hours'
            ORDER BY r.fecha_generacion DESC
            LIMIT 1
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (codigo_saih,))
            result = cursor.fetchone()
            
            if result:
                return self._row_to_dto(result)
        
        return None
    
    def _obtener_info_embalse(self, codigo_saih: str) -> Optional[Dict]:
        """Obtiene información básica del embalse desde la BD."""
        query = """
            SELECT 
                e.codigo_saih,
                e.ubicacion,
                e.nivel_maximo,
                e.id_demarcacion,
                d.nombre AS demarcacion
            FROM estacion_saih e
            LEFT JOIN demarcacion d ON e.id_demarcacion = d.id
            WHERE e.codigo_saih = %s
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (codigo_saih,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def _calcular_metricas_prediccion(
        self,
        prediccion: Dict,
        config: Dict,
        nivel_maximo: float
    ) -> Dict:
        """
        Calcula métricas estadísticas de la predicción.
        
        Args:
            prediccion: Diccionario con predicciones del servicio
            config: Configuración de umbrales
            nivel_maximo: Capacidad máxima del embalse
            
        Returns:
            Diccionario con métricas calculadas
        """
        # Extraer serie de predicción operativa (AEMET + ruido)
        pred_serie = []
        nivel_actual = None
        
        for punto in prediccion.get('predicciones', []):
            if 'pred_aemet_ruido' in punto:
                pred_serie.append(punto['pred_aemet_ruido'])
            if nivel_actual is None and 'nivel_real' in punto and punto['nivel_real']:
                nivel_actual = punto['nivel_real']
        
        if not pred_serie:
            raise ValueError("No hay predicciones operativas disponibles")
        
        pred_array = np.array(pred_serie)
        
        # Si no tenemos nivel actual, usar el primero de la predicción
        if nivel_actual is None:
            # Intentar obtener último nivel de BD
            nivel_actual = self._obtener_ultimo_nivel(prediccion['codigo_saih'])
            if nivel_actual is None:
                nivel_actual = pred_serie[0]
        
        # Calcular estadísticas básicas
        nivel_min = float(np.min(pred_array))
        nivel_max = float(np.max(pred_array))
        nivel_medio = float(np.mean(pred_array))
        
        # Obtener MAE/RMSE si están disponibles
        mae = prediccion.get('mae_historico')
        rmse = prediccion.get('rmse_historico')
        
        # Calcular nivel esperado con incertidumbre
        k_sigma = config.get('k_sigma', 2.0)
        if mae:
            nivel_max_esperado = nivel_max + k_sigma * mae
            nivel_min_esperado = nivel_min - k_sigma * mae
        else:
            nivel_max_esperado = nivel_max
            nivel_min_esperado = nivel_min
        
        # Calcular tendencia
        tendencia = self._calcular_tendencia(pred_array, nivel_actual)
        
        return {
            'nivel_actual': float(nivel_actual),
            'nivel_min': nivel_min,
            'nivel_max': nivel_max,
            'nivel_medio': nivel_medio,
            'nivel_max_esperado': nivel_max_esperado,
            'nivel_min_esperado': nivel_min_esperado,
            'mae': mae,
            'rmse': rmse,
            'tendencia': tendencia,
            'serie_prediccion': pred_serie
        }
    
    def _obtener_ultimo_nivel(self, codigo_saih: str) -> Optional[float]:
        """Obtiene el último nivel registrado del embalse."""
        query = """
            SELECT nivel
            FROM saih_nivel_embalse
            WHERE codigo_saih = %s
            ORDER BY fecha DESC
            LIMIT 1
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (codigo_saih,))
            result = cursor.fetchone()
            return float(result['nivel']) if result else None
    
    def _calcular_tendencia(self, pred_array: np.ndarray, nivel_actual: float) -> str:
        """
        Calcula la tendencia del nivel (subiendo, bajando, estable).
        """
        nivel_final = pred_array[-1]
        diferencia = nivel_final - nivel_actual
        
        # Umbral de 2% para considerar "estable"
        umbral_estable = abs(nivel_actual * 0.02)
        
        if abs(diferencia) <= umbral_estable:
            return TendenciaNivel.ESTABLE.value
        elif diferencia > 0:
            return TendenciaNivel.SUBIENDO.value
        else:
            return TendenciaNivel.BAJANDO.value
    
    def _clasificar_riesgo(
        self,
        metricas: Dict,
        config: Dict,
        nivel_maximo: float
    ) -> Dict:
        """
        Clasifica el nivel de riesgo basándose en umbrales configurados.
        
        Prioridad de clasificación:
        1. ALTO: Si nivel_max_esperado >= umbral_alto * nivel_maximo
        2. SEQUIA: Si nivel_min_esperado <= umbral_minimo * nivel_maximo
        3. MODERADO: Si nivel_max_esperado >= umbral_moderado * nivel_maximo
        4. BAJO: En otro caso
        """
        umbral_alto = float(config['umbral_alto_relativo']) * nivel_maximo
        umbral_moderado = float(config['umbral_moderado_relativo']) * nivel_maximo
        umbral_minimo = float(config['umbral_minimo_relativo']) * nivel_maximo
        
        nivel_max_esp = metricas['nivel_max_esperado']
        nivel_min_esp = metricas['nivel_min_esperado']
        
        # Calcular probabilidad de superar umbral alto
        # Aproximación simple: si nivel_max > umbral, prob proporcional a qué tanto lo supera
        prob_superar = 0.0
        dias_hasta_umbral = None
        
        # Clasificación por prioridad
        if nivel_max_esp >= umbral_alto:
            nivel_riesgo = NivelRiesgo.ALTO
            nivel_severidad = 3
            color_hex = "#FF5722"
            prob_superar = min(1.0, (nivel_max_esp - umbral_alto) / (nivel_maximo - umbral_alto))
            dias_hasta_umbral = self._calcular_dias_hasta_umbral(
                metricas['serie_prediccion'], umbral_alto
            )
        
        elif nivel_min_esp <= umbral_minimo:
            nivel_riesgo = NivelRiesgo.SEQUIA
            nivel_severidad = 4
            color_hex = "#795548"
            prob_superar = min(1.0, (umbral_minimo - nivel_min_esp) / umbral_minimo)
            dias_hasta_umbral = self._calcular_dias_hasta_umbral(
                metricas['serie_prediccion'], umbral_minimo, direccion='bajo'
            )
        
        elif nivel_max_esp >= umbral_moderado:
            nivel_riesgo = NivelRiesgo.MODERADO
            nivel_severidad = 2
            color_hex = "#FFC107"
            prob_superar = min(1.0, (nivel_max_esp - umbral_moderado) / (umbral_alto - umbral_moderado))
            dias_hasta_umbral = self._calcular_dias_hasta_umbral(
                metricas['serie_prediccion'], umbral_moderado
            )
        
        else:
            nivel_riesgo = NivelRiesgo.BAJO
            nivel_severidad = 1
            color_hex = "#4CAF50"
        
        return {
            'nivel_riesgo': nivel_riesgo,
            'nivel_severidad': nivel_severidad,
            'color_hex': color_hex,
            'probabilidad_superar': prob_superar,
            'dias_hasta_umbral': dias_hasta_umbral,
            'umbral_alto': umbral_alto,
            'umbral_moderado': umbral_moderado,
            'umbral_minimo': umbral_minimo
        }
    
    def _calcular_dias_hasta_umbral(
        self,
        serie: List[float],
        umbral: float,
        direccion: str = 'alto'
    ) -> Optional[int]:
        """
        Calcula en cuántos días se alcanzará un umbral.
        
        Args:
            serie: Lista de predicciones diarias
            umbral: Valor umbral
            direccion: 'alto' para superar umbral, 'bajo' para caer por debajo
        """
        for dia, valor in enumerate(serie, start=1):
            if direccion == 'alto' and valor >= umbral:
                return dia
            elif direccion == 'bajo' and valor <= umbral:
                return dia
        
        return None
    
    def _generar_textos_recomendacion(
        self,
        clasificacion: Dict,
        metricas: Dict,
        info_embalse: Dict,
        horizonte: int
    ) -> Dict:
        """
        Genera textos de motivo y acción recomendada.
        
        Primero intenta usar plantillas de BD, si no encuentra usa generación básica.
        """
        nivel_riesgo = clasificacion['nivel_riesgo'].value
        porcentaje = (float(metricas['nivel_medio']) / float(info_embalse['nivel_maximo'])) * 100
        
        # Intentar obtener plantillas de BD
        plantillas = self._obtener_plantillas(nivel_riesgo, porcentaje, metricas['tendencia'])
        
        if plantillas and 'motivo' in plantillas and 'accion' in plantillas:
            # Usar plantillas parametrizadas
            # Asegurar que todos los valores no sean None
            mae_val = metricas.get('mae') or 0.0
            nivel_actual_val = metricas.get('nivel_actual') or metricas.get('nivel_medio', 0.0)
            
            motivo = self._formatear_plantilla(plantillas['motivo'], {
                'porcentaje': f"{porcentaje:.1f}",
                'nivel_pred': metricas['nivel_medio'],
                'nivel_max': info_embalse['nivel_maximo'],
                'nivel_actual': nivel_actual_val,
                'dias': horizonte,
                'mae': mae_val,
                'tendencia': metricas['tendencia'],
                'umbral_min': clasificacion.get('umbral_minimo', 0.0)
            })
            
            volumen_reducir = max(0.0, metricas['nivel_max_esperado'] - clasificacion.get('umbral_moderado', 0.0))
            
            accion = self._formatear_plantilla(plantillas['accion'], {
                'volumen_reducir': volumen_reducir,
                'volumen_reducir_max': volumen_reducir * 1.2,
                'dias': horizonte
            })
        else:
            # Generación básica de textos
            motivo, accion = self._generar_textos_basicos(
                nivel_riesgo, metricas, info_embalse, horizonte, porcentaje
            )
        
        return {
            'motivo': motivo,
            'accion': accion
        }
    
    def _obtener_plantillas(
        self,
        nivel_riesgo: str,
        porcentaje: float,
        tendencia: str
    ) -> Optional[Dict]:
        """Obtiene plantillas de texto desde la BD."""
        query = """
            SELECT tipo_plantilla, plantilla
            FROM plantilla_recomendacion
            WHERE nivel_riesgo = %s
              AND activo = TRUE
              AND (condicion_min_porcentaje IS NULL OR %s >= condicion_min_porcentaje)
              AND (condicion_max_porcentaje IS NULL OR %s <= condicion_max_porcentaje)
              AND (condicion_tendencia IS NULL OR condicion_tendencia = %s)
            ORDER BY prioridad
        """
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (nivel_riesgo, porcentaje/100, porcentaje/100, tendencia))
                results = cursor.fetchall()
                
                if results:
                    plantillas = {}
                    for row in results:
                        plantillas[row['tipo_plantilla']] = row['plantilla']
                    return plantillas
        except Exception as e:
            logger.warning(f"Error obteniendo plantillas: {e}")
        
        return None
    
    def _formatear_plantilla(self, plantilla: str, params: Dict) -> str:
        """Formatea una plantilla con parámetros."""
        try:
            return plantilla.format(**params)
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Error formateando plantilla: {e}. Plantilla: {plantilla[:100]}")
            return plantilla
        except Exception as e:
            logger.error(f"Error inesperado formateando plantilla: {e}")
            return plantilla
    
    def _generar_textos_basicos(
        self,
        nivel_riesgo: str,
        metricas: Dict,
        info_embalse: Dict,
        horizonte: int,
        porcentaje: float
    ) -> Tuple[str, str]:
        """Genera textos básicos cuando no hay plantillas en BD."""
        nivel_pred = metricas.get('nivel_medio', 0.0)
        nivel_max = float(info_embalse.get('nivel_maximo', 0.0))
        mae = metricas.get('mae') or 0.0
        
        if nivel_riesgo == 'ALTO':
            motivo = (
                f"El nivel predicho alcanzará {porcentaje:.1f}% de la capacidad máxima "
                f"({nivel_max:.2f} hm³) en los próximos {horizonte} días, con nivel esperado de "
                f"{nivel_pred:.2f} hm³. MAE histórico: {mae:.2f} hm³."
            )
            accion = (
                "URGENTE: Planificar desembalses preventivos. Coordinar con organismos de cuenca. "
                "Activar protocolos de emergencia y sistema de alertas."
            )
        
        elif nivel_riesgo == 'MODERADO':
            motivo = (
                f"El nivel predicho se situará en {porcentaje:.1f}% de capacidad "
                f"({nivel_pred:.2f} hm³) dentro de {horizonte} días. "
                f"Tendencia: {metricas['tendencia']}. Incertidumbre: ±{mae:.2f} hm³."
            )
            accion = (
                "Incrementar frecuencia de monitoreo. Evaluar desembalses graduales. "
                "Revisar pronósticos meteorológicos."
            )
        
        elif nivel_riesgo == 'SEQUIA':
            motivo = (
                f"El nivel predicho descenderá a {porcentaje:.1f}% de capacidad "
                f"({nivel_pred:.2f} hm³) en {horizonte} días. Riesgo de insuficiencia hídrica."
            )
            accion = (
                "CRÍTICO: Activar protocolos de escasez. Implementar restricciones de uso. "
                "Evaluar fuentes alternativas de suministro."
            )
        
        else:  # BAJO
            motivo = (
                f"El nivel predicho se mantendrá en {porcentaje:.1f}% de capacidad "
                f"({nivel_pred:.2f} hm³), dentro del rango óptimo operativo."
            )
            accion = (
                "Continuar con monitoreo estándar. Nivel estable y seguro. "
                "No se requieren acciones especiales."
            )
        
        return motivo, accion
    
    def _persistir_recomendacion(self, recomendacion: RecomendacionOperativaDTO) -> int:
        """Persiste la recomendación en la base de datos y retorna el ID."""
        query = """
            INSERT INTO recomendacion_operativa (
                codigo_saih, fecha_generacion, fecha_inicio, horizonte_dias,
                nivel_riesgo, nivel_severidad, nivel_actual,
                nivel_predicho_min, nivel_predicho_max, nivel_predicho_medio,
                mae_historico, rmse_historico,
                probabilidad_superar_umbral, dias_hasta_umbral,
                motivo, accion_recomendada,
                config_id, version_modelo
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (
                recomendacion.codigo_saih,
                recomendacion.fecha_generacion,
                recomendacion.fecha_inicio,
                recomendacion.horizonte_dias,
                recomendacion.nivel_riesgo.value,
                recomendacion.nivel_severidad,
                recomendacion.nivel_actual,
                recomendacion.nivel_predicho_min,
                recomendacion.nivel_predicho_max,
                recomendacion.nivel_predicho_medio,
                recomendacion.mae_historico,
                recomendacion.rmse_historico,
                recomendacion.probabilidad_superar_umbral,
                recomendacion.dias_hasta_umbral,
                recomendacion.motivo,
                recomendacion.accion_recomendada,
                recomendacion.config_id,
                recomendacion.version_modelo
            ))
            
            result = cursor.fetchone()
            return result['id']
    
    # =========================================================================
    # FUNCIONES DE CONSULTA
    # =========================================================================
    
    def obtener_recomendacion_por_id(self, recomendacion_id: int) -> Optional[RecomendacionOperativaDTO]:
        """Obtiene una recomendación específica por ID."""
        query = """
            SELECT 
                r.*,
                e.ubicacion,
                e.nivel_maximo,
                tr.color_hex
            FROM recomendacion_operativa r
            JOIN estacion_saih e ON r.codigo_saih = e.codigo_saih
            JOIN tipo_riesgo tr ON r.nivel_riesgo = tr.codigo
            WHERE r.id = %s
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (recomendacion_id,))
            result = cursor.fetchone()
            
            if result:
                return self._row_to_dto(result)
        
        return None
    
    def obtener_ultima_recomendacion(self, codigo_saih: str) -> Optional[RecomendacionOperativaDTO]:
        """Obtiene la última recomendación generada para un embalse."""
        query = """
            SELECT * FROM v_ultima_recomendacion
            WHERE codigo_saih = %s
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (codigo_saih,))
            result = cursor.fetchone()
            
            if result:
                return self._row_to_dto(result)
        
        return None
    
    def obtener_recomendaciones_por_demarcacion(
        self,
        id_demarcacion: str,
        solo_criticas: bool = False
    ) -> RiesgoDemarcacionDTO:
        """
        Obtiene resumen de recomendaciones para una demarcación.
        """
        # Obtener resumen agregado de la vista
        query_resumen = """
            SELECT * FROM v_riesgo_por_demarcacion
            WHERE id_demarcacion = %s
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query_resumen, (id_demarcacion,))
            resumen = cursor.fetchone()
            
            if not resumen:
                raise ValueError(f"Demarcación {id_demarcacion} no encontrada")
            
            # Obtener embalses críticos si se solicita
            embalses_criticos = []
            if solo_criticas or resumen['embalses_riesgo_alto'] > 0 or resumen['embalses_riesgo_sequia'] > 0:
                query_criticos = """
                    SELECT * FROM v_ultima_recomendacion
                    WHERE id_demarcacion = %s
                      AND nivel_riesgo IN ('ALTO', 'SEQUIA')
                    ORDER BY nivel_severidad DESC, nivel_predicho_medio DESC
                """
                cursor.execute(query_criticos, (id_demarcacion,))
                for row in cursor.fetchall():
                    embalses_criticos.append(self._row_to_resumen(row))
            
            return RiesgoDemarcacionDTO(
                id_demarcacion=resumen['id_demarcacion'],
                demarcacion=resumen['demarcacion'],
                organismo_gestor=resumen['organismo_gestor'],
                total_embalses=resumen['total_embalses'],
                embalses_riesgo_alto=resumen['embalses_riesgo_alto'],
                embalses_riesgo_moderado=resumen['embalses_riesgo_moderado'],
                embalses_riesgo_sequia=resumen['embalses_riesgo_sequia'],
                embalses_riesgo_bajo=resumen['embalses_riesgo_bajo'],
                porcentaje_criticos=float(resumen['porcentaje_criticos'] or 0),
                ultima_actualizacion=resumen['ultima_actualizacion'],
                embalses_criticos=embalses_criticos
            )
    
    def obtener_recomendaciones_por_organismo(
        self,
        id_organismo: int,
        incluir_demarcaciones: bool = True
    ) -> RiesgoOrganismoDTO:
        """
        Obtiene resumen de recomendaciones para un organismo gestor.
        """
        query_resumen = """
            SELECT * FROM v_riesgo_por_organismo
            WHERE id_organismo = %s
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query_resumen, (id_organismo,))
            resumen = cursor.fetchone()
            
            if not resumen:
                raise ValueError(f"Organismo {id_organismo} no encontrado")
            
            demarcaciones = []
            if incluir_demarcaciones:
                query_demarcaciones = """
                    SELECT id_demarcacion
                    FROM v_riesgo_por_demarcacion
                    WHERE organismo_gestor = %s
                """
                cursor.execute(query_demarcaciones, (resumen['organismo'],))
                
                for row in cursor.fetchall():
                    try:
                        dem_dto = self.obtener_recomendaciones_por_demarcacion(
                            row['id_demarcacion'],
                            solo_criticas=True
                        )
                        demarcaciones.append(dem_dto)
                    except Exception as e:
                        logger.warning(f"Error obteniendo demarcación {row['id_demarcacion']}: {e}")
            
            return RiesgoOrganismoDTO(
                id_organismo=resumen['id_organismo'],
                organismo=resumen['organismo'],
                tipo_gestion=resumen['tipo_gestion'],
                num_demarcaciones=resumen['num_demarcaciones'],
                total_embalses=resumen['total_embalses'],
                embalses_riesgo_alto=resumen['embalses_riesgo_alto'],
                embalses_riesgo_moderado=resumen['embalses_riesgo_moderado'],
                embalses_riesgo_sequia=resumen['embalses_riesgo_sequia'],
                embalses_riesgo_bajo=resumen['embalses_riesgo_bajo'],
                porcentaje_criticos=float(resumen['porcentaje_criticos'] or 0),
                ultima_actualizacion=resumen['ultima_actualizacion'],
                demarcaciones=demarcaciones
            )
    
    # =========================================================================
    # FUNCIONES AUXILIARES
    # =========================================================================
    
    def _row_to_dto(self, row: Dict) -> RecomendacionOperativaDTO:
        """Convierte una fila de BD a DTO."""
        return RecomendacionOperativaDTO(
            id=row.get('id'),
            codigo_saih=row['codigo_saih'],
            ubicacion=row.get('ubicacion'),
            fecha_generacion=row['fecha_generacion'],
            fecha_inicio=row['fecha_inicio'],
            horizonte_dias=row['horizonte_dias'],
            nivel_riesgo=NivelRiesgo(row['nivel_riesgo']),
            nivel_severidad=row['nivel_severidad'],
            color_hex=row.get('color_hex'),
            nivel_actual=float(row['nivel_actual']) if row.get('nivel_actual') else None,
            nivel_predicho_min=float(row['nivel_predicho_min']) if row.get('nivel_predicho_min') else None,
            nivel_predicho_max=float(row['nivel_predicho_max']) if row.get('nivel_predicho_max') else None,
            nivel_predicho_medio=float(row['nivel_predicho_medio']) if row.get('nivel_predicho_medio') else None,
            nivel_maximo=float(row['nivel_maximo']) if row.get('nivel_maximo') else None,
            mae_historico=float(row['mae_historico']) if row.get('mae_historico') else None,
            rmse_historico=float(row['rmse_historico']) if row.get('rmse_historico') else None,
            probabilidad_superar_umbral=float(row['probabilidad_superar_umbral']) if row.get('probabilidad_superar_umbral') else None,
            dias_hasta_umbral=row.get('dias_hasta_umbral'),
            motivo=row['motivo'],
            accion_recomendada=row['accion_recomendada'],
            config_id=row.get('config_id'),
            version_modelo=row.get('version_modelo')
        )
    
    def _row_to_resumen(self, row: Dict) -> RecomendacionResumen:
        """Convierte una fila de BD a resumen simplificado."""
        porcentaje = None
        if row.get('nivel_actual') and row.get('nivel_maximo'):
            porcentaje = (float(row['nivel_actual']) / float(row['nivel_maximo'])) * 100
        
        return RecomendacionResumen(
            codigo_saih=row['codigo_saih'],
            ubicacion=row['ubicacion'],
            nivel_riesgo=NivelRiesgo(row['nivel_riesgo']),
            nivel_severidad=row['nivel_severidad'],
            color_hex=row['color_hex'],
            nivel_actual=float(row['nivel_actual']) if row.get('nivel_actual') else None,
            nivel_predicho_medio=float(row['nivel_predicho_medio']) if row.get('nivel_predicho_medio') else None,
            porcentaje_llenado=porcentaje,
            fecha_generacion=row['fecha_generacion'],
            accion_recomendada=row['accion_recomendada']
        )


# Instancia singleton del servicio
recomendacion_service = RecomendacionService()
