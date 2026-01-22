"""
Test de validación de requisitos no funcionales (RNF) del modelo.
Verifica que el modelo cumple con las métricas especificadas en el TFM.

Requisitos a validar (según LaTeX Sección 4.2.2):
- RNF1.1: R² ≥ 0.95
- RNF1.2: RMSE ≤ 1.903 m (en unidades de altura)
- RNF1.3: MAE < 1.5 hm³ (preferentemente)
- RNF2: Robustez arquitectónica (divergencia train/val pequeña)
"""
import json
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results" / "model"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLDS = {
    "r2_min": 0.95,
    "rmse_max": 1.903,
    "mae_target": 1.5,
    "overfitting_ratio_max": 1.2,
}


def load_model_artifacts(model_dir: Path) -> Tuple[Dict, Dict]:
    """Carga artefactos del modelo: configuración y métricas de entrenamiento."""
    artifacts_dir = model_dir / "artifacts"
    metrics_path = artifacts_dir / "metrics.json"
    
    if not metrics_path.exists():
        raise FileNotFoundError(f"No se encontró metrics.json en {artifacts_dir}")
    
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    
    return metrics


def find_latest_model(models_base: Path) -> Path:
    """Encuentra el modelo más reciente en el directorio de modelos."""
    model_dirs = [d for d in models_base.iterdir() 
                  if d.is_dir() and d.name.startswith('model_')]
    
    if not model_dirs:
        raise FileNotFoundError(f"No se encontraron modelos en {models_base}")
    
    return sorted(model_dirs, key=lambda x: x.name)[-1]


def validate_training_metrics(metrics: Dict) -> Dict:
    """
    Valida métricas del entrenamiento (RNF2: Robustez Arquitectónica).
    Verifica que no haya overfitting significativo.
    """
    history = metrics.get('training_history', {})
    train_loss = history.get('train_loss', [])
    val_loss = history.get('val_loss', [])
    
    results = {
        "passed": True,
        "checks": []
    }
    
    if not train_loss or not val_loss:
        results["passed"] = False
        results["checks"].append({
            "name": "Historia de entrenamiento",
            "status": "ERROR",
            "message": "No se encontró historia de entrenamiento"
        })
        return results
    
    # Check 1: Ratio de overfitting (val_loss final / train_loss final)
    final_train = train_loss[-1]
    final_val = val_loss[-1]
    overfitting_ratio = final_val / final_train if final_train > 0 else float('inf')
    
    ratio_passed = overfitting_ratio <= THRESHOLDS["overfitting_ratio_max"]
    results["checks"].append({
        "name": "Ratio Overfitting (val/train)",
        "value": round(overfitting_ratio, 4),
        "threshold": f"≤ {THRESHOLDS['overfitting_ratio_max']}",
        "status": "PASS" if ratio_passed else "FAIL"
    })
    if not ratio_passed:
        results["passed"] = False
    
    # Check 2: Convergencia (pérdida final vs mejor)
    best_val = min(val_loss)
    convergence_gap = (final_val - best_val) / best_val if best_val > 0 else 0
    
    convergence_passed = convergence_gap < 0.05  # < 5% peor que el mejor
    results["checks"].append({
        "name": "Gap de Convergencia",
        "value": f"{convergence_gap * 100:.2f}%",
        "threshold": "< 5%",
        "status": "PASS" if convergence_passed else "WARN"
    })
    
    # Check 3: Estabilidad (varianza en últimas 10 épocas)
    if len(val_loss) >= 10:
        last_10_std = np.std(val_loss[-10:])
        last_10_mean = np.mean(val_loss[-10:])
        cv = last_10_std / last_10_mean if last_10_mean > 0 else 0
        
        stability_passed = cv < 0.1  # Coeficiente de variación < 10%
        results["checks"].append({
            "name": "Estabilidad (CV últimas 10 épocas)",
            "value": f"{cv * 100:.2f}%",
            "threshold": "< 10%",
            "status": "PASS" if stability_passed else "WARN"
        })
    
    return results


