#!/usr/bin/env python3
"""
Therapsid - Script de Instalación Rápida
pip install -e . && python install.py
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def install_system_dependencies():
    """Instala dependencias del sistema si es necesario"""
    print("🔧 [Therapsid] Verificando dependencias del sistema...")
    
    # Verificar Python >= 3.9
    if sys.version_info < (3, 9):
        print("❌ Python >= 3.9 requerido")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")


def create_systemd_service(node_name: str, working_dir: str):
    """Crea un servicio systemd para Therapsid"""
    service_content = f"""[Unit]
Description=Therapsid P2P Node - {node_name}
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'therapsid')}
WorkingDirectory={working_dir}
Environment=PYTHONPATH={working_dir}
Environment=THERAPSID_HOME={Path.home()}/.therapsid
ExecStart={sys.executable} -m therapsid start
ExecStop=/bin/kill -SIGTERM $MAINPID
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path.home() / ".config/systemd/user/therapsid.service"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(service_path, "w") as f:
        f.write(service_content)
    
    print(f"✅ Servicio systemd creado: {service_path}")
    print("   Para activar:")
    print(f"   systemctl --user daemon-reload")
    print(f"   systemctl --user enable therapsid.service")
    print(f"   systemctl --user start therapsid.service")


def main():
    parser = argparse.ArgumentParser(description="Instalador de Therapsid")
    parser.add_argument("--systemd", action="store_true", help="Crear servicio systemd")
    parser.add_argument("--node-name", default="Therapsid Node", help="Nombre del nodo")
    args = parser.parse_args()
    
    print("🦊 [Therapsid] Instalador")
    print("=" * 50)
    
    # 1. Verificar dependencias
    install_system_dependencies()
    
    # 2. Instalar paquete Python
    print("\n📦 Instalando paquete...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Error instalando: {result.stderr}")
        sys.exit(1)
    print("✅ Paquete instalado")
    
    # 3. Crear directorios
    print("\n📁 Creando directorios...")
    from therapsid.config import ensure_directories
    ensure_directories()
    print("✅ Directorios creados")
    
    # 4. Crear servicio systemd (opcional)
    if args.systemd:
        print("\n⚙️  Creando servicio systemd...")
        create_systemd_service(args.node_name, os.getcwd())
    
    # 5. Instrucciones finales
    print("\n" + "=" * 50)
    print("✅ Instalación completada!")
    print("\nPróximos pasos:")
    print("  1. Inicializar nodo:  python -m therapsid init")
    print("  2. Iniciar nodo:      python -m therapsid start")
    print("  3. Ver dashboard:     http://localhost:8767/dashboard")
    print("\nDocumentación: https://github.com/sinapsid/therapsid")


if __name__ == "__main__":
    main()
