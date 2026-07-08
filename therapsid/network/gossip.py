"""
Therapsid - Módulo de Red P2P
Protocolo gossip para descubrimiento y sincronización de nodos
"""

import asyncio
import json
import random
import time
from typing import Dict, List, Set, Optional, Callable
from dataclasses import dataclass, asdict
import websockets
import aiohttp
from aiohttp import web

from ..config import NodeConfig, GOSSIP_INTERVAL, MAX_PEERS


@dataclass
class PeerInfo:
    """Información de un peer en la red"""
    node_id: str
    address: str  # IP:puerto o hostname:puerto
    last_seen: float
    capabilities: List[str]  # ["storage", "compute", "bandwidth"]
    region: str
    patients_count: int = 0
    evolutions_count: int = 0
    sinapsid_version: str = "1.0.0"
    is_online: bool = True


class GossipProtocol:
    """
    Implementación del protocolo gossip para Therapsid.
    
    Cada nodo:
    1. Conoce a N peers (3-10)
    2. Cada 60 segundos envía "heartbeat" a 3 peers aleatorios
    3. En el heartbeat incluye: su metadata + metadata de otros peers que conoce
    4. Si no responden en 3 intentos, los marca como offline
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.peers: Dict[str, PeerInfo] = {}
        self.my_info = PeerInfo(
            node_id=config.node_id,
            address=f"127.0.0.1:{config.p2p_port}",  # Se actualiza con IP real
            last_seen=time.time(),
            capabilities=["storage", "compute"],
            region=config.region,
            sinapsid_version="1.0.0",
        )
        self._running = False
        self._gossip_task = None
        self._message_handlers: Dict[str, Callable] = {}
    
    async def start(self):
        """Inicia el protocolo gossip"""
        self._running = True
        
        # Iniciar servidor WebSocket para recibir conexiones
        self._server_task = asyncio.create_task(self._start_server())
        
        # Conectar a peers bootstrap
        for peer_addr in self.config.bootstrap_peers:
            await self._connect_to_peer(peer_addr)
        
        # Iniciar gossip periódico
        self._gossip_task = asyncio.create_task(self._gossip_loop())
        
        print(f"🦊 [Therapsid] Gossip iniciado en puerto {self.config.p2p_port}")
        print(f"   Node ID: {self.config.node_id}")
        print(f"   Peers conocidos: {len(self.peers)}")
    
    async def stop(self):
        """Detiene el protocolo gossip"""
        self._running = False
        if self._gossip_task:
            self._gossip_task.cancel()
        if self._server_task:
            self._server_task.cancel()
        print("🦊 [Therapsid] Gossip detenido")
    
    async def _start_server(self):
        """Inicia servidor WebSocket para recibir peers"""
        async def handler(websocket, path):
            try:
                async for message in websocket:
                    data = json.loads(message)
                    await self._handle_message(data, websocket)
            except websockets.exceptions.ConnectionClosed:
                pass
        
        # Usar puerto configurado
        server = await websockets.serve(
            handler,
            "0.0.0.0",
            self.config.p2p_port,
        )
        await server.wait_closed()
    
    async def _gossip_loop(self):
        """Bucle principal de gossip"""
        while self._running:
            try:
                await self._gossip_round()
                await asyncio.sleep(GOSSIP_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️  Error en gossip: {e}")
                await asyncio.sleep(10)  # Reintentar en 10s
    
    async def _gossip_round(self):
        """Una ronda de gossip: enviar heartbeat a peers seleccionados"""
        # Seleccionar hasta 3 peers aleatorios
        online_peers = [p for p in self.peers.values() if p.is_online]
        
        if not online_peers and not self.config.bootstrap_peers:
            print("🦊 [Therapsid] No hay peers. Esperando conexiones...")
            return
        
        # Priorizar peers que hace más tiempo no vemos
        targets = random.sample(
            online_peers,
            k=min(3, len(online_peers))
        ) if online_peers else []
        
        # También intentar reconectar a bootstrap si no tenemos peers
        if not targets and self.config.bootstrap_peers:
            for addr in random.sample(
                self.config.bootstrap_peers,
                k=min(2, len(self.config.bootstrap_peers))
            ):
                await self._connect_to_peer(addr)
                return
        
        # Enviar heartbeat a cada peer seleccionado
        for peer in targets:
            await self._send_heartbeat(peer)
    
    async def _send_heartbeat(self, peer: PeerInfo):
        """Envía un heartbeat a un peer"""
        message = {
            "type": "HEARTBEAT",
            "sender": asdict(self.my_info),
            "peers": [asdict(p) for p in self.peers.values()],
            "timestamp": time.time(),
        }
        
        try:
            async with websockets.connect(
                f"ws://{peer.address}/gossip",
                timeout=5
            ) as ws:
                await ws.send(json.dumps(message))
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                
                # Actualizar peer como vivo
                peer.last_seen = time.time()
                peer.is_online = True
                
                # Procesar respuesta
                data = json.loads(response)
                if data.get("type") == "HEARTBEAT_ACK":
                    await self._merge_peer_list(data.get("peers", []))
                    
        except Exception as e:
            # Peer no responde, marcar como sospechoso
            peer.is_online = False
            print(f"⚠️  Peer {peer.node_id} no responde: {e}")
    
    async def _handle_message(self, data: dict, websocket):
        """Maneja un mensaje recibido"""
        msg_type = data.get("type")
        
        if msg_type == "HEARTBEAT":
            # Responder con ACK
            response = {
                "type": "HEARTBEAT_ACK",
                "sender": asdict(self.my_info),
                "peers": [asdict(p) for p in self.peers.values()],
            }
            await websocket.send(json.dumps(response))
            
            # Actualizar peer que envió
            sender = data.get("sender", {})
            await self._update_peer(sender)
            
            # Fusionar lista de peers
            await self._merge_peer_list(data.get("peers", []))
            
        elif msg_type in self._message_handlers:
            # Delegar a handler registrado
            handler = self._message_handlers[msg_type]
            await handler(data, websocket)
    
    async def _update_peer(self, peer_data: dict):
        """Actualiza o crea un peer en la lista"""
        node_id = peer_data.get("node_id")
        if not node_id or node_id == self.config.node_id:
            return
        
        if node_id in self.peers:
            # Actualizar existente
            peer = self.peers[node_id]
            peer.last_seen = time.time()
            peer.is_online = True
            peer.patients_count = peer_data.get("patients_count", peer.patients_count)
            peer.evolutions_count = peer_data.get("evolutions_count", peer.evolutions_count)
        else:
            # Nuevo peer
            if len(self.peers) < MAX_PEERS:
                self.peers[node_id] = PeerInfo(
                    node_id=node_id,
                    address=peer_data.get("address", "unknown"),
                    last_seen=time.time(),
                    capabilities=peer_data.get("capabilities", []),
                    region=peer_data.get("region", "UNKNOWN"),
                    patients_count=peer_data.get("patients_count", 0),
                    evolutions_count=peer_data.get("evolutions_count", 0),
                    sinapsid_version=peer_data.get("sinapsid_version", "1.0.0"),
                    is_online=True,
                )
                print(f"🦊 [Therapsid] Nuevo peer descubierto: {node_id} ({peer_data.get('region', 'UNKNOWN')})")
    
    async def _merge_peer_list(self, peers_data: List[dict]):
        """Fusiona una lista de peers recibida"""
        for peer_data in peers_data:
            await self._update_peer(peer_data)
    
    async def _connect_to_peer(self, address: str):
        """Intenta conectar a un peer por su dirección"""
        try:
            async with websockets.connect(
                f"ws://{address}/gossip",
                timeout=5
            ) as ws:
                # Enviar handshake
                handshake = {
                    "type": "HEARTBEAT",
                    "sender": asdict(self.my_info),
                    "peers": [],
                }
                await ws.send(json.dumps(handshake))
                
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                
                if data.get("type") == "HEARTBEAT_ACK":
                    sender = data.get("sender", {})
                    await self._update_peer(sender)
                    await self._merge_peer_list(data.get("peers", []))
                    
        except Exception as e:
            print(f"⚠️  No se pudo conectar a {address}: {e}")
    
    def register_handler(self, msg_type: str, handler: Callable):
        """Registra un handler para un tipo de mensaje personalizado"""
        self._message_handlers[msg_type] = handler
    
    def get_network_stats(self) -> dict:
        """Retorna estadísticas de la red"""
        online = sum(1 for p in self.peers.values() if p.is_online)
        total_patients = sum(p.patients_count for p in self.peers.values())
        total_evolutions = sum(p.evolutions_count for p in self.peers.values())
        
        return {
            "my_node_id": self.config.node_id,
            "peers_total": len(self.peers),
            "peers_online": online,
            "peers_offline": len(self.peers) - online,
            "network_patients": total_patients,
            "network_evolutions": total_evolutions,
            "regions": list(set(p.region for p in self.peers.values())),
        }
    
    def get_peers_list(self) -> List[dict]:
        """Retorna lista de peers para la UI"""
        return [asdict(p) for p in self.peers.values()]
