"""
Validación del sistema de generación de informes.
Mide tiempos de generación y valida estructura HTML.
"""
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

RESULTS_DIR = Path(__file__).parent.parent / "results" / "informes"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# URL base con prefijo /api
API_BASE_URL = "http://localhost:8000/api"


def validate_html_structure(html_content: str) -> dict:
    """Valida que el HTML esté bien formado."""
    issues = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Verificar elementos básicos
        if not soup.find('html'):
            issues.append("Falta tag <html>")
        
        if not soup.find('head'):
            issues.append("Falta tag <head>")
        
        if not soup.find('body'):
            issues.append("Falta tag <body>")
        
        # Verificar título
        title = soup.find('title')
        if not title or not title.text.strip():
            issues.append("Falta o está vacío el <title>")
        
        # Verificar que tenga contenido mínimo
        body = soup.find('body')
        if body and len(body.text.strip()) < 100:
            issues.append("Contenido del body demasiado corto")
        
        # Verificar imágenes rotas
        for img in soup.find_all('img'):
            if not img.get('src'):
                issues.append(f"Imagen sin src: {img}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "title": title.text if title else None,
            "body_length": len(body.text) if body else 0
        }
    
    except Exception as e:
        return {
            "valid": False,
            "issues": [f"Error al parsear HTML: {str(e)}"],
            "title": None,
            "body_length": 0
        }


