"""
SINAPSID DMA - Módulo de Administración
=====================================
Funciones para el dashboard de admin:
- Métricas de sistema
- Gestión de usuarios (CRUD, reset contraseñas)
- Gestión de protocolos (CRUD, aprobación)
- Métricas de completitud de expedientes
- Exportación de cohortes
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import hashlib

from modules.database import get_db_connection, get_db_cursor, dict_from_row
from werkzeug.security import generate_password_hash


# ============================================================================
# MÉTRICAS DEL SISTEMA
# ============================================================================

def get_system_metrics():
    """Obtiene métricas generales del sistema."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        metrics = {}
        
        # Conteo de pacientes
        cursor.execute("SELECT COUNT(*) as total FROM patients")
        metrics['total_patients'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as ingreso FROM patients WHERE estado = 'ingreso'")
        metrics['patients_ingreso'] = cursor.fetchone()['ingreso']
        
        cursor.execute("SELECT COUNT(*) as egreso FROM patients WHERE estado = 'egreso'")
        metrics['patients_egreso'] = cursor.fetchone()['egreso']
        
        # Conteo de usuarios
        cursor.execute("SELECT COUNT(*) as total FROM users")
        metrics['total_users'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE is_active = TRUE")
        metrics['active_users'] = cursor.fetchone()['active']
        
        # Conteo de evoluciones
        cursor.execute("SELECT COUNT(*) as total FROM evoluciones")
        metrics['total_evoluciones'] = cursor.fetchone()['total']
        
        # Conteo de protocolos
        cursor.execute("SELECT COUNT(*) as total FROM protocols")
        metrics['total_protocols'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as active FROM protocols WHERE status = 'active'")
        metrics['active_protocols'] = cursor.fetchone()['active']
        
        # Conteo de inscripciones
        cursor.execute("SELECT COUNT(*) as total FROM protocol_enrollments")
        metrics['total_enrollments'] = cursor.fetchone()['total']
        
        # Instituciones
        cursor.execute("SELECT COUNT(*) as total FROM institutions")
        metrics['total_institutions'] = cursor.fetchone()['total']
        
        return metrics


# ============================================================================
# GESTIÓN DE USUARIOS
# ============================================================================

def get_all_users():
    """Obtiene todos los usuarios con información de institución."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT u.*, i.name as institution_name, i.code as institution_code
            FROM users u
            LEFT JOIN institutions i ON u.institution_id = i.id
            ORDER BY u.created_at DESC
        """)
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def get_user_by_id_admin(user_id):
    """Obtiene un usuario por ID (para admin)."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT u.*, i.name as institution_name
            FROM users u
            LEFT JOIN institutions i ON u.institution_id = i.id
            WHERE u.id = %s
        """, (user_id,))
        row = cursor.fetchone()
        return dict_from_row(row)


def create_user_admin(username, email, password, full_name=None, institution_id=None, role='user'):
    """Crea un usuario desde el panel de admin."""
    password_hash = generate_password_hash(password)
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, institution_id, role, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id
        """, (username, email, password_hash, full_name, institution_id, role))
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id


def update_user_admin(user_id, user_data):
    """Actualiza un usuario desde admin."""
    allowed_fields = ['username', 'email', 'full_name', 'institution_id', 'role', 'is_active', 'is_verified']
    
    # Filtrar solo campos permitidos y no nulos
    filtered = {k: v for k, v in user_data.items() if k in allowed_fields and v is not None}
    
    if not filtered:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered.keys()])
    values = list(filtered.values()) + [user_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = %s", values)
        conn.commit()
        return cursor.rowcount > 0


def reset_user_password(user_id, new_password):
    """Resetea la contraseña de un usuario."""
    password_hash = generate_password_hash(new_password)
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def toggle_user_active(user_id):
    """Activa/desactiva un usuario."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            "UPDATE users SET is_active = NOT is_active WHERE id = %s RETURNING is_active",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.commit()
        return result[0] if result else None


def delete_user_admin(user_id):
    """Elimina un usuario (y sus sesiones)."""
    with get_db_cursor() as (cursor, conn):
        # Primero eliminar sesiones
        cursor.execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
        # Luego el usuario
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# GESTIÓN DE INSTITUCIONES
# ============================================================================

def get_all_institutions():
    """Obtiene todas las instituciones."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT i.*, COUNT(u.id) as user_count
            FROM institutions i
            LEFT JOIN users u ON i.id = u.institution_id
            GROUP BY i.id
            ORDER BY i.name
        """)
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def create_institution(name, code, country='México', state=None, city=None, 
                       type_='public', contact_email=None, contact_phone=None, 
                       contact_person=None):
    """Crea una nueva institución."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO institutions (name, code, country, state, city, type, 
                                      contact_email, contact_phone, contact_person, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
            RETURNING id
        """, (name, code.upper(), country, state, city, type_, contact_email, contact_phone, contact_person))
        inst_id = cursor.fetchone()[0]
        conn.commit()
        return inst_id


