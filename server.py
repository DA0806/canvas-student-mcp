"""
server.py — Entrypoint para MCPHosting, Docker y despliegues cloud.
Exporta `mcp`, `server` y `app`, y arranca el servidor si se ejecuta como proceso.
"""

import os
import sys
import socket
from main import mcp

# Re-exportar server y app (ASGI) con todas las herramientas registradas
server = mcp
app = mcp.http_app()


def _is_port_in_use(host: str, port: int) -> bool:
    """Comprueba si un socket ya está escuchando en host:port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def _print_debug_info():
    """Imprime procesos activos para diagnosticar el entorno cloud."""
    try:
        import subprocess

        ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=2)
        if ps.stdout:
            print("--- [MCP DEBUG] Procesos del contenedor ---", file=sys.stderr, flush=True)
            for line in ps.stdout.strip().splitlines()[:15]:
                print(f"  {line}", file=sys.stderr, flush=True)
    except Exception:
        pass


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    requested_transport = os.getenv("MCP_TRANSPORT")

    port_busy = _is_port_in_use(host, port)

    # Si el puerto asignado (ej. 3000) ya está ocupado por el gateway HTTP/SSE de MCPHosting,
    # o si se solicitó explícitamente stdio, ejecutamos en modo STDIO para conectarnos al gateway del host.
    if port_busy:
        print(
            f"⚡ Puerto {host}:{port} ocupado por el gateway de MCPHosting. Conectando Canvas Student MCP en modo STDIO...",
            file=sys.stderr,
            flush=True,
        )
        _print_debug_info()
        mcp.run(transport="stdio")
    elif requested_transport == "stdio":
        print("🚀 Canvas Student MCP iniciando en modo STDIO...", file=sys.stderr, flush=True)
        mcp.run(transport="stdio")
    else:
        target_transport = requested_transport or "http"
        print(
            f"🚀 Canvas Student MCP iniciando en http://{host}:{port} (transporte: {target_transport})...",
            file=sys.stderr,
            flush=True,
        )
        mcp.run(transport=target_transport, host=host, port=port)


