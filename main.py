"""
Canvas Student MCP Server
Servidor MCP completo para asistentes de IA para interactuar con Canvas LMS
(Canvas Student) de Instructure.
"""

from typing import List, Optional
from fastmcp import FastMCP
from canvas_client import canvas_client, CanvasAPIError
from utils import clean_html, format_date, truncate_text

# Inicialización del servidor MCP
mcp = FastMCP(
    "Canvas Student MCP",
    instructions="Servidor MCP para interactuar con Canvas LMS en nombre de un estudiante. Permite consultar cursos, tareas, calificaciones, anuncios, foros, módulos, archivos, agenda y enviar entregas.",
)


# ==========================================
# 1. PERFIL Y CONECTIVIDAD
# ==========================================


@mcp.tool()
async def test_canvas_connection() -> str:
    """Verifica si la conexión con Canvas LMS y las credenciales (URL y Token) son válidas."""
    try:
        user = await canvas_client.test_connection()
        return (
            f"✅ Conexión exitosa a Canvas LMS ({canvas_client.base_url})\n"
            f"- Usuario: {user.get('name')} (ID: {user.get('id')})\n"
            f"- Nombre corto: {user.get('short_name')}\n"
            f"- Zona horaria: {user.get('time_zone', 'No especificada')}"
        )
    except CanvasAPIError as e:
        return f"❌ Error de conexión: {str(e)}"
    except Exception as e:
        return f"❌ Error inesperado al conectar con Canvas: {str(e)}"


@mcp.tool()
async def get_student_profile() -> str:
    """Obtiene el perfil detallado del estudiante actual (nombre, email, biografía, avatar)."""
    try:
        profile = await canvas_client.get_profile()
        return (
            f"### Perfil del Estudiante\n"
            f"- **Nombre**: {profile.get('name')}\n"
            f"- **ID de Usuario**: {profile.get('id')}\n"
            f"- **Email**: {profile.get('primary_email', 'No visible')}\n"
            f"- **Zona horaria**: {profile.get('time_zone')}\n"
            f"- **Biografía**: {profile.get('bio') or 'Sin biografía'}\n"
            f"- **Avatar URL**: {profile.get('avatar_url', 'Sin avatar')}"
        )
    except CanvasAPIError as e:
        return f"Error al obtener el perfil: {str(e)}"


# ==========================================
# 2. CURSOS Y CALIFICACIONES
# ==========================================


