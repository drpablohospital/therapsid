"""
Therapsid - Tests
Pruebas unitarias para todos los módulos
"""

import unittest
import tempfile
import os
import json
from datetime import datetime

from pathlib import Path
from therapsid.config import NodeConfig, ensure_directories, CONFIG_FILE
from therapsid.crypto import LocalCrypto, SensitiveDataFilter, generate_node_id
from therapsid.sync import P2PSyncManager, DeltaSync, SyncPacket


class TestCrypto(unittest.TestCase):
    """Tests de criptografía"""
    
    def setUp(self):
        # Usar SALT único para tests (evitar conflicto con config real)
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        # Modificar SALT_FILE temporalmente
        from therapsid import crypto
        self.original_salt = crypto.SALT_FILE
        crypto.SALT_FILE = Path(self.temp_dir) / ".salt"
        crypto.MASTER_KEY_FILE = Path(self.temp_dir) / ".master"
        
        self.crypto = LocalCrypto()
        self.crypto.unlock("test-password")
    
    def tearDown(self):
        # Restaurar SALT_FILE original
        from therapsid import crypto
        crypto.SALT_FILE = self.original_salt
    
    def test_encrypt_decrypt(self):
        """Probar cifrado y descifrado"""
        original = "Juan Pérez García"
        encrypted = self.crypto.encrypt(original)
        decrypted = self.crypto.decrypt(encrypted)
        self.assertEqual(original, decrypted)
    
    def test_encrypt_deterministic(self):
        """Cifrado Fernet NO es determinístico (por diseño de seguridad)"""
        enc1 = self.crypto.encrypt("ABC123")
        enc2 = self.crypto.encrypt("ABC123")
        # Fernet añade nonce aleatorio, por eso cada cifrado es diferente
        # Pero ambos se descifran al mismo valor
        self.assertNotEqual(enc1, enc2)
        self.assertEqual(self.crypto.decrypt(enc1), "ABC123")
        self.assertEqual(self.crypto.decrypt(enc2), "ABC123")
    
    def test_encrypt_different_passwords(self):
        """Contraseñas diferentes producen diferentes resultados"""
        from therapsid import crypto
        import tempfile
        temp1 = tempfile.mkdtemp()
        temp2 = tempfile.mkdtemp()
        
        # Crear instancias con SALTs separados
        orig_salt = crypto.SALT_FILE
        crypto.SALT_FILE = Path(temp1) / ".salt"
        crypto.MASTER_KEY_FILE = Path(temp1) / ".master"
        crypto1 = LocalCrypto()
        crypto1.unlock("pass1")
        
        crypto.SALT_FILE = Path(temp2) / ".salt"
        crypto.MASTER_KEY_FILE = Path(temp2) / ".master"
        crypto2 = LocalCrypto()
        crypto2.unlock("pass2")
        
        enc1 = crypto1.encrypt("test")
        enc2 = crypto2.encrypt("test")
        
        # Restaurar
        crypto.SALT_FILE = orig_salt
        
        self.assertNotEqual(enc1, enc2)


class TestAnonymization(unittest.TestCase):
    """Tests de anonimización"""
    
    def test_filter_blocked_fields(self):
        """Quitar campos bloqueados"""
        patient = {
            "nombre": "Juan",
            "curp": "PEGJ900101HDFLRN01",
            "edad": 45,
            "sofa_total": 8,
        }
        anon = SensitiveDataFilter.anonymize_patient(patient)
        # Nombre y CURP deben estar ausentes
        self.assertNotIn("nombre", anon)
        self.assertNotIn("curp", anon)
        # Edad debe estar convertida a age_group
        self.assertIn("age_group", anon)
        # SOFA debe estar presente (es campo clínico)
        self.assertIn("sofa_total", anon)
    
    def test_age_generalization(self):
        """Edad se convierte en rango"""
        patient = {"nombre": "X", "edad": 45}
        anon = SensitiveDataFilter.anonymize_patient(patient)
        self.assertEqual(anon.get("age_group"), "40-49")
    
    def test_weight_generalization(self):
        """Peso se convierte en categoría"""
        patient = {"nombre": "X", "peso": 75}
        anon = SensitiveDataFilter.anonymize_patient(patient)
        # 75 cae en el rango 70-79
        self.assertEqual(anon.get("weight_group"), "70-79")


