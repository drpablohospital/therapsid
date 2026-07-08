"""
Recovery - Recuperación Post-Catástrofe
=========================================
Si xiu-HOME explota, cualquier nodo puede reconstruir todo.

Modo DEV:
- Admin (Dr. Pablo) controla todo el proceso
- Puede forzar la reconstrucción desde cualquier nodo
- Puede designar nuevo coordenador manualmente
- Puede exportar/importar la base de datos completa

Modo PROD (PoP):
- Elección automática de nuevo coordenador
- Consenso distribuido para reconstrucción
- Sin intervención humana
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .merkle_dag import GlobalMerkleTree
from .audit_chain import AuditChain, AuditOperation
from .consensus import SinapsidConsensus, GovernanceMode


class RecoveryManager:
    """
    Gestiona la recuperación de la red después de una catástrofe.
    
    Escenarios:
    1. Coordenador caído (xiu-HOME explota)
    2. Nodo aislado (sin conexión por días)
    3. Datos corruptos (Merkle hash no coincide)
    4. Ataque malicioso (nodo comprometido)
    """
    
    def __init__(self, bridge):
        self.bridge = bridge
        self.governance = bridge.governance
        self.merkle = bridge.merkle
        self.audit = bridge.audit
    
    # === DETECCIÓN DE CATÁSTROFE ===
    
    def check_coordinator_health(self) -> Dict:
        """
        Verifica si el coordenador sigue vivo.
        Si no, inicia elección de nuevo coordenador.
        """
        coord = self.governance.get_coordinator()
        
        if not coord:
            return {
                "status": "NO_COORDINATOR",
                "action": "ELECTION_NEEDED",
                "message": "No hay coordenador. Iniciando elección..."
            }
        
        # Verificar heartbeat (último contacto < 180 segundos)
        time_since_last = time.time() - coord.last_seen
        
        if time_since_last > 180:
            return {
                "status": "COORDINATOR_DOWN",
                "coordinator_id": coord.node_id,
                "last_seen": coord.last_seen,
                "seconds_ago": time_since_last,
                "action": "ELECTION_NEEDED",
                "message": f"Coordenador caído hace {int(time_since_last)}s"
            }
        
        return {
            "status": "HEALTHY",
            "coordinator_id": coord.node_id,
            "last_seen": coord.last_seen,
            "seconds_ago": time_since_last
        }
    
    def initiate_election(self) -> Dict:
        """
        Inicia elección de nuevo coordenador.
        
        Modo DEV: Admin designa directamente
        Modo PoP: El nodo con más pacientes gana
        """
        # Modo DEV: bypass
        if self.bridge.dev_mode:
            # Buscar el nodo del admin o el de mayor peso
            winner = None
            for node_id, node in self.governance.nodes.items():
                if self.governance._is_dev_node(node_id):
                    winner = node
                    break
            
            if not winner:
                # Fallback: mayor peso
                winner_id = self.governance.elect_coordinator()
                if winner_id:
                    winner = self.governance.nodes[winner_id]
            
            if winner:
                self.governance.dev_force_coordinator(winner.node_id)
                
                self.audit.append(
                    operation=AuditOperation.DEV_BYPASS,
                    actor={"account": self.bridge.account, "node_id": self.bridge.node_id},
                    subject={"new_coordinator": winner.node_id},
                    diff={"reason": "DEV_ELECTION", "previous": self.governance.coordinator_id}
                )
                
                return {
                    "success": True,
                    "mode": "DEV_ELECTION",
                    "new_coordinator": winner.node_id,
                    "weight": winner.weight_pop,
                    "patients": winner.patient_count
                }
        
        # Modo PoP: Elección normal
        winner_id = self.governance.elect_coordinator()
        if winner_id:
            winner = self.governance.nodes[winner_id]
            return {
                "success": True,
                "mode": "POP_ELECTION",
                "new_coordinator": winner_id,
                "weight": winner.weight_pop,
                "patients": winner.patient_count
            }
        
        return {
            "success": False,
            "error": "No se pudo elegir coordenador",
            "available_nodes": len([n for n in self.governance.nodes.values() if n.is_online])
        }
    
    # === RECONSTRUCCIÓN DE DATOS ===
    
    def rebuild_database(self, source_nodes: List[str]) -> Dict:
        """
        Reconstruye la base de datos desde múltiples nodos.
        
        Pasos:
        1. Pedir estado Merkle a cada nodo
        2. Comparar y detectar divergencias
        3. Descargar pacientes faltantes
        4. Verificar integridad del Merkle DAG resultante
        5. Guardar en BD local (SQLite/PostgreSQL)
        """
        print(f"🔄 Reconstruyendo BD desde {len(source_nodes)} nodos...")
        
        stats = {
            "sources_contacted": 0,
            "sources_responded": 0,
            "patients_downloaded": 0,
            "versions_downloaded": 0,
            "conflicts": 0,
            "integrity_ok": False
        }
        
        all_patient_data = {}  # uuid -> {versions: [], source: node}
        
        for node_id in source_nodes:
            try:
                stats["sources_contacted"] += 1
                
                # TODO: Pedir pacientes al nodo via HTTP/Gossip
                # Placeholder: simular respuesta
                # response = self._request_patients_from_node(node_id)
                
                stats["sources_responded"] += 1
            except Exception as e:
                print(f"   ❌ Error contactando {node_id}: {e}")
        
        # Merge de datos (resolución de conflictos)
        # Regla: mayor versión gana, si igual versión y hash diferente = conflicto
        # En modo DEV, admin decide. En modo PoP, timestamp gana.
        
        # Verificar integridad
        stats["integrity_ok"] = self.merkle.verify_global()
        
        # Guardar en BD
        self._save_to_database()
        
        # Registrar en audit
        self.audit.append(
            operation=AuditOperation.DEV_BYPASS if self.bridge.dev_mode else AuditOperation.SYNC_IN,
            actor={"account": self.bridge.account, "node_id": self.bridge.node_id},
            subject={"rebuild_sources": source_nodes},
            diff={"stats": stats}
        )
        
        return {
            "success": True,
            "stats": stats,
            "merkle_root": self.merkle.global_root,
            "total_patients": len(self.merkle.patient_chains)
        }
    
    def verify_database_integrity(self) -> Dict:
        """Verifica integridad completa de la base de datos local"""
        checks = {
            "merkle_integrity": self.merkle.verify_global(),
            "audit_integrity": self.audit.verify_chain(),
            "patient_count": len(self.merkle.patient_chains),
            "audit_count": len(self.audit.blocks)
        }
        
        all_ok = all(checks.values())
        
        return {
            "integrity_ok": all_ok,
            "checks": checks,
            "timestamp": time.time()
        }
    
    # === MODO DEV: EXPORT/IMPORT ===
    
    def dev_export_database(self, filepath: str) -> Dict:
        """
        Exporta la base de datos completa a JSON (solo admin).
        Usado para backups, migraciones, o análisis.
        """
        if not self.bridge.dev_mode:
            return {"success": False, "error": "Requiere modo DEV"}
        
        export_data = {
            "export_metadata": {
                "exported_by": self.bridge.account,
                "node_id": self.bridge.node_id,
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0"
            },
            "merkle_tree": self.merkle.get_state_for_sync(),
            "audit_chain": self.audit.export_for_sync(),
            "governance": self.governance.get_network_summary(),
            "nodes": {nid: n.to_dict() for nid, n in self.governance.nodes.items()}
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.audit.append(
            operation=AuditOperation.DEV_BYPASS,
            actor={"account": self.bridge.account, "node_id": self.bridge.node_id},
            subject={"export_path": filepath},
            diff={"action": "database_export"}
        )
        
        return {
            "success": True,
            "filepath": filepath,
            "size_mb": len(json.dumps(export_data)) / (1024 * 1024),
            "patients": len(self.merkle.patient_chains)
        }
    
    def dev_import_database(self, filepath: str, merge: bool = False) -> Dict:
        """
        Importa base de datos desde JSON (solo admin).
        
        Args:
            filepath: Ruta al archivo JSON
            merge: True = fusionar con datos existentes, False = reemplazar
        """
        if not self.bridge.dev_mode:
            return {"success": False, "error": "Requiere modo DEV"}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # Validar formato
        if "merkle_tree" not in import_data:
            return {"success": False, "error": "Formato inválido"}
        
        if not merge:
            # Reemplazar todo
            self.merkle.patient_chains.clear()
        
        # TODO: Importar pacientes, Merkle DAG, audit chain
        # Esto requiere reconstruir los objetos desde los dicts serializados
        
        self.audit.append(
            operation=AuditOperation.DEV_BYPASS,
            actor={"account": self.bridge.account, "node_id": self.bridge.node_id},
            subject={"import_path": filepath, "merge": merge},
            diff={"action": "database_import"}
        )
        
        return {
            "success": True,
            "filepath": filepath,
            "mode": "merge" if merge else "replace",
            "patients_after": len(self.merkle.patient_chains)
        }
    
    # === UTILIDADES ===
    
    def _save_to_database(self):
        """Guarda estado actual en BD SQLite/PostgreSQL"""
        # TODO: Implementar con SQLAlchemy o psycopg2
        pass
    
    def _request_patients_from_node(self, node_id: str) -> List[Dict]:
        """Pide pacientes a un nodo remoto"""
        # TODO: Implementar via HTTP API
        return []
    
    def get_recovery_status(self) -> Dict:
        """Estado actual del proceso de recuperación"""
        return {
            "dev_mode": self.bridge.dev_mode,
            "coordinator_status": self.check_coordinator_health(),
            "merkle_integrity": self.merkle.verify_global(),
            "total_patients": len(self.merkle.patient_chains),
            "total_nodes": len(self.governance.nodes),
            "online_nodes": sum(1 for n in self.governance.nodes.values() if n.is_online)
        }
