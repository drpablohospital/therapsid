"""
SINAPSID DMA - Módulo de Cálculos Médicos
=========================================
Funciones de cálculo automático para el sistema clínico SINAPSID-DMA.
Basado en clinical_manager_audit.md - 23 funciones de cálculo.
"""

from datetime import datetime, date


# =============================================================================
# CÁLCULOS BÁSICOS (14 funciones)
# =============================================================================

def calc_edad(fecha_nac, fecha_ref=None):
    """
    Calcula la edad en años a partir de la fecha de nacimiento.
    
    Args:
        fecha_nac: Fecha de nacimiento (acepta "DD/MM/AAAA" o "YYYY-MM-DD")
        fecha_ref: Fecha de referencia (opcional, por defecto hoy)
    
    Returns:
        int: Edad en años, o None si hay error
    """
    if not fecha_nac:
        return None
    try:
        # Intentar formato ISO primero (YYYY-MM-DD)
        if isinstance(fecha_nac, str):
            try:
                nac = datetime.strptime(fecha_nac, "%Y-%m-%d").date()
            except ValueError:
                # Intentar formato DD/MM/YYYY
                try:
                    nac = datetime.strptime(fecha_nac, "%d/%m/%Y").date()
                except ValueError:
                    return None
        elif isinstance(fecha_nac, date):
            nac = fecha_nac
        else:
            return None
        
        if fecha_ref:
            if isinstance(fecha_ref, str):
                try:
                    ref = datetime.strptime(fecha_ref, "%Y-%m-%d").date()
                except ValueError:
                    ref = datetime.strptime(fecha_ref, "%d/%m/%Y").date()
            elif isinstance(fecha_ref, date):
                ref = fecha_ref
            else:
                ref = date.today()
        else:
            ref = date.today()
        
        delta = ref - nac
        return delta.days // 365
    except:
        return None


def calc_dias_estancia(fecha_ingreso):
    """
    Calcula los días de estancia desde la fecha de ingreso hasta hoy.
    
    Args:
        fecha_ingreso: Fecha de ingreso (acepta "DD/MM/AAAA" o "YYYY-MM-DD")
    
    Returns:
        int: Días de estancia, o None si hay error
    """
    if not fecha_ingreso:
        return None
    try:
        if isinstance(fecha_ingreso, str):
            try:
                ing = datetime.strptime(fecha_ingreso, "%Y-%m-%d").date()
            except ValueError:
                ing = datetime.strptime(fecha_ingreso, "%d/%m/%Y").date()
        elif isinstance(fecha_ingreso, date):
            ing = fecha_ingreso
        else:
            return None
        hoy = date.today()
        return (hoy - ing).days
    except:
        return None


def calc_tam(tas, tad):
    """
    Calcula la Tensión Arterial Media (TAM).
    Fórmula: TAM = (2*TAD + TAS) / 3
    
    Args:
        tas: Tensión arterial sistólica (mmHg)
        tad: Tensión arterial diastólica (mmHg)
    
    Returns:
        float: TAM redondeado a 1 decimal, o None si faltan datos
    """
    if tas is not None and tad is not None:
        try:
            return round((2 * float(tad) + float(tas)) / 3, 1)
        except (ValueError, TypeError):
            return None
    return None


def calc_imc(peso, talla):
    """
    Calcula el Índice de Masa Corporal (IMC).
    Fórmula: IMC = peso / talla²
    
    Args:
        peso: Peso en kg
        talla: Talla en metros
    
    Returns:
        float: IMC redondeado a 2 decimales, o None si faltan datos
    """
    if peso and talla:
        try:
            peso = float(peso)
            talla = float(talla)
            if talla > 0:
                return round(peso / (talla ** 2), 2)
        except (ValueError, TypeError):
            pass
    return None


def calc_peso_ideal(talla, sexo):
    """
    Calcula el peso ideal según la fórmula de Devine.
    
    Args:
        talla: Talla en metros
        sexo: "Hombre" o "Mujer"
    
    Returns:
        float: Peso ideal en kg, o None si faltan datos
    """
    if not talla or not sexo:
        return None
    try:
        talla_cm = float(talla) * 100
        if sexo.lower() in ["hombre", "masculino", "m"]:
            return round(50 + 0.91 * (talla_cm - 152.4), 2)
        else:
            return round(45.5 + 0.91 * (talla_cm - 152.4), 2)
    except (ValueError, TypeError):
        return None


