import { Sparkles, Database, FileCode } from 'lucide-react'

/**
 * Badge que muestra la fuente de la recomendación (IA, Plantilla o Estática)
 * @param {Object} props
 * @param {string} props.fuente - Fuente de la recomendación: 'llm', 'plantilla', 'estatica'
 * @param {boolean} props.generadoPorLlm - Si fue generado por LLM
 * @param {boolean} props.showLabel - Mostrar etiqueta completa
 */
function FuenteBadge({ fuente, generadoPorLlm, showLabel = true }) {
  const getFuenteInfo = () => {
    switch(fuente) {
      case 'llm':
        return {
          icon: Sparkles,
          label: 'IA',
          shortLabel: 'IA',
          className: 'ai-badge',
          description: 'Recomendación generada por inteligencia artificial'
        }
      case 'plantilla':
        return {
          icon: Database,
          label: 'Reglas Estáticas',
          shortLabel: 'Reglas Estáticas',
          className: 'bg-blue-100 text-blue-700',
          description: 'Recomendación basada en reglas predefinidas'
        }
      case 'estatica':
        return {
          icon: FileCode,
          label: 'Reglas Estáticas',
          shortLabel: 'Reglas Estáticas',
          className: 'bg-gray-100 text-gray-700',
          description: 'Recomendación basada en reglas predefinidas'
        }
      default:
        return {
          icon: FileCode,
          label: 'Desconocido',
          shortLabel: '?',
          className: 'bg-gray-100 text-gray-500',
          description: 'Fuente desconocida'
        }
    }
  }

  const info = getFuenteInfo()
  const Icon = info.icon

  return (
    <div
      className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${info.className}`}
      title={info.description}
    >
      <Icon size={12} className={generadoPorLlm ? 'animate-pulse' : ''} />
      <span>{showLabel ? info.label : info.shortLabel}</span>
    </div>
  )
}

export default FuenteBadge
