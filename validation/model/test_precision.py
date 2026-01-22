"""
Validación de precisión del modelo LSTM.
Evalúa MAE, RMSE, R² en diferentes configuraciones y horizontes.
"""
import json
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tqdm import tqdm
import sys
import time

# Añadir path de la raíz del proyecto
sys.path.append(str(Path(__file__).parent.parent.parent))

from api.services.prediction import PredictionService, LSTMSeq2Seq
from api.data import data_loader

# Configuración
RESULTS_DIR = Path(__file__).parent.parent / "results" / "model"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def evaluate_model_on_test_set():
    """
    Evalúa el modelo en el conjunto de test.
    Reproduce los resultados de la Tabla del LaTeX (Sección 6.2.2).
    """
    print("Iniciando validación de precisión del modelo...")
    
    prediction_service = PredictionService()
    prediction_service.load_model()
    
    print("Cargando datos...")
    data_loader.initialize()
    
    # Embalses de test - verificar que existan en el sistema
    embalses_disponibles = prediction_service.get_available_embalses()
    print(f"Embalses disponibles en el modelo: {len(embalses_disponibles)}")
    
    # Intentar con embalses de test, fallback a disponibles si no existen
    candidatos_test = ["E036", "E035", "E350"]
    test_embalses = [e for e in candidatos_test if e in embalses_disponibles]
    
    if not test_embalses:
        print("WARNING: Los embalses de test no están disponibles, usando embalses del modelo...")
        test_embalses = embalses_disponibles[:3] if len(embalses_disponibles) >= 3 else embalses_disponibles
    
    if not test_embalses:
        print("ERROR: No hay embalses disponibles con scalers. Verifique el modelo.")
        return
    
    print(f"Embalses a evaluar: {test_embalses}")
    
    # Horizontes a evaluar
    horizontes = [7, 30, 90, 180]
    
    results = []
    detailed_results = []
    
    for codigo in tqdm(test_embalses, desc="Evaluando embalses"):
        print(f"\nEmbalse: {codigo}")
        
        # Obtener datos históricos
        try:
            df_historico = data_loader.get_embalse_data(codigo)
            if df_historico.empty:
                print(f"  WARNING: Sin datos para {codigo}")
                continue
            
            # Obtener capacidad del embalse
            embalse_info = data_loader.get_embalse_actual(codigo)
            capacidad = float(getattr(embalse_info, "capacidad_total", 100.0))
            
        except Exception as e:
            print(f"  Error al cargar datos: {str(e)[:80]}")
            import traceback
            if '--debug' in sys.argv:
                traceback.print_exc()
            continue
        
        # Evaluar en múltiples fechas
        fecha_max = df_historico['fecha'].max()
        fecha_min = df_historico['fecha'].min()
        
        # Asegurarnos de que hay suficiente historia
        fecha_inicio_valida = fecha_min + pd.Timedelta(days=prediction_service.lookback)
        fecha_fin_valida = fecha_max - pd.Timedelta(days=max(horizontes))
        
        if fecha_fin_valida <= fecha_inicio_valida:
            print(f"  WARNING: Rango de fechas insuficiente")
            continue
        
        fechas_eval = pd.date_range(
            start=fecha_inicio_valida,
            end=fecha_fin_valida,
            periods=min(3, int((fecha_fin_valida - fecha_inicio_valida).days / 60))
        )
        
        for horizonte in horizontes:
            y_true = []
            y_pred = []
            
            for fecha in fechas_eval:
                try:
                    # Delay para evitar rate limit en consultas a BD
                    time.sleep(0.5)
                    
                    # El servicio actual calcula ambos modos en una sola llamada a predecir_embalse
                    df_pred = prediction_service.predecir_embalse(
                        codigo_saih=codigo,
                        fecha=fecha.strftime("%Y-%m-%d"),
                        horizonte=horizonte
                    )
                    
                    # 'pred' contiene la predicción con el modelo completo (AEMET)
                    pred = np.array(df_pred['pred'].values, dtype=np.float64)
                    
                    # Convertir nivel_real a numérico, eliminando NaN
                    df_real = pd.to_numeric(df_pred['nivel_real'], errors='coerce').values
                    
                    # Filtrar solo datos válidos (sin NaN)
                    mask = ~np.isnan(df_real)
                    if np.sum(mask) >= horizonte * 0.8:  # Al menos 80% de datos válidos
                        df_real_clean = df_real[mask]
                        pred_clean = pred[mask]
                        y_true.extend(df_real_clean)
                        y_pred.extend(pred_clean)
                    
                except Exception as e:
                    print(f"    Error en predicción ({fecha.strftime('%Y-%m-%d')}, h={horizonte}): {str(e)[:100]}")
                    import traceback
                    if '--debug' in sys.argv:
                        traceback.print_exc()
                    continue
            
            if len(y_true) > 0:
                # Calcular métricas
                mae = mean_absolute_error(y_true, y_pred)
                rmse = np.sqrt(mean_squared_error(y_true, y_pred))
                r2 = r2_score(y_true, y_pred)
                error_relativo = (mae / capacidad) * 100
                
                result = {
                    "codigo": codigo,
                    "horizonte": horizonte,
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "r2": float(r2),
                    "capacidad": float(capacidad),
                    "error_relativo_pct": float(error_relativo),
                    "n_predictions": len(y_true)
                }
                
                results.append(result)
                
                print(f"  Horizonte {horizonte:3d} días: MAE={mae:.2f} hm³, RMSE={rmse:.2f} hm³, R²={r2:.3f}, Error Rel={error_relativo:.2f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON completo
    json_path = RESULTS_DIR / f"precision_test_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # DataFrame para análisis
    df_results = pd.DataFrame(results)
    
    # CSV
    csv_path = RESULTS_DIR / f"precision_test_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False)
    
    # Generar tabla LaTeX por embalse
    latex_path = RESULTS_DIR / f"precision_test_{timestamp}_latex.txt"
    with open(latex_path, "w") as f:
        f.write("% Tabla: Resultados detallados por embalse (Horizonte promedio 180 días)\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Rendimiento detallado por embalse en el conjunto de test}\n")
        f.write("\\begin{tabular}{lccccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Código} & \\textbf{MAE (hm$^3$)} & \\textbf{RMSE (hm$^3$)} & \\textbf{$R^2$} & \\textbf{Capacidad (hm$^3$)} & \\textbf{Error Rel (\\%)} \\\\\n")
        f.write("\\midrule\n")
        
        # Agrupar por embalse (promedio de todos los horizontes)
        for codigo in test_embalses:
            embalse_data = df_results[df_results['codigo'] == codigo]
            if not embalse_data.empty:
                mae_mean = embalse_data['mae'].mean()
                rmse_mean = embalse_data['rmse'].mean()
                r2_mean = embalse_data['r2'].mean()
                capacidad = embalse_data['capacidad'].iloc[0]
                error_rel = embalse_data['error_relativo_pct'].mean()
                
                f.write(f"{codigo} & {mae_mean:.2f} & {rmse_mean:.2f} & {r2_mean:.2f} & {capacidad:.0f} & {error_rel:.2f} \\\\\n")
        
        f.write("\\midrule\n")
        f.write(f"\\textbf{{Promedio}} & {df_results['mae'].mean():.2f} & {df_results['rmse'].mean():.2f} & {df_results['r2'].mean():.2f} & {df_results['capacidad'].mean():.1f} & {df_results['error_relativo_pct'].mean():.2f} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
        
        # Tabla por horizonte
        f.write("\n\n% Tabla: Resultados por horizonte temporal\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Rendimiento por horizonte de predicción}\n")
        f.write("\\begin{tabular}{lccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Horizonte (días)} & \\textbf{MAE (hm$^3$)} & \\textbf{RMSE (hm$^3$)} & \\textbf{$R^2$} \\\\\n")
        f.write("\\midrule\n")
        
        for horizonte in horizontes:
            h_data = df_results[df_results['horizonte'] == horizonte]
            if not h_data.empty:
                f.write(f"Día {horizonte} & {h_data['mae'].mean():.2f} & {h_data['rmse'].mean():.2f} & {h_data['r2'].mean():.2f} \\\\\n")
        
        f.write("\\midrule\n")
        f.write(f"\\textbf{{Promedio (0-180)}} & {df_results['mae'].mean():.2f} & {df_results['rmse'].mean():.2f} & {df_results['r2'].mean():.2f} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"\nResultados guardados en:")
    print(f"   - JSON: {json_path}")
    print(f"   - CSV: {csv_path}")
    print(f"   - LaTeX: {latex_path}")
    
    print(f"\nRESUMEN GLOBAL:")
    print(f"   MAE promedio: {df_results['mae'].mean():.2f} hm³")
    print(f"   RMSE promedio: {df_results['rmse'].mean():.2f} hm³")
    print(f"   R² promedio: {df_results['r2'].mean():.3f}")
    print(f"   Error relativo: {df_results['error_relativo_pct'].mean():.2f}%")
    
    return results


if __name__ == "__main__":
    results = evaluate_model_on_test_set()
