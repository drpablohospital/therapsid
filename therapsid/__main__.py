#!/usr/bin/env python3
"""
Therapsid v2.0 - Nodo P2P Puro
Punto de entrada principal

Comandos:
    python -m therapsid init     # Configurar nodo nuevo
    python -m therapsid start      # Iniciar nodo y conectar a red
    python -m therapsid stop       # Detener nodo
    python -m therapsid status     # Ver estado
"""

import sys
import asyncio
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from therapsid.config import NodeConfig, ensure_directories
from therapsid.node import TherapsidNode


class TherapsidCLI:
    """Interfaz de linea de comandos para Therapsid"""
    
    def __init__(self):
        self.node = None
    
    def init(self, args):
        """Inicializar nuevo nodo"""
        print("🦊 [Therapsid] Inicializando nodo P2P...")
        
        ensure_directories()
        
        config = NodeConfig.load()
        
        if not config.node_id:
            import secrets
            config.node_id = 'therapsid-' + secrets.token_hex(8)
            config.save()
        
        print(f"✅ Nodo inicializado: {config.node_id}")
        print(f"📍 Region: {config.region}")
        print(f"🌐 Puerto HTTP: {config.web_port}")
        print("")
        print("Para iniciar: therapsid start")
        return 0
    
    def start(self, args):
        """Iniciar nodo y conectar a red Sinapsid"""
        config = NodeConfig.load()
        
        print("🦊 [Therapsid] Iniciando nodo P2P...")
        print(f"   Node ID: {config.node_id}")
        print(f"   Region: {config.region}")
        print(f"   Admin: http://100.127.123.55:5002")
        print("")
        
        self.node = TherapsidNode(config)
        
        try:
            asyncio.run(self.node.start())
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo...")
            asyncio.run(self.node.stop())
        
        return 0
    
    def stop(self, args):
        """Detener nodo"""
        print("🛑 [Therapsid] Deteniendo nodo...")
        # Enviar señal al proceso
        import os
        import signal
        
        # Buscar proceso
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'therapsid start'], 
                              capture_output=True, text=True)
        
        if result.stdout:
            for pid in result.stdout.strip().split('\n'):
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"   Proceso {pid} detenido")
                except:
                    pass
            print("✅ Nodo detenido")
        else:
            print("ℹ️  No estaba corriendo")
        
        return 0
    
    def status(self, args):
        """Ver estado del nodo"""
        import urllib.request
        
        try:
            req = urllib.request.Request('http://localhost:8767/api/v1/health')
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                print("✅ Therapsid activo")
                print(f"   Version: {data.get('version', 'N/A')}")
                print(f"   Node ID: {data.get('node_id', 'N/A')}")
                print(f"   Uptime: {data.get('uptime', 0):.0f}s")
                print("")
                print("   Dashboard: http://localhost:8767/dashboard")
                print("   Admin:     http://100.127.123.55:5002")
        except Exception as e:
            print("❌ Therapsid detenido")
            print(f"   Error: {e}")
        
        return 0
    
    def resources(self, args):
        """Ver recursos del nodo"""
        import urllib.request
        
        try:
            req = urllib.request.Request('http://localhost:8767/api/v1/node/resources')
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                print("📊 Recursos del Nodo")
                print("=" * 30)
                print(f"CPU: {data.get('cpu_percent', 0):.1f}%")
                print(f"RAM: {data.get('ram_used_mb', 0)} / {data.get('ram_total_mb', 0)} MB")
                print(f"Disco: {data.get('disk_used_gb', 0)} / {data.get('disk_total_gb', 0)} GB")
                print(f"Red RX: {data.get('network_rx_mb', 0)} MB")
                print(f"Red TX: {data.get('network_tx_mb', 0)} MB")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        return 0


def main():
    """Punto de entrada principal"""
    parser = argparse.ArgumentParser(
        description='Therapsid v2.0 - Nodo P2P Red Federada LATAM'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos')
    
    # init
    init_parser = subparsers.add_parser('init', help='Configurar nodo nuevo')
    
    # start
    start_parser = subparsers.add_parser('start', help='Iniciar nodo')
    
    # stop
    stop_parser = subparsers.add_parser('stop', help='Detener nodo')
    
    # status
    status_parser = subparsers.add_parser('status', help='Ver estado')
    
    # resources
    resources_parser = subparsers.add_parser('resources', help='Ver recursos')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = TherapsidCLI()
    handler = getattr(cli, args.command, None)
    
    if handler:
        return handler(args)
    else:
        print(f"Comando desconocido: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
