"""
Servicio asíncrono para interacción con LLMs (Ollama).
Incluye caché inteligente, reintentos y manejo robusto de errores.
"""
import asyncio
import json
import hashlib
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import httpx

from ..config import settings
from ..data import db_connection

logger = logging.getLogger(__name__)


class LLMService:
    """Servicio para generación de recomendaciones usando LLM."""
    
    def __init__(self):
        """Inicializa el servicio LLM."""
        self.db = db_connection
        self._cache_local: Dict[str, Tuple[str, str, datetime]] = {}
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'llm_errors': 0,
            'llm_success': 0
        }
    
    def _generar_cache_key(
        self, 
        prompt: str, 
        nivel_riesgo: str,
        codigo_embalse: Optional[str] = None,
        fecha: Optional[str] = None
    ) -> str:
        """Genera una clave única para el caché basada en múltiples factores."""
        # Incluir embalse y fecha si están disponibles para mejor granularidad
        content = f"{nivel_riesgo}:{codigo_embalse or 'generic'}:{fecha or 'any'}:{prompt[:200]}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _obtener_de_cache_db(self, cache_key: str) -> Optional[Tuple[str, str]]:
        """
        Obtiene una respuesta del caché de base de datos si existe y es válida.
        
        Returns:
            Tupla (motivo, accion) si se encuentra en caché, None si no.
        """
        if not settings.llm_cache_enabled:
            return None
        
        query = """
            SELECT motivo, accion_recomendada, fecha_cache
            FROM llm_cache_recomendaciones
            WHERE cache_key = %s
              AND fecha_cache > NOW() - INTERVAL '%s seconds'
            LIMIT 1
        """
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (cache_key, settings.llm_cache_ttl))
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"Cache hit in database for key={cache_key[:16]}...")
                    self._stats['cache_hits'] += 1
                    return (result['motivo'], result['accion_recomendada'])
        except Exception as e:
            logger.error(f"Error consultando caché BD: {e}")
        
        self._stats['cache_misses'] += 1
        return None
    
    async def _guardar_en_cache_db(
        self,
        cache_key: str,
        prompt: str,
        nivel_riesgo: str,
        motivo: str,
        accion: str
    ) -> None:
        """Guarda una respuesta en el caché de base de datos."""
        if not settings.llm_cache_enabled:
            return
        
        query = """
            INSERT INTO llm_cache_recomendaciones (
                cache_key, prompt, nivel_riesgo, motivo, accion_recomendada, fecha_cache
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (cache_key) DO UPDATE SET
                motivo = EXCLUDED.motivo,
                accion_recomendada = EXCLUDED.accion_recomendada,
                fecha_cache = NOW()
        """
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (cache_key, prompt, nivel_riesgo, motivo, accion))
                logger.debug(f"Response saved to database cache: {cache_key[:16]}...")
        except Exception as e:
            logger.error(f"Error guardando en caché BD: {e}")
    
    def _construir_prompt_optimizado(
        self,
        nivel_riesgo: str,
        metricas: Dict,
        info_embalse: Dict,
        horizonte: int,
        porcentaje: float
    ) -> str:
        """Construye un prompt optimizado para el modelo Phi-3.5."""
        
        # Contextualizar según nivel de riesgo
        contexto_urgencia = {
            'ALTO': 'SITUACIÓN CRÍTICA - RIESGO DE DESBORDAMIENTO',
            'MODERADO': 'SITUACIÓN DE VIGILANCIA - NIVELES ELEVADOS',
            'SEQUIA': 'SITUACIÓN CRÍTICA - RIESGO DE SEQUÍA',
            'BAJO': 'SITUACIÓN NORMAL - NIVELES ÓPTIMOS'
        }.get(nivel_riesgo, 'ANÁLISIS HIDROLÓGICO')
        
        # Incluir tendencia si está disponible
        tendencia_texto = ""
        if metricas.get('tendencia'):
            tendencia = metricas['tendencia']
            if tendencia == 'SUBIDA_RAPIDA':
                tendencia_texto = "ALERTA: Subida rápida del nivel"
            elif tendencia == 'SUBIDA':
                tendencia_texto = "Nivel ascendente"
            elif tendencia == 'BAJADA':
                tendencia_texto = "Nivel descendente"
            elif tendencia == 'BAJADA_RAPIDA':
                tendencia_texto = "ALERTA: Bajada rápida del nivel"
            else:
                tendencia_texto = "Nivel estable"
        
        # Construir prompt estructurado
        prompt = f"""Eres un ingeniero hidráulico experto del Sistema Automático de Información Hidrológica (SAIH). 
Tu tarea es analizar datos de embalse y generar recomendaciones operativas profesionales.

{contexto_urgencia}

DATOS DEL EMBALSE:
• Ubicación: {info_embalse.get('ubicacion', 'Desconocido')}
• Demarcación: {info_embalse.get('demarcacion', 'N/A')}
• Nivel Actual: {float(metricas.get('nivel_actual') or 0):.2f} hm³
• Capacidad Máxima: {float(info_embalse.get('nivel_maximo') or 0):.2f} hm³
• Porcentaje de Llenado: {float(porcentaje or 0):.1f}%

PREDICCIÓN ({horizonte} días):
• Nivel Esperado: {float(metricas.get('nivel_medio') or 0):.2f} hm³
• Rango: {float(metricas.get('nivel_min') or 0):.2f} - {float(metricas.get('nivel_max') or 0):.2f} hm³
• Tendencia: {tendencia_texto}
• Incertidumbre (MAE): ±{float(metricas.get('mae') or 0):.2f} hm³
• Nivel de Riesgo: {nivel_riesgo}

TAREA:
Genera un análisis técnico en formato JSON con dos campos:

1. "motivo": Explicación profesional del nivel de riesgo en 2-3 frases máximo.
   - Sin emojis ni símbolos decorativos
   - Menciona datos cuantitativos clave
   - Explica el contexto hidrológico
   - Indica tendencia si es relevante

2. "accion": Lista estructurada de acciones operativas en formato HTML.
   - Usa una lista no ordenada con <ul> y <li>
   - Sin emojis ni símbolos decorativos
   - 3-5 items máximo, ordenados por prioridad
   - Especifica valores numéricos cuando sea posible
   - Incluye coordinación con organismos si es crítico
   - Formato ejemplo:
     "<ul><li>Monitorear niveles cada hora</li><li>Coordinar con autoridades locales</li><li>Preparar protocolo de emergencia</li></ul>"

REGLAS IMPORTANTES:
- NO uses emojis, emoticones ni símbolos decorativos (🔴 ⚠️ ✅ etc)
- Responde ÚNICAMENTE con JSON válido, sin texto adicional antes o después
- El campo "accion" debe contener HTML con etiquetas <ul> y <li>
- Usa lenguaje técnico pero comprensible
- Sé conciso y directo
- Prioriza acciones de mayor a menor importancia

FORMATO DE RESPUESTA (copiar exactamente esta estructura):
{{
  "motivo": "Texto del motivo aquí",
  "accion": "<ul><li>Primera acción</li><li>Segunda acción</li><li>Tercera acción</li></ul>"
}}
```
- Prioriza la seguridad hidrológica

Formato de respuesta:
{{"motivo": "texto aquí", "accion": "texto aquí"}}"""
        
        return prompt
    
    async def _llamar_ollama_async(
        self,
        prompt: str,
        reintentos_restantes: int = None
    ) -> Tuple[str, str]:
        """
        Realiza llamada asíncrona a Ollama con reintentos.
        
        Returns:
            Tupla (motivo, accion)
            
        Raises:
            Exception si falla después de todos los reintentos
        """
        if reintentos_restantes is None:
            reintentos_restantes = settings.ollama_max_retries
        
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
                logger.info(f"Querying {settings.ollama_model} at {settings.ollama_url}")
                
                response = await client.post(
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": settings.ollama_temperature,
                            "top_p": settings.ollama_top_p,
                            "num_predict": 512  # Limitar tokens de salida
                        }
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extraer y parsear la respuesta
                response_text = result.get('response', '{}')
                logger.debug(f"Respuesta LLM (primeros 200 chars): {response_text[:200]}")
                
                # Limpiar respuesta si viene con markdown
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                data = json.loads(response_text)
                motivo = data.get('motivo', '').strip()
                accion = data.get('accion', '').strip()
                
                if not motivo or not accion:
                    raise ValueError("Respuesta LLM incompleta: campos vacíos")
                
                if len(motivo) < 20 or len(accion) < 20:
                    raise ValueError("Respuesta LLM demasiado corta")
                
                self._stats['llm_success'] += 1
                logger.info(f"LLM recommendation generated: {len(motivo)} + {len(accion)} chars")
                
                return motivo, accion
                
        except httpx.ConnectError as e:
            self._stats['llm_errors'] += 1
            logger.error(f"Cannot connect to Ollama at {settings.ollama_url}: {e}")
            raise ConnectionError(f"Ollama not available: {e}")
            
        except httpx.TimeoutException:
            self._stats['llm_errors'] += 1
            if reintentos_restantes > 0:
                logger.warning(f"Ollama timeout, retrying... ({reintentos_restantes} remaining)")
                await asyncio.sleep(2)
                return await self._llamar_ollama_async(prompt, reintentos_restantes - 1)
            else:
                logger.error(f"Ollama timeout after all retries")
                raise TimeoutError("Ollama did not respond in time")
            
        except json.JSONDecodeError as e:
            self._stats['llm_errors'] += 1
            logger.error(f"Error parsing JSON from Ollama: {e}")
            logger.debug(f"Problematic response: {response_text[:500]}")
            
            if reintentos_restantes > 0:
                logger.warning(f"Reintentando por error de parsing... ({reintentos_restantes} restantes)")
                await asyncio.sleep(1)
                return await self._llamar_ollama_async(prompt, reintentos_restantes - 1)
            else:
                raise ValueError(f"JSON inválido de Ollama: {e}")
            
        except Exception as e:
            self._stats['llm_errors'] += 1
            logger.error(f"Unexpected error with Ollama: {type(e).__name__}: {e}")
            
            if reintentos_restantes > 0 and not isinstance(e, (KeyError, AttributeError)):
                logger.warning(f"Reintentando... ({reintentos_restantes} restantes)")
                await asyncio.sleep(1)
                return await self._llamar_ollama_async(prompt, reintentos_restantes - 1)
            else:
                raise
    
    async def generar_recomendacion_async(
        self,
        nivel_riesgo: str,
        metricas: Dict,
        info_embalse: Dict,
        horizonte: int,
        porcentaje: float,
        fecha_referencia: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Genera recomendación usando LLM de forma asíncrona.
        
        Flujo:
        1. Construir prompt optimizado
        2. Verificar caché (BD)
        3. Si no está en caché, llamar a LLM
        4. Guardar en caché
        5. Retornar resultado
        
        Returns:
            Tupla (motivo, accion)
        """
        self._stats['total_requests'] += 1
        
        # 1. Construir prompt
        prompt = self._construir_prompt_optimizado(
            nivel_riesgo, metricas, info_embalse, horizonte, porcentaje
        )
        
        # 2. Generar clave de caché (incluye código de embalse y fecha para mejor granularidad)
        codigo_embalse = info_embalse.get('codigo_saih')
        cache_key = self._generar_cache_key(
            prompt, nivel_riesgo, codigo_embalse, fecha_referencia
        )
        
        # 3. Verificar caché en BD
        cached_result = await self._obtener_de_cache_db(cache_key)
        if cached_result:
            return cached_result
        
        # 4. Llamar a LLM
        try:
            motivo, accion = await self._llamar_ollama_async(prompt)
            
            # 5. Guardar en caché de forma asíncrona (no bloqueante)
            asyncio.create_task(
                self._guardar_en_cache_db(cache_key, prompt, nivel_riesgo, motivo, accion)
            )
            
            return motivo, accion
            
        except Exception as e:
            logger.error(f"Error completo en generación LLM: {e}")
            raise
    
    async def generar_analisis_informe_diario(
        self,
        datos_actual: Dict,
        prediccion: Dict,
        riesgos: Dict,
        metricas: Dict
    ) -> Dict:
        """
        Genera un análisis técnico profundo y recomendaciones específicas para el informe diario.
        """
        prompt_base = f"""Como ingeniero hidrológico jefe, analiza la situación operacional del embalse {datos_actual.get('nombre_embalse', 'seleccionado')}.

ESTADO ACTUAL:
- Nivel: {datos_actual.get('nivel_actual_msnm', 0):.2f} msnm
- Llenado: {datos_actual.get('porcentaje_capacidad', 0):.1f}%
- Capacidad Total: {datos_actual.get('capacidad_total', 0):.2f} hm³

PREDICCIÓN CORTO PLAZO (48h - 30d):
- Tendencia esperada: {prediccion.get('nivel_30d', 0):.2f} msnm a 30 días.
- Riesgos detectados: {riesgos.get('mensaje', 'Sin riesgos significativos')}.

TAREA:
Genera un análisis técnico dividido en:
1. Resumen Ejecutivo (conciso, profesional)
2. Análisis de Situación (detalles técnicos, comparativa)
3. Recomendaciones Operativas (formato HTML <ul><li>)

Responde en Formato JSON:
{{
  "resumen": "...",
  "situacion": "...",
  "recomendaciones": "<ul><li>...</li></ul>"
}}
"""
        try:
            # Una sola consulta robusta para eficiencia, pero con instrucciones claras de profundidad
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt_base,
                        "stream": False,
                        "format": "json"
                    }
                )
                
                if response.status_code == 200:
                    res_json = json.loads(response.json().get('response', '{}'))
                    
                    return {
                        "resumen_ejecutivo": res_json.get('resumen', 'Situación estable.'),
                        "analisis_situacion": res_json.get('situacion', 'Niveles dentro de la normalidad.'),
                        "prediccion_48h": f"Tendencia hacia {prediccion.get('nivel_30d', 0):.2f} msnm.",
                        "recomendaciones_html": res_json.get('recomendaciones', "<ul><li>Vigilancia estándar</li></ul>"),
                        "evaluacion_riesgos": riesgos.get('mensaje', "Monitorización continua."),
                        "llm_usado": True
                    }
            raise Exception("Fallo en respuesta de Ollama")
            
        except Exception as e:
            logger.warning(f"Error en LLM diario avanzado: {e}")
            # Fallback a la versión básica o estática
            return {
                "resumen_ejecutivo": "Análisis operativo basado en niveles actuales.",
                "analisis_situacion": f"El embalse se encuentra al {datos_actual.get('porcentaje_capacidad', 0):.1f}%.",
                "prediccion_48h": "Tendencia estable según modelos.",
                "recomendaciones_html": "<ul><li>Mantener vigilancia rutinaria</li></ul>",
                "evaluacion_riesgos": riesgos.get('mensaje', "Sin alertas."),
                "llm_usado": False
            }

    async def generar_analisis_informe_semanal(
        self,
        datos_actual: Dict,
        datos_historicos_semana: List,
        prediccion: Dict,
        riesgos: Dict,
        escenarios: Dict,
        metricas: Dict
    ) -> Dict:
        """
        Genera un informe estratégico semanal con análisis de tendencias y escenarios.
        """
        prompt_base = f"""Eres el Director de Recursos Hídricos. Analiza el informe semanal del embalse {datos_actual.get('nombre_embalse', 'seleccionado')}.

CONTEXTO SEMANAL:
- Nivel Actual: {datos_actual.get('nivel_actual_msnm', 0):.2f} msnm ({datos_actual.get('porcentaje_capacidad', 0):.1f}% llenado)
- Evolución 7 días: {len(datos_historicos_semana)} puntos de datos registrados.

PROYECCIONES:
- 30 días: {prediccion.get('nivel_30d', 0):.2f} msnm
- 90 días: {prediccion.get('nivel_90d', 0):.2f} msnm
- 180 días: {prediccion.get('nivel_180d', 0):.2f} msnm

ESCENARIOS (180 días):
- Pesimista: {escenarios.get('pesimista', {}).get('nivel_180d', 0):.2f} msnm
- Optimista: {escenarios.get('optimista', {}).get('nivel_180d', 0):.2f} msnm

CALIDAD MODELO:
- MAE Global: {metricas.get('MAE_global', 0):.4f}
- R2 Score: {metricas.get('R2_global', 0):.4f}

TAREA:
Genera un informe estratégico JSON con:
1. resumen: Visión general estratégica.
2. evolucion: Análisis de la tendencia de la última semana.
3. escenarios: Evaluación técnica de los escenarios a largo plazo.
4. recomendaciones: Acciones estratégicas (formato HTML <ul><li>).
5. conclusiones: Trazabilidad y calidad de datos.

Formato JSON:
{{
  "resumen": "...",
  "evolucion": "...",
  "escenarios": "...",
  "recomendaciones": "<ul><li>...</li></ul>",
  "conclusiones": "..."
}}
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt_base,
                        "stream": False,
                        "format": "json"
                    }
                )
                
                if response.status_code == 200:
                    res_json = json.loads(response.json().get('response', '{}'))
                    
                    return {
                        "resumen_ejecutivo": res_json.get('resumen', 'Análisis estratégico semanal disponible.'),
                        "evolucion_semanal": res_json.get('evolucion', 'Evolución estable en el periodo analizado.'),
                        "analisis_escenarios": res_json.get('escenarios', 'Los escenarios muestran una variabilidad dentro de rangos históricos.'),
                        "recomendaciones_estrategicas": res_json.get('recomendaciones', "<ul><li>Continuar planificación estacional</li></ul>"),
                        "conclusiones_calidad": res_json.get('conclusiones', f"Validación técnica completada (R2: {metricas.get('R2_global', 0):.2f})."),
                        "llm_usado": True
                    }
        except Exception as e:
            logger.warning(f"Error en LLM semanal avanzado: {e}")
            
        return {
            "resumen_ejecutivo": "Revisión estratégica del estado del embalse.",
            "evolucion_semanal": "Tendencia observada consistente con el periodo anual.",
            "analisis_escenarios": f"Diferencial entre escenarios de {abs(escenarios.get('optimista', {}).get('nivel_180d', 0) - escenarios.get('pesimista', {}).get('nivel_180d', 0)):.2f} msnm.",
            "recomendaciones_estrategicas": "<ul><li>Optimizar desembalses según prioridad</li><li>Revisar planes de contingencia</li></ul>",
            "conclusiones_calidad": f"Modelo validado con R2 de {metricas.get('R2_global', 0):.2f}.",
            "llm_usado": False
        }

    def get_stats(self) -> Dict:
        """Retorna estadísticas del servicio LLM."""
        total = self._stats['total_requests']
        if total > 0:
            cache_rate = (self._stats['cache_hits'] / total) * 100
            success_rate = (self._stats['llm_success'] / max(1, self._stats['cache_misses'])) * 100
        else:
            cache_rate = 0
            success_rate = 0
        
        return {
            **self._stats,
            'cache_hit_rate': f"{cache_rate:.1f}%",
            'llm_success_rate': f"{success_rate:.1f}%"
        }
    
    async def verificar_salud_ollama(self) -> Dict:
        """Verifica que Ollama esté disponible y el modelo cargado."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.ollama_url}/api/tags")
                
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    
                    modelo_disponible = settings.ollama_model in model_names
                    
                    return {
                        'disponible': True,
                        'url': settings.ollama_url,
                        'modelo_configurado': settings.ollama_model,
                        'modelo_disponible': modelo_disponible,
                        'modelos_instalados': model_names[:5],  # Primeros 5
                        'total_modelos': len(models)
                    }
                else:
                    return {
                        'disponible': False,
                        'error': f'Status code: {response.status_code}'
                    }
                    
        except Exception as e:
            return {
                'disponible': False,
                'error': str(e)
            }


# Instancia singleton del servicio LLM
llm_service = LLMService()
