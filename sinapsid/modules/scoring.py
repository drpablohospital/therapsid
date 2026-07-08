"""
Módulo de cálculo de escalas pronósticas para medicina crítica.

Cascada de datos:
1. Datos de la evolución actual (prioridad máxima)
2. Datos de la evolución de ingreso / primera evolución
3. Valores normales por defecto (fallback seguro)
"""

import math
from typing import Dict, Any, Optional, List

# Valores normales por defecto
VALORES_NORMALES = {
    'temperatura': 37.0,
    'fc': 80,
    'fr': 16,
    'pam': 80,
    'pas': 110,
    'pad': 70,
    'spo2': 98,
    'fio2': 21,
    'pafi': 460,
    'glasgow': 15,
    'rass': 0,
    'creatinina': 1.0,
    'sodio': 140,
    'potasio': 4.0,
    'leucocitos': 7.5,
    'plaquetas': 250,
    'hemoglobina': 14.0,
    'hematocrito': 42.0,
    'bilirrubina_total': 0.8,
    'bilirrubina_directa': 0.3,
    'ph': 7.40,
    'urea': 25,
    'glucosa': 90,
    'pco2': 40,
    'hco3': 24,
}


def obtener_dato_cascada(nombre_campo: str, evolucion_actual: Optional[Dict], 
                          evolucion_ingreso: Optional[Dict]) -> Any:
    """
    Obtiene un dato siguiendo la cascada:
    1. Evolución actual
    2. Evolución de ingreso
    3. Valor normal por defecto
    """
    # 1. Intentar evolución actual
    if evolucion_actual:
        valor = evolucion_actual.get(nombre_campo)
        if valor is not None and str(valor).strip() != '':
            try:
                if isinstance(VALORES_NORMALES.get(nombre_campo), int):
                    return int(valor)
                else:
                    return float(valor)
            except (ValueError, TypeError):
                pass
    
    # 2. Intentar evolución de ingreso
    if evolucion_ingreso:
        valor = evolucion_ingreso.get(nombre_campo)
        if valor is not None and str(valor).strip() != '':
            try:
                if isinstance(VALORES_NORMALES.get(nombre_campo), int):
                    return int(valor)
                else:
                    return float(valor)
            except (ValueError, TypeError):
                pass
    
    # 3. Valor normal por defecto
    return VALORES_NORMALES.get(nombre_campo)


