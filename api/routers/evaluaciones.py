"""
Router para endpoints de evaluación del sistema.
"""
from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta
import json

from ..models import (
    EvaluacionRequest, 
    EvaluacionResponse, 
    EstadisticasEvaluacion,
    PerfilEvaluacion
)
from ..data import db_connection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluaciones",
    tags=["Evaluaciones"],
    responses={
        500: {"description": "Error del servidor"}
    }
)


@router.post(
    "",
    response_model=EvaluacionResponse,
    summary="Registrar evaluación del sistema",
    description="""
    Registra una nueva evaluación del sistema AquaIA.
    
    **Perfiles disponibles:**
    - `tecnico`: Para ingenieros y analistas que usan el sistema diariamente
    - `gestion`: Para responsables de cuenca y toma de decisiones estratégicas
    
    **Preguntas por perfil:**
    
    **Perfil Técnico:**
    - `viz_claridad`: Claridad en la distinción visual entre histórico y predicción
    - `viz_incertidumbre`: Visualización de intervalos de confianza
    - `inter_zoom`: Fluidez de herramientas de zoom y selección temporal
    - `inter_navegacion`: Intuitividad en el acceso a detalles de embalses
    - `metricas_utilidad`: Utilidad de métricas de error (MAE, RMSE)
    - `metricas_suficiencia`: Suficiencia de métricas presentadas
    
    **Perfil Gestión:**
    - `lenguaje_claridad`: Claridad del lenguaje en recomendaciones
    - `lenguaje_profesionalidad`: Profesionalidad del lenguaje usado
    - `riesgos_utilidad`: Utilidad del sistema de clasificación de riesgos
    - `riesgos_priorizacion`: Efectividad para priorizar atención
    - `informes_estructura`: Adecuación de estructura de informes
    - `informes_contenido`: Contenido apropiado para distribución oficial
    - `alineacion_protocolos`: Alineación con protocolos de actuación
    """
)
def crear_evaluacion(
    evaluacion: EvaluacionRequest,
    request: Request
):
    """
    Registra una nueva evaluación del sistema.
    
    Args:
        evaluacion: Datos de la evaluación
        request: Request para obtener IP y user agent
        
    Returns:
        Confirmación con ID de la evaluación creada
    """
    try:
        # Obtener metadatos de la request
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent', '')
        
        # Convertir respuestas a JSON
        respuestas_json = json.dumps(evaluacion.respuestas)
        
        # Insertar evaluación
        query = """
            INSERT INTO evaluaciones (
                nombre, email, organizacion, perfil, anos_experiencia,
                respuestas, comentarios, ip_address, user_agent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, fecha_evaluacion, perfil
        """
        
        with db_connection.get_cursor() as cursor:
            cursor.execute(query, (
                evaluacion.nombre,
                evaluacion.email,
                evaluacion.organizacion,
                evaluacion.perfil.value,
                evaluacion.anos_experiencia,
                respuestas_json,
                evaluacion.comentarios,
                ip_address,
                user_agent
            ))
            row = cursor.fetchone()
        
        logger.info(f"Evaluación registrada: ID={row['id']}, Perfil={row['perfil']}")
        
        return EvaluacionResponse(
            id=row['id'],
            fecha_evaluacion=row['fecha_evaluacion'],
            perfil=row['perfil']
        )
        
    except Exception as e:
        logger.error(f"Error registrando evaluación: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error registrando evaluación: {str(e)}"
        )