def calc_peso_ajustado(peso_real, talla, sexo):
    """
    Calcula el peso ajustado para pacientes con IMC >= 30 (obesidad).
    Si IMC < 30, devuelve el peso real.
    Fórmula: Peso ajustado = ((peso_real - peso_ideal) / 2) + peso_ideal
    
    Args:
        peso_real: Peso actual en kg
        talla: Talla en metros
        sexo: "Hombre" o "Mujer"
    
    Returns:
        float: Peso ajustado o peso real, o None si hay error
    """
    imc = calc_imc(peso_real, talla)
    if imc is None:
        return None
    if imc >= 30:
        peso_ideal = calc_peso_ideal(talla, sexo)
        if peso_ideal is None:
            return None
        try:
            return round(((float(peso_real) - peso_ideal) / 2) + peso_ideal, 2)
        except (ValueError, TypeError):
            return None
    else:
        try:
            return float(peso_real)
        except (ValueError, TypeError):
            return None


def calc_proteinas_requeridas(proteinas_slider, peso_usado):
    """
    Calcula las proteínas requeridas según el peso.
    
    Args:
        proteinas_slider: Requerimiento proteico (g/kg/día)
        peso_usado: Peso del paciente (kg)
    
    Returns:
        float: Proteínas requeridas (g/día), o None si faltan datos
    """
    if proteinas_slider and peso_usado:
        try:
            return round(float(proteinas_slider) * float(peso_usado), 2)
        except (ValueError, TypeError):
            pass
    return None


def calc_volumen_24h(proteinas_req, producto, volumen_aporte=None, proteinas_aporte=None):
    """
    Calcula el volumen de nutrición necesario para 24h.
    
    Concentraciones por producto:
    - Vivase: 9.4 / 237 g/mL
    - Smof K hipo: 75 / 1477 g/mL
    - Smof K normo: 100 / 1477 g/mL
    
    Args:
        proteinas_req: Proteínas requeridas (g/día)
        producto: Nombre del producto
        volumen_aporte: Volumen aportado (mL) - opcional
        proteinas_aporte: Proteínas aportadas (g) - opcional
    
    Returns:
        float: Volumen en mL/24h, o None si faltan datos
    """
    if not proteinas_req:
        return None
    
    try:
        proteinas_req = float(proteinas_req)
        
        if producto and producto != "Otro":
            concentraciones = {
                "Vivase": 9.4 / 237,
                "Smof K hipo": 75 / 1477,
                "Smof K normo": 100 / 1477
            }
            conc = concentraciones.get(producto, 0)
            if conc > 0:
                return round(proteinas_req / conc, 2)
        
        if volumen_aporte and proteinas_aporte:
            vol = float(volumen_aporte)
            prot = float(proteinas_aporte)
            if prot > 0:
                return round((proteinas_req / prot) * vol, 2)
    except (ValueError, TypeError):
        pass
    
    return None


def calc_kcal_totales(ml_24h, volumen_aporte, kcal_aporte):
    """
    Calcula las kcal totales aportadas.
    Fórmula: Kcal_totales = (ml_24h / volumen_aporte) * kcal_aporte
    
    Args:
        ml_24h: mL administrados en 24h
        volumen_aporte: Volumen total del producto (mL)
        kcal_aporte: Kcal totales del producto
    
    Returns:
        float: Kcal totales, o None si faltan datos
    """
    if ml_24h and volumen_aporte and kcal_aporte:
        try:
            return round((float(ml_24h) / float(volumen_aporte)) * float(kcal_aporte), 2)
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return None


def calc_indice_urinario(diuresis, peso, horas):
    """
    Calcula el índice urinario (ml/kg/hora).
    Fórmula: diuresis / (peso × horas)
    
    Args:
        diuresis: Volumen de diuresis total (ml)
        peso: Peso del paciente (kg)
        horas: Periodo de tiempo (horas)
    
    Returns:
        float: Índice urinario, o None si faltan datos
    """
    if diuresis is not None and peso and horas:
        try:
            diuresis = float(diuresis)
            peso = float(peso)
            horas = float(horas)
            if horas > 0 and peso > 0:
                return round(diuresis / peso / horas, 2)
        except (ValueError, TypeError):
            pass
    return None


def calc_tfg(creatinina, edad, sexo, peso=None):
    """
    Calcula la Tasa de Filtración Glomerular (TFG) por Cockroft-Gault.
    Fórmula: ((140 - edad) × peso) / (72 × creatinina) × factor_sexo
    
    Args:
        creatinina: Creatinina sérica (mg/dL)
        edad: Edad en años
        sexo: "Hombre" o "Mujer"
        peso: Peso en kg (opcional, por defecto 70)
    
    Returns:
        float: TFG (ml/min), o None si faltan datos
    """
    if not creatinina or not edad or not sexo:
        return None
    
    try:
        creat = float(creatinina)
        edad_val = float(edad)
        peso_val = float(peso) if peso else 70
        
        if creat <= 0 or edad_val <= 0 or peso_val <= 0:
            return None
            
        factor = 0.85 if sexo.lower() in ["mujer", "femenino", "f"] else 1.0
        
        return round(((140 - edad_val) * peso_val) / (72 * creat) * factor, 2)
    except (ValueError, TypeError):
        return None


