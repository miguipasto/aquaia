import React, { useState, useEffect } from 'react'
import { FileText, Download, Clock, Calendar, TrendingUp, AlertTriangle } from 'lucide-react'
import { listarInformes } from '../../services/informeService'
import { getEmbalses, getEmbalseActual } from '../../services/dashboardService'
import GenerarInformeButton from '../../components/GenerarInforme/GenerarInformeButton'
import useDateStore from '../../store/dateStore'

/**
 * Página de gestión de informes
 */
const Informes = () => {
  const [informesGenerados, setInformesGenerados] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroTipo, setFiltroTipo] = useState('todos') // todos, diario, semanal
  const [embalses, setEmbalses] = useState([])
  const [embalseSeleccionado, setEmbalseSeleccionado] = useState(null)
  const [datosActualesEmbalse, setDatosActualesEmbalse] = useState(null)
  const { simulatedDate } = useDateStore()

  useEffect(() => {
    cargarInformes()
    cargarEmbalses()
  }, [])

  const cargarInformes = async () => {
    try {
      setLoading(true)
      const data = await listarInformes()
      setInformesGenerados(data.informes || [])
    } catch (error) {
      console.error('Error cargando informes:', error)
    } finally {
      setLoading(false)
    }
  }

  const cargarEmbalses = async () => {
    try {
      const data = await getEmbalses(simulatedDate)
      setEmbalses(data || [])
      // Seleccionar el primer embalse por defecto
      if (data && data.length > 0) {
        setEmbalseSeleccionado(data[0])
      }
    } catch (error) {
      console.error('Error cargando embalses:', error)
    }
  }

  useEffect(() => {
    if (embalseSeleccionado) {
      const fetchActual = async () => {
        try {
          const actual = await getEmbalseActual(embalseSeleccionado.codigo_saih, simulatedDate)
          setDatosActualesEmbalse(actual)
        } catch (err) {
          setDatosActualesEmbalse(null)
        }
      }
      fetchActual()
    }
  }, [embalseSeleccionado, simulatedDate])

  const informesFiltrados = informesGenerados.filter(informe => {
    if (filtroTipo === 'todos') return true
    return informe.tipo_informe === filtroTipo
  })

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Gestión de Informes</h1>
          <p className="text-gray-600">
            Genera informes diarios y semanales de situación hidrológica
          </p>
          {simulatedDate && (
            <div className="mt-3 flex items-center gap-2 text-sm text-warning-700 bg-warning-50 border border-warning-300 rounded-lg px-4 py-2 w-fit">
              <Calendar className="w-4 h-4" />
              <span>Los informes se generarán con fecha: <strong>{new Date(simulatedDate).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}</strong></span>
            </div>
          )}
        </div>

        {/* Sección de Generación */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="w-6 h-6 text-purple-600" />
            Generar Nuevo Informe
          </h2>
          
          {/* Selector de Embalse */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Seleccionar Embalse
            </label>
            <select
              value={embalseSeleccionado?.codigo_saih || ''}
              onChange={(e) => {
                const embalse = embalses.find(em => em.codigo_saih === e.target.value)
                setEmbalseSeleccionado(embalse)
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {embalses.map((embalse) => (
                <option key={embalse.codigo_saih} value={embalse.codigo_saih}>
                  {embalse.ubicacion || embalse.nombre} ({embalse.codigo_saih}) - {embalse.provincia}
                </option>
              ))}
            </select>
            {embalseSeleccionado && (
              <p className="mt-2 text-sm text-gray-600">
                Nivel actual: <strong>{datosActualesEmbalse?.nivel_actual?.toFixed(2) || embalseSeleccionado.nivel_actual?.toFixed(2) || 'N/A'} msnm</strong> |
                Capacidad: <strong>{datosActualesEmbalse?.porcentaje_llenado?.toFixed(1) || embalseSeleccionado.porcentaje_llenado?.toFixed(1) || 'N/A'}%</strong>
              </p>
            )}
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            {/* Informe Diario */}
            <div className="border border-purple-200 rounded-lg p-6 bg-purple-50">
              <div className="flex items-start gap-4 mb-4">
                <div className="p-3 bg-purple-600 rounded-lg text-white">
                  <Clock className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Informe Diario</h3>
                  <p className="text-sm text-gray-600">Operativo de 24 horas</p>
                </div>
              </div>
              
              <ul className="text-sm text-gray-700 space-y-2 mb-4">
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  Situación actual del embalse
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  Predicción 24-48 horas
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  Análisis IA de situación
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  Recomendaciones operativas
                </li>
              </ul>
              
              <GenerarInformeButton
                embalseData={embalseSeleccionado || embalses[0]}
                predicciones={null}
                recomendaciones={null}
                showTypeSelector={false}
                defaultType="diario"
                className="w-full"
                variant="default"
              />
            </div>

            {/* Informe Semanal */}
            <div className="border border-indigo-200 rounded-lg p-6 bg-indigo-50">
              <div className="flex items-start gap-4 mb-4">
                <div className="p-3 bg-indigo-600 rounded-lg text-white">
                  <Calendar className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Informe Semanal</h3>
                  <p className="text-sm text-gray-600">Estratégico con análisis IA</p>
                </div>
              </div>
              
              <ul className="text-sm text-gray-700 space-y-2 mb-4">
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-600" />
                  Evolución última semana
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-600" />
                  Predicción 30/90/180 días
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-600" />
                  Análisis avanzado con IA
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-600" />
                  Recomendaciones estratégicas
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-600" />
                  Plan de acción semanal
                </li>
              </ul>
              
              <GenerarInformeButton
                embalseData={embalseSeleccionado || embalses[0]}
                predicciones={null}
                recomendaciones={null}
                showTypeSelector={false}
                defaultType="semanal"
                className="w-full"
                variant="default"
              />
            </div>
          </div>
        </div>

        {/* Historial de Informes */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <FileText className="w-6 h-6 text-gray-600" />
              Historial de Informes Generados
            </h2>
            
            <div className="flex gap-2">
              <button
                onClick={() => setFiltroTipo('todos')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filtroTipo === 'todos'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Todos
              </button>
              <button
                onClick={() => setFiltroTipo('diario')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filtroTipo === 'diario'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Diarios
              </button>
              <button
                onClick={() => setFiltroTipo('semanal')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filtroTipo === 'semanal'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Semanales
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-4 text-gray-600">Cargando informes...</p>
            </div>
          ) : informesFiltrados.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600">No hay informes generados aún</p>
              <p className="text-sm text-gray-500 mt-2">
                Genera tu primer informe usando los botones de arriba
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {informesFiltrados.map((informe) => (
                <div
                  key={informe.informe_id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-lg ${
                        informe.tipo_informe === 'semanal'
                          ? 'bg-indigo-100 text-indigo-600'
                          : 'bg-purple-100 text-purple-600'
                      }`}>
                        {informe.tipo_informe === 'semanal' ? (
                          <Calendar className="w-5 h-5" />
                        ) : (
                          <Clock className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {informe.nombre_embalse}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {informe.tipo_informe === 'semanal' ? 'Informe Semanal' : 'Informe Diario'} | 
                          {' '}{new Date(informe.fecha_generacion).toLocaleString('es-ES')}
                        </p>
                        <p className="text-xs text-gray-500">ID: {informe.informe_id}</p>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <a
                        href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/informes/preview/${informe.informe_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                      >
                        Ver
                      </a>
                      {informe.pdf_path && (
                        <a
                          href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/informes/download/${informe.informe_id}.pdf`}
                          download
                          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          PDF
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Informes
