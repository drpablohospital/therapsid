"""
Merkle DAG - Árbol de Integridad de Datos
============================================
Cada paciente = un nodo en el DAG.
Cada modificación = nuevo nodo + hash del anterior.

Si xiu-HOME explota, cualquier nodo puede reconstruir el DAG completo
y verificar integridad criptográfica de todos los datos.
"""

import hashlib
import json
from typing import List, Dict, Optional, Any
from datetime import datetime


class MerkleNode:
    """Nodo individual en el Merkle DAG"""
    
    def __init__(self, data: Dict, prev_hash: str = "", owner_node: str = ""):
        self.data = data
        self.prev_hash = prev_hash
        self.owner_node = owner_node
        self.timestamp = datetime.utcnow().isoformat()
        self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """SHA-256 del contenido + prev_hash + metadata"""
        content = {
            "data": self.data,
            "prev_hash": self.prev_hash,
            "owner_node": self.owner_node,
            "timestamp": self.timestamp
        }
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "hash": self.hash,
            "prev_hash": self.prev_hash,
            "owner_node": self.owner_node,
            "timestamp": self.timestamp,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'MerkleNode':
        node = cls.__new__(cls)
        node.data = d["data"]
        node.prev_hash = d["prev_hash"]
        node.owner_node = d["owner_node"]
        node.timestamp = d["timestamp"]
        node.hash = d["hash"]
        return node
    
    def verify(self) -> bool:
        """Verifica que el hash coincida con el contenido"""
        return self.hash == self._compute_hash()


class PatientMerkleChain:
    """Cadena de Merkle para un paciente específico"""
    
    def __init__(self, patient_uuid: str):
        self.patient_uuid = patient_uuid
        self.nodes: List[MerkleNode] = []
        self.head_hash: str = ""
    
    def append(self, data: Dict, owner_node: str) -> MerkleNode:
        """Agrega una nueva versión del paciente"""
        prev = self.head_hash if self.nodes else ""
        node = MerkleNode(data=data, prev_hash=prev, owner_node=owner_node)
        self.nodes.append(node)
        self.head_hash = node.hash
        return node
    
    def verify_chain(self) -> bool:
        """Verifica integridad de toda la cadena"""
        for i, node in enumerate(self.nodes):
            if not node.verify():
                return False
            if i > 0 and node.prev_hash != self.nodes[i-1].hash:
                return False
        return True
    
    def get_latest(self) -> Optional[MerkleNode]:
        """Última versión del paciente"""
        return self.nodes[-1] if self.nodes else None
    
    def get_version(self, index: int) -> Optional[MerkleNode]:
        """Versión específica por índice"""
        if 0 <= index < len(self.nodes):
            return self.nodes[index]
        return None
    
    def to_dict(self) -> Dict:
        return {
            "patient_uuid": self.patient_uuid,
            "head_hash": self.head_hash,
            "version_count": len(self.nodes),
            "nodes": [n.to_dict() for n in self.nodes]
        }


class GlobalMerkleTree:
    """
    Árbol global que agrupa todos los pacientes.
    El Merkle root representa el estado completo de la red.
    """
    
    def __init__(self):
        self.patient_chains: Dict[str, PatientMerkleChain] = {}
        self.global_root: str = ""
    
    def add_patient(self, patient_uuid: str, initial_data: Dict, owner_node: str):
        """Registra un paciente nuevo en el árbol global"""
        if patient_uuid not in self.patient_chains:
            self.patient_chains[patient_uuid] = PatientMerkleChain(patient_uuid)
        
        chain = self.patient_chains[patient_uuid]
        chain.append(initial_data, owner_node)
        self._update_global_root()
    
    def update_patient(self, patient_uuid: str, new_data: Dict, owner_node: str):
        """Actualiza un paciente existente (SOLO si es el owner)"""
        if patient_uuid not in self.patient_chains:
            raise ValueError(f"Paciente {patient_uuid} no existe")
        
        chain = self.patient_chains[patient_uuid]
        latest = chain.get_latest()
        
        if latest and latest.owner_node != owner_node:
            raise PermissionError(
                f"Nodo {owner_node} no es dueño del paciente {patient_uuid}. "
                f"Dueño: {latest.owner_node}"
            )
        
        chain.append(new_data, owner_node)
        self._update_global_root()
    
    def _update_global_root(self):
        """Recalcula el Merkle root global"""
        if not self.patient_chains:
            self.global_root = ""
            return
        
        # Ordenar hashes de cabeza de cada cadena
        head_hashes = sorted(
            chain.head_hash for chain in self.patient_chains.values()
        )
        
        # Merkle root = hash de todos los head hashes concatenados
        combined = "".join(head_hashes)
        self.global_root = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def verify_global(self) -> bool:
        """Verifica integridad de TODO el árbol"""
        for chain in self.patient_chains.values():
            if not chain.verify_chain():
                return False
        
        # Recalcular y comparar
        old_root = self.global_root
        self._update_global_root()
        return old_root == self.global_root
    
    def get_state_for_sync(self) -> Dict:
        """
        Devuelve estado comprimido para sincronización entre nodos.
        Solo incluye UUIDs + head_hash (no datos completos).
        """
        return {
            "global_root": self.global_root,
            "patient_count": len(self.patient_chains),
            "patients": {
                uuid: {
                    "head_hash": chain.head_hash,
                    "versions": len(chain.nodes),
                    "owner": chain.get_latest().owner_node if chain.nodes else ""
                }
                for uuid, chain in self.patient_chains.items()
            }
        }
    
    def compare_with_remote(self, remote_state: Dict) -> Dict:
        """
        Compara estado local con remoto y detecta divergencias.
        Retorna: pacientes faltantes, desactualizados, o conflictivos.
        """
        local_state = self.get_state_for_sync()
        
        missing = []      # En remoto pero no en local
        outdated = []     # En ambos pero local tiene menos versiones
        divergent = []    # Misma cantidad de versiones pero hash diferente
        
        remote_patients = remote_state.get("patients", {})
        local_patients = local_state["patients"]
        
        for uuid, remote_info in remote_patients.items():
            if uuid not in local_patients:
                missing.append({
                    "uuid": uuid,
                    "remote_versions": remote_info["versions"],
                    "remote_owner": remote_info["owner"]
                })
            else:
                local_info = local_patients[uuid]
                if local_info["versions"] < remote_info["versions"]:
                    outdated.append({
                        "uuid": uuid,
                        "local_versions": local_info["versions"],
                        "remote_versions": remote_info["versions"],
                        "owner": remote_info["owner"]
                    })
                elif local_info["head_hash"] != remote_info["head_hash"]:
                    divergent.append({
                        "uuid": uuid,
                        "local_hash": local_info["head_hash"],
                        "remote_hash": remote_info["head_hash"]
                    })
        
        return {
            "missing": missing,
            "outdated": outdated,
            "divergent": divergent,
            "sync_needed": bool(missing or outdated or divergent)
        }
