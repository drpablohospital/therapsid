"""
SINAPSID DMA - Integración con Generador de Notas UCI
======================================================
Puente entre Sinapsid y el generador avanzado de notas UCI del Dr. Pablo.

Uso:
    from modules.uci_note_bridge import generar_nota_ingreso_uci
    nota = generar_nota_ingreso_uci(datos_paciente, datos_evolucion)
"""

import sys
import os
from typing import Dict, Optional

# Añadir path al generador de notas UCI
UCI_SKILL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              '..', 'skills', 'notas-uci-assistant')
sys.path.insert(0, UCI_SKILL_PATH)

try:
    from notas_uci_v2 import GeneradorNotasV2, parse_input_natural_v2
    GENERADOR_DISPONIBLE = True
except ImportError:
    GENERADOR_DISPONIBLE = False


def _convertir_paciente_a_datos_skill(patient_data: Dict) -> Dict:
    """
    Convierte datos de paciente Sinapsid al formato exacto que espera notas_uci_v2.py.
    Mapea todas las claves disponibles.
    """
    datos = {}
    
    # --- Datos demográficos ---
    datos['nombre'] = patient_data.get('nombre_completo', '')
    datos['edad'] = str(patient_data.get('edad', ''))
    datos['sexo'] = patient_data.get('sexo', 'MASCULINO')
    if datos['sexo'] == 'M':
        datos['sexo'] = 'MASCULINO'
    elif datos['sexo'] == 'F':
        datos['sexo'] = 'FEMENINO'
    datos['expediente'] = patient_data.get('expediente', '')
    datos['fecha_nacimiento'] = patient_data.get('fecha_nacimiento', '')
    datos['cama'] = patient_data.get('cama', 'N3')
    datos['servicio'] = patient_data.get('servicio_tratante', 'UCI')
    datos['fecha_ingreso_hospital'] = str(patient_data.get('fecha_ingreso', ''))
    datos['fecha_ingreso_uci'] = str(patient_data.get('fecha_ingreso', ''))
    datos['residencia'] = patient_data.get('residencia', 'SAN JUAN DEL RÍO')
    datos['escolaridad'] = patient_data.get('escolaridad', 'ESCOLARIDAD SECUNDARIA COMPLETA')
    datos['estado_civil'] = patient_data.get('estado_civil', '')
    datos['religion'] = patient_data.get('religion', 'SE CONSIDERA CREYENTE')
    datos['lateralidad'] = patient_data.get('lateralidad', 'DIESTRO')
    datos['empleo'] = patient_data.get('empleo', '')
    
    # --- Alergias ---
    alergias = patient_data.get('alergias', '')
    datos['alergias'] = alergias if alergias else 'NIEGA ALERGIAS CONOCIDAS'
    
    # --- APP ---
    datos['app'] = patient_data.get('app_cronicos', '') or patient_data.get('antecedentes_patologicos', '')
    datos['app_quirurgicos'] = patient_data.get('app_quirurgicos', '')
    datos['app_toxicos'] = patient_data.get('app_toxicos', '')
    datos['app_traumatologicos'] = patient_data.get('app_traumatologicos', '')
    datos['app_transfusionales'] = patient_data.get('app_transfusionales', '')
    datos['app_infectocontagiosos'] = patient_data.get('app_infectocontagiosos', '')
    
    # --- Gineco (si aplica) ---
    if datos['sexo'] == 'FEMENINO':
        datos['menarca'] = patient_data.get('menarca', '')
        datos['gesta'] = patient_data.get('gesta', '')
        datos['para'] = patient_data.get('para', '')
        datos['cesarea'] = patient_data.get('cesarea', '')
        datos['fum'] = patient_data.get('fum', '')
        datos['fuc'] = patient_data.get('fuc', '')
        datos['control_gestacional'] = patient_data.get('control_gestacional', '')
        datos['suplementos'] = patient_data.get('suplementos', '')
    
    # --- Signos vitales ---
    datos['signos_vitales'] = {
        'fc': patient_data.get('fc', 80),
        'fr': patient_data.get('fr', 16),
        'ta_sist': patient_data.get('tas', 120),
        'ta_diast': patient_data.get('tad', 80),
        'spo2': patient_data.get('sao2', '') or patient_data.get('spo2', 97),
        'fio2': patient_data.get('fio2', 21),
        'temp': patient_data.get('temperatura', 37.0),
        'glasgow': patient_data.get('glasgow', 15),
    }
    
    # --- Laboratorios ---
    datos['laboratorios'] = {
        'hb': patient_data.get('hemoglobina', ''),
        'hct': patient_data.get('hematocrito', ''),
        'leu': patient_data.get('leucocitos', ''),
        'plt': patient_data.get('plaquetas', ''),
        'pcr': patient_data.get('pcr', ''),
        'pct': patient_data.get('pct', ''),
        'na': patient_data.get('sodio', ''),
        'k': patient_data.get('potasio', ''),
        'cl': patient_data.get('cloro', ''),
        'crt': patient_data.get('creatinina', ''),
        'bun': patient_data.get('bun', ''),
        'glu': patient_data.get('glucosa_central', '') or patient_data.get('glucemia_capilar', '') or patient_data.get('glucosa', ''),
        'bt': patient_data.get('bilirrubina_total', ''),
        'bd': patient_data.get('bilirrubina_directa', ''),
        'bi': patient_data.get('bilirrubina_indirecta', ''),
        'alb': patient_data.get('albumina', ''),
        'ast': patient_data.get('ast', ''),
        'alt': patient_data.get('alt', ''),
        'dhl': patient_data.get('dhl', ''),
        'vsg': patient_data.get('vsg', ''),
        'tp': patient_data.get('tp', ''),
        'inr': patient_data.get('inr', ''),
        'ttp': patient_data.get('ttp', ''),
        'fibrinogeno': patient_data.get('fibrinogeno', ''),
        'dd': patient_data.get('dimero_d', ''),
        'ph': patient_data.get('gasometria_ph', ''),
        'pco2': patient_data.get('gasometria_pco2', ''),
        'po2': patient_data.get('gasometria_po2', ''),
        'hco3': patient_data.get('gasometria_hco3', ''),
        'lct': patient_data.get('gasometria_lactato', '') or patient_data.get('lactato', ''),
        'ca': patient_data.get('calcio', ''),
        'mg': patient_data.get('magnesio', ''),
        'p': patient_data.get('fosforo', ''),
        'bnp': patient_data.get('bnp', ''),
        'troponina': patient_data.get('troponina', ''),
        'amilasa': patient_data.get('amilasa', ''),
        'lipasa': patient_data.get('lipasa', ''),
        'fal': patient_data.get('fosfatasa_alcalina', ''),
        'linfocitos': patient_data.get('linfocitos', ''),
        'neutrofilos': patient_data.get('neutrofilos', ''),
    }
    
    # --- Ventilación ---
    modo_vent = patient_data.get('modo_ventilatorio', '')
    if modo_vent and modo_vent != 'Espontaneo':
        datos['ventilacion'] = {
            'modalidad': modo_vent,
            'vt': patient_data.get('vt_psinp', ''),
            'peep': patient_data.get('peep', ''),
            'pip': patient_data.get('ppico', ''),
            'fr': patient_data.get('fr_ventilador', '') or patient_data.get('fr', ''),
        }
    
    # --- Diagnósticos ---
    dx_ingreso = patient_data.get('diagnostico_ingreso', '')
    if dx_ingreso:
        datos['diagnosticos'] = [dx_ingreso]
        datos['padecimiento_actual'] = dx_ingreso
    else:
        datos['diagnosticos'] = ['PADECIMIENTO ACTUAL']
    
    # --- Plan y notas ---
    datos['plan'] = patient_data.get('plan_ingreso', '')
    datos['subjetivo'] = patient_data.get('subjetivo_ingreso', '')
    datos['exploracion_fisica'] = patient_data.get('exploracion_fisica_ingreso', '')
    datos['analisis'] = patient_data.get('analisis_ingreso', '')
    
    # --- Escores ---
    datos['news2'] = patient_data.get('news2_ingreso', '')
    datos['sofa'] = patient_data.get('sofa_ingreso', '')
    datos['apache2'] = patient_data.get('apache2_ingreso', '')
    datos['saps3'] = patient_data.get('saps3_ingreso', '')
    
    # --- Balance hídrico ---
    balance = patient_data.get('balance', '')
    if balance:
        datos['balance'] = str(balance)
    
    return datos


