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

# Buscar directorio de instalación correcto
THERAPSID_CODE_DIR = Path('/opt/therapsid') if Path('/opt/therapsid').exists() else Path(__file__).parent

# THERAPSID_HOME es la config ( ~/.therapsid/ )
# THERAPSID_CODE_DIR es el código ( /opt/therapsid/ )
from .config import THERAPSID_HOME

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

class ResourceAllocator:
    """Controla cuantos recursos comparte el nodo con la red"""
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.max_ram_percent = 50  # Default: 50% de RAM
        self.max_cpu_percent = 30  # Default: 30% de CPU
        self.max_disk_gb = 5       # Default: 5 GB disco
        self.enabled = True
    
    def set_limits(self, ram_percent: int, cpu_percent: int, disk_gb: int):
        self.max_ram_percent = max(10, min(90, ram_percent))
        self.max_cpu_percent = max(5, min(80, cpu_percent))
        self.max_disk_gb = max(1, min(100, disk_gb))
    
    def get_available_resources(self) -> Dict[str, Any]:
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "ram_limit_mb": (ram.total * self.max_ram_percent // 100) // (1024*1024),
            "ram_used_mb": ram.used // (1024*1024),
            "cpu_limit_percent": self.max_cpu_percent,
            "cpu_current_percent": psutil.cpu_percent(interval=0.5),
            "disk_limit_gb": self.max_disk_gb,
            "disk_used_gb": disk.used // (1024**3),
            "sharing_enabled": self.enabled
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
        self.latency_ms = 0
    
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
    Nodo P2P principal con auth distribuida
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.metrics = ResourceMetrics()
        self.connector = SinapsidConnector(config)
        self.governance = GovernanceManager(config)
        self.auth = None  # Se inicializa en start()
        self.running = False
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Configurar rutas HTTP"""
        # Auth endpoints
        self.app.router.add_post('/api/v1/auth/register', self._auth_register)
        self.app.router.add_post('/api/v1/auth/login', self._auth_login)
        self.app.router.add_post('/api/v1/auth/logout', self._auth_logout)
        self.app.router.add_get('/api/v1/auth/me', self._auth_me)
        
        # Resto de endpoints
        self.app.router.add_get('/', self._index)
        self.app.router.add_get('/dashboard', self._index)
        self.app.router.add_get('/api/v1/health', self._health)
        self.app.router.add_get('/api/v1/node/info', self._node_info)
        self.app.router.add_get('/api/v1/node/resources', self._resources)
        self.app.router.add_post('/api/v1/node/resources/set', self._set_resources)
        self.app.router.add_get('/api/v1/network/status', self._network_status)
        self.app.router.add_get('/api/v1/network/nodes', self._nodes_list)
        self.app.router.add_get('/api/v1/sinapsid/auth', self._sinapsid_auth)
        self.app.router.add_get('/api/v1/sinapsid/iframe', self._sinapsid_iframe)
        self.app.router.add_post('/api/v1/node/shutdown', self._shutdown)
        
        # Static files - buscar en múltiples ubicaciones
        static_paths = [
            THERAPSID_CODE_DIR / 'therapsid' / 'web' / 'static',
            THERAPSID_CODE_DIR / 'web' / 'static',
            Path(__file__).parent / 'web' / 'static',
        ]
        
        for static_path in static_paths:
            if static_path.exists():
                self.app.router.add_static('/static/', 
                    path=str(static_path), 
                    name='static')
                logger.info(f"Static files: {static_path}")
                break
        else:
            logger.warning("No se encontró directorio static")
    
    async def _index(self, request):
        """Dashboard HTML - buscar en múltiples ubicaciones"""
        template_paths = [
            THERAPSID_CODE_DIR / 'therapsid' / 'web' / 'templates' / 'dashboard.html',
            THERAPSID_CODE_DIR / 'web' / 'templates' / 'dashboard.html',
            Path(__file__).parent / 'web' / 'templates' / 'dashboard.html',
        ]
        
        for dashboard_path in template_paths:
            try:
                if dashboard_path.exists():
                    with open(dashboard_path) as f:
                        html = f.read()
                    return web.Response(text=html, content_type='text/html')
            except Exception as e:
                logger.error(f"Error cargando dashboard de {dashboard_path}: {e}")
        
        # Si no encuentra template, servir fallback
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
    
    async def _sinapsid_iframe(self, request):
        """Servir Sinapsid dentro de iframe"""
        html = '''
        <!DOCTYPE html>
        <html><head><title>Sinapsid Federado</title>
        <style>
            body { margin: 0; padding: 0; background: #0a0a0f; }
            .header { 
                background: linear-gradient(135deg, #1a1a2e, #12121a); 
                padding: 10px 20px; 
                border-bottom: 2px solid #ff006e;
                display: flex; align-items: center; justify-content: space-between;
            }
            .header h1 { 
                color: #ff006e; 
                margin: 0; 
                font-family: 'JetBrains Mono', monospace;
                font-size: 1.2rem;
            }
            .header p { color: #8892b0; margin: 0; font-size: 0.8rem; }
            .btn-back { 
                background: #ff006e; color: white; border: none; 
                padding: 8px 16px; border-radius: 20px; cursor: pointer;
                text-decoration: none; font-size: 0.9rem;
            }
            iframe { width: 100%; height: calc(100vh - 60px); border: none; }
        </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <h1>🦊 SINAPSID FEDERADO</h1>
                    <p>Ejecutandose sobre red Therapsid · xiu-HOME:5002</p>
                </div>
                <a href="/dashboard" class="btn-back">← Dashboard</a>
            </div>
            <iframe src="http://100.127.123.55:5002"></iframe>
        </body>
        </html>
        '''
        return web.Response(text=html, content_type='text/html')
    
    async def _sinapsid_auth(self, request):
        """Proxy auth para Sinapsid"""
        return web.json_response({
            "auth_url": "http://100.127.123.55:5002/login",
            "note": "Usa tu cuenta Sinapsid existente"
        })
    
    async def _nodes_list(self, request):
        """Lista de nodos en la red"""
        return web.json_response({
            "nodes": [
                {
                    "id": "xiu-home",
                    "name": "Sinapsid Admin (xiu-HOME)",
                    "url": "http://100.127.123.55:5002",
                    "status": "online" if self.connector.connected else "offline",
                    "weight": self.connector.node_weight,
                    "patients": self.connector.patients_count,
                    "role": "admin"
                },
                {
                    "id": self.config.node_id,
                    "name": self.config.node_name,
                    "url": f"http://localhost:{self.config.web_port}",
                    "status": "online",
                    "weight": 0,
                    "patients": 0,
                    "role": "peer"
                }
            ],
            "leader": self.governance.leader_id,
            "total_nodes": 2 if self.connector.connected else 1
        })
    
    async def _set_resources(self, request):
        """Configurar limites de recursos"""
        try:
            data = await request.json()
            ram = data.get('ram_percent', 50)
            cpu = data.get('cpu_percent', 30)
            disk = data.get('disk_gb', 5)
            
            ram = max(10, min(90, ram))
            cpu = max(5, min(80, cpu))
            disk = max(1, min(100, disk))
            
            self.config.resource_limits = {
                "max_ram_percent": ram,
                "max_cpu_percent": cpu,
                "max_disk_gb": disk
            }
            self.config.save()
            
            return web.json_response({
                "status": "ok",
                "limits": {
                    "ram_percent": ram,
                    "cpu_percent": cpu,
                    "disk_gb": disk
                }
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _shutdown(self, request):
        """Detener nodo"""
        self.running = False
        asyncio.create_task(self.stop())
        return web.json_response({"status": "shutting_down"})
    
    # === AUTH DISTRIBUIDO ===
    
    async def _auth_register(self, request):
        """Registrar nuevo usuario"""
        try:
            data = await request.json()
            success, message = self.auth.register_user(
                email=data.get('email'),
                password=data.get('password'),
                name=data.get('name'),
                role=data.get('role', 'user'),
                hospital=data.get('hospital'),
                node_id=self.config.node_id
            )
            return web.json_response({"success": success, "message": message})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)
    
    async def _auth_login(self, request):
        """Login y emitir token JWT"""
        try:
            data = await request.json()
            success, token, user_data = self.auth.authenticate(
                email=data.get('email'),
                password=data.get('password')
            )
            
            if success:
                return web.json_response({
                    "success": True,
                    "token": token,
                    "user": user_data,
                    "node": self.config.node_id
                })
            else:
                return web.json_response({
                    "success": False,
                    "error": "Credenciales invalidas"
                }, status=401)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)
    
    async def _auth_logout(self, request):
        """Logout y revocar token"""
        try:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                self.auth.revoke_token(token)
            return web.json_response({"success": True, "message": "Sesion cerrada"})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)
    
    async def _auth_me(self, request):
        """Obtener info del usuario autenticado"""
        try:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return web.json_response({"error": "No autenticado"}, status=401)
            
            token = auth_header[7:]
            valid, payload = self.auth.validate_token(token)
            
            if not valid:
                return web.json_response({"error": "Token invalido"}, status=401)
            
            return web.json_response({
                "user": {
                    "id": payload.get('sub'),
                    "email": payload.get('email'),
                    "name": payload.get('name'),
                    "role": payload.get('role'),
                    "hospital": payload.get('hospital'),
                    "node": payload.get('node_id')
                }
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
        """Detener nodo"""
        self.running = False
        asyncio.create_task(self.stop())
        return web.json_response({"status": "shutting_down"})
    
    async def start(self):
        """Iniciar nodo"""
        self.running = True
        self.start_time = time.time()
        
        # Inicializar auth distribuido
        from .auth_distributed import DistributedAuth
        self.auth = DistributedAuth(THERAPSID_HOME / 'auth.db')
        self.auth.create_demo_user()
        
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
