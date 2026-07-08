"""
Consensus - Sistema de Consenso Sinapsid
=========================================
Ahora: Proof-of-Patients (PoP)
Futuro: Proof-of-Stake con tokens crypto

Modo DEV: Bypass total para administrador principal.
"""

import time
import hashlib
from typing import Dict, List, Optional, Any
from enum import Enum


class GovernanceMode(Enum):
    """Modos de gobernanza"""
    DEV = "DEV"           # Bypass total, admin controla todo
    POP = "POP"           # Proof-of-Patients (ahora)
    POS = "POS"           # Proof-of-Stake (futuro con tokens)
    HYBRID = "HYBRID"     # PoP + PoS combinados


class NodeInfo:
    """Información de un nodo en la red"""
    
    def __init__(self, node_id: str, node_name: str, account: str = ""):
        self.node_id = node_id
        self.node_name = node_name
        self.account = account
        self.patient_count = 0
        self.uptime_seconds = 0
        self.last_seen = time.time()
        self.is_online = True
        self.is_coordinator = False
        self.tokens = 0.0  # Para futuro PoS
        self.reputation = 100.0  # 0-100, baja si comportamiento malicioso
    
    @property
    def weight_pop(self) -> float:
        """Peso Proof-of-Patients = pacientes * uptime * reputación"""
        if self.reputation < 50:
            return 0  # Nodo castigado
        return self.patient_count * max(self.uptime_seconds / 3600, 1) * (self.reputation / 100)
    
    @property
    def weight_pos(self) -> float:
        """Peso Proof-of-Stake = tokens * reputación"""
        if self.reputation < 50:
            return 0
        return self.tokens * (self.reputation / 100)
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "account": self.account,
            "patient_count": self.patient_count,
            "uptime_seconds": self.uptime_seconds,
            "last_seen": self.last_seen,
            "is_online": self.is_online,
            "is_coordinator": self.is_coordinator,
            "tokens": self.tokens,
            "reputation": self.reputation,
            "weight_pop": self.weight_pop,
            "weight_pos": self.weight_pos
        }


