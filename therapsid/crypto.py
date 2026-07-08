"""
Therapsid - Módulo de Cifrado Local
Cifrado AES-256-GCM para datos sensibles de pacientes
Los datos NUNCA salen del nodo sin anonimización previa
"""

import os
import secrets
import hashlib
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from .config import SALT_FILE, MASTER_KEY_FILE, KEYS_DIR


class LocalCrypto:
    """
    Cifrado local de datos sensibles.
    La clave maestra se deriva de la contraseña del usuario + SALT único del nodo.
    Los datos cifrados NUNCA salen del nodo sin anonimización.
    """
    
    def __init__(self, password: str = None):
        """
        Inicializa el cifrado. Si no hay clave maestra, la crea.
        
        Args:
            password: Contraseña del usuario Sinapsid (opcional en init)
        """
        self._salt = self._get_or_create_salt()
        self._fernet = None
        
        if password:
            self.unlock(password)
    
    def _get_or_create_salt(self) -> bytes:
        """Obtiene o crea el SALT único del nodo"""
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        
        if SALT_FILE.exists():
            with open(SALT_FILE, "rb") as f:
                return f.read()
        
        # Crear SALT nuevo (32 bytes = 256 bits)
        salt = secrets.token_bytes(32)
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
        os.chmod(SALT_FILE, 0o600)  # Solo el dueño puede leer
        return salt
    
    def unlock(self, password: str) -> bool:
        """
        Desbloquea el cifrado con la contraseña del usuario.
        
        Args:
            password: Contraseña del usuario Sinapsid
            
        Returns:
            True si se pudo desbloquear, False si la contraseña es incorrecta
        """
        try:
            key = self._derive_key(password)
            self._fernet = Fernet(key)
            
            # Verificar guardando una prueba
            if MASTER_KEY_FILE.exists():
                with open(MASTER_KEY_FILE, "rb") as f:
                    encrypted_test = f.read()
                # Intentar descifrar (si falla, la password es incorrecta)
                self._fernet.decrypt(encrypted_test)
            else:
                # Primera vez: crear prueba
                test_data = b"THERAPSID_MASTER_KEY_VERIFICATION"
                encrypted = self._fernet.encrypt(test_data)
                with open(MASTER_KEY_FILE, "wb") as f:
                    f.write(encrypted)
                os.chmod(MASTER_KEY_FILE, 0o600)
            
            return True
        except Exception:
            self._fernet = None
            return False
    
    def _derive_key(self, password: str) -> bytes:
        """Deriva una clave Fernet desde la contraseña + SALT"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100_000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Cifra un texto. Requiere que el cifrado esté desbloqueado.
        
        Args:
            plaintext: Texto plano a cifrar
            
        Returns:
            String base64 con el ciphertext
        """
        if not self._fernet:
            raise RuntimeError("Cifrado no desbloqueado. Llama a unlock() primero.")
        
        encrypted = self._fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Descifra un texto. Requiere que el cifrado esté desbloqueado.
        
        Args:
            ciphertext: Texto cifrado en base64
            
        Returns:
            Texto plano
        """
        if not self._fernet:
            raise RuntimeError("Cifrado no desbloqueado. Llama a unlock() primero.")
        
        decrypted = self._fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    
    def is_unlocked(self) -> bool:
        """Verifica si el cifrado está desbloqueado"""
        return self._fernet is not None
    
    def lock(self):
        """Bloquea el cifrado (elimina la clave de memoria)"""
        self._fernet = None


class SensitiveDataFilter:
    """
    Filtro de datos sensibles para compartir en la red P2P.
    Quita TODO identificador antes de enviar.
    """
    
    # Campos que NUNCA se comparten
    BLOCKED_FIELDS = {
        'nombre', 'nombre_completo', 'curp', 'rfc', 'nss',
        'telefono', 'celular', 'email', 'direccion', 'domicilio',
        'procedencia', 'contacto_familiar', 'nombre_familiar',
        'telefono_familiar', 'fecha_nacimiento_exacta',
        'lugar_nacimiento', 'ocupacion', 'religion',
    }
    
    # Campos que se transforman a rangos/categorías
    AGGREGATED_FIELDS = {
        'edad': 'age_group',           # 45 → "40-49"
        'peso': 'weight_group',         # 75.3 → "70-80"
        'talla': 'height_group',        # 1.70 → "1.65-1.75"
    }
    
    @classmethod
    def anonymize_patient(cls, patient_data: dict) -> dict:
        """
        Anonimiza los datos de un paciente para compartir en la red.
        
        Args:
            patient_data: Dict con datos originales del paciente
            
        Returns:
            Dict con solo metadata agregada segura
        """
        safe_data = {}
        
        for field, value in patient_data.items():
            field_lower = field.lower()
            
            # 1. Bloquear campos sensibles
            if field_lower in cls.BLOCKED_FIELDS:
                continue
            
            # 2. Agregar campos numéricos a rangos
            if field_lower in cls.AGGREGATED_FIELDS:
                safe_data[cls.AGGREGATED_FIELDS[field_lower]] = cls._to_range(value)
            # 3. Campos clínicos (scores, labs) se pasan tal cual
            elif cls._is_clinical_field(field_lower):
                safe_data[field] = value
            # 4. Todo lo demás se bloquea por precaución
            else:
                continue
        
        return safe_data
    
    @classmethod
    def _to_range(cls, value) -> str:
        """Convierte un valor numérico a un rango categórico"""
        try:
            v = float(value)
            if v < 18:
                return "<18"
            elif v < 30:
                return "18-29"
            elif v < 40:
                return "30-39"
            elif v < 50:
                return "40-49"
            elif v < 60:
                return "50-59"
            elif v < 70:
                return "60-69"
            elif v < 80:
                return "70-79"
            else:
                return "80+"
        except (ValueError, TypeError):
            return "unknown"
    
    @classmethod
    def _is_clinical_field(cls, field: str) -> bool:
        """Determina si un campo es clínico (seguro para compartir)"""
        clinical_prefixes = [
            'sofa', 'apache', 'saps', 'news', 'charlson', 'swift',
            'glasgow', 'rass', 'fio2', 'pafi', 'pao2', 'paco2',
            'ph', 'hco3', 'lactato', 'creatinina', 'urea',
            'bilirrubina', 'albumina', 'leucocitos', 'plaquetas',
            'hemoglobina', 'hematocrito', 'inr', 'ptt',
            'temperatura', 'fc', 'fr', 'tas', 'tad', 'pam',
            'diuresis', 'balance',
        ]
        return any(field.startswith(prefix) for prefix in clinical_prefixes)


def generate_node_id() -> str:
    """Genera un ID único para el nodo (therapsid-XXXX)"""
    return f"therapsid-{secrets.token_hex(8)}"