def calc_tobin(fr, vt):
    """
    Calcula el índice de Tobin (frecuencia respiratoria / volumen corriente).
    Fórmula: FR / (Vt / 1000)
    
    Args:
        fr: Frecuencia respiratoria (rpm)
        vt: Volumen corriente (mL)
    
    Returns:
        float: Índice de Tobin, o None si faltan datos
    """
    if fr and vt:
        try:
            fr_val = float(fr)
            vt_val = float(vt)
            if vt_val > 0:
                return round(fr_val / (vt_val / 1000), 2)
        except (ValueError, TypeError):
            pass
    return None


def calc_pafi(pao2, fio2):
    """
    Calcula el ratio PaO2/FiO2 (PAFi).
    Fórmula: PaO2 / (FiO2 / 100)
    
    Args:
        pao2: Presión arterial de oxígeno (mmHg)
        fio2: Fracción inspirada de oxígeno (%)
    
    Returns:
        float: PAFi, o None si faltan datos
    """
    if pao2 and fio2:
        try:
            pao2_val = float(pao2)
            fio2_val = float(fio2)
            if fio2_val > 0:
                return round(pao2_val / (fio2_val / 100), 2)
        except (ValueError, TypeError):
            pass
    return None


def calc_balance(ingresos, egresos):
    """
    Calcula el balance hídrico del día.
    
    Args:
        ingresos: Ingresos totales (mL)
        egresos: Egresos totales (mL)
    
    Returns:
        int: Balance (mL), o None si faltan datos
    """
    if ingresos is not None and egresos is not None:
        try:
            return int(float(ingresos) - float(egresos))
        except (ValueError, TypeError):
            pass
    return None


def calc_vt_peso(vt, peso_ideal):
    """
    Calcula el volumen tidal por peso ideal (mL/kg).
    
    Args:
        vt: Volumen tidal (mL)
        peso_ideal: Peso ideal (kg)
    
    Returns:
        float: VT/peso (mL/kg), o None si faltan datos
    """
    if vt and peso_ideal:
        try:
            vt_val = float(vt)
            peso_val = float(peso_ideal)
            if peso_val > 0:
                return round(vt_val / peso_val, 2)
        except (ValueError, TypeError):
            pass
    return None


# =============================================================================
# ESCALAS PRONÓSTICAS (5 funciones principales + 4 de mortalidad)
# =============================================================================

def calculate_news2(data):
    """
    Calcula el score NEWS2 (National Early Warning Score 2).
    
    Args:
        data: Diccionario con datos clínicos
    
    Returns:
        dict: {'score': int, 'interpretacion': str}
    """
    defaults = {
        'fr': 14,
        'sao2': 96,
        'o2_suplementario': False,
        'tas': 120,
        'fc': 80,
        'temperatura': 36.5,
        'glasgow': 15
    }

    # Obtener valores con manejo de None
    fr = data.get('fr') if data.get('fr') is not None else defaults['fr']
    sao2 = data.get('sao2') if data.get('sao2') is not None else defaults['sao2']
    o2_sup = data.get('o2_suplementario') if data.get('o2_suplementario') is not None else defaults['o2_suplementario']
    tas = data.get('tas') if data.get('tas') is not None else defaults['tas']
    fc = data.get('fc') if data.get('fc') is not None else defaults['fc']
    temp = data.get('temperatura') if data.get('temperatura') is not None else defaults['temperatura']
    gcs = data.get('glasgow') if data.get('glasgow') is not None else defaults['glasgow']

    try:
        # Puntuación de conciencia (AVPU) a partir de Glasgow
        if gcs == 15:
            con_score = 0
        elif 12 <= gcs <= 14:
            con_score = 3
        else:
            con_score = 5

        # FR
        if fr <= 8:
            fr_score = 2
        elif 9 <= fr <= 11:
            fr_score = 1
        elif 12 <= fr <= 20:
            fr_score = 0
        elif 21 <= fr <= 24:
            fr_score = 2
        else:
            fr_score = 3

        # SatO₂
        if o2_sup:
            if sao2 >= 97:
                spo2_score = 0
            elif 94 <= sao2 <= 96:
                spo2_score = 1
            elif 92 <= sao2 <= 93:
                spo2_score = 2
            else:
                spo2_score = 3
        else:
            if sao2 >= 96:
                spo2_score = 0
            elif 94 <= sao2 <= 95:
                spo2_score = 1
            elif 92 <= sao2 <= 93:
                spo2_score = 2
            else:
                spo2_score = 3

        # TAS
        if tas >= 220:
            tas_score = 3
        elif 201 <= tas <= 219:
            tas_score = 2
        elif 111 <= tas <= 200:
            tas_score = 0
        elif 101 <= tas <= 110:
            tas_score = 1
        elif 91 <= tas <= 100:
            tas_score = 2
        else:
            tas_score = 3

        # FC
        if fc <= 40:
            fc_score = 3
        elif 41 <= fc <= 50:
            fc_score = 1
        elif 51 <= fc <= 90:
            fc_score = 0
        elif 91 <= fc <= 110:
            fc_score = 1
        elif 111 <= fc <= 130:
            fc_score = 2
        else:
            fc_score = 3

        # Temperatura
        if temp < 35.0:
            temp_score = 3
        elif 35.0 <= temp <= 35.9:
            temp_score = 1
        elif 36.0 <= temp <= 38.0:
            temp_score = 0
        elif 38.1 <= temp <= 39.0:
            temp_score = 1
        else:
            temp_score = 2

        news2 = fr_score + spo2_score + tas_score + fc_score + temp_score + con_score
        
        # Interpretación
        if news2 < 5:
            interp = "BAJO RIESGO"
        elif news2 < 7:
            interp = "RIESGO MEDIO"
        else:
            interp = "ALTO RIESGO"
        
        return {'score': news2, 'interpretacion': interp}
    except:
        return {'score': 0, 'interpretacion': 'NO CALCULABLE'}


