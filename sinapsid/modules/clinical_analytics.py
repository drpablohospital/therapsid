import statistics
#!/usr/bin/env python3
"""
Módulo de Métricas Avanzadas para Análisis Clínico y Predicción de Mortalidad
Basado en evidencia 2024-2025

Determinantes de mortalidad identificados:
1. Calcio Iónico (Niu et al. Sci Rep 2025)
2. Índice de Choque (FC/TAS) (PLOS One 2024)
3. Δ SOFA (Multiple studies)
4. AUC SOFA (Trapezoidal integral)
5. Δ Lactato (Serial evaluation Sci Rep 2023)
6. Clearance de Lactato (Frontiers 2025)
7. Lactato/Albúmina ratio (Eg J Bronch 2025)
8. PCT Clearance (Infect Drug Resist 2025)
9. PAM (Meta-análisis PLOS One 2024)
10. Bilirrubina/INR (SAPS3 components)
11. Plaquetas Nadir (Sepsis-induced thrombocytopenia)
"""

import math
from datetime import datetime, date, timedelta
from collections import defaultdict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

# ============================================================================
# FUNCIONES UTILITARIAS
# ============================================================================

def safe_float(val, default=None):
    """Convierte valor a float de forma segura."""
    if val is None or val == '':
        return default
    try:
        f = float(val)
        return f if f != 0 else default  # Considerar 0 como ausente para algunos campos
    except (ValueError, TypeError):
        return default

def safe_int(val, default=None):
    """Convierte valor a int de forma segura."""
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def parse_datetime(val):
    """Parsea fecha/hora de forma flexible."""
    if val is None:
        return None
    if hasattr(val, 'isoformat'):
        return val
    if isinstance(val, str):
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
            try:
                return datetime.strptime(val[:19], fmt)
            except:
                continue
    return None

def parse_date(val):
    """Parsea fecha."""
    dt = parse_datetime(val)
    if dt:
        return dt.date() if hasattr(dt, 'date') else dt
    return None

def extract_series(evolutions, field):
    """
    Extrae una serie de valores y timestamps de las evoluciones.
    Retorna (values, times) ordenados cronológicamente.
    """
    pairs = []
    for evo in evolutions:
        val = evo.get(field)
        fecha = evo.get('fecha')
        hora = evo.get('hora', '00:00')
        
        if val is not None and fecha is not None:
            dt = parse_datetime(f"{str(fecha)[:10]} {str(hora)[:5]}")
            if dt:
                fval = safe_float(val)
                if fval is not None:
                    pairs.append((dt, fval))
    
    # Ordenar por tiempo
    pairs.sort(key=lambda x: x[0])
    times = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    
    return values, times

# ============================================================================
# CÁLCULOS ESTADÍSTICOS UNIVERSALES
# ============================================================================

def calculate_range(values):
    """Calcula rango (min, max, mean) de una serie."""
    if not values or len(values) == 0:
        return None, None, None
    return min(values), max(values), round(sum(values) / len(values), 2)

def calculate_delta(values):
    """Calcula delta (máximo - mínimo o último - primero)."""
    if not values or len(values) < 2:
        return None
    # Delta = valor máximo alcanzado - valor inicial
    return round(max(values) - values[0], 3)

def calculate_slope(values, times):
    """
    Calcula la pendiente (tendencia) usando mínimos cuadrados.
    Retorna unidades por día.
    """
    if not values or len(values) < 2:
        return None
    
    base_time = times[0]
    x = []
    y = []
    for t, v in zip(times, values):
        if v is not None:
            delta = (t - base_time).total_seconds() / 86400
            x.append(delta)
            y.append(v)
    
    if len(y) < 2:
        return None
    
    n = len(y)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi ** 2 for xi in x)
    
    denominator = n * sum_x2 - sum_x ** 2
    if denominator == 0:
        return 0
    
    return (n * sum_xy - sum_x * sum_y) / denominator

def calculate_auc(values, times):
    """
    Calcula el área bajo la curva usando método del trapecio.
    Área en unidades × días.
    """
    if not values or len(values) < 2:
        return None
    
    area = 0
    for i in range(len(values) - 1):
        if values[i] is not None and values[i+1] is not None:
            delta_t = (times[i+1] - times[i]).total_seconds() / 86400
            area += (values[i] + values[i+1]) / 2 * delta_t
    
    return round(area, 2) if area != 0 else None

def calculate_clearance(values, times, threshold=2.0, direction='below'):
    """
    Calcula el tiempo hasta que una serie cruza un umbral.
    Retorna horas desde el inicio.
    """
    if not values or len(values) < 2:
        return None
    
    for i, (v, t) in enumerate(zip(values, times)):
        if v is None:
            continue
        if direction == 'below' and v <= threshold:
            return round((t - times[0]).total_seconds() / 3600, 2)
        elif direction == 'above' and v >= threshold:
            return round((t - times[0]).total_seconds() / 3600, 2)
    
    return None

def calculate_variability(values):
    """
    Calcula coeficiente de variación (CV = std/mean).
    Mayor CV = mayor inestabilidad.
    """
    if not values or len(values) < 2:
        return None
    
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = math.sqrt(variance)
    cv = (std / mean) * 100
    
    return round(cv, 2)

# ============================================================================
# DETERMINANTES ESPECÍFICOS DE MORTALIDAD
# ============================================================================

def calculate_shock_index(fc_values, tas_values):
    """
    Índice de Choque = FC / TAS
    
    Valores:
    - Normal: 0.5 - 0.7
    - Elevado: > 0.9 (shock)
    - Severo: > 1.4 (mortalidad ~50%)
    
    Referencia: PLOS One 2024
    """
    if not fc_values or not tas_values or len(fc_values) != len(tas_values):
        return None
    
    si_values = []
    for fc, tas in zip(fc_values, tas_values):
        if tas > 0:
            si = fc / tas
            si_values.append(si)
    
    if not si_values:
        return None
    
    return {
        'min': round(min(si_values), 2),
        'max': round(max(si_values), 2),
        'mean': round(sum(si_values) / len(si_values), 2),
        'shock_ratio': round(sum(1 for si in si_values if si > 0.9) / len(si_values) * 100, 1)
    }

