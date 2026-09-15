"""
server.py — Entrypoint para MCPHosting, Docker y despliegues cloud.
Exporta `mcp`, `server` y `app`, y arranca el servidor si se ejecuta como proceso.
"""

import os
import sys
from main import mcp

# Re-exportar server y app (ASGI) con todas las herramientas registradas
server = mcp
app = mcp.http_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    transport = os.getenv("MCP_TRANSPORT", "http")
    print(f"🚀 Canvas Student MCP iniciando en http://{host}:{port} (transporte: {transport})...", file=sys.stderr, flush=True)
    mcp.run(transport=transport, host=host, port=port)

