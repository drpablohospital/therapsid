"""
🦊 Therapsid - Nodo P2P para Sinapsid DMA

Therapsid es el ancestro común de Sinapsid. Mientras Sinapsid es la aplicación
web de expediente clínico, Therapsid es el nodo descentralizado que:

1. Corre Sinapsid localmente (modo standalone/offline)
2. Se conecta a una red P2P de pares médicos
3. Presta recursos (almacenamiento, computo, ancho de banda)
4. Sincroniza datos sin exponer información sensible
5. Mantiene Sinapsid vivo incluso si los servidores centrales caen

Uso:
    python -m therapsid init    # Primera configuración
    python -m therapsid start   # Iniciar el nodo
    python -m therapsid status  # Ver estado

Documentación: https://github.com/sinapsid/therapsid
"""

__version__ = "0.1.0"
__author__ = "Asociación Civil Sinapsid"
__license__ = "AGPL-3.0"

from .config import NodeConfig, ensure_directories
from .crypto import LocalCrypto, SensitiveDataFilter, generate_node_id
from .network.gossip import GossipProtocol
from .sinapsid_adapter import SinapsidAdapter
from .sync import P2PSyncManager, DeltaSync

__all__ = [
    "NodeConfig",
    "ensure_directories",
    "LocalCrypto",
    "SensitiveDataFilter",
    "generate_node_id",
    "GossipProtocol",
    "SinapsidAdapter",
    "P2PSyncManager",
    "DeltaSync",
]