def calcular_news2(evolucion_actual: Optional[Dict] = None, 
                   evolucion_ingreso: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Calcula NEWS2 (National Early Warning Score 2)
    Rango: 0-20
    Riesgo bajo: 0-4
    Riesgo moderado: 5-6
    Riesgo alto: ≥7
    """
    datos = {
        'fc': obtener_dato_cascada('fc', evolucion_actual, evolucion_ingreso),
        'spo2': obtener_dato_cascada('spo2', evolucion_actual, evolucion_ingreso),
        'fio2': obtener_dato_cascada('fio2', evolucion_actual, evolucion_ingreso),
        'temperatura': obtener_dato_cascada('temperatura', evolucion_actual, evolucion_ingreso),
        'pam': obtener_dato_cascada('pam', evolucion_actual, evolucion_ingreso),
        'pas': obtener_dato_cascada('pas', evolucion_actual, evolucion_ingreso),
        'fr': obtener_dato_cascada('fr', evolucion_actual, evolucion_ingreso),
        'glasgow': obtener_dato_cascada('glasgow', evolucion_actual, evolucion_ingreso),
    }
    
    score = 0
    componentes = {}
    
    # FC
    fc = datos['fc']
    if fc is not None:
        if fc <= 40:
            score += 3
            componentes['fc'] = {'valor': fc, 'puntos': 3, 'texto': 'FC ≤40'}
        elif fc <= 50:
            score += 1
            componentes['fc'] = {'valor': fc, 'puntos': 1, 'texto': 'FC 41-50'}
        elif fc <= 90:
            componentes['fc'] = {'valor': fc, 'puntos': 0, 'texto': 'FC 51-90'}
        elif fc <= 110:
            score += 1
            componentes['fc'] = {'valor': fc, 'puntos': 1, 'texto': 'FC 91-110'}
        elif fc <= 130:
            score += 2
            componentes['fc'] = {'valor': fc, 'puntos': 2, 'texto': 'FC 111-130'}
        else:
            score += 3
            componentes['fc'] = {'valor': fc, 'puntos': 3, 'texto': 'FC ≥131'}
    
    # SpO2
    spo2 = datos['spo2']
    if spo2 is not None:
        if spo2 <= 91:
            score += 3
            componentes['spo2'] = {'valor': spo2, 'puntos': 3, 'texto': 'SpO2 ≤91%'}
        elif spo2 <= 93:
            score += 2
            componentes['spo2'] = {'valor': spo2, 'puntos': 2, 'texto': 'SpO2 92-93%'}
        elif spo2 <= 95:
            score += 1
            componentes['spo2'] = {'valor': spo2, 'puntos': 1, 'texto': 'SpO2 94-95%'}
        else:
            componentes['spo2'] = {'valor': spo2, 'puntos': 0, 'texto': 'SpO2 ≥96%'}
    
    # Aire/O2
    fio2 = datos['fio2']
    if fio2 is not None and fio2 > 21:
        score += 2
        componentes['oxigeno'] = {'valor': fio2, 'puntos': 2, 'texto': 'En O2 suplementario'}
    else:
        componentes['oxigeno'] = {'valor': fio2, 'puntos': 0, 'texto': 'Aire ambiental'}
    
    # Temperatura
    temp = datos['temperatura']
    if temp is not None:
        if temp <= 35.0:
            score += 3
            componentes['temperatura'] = {'valor': temp, 'puntos': 3, 'texto': 'Temp ≤35.0°C'}
        elif temp <= 36.0:
            score += 1
            componentes['temperatura'] = {'valor': temp, 'puntos': 1, 'texto': 'Temp 35.1-36.0°C'}
        elif temp <= 38.0:
            componentes['temperatura'] = {'valor': temp, 'puntos': 0, 'texto': 'Temp 36.1-38.0°C'}
        elif temp <= 39.0:
            score += 1
            componentes['temperatura'] = {'valor': temp, 'puntos': 1, 'texto': 'Temp 38.1-39.0°C'}
        else:
            score += 2
            componentes['temperatura'] = {'valor': temp, 'puntos': 2, 'texto': 'Temp ≥39.1°C'}
    
    # PAM
    pam = datos['pam']
    pas = datos['pas']
    if pam is not None:
        if pam <= 70:
            score += 3
            componentes['pam'] = {'valor': pam, 'puntos': 3, 'texto': 'PAM ≤70'}
        elif pam <= 90:
            score += 2
            componentes['pam'] = {'valor': pam, 'puntos': 2, 'texto': 'PAM 71-90'}
        elif pam <= 100:
            score += 1
            componentes['pam'] = {'valor': pam, 'puntos': 1, 'texto': 'PAM 91-100'}
        elif pas is not None and pas >= 220:
            score += 3
            componentes['pam'] = {'valor': pas, 'puntos': 3, 'texto': 'PAS ≥220'}
        else:
            componentes['pam'] = {'valor': pam, 'puntos': 0, 'texto': 'PAM 101-219'}
    
    # FR
    fr = datos['fr']
    if fr is not None:
        if fr <= 8:
            score += 3
            componentes['fr'] = {'valor': fr, 'puntos': 3, 'texto': 'FR ≤8'}
        elif fr <= 11:
            score += 1
            componentes['fr'] = {'valor': fr, 'puntos': 1, 'texto': 'FR 9-11'}
        elif fr <= 20:
            componentes['fr'] = {'valor': fr, 'puntos': 0, 'texto': 'FR 12-20'}
        elif fr <= 24:
            score += 2
            componentes['fr'] = {'valor': fr, 'puntos': 2, 'texto': 'FR 21-24'}
        else:
            score += 3
            componentes['fr'] = {'valor': fr, 'puntos': 3, 'texto': 'FR ≥25'}
    
    # GCS (Conciencia)
    gcs = datos['glasgow']
    if gcs is not None:
        if gcs < 15:
            score += 3
            componentes['conciencia'] = {'valor': gcs, 'puntos': 3, 'texto': f'GCS {gcs} (alterado)'}
        else:
            componentes['conciencia'] = {'valor': gcs, 'puntos': 0, 'texto': 'GCS 15 (alerta)'}
    
    # Interpretación
    if score <= 4:
        riesgo = 'Bajo'
        accion = 'Monitoreo estándar'
    elif score <= 6:
        riesgo = 'Moderado'
        accion = 'Evaluación por médico urgente'
    else:
        riesgo = 'Alto'
        accion = 'Respuesta de emergencia inmediata'
    
    return {
        'escala': 'NEWS2',
        'score': score,
        'riesgo': riesgo,
        'accion': accion,
        'componentes': componentes,
        'maximo': 20
    }


def calcular_qsofa(evolucion_actual: Optional[Dict] = None, 
                   evolucion_ingreso: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Calcula qSOFA (quick SOFA)
    Rango: 0-3
    Sepsis sospechada: ≥2 puntos
    """
    datos = {
        'fr': obtener_dato_cascada('fr', evolucion_actual, evolucion_ingreso),
        'glasgow': obtener_dato_cascada('glasgow', evolucion_actual, evolucion_ingreso),
        'pas': obtener_dato_cascada('pas', evolucion_actual, evolucion_ingreso),
    }
    
    score = 0
    componentes = {}
    
    # FR ≥22
    fr = datos['fr']
    if fr is not None and fr >= 22:
        score += 1
        componentes['fr'] = {'valor': fr, 'puntos': 1, 'texto': f'FR {fr}/min (≥22)'}
    else:
        componentes['fr'] = {'valor': fr, 'puntos': 0, 'texto': f'FR {fr}/min (<22)'}
    
    # GCS alterado <15
    gcs = datos['glasgow']
    if gcs is not None and gcs < 15:
        score += 1
        componentes['glasgow'] = {'valor': gcs, 'puntos': 1, 'texto': f'GCS {gcs} (<15)'}
    else:
        componentes['glasgow'] = {'valor': gcs, 'puntos': 0, 'texto': f'GCS {gcs} (normal)'}
    
    # PAS ≤100
    pas = datos['pas']
    if pas is not None and pas <= 100:
        score += 1
        componentes['pas'] = {'valor': pas, 'puntos': 1, 'texto': f'PAS {pas} mmHg (≤100)'}
    else:
        componentes['pas'] = {'valor': pas, 'puntos': 0, 'texto': f'PAS {pas} mmHg (>100)'}
    
    # Interpretación
    if score >= 2:
        riesgo = 'Sepsis sospechada'
        accion = 'Evaluar SOFA completo, cultivos, antibióticos'
    else:
        riesgo = 'Bajo riesgo de sepsis'
        accion = 'Monitoreo continuo'
    
    return {
        'escala': 'qSOFA',
        'score': score,
        'riesgo': riesgo,
        'accion': accion,
        'componentes': componentes,
        'maximo': 3
    }


def calcular_sofa(evolucion_actual: Optional[Dict] = None, 
                  evolucion_ingreso: Optional[Dict] = None,
                  datos_paciente: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Calcula SOFA (Sequential Organ Failure Assessment)
    Rango: 0-24
    Requiere: PaO2/FiO2, plaquetas, bilirrubina, MAP, vasopresores, creatinina, GCS
    """
    datos = {
        'pafi': obtener_dato_cascada('pafi', evolucion_actual, evolucion_ingreso),
        'spo2': obtener_dato_cascada('spo2', evolucion_actual, evolucion_ingreso),
        'fio2': obtener_dato_cascada('fio2', evolucion_actual, evolucion_ingreso),
        'po2': obtener_dato_cascada('po2', evolucion_actual, evolucion_ingreso),
        'plaquetas': obtener_dato_cascada('plaquetas', evolucion_actual, evolucion_ingreso),
        'bilirrubina_total': obtener_dato_cascada('bilirrubina_total', evolucion_actual, evolucion_ingreso),
        'pam': obtener_dato_cascada('pam', evolucion_actual, evolucion_ingreso),
        'vasopresores': evolucion_actual.get('vasopresores') if evolucion_actual else None,
        'creatinina': obtener_dato_cascada('creatinina', evolucion_actual, evolucion_ingreso),
        'diuresis': obtener_dato_cascada('diuresis', evolucion_actual, evolucion_ingreso),
        'glasgow': obtener_dato_cascada('glasgow', evolucion_actual, evolucion_ingreso),
    }
    
    # Si no hay PA/FiO2 pero hay PO2 y FiO2, calcularlo
    if datos['pafi'] is None and datos['po2'] is not None and datos['fio2'] is not None and datos['fio2'] > 0:
        datos['pafi'] = datos['po2'] / datos['fio2']
    
    score = 0
    componentes = {}
    
    # Respiratorio (PaO2/FiO2)
    pafi = datos['pafi']
    if pafi is not None:
        if pafi > 400:
            componentes['respiratorio'] = {'valor': round(pafi, 1), 'puntos': 0, 'texto': f'Pa/Fi {pafi:.0f} (>400)'}
        elif pafi > 300:
            score += 1
            componentes['respiratorio'] = {'valor': round(pafi, 1), 'puntos': 1, 'texto': f'Pa/Fi {pafi:.0f} (≤400)'}
        elif pafi > 200:
            score += 2
            componentes['respiratorio'] = {'valor': round(pafi, 1), 'puntos': 2, 'texto': f'Pa/Fi {pafi:.0f} (≤300)'}
        elif pafi > 100:
            score += 3
            componentes['respiratorio'] = {'valor': round(pafi, 1), 'puntos': 3, 'texto': f'Pa/Fi {pafi:.0f} (≤200 + VM)'}
        else:
            score += 4
            componentes['respiratorio'] = {'valor': round(pafi, 1), 'puntos': 4, 'texto': f'Pa/Fi {pafi:.0f} (≤100 + VM)'}
    
    # Coagulación (Plaquetas)
    plt = datos['plaquetas']
    if plt is not None:
        if plt > 150:
            componentes['coagulacion'] = {'valor': plt, 'puntos': 0, 'texto': f'PLT {plt} (>150K)'}
        elif plt > 100:
            score += 1
            componentes['coagulacion'] = {'valor': plt, 'puntos': 1, 'texto': f'PLT {plt} (≤150K)'}
        elif plt > 50:
            score += 2
            componentes['coagulacion'] = {'valor': plt, 'puntos': 2, 'texto': f'PLT {plt} (≤100K)'}
        elif plt > 20:
            score += 3
            componentes['coagulacion'] = {'valor': plt, 'puntos': 3, 'texto': f'PLT {plt} (≤50K)'}
        else:
            score += 4
            componentes['coagulacion'] = {'valor': plt, 'puntos': 4, 'texto': f'PLT {plt} (≤20K)'}
    
    # Hepático (Bilirrubina)
    bili = datos['bilirrubina_total']
    if bili is not None:
        if bili < 1.2:
            componentes['hepatico'] = {'valor': bili, 'puntos': 0, 'texto': f'Bili {bili} (<1.2)'}
        elif bili < 2.0:
            score += 1
            componentes['hepatico'] = {'valor': bili, 'puntos': 1, 'texto': f'Bili {bili} (1.2-1.9)'}
        elif bili < 6.0:
            score += 2
            componentes['hepatico'] = {'valor': bili, 'puntos': 2, 'texto': f'Bili {bili} (2.0-5.9)'}
        elif bili < 12.0:
            score += 3
            componentes['hepatico'] = {'valor': bili, 'puntos': 3, 'texto': f'Bili {bili} (6.0-11.9)'}
        else:
            score += 4
            componentes['hepatico'] = {'valor': bili, 'puntos': 4, 'texto': f'Bili {bili} (≥12.0)'}
    
    # Cardiovascular (PAM + vasopresores)
    pam = datos['pam']
    vasopresores = datos['vasopresores']
    
    # Parsear vasopresores del texto
    vasopresor_dosis = None
    vasopresor_tipo = None
    if vasopresores:
        texto_vaso = str(vasopresores).lower()
        if 'dopamina' in texto_vaso:
            vasopresor_tipo = 'dopamina'
            # Buscar dosis en mcg/kg/min
            import re
            match = re.search(r'(\d+\.?\d*)\s*mcg', texto_vaso)
            if match:
                vasopresor_dosis = float(match.group(1))
        elif 'nor' in texto_vaso or 'norepinefrina' in texto_vaso:
            vasopresor_tipo = 'norepinefrina'
            match = re.search(r'(\d+\.?\d*)\s*mcg', texto_vaso)
            if match:
                vasopresor_dosis = float(match.group(1))
    
    if vasopresor_tipo == 'dopamina' and vasopresor_dosis is not None:
        if vasopresor_dosis > 15:
            score += 4
            componentes['cardiovascular'] = {'valor': vasopresores, 'puntos': 4, 'texto': f'Dopamina >15 mcg/kg/min'}
        elif vasopresor_dosis > 5:
            score += 3
            componentes['cardiovascular'] = {'valor': vasopresores, 'puntos': 3, 'texto': f'Dopamina >5 mcg/kg/min'}
        else:
            score += 2
            componentes['cardiovascular'] = {'valor': vasopresores, 'puntos': 2, 'texto': f'Dopamina ≤5 mcg/kg/min'}
    elif vasopresor_tipo == 'norepinefrina':
        score += 3
        componentes['cardiovascular'] = {'valor': vasopresores, 'puntos': 3, 'texto': f'Norepinefrina activa'}
    elif pam is not None:
        if pam < 70:
            score += 1
            componentes['cardiovascular'] = {'valor': pam, 'puntos': 1, 'texto': f'PAM {pam} (<70)'}
        else:
            componentes['cardiovascular'] = {'valor': pam, 'puntos': 0, 'texto': f'PAM {pam} (≥70)'}
    
    # Renal (Creatinina o diuresis)
    crea = datos['creatinina']
    diuresis = datos['diuresis']
    
    if crea is not None:
        if crea < 1.2:
            componentes['renal'] = {'valor': crea, 'puntos': 0, 'texto': f'Cr {crea} (<1.2)'}
        elif crea < 2.0:
            score += 1
            componentes['renal'] = {'valor': crea, 'puntos': 1, 'texto': f'Cr {crea} (1.2-1.9)'}
        elif crea < 3.5:
            score += 2
            componentes['renal'] = {'valor': crea, 'puntos': 2, 'texto': f'Cr {crea} (2.0-3.4)'}
        elif crea < 5.0:
            score += 3
            componentes['renal'] = {'valor': crea, 'puntos': 3, 'texto': f'Cr {crea} (3.5-4.9)'}
        else:
            score += 4
            componentes['renal'] = {'valor': crea, 'puntos': 4, 'texto': f'Cr {crea} (≥5.0)'}
    elif diuresis is not None and diuresis < 500:
        score += 3
        componentes['renal'] = {'valor': diuresis, 'puntos': 3, 'texto': f'Diuresis {diuresis}mL (<500/día)'}
    
    # Neurológico (GCS)
    gcs = datos['glasgow']
    if gcs is not None:
        if gcs == 15:
            componentes['neurologico'] = {'valor': gcs, 'puntos': 0, 'texto': f'GCS {gcs}'}
        elif gcs >= 13:
            score += 1
            componentes['neurologico'] = {'valor': gcs, 'puntos': 1, 'texto': f'GCS {gcs}'}
        elif gcs >= 10:
            score += 2
            componentes['neurologico'] = {'valor': gcs, 'puntos': 2, 'texto': f'GCS {gcs}'}
        elif gcs >= 6:
            score += 3
            componentes['neurologico'] = {'valor': gcs, 'puntos': 3, 'texto': f'GCS {gcs}'}
        else:
            score += 4
            componentes['neurologico'] = {'valor': gcs, 'puntos': 4, 'texto': f'GCS {gcs}'}
    
    # Interpretación
    if score == 0:
        riesgo = 'Sin fallo orgánico'
        accion = 'Monitoreo estándar'
    elif score <= 6:
        riesgo = 'Fallo orgánico leve-moderado'
        accion = 'Vigilancia intensiva'
    elif score <= 12:
        riesgo = 'Fallo orgánico moderado-grave'
        accion = 'Reevaluación frecuente, considerar UCI'
    else:
        riesgo = 'Fallo orgánico grave'
        accion = 'UCI obligatoria, alta mortalidad'
    
    # Mortalidad aproximada según SOFA
    if score <= 6:
        mortalidad = '<10%'
    elif score <= 9:
        mortalidad = '15-30%'
    elif score <= 12:
        mortalidad = '40-60%'
    else:
        mortalidad = '>80%'
    
    return {
        'escala': 'SOFA',
        'score': score,
        'riesgo': riesgo,
        'accion': accion,
        'mortalidad': mortalidad,
        'componentes': componentes,
        'maximo': 24
    }


def calcular_curb65(evolucion_actual: Optional[Dict] = None,
                   evolucion_ingreso: Optional[Dict] = None,
                   edad: int = None) -> Dict[str, Any]:
    """
    Calcula CURB-65 (Neumonía)
    Rango: 0-5
    """
    datos = {
        'glasgow': obtener_dato_cascada('glasgow', evolucion_actual, evolucion_ingreso),
        'urea': obtener_dato_cascada('urea', evolucion_actual, evolucion_ingreso),
        'fr': obtener_dato_cascada('fr', evolucion_actual, evolucion_ingreso),
        'pas': obtener_dato_cascada('pas', evolucion_actual, evolucion_ingreso),
        'pad': obtener_dato_cascada('pad', evolucion_actual, evolucion_ingreso),
    }
    
    score = 0
    componentes = {}
    
    # Confusión (GCS < 15)
    gcs = datos['glasgow']
    if gcs is not None and gcs < 15:
        score += 1
        componentes['confusion'] = {'valor': gcs, 'puntos': 1, 'texto': f'GCS {gcs} (confusión)'}
    else:
        componentes['confusion'] = {'valor': gcs, 'puntos': 0, 'texto': 'Sin confusión'}
    
    # Urea >20 mg/dL (7 mmol/L ≈ 20 mg/dL)
    urea = datos['urea']
    if urea is not None and urea > 20:
        score += 1
        componentes['urea'] = {'valor': urea, 'puntos': 1, 'texto': f'Urea {urea} >20 mg/dL'}
    else:
        componentes['urea'] = {'valor': urea, 'puntos': 0, 'texto': f'Urea {urea} mg/dL'}
    
    # FR ≥30
    fr = datos['fr']
    if fr is not None and fr >= 30:
        score += 1
        componentes['fr'] = {'valor': fr, 'puntos': 1, 'texto': f'FR {fr}/min (≥30)'}
    else:
        componentes['fr'] = {'valor': fr, 'puntos': 0, 'texto': f'FR {fr}/min (<30)'}
    
    # BP sistólica <90 o diastólica ≤60
    pas = datos['pas']
    pad = datos['pad']
    if (pas is not None and pas < 90) or (pad is not None and pad <= 60):
        score += 1
        componentes['bp'] = {'valor': f'{pas}/{pad}', 'puntos': 1, 'texto': f'PA {pas}/{pad} (hipotenso)'}
    else:
        componentes['bp'] = {'valor': f'{pas}/{pad}', 'puntos': 0, 'texto': f'PA {pas}/{pad} (normal)'}
    
    # Edad ≥65
    if edad is not None and edad >= 65:
        score += 1
        componentes['edad'] = {'valor': edad, 'puntos': 1, 'texto': f'Edad {edad} años (≥65)'}
    else:
        componentes['edad'] = {'valor': edad, 'puntos': 0, 'texto': f'Edad {edad} años (<65)'}
    
    # Interpretación
    if score == 0:
        riesgo = 'Riesgo bajo'
        accion = 'Tratamiento ambulatorio'
    elif score == 1:
        riesgo = 'Riesgo bajo-moderado'
        accion = 'Hospitalización corta u observación'
    elif score == 2:
        riesgo = 'Riesgo moderado'
        accion = 'Hospitalización'
    elif score == 3:
        riesgo = 'Riesgo alto'
        accion = 'Hospitalización + posible UCI'
    else:
        riesgo = 'Riesgo muy alto'
        accion = 'Hospitalización inmediata, UCI'
    
    return {
        'escala': 'CURB-65',
        'score': score,
        'riesgo': riesgo,
        'accion': accion,
        'componentes': componentes,
        'maximo': 5
    }


def calcular_todas_las_escalas(evolucion_actual: Optional[Dict] = None,
                                evolucion_ingreso: Optional[Dict] = None,
                                datos_paciente: Optional[Dict] = None) -> Dict[str, Dict]:
    """
    Calcula todas las escalas disponibles y retorna un diccionario con los resultados.
    """
    edad = datos_paciente.get('edad') if datos_paciente else None
    
    resultados = {
        'news2': calcular_news2(evolucion_actual, evolucion_ingreso),
        'qsofa': calcular_qsofa(evolucion_actual, evolucion_ingreso),
        'sofa': calcular_sofa(evolucion_actual, evolucion_ingreso, datos_paciente),
        'curb65': calcular_curb65(evolucion_actual, evolucion_ingreso, edad),
    }
    
    return resultados


def obtener_estado_combinado(resultados: Dict[str, Dict]) -> str:
    """
    Genera un resumen del estado general del paciente basado en las escalas.
    """
    alertas = []
    
    if resultados['news2']['score'] >= 7:
        alertas.append(f"⚠️ NEWS2 alto ({resultados['news2']['score']})")
    
    if resultados['qsofa']['score'] >= 2:
        alertas.append(f"🚨 Sepsis sospechada (qSOFA {resultados['qsofa']['score']})")
    
    if resultados['sofa']['score'] >= 2:
        alertas.append(f"⚠️ Fallo orgánico (SOFA {resultados['sofa']['score']})")
    
    if resultados['curb65']['score'] >= 3:
        alertas.append(f"🏥 CURB-65 alto ({resultados['curb65']['score']})")
    
    if not alertas:
        return "✅ Estado estable"
    
    return " | ".join(alertas)
