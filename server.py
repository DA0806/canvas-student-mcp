"""
server.py — Re-exporta el objeto `mcp` de main.py.
MCPHosting busca automáticamente un objeto llamado `mcp`, `server` o `app`
en este archivo. No debe iniciarse ningún proceso adicional aquí.
"""

from main import mcp  # noqa: F401  – MCPHosting usa este objeto directamente
