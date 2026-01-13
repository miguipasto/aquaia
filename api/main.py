"""
API REST para predicción de niveles de embalses usando LSTM Seq2Seq.

AquaAI - Sistema Inteligente de Predicción de Embalses
Autor: Miguel (TFM)
Versión: 1.0.0
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
import logging
import pandas as pd

from .config import settings
from .models import (
    EmbalseInfo,
    SerieHistoricaPunto,
    PrediccionPunto,
    PrediccionRequest,
    PrediccionResponse,
    RiesgoRequest,
    RiesgoEmbalse,
    EmbalseResumen,
    PrediccionLoteRequest,
    HealthCheck,
    Demarcacion,
    OrganismoGestor,
    Geografia,
    EstadisticasRegion,
    ComparacionResponse
)
from .data import data_loader, db_connection
from .services import prediction_service, risk_service
from .routers import recomendaciones as recomendaciones_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor del ciclo de vida de la aplicación.
    Carga modelo y datos al iniciar, libera recursos al finalizar.
    """
    logger.info("🚀 Iniciando AquaAI API...")
    
    # Cargar modelo y scalers
    try:
        prediction_service.load_model()
        logger.info("✓ Modelo y scalers cargados correctamente")
    except Exception as e:
        logger.error(f"❌ Error al cargar modelo: {e}")
        raise
    
    # Inicializar conexión a base de datos
    try:
        data_loader.initialize()
        logger.info("✓ Conexión a PostgreSQL establecida")
    except Exception as e:
        logger.error(f"❌ Error al conectar con la base de datos: {e}")
        raise
    
    logger.info("✅ AquaAI API lista para recibir peticiones")
    
    yield  # La aplicación está activa
    
    # Cleanup
    logger.info("👋 Cerrando AquaAI API...")
    data_loader.close()


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(recomendaciones_router.router)


# ============================================================================
# ENDPOINTS DE SALUD Y UTILIDADES
# ============================================================================

@app.get(
    "/",
    summary="Raíz de la API",
    description="Endpoint raíz que devuelve información básica de la API"
)
async def root():
    """Endpoint raíz."""
    return {
        "nombre": settings.app_name,
        "version": settings.app_version,
        "descripcion": settings.app_description,
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["Utilidades"],
    summary="Estado de salud de la API",
    description="Verifica que todos los componentes estén cargados correctamente"
)
async def health_check():
    """Verifica el estado de salud de la API."""
    model_loaded = prediction_service.model is not None
    scalers_loaded = prediction_service.scalers is not None
    
    # Verificar conexión a base de datos
    try:
        data_loaded = db_connection.test_connection()
    except:
        data_loaded = False
    
    num_embalses = len(prediction_service.get_available_embalses()) if scalers_loaded else 0
    
    return {
        "status": "healthy" if all([model_loaded, scalers_loaded, data_loaded]) else "unhealthy",
        "version": settings.app_version,
        "model_loaded": model_loaded,
        "scalers_loaded": scalers_loaded,
        "data_loaded": data_loaded,
        "num_embalses": num_embalses
    }


# ============================================================================
# ENDPOINTS DE VISUALIZACIÓN / DASHBOARD
# ============================================================================

@app.get(
    "/embalses",
    response_model=List[EmbalseInfo],
    tags=["Embalses"],
    summary="Listar embalses disponibles",
    description="Devuelve la lista completa de embalses disponibles en el sistema con sus datos básicos"
)
async def listar_embalses():
    """Obtiene la lista de todos los embalses disponibles."""
    try:
        embalses = data_loader.get_embalses_list()
        return embalses
    except Exception as e:
        logger.error(f"Error al listar embalses: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener lista de embalses: {str(e)}")