def update_institution(inst_id, inst_data):
    """Actualiza una institución."""
    allowed_fields = ['name', 'code', 'country', 'state', 'city', 'type', 
                      'contact_email', 'contact_phone', 'contact_person', 'status']
    
    filtered = {k: v for k, v in inst_data.items() if k in allowed_fields and v is not None}
    
    if not filtered:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered.keys()])
    values = list(filtered.values()) + [inst_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(f"UPDATE institutions SET {set_clause} WHERE id = %s", values)
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# GESTIÓN DE PROTOCOLOS
# ============================================================================

def get_all_protocols(status=None):
    """Obtiene todos los protocolos."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        if status:
            cursor.execute("""
                SELECT p.*, u.username as created_by_name
                FROM protocols p
                LEFT JOIN users u ON p.created_by = u.id
                WHERE p.status = %s
                ORDER BY p.created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT p.*, u.username as created_by_name
                FROM protocols p
                LEFT JOIN users u ON p.created_by = u.id
                ORDER BY p.created_at DESC
            """)
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def get_protocol_by_id(protocol_id):
    """Obtiene un protocolo por ID."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT p.*, u.username as created_by_name,
                   ru.username as reviewed_by_name
            FROM protocols p
            LEFT JOIN users u ON p.created_by = u.id
            LEFT JOIN users ru ON p.reviewed_by = ru.id
            WHERE p.id = %s
        """, (protocol_id,))
        row = cursor.fetchone()
        return dict_from_row(row)


def create_protocol(slug, name, description, objective, form_definition, 
                    visits=None, inclusion_criteria=None, exclusion_criteria=None,
                    pi_name=None, pi_email=None, pi_institution=None,
                    created_by=None):
    """Crea un nuevo protocolo."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO protocols (slug, name, description, objective, form_definition,
                                visits, inclusion_criteria, exclusion_criteria,
                                pi_name, pi_email, pi_institution, created_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
            RETURNING id
        """, (slug, name, description, objective, json.dumps(form_definition),
              json.dumps(visits) if visits else '[]',
              inclusion_criteria or [], exclusion_criteria or [],
              pi_name, pi_email, pi_institution, created_by))
        protocol_id = cursor.fetchone()[0]
        conn.commit()
        return protocol_id


def update_protocol(protocol_id, protocol_data):
    """Actualiza un protocolo."""
    allowed_fields = ['slug', 'name', 'description', 'objective', 'form_definition',
                      'visits', 'inclusion_criteria', 'exclusion_criteria',
                      'pi_name', 'pi_email', 'pi_institution', 'status', 'version']
    
    filtered = {}
    for k, v in protocol_data.items():
        if k in allowed_fields and v is not None:
            if k in ['form_definition', 'visits']:
                filtered[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
            else:
                filtered[k] = v
    
    if not filtered:
        return False
    
    set_clause = ', '.join([f"{k} = %s" for k in filtered.keys()])
    values = list(filtered.values()) + [protocol_id]
    
    with get_db_cursor() as (cursor, conn):
        cursor.execute(f"UPDATE protocols SET {set_clause} WHERE id = %s", values)
        conn.commit()
        return cursor.rowcount > 0


def approve_protocol(protocol_id, reviewed_by, review_notes=None):
    """Aprueba un protocolo (cambia status a 'active')."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            UPDATE protocols 
            SET status = 'active', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP, review_notes = %s
            WHERE id = %s
        """, (reviewed_by, review_notes, protocol_id))
        conn.commit()
        return cursor.rowcount > 0


def close_protocol(protocol_id):
    """Cierra un protocolo (cambia status a 'closed')."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("UPDATE protocols SET status = 'closed' WHERE id = %s", (protocol_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_protocol(protocol_id):
    """Elimina un protocolo (y sus inscripciones/respuestas en cascada)."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("DELETE FROM protocols WHERE id = %s", (protocol_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# INSCRIPCIÓN DE PACIENTES EN PROTOCOLOS
# ============================================================================

def get_patient_enrollments(patient_id):
    """Obtiene todos los protocolos en los que está inscrito un paciente."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT pe.*, p.name as protocol_name, p.slug as protocol_slug, p.status as protocol_status
            FROM protocol_enrollments pe
            JOIN protocols p ON pe.protocol_id = p.id
            WHERE pe.patient_id = %s
            ORDER BY pe.enrolled_at DESC
        """, (patient_id,))
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def get_protocol_enrollments(protocol_id):
    """Obtiene todos los pacientes inscritos en un protocolo."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT pe.*, p.nombre_completo as patient_name, p.expediente, p.estado
            FROM protocol_enrollments pe
            JOIN patients p ON pe.patient_id = p.id
            WHERE pe.protocol_id = %s
            ORDER BY pe.enrolled_at DESC
        """, (protocol_id,))
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def enroll_patient(patient_id, protocol_id, enrolled_by, institution_id=None):
    """Inscribe un paciente en un protocolo."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO protocol_enrollments (patient_id, protocol_id, enrolled_by, institution_id, status)
            VALUES (%s, %s, %s, %s, 'active')
            ON CONFLICT (patient_id, protocol_id) DO NOTHING
            RETURNING id
        """, (patient_id, protocol_id, enrolled_by, institution_id))
        result = cursor.fetchone()
        conn.commit()
        return result[0] if result else None


def update_enrollment_status(enrollment_id, status, reason=None):
    """Actualiza el estado de una inscripción."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            UPDATE protocol_enrollments 
            SET status = %s, withdrawal_reason = %s
            WHERE id = %s
        """, (status, reason, enrollment_id))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# RESPUESTAS DE FORMULARIOS
# ============================================================================

def get_responses_by_enrollment(enrollment_id):
    """Obtiene todas las respuestas de una inscripción."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT pr.*, u.username as submitted_by_name
            FROM protocol_responses pr
            LEFT JOIN users u ON pr.submitted_by = u.id
            WHERE pr.enrollment_id = %s
            ORDER BY pr.visit_date, pr.submitted_at
        """, (enrollment_id,))
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]


def save_response(enrollment_id, visit_name, visit_date, form_data, key_outcomes=None, submitted_by=None):
    """Guarda una respuesta de formulario."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO protocol_responses (enrollment_id, visit_name, visit_date, form_data, key_outcomes, submitted_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (enrollment_id, visit_name, visit_date, json.dumps(form_data),
              json.dumps(key_outcomes) if key_outcomes else '{}', submitted_by))
        response_id = cursor.fetchone()[0]
        conn.commit()
        return response_id


