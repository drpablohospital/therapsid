"""
Replication Engine - Motor de Replicación
===========================================
Sincroniza datos entre nodos de forma segura y verificable.

Responsabilidades:
- Detectar divergencias entre nodos
- Transmitir paquetes de sincronización
- Manejar conflictos por timestamp + versión
- Recuperación post-catástrofe
"""

import json
import zlib
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .merkle_dag import GlobalMerkleTree
from .audit_chain import AuditChain, AuditOperation
from .consensus import SinapsidConsensus


class SyncPacket:
    """Paquete de sincronización entre nodos"""
    
    def __init__(self,
                 packet_type: str,  # "full_sync", "delta", "heartbeat", "recovery"
                 sender_node: str,
                 target_nodes: List[str],
                 payload: Dict,
                 priority: int = 5):  # 1-10, 1 = urgente
        self.packet_type = packet_type
        self.sender_node = sender_node
        self.target_nodes = target_nodes
        self.payload = payload
        self.priority = priority
        self.timestamp = time.time()
        self.signature = ""
    
    def serialize(self) -> bytes:
        """Serializa a bytes comprimidos"""
        data = {
            "type": self.packet_type,
            "sender": self.sender_node,
            "targets": self.target_nodes,
            "payload": self.payload,
            "priority": self.priority,
            "timestamp": self.timestamp
        }
        serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
        return zlib.compress(serialized)
    
    @classmethod
    def deserialize(cls, compressed: bytes) -> 'SyncPacket':
        """Deserializa desde bytes comprimidos"""
        serialized = zlib.decompress(compressed)
        data = json.loads(serialized.decode('utf-8'))
        
        packet = cls.__new__(cls)
        packet.packet_type = data["type"]
        packet.sender_node = data["sender"]
        packet.target_nodes = data["targets"]
        packet.payload = data["payload"]
        packet.priority = data["priority"]
        packet.timestamp = data["timestamp"]
        packet.signature = ""
        return packet