def calculate_sofa(data):
    """
    Calcula el score SOFA (Sequential Organ Failure Assessment).
    
    Args:
        data: Diccionario con datos clínicos
    
    Returns:
        dict: {'score': int, 'interpretacion': str}
    """
    defaults = {
        'pafi': 400,
        'plaquetas': 150,
        'bilirrubina_total': 0.5,
        'tam': 70,
        'creatinina': 0.7,
        'glasgow': 15
    }

    pafi = data.get('pafi') if data.get('pafi') is not None else defaults['pafi']
    plt = data.get('plaquetas') if data.get('plaquetas') is not None else defaults['plaquetas']
    bili = data.get('bilirrubina_total') if data.get('bilirrubina_total') is not None else defaults['bilirrubina_total']
    tam = data.get('tam') if data.get('tam') is not None else defaults['tam']
    cr = data.get('creatinina') if data.get('creatinina') is not None else defaults['creatinina']
    gcs = data.get('glasgow') if data.get('glasgow') is not None else defaults['glasgow']

    try:
        # Respiratorio (PaFi)
        if pafi >= 400:
            resp_score = 0
        elif 300 <= pafi < 400:
            resp_score = 1
        elif 200 <= pafi < 300:
            resp_score = 2
        elif 100 <= pafi < 200:
            resp_score = 3
        else:
            resp_score = 4

        # Coagulación (Plaquetas)
        if plt >= 150:
            coag_score = 0
        elif 100 <= plt < 150:
            coag_score = 1
        elif 50 <= plt < 100:
            coag_score = 2
        else:
            coag_score = 3

        # Hepático (Bilirrubina)
        if bili < 1.2:
            liver_score = 0
        elif 1.2 <= bili < 2.0:
            liver_score = 1
        elif 2.0 <= bili < 6.0:
            liver_score = 2
        elif 6.0 <= bili < 12.0:
            liver_score = 3
        else:
            liver_score = 4

        # Cardiovascular (TAM)
        if tam >= 70:
            cv_score = 0
        else:
            cv_score = 2

        # Renal (Creatinina)
        if cr < 1.2:
            renal_score = 0
        elif 1.2 <= cr < 2.0:
            renal_score = 1
        elif 2.0 <= cr < 3.5:
            renal_score = 2
        elif 3.5 <= cr < 5.0:
            renal_score = 3
        else:
            renal_score = 4

        # Neurológico (Glasgow)
        if gcs >= 15:
            neuro_score = 0
        elif 13 <= gcs <= 14:
            neuro_score = 1
        elif 10 <= gcs <= 12:
            neuro_score = 2
        elif 6 <= gcs <= 9:
            neuro_score = 3
        else:
            neuro_score = 4

        sofa = resp_score + coag_score + liver_score + cv_score + renal_score + neuro_score
        
        if sofa < 6:
            interp = "LEVE"
        elif sofa < 11:
            interp = "MODERADA"
        else:
            interp = "SEVERA"
        
        return {'score': sofa, 'interpretacion': interp}
    except:
        return {'score': 0, 'interpretacion': 'NO CALCULABLE'}


