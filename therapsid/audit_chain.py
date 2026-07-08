"""
Audit Chain - Cadena de Auditoría Inmutable
=============================================
Registro completo de quién, cuándo, qué nodo y qué cuenta realizó cada operación.

Inmutable = append-only. Nunca se borra, nunca se modifica.
Sirve para:
- Trazabilidad completa
- Detección de intrusiones
- Resolución de conflictos
- Auditoría regulatoria (cumplimiento HIPAA/GDPR)
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AuditOperation(Enum):
    """Tipos de operaciones auditables"""
    CREATE_PATIENT = "CREATE_PATIENT"
    UPDATE_PATIENT = "UPDATE_PATIENT"
    DELETE_PATIENT = "DELETE_PATIENT"  # Soft delete
    SYNC_OUT = "SYNC_OUT"              # Enviar a red P2P
    SYNC_IN = "SYNC_IN"                # Recibir de red P2P
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    GOVERNANCE_VOTE = "GOVERNANCE_VOTE"
    DEV_BYPASS = "DEV_BYPASS"          # Admin bypass (marcado especial)


class AuditBlock:
    """Bloque individual de la cadena de auditoría"""
    
    def __init__(self,
                 operation: AuditOperation,
                 actor: Dict[str, Any],
                 subject: Dict[str, Any],
                 diff: Dict[str, Any],
                 prev_hash: str = ""):
        self.operation = operation
        self.actor = actor
        self.subject = subject
        self.diff = diff
        self.timestamp = time.time()
        self.prev_hash = prev_hash
        self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """SHA-256 del bloque completo"""
        content = {
            "operation": self.operation.value,
            "actor": self.actor,
            "subject": self.subject,
            "diff": self.diff,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash
        }
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "hash": self.hash,
            "operation": self.operation.value,
            "actor": self.actor,
            "subject": self.subject,
            "diff": self.diff,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "datetime_utc": datetime.utcfromtimestamp(self.timestamp).isoformat()
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'AuditBlock':
        block = cls.__new__(cls)
        block.operation = AuditOperation(d["operation"])
        block.actor = d["actor"]
        block.subject = d["subject"]
        block.diff = d["diff"]
        block.timestamp = d["timestamp"]
        block.prev_hash = d["prev_hash"]
        block.hash = d["hash"]
        return block


class AuditChain:
    """
    Cadena de auditoría append-only.
    Cada nodo tiene su propia cadena local.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.blocks: List[AuditBlock] = []
        self.head_hash: str = ""
        self.block_count = 0
    
    def append(self,
               operation: AuditOperation,
               actor: Dict[str, Any],
               subject: Dict[str, Any],
               diff: Dict[str, Any]) -> AuditBlock:
        """
        Agrega un bloque a la cadena.
        
        Args:
            operation: Tipo de operación
            actor: {account, role, node_id, ip}
            subject: {patient_uuid, patient_owner_node}
            diff: {before, after} para cambios
        """
        prev = self.head_hash if self.blocks else ""
        
        block = AuditBlock(
            operation=operation,
            actor=actor,
            subject=subject,
            diff=diff,
            prev_hash=prev
        )
        
        self.blocks.append(block)
        self.head_hash = block.hash
        self.block_count += 1
        
        return block
    
    def verify_chain(self) -> bool:
        """Verifica integridad criptográfica de toda la cadena"""
        for i, block in enumerate(self.blocks):
            if block.hash != block._compute_hash():
                return False
            if i > 0 and block.prev_hash != self.blocks[i-1].hash:
                return False
        return True
    
    def get_by_patient(self, patient_uuid: str) -> List[AuditBlock]:
        """Toda la historia de un paciente"""
        return [
            block for block in self.blocks
            if block.subject.get("patient_uuid") == patient_uuid
        ]
    
    def get_by_account(self, account: str) -> List[AuditBlock]:
        """Todas las operaciones de una cuenta"""
        return [
            block for block in self.blocks
            if block.actor.get("account") == account
        ]
    
    def get_by_node(self, node_id: str) -> List[AuditBlock]:
        """Todas las operaciones de un nodo"""
        return [
            block for block in self.blocks
            if block.actor.get("node_id") == node_id
        ]
    
    def get_by_operation(self, operation: AuditOperation) -> List[AuditBlock]:
        """Todas las operaciones de un tipo"""
        return [
            block for block in self.blocks
            if block.operation == operation
        ]
    
    def get_dev_bypasses(self) -> List[AuditBlock]:
        """Todos los bypasses de admin (para auditoría)"""
        return self.get_by_operation(AuditOperation.DEV_BYPASS)
    
    def get_recent(self, limit: int = 100) -> List[AuditBlock]:
        """Últimos N bloques"""
        return self.blocks[-limit:] if len(self.blocks) > limit else self.blocks
    
    def export_to_json(self) -> str:
        """Exporta toda la cadena como JSON"""
        return json.dumps({
            "node_id": self.node_id,
            "head_hash": self.head_hash,
            "block_count": self.block_count,
            "blocks": [b.to_dict() for b in self.blocks]
        }, indent=2, ensure_ascii=False)
    
    def export_for_sync(self) -> Dict:
        """
        Exporta versión comprimida para sincronización.
        Solo metadatos, no datos completos de pacientes.
        """
        return {
            "node_id": self.node_id,
            "head_hash": self.head_hash,
            "block_count": self.block_count,
            "summary": [
                {
                    "hash": b.hash,
                    "operation": b.operation.value,
                    "timestamp": b.timestamp,
                    "patient_uuid": b.subject.get("patient_uuid"),
                    "actor_account": b.actor.get("account")
                }
                for b in self.blocks[-1000:]  # Solo últimos 1000 para sync
            ]
        }


class AuditReporter:
    """
    Genera reportes de auditoría para análisis.
    """
    
    def __init__(self, chain: AuditChain):
        self.chain = chain
    
    def activity_by_hour(self) -> Dict[int, int]:
        """Actividad agrupada por hora del día (UTC)"""
        from collections import Counter
        hours = [datetime.utcfromtimestamp(b.timestamp).hour for b in self.chain.blocks]
        return dict(Counter(hours))
    
    def top_operators(self, limit: int = 10) -> List[Dict]:
        """Cuentas con más actividad"""
        from collections import Counter
        accounts = [b.actor.get("account", "unknown") for b in self.chain.blocks]
        return [
            {"account": acc, "operations": count}
            for acc, count in Counter(accounts).most_common(limit)
        ]
    
    def governance_summary(self) -> Dict:
        """Resumen para dashboard de gobernanza"""
        total = len(self.chain.blocks)
        
        return {
            "total_operations": total,
            "by_operation": {
                op.value: len(self.chain.get_by_operation(op))
                for op in AuditOperation
            },
            "by_account": self.top_operators(5),
            "dev_bypasses": len(self.chain.get_dev_bypasses()),
            "last_24h": len([
                b for b in self.chain.blocks
                if time.time() - b.timestamp < 86400
            ]),
            "chain_integrity": self.chain.verify_chain()
        }
