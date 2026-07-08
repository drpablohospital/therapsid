"""
Validaciones de rangos clínicos para Sinapsid DMA
"""

from typing import Dict, List, Tuple, Optional

# Rangos válidos para campos clínicos
# Formato: (min, max, unidad, descripción)
VALIDATION_RANGES = {
    # Signos vitales
    'fc': (30, 220, 'lpm', 'Frecuencia cardíaca'),
    'fr': (4, 60, 'rpm', 'Frecuencia respiratoria'),
    'tas': (40, 300, 'mmHg', 'Tensión arterial sistólica'),
    'tad': (20, 200, 'mmHg', 'Tensión arterial diastólica'),
    'tam': (30, 250, 'mmHg', 'Tensión arterial media'),
    'temperatura': (32, 43, '°C', 'Temperatura corporal'),
    'spo2': (40, 100, '%', 'Saturación de oxígeno'),
    'fio2': (21, 100, '%', 'Fracción de oxígeno inspirado'),
    'glasgow': (3, 15, 'puntos', 'Escala de Glasgow'),
    'rass': (-5, 4, 'puntos', 'Escala RASS'),
    
    # Ventilación
    'vt_psinp': (50, 2000, 'ml', 'Volumen tidal'),
    'peep': (0, 25, 'cmH2O', 'PEEP'),
    'ppico': (5, 80, 'cmH2O', 'Presión pico'),
    'pplat': (5, 80, 'cmH2O', 'Presión plateau'),
    
    # Laboratorios
    'hemoglobina': (3, 20, 'g/dL', 'Hemoglobina'),
    'hematocrito': (10, 65, '%', 'Hematocrito'),
    'leucocitos': (0.5, 50, '×10³/μL', 'Leucocitos'),
    'neutrofilos': (0, 100, '%', 'Neutrófilos'),
    'linfocitos': (0, 100, '%', 'Linfocitos'),
    'plaquetas': (5, 1000, '×10³/μL', 'Plaquetas'),
    'glucosa': (20, 600, 'mg/dL', 'Glucosa'),
    'creatinina': (0.1, 20, 'mg/dL', 'Creatinina'),
    'urea': (5, 300, 'mg/dL', 'Urea'),
    'bun': (2, 150, 'mg/dL', 'BUN'),
    'sodio': (100, 180, 'mEq/L', 'Sodio'),
    'potasio': (2, 10, 'mEq/L', 'Potasio'),
    'cloro': (70, 140, 'mEq/L', 'Cloro'),
    'calcio': (4, 15, 'mg/dL', 'Calcio'),
    'magnesio': (0.5, 5, 'mg/dL', 'Magnesio'),
    'fosforo': (1, 10, 'mg/dL', 'Fósforo'),
    'pcr': (0, 500, 'mg/L', 'PCR'),
    'pct': (0, 100, 'ng/mL', 'PCT'),
    'ph': (6.8, 7.8, 'pH', 'pH arterial'),
    'pco2': (10, 150, 'mmHg', 'pCO2'),
    'po2': (20, 600, 'mmHg', 'pO2'),
    'hco3': (5, 50, 'mEq/L', 'HCO3'),
    'lactato': (0.2, 30, 'mmol/L', 'Lactato'),
    
    # Balance de líquidos
    'ingresos': (0, 20000, 'ml', 'Ingresos'),
    'egresos': (0, 20000, 'ml', 'Egresos'),
    'diuresis': (0, 10000, 'ml', 'Diuresis'),
    'drenajes': (0, 5000, 'ml', 'Drenajes'),
    'balance': (-10000, 10000, 'ml', 'Balance'),
}


def validate_field(field_name: str, value) -> Tuple[bool, Optional[str]]:
    """
    Valida un campo contra su rango permitido.
    
    Args:
        field_name: Nombre del campo
        value: Valor a validar
        
    Returns:
        (is_valid, error_message)
    """
    if value is None or value == '':
        return True, None
    
    # Convertir a float si es posible
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return True, None  # No validar si no es numérico
    
    # Verificar si tenemos rango definido
    if field_name not in VALIDATION_RANGES:
        return True, None
    
    min_val, max_val, unit, description = VALIDATION_RANGES[field_name]
    
    if num_value < min_val:
        return False, f"{description} ({field_name}): {num_value} {unit} está por debajo del mínimo ({min_val} {unit})"
    
    if num_value > max_val:
        return False, f"{description} ({field_name}): {num_value} {unit} excede el máximo ({max_val} {unit})"
    
    return True, None


def validate_form_data(form_data: Dict) -> List[str]:
    """
    Valida todos los campos numéricos de un formulario.
    
    Args:
        form_data: Diccionario con datos del formulario
        
    Returns:
        Lista de mensajes de error (vacía si todo es válido)
    """
    errors = []
    
    for field_name, value in form_data.items():
        is_valid, error_msg = validate_field(field_name, value)
        if not is_valid:
            errors.append(error_msg)
    
    return errors


def validate_evolution_data(data: Dict) -> Dict:
    """
    Valida datos de evolución completa.
    
    Args:
        data: Diccionario con datos de evolución
        
    Returns:
        Dict con 'valid' (bool) y 'errors' (list)
    """
    errors = validate_form_data(data)
    
    # Validaciones cruzadas
    if 'tas' in data and 'tad' in data:
        tas = float(data.get('tas', 0) or 0)
        tad = float(data.get('tad', 0) or 0)
        if tas <= tad:
            errors.append("TAS debe ser mayor que TAD")
    
    if 'po2' in data and 'fio2' in data:
        po2 = float(data.get('po2', 0) or 0)
        fio2 = float(data.get('fio2', 0) or 0)
        if fio2 > 0 and po2 > 0:
            pafi = (po2 / fio2) * 100
            if pafi < 50:
                errors.append(f"PaFi calculado ({pafi:.0f}) es críticamente bajo")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
