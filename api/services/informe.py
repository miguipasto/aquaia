"""
Servicio para generación de informes PDF/HTML de predicciones de embalses.
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
import uuid
import json
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from .llm_service import llm_service
from .prediction import prediction_service
from .risk import RiskService
from ..data import data_loader
from ..config import settings

logger = logging.getLogger(__name__)


class InformeService:
    """Servicio de generación de informes en PDF y HTML."""
    
    def __init__(self):
        """Inicializa el servicio de informes."""
        # Directorio de plantillas
        self.template_dir = Path(__file__).parent.parent / "templates"
        
        # Directorio de salida para informes generados
        self.output_dir = Path(__file__).parent.parent / "informes_generados"
        # Crear la carpeta si no existe (incluye carpetas padre si es necesario)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        logger.info(f"InformeService inicializado. Templates: {self.template_dir}, Output: {self.output_dir}")
    
    def _generar_id_informe(self, embalse_id: str, fecha: datetime, tipo: str = "") -> str:
        """
        Genera un ID único para el informe incluyendo el tipo.
        
        Args:
            embalse_id: ID del embalse
            fecha: Fecha de generación
            tipo: Tipo de informe (diario, semanal)
            
        Returns:
            ID único del informe
        """
        fecha_str = fecha.strftime('%Y%m%d_%H%M%S')
        prefix = f"INF_{tipo.upper()}_" if tipo else "INF_"
        return f"{prefix}{embalse_id}_{fecha_str}"
    
    def _generar_graficas(self, data: Dict) -> Dict[str, str]:
        """
        Genera gráficas basadas en los datos y las devuelve como base64.
        """
        graficas = {}
        try:
            # Gráfica de evolución semanal (si hay datos históricos)
            if data.get('datos_historicos_semana'):
                df_hist = pd.DataFrame(data['datos_historicos_semana'])
                if not df_hist.empty and 'fecha' in df_hist.columns and 'nivel' in df_hist.columns:
                    plt.figure(figsize=(10, 5))
                    plt.plot(pd.to_datetime(df_hist['fecha']), df_hist['nivel'], marker='o', linestyle='-', color='#2c3e50')
                    plt.title('Evolución de Nivel - Última Semana')
                    plt.xlabel('Fecha')
                    plt.ylabel('Nivel (hm³)')
                    plt.grid(True, linestyle='--', alpha=0.7)
                    plt.tight_layout()
                    
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', dpi=100)
                    plt.close()
                    graficas['evolucion_semanal'] = base64.b64encode(buf.getvalue()).decode('utf-8')

            # Gráfica de Predicción
            if data.get('prediccion'):
                pred = data['prediccion']
                fechas = ['Hoy', '30d', '90d', '180d']
                niveles = [
                    data.get('datos_actual', {}).get('nivel_actual_msnm', 0),
                    pred.get('nivel_30d', 0),
                    pred.get('nivel_90d', 0),
                    pred.get('nivel_180d', 0)
                ]
                
                plt.figure(figsize=(10, 5))
                plt.bar(fechas, niveles, color=['#3498db', '#e67e22', '#e74c3c', '#c0392b'], alpha=0.8)
                plt.title('Proyección de Niveles (msnm)')
                plt.ylabel('Nivel (msnm)')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Añadir etiquetas de valor
                for i, v in enumerate(niveles):
                    plt.text(i, v + 0.1, f"{v:.2f}", ha='center', fontweight='bold')
                
                plt.tight_layout()
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                plt.close()
                graficas['proyeccion'] = base64.b64encode(buf.getvalue()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Error generando gráficas: {e}")
            
        return graficas

    def _calcular_semaforo_nivel(self, porcentaje: float, percentil_20: float, percentil_80: float) -> str:
        """
        Calcula el estado semáforo del nivel del embalse.
        
        Args:
            porcentaje: Porcentaje de capacidad actual
            percentil_20: Percentil 20 histórico
            percentil_80: Percentil 80 histórico
            
        Returns:
            Código de color: 'verde', 'amarillo', 'rojo'
        """
        if porcentaje < percentil_20:
            return 'rojo'
        elif porcentaje > percentil_80:
            return 'verde'
        else:
            return 'amarillo'
    
    def generar_html(self, data: Dict) -> tuple[str, str, str]:
        """
        Genera un informe HTML a partir de los datos.
        
        Args:
            data: Diccionario con todos los datos del informe
            
        Returns:
            Tuple con (ruta_archivo, contenido_html, informe_id)
        """
        try:
            # Determinar qué plantilla usar
            tipo_informe = data.get('tipo_informe', 'diario')
            
            if tipo_informe == 'semanal':
                template_name = 'informe_semanal_template.html'
            else:
                template_name = 'informe_diario_template.html'
            
            # Generar gráficas y añadirlas a los datos
            data['graficas'] = self._generar_graficas(data)
            
            # Cargar plantilla
            template = self.env.get_template(template_name)
            
            # Renderizar
            html_content = template.render(**data)
            
            # Generar ID y nombre de archivo
            informe_id = self._generar_id_informe(data['embalse_id'], data['fecha_generacion'], tipo_informe)
            filename = f"{informe_id}.html"
            filepath = self.output_dir / filename
            
            # Guardar archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML generado ({tipo_informe}): {filepath}")
            return str(filepath), html_content, informe_id
            
        except Exception as e:
            logger.error(f"Error generando HTML: {e}")
            raise
    
    def generar_pdf(self, html_content: str, informe_id: str) -> str:
        """
        Genera un PDF a partir del contenido HTML.
        
        Args:
            html_content: Contenido HTML a convertir
            informe_id: ID del informe
            
        Returns:
            Ruta del archivo PDF generado
        """
        try:
            from weasyprint import HTML, CSS
            
            filename = f"{informe_id}.pdf"
            filepath = self.output_dir / filename
            
            # Configurar CSS adicional para impresión
            css = CSS(string='''
                @page {
                    size: A4;
                    margin: 2cm;
                }
                body {
                    font-size: 11pt;
                }
            ''')
            
            # Generar PDF
            HTML(string=html_content).write_pdf(
                str(filepath),
                stylesheets=[css]
            )
            
            logger.info(f"PDF generado: {filepath}")
            return str(filepath)
            
        except ImportError:
            logger.warning("WeasyPrint no disponible. PDF no generado.")
            return ""
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return ""
    
    def generar_informe_completo(self, data: Dict) -> Dict[str, str]:
        """
        Genera informe completo en HTML y PDF.
        
        Args:
            data: Diccionario con todos los datos del informe
            
        Returns:
            Diccionario con rutas y URLs de los archivos generados
        """
        try:
            # Asegurar datos consistentes
            data = self._completar_datos_informe(data)
            
            tipo_informe = data.get('tipo_informe', 'diario')
            logger.info(f"Generando informe {tipo_informe} para embalse {data.get('embalse_id')}")
            
            # Generar HTML (ahora devuelve informe_id también)
            html_path, html_content, informe_id = self.generar_html(data)
            
            # Generar PDF (si WeasyPrint está disponible)
            pdf_path = self.generar_pdf(html_content, informe_id)
            
            # Generar URLs relativas para la API
            html_url = f"/api/informes/preview/{informe_id}.html"
            pdf_url = f"/api/informes/download/{informe_id}.pdf" if pdf_path else None
            
            # Guardar metadatos para auditoría
            metadata = {
                "informe_id": informe_id,
                "tipo_informe": tipo_informe,
                "embalse_id": data['embalse_id'],
                "nombre_embalse": data['nombre_embalse'],
                "fecha_generacion": data['fecha_generacion'].isoformat(),
                "fecha_inicio_periodo": data.get('fecha_inicio_periodo').isoformat() if data.get('fecha_inicio_periodo') else None,
                "fecha_fin_periodo": data.get('fecha_fin_periodo').isoformat() if data.get('fecha_fin_periodo') else None,
                "model_version": data['model_version'],
                "usuario": data['usuario'],
                "html_path": html_path,
                "pdf_path": pdf_path if pdf_path else None,
                "llm_usado": bool(data.get('analisis_llm'))
            }
            
            self._guardar_metadata(informe_id, metadata)
            
            return {
                "informe_id": informe_id,
                "html_path": html_path,
                "pdf_path": pdf_path,
                "html_url": html_url,
                "pdf_url": pdf_url,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error generando informe completo: {e}")
            raise
    
    async def generar_informe_con_llm(self, data: Dict) -> Dict[str, str]:
        """
        Genera informe completo con análisis de LLM integrado.
        
        Args:
            data: Diccionario con todos los datos del informe
            
        Returns:
            Diccionario con rutas y URLs de los archivos generados
        """
        try:
            tipo_informe = data.get('tipo_informe', 'diario')
            logger.info(f"Generando informe {tipo_informe} con análisis LLM para embalse {data.get('embalse_id')}")
            
            # Generar análisis con LLM según tipo de informe
            if tipo_informe == 'semanal':
                analisis_llm = await llm_service.generar_analisis_informe_semanal(
                    datos_actual=data.get('datos_actual', {}),
                    datos_historicos_semana=data.get('datos_historicos_semana', []),
                    prediccion=data.get('prediccion', {}),
                    riesgos=data.get('riesgos', {}),
                    escenarios=data.get('escenarios', {}),
                    metricas=data.get('metricas_modelo', {})
                )
            else:  # diario
                analisis_llm = await llm_service.generar_analisis_informe_diario(
                    datos_actual=data.get('datos_actual', {}),
                    prediccion=data.get('prediccion', {}),
                    riesgos=data.get('riesgos', {}),
                    metricas=data.get('metricas_modelo', {})
                )
            
            # Agregar análisis LLM a los datos
            data['analisis_llm'] = analisis_llm
            
            # Generar informe con análisis incluido
            return self.generar_informe_completo(data)
            
        except Exception as e:
            logger.error(f"Error generando informe con LLM: {e}")
            # Si falla el LLM, generar informe sin análisis
            logger.warning("Generando informe sin análisis LLM debido a error")
            return self.generar_informe_completo(data)
    
    def _guardar_metadata(self, informe_id: str, metadata: Dict):
        """
        Guarda metadatos del informe para auditoría.
        
        Args:
            informe_id: ID del informe
            metadata: Diccionario con metadatos
        """
        try:
            import json
            metadata_file = self.output_dir / f"{informe_id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Metadatos guardados: {metadata_file}")
        except Exception as e:
            logger.error(f"Error guardando metadatos: {e}")

    def _completar_datos_informe(self, data: Dict) -> Dict:
        """
        Completa los datos del informe si faltan campos, asegurando consistencia con la web.
        """
        # Asegurar metadatos básicos de configuración desde .env
        if not data.get('model_version'):
            data['model_version'] = settings.report_model_version
            logger.info(f"Usando model_version desde .env: {settings.report_model_version}")
        
        if not data.get('usuario'):
            data['usuario'] = settings.report_default_user
            logger.info(f"Usando usuario desde .env: {settings.report_default_user}")
        
        # Asegurar idioma por defecto
        if not data.get('idioma'):
            data['idioma'] = 'es'
        
        # Asegurar nombre_embalse si falta
        if not data.get('nombre_embalse'):
            data['nombre_embalse'] = data.get('embalse_id', 'Embalse')
            
        embalse_id = data.get('embalse_id')
        fecha_gen = data.get('fecha_generacion')
        if isinstance(fecha_gen, str):
            fecha_gen = datetime.fromisoformat(fecha_gen.replace('Z', '+00:00'))
        elif not isinstance(fecha_gen, datetime):
            fecha_gen = datetime.now()
        
        # Actualizar fecha_generacion en el diccionario como datetime
        data['fecha_generacion'] = fecha_gen
        fecha_str = fecha_gen.strftime('%Y-%m-%d')
        
        # Asegurar que fecha_inicio_periodo y fecha_fin_periodo sean datetime si existen
        if data.get('fecha_inicio_periodo') and isinstance(data['fecha_inicio_periodo'], str):
            data['fecha_inicio_periodo'] = datetime.fromisoformat(data['fecha_inicio_periodo'].replace('Z', '+00:00'))
        if data.get('fecha_fin_periodo') and isinstance(data['fecha_fin_periodo'], str):
            data['fecha_fin_periodo'] = datetime.fromisoformat(data['fecha_fin_periodo'].replace('Z', '+00:00'))
        
        logger.info(f"Completando datos para {embalse_id} en fecha {fecha_str}")
        
        # Asegurar estructura mínima de datos_actual con valores por defecto
        if 'datos_actual' not in data or data['datos_actual'] is None:
            data['datos_actual'] = {}
        
        # Valores por defecto para datos_actual (evita Undefined en plantillas)
        datos_actual_defaults = {
            'nombre_embalse': data.get('nombre_embalse', 'Embalse'),
            'nivel_actual_msnm': 0.0,
            'porcentaje_capacidad': 0.0,
            'capacidad_total': 100.0,
            'nivel_maximo_msnm': 100.0,
            'media_historica': 50.0,
            'percentil_20': 20.0,
            'percentil_80': 80.0,
            'tendencia': 'estable'
        }
        for key, default_val in datos_actual_defaults.items():
            if key not in data['datos_actual'] or data['datos_actual'].get(key) is None:
                data['datos_actual'][key] = default_val
        
        # 1. Obtener datos actuales reales de la BD (sobrescribe defaults si disponible)
        if data['datos_actual'].get('nivel_actual_msnm', 0) == 0:
            try:
                actual = data_loader.get_embalse_actual(embalse_id, fecha_str)
                if actual:
                    # Mapear campos de EmbalseActual a diccionario
                    data['datos_actual'] = {
                        'nombre_embalse': actual.nombre,
                        'nivel_actual_msnm': actual.nivel_actual,
                        'porcentaje_capacidad': (actual.nivel_actual / actual.capacidad_total * 100) if actual.capacidad_total > 0 else 0,
                        'capacidad_total': actual.capacidad_total,
                        'nivel_maximo_msnm': actual.capacidad_total, # Usamos capacidad como referencia
                        'percentil_20': 20.0, # Valores por defecto si no hay estadísticos
                        'percentil_80': 80.0
                    }
            except Exception as e:
                logger.warning(f"No se pudieron obtener datos actuales de BD: {e}")

        # Asegurar estructura mínima de prediccion con valores por defecto
        if 'prediccion' not in data or data['prediccion'] is None:
            data['prediccion'] = {}
        
        prediccion_defaults = {
            'nivel_30d': data['datos_actual'].get('nivel_actual_msnm', 100.0),
            'nivel_90d': data['datos_actual'].get('nivel_actual_msnm', 100.0),
            'nivel_180d': data['datos_actual'].get('nivel_actual_msnm', 100.0),
            'porcentaje_30d': data['datos_actual'].get('porcentaje_capacidad', 50.0),
            'porcentaje_90d': data['datos_actual'].get('porcentaje_capacidad', 50.0),
            'porcentaje_180d': data['datos_actual'].get('porcentaje_capacidad', 50.0),
            'horizonte_dias': 180,
            'confianza': 0.95
        }
        for key, default_val in prediccion_defaults.items():
            if key not in data['prediccion'] or data['prediccion'].get(key) is None:
                data['prediccion'][key] = default_val

        # 2. Obtener predicciones reales del modelo (sobrescribe defaults si disponible)
        if data['prediccion'].get('nivel_30d') == data['datos_actual'].get('nivel_actual_msnm'):
            try:
                df_pred = prediction_service.predecir_embalse(embalse_id, fecha_str, horizonte=180)
                if not df_pred.empty:
                    # Extraer niveles a 30, 90, 180 días
                    n30 = float(df_pred.iloc[min(29, len(df_pred)-1)]['pred'])
                    n90 = float(df_pred.iloc[min(89, len(df_pred)-1)]['pred'])
                    n180 = float(df_pred.iloc[min(179, len(df_pred)-1)]['pred'])
                    
                    capacidad = data.get('datos_actual', {}).get('capacidad_total', 330.0)
                    
                    data['prediccion'] = {
                        'nivel_30d': n30,
                        'nivel_90d': n90,
                        'nivel_180d': n180,
                        'porcentaje_30d': (n30 / capacidad * 100) if capacidad > 0 else 0,
                        'porcentaje_90d': (n90 / capacidad * 100) if capacidad > 0 else 0,
                        'porcentaje_180d': (n180 / capacidad * 100) if capacidad > 0 else 0
                    }
            except Exception as e:
                logger.warning(f"No se pudieron obtener predicciones de modelo: {e}")

        # Asegurar estructura mínima de riesgos con valores por defecto
        if 'riesgos' not in data or data['riesgos'] is None:
            data['riesgos'] = {}
        
        riesgos_defaults = {
            'categoria_riesgo': 'bajo',
            'nivel_riesgo': 'bajo',
            'probabilidad_sequia': 0.1,
            'descripcion': 'Sin alertas significativas'
        }
        for key, default_val in riesgos_defaults.items():
            if key not in data['riesgos'] or data['riesgos'].get(key) is None:
                data['riesgos'][key] = default_val

        # 3. Obtener riesgos reales (sobrescribe defaults si disponible)
        if data['riesgos'].get('categoria_riesgo') == 'bajo' and data['riesgos'].get('probabilidad_sequia') == 0.1:
            try:
                riesgo = RiskService.analizar_riesgo(embalse_id, fecha_str)
                data['riesgos'] = riesgo
            except Exception as e:
                logger.warning(f"No se pudo realizar análisis de riesgo: {e}")

        # 4. Datos históricos para informe semanal
        if data.get('tipo_informe') == 'semanal' and not data.get('datos_historicos_semana'):
            try:
                start_dt = fecha_gen - timedelta(days=7)
                hist = data_loader.get_historico(embalse_id, start_dt.strftime('%Y-%m-%d'), fecha_str)
                if not hist.empty:
                    data['datos_historicos_semana'] = hist[['fecha', 'nivel']].to_dict(orient='records')
            except Exception as e:
                logger.warning(f"No se pudieron obtener datos históricos: {e}")

        # 5. Generar o normalizar escenarios (necesarios para el template semanal)
        if data.get('tipo_informe') == 'semanal':
            escenarios = data.get('escenarios', {}) or {}
            
            # Normalizar nombres (soporte para legacy)
            if 'conservador' in escenarios and 'pesimista' not in escenarios:
                escenarios['pesimista'] = escenarios['conservador']
            if 'agresivo' in escenarios and 'optimista' not in escenarios:
                escenarios['optimista'] = escenarios['agresivo']
                
            # Si faltan claves críticas, generarlas
            if not escenarios or 'pesimista' not in escenarios or 'optimista' not in escenarios or 'neutro' not in escenarios:
                try:
                    base_180d = data.get('prediccion', {}).get('nivel_180d', 0)
                    if not escenarios:
                        escenarios = {
                            'neutro': {'nivel_180d': base_180d},
                            'pesimista': {'nivel_180d': base_180d * 0.9},
                            'optimista': {'nivel_180d': base_180d * 1.1}
                        }
                    else:
                        if 'neutro' not in escenarios: escenarios['neutro'] = {'nivel_180d': base_180d}
                        if 'pesimista' not in escenarios: escenarios['pesimista'] = {'nivel_180d': base_180d * 0.9}
                        if 'optimista' not in escenarios: escenarios['optimista'] = {'nivel_180d': base_180d * 1.1}
                except Exception as e:
                    logger.warning(f"Error completando escenarios: {e}")
            
            data['escenarios'] = escenarios

        # 6. Asegurar recomendaciones mínimas
        if not data.get('recomendaciones') or len(data.get('recomendaciones', [])) == 0:
            data['recomendaciones'] = []

        # 7. Generar gráficas (se almacenan como base64 en el mismo diccionario)
        if not data.get('graficas'):
            data['graficas'] = self._generar_graficas(data)

        return data
    
    def obtener_informe(self, informe_id: str, formato: str = 'html') -> Optional[Path]:
        """
        Obtiene la ruta de un informe generado previamente.
        
        Args:
            informe_id: ID del informe
            formato: 'html' o 'pdf'
            
        Returns:
            Path del archivo o None si no existe
        """
        extension = 'html' if formato == 'html' else 'pdf'
        filepath = self.output_dir / f"{informe_id}.{extension}"
        
        if filepath.exists():
            return filepath
        else:
            logger.warning(f"Informe no encontrado: {filepath}")
            return None
    
    def listar_informes(self, embalse_id: Optional[str] = None) -> list[Dict]:
        """
        Lista todos los informes generados.
        
        Args:
            embalse_id: Filtrar por embalse (opcional)
            
        Returns:
            Lista de metadatos de informes
        """
        import json
        informes = []
        
        for metadata_file in self.output_dir.glob("*_metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                if embalse_id is None or metadata.get('embalse_id') == embalse_id:
                    informes.append(metadata)
            except Exception as e:
                logger.error(f"Error leyendo metadata {metadata_file}: {e}")
        
        # Ordenar por fecha (más recientes primero)
        informes.sort(key=lambda x: x.get('fecha_generacion', ''), reverse=True)
        
        return informes


# Instancia global del servicio
informe_service = InformeService()
