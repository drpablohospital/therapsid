#!/usr/bin/env python3
"""
Therapsid - Punto de entrada principal

Comandos:
    python -m therapsid init     # Configurar nodo nuevo
    python -m therapsid start    # Iniciar nodo
    python -m therapsid stop     # Detener nodo
    python -m therapsid status   # Ver estado
    python -m therapsid reset    # Resetear configuración

"""

import sys
import asyncio
import argparse
from pathlib import Path

# Agregar el directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from therapsid.config import NodeConfig, ensure_directories
from therapsid.crypto import generate_node_id, LocalCrypto
from therapsid.network.gossip import GossipProtocol
from therapsid.network.transport import HTTPTransport
from therapsid.sinapsid_adapter import SinapsidAdapter
from therapsid.sinapsid_bridge import SinapsidBridge
from therapsid.consensus import GovernanceMode
from therapsid.recovery import RecoveryManager


class TherapsidCLI:
    """Interfaz de línea de comandos para Therapsid"""
    
    def __init__(self):
        self.node = None
        self.gossip = None
        self.transport = None
        self.sinapsid = None
    
    def init(self, args):
        """Inicializa un nuevo nodo Therapsid"""
        print("🦊 [Therapsid] Inicializando nodo nuevo...")
        
        ensure_directories()
        
        # Crear configuración
        config = NodeConfig.load()
        
        if not config.node_id:
            config.node_id = generate_node_id()
        
        # Preguntar configuración básica
        print("\n--- Configuración del Nodo ---")
        
        name = input(f"Nombre del nodo [{config.node_name}]: ").strip()
        if name:
            config.node_name = name
        
        print("\nTipo de cuenta:")
        print("  1. individual - Médico o investigador individual")
        print("  2. hospital - Institución hospitalaria")
        print("  3. admin - Administrador de la red")
        tipo = input("Selecciona [1]: ").strip() or "1"
        account_types = {"1": "individual", "2": "hospital", "3": "admin"}
        config.account_type = account_types.get(tipo, "individual")
        
        region = input(f"Región (ej. MX-QUE) [{config.region}]: ").strip()
        if region:
            config.region = region
        
        # Configurar puertos
        print(f"\nPuertos (dejar en blanco para defaults):")
        p2p = input(f"  P2P Gossip [{config.p2p_port}]: ").strip()
        if p2p:
            config.p2p_port = int(p2p)
        
        web = input(f"  Web UI [{config.web_port}]: ").strip()
        if web:
            config.web_port = int(web)
        
        # Bootstrap peers
        print("\nPeers bootstrap (direcciones IP:puerto, vacío para terminar):")
        peers = []
        while True:
            peer = input(f"  Peer {len(peers)+1}: ").strip()
            if not peer:
                break
            peers.append(peer)
        config.bootstrap_peers = peers
        
        # Guardar configuración
        config.save()
        
        print(f"\n✅ Nodo inicializado: {config.node_id}")
        print(f"   Configuración guardada en: {Path.home() / '.therapsid' / 'config' / 'config.json'}")
        print(f"\nPara iniciar: python -m therapsid start")
        
        return 0
    
    async def start(self, args):
        """Inicia el nodo Therapsid"""
        ensure_directories()
        config = NodeConfig.load()
        
        if not config.node_id:
            print("❌ Nodo no inicializado. Ejecuta: python -m therapsid init")
            return 1
        
        print(f"🦊 [Therapsid] Iniciando nodo {config.node_id}...")
        print(f"   Nombre: {config.node_name}")
        print(f"   Región: {config.region}")
        print(f"   Tipo: {config.account_type}")
        
        # Inicializar gossip
        self.gossip = GossipProtocol(config)
        await self.gossip.start()
        
        # Inicializar Sinapsid (subproceso local)
        self.sinapsid = SinapsidAdapter(config)
        self.sinapsid.setup_local_database()
        if config.sinapsid_enabled:
            sinapsid_ok = self.sinapsid.start()
            if sinapsid_ok:
                print(f"   Sinapsid: {self.sinapsid.url}")
        
        # Inicializar transporte HTTP
        self.transport = HTTPTransport(self.gossip, config.web_port)
        await self.transport.start()
        
        print(f"\n✅ Nodo activo")
        print(f"   Gossip P2P: ws://0.0.0.0:{config.p2p_port}")
        print(f"   HTTP API: http://0.0.0.0:{config.web_port}")
        if self.sinapsid and self.sinapsid.running:
            print(f"   Sinapsid Local: {self.sinapsid.url}")
        print(f"\n   Presiona Ctrl+C para detener")
        
        # Mantener vivo
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo nodo...")
            await self.stop(args)
        
        return 0
    
    async def stop(self, args):
        """Detiene el nodo"""
        if self.sinapsid:
            self.sinapsid.stop()
        if self.gossip:
            await self.gossip.stop()
        if self.transport:
            await self.transport.stop()
        print("🦊 [Therapsid] Nodo detenido")
        return 0
    
    async def status(self, args):
        """Muestra el estado del nodo"""
        import aiohttp
        
        config = NodeConfig.load()
        if not config.node_id:
            print("❌ Nodo no inicializado")
            return 1
        
        print(f"🦊 [Therapsid] Estado del nodo {config.node_id}")
        print(f"   Nombre: {config.node_name}")
        print(f"   Región: {config.region}")
        print(f"   Tipo: {config.account_type}")
        
        # Intentar conectar al HTTP API local
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:{config.web_port}/status", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"\n   Status: 🟢 ONLINE")
                        print(f"   Peers conectados: {data.get('peers_count', 0)}")
                    else:
                        print(f"\n   Status: 🔴 ERROR ({resp.status})")
        except Exception:
            print(f"\n   Status: ⚪ NO INICIADO (o API no responde)")
        
        # Estado de Sinapsid
        if self.sinapsid:
            sinapsid_stats = self.sinapsid.get_stats()
            print(f"\n   Sinapsid: {sinapsid_stats.get('status', 'unknown')}")
            if sinapsid_stats.get('patients_count'):
                print(f"   Pacientes locales: {sinapsid_stats['patients_count']}")
            if sinapsid_stats.get('evolutions_count'):
                print(f"   Evoluciones locales: {sinapsid_stats['evolutions_count']}")
        
        return 0
    
    async def recovery(self, args):
        """Comandos de recuperación post-catástrofe"""
        print("🚨 [Therapsid Recovery]")
        
        config = NodeConfig.load()
        
        if not config.node_id:
            print("❌ Nodo no inicializado")
            return 1
        
        # Crear bridge
        bridge = SinapsidBridge(
            node_id=config.node_id,
            account=getattr(args, 'account', ''),
            governance_mode=GovernanceMode.DEV if args.dev else GovernanceMode.POP
        )
        
        recovery = RecoveryManager(bridge)
        
        if args.recovery_command == "check":
            # Verificar salud del coordenador
            result = recovery.check_coordinator_health()
            print(f"\n   Estado del coordenador:")
            print(f"   Status: {result['status']}")
            if 'coordinator_id' in result:
                print(f"   ID: {result['coordinator_id']}")
            if 'seconds_ago' in result:
                print(f"   Último contacto: hace {int(result['seconds_ago'])}s")
            print(f"   Acción: {result['action']}")
        
        elif args.recovery_command == "elect":
            # Iniciar elección de nuevo coordenador
            print("   Iniciando elección...")
            result = recovery.initiate_election()
            if result.get('success'):
                print(f"   ✅ Nuevo coordenador: {result.get('new_coordinator')}")
                print(f"   Modo: {result.get('mode')}")
                print(f"   Peso/Pacientes: {result.get('weight', 'N/A')}")
            else:
                print(f"   ❌ Error: {result.get('error')}")
        
        elif args.recovery_command == "rebuild":
            # Reconstruir desde peers
            print("   Reconstruyendo base de datos...")
            # TODO: Implementar selección de peers
            result = recovery.rebuild_database(args.sources.split(","))
            print(f"   Resultado: {result}")
        
        elif args.recovery_command == "verify":
            # Verificar integridad
            result = recovery.verify_database_integrity()
            print(f"\n   Integridad BD:")
            print(f"   ✅ OK: {result['integrity_ok']}")
            for check, value in result['checks'].items():
                print(f"   {check}: {value}")
        
        elif args.recovery_command == "status":
            result = recovery.get_recovery_status()
            print(f"\n   Estado de recuperación:")
            print(f"   Modo DEV: {result['dev_mode']}")
            print(f"   Nodos totales: {result['total_nodes']}")
            print(f"   Nodos online: {result['online_nodes']}")
            print(f"   Pacientes: {result['total_patients']}")
        
        return 0
    
    async def sync(self, args):
        """Sincronización manual con otros nodos"""
        print("🔄 [Therapsid Sync]")
        
        config = NodeConfig.load()
        if not config.node_id:
            print("❌ Nodo no inicializado")
            return 1
        
        # TODO: Implementar sync manual
        print("   Sincronización con peers...")
        print("   (Placeholder - requiere gossip activo)")
        
        return 0
    
    async def dev_mode(self, args):
        """Comandos de desarrollador (admin only)"""
        print("🔧 [Therapsid DEV MODE]")
        
        config = NodeConfig.load()
        if not config.node_id:
            print("❌ Nodo no inicializado")
            return 1
        
        # Verificar si es admin
        account = getattr(args, 'account', '') or input("Cuenta admin: ").strip()
        
        bridge = SinapsidBridge(
            node_id=config.node_id,
            account=account,
            governance_mode=GovernanceMode.DEV
        )
        
        if not bridge.dev_mode:
            print("❌ Cuenta no autorizada para modo DEV")
            return 1
        
        recovery = RecoveryManager(bridge)
        
        if args.dev_command == "export":
            filepath = args.file or f"sinapsid_backup_{int(time.time())}.json"
            result = recovery.dev_export_database(filepath)
            if result.get('success'):
                print(f"   ✅ Exportado: {result['filepath']}")
                print(f"   Pacientes: {result['patients']}")
                print(f"   Tamaño: {result['size_mb']:.2f} MB")
            else:
                print(f"   ❌ Error: {result.get('error')}")
        
        elif args.dev_command == "import":
            if not args.file:
                print("❌ Especifica archivo con -f")
                return 1
            result = recovery.dev_import_database(args.file, merge=args.merge)
            if result.get('success'):
                print(f"   ✅ Importado: {result['filepath']}")
                print(f"   Modo: {result['mode']}")
            else:
                print(f"   ❌ Error: {result.get('error')}")
        
        elif args.dev_command == "force-sync":
            targets = args.targets.split(",") if args.targets else []
            if not targets:
                print("❌ Especifica targets con -t nodo1,nodo2")
                return 1
            # TODO: Implementar force sync
            print(f"   Forzando sync a: {targets}")
        
        elif args.dev_command == "force-coordinator":
            new_coord = args.coordinator or input("Nuevo coordenador (node_id): ").strip()
            if new_coord:
                bridge.governance.dev_force_coordinator(new_coord)
                print(f"   ✅ Coordenador forzado: {new_coord}")
        
        elif args.dev_command == "bypass":
            action = args.action or input("Acción a bypass: ").strip()
            result = bridge.dev_force_propagate("", [])
            print(f"   Bypass: {result}")
        
        return 0

    def reset(self, args):
        """Resetea la configuración"""
        import shutil
        
        confirm = input("⚠️  ¿Estás seguro? Esto borrará toda la configuración [s/N]: ")
        if confirm.lower() == 's':
            therapsid_home = Path.home() / ".therapsid"
            if therapsid_home.exists():
                shutil.rmtree(therapsid_home)
                print("✅ Configuración eliminada")
            else:
                print("ℹ️  No había configuración")
        else:
            print("Cancelado")
        return 0