def calculate_apache2(data):
    """
    Calcula el score APACHE II.
    
    Args:
        data: Diccionario con datos clínicos
    
    Returns:
        dict: {'score': int, 'interpretacion': str}
    """
    defaults = {
        'tam': 70, 'fc': 80, 'fr': 14, 'temperatura': 36.5, 
        'gasometria_ph': 7.4, 'sodio': 140, 'potasio': 4.0, 
        'creatinina': 0.7, 'hematocrito': 40, 'leucocitos': 10
    }

    try:
        # Edad
        edad = data.get('edad') if data.get('edad') is not None else 60
        if edad < 45:
            age_score = 0
        elif 45 <= edad <= 54:
            age_score = 2
        elif 55 <= edad <= 64:
            age_score = 3
        elif 65 <= edad <= 74:
            age_score = 5
        else:
            age_score = 6

        # Glasgow
        gcs = data.get('glasgow') if data.get('glasgow') is not None else 15
        gcs_score = 15 - gcs

        # TAM
        tam = data.get('tam') if data.get('tam') is not None else defaults['tam']
        if tam >= 130:
            tam_score = 2
        elif 110 <= tam <= 129:
            tam_score = 1
        elif 70 <= tam <= 109:
            tam_score = 0
        elif 50 <= tam <= 69:
            tam_score = 2
        else:
            tam_score = 4

        # FC
        fc = data.get('fc') if data.get('fc') is not None else defaults['fc']
        if fc >= 180:
            fc_score = 3
        elif 140 <= fc <= 179:
            fc_score = 2
        elif 110 <= fc <= 139:
            fc_score = 1
        elif 70 <= fc <= 109:
            fc_score = 0
        elif 55 <= fc <= 69:
            fc_score = 2
        elif 40 <= fc <= 54:
            fc_score = 3
        else:
            fc_score = 4

        # FR
        fr = data.get('fr') if data.get('fr') is not None else defaults['fr']
        if fr >= 50:
            fr_score = 3
        elif 35 <= fr <= 49:
            fr_score = 2
        elif 25 <= fr <= 34:
            fr_score = 1
        elif 12 <= fr <= 24:
            fr_score = 0
        elif 10 <= fr <= 11:
            fr_score = 1
        elif 6 <= fr <= 9:
            fr_score = 2
        else:
            fr_score = 4

        # Temperatura
        temp = data.get('temperatura') if data.get('temperatura') is not None else defaults['temperatura']
        if temp >= 41:
            temp_score = 3
        elif 39 <= temp <= 40.9:
            temp_score = 2
        elif 38.5 <= temp <= 38.9:
            temp_score = 1
        elif 36 <= temp <= 38.4:
            temp_score = 0
        elif 34 <= temp <= 35.9:
            temp_score = 1
        elif 32 <= temp <= 33.9:
            temp_score = 2
        elif 30 <= temp <= 31.9:
            temp_score = 3
        else:
            temp_score = 4

        # pH
        ph = data.get('gasometria_ph') if data.get('gasometria_ph') is not None else defaults['gasometria_ph']
        if ph >= 7.7:
            ph_score = 3
        elif 7.6 <= ph <= 7.69:
            ph_score = 2
        elif 7.5 <= ph <= 7.59:
            ph_score = 1
        elif 7.33 <= ph <= 7.49:
            ph_score = 0
        elif 7.25 <= ph <= 7.32:
            ph_score = 2
        elif 7.15 <= ph <= 7.24:
            ph_score = 3
        else:
            ph_score = 4

        # Sodio
        na = data.get('sodio') if data.get('sodio') is not None else defaults['sodio']
        if na >= 180:
            na_score = 3
        elif 160 <= na <= 179:
            na_score = 2
        elif 155 <= na <= 159:
            na_score = 1
        elif 150 <= na <= 154:
            na_score = 0
        elif 130 <= na <= 149:
            na_score = 0
        elif 120 <= na <= 129:
            na_score = 2
        elif 110 <= na <= 119:
            na_score = 3
        else:
            na_score = 4

        # Potasio
        k = data.get('potasio') if data.get('potasio') is not None else defaults['potasio']
        if k >= 7:
            k_score = 3
        elif 6.0 <= k <= 6.9:
            k_score = 2
        elif 5.5 <= k <= 5.9:
            k_score = 1
        elif 3.5 <= k <= 5.4:
            k_score = 0
        elif 3.0 <= k <= 3.4:
            k_score = 1
        elif 2.5 <= k <= 2.9:
            k_score = 2
        else:
            k_score = 3

        # Creatinina
        cr = data.get('creatinina') if data.get('creatinina') is not None else defaults['creatinina']
        if cr >= 3.5:
            cr_score = 3
        elif 2.0 <= cr <= 3.4:
            cr_score = 2
        elif 1.5 <= cr <= 1.9:
            cr_score = 1
        else:
            cr_score = 0

        # Hematocrito
        hto = data.get('hematocrito') if data.get('hematocrito') is not None else defaults['hematocrito']
        if hto >= 60:
            hto_score = 3
        elif 50 <= hto <= 59.9:
            hto_score = 2
        elif 46 <= hto <= 49.9:
            hto_score = 1
        elif 30 <= hto <= 45.9:
            hto_score = 0
        elif 20 <= hto <= 29.9:
            hto_score = 2
        else:
            hto_score = 3

        # Leucocitos
        wbc = data.get('leucocitos') if data.get('leucocitos') is not None else defaults['leucocitos']
        if wbc >= 40:
            wbc_score = 3
        elif 20 <= wbc <= 39.9:
            wbc_score = 2
        elif 15 <= wbc <= 19.9:
            wbc_score = 1
        elif 3 <= wbc <= 14.9:
            wbc_score = 0
        elif 1 <= wbc <= 2.9:
            wbc_score = 2
        else:
            wbc_score = 3

        apache2 = (age_score + gcs_score + tam_score + fc_score + fr_score + 
                   temp_score + ph_score + na_score + k_score + cr_score + 
                   hto_score + wbc_score)
        
        if apache2 < 10:
            interp = "BAJO RIESGO"
        elif apache2 < 20:
            interp = "RIESGO MODERADO"
        else:
            interp = "ALTO RIESGO"
        
        return {'score': apache2, 'interpretacion': interp}
    except:
        return {'score': 0, 'interpretacion': 'NO CALCULABLE'}


