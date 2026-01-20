from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import date, datetime, timedelta
import logging

from ..models import (
    DashboardKPIs,
    EmbalseActual,
    Alerta,
    AlertasResponse,
    ConfiguracionAlerta
)
from ..data import data_loader
from ..services.recomendacion import recomendacion_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    responses={
        404: {"description": "Recurso no encontrado"},
        500: {"description": "Error interno del servidor"}
    }
)


@router.get(
    "/kpis",
    response_model=DashboardKPIs,
    summary="Obtener KPIs agregados del sistema",
    description="Devuelve indicadores clave de rendimiento (KPIs) del sistema de embalses."
)
async def obtener_kpis_dashboard(
    fecha_referencia: Optional[str] = Query(
        None, 
        description="Fecha de referencia para simular dashboard (YYYY-MM-DD)"
    )
):
    """Obtiene los KPIs agregados del sistema para el dashboard."""
    try:
        # Convertir fecha si se proporciona
        fecha_ref = None
        if fecha_referencia:
            try:
                fecha_ref = datetime.strptime(fecha_referencia, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )
        
        embalses = data_loader.get_embalses_list()
        num_embalses = len(embalses)
        
        capacidad_total = 0.0
        nivel_total_actual = 0.0
        niveles_porcentaje = []
        embalses_criticos = 0
        
        for embalse in embalses:
            codigo = embalse['codigo_saih']
            
            if fecha_ref:
                historico = data_loader.get_historico(codigo, fecha_ref.strftime('%Y-%m-%d'), fecha_ref.strftime('%Y-%m-%d'))
                if not historico.empty:
                    nivel_actual = float(historico.iloc[0]['nivel'])
                else:
                    continue
            else:
                resumen = data_loader.get_resumen(codigo)
                nivel_actual = resumen['ultimo_nivel']
            
            nivel_maximo = embalse.get('nivel_maximo')
            
            if nivel_maximo and nivel_maximo > 0:
                capacidad_total += nivel_maximo
                nivel_total_actual += nivel_actual
                porcentaje = (nivel_actual / nivel_maximo) * 100
                niveles_porcentaje.append(porcentaje)
                
                if porcentaje < 30 or porcentaje > 95:
                    embalses_criticos += 1
        
        porcentaje_llenado_promedio = sum(niveles_porcentaje) / len(niveles_porcentaje) if niveles_porcentaje else 0
        
        tendencia = "estable"
        if fecha_ref:
            fecha_anterior = fecha_ref - timedelta(days=7)
        else:
            fecha_anterior = datetime.now().date() - timedelta(days=7)
        
        nivel_anterior_total = 0.0
        for embalse in embalses:
            codigo = embalse['codigo_saih']
            historico = data_loader.get_historico(
                codigo, 
                fecha_anterior.strftime('%Y-%m-%d'), 
                fecha_anterior.strftime('%Y-%m-%d')
            )
            if not historico.empty:
                nivel_anterior_total += float(historico.iloc[0]['nivel'])
        
        if nivel_anterior_total > 0:
            cambio_porcentual = ((nivel_total_actual - nivel_anterior_total) / nivel_anterior_total) * 100
            if cambio_porcentual > 2:
                tendencia = "aumento"
            elif cambio_porcentual < -2:
                tendencia = "descenso"
        
        num_alertas_activas = embalses_criticos
        
        return {
            "fecha_referencia": fecha_ref.strftime('%Y-%m-%d') if fecha_ref else datetime.now().strftime('%Y-%m-%d'),
            "num_embalses": num_embalses,
            "capacidad_total": round(capacidad_total, 2),
            "nivel_total_actual": round(nivel_total_actual, 2),
            "porcentaje_llenado_promedio": round(porcentaje_llenado_promedio, 2),
            "num_embalses_criticos": embalses_criticos,
            "num_alertas_activas": num_alertas_activas,
            "tendencia": tendencia
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener KPIs del dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular KPIs: {str(e)}"
        )


