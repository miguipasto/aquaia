
import os
import random
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --- CONFIG ---
SEED = 42
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# Lookback/Horizon must match the saved model config
# We will read them from metrics.json later, but for data prep we need them.
# The notebook has them hardcoded, but better to read from config if possible.
# For now, I'll use the values found in metrics.json in previous turn.
LOOKBACK = 360
HORIZON = 180
SIGMA_FORECAST = 0.02
BATCH_SIZE = 32

# Set seeds
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

def load_data():
    # Try multiple paths
    paths = [
        'data/dataset_embalses_aemet.csv',
        '../data/dataset_embalses_aemet.csv',
        'dataset_embalses_aemet.csv'
    ]
    data_path = None
    for p in paths:
        if os.path.exists(p):
            data_path = p
            break
    if not data_path:
        raise FileNotFoundError("dataset_embalses_aemet.csv not found")
        
    print(f"Loading data from {data_path}")
    df = pd.read_csv(data_path)
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['fecha']).sort_values(['codigo_saih', 'fecha'])
    
    # Numeric conversion
    numeric_cols = ['nivel','precipitacion','temperatura','caudal_promedio',
                    'tmed','prec','tmin','tmax','hr_media','velmedia','racha']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Fill AEMET nans
    aemet_cols = ['tmed','prec','tmin','tmax','hr_media','velmedia','racha']
    for col in aemet_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
            
    df = df.dropna(subset=['nivel'])
    
    # Filter stations
    min_len = LOOKBACK + HORIZON + 10
    valid_stations = [e for e, g in df.groupby('codigo_saih') if len(g) >= min_len]
    df = df[df['codigo_saih'].isin(valid_stations)]
    return df

def multistep_windows(df, lookback, horizon, sigma):
    X, y = [], []
    idx_pairs = []
    scalers = {}
    
    base_cols = ['nivel','precipitacion','temperatura','caudal_promedio',
                 'tmed','prec','tmin','tmax','hr_media','velmedia','racha']
    hist_cols = [c for c in base_cols if c in df.columns]
    
    # Needs to match the order in the notebook iteration
    # Notebook: for estacion, g in df.groupby('codigo_saih'):
    # Default groupby sort is True (alphabetical keys)
    
    for estacion, g in df.groupby('codigo_saih'):
        g = g.sort_values('fecha').set_index('fecha')
        if len(g) < lookback + horizon + 1:
            continue
            
        scaler = MinMaxScaler()
        scaled_vals = scaler.fit_transform(g[hist_cols])
        scaled_hist = pd.DataFrame(scaled_vals, index=g.index, columns=hist_cols)
        scalers[estacion] = scaler
        
        # Iteration
        # Notebook: for i in range(lookback, len(scaled_hist) - horizon):
        # We need to ensure the order of X is identical to notebook
        
        n_samples = len(scaled_hist) - horizon - lookback
        if n_samples <= 0: continue
            
        for i in range(lookback, len(scaled_hist) - horizon):
            # Window creation logic (Simplified as we just need X/Y strict reconstruction)
            hist_window = scaled_vals[i-lookback:i]
            
            fut_real = scaled_vals[i:i+horizon]
            noise = np.random.normal(loc=0.0, scale=sigma, size=fut_real.shape)
            fut_forecast = np.clip(fut_real + noise, 0.0, 1.0)
            
            fut_summary = fut_forecast.mean(axis=0)
            fut_tiled = np.tile(fut_summary, (lookback, 1))
            
            x_win = np.hstack([hist_window, fut_tiled])
            X.append(x_win)
            
            # Target is 'nivel' column. Find its index.
            nivel_idx = hist_cols.index('nivel')
            y.append(scaled_vals[i:i+horizon, nivel_idx]) # (horizon,)
            
            idx_pairs.append((estacion, g.index[i])) # timestamp at start of prediction horizon
            
    return np.array(X), np.array(y), idx_pairs, scalers, hist_cols

class LSTMSeq2Seq(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout, horizon):
        super().__init__()
        self.encoder = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc_out = nn.Linear(hidden_size, horizon)
        
    def forward(self, x):
        _, (h_n, _) = self.encoder(x)
        h = self.dropout(h_n[-1])
        out = self.fc_out(h)
        return out

