"""
Router para endpoints de generación de informes.
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
from typing import List, Optional
import logging
from pathlib import Path

from ..models import InformeRequest, InformeResponse
from ..services.informe import informe_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/informes",
    tags=["Informes"],
    responses={
        404: {"description": "Informe no encontrado"},
        500: {"description": "Error generando informe"}
    }
)


@router.post(
    "/generar",
    response_model=InformeResponse,
    summary="Generar informe de predicción",
    description="""
    Genera un informe completo en PDF y HTML con las predicciones y recomendaciones
    para un embalse específico.
    
    **Tipos de informe:**
    - **DIARIO**: Informe operativo del día con análisis de situación actual y próximas 24-48h
    - **SEMANAL**: Informe estratégico con evolución de la última semana y predicciones a 30/90/180 días
    
    **Características:**
    - Diseño profesional sin elementos decorativos
    - Análisis técnico de tendencias y riesgos
    - Conclusiones basadas en datos cuantitativos
    - Recomendaciones operativas accionables
    - Evaluación de escenarios y riesgos
    - Métricas de calidad del modelo predictivo
    
    **Secciones del informe DIARIO:**
    1. Resumen ejecutivo
    2. Estado operacional actual
    3. Análisis y predicción (24-48h)
    4. Evaluación de riesgos
    5. Recomendaciones operativas
    6. Fiabilidad de predicciones
    7. Información del documento
    
    **Secciones del informe SEMANAL:**
    1. Resumen ejecutivo
    2. Evolución durante la semana
    3. Estado operacional actual
    4. Predicción y análisis de escenarios
    5. Evaluación de riesgos
    6. Recomendaciones estratégicas
    7. Calidad y confiabilidad del modelo
    8. Metadatos y trazabilidad
    
    **Formatos generados:**
    - HTML: Para previsualización en navegador
    - PDF: Para descarga y distribución (requiere WeasyPrint)
    """
)
async def generar_informe(request: InformeRequest):
    """
    Genera un informe completo de predicción para un embalse.
    
    Args:
        request: Datos del embalse y predicciones
        
    Returns:
        InformeResponse con URLs de acceso a los informes generados
    """
    try:
        tipo_informe = request.tipo_informe.value if hasattr(request.tipo_informe, 'value') else request.tipo_informe
        logger.info(f"Generando informe {tipo_informe} para embalse {request.embalse_id}")
        
        # Convertir request a diccionario para el servicio
        data = request.model_dump()
        
        # Generar informe con análisis LLM integrado
        resultado = await informe_service.generar_informe_con_llm(data)
        
        # Construir response
        response = InformeResponse(
            success=True,
            pdf_url=resultado['pdf_url'],
            html_url=resultado['html_url'],
            informe_id=resultado['informe_id'],
            fecha_generacion=request.fecha_generacion,
            metadata={
                "embalse": request.embalse_id,
                "tipo_informe": tipo_informe,
                "usuario": request.usuario,
                "model_version": request.model_version,
                "llm_usado": str(resultado['metadata'].get('llm_usado', False))
            }
        )
        
        logger.info(f"Informe {tipo_informe} generado exitosamente: {resultado['informe_id']}")
        return response
        
    except Exception as e:
        logger.error(f"Error generando informe: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando informe: {str(e)}"
        )


@router.get(
    "/preview/{informe_id}",
    response_class=HTMLResponse,
    summary="Previsualizar informe HTML",
    description="Muestra el informe generado en formato HTML para previsualización en el navegador."
)
async def preview_informe(informe_id: str):
    """
    Muestra la vista previa HTML de un informe.
    
    Args:
        informe_id: ID del informe (sin extensión .html)
        
    Returns:
        Contenido HTML del informe
    """
    try:
        # Remover extensión si la tiene
        if informe_id.endswith('.html'):
            informe_id = informe_id[:-5]
        
        # Obtener archivo
        filepath = informe_service.obtener_informe(informe_id, formato='html')
        
        if not filepath:
            raise HTTPException(
                status_code=404,
                detail=f"Informe {informe_id} no encontrado"
            )
        
        # Leer y devolver contenido
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return HTMLResponse(content=content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mostrando preview: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error mostrando informe: {str(e)}"
        )


@router.get(
    "/download/{informe_id}",
    response_class=FileResponse,
    summary="Descargar informe PDF",
    description="Descarga el informe en formato PDF."
)
async def download_informe(informe_id: str):
    """
    Descarga un informe en formato PDF.
    
    Args:
        informe_id: ID del informe (sin extensión .pdf)
        
    Returns:
        Archivo PDF para descarga
    """
    try:
        # Remover extensión si la tiene
        if informe_id.endswith('.pdf'):
            informe_id = informe_id[:-4]
        
        # Obtener archivo
        filepath = informe_service.obtener_informe(informe_id, formato='pdf')
        
        if not filepath:
            raise HTTPException(
                status_code=404,
                detail=f"Informe PDF {informe_id} no encontrado. Verifica que WeasyPrint esté instalado."
            )
        
        # Devolver archivo para descarga
        return FileResponse(
            path=filepath,
            filename=f"{informe_id}.pdf",
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando informe: {str(e)}"
        )


@router.get(
    "/listar",
    summary="Listar informes generados",
    description="Lista todos los informes generados, opcionalmente filtrados por embalse."
)
async def listar_informes(embalse_id: Optional[str] = None):
    """
    Lista los informes generados.
    
    Args:
        embalse_id: Filtrar por embalse (opcional)
        
    Returns:
        Lista de metadatos de informes
    """
    try:
        informes = informe_service.listar_informes(embalse_id)
        
        return {
            "total": len(informes),
            "embalse_filtro": embalse_id,
            "informes": informes
        }
        
    except Exception as e:
        logger.error(f"Error listando informes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listando informes: {str(e)}"
        )


@router.delete(
    "/{informe_id}",
    summary="Eliminar informe",
    description="Elimina un informe y todos sus archivos asociados (HTML, PDF, metadata)."
)
async def eliminar_informe(informe_id: str):
    """
    Elimina un informe y sus archivos asociados.
    
    Args:
        informe_id: ID del informe a eliminar
        
    Returns:
        Confirmación de eliminación
    """
    try:
        import os
        
        eliminados = []
        
        # Eliminar HTML
        html_path = informe_service.obtener_informe(informe_id, formato='html')
        if html_path and html_path.exists():
            os.remove(html_path)
            eliminados.append('html')
        
        # Eliminar PDF
        pdf_path = informe_service.obtener_informe(informe_id, formato='pdf')
        if pdf_path and pdf_path.exists():
            os.remove(pdf_path)
            eliminados.append('pdf')
        
        # Eliminar metadata
        metadata_path = informe_service.output_dir / f"{informe_id}_metadata.json"
        if metadata_path.exists():
            os.remove(metadata_path)
            eliminados.append('metadata')
        
        if not eliminados:
            raise HTTPException(
                status_code=404,
                detail=f"Informe {informe_id} no encontrado"
            )
        
        logger.info(f"Informe eliminado: {informe_id}")
        
        return {
            "success": True,
            "informe_id": informe_id,
            "archivos_eliminados": eliminados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando informe: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando informe: {str(e)}"
        )
