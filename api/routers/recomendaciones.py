"""
Endpoints REST para el sistema de recomendaciones operativas.

Proporciona APIs para:
- Generar y consultar recomendaciones individuales por embalse
- Obtener resúmenes agregados por demarcación
- Obtener resúmenes agregados por organismo gestor
- Gestionar configuraciones de umbrales
- Consultar estadísticas del sistema
"""
from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks
from typing import Optional, List
from datetime import date, datetime
import logging

from ..config import settings
from ..models_recomendaciones import (
    RecomendacionRequest,
    RecomendacionOperativaDTO,
    RecomendacionResumen,
    RiesgoDemarcacionDTO,
    RiesgoOrganismoDTO,
    RecomendacionConfigCreate,
    RecomendacionConfigResponse,
    ListaRecomendacionesResponse,
    EstadisticasRecomendaciones,
    NivelRiesgo
)
from ..services.recomendacion import recomendacion_service

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(
    prefix="/recomendaciones",
    tags=["Recomendaciones Operativas"],
    responses={
        404: {"description": "Recurso no encontrado"},
        500: {"description": "Error interno del servidor"}
    }
)


# =============================================================================
# FUNCIONES AUXILIARES PARA BACKGROUND TASKS
# =============================================================================

async def generar_recomendacion_background_router(
    codigo_saih: str, 
    fecha_inicio: Optional[date], 
    horizonte: Optional[int],
    forzar: bool
):
    """
    Genera una recomendación con IA en segundo plano desde el router.
    No bloquea la respuesta de la API.
    """
    try:
        logger.info(f"[BACKGROUND] Starting AI recommendation generation for {codigo_saih}")
        recomendacion_dto = await recomendacion_service.evaluar_riesgo_embalse(
            codigo_saih=codigo_saih,
            fecha_inicio=fecha_inicio,
            horizonte=horizonte,
            forzar_regeneracion=forzar
        )
        logger.info(
            f"[BACKGROUND] AI recommendation generated for {codigo_saih}: "
            f"{recomendacion_dto.fuente_recomendacion} - {recomendacion_dto.nivel_riesgo.value}"
        )
    except Exception as e:
        logger.error(f"[BACKGROUND] Error generating AI recommendation for {codigo_saih}: {e}")


# =============================================================================
# ENDPOINTS DE RECOMENDACIONES INDIVIDUALES
# =============================================================================

