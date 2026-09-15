"""
Utilidades auxiliares para Canvas Student MCP.
Incluye limpiador de HTML a Markdown para instrucciones de tareas y anuncios,
formateo de fechas y manejo de respuestas limpias para asistentes IA.
"""

import re
import html
from datetime import datetime
from typing import Optional, Any


def clean_html(raw_html: Optional[str]) -> str:
    """
    Convierte contenido HTML devuelto por Canvas (descripciones de tareas,
    anuncios, páginas) en texto legible en formato Markdown, optimizado
    para el consumo de tokens de asistentes de Inteligencia Artificial.
    """
    if not raw_html or not isinstance(raw_html, str):
        return "Sin descripción o contenido disponible."

    text = raw_html

    # Normalizar saltos de línea
    text = re.sub(r"\r\n|\r", "\n", text)

    # Reemplazar encabezados
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h[4-6][^>]*>(.*?)</h[4-6]>", r"\n#### \1\n", text, flags=re.IGNORECASE | re.DOTALL)

    # Reemplazar enlaces <a href="url">texto</a>
    text = re.sub(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Negritas y cursivas
    text = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.IGNORECASE | re.DOTALL)

    # Elementos de lista
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"• \1\n", text, flags=re.IGNORECASE | re.DOTALL)

    # Saltos de línea y párrafos
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?div[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Eliminar cualquier otra etiqueta HTML restante
    text = re.sub(r"<[^>]+>", "", text)

    # Decodificar entidades HTML (&nbsp;, &amp;, &lt;, etc.)
    text = html.unescape(text)

    # Limpiar espacios repetidos y líneas vacías excesivas
    lines = [line.strip() for line in text.split("\n")]
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                cleaned_lines.append("")
                prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    result = "\n".join(cleaned_lines).strip()
    return result if result else "Sin contenido textual disponible."


def format_date(iso_str: Optional[str]) -> str:
    """
    Formatea una fecha ISO 8601 (típica de Canvas) a una representación
    legible y comprensible en español/UTC.
    """
    if not iso_str:
        return "Sin fecha programada"
    try:
        # Reemplazar Z por +00:00 para datetime.fromisoformat
        normalized = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(iso_str)


def truncate_text(text: str, max_chars: int = 1500) -> str:
    """
    Trunca texto extenso para evitar saturar la ventana de contexto del LLM.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [Texto truncado, longitud total: {len(text)} caracteres]"
