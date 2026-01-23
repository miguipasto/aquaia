import React, { useState, useEffect } from 'react'
import { BarChart3, Users, Star, MessageSquare, TrendingUp, Filter } from 'lucide-react'
import api from '../../lib/api'

const ResultadosEvaluacion = () => {
  const [estadisticas, setEstadisticas] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filtroPerfil, setFiltroPerfil] = useState('todos') // 'todos', 'tecnico', 'gestion'

  useEffect(() => {
    cargarEstadisticas()
  }, [])

  const cargarEstadisticas = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get('/api/evaluaciones/estadisticas')
      setEstadisticas(response.data)
    } catch (err) {
      setError('Error cargando estadísticas')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">Cargando estadísticas...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <button
            onClick={cargarEstadisticas}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (!estadisticas) return null

  const StarDisplay = ({ valor }) => {
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-4 h-4 ${
              star <= Math.round(valor)
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-gray-300'
            }`}
          />
        ))}
        <span className="ml-2 text-sm font-medium">{valor.toFixed(2)}</span>
      </div>
    )
  }

  const getPromediosPorPerfil = () => {
    if (filtroPerfil === 'todos') {
      return {
        tecnico: estadisticas.por_perfil.tecnico?.promedios || {},
        gestion: estadisticas.por_perfil.gestion?.promedios || {}
      }
    } else if (filtroPerfil === 'tecnico') {
      return {
        tecnico: estadisticas.por_perfil.tecnico?.promedios || {}
      }
    } else {
      return {
        gestion: estadisticas.por_perfil.gestion?.promedios || {}
      }
    }
  }

  const nombresPreguntas = {
    // Técnico
    viz_claridad: 'Claridad de visualización',
    viz_incertidumbre: 'Representación de incertidumbre',
    inter_zoom: 'Funcionalidad de zoom',
    inter_navegacion: 'Navegación entre secciones',
    metricas_utilidad: 'Utilidad de métricas',
    metricas_suficiencia: 'Suficiencia de indicadores',
    
    // Gestión
    lenguaje_claridad: 'Claridad del lenguaje',
    lenguaje_profesionalidad: 'Profesionalidad del lenguaje',
    riesgos_utilidad: 'Utilidad de clasificación de riesgos',
    riesgos_priorizacion: 'Ayuda en priorización',
    informes_estructura: 'Estructura de informes',
    informes_contenido: 'Contenido de informes',
    alineacion_protocolos: 'Alineación con protocolos'
  }

  const promedios = getPromediosPorPerfil()

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Resultados de Evaluación
              </h1>
              <p className="text-gray-600">
                Análisis agregado y anónimo de las valoraciones del sistema
              </p>
            </div>
            <button
              onClick={cargarEstadisticas}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
            >
              <TrendingUp className="w-4 h-4" />
              Actualizar
            </button>
          </div>
        </div>

        {/* Filtros */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="flex items-center gap-4">
            <Filter className="w-5 h-5 text-gray-600" />
            <span className="font-medium text-gray-700">Filtrar por perfil:</span>
            <div className="flex gap-2">
              <button
                onClick={() => setFiltroPerfil('todos')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filtroPerfil === 'todos'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Todos
              </button>
              <button
                onClick={() => setFiltroPerfil('tecnico')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filtroPerfil === 'tecnico'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Técnico
              </button>
              <button
                onClick={() => setFiltroPerfil('gestion')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filtroPerfil === 'gestion'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Gestión
              </button>
            </div>
          </div>
        </div>

        {/* Resumen general */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-8 h-8 text-blue-500" />
              <h3 className="text-lg font-semibold text-gray-700">Total Evaluaciones</h3>
            </div>
            <p className="text-4xl font-bold text-gray-900">{estadisticas.total_evaluaciones}</p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-8 h-8 text-green-500" />
              <h3 className="text-lg font-semibold text-gray-700">Perfil Técnico</h3>
            </div>
            <p className="text-4xl font-bold text-gray-900">
              {estadisticas.por_perfil.tecnico?.total || 0}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-8 h-8 text-purple-500" />
              <h3 className="text-lg font-semibold text-gray-700">Perfil Gestión</h3>
            </div>
            <p className="text-4xl font-bold text-gray-900">
              {estadisticas.por_perfil.gestion?.total || 0}
            </p>
          </div>
        </div>

        {/* Promedios por pregunta */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <Star className="w-6 h-6 text-yellow-500" />
            Valoraciones Promedio por Pregunta
          </h2>

          {/* Perfil Técnico */}
          {(filtroPerfil === 'todos' || filtroPerfil === 'tecnico') && promedios.tecnico && Object.keys(promedios.tecnico).length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-green-600 mb-4">
                Perfil Técnico Operativo ({estadisticas.por_perfil.tecnico?.total || 0} evaluaciones)
              </h3>
              <div className="space-y-4">
                {Object.entries(promedios.tecnico).map(([key, valor]) => (
                  <div key={key} className="border-b border-gray-200 pb-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">
                        {nombresPreguntas[key] || key}
                      </span>
                      <StarDisplay valor={valor} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Perfil Gestión */}
          {(filtroPerfil === 'todos' || filtroPerfil === 'gestion') && promedios.gestion && Object.keys(promedios.gestion).length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-purple-600 mb-4">
                Perfil Gestión Estratégica ({estadisticas.por_perfil.gestion?.total || 0} evaluaciones)
              </h3>
              <div className="space-y-4">
                {Object.entries(promedios.gestion).map(([key, valor]) => (
                  <div key={key} className="border-b border-gray-200 pb-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">
                        {nombresPreguntas[key] || key}
                      </span>
                      <StarDisplay valor={valor} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(promedios.tecnico || {}).length === 0 && Object.keys(promedios.gestion || {}).length === 0 && (
            <p className="text-gray-500 text-center py-8">
              No hay datos disponibles para este perfil
            </p>
          )}
        </div>

        {/* Distribución de experiencia */}
        {estadisticas.distribucion_experiencia && estadisticas.distribucion_experiencia.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-6">
              Distribución de Años de Experiencia
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {estadisticas.distribucion_experiencia.map((rango) => (
                <div key={rango.rango} className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">{rango.rango}</p>
                  <p className="text-3xl font-bold text-blue-600">{rango.cantidad}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Comentarios recientes */}
        {estadisticas.comentarios_recientes && estadisticas.comentarios_recientes.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <MessageSquare className="w-6 h-6 text-blue-500" />
              Comentarios Recientes
            </h2>
            <div className="space-y-4">
              {estadisticas.comentarios_recientes.map((comentario, index) => (
                <div key={index} className="border-l-4 border-blue-500 pl-4 py-2 bg-gray-50">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      comentario.perfil === 'tecnico'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-purple-100 text-purple-700'
                    }`}>
                      {comentario.perfil === 'tecnico' ? 'Técnico' : 'Gestión'}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(comentario.fecha).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                  <p className="text-gray-700">{comentario.comentario}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ResultadosEvaluacion
