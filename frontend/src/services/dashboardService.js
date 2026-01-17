import api from '../lib/api'

/**
 * Servicio de Dashboard - Endpoints para KPIs y datos agregados
 */

/**
 * Obtiene los KPIs del dashboard
 * @param {string} fechaReferencia - Fecha de referencia opcional (YYYY-MM-DD)
 */
export const getKPIs = async (fechaReferencia = null) => {
  const params = fechaReferencia ? { fecha_referencia: fechaReferencia } : {}
  const response = await api.get('/dashboard/kpis', { params })
  return response.data
}

/**
 * Obtiene datos actuales de un embalse específico
 * @param {string} codigoSaih - Código SAIH del embalse
 * @param {string} fechaReferencia - Fecha de referencia opcional
 */
export const getEmbalseActual = async (codigoSaih, fechaReferencia = null) => {
  const params = fechaReferencia ? { fecha_referencia: fechaReferencia } : {}
  const response = await api.get(`/dashboard/embalses/${codigoSaih}/actual`, { params })
  return response.data
}

/**
 * Obtiene las alertas activas del sistema
 * @param {Object} filters - Filtros opcionales (fecha_referencia, severidad, tipo, demarcacion)
 */
export const getAlertas = async (filters = {}) => {
  const response = await api.get('/dashboard/alertas', { params: filters })
  return response.data
}

/**
 * Obtiene lista de todos los embalses
 * @param {string} fechaReferencia - Fecha de referencia opcional (YYYY-MM-DD)
 */
export const getEmbalses = async (fechaReferencia = null) => {
  const params = fechaReferencia ? { fecha_referencia: fechaReferencia } : {}
  const response = await api.get('/embalses', { params })
  return response.data
}

/**
 * Obtiene histórico de un embalse
 * @param {string} codigoSaih - Código del embalse
 * @param {string} startDate - Fecha inicio (YYYY-MM-DD)
 * @param {string} endDate - Fecha fin (YYYY-MM-DD)
 */
export const getHistorico = async (codigoSaih, startDate = null, endDate = null) => {
  const params = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  
  const response = await api.get(`/embalses/${codigoSaih}/historico`, { params })
  return response.data
}

/**
 * Genera predicción para un embalse
 * @param {string} codigoSaih - Código del embalse
 * @param {Object} data - Datos de la predicción (fecha_inicio, horizonte_dias)
 */
export const generarPrediccion = async (codigoSaih, data) => {
  const response = await api.post(`/predicciones/${codigoSaih}`, data)
  return response.data
}

/**
 * Obtiene recomendación operativa de un embalse
 * @param {string} codigoSaih - Código del embalse
 * @param {string} fechaInicio - Fecha inicio opcional
 * @param {number} horizonteDias - Horizonte de predicción opcional
 */
export const getRecomendacion = async (codigoSaih, fechaInicio = null, horizonteDias = null) => {
  const params = {}
  if (fechaInicio) params.fecha_inicio = fechaInicio
  if (horizonteDias) params.horizonte_dias = horizonteDias
  
  const response = await api.get(`/recomendaciones/${codigoSaih}`, { params })
  return response.data
}

/**
 * Obtiene resumen de un embalse
 * @param {string} codigoSaih - Código del embalse
 */
export const getResumenEmbalse = async (codigoSaih) => {
  const response = await api.get(`/embalses/${codigoSaih}/resumen`)
  return response.data
}

/**
 * Obtiene demarcaciones hidrográficas
 */
export const getDemarcaciones = async () => {
  const response = await api.get('/demarcaciones')
  return response.data
}

/**
 * Verifica el estado del servicio LLM (Ollama)
 */
export const getLLMSalud = async () => {
  const response = await api.get('/recomendaciones/llm/salud')
  return response.data
}

/**
 * Obtiene estadísticas de uso del LLM
 */
export const getLLMEstadisticas = async () => {
  const response = await api.get('/recomendaciones/llm/estadisticas')
  return response.data
}

/**
 * Genera recomendación forzada (ignora caché)
 * @param {string} codigoSaih - Código del embalse
 * @param {Object} data - Datos opcionales (fecha_inicio, horizonte_dias)
 */
export const generarRecomendacionForzada = async (codigoSaih, data = {}) => {
  const response = await api.post(`/recomendaciones/${codigoSaih}`, data)
  return response.data
}
