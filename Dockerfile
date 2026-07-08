FROM python:3.11-slim

LABEL maintainer="Asociación Civil Sinapsid <contacto@sinapsid.org>"
LABEL description="🦊 Therapsid - Nodo P2P para Sinapsid DMA"

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . /app/

# Instalar Therapsid
RUN pip install --no-cache-dir -e .

# Crear directorios necesarios
RUN mkdir -p /root/.therapsid/{data,config,logs,.keys}

# Exponer puertos
EXPOSE 8765 8767

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8767/health')" || exit 1

# Comando por defecto: inicializar si es necesario, luego iniciar
CMD ["sh", "-c", "if [ ! -f /root/.therapsid/config/config.json ]; then python -m therapsid init --non-interactive; fi; python -m therapsid start"]
