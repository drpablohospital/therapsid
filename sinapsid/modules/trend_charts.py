#!/usr/bin/env python3
"""
Generador de gráficas de tendencias clínicas usando matplotlib.
Guarda imágenes PNG en /tmp/ para ser servidas por Flask.
"""

import matplotlib
matplotlib.use('Agg')  # Backend no-interactivo
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io
import base64


def generate_trend_chart(evoluciones, parametros, titulo="Tendencias Clínicas", theme='dark'):
    """
    Genera una gráfica de tendencias para múltiples parámetros.
    
    Args:
        evoluciones: Lista de diccionarios con datos de evoluciones
        parametros: Lista de dicts con {'campo': 'nombre_db', 'label': 'Nombre visible', 'color': '#hex'}
        titulo: Título de la gráfica
        theme: 'dark' u 'light'
    
    Returns:
        str: Imagen PNG en base64
    """
    if not evoluciones:
        return None
    
    # Configurar estilos según tema
    if theme == 'light':
        bg_color = '#ffffff'
        fg_color = '#f8f9fa'
        text_color = '#000000'
        grid_color = '#e9ecef'
        legend_face = '#f8f9fa'
        legend_edge = '#ced4da'
        tick_color = '#333333'
    else:
        bg_color = '#1a1a1a'
        fg_color = '#1a1a1a'
        text_color = '#ffffff'
        grid_color = '#444444'
        legend_face = '#2d2d2d'
        legend_edge = '#444444'
        tick_color = '#cccccc'
    
    if theme == 'light':
        plt.style.use('default')
    else:
        plt.style.use('dark_background')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(fg_color)
    
    # Extraer fechas
    fechas = []
    for evo in evoluciones:
        fecha_str = evo.get('fecha', '')
        if fecha_str:
            try:
                if isinstance(fecha_str, str):
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                else:
                    fecha = fecha_str
                fechas.append(fecha)
            except:
                fechas.append(None)
        else:
            fechas.append(None)
    
    # Filtrar fechas None
    fechas_validas = [f for f in fechas if f is not None]
    if not fechas_validas:
        return None
    
    # Dibujar cada parámetro
    for param in parametros:
        campo = param['campo']
        label = param['label']
        color = param.get('color', '#4ade80')
        
        valores = []
        fechas_param = []
        
        for i, evo in enumerate(evoluciones):
            if fechas[i] is not None:
                val = evo.get(campo)
                if val is not None and str(val).strip() != '':
                    try:
                        valores.append(float(val))
                        fechas_param.append(fechas[i])
                    except (ValueError, TypeError):
                        pass
        
        if valores:
            ax.plot(fechas_param, valores, marker='o', linewidth=2, 
                   markersize=6, label=label, color=color)
    
    # Configuración del gráfico
    ax.set_xlabel('Fecha', fontsize=11, color=tick_color)
    ax.set_ylabel('Valor', fontsize=11, color=tick_color)
    ax.set_title(titulo, fontsize=14, fontweight='bold', color=text_color, pad=15)
    ax.legend(loc='best', fontsize=10, facecolor=legend_face, edgecolor=legend_edge, labelcolor=text_color)
    ax.grid(True, alpha=0.3 if theme == 'dark' else 0.5, color=grid_color)
    ax.tick_params(colors=tick_color)
    
    # Formato de fechas
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Guardar a base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, facecolor=bg_color, 
                edgecolor='none', bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    
    return image_base64


def generate_liquids_chart(evoluciones):
    """Gráfica de balance de líquidos y diuresis."""
    parametros = [
        {'campo': 'balance', 'label': 'Balance (mL)', 'color': '#4ade80'},
        {'campo': 'diuresis', 'label': 'Diuresis (mL/24h)', 'color': '#60a5fa'},
    ]
    return generate_trend_chart(evoluciones, parametros, "Balance Hídrico y Diuresis")


def generate_vitals_chart(evoluciones):
    """Gráfica de signos vitales."""
    parametros = [
        {'campo': 'fc', 'label': 'FC (lpm)', 'color': '#ef4444'},
        {'campo': 'fr', 'label': 'FR (rpm)', 'color': '#f97316'},
        {'campo': 'pam', 'label': 'PAM (mmHg)', 'color': '#8b5cf6'},
        {'campo': 'temperatura', 'label': 'Temp (°C)', 'color': '#f59e0b'},
    ]
    return generate_trend_chart(evoluciones, parametros, "Signos Vitales")


def generate_labs_chart(evoluciones):
    """Gráfica de laboratorios importantes."""
    parametros = [
        {'campo': 'hemoglobina', 'label': 'Hb (g/dL)', 'color': '#ef4444'},
        {'campo': 'hematocrito', 'label': 'Hto (%)', 'color': '#f97316'},
        {'campo': 'plaquetas', 'label': 'Plt (×10³/μL)', 'color': '#8b5cf6'},
        {'campo': 'leucocitos', 'label': 'Leu (×10³/μL)', 'color': '#60a5fa'},
        {'campo': 'glucosa', 'label': 'Glu (mg/dL)', 'color': '#f59e0b'},
        {'campo': 'urea', 'label': 'BUN (mg/dL)', 'color': '#10b981'},
        {'campo': 'creatinina', 'label': 'Cr (mg/dL)', 'color': '#ec4899'},
        {'campo': 'sodio', 'label': 'Na (mEq/L)', 'color': '#06b6d4'},
        {'campo': 'potasio', 'label': 'K (mEq/L)', 'color': '#84cc16'},
        {'campo': 'lactato', 'label': 'Lactato (mmol/L)', 'color': '#f43f5e'},
    ]
    return generate_trend_chart(evoluciones, parametros, "Laboratorios Importantes")
