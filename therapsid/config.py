"""
Therapsid - Nodo P2P para Sinapsid DMA
Core de configuración y constantes
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import json

# Directorios base
THERAPSID_HOME = Path.home() / ".therapsid"
DATA_DIR = THERAPSID_HOME / "data"
CONFIG_DIR = THERAPSID_HOME / "config"
LOGS_DIR = THERAPSID_HOME / "logs"
KEYS_DIR = THERAPSID_HOME / ".keys"

# Archivos
CONFIG_FILE = CONFIG_DIR / "config.json"
PEERS_FILE = CONFIG_DIR / "peers.json"
SALT_FILE = KEYS_DIR / ".salt"
MASTER_KEY_FILE = KEYS_DIR / ".master"
DB_FILE = DATA_DIR / "therapsid.db"

# Red P2P defaults
DEFAULT_P2P_PORT = 8765
DEFAULT_SINAPSID_PORT = 8766
DEFAULT_WEB_PORT = 8767
GOSSIP_INTERVAL = 60  # segundos
MAX_PEERS = 10
BOOTSTRAP_PEERS = [
    # Se llenará dinámicamente o desde config
]

# Sinapsid
SINAPSID_REPO = "https://github.com/sinapsid/core"
SINAPSID_VERSION = "1.0.0"

@dataclass
class NodeConfig:
    """Configuración de un nodo Therapsid"""
    node_id: str = ""
    node_name: str = "Therapsid Node"
    account_type: str = "individual"  # hospital, individual, admin
    region: str = "UNKNOWN"
    
    # Red
    p2p_port: int = DEFAULT_P2P_PORT
    sinapsid_port: int = DEFAULT_SINAPSID_PORT
    web_port: int = DEFAULT_WEB_PORT
    bootstrap_peers: List[str] = field(default_factory=list)
    
    # Recursos
    max_storage_mb: int = 1024  # 1GB default
    max_cpu_percent: int = 50
    max_bandwidth_mbps: int = 10
    
    # Sinapsid
    sinapsid_enabled: bool = True
    sinapsid_db_url: str = "sqlite:///therapsid.db"
    
    # Federación
    federation_enabled: bool = False
    flower_server: str = ""
    
    def to_dict(self):
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "account_type": self.account_type,
            "region": self.region,
            "p2p_port": self.p2p_port,
            "sinapsid_port": self.sinapsid_port,
            "web_port": self.web_port,
            "bootstrap_peers": self.bootstrap_peers,
            "max_storage_mb": self.max_storage_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_bandwidth_mbps": self.max_bandwidth_mbps,
            "sinapsid_enabled": self.sinapsid_enabled,
            "sinapsid_db_url": self.sinapsid_db_url,
            "federation_enabled": self.federation_enabled,
            "flower_server": self.flower_server,
        }
    
    @classmethod
    def from_dict(cls, d):
        return cls(**d)
    
    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return cls.from_dict(json.load(f))
        return cls()


def ensure_directories():
    """Crea todos los directorios necesarios"""
    for d in [THERAPSID_HOME, DATA_DIR, CONFIG_DIR, LOGS_DIR, KEYS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    # Permisos restrictivos para keys
    os.chmod(KEYS_DIR, 0o700)
