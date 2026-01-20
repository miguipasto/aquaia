import { useQuery } from '@tanstack/react-query'
import { 
  Droplets, 
  TrendingUp, 
  TrendingDown, 
  AlertCircle,
  Activity 
} from 'lucide-react'
import useDateStore from '../../store/dateStore'
import { getKPIs, getEmbalses } from '../../services/dashboardService'
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner'
import Alert from '../../components/Alert/Alert'
import { formatNumber, formatPercentage, getLlenadoColor } from '../../lib/utils'
import { Link } from 'react-router-dom'

function KPICard({ title, value, subtitle, icon: Icon, trend, color = 'primary' }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`text-3xl font-bold text-${color}-600 mt-2`}>{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
          {trend && (
            <div className="flex items-center mt-2 space-x-1">
              {trend === 'aumento' ? (
                <>
                  <TrendingUp size={16} className="text-success-500" />
                  <span className="text-xs text-success-600">Tendencia al alza</span>
                </>
              ) : trend === 'descenso' ? (
                <>
                  <TrendingDown size={16} className="text-danger-500" />
                  <span className="text-xs text-danger-600">Tendencia a la baja</span>
                </>
              ) : (
                <>
                  <Activity size={16} className="text-gray-500" />
                  <span className="text-xs text-gray-600">Estable</span>
                </>
              )}
            </div>
          )}
        </div>
        <div className={`p-4 bg-${color}-50 rounded-lg`}>
          <Icon className={`text-${color}-500`} size={32} />
        </div>
      </div>
    </div>
  )
}

const calcularPorcentajeLlenado = (nivelActual, nivelMaximo) => {
  if (!nivelMaximo || nivelMaximo <= 0) return 0
  return ((nivelActual || 0) / nivelMaximo) * 100
}

function EmbalseCard({ embalse }) {
  const porcentajeLlenado = calcularPorcentajeLlenado(
    embalse.ultimo_nivel, 
    embalse.nivel_maximo
  )
  const colorClass = getLlenadoColor(porcentajeLlenado)

  return (
    <Link 
      to={`/predicciones/${embalse.codigo_saih}`}
      className="card hover:scale-105 transition-transform cursor-pointer"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">{embalse.ubicacion}</h3>
          <p className="text-sm text-gray-500">{embalse.provincia}</p>
        </div>
        <span className={`badge badge-${colorClass}`}>
          {formatPercentage(porcentajeLlenado, 0)}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Nivel actual:</span>
          <span className="font-medium">{formatNumber(embalse.ultimo_nivel || 0)} msnm</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Capacidad:</span>
          <span className="font-medium">{formatNumber(embalse.nivel_maximo)} msnm</span>
        </div>
        
        <div className="mt-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`bg-${colorClass}-500 h-2 rounded-full transition-all`}
              style={{ width: `${Math.min(porcentajeLlenado, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </Link>
  )
}

function Dashboard() {
  const { simulatedDate } = useDateStore()

  // Obtener KPIs
  const { data: kpis, isLoading: loadingKPIs, error: errorKPIs } = useQuery({
    queryKey: ['kpis', simulatedDate],
    queryFn: () => getKPIs(simulatedDate),
  })

  // Obtener lista de embalses
  const { data: embalses, isLoading: loadingEmbalses } = useQuery({
    queryKey: ['embalses', simulatedDate],
    queryFn: () => getEmbalses(simulatedDate),
  })

  if (loadingKPIs || loadingEmbalses) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="xl" />
      </div>
    )
  }

  if (errorKPIs) {
    return (
      <Alert
        type="error"
        title="Error al cargar datos"
        message="No se pudieron cargar los KPIs del sistema. Por favor, intenta de nuevo."
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Dashboard General</h2>
        <p className="text-gray-600 mt-1">
          Visión general del sistema de embalses
          {simulatedDate && (
            <span className="ml-2 text-warning-600 font-medium">
              (Simulación: {simulatedDate})
            </span>
          )}
        </p>
      </div>

      {/* KPIs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Embalses Monitorizados"
          value={kpis?.num_embalses || 0}
          icon={Droplets}
          color="primary"
        />
        
        <KPICard
          title="Llenado Promedio"
          value={formatPercentage(kpis?.porcentaje_llenado_promedio || 0, 1)}
          subtitle={`${formatNumber(kpis?.nivel_total_actual || 0)} / ${formatNumber(kpis?.capacidad_total || 0)} msnm`}
          icon={Activity}
          color="water"
          trend={kpis?.tendencia}
        />
        
        <KPICard
          title="Embalses Críticos"
          value={kpis?.num_embalses_criticos || 0}
          subtitle={`${((kpis?.num_embalses_criticos || 0) / (kpis?.num_embalses || 1) * 100).toFixed(0)}% del total`}
          icon={AlertCircle}
          color={kpis?.num_embalses_criticos > 0 ? 'danger' : 'success'}
        />
        
        <KPICard
          title="Alertas Activas"
          value={kpis?.num_alertas_activas || 0}
          subtitle="Sistema de monitoreo"
          icon={AlertCircle}
          color={kpis?.num_alertas_activas > 0 ? 'warning' : 'success'}
        />
      </div>

      {/* Alertas importantes */}
      {kpis?.num_alertas_activas > 0 && (
        <Alert
          type="warning"
          title="Alertas activas en el sistema"
          message={
            <Link to="/alertas" className="underline font-medium">
              Ver {kpis.num_alertas_activas} alerta{kpis.num_alertas_activas !== 1 ? 's' : ''} →
            </Link>
          }
        />
      )}

      {/* Lista de embalses */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-900">
            Embalses del Sistema
          </h3>
          <Link to="/predicciones" className="text-primary-600 hover:text-primary-700 font-medium">
            Ver predicciones →
          </Link>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {embalses?.slice(0, 9).map((embalse) => (
            <EmbalseCard 
              key={embalse.codigo_saih} 
              embalse={embalse}
              fechaReferencia={simulatedDate}
            />
          ))}
        </div>

        {embalses && embalses.length > 9 && (
          <div className="text-center mt-6">
            <Link 
              to="/predicciones"
              className="btn-primary"
            >
              Ver todos los embalses ({embalses.length})
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
