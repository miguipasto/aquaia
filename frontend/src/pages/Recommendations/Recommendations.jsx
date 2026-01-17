import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Filter, TrendingUp, Sparkles, RefreshCw, Zap, Database, FileCode } from 'lucide-react'
import useDateStore from '../../store/dateStore'
import { getEmbalses, getRecomendacion, getLLMSalud, getLLMEstadisticas, generarRecomendacionForzada } from '../../services/dashboardService'
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner'
import Alert from '../../components/Alert/Alert'
import FuenteBadge from '../../components/FuenteBadge/FuenteBadge'
import { getRiesgoColor, formatNumber } from '../../lib/utils'

function RecomendacionCard({ embalse, fechaRef }) {
  const queryClient = useQueryClient()
  const { data: recomendacion, isLoading, refetch } = useQuery({
    queryKey: ['recomendacion', embalse.codigo_saih, fechaRef],
    queryFn: () => getRecomendacion(embalse.codigo_saih, fechaRef),
    refetchInterval: (data) => {
      // Si la fuente no es 'llm' y existe, refetch cada 10 segundos para obtener versión con IA
      if (data && data.fuente_recomendacion !== 'llm') {
        return 10000
      }
      return false
    }
  })

  const regenerarMutation = useMutation({
    mutationFn: () => generarRecomendacionForzada(embalse.codigo_saih, {
      fecha_inicio: fechaRef,
      horizonte_dias: 7
    }),
    onSuccess: () => {
      // Esperar un momento y luego hacer refetch continuo
      setTimeout(() => {
        queryClient.invalidateQueries(['recomendacion', embalse.codigo_saih, fechaRef])
      }, 1000)
    }
  })

  if (isLoading) {
    return (
      <div className="card">
        <LoadingSpinner size="sm" />
      </div>
    )
  }

  if (!recomendacion) {
    return null
  }

  const riesgoColor = getRiesgoColor(recomendacion.nivel_riesgo)
  const esProcesamientoIA = recomendacion.fuente_recomendacion !== 'llm' && recomendacion.fuente_recomendacion !== 'plantilla'

  return (
    <div className={`card border-l-4 border-${riesgoColor}-500 relative`}>
      {/* Indicador de procesamiento en background */}
      {esProcesamientoIA && (
        <div className="absolute top-3 left-3">
          <div className="flex items-center space-x-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
            <RefreshCw size={12} className="animate-spin" />
            <span>Generando con IA...</span>
          </div>
        </div>
      )}
      
      {/* Badge de fuente y botón de regeneración */}
      <div className="absolute top-3 right-3 flex items-center space-x-2">
        <FuenteBadge 
          fuente={recomendacion.fuente_recomendacion}
          generadoPorLlm={recomendacion.generado_por_llm}
          showLabel={false}
        />
        <button
          onClick={() => regenerarMutation.mutate()}
          disabled={regenerarMutation.isPending}
          className="p-1.5 hover:bg-gray-100 rounded-full transition-colors disabled:opacity-50"
          title="Regenerar recomendación"
        >
          <RefreshCw 
            size={14} 
            className={`text-gray-600 ${regenerarMutation.isPending ? 'animate-spin' : ''}`}
          />
        </button>
      </div>

      <div className="flex items-start justify-between mb-3 pr-20">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="font-semibold text-gray-900">{embalse.ubicacion}</h3>
            <span className={`badge badge-${riesgoColor}`}>
              {recomendacion.nivel_riesgo}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <span>{embalse.provincia}</span>
            {recomendacion.horizonte_dias && (
              <>
                <span className="text-gray-400">•</span>
                <span>Horizonte: {recomendacion.horizonte_dias}d</span>
              </>
            )}
          </div>
        </div>
      </div>

      <p className="text-sm text-gray-700 mb-3">
        {recomendacion.motivo}
      </p>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600">Nivel mín. predicho:</span>
          <span className="ml-2 font-medium">
            {formatNumber(recomendacion.nivel_predicho_min)} msnm
          </span>
        </div>
        <div>
          <span className="text-gray-600">Nivel máx. predicho:</span>
          <span className="ml-2 font-medium">
            {formatNumber(recomendacion.nivel_predicho_max)} msnm
          </span>
        </div>
      </div>

      {recomendacion.accion_recomendada && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-sm font-medium text-gray-700 mb-2">Acciones recomendadas:</p>
          <div 
            className="text-sm text-gray-600 prose prose-sm max-w-none"
            style={{ listStylePosition: 'inside' }}
            dangerouslySetInnerHTML={{ __html: recomendacion.accion_recomendada }}
          />
        </div>
      )}
    </div>
  )
}