class ReplicationEngine:
    """
    Motor de replicación entre nodos Sinapsid.
    
    Modo DEV:
    - Admin puede forzar sync completo
    - Bypass de quórum
    - Recuperación manual de nodos
    
    Modo PROD (PoP):
    - Sync automático por intervalos
    - Quórum requerido para escrituras
    - Elección automática de coordenador
    """
    
    def __init__(self, bridge, gossip_transport=None):
        self.bridge = bridge
        self.gossip = gossip_transport
        self.sync_queue: List[SyncPacket] = []
        self.last_sync = 0
        self.sync_interval = 300  # 5 minutos entre syncs automáticos
    
    # === SINCRONIZACIÓN ===
    
    def sync_with_node(self, target_node: str) -> Dict:
        """
        Sincroniza estado con un nodo específico.
        
        Pasos:
        1. Pedir estado remoto
        2. Comparar con estado local
        3. Resolver divergencias
        4. Enviar/recibir paquetes de sync
        """
        # 1. Obtener estado local
        local_state = self.bridge.get_state_for_sync()
        
        # 2. Pedir estado remoto (via HTTP API o Gossip)
        remote_state = self._request_remote_state(target_node)
        if not remote_state:
            return {"success": False, "error": "Nodo no responde"}
        
        # 3. Comparar
        diff = self.bridge.compare_with_remote(remote_state)
        
        # 4. Resolver
        results = {
            "missing_from_local": 0,
            "missing_from_remote": 0,
            "outdated_local": 0,
            "outdated_remote": 0,
            "conflicts": 0
        }
        
        # Pedir pacientes faltantes
        for patient in diff.get("missing", []):
            self._request_patient(target_node, patient["uuid"])
            results["missing_from_local"] += 1
        
        # Enviar pacientes que el remoto no tiene
        # (solo si somos dueños)
        # TODO: Implementar
        
        return {
            "success": True,
            "compared_with": target_node,
            "divergences": diff,
            "resolved": results
        }
    
    def broadcast_sync(self) -> Dict:
        """
        Propaga estado actual a todos los peers.
        Usado después de crear/modificar un paciente.
        """
        if not self.gossip:
            return {"success": False, "error": "Gossip no disponible"}
        
        state = self.bridge.get_state_for_sync()
        
        packet = SyncPacket(
            packet_type="heartbeat",
            sender_node=self.bridge.node_id,
            target_nodes=[],  # Todos
            payload={
                "merkle_root": state["merkle_state"]["global_root"],
                "patient_count": state["merkle_state"]["patient_count"],
                "timestamp": time.time()
            },
            priority=3
        )
        
        # Encolar para envío
        self.sync_queue.append(packet)
        
        # Enviar inmediatamente si es urgente
        return {"success": True, "queued": True, "peers": len(self.gossip.peers)}
    
    def _request_remote_state(self, node_id: str) -> Optional[Dict]:
        """Pide estado a un nodo remoto"""
        # TODO: Implementar via HTTP API call
        # Por ahora, placeholder
        return None
    
    def _request_patient(self, node_id: str, patient_uuid: str) -> Dict:
        """Pide un paciente específico a un nodo"""
        # TODO: Implementar via HTTP API call
        return {"success": False, "placeholder": True}
    
    # === RECUPERACIÓN POST-CATÁSTROFE ===
    
    def initiate_recovery(self, failed_node: str) -> Dict:
        """
        Inicia recuperación de un nodo que ha fallado.
        
        Pasos:
        1. Identificar nodos que tienen réplicas
        2. Recolectar pacientes del nodo fallido
        3. Reconstruir Merkle DAG
        4. Elegir nuevo dueño (o mantener múltiples réplicas)
        """
        print(f"🚨 Iniciando recuperación de nodo: {failed_node}")
        
        # Buscar pacientes del nodo fallido en otros nodos
        recovered_patients = []
        
        for uuid, chain in self.bridge.merkle.patient_chains.items():
            latest = chain.get_latest()
            if latest and latest.owner_node == failed_node:
                recovered_patients.append({
                    "uuid": uuid,
                    "last_version": latest.to_dict(),
                    "chain_length": len(chain.nodes)
                })
        
        if not recovered_patients:
            return {
                "success": False,
                "error": "No se encontraron pacientes del nodo fallido",
                "failed_node": failed_node
            }
        
        # En modo DEV, admin puede reasignar
        if self.bridge.dev_mode:
            return {
                "success": True,
                "mode": "DEV_RECOVERY",
                "failed_node": failed_node,
                "patients_found": len(recovered_patients),
                "action_required": "Use dev_emergency_recovery() para reasignar",
                "patients": recovered_patients
            }
        
        # En modo PoP, los pacientes quedan "huérfanos" hasta que alguien reclame
        return {
            "success": True,
            "mode": "POP_RECOVERY",
            "failed_node": failed_node,
            "orphan_patients": len(recovered_patients),
            "note": "Pacientes huérfanos pueden ser reclamados por otros nodos"
        }
    
    def reconstruct_from_peers(self, peers: List[str]) -> Dict:
        """
        Reconstruye la base de datos completa desde los peers.
        Usado cuando un nodo nuevo se une o después de una catástrofe.
        """
        print(f"🔄 Reconstruyendo desde {len(peers)} peers...")
        
        total_recovered = 0
        failed_requests = 0
        
        for peer in peers:
            try:
                result = self.sync_with_node(peer)
                if result.get("success"):
                    total_recovered += result.get("resolved", {}).get("missing_from_local", 0)
            except Exception as e:
                print(f"   ❌ Error con {peer}: {e}")
                failed_requests += 1
        
        # Verificar integridad del Merkle DAG reconstruido
        integrity = self.bridge.merkle.verify_global()
        
        return {
            "success": True,
            "peers_contacted": len(peers),
            "failed_requests": failed_requests,
            "patients_recovered": total_recovered,
            "merkle_integrity": integrity,
            "global_root": self.bridge.merkle.global_root
        }
    
    # === MODO DEV: FORZAR SYNC ===
    
    def dev_force_full_sync(self, target_nodes: List[str]) -> Dict:
        """
        Admin fuerza sincronización completa con nodos específicos.
        Envia TODOS los pacientes locales (completos) a los targets.
        """
        if not self.bridge.dev_mode:
            return {"success": False, "error": "Requiere modo DEV"}
        
        # Preparar paquete con todos los pacientes locales
        own_patients = []
        for uuid, chain in self.bridge.merkle.patient_chains.items():
            latest = chain.get_latest()
            if latest and latest.owner_node == self.bridge.node_id:
                own_patients.append({
                    "uuid": uuid,
                    "data": latest.data,
                    "versions": len(chain.nodes),
                    "merkle_hash": latest.hash
                })
        
        packet = SyncPacket(
            packet_type="full_sync",
            sender_node=self.bridge.node_id,
            target_nodes=target_nodes,
            payload={
                "patients": own_patients,
                "merkle_root": self.bridge.merkle.global_root,
                "force": True,
                "by_admin": self.bridge.account
            },
            priority=1  # Urgente
        )
        
        # Enviar
        results = []
        for target in target_nodes:
            try:
                # TODO: Enviar via gossip/HTTP
                results.append({"target": target, "status": "sent"})
            except Exception as e:
                results.append({"target": target, "status": "failed", "error": str(e)})
        
        # Registrar en audit
        self.bridge.audit.append(
            operation=AuditOperation.DEV_BYPASS,
            actor={"account": self.bridge.account, "node_id": self.bridge.node_id},
            subject={"forced_sync_to": target_nodes},
            diff={"patients_sent": len(own_patients), "results": results}
        )
        
        return {
            "success": True,
            "mode": "DEV_FORCE_SYNC",
            "patients_sent": len(own_patients),
            "targets": target_nodes,
            "results": results
        }
    
    # === UTILIDADES ===
    
    def get_sync_status(self) -> Dict:
        """Estado actual de sincronización"""
        return {
            "queue_size": len(self.sync_queue),
            "last_sync": self.last_sync,
            "next_sync_in": max(0, self.sync_interval - (time.time() - self.last_sync)),
            "merkle_root": self.bridge.merkle.global_root,
            "patient_count": len(self.bridge.merkle.patient_chains)
        }
