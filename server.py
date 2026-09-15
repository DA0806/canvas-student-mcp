"""
Entrypoint alternativo para servidores de hosting MCP (MCPHosting, Render, Railway, etc.).
Redirige directamente al servidor implementado en main.py.
"""

import os
from main import app, mcp

if __name__ == "__main__":
    cloud_port = os.getenv("PORT")
    transport = os.getenv("MCP_TRANSPORT") or os.getenv("FASTMCP_TRANSPORT")

    if cloud_port or (transport and transport in {"http", "sse", "streamable-http"}):
        target_transport = transport if transport in {"http", "sse", "streamable-http"} else "http"
        host = os.getenv("HOST", "0.0.0.0")
        port = int(cloud_port or os.getenv("FASTMCP_PORT", "8000"))
        print(f"🚀 Iniciando Canvas Student MCP desde server.py en modo {target_transport} ({host}:{port})...")
        mcp.run(transport=target_transport, host=host, port=port)
    else:
        mcp.run(transport="stdio")
