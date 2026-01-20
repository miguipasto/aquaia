import { Link, useLocation } from 'react-router-dom'
import { 
  Home, 
  TrendingUp, 
  AlertTriangle, 
  FileText,
  Droplets,
  Menu,
  X,
  Star,
  BarChart3
} from 'lucide-react'
import { useState } from 'react'
import DateSelector from '../DateSelector/DateSelector'
import EvaluacionModal from '../EvaluacionModal/EvaluacionModal'

const NAV_ITEMS = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Predicciones', href: '/predicciones', icon: TrendingUp },
  { name: 'Alertas', href: '/alertas', icon: AlertTriangle },
  { name: 'Recomendaciones', href: '/recomendaciones', icon: FileText },
  { name: 'Informes', href: '/informes', icon: FileText },
  { name: 'Resultados Evaluación', href: '/evaluaciones/resultados', icon: BarChart3 },
]

const APP_CONFIG = {
  title: 'AquaIA',
  subtitle: 'Sistema Inteligente de Gestión de Embalses',
}

function Layout({ children }) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [evaluacionOpen, setEvaluacionOpen] = useState(false)

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)
  const closeSidebar = () => setSidebarOpen(false)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <button
                onClick={toggleSidebar}
                className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
                aria-label="Toggle sidebar"
              >
                {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
              
              <Droplets className="h-8 w-8 text-water-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {APP_CONFIG.title}
                </h1>
                <p className="text-sm text-gray-500">
                  {APP_CONFIG.subtitle}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <DateSelector />
              <button
                onClick={() => setEvaluacionOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors shadow-md"
                title="Evaluar el sistema"
              >
                <Star className="w-5 h-5" />
                <span className="hidden sm:inline">Valorar</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <EvaluacionModal 
        isOpen={evaluacionOpen} 
        onClose={() => setEvaluacionOpen(false)} 
      />

      <div className="flex">
        <aside
          className={`
            fixed lg:static inset-y-0 left-0 z-30 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out mt-[73px] lg:mt-0
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          `}
        >
          <nav className="h-full px-4 py-6 space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.href
              const Icon = item.icon
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={closeSidebar}
                  className={`
                    flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors
                    ${isActive
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                    }
                  `}
                >
                  <Icon size={20} />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </aside>

        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-20 lg:hidden mt-[73px]"
            onClick={closeSidebar}
            aria-hidden="true"
          />
        )}

        <main className="flex-1 min-h-[calc(100vh-73px)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