@mcp.tool()
async def get_active_courses() -> str:
    """Obtiene la lista completa de cursos activos en los que está inscrito el estudiante, incluyendo profesores y periodo académico."""
    try:
        courses = await canvas_client.get_active_courses()
        if not courses:
            return "No se encontraron cursos activos para este estudiante."

        lines = ["### Cursos Activos:"]
        for c in courses:
            c_id = c.get("id")
            name = c.get("name", "Sin nombre")
            code = c.get("course_code", "")
            term = c.get("term", {}).get("name", "Periodo actual")
            teachers = [t.get("display_name") for t in c.get("teachers", []) if t.get("display_name")]
            teachers_str = ", ".join(teachers) if teachers else "Profesor no asignado"

            # Notas si están disponibles en el objeto del curso
            enrollments = c.get("enrollments", [])
            grade_info = ""
            if enrollments:
                current_grade = enrollments[0].get("computed_current_grade")
                current_score = enrollments[0].get("computed_current_score")
                if current_score is not None:
                    grade_info = f" | Nota: {current_score}% ({current_grade or 'N/A'})"

            lines.append(
                f"- **ID: `{c_id}`** | **{name}** ({code})\n"
                f"  - Periodo: {term} | Docente(s): {teachers_str}{grade_info}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar cursos: {str(e)}"


@mcp.tool()
async def get_course_details(course_id: str) -> str:
    """Obtiene los detalles completos de un curso específico, incluyendo su sílabo (programa de la materia) y profesores."""
    try:
        c = await canvas_client.get_course(course_id)
        name = c.get("name")
        code = c.get("course_code")
        term = c.get("term", {}).get("name", "N/A")
        teachers = [t.get("display_name") for t in c.get("teachers", [])]
        syllabus_raw = c.get("syllabus_body")
        syllabus_clean = clean_html(syllabus_raw)

        return (
            f"### Detalles del Curso: {name} (`{code}`)\n"
            f"- **ID**: {c.get('id')}\n"
            f"- **Periodo**: {term}\n"
            f"- **Profesor(es)**: {', '.join(teachers) if teachers else 'No especificados'}\n"
            f"- **Fecha de inicio**: {format_date(c.get('start_at'))}\n"
            f"- **Fecha de fin**: {format_date(c.get('end_at'))}\n\n"
            f"#### Sílabo / Programa de la Asignatura:\n"
            f"{truncate_text(syllabus_clean, 2000)}"
        )
    except CanvasAPIError as e:
        return f"Error al obtener detalles del curso {course_id}: {str(e)}"


@mcp.tool()
async def get_student_grades(course_id: Optional[str] = None) -> str:
    """Obtiene las calificaciones y porcentajes actuales del estudiante para todos los cursos activos o para un curso específico."""
    try:
        enrollments = await canvas_client.get_student_enrollments(course_id=course_id)
        if not enrollments:
            return "No se encontraron calificaciones disponibles."

        lines = ["### Reporte de Calificaciones:"]
        for enr in enrollments:
            c_id = enr.get("course_id")
            grades = enr.get("grades", {})
            current_score = grades.get("current_score")
            current_grade = grades.get("current_grade")
            final_score = grades.get("final_score")
            final_grade = grades.get("final_grade")

            score_text = f"Puntaje actual: {current_score}%" if current_score is not None else "Sin calificar aún"
            if current_grade:
                score_text += f" (Letra: {current_grade})"
            if final_score is not None and final_score != current_score:
                score_text += f" | Puntaje final proyectado: {final_score}% ({final_grade or ''})"

            lines.append(f"- **Curso ID `{c_id}`**: {score_text}")

        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al obtener calificaciones: {str(e)}"


# ==========================================
# 3. TAREAS Y EXÁMENES (ASSIGNMENTS & QUIZZES)
# ==========================================


@mcp.tool()
async def get_course_assignments(course_id: str, bucket: Optional[str] = None) -> str:
    """
    Obtiene las tareas de un curso ordenadas por fecha límite.
    bucket: Filtro opcional. Opciones: 'upcoming' (próximas), 'overdue' (vencidas), 'past' (pasadas), 'undated' (sin fecha), 'ungraded' (sin calificar).
    """
    try:
        assignments = await canvas_client.get_assignments(course_id=course_id, bucket=bucket)
        if not assignments:
            filter_text = f" con filtro '{bucket}'" if bucket else ""
            return f"No se encontraron tareas en el curso {course_id}{filter_text}."

        lines = [f"### Tareas del Curso `{course_id}` ({len(assignments)} encontradas):"]
        for a in assignments:
            a_id = a.get("id")
            name = a.get("name")
            due_at = format_date(a.get("due_at"))
            points = a.get("points_possible", "Sin puntos")
            submission = a.get("submission", {})
            submitted = "✅ Entregada" if submission.get("submitted_at") else "⏳ Pendiente"
            score = f" | Nota: {submission.get('score')}/{points}" if submission.get("score") is not None else ""

            lines.append(
                f"- **ID: `{a_id}`** | **{name}**\n"
                f"  - Fecha Límite: {due_at} | Puntos: {points} | Estado: {submitted}{score}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar tareas del curso {course_id}: {str(e)}"


@mcp.tool()
async def get_assignment_details(course_id: str, assignment_id: str) -> str:
    """Obtiene las instrucciones completas, tipos de entrega aceptados (texto, archivo, url), rúbrica y fecha límite de una tarea específica."""
    try:
        a = await canvas_client.get_assignment(course_id, assignment_id)
        name = a.get("name")
        due_at = format_date(a.get("due_at"))
        points = a.get("points_possible", "Sin puntos")
        sub_types = ", ".join(a.get("submission_types", []))
        desc_clean = clean_html(a.get("description"))

        # Revisar si hay rúbrica
        rubric_lines = []
        rubric = a.get("rubric", [])
        if rubric:
            rubric_lines.append("\n#### Rúbrica de Evaluación:")
            for crit in rubric:
                crit_desc = crit.get("description", "")
                crit_points = crit.get("points", "")
                rubric_lines.append(f"- **{crit_desc}** ({crit_points} pts)")

        rubric_text = "\n".join(rubric_lines) if rubric_lines else ""

        return (
            f"### Tarea: {name} (ID: `{assignment_id}`)\n"
            f"- **Curso ID**: `{course_id}`\n"
            f"- **Fecha Límite**: {due_at}\n"
            f"- **Puntos Posibles**: {points}\n"
            f"- **Formatos de Entrega Permitidos**: {sub_types}\n"
            f"- **Enlace Web**: {a.get('html_url')}\n\n"
            f"#### Instrucciones:\n"
            f"{truncate_text(desc_clean, 3000)}"
            f"{rubric_text}"
        )
    except CanvasAPIError as e:
        return f"Error al obtener detalle de la tarea: {str(e)}"


@mcp.tool()
async def get_quizzes(course_id: str) -> str:
    """Lista los exámenes, evaluaciones y cuestionarios de un curso con límite de tiempo e intentos."""
    try:
        quizzes = await canvas_client.get_quizzes(course_id)
        if not quizzes:
            return f"No se encontraron cuestionarios/exámenes en el curso {course_id}."

        lines = [f"### Cuestionarios / Exámenes del Curso `{course_id}`:"]
        for q in quizzes:
            q_id = q.get("id")
            title = q.get("title")
            due_at = format_date(q.get("due_at"))
            time_limit = f"{q.get('time_limit')} min" if q.get("time_limit") else "Sin límite de tiempo"
            attempts = q.get("allowed_attempts")
            attempts_str = "Ilimitados" if attempts == -1 else f"{attempts} intento(s)"
            points = q.get("points_possible", 0)

            lines.append(
                f"- **ID: `{q_id}`** | **{title}**\n"
                f"  - Fecha Límite: {due_at} | Tiempo: {time_limit} | Intentos: {attempts_str} | Puntos: {points}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar cuestionarios: {str(e)}"


@mcp.tool()
async def get_quiz_details(course_id: str, quiz_id: str) -> str:
    """Obtiene los detalles e instrucciones de un cuestionario o examen específico."""
    try:
        q = await canvas_client.get_quiz(course_id, quiz_id)
        desc_clean = clean_html(q.get("description"))
        return (
            f"### Cuestionario: {q.get('title')} (ID: `{quiz_id}`)\n"
            f"- **Tipo de examen**: {q.get('quiz_type')}\n"
            f"- **Fecha Límite**: {format_date(q.get('due_at'))}\n"
            f"- **Tiempo límite**: {q.get('time_limit') or 'Sin límite'} minutos\n"
            f"- **Preguntas**: {q.get('question_count')}\n"
            f"- **Puntos posibles**: {q.get('points_possible')}\n"
            f"- **Enlace para resolver**: {q.get('html_url')}\n\n"
            f"#### Instrucciones:\n"
            f"{truncate_text(desc_clean, 2500)}"
        )
    except CanvasAPIError as e:
        return f"Error al obtener detalle del cuestionario: {str(e)}"


# ==========================================
# 4. ENTREGAS (SUBMISSIONS) Y RETROALIMENTACIÓN
# ==========================================


@mcp.tool()
async def get_assignment_submission(course_id: str, assignment_id: str) -> str:
    """Consulta la entrega realizada por el estudiante en una tarea, la calificación obtenida y los comentarios del profesor."""
    try:
        sub = await canvas_client.get_submission(course_id, assignment_id)
        submitted_at = format_date(sub.get("submitted_at"))
        grade = sub.get("grade") or "No asignada aún"
        score = sub.get("score")
        workflow = sub.get("workflow_state", "unsubmitted")

        # Comentarios del profesor o alumno
        comments_lines = []
        for c in sub.get("submission_comments", []):
            author = c.get("author_name", "Desconocido")
            date_str = format_date(c.get("created_at"))
            comment_body = c.get("comment", "").strip()
            comments_lines.append(f"  - **{author}** ({date_str}): {comment_body}")

        comments_text = "\n" + "\n".join(comments_lines) if comments_lines else "  Sin comentarios registrados."

        # Archivos adjuntos si los hubo
        attachments = sub.get("attachments", [])
        att_lines = []
        for att in attachments:
            att_lines.append(f"  - [{att.get('display_name')}]({att.get('url')})")
        att_text = "\n" + "\n".join(att_lines) if att_lines else "  Ninguno."

        return (
            f"### Estado de Entrega (Tarea `{assignment_id}` en Curso `{course_id}`)\n"
            f"- **Estado**: {workflow.upper()}\n"
            f"- **Fecha de entrega**: {submitted_at}\n"
            f"- **Puntuación**: {score if score is not None else 'Sin calificar'} (Calificación: {grade})\n"
            f"- **Intento número**: {sub.get('attempt', 1)}\n\n"
            f"#### Archivos entregados:\n{att_text}\n\n"
            f"#### Retroalimentación / Comentarios:\n{comments_text}"
        )
    except CanvasAPIError as e:
        return f"Error al consultar la entrega: {str(e)}"


@mcp.tool()
async def submit_assignment_text(course_id: str, assignment_id: str, text_body: str) -> str:
    """
    Realiza una entrega de tarea en Canvas en nombre del estudiante enviando texto enriquecido o código (online_text_entry).
    Requiere que la tarea acepte entregas de tipo texto.
    """
    try:
        sub = await canvas_client.submit_assignment_text(course_id, assignment_id, text_body)
        return (
            f"✅ Entrega de texto realizada con éxito para la tarea `{assignment_id}` en el curso `{course_id}`.\n"
            f"- Fecha de entrega registrada: {format_date(sub.get('submitted_at'))}\n"
            f"- Estado: {sub.get('workflow_state')}\n"
            f"- Intento: {sub.get('attempt')}"
        )
    except CanvasAPIError as e:
        return f"❌ Error al enviar la entrega de texto: {str(e)}"


@mcp.tool()
async def submit_assignment_url(course_id: str, assignment_id: str, url: str) -> str:
    """
    Realiza una entrega de tarea en Canvas enviando un enlace web (online_url) como Google Drive, GitHub o documento online.
    Requiere que la tarea acepte entregas de tipo URL.
    """
    try:
        sub = await canvas_client.submit_assignment_url(course_id, assignment_id, url)
        return (
            f"✅ Entrega de URL realizada con éxito para la tarea `{assignment_id}` en el curso `{course_id}`.\n"
            f"- URL enviada: {url}\n"
            f"- Fecha de registro: {format_date(sub.get('submitted_at'))}\n"
            f"- Estado: {sub.get('workflow_state')}"
        )
    except CanvasAPIError as e:
        return f"❌ Error al enviar la entrega por URL: {str(e)}"


@mcp.tool()
async def add_submission_comment(course_id: str, assignment_id: str, comment: str) -> str:
    """Añade un comentario a la entrega de una tarea para que lo lea el profesor."""
    try:
        await canvas_client.add_submission_comment(course_id, assignment_id, comment)
        return f"✅ Comentario publicado con éxito en la tarea `{assignment_id}`."
    except CanvasAPIError as e:
        return f"❌ Error al añadir comentario: {str(e)}"


# ==========================================
# 5. AGENDA, TO-DO Y ENTREGAS FALTANTES
# ==========================================


@mcp.tool()
async def get_todo_items() -> str:
    """Obtiene los elementos pendientes urgentes del panel de To-Do del estudiante (tareas y quizzes próximos a vencer)."""
    try:
        items = await canvas_client.get_todo()
        if not items:
            return "🎉 ¡Excelente! No tienes elementos pendientes en tu lista de To-Do."

        lines = [f"### Tareas y Pendientes Urgentes (To-Do - {len(items)} items):"]
        for item in items:
            assignment = item.get("assignment", {})
            course_id = item.get("course_id")
            name = assignment.get("name", item.get("title", "Pendiente"))
            due_at = format_date(assignment.get("due_at"))
            points = assignment.get("points_possible", "N/A")
            html_url = item.get("html_url", assignment.get("html_url", ""))

            lines.append(
                f"- **{name}** (Curso ID: `{course_id}`)\n"
                f"  - Fecha Límite: {due_at} | Puntos: {points} | [Ver en Canvas]({html_url})"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar el To-Do: {str(e)}"


@mcp.tool()
async def get_missing_submissions() -> str:
    """Obtiene la lista de tareas pasadas de fecha que el estudiante NO ha entregado (entregas faltantes)."""
    try:
        missing = await canvas_client.get_missing_submissions()
        if not missing:
            return "🎉 No tienes entregas atrasadas o faltantes reportadas."

        lines = [f"⚠️ **Entregas Faltantes / Atrasadas ({len(missing)} tareas)**:"]
        for m in missing:
            m_id = m.get("id")
            course_id = m.get("course_id")
            name = m.get("name")
            due_at = format_date(m.get("due_at"))
            points = m.get("points_possible", "N/A")
            lines.append(
                f"- **ID: `{m_id}`** | **{name}** (Curso: `{course_id}`)\n"
                f"  - Debió entregarse el: {due_at} | Puntos en juego: {points}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al obtener entregas faltantes: {str(e)}"


@mcp.tool()
async def get_planner_items(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    course_id: Optional[str] = None,
) -> str:
    """
    Obtiene los eventos y tareas del planificador en un rango de fechas (ISO 8601: 'YYYY-MM-DD').
    course_id: Opcional, para filtrar por un curso específico.
    """
    try:
        context_codes = [f"course_{course_id}"] if course_id else None
        items = await canvas_client.get_planner_items(
            start_date=start_date, end_date=end_date, context_codes=context_codes
        )
        if not items:
            return "No se encontraron elementos en el planificador para el rango especificado."

        lines = ["### Elementos del Planificador:"]
        for it in items:
            title = it.get("plannable", {}).get("title", it.get("title", "Actividad"))
            item_type = it.get("plannable_type")
            plannable_date = format_date(it.get("plannable_date"))
            c_code = it.get("context_name", "General")
            status = "Completado" if it.get("submissions", {}).get("submitted") else "Pendiente"

            lines.append(f"- [{item_type}] **{title}** ({c_code}) - {plannable_date} - Estado: {status}")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al obtener el planificador: {str(e)}"


@mcp.tool()
async def get_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    course_id: Optional[str] = None,
) -> str:
    """Obtiene los eventos registrados en el calendario de Canvas para el estudiante."""
    try:
        context_codes = [f"course_{course_id}"] if course_id else None
        events = await canvas_client.get_calendar_events(
            start_date=start_date, end_date=end_date, context_codes=context_codes
        )
        if not events:
            return "No se encontraron eventos de calendario en el rango seleccionado."

        lines = ["### Eventos del Calendario:"]
        for ev in events:
            title = ev.get("title", "Sin título")
            start = format_date(ev.get("start_at"))
            end = format_date(ev.get("end_at"))
            location = ev.get("location_name") or "En línea"
            lines.append(f"- **{title}** | Desde: {start} hasta: {end} | Lugar: {location}")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar el calendario: {str(e)}"


# ==========================================
# 6. ANUNCIOS Y FOROS DE DISCUSIÓN
# ==========================================


@mcp.tool()
async def get_course_announcements(course_id: str, latest_only: bool = False) -> str:
    """Obtiene los anuncios y comunicados oficiales publicados por los profesores en un curso."""
    try:
        announcements = await canvas_client.get_announcements(
            context_codes=[f"course_{course_id}"], latest_only=latest_only
        )
        if not announcements:
            return f"No hay anuncios publicados en el curso `{course_id}`."

        lines = [f"### Anuncios del Curso `{course_id}`:"]
        for a in announcements:
            title = a.get("title")
            author = a.get("user_name", "Profesor")
            date_str = format_date(a.get("posted_at"))
            message_clean = clean_html(a.get("message"))

            lines.append(
                f"\n#### 📢 {title}\n"
                f"- **Publicado por**: {author} el {date_str}\n"
                f"{truncate_text(message_clean, 1000)}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar anuncios: {str(e)}"


@mcp.tool()
async def get_course_discussions(course_id: str) -> str:
    """Lista los foros y temas de discusión activos de un curso."""
    try:
        discussions = await canvas_client.get_discussions(course_id)
        if not discussions:
            return f"No hay foros de discusión activos en el curso `{course_id}`."

        lines = [f"### Foros de Discusión en Curso `{course_id}`:"]
        for d in discussions:
            d_id = d.get("id")
            title = d.get("title")
            posted_at = format_date(d.get("posted_at"))
            unread = d.get("unread_count", 0)
            lines.append(
                f"- **ID: `{d_id}`** | **{title}** (Publicado: {posted_at}) - Mensajes sin leer: {unread}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar foros: {str(e)}"


@mcp.tool()
async def get_discussion_entries(course_id: str, topic_id: str) -> str:
    """Lee los comentarios y respuestas de los alumnos y profesores en un foro de discusión específico."""
    try:
        entries = await canvas_client.get_discussion_entries(course_id, topic_id)
        if not entries:
            return f"El foro `{topic_id}` no tiene respuestas aún."

        lines = [f"### Aportaciones en el Foro `{topic_id}` ({len(entries)} respuestas):"]
        for e in entries[:20]:  # Limitar a 20 para no sobrecargar
            author = e.get("user_name", "Usuario")
            date_str = format_date(e.get("created_at"))
            body_clean = clean_html(e.get("message"))
            lines.append(f"- **{author}** ({date_str}):\n  {truncate_text(body_clean, 500)}\n")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar respuestas del foro: {str(e)}"


@mcp.tool()
async def post_discussion_reply(course_id: str, topic_id: str, message: str) -> str:
    """Publica una respuesta o aportación del estudiante en un foro de discusión."""
    try:
        await canvas_client.post_discussion_reply(course_id, topic_id, message)
        return f"✅ Tu respuesta fue publicada exitosamente en el foro `{topic_id}`."
    except CanvasAPIError as e:
        return f"❌ Error al publicar en el foro: {str(e)}"


# ==========================================
# 7. MÓDULOS, PÁGINAS Y ARCHIVOS DEL CURSO
# ==========================================


@mcp.tool()
async def get_course_modules(course_id: str) -> str:
    """Obtiene la estructura de módulos de aprendizaje (semanas, unidades o bloques temáticos) del curso con sus recursos asociados."""
    try:
        modules = await canvas_client.get_modules(course_id)
        if not modules:
            return f"No se encontraron módulos en el curso `{course_id}`."

        lines = [f"### Módulos del Curso `{course_id}`:"]
        for m in modules:
            m_name = m.get("name")
            m_id = m.get("id")
            items = m.get("items", [])
            lines.append(f"\n📁 **Módulo: {m_name}** (ID: `{m_id}`) - {len(items)} elemento(s):")
            for item in items:
                it_title = item.get("title")
                it_type = item.get("type")
                it_id = item.get("content_id") or item.get("id")
                lines.append(f"  - [{it_type}] {it_title} (ID: `{it_id}`)")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar módulos: {str(e)}"


@mcp.tool()
async def get_course_pages(course_id: str) -> str:
    """Lista las páginas informativas o de contenido creadas por el docente en el curso."""
    try:
        pages = await canvas_client.get_pages(course_id)
        if not pages:
            return f"No hay páginas publicadas en el curso `{course_id}`."

        lines = [f"### Páginas de Contenido en Curso `{course_id}`:"]
        for p in pages:
            title = p.get("title")
            url_slug = p.get("url")
            updated = format_date(p.get("updated_at"))
            lines.append(f"- **{title}** | Slug: `{url_slug}` (Actualizada: {updated})")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al listar páginas: {str(e)}"


@mcp.tool()
async def get_page_content(course_id: str, page_url_or_slug: str) -> str:
    """Obtiene el texto limpio y contenido de una página de clase de Canvas mediante su URL slug o ID."""
    try:
        page = await canvas_client.get_page(course_id, page_url_or_slug)
        title = page.get("title")
        body_clean = clean_html(page.get("body"))
        return (
            f"### Página: {title}\n"
            f"- **Curso**: `{course_id}`\n"
            f"- **Última edición**: {format_date(page.get('updated_at'))}\n\n"
            f"#### Contenido:\n"
            f"{truncate_text(body_clean, 3500)}"
        )
    except CanvasAPIError as e:
        return f"Error al leer contenido de la página: {str(e)}"


@mcp.tool()
async def get_course_files(course_id: str, search_term: Optional[str] = None) -> str:
    """Lista los archivos (PDFs, presentaciones, lecturas) subidos al curso, con opción de búsqueda por nombre."""
    try:
        files = await canvas_client.get_files(course_id, search_term=search_term)
        if not files:
            term_str = f" con término '{search_term}'" if search_term else ""
            return f"No se encontraron archivos en el curso `{course_id}`{term_str}."

        lines = [f"### Archivos del Curso `{course_id}`:"]
        for f in files[:30]:  # Limitar a 30
            name = f.get("display_name", f.get("filename"))
            size_kb = round(f.get("size", 0) / 1024, 1)
            download_url = f.get("url")
            created = format_date(f.get("created_at"))
            lines.append(f"- **[{name}]({download_url})** ({size_kb} KB, {created})")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al listar archivos: {str(e)}"


# ==========================================
# 8. BANDEJA DE ENTRADA / MENSAJERÍA (INBOX)
# ==========================================


@mcp.tool()
async def get_inbox_messages(scope: Optional[str] = None) -> str:
    """
    Obtiene las conversaciones de la bandeja de entrada de Canvas.
    scope: Opcional. Opciones: 'unread' (no leídos), 'starred' (destacados), 'archived' (archivados).
    """
    try:
        convos = await canvas_client.get_conversations(scope=scope)
        if not convos:
            scope_str = f" con filtro '{scope}'" if scope else ""
            return f"No hay conversaciones en tu bandeja de entrada{scope_str}."

        lines = [f"### Bandeja de Mensajes de Canvas ({len(convos)} conversaciones):"]
        for c in convos:
            c_id = c.get("id")
            subject = c.get("subject") or "Sin asunto"
            last_msg = c.get("last_message", "")
            date_str = format_date(c.get("last_message_at"))
            unread = "🔵 No leído" if c.get("workflow_state") == "unread" else "Leído"
            participants = [p.get("name") for p in c.get("participants", [])]

            lines.append(
                f"- **ID: `{c_id}`** | **{subject}** ({unread})\n"
                f"  - Participantes: {', '.join(participants[:3])}\n"
                f"  - Último mensaje ({date_str}): {truncate_text(last_msg, 120)}"
            )
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al consultar la bandeja de entrada: {str(e)}"


@mcp.tool()
async def get_conversation_detail(conversation_id: str) -> str:
    """Obtiene el historial completo de mensajes intercambiados en una conversación de la bandeja de entrada."""
    try:
        convo = await canvas_client.get_conversation(conversation_id)
        subject = convo.get("subject", "Sin asunto")
        messages = convo.get("messages", [])

        lines = [f"### Conversación: {subject} (ID: `{conversation_id}`):"]
        for m in messages:
            author_id = m.get("author_id")
            date_str = format_date(m.get("created_at"))
            body = m.get("body", "")
            lines.append(f"- **Autor ID `{author_id}`** ({date_str}):\n  {body}\n")
        return "\n".join(lines)
    except CanvasAPIError as e:
        return f"Error al obtener detalle de la conversación: {str(e)}"


@mcp.tool()
async def send_inbox_message(
    recipients: List[str],
    body: str,
    subject: Optional[str] = None,
    course_id: Optional[str] = None,
) -> str:
    """
    Envía un mensaje interno a través de la bandeja de entrada de Canvas a uno o más destinatarios (IDs de usuario).
    course_id: Opcional, para asociar el mensaje al contexto de un curso.
    """
    try:
        context_code = f"course_{course_id}" if course_id else None
        await canvas_client.send_message(
            recipients=recipients, body=body, subject=subject, context_code=context_code
        )
        return f"✅ Mensaje enviado exitosamente a los destinatarios: {', '.join(recipients)}."
    except CanvasAPIError as e:
        return f"❌ Error al enviar mensaje: {str(e)}"


# ==========================================
# PUNTO DE ENTRADA
# ==========================================

if __name__ == "__main__":
    mcp.run()