def update_response(response_id, form_data, key_outcomes=None):
    """Actualiza una respuesta existente."""
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            UPDATE protocol_responses 
            SET form_data = %s, key_outcomes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (json.dumps(form_data), json.dumps(key_outcomes) if key_outcomes else '{}', response_id))
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# MÉTRICAS DE COMPLETITUD
# ============================================================================

def get_patient_completeness(patient_id=None):
    """Calcula la completitud de los expedientes."""
    # Campos críticos por categoría
    critical_fields = {
        'identificacion': ['nombre_completo', 'edad', 'sexo', 'expediente'],
        'neurologico': ['glasgow', 'rass', 'cpot'],
        'hemodinamico': ['tas', 'tad', 'tam', 'fc'],
        'ventilatorio': ['fr', 'sao2', 'fio2', 'modo_ventilatorio'],
        'hidrico': ['balance', 'diuresis_total'],
        'renal': ['creatinina', 'urea', 'sodio', 'potasio'],
        'gastro': ['tipo_nutricion', 'volumen_aporte'],
        'gasometria': ['gasometria_ph', 'gasometria_pco2', 'pafi']
    }
    
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        # Obtener todos los pacientes o uno específico
        if patient_id:
            cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        else:
            cursor.execute("SELECT * FROM patients LIMIT 100")  # Limitar para performance
        
        patients = cursor.fetchall()
        
        results = []
        for patient in patients:
            patient_dict = dict_from_row(patient)
            completeness = {}
            
            for category, fields in critical_fields.items():
                total = len(fields)
                filled = sum(1 for f in fields if patient_dict.get(f) not in [None, '', 'N/A'])
                completeness[category] = {
                    'filled': filled,
                    'total': total,
                    'percent': round((filled / total) * 100, 1) if total > 0 else 0
                }
            
            overall = sum(c['percent'] for c in completeness.values()) / len(completeness) if completeness else 0
            
            results.append({
                'patient_id': patient_dict.get('id'),
                'patient_name': patient_dict.get('nombre_completo'),
                'expediente': patient_dict.get('expediente'),
                'completeness': completeness,
                'overall_percent': round(overall, 1)
            })
        
        return results


