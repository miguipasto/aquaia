import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, Search } from 'lucide-react'
import useDateStore from '../../store/dateStore'
import { getEmbalses } from '../../services/dashboardService'
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner'
import Alert from '../../components/Alert/Alert'
import { formatNumber, formatPercentage, getLlenadoColor } from '../../lib/utils'

function EmbalseCard({ embalse }) {
  // Calcular porcentaje de llenado
  const porcentaje = embalse.nivel_maximo > 0 
    ? ((embalse.ultimo_nivel || 0) / embalse.nivel_maximo) * 100 
    : 0
  
  const colorClass = getLlenadoColor(porcentaje)

  return (
    <Link 
      to={`/predicciones/${embalse.codigo_saih}`}
      className="card hover:scale-105 transition-transform cursor-pointer"
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900">{embalse.ubicacion}</h3>
          <p className="text-sm text-gray-500">{embalse.codigo_saih}</p>
        </div>
        <span className={`badge badge-${colorClass}`}>
          {formatPercentage(porcentaje, 0)}
        </span>
      </div>
      
      <div className="space-y-2 mb-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Provincia:</span>
          <span className="font-medium">{embalse.provincia}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Nivel actual:</span>
          <span className="font-medium">{formatNumber(embalse.ultimo_nivel || 0)} msnm</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Capacidad:</span>
          <span className="font-medium">{formatNumber(embalse.nivel_maximo)} msnm</span>
        </div>
      </div>

      {/* Barra de progreso */}
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
        <div
          className={`bg-${colorClass}-500 h-2.5 rounded-full transition-all`}
          style={{ width: `${Math.min(porcentaje, 100)}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500">
          {embalse.demarcacion || 'Sin demarcación'}
        </span>
        <div className="flex items-center text-primary-600 font-medium">
          <TrendingUp size={16} className="mr-1" />
          <span>Ver predicción</span>
        </div>
      </div>
    </Link>
  )
}

function Predictions() {
  const { simulatedDate } = useDateStore()
  const [searchTerm, setSearchTerm] = useState('')
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
        title="Error al cargar embalses"
        message="No se pudieron cargar los embalses del sistema. Por favor, intenta de nuevo."
      />
    )
  }

  // Obtener lista única de provincias
  const provincias = [...new Set(embalses?.map(e => e.provincia).filter(Boolean))]
    .sort()

  // Filtrar embalses
  const embalsesFiltereddata = embalses?.filter(embalse => {
    const matchesSearch = embalse.ubicacion.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         embalse.codigo_saih.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesProvincia = !filterProvincia || embalse.provincia === filterProvincia
    
    return matchesSearch && matchesProvincia
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Predicciones de Embalses</h2>
        <p className="text-gray-600 mt-1">
          Selecciona un embalse para ver predicciones detalladas
        </p>
      </div>

      {/* Filtros y búsqueda */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Buscador */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Buscar embalse
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Buscar por nombre o código..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>

          {/* Filtro por provincia */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filtrar por provincia
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
        </div>

        {(searchTerm || filterProvincia) && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Mostrando {embalsesFiltereddata?.length || 0} de {embalses?.length || 0} embalses
            </p>
            <button
              onClick={() => {
                setSearchTerm('')
                setFilterProvincia('')
              }}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {/* Grid de embalses */}
      {embalsesFiltereddata?.length === 0 ? (
        <div className="card text-center py-12">
          <Search className="mx-auto text-gray-400 mb-4" size={48} />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No se encontraron embalses
          </h3>
          <p className="text-gray-600">
            Intenta con otros términos de búsqueda o filtros.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {embalsesFiltereddata?.map((embalse) => (
            <EmbalseCard key={embalse.codigo_saih} embalse={embalse} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Predictions
