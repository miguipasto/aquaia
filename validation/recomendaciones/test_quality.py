"""
Validación de calidad de las recomendaciones.
Evalúa coherencia, alineación con datos y calidad del texto generado.
"""
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import re

RESULTS_DIR = Path(__file__).parent.parent / "results" / "recomendaciones"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

API_BASE_URL = "http://localhost:8000"


def validate_recommendation_structure(rec: Dict) -> Dict:
    """Valida la estructura de una recomendación."""
    issues = []
    
    # Verificar campos requeridos
    required_fields = ["nivel_riesgo", "motivo", "accion_recomendada"]
    for field in required_fields:
        if field not in rec:
            issues.append(f"Falta campo requerido: {field}")
    
    # Verificar nivel de riesgo válido
    valid_levels = ["BAJO", "MODERADO", "ALTO", "SEQUIA"]
    if rec.get("nivel_riesgo") not in valid_levels:
        issues.append(f"Nivel de riesgo inválido: {rec.get('nivel_riesgo')}")
    
    # Verificar que motivo no esté vacío
    if not rec.get("motivo") or len(rec.get("motivo", "").strip()) < 10:
        issues.append("Motivo vacío o demasiado corto")
    
    # Verificar que acción no esté vacía
    if not rec.get("accion_recomendada") or len(rec.get("accion_recomendada", "").strip()) < 10:
        issues.append("Acción recomendada vacía o demasiado corta")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


def check_text_quality(text: str) -> Dict:
    """Evalúa la calidad del texto generado."""
    issues = []
    
    # Verificar longitud mínima
    if len(text) < 20:
        issues.append("Texto demasiado corto")
    
    # Verificar si tiene contenido HTML válido (para acciones)
    if "<ul>" in text and "</ul>" not in text:
        issues.append("HTML mal formado: falta cierre </ul>")
    
    if "<li>" in text and text.count("<li>") != text.count("</li>"):
        issues.append("HTML mal formado: desbalance en tags <li>")
    
    # Verificar que no tenga placeholders sin reemplazar
    placeholders = re.findall(r'\{[^}]+\}', text)
    if placeholders:
        issues.append(f"Placeholders sin reemplazar: {placeholders}")
    
    # Verificar que no tenga errores comunes de LLM
    if "como modelo de lenguaje" in text.lower():
        issues.append("Respuesta genérica de LLM detectada")
    
    if "no puedo" in text.lower() or "no dispongo" in text.lower():
        issues.append("LLM indicando incapacidad")
    
    return {
        "quality_score": 1.0 - (len(issues) * 0.2),  # Penalizar por cada issue
        "issues": issues
    }


def validate_data_alignment(rec: Dict, embalse_data: Dict) -> Dict:
    """Verifica que la recomendación esté alineada con los datos del embalse."""
    issues = []
    
    nivel_riesgo = rec.get("nivel_riesgo")
    metricas = rec.get("metricas", {})
    
    # Verificar coherencia entre nivel de riesgo y porcentajes
    porcentaje_actual = metricas.get("porcentaje_actual")
    porcentaje_max = metricas.get("porcentaje_maximo_esperado")
    porcentaje_min = metricas.get("porcentaje_minimo_esperado")
    
    if porcentaje_max is not None and porcentaje_max > 90 and nivel_riesgo != "ALTO":
        issues.append(f"Nivel máximo {porcentaje_max:.1f}% pero riesgo no es ALTO")
    
    if porcentaje_min is not None and porcentaje_min < 30 and nivel_riesgo != "SEQUIA":
        issues.append(f"Nivel mínimo {porcentaje_min:.1f}% pero riesgo no es SEQUÍA")
    
    # Verificar coherencia de tendencia con métricas
    tendencia = rec.get("tendencia")
    if tendencia == "SUBIDA" and porcentaje_max is not None and porcentaje_actual is not None:
        if porcentaje_max < porcentaje_actual:
            issues.append("Tendencia SUBIDA pero máximo esperado es menor que actual")
    
    return {
        "aligned": len(issues) == 0,
        "issues": issues
    }