@router.get(
    "/embalses/{codigo_saih}/actual",
    response_model=EmbalseActual,
    summary="Obtener datos actuales de un embalse",
    description="""
    Devuelve los datos actuales de un embalse para una fecha de referencia específica.
    
    **Datos incluidos:**
    - Información básica del embalse
    - Nivel actual
    - Porcentaje de llenado
    - Datos meteorológicos recientes
    - Estadísticas de los últimos 30 días
    
    **Simulación temporal:**
    Si se proporciona `fecha_referencia`, devuelve los datos como si estuvieras en esa fecha.
    Esto permite simular el dashboard en cualquier momento histórico.
    """
)
async def obtener_datos_actuales_embalse(
    codigo_saih: str,
    fecha_referencia: Optional[str] = Query(
        None,
        description="Fecha de referencia para simular dashboard (YYYY-MM-DD)"
    )
):
    """
    Obtiene los datos actuales de un embalse para una fecha específica.
    
    Args:
        codigo_saih: Código SAIH del embalse
        fecha_referencia: Fecha opcional para simular datos históricos
        
    Returns:
        EmbalseActual con todos los datos del embalse para esa fecha
    """
    try:
        # Validar que el embalse existe
        if not data_loader.embalse_exists(codigo_saih):
            raise HTTPException(
                status_code=404,
                detail=f"Embalse {codigo_saih} no encontrado"
            )
        
        # Convertir fecha si se proporciona
        fecha_ref = None
        if fecha_referencia:
            try:
                fecha_ref = datetime.strptime(fecha_referencia, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )
        
        # Obtener información del embalse
        embalses = data_loader.get_embalses_list()
        embalse_info = next((e for e in embalses if e['codigo_saih'] == codigo_saih), None)
        
        if not embalse_info:
            raise HTTPException(
                status_code=404,
                detail=f"Información del embalse {codigo_saih} no disponible"
            )
        
        # Obtener nivel actual
        if fecha_ref:
            # Buscar nivel en fecha específica
            historico = data_loader.get_historico(
                codigo_saih,
                fecha_ref.strftime('%Y-%m-%d'),
                fecha_ref.strftime('%Y-%m-%d')
            )
            if historico.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No hay datos disponibles para la fecha {fecha_referencia}"
                )
            nivel_actual = float(historico.iloc[0]['nivel'])
            precipitacion_actual = float(historico.iloc[0].get('precipitacion', 0)) if 'precipitacion' in historico.columns else None
            temperatura_actual = float(historico.iloc[0].get('temperatura', 0)) if 'temperatura' in historico.columns else None
            caudal_actual = float(historico.iloc[0].get('caudal_promedio', 0)) if 'caudal_promedio' in historico.columns else None
            fecha_actual = fecha_ref.strftime('%Y-%m-%d')
        else:
            # Usar último nivel disponible
            resumen = data_loader.get_resumen(codigo_saih)
            nivel_actual = resumen['ultimo_nivel']
            fecha_actual = resumen['fecha_ultimo_registro']
            
            # Obtener datos complementarios de la última fecha
            historico = data_loader.get_historico(
                codigo_saih,
                fecha_actual,
                fecha_actual
            )
            if not historico.empty:
                precipitacion_actual = float(historico.iloc[0].get('precipitacion', 0)) if 'precipitacion' in historico.columns else None
                temperatura_actual = float(historico.iloc[0].get('temperatura', 0)) if 'temperatura' in historico.columns else None
                caudal_actual = float(historico.iloc[0].get('caudal_promedio', 0)) if 'caudal_promedio' in historico.columns else None
            else:
                precipitacion_actual = None
                temperatura_actual = None
                caudal_actual = None
        
        # Calcular porcentaje de llenado
        nivel_maximo = embalse_info.get('nivel_maximo')
        porcentaje_llenado = (nivel_actual / nivel_maximo * 100) if nivel_maximo and nivel_maximo > 0 else None
        
        # Obtener estadísticas de los últimos 30 días
        fecha_inicio_stats = (datetime.strptime(fecha_actual, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
        historico_30d = data_loader.get_historico(codigo_saih, fecha_inicio_stats, fecha_actual)
        
        if not historico_30d.empty:
            nivel_min_30d = float(historico_30d['nivel'].min())
            nivel_max_30d = float(historico_30d['nivel'].max())
            nivel_medio_30d = float(historico_30d['nivel'].mean())
            variacion_30d = nivel_actual - float(historico_30d.iloc[0]['nivel'])
            
            # Precipitación acumulada últimos 30 días
            precipitacion_acumulada_30d = float(historico_30d['precipitacion'].sum()) if 'precipitacion' in historico_30d.columns else None
        else:
            nivel_min_30d = None
            nivel_max_30d = None
            nivel_medio_30d = None
            variacion_30d = None
            precipitacion_acumulada_30d = None
        
        # Determinar estado del embalse
        if porcentaje_llenado is not None:
            if porcentaje_llenado >= 95:
                estado = "critico_alto"
            elif porcentaje_llenado >= 80:
                estado = "alto"
            elif porcentaje_llenado >= 30:
                estado = "normal"
            elif porcentaje_llenado >= 20:
                estado = "bajo"
            else:
                estado = "critico_bajo"
        else:
            estado = "desconocido"
        
        return {
            "codigo_saih": codigo_saih,
            "ubicacion": embalse_info['ubicacion'],
            "municipio": embalse_info.get('municipio'),
            "provincia": embalse_info.get('provincia'),
            "comunidad_autonoma": embalse_info.get('comunidad_autonoma'),
            "demarcacion": embalse_info.get('demarcacion'),
            "fecha_referencia": fecha_actual,
            "nivel_actual": round(nivel_actual, 2),
            "nivel_maximo": round(nivel_maximo, 2) if nivel_maximo else None,
            "porcentaje_llenado": round(porcentaje_llenado, 2) if porcentaje_llenado else None,
            "estado": estado,
            "precipitacion_actual": round(precipitacion_actual, 2) if precipitacion_actual else None,
            "temperatura_actual": round(temperatura_actual, 2) if temperatura_actual else None,
            "caudal_actual": round(caudal_actual, 2) if caudal_actual else None,
            "nivel_min_30d": round(nivel_min_30d, 2) if nivel_min_30d else None,
            "nivel_max_30d": round(nivel_max_30d, 2) if nivel_max_30d else None,
            "nivel_medio_30d": round(nivel_medio_30d, 2) if nivel_medio_30d else None,
            "variacion_30d": round(variacion_30d, 2) if variacion_30d else None,
            "precipitacion_acumulada_30d": round(precipitacion_acumulada_30d, 2) if precipitacion_acumulada_30d else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener datos actuales de {codigo_saih}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener datos actuales: {str(e)}"
        )


@router.get(
    "/alertas",
    response_model=AlertasResponse,
    summary="Obtener alertas activas del sistema",
    description="""
    Devuelve las alertas activas del sistema de embalses.
    
    **Tipos de alertas:**
    - **NIVEL_BAJO**: Embalse por debajo del 30% de capacidad
    - **NIVEL_CRITICO_BAJO**: Embalse por debajo del 20% de capacidad
    - **NIVEL_ALTO**: Embalse por encima del 80% de capacidad
    - **NIVEL_CRITICO_ALTO**: Embalse por encima del 95% de capacidad
    - **PREDICCION_RIESGO**: Predicción indica riesgo en los próximos días
    
    **Filtros disponibles:**
    - Por severidad (info, warning, error, critical)
    - Por tipo de alerta
    - Por demarcación
    """
)
async def obtener_alertas(
    fecha_referencia: Optional[str] = Query(
        None,
        description="Fecha de referencia para alertas (YYYY-MM-DD)"
    ),
    severidad: Optional[str] = Query(
        None,
        description="Filtrar por severidad: info, warning, error, critical"
    ),
    tipo: Optional[str] = Query(
        None,
        description="Filtrar por tipo de alerta"
    ),
    demarcacion: Optional[str] = Query(
        None,
        description="Filtrar por demarcación hidrográfica"
    )
):
    """
    Obtiene las alertas activas del sistema.
    
    Args:
        fecha_referencia: Fecha opcional para simular alertas históricas
        severidad: Filtro por severidad
        tipo: Filtro por tipo de alerta
        demarcacion: Filtro por demarcación
        
    Returns:
        AlertasResponse con lista de alertas activas
    """
    try:
        # Convertir fecha si se proporciona
        fecha_ref = None
        if fecha_referencia:
            try:
                fecha_ref = datetime.strptime(fecha_referencia, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha inválido. Use YYYY-MM-DD"
                )
        else:
            fecha_ref = datetime.now().date()
        
        # Obtener lista de embalses
        embalses = data_loader.get_embalses_list()
        
        # Generar alertas basadas en el estado actual
        alertas = []
        
        for embalse in embalses:
            codigo = embalse['codigo_saih']
            
            # Filtrar por demarcación si se especifica
            if demarcacion and embalse.get('demarcacion') != demarcacion:
                continue
            
            try:
                # Obtener nivel actual
                historico = data_loader.get_historico(
                    codigo,
                    fecha_ref.strftime('%Y-%m-%d'),
                    fecha_ref.strftime('%Y-%m-%d')
                )
                
                if historico.empty:
                    continue
                
                nivel_actual = float(historico.iloc[0]['nivel'])
                nivel_maximo = embalse.get('nivel_maximo')
                
                if not nivel_maximo or nivel_maximo <= 0:
                    continue
                
                porcentaje = (nivel_actual / nivel_maximo) * 100
                
                # Generar alertas según el nivel
                if porcentaje < 20:
                    alerta = {
                        "id": f"{codigo}_nivel_critico_bajo",
                        "codigo_saih": codigo,
                        "ubicacion": embalse['ubicacion'],
                        "tipo": "NIVEL_CRITICO_BAJO",
                        "severidad": "critical",
                        "mensaje": f"Nivel crítico bajo: {porcentaje:.1f}% de capacidad",
                        "valor_actual": round(nivel_actual, 2),
                        "umbral": round(nivel_maximo * 0.2, 2),
                        "fecha_deteccion": fecha_ref.strftime('%Y-%m-%d'),
                        "demarcacion": embalse.get('demarcacion')
                    }
                    
                    # Aplicar filtro de severidad
                    if not severidad or severidad == "critical":
                        alertas.append(alerta)
                
                elif porcentaje < 30:
                    alerta = {
                        "id": f"{codigo}_nivel_bajo",
                        "codigo_saih": codigo,
                        "ubicacion": embalse['ubicacion'],
                        "tipo": "NIVEL_BAJO",
                        "severidad": "warning",
                        "mensaje": f"Nivel bajo: {porcentaje:.1f}% de capacidad",
                        "valor_actual": round(nivel_actual, 2),
                        "umbral": round(nivel_maximo * 0.3, 2),
                        "fecha_deteccion": fecha_ref.strftime('%Y-%m-%d'),
                        "demarcacion": embalse.get('demarcacion')
                    }
                    
                    if not severidad or severidad == "warning":
                        alertas.append(alerta)
                
                elif porcentaje > 95:
                    alerta = {
                        "id": f"{codigo}_nivel_critico_alto",
                        "codigo_saih": codigo,
                        "ubicacion": embalse['ubicacion'],
                        "tipo": "NIVEL_CRITICO_ALTO",
                        "severidad": "critical",
                        "mensaje": f"Nivel crítico alto: {porcentaje:.1f}% de capacidad",
                        "valor_actual": round(nivel_actual, 2),
                        "umbral": round(nivel_maximo * 0.95, 2),
                        "fecha_deteccion": fecha_ref.strftime('%Y-%m-%d'),
                        "demarcacion": embalse.get('demarcacion')
                    }
                    
                    if not severidad or severidad == "critical":
                        alertas.append(alerta)
                
                elif porcentaje > 80:
                    alerta = {
                        "id": f"{codigo}_nivel_alto",
                        "codigo_saih": codigo,
                        "ubicacion": embalse['ubicacion'],
                        "tipo": "NIVEL_ALTO",
                        "severidad": "warning",
                        "mensaje": f"Nivel alto: {porcentaje:.1f}% de capacidad",
                        "valor_actual": round(nivel_actual, 2),
                        "umbral": round(nivel_maximo * 0.8, 2),
                        "fecha_deteccion": fecha_ref.strftime('%Y-%m-%d'),
                        "demarcacion": embalse.get('demarcacion')
                    }
                    
                    if not severidad or severidad == "warning":
                        alertas.append(alerta)
            
            except Exception as e:
                logger.warning(f"Error al procesar alertas para {codigo}: {e}")
                continue
        
        # Aplicar filtro de tipo si se especifica
        if tipo:
            alertas = [a for a in alertas if a['tipo'] == tipo]
        
        # Ordenar por severidad (critical > error > warning > info)
        severidad_orden = {'critical': 0, 'error': 1, 'warning': 2, 'info': 3}
        alertas.sort(key=lambda x: severidad_orden.get(x['severidad'], 4))
        
        return {
            "fecha_referencia": fecha_ref.strftime('%Y-%m-%d'),
            "total_alertas": len(alertas),
            "alertas_por_severidad": {
                "critical": len([a for a in alertas if a['severidad'] == 'critical']),
                "error": len([a for a in alertas if a['severidad'] == 'error']),
                "warning": len([a for a in alertas if a['severidad'] == 'warning']),
                "info": len([a for a in alertas if a['severidad'] == 'info'])
            },
            "alertas": alertas
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener alertas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener alertas: {str(e)}"
        )
