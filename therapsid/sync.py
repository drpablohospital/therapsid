"""
Therapsid - Módulo de Sincronización P2P
Anonimiza y sincroniza datos médicos entre nodos
"""

import json
import gzip
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .crypto import SensitiveDataFilter


@dataclass
class SyncPacket:
    """Paquete de sincronización seguro para enviar por P2P"""
    node_id: str
    timestamp: str
    region: str
    account_type: str
    
    # Metadata agregada (anónima)
    patients_count: int
    evolutions_count: int
    mortality_count: int
    avg_sofa_score: Optional[float]
    avg_saps3_score: Optional[float]
    
    # Datos clínicos anonimizados (lista de dicts)
    clinical_data: List[Dict[str, Any]]
    
    # Modelo federado (gradientes comprimidos)
    model_update: Optional[bytes] = None
    
    def to_json(self) -> str:
        """Serializa a JSON comprimido"""
        data = {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "region": self.region,
            "account_type": self.account_type,
            "metadata": {
                "patients_count": self.patients_count,
                "evolutions_count": self.evolutions_count,
                "mortality_count": self.mortality_count,
                "avg_sofa_score": self.avg_sofa_score,
                "avg_saps3_score": self.avg_saps3_score,
            },
            "clinical_data": self.clinical_data,
        }
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SyncPacket':
        """Deserializa desde JSON"""
        data = json.loads(json_str)
        return cls(
            node_id=data["node_id"],
            timestamp=data["timestamp"],
            region=data["region"],
            account_type=data["account_type"],
            patients_count=data["metadata"]["patients_count"],
            evolutions_count=data["metadata"]["evolutions_count"],
            mortality_count=data["metadata"]["mortality_count"],
            avg_sofa_score=data["metadata"].get("avg_sofa_score"),
            avg_saps3_score=data["metadata"].get("avg_saps3_score"),
            clinical_data=data.get("clinical_data", []),
        )


class P2PSyncManager:
    """
    Gestiona la sincronización segura de datos entre nodos Therapsid.
    
    Principios:
    1. ANONIMIZAR: Quitar TODO identificador antes de enviar
    2. AGREGAR: Solo enviar conteos, promedios, rangos
    3. COMPRIMIR: gzip para reducir ancho de banda
    4. DELTA: Solo enviar cambios desde último sync
    5. OPT-IN: Cada nodo decide qué compartir
    """
    
    def __init__(self, node_id: str, region: str, account_type: str):
        self.node_id = node_id
        self.region = region
        self.account_type = account_type
        self.last_sync: Optional[datetime] = None
        self.sync_enabled = True
        self.share_clinical_data = False  # Por defecto: solo metadata
        self.share_model_updates = True
    
    def create_sync_packet(self, local_patients: List[Dict], local_evolutions: List[Dict]) -> SyncPacket:
        """
        Crea un paquete de sincronización desde datos locales.
        Anonimiza antes de empaquetar.
        """
        # Conteos
        patients_count = len(local_patients)
        evolutions_count = len(local_evolutions)
        
        # Contar mortalidades (egreso = 'death')
        mortality_count = sum(
            1 for p in local_patients 
            if p.get('egreso') == 'death' or p.get('estatus_egreso') == 'fallecido'
        )
        
        # Calcular promedios de scores (si hay datos)
        avg_sofa = None
        avg_saps3 = None
        
        if local_evolutions:
            sofa_scores = [e.get('sofa_total', 0) for e in local_evolutions if e.get('sofa_total')]
            saps3_scores = [e.get('saps3', 0) for e in local_evolutions if e.get('saps3')]
            
            if sofa_scores:
                avg_sofa = sum(sofa_scores) / len(sofa_scores)
            if saps3_scores:
                avg_saps3 = sum(saps3_scores) / len(saps3_scores)
        
        # Anonimizar datos clínicos (si está habilitado)
        clinical_data = []
        if self.share_clinical_data:
            for patient in local_patients:
                anon = SensitiveDataFilter.anonymize_patient(patient)
                if anon:  # Solo agregar si quedó algo después de filtrar
                    clinical_data.append(anon)
        
        return SyncPacket(
            node_id=self.node_id,
            timestamp=datetime.now().isoformat(),
            region=self.region,
            account_type=self.account_type,
            patients_count=patients_count,
            evolutions_count=evolutions_count,
            mortality_count=mortality_count,
            avg_sofa_score=avg_sofa,
            avg_saps3_score=avg_saps3,
            clinical_data=clinical_data,
        )
    
    def compress_packet(self, packet: SyncPacket) -> bytes:
        """Comprime un paquete con gzip"""
        json_str = packet.to_json()
        return gzip.compress(json_str.encode('utf-8'))
    
    def decompress_packet(self, compressed: bytes) -> SyncPacket:
        """Descomprime un paquete"""
        json_str = gzip.decompress(compressed).decode('utf-8')
        return SyncPacket.from_json(json_str)
    
    def validate_incoming(self, packet: SyncPacket) -> bool:
        """
        Valida que un paquete entrante no contenga datos sensibles.
        Seguridad defensiva: rechazar si hay campos bloqueados.
        """
        blocked_fields = SensitiveDataFilter.BLOCKED_FIELDS
        
        for patient_data in packet.clinical_data:
            for field in patient_data.keys():
                if field.lower() in blocked_fields:
                    print(f"🚫 [Therapsid] Paquete de {packet.node_id} rechazado: contiene campo bloqueado '{field}'")
                    return False
        
        return True


class DeltaSync:
    """
    Sincronización delta: solo envía cambios desde último sync.
    Reduce ancho de banda 90%+ comparado con sync completo.
    """
    
    def __init__(self):
        self.last_checksums: Dict[str, str] = {}  # patient_id -> hash
    
    def compute_checksum(self, patient_data: Dict) -> str:
        """Computa un hash simple de los datos del paciente"""
        import hashlib
        # Usar solo campos clínicos (no identificadores)
        clinical_fields = {k: v for k, v in patient_data.items() 
                          if k in ['edad', 'peso', 'talla', 'sofa_total', 'saps3', 'apache']}
        data_str = json.dumps(clinical_fields, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get_changed_patients(self, current_patients: List[Dict]) -> List[Dict]:
        """
        Retorna solo los pacientes que han cambiado desde último sync.
        """
        changed = []
        
        for patient in current_patients:
            pid = str(patient.get('id', patient.get('identifier', 'unknown')))
            current_checksum = self.compute_checksum(patient)
            
            if pid not in self.last_checksums or self.last_checksums[pid] != current_checksum:
                changed.append(patient)
                self.last_checksums[pid] = current_checksum
        
        return changed
    
    def cleanup_old_checksums(self, current_patient_ids: List[str]):
        """Limpia checksums de pacientes que ya no existen"""
        current_ids = set(current_patient_ids)
        self.last_checksums = {k: v for k, v in self.last_checksums.items() if k in current_ids}
