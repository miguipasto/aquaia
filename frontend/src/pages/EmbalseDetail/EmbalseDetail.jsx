import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { 
  ArrowLeft, 
  TrendingUp, 
  Droplets, 
  Calendar,
  Eye,
  EyeOff,
  Activity
} from 'lucide-react'
import {
  LineChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  ComposedChart,
} from 'recharts'
import useDateStore from '../../store/dateStore'
import {
  getEmbalseActual,
  getHistorico,
  generarPrediccion,
  getRecomendacion,
} from '../../services/dashboardService'
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner'
import Alert from '../../components/Alert/Alert'
import {
  formatNumber,
  formatPercentage,
  formatDate,
  getEstadoColor,
  getEstadoText,
  getRiesgoColor,
} from '../../lib/utils'
import { format, subDays, parseISO } from 'date-fns'

function EmbalseDetail() {
  const { codigoSaih } = useParams()
  const navigate = useNavigate()
  const { simulatedDate } = useDateStore()
  
  const [showRealData, setShowRealData] = useState(false)
  const [horizonteDias, setHorizonteDias] = useState(90)

  // Calcular fecha de inicio para predicción (la fecha simulada actual o hoy)
  const fechaInicio = simulatedDate || format(new Date(), 'yyyy-MM-dd')

  // Obtener datos actuales del embalse
  const { data: embalseActual, isLoading: loadingActual } = useQuery({
    queryKey: ['embalse-actual', codigoSaih, simulatedDate],
    queryFn: () => getEmbalseActual(codigoSaih, simulatedDate),
  })

  // Obtener histórico (últimos 180 días desde la fecha simulada)
  const fechaHistoricoInicio = simulatedDate
    ? format(subDays(parseISO(simulatedDate), 180), 'yyyy-MM-dd')
    : format(subDays(new Date(), 180), 'yyyy-MM-dd')
  
  const { data: historico, isLoading: loadingHistorico } = useQuery({
    queryKey: ['historico', codigoSaih, fechaHistoricoInicio, simulatedDate],
    queryFn: () => getHistorico(codigoSaih, fechaHistoricoInicio, simulatedDate || undefined),
  })

  // Generar predicción
  const { data: prediccion, isLoading: loadingPrediccion, error: errorPrediccion } = useQuery({
    queryKey: ['prediccion', codigoSaih, fechaInicio, horizonteDias],
    queryFn: () => generarPrediccion(codigoSaih, {
      fecha_inicio: fechaInicio,
      horizonte_dias: horizonteDias,
    }),
    enabled: !!fechaInicio,
    retry: 1,
  })

  // Obtener recomendación
  const { data: recomendacion, isLoading: loadingRecomendacion, error: errorRecomendacion } = useQuery({
    queryKey: ['recomendacion', codigoSaih, simulatedDate, horizonteDias],
    queryFn: () => getRecomendacion(codigoSaih, simulatedDate, horizonteDias),
    retry: 1,
  })

  if (loadingActual || loadingHistorico) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="xl" />
      </div>
    )
  }

  if (!embalseActual) {
    return (
      <div className="space-y-4">
        <Alert
          type="error"
          title="Embalse no encontrado"
          message={`No se encontró el embalse con código ${codigoSaih}`}
        />
        <button onClick={() => navigate('/predicciones')} className="btn-secondary">
          <ArrowLeft size={20} className="mr-2" />
          Volver a la lista
        </button>
      </div>
    )
  }

  // Preparar datos para el gráfico
  const chartData = []
  
  // Añadir datos históricos
  if (historico) {
    historico.forEach(punto => {
      chartData.push({
        fecha: punto.fecha,
        nivel_real: punto.nivel,
        lluvia: punto.precipitacion,
        tipo: 'historico',
      })
    })
  }

  // Añadir predicciones
  if (prediccion) {
    prediccion.predicciones.forEach(punto => {
      const existingPoint = chartData.find(p => p.fecha === punto.fecha)
      if (existingPoint) {
        existingPoint.pred_hist = punto.pred_hist
        existingPoint.pred = punto.pred
        if (showRealData && punto.nivel_real !== null) {
          existingPoint.nivel_real = punto.nivel_real
        }
        existingPoint.tipo = 'prediccion'
      } else {
        chartData.push({
          fecha: punto.fecha,
          pred_hist: punto.pred_hist,
          pred: punto.pred,
          nivel_real: (showRealData && punto.nivel_real !== null) ? punto.nivel_real : undefined,
          tipo: 'prediccion',
        })
      }
    })
  }

  // Calcular MAE si se muestran los datos reales
  const mae = showRealData && prediccion ? (() => {
    const puntosConError = prediccion.predicciones.filter(p => p.nivel_real !== null && p.pred !== null)
    if (puntosConError.length === 0) return null
    const sumaError = puntosConError.reduce((acc, p) => acc + Math.abs(p.nivel_real - p.pred), 0)
    return sumaError / puntosConError.length
  })() : null

  const estadoColor = getEstadoColor(embalseActual.estado)
  const nivelRiesgo = recomendacion?.nivel_riesgo
  const riesgoColor = nivelRiesgo ? getRiesgoColor(nivelRiesgo) : 'gray'

  return (
    <div className="space-y-6">
      {/* Navegación */}
      <button 
        onClick={() => navigate('/predicciones')}
        className="flex items-center text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft size={20} className="mr-2" />
        Volver a la lista
      </button>

      {/* Header del embalse */}
      <div className="card">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <Droplets className="text-water-500" size={32} />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {embalseActual.ubicacion}
                </h1>
                <p className="text-gray-600">{embalseActual.codigo_saih}</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <div>
                <p className="text-sm text-gray-600">Provincia</p>
                <p className="font-medium">{embalseActual.provincia}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Comunidad</p>
                <p className="font-medium">{embalseActual.comunidad_autonoma}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Demarcación</p>
                <p className="font-medium text-sm">{embalseActual.demarcacion}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Fecha Referencia</p>
                <p className="font-medium">{formatDate(embalseActual.fecha_referencia)}</p>
              </div>
            </div>
          </div>

          <div className="mt-4 lg:mt-0 lg:ml-8">
            <div className="text-center">
              <span className={`badge badge-${estadoColor} text-lg px-4 py-2`}>
                {getEstadoText(embalseActual.estado)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPIs del embalse */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-water-50">
          <p className="text-sm text-water-700 mb-1">Nivel Actual</p>
          <p className="text-2xl font-bold text-water-700">
            {formatNumber(embalseActual.nivel_actual)} msnm
          </p>
          <p className="text-sm text-water-600 mt-1">
            {formatPercentage(embalseActual.porcentaje_llenado)} de capacidad
          </p>
        </div>

        <div className="card">
          <p className="text-sm text-gray-600 mb-1">Capacidad Máxima</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatNumber(embalseActual.nivel_maximo)} msnm
          </p>
        </div>

        <div className="card">
          <p className="text-sm text-gray-600 mb-1">Variación 30 días</p>
          <p className={`text-2xl font-bold ${
            embalseActual.variacion_30d > 0 ? 'text-success-600' : 
            embalseActual.variacion_30d < 0 ? 'text-danger-600' : 
            'text-gray-900'
          }`}>
            {embalseActual.variacion_30d > 0 ? '+' : ''}
            {formatNumber(embalseActual.variacion_30d)} hm³
          </p>
        </div>

        <div className="card">
          <p className="text-sm text-gray-600 mb-1">Precipitación 30d</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatNumber(embalseActual.precipitacion_acumulada_30d || 0)} mm
          </p>
        </div>
      </div>

      {/* Recomendación operativa */}
      {errorRecomendacion && (
        <Alert
          type="warning"
          title="Recomendación no disponible"
          message={`No se pudo generar la recomendación para esta fecha. ${errorRecomendacion.response?.data?.detail || errorRecomendacion.message}`}
        />
      )}
      {recomendacion && !errorRecomendacion && (
        <div className={`card border-l-4 border-${riesgoColor}-500`}>
          <div className="flex items-start space-x-4">
            <Activity className={`text-${riesgoColor}-500 flex-shrink-0`} size={24} />
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <h3 className="text-lg font-semibold text-gray-900">
                  Recomendación Operativa
                </h3>
                <span className={`badge badge-${riesgoColor}`}>
                  {nivelRiesgo}
                </span>
              </div>
              <p className="text-gray-700 mb-3">{recomendacion.motivo}</p>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
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
                <div>
                  <span className="text-gray-600">Días analizados:</span>
                  <span className="ml-2 font-medium">{recomendacion.horizonte_dias}</span>
                </div>
              </div>
              
              {recomendacion.accion_recomendada && (
                <div className="mt-4 p-3 bg-white/50 rounded border border-gray-100 italic text-sm text-gray-800">
                  <span className="font-semibold not-italic text-gray-900 mr-2">Acción:</span>
                  {recomendacion.accion_recomendada}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Controles del gráfico */}
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Horizonte de Predicción
            </label>
            <select
              value={horizonteDias}
              onChange={(e) => setHorizonteDias(Number(e.target.value))}
              className="input w-48"
            >
              <option value={30}>30 días</option>
              <option value={60}>60 días</option>
              <option value={90}>90 días</option>
              <option value={120}>120 días</option>
              <option value={180}>180 días</option>
            </select>
          </div>

          <button
            onClick={() => setShowRealData(!showRealData)}
            className={`btn ${showRealData ? 'btn-primary' : 'btn-secondary'}`}
          >
            {showRealData ? (
              <>
                <EyeOff size={18} className="mr-2" />
                Ocultar datos reales
              </>
            ) : (
              <>
                <Eye size={18} className="mr-2" />
                Mostrar lo que pasó realmente
              </>
            )}
          </button>
        </div>
      </div>

      {/* Gráfico de predicción */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Evolución y Predicción del Nivel
        </h3>
        
        {errorPrediccion && (
          <Alert
            type="warning"
            title="Predicción no disponible"
            message={`No se pudo generar la predicción para esta fecha. ${errorPrediccion.response?.data?.detail || errorPrediccion.message}`}
          />
        )}
        
        {loadingPrediccion ? (
          <div className="flex items-center justify-center h-96">
            <LoadingSpinner />
          </div>
        ) : !errorPrediccion && (
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis 
                  dataKey="fecha" 
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  stroke="#9ca3af"
                />
                <YAxis 
                  yAxisId="left"
                  stroke="#2563eb"
                  tick={{ fontSize: 12 }}
                  domain={['auto', 'auto']}
                  label={{ value: 'Nivel (msnm)', angle: -90, position: 'insideLeft', style: { fill: '#2563eb', fontWeight: 600 } }}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  stroke="#0ea5e9"
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Lluvia (mm)', angle: 90, position: 'insideRight', style: { fill: '#0ea5e9', fontWeight: 600 } }}
                />
                
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-white p-4 border border-gray-200 shadow-xl rounded-lg">
                          <p className="font-bold text-gray-700 mb-2">{formatDate(label)}</p>
                          <div className="space-y-1">
                            {payload.map((entry, index) => {
                              const isRain = entry.dataKey === 'lluvia'
                              const unit = isRain ? 'mm' : 'msnm'
                              return (
                                <div key={index} className="flex justify-between items-center gap-4">
                                  <div className="flex items-center">
                                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: entry.color }} />
                                    <span className="text-xs font-medium text-gray-600">
                                      {entry.name}:
                                    </span>
                                  </div>
                                  <span className="text-xs font-bold text-gray-900">
                                    {formatNumber(entry.value)} {unit}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Legend verticalAlign="top" height={36}/>
                
                {/* Zona de Predicción (Futuro) */}
                {simulatedDate && (
                  <ReferenceArea 
                    x1={simulatedDate} 
                    x2={chartData[chartData.length - 1]?.fecha} 
                    yAxisId="left"
                    fill="#f8fafc" 
                    fillOpacity={0.5} 
                  />
                )}

                {/* Línea de hoy */}
                {simulatedDate && (
                  <ReferenceLine 
                    x={simulatedDate} 
                    stroke="#ef4444" 
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    label={{ 
                      value: 'Hoy', 
                      position: 'top', 
                      fill: '#ef4444',
                      fontSize: 12,
                      fontWeight: 'bold'
                    }}
                    yAxisId="left"
                  />
                )}
                
                {/* Lluvia (Barras) */}
                <Bar
                  yAxisId="right"
                  dataKey="lluvia"
                  fill="#0ea5e9"
                  name="Precipitación"
                  barSize={10}
                  opacity={0.3}
                />

                {/* Líneas del gráfico */}
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="nivel_real"
                  stroke="#2563eb"
                  strokeWidth={3}
                  dot={false}
                  name="Nivel real"
                  animationDuration={1500}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="pred_hist"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  name="Modelo Base (Solo hist.)"
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="pred"
                  stroke="#10b981"
                  strokeWidth={3}
                  dot={false}
                  name="Modelo Avanzado (AEMET)"
                  animationDuration={2000}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}

        {showRealData && (
          <div className="mt-6 border-t pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 text-blue-700 mb-2">
                  <Activity size={20} />
                  <h4 className="font-semibold">Métricas de Validación</h4>
                </div>
                <div className="flex items-baseline space-x-3">
                  <span className="text-3xl font-bold text-blue-900">
                    {mae ? formatNumber(mae) : '--'}
                  </span>
                  <span className="text-sm text-blue-700 font-medium">
                    MAE (Error Absoluto Medio) en msnm
                  </span>
                </div>
                <p className="text-xs text-blue-600 mt-2">
                  * Calculado dinámicamente comparando la predicción con los datos reales observados en el periodo de validación.
                </p>
              </div>

              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 text-green-700 mb-2">
                  <TrendingUp size={20} />
                  <h4 className="font-semibold">Insight del Modelo</h4>
                </div>
                <p className="text-sm text-green-800 italic">
                  {mae === null ? 
                    "No hay suficientes datos reales para calcular la precisión en este rango." :
                    mae < 0.5 ? 
                    "El modelo presenta una precisión excepcional para este embalse, permitiendo una toma de decisiones de alta confianza." :
                    mae < 1.5 ? 
                    "La precisión es adecuada para planificación operativa a medio plazo." :
                    "Se observa una desviación mayor de lo habitual; se recomienda precaución en maniobras críticas basándose solo en la tendencia."
                  }
                </p>
              </div>
            </div>
            
            <div className="mt-4">
              <Alert
                type="info"
                message="Se están mostrando los datos reales para comparar con las predicciones. En un escenario real, estos datos no estarían disponibles."
              />
            </div>
          </div>
        )}
      </div>

      {/* Estadísticas adicionales */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Estadísticas de los Últimos 30 Días
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-600 mb-2">Nivel Mínimo</p>
            <p className="text-xl font-bold text-gray-900">
              {formatNumber(embalseActual.nivel_min_30d)} msnm
            </p>
          </div>
          
          <div>
            <p className="text-sm text-gray-600 mb-2">Nivel Medio</p>
            <p className="text-xl font-bold text-gray-900">
              {formatNumber(embalseActual.nivel_medio_30d)} msnm
            </p>
          </div>
          
          <div>
            <p className="text-sm text-gray-600 mb-2">Nivel Máximo</p>
            <p className="text-xl font-bold text-gray-900">
              {formatNumber(embalseActual.nivel_max_30d)} msnm
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EmbalseDetail