def calculate_calcium_ionized_risk(calcium_values):
    """
    Riesgo basado en calcio iónico.
    
    Umbral: < 1.0 mmol/L asociado con mayor mortalidad
    Referencia: Niu et al. Sci Rep 2025
    """
    if not calcium_values:
        return None
    
    min_ca = min(calcium_values)
    mean_ca = sum(calcium_values) / len(calcium_values)
    
    return {
        'min': round(min_ca, 2),
        'mean': round(mean_ca, 2),
        'risk_low': min_ca < 1.0,
        'risk_severe': min_ca < 0.9
    }

def calculate_lactate_albumin_ratio(lactato_values, albumina_values):
    """
    Lactato/Albúmina ratio como predictor de mortalidad.
    
    Umbral: > 1.5 asociado con mayor mortalidad
    Referencia: Egyptian Journal of Bronchology 2025
    """
    if not lactato_values or not albumina_values:
        return None
    
    # Usar valores máximos de lactato y mínimos de albúmina
    max_lact = max(lactato_values)
    min_alb = min(albumina_values)
    
    if min_alb <= 0:
        return None
    
    ratio = max_lact / min_alb
    
    return {
        'ratio': round(ratio, 2),
        'high_risk': ratio > 1.5
    }

def calculate_pct_clearance(pct_values, times):
    """
    Clearance de procalcitonina.
    
    Umbral: < 80% a 24h asociado con mayor mortalidad
    Referencia: Infect Drug Resist 2025
    """
    if not pct_values or len(pct_values) < 2:
        return None
    
    baseline = pct_values[0]
    if baseline <= 0:
        return None
    
    # Buscar valor a 24h
    time_24h = times[0] + timedelta(hours=24)
    pct_24h = None
    for i, t in enumerate(times):
        if t >= time_24h:
            pct_24h = pct_values[i]
            break
    
    if pct_24h is None:
        # Usar último valor disponible
        pct_24h = pct_values[-1]
    
    clearance = ((baseline - pct_24h) / baseline) * 100
    
    return {
        'baseline': round(baseline, 2),
        'value_24h': round(pct_24h, 2),
        'clearance_percent': round(clearance, 1),
        'adequate': clearance >= 80
    }

def calculate_lactate_clearance_percent(lactato_values, times):
    """
    Clearance de lactato en porcentaje.
    
    Umbral: < 10% a 6h mal pronóstico
    Referencia: Frontiers Medicine 2025
    """
    if not lactato_values or len(lactato_values) < 2:
        return None
    
    baseline = lactato_values[0]
    if baseline <= 0:
        return None
    
    # Buscar valor a 6h
    time_6h = times[0] + timedelta(hours=6)
    lact_6h = None
    for i, t in enumerate(times):
        if t >= time_6h:
            lact_6h = lactato_values[i]
            break
    
    if lact_6h is None:
        return None
    
    clearance = ((baseline - lact_6h) / baseline) * 100
    
    return {
        'baseline': round(baseline, 2),
        'value_6h': round(lact_6h, 2),
        'clearance_percent': round(clearance, 1),
        'adequate': clearance >= 10
    }

def calculate_pam_risk(pam_values):
    """
    Riesgo basado en PAM (Presión Arterial Media).
    
    Umbral: < 65 mmHg asociado con shock y mayor mortalidad
    Referencia: Meta-análisis PLOS One 2024
    """
    if not pam_values:
        return None
    
    min_pam = min(pam_values)
    mean_pam = sum(pam_values) / len(pam_values)
    time_below_65 = sum(1 for p in pam_values if p < 65)
    
    return {
        'min': round(min_pam, 1),
        'mean': round(mean_pam, 1),
        'hypotension_ratio': round(time_below_65 / len(pam_values) * 100, 1),
        'shock': min_pam < 65
    }

def calculate_platelet_nadir_risk(platelet_values):
    """
    Riesgo basado en nadir de plaquetas.
    
    Umbral: < 100,000 trombocitopenia severa
    < 50,000 riesgo de sangrado
    Referencia: Sepsis-induced thrombocytopenia studies
    """
    if not platelet_values:
        return None
    
    nadir = min(platelet_values)
    
    return {
        'nadir': round(nadir, 0),
        'thrombocytopenia': nadir < 100,
        'severe': nadir < 50,
        'bleeding_risk': nadir < 20
    }

def calculate_bilirubin_inr_risk(bili_values, inr_values):
    """
    Riesgo hepático-coagulopatía.
    Parte de SAPS3.
    """
    if not bili_values or not inr_values:
        return None
    
    max_bili = max(bili_values)
    max_inr = max(inr_values)
    
    # Score compuesto
    risk_score = 0
    if max_bili > 2: risk_score += 1
    if max_bili > 6: risk_score += 1
    if max_inr > 1.5: risk_score += 1
    if max_inr > 2.5: risk_score += 1
    
    return {
        'max_bilirubin': round(max_bili, 1),
        'max_inr': round(max_inr, 2),
        'risk_score': risk_score,
        'high_risk': risk_score >= 3
    }

# ============================================================================
# CALCULADORA UNIVERSAL DE TENDENCIAS
# ============================================================================