def calculate_saps3(data):
    """
    Calcula el score SAPS 3 (simplificado).
    
    Args:
        data: Diccionario con datos clínicos
    
    Returns:
        dict: {'score': int, 'interpretacion': str}
    """
    defaults = {
        'edad': 60, 'glasgow': 15, 'fc': 80, 'tas': 120, 'fr': 14,
        'temperatura': 36.5, 'bilirrubina_total': 0.5, 'creatinina': 0.7,
        'leucocitos': 10, 'plaquetas': 200
    }

    try:
        # Edad
        edad = data.get('edad') if data.get('edad') is not None else defaults['edad']
        if edad < 40:
            age_score = 0
        elif edad < 60:
            age_score = 2
        elif edad < 70:
            age_score = 4
        elif edad < 80:
            age_score = 6
        else:
            age_score = 8

        # Glasgow
        gcs = data.get('glasgow') if data.get('glasgow') is not None else defaults['glasgow']
        if gcs >= 15:
            gcs_score = 0
        elif gcs >= 13:
            gcs_score = 2
        elif gcs >= 10:
            gcs_score = 4
        elif gcs >= 7:
            gcs_score = 6
        else:
            gcs_score = 8

        # FC
        fc = data.get('fc') if data.get('fc') is not None else defaults['fc']
        if fc <= 60:
            fc_score = 0
        elif fc <= 100:
            fc_score = 1
        elif fc <= 140:
            fc_score = 2
        else:
            fc_score = 3

        # TAS
        tas = data.get('tas') if data.get('tas') is not None else defaults['tas']
        if tas >= 120:
            tas_score = 0
        elif tas >= 100:
            tas_score = 1
        elif tas >= 70:
            tas_score = 2
        else:
            tas_score = 3

        # FR
        fr = data.get('fr') if data.get('fr') is not None else defaults['fr']
        if fr <= 12:
            fr_score = 0
        elif fr <= 20:
            fr_score = 1
        elif fr <= 30:
            fr_score = 2
        else:
            fr_score = 3

        # Temperatura
        temp = data.get('temperatura') if data.get('temperatura') is not None else defaults['temperatura']
        if 36.0 <= temp <= 38.0:
            temp_score = 0
        elif 34.0 <= temp < 36.0 or 38.0 < temp <= 39.0:
            temp_score = 1
        else:
            temp_score = 2

        # Bilirrubina
        bili = data.get('bilirrubina_total') if data.get('bilirrubina_total') is not None else defaults['bilirrubina_total']
        if bili < 1.2:
            bili_score = 0
        elif bili < 3.0:
            bili_score = 1
        elif bili < 6.0:
            bili_score = 2
        else:
            bili_score = 3

        # Creatinina
        cr = data.get('creatinina') if data.get('creatinina') is not None else defaults['creatinina']
        if cr < 1.2:
            cr_score = 0
        elif cr < 2.0:
            cr_score = 1
        elif cr < 3.5:
            cr_score = 2
        else:
            cr_score = 3

        # Leucocitos
        wbc = data.get('leucocitos') if data.get('leucocitos') is not None else defaults['leucocitos']
        if 3 <= wbc <= 12:
            wbc_score = 0
        elif 2 <= wbc < 3 or 12 < wbc <= 20:
            wbc_score = 1
        elif 1 <= wbc < 2 or 20 < wbc <= 30:
            wbc_score = 2
        else:
            wbc_score = 3

        # Plaquetas
        plt = data.get('plaquetas') if data.get('plaquetas') is not None else defaults['plaquetas']
        if plt >= 150:
            plt_score = 0
        elif plt >= 100:
            plt_score = 1
        elif plt >= 50:
            plt_score = 2
        else:
            plt_score = 3

        saps3 = (age_score + gcs_score + fc_score + tas_score + fr_score + 
                 temp_score + bili_score + cr_score + wbc_score + plt_score)
        
        if saps3 < 30:
            interp = "BAJO RIESGO"
        elif saps3 < 50:
            interp = "RIESGO MODERADO"
        else:
            interp = "ALTO RIESGO"
        
        return {'score': saps3, 'interpretacion': interp}
    except:
        return {'score': 0, 'interpretacion': 'NO CALCULABLE'}


