"""
Therapsid - Adaptador de Sinapsid
Integra Sinapsid DMA como subproceso dentro de Therapsid
"""

import os
import sys
import asyncio
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
import json
import requests

from .config import NodeConfig, THERAPSID_HOME, DATA_DIR


class SinapsidAdapter:
    """
    Adaptador que corre Sinapsid como subproceso dentro de Therapsid.
    
    Sinapsid corre localmente en el nodo Therapsid, usando:
    - SQLite local (en vez de PostgreSQL remoto)
    - Puerto configurable (default: 8766)
    - Modo standalone (funciona sin internet)
    
    Cuando hay conectividad P2P, Therapsid sincroniza datos con la red.
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.url = f"http://127.0.0.1:{config.sinapsid_port}"
        self.local_db = DATA_DIR / "sinapsid_local.db"
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
    
    def setup_local_database(self):
        """
        Configura la base de datos local SQLite para Sinapsid.
        Crea las tablas necesarias si no existen.
        """
        import sqlite3
        
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        # Tabla de pacientes (simplificada para modo standalone)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de evoluciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                data TEXT,  -- JSON con datos cifrados/anónimos
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        # Tabla de usuarios (local)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT DEFAULT 'medico',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ [Therapsid] Base de datos local configurada: {self.local_db}")
    
    def start(self) -> bool:
        """
        Inicia Sinapsid como subproceso.
        
        Returns:
            True si se inició correctamente
        """
        if self.running:
            print("⚠️  Sinapsid ya está corriendo")
            return True
        
        # Verificar que existe el código de Sinapsid
        sinapsid_path = self._find_sinapsid_code()
        if not sinapsid_path:
            print("❌ [Therapsid] No se encontró el código de Sinapsid")
            print("   Se usará modo demo/placeholder")
            return self._start_placeholder()
        
        # Configurar variables de entorno
        env = os.environ.copy()
        env["SINAPSID_DB_URL"] = f"sqlite:///{self.local_db}"
        env["SINAPSID_PORT"] = str(self.config.sinapsid_port)
        env["SINAPSID_MODE"] = "therapsid"
        
        try:
            # Iniciar Sinapsid como subproceso
            self.process = subprocess.Popen(
                [sys.executable, str(sinapsid_path / "app.py")],
                cwd=str(sinapsid_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            self.running = True
            print(f"✅ [Therapsid] Sinapsid iniciado en {self.url}")
            
            # Iniciar monitor de health
            self._start_monitor()
            
            return True
            
        except Exception as e:
            print(f"❌ [Therapsid] Error iniciando Sinapsid: {e}")
            return self._start_placeholder()
    
    def stop(self):
        """Detiene Sinapsid"""
        self._stop_monitor.set()
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        
        self.running = False
        print("🛑 [Therapsid] Sinapsid detenido")
    
    def is_healthy(self) -> bool:
        """Verifica si Sinapsid responde"""
        try:
            response = requests.get(f"{self.url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de Sinapsid local"""
        if not self.running:
            return {"status": "stopped"}
        
        try:
            response = requests.get(f"{self.url}/api/stats", timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {
            "status": "running" if self.is_healthy() else "unhealthy",
            "patients_count": 0,
            "evolutions_count": 0,
        }
    
    def _find_sinapsid_code(self) -> Optional[Path]:
        """
        Busca el código de Sinapsid en ubicaciones conocidas.
        Orden de búsqueda:
        1. Ruta de instalación del .deb (/opt/therapsid/sinapsid)
        2. Dentro del paquete therapsid
        3. En directorios conocidos del sistema
        """
        # 1. Ruta de instalación del .deb (prioridad máxima)
        deb_path = Path("/opt/therapsid/sinapsid")
        if deb_path.exists() and (deb_path / "app.py").exists():
            print(f"[Therapsid] Sinapsid encontrado en: {deb_path}")
            return deb_path
        
        # 2. Buscar en el paquete therapsid
        try:
            import therapsid
            therapsid_dir = Path(therapsid.__file__).parent
            
            # Buscar al mismo nivel (hermano)
            sibling = therapsid_dir.parent / "sinapsid"
            if sibling.exists() and (sibling / "app.py").exists():
                print(f"[Therapsid] Sinapsid encontrado en: {sibling}")
                return sibling
            
            # Dentro del paquete (legacy)
            bundled = therapsid_dir / "sinapsid"
            if bundled.exists() and (bundled / "app.py").exists():
                print(f"[Therapsid] Sinapsid encontrado en: {bundled}")
                return bundled
        except ImportError:
            pass
        
        # 3. Buscar en directorios comunes
        search_paths = [
            Path.home() / ".openclaw" / "workspace" / "sinapsid-working" / "current",
            Path.home() / ".openclaw" / "workspace" / "sinapsid-dma-auth",
            Path("/opt/sinapsid"),
            Path("/usr/local/sinapsid"),
        ]
        
        for path in search_paths:
            if path.exists() and (path / "app.py").exists():
                print(f"[Therapsid] Sinapsid encontrado en: {path}")
                return path
        
        print("[Therapsid] No se encontró Sinapsid en ninguna ubicación conocida")
        return None
    
    def _start_placeholder(self) -> bool:
        """
        Inicia un servidor placeholder cuando Sinapsid no está disponible.
        Muestra una página informativa con instrucciones.
        """
        from flask import Flask, jsonify, render_template_string
        
        app = Flask(__name__)
        
        @app.route("/")
        def home():
            return render_template_string(PLACEHOLDER_HTML)
        
        @app.route("/health")
        def health():
            return jsonify({"status": "placeholder"})
        
        @app.route("/api/stats")
        def stats():
            return jsonify({
                "status": "placeholder",
                "patients_count": 0,
                "evolutions_count": 0,
                "message": "Sinapsid no está instalado. Ejecuta: therapsid install-sinapsid"
            })
        
        # Iniciar en thread separado
        def run_flask():
            app.run(host="127.0.0.1", port=self.config.sinapsid_port, debug=False)
        
        thread = threading.Thread(target=run_flask, daemon=True)
        thread.start()
        
        self.running = True
        print(f"⚠️  [Therapsid] Sinapsid en modo placeholder: {self.url}")
        print("    Instala Sinapsid para funcionalidad completa")
        
        return True
    
    def _start_monitor(self):
        """Inicia el monitor de salud de Sinapsid"""
        def monitor():
            while not self._stop_monitor.is_set():
                if self.process and self.process.poll() is not None:
                    # Sinapsid murió, intentar reiniciar
                    print("⚠️  [Therapsid] Sinapsid se detuvo inesperadamente")
                    self.running = False
                    time.sleep(5)
                    print("🔄 [Therapsid] Reiniciando Sinapsid...")
                    self.start()
                time.sleep(10)
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()


# HTML placeholder cuando Sinapsid no está instalado
PLACEHOLDER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sinapsid - Modo Standalone</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
            max-width: 600px;
        }
        .logo {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        h1 {
            color: #4ade80;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .tagline {
            color: #ff6b35;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        .status {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        .status h2 {
            color: #4ade80;
            margin-top: 0;
        }
        .status p {
            color: #aaa;
            line-height: 1.6;
        }
        .code {
            background: #0a0a0a;
            border: 1px solid #4ade80;
            border-radius: 6px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            color: #4ade80;
            margin: 1rem 0;
            text-align: left;
            overflow-x: auto;
        }
        .cta {
            display: inline-block;
            background: linear-gradient(90deg, #ff6b35, #ff8c5a);
            color: white;
            text-decoration: none;
            padding: 0.8rem 2rem;
            border-radius: 8px;
            font-weight: bold;
            margin-top: 1rem;
        }
        .cta:hover {
            background: linear-gradient(90deg, #ff8c5a, #ff6b35);
        }
        .footer {
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #666;
        }
        .footer a {
            color: #4ade80;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🦊</div>
        <h1>Therapsid Node</h1>
        <div class="tagline">Nodo P2P para Sinapsid DMA</div>
        
        <div class="status">
            <h2>⚠️ Sinapsid no está instalado</h2>
            <p>
                Este nodo Therapsid está funcionando correctamente, pero Sinapsid 
                (la aplicación de expediente clínico) no está disponible en este sistema.
            </p>
            <p>
                Para usar Sinapsid localmente, instálalo con:
            </p>
            <div class="code">
therapsid install-sinapsid
            </div>
            <p>
                O descarga el código desde GitHub:
            </p>
            <div class="code">
git clone https://github.com/sinapsid/core.git
therapsid link-sinapsid ./core
            </div>
        </div>
        
        <div class="status">
            <h2>ℹ️ Información</h2>
            <p>
                <strong>Therapsid</strong> corre correctamente y está conectado 
                a la red P2P. Puedes ver el estado del nodo en el dashboard:
            </p>
            <a href="/dashboard" class="cta">Ver Dashboard</a>
        </div>
        
        <div class="footer">
            <p>Therapsid v0.1.0 | AGPL-3.0</p>
            <p><a href="https://github.com/sinapsid/therapsid">GitHub</a> | 
               <a href="https://med.dogma.tools">Demo</a> | 
               <a href="mailto:contacto@sinapsid.org">Contacto</a></p>
        </div>
    </div>
</body>
</html>
"""