def main():
    """Punto de entrada principal"""
    parser = argparse.ArgumentParser(
        description="🦊 Therapsid - Nodo P2P para Sinapsid DMA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # init
    init_parser = subparsers.add_parser("init", help="Inicializar nodo nuevo")
    
    # start
    start_parser = subparsers.add_parser("start", help="Iniciar nodo")
    
    # stop
    stop_parser = subparsers.add_parser("stop", help="Detener nodo")
    
    # status
    status_parser = subparsers.add_parser("status", help="Ver estado del nodo")
    
    # recovery
    recovery_parser = subparsers.add_parser("recovery", help="Recuperación post-catástrofe")
    recovery_parser.add_argument("recovery_command", choices=["check", "elect", "rebuild", "verify", "status"],
                                 help="Comando de recuperación")
    recovery_parser.add_argument("--sources", "-s", help="Nodos fuente para rebuild (coma separados)")
    recovery_parser.add_argument("--dev", action="store_true", help="Modo DEV (bypass gobernanza)")
    recovery_parser.add_argument("--account", "-a", help="Cuenta admin para DEV mode")
    
    # sync
    sync_parser = subparsers.add_parser("sync", help="Sincronizar con peers")
    
    # dev-mode (admin only)
    dev_parser = subparsers.add_parser("dev", help="Modo desarrollador (admin only)")
    dev_parser.add_argument("dev_command", choices=["export", "import", "force-sync", "force-coordinator", "bypass"],
                           help="Comando DEV")
    dev_parser.add_argument("--file", "-f", help="Archivo para import/export")
    dev_parser.add_argument("--merge", "-m", action="store_true", help="Merge en lugar de reemplazar (import)")
    dev_parser.add_argument("--targets", "-t", help="Nodos target para force-sync (coma separados)")
    dev_parser.add_argument("--coordinator", "-c", help="Nuevo coordenador (force-coordinator)")
    dev_parser.add_argument("--account", "-a", required=True, help="Cuenta admin")
    dev_parser.add_argument("--action", help="Acción para bypass")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = TherapsidCLI()
    
    # Ejecutar comando
    if args.command == "init":
        return cli.init(args)
    elif args.command == "start":
        return asyncio.run(cli.start(args))
    elif args.command == "stop":
        return asyncio.run(cli.stop(args))
    elif args.command == "status":
        return asyncio.run(cli.status(args))
    elif args.command == "sync":
        return asyncio.run(cli.sync(args))
    elif args.command == "recovery":
        return asyncio.run(cli.recovery(args))
    elif args.command == "dev":
        return asyncio.run(cli.dev_mode(args))
    elif args.command == "reset":
        return cli.reset(args)
    elif args.command == "status":
        return asyncio.run(cli.status(args))
    elif args.command == "reset":
        return cli.reset(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
