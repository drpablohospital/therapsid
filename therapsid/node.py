"""
Therapsid v2.0 - Nodo P2P Puro
No incluye Sinapsid local. Se conecta a xiu-HOME:5002
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp
from aiohttp import web

from .config import NodeConfig, THERAPSID_HOME

logger = logging.getLogger("therapsid")

class ResourceMetrics:
    """Metricas de recursos del nodo"""
    
    def __init__(self):
        self.cpu_percent = 0.0
        self.ram_used_mb = 0
        self.ram_total_mb = 0
        self.disk_used_gb = 0
        self.disk_total_gb = 0
        self.network_rx_mb = 0
        self.network_tx_mb = 0
        self.last_update = time.time()
    
    def update(self):
        """Actualizar metricas"""
        self.cpu_percent = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        self.ram_used_mb = ram.used // (1024 * 1024)
        self.ram_total_mb = ram.total // (1024 * 1024)
        disk = psutil.disk_usage('/')
        self.disk_used_gb = disk.used // (1024**3)
        self.disk_total_gb = disk.total // (1024**3)
        net = psutil.net_io_counters()
        self.network_rx_mb = net.bytes_recv // (1024 * 1024)
        self.network_tx_mb = net.bytes_sent // (1024 * 1024)
        self.last_update = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "ram_available_mb": self.ram_total_mb - self.ram_used_mb,
            "disk_used_gb": self.disk_used_gb,
            "disk_total_gb": self.disk_total_gb,
            "network_rx_mb": self.network_rx_mb,
            "network_tx_mb": self.network_tx_mb,
            "timestamp": self.last_update
        }

class SinapsidConnector:
    """
    Conector al nodo administrador (xiu-HOME:5002)
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.admin_url = "http://100.127.123.55:5002"  # xiu-HOME
        self.connected = False
        self.last_heartbeat = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.patients_count = 0
        self.evolutions_count = 0
        self.node_weight = 0  # PoP weight
    
    async def connect(self):
        """Conectar a xiu-HOME"""
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(f"{self.admin_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.connected = True
                    logger.info(f"Conectado a xiu-HOME: {data}")
                    return True
        except Exception as e:
            logger.warning(f"No se pudo conectar a xiu-HOME: {e}")
            self.connected = False
            return False
    
    async def heartbeat(self):
        """Enviar heartbeat a xiu-HOME"""
        if not self.session:
            return
        
        try:
            payload = {
                "node_id": self.config.node_id,
                "node_name": self.config.node_name,
                "region": self.config.region,
                "resources": ResourceMetrics().to_dict(),
                "timestamp": time.time()
            }
            
            async with self.session.post(
                f"{self.admin_url}/api/nodes/heartbeat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    self.last_heartbeat = time.time()
                    data = await resp.json()
                    self.patients_count = data.get("patients_count", 0)
                    self.evolutions_count = data.get("evolutions_count", 0)
                    self.node_weight = data.get("node_weight", 0)
                    logger.debug("Heartbeat enviado")
        except Exception as e:
            logger.warning(f"Heartbeat fallido: {e}")
            self.connected = False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadisticas de xiu-HOME"""
        if not self.session:
            return {"error": "No conectado"}
        
        try:
            async with self.session.get(f"{self.admin_url}/api/stats") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e)}
        
        return {"error": "No data"}
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

class GovernanceManager:
    """
    Gobernanza por Proof-of-Patients (PoP)
    Si el admin (xiu-HOME) desaparece, el nodo con mas peso asume
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.nodes: List[Dict[str, Any]] = []
        self.leader_id = None
        self.leader_url = None
        self.is_leader = False
        self.last_election = 0
    
    async def check_leader(self, connector: SinapsidConnector):
        """Verificar si el lider sigue vivo"""
        if connector.connected:
            # xiu-HOME sigue vivo, es el lider
            self.leader_id = "xiu-home"
            self.leader_url = connector.admin_url
            self.is_leader = False
            return True
        
        # xiu-HOME offline, iniciar eleccion
        await self._initiate_election()
        return False
    
    async def _initiate_election(self):
        """Iniciar eleccion de nuevo lider"""
        logger.info("Iniciando eleccion de lider...")
        
        # El nodo con mas pacientes/recursos gana
        if not self.nodes:
            # Solo yo existo, me convierto en lider
            self.is_leader = True
            self.leader_id = self.config.node_id
            logger.info(f"Soy el nuevo lider: {self.config.node_id}")
            return
        
        # Encontrar nodo con mayor peso
        weights = [(n["id"], n.get("weight", 0)) for n in self.nodes]
        weights.append((self.config.node_id, self._calculate_local_weight()))
        
        leader = max(weights, key=lambda x: x[1])
        self.leader_id = leader[0]
        self.is_leader = (leader[0] == self.config.node_id)
        
        logger.info(f"Nuevo lider: {self.leader_id} (peso: {leader[1]})")
    
    def _calculate_local_weight(self) -> int:
        """Calcular peso local (pacientes + recursos)"""
        try:
            # Simulado - en realidad vendria de Sinapsid
            return 100  # Base weight
        except:
            return 0
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "leader_id": self.leader_id,
            "is_leader": self.is_leader,
            "nodes_count": len(self.nodes) + 1,  # +1 por mi mismo
            "last_election": self.last_election
        }

class TherapsidNode:
    """
    Nodo P2P principal
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.metrics = ResourceMetrics()
        self.connector = SinapsidConnector(config)
        self.governance = GovernanceManager(config)
        self.running = False
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Configurar rutas HTTP"""
        self.app.router.add_get('/', self._index)
        self.app.router.add_get('/api/v1/health', self._health)
        self.app.router.add_get('/api/v1/node/info', self._node_info)
        self.app.router.add_get('/api/v1/node/resources', self._resources)
        self.app.router.add_get('/api/v1/network/status', self._network_status)
        self.app.router.add_post('/api/v1/node/shutdown', self._shutdown)
        self.app.router.add_static('/static/', 
            path=str(THERAPSID_HOME / 'web' / 'static'), 
            name='static')
    
    async def _index(self, request):
        """Dashboard HTML"""
        try:
            dashboard_path = THERAPSID_HOME / 'web' / 'templates' / 'dashboard.html'
            if dashboard_path.exists():
                with open(dashboard_path) as f:
                    html = f.read()
                return web.Response(text=html, content_type='text/html')
        except Exception as e:
            logger.error(f"Error cargando dashboard: {e}")
        
        return web.Response(text=self._get_fallback_dashboard(), content_type='text/html')
    
    def _get_fallback_dashboard(self) -> str:
        """Dashboard fallback"""
        return """<!DOCTYPE html>
<html><head><title>Therapsid Node</title></head>
<body><h1>Therapsid v2.0</h1><p>Cargando...</p></body></html>"""
    
    async def _health(self, request):
        """Health check"""
        return web.json_response({
            "status": "ok",
            "version": "2.0.0",
            "node_id": self.config.node_id,
            "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        })
    
    async def _node_info(self, request):
        """Informacion completa del nodo"""
        self.metrics.update()
        
        return web.json_response({
            "node": {
                "id": self.config.node_id,
                "name": self.config.node_name,
                "region": self.config.region,
                "type": self.config.account_type,
                "version": "2.0.0"
            },
            "resources": self.metrics.to_dict(),
            "network": {
                "connected_to_admin": self.connector.connected,
                "admin_url": self.connector.admin_url,
                "patients_count": self.connector.patients_count,
                "evolutions_count": self.connector.evolutions_count
            },
            "governance": self.governance.get_status()
        })
    
    async def _resources(self, request):
        """Metricas de recursos"""
        self.metrics.update()
        return web.json_response(self.metrics.to_dict())
    
    async def _network_status(self, request):
        """Estado de la red"""
        return web.json_response({
            "admin_connected": self.connector.connected,
            "leader": self.governance.leader_id,
            "is_leader": self.governance.is_leader,
            "nodes": len(self.governance.nodes) + 1
        })
    
    async def _shutdown(self, request):
        """Detener nodo"""
        self.running = False
        asyncio.create_task(self.stop())
        return web.json_response({"status": "shutting_down"})
    
    async def start(self):
        """Iniciar nodo"""
        self.running = True
        self.start_time = time.time()
        
        logger.info("=" * 50)
        logger.info("  THERAPSID v2.0 - Nodo P2P")
        logger.info("  Red Federada Latinoamericana")
        logger.info("=" * 50)
        logger.info(f"Node ID: {self.config.node_id}")
        logger.info(f"Region: {self.config.region}")
        logger.info(f"Admin: {self.connector.admin_url}")
        
        # Conectar a xiu-HOME
        await self.connector.connect()
        
        # Iniciar tareas en background
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._metrics_loop())
        
        # Iniciar servidor HTTP
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.config.web_port)
        await site.start()
        
        logger.info(f"🌐 Dashboard: http://localhost:{self.config.web_port}/dashboard")
        logger.info(f"🏥 Admin: {self.connector.admin_url}")
        logger.info("=" * 50)
        
        # Mantener vivo
        while self.running:
            await asyncio.sleep(1)
        
        await runner.cleanup()
    
    async def stop(self):
        """Detener nodo"""
        self.running = False
        await self.connector.close()
        logger.info("Therapsid detenido")
    
    async def _heartbeat_loop(self):
        """Enviar heartbeat cada 30 segundos"""
        while self.running:
            await self.connector.heartbeat()
            await self.governance.check_leader(self.connector)
            await asyncio.sleep(30)
    
    async def _metrics_loop(self):
        """Actualizar metricas cada 5 segundos"""
        while self.running:
            self.metrics.update()
            await asyncio.sleep(5)

# Singleton
_node: Optional[TherapsidNode] = None

def get_node() -> Optional[TherapsidNode]:
    return _node

def set_node(node: TherapsidNode):
    global _node
    _node = node