def calculate_trend_analytics(values, times, field_name):
    """
    Calcula TODAS las métricas de tendencia para un campo dado.
    
    Retorna diccionario con:
    - range_min, range_max, range_mean
    - delta (max - baseline)
    - slope (unidades/día)
    - auc (unidades × días)
    - variability (CV %)
    - trend_direction: 'improving', 'worsening', 'stable'
    """
    if not values or len(values) == 0:
        return {}
    
    result = {}
    
    # OHLC (Open, High, Low, Close) - formato velas de trading
    open_val = values[0]  # Primer valor (inicio)
    close_val = values[-1]  # Ultimo valor (mas reciente)
    high_val = max(values)
    low_val = min(values)
    mean_val = statistics.mean(values)
    
    # Guardar OHLC
    result[f'{field_name}_open'] = open_val
    result[f'{field_name}_high'] = high_val
    result[f'{field_name}_low'] = low_val
    result[f'{field_name}_close'] = close_val
    result[f'{field_name}_mean'] = mean_val
    
    # Para backward compatibility
    result[f'{field_name}_min'] = low_val
    result[f'{field_name}_max'] = high_val
    result[f'{field_name}_last'] = close_val
    
    # Calcular delta como Close - Open (como en trading)
    if len(values) >= 2:
        ohlc_delta = close_val - open_val
        result[f'{field_name}_ohlc_delta'] = ohlc_delta
        
        # Delta porcentual
        if open_val != 0:
            ohlc_delta_pct = (ohlc_delta / abs(open_val)) * 100
            result[f'{field_name}_ohlc_delta_pct'] = round(ohlc_delta_pct, 2)
        
        # Tendencia basada en OHLC
        bad_increasing = ['creatinina', 'lactato', 'pcr', 'inr', 'bilirrubina', 'fc', 'temperatura', 'dimero_d', 'fio2', 'peep']
        is_bad = any(bad in field_name.lower() for bad in bad_increasing)
        
        if abs(ohlc_delta) < 0.01 * abs(open_val) if open_val != 0 else abs(ohlc_delta) < 0.01:
            result[f'{field_name}_ohlc_trend'] = 'stable'
        elif ohlc_delta > 0:
            result[f'{field_name}_ohlc_trend'] = 'worsening' if is_bad else 'improving'
        else:
            result[f'{field_name}_ohlc_trend'] = 'improving' if is_bad else 'worsening'
    
    # Rango (formato viejo - mantener para compatibilidad)
    if isinstance(low_val, float):
        result[f'{field_name}_range'] = f"{low_val:.1f} - {high_val:.1f}"
    else:
        result[f'{field_name}_range'] = f"{low_val} - {high_val}"
    
    # Delta
    if len(values) >= 2:
        delta = calculate_delta(values)
        if delta is not None:
            result[f'{field_name}_delta'] = delta
    
    # Tendencia (slope)
    if times and len(times) == len(values) and len(values) >= 2:
        slope = calculate_slope(values, times)
        if slope is not None:
            result[f'{field_name}_slope'] = round(slope, 4)
            
            # Determinar dirección
            bad_increasing = ['creatinina', 'lactato', 'pcr', 'inr', 'bilirrubina', 'fc', 'temperatura', 'dimero_d', 'fio2', 'peep']
            if abs(slope) < 0.01:
                result[f'{field_name}_trend'] = 'stable'
            elif slope > 0:
                if any(bad in field_name.lower() for bad in bad_increasing):
                    result[f'{field_name}_trend'] = 'worsening'
                else:
                    result[f'{field_name}_trend'] = 'improving'
            else:
                if any(bad in field_name.lower() for bad in bad_increasing):
                    result[f'{field_name}_trend'] = 'improving'
                else:
                    result[f'{field_name}_trend'] = 'worsening'
    # AUC
    if times and len(times) == len(values) and len(values) >= 2:
        auc = calculate_auc(values, times)
        if auc is not None:
            result[f'{field_name}_auc'] = auc
    
    # Variabilidad
    if len(values) >= 2:
        cv = calculate_variability(values)
        if cv is not None:
            result[f'{field_name}_cv'] = cv
    
    return result

# ============================================================================
# FUNCIÓN PRINCIPAL: CALCULAR TODAS LAS MÉTRICAS
# ============================================================================