def test_informe_generation():
    """Prueba la generación de informes diarios y semanales."""
    print("Iniciando validación de generación de informes...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/embalses", timeout=10)
        if response.status_code != 200:
            response = requests.get("http://localhost:8000/embalses", timeout=10)
        embalses = response.json()
        if not embalses:
            print("ERROR: No hay embalses disponibles")
            return
        
        embalse = embalses[0]
        codigo_embalse = embalse.get("codigo_saih", embalse.get("codigo", "E001"))
        nombre_embalse = embalse.get("ubicacion", embalse.get("nombre", "Embalse Test"))
    except Exception as e:
        print(f"ERROR: Error al obtener embalses: {e}")
        print("Usando valores por defecto...")
        codigo_embalse = "E001"
        nombre_embalse = "Belesar"
    
    print(f"Embalse de prueba: {codigo_embalse} ({nombre_embalse})\n")
    
    results = []
    
    tipos_informe = ["diario", "semanal"]
    
    for tipo in tipos_informe:
        print(f"Generando informe {tipo}...")
        
        # Delay entre tipos de informe
        time.sleep(2)
        
        # Construir request según el modelo InformeRequest de la API
        # Los nombres de campos deben coincidir con lo que espera la plantilla Jinja2
        request_data = {
            "embalse_id": codigo_embalse,
            "nombre_embalse": nombre_embalse,
            "tipo_informe": tipo,
            "fecha_generacion": datetime.now().isoformat(),
            "usuario": "Test Automatizado",
            "model_version": "v1.0",
            # Datos actuales con nombres de campos correctos para la plantilla
            "datos_actual": {
                "nombre_embalse": nombre_embalse,
                "nivel_actual_msnm": 300.0,
                "porcentaje_capacidad": 75.0,
                "capacidad_total": 400.0,
                "nivel_maximo_msnm": 400.0,
                "media_historica": 70.0,
                "percentil_20": 40.0,
                "percentil_80": 85.0,
                "tendencia": "estable"
            },
            # Predicciones con nombres correctos
            "prediccion": {
                "nivel_30d": 295.0,
                "nivel_90d": 290.0,
                "nivel_180d": 285.0,
                "porcentaje_30d": 73.75,
                "porcentaje_90d": 72.5,
                "porcentaje_180d": 71.25,
                "horizonte_dias": 180,
                "confianza": 0.95
            },
            # Riesgos con estructura correcta
            "riesgos": {
                "categoria_riesgo": "bajo",
                "nivel_riesgo": "bajo",
                "probabilidad_sequia": 0.15,
                "descripcion": "Riesgo bajo de sequía en los próximos 6 meses"
            },
            # Métricas del modelo
            "metricas_modelo": {
                "mae": 1.46,
                "rmse": 2.03,
                "r2": 0.98
            }
        }
        
        # Añadir campos adicionales para informe semanal
        if tipo == "semanal":
            request_data["datos_historicos_semana"] = [
                {"fecha": "2026-01-15", "nivel": 298.5},
                {"fecha": "2026-01-16", "nivel": 299.0},
                {"fecha": "2026-01-17", "nivel": 299.5},
                {"fecha": "2026-01-18", "nivel": 300.0},
                {"fecha": "2026-01-19", "nivel": 300.2},
                {"fecha": "2026-01-20", "nivel": 300.0},
                {"fecha": "2026-01-21", "nivel": 300.0}
            ]
            # Escenarios con la estructura que espera la plantilla
            request_data["escenarios"] = {
                "optimista": {
                    "nivel_180d": 320.0,
                    "probabilidad": 0.25,
                    "descripcion": "Escenario favorable con precipitaciones por encima de la media"
                },
                "neutro": {
                    "nivel_180d": 295.0,
                    "probabilidad": 0.50,
                    "descripcion": "Escenario base con condiciones normales"
                },
                "pesimista": {
                    "nivel_180d": 260.0,
                    "probabilidad": 0.25,
                    "descripcion": "Escenario adverso con sequía prolongada"
                }
            }
            request_data["fecha_inicio_periodo"] = "2026-01-15T00:00:00"
            request_data["fecha_fin_periodo"] = "2026-01-21T00:00:00"
        
        # Probar generación
        print(f"  - Generando...")
        start = time.time()
        try:
            response = requests.post(
                f"{API_BASE_URL}/informes/generar",
                json=request_data,
                timeout=120
            )
            
            tiempo_generacion = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                
                # Obtener el HTML desde la URL de preview
                html_url = data.get("html_url", "")
                informe_id = data.get("informe_id", "")
                
                html_content = ""
                if html_url or informe_id:
                    try:
                        # Intentar obtener el HTML desde el preview
                        preview_url = f"{API_BASE_URL}/informes/preview/{informe_id}"
                        html_response = requests.get(preview_url, timeout=30)
                        if html_response.status_code == 200:
                            html_content = html_response.text
                    except:
                        pass
                
                # Validar HTML
                validation = validate_html_structure(html_content) if html_content else {
                    "valid": False,
                    "issues": ["No se pudo obtener el contenido HTML"],
                    "title": None,
                    "body_length": 0
                }
                
                result = {
                    "tipo": tipo,
                    "tiempo_segundos": tiempo_generacion,
                    "tamano_bytes": len(html_content),
                    "html_valido": validation["valid"],
                    "html_issues": validation["issues"],
                    "title": validation["title"],
                    "contenido_length": validation["body_length"],
                    "informe_id": informe_id,
                    "success": True
                }
                
                results.append(result)
                
                print(f"     Tiempo: {tiempo_generacion:.2f}s, Tamaño: {len(html_content)} bytes, "
                      f"Válido: {validation['valid']}, ID: {informe_id}")
            else:
                print(f"     Error HTTP {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"      Detalle: {error_detail}")
                except:
                    print(f"      Respuesta: {response.text[:200]}")
                
                results.append({
                    "tipo": tipo,
                    "tiempo_segundos": tiempo_generacion,
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
        
        except requests.exceptions.Timeout:
            print(f"     Timeout después de 120s")
            results.append({
                "tipo": tipo,
                "success": False,
                "error": "Timeout"
            })
        except Exception as e:
            print(f"     Error: {e}")
            results.append({
                "tipo": tipo,
                "success": False,
                "error": str(e)
            })
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_path = RESULTS_DIR / f"generation_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Generar tabla LaTeX
    latex_path = RESULTS_DIR / f"generation_{timestamp}_latex.txt"
    with open(latex_path, "w") as f:
        f.write("% Tiempos de generación de informes\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Tiempos de generación de informes}\n")
        f.write("\\begin{tabular}{lccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Tipo Informe} & \\textbf{Tiempo (s)} & \\textbf{Tamaño (KB)} & \\textbf{HTML Válido} \\\\\n")
        f.write("\\midrule\n")
        
        for result in results:
            if result.get("success", False):
                valido_str = "Sí" if result.get("html_valido", False) else "No"
                tamano_kb = result.get("tamano_bytes", 0) / 1024
                f.write(f"{result['tipo'].capitalize()} & {result['tiempo_segundos']:.2f} & {tamano_kb:.1f} & {valido_str} \\\\\n")
            else:
                f.write(f"{result['tipo'].capitalize()} & --- & --- & Error: {result.get('error', 'Desconocido')} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"\nResultados guardados en:")
    print(f"   - JSON: {json_path}")
    print(f"   - LaTeX: {latex_path}")
    
    if results:
        tiempos_exitosos = [r["tiempo_segundos"] for r in results if r.get("success", False)]
        
        print(f"\nRESUMEN:")
        print(f"   Total intentos: {len(results)}")
        print(f"   Exitosos: {len(tiempos_exitosos)}")
        if tiempos_exitosos:
            print(f"   Tiempo promedio: {sum(tiempos_exitosos)/len(tiempos_exitosos):.2f}s")


if __name__ == "__main__":
    test_informe_generation()