# Función original (mantenida por compatibilidad)
def _convertir_paciente_a_texto(patient_data: Dict) -> str:
    """Convierte datos de paciente Sinapsid a texto natural para el parser UCI."""
    partes = []
    
    sexo = patient_data.get('sexo', '')
    if sexo:
        partes.append('Mujer' if sexo == 'F' else 'Hombre' if sexo == 'M' else '')
    
    edad = patient_data.get('edad', '')
    if edad:
        partes.append(f"{edad} años")
    
    nombre = patient_data.get('nombre_completo', '')
    if nombre:
        partes.append(f"nombre {nombre}")
    
    # Signos vitales del ingreso
    fc = patient_data.get('fc', '')
    if fc:
        partes.append(f"FC {fc}")
    
    tas = patient_data.get('tas', '')
    tad = patient_data.get('tad', '')
    if tas and tad:
        partes.append(f"TA {tas}/{tad}")
    
    fr = patient_data.get('fr', '')
    if fr:
        partes.append(f"FR {fr}")
    
    spo2 = patient_data.get('sao2', '')
    if spo2:
        partes.append(f"SpO2 {spo2}%")
    
    fio2 = patient_data.get('fio2', '')
    if fio2:
        partes.append(f"FiO2 {fio2}%")
    
    glasgow = patient_data.get('glasgow', '')
    if glasgow:
        partes.append(f"Glasgow {glasgow}")
    
    # Laboratorios del ingreso
    hemoglobina = patient_data.get('hemoglobina', '')
    if hemoglobina:
        partes.append(f"HB {hemoglobina}")
    
    leucocitos = patient_data.get('leucocitos', '')
    if leucocitos:
        partes.append(f"LEU {leucocitos}")
    
    plaquetas = patient_data.get('plaquetas', '')
    if plaquetas:
        partes.append(f"PLT {plaquetas}")
    
    creatinina = patient_data.get('creatinina', '')
    if creatinina:
        partes.append(f"CRT {creatinina}")
    
    sodio = patient_data.get('sodio', '')
    if sodio:
        partes.append(f"NA {sodio}")
    
    potasio = patient_data.get('potasio', '')
    if potasio:
        partes.append(f"K {potasio}")
    
    glucosa = patient_data.get('glucemia_capilar', '') or patient_data.get('glucosa', '')
    if glucosa:
        partes.append(f"GLU {glucosa}")
    
    ph = patient_data.get('gasometria_ph', '')
    if ph:
        partes.append(f"pH {ph}")
    
    lactato = patient_data.get('gasometria_lactato', '')
    if lactato:
        partes.append(f"LCT {lactato}")
    
    # Diagnóstico
    diagnostico = patient_data.get('diagnostico_ingreso', '')
    if diagnostico:
        partes.append(diagnostico)
    
    # Ventilación
    modo_vent = patient_data.get('modo_ventilatorio', '')
    if modo_vent and modo_vent != 'Espontáneo':
        partes.append(f"VMI {modo_vent}")
    
    return ', '.join(filter(None, partes))


