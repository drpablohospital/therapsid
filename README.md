# 🦊 Therapsid - Nodo P2P para SINAPSID

**Sistema descentralizado de intercambio de datos médicos para cuidados intensivos.**

Cada nodo es una **réplica completa** de Sinapsid. Si un nodo cae, la red lo reconstruye. Si xiu-HOME explota, cualquier nodo puede recuperar todo.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    SINAPSID SHARDED NETWORK                  │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  NODO A      │◄───►│  NODO B      │◄───►│  NODO C      │
│  (xiu-Asus)  │ P2P │  (Hospital)  │     │  (Tablet UCI)│
│              │Gossip│              │     │              │
│ ┌──────────┐ │     │ ┌──────────┐ │     │ ┌──────────┐ │
│ │Sinapsid  │◄┼────►│ │Sinapsid  │ │     │ │Sinapsid  │ │
│ │Completo  │ │     │ │Completo  │ │     │ │Completo  │ │
│ │(SQLite)  │ │     │ │(Postgre) │ │     │ │(SQLite)  │ │
│ └──────────┘ │     │ └──────────┘ │     │ └──────────┘ │
│              │     │              │     │              │
│ ┌──────────┐ │     │ ┌──────────┐ │     │ ┌──────────┐ │
│ │Therapsid │ │     │ │Therapsid │ │     │ │Therapsid │ │
│ │(P2P Node)│ │     │ │(P2P Node)│ │     │ │(P2P Node)│ │
│ └──────────┘ │     │ └──────────┘ │     │ └──────────┘ │
└──────────────┘     └──────────────┘     └──────────────┘
       ▲                    ▲                    ▲
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                    💥 KA-BOOM (xiu-HOME muere)
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
┌──────▼──────┐    ┌──────▼──────┐    ┌───────▼───────┐
│  NODO A     │◄──►│  NODO B     │◄──►│   NODO C      │
│  ASUME      │     │  ASUME      │     │   ASUME       │
│  LIDERAZGO  │     │  LIDERAZGO  │     │   LIDERAZGO  │
│  (PoP)      │     │  (PoP)      │     │   (PoP)       │
└─────────────┘     └─────────────┘     └───────────────┘
```

---

## 🛡️ Principios de Seguridad

| Principio | Implementación |
|-----------|---------------|
| **SOBERANÍA** | Cada nodo solo modifica sus propios pacientes |
| **INMUTABILIDAD** | Datos ajenos son solo lectura |
| **TRAZABILIDAD** | Audit trail criptográfico de todas las operaciones |
| **CONFIDENCIALIDAD** | Solo metadata agregada sale por la red |
| **CERO CORRUPCIÓN** | Bridge valida todo antes de tocar la DB |
| **RESILIENCIA** | Cada nodo tiene réplica completa; recuperación post-catástrofe |

---

## 📦 Instalación

### Ubuntu/Debian (.deb)

```bash
# Descargar
wget https://github.com/sinapsid/therapsid/releases/download/v0.1.1/therapsid_0.1.1_all.deb

# Instalar
sudo dpkg -i therapsid_0.1.1_all.deb
sudo apt-get install -f  # Si faltan dependencias

# Iniciar
sudo systemctl start therapsid

# Verificar
therapsid status
```

### Python (desarrollo)

```bash
git clone https://github.com/sinapsid/therapsid.git
cd therapsid
python3 -m venv venv
source venv/bin/activate
pip install -e .
python -m therapsid init
python -m therapsid start
```

---

## 🚀 Comandos

| Comando | Descripción |
|---------|-------------|
| `therapsid init` | Configurar nodo nuevo |
| `therapsid start` | Iniciar nodo |
| `therapsid stop` | Detener nodo |
| `therapsid status` | Estado del nodo |
| `therapsid sync` | Sincronizar con peers |
| `therapsid recovery check` | Verificar coordenador |
| `therapsid recovery elect` | Elegir nuevo coordenador |
| `therapsid recovery rebuild -s nodo1,nodo2` | Reconstruir BD |
| `therapsid recovery verify` | Verificar integridad |
| `therapsid dev export -a dr.pablo@gmail.com` | Exportar BD (admin) |
| `therapsid dev import -f backup.json -a dr.pablo@gmail.com` | Importar BD (admin) |
| `therapsid dev force-coordinator -c nodo123 -a dr.pablo@gmail.com` | Forzar coordenador |

---

## 🔐 Sistema de Consenso

### Modo Actual: Proof-of-Patients (PoP)

```
Peso del nodo = pacientes × uptime × reputación

