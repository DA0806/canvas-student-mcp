FROM python:3.12-slim

# Evitar escritura de .pyc y activar salida en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Puerto expuesto
EXPOSE 8000

# Verificación de salud del servicio (health check)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Iniciar servidor
CMD ["python", "main.py"]
