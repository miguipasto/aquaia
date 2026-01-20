import React, { useState, useEffect } from 'react'
import { X, Star, Send, CheckCircle } from 'lucide-react'
import api from '../../lib/api'

const EvaluacionModal = ({ isOpen, onClose }) => {
  const [step, setStep] = useState(1) // 1: datos básicos, 2: preguntas, 3: éxito
  const [perfil, setPerfil] = useState('tecnico')
  const [preguntas, setPreguntas] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Datos del formulario
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    organizacion: '',
    anos_experiencia: '',
    respuestas: {},
    comentarios: ''
  })

  useEffect(() => {
    if (isOpen && step === 2) {
      cargarPreguntas()
    }
  }, [isOpen, step, perfil])

  const cargarPreguntas = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/evaluaciones/preguntas/${perfil}`)
      setPreguntas(response.data.preguntas)
      // Inicializar respuestas
      const respuestasIniciales = {}
      response.data.preguntas.forEach(p => {
        respuestasIniciales[p.id] = 0
      })
      setFormData(prev => ({ ...prev, respuestas: respuestasIniciales }))
    } catch (err) {
      setError('Error cargando preguntas')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleRespuestaChange = (preguntaId, valor) => {
    setFormData(prev => ({
      ...prev,
      respuestas: { ...prev.respuestas, [preguntaId]: valor }
    }))
  }

  const handleSubmit = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Validar que todas las preguntas estén respondidas
      const respuestasCompletas = Object.values(formData.respuestas).every(v => v > 0)
      if (!respuestasCompletas) {
        setError('Por favor, responda todas las preguntas')
        setLoading(false)
        return
      }

      await api.post('/evaluaciones', {
        nombre: formData.nombre || null,
        email: formData.email || null,
        organizacion: formData.organizacion || null,
        perfil: perfil,
        anos_experiencia: formData.anos_experiencia ? parseInt(formData.anos_experiencia) : null,
        respuestas: formData.respuestas,
        comentarios: formData.comentarios || null
      })

      setStep(3) // Mostrar mensaje de éxito
    } catch (err) {
      setError(err.response?.data?.detail || 'Error enviando evaluación')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setStep(1)
    setPerfil('tecnico')
    setFormData({
      nombre: '',
      email: '',
      organizacion: '',
      anos_experiencia: '',
      respuestas: {},
      comentarios: ''
    })
    setError(null)
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  if (!isOpen) return null

  const perfiles = {
    tecnico: {
      nombre: 'Técnico Operativo',
      descripcion: 'Ingenieros y analistas que usan el sistema diariamente'
    },
    gestion: {
      nombre: 'Gestión Estratégica',
      descripcion: 'Responsables de cuenca y toma de decisiones'
    }
  }

  const StarRating = ({ valor, onChange }) => {
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className="focus:outline-none transition-colors"
          >
            <Star
              className={`w-6 h-6 ${
                star <= valor
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'text-gray-300'
              }`}
            />
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b bg-gradient-to-r from-yellow-500 to-orange-500 text-white">
          <div className="flex items-center gap-3">
            <Star className="w-6 h-6" />
            <div>
              <h2 className="text-xl font-bold">Evaluación del Sistema AquaIA</h2>
              <p className="text-sm opacity-90">Su opinión nos ayuda a mejorar</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-white/20 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          {/* Step 1: Datos básicos */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-4">Datos del Evaluador</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Los datos personales son opcionales y se manejan de forma confidencial
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nombre (opcional)
                </label>
                <input
                  type="text"
                  value={formData.nombre}
                  onChange={(e) => handleInputChange('nombre', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="Su nombre"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email (opcional)
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="su.email@ejemplo.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Organización (opcional)
                </label>
                <input
                  type="text"
                  value={formData.organizacion}
                  onChange={(e) => handleInputChange('organizacion', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="Organismo o entidad"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Perfil <span className="text-red-500">*</span>
                </label>
                <select
                  value={perfil}
                  onChange={(e) => setPerfil(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                >
                  {Object.entries(perfiles).map(([key, value]) => (
                    <option key={key} value={key}>
                      {value.nombre} - {value.descripcion}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Años de experiencia en gestión hídrica (opcional)
                </label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  value={formData.anos_experiencia}
                  onChange={(e) => handleInputChange('anos_experiencia', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="Años"
                />
              </div>

              <div className="flex justify-end pt-4">
                <button
                  onClick={() => setStep(2)}
                  className="px-6 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                >
                  Continuar
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Preguntas */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">
                  Preguntas de Evaluación - {perfiles[perfil].nombre}
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Valore de 1 (muy en desacuerdo) a 5 (muy de acuerdo)
                </p>
              </div>

              {loading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : (
                <>
                  {preguntas.map((pregunta, index) => (
                    <div key={pregunta.id} className="border-b border-gray-200 pb-4">
                      <div className="mb-2">
                        <span className="text-xs text-gray-500 uppercase">
                          {pregunta.categoria}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-800 mb-3">
                        {index + 1}. {pregunta.pregunta}
                      </p>
                      <StarRating
                        valor={formData.respuestas[pregunta.id] || 0}
                        onChange={(valor) => handleRespuestaChange(pregunta.id, valor)}
                      />
                    </div>
                  ))}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Comentarios adicionales (opcional)
                    </label>
                    <textarea
                      value={formData.comentarios}
                      onChange={(e) => handleInputChange('comentarios', e.target.value)}
                      rows="4"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                      placeholder="Sugerencias, mejoras o cualquier observación..."
                      maxLength="1000"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {formData.comentarios.length}/1000 caracteres
                    </p>
                  </div>

                  <div className="flex justify-between pt-4">
                    <button
                      onClick={() => setStep(1)}
                      className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Atrás
                    </button>
                    <button
                      onClick={handleSubmit}
                      disabled={loading}
                      className="flex items-center gap-2 px-6 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors disabled:bg-gray-400"
                    >
                      <Send className="w-4 h-4" />
                      Enviar Evaluación
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 3: Éxito */}
          {step === 3 && (
            <div className="text-center py-8">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                ¡Evaluación Enviada!
              </h3>
              <p className="text-gray-600 mb-6">
                Gracias por su tiempo. Su opinión es muy valiosa para mejorar AquaIA.
              </p>
              <button
                onClick={handleClose}
                className="px-6 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
              >
                Cerrar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default EvaluacionModal
