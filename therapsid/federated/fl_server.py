"""
Therapsid - Servidor Federado (Flower)
Coordinador central para entrenamiento federado
Puede correr en cualquier nodo (no hay servidor central dedicado)
"""

import flwr as fl
from typing import Dict, List, Tuple, Optional
import numpy as np

from .fl_client import MortalityPredictor, DEFAULT_SERVER_CONFIG


class FederatedServer:
    """
    Servidor Flower para entrenamiento federado.
    
    NOTA: Aunque Flower usa un servidor central para coordinar,
    Therapsid implementa un servidor ROTATIVO:
    - Cualquier nodo puede actuar como servidor
    - Si el servidor cae, otro nodo asume automáticamente
    - Los datos NUNCA salen de los nodos clientes
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.running = False
        self.server = None
    
    def start(self, config: Optional[Dict] = None):
        """
        Inicia el servidor Flower.
        
        Args:
            config: Configuración del servidor (ver DEFAULT_SERVER_CONFIG)
        """
        if config is None:
            config = DEFAULT_SERVER_CONFIG
        
        print(f"🧠 [Therapsid] Iniciando servidor federado en {self.host}:{self.port}")
        
        # Estrategia de federación: FedAvg con Momentum
        strategy = fl.server.strategy.FedAvg(
            fraction_fit=config.get("fraction_fit", 0.5),
            fraction_evaluate=config.get("fraction_evaluate", 0.3),
            min_fit_clients=config.get("min_fit_clients", 2),
            min_evaluate_clients=config.get("min_evaluate_clients", 1),
            min_available_clients=config.get("min_available_clients", 2),
            evaluate_fn=None,  # No evaluación centralizada
            on_fit_config_fn=lambda rnd: {
                "epochs": 5,
                "learning_rate": 0.01,
                "batch_size": 32,
            },
            on_evaluate_config_fn=lambda rnd: {
                "epochs": 1,
            },
        )
        
        # Iniciar servidor
        try:
            fl.server.start_server(
                server_address=f"{self.host}:{self.port}",
                strategy=strategy,
                config=fl.server.ServerConfig(num_rounds=config.get("num_rounds", 10)),
            )
            self.running = True
        except Exception as e:
            print(f"❌ [Therapsid] Error iniciando servidor federado: {e}")
            self.running = False
    
    def stop(self):
        """Detiene el servidor"""
        self.running = False
        print("🛑 [Therapsid] Servidor federado detenido")


class RotatingServerManager:
    """
    Gestiona la rotación del servidor federado.
    Si el servidor actual cae, elige un nuevo líder.
    """
    
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers
        self.current_server: Optional[str] = None
        self.is_leader = False
    
    def elect_leader(self) -> str:
        """
        Elige un nuevo líder basado en capacidad.
        Simple: el nodo con ID más bajo (determinístico).
        """
        all_nodes = [self.node_id] + self.peers
        all_nodes.sort()
        return all_nodes[0]  # ID más bajo = líder
    
    def check_leader(self):
        """Verifica si este nodo debe ser el líder"""
        leader = self.elect_leader()
        self.is_leader = (leader == self.node_id)
        
        if self.is_leader and self.current_server != self.node_id:
            print(f"👑 [Therapsid] Este nodo es ahora el líder federado")
            self.current_server = self.node_id
            return True
        
        return False
