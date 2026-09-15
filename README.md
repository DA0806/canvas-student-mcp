# 🎓 Canvas Student MCP Server

Un servidor **Model Context Protocol (MCP)** completo y optimizado para permitir a asistentes de Inteligencia Artificial (Claude Desktop, Cursor, Gemini, ChatGPT, Cline, etc.) interactuar fluidamente con la plataforma educativa **Canvas LMS (Canvas Student)** de Instructure en nombre de un estudiante.

---

## 🌟 Características Principales

- **28 herramientas especializadas** cubriendo el ciclo académico completo del estudiante.
- **Optimizado para Asistentes IA**:
  - Paginación automática (`per_page=50/100`) para no omitir materias ni tareas.
  - Limpieza de HTML crudo a Markdown legible para ahorrar tokens y mejorar la comprensión del LLM.
  - Formateo de fechas ISO 8601 a horarios legibles.
  - Manejo amigable de permisos y restricciones institucionales.
- **Arquitectura Asíncrona**: Basado en **FastMCP 4.x** y **HTTPX**.

---

## 📋 Catálogo de Herramientas MCP

### 1. Perfil y Conexión
| Herramienta | Descripción |
| :--- | :--- |
| `test_canvas_connection` | Verifica credenciales, conectividad y muestra el usuario conectado. |
| `get_student_profile` | Consulta información del estudiante (nombre, ID, correo institucional, biografía). |

### 2. Cursos y Calificaciones
| Herramienta | Descripción |
| :--- | :--- |
| `get_active_courses` | Lista cursos activos con ID, código, periodo académico y docentes asignados. |
| `get_course_details` | Silabo completo del curso, fechas de inicio/fin y programa de la materia. |
| `get_student_grades` | Calificaciones actuales y finales proyectadas por curso. |

### 3. Tareas y Exámenes (Assignments & Quizzes)
| Herramienta | Descripción |
| :--- | :--- |
| `get_course_assignments` | Tareas con fechas límite y estado de entrega (`upcoming`, `overdue`, `past`). |
| `get_assignment_details` | Instrucciones limpias, puntos, formatos permitidos y rúbrica de evaluación. |
| `get_quizzes` | Cuestionarios/exámenes con límite de tiempo e intentos permitidos. |
| `get_quiz_details` | Instrucciones y configuración detallada de un cuestionario. |

### 4. Entregas y Retroalimentación
| Herramienta | Descripción |
| :--- | :--- |
| `get_assignment_submission` | Consulta la entrega realizada, nota obtenida y comentarios del docente. |
| `submit_assignment_text` | Realiza una entrega enviando texto enriquecido o código. |
| `submit_assignment_url` | Realiza una entrega enviando un enlace web (Google Drive, GitHub, etc.). |
| `add_submission_comment` | Envía un mensaje o aclaración al docente en una entrega existente. |

### 5. Agenda, To-Do y Entregas Faltantes
| Herramienta | Descripción |
| :--- | :--- |
| `get_todo_items` | Tareas y actividades urgentes del panel To-Do de Canvas. |
| `get_missing_submissions` | Identifica tareas pasadas de fecha que **aún no han sido entregadas**. |
| `get_planner_items` | Agenda del planificador de Canvas en un rango de fechas. |
| `get_calendar_events` | Eventos y citas del calendario escolar. |

### 6. Anuncios y Foros
| Herramienta | Descripción |
| :--- | :--- |
| `get_course_announcements` | Avisos oficiales publicados por profesores. |
| `get_course_discussions` | Lista de foros de discusión activos en el curso. |
| `get_discussion_entries` | Respuestas e intervenciones en un foro específico. |
| `post_discussion_reply` | Publica una aportación o respuesta en un foro de discusión. |

### 7. Módulos, Páginas y Archivos
| Herramienta | Descripción |
| :--- | :--- |
| `get_course_modules` | Estructura temática/semanal de la clase con sus respectivos recursos. |
| `get_course_pages` | Lista de páginas de contenido publicadas por el profesor. |
| `get_page_content` | Lee el texto completo de una página de clase. |
| `get_course_files` | Archivos (PDFs, lecturas, diapositivas) con buscador por nombre. |

### 8. Bandeja de Mensajería (Inbox)
| Herramienta | Descripción |
| :--- | :--- |
| `get_inbox_messages` | Mensajes recientes o no leídos en la bandeja de entrada. |
| `get_conversation_detail` | Hilo completo de mensajes con un profesor o compañero. |
| `send_inbox_message` | Envía un mensaje interno a través de Canvas. |

---

## 🔑 Cómo Obtener tu Token de Canvas LMS

1. Abre Canvas LMS en tu navegador (la URL de tu colegio o universidad).
2. En la barra lateral izquierda, haz clic en **Cuenta (Account)** -> **Configuración (Settings)**.
3. Desplázate hacia abajo hasta la sección **Tokens de acceso aprobados (Approved Integrations)**.
4. Haz clic en el botón **+ Nuevo token de acceso (+ New Access Token)**.
5. En "Propósito", escribe un nombre descriptivo (ej: `Asistente IA MCP`) y opcionalmente define una fecha de expiración.
6. Haz clic en **Generar token**.
7. **Copia el token inmediatamente**, ya que Canvas solo lo muestra una vez.

---

## ⚙️ Configuración e Instalación

### 1. Clonar o ingresar a la carpeta del proyecto
```bash
cd "d:\Proyectos\Visual Studio Projects\Canva Student MCP"
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` con tus datos:
```env
CANVAS_BASE_URL=https://tu-universidad.instructure.com
CANVAS_API_TOKEN=tu_token_generado_aqui
```

---

## 🤖 Integración con Clientes MCP

### Configuración en Claude Desktop
Añade lo siguiente a tu archivo `claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json` en Windows):

```json
{
  "mcpServers": {
    "canvas-student": {
      "command": "python",
      "args": [
        "d:\\Proyectos\\Visual Studio Projects\\Canva Student MCP\\main.py"
      ],
      "env": {
        "CANVAS_BASE_URL": "https://tu-universidad.instructure.com",
        "CANVAS_API_TOKEN": "tu_token_aqui"
      }
    }
  }
}
```

### Configuración en Cursor / Gemini / Cline / Roo Code
Configura un nuevo servidor MCP tipo `stdio`:
- **Nombre**: `Canvas Student`
- **Comando**: `python`
- **Argumentos**: `d:/Proyectos/Visual Studio Projects/Canva Student MCP/main.py`
- **Variables de Entorno**:
  - `CANVAS_BASE_URL`: URL de tu institución.
  - `CANVAS_API_TOKEN`: Tu token de Canvas.

---

## 💬 Ejemplos de Preguntas para tu Asistente IA

Una vez conectado, podrás pedirle cosas como:

- *"¿Qué tareas tengo pendientes de entregar para esta semana en todos mis cursos?"*
- *"Revisa si tengo entregas atrasadas o faltantes en Canvas."*
- *"¿Cuál es mi promedio y calificación actual en cada asignatura?"*
- *"Léeme las instrucciones y la rúbrica de la Tarea 3 del curso de Algoritmos."*
- *"¿Qué avisos nuevos han publicado mis profesores en los últimos 7 días?"*
- *"Busca diapositivas o PDFs subidos en la materia de Física."*
- *"Entrega este enlace de Google Drive en la tarea de Proyecto Final."*
