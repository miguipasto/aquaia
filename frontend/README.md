# Frontend - AquaAI Dashboard

Dashboard web interactivo para visualización de predicciones y recomendaciones de embalses.

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

## Tecnologías

- React 18
- Vite
- TailwindCSS
- TanStack Query (React Query)
- Recharts
- Axios