def calculate_advanced_metrics(patient, evolutions):
    """
    Calcula TODAS las métricas avanzadas para análisis clínico.
    
    Args:
        patient: Diccionario con datos del paciente
        evolutions: Lista de diccionarios con evoluciones
    
    Returns:
        dict: Diccionario con todas las métricas calculadas
    """
    metrics = {}
    
    # ============ CUMPLIMIENTO (del sistema anterior) ============
    # No se calcula aquí, se pasa como parámetro
    
    # ============ ESTANCIA ============
    fecha_ingreso = parse_date(patient.get('fecha_ingreso_uci') or patient.get('fecha_ingreso'))
    fecha_egreso = parse_date(patient.get('fecha_egreso_uci') or patient.get('fecha_egreso_hospital'))
    
    if fecha_ingreso:
        if fecha_egreso:
            dias_estancia = max(1, (fecha_egreso - fecha_ingreso).days)
        else:
            dias_estancia = max(1, (date.today() - fecha_ingreso).days)
    else:
        dias_estancia = len(set(e.get('fecha') for e in evolutions if e.get('fecha'))) or 1
    
    metrics['dias_estancia'] = dias_estancia
    metrics['total_evoluciones'] = len(evolutions)
    metrics['evoluciones_por_dia'] = round(len(evolutions) / dias_estancia, 2) if dias_estancia > 0 else 0
    
    # ============ SIGNOS VITALES - TENDENCIAS COMPLETAS ============
    
    # FC
    fc_values, fc_times = extract_series(evolutions, 'fc')
    if fc_values:
        fc_metrics = calculate_trend_analytics(fc_values, fc_times, 'fc')
        metrics.update(fc_metrics)
    
    # FR
    fr_values, fr_times = extract_series(evolutions, 'fr')
    if fr_values:
        fr_metrics = calculate_trend_analytics(fr_values, fr_times, 'fr')
        metrics.update(fr_metrics)
    
    # TAS
    tas_values, tas_times = extract_series(evolutions, 'tas')
    if tas_values:
        tas_metrics = calculate_trend_analytics(tas_values, tas_times, 'tas')
        metrics.update(tas_metrics)
    
    # TAD
    tad_values, tad_times = extract_series(evolutions, 'tad')
    if tad_values:
        tad_metrics = calculate_trend_analytics(tad_values, tad_times, 'tad')
        metrics.update(tad_metrics)
    
    # TAM/PAM
    pam_values, pam_times = extract_series(evolutions, 'tam')
    if not pam_values:
        # Calcular TAM = (TAS + 2*TAD) / 3
        if tas_values and tad_values:
            pam_values = []
            pam_times = []
            for i, (tas, tad) in enumerate(zip(tas_values, tad_values)):
                if tas and tad:
                    pam = (tas + 2 * tad) / 3
                    pam_values.append(pam)
                    # Usar tiempo de TAS
                    if i < len(tas_times):
                        pam_times.append(tas_times[i])
    
    if pam_values:
        pam_metrics = calculate_trend_analytics(pam_values, pam_times, 'pam')
        metrics.update(pam_metrics)
        
        # Riesgo de PAM
        pam_risk = calculate_pam_risk(pam_values)
        if pam_risk:
            metrics['pam_risk_min'] = pam_risk['min']
            metrics['pam_risk_mean'] = pam_risk['mean']
            metrics['pam_hypotension_ratio'] = pam_risk['hypotension_ratio']
            metrics['pam_shock'] = pam_risk['shock']
    
    # SpO2
    spo2_values, spo2_times = extract_series(evolutions, 'spo2')
    if spo2_values:
        spo2_metrics = calculate_trend_analytics(spo2_values, spo2_times, 'spo2')
        metrics.update(spo2_metrics)
        
        # Tiempo con SpO2 < 90
        hours_below_90 = sum(1 for v in spo2_values if v < 90)
        metrics['spo2_time_below_90'] = round(hours_below_90 * 24 / max(1, len(spo2_values)), 2)
    
    # Temperatura
    temp_values, temp_times = extract_series(evolutions, 'temperatura')
    if temp_values:
        temp_metrics = calculate_trend_analytics(temp_values, temp_times, 'temperatura')
        metrics.update(temp_metrics)
    
    # Glasgow
    glasgow_values, glasgow_times = extract_series(evolutions, 'glasgow')
    if glasgow_values:
        glasgow_metrics = calculate_trend_analytics(glasgow_values, glasgow_times, 'glasgow')
        metrics.update(glasgow_metrics)
    
    # RASS
    rass_values, rass_times = extract_series(evolutions, 'rass')
    if rass_values:
        rass_metrics = calculate_trend_analytics(rass_values, rass_times, 'rass')
        metrics.update(rass_metrics)
    
    # ============ ÍNDICE DE CHOQUE ============
    if fc_values and tas_values and len(fc_values) == len(tas_values):
        si_data = calculate_shock_index(fc_values, tas_values)
        if si_data:
            metrics['shock_index_min'] = si_data['min']
            metrics['shock_index_max'] = si_data['max']
            metrics['shock_index_mean'] = si_data['mean']
            metrics['shock_index_shock_ratio'] = si_data['shock_ratio']
    
    # ============ LABORATORIOS - TENDENCIAS COMPLETAS ============
    
    # Creatinina
    crea_values, crea_times = extract_series(evolutions, 'creatinina')
    if crea_values:
        crea_metrics = calculate_trend_analytics(crea_values, crea_times, 'creatinina')
        metrics.update(crea_metrics)
    
    # Lactato
    lact_values, lact_times = extract_series(evolutions, 'lactato')
    if lact_values:
        lact_metrics = calculate_trend_analytics(lact_values, lact_times, 'lactato')
        metrics.update(lact_metrics)
        
        # Clearance de lactato
        lact_clearance = calculate_clearance(lact_values, lact_times, 2.0, 'below')
        if lact_clearance:
            metrics['lactato_clearance_time'] = lact_clearance
        
        # Clearance porcentual
        lact_pct_clearance = calculate_lactate_clearance_percent(lact_values, lact_times)
        if lact_pct_clearance:
            metrics['lactato_clearance_percent'] = lact_pct_clearance['clearance_percent']
            metrics['lactato_clearance_adequate'] = lact_pct_clearance['adequate']
    
    # PCR
    pcr_values, pcr_times = extract_series(evolutions, 'pcr')
    if pcr_values:
        pcr_metrics = calculate_trend_analytics(pcr_values, pcr_times, 'pcr')
        metrics.update(pcr_metrics)
    
    # Procalcitonina
    pct_values, pct_times = extract_series(evolutions, 'procalcitonina')
    if pct_values:
        pct_metrics = calculate_trend_analytics(pct_values, pct_times, 'pct')
        metrics.update(pct_metrics)
        
        # Clearance de PCT
        pct_clearance = calculate_pct_clearance(pct_values, pct_times)
        if pct_clearance:
            metrics['pct_clearance_percent'] = pct_clearance['clearance_percent']
            metrics['pct_clearance_adequate'] = pct_clearance['adequate']
    
    # Leucocitos
    leu_values, leu_times = extract_series(evolutions, 'leucocitos')
    if leu_values:
        leu_metrics = calculate_trend_analytics(leu_values, leu_times, 'leucocitos')
        metrics.update(leu_metrics)
    
    # Neutrófilos
    neu_values, neu_times = extract_series(evolutions, 'neutrofilos')
    if neu_values:
        neu_metrics = calculate_trend_analytics(neu_values, neu_times, 'neutrofilos')
        metrics.update(neu_metrics)
    
    # Linfocitos
    lin_values, lin_times = extract_series(evolutions, 'linfocitos')
    if lin_values:
        lin_metrics = calculate_trend_analytics(lin_values, lin_times, 'linfocitos')
        metrics.update(lin_metrics)
    
    # Plaquetas
    pla_values, pla_times = extract_series(evolutions, 'plaquetas')
    if pla_values:
        pla_metrics = calculate_trend_analytics(pla_values, pla_times, 'plaquetas')
        metrics.update(pla_metrics)
        
        # Riesgo de plaquetas
        plt_risk = calculate_platelet_nadir_risk(pla_values)
        if plt_risk:
            metrics['plaquetas_nadir'] = plt_risk['nadir']
            metrics['plaquetas_thrombocytopenia'] = plt_risk['thrombocytopenia']
            metrics['plaquetas_severe'] = plt_risk['severe']
    
    # Hemoglobina
    hb_values, hb_times = extract_series(evolutions, 'hemoglobina')
    if hb_values:
        hb_metrics = calculate_trend_analytics(hb_values, hb_times, 'hemoglobina')
        metrics.update(hb_metrics)
    
    # Hematocrito
    hto_values, hto_times = extract_series(evolutions, 'hematocrito')
    if hto_values:
        hto_metrics = calculate_trend_analytics(hto_values, hto_times, 'hematocrito')
        metrics.update(hto_metrics)
    
    # ============ HEPÁTICOS ============
    bili_t_values, bili_t_times = extract_series(evolutions, 'bilirrubina_total')
    if bili_t_values:
        bili_metrics = calculate_trend_analytics(bili_t_values, bili_t_times, 'bilirrubina_total')
        metrics.update(bili_metrics)
    
    bili_d_values, bili_d_times = extract_series(evolutions, 'bilirrubina_directa')
    if bili_d_values:
        bili_d_metrics = calculate_trend_analytics(bili_d_values, bili_d_times, 'bilirrubina_directa')
        metrics.update(bili_d_metrics)
    
    alt_values, alt_times = extract_series(evolutions, 'alt')
    if alt_values:
        alt_metrics = calculate_trend_analytics(alt_values, alt_times, 'alt')
        metrics.update(alt_metrics)
    
    ast_values, ast_times = extract_series(evolutions, 'ast')
    if ast_values:
        ast_metrics = calculate_trend_analytics(ast_values, ast_times, 'ast')
        metrics.update(ast_metrics)
    
    albumina_values, albumina_times = extract_series(evolutions, 'albumina')
    if albumina_values:
        alb_metrics = calculate_trend_analytics(albumina_values, albumina_times, 'albumina')
        metrics.update(alb_metrics)
    
    # ============ COAGULACIÓN ============
    inr_values, inr_times = extract_series(evolutions, 'inr')
    if inr_values:
        inr_metrics = calculate_trend_analytics(inr_values, inr_times, 'inr')
        metrics.update(inr_metrics)
    
    pt_values, pt_times = extract_series(evolutions, 'pt')
    if pt_values:
        pt_metrics = calculate_trend_analytics(pt_values, pt_times, 'pt')
        metrics.update(pt_metrics)
    
    aptt_values, aptt_times = extract_series(evolutions, 'aptt')
    if aptt_values:
        aptt_metrics = calculate_trend_analytics(aptt_values, aptt_times, 'aptt')
        metrics.update(aptt_metrics)
    
    dimero_values, dimero_times = extract_series(evolutions, 'dimero_d')
    if dimero_values:
        dimero_metrics = calculate_trend_analytics(dimero_values, dimero_times, 'dimero_d')
        metrics.update(dimero_metrics)
    
    fibrinogeno_values, fibrinogeno_times = extract_series(evolutions, 'fibrinogeno')
    if fibrinogeno_values:
        fib_metrics = calculate_trend_analytics(fibrinogeno_values, fibrinogeno_times, 'fibrinogeno')
        metrics.update(fib_metrics)
    
    # Riesgo hepático-coagulopatía
    if bili_t_values and inr_values:
        bili_inr_risk = calculate_bilirubin_inr_risk(bili_t_values, inr_values)
        if bili_inr_risk:
            metrics['hepatic_coag_risk_score'] = bili_inr_risk['risk_score']
            metrics['hepatic_coag_high_risk'] = bili_inr_risk['high_risk']
    
    # ============ ELECTROLITOS ============
    sodio_values, sodio_times = extract_series(evolutions, 'sodio')
    if sodio_values:
        sodio_metrics = calculate_trend_analytics(sodio_values, sodio_times, 'sodio')
        metrics.update(sodio_metrics)
    
    potasio_values, potasio_times = extract_series(evolutions, 'potasio')
    if potasio_values:
        pot_metrics = calculate_trend_analytics(potasio_values, potasio_times, 'potasio')
        metrics.update(pot_metrics)
    
    cloro_values, cloro_times = extract_series(evolutions, 'cloro')
    if cloro_values:
        cloro_metrics = calculate_trend_analytics(cloro_values, cloro_times, 'cloro')
        metrics.update(cloro_metrics)
    
    magnesio_values, magnesio_times = extract_series(evolutions, 'magnesio')
    if magnesio_values:
        mag_metrics = calculate_trend_analytics(magnesio_values, magnesio_times, 'magnesio')
        metrics.update(mag_metrics)
    
    # Calcio
    calcio_values, calcio_times = extract_series(evolutions, 'calcio')
    if calcio_values:
        ca_metrics = calculate_trend_analytics(calcio_values, calcio_times, 'calcio')
        metrics.update(ca_metrics)
        
        # Riesgo de calcio
        ca_risk = calculate_calcium_ionized_risk(calcio_values)
        if ca_risk:
            metrics['calcio_risk_low'] = ca_risk['risk_low']
            metrics['calcio_risk_severe'] = ca_risk['risk_severe']
    
    # Fósforo
    fosforo_values, fosforo_times = extract_series(evolutions, 'fosforo')
    if fosforo_values:
        fos_metrics = calculate_trend_analytics(fosforo_values, fosforo_times, 'fosforo')
        metrics.update(fos_metrics)
    
    # ============ GASOMETRÍA / VENTILACIÓN ============
    ph_values, ph_times = extract_series(evolutions, 'ph')
    if ph_values:
        ph_metrics = calculate_trend_analytics(ph_values, ph_times, 'ph')
        metrics.update(ph_metrics)
    
    pao2_values, pao2_times = extract_series(evolutions, 'pao2')
    if pao2_values:
        pao2_metrics = calculate_trend_analytics(pao2_values, pao2_times, 'pao2')
        metrics.update(pao2_metrics)
    
    paco2_values, paco2_times = extract_series(evolutions, 'paco2')
    if paco2_values:
        paco2_metrics = calculate_trend_analytics(paco2_values, paco2_times, 'paco2')
        metrics.update(paco2_metrics)
    
    hco3_values, hco3_times = extract_series(evolutions, 'hco3')
    if hco3_values:
        hco3_metrics = calculate_trend_analytics(hco3_values, hco3_times, 'hco3')
        metrics.update(hco3_metrics)
    
    lactato_gas_values, lactato_gas_times = extract_series(evolutions, 'lactato_gasometria')
    if lactato_gas_values:
        lact_gas_metrics = calculate_trend_analytics(lactato_gas_values, lactato_gas_times, 'lactato_gasometria')
        metrics.update(lact_gas_metrics)
    
    # PaFi
    pafi_values = []
    pafi_times = []
    for evo in evolutions:
        pafi = evo.get('pafi')
        if pafi and safe_float(pafi):
            pafi_values.append(safe_float(pafi))
            dt = parse_datetime(f"{str(evo.get('fecha'))[:10]} {str(evo.get('hora'))[:5]}")
            if dt:
                pafi_times.append(dt)
    
    if not pafi_values and pao2_values:
        # Calcular PaFi proxy
        fio2_values, _ = extract_series(evolutions, 'fio2')
        if fio2_values and len(pao2_values) == len(fio2_values):
            pafi_values = []
            pafi_times = []
            for pao2, fio2 in zip(pao2_values, fio2_values):
                if fio2 and fio2 > 0:
                    pafi = (pao2 / fio2) * 100
                    pafi_values.append(pafi)
                    pafi_times.append(pao2_times[0])  # Simplificado
    
    if pafi_values:
        pafi_metrics = calculate_trend_analytics(pafi_values, pafi_times, 'pafi')
        metrics.update(pafi_metrics)
    
    # FiO2
    fio2_values, fio2_times = extract_series(evolutions, 'fio2')
    if fio2_values:
        fio2_metrics = calculate_trend_analytics(fio2_values, fio2_times, 'fio2')
        metrics.update(fio2_metrics)
    
    # PEEP
    peep_values, peep_times = extract_series(evolutions, 'peep')
    if peep_values:
        peep_metrics = calculate_trend_analytics(peep_values, peep_times, 'peep')
        metrics.update(peep_metrics)
    
    # PPico
    ppico_values, ppico_times = extract_series(evolutions, 'ppico')
    if ppico_values:
        ppico_metrics = calculate_trend_analytics(ppico_values, ppico_times, 'ppico')
        metrics.update(ppico_metrics)
    
    # Driving Pressure
    dp_values, dp_times = extract_series(evolutions, 'driving_pressure')
    if dp_values:
        dp_metrics = calculate_trend_analytics(dp_values, dp_times, 'driving_pressure')
        metrics.update(dp_metrics)
    
    # Compliance
    compliance_values, compliance_times = extract_series(evolutions, 'compliance_pulmonar')
    if compliance_values:
        comp_metrics = calculate_trend_analytics(compliance_values, compliance_times, 'compliance_pulmonar')
        metrics.update(comp_metrics)
    
    # ============ SCORES DINÁMICOS ============
    
    # SOFA
    sofa_scores = []
    sofa_times_scored = []
    for evo in evolutions:
        try:
            from modules.calculations import calculate_sofa
            score = calculate_sofa(evo)
            if isinstance(score, dict):
                score = score.get('score')
            if score is not None:
                sofa_scores.append(score)
                dt = parse_datetime(f"{str(evo.get('fecha'))[:10]} {str(evo.get('hora'))[:5]}")
                if dt:
                    sofa_times_scored.append(dt)
        except:
            pass
    
    sofa_baseline = safe_float(patient.get('sofa_ingreso'))
    if sofa_scores:
        if sofa_baseline is not None:
            sofa_scores.insert(0, sofa_baseline)
            fecha_ingreso = parse_date(patient.get('fecha_ingreso'))
            if fecha_ingreso:
                sofa_times_scored.insert(0, datetime.combine(fecha_ingreso, datetime.min.time()))
        
        sofa_metrics = calculate_trend_analytics(sofa_scores, sofa_times_scored, 'sofa')
        metrics.update(sofa_metrics)
    
    # NEWS2
    news2_scores = []
    news2_times_scored = []
    for evo in evolutions:
        try:
            from modules.calculations import calculate_news2
            score = calculate_news2(evo)
            if isinstance(score, dict):
                score = score.get('score')
            if score is not None:
                news2_scores.append(score)
                dt = parse_datetime(f"{str(evo.get('fecha'))[:10]} {str(evo.get('hora'))[:5]}")
                if dt:
                    news2_times_scored.append(dt)
        except:
            pass
    
    news2_baseline = safe_float(patient.get('news2_ingreso'))
    if news2_scores:
        if news2_baseline is not None:
            news2_scores.insert(0, news2_baseline)
            fecha_ingreso = parse_date(patient.get('fecha_ingreso'))
            if fecha_ingreso:
                news2_times_scored.insert(0, datetime.combine(fecha_ingreso, datetime.min.time()))
        
        news2_metrics = calculate_trend_analytics(news2_scores, news2_times_scored, 'news2')
        metrics.update(news2_metrics)
    
    # APACHE2
    apache2_baseline = safe_float(patient.get('apache2_ingreso'))
    if apache2_baseline:
        metrics['apache2_baseline'] = apache2_baseline
    
    # SAPS3
    saps3_baseline = safe_float(patient.get('saps3_ingreso'))
    if saps3_baseline:
        metrics['saps3_baseline'] = saps3_baseline
    
    # ============ BALANCE HÍDRICO ============
    balance_values, balance_times = extract_series(evolutions, 'balance')
    if balance_values:
        balance_metrics = calculate_trend_analytics(balance_values, balance_times, 'balance')
        metrics.update(balance_metrics)
        
        metrics['balance_total'] = round(sum(balance_values), 2)
        metrics['balance_positivo_dias'] = sum(1 for v in balance_values if v > 500)
    
    diuresis_values, diuresis_times = extract_series(evolutions, 'diuresis')
    if diuresis_values:
        diuresis_metrics = calculate_trend_analytics(diuresis_values, diuresis_times, 'diuresis')
        metrics.update(diuresis_metrics)
        
        metrics['diuresis_total'] = round(sum(diuresis_values), 2)
        metrics['diuresis_media'] = round(sum(diuresis_values) / len(diuresis_values), 2)
    
    # ============ NUTRICIÓN ============
    albumina_values, albumina_times = extract_series(evolutions, 'albumina')
    if albumina_values:
        albumina_metrics = calculate_trend_analytics(albumina_values, albumina_times, 'albumina')
        metrics.update(albumina_metrics)
    
    # Lactato/Albúmina ratio
    if lact_values and albumina_values:
        lar = calculate_lactate_albumin_ratio(lact_values, albumina_values)
        if lar:
            metrics['lactato_albumina_ratio'] = lar['ratio']
            metrics['lactato_albumina_high_risk'] = lar['high_risk']
    
    # ============ DISPOSITIVOS ============
    for dispositivo in ['cateter_cvc', 'sonda_urinaria', 'tubo_endotraqueal', 'traqueostomia', 
                         'cateter_hemodialisis', 'linea_arterial', 'gastrostomia']:
        dias_field = f'dias_{dispositivo.replace("cateter_", "").replace("sonda_", "").replace("tubo_endotraqueal", "ett")}'
        dias_values, _ = extract_series(evolutions, dias_field)
        if dias_values:
            metrics[f'{dias_field}_max'] = max(dias_values)
    
    # ============ VASOPRESORES ============
    vasopresor_values, vasopresor_times = extract_series(evolutions, 'vasopresores')
    if vasopresor_values:
        vaso_metrics = calculate_trend_analytics(vasopresor_values, vasopresor_times, 'vasopresores')
        metrics.update(vaso_metrics)
    
    norad_values, norad_times = extract_series(evolutions, 'noradrenalina')
    if norad_values:
        norad_metrics = calculate_trend_analytics(norad_values, norad_times, 'noradrenalina')
        metrics.update(norad_metrics)
    
    # ============ ANTIBIÓTICOS ============
    antibioticos_dias = sum(1 for evo in evolutions if evo.get('antibiotico'))
    metrics['antibioticos_dias'] = antibioticos_dias
    
    # ============ OUTCOMES (si existen) ============
    if patient.get('fecha_egreso_uci'):
        metrics['icu_los'] = dias_estancia
    if patient.get('fecha_egreso_hospital'):
        hospital_ingreso = parse_date(patient.get('fecha_ingreso'))
        hospital_egreso = parse_date(patient.get('fecha_egreso_hospital'))
        if hospital_ingreso and hospital_egreso:
            metrics['hospital_los'] = (hospital_egreso - hospital_ingreso).days
    
    # ============ COMPLEJIDAD ============
    total_evo = len(evolutions)
    evo_por_dia = metrics.get('evoluciones_por_dia', 0)
    
    # Score de complejidad (0-100)
    complexity_score = 0
    if dias_estancia > 14: complexity_score += 30
    elif dias_estancia > 7: complexity_score += 20
    elif dias_estancia > 3: complexity_score += 10
    else: complexity_score += 5
    
    if evo_por_dia > 2: complexity_score += 25
    elif evo_por_dia > 1: complexity_score += 15
    elif evo_por_dia > 0.5: complexity_score += 10
    else: complexity_score += 5
    
    # Factor: número total de evoluciones
    if total_evo > 30: complexity_score += 10
    elif total_evo > 15: complexity_score += 7
    elif total_evo > 7: complexity_score += 5
    else: complexity_score += 3
    
    # Factor: datos de ingreso completos
    ingreso_fields = ['fecha_ingreso_uci', 'diagnostico_ingreso', 'glasgow_ingreso', 'fc_ingreso', 'tam_ingreso', 'fr_ingreso']
    ingreso_filled = sum(1 for f in ingreso_fields if patient.get(f))
    ingreso_pct = (ingreso_filled / len(ingreso_fields)) * 100
    if ingreso_pct >= 80: complexity_score += 15
    elif ingreso_pct >= 50: complexity_score += 10
    else: complexity_score += 5
    
    # Normalizar a 0-100
    max_score = 30 + 25 + 10 + 15  # = 80
    complexity_score = min(100, round((complexity_score / max_score) * 100))
    
    # Nivel de complejidad
    complexity_level = 'Baja'
    if complexity_score >= 70: complexity_level = 'Alta'
    elif complexity_score >= 40: complexity_level = 'Media'
    
    metrics['complexity_score'] = complexity_score
    metrics['complexity_level'] = complexity_level
    
    # ============ BOOLEANOS CLÍNICOS ============
    # LRA (Lesión Renal Aguda)
    creat_max = metrics.get('creatinina_max', 0)
    diuresis_min = metrics.get('diuresis_min', 9999)
    metrics['lra_detected'] = bool(creat_max > 1.5 or (diuresis_min < 400 and diuresis_min > 0))
    
    # Sepsis (basado en NEWS2 elevado + lactato alto)
    news2_max = metrics.get('news2_max', 0)
    lact_max = metrics.get('lactato_max', 0)
    metrics['sepsis_detected'] = bool(news2_max >= 7 or lact_max > 4)
    
    # Choque (índice de choque > 0.9 o PAM < 65)
    si_max = metrics.get('shock_index_max', 0)
    pam_min = metrics.get('pam_min', 999)
    metrics['shock_detected'] = bool(si_max > 0.9 or pam_min < 65)
    
    # SDRA (PaFi < 300)
    pafi_min = metrics.get('pafi_min', 999)
    metrics['sdr_detected'] = bool(pafi_min < 300 and pafi_min > 0)
    
    # VM (días de ventilación > 0)
    vm_dias = metrics.get('ventilador_dias', 0)
    metrics['vm_required'] = bool(vm_dias > 0)
    
    # Coma (Glasgow <= 8)
    glasgow_min = metrics.get('glasgow_min', 15)
    metrics['coma_detected'] = bool(glasgow_min <= 8)
    
    # Hiperlactatemia (lactato > 4)
    metrics['hyperlactatemia'] = bool(lact_max > 4)
    
    # Coagulopatía (plaquetas < 100 o INR > 1.5)
    plaq_nadir = metrics.get('plaquetas_min', 999)
    inr_max = metrics.get('inr_max', 0)
    metrics['coagulopathy'] = bool(plaq_nadir < 100 or inr_max > 1.5)
    
    # Vasopresor requerido (PAM < 60 o uso de vasopresores)
    vaso_max = metrics.get('vasopresores_max', 0)
    metrics['vasopressor_required'] = bool(pam_min < 60 or vaso_max > 0)
    
    return metrics