def generar_nota_ingreso_uci(patient_data: Dict, evolution_data: Optional[Dict] = None) -> str:
    """
    Genera nota de ingreso a UCI usando el generador avanzado.
    
    Args:
        patient_data: Datos del paciente desde Sinapsid
        evolution_data: Datos de evolución (opcional, para notas post-ingreso)
    
    Returns:
        str: Nota generada en formato del Dr. Pablo
    """
    if not GENERADOR_DISPONIBLE:
        return "ERROR: Generador UCI no disponible. Verificar instalación de skill notas-uci-assistant."
    
    try:
        # Usar nuevo mapeo completo en vez de texto natural
        datos_uci = _convertir_paciente_a_datos_skill(patient_data)
        
        # Si hay datos de evolución, enriquecer
        if evolution_data:
            # Actualizar signos vitales con evolución si hay datos más recientes
            sv = datos_uci.get('signos_vitales', {})
            if evolution_data.get('fc') and evolution_data.get('fc') != '':
                sv['fc'] = evolution_data.get('fc')
            if evolution_data.get('fr') and evolution_data.get('fr') != '':
                sv['fr'] = evolution_data.get('fr')
            if evolution_data.get('tas') and evolution_data.get('tad'):
                sv['ta_sist'] = evolution_data.get('tas')
                sv['ta_diast'] = evolution_data.get('tad')
            if evolution_data.get('sao2') and evolution_data.get('sao2') != '':
                sv['spo2'] = evolution_data.get('sao2')
            if evolution_data.get('fio2') and evolution_data.get('fio2') != '':
                sv['fio2'] = evolution_data.get('fio2')
            if evolution_data.get('temperatura') and evolution_data.get('temperatura') != '':
                sv['temp'] = evolution_data.get('temperatura')
            if evolution_data.get('glasgow') and evolution_data.get('glasgow') != '':
                sv['glasgow'] = evolution_data.get('glasgow')
            datos_uci['signos_vitales'] = sv
            
            # Actualizar laboratorios con evolución
            labs = datos_uci.get('laboratorios', {})
            if evolution_data.get('hemoglobina'): labs['hb'] = evolution_data.get('hemoglobina')
            if evolution_data.get('hematocrito'): labs['hct'] = evolution_data.get('hematocrito')
            if evolution_data.get('leucocitos'): labs['leu'] = evolution_data.get('leucocitos')
            if evolution_data.get('plaquetas'): labs['plt'] = evolution_data.get('plaquetas')
            if evolution_data.get('neutrofilos'): labs['neutrofilos'] = evolution_data.get('neutrofilos')
            if evolution_data.get('linfocitos'): labs['linfocitos'] = evolution_data.get('linfocitos')
            if evolution_data.get('creatinina'): labs['crt'] = evolution_data.get('creatinina')
            if evolution_data.get('bun'): labs['bun'] = evolution_data.get('bun')
            if evolution_data.get('sodio'): labs['na'] = evolution_data.get('sodio')
            if evolution_data.get('potasio'): labs['k'] = evolution_data.get('potasio')
            if evolution_data.get('cloro'): labs['cl'] = evolution_data.get('cloro')
            if evolution_data.get('glucosa'): labs['glu'] = evolution_data.get('glucosa')
            if evolution_data.get('ph'): labs['ph'] = evolution_data.get('ph')
            if evolution_data.get('lactato'): labs['lct'] = evolution_data.get('lactato')
            if evolution_data.get('bilirrubina_total'): labs['bt'] = evolution_data.get('bilirrubina_total')
            if evolution_data.get('bilirrubina_directa'): labs['bd'] = evolution_data.get('bilirrubina_directa')
            if evolution_data.get('albumina'): labs['alb'] = evolution_data.get('albumina')
            if evolution_data.get('pcr'): labs['pcr'] = evolution_data.get('pcr')
            if evolution_data.get('pct'): labs['pct'] = evolution_data.get('pct')
            datos_uci['laboratorios'] = labs
            
            # Notas de evolución
            if evolution_data.get('subjetivo'):
                datos_uci['subjetivo'] = evolution_data.get('subjetivo')
            if evolution_data.get('objetivo'):
                datos_uci['exploracion_fisica'] = evolution_data.get('objetivo')
            if evolution_data.get('analisis'):
                datos_uci['analisis'] = evolution_data.get('analisis')
            if evolution_data.get('plan_nota'):
                datos_uci['plan'] = evolution_data.get('plan_nota')
        
        # Generar nota
        generador = GeneradorNotasV2()
        nota = generador.generar_nota(datos_uci)
        
        return nota
        
    except Exception as e:
        import traceback
        return f"ERROR al generar nota UCI: {str(e)}\n\n{traceback.format_exc()}"


