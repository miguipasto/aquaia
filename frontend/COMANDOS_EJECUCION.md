# Lista de Comandos para Ejecutar el Sistema AquaIA

## 1️⃣ BACKEND (API)

### Opción A: Desde el directorio api/
```bash
cd /home/migui/master/TFM/aquaia/api
python run.py
```

### Opción B: Con uvicorn directamente
```bash
cd /home/migui/master/TFM/aquaia/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Resultado esperado**: La API estará corriendo en http://localhost:8000


## 2️⃣ FRONTEND (Dashboard React)

```bash
cd /home/migui/master/TFM/aquaia/frontend
npm install
npm run dev
```

**Resultado esperado**: El dashboard estará en http://localhost:3000


## 📝 NOTAS IMPORTANTES

1. **Base de Datos**: Asegúrate de que PostgreSQL está corriendo:
   ```bash
   cd /home/migui/master/TFM/aquaia/data/database
   docker-compose up -d
   ```

2. **Orden de ejecución**:
   - Primero: Base de datos
   - Segundo: Backend (API)
   - Tercero: Frontend

3. **Verificar que funciona**:
   - API: http://localhost:8000/docs
   - Dashboard: http://localhost:3000

4. **Detener servicios**:
   - API: Ctrl+C en la terminal
   - Frontend: Ctrl+C en la terminal
   - Base de datos: `docker-compose down` en data/database/


## 🚀 COMANDOS RÁPIDOS (COPIAR Y PEGAR)

### Terminal 1 (Base de Datos)
```bash
cd /home/migui/master/TFM/aquaia/data/database && docker-compose up -d
```

### Terminal 2 (Backend)
```bash
cd /home/migui/master/TFM/aquaia/api && python run.py
```

### Terminal 3 (Frontend - solo la primera vez)
```bash
cd /home/migui/master/TFM/aquaia/frontend && npm install && npm run dev
```

### Terminal 3 (Frontend - siguientes veces)
```bash
cd /home/migui/master/TFM/aquaia/frontend && npm run dev
```


## ✅ VERIFICACIÓN RÁPIDA

Después de ejecutar todo, verifica:

```bash
# Ver si la API responde
curl http://localhost:8000/health

# Ver si el frontend responde (desde el navegador)
# Abre: http://localhost:3000
```


## 🔍 RESOLVER PROBLEMAS

### Si la API no arranca:
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# Ver logs de la API para identificar errores
cd /home/migui/master/TFM/aquaia/api
python run.py  # Los errores aparecerán en la consola
```

### Si el frontend no arranca:
```bash
# Limpiar caché de npm y reinstalar
cd /home/migui/master/TFM/aquaia/frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Ver puertos ocupados:
```bash
# Ver qué está usando el puerto 8000
lsof -i :8000

# Ver qué está usando el puerto 3000
lsof -i :3000
```
