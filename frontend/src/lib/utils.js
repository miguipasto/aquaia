const EMPTY_VALUE = '-'

const LOCALE = 'es-ES'

const DATE_FORMATS = {
  short: { day: '2-digit', month: '2-digit', year: 'numeric' },
  medium: { day: '2-digit', month: 'short', year: 'numeric' },
  long: { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' },
}

const ESTADO_CONFIG = {
  critico_alto: { color: 'danger', text: 'Crítico Alto' },
  alto: { color: 'warning', text: 'Alto' },
  normal: { color: 'success', text: 'Normal' },
  bajo: { color: 'warning', text: 'Bajo' },
  critico_bajo: { color: 'danger', text: 'Crítico Bajo' },
  desconocido: { color: 'gray', text: 'Desconocido' },
}

const SEVERIDAD_CONFIG = {
  critical: { color: 'danger', text: 'Crítica' },
  error: { color: 'danger', text: 'Error' },
  warning: { color: 'warning', text: 'Advertencia' },
  info: { color: 'primary', text: 'Información' },
}

const isValidValue = (value) => value !== null && value !== undefined

export const formatPercentage = (value, decimals = 1) => {
  if (!isValidValue(value)) return EMPTY_VALUE
  return `${value.toFixed(decimals)}%`
}

export const formatNumber = (value, decimals = 2) => {
  if (!isValidValue(value)) return EMPTY_VALUE
  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export const formatDate = (dateString, formatType = 'short') => {
  if (!dateString) return EMPTY_VALUE
  
  const date = new Date(dateString)
  const format = DATE_FORMATS[formatType] || DATE_FORMATS.short
  
  return new Intl.DateTimeFormat(LOCALE, format).format(date)
}

export const getEstadoColor = (estado) => 
  ESTADO_CONFIG[estado]?.color || 'gray'

export const getEstadoText = (estado) => 
  ESTADO_CONFIG[estado]?.text || 'Desconocido'

export const getSeveridadColor = (severidad) => 
  SEVERIDAD_CONFIG[severidad]?.color || 'gray'

export const getSeveridadText = (severidad) => 
  SEVERIDAD_CONFIG[severidad]?.text || severidad

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
