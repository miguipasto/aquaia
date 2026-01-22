# Frontend - AquaIA Dashboard

Dashboard web interactivo para visualización de predicciones, recomendaciones e informes de gestión de embalses con simulación temporal y alertas en tiempo real.

## Requisitos

- Node.js 18+
- npm o yarn

## Instalación

```bash
# Instalar dependencias
npm install
```

## Configuración

Crear archivo `.env` en base a `.env.example`:

```bash
cp .env.example .env
```

Variables principales:
- `VITE_API_URL`: URL del backend API (por defecto: `http://localhost:8000`)

## Ejecución

### Desarrollo

```bash
npm run dev
```

Acceder a: http://localhost:5173

### Producción

```bash
# Build
npm run build

# Preview
npm run preview
```

## Características Principales

- **Vista Global**: KPIs agregados, lista de embalses con estados
- **Vista Detalle**: Gráficos históricos, predicciones a múltiples horizontes
- **Recomendaciones**: Panel con nivel de riesgo, motivo y acciones
- **Informes**: Generación y descarga de informes HTML
- **Simulación Temporal**: Navegar por fechas históricas
- **Alertas**: Sistema de notificaciones para niveles críticos
- **Responsive**: Diseño adaptativo para múltiples dispositivos

## Tecnologías

- React 18 con Hooks
- Vite (build tool rápido)
- TailwindCSS 3 (diseño utility-first)
- TanStack Query v5 (gestión estado servidor)
- Recharts (gráficos interactivos)
- Axios (cliente HTTP)
- React Router v6 (navegación)
- Zustand (estado local opcional)