def calculate_swift(data):
    """
    Calcula el score SWIFT (Simplified Weaning Failure Predictor).
    
    Args:
        data: Diccionario con datos clínicos
    
    Returns:
        dict: {'score': int, 'interpretacion': str}
    """
    defaults = {
        'edad': 60, 'pafi': 400, 'peep': 5, 'fr': 14, 'fc': 80, 'glasgow': 15
    }

    try:
        # Edad
        edad = data.get('edad') if data.get('edad') is not None else defaults['edad']
        age_points = 0
        if edad > 65:
            age_points = 10
        elif edad >= 50:
            age_points = 5

        # PaO2/FiO2
        pafi = data.get('pafi') if data.get('pafi') is not None else defaults['pafi']
        if pafi < 200:
            pafi_points = 20
        elif pafi < 300:
            pafi_points = 10
        else:
            pafi_points = 0

        # PEEP
        peep = data.get('peep') if data.get('peep') is not None else defaults['peep']
        if peep > 8:
            peep_points = 10
        elif peep >= 5:
            peep_points = 5
        else:
            peep_points = 0

        # FR
        fr = data.get('fr') if data.get('fr') is not None else defaults['fr']
        if fr > 30:
            fr_points = 10
        elif fr >= 20:
            fr_points = 5
        else:
            fr_points = 0

        # FC
        fc = data.get('fc') if data.get('fc') is not None else defaults['fc']
        if fc > 120:
            fc_points = 10
        elif fc >= 100:
            fc_points = 5
        else:
            fc_points = 0

        # Glasgow
        gcs = data.get('glasgow') if data.get('glasgow') is not None else defaults['glasgow']
        gcs_points = 0 if gcs >= 15 else 10

        swift = age_points + pafi_points + peep_points + fr_points + fc_points + gcs_points
        
        if swift <= 15:
            interp = "ALTO PROBABILIDAD DE ÉXITO"
        elif swift <= 30:
            interp = "RIESGO MODERADO"
        else:
            interp = "ALTO RIESGO DE FALLO"
        
        return {'score': swift, 'interpretacion': interp}
    except:
        return {'score': 0, 'interpretacion': 'NO CALCULABLE'}


# =============================================================================
# MORTALIDAD ESTIMADA
# =============================================================================

def mortality_news2(score):
    """Estimación de mortalidad según NEWS2."""
    if score is None:
        return "N/A"
    if score < 5:
        return "< 1%"
    elif score < 7:
        return "1-5%"
    else:
        return "> 5%"


def mortality_sofa(score):
    """Estimación de mortalidad según SOFA."""
    if score is None:
        return "N/A"
    if score >= 15:
        return "> 90%"
    else:
        return f"{min(95, score * 5 + 5):.0f}%"


def mortality_apache2(score):
    """Estimación de mortalidad según APACHE II."""
    if score is None:
        return "N/A"
    mortality = 100 * (0.01 * score ** 2)
    if mortality > 95:
        return "> 95%"
    else:
        return f"{mortality:.0f}%"


def mortality_saps3(score):
    """Estimación de mortalidad según SAPS 3."""
    if score is None:
        return "N/A"
    mortality = min(95, score * 1.5)
    return f"{mortality:.0f}%"


# =============================================================================
# FUNCIÓN PRINCIPAL - CALCULAR TODOS LOS SCORES
# =============================================================================

def calculate_all_scores(data):
    """
    Calcula todas las escalas pronósticas y sus interpretaciones.
    
    Args:
        data: Diccionario con todos los datos clínicos necesarios
    
    Returns:
        dict: Diccionario con todos los scores y mortalidades
    """
    results = {}
    
    # NEWS2
    news2_result = calculate_news2(data)
    results['news2'] = {
        'score': news2_result['score'],
        'interpretacion': news2_result['interpretacion'],
        'mortalidad': mortality_news2(news2_result['score'])
    }
    
    # SOFA
    sofa_result = calculate_sofa(data)
    results['sofa'] = {
        'score': sofa_result['score'],
        'interpretacion': sofa_result['interpretacion'],
        'mortalidad': mortality_sofa(sofa_result['score'])
    }
    
    # SOFA2 (usamos el mismo valor que SOFA)
    results['sofa2'] = {
        'score': sofa_result['score'],
        'interpretacion': sofa_result['interpretacion'],
        'mortalidad': mortality_sofa(sofa_result['score'])
    }
    
    # APACHE II
    apache2_result = calculate_apache2(data)
    results['apache2'] = {
        'score': apache2_result['score'],
        'interpretacion': apache2_result['interpretacion'],
        'mortalidad': mortality_apache2(apache2_result['score'])
    }
    
    # SAPS 3
    saps3_result = calculate_saps3(data)
    results['saps3'] = {
        'score': saps3_result['score'],
        'interpretacion': saps3_result['interpretacion'],
        'mortalidad': mortality_saps3(saps3_result['score'])
    }
    
    # SWIFT
    swift_result = calculate_swift(data)
    results['swift'] = {
        'score': swift_result['score'],
        'interpretacion': swift_result['interpretacion']
    }
    
    return results


