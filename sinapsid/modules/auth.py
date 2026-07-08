"""
SINAPSID DMA - Sistema de Autenticación
=======================================
Maneja usuarios, sesiones y autenticación.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request
from modules.database import get_db_connection
import hashlib
import secrets
from datetime import datetime, timedelta


def init_auth_tables():
    """Inicializa las tablas de autenticación si no existen."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                institution VARCHAR(255),
                role VARCHAR(50) DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                session_token VARCHAR(255)
            )
        """)
        
        # Tabla de sesiones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Tabla de aplicaciones beta
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS beta_applications (
                id SERIAL PRIMARY KEY,
                institution VARCHAR(255) NOT NULL,
                institution_type VARCHAR(100),
                contact_name VARCHAR(255) NOT NULL,
                role VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL,
                country VARCHAR(100),
                use_case TEXT NOT NULL,
                research_interest BOOLEAN DEFAULT FALSE,
                donation_interest BOOLEAN DEFAULT FALSE,
                ref_code VARCHAR(50) UNIQUE NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER REFERENCES users(id)
            )
        """)
        
        conn.commit()


def hash_password(password):
    """Genera hash seguro de contraseña."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${hash_obj.hex()}"


def verify_password(password, password_hash):
    """Verifica contraseña contra hash."""
    try:
        salt, hash_value = password_hash.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hash_obj.hex() == hash_value
    except:
        return False


def create_user(username, email, password, full_name=None, institution=None, role='user'):
    """Crea un nuevo usuario."""
    password_hash = hash_password(password)
    # Normalizar a lowercase para consistencia
    username = username.lower() if username else username
    email = email.lower() if email else email
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, institution, role)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (username, email, password_hash, full_name, institution, role))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            return user_id
        except Exception as e:
            conn.rollback()
            print(f"Error creating user: {e}")
            return None


def authenticate_user(username_or_email, password):
    """Autentica usuario por username/email y password."""
    # Normalizar a lowercase para comparación case-insensitive
    normalized = username_or_email.lower() if username_or_email else username_or_email
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Buscar por lowercase para soportar login case-insensitive
        cursor.execute("""
            SELECT id, username, email, password_hash, full_name, institution, role, is_active
            FROM users 
            WHERE (LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)) AND is_active = TRUE
        """, (normalized, normalized))
        
        user = cursor.fetchone()
        
        if user and verify_password(password, user[3]):
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[4],
                'institution': user[5],
                'role': user[6],
                'is_active': user[7]
            }
        return None


def get_user_by_id(user_id):
    """Obtiene usuario por ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, full_name, institution, role, is_active, created_at
            FROM users WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3],
                'institution': user[4],
                'role': user[5],
                'is_active': user[6],
                'created_at': user[7]
            }
        return None


def create_session(user_id, ip_address=None, user_agent=None):
    """Crea nueva sesión para usuario."""
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)  # Sesión válida por 30 días
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, session_token, ip_address, user_agent, expires_at))
        
        # Actualizar last_login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
        
        conn.commit()
        
        return session_token


def validate_session(session_token):
    """Valida token de sesión."""
    if not session_token:
        return None
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT us.user_id, us.expires_at, u.username, u.email, u.full_name, u.institution, u.role
            FROM user_sessions us
            JOIN users u ON us.user_id = u.id
            WHERE us.session_token = %s AND us.is_active = TRUE AND us.expires_at > CURRENT_TIMESTAMP
            AND u.is_active = TRUE
        """, (session_token,))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[2],
                'email': result[3],
                'full_name': result[4],
                'institution': result[5],
                'role': result[6]
            }
        return None


def invalidate_session(session_token):
    """Invalida token de sesión (logout)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_sessions SET is_active = FALSE WHERE session_token = %s
        """, (session_token,))
        
        conn.commit()


def _is_api_request():
    """Detecta si la petición es una llamada API (fetch/XHR)."""
    # Si la ruta empieza con /api/, es una API call
    if request.path.startswith('/api/'):
        return True
    # Si el Accept header prefiere JSON
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept:
        return True
    # Si es una petición XHR
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    return False


def login_required(f):
    """Decorador que requiere autenticación."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get('session_token')
        is_api = _is_api_request()
        
        if not session_token:
            if is_api or request.is_json:
                return {'error': 'Autenticación requerida. Inicia sesión nuevamente.'}, 401
            flash('Por favor inicie sesión para acceder', 'warning')
            return redirect(url_for('landing'))
        
        user = validate_session(session_token)
        if not user:
            session.pop('session_token', None)
            if is_api or request.is_json:
                return {'error': 'Sesión inválida o expirada. Inicia sesión nuevamente.'}, 401
            flash('Sesión expirada, por favor inicie sesión nuevamente', 'warning')
            return redirect(url_for('landing'))
        
        # Agregar usuario a request para uso en vistas
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(role):
    """Decorador que requiere rol específico."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return redirect(url_for('landing'))
            
            if request.current_user['role'] not in (role if isinstance(role, (list, tuple)) else [role]):
                flash('No tiene permisos para acceder a esta sección', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def save_beta_application(data):
    """Guarda aplicación beta en base de datos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO beta_applications 
                (institution, institution_type, contact_name, role, email, country, 
                 use_case, research_interest, donation_interest, ref_code, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data.get('institution'),
                data.get('institution_type'),
                data.get('contact_name'),
                data.get('role'),
                data.get('email'),
                data.get('country'),
                data.get('use_case'),
                data.get('research_interest', False),
                data.get('donation_interest', False),
                data.get('ref_code'),
                'pending'
            ))
            
            app_id = cursor.fetchone()[0]
            conn.commit()
            return app_id
        except Exception as e:
            conn.rollback()
            print(f"Error saving beta application: {e}")
            return None


def get_public_stats():
    """Obtiene estadísticas públicas seguras."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Contar usuarios activos (sin información sensible)
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        user_count = cursor.fetchone()[0]
        
        # Contar aplicaciones beta aprobadas
        cursor.execute("SELECT COUNT(*) FROM beta_applications WHERE status = 'approved'")
        beta_count = cursor.fetchone()[0]
        
        return {
            'users': user_count,
            'beta_participants': beta_count,
            'status': 'operational'
        }


# Inicializar tablas al importar
init_auth_tables()