@app.get(
    "/embalses/{codigo_saih}/historico",
    response_model=List[SerieHistoricaPunto],
    tags=["Embalses"],
    summary="Obtener serie histórica de un embalse",
    description="Devuelve los datos históricos de nivel, precipitación, temperatura y caudal del embalse"
)
async def obtener_historico(
    codigo_saih: str,
    start_date: Optional[str] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha final (YYYY-MM-DD)")
):
    """Obtiene la serie histórica de un embalse."""
    try:
        # Validar que el embalse existe
        if not data_loader.embalse_exists(codigo_saih):
            raise HTTPException(status_code=404, detail=f"Embalse {codigo_saih} no encontrado")
        
        # Obtener datos históricos
        df_hist = data_loader.get_historico(codigo_saih, start_date, end_date)
        
        # Convertir a lista de diccionarios
        result = []
        for _, row in df_hist.iterrows():
            result.append({
                "fecha": row['fecha'].strftime('%Y-%m-%d'),
                "nivel": float(row['nivel']) if not pd.isna(row['nivel']) else None,
                "precipitacion": float(row['precipitacion']) if 'precipitacion' in row and not pd.isna(row['precipitacion']) else None,
                "temperatura": float(row['temperatura']) if 'temperatura' in row and not pd.isna(row['temperatura']) else None,
                "caudal_promedio": float(row['caudal_promedio']) if 'caudal_promedio' in row and not pd.isna(row['caudal_promedio']) else None
            })
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener histórico de {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener histórico: {str(e)}")


@app.get(
    "/embalses/{codigo_saih}/resumen",
    response_model=EmbalseResumen,
    tags=["Embalses"],
    summary="Obtener resumen estadístico del embalse",
    description="Devuelve un resumen con el último nivel registrado y estadísticas anuales"
)
async def obtener_resumen(codigo_saih: str):
    """Obtiene un resumen estadístico del embalse."""
    try:
        # Validar que el embalse existe
        if not data_loader.embalse_exists(codigo_saih):
            raise HTTPException(status_code=404, detail=f"Embalse {codigo_saih} no encontrado")
        
        resumen = data_loader.get_resumen(codigo_saih)
        return resumen
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener resumen de {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


# ============================================================================
# ENDPOINTS DE PREDICCIÓN
# ============================================================================

@app.post(
    "/predicciones/{codigo_saih}",
    response_model=PrediccionResponse,
    tags=["Predicción"],
    summary="Generar predicción para un embalse",
    description="Ejecuta el modelo LSTM en los dos modos (hist, aemet_ruido) y devuelve las predicciones"
)
async def generar_prediccion(
    codigo_saih: str,
    request: PrediccionRequest
):
    """Genera predicción de nivel para un embalse."""
    try:
        # Validar que el embalse existe y tiene scaler
        if not prediction_service.embalse_disponible(codigo_saih):
            raise HTTPException(
                status_code=404,
                detail=f"Embalse {codigo_saih} no disponible para predicción (sin scaler)"
            )
        
        # Ejecutar predicción
        df_pred = prediction_service.predecir_embalse(
            codigo_saih=codigo_saih,
            fecha=request.fecha_inicio,
            horizonte=request.horizonte_dias
        )
        
        # Convertir a formato de respuesta
        predicciones = []
        for _, row in df_pred.iterrows():
            predicciones.append({
                "fecha": row['fecha'].strftime('%Y-%m-%d'),
                "pred_hist": float(row['pred_hist']),
                "pred_aemet_ruido": float(row['pred_aemet_ruido']),
                "nivel_real": float(row['nivel_real']) if not pd.isna(row['nivel_real']) else None
            })
        
        return {
            "codigo_saih": codigo_saih,
            "fecha_inicio": request.fecha_inicio,
            "horizonte_dias": request.horizonte_dias,
            "predicciones": predicciones
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al generar predicción para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al generar predicción: {str(e)}")


@app.get(
    "/predicciones/{codigo_saih}/ultimo",
    response_model=PrediccionResponse,
    tags=["Predicción"],
    summary="Predicción rápida con parámetros por defecto",
    description="Genera una predicción usando la última fecha disponible y horizonte por defecto (90 días)"
)
async def prediccion_ultimo(codigo_saih: str):
    """Genera predicción con parámetros por defecto."""
    try:
        # Validar que el embalse existe
        if not prediction_service.embalse_disponible(codigo_saih):
            raise HTTPException(
                status_code=404,
                detail=f"Embalse {codigo_saih} no disponible para predicción"
            )
        
        # Determinar fecha automáticamente
        fecha_max = data_loader.get_fecha_maxima(codigo_saih)
        import pandas as pd
        fecha_inicio_dt = pd.to_datetime(fecha_max) - pd.Timedelta(days=settings.default_prediction_horizon)
        fecha_inicio = fecha_inicio_dt.strftime('%Y-%m-%d')
        
        # Ejecutar predicción
        df_pred = prediction_service.predecir_embalse(
            codigo_saih=codigo_saih,
            fecha=fecha_inicio,
            horizonte=settings.default_prediction_horizon
        )
        
        # Convertir a formato de respuesta
        predicciones = []
        for _, row in df_pred.iterrows():
            predicciones.append({
                "fecha": row['fecha'].strftime('%Y-%m-%d'),
                "pred_hist": float(row['pred_hist']),
                "pred_aemet_ruido": float(row['pred_aemet_ruido']),
                "nivel_real": float(row['nivel_real']) if not pd.isna(row['nivel_real']) else None
            })
        
        return {
            "codigo_saih": codigo_saih,
            "fecha_inicio": fecha_inicio,
            "horizonte_dias": settings.default_prediction_horizon,
            "predicciones": predicciones
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en predicción rápida para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al generar predicción: {str(e)}")


@app.post(
    "/predicciones/lote",
    response_model=List[PrediccionResponse],
    tags=["Predicción"],
    summary="Predicción en lote para múltiples embalses",
    description="Genera predicciones para varios embalses con parámetros comunes"
)
async def prediccion_lote(request: PrediccionLoteRequest):
    """Genera predicciones para múltiples embalses."""
    resultados = []
    errores = []
    
    for codigo in request.codigos_saih:
        try:
            # Validar disponibilidad
            if not prediction_service.embalse_disponible(codigo):
                errores.append(f"{codigo}: no disponible")
                continue
            
            # Ejecutar predicción
            df_pred = prediction_service.predecir_embalse(
                codigo_saih=codigo,
                fecha=request.fecha_inicio,
                horizonte=request.horizonte_dias
            )
            
            # Convertir a formato de respuesta
            predicciones = []
            for _, row in df_pred.iterrows():
                predicciones.append({
                    "fecha": row['fecha'].strftime('%Y-%m-%d'),
                    "pred_hist": float(row['pred_hist']),
                    "pred_aemet_ruido": float(row['pred_aemet_ruido']),
                    "nivel_real": float(row['nivel_real']) if not pd.isna(row['nivel_real']) else None
                })
            
            resultados.append({
                "codigo_saih": codigo,
                "fecha_inicio": request.fecha_inicio,
                "horizonte_dias": request.horizonte_dias,
                "predicciones": predicciones
            })
        
        except Exception as e:
            errores.append(f"{codigo}: {str(e)}")
    
    if len(resultados) == 0 and len(errores) > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo generar ninguna predicción. Errores: {', '.join(errores)}"
        )
    
    return resultados


# ============================================================================
# ENDPOINTS DE RIESGO Y RECOMENDACIÓN
# ============================================================================

@app.post(
    "/embalses/{codigo_saih}/riesgo",
    response_model=RiesgoEmbalse,
    tags=["Riesgo"],
    summary="Análisis de riesgo del embalse",
    description="Evalúa el riesgo basándose en predicciones operativas y umbrales configurables"
)
async def analizar_riesgo(
    codigo_saih: str,
    request: RiesgoRequest
):
    """Analiza el riesgo operativo de un embalse."""
    try:
        # Validar que el embalse existe
        if not prediction_service.embalse_disponible(codigo_saih):
            raise HTTPException(
                status_code=404,
                detail=f"Embalse {codigo_saih} no disponible para análisis"
            )
        
        # Ejecutar análisis de riesgo
        analisis = risk_service.analizar_riesgo(
            codigo_saih=codigo_saih,
            fecha_inicio=request.fecha_inicio,
            horizonte_dias=request.horizonte_dias,
            umbral_minimo=request.umbral_minimo,
            umbral_maximo=request.umbral_maximo
        )
        
        return analisis
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al analizar riesgo de {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al analizar riesgo: {str(e)}")


@app.get(
    "/embalses/{codigo_saih}/recomendacion",
    response_model=RiesgoEmbalse,
    tags=["Riesgo"],
    summary="Recomendación rápida",
    description="Genera una recomendación operativa con parámetros por defecto"
)
async def obtener_recomendacion(codigo_saih: str):
    """Obtiene una recomendación operativa rápida."""
    try:
        # Validar que el embalse existe
        if not prediction_service.embalse_disponible(codigo_saih):
            raise HTTPException(
                status_code=404,
                detail=f"Embalse {codigo_saih} no disponible para análisis"
            )
        
        # Ejecutar análisis con parámetros por defecto
        analisis = risk_service.recomendacion_rapida(codigo_saih)
        
        return analisis
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al generar recomendación para {codigo_saih}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al generar recomendación: {str(e)}")


# ============================================================================
# ENDPOINTS DE INFORMACIÓN GEOGRÁFICA Y ORGANIZATIVA
# ============================================================================

@app.get(
    "/demarcaciones",
    response_model=List[Demarcacion],
    tags=["Geografía"],
    summary="Listar demarcaciones hidrográficas",
    description="Devuelve todas las demarcaciones hidrográficas con su información organizativa"
)
async def listar_demarcaciones():
    """Obtiene la lista de demarcaciones hidrográficas."""
    try:
        demarcaciones = data_loader.get_demarcaciones()
        return demarcaciones
    except Exception as e:
        logger.error(f"Error al listar demarcaciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener demarcaciones: {str(e)}")


@app.get(
    "/demarcaciones/{id_demarcacion}",
    response_model=Demarcacion,
    tags=["Geografía"],
    summary="Detalle de demarcación",
    description="Obtiene información detallada de una demarcación hidrográfica"
)
async def obtener_demarcacion(id_demarcacion: str):
    """Obtiene detalle de una demarcación."""
    try:
        demarcacion = data_loader.get_demarcacion_detail(id_demarcacion)
        if not demarcacion:
            raise HTTPException(status_code=404, detail=f"Demarcación {id_demarcacion} no encontrada")
        return demarcacion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener demarcación {id_demarcacion}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener demarcación: {str(e)}")


@app.get(
    "/demarcaciones/{id_demarcacion}/embalses",
    response_model=List[dict],
    tags=["Geografía"],
    summary="Embalses de una demarcación",
    description="Lista todos los embalses pertenecientes a una demarcación hidrográfica"
)
async def listar_embalses_demarcacion(id_demarcacion: str):
    """Obtiene embalses de una demarcación."""
    try:
        embalses = data_loader.get_embalses_by_demarcacion(id_demarcacion)
        return embalses
    except Exception as e:
        logger.error(f"Error al listar embalses de {id_demarcacion}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener embalses: {str(e)}")


@app.get(
    "/organismos",
    response_model=List[OrganismoGestor],
    tags=["Geografía"],
    summary="Listar organismos gestores",
    description="Devuelve todos los organismos gestores (Confederaciones y Administraciones Autonómicas)"
)
async def listar_organismos():
    """Obtiene la lista de organismos gestores."""
    try:
        organismos = data_loader.get_organismos()
        return organismos
    except Exception as e:
        logger.error(f"Error al listar organismos: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener organismos: {str(e)}")


@app.get(
    "/geografia/comunidades",
    response_model=List[Geografia],
    tags=["Geografía"],
    summary="Listar comunidades autónomas",
    description="Devuelve todas las comunidades autónomas con número de embalses"
)
async def listar_comunidades():
    """Obtiene la lista de comunidades autónomas."""
    try:
        comunidades = data_loader.get_comunidades_autonomas()
        return comunidades
    except Exception as e:
        logger.error(f"Error al listar comunidades: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener comunidades: {str(e)}")


@app.get(
    "/geografia/provincias",
    response_model=List[Geografia],
    tags=["Geografía"],
    summary="Listar provincias",
    description="Devuelve todas las provincias, opcionalmente filtradas por comunidad autónoma"
)
async def listar_provincias(
    id_ccaa: Optional[int] = Query(None, description="ID de comunidad autónoma para filtrar")
):
    """Obtiene la lista de provincias."""
    try:
        provincias = data_loader.get_provincias(id_ccaa)
        return provincias
    except Exception as e:
        logger.error(f"Error al listar provincias: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener provincias: {str(e)}")


# ============================================================================
# ENDPOINTS DE ESTADÍSTICAS Y ANÁLISIS AGREGADO
# ============================================================================

@app.get(
    "/estadisticas/ccaa/{id_ccaa}",
    response_model=EstadisticasRegion,
    tags=["Estadísticas"],
    summary="Estadísticas por comunidad autónoma",
    description="Calcula estadísticas agregadas de embalses en una comunidad autónoma"
)
async def estadisticas_ccaa(id_ccaa: int):
    """Obtiene estadísticas de una comunidad autónoma."""
    try:
        stats = data_loader.get_estadisticas_region('ccaa', id_ccaa)
        if not stats:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para CCAA {id_ccaa}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al calcular estadísticas CCAA {id_ccaa}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al calcular estadísticas: {str(e)}")


@app.get(
    "/estadisticas/provincia/{id_provincia}",
    response_model=EstadisticasRegion,
    tags=["Estadísticas"],
    summary="Estadísticas por provincia",
    description="Calcula estadísticas agregadas de embalses en una provincia"
)
async def estadisticas_provincia(id_provincia: int):
    """Obtiene estadísticas de una provincia."""
    try:
        stats = data_loader.get_estadisticas_region('provincia', id_provincia)
        if not stats:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para provincia {id_provincia}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al calcular estadísticas provincia {id_provincia}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al calcular estadísticas: {str(e)}")


@app.get(
    "/estadisticas/demarcacion/{id_demarcacion}",
    response_model=EstadisticasRegion,
    tags=["Estadísticas"],
    summary="Estadísticas por demarcación",
    description="Calcula estadísticas agregadas de embalses en una demarcación hidrográfica"
)
async def estadisticas_demarcacion(id_demarcacion: str):
    """Obtiene estadísticas de una demarcación."""
    try:
        stats = data_loader.get_estadisticas_region('demarcacion', id_demarcacion)
        if not stats:
            raise HTTPException(status_code=404, detail=f"No se encontraron datos para demarcación {id_demarcacion}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al calcular estadísticas demarcación {id_demarcacion}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al calcular estadísticas: {str(e)}")


@app.post(
    "/comparar",
    response_model=ComparacionResponse,
    tags=["Estadísticas"],
    summary="Comparar embalses",
    description="Compara niveles actuales y tendencias de múltiples embalses"
)
async def comparar_embalses(codigos_saih: List[str] = Query(..., description="Códigos de embalses a comparar")):
    """Compara múltiples embalses."""
    try:
        if len(codigos_saih) < 2:
            raise HTTPException(status_code=400, detail="Se requieren al menos 2 embalses para comparar")
        
        if len(codigos_saih) > 20:
            raise HTTPException(status_code=400, detail="Máximo 20 embalses para comparar")
        
        comparacion = data_loader.comparar_embalses(codigos_saih)
        return comparacion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al comparar embalses: {e}")
        raise HTTPException(status_code=500, detail=f"Error al comparar embalses: {str(e)}")


# ============================================================================
# EJECUTAR SERVIDOR (si se ejecuta directamente)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