# =============================================================================
# CÁLCULO DE CAMPOS COMPUTADOS COMPLETO
# =============================================================================

def calculate_computed_fields(patient_data):
    """
    Calcula todos los campos automáticos para un paciente.
    
    Args:
        patient_data: Diccionario con datos del paciente
    
    Returns:
        dict: Diccionario con campos calculados añadidos
    """
    data = patient_data.copy()
    
    # Fecha de referencia para cálculos
    fecha_ref = data.get('fecha_ingreso') or data.get('fecha_ingreso_hosp')
    
    # 1. Edad
    if data.get('fecha_nacimiento'):
        data['edad'] = calc_edad(data['fecha_nacimiento'], fecha_ref)
    
    # 2. Días de estancia
    if data.get('fecha_ingreso'):
        data['dias_estancia'] = calc_dias_estancia(data['fecha_ingreso'])
    
    # 3. TAM
    if data.get('tas') and data.get('tad'):
        data['tam'] = calc_tam(data['tas'], data['tad'])
    
    # 4. IMC
    if data.get('peso_estimado') and data.get('talla'):
        data['imc'] = calc_imc(data['peso_estimado'], data['talla'])
    
    # 5. Peso ideal
    if data.get('talla') and data.get('sexo'):
        data['peso_ideal'] = calc_peso_ideal(data['talla'], data['sexo'])
    
    # 6. Peso ajustado
    if data.get('peso_estimado') and data.get('talla') and data.get('sexo'):
        data['peso_ajustado'] = calc_peso_ajustado(
            data['peso_estimado'], data['talla'], data['sexo']
        )
    
    # 7. Proteínas requeridas
    if data.get('proteinas_slider') and (data.get('peso_ajustado') or data.get('peso_estimado')):
        peso_usado = data.get('peso_ajustado') or data.get('peso_estimado')
        data['proteinas_requeridas'] = calc_proteinas_requeridas(
            data['proteinas_slider'], peso_usado
        )
    
    # 8. Volumen 24h
    if data.get('proteinas_requeridas'):
        data['ml_24h_calc'] = calc_volumen_24h(
            data['proteinas_requeridas'],
            data.get('producto_nutricion'),
            data.get('volumen_aporte'),
            data.get('proteinas_aporte')
        )
    
    # 9. Kcal totales
    if data.get('ml_24h_calc') and data.get('volumen_aporte') and data.get('kcal_aporte'):
        data['kcal_totales_calc'] = calc_kcal_totales(
            data['ml_24h_calc'], data['volumen_aporte'], data['kcal_aporte']
        )
    
    # 10. Índice urinario
    if data.get('diuresis_total') and data.get('peso_estimado') and data.get('periodo_horas'):
        data['indice_urinario'] = calc_indice_urinario(
            data['diuresis_total'], data['peso_estimado'], data['periodo_horas']
        )
    
    # 11. TFG
    if data.get('creatinina') and data.get('edad') and data.get('sexo'):
        data['tfg'] = calc_tfg(
            data['creatinina'], data['edad'], data['sexo'], data.get('peso_estimado')
        )
    
    # 12. Tobin
    if data.get('fr') and data.get('vt_psinp'):
        data['tobin'] = calc_tobin(data['fr'], data['vt_psinp'])
    
    # 13. PAFi
    if data.get('gasometria_po2') and data.get('fio2'):
        data['pafi'] = calc_pafi(data['gasometria_po2'], data['fio2'])
    
    # 14. Balance
    if data.get('ingresos') is not None and data.get('egresos') is not None:
        data['balance'] = calc_balance(data['ingresos'], data['egresos'])
    
    # 15. VT/peso
    if data.get('vt_psinp') and data.get('peso_ideal'):
        data['vt_peso'] = calc_vt_peso(data['vt_psinp'], data['peso_ideal'])
    
    # Calcular scores pronósticos
    scores = calculate_all_scores(data)
    
    # Agregar scores al resultado
    data['news2_ingreso'] = scores['news2']['score']
    data['news2_interpretado'] = scores['news2']['interpretacion']
    data['sofa_ingreso'] = scores['sofa']['score']
    data['sofa_mortalidad'] = scores['sofa']['mortalidad']
    data['sofa2_ingreso'] = scores['sofa2']['score']
    data['apache2_ingreso'] = scores['apache2']['score']
    data['apache2_mortalidad'] = scores['apache2']['mortalidad']
    data['saps3_ingreso'] = scores['saps3']['score']
    data['saps3_mortalidad'] = scores['saps3']['mortalidad']
    data['swift_score'] = scores['swift']['score']
    
    return data