function Recommendations() {
  const { simulatedDate } = useDateStore()
  const [filterRiesgo, setFilterRiesgo] = useState('')
  const [filterProvincia, setFilterProvincia] = useState('')
  const [showLLMInfo, setShowLLMInfo] = useState(false)

  // Obtener lista de embalses
  const { data: embalses, isLoading, error } = useQuery({
    queryKey: ['embalses', simulatedDate],
    queryFn: () => getEmbalses(simulatedDate),
  })

  // Obtener estado de Ollama
  const { data: llmSalud } = useQuery({
    queryKey: ['llm-salud'],
    queryFn: getLLMSalud,
    refetchInterval: 30000, // Refrescar cada 30 segundos
  })

  // Obtener estadísticas de LLM
  const { data: llmStats } = useQuery({
    queryKey: ['llm-stats'],
    queryFn: getLLMEstadisticas,
    enabled: showLLMInfo,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="xl" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert
        type="error"
        title="Error al cargar datos"
        message="No se pudieron cargar las recomendaciones. Por favor, intenta de nuevo."
      />
    )
  }

  // Obtener lista única de provincias
  const provincias = [...new Set(embalses?.map(e => e.provincia).filter(Boolean))].sort()

  // Filtrar embalses
  const embalsesFiltered = embalses?.filter(embalse => {
    const matchesProvincia = !filterProvincia || embalse.provincia === filterProvincia
    return matchesProvincia
  }).slice(0, 20) // Limitar a 20 para no saturar

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Recomendaciones Operativas</h2>
        <p className="text-gray-600 mt-1">
          Análisis predictivo y recomendaciones para la gestión de embalses
          {simulatedDate && (
            <span className="ml-2 text-warning-600 font-medium">
              (Simulación: {simulatedDate})
            </span>
          )}
        </p>
      </div>

      {/* Estado de IA */}
      {llmSalud && (
        <div className="card bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className={`mt-1 p-2 rounded-full ${
                llmSalud.disponible && llmSalud.modelo_disponible
                  ? 'bg-green-100 text-green-600'
                  : 'bg-yellow-100 text-yellow-600'
              }`}>
                <Zap size={20} />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <h3 className="font-semibold text-gray-900">Sistema de IA (Ollama)</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    llmSalud.disponible && llmSalud.modelo_disponible
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {llmSalud.disponible && llmSalud.modelo_disponible ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                <p className="text-sm text-gray-600">
                  {llmSalud.disponible && llmSalud.modelo_disponible ? (
                    <>
                      Modelo <span className="font-mono font-medium">{llmSalud.modelo_configurado}</span> disponible.
                      Las recomendaciones se generan con IA para mayor precisión contextual.
                    </>
                  ) : (
                    'IA no disponible. Usando recomendaciones basadas en plantillas.'
                  )}
                </p>
                {showLLMInfo && llmStats && (
                  <div className="mt-3 pt-3 border-t border-purple-200 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Total peticiones:</span>
                      <span className="ml-2 font-medium">{llmStats.servicio.total_requests}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Cache hits:</span>
                      <span className="ml-2 font-medium">{llmStats.servicio.cache_hit_rate}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Éxito LLM:</span>
                      <span className="ml-2 font-medium">{llmStats.servicio.llm_success_rate}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Errores:</span>
                      <span className="ml-2 font-medium">{llmStats.servicio.llm_errors}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={() => setShowLLMInfo(!showLLMInfo)}
              className="text-xs text-purple-600 hover:text-purple-700 font-medium"
            >
              {showLLMInfo ? 'Ocultar' : 'Ver'} estadísticas
            </button>
          </div>
        </div>
      )}

      {/* Información */}
      {/* Filtros */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-4">
          <Filter size={20} className="text-gray-500" />
          <h3 className="font-semibold text-gray-900">Filtros</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Filtro por provincia */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provincia
            </label>
            <select
              value={filterProvincia}
              onChange={(e) => setFilterProvincia(e.target.value)}
              className="input"
            >
              <option value="">Todas las provincias</option>
              {provincias.map(provincia => (
                <option key={provincia} value={provincia}>
                  {provincia}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro por nivel de riesgo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nivel de Riesgo
            </label>
            <div className="flex flex-wrap gap-2">
              {['ALTO', 'MODERADO', 'BAJO', 'SEQUÍA'].map((nivel) => (
                <button
                  key={nivel}
                  onClick={() => setFilterRiesgo(filterRiesgo === nivel ? '' : nivel)}
                  className={`
                    px-3 py-1 rounded-full text-sm font-medium transition-all
                    ${filterRiesgo === nivel
                      ? `bg-${getRiesgoColor(nivel)}-500 text-white`
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  {nivel}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Lista de recomendaciones */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">
            Recomendaciones Generadas
          </h3>
          <p className="text-sm text-gray-600">
            Mostrando {embalsesFiltered?.length || 0} embalses
          </p>
        </div>

        {embalsesFiltered?.length === 0 ? (
          <div className="card text-center py-12">
            <FileText className="mx-auto text-gray-400 mb-4" size={48} />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No hay recomendaciones disponibles
            </h3>
            <p className="text-gray-600">
              Ajusta los filtros para ver más resultados.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {embalsesFiltered?.map((embalse) => (
              <RecomendacionCard
                key={embalse.codigo_saih}
                embalse={embalse}
                fechaRef={simulatedDate}
              />
            ))}
          </div>
        )}
      </div>

      {/* Leyenda de niveles de riesgo */}
      <div className="card bg-gray-50">
        <h3 className="font-semibold text-gray-900 mb-3">Niveles de Riesgo</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="badge badge-danger">ALTO</span>
            <p className="mt-1 text-gray-600">≥ 95% de capacidad máxima</p>
          </div>
          <div>
            <span className="badge badge-warning">MODERADO</span>
            <p className="mt-1 text-gray-600">80-95% de capacidad</p>
          </div>
          <div>
            <span className="badge badge-success">BAJO</span>
            <p className="mt-1 text-gray-600">30-80% de capacidad</p>
          </div>
          <div>
            <span className="badge badge-danger">SEQUÍA</span>
            <p className="mt-1 text-gray-600">≤ 30% de capacidad máxima</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Recommendations
