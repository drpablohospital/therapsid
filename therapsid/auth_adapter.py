"""
Therapsid Auth Adapter
======================
Integra el sistema de autenticación de SINAPSID en Therapsid.
Usa las mismas tablas users, user_sessions de SINAPSID DMA.
Roles: admin, coordinator, clinician, visitor
"""

import hashlib
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


class SinapsidAuthAdapter:
    """Adaptador que conecta Therapsid con el auth de Sinapsid"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa el adaptador de autenticación.
        
        Args:
            db_path: Ruta a la base de datos de Sinapsid (PostgreSQL o SQLite)
                  Si es None, usa la base de datos local de Therapsid
        """
        self.db_path = db_path
        self._users_cache: Dict[str, Any] = {}
    
    def _get_db(self):
        """Obtiene conexión a base de datos (placeholder para integración real)"""
        # TODO: Integrar con modules.database de Sinapsid
        # Por ahora, usa JSON local para modo standalone
        pass
    
    def hash_password(self, password: str) -> str:
        """Genera hash seguro compatible con Sinapsid"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                       salt.encode('utf-8'), 100000)
        return f"{salt}${hash_obj.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica contraseña contra hash de Sinapsid"""
        try:
            salt, hash_value = password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                           salt.encode('utf-8'), 100000)
            return hash_obj.hex() == hash_value
        except:
            return False
    
    def create_session_token(self, user_id: int) -> str:
        """Crea token de sesión compatible con Sinapsid"""
        return secrets.token_urlsafe(32)
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Valida token de sesión"""
        # TODO: Verificar contra tabla user_sessions de Sinapsid
        # Por ahora, acepta cualquier token válido (placeholder)
        if not token or len(token) < 20:
            return None
        return {
            'user_id': 0,
            'role': 'visitor',
            'is_active': True
        }
    
    def get_user_role(self, username: str) -> str:
        """
        Obtiene rol de usuario:
        - admin: Administrador de red (ve todos los nodos)
        - coordinator: Coordinador de hospital (ve nodos de su región)
        - clinician: Médico tratante (ve solo su nodo)
        - visitor: Visitante (solo lectura demo)
        """
        # TODO: Consultar tabla users de Sinapsid
        return 'visitor'
    
    def can_view_node(self, user_role: str, node_region: str, 
                      user_region: str) -> bool:
        """Verifica si un usuario puede ver un nodo"""
        if user_role == 'admin':
            return True
        if user_role == 'coordinator':
            return node_region == user_region
        if user_role == 'clinician':
            return node_region == user_region
        return False  # visitor
    
    def can_send_data(self, user_role: str) -> bool:
        """Verifica si el rol puede enviar datos a la red"""
        return user_role in ('admin', 'coordinator', 'clinician')
    
    def can_receive_data(self, user_role: str) -> bool:
        """Verifica si el rol puede recibir datos sincronizados"""
        return user_role in ('admin', 'coordinator', 'clinician')


class AuthMiddleware:
    """Middleware de autenticación para endpoints HTTP de Therapsid"""
    
    def __init__(self, auth_adapter: SinapsidAuthAdapter):
        self.auth = auth_adapter
    
    async def authenticate_request(self, request) -> Optional[Dict]:
        """
        Extrae y valida token de una petición HTTP.
        Soporta header Authorization Bearer y cookie.
        """
        token = None
        
        # Header Authorization: Bearer <token>
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        # Cookie therapsid_session
        if not token:
            token = request.cookies.get('therapsid_session')
        
        if not token:
            return None
        
        return self.auth.validate_session(token)
    
    def require_role(self, *roles):
        """Decorador para requerir rol específico"""
        def decorator(handler):
            async def wrapper(request):
                user = await self.authenticate_request(request)
                if not user:
                    return web.json_response({'error': 'No autenticado'}, status=401)
                if user.get('role') not in roles:
                    return web.json_response({'error': 'Sin permisos'}, status=403)
                return await handler(request, user)
            return wrapper
        return decorator


# Instancia global (lazy)
_auth_instance: Optional[SinapsidAuthAdapter] = None

def get_auth() -> SinapsidAuthAdapter:
    """Obtiene instancia singleton de autenticación"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = SinapsidAuthAdapter()
    return _auth_instance
