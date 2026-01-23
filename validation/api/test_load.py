"""
Prueba de carga de la API usando Locust.
Simula múltiples usuarios concurrentes.
"""
from locust import HttpUser, task, between, events
import json
from datetime import datetime
from pathlib import Path


# Directorio de resultados
RESULTS_DIR = Path(__file__).parent.parent / "results" / "api"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Estadísticas globales
stats = {
    "requests": [],
    "errors": []
}


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Captura estadísticas de cada request."""
    stats["requests"].append({
        "type": request_type,
        "name": name,
        "response_time": response_time,
        "response_length": response_length,
        "timestamp": datetime.now().isoformat(),
        "success": exception is None
    })
    
    if exception:
        stats["errors"].append({
            "type": request_type,
            "name": name,
            "exception": str(exception),
            "timestamp": datetime.now().isoformat()
        })


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Guarda estadísticas al finalizar."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"load_test_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nResultados guardados en: {output_file}")


class AquaIAUser(HttpUser):
    
    wait_time = between(1, 3)
    
    def on_start(self):
        pass
    
    @task(5)
    def get_embalses(self):
        self.client.get("/embalses")
    
    @task(3)
    def get_historico(self):
        self.client.get("/embalses/E001/historico?limit=100")
    
    @task(2)
    def predict_short(self):
        self.client.post(
            "/api/predicciones/E001",
            json={"fecha_inicio": "2024-06-01", "horizonte_dias": 7}
        )
    
    @task(1)
    def predict_medium(self):
        """Predicción a medio plazo (30 días)."""
        self.client.post(
            "/api/predicciones/E001",
            json={"fecha_inicio": "2024-06-01", "horizonte_dias": 30}
        )
    
    @task(2)
    def get_dashboard_kpis(self):
        """Obtiene KPIs del dashboard."""
        self.client.get("/api/dashboard/kpis")
    
    @task(1)
    def get_recomendacion(self):
        """Obtiene recomendación para un embalse."""
        self.client.get("/api/recomendaciones/E001")
    
    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health")


"""
Para ejecutar este test de carga:

1. Iniciar la API:
   cd aquaia/api
   python run.py

2. Ejecutar Locust (en otra terminal):
   
   # Prueba con 10 usuarios concurrentes
   locust -f validation/api/test_load.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --run-time 60s --headless
   
   # Prueba con 50 usuarios concurrentes
   locust -f validation/api/test_load.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 120s --headless
   
   # Prueba con 100 usuarios concurrentes
   locust -f validation/api/test_load.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 180s --headless

3. Los resultados se guardarán automáticamente en validation/results/api/

Parámetros:
- --users: Número de usuarios concurrentes
- --spawn-rate: Usuarios nuevos por segundo
- --run-time: Duración de la prueba
- --headless: Sin interfaz web
"""
