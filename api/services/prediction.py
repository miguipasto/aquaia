"""
Servicio de predicción de niveles de embalses usando modelo LSTM Seq2Seq.
"""
import numpy as np
import pandas as pd
import torch
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sklearn.preprocessing import MinMaxScaler

from ..config import settings
from ..data import data_loader


class LSTMSeq2Seq(torch.nn.Module):
    """Modelo LSTM Seq2Seq para predicción de series temporales."""
    
    def __init__(
        self, 
        input_size: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
        horizon: int
    ):
        super().__init__()
        self.encoder = torch.nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers, 
            batch_first=True, 
            dropout=dropout
        )
        self.dropout = torch.nn.Dropout(dropout)
        self.fc_out = torch.nn.Linear(hidden_size, horizon)
    
    def forward(self, x):
        _, (h_n, _) = self.encoder(x)
        h = self.dropout(h_n[-1])
        out = self.fc_out(h)
        return out


class PredictionService:
    """Servicio de predicción de embalses."""
    
    def __init__(self):
        """Inicializa el servicio de predicción."""
        self.model: Optional[LSTMSeq2Seq] = None
        self.scalers: Optional[Dict] = None
        self.config: Dict = {}
        self.hist_cols: List[str] = []
        self.lookback: int = 90
        self.horizon: int = 180
        self.sigma_forecast: float = 0.05
        self.features: int = 22
        
    def load_model(self):
        """Carga el modelo y los scalers desde disco."""
        if self.model is not None:
            return
        
        ckpt = torch.load(settings.model_path_absolute, map_location='cpu', weights_only=False)
        self.config = ckpt.get('config', {})
        
        self.lookback = self.config.get('LOOKBACK', settings.model_lookback)
        self.horizon = self.config.get('HORIZON', settings.model_horizon)
        hidden_size = self.config.get('HIDDEN_SIZE', settings.model_hidden_size)
        num_layers = self.config.get('NUM_LAYERS', settings.model_num_layers)
        dropout = self.config.get('DROPOUT', settings.model_dropout)
        self.features = self.config.get('FEATURES', settings.model_features)
        self.hist_cols = self.config.get('HIST_COLS', ['nivel', 'precipitacion', 'temperatura', 'caudal_promedio'])
        self.sigma_forecast = self.config.get('SIGMA_FORECAST', settings.model_sigma_forecast)
        
        # Crear modelo
        self.model = LSTMSeq2Seq(
            input_size=self.features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            horizon=self.horizon
        )
        
        # Cargar pesos
        self.model.load_state_dict(ckpt['model_state_dict'])
        self.model.eval()
        self.model.cpu()
        
        self.scalers = np.load(settings.scalers_path_absolute, allow_pickle=True).item()
    
    def _build_window(
        self,
        df_est: pd.DataFrame,
        fecha_dt: datetime,
        scaler: MinMaxScaler,
        mode: str,
        horizonte: int
    ) -> torch.Tensor:
        """
        Construye ventana de entrada para inferencia según el modo.
        
        Args:
            df_est: DataFrame de una estación
            fecha_dt: fecha inicial de predicción
            scaler: scaler de la estación
            mode: 'hist' o 'aemet_ruido'
            horizonte: días a predecir
        
        Returns:
            Tensor (1, LOOKBACK, FEATURES)
        """
        # Obtener datos históricos (LOOKBACK días antes de fecha_dt)
        df_hist = df_est[df_est['fecha'] <= fecha_dt].tail(self.lookback).copy()
        
        if len(df_hist) < self.lookback:
            raise ValueError(
                f'No hay suficientes datos previos a {fecha_dt.strftime("%Y-%m-%d")}. '
                f'Se requieren {self.lookback} días, solo hay {len(df_hist)}'
            )
        
        # Asegurar columnas y rellenar NaN con 0
        for c in self.hist_cols:
            if c not in df_hist.columns:
                df_hist[c] = 0.0
            else:
                df_hist[c] = df_hist[c].fillna(0.0)
        
        # Normalizar datos históricos
        hist_vals = scaler.transform(df_hist[self.hist_cols])  # (lookback, n_feat)
        
        # Obtener datos futuros observados
        df_fut = df_est[df_est['fecha'] > fecha_dt].sort_values('fecha').head(horizonte).copy()
        
        # Construir resumen futuro según modo
        if mode == 'hist':
            # Solo histórico: features futuras = 0
            fut_summary = np.zeros(len(self.hist_cols))
        
        elif mode == 'aemet_ruido':
            if len(df_fut) >= horizonte:
                # Asegurar columnas y rellenar NaN con 0
                for c in self.hist_cols:
                    if c not in df_fut.columns:
                        df_fut[c] = 0.0
                    else:
                        df_fut[c] = df_fut[c].fillna(0.0)
                
                # Normalizar datos futuros
                fut_vals = scaler.transform(df_fut[self.hist_cols])
                
                # Añadir ruido gaussiano
                noise = np.random.normal(0.0, self.sigma_forecast, size=fut_vals.shape)
                fut_summary = np.clip(fut_vals + noise, 0.0, 1.0).mean(axis=0)
            else:
                # No hay suficientes datos futuros, usar ceros
                fut_summary = np.zeros(len(self.hist_cols))
        else:
            raise ValueError(f"Modo no soportado: {mode}. Use 'hist' o 'aemet_ruido'")
        
        # Replicar resumen futuro para toda la ventana histórica
        fut_tiled = np.tile(fut_summary, (self.lookback, 1))
        
        # Concatenar histórico + futuro
        x_win = np.hstack([hist_vals, fut_tiled])
        
        # Convertir a tensor
        return torch.from_numpy(x_win).float().unsqueeze(0)  # (1, lookback, FEATURES)
    
    def predecir_embalse(
        self,
        codigo_saih: str,
        fecha: str,
        horizonte: int = 30
    ) -> pd.DataFrame:
        """
        Predice nivel de embalse en 3 escenarios y compara con real.
        
        Args:
            codigo_saih: código de la estación
            fecha: fecha inicial de predicción (YYYY-MM-DD)
            horizonte: días a predecir (default: 30)
        
        Returns:
            DataFrame con columnas: fecha, pred_hist, pred, nivel_real
        
        Raises:
            ValueError: Si el embalse no existe o no tiene scaler
        """
        # Validar que el modelo esté cargado
        if self.model is None:
            raise RuntimeError("Modelo no cargado. Llame a load_model() primero.")
        
        # Validar que el embalse tenga scaler
        if codigo_saih not in self.scalers:
            raise ValueError(f'No hay scaler para el embalse {codigo_saih}')
        
        # Obtener datos del embalse
        df_est = data_loader.get_embalse_data(codigo_saih)
        scaler = self.scalers[codigo_saih]
        fecha_dt = pd.to_datetime(fecha)
        
        # Validar que la fecha tenga suficiente historial
        min_fecha_valida = df_est['fecha'].min() + timedelta(days=self.lookback)
        if fecha_dt < min_fecha_valida:
            raise ValueError(
                f'Fecha {fecha} es demasiado temprana. '
                f'Primera fecha válida: {min_fecha_valida.strftime("%Y-%m-%d")}'
            )
        
        # Construir ventanas para cada modo y ejecutar inferencia
        preds = {}
        
        for mode_name in ['hist', 'aemet_ruido']:
            # Construir ventana
            x = self._build_window(df_est, fecha_dt, scaler, mode_name, horizonte)
            
            # Inferencia
            with torch.no_grad():
                pred_scaled = self.model(x).cpu().numpy().flatten()[:horizonte]
                
                # Invertir normalización solo para 'nivel'
                nivel_idx = self.hist_cols.index('nivel')
                dummy = np.zeros((len(pred_scaled), len(self.hist_cols)))
                dummy[:, nivel_idx] = pred_scaled
                preds[mode_name] = scaler.inverse_transform(dummy)[:, nivel_idx]
        
        # Construir DataFrame resultado
        fechas_pred = [fecha_dt + timedelta(days=i+1) for i in range(horizonte)]
        
        # Obtener niveles reales observados
        df_real = df_est[
            (df_est['fecha'] > fecha_dt) & 
            (df_est['fecha'] <= fecha_dt + timedelta(days=horizonte))
        ][['fecha', 'nivel']]
        
        # Construir DataFrame de salida
        out = pd.DataFrame({
            'fecha': fechas_pred,
            'pred_hist': preds['hist'],
            'pred': preds['aemet_ruido']
        })
        
        # Hacer merge con datos reales
        out = out.merge(df_real, on='fecha', how='left').rename(columns={'nivel': 'nivel_real'})
        
        return out
    
    def get_available_embalses(self) -> List[str]:
        """
        Obtiene la lista de códigos de embalses con scaler disponible.
        
        Returns:
            Lista de códigos SAIH
        """
        if self.scalers is None:
            return []
        return sorted(self.scalers.keys())
    
    def embalse_disponible(self, codigo_saih: str) -> bool:
        """
        Verifica si un embalse está disponible para predicción.
        
        Args:
            codigo_saih: Código del embalse
            
        Returns:
            True si tiene scaler, False si no
        """
        if self.scalers is None:
            return False
        return codigo_saih in self.scalers


# Instancia global del servicio de predicción (singleton)
prediction_service = PredictionService()