def get_global_completeness():
    """Calcula métricas globales de completitud."""
    patients = get_patient_completeness()
    
    if not patients:
        return {}
    
    categories = list(patients[0]['completeness'].keys())
    
    global_stats = {}
    for cat in categories:
        values = [p['completeness'][cat]['percent'] for p in patients]
        global_stats[cat] = {
            'mean': round(sum(values) / len(values), 1),
            'min': round(min(values), 1),
            'max': round(max(values), 1)
        }
    
    overall_values = [p['overall_percent'] for p in patients]
    global_stats['overall'] = {
        'mean': round(sum(overall_values) / len(overall_values), 1),
        'min': round(min(overall_values), 1),
        'max': round(max(overall_values), 1)
    }
    
    return global_stats


# ============================================================================
# EXPORTACIÓN DE COHORTE
# ============================================================================

def export_protocol_data(protocol_id, include_pii=False):
    """Exporta los datos de un protocolo para análisis."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        cursor.execute("""
            SELECT 
                pe.cohort_id,
                pe.enrolled_at,
                pe.status as enrollment_status,
                pr.visit_name,
                pr.visit_date,
                pr.form_data,
                pr.key_outcomes,
                i.code as institution_code,
                i.country
            FROM protocol_enrollments pe
            JOIN protocols p ON pe.protocol_id = p.id
            JOIN institutions i ON pe.institution_id = i.id
            LEFT JOIN protocol_responses pr ON pe.id = pr.enrollment_id
            WHERE pe.protocol_id = %s AND pe.share_data = TRUE
            ORDER BY pe.cohort_id, pr.visit_name
        """, (protocol_id,))
        
        rows = cursor.fetchall()
        
        # Flatten JSONB data
        flattened = []
        for row in rows:
            flat = dict_from_row(row)
            # Expand form_data keys
            if flat.get('form_data'):
                for key, value in flat['form_data'].items():
                    flat[f"form_{key}"] = value
                del flat['form_data']
            flattened.append(flat)
        
        return flattened


def get_protocol_summary(protocol_id):
    """Obtiene resumen estadístico de un protocolo."""
    with get_db_cursor(RealDictCursor) as (cursor, conn):
        # Totales
        cursor.execute("""
            SELECT 
                COUNT(*) as total_enrolled,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'withdrawn' THEN 1 END) as withdrawn,
                COUNT(DISTINCT institution_id) as institutions
            FROM protocol_enrollments
            WHERE protocol_id = %s
        """, (protocol_id,))
        summary = dict_from_row(cursor.fetchone())
        
        # Timeline de reclutamiento (últimos 30 días)
        cursor.execute("""
            SELECT DATE(enrolled_at) as date, COUNT(*) as count
            FROM protocol_enrollments
            WHERE protocol_id = %s AND enrolled_at > CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(enrolled_at)
            ORDER BY date
        """, (protocol_id,))
        summary['timeline'] = [dict_from_row(r) for r in cursor.fetchall()]
        
        return summary
