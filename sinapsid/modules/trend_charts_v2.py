"""
Trend Charts v2.1 - Empatado con tema Sinapsid
Genera graficas combinadas con parametros multiples
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
from datetime import datetime
import numpy as np

def generate_chart(evoluciones, chart_type='main', theme='dark', figsize=(14, 10)):
    """
    Genera grafica de tendencias para AX v2.1
    
    Args:
        evoluciones: Lista de diccionarios con datos de evoluciones
        chart_type: Tipo de grafica ('main', 'vitals', 'liquids', 'renal', 'ventilatory', 
                    'metabolic', 'hematologic', 'liver', 'coagulation', 'labs', 'combined')
        theme: 'dark' (Sinapsid oscuro), 'light' (Sinapsid claro), 'medical'
        figsize: Tamano de figura
    
    Returns:
        dict: {image: 'data:image/png;base64,...', title: '...'}
    """
    
    # Tema Sinapsid
    if theme == 'light':
        bg_color = '#ffffff'
        card_color = '#f6f8fa'
        text_color = '#24292f'
        grid_color = '#d0d7de'
        line_colors = ['#0969da', '#cf222e', '#1a7f37', '#fb8500', '#6f42c1', '#d1242f', '#1a7f37', '#8250df']
    else:
        # Dark (default Sinapsid)
        bg_color = '#0d1117'
        card_color = '#161b22'
        text_color = '#c9d1d9'
        grid_color = '#30363d'
        line_colors = ['#58a6ff', '#f85149', '#3fb950', '#d29922', '#a371f7', '#ff7b72', '#56d364', '#79c0ff']
    
    fig, ax = plt.subplots(figsize=figsize, facecolor=bg_color)
    ax.set_facecolor(card_color)
    
    # Extraer fechas
    fechas = []
    for e in evoluciones:
        fecha = e.get('fecha')
        if fecha:
            if isinstance(fecha, str):
                try:
                    fechas.append(datetime.strptime(fecha, '%Y-%m-%d'))
                except:
                    fechas.append(None)
            else:
                fechas.append(fecha)
        else:
            fechas.append(None)
    
    valid_idx = [i for i, f in enumerate(fechas) if f is not None]
    if not valid_idx:
        return {'image': None, 'title': 'Sin datos'}
    
    # Configurar ejes
    ax.tick_params(colors=text_color, labelsize=9)
    ax.xaxis.label.set_color(text_color)
    ax.yaxis.label.set_color(text_color)
    ax.title.set_color(text_color)
    ax.grid(True, alpha=0.2, color=grid_color)
    
    # Seleccionar parametros segun tipo
    if chart_type == 'combined':
        return _generate_combined(evoluciones, valid_idx, fechas, ax, line_colors, text_color, grid_color, bg_color, card_color)
    elif chart_type == 'vitals':
        params = [
            ('frecuencia_cardiaca', 'FC (lpm)', line_colors[0]),
            ('frecuencia_respiratoria', 'FR (rpm)', line_colors[1]),
            ('presion_arterial_media', 'PAM (mmHg)', line_colors[2]),
            ('temperatura', 'Temp (C)', line_colors[3]),
        ]
    elif chart_type == 'liquids':
        params = [
            ('diuresis', 'Diuresis (ml)', line_colors[0]),
            ('total_ingresos', 'Ingresos (ml)', line_colors[1]),
            ('total_egresos', 'Egresos (ml)', line_colors[2]),
            ('balance_liquidos', 'Balance (ml)', line_colors[3]),
        ]
    elif chart_type == 'renal':
        params = [
            ('creatinina', 'Creatinina', line_colors[0]),
            ('bun', 'BUN', line_colors[1]),
            ('diuresis', 'Diuresis (ml)', line_colors[2]),
            ('sodio', 'Sodio', line_colors[3]),
            ('potasio', 'Potasio', line_colors[4]),
        ]
    elif chart_type == 'ventilatory':
        params = [
            ('frecuencia_respiratoria', 'FR (rpm)', line_colors[0]),
            ('saturacion_o2', 'SpO2 (%)', line_colors[1]),
            ('fio2', 'FiO2 (%)', line_colors[2]),
            ('pafi', 'PaFi', line_colors[3]),
            ('peep', 'PEEP', line_colors[4]),
        ]
    elif chart_type == 'metabolic':
        params = [
            ('ph', 'pH', line_colors[0]),
            ('lactato', 'Lactato', line_colors[1]),
            ('glucosa', 'Glucosa', line_colors[2]),
            ('bicarbonato', 'HCO3', line_colors[3]),
        ]
    elif chart_type == 'hematologic':
        params = [
            ('hemoglobina', 'Hb (g/dL)', line_colors[0]),
            ('hematocrito', 'Hto (%)', line_colors[1]),
            ('leucocitos', 'Leucocitos', line_colors[2]),
            ('plaquetas', 'Plaquetas', line_colors[3]),
            ('inr', 'INR', line_colors[4]),
        ]
    elif chart_type == 'liver':
        params = [
            ('tgo', 'TGO', line_colors[0]),
            ('tgp', 'TGP', line_colors[1]),
            ('bilirrubina_total', 'Bili Total', line_colors[2]),
            ('albumina', 'Albumina', line_colors[3]),
        ]
    elif chart_type == 'coagulation':
        params = [
            ('tpt', 'TPT', line_colors[0]),
            ('pt', 'PT', line_colors[1]),
            ('inr', 'INR', line_colors[2]),
            ('plaquetas', 'Plaquetas', line_colors[3]),
        ]
    elif chart_type == 'labs':
        params = [
            ('glucosa', 'Glucosa', line_colors[0]),
            ('urea', 'Urea', line_colors[1]),
            ('creatinina', 'Creatinina', line_colors[2]),
            ('sodio', 'Sodio', line_colors[3]),
            ('potasio', 'Potasio', line_colors[4]),
            ('cloro', 'Cloro', line_colors[5]),
        ]
    else:  # main
        params = [
            ('frecuencia_cardiaca', 'FC', line_colors[0]),
            ('presion_arterial_media', 'PAM', line_colors[1]),
            ('frecuencia_respiratoria', 'FR', line_colors[2]),
            ('saturacion_o2', 'SpO2', line_colors[3]),
            ('creatinina', 'Creat', line_colors[4]),
            ('lactato', 'Lactato', line_colors[5]),
            ('hemoglobina', 'Hb', line_colors[6]),
            ('plaquetas', 'Plaq', line_colors[7]),
        ]
    
    # Dibujar lineas
    for param, label, color in params:
        values = []
        dates = []
        for i in valid_idx:
            val = evoluciones[i].get(param)
            if val is not None:
                try:
                    values.append(float(val))
                    dates.append(fechas[i])
                except (ValueError, TypeError):
                    pass
        
        if values:
            ax.plot(dates, values, 'o-', color=color, label=label, linewidth=2, markersize=5)
    
    # Configurar leyenda
    ax.legend(loc='upper left', fontsize=9, facecolor=card_color, edgecolor=grid_color, labelcolor=text_color)
    
    # Formato de fechas
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(valid_idx)//7)))
    plt.xticks(rotation=45, ha='right')
    
    # Titulo
    titles = {
        'main': 'Dashboard Principal',
        'vitals': 'Signos Vitales',
        'liquids': 'Balance de Liquidos',
        'renal': 'Funcion Renal',
        'ventilatory': 'Soporte Ventilatorio',
        'metabolic': 'Estado Metabolico',
        'hematologic': 'Hematologia / Coagulacion',
        'liver': 'Funcion Hepatica',
        'coagulation': 'Coagulacion',
        'labs': 'Laboratorios',
        'combined': 'Vista Combinada'
    }
    ax.set_title(titles.get(chart_type, 'Tendencias'), fontsize=14, fontweight='bold', pad=15)
    
    plt.tight_layout()
    
    # Guardar
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=120, facecolor=bg_color, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return {
        'image': f'data:image/png;base64,{img_base64}',
        'title': titles.get(chart_type, 'Tendencias')
    }


def _generate_combined(evoluciones, valid_idx, fechas, ax, line_colors, text_color, grid_color, bg_color, card_color):
    """Genera grafica combinada con todos los sistemas"""
    
    # Organizar por sistemas con eje Y secundario
    ax2 = ax.twinx()
    ax3 = ax.twinx()
    ax4 = ax.twinx()
    
    # Ajustar posicion de ejes Y
    ax2.spines['right'].set_position(('outward', 60))
    ax3.spines['right'].set_position(('outward', 120))
    ax4.spines['right'].set_position(('outward', 180))
    
    for axis in [ax, ax2, ax3, ax4]:
        axis.tick_params(colors=text_color, labelsize=8)
        axis.set_facecolor(card_color)
    
    # Hemodinamico (eje izquierdo) - FC, PAM
    dates_hm = []
    fc_vals = []
    pam_vals = []
    for i in valid_idx:
        fc = evoluciones[i].get('frecuencia_cardiaca')
        pam = evoluciones[i].get('presion_arterial_media')
        if fc is not None or pam is not None:
            dates_hm.append(fechas[i])
            fc_vals.append(float(fc) if fc else None)
            pam_vals.append(float(pam) if pam else None)
    
    if any(v is not None for v in fc_vals):
        ax.plot(dates_hm, fc_vals, 'o-', color=line_colors[0], label='FC (lpm)', linewidth=2, markersize=4)
    if any(v is not None for v in pam_vals):
        ax.plot(dates_hm, pam_vals, 's-', color=line_colors[1], label='PAM (mmHg)', linewidth=2, markersize=4)
    
    ax.set_ylabel('Hemodinamico', color=line_colors[0], fontsize=9)
    ax.tick_params(axis='y', labelcolor=line_colors[0])
    
    # Ventilatorio (eje derecho 1) - SpO2, FR
    dates_vt = []
    spo2_vals = []
    fr_vals = []
    for i in valid_idx:
        spo2 = evoluciones[i].get('saturacion_o2')
        fr = evoluciones[i].get('frecuencia_respiratoria')
        if spo2 is not None or fr is not None:
            dates_vt.append(fechas[i])
            spo2_vals.append(float(spo2) if spo2 else None)
            fr_vals.append(float(fr) if fr else None)
    
    if any(v is not None for v in spo2_vals):
        ax2.plot(dates_vt, spo2_vals, '^-', color=line_colors[3], label='SpO2 (%)', linewidth=2, markersize=4)
    if any(v is not None for v in fr_vals):
        ax2.plot(dates_vt, fr_vals, 'v-', color=line_colors[2], label='FR (rpm)', linewidth=2, markersize=4)
    
    ax2.set_ylabel('Ventilatorio', color=line_colors[3], fontsize=9)
    ax2.tick_params(axis='y', labelcolor=line_colors[3])
    
    # Renal (eje derecho 2) - Creatinina, Diuresis
    dates_rn = []
    crea_vals = []
    diur_vals = []
    for i in valid_idx:
        crea = evoluciones[i].get('creatinina')
        diur = evoluciones[i].get('diuresis')
        if crea is not None or diur is not None:
            dates_rn.append(fechas[i])
            crea_vals.append(float(crea) if crea else None)
            diur_vals.append(float(diur) if diur else None)
    
    if any(v is not None for v in crea_vals):
        ax3.plot(dates_rn, crea_vals, 'D-', color=line_colors[4], label='Creat (mg/dL)', linewidth=2, markersize=4)
    if any(v is not None for v in diur_vals):
        ax3.plot(dates_rn, diur_vals, 'p-', color=line_colors[5], label='Diuresis (ml)', linewidth=2, markersize=4)
    
    ax3.set_ylabel('Renal', color=line_colors[4], fontsize=9)
    ax3.tick_params(axis='y', labelcolor=line_colors[4])
    
    # Metabolico (eje derecho 3) - Lactato, pH
    dates_mt = []
    lact_vals = []
    ph_vals = []
    for i in valid_idx:
        lact = evoluciones[i].get('lactato')
        ph = evoluciones[i].get('ph')
        if lact is not None or ph is not None:
            dates_mt.append(fechas[i])
            lact_vals.append(float(lact) if lact else None)
            ph_vals.append(float(ph) if ph else None)
    
    if any(v is not None for v in lact_vals):
        ax4.plot(dates_mt, lact_vals, 'h-', color=line_colors[6], label='Lactato', linewidth=2, markersize=4)
    if any(v is not None for v in ph_vals):
        ax4.plot(dates_mt, ph_vals, '*-', color=line_colors[7], label='pH', linewidth=2, markersize=6)
    
    ax4.set_ylabel('Metabolico', color=line_colors[6], fontsize=9)
    ax4.tick_params(axis='y', labelcolor=line_colors[6])
    
    # Formato de fechas
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(valid_idx)//7)))
    plt.xticks(rotation=45, ha='right', color=text_color)
    
    # Leyenda combinada
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    lines4, labels4 = ax4.get_legend_handles_labels()
    
    all_lines = lines1 + lines2 + lines3 + lines4
    all_labels = labels1 + labels2 + labels3 + labels4
    
    ax.legend(all_lines, all_labels, loc='upper left', fontsize=8, 
              facecolor=card_color, edgecolor=grid_color, labelcolor=text_color,
              ncol=2)
    
    ax.set_title('Vista Combinada - Todos los Sistemas', fontsize=14, fontweight='bold', pad=15, color=text_color)
    ax.grid(True, alpha=0.2, color=grid_color)
    
    return {
        'image': _save_fig_to_base64(ax.figure, bg_color),
        'title': 'Vista Combinada'
    }


def _save_fig_to_base64(fig, bg_color):
    """Guarda figura a base64"""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=120, facecolor=bg_color, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f'data:image/png;base64,{img_base64}'