@router.get(
    "/{codigo_saih}",
    response_model=RecomendacionOperativaDTO,
    summary="Obtener recomendación operativa para un embalse",
    description="""
    Genera o recupera la recomendación operativa más reciente para un embalse específico.
    
    **Comportamiento:**
    - Si existe una recomendación generada en las últimas 6 horas con los mismos parámetros, la devuelve.
    - Si no existe o `forzar_regeneracion=True`, genera una nueva predicción y recomendación.
    
    **Parámetros de simulación:**
    - `fecha_inicio`: Permite simular recomendaciones para cualquier fecha histórica. Si no se proporciona, usa la fecha actual.
    - `horizonte_dias`: Número de días a predecir desde la fecha de inicio.
    
    **Clasificación de riesgo:**
    - **ALTO**: Nivel predicho ≥ 95% de capacidad máxima (umbral configurable)
    - **MODERADO**: Nivel predicho entre 80% y 95% de capacidad
    - **BAJO**: Nivel predicho entre 30% y 80% de capacidad
    - **SEQUÍA**: Nivel predicho ≤ 30% de capacidad
    
    Los umbrales son configurables por embalse o se usan valores globales por defecto.
    """
)
async def obtener_recomendacion_embalse(
    codigo_saih: str = Path(..., description="Código SAIH del embalse (ej: E001)"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio para simulación (YYYY-MM-DD). Si no se especifica, usa la fecha actual del sistema."),
    horizonte_dias: Optional[int] = Query(None, ge=1, le=180, description="Horizonte de predicción en días. Si es None, usa la configuración del embalse (defecto: 7)."),
    forzar_regeneracion: bool = Query(False, description="Si True, regenera la recomendación aunque exista una reciente en caché."),
    esperar_ia: bool = Query(False, description="Si True y la IA está habilitada, espera a que se genere la recomendación con IA antes de responder."),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Genera o recupera recomendación operativa para un embalse."""
    try:
        # Convertir fecha_inicio de string a date
        fecha_inicio_date = None
        if fecha_inicio:
            try:
                fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Formato de fecha inválido: {fecha_inicio}. Use YYYY-MM-DD"
                )
        
        # Si no se fuerza regeneración, intentar obtener de BD (rápido)
        if not forzar_regeneracion:
            recomendacion_existente = recomendacion_service._obtener_recomendacion_reciente(
                codigo_saih, fecha_inicio_date, horizonte_dias
            )
            if recomendacion_existente:
                logger.info(f"Cached recommendation for {codigo_saih}")
                return recomendacion_existente
        
        # Si la IA está deshabilitada, generar síncrono (es rápido sin LLM)
        if not settings.enable_llm_recomendaciones:
            logger.info(f"Generating recommendation without AI for {codigo_saih}")
            recomendacion = await recomendacion_service.evaluar_riesgo_embalse(
                codigo_saih=codigo_saih,
                fecha_inicio=fecha_inicio_date,
                horizonte=horizonte_dias,
                forzar_regeneracion=forzar_regeneracion
            )
            return recomendacion
        
        # Si la IA está habilitada y no se pide esperar, generar en background
        if settings.enable_llm_recomendaciones and not esperar_ia:
            logger.info(f"Scheduling AI recommendation in background for {codigo_saih}")
            background_tasks.add_task(
                generar_recomendacion_background_router,
                codigo_saih,
                fecha_inicio_date,
                horizonte_dias,
                forzar_regeneracion
            )
            
            # Devolver recomendación básica inmediata (sin IA, rápido)
            # Deshabilitamos temporalmente la IA para esta llamada
            enable_llm_original = settings.enable_llm_recomendaciones
            settings.enable_llm_recomendaciones = False
            try:
                recomendacion = await recomendacion_service.evaluar_riesgo_embalse(
                    codigo_saih=codigo_saih,
                    fecha_inicio=fecha_inicio_date,
                    horizonte=horizonte_dias,
                    forzar_regeneracion=forzar_regeneracion
                )
            finally:
                settings.enable_llm_recomendaciones = enable_llm_original
            
            return recomendacion
        
        # Si no hay IA habilitada O se pide esperar, generar síncrono
        logger.info(f"Generating recommendation (wait_ai={esperar_ia}) for {codigo_saih}")
        recomendacion = await recomendacion_service.evaluar_riesgo_embalse(
            codigo_saih=codigo_saih,
            fecha_inicio=fecha_inicio_date,
            horizonte=horizonte_dias,
            forzar_regeneracion=forzar_regeneracion
        )
        return recomendacion
        
    except ValueError as e:
        logger.error(f"Error de validación para {codigo_saih}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generando recomendación para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/{codigo_saih}",
    response_model=RecomendacionOperativaDTO,
    summary="Generar nueva recomendación (forzada)",
    description="""
    Genera una nueva recomendación para el embalse, independientemente de si existe una reciente.
    
    **Uso en simulaciones:**
    Este endpoint es ideal para dashboards interactivos donde el usuario puede:
    - Navegar por diferentes fechas históricas
    - Simular escenarios futuros
    - Comparar predicciones con datos reales
    
    **Body (JSON):**
    - `fecha_inicio`: Fecha para la simulación (opcional, usa hoy si no se especifica)
    - `horizonte_dias`: Número de días a predecir (opcional, usa config del embalse)
    """
)
async def generar_recomendacion_embalse(
    codigo_saih: str = Path(..., description="Código SAIH del embalse"),
    request: RecomendacionRequest = RecomendacionRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Fuerza la generación de una nueva recomendación.
    
    Si la IA está habilitada, genera una versión rápida sin IA primero,
    y programa la versión con IA en segundo plano.
    
    Útil para simulaciones y análisis interactivos en el dashboard.
    """
    try:
        # Convertir fecha_inicio si se proporciona
        fecha_inicio_date = None
        if request.fecha_inicio:
            try:
                fecha_inicio_date = datetime.strptime(request.fecha_inicio, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de fecha inválido: {request.fecha_inicio}. Use YYYY-MM-DD"
                )
        
        # Si la IA está habilitada, generar en background
        if settings.enable_llm_recomendaciones:
            logger.info(f"Scheduling AI recommendation in background for {codigo_saih}")
            background_tasks.add_task(
                generar_recomendacion_background_router,
                codigo_saih,
                fecha_inicio_date,
                request.horizonte_dias,
                True  # Siempre forzar en POST
            )
            
            # Generar versión rápida sin IA
            enable_llm_original = settings.enable_llm_recomendaciones
            settings.enable_llm_recomendaciones = False
            try:
                recomendacion = await recomendacion_service.evaluar_riesgo_embalse(
                    codigo_saih=codigo_saih,
                    fecha_inicio=fecha_inicio_date,
                    horizonte=request.horizonte_dias,
                    forzar_regeneracion=True
                )
            finally:
                settings.enable_llm_recomendaciones = enable_llm_original
            
            return recomendacion
        
        # Si no hay IA, generar normal (es rápido)
        recomendacion = await recomendacion_service.evaluar_riesgo_embalse(
            codigo_saih=codigo_saih,
            fecha_inicio=fecha_inicio_date,
            horizonte=request.horizonte_dias,
            forzar_regeneracion=True
        )
        
        return recomendacion
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generando recomendación para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{codigo_saih}/historico",
    response_model=ListaRecomendacionesResponse,
    summary="Obtener histórico de recomendaciones",
    description="Obtiene el histórico completo de recomendaciones generadas para un embalse."
)
async def obtener_historico_recomendaciones(
    codigo_saih: str = Path(..., description="Código SAIH del embalse"),
    limite: int = Query(30, ge=1, le=365, description="Número máximo de recomendaciones a retornar"),
    nivel_riesgo: Optional[NivelRiesgo] = Query(None, description="Filtrar por nivel de riesgo")
):
    """
    Obtiene el histórico de recomendaciones para un embalse.
    """
    try:
        query = """
            SELECT 
                r.*,
                e.ubicacion,
                e.nivel_maximo,
                tr.color_hex
            FROM recomendacion_operativa r
            JOIN estacion_saih e ON r.codigo_saih = e.codigo_saih
            JOIN tipo_riesgo tr ON r.nivel_riesgo = tr.codigo
            WHERE r.codigo_saih = %s
        """
        
        params = [codigo_saih]
        
        if nivel_riesgo:
            query += " AND r.nivel_riesgo = %s"
            params.append(nivel_riesgo.value)
        
        query += " ORDER BY r.fecha_generacion DESC LIMIT %s"
        params.append(limite)
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            recomendaciones = [
                recomendacion_service._row_to_dto(row) for row in results
            ]
            
            filtros = {"codigo_saih": codigo_saih}
            if nivel_riesgo:
                filtros["nivel_riesgo"] = nivel_riesgo.value
            
            return ListaRecomendacionesResponse(
                total=len(recomendaciones),
                recomendaciones=recomendaciones,
                filtros_aplicados=filtros
            )
            
    except Exception as e:
        logger.error(f"Error obteniendo histórico para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS AGREGADOS POR REGIÓN
# =============================================================================

@router.get(
    "/demarcacion/{id_demarcacion}",
    response_model=RiesgoDemarcacionDTO,
    summary="Resumen de riesgos por demarcación",
    description="""
    Obtiene un resumen agregado de los niveles de riesgo de todos los embalses
    en una demarcación hidrográfica específica.
    
    Incluye:
    - Contadores por nivel de riesgo
    - Porcentaje de embalses críticos
    - Listado detallado de embalses en situación crítica (ALTO o SEQUÍA)
    """
)
async def obtener_riesgos_demarcacion(
    id_demarcacion: str = Path(..., description="Código de demarcación (ej: ES090)"),
    solo_criticas: bool = Query(False, description="Si True, solo incluye embalses críticos en el detalle")
):
    """
    Obtiene resumen de riesgos para una demarcación hidrográfica.
    """
    try:
        resultado = recomendacion_service.obtener_recomendaciones_por_demarcacion(
            id_demarcacion=id_demarcacion,
            solo_criticas=solo_criticas
        )
        return resultado
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error obteniendo riesgos para demarcación {id_demarcacion}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/organismo/{id_organismo}",
    response_model=RiesgoOrganismoDTO,
    summary="Resumen de riesgos por organismo gestor",
    description="""
    Obtiene un resumen agregado de los niveles de riesgo de todos los embalses
    gestionados por un organismo específico (Confederación o Administración Autonómica).
    
    Incluye:
    - Estadísticas globales del organismo
    - Desglose por demarcaciones gestionadas
    - Identificación de embalses críticos
    """
)
async def obtener_riesgos_organismo(
    id_organismo: int = Path(..., description="ID del organismo gestor"),
    incluir_demarcaciones: bool = Query(True, description="Incluir desglose por demarcaciones")
):
    """
    Obtiene resumen de riesgos para un organismo gestor.
    """
    try:
        resultado = recomendacion_service.obtener_recomendaciones_por_organismo(
            id_organismo=id_organismo,
            incluir_demarcaciones=incluir_demarcaciones
        )
        return resultado
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error obteniendo riesgos para organismo {id_organismo}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/resumen/todas",
    response_model=List[RecomendacionResumen],
    summary="Resumen de todas las recomendaciones actuales",
    description="Obtiene un listado resumido de las últimas recomendaciones para todos los embalses."
)
async def obtener_todas_recomendaciones(
    nivel_riesgo: Optional[NivelRiesgo] = Query(None, description="Filtrar por nivel de riesgo"),
    limite: int = Query(100, ge=1, le=500, description="Número máximo de resultados")
):
    """
    Obtiene resumen de todas las últimas recomendaciones.
    """
    try:
        query = "SELECT * FROM v_ultima_recomendacion"
        params = []
        
        if nivel_riesgo:
            query += " WHERE nivel_riesgo = %s"
            params.append(nivel_riesgo.value)
        
        query += " ORDER BY nivel_severidad DESC, fecha_generacion DESC LIMIT %s"
        params.append(limite)
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            resumenes = [
                recomendacion_service._row_to_resumen(row) for row in results
            ]
            
            return resumenes
            
    except Exception as e:
        logger.error(f"Error obteniendo resumen de recomendaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE CONFIGURACIÓN
# =============================================================================

@router.get(
    "/config/{codigo_saih}",
    response_model=RecomendacionConfigResponse,
    summary="Obtener configuración de umbrales",
    description="Obtiene la configuración de umbrales efectiva para un embalse (específica o global)."
)
async def obtener_configuracion(
    codigo_saih: str = Path(..., description="Código SAIH del embalse")
):
    """
    Obtiene la configuración de umbrales para un embalse.
    """
    try:
        config = recomendacion_service.obtener_configuracion_embalse(codigo_saih)
        
        if not config or not config.get('id'):
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró configuración para {codigo_saih}"
            )
        
        # Convertir a modelo Pydantic
        return RecomendacionConfigResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo configuración para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/config",
    response_model=RecomendacionConfigResponse,
    summary="Crear o actualizar configuración de umbrales",
    description="""
    Crea o actualiza la configuración de umbrales para un embalse específico o global.
    
    **Parámetros clave:**
    - `codigo_saih`: NULL para configuración global, código específico para un embalse
    - `umbral_alto_relativo`: % de capacidad para riesgo ALTO (ej: 0.95 = 95%)
    - `umbral_moderado_relativo`: % de capacidad para riesgo MODERADO (ej: 0.80)
    - `umbral_minimo_relativo`: % bajo el cual se considera SEQUÍA (ej: 0.30)
    - `k_sigma`: Multiplicador para intervalo de confianza (nivel ± k*MAE)
    """
)
async def crear_actualizar_configuracion(
    config: RecomendacionConfigCreate
):
    """
    Crea o actualiza configuración de umbrales.
    """
    try:
        # Verificar que el embalse existe si se proporciona codigo_saih
        if config.codigo_saih:
            info = recomendacion_service._obtener_info_embalse(config.codigo_saih)
            if not info:
                raise HTTPException(
                    status_code=404,
                    detail=f"Embalse {config.codigo_saih} no encontrado"
                )
        
        # Insertar o actualizar configuración
        query = """
            INSERT INTO recomendacion_config (
                codigo_saih, nombre, descripcion,
                umbral_alto_relativo, umbral_moderado_relativo, umbral_minimo_relativo,
                horizonte_dias, k_sigma,
                prob_umbral_moderado, prob_umbral_alto,
                activo
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (codigo_saih, nombre)
            DO UPDATE SET
                descripcion = EXCLUDED.descripcion,
                umbral_alto_relativo = EXCLUDED.umbral_alto_relativo,
                umbral_moderado_relativo = EXCLUDED.umbral_moderado_relativo,
                umbral_minimo_relativo = EXCLUDED.umbral_minimo_relativo,
                horizonte_dias = EXCLUDED.horizonte_dias,
                k_sigma = EXCLUDED.k_sigma,
                prob_umbral_moderado = EXCLUDED.prob_umbral_moderado,
                prob_umbral_alto = EXCLUDED.prob_umbral_alto,
                activo = EXCLUDED.activo,
                fecha_modificacion = CURRENT_TIMESTAMP
            RETURNING *
        """
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query, (
                config.codigo_saih,
                config.nombre,
                config.descripcion,
                config.umbral_alto_relativo,
                config.umbral_moderado_relativo,
                config.umbral_minimo_relativo,
                config.horizonte_dias,
                config.k_sigma,
                config.prob_umbral_moderado,
                config.prob_umbral_alto,
                config.activo
            ))
            
            result = cursor.fetchone()
            
            return RecomendacionConfigResponse(**dict(result))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando/actualizando configuración: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/config/{config_id}",
    summary="Desactivar configuración",
    description="Desactiva una configuración de umbrales específica."
)
async def desactivar_configuracion(
    config_id: int = Path(..., description="ID de la configuración")
):
    """
    Desactiva (no elimina) una configuración de umbrales.
    """
    try:
        query = """
            UPDATE recomendacion_config
            SET activo = FALSE, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id
        """
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query, (config_id,))
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Configuración {config_id} no encontrada"
                )
            
            return {"message": f"Configuración {config_id} desactivada correctamente"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error desactivando configuración {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE ESTADÍSTICAS
# =============================================================================

@router.get(
    "/estadisticas/sistema",
    response_model=EstadisticasRecomendaciones,
    summary="Estadísticas del sistema de recomendaciones",
    description="Obtiene estadísticas globales del sistema de recomendaciones."
)
async def obtener_estadisticas_sistema():
    """
    Obtiene estadísticas globales del sistema.
    """
    try:
        query_stats = """
            SELECT 
                (SELECT COUNT(DISTINCT codigo_saih) FROM estacion_saih WHERE nivel_maximo IS NOT NULL) 
                    AS total_embalses,
                (SELECT COUNT(DISTINCT codigo_saih) FROM recomendacion_operativa) 
                    AS embalses_con_rec,
                (SELECT COUNT(*) FROM recomendacion_operativa) 
                    AS total_recomendaciones,
                (SELECT MAX(fecha_generacion) FROM recomendacion_operativa) 
                    AS ultima_generacion,
                (SELECT AVG(horizonte_dias) FROM recomendacion_operativa) 
                    AS prom_horizonte,
                (SELECT AVG(mae_historico) FROM recomendacion_operativa WHERE mae_historico IS NOT NULL) 
                    AS prom_mae
        """
        
        query_dist = """
            SELECT nivel_riesgo, COUNT(DISTINCT codigo_saih) as cantidad
            FROM v_ultima_recomendacion
            GROUP BY nivel_riesgo
        """
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query_stats)
            stats = cursor.fetchone()
            
            cursor.execute(query_dist)
            dist_results = cursor.fetchall()
            
            distribucion = {row['nivel_riesgo']: row['cantidad'] for row in dist_results}
            
            return EstadisticasRecomendaciones(
                total_embalses_monitorizados=stats['total_embalses'] or 0,
                embalses_con_recomendaciones=stats['embalses_con_rec'] or 0,
                recomendaciones_totales_generadas=stats['total_recomendaciones'] or 0,
                ultima_generacion=stats['ultima_generacion'],
                distribucion_riesgos=distribucion,
                promedio_dias_horizonte=float(stats['prom_horizonte'] or 0),
                promedio_mae=float(stats['prom_mae']) if stats['prom_mae'] else None
            )
            
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE UTILIDAD
# =============================================================================

@router.get(
    "/tipos-riesgo",
    summary="Listar tipos de riesgo disponibles",
    description="Obtiene el catálogo de tipos de riesgo con sus descripciones."
)
async def listar_tipos_riesgo():
    """
    Obtiene el catálogo de tipos de riesgo.
    """
    try:
        query = "SELECT * FROM tipo_riesgo ORDER BY nivel_severidad"
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
    except Exception as e:
        logger.error(f"Error obteniendo tipos de riesgo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE LLM (Ollama)
# =============================================================================

@router.get(
    "/llm/salud",
    summary="Verificar estado del servicio LLM (Ollama)",
    description="""
    Verifica que el servicio Ollama esté disponible y el modelo configurado esté cargado.
    
    **Retorna:**
    - `disponible`: Si Ollama está accesible
    - `modelo_configurado`: Nombre del modelo configurado
    - `modelo_disponible`: Si el modelo está instalado
    - `modelos_instalados`: Lista de modelos disponibles
    """
)
async def verificar_salud_llm():
    """Verifica el estado del servicio Ollama."""
    try:
        from ..services.llm_service import llm_service
        resultado = await llm_service.verificar_salud_ollama()
        return resultado
    except Exception as e:
        logger.error(f"Error verificando salud LLM: {e}")
        return {
            'disponible': False,
            'error': str(e)
        }


@router.get(
    "/llm/estadisticas",
    summary="Obtener estadísticas de uso del LLM",
    description="""
    Muestra estadísticas sobre el uso del servicio LLM:
    - Total de peticiones
    - Cache hits/misses
    - Tasa de éxito del LLM
    - Errores
    """
)
async def obtener_estadisticas_llm():
    """Retorna estadísticas de uso del servicio LLM."""
    try:
        from ..services.llm_service import llm_service
        from ..services.llm_service import llm_service
        stats = llm_service.get_stats()
        
        # Obtener también estadísticas de BD con fallback a query simple
        cache_stats = []
        
        try:
            # Intentar usar la vista optimizada
            query = "SELECT * FROM v_llm_cache_stats"
            with recomendacion_service.db.get_cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                cache_stats = [dict(row) for row in results]
        except Exception as e:
            logger.warning(f"No se pudo usar v_llm_cache_stats: {e}")
            # Fallback: query directa a la tabla
            try:
                query_fallback = """
                    SELECT 
                        nivel_riesgo,
                        COUNT(*) as total_entradas,
                        COALESCE(SUM(hits), 0) as total_hits,
                        COALESCE(AVG(hits), 0) as hits_promedio,
                        MAX(fecha_cache) as ultima_actualizacion,
                        COUNT(CASE WHEN fecha_cache > NOW() - INTERVAL '24 hours' THEN 1 END) as entradas_recientes
                    FROM llm_cache_recomendaciones
                    GROUP BY nivel_riesgo
                """
                with recomendacion_service.db.get_cursor() as cursor:
                    cursor.execute(query_fallback)
                    results = cursor.fetchall()
                    cache_stats = [dict(row) for row in results]
            except Exception as e2:
                logger.warning(f"Tampoco se pudo acceder a la tabla directamente: {e2}")
                cache_stats = []
        
        return {
            'servicio': stats,
            'cache_bd': cache_stats,
            'configuracion': {
                'habilitado': settings.enable_llm_recomendaciones,
                'modelo': settings.ollama_model,
                'url': settings.ollama_url,
                'timeout': settings.ollama_timeout,
                'cache_ttl_horas': settings.llm_cache_ttl / 3600
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas LLM: {e}")
        # En lugar de fallar completamente, devolver lo que podamos
        try:
            from ..services.llm_service import llm_service
            return {
                'servicio': llm_service.get_stats(),
                'cache_bd': [],
                'configuracion': {
                    'habilitado': settings.enable_llm_recomendaciones,
                    'modelo': settings.ollama_model,
                    'url': settings.ollama_url,
                    'timeout': settings.ollama_timeout,
                    'cache_ttl_horas': settings.llm_cache_ttl / 3600
                },
                'error': str(e)
            }
        except:
            raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/llm/limpiar-cache",
    summary="Limpiar caché antiguo del LLM",
    description="""
    Elimina entradas antiguas del caché de respuestas LLM.
    
    **Parámetro:**
    - `dias_antiguedad`: Eliminar entradas más antiguas que estos días (default: 30)
    """
)
async def limpiar_cache_llm(
    dias_antiguedad: int = Query(30, ge=1, le=365, description="Días de antigüedad para limpiar")
):
    """Limpia el caché antiguo del LLM."""
    try:
        query = "SELECT limpiar_cache_llm_antiguo(%s)"
        
        with recomendacion_service.db.get_cursor() as cursor:
            cursor.execute(query, (dias_antiguedad,))
            result = cursor.fetchone()
            filas_eliminadas = result['limpiar_cache_llm_antiguo'] if result else 0
            
            return {
                'success': True,
                'filas_eliminadas': filas_eliminadas,
                'dias_antiguedad': dias_antiguedad
            }
            
    except Exception as e:
        logger.error(f"Error limpiando caché LLM: {e}")
        raise HTTPException(status_code=500, detail=str(e))

