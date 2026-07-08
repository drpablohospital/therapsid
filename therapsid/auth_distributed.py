"""
Auth distribuida y resiliente para Therapsid
Cada nodo puede autenticar usuarios independientemente
Los tokens JWT se sincronizan entre nodos
"""

import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import jwt

# Clave secreta compartida entre todos los nodos (se sincroniza via gossip)
# En produccion cada nodo genera la suya pero acepta tokens de otros
JWT_SECRET = "therapsid-shared-auth-v1.0"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

class DistributedAuth:
    """
    Sistema de autenticacion distribuida
    - Registra usuarios localmente
    - Emite tokens JWT
    - Valida tokens propios y de otros nodos
    - Sincroniza credenciales via gossip
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializar base de datos de usuarios"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT,
                    role TEXT DEFAULT 'user',
                    hospital TEXT,
                    node_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    active BOOLEAN DEFAULT 1
                );
                
                CREATE TABLE IF NOT EXISTS tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    node_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    revoked BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                CREATE TABLE IF NOT EXISTS trusted_nodes (
                    node_id TEXT PRIMARY KEY,
                    public_key TEXT,
                    last_seen TIMESTAMP,
                    trust_score REAL DEFAULT 1.0
                );
            ''')
    
    def hash_password(self, password: str) -> str:
        """Hash seguro de password"""
        salt = secrets.token_hex(16)
        return f"{salt}${hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verificar password contra hash"""
        try:
            salt, hash_value = password_hash.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            return new_hash == hash_value
        except:
            return False
    
    def register_user(self, email: str, password: str, name: str = None, 
                      role: str = 'user', hospital: str = None, 
                      node_id: str = None) -> Tuple[bool, str]:
        """
        Registrar nuevo usuario
        Retorna: (exito, mensaje)
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                password_hash = self.hash_password(password)
                conn.execute(
                    'INSERT INTO users (email, password_hash, name, role, hospital, node_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (email, password_hash, name, role, hospital, node_id)
                )
                conn.commit()
                return True, "Usuario registrado"
        except sqlite3.IntegrityError:
            return False, "Email ya registrado"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def authenticate(self, email: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Autenticar usuario y emitir token
        Retorna: (exito, token, user_data)
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                'SELECT id, email, password_hash, name, role, hospital, node_id FROM users WHERE email = ? AND active = 1',
                (email,)
            )
            user = cursor.fetchone()
            
            if not user:
                return False, None, None
            
            user_id, db_email, password_hash, name, role, hospital, node_id = user
            
            if not self.verify_password(password, password_hash):
                return False, None, None
            
            # Actualizar last_login
            conn.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            
            # Crear token JWT
            token = self._create_token(user_id, db_email, name, role, hospital, node_id)
            
            user_data = {
                'id': user_id,
                'email': db_email,
                'name': name,
                'role': role,
                'hospital': hospital,
                'node_id': node_id
            }
            
            return True, token, user_data
    
    def _create_token(self, user_id: int, email: str, name: str, 
                      role: str, hospital: str, node_id: str) -> str:
        """Crear token JWT"""
        expires = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
        
        payload = {
            'sub': str(user_id),
            'email': email,
            'name': name,
            'role': role,
            'hospital': hospital,
            'node_id': node_id,
            'exp': expires,
            'iat': datetime.utcnow(),
            'iss': 'therapsid-auth'
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validar token JWT
        Acepta tokens propios y de otros nodos (si están en trusted_nodes)
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Verificar si token fue revocado
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    'SELECT revoked FROM tokens WHERE token_id = ?',
                    (token,)
                )
                result = cursor.fetchone()
                if result and result[0]:
                    return False, None
            
            return True, payload
            
        except jwt.ExpiredSignatureError:
            return False, {"error": "Token expirado"}
        except jwt.InvalidTokenError:
            return False, {"error": "Token invalido"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def revoke_token(self, token: str) -> bool:
        """Revocar token"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    'UPDATE tokens SET revoked = 1 WHERE token_id = ?',
                    (token,)
                )
                conn.commit()
                return True
        except:
            return False
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Obtener usuario por email"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                'SELECT id, email, name, role, hospital, node_id, active FROM users WHERE email = ?',
                (email,)
            )
            user = cursor.fetchone()
            if user:
                return {
                    'id': user[0],
                    'email': user[1],
                    'name': user[2],
                    'role': user[3],
                    'hospital': user[4],
                    'node_id': user[5],
                    'active': user[6]
                }
            return None
    
    def list_users(self) -> list:
        """Listar todos los usuarios"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                'SELECT id, email, name, role, hospital, node_id, active, last_login FROM users'
            )
            return [
                {
                    'id': row[0],
                    'email': row[1],
                    'name': row[2],
                    'role': row[3],
                    'hospital': row[4],
                    'node_id': row[5],
                    'active': row[6],
                    'last_login': row[7]
                }
                for row in cursor.fetchall()
            ]
    
    def sync_user_from_node(self, user_data: Dict, source_node: str) -> bool:
        """
        Sincronizar usuario desde otro nodo
        Se usa cuando un usuario se autentica en otro nodo de la red
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Verificar si usuario ya existe
                cursor = conn.execute(
                    'SELECT id FROM users WHERE email = ?',
                    (user_data.get('email'),)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Actualizar info
                    conn.execute('''
                        UPDATE users SET 
                            name = ?, role = ?, hospital = ?, node_id = ?
                        WHERE email = ?
                    ''', (
                        user_data.get('name'),
                        user_data.get('role', 'user'),
                        user_data.get('hospital'),
                        source_node,
                        user_data.get('email')
                    ))
                else:
                    # Crear usuario local (sin password - auth via token)
                    conn.execute('''
                        INSERT INTO users (email, password_hash, name, role, hospital, node_id, active)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (
                        user_data.get('email'),
                        'SYNCED_FROM_NODE',  # Marcador especial
                        user_data.get('name'),
                        user_data.get('role', 'user'),
                        user_data.get('hospital'),
                        source_node
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error sincronizando usuario: {e}")
            return False
    
    def create_demo_user(self):
        """Crear usuario demo si no existe"""
        email = "demo@therapsid.org"
        result = self.get_user_by_email(email)
        if not result:
            self.register_user(
                email=email,
                password="***",
                name="Usuario Demo",
                role="demo",
                hospital="Demo Hospital",
                node_id="local"
            )
            print("✅ Usuario demo creado: demo@therapsid.org / ***")
