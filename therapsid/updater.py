"""
Auto-Updater - Actualizador Automático
=======================================
Detecta nuevas versiones en GitHub y descarga actualizaciones.

Uso:
- Al iniciar Therapsid, chequea si hay nueva versión
- Si hay, muestra notificación en dashboard
- Botón "Actualizar" descarga e instala
"""

import os
import sys
import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional

# Configuración
GITHUB_REPO = "drpablohospital/therapsid"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "0.1.3"

class AutoUpdater:
    """Gestiona actualizaciones automáticas desde GitHub"""
    
    def __init__(self):
        self.latest_version = None
        self.download_url = None
        self.changelog = None
        self.has_update = False
    
    def check_for_updates(self) -> Dict:
        """
        Chequea si hay nueva versión en GitHub.
        Retorna dict con estado de actualización.
        """
        try:
            # Consultar GitHub API
            req = urllib.request.Request(
                GITHUB_API,
                headers={"User-Agent": "Therapsid-Updater"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            self.latest_version = data.get("tag_name", "v0.0.0").lstrip("v")
            self.download_url = data.get("html_url", "")
            self.changelog = data.get("body", "No hay notas de versión")
            
            # Comparar versiones
            if self._version_compare(self.latest_version, CURRENT_VERSION) > 0:
                self.has_update = True
                return {
                    "has_update": True,
                    "current_version": CURRENT_VERSION,
                    "latest_version": self.latest_version,
                    "download_url": self.download_url,
                    "changelog": self.changelog[:500] + "..." if len(self.changelog) > 500 else self.changelog
                }
            else:
                return {
                    "has_update": False,
                    "current_version": CURRENT_VERSION,
                    "latest_version": self.latest_version
                }
                
        except Exception as e:
            return {
                "has_update": False,
                "error": str(e),
                "current_version": CURRENT_VERSION
            }
    
    def _version_compare(self, v1: str, v2: str) -> int:
        """Compara versiones. Retorna >0 si v1 > v2"""
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        
        for i in range(max(len(parts1), len(parts2))):
            p1 = parts1[i] if i < len(parts1) else 0
            p2 = parts2[i] if i < len(parts2) else 0
            
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        
        return 0
    
    def download_update(self) -> Dict:
        """
        Descarga e instala la última versión.
        
        Pasos:
        1. Descargar .deb desde GitHub releases
        2. Instalar con dpkg
        3. Reiniciar servicio
        """
        try:
            # Buscar asset .deb en el release
            req = urllib.request.Request(
                GITHUB_API,
                headers={"User-Agent": "Therapsid-Updater"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            # Buscar asset .deb
            deb_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".deb"):
                    deb_url = asset["browser_download_url"]
                    break
            
            if not deb_url:
                return {"success": False, "error": "No se encontró .deb en el release"}
            
            # Descargar
            deb_path = "/tmp/therapsid-update.deb"
            print(f"📥 Descargando actualización desde {deb_url}...")
            
            urllib.request.urlretrieve(deb_url, deb_path)
            
            # Instalar (requiere sudo - el usuario debe autorizar)
            print("📦 Instalando...")
            return {
                "success": True,
                "message": "Descarga completa. Ejecuta: sudo dpkg -i /tmp/therapsid-update.deb",
                "deb_path": deb_path,
                "version": self.latest_version
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict:
        """Retorna estado del actualizador"""
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": self.latest_version,
            "has_update": self.has_update,
            "github_repo": GITHUB_REPO
        }

# Singleton
_updater = None

def get_updater() -> AutoUpdater:
    """Retorna instancia singleton del updater"""
    global _updater
    if _updater is None:
        _updater = AutoUpdater()
    return _updater
