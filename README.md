# Canvas Student MCP

Servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) para consultar Canvas LMS desde un asistente compatible. La ruta recomendada es local, para una sola persona, por STDIO. El proceso usa la cuenta de Canvas configurada en el archivo `.env` del proyecto.

Esta documentación describe el estado del repositorio auditado el 2 de octubre de 2026. El proyecto no incluye un instalador, un paquete publicado, una imagen Docker, un lockfile ni una suite de pruebas.

## Índice

- [Requisitos y alcance](#requisitos-y-alcance)
- [Instalación local](#instalación-local)
- [Configurar Canvas](#configurar-canvas)
- [Iniciar el servidor por STDIO](#iniciar-el-servidor-por-stdio)
- [Conectar un cliente MCP](#conectar-un-cliente-mcp)
- [Primera comprobación segura](#primera-comprobación-segura)
- [Solucionar problemas](#solucionar-problemas)
- [Catálogo de herramientas](#catálogo-de-herramientas)
- [Límites actuales y seguridad](#límites-actuales-y-seguridad)
- [HTTP y despliegue remoto](#http-y-despliegue-remoto)
- [Accesibilidad e instalación futura](docs/accessibility-and-installation.md)
- [Fuentes](#fuentes)

## Requisitos y alcance

- Python 3.10 o posterior, que es el mínimo requerido por la versión actual de FastMCP.
- Una cuenta de Canvas y un token personal de acceso permitido por tu institución.
- Un cliente MCP que pueda iniciar un servidor local por STDIO.
- Windows, macOS y Linux son rutas documentadas por sus comandos equivalentes; no se ha validado aquí una matriz completa de sistemas o clientes.

Las dependencias directas están en [`requirements.txt`](requirements.txt): FastMCP, HTTPX, python-dotenv, Pydantic, Uvicorn y Starlette. La instalación local verificada usa Python 3.14.4 y FastMCP 4.0.10 dentro de `.venv`.

## Instalación local

### Obtener el código

Con Git:

```bash
git clone https://github.com/DA0806/canvas-student-mcp.git
cd canvas-student-mcp
```

Si no tienes Git, descarga el ZIP desde el repositorio al que tengas acceso, extráelo y abre una terminal en la carpeta que contiene `server.py`. No uses una ruta personal de ejemplo del equipo de otra persona.

### Crear el entorno e instalar dependencias

No hace falta activar el entorno virtual: usar el ejecutable de `.venv` evita que el cliente MCP dependa del `PATH` de la terminal.

En Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En macOS o Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Si `py -3` o `python3` no existe, instala [Python desde su sitio oficial](https://www.python.org/downloads/) y vuelve a ejecutar el comando. El servidor se ejecuta desde esta copia local; no tiene un paquete publicado para instalar con `pip` o `uvx`.

## Configurar Canvas

Copia la plantilla y edita el archivo local `.env`:

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

En macOS o Linux:

```bash
cp .env.example .env
```

Completa únicamente estos valores:

```env
CANVAS_BASE_URL=https://tu-institucion.instructure.com
CANVAS_API_TOKEN=pega_aqui_el_token_personal
```

`CANVAS_BASE_URL` debe ser el origen HTTPS que abre tu institución en el navegador. No agregues `/courses`, `/api/v1` ni una ruta de un curso. Si no se define, el cliente cae en `https://canvas.instructure.com`; confirma siempre que el origen sea el correcto antes de usar el token.

Para un uso personal o de prueba, Canvas permite crear el token desde **Cuenta → Configuración → Nuevo token de acceso**. La institución puede restringir esta opción, exigir expiración o revocar el token. Cópialo solo en `.env`; no lo pongas en comandos, capturas, mensajes, logs ni commits. El `.gitignore` debe mantener `.env` fuera del control de versiones.

El cliente carga primero las variables del entorno y luego el bloque `deployment.env` de `fastmcp.json` si existiera. En el archivo actual no hay credenciales allí. En HTTP también puede recibir el origen mediante `x-canvas-base-url`/`x-canvas-url` y el token mediante `Authorization: Bearer` o `x-canvas-token`; esa ruta no es la recomendada para uso local compartido.

## Iniciar el servidor por STDIO

Usa el comando explícito de FastMCP. Así el transporte queda fijado en STDIO y no depende del `__main__` de `server.py` ni de que el puerto 8000 esté libre.

En Windows PowerShell, desde la raíz del repositorio:

```powershell
$canvasMcpCommand = (Resolve-Path '.venv\Scripts\fastmcp.exe').Path
$canvasMcpServer = (Resolve-Path 'server.py').Path
& $canvasMcpCommand run $canvasMcpServer --transport stdio
```

En macOS o Linux:

```bash
.venv/bin/fastmcp run "$(pwd)/server.py" --transport stdio
```

El cliente puede ejecutar ese mismo comando cuando se conecte. No hace falta definir `MCP_TRANSPORT` si se usa `--transport stdio`. Como alternativa directa, el proceso acepta `MCP_TRANSPORT=stdio` con `python server.py`, pero la orden `fastmcp run ... --transport stdio` es la ruta principal documentada.

## Conectar un cliente MCP

### Codex CLI

La sintaxis local verificada es `codex mcp add NOMBRE -- COMANDO ARGUMENTOS`. En Windows PowerShell:

```powershell
$canvasMcpCommand = (Resolve-Path '.venv\Scripts\fastmcp.exe').Path
$canvasMcpServer = (Resolve-Path 'server.py').Path
codex mcp add canvas-student -- $canvasMcpCommand run $canvasMcpServer --transport stdio
```

El token permanece en `.env`; no lo añadas como argumento de `codex mcp add`.

### Clientes que acepten una configuración JSON STDIO

Adapta las rutas absolutas a tu equipo. Este ejemplo no incluye secretos:

```json
{
  "mcpServers": {
    "canvas-student": {
      "command": "C:/ruta/canvas-student-mcp/.venv/Scripts/fastmcp.exe",
      "args": [
        "run",
        "C:/ruta/canvas-student-mcp/server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

Otros clientes deben documentar explícitamente que soportan servidores locales STDIO. No se ha validado en este repositorio una integración de interfaz concreta con Claude Desktop, Cursor, Gemini, Cline, Roo Code o ChatGPT. ChatGPT requiere un transporte remoto y una configuración compatible con su producto; no asumas que puede abrir STDIO local desde una conversación de escritorio.

## Primera comprobación segura

Antes de pedir datos académicos:

1. Comprueba que el cliente descubre el servidor y las 29 herramientas durante el handshake.
2. Ejecuta `test_canvas_connection` solo cuando hayas confirmado el origen y el token. Esta llamada sí contacta Canvas y usa la cuenta configurada.
3. Después prueba `get_active_courses` y verifica que el resultado corresponde a tu cuenta.

El endpoint `/health`, si se expone por HTTP, solo confirma que el proceso está vivo. No comprueba la URL, el token ni el acceso a Canvas. Un fallo de `client.ping()` tampoco es un diagnóstico válido por sí mismo: el SDK actual puede responder `Method not found` a ese método.

## Solucionar problemas

| Problema | Siguiente acción |
| --- | --- |
| PowerShell no reconoce `py` | Ejecuta `python --version`. Si muestra Python 3.10 o posterior, usa `python -m venv .venv`; si no, instala Python y vuelve a abrir la terminal. |
| Falta el token | Confirma que `.env` está en la misma carpeta que `server.py` y contiene `CANVAS_API_TOKEN`. Reinicia la conexión del cliente tras editarlo. |
| Canvas devuelve 401 | Revisa el origen institucional y genera un token nuevo si el anterior expiró o fue revocado. |
| Canvas devuelve 403 | Comprueba el permiso del curso o recurso con tu institución; cambiar el token no concede permisos nuevos. |
| El cliente no descubre el servidor | Revisa las dos rutas absolutas y `--transport stdio`. Prueba el comando de arranque y consulta los errores del cliente sin compartir secretos. |
| El servidor parece esperar sin responder | En STDIO espera mensajes de un cliente MCP. No abre una página web ni expone `/health`; termina la prueba manual con `Ctrl+C` y configura el cliente. |

## Catálogo de herramientas

El código registra 29 herramientas MCP. Las cinco herramientas que escriben en Canvas están marcadas con **Escritura Canvas** y no tienen una confirmación obligatoria en el servidor; revisa cada contenido antes de invocarlas y usa las aprobaciones que ofrezca tu cliente.

### Credenciales y perfil

| Herramienta | Acción |
| --- | --- |
| `configure_canvas_credentials` | Cambia URL y token para todo el proceso; no aísla sesiones ni escribe en Canvas. |
| `test_canvas_connection` | Comprueba la conexión y devuelve el usuario de Canvas. |
| `get_student_profile` | Consulta el perfil del estudiante. |

### Cursos y calificaciones

| Herramienta | Acción |
| --- | --- |
| `get_active_courses` | Lista los cursos activos. |
| `get_course_details` | Consulta detalles y syllabus de un curso. |
| `get_student_grades` | Consulta calificaciones actuales y finales proyectadas. |

### Tareas y cuestionarios

| Herramienta | Acción |
| --- | --- |
| `get_course_assignments` | Lista tareas y fechas de entrega. |
| `get_assignment_details` | Lee instrucciones, puntos y rúbrica disponible. |
| `get_quizzes` | Lista cuestionarios. |
| `get_quiz_details` | Lee la configuración de un cuestionario. |

### Entregas y retroalimentación

| Herramienta | Acción |
| --- | --- |
| `get_assignment_submission` | Consulta una entrega y sus comentarios. |
| `submit_assignment_text` | **Escritura Canvas:** envía texto o código a una tarea. |
| `submit_assignment_url` | **Escritura Canvas:** envía una URL a una tarea. |
| `add_submission_comment` | **Escritura Canvas:** agrega un comentario a una entrega. |

### Agenda y pendientes

| Herramienta | Acción |
| --- | --- |
| `get_todo_items` | Consulta el panel To-Do. |
| `get_missing_submissions` | Busca entregas faltantes. |
| `get_planner_items` | Consulta elementos del planificador. |
| `get_calendar_events` | Consulta eventos del calendario. |

### Anuncios y debates

| Herramienta | Acción |
| --- | --- |
| `get_course_announcements` | Lee anuncios del curso. |
| `get_course_discussions` | Lista debates del curso. |
| `get_discussion_entries` | Lee intervenciones de un debate. |
| `post_discussion_reply` | **Escritura Canvas:** publica una respuesta en un debate. |

### Módulos, páginas y archivos

| Herramienta | Acción |
| --- | --- |
| `get_course_modules` | Consulta módulos y recursos. |
| `get_course_pages` | Lista páginas publicadas. |
| `get_page_content` | Lee el contenido de una página. |
| `get_course_files` | Busca archivos del curso por nombre. |

### Bandeja de entrada

| Herramienta | Acción |
| --- | --- |
| `get_inbox_messages` | Lista mensajes de la bandeja. |
| `get_conversation_detail` | Lee un hilo de mensajes. |
| `send_inbox_message` | **Escritura Canvas:** envía un mensaje interno. |

## Límites actuales y seguridad

- La configuración está pensada para una persona por proceso. No hay autenticación propia del servidor, aislamiento multiusuario ni control de organización. `configure_canvas_credentials` modifica el entorno global del proceso y no debe usarse para compartir un servidor HTTP entre cuentas.
- Las cinco escrituras no tienen modo de solo lectura ni confirmación server-side. Ocultar una herramienta en la interfaz del cliente no es una barrera de seguridad.
- `per_page=30/50/100` aumenta el tamaño de algunas respuestas, pero el cliente no sigue los enlaces `Link` de Canvas. Una lista puede quedar incompleta.
- `clean_html` conserva algunos encabezados, enlaces y énfasis, pero elimina etiquetas restantes y no conserva de forma completa imágenes, texto alternativo, tablas, OCR ni estructura de documentos. No sube archivos ni resuelve cuestionarios.
- `format_date` etiqueta la salida como UTC; no convierte la hora a la zona local y los offsets que no terminan en `Z` necesitan verificación en Canvas.
- La herramienta puede truncar instrucciones o resultados extensos. Confirma el contenido completo y las fechas directamente en Canvas antes de entregar un trabajo.
- Mantén el token en `.env`, evita pasarlo como argumento y no lo pegues en el chat. Revócalo en Canvas cuando ya no lo necesites.

## HTTP y despliegue remoto

`fastmcp.json` declara un despliegue HTTP y `server.py` usa por defecto `0.0.0.0:8000` cuando se ejecuta como proceso. Eso sirve como comportamiento técnico existente, pero no convierte el proyecto en un servicio cloud listo para compartir. No hay Dockerfile, configuración de CI, lockfile ni autenticación propia.

La documentación oficial de Canvas exige OAuth para aplicaciones usadas por múltiples usuarios. Un token personal es adecuado para pruebas manuales de una cuenta, pero no para distribuir este servidor a terceros, aunque cada usuario tenga un proceso separado. Antes de proponer una instalación remota se necesitan OAuth registrado con la institución, aislamiento de sesión y cuenta, autorización de origen, TLS, límites, revocación, auditoría y redacción de secretos. Estas medidas no están implementadas en este repositorio.

## Fuentes

- [FastMCP: ejecutar un servidor](https://gofastmcp.com/deployment/running-server): transporte explícito mediante CLI.
- [uv: entornos virtuales](https://docs.astral.sh/uv/pip/environments/): referencia opcional para trabajar con entornos, sin requerir `uv` en esta guía.
- [Canvas: OAuth2 y autenticación](https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth): diferencia entre token personal y OAuth para aplicaciones de terceros.
- [OpenAI Codex: servidores MCP](https://developers.openai.com/codex/mcp/): sintaxis de servidores MCP locales por STDIO.

Para el plan de mejoras de instalación y accesibilidad, consulta [`docs/accessibility-and-installation.md`](docs/accessibility-and-installation.md).
