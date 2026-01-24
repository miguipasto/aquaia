"""
Generación de gráficas profesionales para el TFM.
Basado en los resultados reales de validación del modelo.

Genera:
1. Evolución del MAE y RMSE vs. horizonte temporal con bandas de error
2. Comparativa del MAE y error relativo por embalse
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import seaborn as sns

# Configuración de estilo profesional para documentos oficiales
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("deep")

# Paleta de colores profesionales y distinguibles para estudio oficial
# Colores sobrios pero con buena visibilidad y contraste
COLORS = {
    'primary': '#1f77b4',      # Azul profesional (MAE)
    'secondary': '#2ca02c',    # Verde sobrio (RMSE)
    'accent': '#ff7f0e',       # Naranja suave (error relativo)
    'light': '#9467bd',        # Púrpura claro
    'success': '#2ca02c',      # Verde 
    'warning': '#ff7f0e',      # Naranja
    'danger': '#d62728',       # Rojo discreto
    'gray': '#7f7f7f',         # Gris medio
    'dark': '#17305c'          # Azul muy oscuro
}

# Directorio de resultados
RESULTS_DIR = Path(__file__).parent / "results" / "model"
OUTPUT_DIR = Path(__file__).parent / "figuras"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_validation_data():
    """Carga los datos de validación más recientes."""
    # Buscar el archivo JSON más reciente
    json_files = list(RESULTS_DIR.glob("precision_test_*.json"))
    if not json_files:
        raise FileNotFoundError("No se encontraron archivos de validación en results/model/")
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"Cargando datos de: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return pd.DataFrame(data)


def plot_mae_rmse_vs_horizon(df, output_path):
    """
    Gráfica 1: Evolución del MAE y RMSE vs. horizonte temporal.
    
    Incluye:
    - Líneas con marcadores para MAE y RMSE
    - Bandas de error (desviación estándar entre embalses)
    - Umbrales de utilidad operativa
    - Anotaciones explicativas
    """
    # Agrupar por horizonte
    grouped = df.groupby('horizonte').agg({
        'mae': ['mean', 'std'],
        'rmse': ['mean', 'std'],
        'r2': 'mean'
    }).reset_index()
    
    # Extraer valores
    horizontes = grouped['horizonte'].values
    mae_mean = grouped['mae']['mean'].values
    mae_std = grouped['mae']['std'].values
    rmse_mean = grouped['rmse']['mean'].values
    rmse_std = grouped['rmse']['std'].values
    
    # Crear figura
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Eje principal (MAE y RMSE)
    # MAE
    line_mae = ax1.plot(horizontes, mae_mean, 
                        marker='o', markersize=9, linewidth=2.8,
                        color=COLORS['primary'], label='MAE', 
                        linestyle='-', markerfacecolor='white', 
                        markeredgewidth=2.5, markeredgecolor=COLORS['primary'],
                        zorder=3)
    
    # Banda de error MAE
    ax1.fill_between(horizontes, 
                     mae_mean - mae_std, 
                     mae_mean + mae_std,
                     alpha=0.25, color=COLORS['primary'], zorder=1)
    
    # RMSE
    line_rmse = ax1.plot(horizontes, rmse_mean, 
                         marker='s', markersize=9, linewidth=2.8,
                         color=COLORS['secondary'], label='RMSE',
                         linestyle='--', markerfacecolor='white',
                         markeredgewidth=2.5, markeredgecolor=COLORS['secondary'],
                         zorder=3)
    
    # Banda de error RMSE
    ax1.fill_between(horizontes, 
                     rmse_mean - rmse_std, 
                     rmse_mean + rmse_std,
                     alpha=0.25, color=COLORS['secondary'], zorder=1)
    
    # Configuración eje principal
    ax1.set_xlabel('Horizonte de Predicción (días)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Error (hm³)', fontsize=13, fontweight='bold')
    ax1.tick_params(axis='both', labelsize=11)
    ax1.grid(True, alpha=0.3, linestyle=':', linewidth=0.8)
    
    # Umbrales de utilidad operativa
    # Umbral de precisión aceptable (basado en requisitos)
    umbral_corto = 1.5  # Para horizontes cortos (< 30 días)
    umbral_medio = 2.5  # Para horizontes medios (30-90 días)
    umbral_largo = 4.0  # Para horizontes largos (> 90 días)
    
    # Líneas de umbral con colores distinguibles
    ax1.axhline(y=umbral_corto, color=COLORS['success'], 
                linestyle=':', linewidth=1.5, alpha=0.7, zorder=2)
    ax1.axhline(y=umbral_medio, color=COLORS['warning'], 
                linestyle=':', linewidth=1.5, alpha=0.7, zorder=2)
    ax1.axhline(y=umbral_largo, color=COLORS['danger'], 
                linestyle=':', linewidth=1.5, alpha=0.7, zorder=2)
    
    # Anotaciones de umbrales con colores
    ax1.text(185, umbral_corto + 0.1, 'Umbral corto plazo', 
             fontsize=8.5, color=COLORS['success'], 
             ha='right', va='bottom', style='italic', fontweight='bold')
    ax1.text(185, umbral_medio + 0.1, 'Umbral medio plazo', 
             fontsize=8.5, color=COLORS['warning'], 
             ha='right', va='bottom', style='italic', fontweight='bold')
    ax1.text(185, umbral_largo + 0.1, 'Umbral largo plazo', 
             fontsize=8.5, color=COLORS['danger'], 
             ha='right', va='bottom', style='italic', fontweight='bold')
    
    # Áreas de clasificación con colores sutiles
    ax1.axvspan(0, 30, alpha=0.08, color=COLORS['success'], label='Corto plazo', zorder=0)
    ax1.axvspan(30, 90, alpha=0.08, color=COLORS['warning'], label='Medio plazo', zorder=0)
    ax1.axvspan(90, 180, alpha=0.08, color=COLORS['danger'], label='Largo plazo', zorder=0)
    
    # Anotaciones con valores específicos
    for i, (h, mae, rmse) in enumerate(zip(horizontes, mae_mean, rmse_mean)):
        # Anotación MAE
        ax1.annotate(f'{mae:.2f}', 
                     xy=(h, mae), 
                     xytext=(0, 12),
                     textcoords='offset points',
                     fontsize=9.5, 
                     ha='center',
                     bbox=dict(boxstyle='round,pad=0.35', 
                              facecolor=COLORS['primary'], 
                              edgecolor='white', 
                              alpha=0.95, linewidth=1.5),
                     color='white',
                     fontweight='bold',
                     zorder=5)
        
        # Anotación RMSE
        ax1.annotate(f'{rmse:.2f}', 
                     xy=(h, rmse), 
                     xytext=(0, -16),
                     textcoords='offset points',
                     fontsize=9.5, 
                     ha='center',
                     bbox=dict(boxstyle='round,pad=0.35', 
                              facecolor=COLORS['secondary'], 
                              edgecolor='white', 
                              alpha=0.95, linewidth=1.5),
                     color='white',
                     fontweight='bold',
                     zorder=5)
    
    # Título y leyenda
    plt.title('Evolución del Error de Predicción según Horizonte Temporal\n' +
              'Modelo LSTM Seq2Seq - Embalses de Test',
              fontsize=14, fontweight='bold', pad=20)
    
    # Leyenda combinada
    lines1, labels1 = ax1.get_legend_handles_labels()
    ax1.legend(lines1, labels1, 
              loc='upper left', 
              fontsize=10, 
              frameon=True, 
              fancybox=True, 
              shadow=True,
              ncol=2)
    
    # Ajustar límites
    ax1.set_xlim(-5, 185)
    ax1.set_ylim(0, max(rmse_mean + rmse_std) * 1.15)
    
    # Información adicional
    info_text = (f'n = {df.shape[0]} predicciones | '
                 f'{len(df["codigo"].unique())} embalses de test')
    fig.text(0.99, 0.01, info_text, 
             ha='right', va='bottom', 
             fontsize=8, style='italic', 
             color=COLORS['gray'])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f" Gráfica guardada: {output_path}")
    plt.close()


def plot_mae_by_reservoir(df, output_path):
    """
    Gráfica 2: Comparativa del MAE y error relativo por embalse.
    
    Incluye:
    - Barras agrupadas por embalse (MAE)
    - Línea superpuesta con error relativo (%)
    - Línea horizontal con promedio
    - Anotaciones con capacidad del embalse
    """
    # Agrupar por embalse (promedio de todos los horizontes)
    embalse_stats = df.groupby('codigo').agg({
        'mae': 'mean',
        'rmse': 'mean',
        'error_relativo_pct': 'mean',
        'capacidad': 'first',
        'r2': 'mean'
    }).reset_index()
    
    # Ordenar por MAE
    embalse_stats = embalse_stats.sort_values('mae')
    
    # Crear figura con dos ejes Y
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Posiciones de las barras
    x_pos = np.arange(len(embalse_stats))
    width = 0.6
    
    # Eje primario: MAE con colores
    bars = ax1.bar(x_pos, embalse_stats['mae'], 
                   width=width,
                   color=COLORS['primary'], 
                   alpha=0.85,
                   edgecolor=COLORS['dark'],
                   linewidth=2,
                   label='MAE promedio',
                   zorder=2)
    
    # Añadir gradiente de color para mejor visualización
    for i, bar in enumerate(bars):
        # Gradiente de azul según el MAE
        intensity = embalse_stats['mae'].iloc[i] / embalse_stats['mae'].max()
        bar.set_facecolor(plt.cm.Blues(0.4 + 0.5 * intensity))
    
    ax1.set_xlabel('Embalse (Código SAIH)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('MAE promedio (hm³)', fontsize=13, fontweight='bold', 
                   color=COLORS['dark'])
    ax1.tick_params(axis='y', labelcolor=COLORS['dark'], labelsize=11)
    ax1.tick_params(axis='x', labelsize=11)
    
    # Línea horizontal con promedio MAE
    mae_promedio = embalse_stats['mae'].mean()
    ax1.axhline(y=mae_promedio, 
                color=COLORS['danger'], 
                linestyle='--', 
                linewidth=2.5, 
                label=f'Promedio global: {mae_promedio:.2f} hm³',
                alpha=0.8,
                zorder=3)
    
    # Eje secundario: Error relativo (%)
    ax2 = ax1.twinx()
    line = ax2.plot(x_pos, embalse_stats['error_relativo_pct'], 
                    marker='D', markersize=10, 
                    color=COLORS['accent'], 
                    linewidth=2.5,
                    linestyle='-',
                    markerfacecolor='white',
                    markeredgewidth=2,
                    markeredgecolor=COLORS['accent'],
                    label='Error relativo',
                    zorder=10)
    
    ax2.set_ylabel('Error Relativo (%)', fontsize=13, fontweight='bold', 
                   color=COLORS['accent'])
    ax2.tick_params(axis='y', labelcolor=COLORS['accent'], labelsize=11)
    
    # Etiquetas en el eje X
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(embalse_stats['codigo'], fontsize=12, fontweight='bold')
    
    # Grid
    ax1.grid(True, axis='y', alpha=0.3, linestyle=':', linewidth=0.8)
    ax1.set_axisbelow(True)
    
    # Anotaciones: Valores de MAE sobre las barras
    for i, (idx, row) in enumerate(embalse_stats.iterrows()):
        # MAE sobre la barra
        ax1.text(i, row['mae'] + 0.1, 
                 f"{row['mae']:.2f}", 
                 ha='center', va='bottom',
                 fontsize=10, fontweight='bold',
                 color=COLORS['dark'])
        
        # Capacidad del embalse (debajo de la barra)
        ax1.text(i, -0.3, 
                 f"Cap: {row['capacidad']:.0f} hm³", 
                 ha='center', va='top',
                 fontsize=8, style='italic',
                 color=COLORS['gray'])
        
        # Error relativo en los puntos de la línea
        ax2.text(i, row['error_relativo_pct'] + 0.02, 
                 f"{row['error_relativo_pct']:.1f}%", 
                 ha='center', va='bottom',
                 fontsize=9.5,
                 bbox=dict(boxstyle='round,pad=0.35', 
                          facecolor=COLORS['accent'], 
                          edgecolor='white', 
                          alpha=0.95, linewidth=1.5),
                 color='white',
                 fontweight='bold',
                 zorder=11)
    
    # Título
    plt.title('Comparativa de Rendimiento por Embalse\n' +
              'MAE y Error Relativo (Promedio todos los horizontes)',
              fontsize=14, fontweight='bold', pad=20)
    
    # Leyendas combinadas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, 
              loc='upper left', 
              fontsize=10, 
              frameon=True, 
              fancybox=True, 
              shadow=True)
    
    # Ajustar límites
    ax1.set_ylim(0, embalse_stats['mae'].max() * 1.3)
    ax2.set_ylim(0, embalse_stats['error_relativo_pct'].max() * 1.3)
    
    # Información adicional
    info_text = (f'Análisis basado en {len(df)} predicciones | '
                 f'{len(df["horizonte"].unique())} horizontes temporales')
    fig.text(0.99, 0.01, info_text, 
             ha='right', va='bottom', 
             fontsize=8, style='italic', 
             color=COLORS['gray'])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✓ Gráfica guardada: {output_path}")
    plt.close()


def generate_additional_metrics_table(df):
    """Genera tabla resumen de métricas para el LaTeX."""
    output_file = OUTPUT_DIR / "metricas_resumen.txt"
    
    with open(output_file, 'w') as f:
        f.write("% Tabla resumen de métricas por horizonte\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Resumen de métricas de validación por horizonte temporal}\n")
        f.write("\\label{tab:metricas_horizonte}\n")
        f.write("\\begin{tabular}{lcccc}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Horizonte} & \\textbf{MAE (hm$^3$)} & \\textbf{RMSE (hm$^3$)} & \\textbf{$R^2$} & \\textbf{Error Rel (\\%)} \\\\\n")
        f.write("\\midrule\n")
        
        for h in sorted(df['horizonte'].unique()):
            h_data = df[df['horizonte'] == h]
            f.write(f"{h} días & "
                   f"{h_data['mae'].mean():.2f} $\\pm$ {h_data['mae'].std():.2f} & "
                   f"{h_data['rmse'].mean():.2f} $\\pm$ {h_data['rmse'].std():.2f} & "
                   f"{h_data['r2'].mean():.3f} & "
                   f"{h_data['error_relativo_pct'].mean():.2f} \\\\\n")
        
        f.write("\\midrule\n")
        f.write(f"\\textbf{{Promedio}} & "
               f"{df['mae'].mean():.2f} & "
               f"{df['rmse'].mean():.2f} & "
               f"{df['r2'].mean():.3f} & "
               f"{df['error_relativo_pct'].mean():.2f} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"✓ Tabla LaTeX generada: {output_file}")


def main():
    """Función principal que genera todas las gráficas."""
    print("=" * 70)
    print("GENERACIÓN DE GRÁFICAS PARA EL TFM")
    print("=" * 70)
    print()
    
    # Cargar datos
    print(" Cargando datos de validación...")
    df = load_validation_data()
    print(f"   {len(df)} registros cargados")
    print(f"   Embalses: {df['codigo'].unique().tolist()}")
    print(f"   Horizontes: {sorted(df['horizonte'].unique())}")
    print()
    
    # Gráfica 1: MAE/RMSE vs Horizonte
    print(" Generando Gráfica 1: MAE y RMSE vs Horizonte...")
    output_1 = OUTPUT_DIR / "mae_rmse_vs_horizonte.png"
    plot_mae_rmse_vs_horizon(df, output_1)
    print()
    
    # Gráfica 2: Comparativa por Embalse
    print(" Generando Gráfica 2: Comparativa por Embalse...")
    output_2 = OUTPUT_DIR / "mae_error_por_embalse.png"
    plot_mae_by_reservoir(df, output_2)
    print()
    
    # Tabla resumen
    print(" Generando tabla resumen de métricas...")
    generate_additional_metrics_table(df)
    print()
    
    print("=" * 70)
    print(" GENERACIÓN COMPLETADA")
    print("=" * 70)
    print(f"\nArchivos generados en: {OUTPUT_DIR}")
    print("   - mae_rmse_vs_horizonte.png")
    print("   - mae_error_por_embalse.png")
    print("   - metricas_resumen.txt (tabla LaTeX)")
    print()
    print("Puedes incluir las imágenes en tu LaTeX con:")
    print("   \\includegraphics[width=\\textwidth]{figuras/mae_rmse_vs_horizonte.png}")
    print("   \\includegraphics[width=\\textwidth]{figuras/mae_error_por_embalse.png}")


if __name__ == "__main__":
    main()
