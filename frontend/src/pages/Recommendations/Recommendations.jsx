import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Filter, TrendingUp } from 'lucide-react'
import useDateStore from '../../store/dateStore'
import { getEmbalses, getRecomendacion } from '../../services/dashboardService'
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner'
import Alert from '../../components/Alert/Alert'
import { getRiesgoColor, formatNumber } from '../../lib/utils'

function RecomendacionCard({ embalse, fechaRef }) {
  const { data: recomendacion, isLoading } = useQuery({
    queryKey: ['recomendacion', embalse.codigo_saih, fechaRef],
    queryFn: () => getRecomendacion(embalse.codigo_saih, fechaRef),
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

  return (
    <div className={`card border-l-4 border-${riesgoColor}-500`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="font-semibold text-gray-900">{embalse.ubicacion}</h3>
            <span className={`badge badge-${riesgoColor}`}>
              {recomendacion.nivel_riesgo}
            </span>
          </div>
          <p className="text-sm text-gray-500">{embalse.provincia}</p>
        </div>
        
        <Link
          to={`/predicciones/${embalse.codigo_saih}`}
          className="btn-secondary text-sm"
        >
          <TrendingUp size={16} className="mr-1" />
          Ver detalles
        </Link>
      </div>

      <p className="text-sm text-gray-700 mb-3">
        {recomendacion.recomendacion}
      </p>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600">Nivel mín. predicho:</span>
          <span className="ml-2 font-medium">
            {formatNumber(recomendacion.nivel_min_predicho)} msnm
          </span>
        </div>
        <div>
          <span className="text-gray-600">Nivel máx. predicho:</span>
          <span className="ml-2 font-medium">
            {formatNumber(recomendacion.nivel_max_predicho)} msnm
          </span>
        </div>
      </div>

      {recomendacion.acciones && recomendacion.acciones.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-sm font-medium text-gray-700 mb-2">Acciones recomendadas:</p>
          <ul className="space-y-1">
            {recomendacion.acciones.map((accion, index) => (
              <li key={index} className="text-sm text-gray-600 flex items-start">
                <span className="mr-2">•</span>
                <span>{accion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Recommendations() {
  const { simulatedDate } = useDateStore()
  const [filterRiesgo, setFilterRiesgo] = useState('')
  const [filterProvincia, setFilterProvincia] = useState('')

  // Obtener lista de embalses
  const { data: embalses, isLoading, error } = useQuery({
    queryKey: ['embalses', simulatedDate],
    queryFn: () => getEmbalses(simulatedDate),
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

      {/* Información */}
      <Alert
        type="info"
        title="Sistema de Recomendaciones Inteligente"
        message="Las recomendaciones se generan automáticamente basándose en predicciones LSTM con datos meteorológicos AEMET y análisis de riesgo operativo."
      />

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
