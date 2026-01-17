import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './pages/Dashboard/Dashboard'
import Predictions from './pages/Predictions/Predictions'
import Alerts from './pages/Alerts/Alerts'
import Recommendations from './pages/Recommendations/Recommendations'
import EmbalseDetail from './pages/EmbalseDetail/EmbalseDetail'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/predicciones" element={<Predictions />} />
          <Route path="/predicciones/:codigoSaih" element={<EmbalseDetail />} />
          <Route path="/alertas" element={<Alerts />} />
          <Route path="/recomendaciones" element={<Recommendations />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
