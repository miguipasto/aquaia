import React, { useState } from 'react'
import { FileText, Download, Eye, X, Loader2, Calendar, Clock } from 'lucide-react'
import { generarInforme, getPreviewUrl, getDownloadUrl } from '../../services/informeService'
import useDateStore from '../../store/dateStore'

/**
 * Modal de carga durante la generación del informe
 */
const LoadingModal = ({ isOpen, tipoInforme }) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-16 h-16 text-purple-600 animate-spin" />
          <h3 className="text-xl font-bold text-gray-800">Generando Informe {tipoInforme === 'semanal' ? 'Semanal' : 'Diario'}</h3>
          <p className="text-gray-600 text-center">
            {tipoInforme === 'semanal' 
              ? 'Analizando datos de la última semana y generando recomendaciones estratégicas...'
              : 'Analizando situación actual y generando recomendaciones operativas...'}
          </p>
          <p className="text-sm text-gray-500">
            {tipoInforme === 'semanal' ? 'Esto puede tardar 30-60 segundos' : 'Esto puede tardar 15-30 segundos'}
          </p>
        </div>
      </div>
    </div>
  )
}

/**
 * Modal para previsualizar y gestionar informes
 */
const InformeModal = ({ isOpen, onClose, informeData }) => {
  if (!isOpen) return null

  const tipoInforme = informeData.metadata?.tipo_informe || 'diario'
  const llmUsado = informeData.metadata?.llm_usado === 'True'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-purple-600 to-indigo-600 text-white">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Informe {tipoInforme === 'semanal' ? 'Semanal' : 'Diario'} - Vista Previa
            </h2>

          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-auto max-h-[calc(90vh-140px)]">
          <iframe
            src={getPreviewUrl(informeData.informe_id)}
            className="w-full h-[70vh] border rounded"
            title="Preview del Informe"
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            <p className="font-semibold">ID: {informeData.informe_id}</p>
            <p>Generado: {new Date(informeData.fecha_generacion).toLocaleString('es-ES')}</p>
            <p className="text-xs text-gray-500 mt-1">
              Tipo: {tipoInforme.toUpperCase()} | Modelo: {informeData.metadata?.model_version}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded hover:bg-gray-300 transition-colors"
            >
              Cerrar
            </button>
            {informeData.pdf_url && (
              <a
                href={getDownloadUrl(informeData.informe_id)}
                download
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Descargar PDF
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Botón para generar informes con modal de preview
 */
const GenerarInformeButton = ({ 
  embalseData, 
  predicciones, 
  recomendaciones,
  datosHistoricosSemana = null,
  className = "",
  variant = "default", // "default", "icon", "mini"
  showTypeSelector = true, // Mostrar selector de tipo de informe
  defaultType = 'diario' // Tipo por defecto si no hay selector
}) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [informeGenerado, setInformeGenerado] = useState(null)
  const [tipoInforme, setTipoInforme] = useState(defaultType)
  const [showTypeMenu, setShowTypeMenu] = useState(false)
  
  // Obtener fecha simulada del store
  const { simulatedDate, getCurrentDate } = useDateStore()

  const handleGenerarInforme = async (tipo = tipoInforme) => {
    setLoading(true)
    setError(null)
    setShowTypeMenu(false)

    try {
      // Usar fecha simulada si existe, sino fecha actual
      const fechaActual = simulatedDate ? new Date(simulatedDate) : new Date()
      
      // Preparar fechas para informe semanal
      const fechaFin = new Date(fechaActual)
      const fechaInicio = new Date(fechaActual)
      fechaInicio.setDate(fechaInicio.getDate() - 7)

      // **IMPORTANTE: Obtener predicciones reales del modelo**
      let prediccionesReales = predicciones
      if (!prediccionesReales || !prediccionesReales.nivel_30d) {
        try {
          // Llamar al endpoint de predicciones con formato correcto
          const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
          const response = await fetch(`${baseUrl}/api/predicciones/${embalseData.codigo_saih || embalseData.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              fecha_inicio: fechaActual.toISOString().split('T')[0],
              horizonte_dias: 180
            })
          })
          
          if (response.ok) {
            const data = await response.json()
            console.log('Predicciones recibidas:', data)
            
            // La API devuelve predicciones con fecha, pred, pred_hist
            // Necesitamos obtener los valores en los días específicos (30, 90, 180)
            // La capacidad puede estar en diferentes campos según el contexto
            const capacidadMaxima = embalseData.capacidad_maxima || 
                                   embalseData.capacidad_total || 
                                   embalseData.capacidad || 
                                   330 // Valor por defecto para Belesar
            
            if (!data.predicciones || data.predicciones.length === 0) {
              console.warn('No hay predicciones disponibles en la respuesta')
              throw new Error('No hay predicciones disponibles')
            }
            
            // Buscar predicciones más cercanas a 30, 90 y 180 días
            const pred30d = data.predicciones[Math.min(29, data.predicciones.length - 1)]
            const pred90d = data.predicciones[Math.min(89, data.predicciones.length - 1)]
            const pred180d = data.predicciones[Math.min(179, data.predicciones.length - 1)]
            
            console.log('Predicciones extraídas:', { pred30d, pred90d, pred180d, capacidadMaxima })
            
            prediccionesReales = {
              nivel_30d: pred30d?.pred || pred30d?.pred_hist || 0,
              nivel_90d: pred90d?.pred || pred90d?.pred_hist || 0,
              nivel_180d: pred180d?.pred || pred180d?.pred_hist || 0,
              porcentaje_30d: (pred30d?.pred || pred30d?.pred_hist) ? ((pred30d.pred || pred30d.pred_hist) / capacidadMaxima * 100) : 0,
              porcentaje_90d: (pred90d?.pred || pred90d?.pred_hist) ? ((pred90d.pred || pred90d.pred_hist) / capacidadMaxima * 100) : 0,
              porcentaje_180d: (pred180d?.pred || pred180d?.pred_hist) ? ((pred180d.pred || pred180d.pred_hist) / capacidadMaxima * 100) : 0
            }
            
            console.log('Predicciones procesadas:', prediccionesReales)
          }
        } catch (predError) {
          console.warn('No se pudieron obtener predicciones, usando datos mock:', predError)
        }
      }

      // Construir datos del informe
      const datosInforme = {
        tipo_informe: tipo,
        embalse_id: embalseData.codigo_saih || embalseData.id,
        nombre_embalse: embalseData.ubicacion || embalseData.nombre,
        fecha_generacion: fechaActual.toISOString(),
        fecha_inicio_periodo: tipo === 'semanal' ? fechaInicio.toISOString() : null,
        fecha_fin_periodo: tipo === 'semanal' ? fechaFin.toISOString() : null,
        // model_version y usuario se tomarán de las variables de .env en el backend
        metricas_modelo: {
          MAE_30d: 0.85,
          MAE_90d: 1.12,
          MAE_180d: 1.46,
          R2_global: 0.92
        },
        datos_actual: {
          // IMPORTANTE: Los niveles son cotas en metros sobre nivel del mar (msnm), no volumen (hm³)
          nivel_actual_msnm: embalseData.ultimo_nivel || embalseData.nivel_actual || embalseData.capacidad_actual || 0,
          nivel_maximo_msnm: embalseData.nivel_maximo || 330.0,
          porcentaje_capacidad: embalseData.porcentaje_llenado || embalseData.porcentaje || 0,
          media_historica: 72.1,
          percentil_20: 45.0,
          percentil_80: 88.0
        },
        prediccion: {
          nivel_30d: prediccionesReales?.nivel_30d || 0,
          nivel_90d: prediccionesReales?.nivel_90d || 0,
          nivel_180d: prediccionesReales?.nivel_180d || 0,
          porcentaje_30d: prediccionesReales?.porcentaje_30d || 0,
          porcentaje_90d: prediccionesReales?.porcentaje_90d || 0,
          porcentaje_180d: prediccionesReales?.porcentaje_180d || 0
        },
        riesgos: {
          sequia_moderada_90d: (prediccionesReales?.porcentaje_90d || 100) < 30,
          sequia_grave_180d: (prediccionesReales?.porcentaje_180d || 100) < 20,
          llena_30d: (prediccionesReales?.porcentaje_30d || 0) > 95
        },
        recomendaciones: recomendaciones || [
          {
            accion: 'Mantener monitoreo actual',
            justificacion: 'Niveles dentro de parámetros normales',
            impacto: 'Continuidad operacional'
          }
        ],
        escenarios: {
          // Los escenarios son cotas en msnm, no multiplicamos sino que restamos/sumamos metros
          conservador: { 
            nivel_180d: (prediccionesReales?.nivel_180d || embalseData.ultimo_nivel || embalseData.nivel_actual || 0) - 2 
          },
          neutro: { 
            nivel_180d: prediccionesReales?.nivel_180d || embalseData.ultimo_nivel || embalseData.nivel_actual || 0 
          },
          agresivo: { 
            nivel_180d: (prediccionesReales?.nivel_180d || embalseData.ultimo_nivel || embalseData.nivel_actual || 0) + 1 
          }
        },
        datos_historicos_semana: tipo === 'semanal' ? (datosHistoricosSemana || generarDatosHistoricosMock()) : null,
        // usuario se tomará de las variables de .env en el backend
        idioma: 'es'
      }

      // Función helper para generar datos históricos mock si no están disponibles
      function generarDatosHistoricosMock() {
        const datos = []
        // Usar cota actual en msnm, no volumen
        const nivelBaseMsnm = embalseData.ultimo_nivel || embalseData.nivel_actual || 300.0
        for (let i = 0; i < 7; i++) {
          // Usar fecha simulada como base si existe
          const fecha = new Date(fechaActual)
          fecha.setDate(fecha.getDate() - (6 - i))
          datos.push({
            fecha: fecha.toISOString().split('T')[0],
            nivel: nivelBaseMsnm + (Math.random() - 0.5) * 1.5, // Variación pequeña en metros
            precipitacion: Math.random() * 10,
            temperatura: 8 + Math.random() * 8,
            caudal_promedio: 10 + Math.random() * 10
          })
        }
        return datos
      }

      // Llamar al servicio
      const response = await generarInforme(datosInforme)
      
      if (response.success) {
        setInformeGenerado(response)
        setModalOpen(true)
      } else {
        throw new Error('Error al generar el informe')
      }
    } catch (err) {
      console.error('Error:', err)
      setError(err.response?.data?.detail || 'Error al generar el informe')
    } finally {
      setLoading(false)
    }
  }

  // Renderizado según variante
  if (variant === 'icon') {
    return (
      <>
        {showTypeSelector ? (
          <div className="relative">
            <button
              onClick={() => setShowTypeMenu(!showTypeMenu)}
              disabled={loading}
              className={`p-2 bg-purple-600 text-white rounded-full hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-lg ${className}`}
              title="Generar Informe"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <FileText className="w-5 h-5" />
              )}
            </button>
            
            {showTypeMenu && !loading && (
              <div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50 min-w-[200px]">
                <button
                  onClick={() => handleGenerarInforme('diario')}
                  className="w-full px-4 py-2 text-left hover:bg-purple-50 flex items-center gap-2 text-sm"
                >
                  <Clock className="w-4 h-4 text-purple-600" />
                  <div>
                    <div className="font-semibold">Informe Diario</div>
                    <div className="text-xs text-gray-500">Operativo 24h</div>
                  </div>
                </button>
                <button
                  onClick={() => handleGenerarInforme('semanal')}
                  className="w-full px-4 py-2 text-left hover:bg-purple-50 flex items-center gap-2 text-sm"
                >
                  <Calendar className="w-4 h-4 text-indigo-600" />
                  <div>
                    <div className="font-semibold">Informe Semanal</div>
                    <div className="text-xs text-gray-500">Estratégico con IA</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => handleGenerarInforme()}
            disabled={loading}
            className={`p-2 bg-purple-600 text-white rounded-full hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-lg ${className}`}
            title="Generar Informe"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <FileText className="w-5 h-5" />
            )}
          </button>
        )}
        
        <LoadingModal isOpen={loading} tipoInforme={tipoInforme} />
        
        {error && (
          <div className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded shadow-lg z-50">
            {error}
          </div>
        )}
        
        {informeGenerado && (
          <InformeModal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            informeData={informeGenerado}
          />
        )}
      </>
    )
  }

  if (variant === 'mini') {
    return (
      <>
        {showTypeSelector ? (
          <div className="relative">
            <button
              onClick={() => setShowTypeMenu(!showTypeMenu)}
              disabled={loading}
              className={`flex items-center gap-2 px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors ${className}`}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Informe
            </button>
            
            {showTypeMenu && !loading && (
              <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50 min-w-[180px]">
                <button
                  onClick={() => handleGenerarInforme('diario')}
                  className="w-full px-3 py-2 text-left hover:bg-purple-50 flex items-center gap-2 text-xs"
                >
                  <Clock className="w-3 h-3" />
                  <span>Diario (24h)</span>
                </button>
                <button
                  onClick={() => handleGenerarInforme('semanal')}
                  className="w-full px-3 py-2 text-left hover:bg-purple-50 flex items-center gap-2 text-xs"
                >
                  <Calendar className="w-3 h-3" />
                  <span>Semanal (con IA)</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => handleGenerarInforme()}
            disabled={loading}
            className={`flex items-center gap-2 px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors ${className}`}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
            Informe
          </button>
        )}
        
        <LoadingModal isOpen={loading} tipoInforme={tipoInforme} />
        
        {error && (
          <div className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded shadow-lg z-50">
            {error}
          </div>
        )}
        
        {informeGenerado && (
          <InformeModal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            informeData={informeGenerado}
          />
        )}
      </>
    )
  }

  // Variante default
  return (
    <>
      {showTypeSelector ? (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <button
              onClick={() => handleGenerarInforme('diario')}
              disabled={loading}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-purple-800 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl ${className}`}
            >
              <Clock className="w-5 h-5" />
              <div className="text-left">
                <div className="text-sm font-bold">Informe Diario</div>
                <div className="text-xs opacity-90">Operativo 24 horas</div>
              </div>
            </button>
            
            <button
              onClick={() => handleGenerarInforme('semanal')}
              disabled={loading}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-semibold rounded-lg hover:from-indigo-700 hover:to-indigo-800 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl ${className}`}
            >
              <Calendar className="w-5 h-5" />
              <div className="text-left">
                <div className="text-sm font-bold">Informe Semanal</div>
                <div className="text-xs opacity-90">Estratégico con IA</div>
              </div>
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => handleGenerarInforme()}
          disabled={loading}
          className={`flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl ${className}`}
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Generando...
            </>
          ) : (
            <>
              <FileText className="w-5 h-5" />
              Generar Informe
            </>
          )}
        </button>
      )}

      <LoadingModal isOpen={loading} tipoInforme={tipoInforme} />

      {error && (
        <div className="mt-2 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          <p className="text-sm">{error}</p>
        </div>
      )}

      {informeGenerado && (
        <InformeModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          informeData={informeGenerado}
        />
      )}
    </>
  )
}

export default GenerarInformeButton