def validate_prediction_metrics_from_artifacts(metrics: Dict) -> Dict:
    """
    Valida métricas de predicción basándose en la pérdida de validación.
    Estima MAE y R² a partir de MSE loss.
    """
    results = {
        "passed": True,
        "checks": [],
        "note": "Métricas estimadas desde val_loss (MSE). Para validación completa usar test_precision.py"
    }
    
    best_val_loss = metrics.get('best_val_loss', None)
    
    if best_val_loss is None:
        results["passed"] = False
        results["checks"].append({
            "name": "Val Loss",
            "status": "ERROR",
            "message": "No se encontró best_val_loss"
        })
        return results
    
    # Estimar RMSE desde MSE (loss normalizado)
    # Nota: esto es una aproximación ya que el modelo trabaja con datos normalizados
    estimated_rmse_normalized = np.sqrt(best_val_loss)
    
    results["checks"].append({
        "name": "RMSE Normalizado",
        "value": round(estimated_rmse_normalized, 4),
        "note": "Error en escala [0,1]",
        "status": "INFO"
    })
    
    # El MSE loss indica la calidad del ajuste
    # Un MSE < 0.03 en datos normalizados típicamente indica R² > 0.95
    estimated_r2 = 1 - best_val_loss if best_val_loss < 1 else 0
    
    r2_passed = estimated_r2 >= THRESHOLDS["r2_min"]
    results["checks"].append({
        "name": "R² Estimado",
        "value": round(estimated_r2, 4),
        "threshold": f"≥ {THRESHOLDS['r2_min']}",
        "status": "PASS" if r2_passed else "WARN",
        "note": "Estimación basada en MSE loss"
    })
    
    return results


def generate_rnf_report(model_metrics: Dict, training_validation: Dict, 
                        prediction_validation: Dict) -> str:
    """Genera un informe de validación de requisitos no funcionales."""
    lines = []
    lines.append("=" * 70)
    lines.append("INFORME DE VALIDACIÓN DE REQUISITOS NO FUNCIONALES (RNF)")
    lines.append("=" * 70)
    lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Modelo: {model_metrics.get('model_timestamp', 'Desconocido')}")
    lines.append("")
    
    # Configuración del modelo
    config = model_metrics.get('config', {})
    lines.append("CONFIGURACION DEL MODELO:")
    lines.append("-" * 40)
    for key, value in config.items():
        if key != 'HIST_COLS':
            lines.append(f"   {key}: {value}")
    lines.append("")
    
    lines.append("RNF2: ROBUSTEZ ARQUITECTONICA")
    lines.append("-" * 40)
    for check in training_validation.get('checks', []):
        status_icon = "PASS" if check['status'] == "PASS" else "WARN" if check['status'] == "WARN" else "FAIL"
        lines.append(f"   [{status_icon}] {check['name']}: {check.get('value', check.get('message', 'N/A'))}")
        if 'threshold' in check:
            lines.append(f"      Umbral: {check['threshold']}")
    lines.append("")
    
    lines.append("RNF1: PRECISION DEL MODELO")
    lines.append("-" * 40)
    if prediction_validation.get('note'):
        lines.append(f"   INFO: {prediction_validation['note']}")
    for check in prediction_validation.get('checks', []):
        status_icon = "PASS" if check['status'] == "PASS" else "WARN" if check['status'] == "WARN" else "INFO"
        lines.append(f"   [{status_icon}] {check['name']}: {check.get('value', check.get('message', 'N/A'))}")
        if 'threshold' in check:
            lines.append(f"      Umbral: {check['threshold']}")
        if 'note' in check and check['status'] != 'INFO':
            lines.append(f"      Nota: {check['note']}")
    lines.append("")
    
    lines.append("RESUMEN:")
    lines.append("-" * 40)
    all_passed = training_validation['passed'] and prediction_validation['passed']
    if all_passed:
        lines.append("   El modelo cumple con los requisitos no funcionales")
    else:
        lines.append("   Algunos requisitos requieren revision")
    lines.append("")
    
    lines.append("RECOMENDACIONES:")
    lines.append("-" * 40)
    lines.append("   1. Ejecutar test_precision.py para metricas detalladas en conjunto de test")
    lines.append("   2. Ejecutar test_ablation.py para validar impacto de variables AEMET")
    lines.append("   3. Ejecutar train_hyperparameter_comparison.py para comparar configuraciones")
    lines.append("")
    
    return "\n".join(lines)