def main():
    # 1. Find Model
    models_dir = 'Models'
    if not os.path.exists(models_dir):
        print("Models dir not found")
        return

    # Assuming model_20260114_193518 based on previous turn
    model_name = 'model_20260114_193518'
    model_path = os.path.join(models_dir, model_name)
    metrics_path = os.path.join(model_path, 'artifacts', 'metrics.json')
    
    print(f"Analyzing {model_name}...")
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
        
    cfg = metrics['config']
    
    # 2. Data Prep
    df = load_data()
    X, Y, idx_pairs, scalers, hist_cols = multistep_windows(df, cfg['LOOKBACK'], cfg['HORIZON'], cfg['SIGMA_FORECAST'])
    
    # 3. Split
    N = len(X)
    split1 = int(0.8 * N)
    split2 = int(0.9 * N)
    
    X_test = X[split2:]
    Y_test = Y[split2:]
    pairs_test = idx_pairs[split2:]
    
    X_test_t = torch.from_numpy(X_test).float().to(DEVICE)
    
    # 4. Load Model
    model = LSTMSeq2Seq(
        input_size=cfg['FEATURES'],
        hidden_size=cfg['HIDDEN_SIZE'],
        num_layers=cfg['NUM_LAYERS'],
        dropout=cfg['DROPOUT'],
        horizon=cfg['HORIZON']
    ).to(DEVICE)
    
    pth_file = os.path.join(model_path, f"{model_name}.pth")
    ckpt = torch.load(pth_file, map_location=DEVICE)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    
    # 5. Predict
    batch_size = 64
    preds = []
    with torch.no_grad():
        for i in range(0, len(X_test_t), batch_size):
            batch = X_test_t[i:i+batch_size]
            out = model(batch)
            preds.append(out.cpu().numpy())
    preds = np.concatenate(preds, axis=0) # (N_test, Horizon)
    
    # 6. Inverse Transform
    real_preds = []
    real_targets = []
    
    nivel_max_capacities = []
    
    print(f"Inverse transforming {len(preds)} samples...")
    for i in range(len(preds)):
        estacion, date = pairs_test[i]
        scaler = scalers[estacion]
        
        # Reconstruct "nivel" inverse
        # Scaler expects (n_features)
        # We only have 'nivel' (prediction).
        # We need to construct a dummy row to use scaler.inverse_transform
        # Or easier: since fit_transform is linear: X_scaled = (X - min) / (max - min)
        # X = X_scaled * (max - min) + min
        # We can extract min/scale for 'nivel' column
        
        nivel_idx = hist_cols.index('nivel')
        d_min = scaler.data_min_[nivel_idx]
        d_max = scaler.data_max_[nivel_idx]
        d_range = scaler.data_range_[nivel_idx]
        
        # Validation checks
        # d_range could be 0?
        
        # Inverse
        p_inv = preds[i] * d_range + d_min
        y_inv = Y_test[i] * d_range + d_min
        
        real_preds.append(p_inv)
        real_targets.append(y_inv)
        nivel_max_capacities.append(d_max) # Approx capacity
        
    real_preds = np.array(real_preds)
    real_targets = np.array(real_targets)
    
    # 7. Calculate Metrics (Physical)
    mae_overall = mean_absolute_error(real_targets, real_preds)
    rmse_overall = np.sqrt(mean_squared_error(real_targets, real_preds))
    r2_overall = r2_score(real_targets, real_preds) # Flat R2?
    
    # By horizon
    mae_h = np.mean(np.abs(real_targets - real_preds), axis=0)
    rmse_h = np.sqrt(np.mean((real_targets - real_preds)**2, axis=0))
    
    print("\n=== PHYSICAL METRICS ===")
    print(f"Overall MAE: {mae_overall:.4f} hm3")
    print(f"Overall RMSE: {rmse_overall:.4f} hm3")
    print(f"Overall R2: {r2_overall:.4f}")
    
    print(f"MAE Day 1: {mae_h[0]:.4f} hm3")
    print(f"MAE Day 30: {mae_h[29]:.4f} hm3")
    print(f"MAE Day 90: {mae_h[89]:.4f} hm3")
    print(f"MAE Day 180: {mae_h[179]:.4f} hm3")
    
    print(f"Avg MAE (First 30 days): {np.mean(mae_h[:30]):.4f} hm3")

    # --- PER STATION METRICS ---
    print("\n=== PER STATION METRICS ===")
    station_metrics = []
    
    # We need to map index i back to station.
    # We already iterated over range(len(preds)) and have `estacion` in the loop.
    # But we didn't store per-station errors.
    # Re-iterate or better, accumulate during loop.
    
    # Let's accumulate errors in a dict
    errors_by_station = {} # {code: {'abs': [], 'sq': [], 'target': [], 'pred': []}}
    
    for i in range(len(preds)):
        estacion, date = pairs_test[i]
        if estacion not in errors_by_station:
            errors_by_station[estacion] = {'abs': [], 'sq': [], 'target': [], 'pred': []}
        
        # We focus on Horizon 180 (average over all days) for ranking?
        # Text says "MAE en horizonte de 180 días".
        # This usually implies average MAE over the 180 days? Or specific day?
        # Usually average over the horizon sequence.
        
        e_abs = np.mean(np.abs(real_targets[i] - real_preds[i]))
        e_sq = np.mean((real_targets[i] - real_preds[i])**2)
        
        errors_by_station[estacion]['abs'].append(e_abs)
        errors_by_station[estacion]['sq'].append(e_sq)
        # R2 per station is tricky if we average first. 
        # Correct R2 per station: 1 - sum(sq_err) / sum((y - mean_y)^2)
        # We need to store all individual points to calc R2 properly.
        # Let's store flattened arrays per station.
        errors_by_station[estacion]['target'].append(real_targets[i])
        errors_by_station[estacion]['pred'].append(real_preds[i])

    results = []
    for code, data in errors_by_station.items():
        # Flatten
        y_true = np.concatenate(data['target'])
        y_pred = np.concatenate(data['pred'])
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        # Estimate Capacity (Max observed in test)
        cap = np.max(y_true)
        
        results.append({
            'code': code,
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'cap': cap
        })
        
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values('mae')
    
    print("TOP 5 BEST:")
    print(df_res.head(5).to_string(index=False))
    
    print("\nTOP 5 WORST:")
    print(df_res.tail(5).to_string(index=False))
    
    # Quantiles
    print("\nQUANTILES (MAE):")
    print(df_res['mae'].describe())
    
    # IQR outliers
    Q1 = df_res['mae'].quantile(0.25)
    Q3 = df_res['mae'].quantile(0.75)
    IQR = Q3 - Q1
    limit = Q3 + 1.5 * IQR
    print(f"IQR Limit: {limit:.4f}")
    outliers = df_res[df_res['mae'] > limit]
    print(f"Outliers count: {len(outliers)}")
    if not outliers.empty:
        print(outliers.to_string(index=False))

if __name__ == "__main__":
    main()