def generar_nota_evolucion_psoas(patient_data: Dict, evolution_data: Dict) -> str:
    """
    Genera nota de evolución PSOAP usando datos de Sinapsid.
    Esta es una versión mejorada del generador PSOAP actual.
    
    Args:
        patient_data: Datos del paciente
        evolution_data: Datos de la evolución
    
    Returns:
        str: Nota PSOAP generada
    """
    # Usar el generador de notas de evolución del servidor (ya implementado en app.py)
    # Este es un wrapper para compatibilidad
    
    # Preparar datos para el endpoint existente
    datos_formulario = {}
    for key, value in evolution_data.items():
        if value is not None:
            datos_formulario[key] = str(value)
    
    # Llamar al generador (simulado - en producción sería via API)
    # Por ahora, retornar placeholder que indica usar el botón del formulario
    return "Use el botón 'Generar Nota PSOAP' en el formulario de evolución para generar la nota automáticamente."


# ============================================================================
# Funciones de conveniencia
# ============================================================================

def disponible() -> bool:
    """Verifica si el generador UCI está disponible."""
    return GENERADOR_DISPONIBLE


def info() -> Dict:
    """Retorna información sobre la integración."""
    return {
        'disponible': GENERADOR_DISPONIBLE,
        'path_skill': UCI_SKILL_PATH,
        'version': '1.0.0',
        'notas_soportadas': ['ingreso_uci', 'evolucion_psoas']
    }
