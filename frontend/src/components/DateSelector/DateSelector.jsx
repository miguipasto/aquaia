import { Calendar, RotateCcw } from 'lucide-react'
import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import useDateStore from '../../store/dateStore'

function DateSelector() {
  const { simulatedDate, setSimulatedDate, resetDate } = useDateStore()
  const [showPicker, setShowPicker] = useState(false)
  const [selectedDate, setSelectedDate] = useState(simulatedDate || format(new Date(), 'yyyy-MM-dd'))

  useEffect(() => {
    if (simulatedDate) {
      setSelectedDate(simulatedDate)
    }
  }, [simulatedDate])

  const handleDateChange = (e) => {
    const newDate = e.target.value
    setSelectedDate(newDate)
  }

  const handleApply = () => {
    setSimulatedDate(selectedDate)
    setShowPicker(false)
  }

  const handleReset = () => {
    resetDate()
    setSelectedDate(format(new Date(), 'yyyy-MM-dd'))
    setShowPicker(false)
  }

  const isSimulating = simulatedDate !== null

  return (
    <div className="relative">
      <button
        onClick={() => setShowPicker(!showPicker)}
        className={`
          flex items-center space-x-2 px-4 py-2 rounded-lg border transition-all
          ${isSimulating 
            ? 'bg-warning-50 border-warning-300 text-warning-800 hover:bg-warning-100' 
            : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
          }
        `}
      >
        <Calendar size={18} />
        <span className="text-sm font-medium">
          {isSimulating ? (
            <>
              <span className="hidden sm:inline">Simulando: </span>
              {format(new Date(simulatedDate), 'dd MMM yyyy', { locale: es })}
            </>
          ) : (
            <>
              <span className="hidden sm:inline">Fecha: </span>
              <span className="sm:hidden">Hoy</span>
              <span className="hidden sm:inline">Actual</span>
            </>
          )}
        </span>
      </button>

      {showPicker && (
        <>
          {/* Overlay */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowPicker(false)}
          />
          
          {/* Picker panel */}
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
            <div className="p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Simulación Temporal
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Selecciona una fecha
                  </label>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={handleDateChange}
                    max={format(new Date(), 'yyyy-MM-dd')}
                    className="input"
                  />
                  <p className="mt-2 text-xs text-gray-500">
                    El dashboard mostrará datos como si estuvieras en esta fecha.
                    No verás datos posteriores.
                  </p>
                </div>

                <div className="flex space-x-2">
                  <button
                    onClick={handleApply}
                    className="btn-primary flex-1"
                  >
                    Aplicar
                  </button>
                  
                  {isSimulating && (
                    <button
                      onClick={handleReset}
                      className="btn-secondary flex items-center space-x-1"
                    >
                      <RotateCcw size={16} />
                      <span>Restablecer</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default DateSelector