Ejemplo:
- Hospital Central: 150 pacientes × 100h × 100% = 15,000 peso
- Clínica Norte: 80 pacientes × 50h × 90% = 3,600 peso
- UCI Móvil: 25 pacientes × 10h × 100% = 250 peso

Quórum = 50% del peso total
```

### Modo DEV (Admin)

El desarrollador principal (Dr. Pablo) puede:
- Bypass total de gobernanza
- Forzar sincronizaciones
- Designar coordenadores manualmente
- Exportar/importar bases de datos completas

### Futuro: Proof-of-Stake (PoS)

Cuando haya comunidad estable, migrar a tokens crypto:
- Staking para participar
- Recompensas por buen comportamiento
- Slashing por mal comportamiento

---

## 🔄 Flujo de Datos

### Enviar paciente a la red

```python
# 1. Crear paciente en Sinapsid local
bridge.create_patient(patient_data, account="dr.pablo", node_id="hospital-central")

# 2. Bridge anonimiza datos
anonymized = {
    "age_range": "60-69",
    "weight_category": "70-79kg",
    "sofa_total": 8,
    "saps3": 45,
    "outcome": "alive"
}

# 3. Registrar en Merkle DAG
merkle.add_patient(uuid, anonymized, owner="hospital-central")

# 4. Firmar y enviar por gossip
gossip.broadcast(sync_packet)
```

### Recibir paciente de la red

```python
# 1. Recibir paquete cifrado
packet = gossip.receive()

# 2. Bridge valida origen
if node.reputation < 50: reject()

# 3. Verificar integridad Merkle
verify(packet.merkle_hash)

# 4. Guardar en tabla federada (NO modifica pacientes locales)
db.insert("patients_federated", packet.data)

# 5. Registrar en audit
audit.append(operation="SYNC_IN", actor=packet.sender)
```

---

## 🏥 Sincronización con Sinapsid Real

**Actualmente:** Therapsid tiene placeholder en puerto 8766
**Próximamente:** Integración completa

Para conectar con tu instancia de Sinapsid (med.dogma.tools):

```python
# En therapsid/config.py
sinapsid_enabled = true
sinapsid_url = "http://localhost:5001"  # Tu instancia local
sinapsid_db = "postgresql://..."  # Conexión a tu BD PostgreSQL
```

---

## 🧪 Tests

```bash
cd therapsid
python -m pytest tests/ -v

# O ejecutar individual
python tests/test_therapsid.py
```

**Tests actuales:** 13/13 pasando

---

## 🌐 API REST

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/status` | GET | No | Estado del nodo |
| `/dashboard` | GET | No | Web UI |
| `/api/v1/node/info` | GET | No | Info del nodo |
| `/api/v1/auth/login` | POST | No | Login |
| `/api/v1/auth/logout` | POST | Sí | Logout |
| `/api/v1/data/send` | POST | Sí | Enviar datos a red |
| `/api/v1/data/receive` | GET | Sí | Recibir datos de red |
| `/api/v1/data/pending` | GET | Sí | Paquetes pendientes |
| `/api/v1/sinapsid/stats` | GET | Sí | Stats de Sinapsid local |

---

## 🎨 Dashboard

**URL:** http://localhost:8767/dashboard

**Tabs:**
- 📊 Visión General (estado del nodo, peers, recursos)
- 🌐 Red P2P (nodos conectados, coordenador)
- 🏥 Sinapsid Local (pacientes, evoluciones)
- 🔄 Sincronización (paquetes enviados/recibidos)
- 🛡️ Recuperación (estado post-catástrofe)

---

## 🔗 Repositorios

- **Sinapsid:** https://github.com/drpablohospital/sinapsid
- **Therapsid:** https://github.com/sinapsid/therapsid
- **Demo:** https://med.dogma.tools

---

## 👤 Autor

**Dr. Pablo Fernández** — contacto@sinapsid.org

**Licencia:** AGPL-3.0

---

*"Sinapsid nunca muere. Ni siquiera si xiu-HOME explota."*