class TestNodeConfig(unittest.TestCase):
    """Tests de configuración"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
    
    def test_config_creation(self):
        """Crear configuración básica"""
        config = NodeConfig(
            node_id="test-node-123",
            node_name="Hospital Test",
            account_type="hospital",
            region="MX-QUE",
        )
        self.assertEqual(config.node_name, "Hospital Test")
        self.assertEqual(config.p2p_port, 8765)  # Default
    
    def test_config_save_load(self):
        """Guardar y cargar configuración"""
        # Hacer backup del config original
        original_config = None
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                original_config = json.load(f)
        
        config = NodeConfig(
            node_id="test-node-456",
            node_name="Clínica Norte",
            account_type="individual",
            region="MX-CMX",
        )
        config.save()
        
        loaded = NodeConfig.load()
        self.assertEqual(loaded.node_name, "Clínica Norte")
        self.assertEqual(loaded.account_type, "individual")
        
        # Restaurar config original
        if original_config:
            with open(CONFIG_FILE, "w") as f:
                json.dump(original_config, f, indent=2)


class TestSyncPacket(unittest.TestCase):
    """Tests de sincronización"""
    
    def test_packet_serialization(self):
        """Serializar y deserializar paquete"""
        packet = SyncPacket(
            node_id="node-1",
            timestamp=datetime.now().isoformat(),
            region="MX-QUE",
            account_type="hospital",
            patients_count=10,
            evolutions_count=50,
            mortality_count=2,
            avg_sofa_score=5.5,
            avg_saps3_score=45.0,
            clinical_data=[{"edad": "40-49", "sofa": 6}],
        )
        
        json_str = packet.to_json()
        restored = SyncPacket.from_json(json_str)
        
        self.assertEqual(restored.patients_count, 10)
        self.assertEqual(restored.mortality_count, 2)
        self.assertEqual(restored.clinical_data[0]["edad"], "40-49")


class TestDeltaSync(unittest.TestCase):
    """Tests de sincronización delta"""
    
    def setUp(self):
        self.delta = DeltaSync()
    
    def test_no_changes(self):
        """Sin cambios = lista vacía"""
        patients = [{"id": 1, "edad": 30, "sofa": 5}]
        changed = self.delta.get_changed_patients(patients)
        self.assertEqual(len(changed), 1)  # Primera vez, todo es nuevo
        
        # Segunda vez sin cambios
        changed2 = self.delta.get_changed_patients(patients)
        self.assertEqual(len(changed2), 0)  # Sin cambios
    
    def test_with_changes(self):
        """Detectar cambios"""
        patients = [{"id": 1, "edad": 30, "sofa": 5}]
        self.delta.get_changed_patients(patients)
        
        # Modificar paciente - cambiar un campo clínico afecta el checksum
        patients[0]["edad"] = 35  # Cambio que afecta checksum
        changed = self.delta.get_changed_patients(patients)
        self.assertEqual(len(changed), 1)


class TestP2PSyncManager(unittest.TestCase):
    """Tests del gestor de sincronización"""
    
    def setUp(self):
        self.manager = P2PSyncManager(
            node_id="test-node",
            region="MX-QUE",
            account_type="hospital",
        )
    
    def test_create_packet(self):
        """Crear paquete desde datos locales"""
        patients = [
            {"id": 1, "egreso": "death", "nombre": "Juan"},
            {"id": 2, "egreso": "alive", "nombre": "María"},
        ]
        evolutions = [
            {"patient_id": 1, "sofa_total": 8},
            {"patient_id": 2, "sofa_total": 3},
        ]
        
        packet = self.manager.create_sync_packet(patients, evolutions)
        self.assertEqual(packet.patients_count, 2)
        self.assertEqual(packet.mortality_count, 1)
    
    def test_compress_decompress(self):
        """Comprimir y descomprimir paquete"""
        packet = SyncPacket(
            node_id="n1",
            timestamp="2024-01-01T00:00:00",
            region="MX-QUE",
            account_type="hospital",
            patients_count=5,
            evolutions_count=25,
            mortality_count=1,
            avg_sofa_score=4.0,
            avg_saps3_score=None,
            clinical_data=[{"edad": "40-49"}],
        )
        
        compressed = self.manager.compress_packet(packet)
        self.assertIsInstance(compressed, bytes)
        
        restored = self.manager.decompress_packet(compressed)
        self.assertEqual(restored.patients_count, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
