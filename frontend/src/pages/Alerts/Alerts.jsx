import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Filter, X } from 'lucide-react'
import { useState } from 'react'
import useDateStore from '../../store/dateStore'
import { getAlertas } from '../../services/dashboardService'
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner'
import Alert from '../../components/Alert/Alert'
import { getSeveridadColor, getSeveridadText, formatNumber } from '../../lib/utils'
import { Link } from 'react-router-dom'

function AlertCard({ alerta }) {
  const colorClass = getSeveridadColor(alerta.severidad)
  
  return (
    <div className={`card border-l-4 border-${colorClass}-500`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <AlertTriangle className={`text-${colorClass}-500`} size={20} />
            <span className={`badge badge-${colorClass}`}>
              {getSeveridadText(alerta.severidad)}
            </span>
            <span className="text-sm text-gray-500">
              {alerta.tipo.replace(/_/g, ' ')}
            </span>
          </div>
          
          <h3 className="font-semibold text-gray-900 mb-1">
            {alerta.ubicacion}
          </h3>
          
          <p className="text-sm text-gray-600 mb-3">
            {alerta.mensaje}
          </p>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Valor actual:</span>
              <span className="ml-2 font-medium">{formatNumber(alerta.valor_actual)} msnm</span>
            </div>
            <div>
              <span className="text-gray-500">Umbral:</span>
              <span className="ml-2 font-medium">{formatNumber(alerta.umbral)} msnm</span>
            </div>
          </div>
          
          {alerta.demarcacion && (
            <p className="text-xs text-gray-500 mt-2">
              {alerta.demarcacion}
            </p>
          )}
        </div>
        
        <Link
          to={`/predicciones/${alerta.codigo_saih}`}
          className="ml-4 btn-secondary text-sm"
        >
          Ver detalles
        </Link>
      </div>
    </div>
  )
}

function Alerts() {
  const { simulatedDate } = useDateStore()
  const [filters, setFilters] = useState({
    severidad: '',
    tipo: '',
  })

  // Obtener alertas
  const { data: alertasData, isLoading, error } = useQuery({
    queryKey: ['alertas', simulatedDate, filters],
    queryFn: () => getAlertas({
      fecha_referencia: simulatedDate,
      ...filters,
    }),
  })

  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value === prev[filterType] ? '' : value,
    }))
  }

  const clearFilters = () => {
    setFilters({ severidad: '', tipo: '' })
  }

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
        title="Error al cargar alertas"
        message="No se pudieron cargar las alertas del sistema. Por favor, intenta de nuevo."
      />
    )
  }

  const alertas = alertasData?.alertas || []
  const totalAlertas = alertasData?.total_alertas || 0
  const alertasPorSeveridad = alertasData?.alertas_por_severidad || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Sistema de Alertas</h2>
        <p className="text-gray-600 mt-1">
          Monitoreo en tiempo real de condiciones críticas
          {simulatedDate && (
            <span className="ml-2 text-warning-600 font-medium">
              (Simulación: {simulatedDate})
            </span>
          )}
        </p>
      </div>

      {/* Resumen de alertas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-gray-50">
          <div className="text-center">
            <p className="text-sm text-gray-600">Total</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{totalAlertas}</p>
          </div>
        </div>
        
        <div className="card bg-danger-50">
          <div className="text-center">
            <p className="text-sm text-danger-700">Críticas</p>
            <p className="text-3xl font-bold text-danger-700 mt-1">
              {alertasPorSeveridad.critical || 0}
            </p>
          </div>
        </div>
        
        <div className="card bg-warning-50">
          <div className="text-center">
            <p className="text-sm text-warning-700">Advertencias</p>
            <p className="text-3xl font-bold text-warning-700 mt-1">
              {alertasPorSeveridad.warning || 0}
            </p>
          </div>
        </div>
        
        <div className="card bg-primary-50">
          <div className="text-center">
            <p className="text-sm text-primary-700">Información</p>
            <p className="text-3xl font-bold text-primary-700 mt-1">
              {alertasPorSeveridad.info || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Filter size={20} className="text-gray-500" />
            <h3 className="font-semibold text-gray-900">Filtros</h3>
          </div>
          {(filters.severidad || filters.tipo) && (
            <button
              onClick={clearFilters}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center space-x-1"
            >
              <X size={16} />
              <span>Limpiar filtros</span>
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Filtro por severidad */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severidad
            </label>
            <div className="flex flex-wrap gap-2">
              {['critical', 'warning', 'info'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => handleFilterChange('severidad', sev)}
                  className={`
                    px-3 py-1 rounded-full text-sm font-medium transition-all
                    ${filters.severidad === sev
                      ? `bg-${getSeveridadColor(sev)}-500 text-white`
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  {getSeveridadText(sev)}
                </button>
              ))}
            </div>
          </div>

          {/* Filtro por tipo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de alerta
            </label>
            <div className="flex flex-wrap gap-2">
              {['NIVEL_CRITICO_BAJO', 'NIVEL_BAJO', 'NIVEL_ALTO', 'NIVEL_CRITICO_ALTO'].map((tipo) => (
                <button
                  key={tipo}
                  onClick={() => handleFilterChange('tipo', tipo)}
                  className={`
                    px-3 py-1 rounded-full text-sm font-medium transition-all
                    ${filters.tipo === tipo
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  {tipo.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Lista de alertas */}
      {alertas.length === 0 ? (
        <div className="card text-center py-12">
          <AlertTriangle className="mx-auto text-gray-400 mb-4" size={48} />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No hay alertas activas
          </h3>
          <p className="text-gray-600">
            {filters.severidad || filters.tipo
              ? 'No se encontraron alertas con los filtros seleccionados.'
              : 'Todos los embalses están operando dentro de rangos normales.'
            }
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Alertas Activas ({alertas.length})
          </h3>
          
          {alertas.map((alerta) => (
            <AlertCard key={alerta.id} alerta={alerta} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Alerts