@router.get(
    "/estadisticas",
    response_model=EstadisticasEvaluacion,
    summary="Obtener estadísticas de evaluaciones",
    description="Obtiene estadísticas agregadas y anonimizadas de todas las evaluaciones"
)
def obtener_estadisticas():
    """
    Obtiene estadísticas agregadas de las evaluaciones.
    
    Returns:
        Estadísticas completas anonimizadas
    """
    try:
        # Total de evaluaciones
        total_result = db_connection.execute_query("SELECT COUNT(*) as total FROM evaluaciones")
        total = total_result[0]['total'] if total_result else 0
        
        # Estadísticas por perfil
        por_perfil = {}
        
        for perfil in ['tecnico', 'gestion']:
            # Total por perfil
            count_result = db_connection.execute_query(
                "SELECT COUNT(*) as count FROM evaluaciones WHERE perfil = %s",
                (perfil,)
            )
            count = count_result[0]['count'] if count_result else 0
            
            # Promedios por pregunta para este perfil
            promedios_query = """
                SELECT key as pregunta, AVG((value::text)::numeric) as promedio
                FROM evaluaciones,
                     jsonb_each(respuestas)
                WHERE perfil = %s
                GROUP BY key
                ORDER BY key
            """
            promedios_result = db_connection.execute_query(promedios_query, (perfil,))
            promedios = {
                row['pregunta']: round(float(row['promedio']), 2) 
                for row in (promedios_result or [])
            }
            
            por_perfil[perfil] = {
                "total": count,
                "promedios": promedios
            }
        
        # Distribución de experiencia
        exp_query = """
            SELECT 
                CASE 
                    WHEN anos_experiencia IS NULL THEN 'No especificado'
                    WHEN anos_experiencia <= 5 THEN '0-5 años'
                    WHEN anos_experiencia <= 10 THEN '6-10 años'
                    WHEN anos_experiencia <= 20 THEN '11-20 años'
                    ELSE '>20 años'
                END as rango,
                COUNT(*) as cantidad
            FROM evaluaciones
            GROUP BY 
                CASE 
                    WHEN anos_experiencia IS NULL THEN 'No especificado'
                    WHEN anos_experiencia <= 5 THEN '0-5 años'
                    WHEN anos_experiencia <= 10 THEN '6-10 años'
                    WHEN anos_experiencia <= 20 THEN '11-20 años'
                    ELSE '>20 años'
                END
            ORDER BY 
                MIN(COALESCE(anos_experiencia, 999))
        """
        exp_result = db_connection.execute_query(exp_query)
        distribucion_experiencia = [
            {"rango": row['rango'], "cantidad": row['cantidad']}
            for row in (exp_result or [])
        ]
        
        # Comentarios recientes (últimos 10, anonimizados)
        comentarios_query = """
            SELECT 
                perfil,
                comentarios as comentario,
                fecha_evaluacion as fecha
            FROM evaluaciones
            WHERE comentarios IS NOT NULL AND comentarios != ''
            ORDER BY fecha_evaluacion DESC
            LIMIT 10
        """
        comentarios_result = db_connection.execute_query(comentarios_query)
        comentarios_recientes = [
            {
                "perfil": row['perfil'],
                "comentario": row['comentario'],
                "fecha": row['fecha'].isoformat()
            }
            for row in (comentarios_result or [])
        ]
        
        return {
            "total_evaluaciones": total,
            "por_perfil": por_perfil,
            "distribucion_experiencia": distribucion_experiencia,
            "comentarios_recientes": comentarios_recientes
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get(
    "/preguntas/{perfil}",
    summary="Obtener preguntas para un perfil",
    description="Obtiene el listado de preguntas según el perfil del evaluador"
)
def obtener_preguntas(perfil: PerfilEvaluacion):
    """
    Obtiene las preguntas de evaluación según el perfil.
    
    Args:
        perfil: Perfil del evaluador (tecnico o gestion)
        
    Returns:
        Lista de preguntas con sus IDs
    """
    preguntas = {
        "tecnico": [
            {
                "id": "viz_claridad",
                "pregunta": "¿Es clara la distinción visual entre la serie histórica y la predicción?",
                "categoria": "Visualización"
            },
            {
                "id": "viz_incertidumbre",
                "pregunta": "¿Los intervalos de confianza ayudan a evaluar la incertidumbre de las predicciones?",
                "categoria": "Visualización"
            },
            {
                "id": "inter_zoom",
                "pregunta": "¿Las herramientas de zoom y selección temporal responden con fluidez adecuada?",
                "categoria": "Interactividad"
            },
            {
                "id": "inter_navegacion",
                "pregunta": "¿Es intuitivo el acceso a los detalles de un embalse desde el mapa general?",
                "categoria": "Interactividad"
            },
            {
                "id": "metricas_utilidad",
                "pregunta": "¿Son útiles las métricas de error (MAE, RMSE) para validar la fiabilidad?",
                "categoria": "Métricas"
            },
            {
                "id": "metricas_suficiencia",
                "pregunta": "¿Considera suficientes las métricas presentadas para análisis técnico?",
                "categoria": "Métricas"
            }
        ],
        "gestion": [
            {
                "id": "lenguaje_claridad",
                "pregunta": "¿El lenguaje usado en las recomendaciones automáticas es claro y coherente?",
                "categoria": "Inteligibilidad"
            },
            {
                "id": "lenguaje_profesionalidad",
                "pregunta": "¿Considera profesional el lenguaje utilizado en los resúmenes ejecutivos?",
                "categoria": "Inteligibilidad"
            },
            {
                "id": "riesgos_utilidad",
                "pregunta": "¿La clasificación de riesgos (semáforo) es útil para la toma de decisiones?",
                "categoria": "Utilidad Operativa"
            },
            {
                "id": "riesgos_priorizacion",
                "pregunta": "¿Ayuda a priorizar eficazmente la atención sobre los embalses más críticos?",
                "categoria": "Utilidad Operativa"
            },
            {
                "id": "informes_estructura",
                "pregunta": "¿La estructura de los informes generados es adecuada para reuniones oficiales?",
                "categoria": "Informes"
            },
            {
                "id": "informes_contenido",
                "pregunta": "¿El contenido de los informes es apropiado para distribución oficial?",
                "categoria": "Informes"
            },
            {
                "id": "alineacion_protocolos",
                "pregunta": "¿Las recomendaciones se ajustan a los protocolos de actuación vigentes?",
                "categoria": "Alineación"
            }
        ]
    }
    
    return {
        "perfil": perfil.value,
        "preguntas": preguntas[perfil.value]
    }
