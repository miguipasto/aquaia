/**
 * Utilidades para formateo y validación de datos
 */

/**
 * Formatea un número como porcentaje
 */
export const formatPercentage = (value, decimals = 1) => {
  if (value === null || value === undefined) return '-'
  return `${value.toFixed(decimals)}%`
}

/**
 * Formatea un número con separadores de miles
 */
export const formatNumber = (value, decimals = 2) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Formatea una fecha
 */
export const formatDate = (dateString, formatType = 'short') => {
  if (!dateString) return '-'
  
  const date = new Date(dateString)
  
  const formats = {
    short: { day: '2-digit', month: '2-digit', year: 'numeric' },
    medium: { day: '2-digit', month: 'short', year: 'numeric' },
    long: { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' },
  }
  
  return new Intl.DateTimeFormat('es-ES', formats[formatType] || formats.short).format(date)
}

/**
 * Obtiene el color basado en el estado del embalse
 */
export const getEstadoColor = (estado) => {
  const colors = {
    critico_alto: 'danger',
    alto: 'warning',
    normal: 'success',
    bajo: 'warning',
    critico_bajo: 'danger',
    desconocido: 'gray',
  }
  
  return colors[estado] || 'gray'
}

/**
 * Obtiene el texto del estado del embalse
 */
export const getEstadoText = (estado) => {
  const texts = {
    critico_alto: 'Crítico Alto',
    alto: 'Alto',
    normal: 'Normal',
    bajo: 'Bajo',
    critico_bajo: 'Crítico Bajo',
    desconocido: 'Desconocido',
  }
  
  return texts[estado] || 'Desconocido'
}

/**
 * Obtiene el color basado en la severidad de una alerta
 */
export const getSeveridadColor = (severidad) => {
  const colors = {
    critical: 'danger',
    error: 'danger',
    warning: 'warning',
    info: 'primary',
  }
  
  return colors[severidad] || 'gray'
}

/**
 * Obtiene el texto de la severidad
 */
export const getSeveridadText = (severidad) => {
  const texts = {
    critical: 'Crítica',
    error: 'Error',
    warning: 'Advertencia',
    info: 'Información',
  }
  
  return texts[severidad] || severidad
}

/**
 * Obtiene el color del nivel de riesgo
 */
export const getRiesgoColor = (nivel) => {
  const colors = {
    ALTO: 'danger',
    MODERADO: 'warning',
    BAJO: 'success',
    SEQUIA: 'danger',
    'SEQUÍA': 'danger',
  }
  
  return colors[nivel] || 'gray'
}

/**
 * Calcula el color del nivel de llenado
 */
export const getLlenadoColor = (porcentaje) => {
  if (porcentaje >= 95) return 'danger'
  if (porcentaje >= 80) return 'warning'
  if (porcentaje >= 30) return 'success'
  if (porcentaje >= 20) return 'warning'
  return 'danger'
}

/**
 * Combina clases de CSS con tw-merge y clsx
 */
export const cn = (...classes) => {
  return classes.filter(Boolean).join(' ')
}
