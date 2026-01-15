import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { format, parseISO } from 'date-fns'

/**
 * Store global para el estado de la aplicación
 * Maneja la fecha simulada que permite "viajar en el tiempo"
 */
const useDateStore = create(
  persist(
    (set) => ({
      // Fecha simulada actual (null = usar fecha real/última disponible)
      simulatedDate: null,
      
      // Rango de fechas disponibles en el sistema
      minDate: null,
      maxDate: null,
      
      /**
       * Establece la fecha simulada
       * @param {string|Date|null} date - Fecha a simular (null para desactivar simulación)
       */
      setSimulatedDate: (date) => set({ 
        simulatedDate: date ? format(parseISO(date), 'yyyy-MM-dd') : null 
      }),
      
      /**
       * Establece el rango de fechas disponibles
       */
      setDateRange: (minDate, maxDate) => set({ minDate, maxDate }),
      
      /**
       * Resetea la fecha simulada a la actual
       */
      resetDate: () => set({ simulatedDate: null }),
      
      /**
       * Obtiene la fecha actual considerando la simulación
       * @returns {string} Fecha en formato YYYY-MM-DD
       */
      getCurrentDate: () => {
        const state = useDateStore.getState()
        return state.simulatedDate || format(new Date(), 'yyyy-MM-dd')
      },
    }),
    {
      name: 'aquaia-date-storage',
    }
  )
)

export default useDateStore
