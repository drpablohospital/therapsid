"""
SINAPSID DMA - Módulo de Privacidad
====================================
Máscara de datos sensibles para proteger información de pacientes.
Solo usuarios de instituciones autorizadas (HGSJDR) ven datos reales.
"""

import random
import string
from datetime import datetime, timedelta

# Instituciones autorizadas para ver datos reales
AUTHORIZED_INSTITUTIONS = ['HGSJDR', 'hgsjdr']

# Campos sensibles que deben ser ofuscados
SENSITIVE_FIELDS = ['nombre_completo', 'curp', 'expediente', 'fecha_nacimiento']


def generate_mask(length=10):
    """Genera una cadena aleatoria de caracteres."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def mask_date(date_str):
    """Genera una fecha aleatoria dentro de un rango razonable."""
    if not date_str:
        return None
    try:
        # Fecha aleatoria entre 1950 y 2000
        start_date = datetime(1950, 1, 1)
        end_date = datetime(2000, 12, 31)
        random_date = start_date + timedelta(
            seconds=random.randint(0, int((end_date - start_date).total_seconds()))
        )
        return random_date.strftime('%Y-%m-%d')
    except:
        return '1970-01-01'


def mask_patient_data(patient_data, user_institution):
    """
    Ofusca datos sensibles del paciente si el usuario no está en institución autorizada.
    
    Args:
        patient_data: dict o lista con datos del paciente
        user_institution: str - institución del usuario logueado
    
    Returns:
        dict o lista con datos ofuscados si es necesario
    """
    if not user_institution:
        user_institution = ''
    
    # Verificar si la institución está autorizada
    is_authorized = user_institution.upper() in [inst.upper() for inst in AUTHORIZED_INSTITUTIONS]
    
    if is_authorized:
        return patient_data
    
    # Si es un diccionario
    if isinstance(patient_data, dict):
        masked = patient_data.copy()
        for field in SENSITIVE_FIELDS:
            if field in masked:
                if field == 'fecha_nacimiento':
                    masked[field] = mask_date(masked[field])
                else:
                    masked[field] = generate_mask(12)
        return masked
    
    # Si es una lista de diccionarios
    if isinstance(patient_data, list):
        return [mask_patient_data(p, user_institution) for p in patient_data]
    
    return patient_data


def get_user_institution(user_id):
    """Obtiene la institución del usuario desde la base de datos."""
    from modules.database import get_db_connection
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT institution FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            if result:
                return result[0] or ''
    except:
        pass
    return ''