def test_recommendations_quality():
    """
    Prueba la calidad de las recomendaciones para múltiples embalses.
    
    Este test evalúa:
    1. Estructura: Que el JSON tenga todos los campos requeridos y tipos correctos.
    2. Alineación: Que el riesgo asignado sea coherente con los datos numéricos.
    3. Calidad del texto: Longitud, HTML correcto y ausencia de errores comunes de LLM.
    
    Nota: Se fuerza el uso de IA mediante el parámetro 'esperar_ia=True'.
    """
    print(" Iniciando validación de calidad de recomendaciones (FORZANDO IA)...")
    
    # Obtener lista de embalses
    try:
        response = requests.get(f"{API_BASE_URL}/embalses", timeout=120)
        embalses = response.json()[:3]  # Reducido a 3 por rate limit
    except Exception as e:
        print(f" Error al obtener embalses: {e}")
        return
    
    results = []
    
    for embalse in embalses:
        codigo = embalse["codigo_saih"]
        print(f"\n Evaluando embalse: {codigo}")
        
        try:
            # Delay para evitar saturar el LLM local
            time.sleep(1.0)
            
            # Obtener recomendación FORZANDO IA
            # esperar_ia=True hace que la API no responda hasta que el LLM termine
            response = requests.get(
                f"{API_BASE_URL}/recomendaciones/{codigo}",
                params={
                    "horizonte_dias": 7, 
                    "esperar_ia": True,
                    "forzar_regeneracion": True
                },
                timeout=120  # LLM puede tardar bastante
            )
            
            if response.status_code != 200:
                print(f"    Error HTTP {response.status_code}: {response.text}")
                continue
            
            rec = response.json()
            
            # Validar estructura
            struct_validation = validate_recommendation_structure(rec)
            
            # Validar calidad del texto
            motivo_quality = check_text_quality(rec.get("motivo", ""))
            accion_quality = check_text_quality(rec.get("accion_recomendada", ""))
            
            # Validar alineación con datos
            alignment = validate_data_alignment(rec, embalse)
            
            usa_llm = rec.get("generado_por_llm", False)
            fuente = rec.get("fuente_recomendacion", "desconocida")
            
            result = {
                "codigo": codigo,
                "nivel_riesgo": rec.get("nivel_riesgo"),
                "fuente": fuente,
                "estructura_valida": struct_validation["valid"],
                "estructura_issues": struct_validation["issues"],
                "motivo_quality_score": motivo_quality["quality_score"],
                "motivo_issues": motivo_quality["issues"],
                "accion_quality_score": accion_quality["quality_score"],
                "accion_issues": accion_quality["issues"],
                "datos_alineados": alignment["aligned"],
                "alignment_issues": alignment["issues"],
                "usa_llm": usa_llm,
                "timestamp": rec.get("fecha_generacion")
            }
            
            results.append(result)
            
            # Mostrar resumen
            status = "✓" if all([
                struct_validation["valid"],
                motivo_quality["quality_score"] > 0.7,
                accion_quality["quality_score"] > 0.7,
                alignment["aligned"]
            ]) else "⚠"
            
            llm_tag = "[IA]" if usa_llm else "[PLANTILLA]"
            print(f"  {status} {llm_tag} Riesgo: {rec.get('nivel_riesgo')}, Calidad: {(motivo_quality['quality_score'] + accion_quality['quality_score']) / 2:.2f}")
            
        except requests.exceptions.Timeout:
            print(f"  Error: Timeout esperando respuesta del LLM")
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_path = RESULTS_DIR / f"quality_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Generar informe
    report_path = RESULTS_DIR / f"quality_{timestamp}_report.txt"
    with open(report_path, "w") as f:
        f.write("INFORME DE CALIDAD DE RECOMENDACIONES\n")
        f.write("=" * 60 + "\n\n")
        
        total = len(results)
        estructuras_validas = sum(1 for r in results if r["estructura_valida"])
        datos_alineados = sum(1 for r in results if r["datos_alineados"])
        calidad_alta = sum(1 for r in results if r["motivo_quality_score"] > 0.7 and r["accion_quality_score"] > 0.7)
        uso_llm = sum(1 for r in results if r["usa_llm"])
        
        f.write(f"Total de recomendaciones evaluadas: {total}\n\n")
        
        if total > 0:
            f.write(f"Estructuras válidas: {estructuras_validas}/{total} ({estructuras_validas/total*100:.1f}%)\n")
            f.write(f"Datos alineados: {datos_alineados}/{total} ({datos_alineados/total*100:.1f}%)\n")
            f.write(f"Calidad alta (>0.7): {calidad_alta}/{total} ({calidad_alta/total*100:.1f}%)\n")
            f.write(f"Uso de LLM: {uso_llm}/{total} ({uso_llm/total*100:.1f}%)\n\n")
        else:
            f.write("No se pudieron evaluar recomendaciones.\n\n")
        
        f.write("ISSUES DETECTADOS:\n")
        f.write("-" * 60 + "\n")
        
        for result in results:
            if result["estructura_issues"] or result["motivo_issues"] or result["accion_issues"] or result["alignment_issues"]:
                f.write(f"\nEmbalse {result['codigo']} ({result['nivel_riesgo']}):\n")
                
                if result["estructura_issues"]:
                    f.write(f"  - Estructura: {', '.join(result['estructura_issues'])}\n")
                if result["motivo_issues"]:
                    f.write(f"  - Motivo: {', '.join(result['motivo_issues'])}\n")
                if result["accion_issues"]:
                    f.write(f"  - Acción: {', '.join(result['accion_issues'])}\n")
                if result["alignment_issues"]:
                    f.write(f"  - Alineación: {', '.join(result['alignment_issues'])}\n")
    
    print(f"\nResultados guardados en:")
    print(f"   - JSON: {json_path}")
    print(f"   - Informe: {report_path}")
    
    print(f"\nRESUMEN:")
    print(f"   Recomendaciones evaluadas: {total}")
    if total > 0:
        print(f"   Estructuras validas: {estructuras_validas}/{total} ({estructuras_validas/total*100:.1f}%)")
        print(f"   Calidad alta: {calidad_alta}/{total} ({calidad_alta/total*100:.1f}%)")
    else:
        print("   No se procesaron recomendaciones.")


if __name__ == "__main__":
    test_recommendations_quality()
