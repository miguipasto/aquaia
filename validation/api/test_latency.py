"""
Prueba de latencia de los endpoints de la API.
Mide tiempos de respuesta para todos los endpoints críticos.
"""
import time
import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm
import statistics

# Configuración
API_BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 20
REQUEST_DELAY = 0.7
RESULTS_DIR = Path(__file__).parent.parent / "results" / "api"


def measure_endpoint_latency(url: str, method: str = "GET", data: dict = None) -> Dict:
    """Mide la latencia de un endpoint."""
    latencies = []
    errors = 0
    rate_limit_errors = 0
    
    for i in range(NUM_REQUESTS):
        start = time.time()
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            else:
                response = requests.post(url, json=data, timeout=30)
            
            latency = (time.time() - start) * 1000  # ms
            
            if response.status_code == 200:
                latencies.append(latency)
            elif response.status_code == 429:
                rate_limit_errors += 1
                print(f"Rate limit alcanzado, esperando...")
                time.sleep(5)  # Esperar 5 segundos si hay rate limit
            else:
                errors += 1
        except Exception as e:
            errors += 1
            print(f"Error: {e}")
        
        # Delay entre requests para evitar rate limit
        if i < NUM_REQUESTS - 1:
            time.sleep(REQUEST_DELAY)
    
    if not latencies:
        return {
            "error": "No successful requests",
            "errors": errors,
            "rate_limit_errors": rate_limit_errors
        }
    
    # Calcular percentiles de forma segura
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    if n >= 20:
        # Usar quantiles si hay suficientes datos
        quantiles = statistics.quantiles(sorted_latencies, n=20)  # Devuelve 19 valores
        p95 = quantiles[18]  # Índice 18 de 19 es aproximadamente p95
        p99 = sorted_latencies[int(0.99 * n)]  # Calcular p99 directamente
    elif n >= 4:
        quantiles = statistics.quantiles(sorted_latencies, n=4)  # Devuelve 3 valores
        p95 = quantiles[2]  # Aproximación
        p99 = sorted_latencies[-1]  # Máximo
    else:
        p95 = sorted_latencies[-1]
        p99 = sorted_latencies[-1]
    
    return {
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p95": p95,
        "p99": p99,
        "min": min(latencies),
        "max": max(latencies),
        "std": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "success_rate": len(latencies) / NUM_REQUESTS * 100,
        "errors": errors,
        "rate_limit_errors": rate_limit_errors
    }


def test_all_endpoints():
    """Prueba todos los endpoints críticos."""
    print("Iniciando pruebas de latencia de API...")
    print(f"URL Base: {API_BASE_URL}")
    print(f"Número de requests por endpoint: {NUM_REQUESTS}\n")
    
    endpoints = [
        {
            "name": "Health Check",
            "url": f"{API_BASE_URL}/health",
            "method": "GET"
        },
        {
            "name": "Listado Embalses",
            "url": f"{API_BASE_URL}/embalses",
            "method": "GET"
        },
        {
            "name": "Histórico Embalse (E001)",
            "url": f"{API_BASE_URL}/embalses/E001/historico?limit=100",
            "method": "GET"
        },
        {
            "name": "Predicción 7 días",
            "url": f"{API_BASE_URL}/predicciones/E001",
            "method": "POST",
            "data": {"fecha_inicio": "2024-06-01", "horizonte_dias": 7}
        },
        {
            "name": "Predicción 30 días",
            "url": f"{API_BASE_URL}/predicciones/E001",
            "method": "POST",
            "data": {"fecha_inicio": "2024-06-01", "horizonte_dias": 30}
        },
        {
            "name": "Predicción 180 días",
            "url": f"{API_BASE_URL}/predicciones/E001",
            "method": "POST",
            "data": {"fecha_inicio": "2024-06-01", "horizonte_dias": 180}
        },
        {
            "name": "Dashboard KPIs",
            "url": f"{API_BASE_URL}/dashboard/kpis",
            "method": "GET"
        },
        {
            "name": "Recomendación GET",
            "url": f"{API_BASE_URL}/recomendaciones/E001",
            "method": "GET"
        },
        {
            "name": "Recomendación POST",
            "url": f"{API_BASE_URL}/recomendaciones/E001",
            "method": "POST",
            "data": {"fecha_inicio": "2024-06-01", "horizonte_dias": 7}
        }
    ]
    
    results = []
    
    for endpoint in tqdm(endpoints, desc="Testing endpoints"):
        print(f"\nTesting: {endpoint['name']}")
        metrics = measure_endpoint_latency(
            url=endpoint["url"],
            method=endpoint.get("method", "GET"),
            data=endpoint.get("data")
        )
        
        result = {
            "endpoint": endpoint["name"],
            "url": endpoint["url"],
            "method": endpoint.get("method", "GET"),
            **metrics
        }
        results.append(result)
        
        time.sleep(2)
        
        if "error" not in metrics:
            print(f"Mean: {metrics['mean']:.2f}ms | P95: {metrics['p95']:.2f}ms | Success: {metrics['success_rate']:.1f}%")
        else:
            print(f"Error: {metrics['error']}")
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_path = RESULTS_DIR / f"latency_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    df = pd.DataFrame(results)
    csv_path = RESULTS_DIR / f"latency_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    latex_path = RESULTS_DIR / f"latency_{timestamp}_latex.txt"
    with open(latex_path, "w") as f:
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Latencia de endpoints de la API (ms)}\n")
        f.write("\\begin{tabular}{lcccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Endpoint} & \\textbf{Media} & \\textbf{P95} & \\textbf{P99} & \\textbf{Éxito (\\%)} \\\\\n")
        f.write("\\midrule\n")
        
        for result in results:
            if "error" not in result:
                f.write(f"{result['endpoint']} & {result['mean']:.2f} & {result['p95']:.2f} & {result['p99']:.2f} & {result['success_rate']:.1f} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"\nResultados guardados en:")
    print(f"   - JSON: {json_path}")
    print(f"   - CSV: {csv_path}")
    print(f"   - LaTeX: {latex_path}")
    
    return results


if __name__ == "__main__":
    results = test_all_endpoints()
