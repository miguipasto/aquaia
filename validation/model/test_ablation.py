"""
Estudio de ablación del modelo.
Evalúa el impacto de las variables AEMET y el ruido en el entrenamiento.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import sys
import time

sys.path.append(str(Path(__file__).parent.parent.parent))

from api.services.prediction import PredictionService
from api.data import data_loader

RESULTS_DIR = Path(__file__).parent.parent / "results" / "model"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def test_ablation_aemet():
    """
    Evalúa el impacto de las variables AEMET.
    Compara predicciones con mode='hist' vs mode='aemet'.
    """
    print("Iniciando estudio de ablación: Impacto de AEMET...")
    
    # Cargar modelo
    prediction_service = PredictionService()
    prediction_service.load_model()
    data_loader.initialize()
    
    # Seleccionar embalses para prueba (verificar que existan en el sistema)
    embalses_disponibles = prediction_service.get_available_embalses()
    embalses_test = [e for e in ["E001", "E003", "E036"] if e in embalses_disponibles][:3]
    
    if not embalses_test:
        print("ERROR: No hay embalses disponibles con scalers. Verifique el modelo.")
        return
    
    print(f"Embalses a evaluar: {embalses_test}")
    horizonte = 90
    
    results = []
    
    for codigo in tqdm(embalses_test, desc="Evaluando configuraciones"):
        print(f"\nEmbalse: {codigo}")
        
        try:
            df_historico = data_loader.get_embalse_data(codigo)
            if df_historico.empty:
                continue
            
            # Seleccionar fechas de evaluación
            fecha_max = df_historico['fecha'].max()
            fecha_min = df_historico['fecha'].min()
            
            # Asegurarnos de que hay suficiente historia antes y después
            fecha_inicio_valida = fecha_min + pd.Timedelta(days=prediction_service.lookback)
            fecha_fin_valida = fecha_max - pd.Timedelta(days=horizonte)
            
            if fecha_fin_valida <= fecha_inicio_valida:
                print(f"  WARNING: Rango de fechas insuficiente para horizonte de {horizonte} días")
                continue
            
            fechas_eval = pd.date_range(
                start=fecha_inicio_valida,
                end=fecha_fin_valida,
                periods=min(3, int((fecha_fin_valida - fecha_inicio_valida).days / 90))
            )
            
            for fecha in fechas_eval:
                try:
                    # Delay entre operaciones
                    time.sleep(0.5)
                    
                    # El servicio actual calcula ambos modos en una sola llamada
                    df_pred = prediction_service.predecir_embalse(
                        codigo_saih=codigo,
                        fecha=fecha.strftime("%Y-%m-%d"),
                        horizonte=horizonte
                    )
                    
                    # Obtener valores reales y predicciones del DataFrame generado
                    # 'pred_hist' es el baseline (solo histórico)
                    # 'pred' es el modelo completo (AEMET con ruido)
                    pred_hist = np.array(df_pred['pred_hist'].values, dtype=np.float64)
                    pred_aemet = np.array(df_pred['pred'].values, dtype=np.float64)
                    
                    # Convertir nivel_real a numérico, eliminando NaN
                    df_real = pd.to_numeric(df_pred['nivel_real'], errors='coerce').values
                    
                    # Filtrar solo datos válidos (sin NaN)
                    mask = ~np.isnan(df_real)
                    if np.sum(mask) < horizonte * 0.8:  # Al menos 80% de datos válidos
                        print(f"    Datos insuficientes: solo {np.sum(mask)}/{horizonte} valores válidos")
                        continue
                    
                    # Aplicar máscara a todos los arrays
                    df_real = df_real[mask]
                    pred_hist = pred_hist[mask]
                    pred_aemet = pred_aemet[mask]
                    
                    if len(df_real) >= horizonte * 0.8:
                        # Calcular errores
                        mae_hist = np.mean(np.abs(df_real - pred_hist))
                        mae_aemet = np.mean(np.abs(df_real - pred_aemet))
                        
                        rmse_hist = np.sqrt(np.mean((df_real - pred_hist) ** 2))
                        rmse_aemet = np.sqrt(np.mean((df_real - pred_aemet) ** 2))
                        
                        # Calcular R²
                        ss_res_hist = np.sum((df_real - pred_hist) ** 2)
                        ss_res_aemet = np.sum((df_real - pred_aemet) ** 2)
                        ss_tot = np.sum((df_real - np.mean(df_real)) ** 2)
                        
                        r2_hist = 1 - (ss_res_hist / ss_tot) if ss_tot > 0 else -999
                        r2_aemet = 1 - (ss_res_aemet / ss_tot) if ss_tot > 0 else -999
                        
                        results.append({
                            "codigo": codigo,
                            "fecha": fecha.strftime("%Y-%m-%d"),
                            "mae_hist": float(mae_hist),
                            "mae_aemet": float(mae_aemet),
                            "rmse_hist": float(rmse_hist),
                            "rmse_aemet": float(rmse_aemet),
                            "r2_hist": float(r2_hist),
                            "r2_aemet": float(r2_aemet),
                            "mejora_mae_pct": float((mae_hist - mae_aemet) / mae_hist * 100),
                            "mejora_rmse_pct": float((rmse_hist - rmse_aemet) / rmse_hist * 100)
                        })
                
                except Exception as e:
                    print(f"    WARNING: Error en prediccion para fecha {fecha.strftime('%Y-%m-%d')}: {str(e)[:100]}")
                    import traceback
                    if '--debug' in sys.argv:
                        traceback.print_exc()
                    continue
        
        except Exception as e:
            print(f"  Error al cargar embalse: {e}")
            continue
    
    if not results:
        print("ERROR: No se pudieron generar resultados")
        return
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_results = pd.DataFrame(results)
    
    # JSON
    json_path = RESULTS_DIR / f"ablation_aemet_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # CSV
    csv_path = RESULTS_DIR / f"ablation_aemet_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False)
    
    # Tabla LaTeX
    latex_path = RESULTS_DIR / f"ablation_aemet_{timestamp}_latex.txt"
    with open(latex_path, "w") as f:
        f.write("% Estudio de ablación: Impacto de variables AEMET\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Impacto de integrar variables meteorológicas AEMET}\n")
        f.write("\\begin{tabular}{lccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Configuración} & \\textbf{MAE (hm$^3$)} & \\textbf{RMSE (hm$^3$)} & \\textbf{$R^2$} \\\\\n")
        f.write("\\midrule\n")
        
        mae_hist_mean = df_results['mae_hist'].mean()
        rmse_hist_mean = df_results['rmse_hist'].mean()
        r2_hist_mean = df_results['r2_hist'].mean()
        
        mae_aemet_mean = df_results['mae_aemet'].mean()
        rmse_aemet_mean = df_results['rmse_aemet'].mean()
        r2_aemet_mean = df_results['r2_aemet'].mean()
        
        mejora_mae = ((mae_hist_mean - mae_aemet_mean) / mae_hist_mean) * 100
        mejora_rmse = ((rmse_hist_mean - rmse_aemet_mean) / rmse_hist_mean) * 100
        
        f.write(f"Sin AEMET (Baseline) & {mae_hist_mean:.2f} & {rmse_hist_mean:.2f} & {r2_hist_mean:.2f} \\\\\n")
        f.write(f"Con AEMET & {mae_aemet_mean:.2f} & {rmse_aemet_mean:.2f} & {r2_aemet_mean:.2f} \\\\\n")
        f.write("\\midrule\n")
        f.write(f"Mejora Absoluta & {mae_hist_mean - mae_aemet_mean:.2f} & {rmse_hist_mean - rmse_aemet_mean:.2f} & {r2_aemet_mean - r2_hist_mean:.2f} \\\\\n")
        f.write(f"Mejora Relativa & \\textbf{{{mejora_mae:.2f}\\%}} & \\textbf{{{mejora_rmse:.2f}\\%}} & --- \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"\nResultados guardados en:")
    print(f"   - JSON: {json_path}")
    print(f"   - CSV: {csv_path}")
    print(f"   - LaTeX: {latex_path}")
    
    print(f"\nRESUMEN:")
    print(f"   MAE sin AEMET: {mae_hist_mean:.2f} hm³")
    print(f"   MAE con AEMET: {mae_aemet_mean:.2f} hm³")
    print(f"   Mejora: {mejora_mae:.2f}%")


if __name__ == "__main__":
    test_ablation_aemet()
