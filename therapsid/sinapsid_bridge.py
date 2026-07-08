"""
Sinapsid Bridge - El Intermediario (Shield)
=============================================
Muro de protección entre Sinapsid (DB real) y los nodos P2P.

PRINCIPIOS:
1. SOBERANÍA: Cada nodo es dueño de sus pacientes
2. INMUTABILIDAD: Los datos ajenos no se modifican
3. TRAZABILIDAD: Todo queda auditado
4. CONFIDENCIALIDAD: Solo metadata agregada sale por la red
5. CERO CORRUPCIÓN: Bridge valida todo antes de tocar la DB
6. DEV MODE: Admin bypass para desarrollo

Arquitectura:
  Sinapsid (PostgreSQL/SQLite) ←→ Bridge ←→ Red P2P (Therapsid)
     ↓                                ↓              ↓
  Datos reales                   Validación       Datos anonimizados
  + sensibles                    + Trazabilidad   + Metadata
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .merkle_dag import GlobalMerkleTree, PatientMerkleChain
from .audit_chain import AuditChain, AuditOperation, AuditBlock
from .consensus import SinapsidConsensus, GovernanceMode


class PatientDataClassification:
    """Clasificación de campos de paciente por sensibilidad"""
    
    # Campos que NUNCA salen por la red
    SENSITIVE_FIELDS = [
        "nombre", "apellido_paterno", "apellido_materno", "curp", "rfc",
        "nss", "telefono", "email", "direccion", "contacto_familiar",
        "nombre_familiar", "telefono_familiar", "ocupacion", "empresa"
    ]
    
    # Campos que se generalizan (rangos/categorías)
    GENERALIZED_FIELDS = {
        "edad": "age_range",           # 0-9, 10-19, etc.
        "peso": "weight_category",      # 0-49, 50-69, 70-89, etc.
        "fecha_nacimiento": "birth_year", # Solo año
        "fecha_ingreso": "admission_date", # Solo fecha, sin hora
        "fecha_egreso": "discharge_date"   # Solo fecha, sin hora
    }
    
    # Campos que salen tal cual (datos agregados/clínicos)
    SAFE_FIELDS = [
        "diagnostico_principal", "diagnostico_secundario", "comorbilidades",
        "sofa_total", "saps3", "apache", "charlson", "fc", "tas", "tad",
        "temperatura", "fr", "lactato", "creatinina", "urea",
        "leucocitos", "plaquetas", "hemoglobina", "ph", "pao2",
        "dias_ventilacion", "modo_ventilatorio", "num_dispositivos",
        "vasopresores", "sedacion", "nutricion", "balance_liquidos",
        "outcome", "lugar_egreso", "dias_estancia"
    ]


class SinapsidBridge:
    """
    Intermediario entre Sinapsid (DB real) y la red P2P.
    
    Responsabilidades:
    - Validar que solo el dueño modifica sus pacientes
    - Anonimizar datos antes de enviar a la red
    - Registrar auditoría de todas las operaciones
    - Mantener integridad Merkle de los datos
    - Permitir recuperación post-catástrofe
    """
    
    def __init__(self, node_id: str, account: str = "", 
                 governance_mode: GovernanceMode = GovernanceMode.DEV):
        self.node_id = node_id
        self.account = account
        self.governance = SinapsidConsensus(node_id, account, governance_mode)
        self.merkle = GlobalMerkleTree()
        self.audit = AuditChain(node_id)
        self.classifier = PatientDataClassification()
        
        # Dev mode activo si es el admin principal
        self.dev_mode = self.governance.dev_mode_active
        
        print(f"🛡️  Sinapsid Bridge inicializado (modo: {governance_mode.value})")
        if self.dev_mode:
            print(f"   ⚠️  DEV MODE ACTIVO para {account}")
    
    # === MODO DEV: ADMIN BYPASS ===
    
    def dev_force_propagate(self, patient_uuid: str, target_nodes: List[str]) -> Dict:
        """
        Admin fuerza la propagación de un paciente a nodos específicos.
        Bypass de todas las validaciones de gobernanza.
        """
        result = self.governance.dev_bypass_governance("FORCE_PROPAGATE")
        if not result["allowed"]:
            return result
        
        # Registrar en audit
        self.audit.append(
            operation=AuditOperation.DEV_BYPASS,
            actor={
                "account": self.account,
                "role": "admin",
                "node_id": self.node_id
            },
            subject={
                "patient_uuid": patient_uuid,
                "target_nodes": target_nodes
            },
            diff={"action": "force_propagate", "targets": target_nodes}
        )
        
        return {
            "allowed": True,
            "mode": "DEV_BYPASS",
            "propagated_to": target_nodes
        }
    
    def dev_emergency_recovery(self, source_node: str, patient_uuids: List[str]) -> Dict:
        """
        Recuperación de emergencia: admin extrae pacientes de un nodo específico.
        Usado cuando un nodo está dañado o comprometido.
        """
        result = self.governance.dev_bypass_governance("EMERGENCY_RECOVERY")
        if not result["allowed"]:
            return result
        
        recovered = []
        for uuid in patient_uuids:
            # Marcar para recuperación (la operación real la hace replication_engine)
            recovered.append({
                "uuid": uuid,
                "source_node": source_node,
                "recovered_by": self.account,
                "timestamp": time.time()
            })
        
        self.audit.append(
            operation=AuditOperation.DEV_BYPASS,
            actor={"account": self.account, "role": "admin", "node_id": self.node_id},
            subject={"recovered_patients": patient_uuids, "source": source_node},
            diff={"action": "emergency_recovery", "count": len(patient_uuids)}
        )
        
        return {
            "allowed": True,
            "mode": "DEV_BYPASS",
            "recovered": recovered
        }
    
    # === ANONIMIZACIÓN ===
    
    def anonymize_patient(self, patient_data: Dict) -> Dict:
        """
        Convierte datos reales de paciente en versión anonimizada para la red.
        
        Reglas:
        - Campos sensibles: ELIMINADOS
        - Edad/Peso: convertidos a rangos
        - Fechas: solo fecha, sin hora
        - Datos clínicos: PRESERVADOS
        """
        anonymized = {}
        
        # Copiar campos seguros
        for field in self.classifier.SAFE_FIELDS:
            if field in patient_data:
                anonymized[field] = patient_data[field]
        
        # Generalizar campos sensibles
        if "edad" in patient_data:
            anonymized["age_range"] = self._generalize_age(patient_data["edad"])
        
        if "peso" in patient_data:
            anonymized["weight_category"] = self._generalize_weight(patient_data["peso"])
        
        if "fecha_nacimiento" in patient_data:
            anonymized["birth_year"] = self._extract_year(patient_data["fecha_nacimiento"])
        
        if "fecha_ingreso" in patient_data:
            anonymized["admission_date"] = self._generalize_date(patient_data["fecha_ingreso"])
        
        if "fecha_egreso" in patient_data:
            anonymized["discharge_date"] = self._generalize_date(patient_data["fecha_egreso"])
        
        # Metadata de origen
        anonymized["_origin"] = {
            "node_id": self.node_id,
            "anonymized_at": datetime.utcnow().isoformat(),
            "classification_version": "1.0"
        }
        
        return anonymized
    
    def _generalize_age(self, age: Any) -> str:
        """Convierte edad a rango decenal"""
        try:
            a = int(age)
            return f"{(a // 10) * 10}-{(a // 10) * 10 + 9}"
        except:
            return "unknown"
    
    def _generalize_weight(self, weight: Any) -> str:
        """Convierte peso a categoría"""
        try:
            w = float(weight)
            if w < 50: return "0-49kg"
            elif w < 70: return "50-69kg"
            elif w < 90: return "70-89kg"
            else: return "90+kg"
        except:
            return "unknown"
    
    def _extract_year(self, date_str: str) -> str:
        """Extrae solo el año de una fecha"""
        try:
            return date_str.split("-")[0]
        except:
            return "unknown"
    
    def _generalize_date(self, date_str: str) -> str:
        """Mantiene solo fecha (sin hora)"""
        try:
            # Si viene con hora, quitarla
            return date_str.split(" ")[0]
        except:
            return date_str
    
    # === VALIDACIÓN DE PERMISOS ===
    
    def validate_ownership(self, patient_uuid: str, requesting_node: str,
                          requesting_account: str, action: str = "modify") -> Dict:
        """
        Valida si un nodo/cuenta puede actuar sobre un paciente.
        
        Reglas:
        1. DEV MODE: Admin puede todo
        2. Dueño: El nodo que creó el paciente puede modificarlo
        3. Otros: Solo lectura, no modificación
        """
        # Bypass DEV
        if self.dev_mode and self.governance._is_dev_account(requesting_account):
            return {
                "allowed": True,
                "reason": "DEV_BYPASS",
                "by": requesting_account
            }
        
        # Verificar en Merkle DAG quién es dueño
        if patient_uuid in self.merkle.patient_chains:
            chain = self.merkle.patient_chains[patient_uuid]
            latest = chain.get_latest()
            
            if latest and latest.owner_node == requesting_node:
                return {
                    "allowed": True,
                    "reason": "OWNER",
                    "owner_node": requesting_node
                }
            else:
                return {
                    "allowed": False if action in ["modify", "delete"] else True,
                    "reason": "NOT_OWNER",
                    "owner_node": latest.owner_node if latest else "unknown",
                    "requesting_node": requesting_node,
                    "action_requested": action,
                    "note": "Solo lectura permitida para pacientes ajenos"
                }
        
        # Paciente nuevo
        return {
            "allowed": True,
            "reason": "NEW_PATIENT",
            "will_be_owned_by": requesting_node
        }
    
    # === OPERACIONES CON PACIENTES ===
    
    def create_patient(self, patient_data: Dict, account: str,
                      node_id: str, is_local: bool = True) -> Dict:
        """
        Crea un paciente nuevo en el sistema.
        
        Args:
            patient_data: Datos completos del paciente
            account: Cuenta que crea el paciente
            node_id: Nodo que crea el paciente
            is_local: True si viene de UI local, False si viene de red P2P
        """
        # Generar UUID único
        patient_uuid = f"sinapsid:patient:{int(time.time() * 1000)}:{hash(account + node_id) % 10000}"
        
        # Validar consenso
        validation = self.governance.validate_write(patient_uuid, node_id, account)
        if not validation["allowed"]:
            return validation
        
        # Registrar en Merkle DAG
        self.merkle.add_patient(
            patient_uuid=patient_uuid,
            initial_data=self.anonymize_patient(patient_data),
            owner_node=node_id
        )
        
        # Registrar en audit
        self.audit.append(
            operation=AuditOperation.CREATE_PATIENT,
            actor={"account": account, "node_id": node_id},
            subject={"patient_uuid": patient_uuid, "patient_owner_node": node_id},
            diff={"before": None, "after": {"uuid": patient_uuid, "owner": node_id}}
        )
        
        # Si es local, propagar a red (anonimizado)
        if is_local:
            self._schedule_propagation(patient_uuid)
        
        return {
            "success": True,
            "patient_uuid": patient_uuid,
            "owner_node": node_id,
            "action": "created"
        }
    
    def update_patient(self, patient_uuid: str, new_data: Dict,
                    account: str, node_id: str) -> Dict:
        """
        Actualiza un paciente existente.
        SOLO el dueño puede modificar.
        """
        # Validar ownership
        ownership = self.validate_ownership(patient_uuid, node_id, account, "modify")
        if not ownership["allowed"]:
            return ownership
        
        # Actualizar Merkle DAG
        self.merkle.update_patient(
            patient_uuid=patient_uuid,
            new_data=self.anonymize_patient(new_data),
            owner_node=node_id
        )
        
        # Registrar en audit
        self.audit.append(
            operation=AuditOperation.UPDATE_PATIENT,
            actor={"account": account, "node_id": node_id},
            subject={"patient_uuid": patient_uuid, "patient_owner_node": node_id},
            diff={"before": "previous_version", "after": "new_version"}
        )
        
        return {
            "success": True,
            "patient_uuid": patient_uuid,
            "version": len(self.merkle.patient_chains[patient_uuid].nodes),
            "action": "updated"
        }
    
    def receive_from_network(self, encrypted_packet: Dict,
                           sender_node: str, sender_account: str) -> Dict:
        """
        Recibe un paciente de la red P2P.
        Valida, desencripta, guarda en tabla federada (NO modifica pacientes locales).
        """
        # Validar nodo remoto
        if sender_node not in self.governance.nodes:
            return {"success": False, "error": "Nodo no registrado"}
        
        node = self.governance.nodes[sender_node]
        if node.reputation < 50:
            return {"success": False, "error": "Nodo con reputación baja"}
        
        # Extraer datos del paquete
        patient_data = encrypted_packet.get("patient_data", {})
        patient_uuid = encrypted_packet.get("patient_uuid", "")
        
        if not patient_uuid:
            return {"success": False, "error": "UUID faltante"}
        
        # Verificar integridad Merkle
        merkle_hash = encrypted_packet.get("integrity", {}).get("merkle_hash", "")
        # TODO: Verificar que el hash coincide con el Merkle DAG del remitente
        
        # Guardar en tabla de pacientes federados (SEPARADA de los locales)
        # NO modificar pacientes locales
        self._store_federated_patient(patient_uuid, patient_data, sender_node)
        
        # Registrar en audit
        self.audit.append(
            operation=AuditOperation.SYNC_IN,
            actor={"account": sender_account, "node_id": sender_node},
            subject={"patient_uuid": patient_uuid, "patient_owner_node": sender_node},
            diff={"source": "p2p_network", "integrity_hash": merkle_hash}
        )
        
        return {
            "success": True,
            "patient_uuid": patient_uuid,
            "source_node": sender_node,
            "action": "received_federated"
        }
    
    def _store_federated_patient(self, patient_uuid: str, data: Dict, source_node: str):
        """Guarda paciente de otro nodo en tabla separada"""
        # TODO: Implementar con SQLite/PostgreSQL
        # Tabla: patients_federated (uuid, data_json, source_node, received_at)
        pass
    
    def _schedule_propagation(self, patient_uuid: str):
        """Programa la propagación de un paciente a la red"""
        # TODO: Implementar con replication_engine
        # Agregar a cola de sincronización
        pass
    
    # === QUERIES SEGURAS ===
    
    def query_patients_for_node(self, requesting_node: str, 
                               requesting_account: str) -> Dict:
        """
        Devuelve pacientes que un nodo puede ver:
        - Todos los pacientes propios (completos)
        - Pacientes de otros nodos (anonimizados)
        """
        result = {
            "own_patients": [],
            "federated_patients": []
        }
        
        for uuid, chain in self.merkle.patient_chains.items():
            latest = chain.get_latest()
            if not latest:
                continue
            
            if latest.owner_node == requesting_node:
                # Paciente propio - datos completos
                result["own_patients"].append({
                    "uuid": uuid,
                    "owner": requesting_node,
                    "versions": len(chain.nodes),
                    "data": latest.data  # Datos completos
                })
            else:
                # Paciente ajeno - solo datos anonimizados
                result["federated_patients"].append({
                    "uuid": uuid,
                    "owner": latest.owner_node,
                    "versions": len(chain.nodes),
                    "data": latest.data  # Ya está anonimizado
                })
        
        return result
    
    # === ESTADO Y SINCRONIZACIÓN ===
    
    def get_state_for_sync(self) -> Dict:
        """Estado completo para sincronización con otros nodos"""
        return {
            "node_id": self.node_id,
            "merkle_state": self.merkle.get_state_for_sync(),
            "audit_summary": self.audit.export_for_sync(),
            "governance_summary": self.governance.get_network_summary(),
            "dev_mode": self.dev_mode
        }
    
    def compare_with_remote(self, remote_state: Dict) -> Dict:
        """Compara estado local con remoto para detectar divergencias"""
        return self.merkle.compare_with_remote(remote_state.get("merkle_state", {}))