class SinapsidConsensus:
    """
    Motor de consenso de Sinapsid Network.
    
    Modo DEV (actual):
        - Admin/dev principal (Dr. Pablo) controla todo
        - No hay votaciones ni quórum
        - Las escrituras se propagan inmediatamente
        - Los nodos confían ciegamente en el coordenador designado
    
    Modo PoP (para comunidad pequeña):
        - El nodo con más pacientes lidera
        - Quórum = 50% del peso total
        - Elección automática de coordenador
    
    Modo PoS (futuro, con tokens):
        - Los tokens determinan el peso de voto
        - Staking para participar
        - Recompensas por buen comportamiento
    """
    
    # Cuenta del desarrollador principal - siempre tiene control total
    DEV_ACCOUNT = "drpablo.hospita@gmail.com"
    DEV_NODE_PREFIX = "sinapsid-dev"
    
    def __init__(self, node_id: str, account: str = "", mode: GovernanceMode = GovernanceMode.DEV):
        self.node_id = node_id
        self.account = account
        self.mode = mode
        self.nodes: Dict[str, NodeInfo] = {}
        self.coordinator_id: Optional[str] = None
        self.election_timestamp = 0
        self.dev_mode_active = self._is_dev_account(account)
    
    def _is_dev_account(self, account: str) -> bool:
        """Verifica si la cuenta es el admin/dev principal"""
        return account.lower() == self.DEV_ACCOUNT.lower()
    
    def _is_dev_node(self, node_id: str) -> bool:
        """Verifica si el nodo es del desarrollador"""
        return node_id.startswith(self.DEV_NODE_PREFIX) or self._is_dev_account(
            self.nodes.get(node_id, NodeInfo("", "")).account
        )
    
    # === MODO DEV: BYPASS TOTAL ===
    
    def dev_bypass_governance(self, action: str) -> Dict:
        """
        Bypass total de gobernanza para admin.
        Registra la acción pero la ejecuta inmediatamente.
        """
        if not self.dev_mode_active:
            return {
                "allowed": False,
                "reason": "Modo DEV no activo o cuenta no autorizada"
            }
        
        return {
            "allowed": True,
            "mode": "DEV_BYPASS",
            "action": action,
            "by": self.account,
            "warning": "Esta acción fue ejecutada con bypass de gobernanza"
        }
    
    def dev_force_coordinator(self, node_id: str) -> bool:
        """Admin fuerza a un nodo como coordenador (bypass elección)"""
        if not self.dev_mode_active:
            return False
        
        self.coordinator_id = node_id
        self.election_timestamp = time.time()
        
        # Actualizar flags
        for nid, node in self.nodes.items():
            node.is_coordinator = (nid == node_id)
        
        return True
    
    def dev_override_patient(self, patient_uuid: str, new_owner: str) -> bool:
        """
        Admin puede reasignar dueño de paciente (emergencia/recuperación).
        Solo en modo DEV.
        """
        if not self.dev_mode_active:
            return False
        
        # Esto requiere el bridge - aquí solo marcamos la intención
        return True
    
    # === MODO POP: PROOF-OF-PATIENTS ===
    
    def register_node(self, node_id: str, node_name: str, account: str = "") -> NodeInfo:
        """Registra un nodo en el consenso"""
        if node_id not in self.nodes:
            self.nodes[node_id] = NodeInfo(node_id, node_name, account)
        return self.nodes[node_id]
    
    def update_node_stats(self, node_id: str, patient_count: int, uptime: float):
        """Actualiza estadísticas de un nodo"""
        if node_id in self.nodes:
            self.nodes[node_id].patient_count = patient_count
            self.nodes[node_id].uptime_seconds = uptime
            self.nodes[node_id].last_seen = time.time()
    
    def elect_coordinator(self) -> Optional[str]:
        """
        Elección de coordenador por Proof-of-Patients.
        El nodo con mayor peso gana.
        """
        if self.mode == GovernanceMode.DEV and self.dev_mode_active:
            # En modo DEV, el nodo del admin es siempre coordenador
            for nid, node in self.nodes.items():
                if self._is_dev_node(nid):
                    self.coordinator_id = nid
                    node.is_coordinator = True
                    return nid
        
        # Filtrar nodos online
        online_nodes = [
            node for node in self.nodes.values()
            if node.is_online and node.reputation >= 50
        ]
        
        if not online_nodes:
            return None
        
        # Ordenar por peso PoP descendente
        if self.mode == GovernanceMode.POS:
            # Futuro: usar peso PoS
            online_nodes.sort(key=lambda n: n.weight_pos, reverse=True)
        else:
            online_nodes.sort(key=lambda n: n.weight_pop, reverse=True)
        
        winner = online_nodes[0]
        
        # Solo cambiar si hay diferencia significativa o ha pasado tiempo
        if (self.coordinator_id != winner.node_id and 
            (not self.coordinator_id or 
             time.time() - self.election_timestamp > 300)):  # 5 min cooldown
            
            # Desactivar anterior
            if self.coordinator_id in self.nodes:
                self.nodes[self.coordinator_id].is_coordinator = False
            
            # Activar nuevo
            self.coordinator_id = winner.node_id
            winner.is_coordinator = True
            self.election_timestamp = time.time()
        
        return self.coordinator_id
    
    def check_quorum(self, supporting_nodes: List[str]) -> bool:
        """
        Verifica si hay quórum para una operación.
        Quórum = 50% del peso total.
        """
        if self.mode == GovernanceMode.DEV and self.dev_mode_active:
            return True  # Bypass en DEV
        
        total_weight = sum(
            node.weight_pop if self.mode != GovernanceMode.POS else node.weight_pos
            for node in self.nodes.values() if node.is_online
        )
        
        if total_weight == 0:
            return False
        
        supporting_weight = sum(
            self.nodes[nid].weight_pop if self.mode != GovernanceMode.POS 
            else self.nodes[nid].weight_pos
            for nid in supporting_nodes if nid in self.nodes and self.nodes[nid].is_online
        )
        
        return supporting_weight >= (total_weight * 0.5)
    
    def validate_write(self, patient_uuid: str, node_id: str, account: str) -> Dict:
        """
        Valida si un nodo puede escribir/modificar un paciente.
        
        Reglas:
        1. Modo DEV: Admin bypass todo
        2. Creador: Si el nodo creó el paciente, puede modificarlo
        3. Otros: Rechazado (solo lectura)
        """
        # Bypass DEV
        if self.mode == GovernanceMode.DEV and self._is_dev_account(account):
            return {
                "allowed": True,
                "reason": "DEV_BYPASS",
                "by": account
            }
        
        # Verificar si es el dueño
        # Nota: La verificación real del dueño está en el bridge
        # Aquí solo validamos participación en consenso
        
        if node_id not in self.nodes:
            return {
                "allowed": False,
                "reason": "Nodo no registrado en consenso"
            }
        
        node = self.nodes[node_id]
        if not node.is_online:
            return {
                "allowed": False,
                "reason": "Nodo offline"
            }
        
        if node.reputation < 50:
            return {
                "allowed": False,
                "reason": f"Reputación baja ({node.reputation})"
            }
        
        return {
            "allowed": True,
            "reason": "Nodo autorizado",
            "node_id": node_id
        }
    
    def report_malicious(self, reporter: str, suspect: str, reason: str) -> bool:
        """
        Reporta comportamiento malicioso. Reduce reputación del sospechoso.
        En modo DEV, el admin puede resetear reputaciones.
        """
        if suspect in self.nodes:
            self.nodes[suspect].reputation = max(0, self.nodes[suspect].reputation - 20)
            return True
        return False
    
    def get_coordinator(self) -> Optional[NodeInfo]:
        """Retorna info del coordenador actual"""
        if self.coordinator_id and self.coordinator_id in self.nodes:
            return self.nodes[self.coordinator_id]
        return None
    
    def get_network_summary(self) -> Dict:
        """Resumen de la red para dashboard"""
        total_patients = sum(n.patient_count for n in self.nodes.values())
        total_nodes = len(self.nodes)
        online_nodes = sum(1 for n in self.nodes.values() if n.is_online)
        
        return {
            "governance_mode": self.mode.value,
            "dev_mode": self.dev_mode_active,
            "coordinator": self.coordinator_id,
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "total_patients": total_patients,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}
        }