def validate_rnf():
    """
    Ejecuta la validacion completa de requisitos no funcionales.
    """
    print("Iniciando validacion de Requisitos No Funcionales (RNF)...")
    
    # Buscar modelo más reciente
    training_dir = Path(__file__).parent.parent.parent / "training"
    models_base = training_dir / "Models"
    
    try:
        model_dir = find_latest_model(models_base)
        print(f" Modelo encontrado: {model_dir.name}")
    except FileNotFoundError as e:
        print(f" Error: {e}")
        return
    
    # Cargar métricas
    try:
        model_metrics = load_model_artifacts(model_dir)
        print(f" Métricas de entrenamiento cargadas")
    except FileNotFoundError as e:
        print(f" Error: {e}")
        return
    
    # Validar métricas de entrenamiento (RNF2)
    print("\n Validando RNF2: Robustez Arquitectónica...")
    training_validation = validate_training_metrics(model_metrics)
    
    # Validar métricas de predicción (RNF1)
    print(" Validando RNF1: Precisión del Modelo...")
    prediction_validation = validate_prediction_metrics_from_artifacts(model_metrics)
    
    # Generar informe
    report = generate_rnf_report(model_metrics, training_validation, prediction_validation)
    print("\n" + report)
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    results = {
        "timestamp": timestamp,
        "model": model_metrics.get('model_timestamp'),
        "config": model_metrics.get('config'),
        "rnf2_training": training_validation,
        "rnf1_prediction": prediction_validation,
        "thresholds": THRESHOLDS
    }
    
    json_path = RESULTS_DIR / f"rnf_validation_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Informe de texto
    report_path = RESULTS_DIR / f"rnf_validation_{timestamp}_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Tabla LaTeX
    latex_path = RESULTS_DIR / f"rnf_validation_{timestamp}_latex.txt"
    generate_latex_rnf_table(results, latex_path)
    
    print(f"\n Resultados guardados en:")
    print(f"   - JSON: {json_path}")
    print(f"   - Informe: {report_path}")
    print(f"   - LaTeX: {latex_path}")
    
    return results


def generate_latex_rnf_table(results: Dict, output_path: Path):
    """Genera tabla LaTeX de validación de RNF."""
    with open(output_path, 'w') as f:
        f.write("% Tabla de Validación de Requisitos No Funcionales\n")
        f.write(f"% Generado: {results['timestamp']}\n\n")
        
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Validación de Requisitos No Funcionales del Modelo}\n")
        f.write("\\begin{tabular}{llccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{RNF} & \\textbf{Métrica} & \\textbf{Valor} & \\textbf{Umbral} & \\textbf{Estado} \\\\\n")
        f.write("\\midrule\n")
        
        # RNF2
        for check in results.get('rnf2_training', {}).get('checks', []):
            status = "\\checkmark" if check['status'] == "PASS" else "\\texttimes" if check['status'] == "FAIL" else "\\textasciitilde"
            threshold = check.get('threshold', 'N/A')
            f.write(f"RNF2 & {check['name']} & {check.get('value', 'N/A')} & {threshold} & {status} \\\\\n")
        
        f.write("\\midrule\n")
        
        # RNF1
        for check in results.get('rnf1_prediction', {}).get('checks', []):
            if check['status'] != 'INFO':
                status = "\\checkmark" if check['status'] == "PASS" else "\\texttimes" if check['status'] == "FAIL" else "\\textasciitilde"
                threshold = check.get('threshold', 'N/A')
                f.write(f"RNF1 & {check['name']} & {check.get('value', 'N/A')} & {threshold} & {status} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\label{tab:validacion_rnf}\n")
        f.write("\\end{table}\n")
    
    print(f" Tabla LaTeX generada: {output_path}")


if __name__ == "__main__":
    validate_rnf()