# ============================================================================
# FUNCIONES PARA GUARDAR EN BASE DE DATOS
# ============================================================================

def save_analytics(patient_id, metrics, compliance_data=None, db_url=DATABASE_URL):
    """
    Guarda métricas calculadas en la tabla clinical_analytics.
    Usa JSONB para almacenar todas las métricas de forma flexible.
    """
    import psycopg2
    import json
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existe registro
        cursor.execute("SELECT id FROM clinical_analytics WHERE patient_id = %s", (patient_id,))
        existing = cursor.fetchone()
        
        if compliance_data:
            metrics['compliance_ingreso'] = compliance_data.get('ingreso_compliance')
            metrics['compliance_evoluciones'] = compliance_data.get('evolution_compliance')
            metrics['coverage_evoluciones'] = compliance_data.get('evolution_coverage')
            metrics['compliance_overall'] = compliance_data.get('overall_score')
            metrics['compliance_label'] = compliance_data.get('label')
        
        # Preparar JSON con todas las métricas (convertir valores serializables)
        metrics_json = {}
        for key, val in metrics.items():
            if val is not None:
                if hasattr(val, 'isoformat'):
                    metrics_json[key] = val.isoformat()
                elif isinstance(val, bool):
                    metrics_json[key] = val
                elif isinstance(val, (int, float)):
                    metrics_json[key] = val
                else:
                    metrics_json[key] = str(val)
        
        # Extraer métricas clave para columnas individuales (para indexación/búsquedas)
        key_metrics = {}
        key_fields = [
            'dias_estancia', 'total_evoluciones', 'evoluciones_por_dia',
            'sofa_max', 'sofa_delta', 'sofa_auc',
            'news2_max', 'news2_delta',
            'lactato_max', 'creatinina_max',
            'pam_min', 'fc_max', 'spo2_min',
            'shock_index_max',
            'compliance_overall', 'compliance_label',
            # Nuevos campos de complejidad y booleanos clínicos
            'complexity_score', 'complexity_level',
            'lra_detected', 'sepsis_detected', 'shock_detected',
            'sdr_detected', 'vm_required', 'coma_detected',
            'hyperlactatemia', 'coagulopathy', 'vasopressor_required'
        ]
        for field in key_fields:
            if field in metrics and metrics[field] is not None:
                key_metrics[field] = metrics[field]
        
        if existing:
            # Actualizar registro existente
            update_fields = []
            values = []
            for key, val in key_metrics.items():
                update_fields.append(f"{key} = %s")
                values.append(val)
            
            # Agregar JSON
            update_fields.append("metrics_json = %s")
            values.append(json.dumps(metrics_json))
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_fields.append("last_calc_at = CURRENT_TIMESTAMP")
            values.append(patient_id)
            
            sql = f"UPDATE clinical_analytics SET {', '.join(update_fields)} WHERE patient_id = %s"
            cursor.execute(sql, values)
        else:
            # Insertar nuevo registro
            fields = ['patient_id', 'metrics_json']
            placeholders = ['%s', '%s']
            values = [patient_id, json.dumps(metrics_json)]
            
            for key, val in key_metrics.items():
                fields.append(key)
                placeholders.append('%s')
                values.append(val)
            
            sql = f"INSERT INTO clinical_analytics ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(sql, values)
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error guardando analytics: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_analytics(patient_id, db_url=DATABASE_URL):
    """
    Recupera métricas analíticas de un paciente.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT * FROM clinical_analytics WHERE patient_id = %s", (patient_id,))
        result = cursor.fetchone()
        if result and result.get("metrics_json"):
            # Expandir JSON
            merged = dict(result)
            json_data = result.get("metrics_json")
            if json_data:
                if isinstance(json_data, str):
                    import json
                    json_data = json.loads(json_data)
                merged.update(json_data)
            return dict(merged)
        return dict(result) if result else None
    except Exception as e:
        print(f"Error recuperando analytics: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def recalculate_all_analytics():
    """
    Recalcula métricas para TODOS los pacientes.
    """
    import sys
    sys.path.insert(0, '/home/xiu/dogma/sinapsid-dma-auth')
    from modules.database import get_all_patients, get_evolutions
    
    patients = get_all_patients()
    total = len(patients)
    updated = 0
    
    print(f"Recalculando analytics para {total} pacientes...")
    
    for i, patient in enumerate(patients, 1):
        patient_id = patient.get('id')
        if not patient_id:
            continue
        
        try:
            evolutions = get_evolutions(patient_id)
            metrics = calculate_advanced_metrics(patient, evolutions)
            
            # Calcular compliance
            from app import calculate_patient_compliance
            compliance = calculate_patient_compliance(patient_id)
            
            save_analytics(patient_id, metrics, compliance)
            updated += 1
            
            if i % 10 == 0:
                print(f"  Progreso: {i}/{total} ({updated} actualizados)")
        
        except Exception as e:
            print(f"  Error en paciente {patient_id}: {e}")
    
    print(f"✅ Analytics actualizados: {updated}/{total}")
    return updated

if __name__ == '__main__':
    print("🦞 Recalculando todas las métricas avanzadas...")
    recalculate_all_analytics()
