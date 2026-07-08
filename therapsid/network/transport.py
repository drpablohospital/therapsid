"""
Therapsid - Módulo de Transporte HTTP
Fallback HTTP para cuando WebSocket no está disponible
API REST para integración con Sinapsid
"""

import asyncio
import json
from aiohttp import web
from typing import Dict, Optional

from .gossip import GossipProtocol
from ..auth_adapter import get_auth, AuthMiddleware


class HTTPTransport:
    """
    Transporte HTTP como fallback y API REST.
    Corre en paralelo con el gossip WebSocket.
    """
    
    def __init__(self, gossip: GossipProtocol, port: int = 8767, sinapsid_adapter=None):
        self.gossip = gossip
        self.port = port
        self.sinapsid = sinapsid_adapter
        self.auth = get_auth()
        self.auth_middleware = AuthMiddleware(self.auth)
        self.app = web.Application()
        self._setup_routes()
        self.runner = None
    
    def _setup_routes(self):
        """Configura las rutas de la API"""
        self.app.router.add_get("/", self._dashboard_redirect)
        self.app.router.add_get("/dashboard", self._dashboard)
        self.app.router.add_get("/health", self._health_check)
        self.app.router.add_get("/status", self._status)
        self.app.router.add_get("/peers", self._get_peers)
        self.app.router.add_get("/network/stats", self._network_stats)
        self.app.router.add_post("/gossip/message", self._receive_gossip_message)
        self.app.router.add_get("/sinapsid/local", self._sinapsid_local_status)
        self.app.router.add_get("/api/v1/node/info", self._node_info)
        self.app.router.add_get("/api/v1/sinapsid/stats", self._sinapsid_stats)
        self.app.router.add_get("/api/v1/updater/check", self._check_updates)
        self.app.router.add_post("/api/v1/node/shutdown", self._shutdown)
        
        # Endpoints protegidos (envío/recepción de datos)
        self.app.router.add_post("/api/v1/data/send", self._send_data)
        self.app.router.add_get("/api/v1/data/receive", self._receive_data)
        self.app.router.add_get("/api/v1/data/pending", self._get_pending_data)
        self.app.router.add_post("/api/v1/auth/login", self._login)
        self.app.router.add_post("/api/v1/auth/logout", self._logout)
        
        # Servir archivos estáticos (CSS, imágenes, etc)
        import os
        static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'static')
        if os.path.exists(static_path):
            self.app.router.add_static('/static/', path=static_path, name='static')
        
        # Servir templates
        templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'templates')
        if os.path.exists(templates_path):
            self.app.router.add_static('/templates/', path=templates_path, name='templates')
    
    async def _check_updates(self, request):
        """Chequea si hay actualizaciones disponibles"""
        try:
            from ..updater import get_updater
            updater = get_updater()
            result = updater.check_for_updates()
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"has_update": False, "error": str(e)})
    
    async def _shutdown(self, request):
        """Apaga el nodo Therapsid"""
        import asyncio
        asyncio.create_task(self.stop())
        if self.gossip:
            await self.gossip.stop()
        return web.json_response({"success": True, "message": "Therapsid detenido"})
    
    # Auth handlers
    
    async def start(self):
        """Inicia el servidor HTTP"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()
        print(f"🌐 [Therapsid] HTTP API en http://0.0.0.0:{self.port}")
    
    async def stop(self):
        """Detiene el servidor HTTP"""
        if self.runner:
            await self.runner.cleanup()
    
    # Handlers
    async def _health_check(self, request):
        """Endpoint de health check"""
        return web.json_response({
            "status": "healthy",
            "node_id": self.gossip.config.node_id,
            "timestamp": asyncio.get_event_loop().time(),
        })
    
    async def _status(self, request):
        """Estado completo del nodo"""
        return web.json_response({
            "node_id": self.gossip.config.node_id,
            "node_name": self.gossip.config.node_name,
            "account_type": self.gossip.config.account_type,
            "region": self.gossip.config.region,
            "p2p_port": self.gossip.config.p2p_port,
            "web_port": self.gossip.config.web_port,
            "sinapsid_enabled": self.gossip.config.sinapsid_enabled,
            "federation_enabled": self.gossip.config.federation_enabled,
            "peers_count": len(self.gossip.peers),
        })
    
    async def _get_peers(self, request):
        """Lista de peers conocidos"""
        return web.json_response({
            "peers": self.gossip.get_peers_list()
        })
    
    async def _network_stats(self, request):
        """Estadísticas de la red"""
        return web.json_response(self.gossip.get_network_stats())
    
    async def _receive_gossip_message(self, request):
        """Recibe un mensaje gossip vía HTTP (fallback)"""
        try:
            data = await request.json()
            # Procesar como mensaje gossip
            # Nota: En implementación real, esto delegaría al gossip handler
            return web.json_response({"status": "received"})
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=400
            )
    
    async def _dashboard_redirect(self, request):
        """Redirige / a /dashboard"""
        raise web.HTTPFound("/dashboard")
    
    async def _dashboard(self, request):
        """Dashboard web del nodo Therapsid"""
        import os
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'web', 'templates', 'dashboard.html'
        )
        
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                html = f.read()
            html = html.replace('{{VERSION}}', '0.1.3')
        else:
            html = self._get_fallback_dashboard()
        
        return web.Response(text=html, content_type="text/html")
    
    def _get_fallback_dashboard(self) -> str:
        """Dashboard fallback si no encuentra template"""
        return '<!DOCTYPE html><html><head><title>Therapsid</title></head><body><h1>Therapsid Node</h1><p>Cargando dashboard...</p></body></html>'
    
    async def _node_info(self, request):
        """Información completa del nodo (API v1)"""
        network_stats = self.gossip.get_network_stats()
        sinapsid_stats = {}
        if self.sinapsid:
            sinapsid_stats = self.sinapsid.get_stats()
        
        return web.json_response({
            "node": {
                "id": self.gossip.config.node_id,
                "name": self.gossip.config.node_name,
                "type": self.gossip.config.account_type,
                "region": self.gossip.config.region,
                "version": "0.1.0",
            },
            "network": network_stats,
            "sinapsid": sinapsid_stats,
            "resources": {
                "max_storage_mb": self.gossip.config.max_storage_mb,
                "max_cpu_percent": self.gossip.config.max_cpu_percent,
                "max_bandwidth_mbps": self.gossip.config.max_bandwidth_mbps,
            },
        })
    
    async def _sinapsid_stats(self, request):
        """Estadísticas de Sinapsid local"""
        if not self.sinapsid:
            return web.json_response({"error": "Sinapsid no disponible"}, status=503)
        
        stats = self.sinapsid.get_stats()
        return web.json_response(stats)
    
    def _get_dashboard_html(self) -> str:
        """Genera HTML del dashboard"""
        return DASHBOARD_HTML
    
    async def _sinapsid_local_status(self, request):
        """Estado de la instancia local de Sinapsid"""
        if self.sinapsid:
            stats = self.sinapsid.get_stats()
            return web.json_response(stats)
        return web.json_response({
            "running": False,
            "message": "Sinapsid no está configurado"
        })
    
    # === Auth Handlers ===
    
    async def _login(self, request):
        """Login con credenciales de Sinapsid"""
        try:
            data = await request.json()
            username = data.get('username', '').lower()
            password = data.get('password', '')
            
            # TODO: Verificar contra base de datos de Sinapsid
            # Por ahora, acepta demo/demo
            if username == 'demo' and password == 'demo':
                token = self.auth.create_session_token(1)
                return web.json_response({
                    'success': True,
                    'token': token,
                    'role': 'visitor',
                    'message': 'Login exitoso (modo demo)'
                })
            
            return web.json_response({
                'success': False,
                'error': 'Credenciales inválidas'
            }, status=401)
        except:
            return web.json_response({
                'success': False,
                'error': 'Formato inválido'
            }, status=400)
    
    async def _logout(self, request):
        """Logout - invalida sesión"""
        return web.json_response({
            'success': True,
            'message': 'Sesión cerrada'
        })
    
    # === Data Sync Handlers ===
    
    async def _send_data(self, request):
        """
        Envía datos anonimizados a la red P2P.
        Requiere autenticación (admin/coordinator/clinician).
        """
        user = await self.auth_middleware.authenticate_request(request)
        if not user:
            return web.json_response({'error': 'No autenticado'}, status=401)
        
        if not self.auth.can_send_data(user.get('role', '')):
            return web.json_response({'error': 'Sin permisos'}, status=403)
        
        try:
            data = await request.json()
            
            # Anonimizar datos antes de enviar
            from ..sync import SyncManager
            sync = SyncManager(self.gossip.config)
            packet = sync.create_sync_packet(data)
            
            # Enviar a peers
            await self.gossip.broadcast_sync_packet(packet)
            
            return web.json_response({
                'success': True,
                'message': 'Datos enviados a la red',
                'peers_notified': len(self.gossip.peers)
            })
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    async def _receive_data(self, request):
        """
        Recibe datos sincronizados de la red.
        Requiere autenticación.
        """
        user = await self.auth_middleware.authenticate_request(request)
        if not user:
            return web.json_response({'error': 'No autenticado'}, status=401)
        
        # Listar paquetes pendientes
        from ..sync import SyncManager
        sync = SyncManager(self.gossip.config)
        pending = sync.get_pending_packets()
        
        return web.json_response({
            'success': True,
            'packets': pending,
            'count': len(pending)
        })
    
    async def _get_pending_data(self, request):
        """Obtiene lista de paquetes pendientes por procesar"""
        user = await self.auth_middleware.authenticate_request(request)
        if not user:
            return web.json_response({'error': 'No autenticado'}, status=401)
        
        return web.json_response({
            'success': True,
            'pending': [],  # TODO: Implementar cola
            'count': 0
        })


# HTML del Dashboard Web - Estética Sinapsid + Therapsid
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Therapsid Node - SINAPSID Network</title>
    <style>
        :root {
            /* Tema Sinapsid (azul) + Acentos Therapsid */
            --bg-dark: #1a2332;
            --bg-card: #252f42;
            --bg-hover: #2d3b55;
            --accent-blue: #4a90d9;
            --accent-light: #6ab3ff;
            --accent-orange: #ff6b35;
            --accent-green: #4ade80;
            --text-primary: #e0e0e0;
            --text-secondary: #a8d4ff;
            --border: rgba(74,144,217,0.2);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a2332 0%, #2d3b55 100%);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #2d3b55 0%, #344866 100%);
            padding: 1.5rem 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border-bottom: 2px solid var(--accent-blue);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .header .logo { 
            width: 50px; 
            height: 50px;
            border-radius: 12px;
        }
        .header h1 { font-size: 1.5rem; color: var(--accent-light); }
        .header .subtitle { 
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-left: auto;
        }
        .header .version { 
            background: rgba(74,144,217,0.2);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            color: var(--accent-light);
            border: 1px solid var(--accent-blue);
        }
        .nav-tabs {
            display: flex;
            gap: 0;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 0 2rem;
        }
        .nav-tab {
            padding: 1rem 1.5rem;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
            color: var(--text-secondary);
        }
        .nav-tab:hover { color: var(--accent-light); }
        .nav-tab.active {
            color: var(--accent-orange);
            border-bottom-color: var(--accent-orange);
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-top: 1.5rem;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(74,144,217,0.15);
        }
        .card h2 {
            font-size: 1.1rem;
            color: var(--accent-light);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.75rem;
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .status-online { background: rgba(74,222,128,0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }
        .status-offline { background: rgba(255,107,107,0.15); color: var(--accent-orange); border: 1px solid var(--accent-orange); }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: var(--text-secondary); font-size: 0.9rem; }
        .metric-value { font-weight: 600; color: var(--accent-light); }
        .peers-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .peer-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            background: rgba(74,144,217,0.05);
            border-radius: 8px;
            margin-bottom: 0.5rem;
            border: 1px solid var(--border);
        }
        .peer-item:hover { background: rgba(74,144,217,0.1); }
        .peer-name { font-weight: 500; }
        .peer-region { 
            font-size: 0.75rem; 
            color: var(--text-secondary); 
            background: rgba(74,144,217,0.1);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }
        .sinapsid-panel {
            background: linear-gradient(135deg, rgba(74,144,217,0.1) 0%, rgba(106,179,255,0.05) 100%);
            border: 1px solid var(--accent-blue);
            border-radius: 12px;
            padding: 1.5rem;
        }
        .sinapsid-panel h2 { color: var(--accent-blue); }
        .btn {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, var(--accent-blue) 0%, #357abd 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
        }
        .btn:hover {
            box-shadow: 0 4px 12px rgba(74,144,217,0.3);
            transform: translateY(-1px);
        }
        .footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }
        .sync-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.5rem;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/img/sinapsid-logo.png" alt="SINAPSID" class="logo" onerror="this.style.display='none'">
        <div>
            <h1>🦊 Therapsid Node</h1>
            <span style="color: var(--text-secondary); font-size: 0.9rem;">Nodo P2P Federado · SINAPSID Network</span>
        </div>
        <span class="subtitle">Descentralizado · Seguro · Colaborativo</span>
        <span class="version" id="node-version">v0.1.0</span>
    </div>
    
    <div class="nav-tabs">
        <div class="nav-tab active" onclick="showTab('overview')">📊 Visión General</div>
        <div class="nav-tab" onclick="showTab('network')">🌐 Red P2P</div>
        <div class="nav-tab" onclick="showTab('sinapsid')">🏥 Sinapsid Local</div>
        <div class="nav-tab" onclick="showTab('sync')">🔄 Sincronización</div>
    </div>
    
    <div class="container">
        <!-- TAB: OVERVIEW -->
        <div id="tab-overview" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h2>📡 Estado del Nodo</h2>
                    <div class="metric">
                        <span class="metric-label">ID</span>
                        <span class="metric-value" id="node-id">Cargando...</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Nombre</span>
                        <span class="metric-value" id="node-name">Cargando...</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Estado</span>
                        <span class="metric-value"><span class="status-badge status-online">● Online</span></span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Región</span>
                        <span class="metric-value" id="node-region">Cargando...</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Uptime</span>
                        <span class="metric-value" id="node-uptime">Cargando...</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🌐 Red P2P</h2>
                    <div class="metric">
                        <span class="metric-label">Peers Conectados</span>
                        <span class="metric-value" id="peers-count">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Mensajes Recibidos</span>
                        <span class="metric-value" id="messages-received">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Último Heartbeat</span>
                        <span class="metric-value" id="last-heartbeat">Nunca</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Sincronización</span>
                        <span class="metric-value"><span class="sync-indicator" style="background: var(--accent-green);"></span>Activa</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>💾 Recursos</h2>
                    <div class="metric">
                        <span class="metric-label">Almacenamiento</span>
                        <span class="metric-value" id="storage">Cargando...</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Base de Datos</span>
                        <span class="metric-value" id="db-size">Cargando...</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Ancho de Banda</span>
                        <span class="metric-value" id="bandwidth">Cargando...</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- TAB: NETWORK -->
        <div id="tab-network" class="tab-content" style="display:none;">
            <div class="card">
                <h2>🌐 Nodos en la Red</h2>
                <div class="peers-list" id="peers-list">
                    <p style="color: var(--text-secondary); text-align: center; padding: 2rem;">
                        No hay peers conectados. El nodo está esperando conexiones...
                    </p>
                </div>
            </div>
        </div>
        
        <!-- TAB: SINAPSID -->
        <div id="tab-sinapsid" class="tab-content" style="display:none;">
            <div class="sinapsid-panel">
                <h2>🏥 Sinapsid Local</h2>
                <div class="metric">
                    <span class="metric-label">Estado</span>
                    <span class="metric-value" id="sinapsid-status">Cargando...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">URL</span>
                    <span class="metric-value"><a href="http://localhost:8766" style="color: var(--accent-light);">localhost:8766</a></span>
                </div>
                <div class="metric">
                    <span class="metric-label">Pacientes</span>
                    <span class="metric-value" id="sinapsid-patients">Cargando...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Evoluciones</span>
                    <span class="metric-value" id="sinapsid-evolutions">Cargando...</span>
                </div>
                <div style="margin-top: 1rem;">
                    <a href="http://localhost:8766" class="btn">Abrir Sinapsid →</a>
                </div>
            </div>
        </div>
        
        <!-- TAB: SYNC -->
        <div id="tab-sync" class="tab-content" style="display:none;">
            <div class="card">
                <h2>🔄 Sincronización P2P</h2>
                <div class="metric">
                    <span class="metric-label">Estado</span>
                    <span class="metric-value"><span class="sync-indicator" style="background: var(--accent-green);"></span>Escuchando...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Paquetes Enviados</span>
                    <span class="metric-value" id="packets-sent">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Paquetes Recibidos</span>
                    <span class="metric-value" id="packets-received">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Último Sync</span>
                    <span class="metric-value" id="last-sync">Nunca</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🦊 <strong>Therapsid</strong> · Nodo P2P para <strong>SINAPSID</strong> · AGPL-3.0</p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;">
                Descentralizado · Cifrado · Sin datos de pacientes · 
                <a href="https://github.com/sinapsid/therapsid" style="color: var(--accent-blue);">GitHub</a>
            </p>
        </div>
    </div>
    
    <script>
        function showTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tab).style.display = 'block';
            event.target.classList.add('active');
        }
        
        async function updateDashboard() {
            try {
                const response = await fetch('/api/v1/node/info');
                const data = await response.json();
                
                document.getElementById('node-id').textContent = data.node_id ? data.node_id.substring(0, 20) + '...' : 'N/A';
                document.getElementById('node-name').textContent = data.node_name || 'Sin nombre';
                document.getElementById('node-region').textContent = data.region || 'N/A';
                document.getElementById('node-uptime').textContent = data.uptime || '0s';
                document.getElementById('peers-count').textContent = data.peers_count || 0;
                document.getElementById('storage').textContent = data.storage || 'N/A';
                
                // Peers list
                const peersList = document.getElementById('peers-list');
                if (data.peers && data.peers.length > 0) {
                    peersList.innerHTML = data.peers.map(peer => `
                        <div class="peer-item">
                            <span class="peer-name">${peer.name || 'Anónimo'}</span>
                            <span class="peer-region">${peer.region || 'N/A'}</span>
                            <span class="status-badge ${peer.online ? 'status-online' : 'status-offline'}">
                                ${peer.online ? '● Online' : '● Offline'}
                            </span>
                        </div>
                    `).join('');
                }
            } catch (e) {
                console.error('Error actualizando dashboard:', e);
            }
        }
        
        // Actualizar cada 5 segundos
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""
