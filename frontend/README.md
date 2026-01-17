# Dashboard AquaIA - Frontend

Dashboard inteligente en React para el sistema de gestión y predicción de niveles de embalses AquaIA.

## 🌊 Características Principales

### 🎯 Simulación Temporal
- **Selector de Fecha**: Permite simular cualquier fecha histórica como "hoy"
- El dashboard muestra solo datos anteriores a la fecha seleccionada
- Perfecto para análisis retrospectivo y validación de modelos

### 📊 Dashboard Principal
- **KPIs del Sistema**: Métricas agregadas en tiempo real
  - Número total de embalses monitorizados
  - Porcentaje de llenado promedio
  - Embalses en estado crítico
  - Alertas activas
- **Visualización de Tendencias**: Indicadores de tendencia (alza, baja, estable)
- **Vista General de Embalses**: Tarjetas interactivas con estado actual

### 🔮 Predicciones
- **Lista Completa de Embalses**: Con búsqueda y filtros
- **Detalle de Embalse Individual**:
  - Gráfico interactivo de evolución histórica y predicción
  - Predicción dual: solo histórico vs. con datos meteorológicos AEMET
  - Botón "Mostrar lo que pasó realmente" para comparación
  - KPIs del embalse (nivel actual, capacidad, variación)
  - Estadísticas de 30 días
- **Horizontes Configurables**: 30, 60, 90, 120 o 180 días

### 🚨 Sistema de Alertas
- **Monitoreo Automático**: Detecta condiciones críticas
- **Tipos de Alertas**:
  - Nivel Crítico Bajo (< 20%)
  - Nivel Bajo (< 30%)
  - Nivel Alto (> 80%)
  - Nivel Crítico Alto (> 95%)
- **Filtros Avanzados**: Por severidad, tipo y demarcación
- **Severidades**: Critical, Warning, Info

### 📋 Recomendaciones Operativas
- **Análisis Predictivo**: Basado en modelos LSTM + datos AEMET
- **Niveles de Riesgo**:
  - ALTO: ≥ 95% de capacidad
  - MODERADO: 80-95% de capacidad
  - BAJO: 30-80% de capacidad
  - SEQUÍA: ≤ 30% de capacidad
- **Acciones Sugeridas**: Recomendaciones específicas por embalse

## 🛠️ Tecnologías Utilizadas

- **React 18**: Framework principal
- **Vite**: Build tool y dev server
- **React Router**: Navegación
- **TanStack Query (React Query)**: Gestión de estado servidor
- **Zustand**: Gestión de estado global (fecha simulada)
- **Recharts**: Gráficos interactivos
- **Tailwind CSS**: Estilos
- **Lucide React**: Iconografía
- **Axios**: Cliente HTTP
- **date-fns**: Manipulación de fechas

## 📁 Estructura del Proyecto

```
frontend/
├── public/
├── src/
│   ├── components/          # Componentes reutilizables
│   │   ├── Layout/         # Layout principal con navegación
│   │   ├── DateSelector/   # Selector de fecha simulada
│   │   ├── LoadingSpinner/ # Indicador de carga
│   │   └── Alert/          # Componente de alertas
│   ├── pages/              # Páginas principales
│   │   ├── Dashboard/      # Dashboard principal con KPIs
│   │   ├── Predictions/    # Lista de embalses
│   │   ├── EmbalseDetail/  # Detalle y predicción de embalse
│   │   ├── Alerts/         # Sistema de alertas
│   │   └── Recommendations/# Recomendaciones operativas
│   ├── services/           # Servicios de API
│   │   └── dashboardService.js
│   ├── store/              # Estado global
│   │   └── dateStore.js    # Store de fecha simulada
│   ├── lib/                # Utilidades
│   │   ├── api.js          # Configuración de Axios
│   │   └── utils.js        # Funciones de utilidad
│   ├── App.jsx             # Componente raíz
│   ├── main.jsx            # Punto de entrada
│   └── index.css           # Estilos globales
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 🚀 Instalación y Uso

### 1. Instalar dependencias

```bash
cd frontend
npm install
```

### 2. Configurar variables de entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

Edita `.env` y configura la URL de la API:

```
VITE_API_URL=http://localhost:8000
```

### 3. Iniciar servidor de desarrollo

```bash
npm run dev
```

El dashboard estará disponible en `http://localhost:3000`

