import api from '../lib/api'

/**
 * Servicio para gestión de informes de embalses
 */

/**
 * Genera un informe completo para un embalse
 * @param {Object} data - Datos del informe según InformeRequest
 * @returns {Promise} Response con URLs del informe generado
 */
export const generarInforme = async (data) => {
  try {
    const response = await api.post('/api/informes/generar', data)
    return response.data
  } catch (error) {
    console.error('Error generando informe:', error)
    throw error
  }
}

/**
 * Lista todos los informes generados
 * @param {string} embalseId - ID del embalse para filtrar (opcional)
 * @returns {Promise} Lista de informes
 */
export const listarInformes = async (embalseId = null) => {
  try {
    const params = embalseId ? { embalse_id: embalseId } : {}
    const response = await api.get('/api/informes/listar', { params })
    return response.data
  } catch (error) {
    console.error('Error listando informes:', error)
    throw error
  }
}

/**
 * Obtiene la URL para previsualizar un informe HTML
 * @param {string} informeId - ID del informe
 * @returns {string} URL del preview
 */
export const getPreviewUrl = (informeId) => {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return `${baseUrl}/api/informes/preview/${informeId}`
}

/**
 * Obtiene la URL para descargar un informe PDF
 * @param {string} informeId - ID del informe
 * @returns {string} URL de descarga
 */
export const getDownloadUrl = (informeId) => {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return `${baseUrl}/api/informes/download/${informeId}.pdf`
}

/**
 * Elimina un informe
 * @param {string} informeId - ID del informe
 * @returns {Promise} Confirmación de eliminación
 */
export const eliminarInforme = async (informeId) => {
  try {
    const response = await api.delete(`/api/informes/${informeId}`)
    return response.data
  } catch (error) {
    console.error('Error eliminando informe:', error)
    throw error
  }
}

/**
 * Construye los datos para generar un informe a partir de datos del dashboard
 * @param {Object} embalse - Datos del embalse
 * @param {Object} predicciones - Predicciones del modelo
 * @param {Object} recomendaciones - Recomendaciones generadas
 * @param {string} usuario - Tipo de usuario
 * @returns {Object} Datos formateados para InformeRequest
 */
export const construirDatosInforme = (embalse, predicciones, recomendaciones, usuario = 'tecnico_operativo') => {
  // Esta es una función helper que el frontend puede usar para construir
  // el objeto InformeRequest a partir de los datos del dashboard
  
  // IMPORTANTE: Los niveles son cotas en metros sobre nivel del mar (msnm), no volumen (hm³)
  const nivelActualMsnm = embalse.ultimo_nivel || embalse.nivel_actual || 0
  const nivelMaximoMsnm = embalse.nivel_maximo || 330.0
  const porcentajeCapacidad = embalse.porcentaje_llenado || 
    (nivelMaximoMsnm > 0 ? (nivelActualMsnm / nivelMaximoMsnm) * 100 : 0)
  
  return {
    embalse_id: embalse.codigo_saih,
    nombre_embalse: embalse.ubicacion || embalse.nombre_embalse,
    fecha_generacion: new Date().toISOString(),
    model_version: 'v1.2_AEMET_Ruido',
    metricas_modelo: {
      MAE_30d: 0.85,
      MAE_90d: 1.12,
      MAE_180d: 1.46,
      R2_global: 0.92
    },
    datos_actual: {
      nivel_actual_msnm: nivelActualMsnm,
      nivel_maximo_msnm: nivelMaximoMsnm,
      porcentaje_capacidad: porcentajeCapacidad,
      media_historica: 72.1, // TODO: Calcular desde datos históricos
      percentil_20: 45.0,
      percentil_80: 88.0
    },
    prediccion: {
      // Las predicciones también deben estar en msnm (cotas)
      nivel_30d: predicciones?.nivel_30d || nivelActualMsnm - 1,
      nivel_90d: predicciones?.nivel_90d || nivelActualMsnm - 2,
      nivel_180d: predicciones?.nivel_180d || nivelActualMsnm - 3,
      porcentaje_30d: predicciones?.porcentaje_30d || porcentajeCapacidad - 1,
      porcentaje_90d: predicciones?.porcentaje_90d || porcentajeCapacidad - 2,
      porcentaje_180d: predicciones?.porcentaje_180d || porcentajeCapacidad - 3
    },
    riesgos: {
      sequia_moderada_90d: predicciones?.porcentaje_90d < 30,
      sequia_grave_180d: predicciones?.porcentaje_180d < 20,
      llena_30d: predicciones?.porcentaje_30d > 95
    },
    recomendaciones: recomendaciones || [],
    escenarios: {
      // Escenarios en cotas (msnm)
      conservador: { nivel_180d: (predicciones?.nivel_180d || nivelActualMsnm) - 2 },
      neutro: { nivel_180d: predicciones?.nivel_180d || nivelActualMsnm },
      agresivo: { nivel_180d: (predicciones?.nivel_180d || nivelActualMsnm) + 1 }
    },
    usuario: usuario,
    idioma: 'es'
  }
}

export default {
  generarInforme,
  listarInformes,
  getPreviewUrl,
  getDownloadUrl,
  eliminarInforme,
  construirDatosInforme
}