### 4. Construir para producción

```bash
npm run build
```

Los archivos se generarán en `dist/`

### 5. Vista previa de producción

```bash
npm run preview
```

## 🔧 Configuración

### Proxy de API

El archivo `vite.config.js` incluye un proxy para facilitar el desarrollo:

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```

Esto permite hacer peticiones a `/api/...` que se redirigen automáticamente al backend.

### Tailwind CSS

Los colores personalizados del proyecto están definidos en `tailwind.config.js`:

- `primary`: Azul corporativo
- `water`: Tonos de agua/cyan
- `danger`: Rojo para alertas críticas
- `warning`: Amarillo para advertencias
- `success`: Verde para estados OK

## 🎨 Temas Visuales

### Estados del Embalse

- **Normal**: Verde - 30-80% de capacidad
- **Bajo**: Amarillo - 20-30% de capacidad
- **Crítico Bajo**: Rojo - < 20% de capacidad
- **Alto**: Amarillo - 80-95% de capacidad
- **Crítico Alto**: Rojo - > 95% de capacidad

### Severidad de Alertas

- **Critical**: Rojo - Requiere acción inmediata
- **Warning**: Amarillo - Requiere atención
- **Info**: Azul - Informativo

## 📡 Endpoints de API Utilizados

### Dashboard
- `GET /dashboard/kpis` - KPIs agregados del sistema
- `GET /dashboard/embalses/:codigo/actual` - Datos actuales de un embalse
- `GET /dashboard/alertas` - Alertas activas

### Embalses
- `GET /embalses` - Lista de todos los embalses
- `GET /embalses/:codigo/historico` - Serie histórica
- `GET /embalses/:codigo/resumen` - Resumen estadístico

### Predicciones
- `POST /predicciones/:codigo` - Generar predicción

### Recomendaciones
- `GET /recomendaciones/:codigo` - Recomendación operativa

## 🎯 Casos de Uso

### 1. Análisis Retrospectivo
- Selecciona una fecha histórica en el selector de fecha
- Navega por el dashboard como si estuvieras en ese día
- Útil para validar predicciones pasadas

### 2. Monitoreo en Tiempo Real
- No selecciones ninguna fecha (modo actual)
- Visualiza el estado actual de todos los embalses
- Recibe alertas de condiciones críticas

### 3. Planificación Operativa
- Accede a las recomendaciones operativas
- Revisa las predicciones a diferentes horizontes
- Toma decisiones basadas en el análisis predictivo

### 4. Comparación de Predicciones
- En la vista de detalle de embalse, haz una predicción
- Haz clic en "Mostrar lo que pasó realmente"
- Compara la predicción con los datos reales

## 🐛 Solución de Problemas

### Error de conexión con la API

Asegúrate de que:
1. El backend está corriendo en `http://localhost:8000`
2. La variable `VITE_API_URL` en `.env` es correcta
3. No hay problemas de CORS (el backend debe permitir el origen del frontend)

### Gráficos no se muestran

Verifica que:
1. Hay datos disponibles para el embalse seleccionado
2. La fecha de simulación no está fuera del rango de datos históricos
3. La predicción se generó correctamente (revisa la consola)

### Alertas no aparecen

Comprueba:
1. Que la fecha de referencia tiene datos
2. Que hay embalses en estados críticos
3. Los filtros de severidad/tipo no están excluyendo todas las alertas

## 📝 Mejoras Futuras

- [ ] Exportación de gráficos como imágenes
- [ ] Exportación de datos a CSV/Excel
- [ ] Comparación lado a lado de múltiples embalses
- [ ] Mapas interactivos con ubicación de embalses
- [ ] Notificaciones push para alertas críticas
- [ ] Dashboard personalizable con widgets arrastrables
- [ ] Modo oscuro
- [ ] Soporte multi-idioma

## 📄 Licencia

Este proyecto es parte del TFM de AquaIA.
