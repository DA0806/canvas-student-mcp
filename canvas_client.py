"""
Cliente HTTP asíncrono para la API REST de Canvas LMS.
Gestiona autenticación mediante Bearer Token, resolución de URLs base,
control de errores HTTP y soporte para endpoints orientados al estudiante.
"""

import os
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env local
load_dotenv()

# Fallback: si no están en el entorno, intentar cargar desde fastmcp.json (ideal para MCPHosting si el repo es privado)
try:
    import json
    from pathlib import Path

    _cfg_path = Path(__file__).parent / "fastmcp.json"
    if _cfg_path.exists():
        with open(_cfg_path, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
            _env_vars = _data.get("deployment", {}).get("env", {})
            for _k, _v in _env_vars.items():
                if _k not in os.environ and _v:
                    os.environ[_k] = str(_v)
except Exception:
    pass



class CanvasAPIError(Exception):
    """Excepción para errores devueltos por la API de Canvas LMS."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class CanvasClient:
    """
    Cliente asíncrono optimizado para Canvas LMS REST API v1.
    """

    def __init__(self):
        self.timeout = 25.0

    @property
    def base_url(self) -> str:
        # 1. Variable de entorno
        url = os.getenv("CANVAS_BASE_URL", "").strip().rstrip("/")
        if url:
            return url
        # 2. Header HTTP de la petición actual (enviado por cliente MCP / ChatGPT)
        try:
            from fastmcp.server.dependencies import get_http_request

            req = get_http_request()
            h_url = req.headers.get("x-canvas-base-url") or req.headers.get("x-canvas-url")
            if h_url:
                return h_url.strip().rstrip("/")
        except Exception:
            pass
        # 3. Fallback seguro por defecto
        return "https://canvas.instructure.com"

    @property
    def token(self) -> str:
        # 1. Variable de entorno
        tok = os.getenv("CANVAS_API_TOKEN", "").strip()
        if tok:
            return tok
        # 2. Header Authorization (Bearer token) o x-canvas-token enviado por ChatGPT
        try:
            from fastmcp.server.dependencies import get_http_request

            req = get_http_request()
            auth = req.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                return auth[7:].strip()
            elif auth:
                return auth.strip()
            h_tok = req.headers.get("x-canvas-token", "")
            if h_tok:
                return h_tok.strip()
        except Exception:
            pass
        return ""


    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            raise CanvasAPIError(
                "No se ha configurado CANVAS_API_TOKEN. Por favor define la variable de entorno o tu archivo .env.",
                status_code=401,
            )
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "CanvasStudentMCP/1.0",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Ejecuta una petición HTTP a la API de Canvas con manejo de errores exhaustivo.
        """
        if not self.token:
            raise CanvasAPIError(
                "Falta el token de acceso de Canvas. Configura CANVAS_API_TOKEN en el entorno o en el archivo .env.",
                status_code=401,
            )

        clean_endpoint = endpoint.lstrip("/")
        if not clean_endpoint.startswith("api/v1/"):
            clean_endpoint = f"api/v1/{clean_endpoint}"

        url = f"{self.base_url}/{clean_endpoint}"
        headers = self._get_headers()

        # Filtrar parámetros None
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=clean_params,
                    data=data,
                    json=json_body,
                )
            except httpx.RequestError as exc:
                raise CanvasAPIError(
                    f"Error de red o conexión al contactar Canvas LMS ({self.base_url}): {str(exc)}"
                )

            if response.status_code == 401:
                raise CanvasAPIError(
                    "Error 401: No autorizado. El token de Canvas es inválido o ha expirado. Verifica CANVAS_API_TOKEN.",
                    status_code=401,
                )
            elif response.status_code == 403:
                raise CanvasAPIError(
                    "Error 403: Prohibido. Tu institución o curso no permite el acceso a este recurso para tu rol de estudiante.",
                    status_code=403,
                )
            elif response.status_code == 404:
                raise CanvasAPIError(
                    f"Error 404: El recurso solicitado no fue encontrado en Canvas ({url}).",
                    status_code=404,
                )
            elif response.status_code >= 400:
                try:
                    error_json = response.json()
                except Exception:
                    error_json = response.text
                raise CanvasAPIError(
                    f"Error de Canvas LMS ({response.status_code}): {error_json}",
                    status_code=response.status_code,
                    details=error_json,
                )

            try:
                return response.json()
            except Exception:
                return response.text

    # --- 1. Perfil y Conectividad ---

    async def get_profile(self) -> Dict[str, Any]:
        """Obtiene el perfil del usuario autenticado."""
        return await self._request("GET", "users/self/profile")

    async def test_connection(self) -> Dict[str, Any]:
        """Prueba básica de conectividad."""
        return await self._request("GET", "users/self")

    # --- 2. Cursos, Silabos y Calificaciones ---

    async def get_active_courses(self) -> List[Dict[str, Any]]:
        """Lista cursos activos con datos de profesores, periodo y puntajes."""
        params = {
            "enrollment_state": "active",
            "include[]": ["total_scores", "current_grading_period_scores", "teachers", "term", "course_image"],
            "per_page": 50,
        }
        res = await self._request("GET", "courses", params=params)
        return res if isinstance(res, list) else []

    async def get_course(self, course_id: str) -> Dict[str, Any]:
        """Detalles de un curso con silabo y profesores."""
        params = {
            "include[]": ["syllabus_body", "teachers", "total_scores", "term"],
        }
        return await self._request("GET", f"courses/{course_id}", params=params)

    async def get_student_enrollments(self, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene las inscripciones con notas actuales y finales."""
        if course_id:
            params = {"user_id": "self", "include[]": ["current_points"]}
            res = await self._request("GET", f"courses/{course_id}/enrollments", params=params)
        else:
            params = {
                "type[]": "StudentEnrollment",
                "state[]": "active",
                "include[]": ["current_points", "avatar_url"],
                "per_page": 50,
            }
            res = await self._request("GET", "users/self/enrollments", params=params)
        return res if isinstance(res, list) else []

    # --- 3. Tareas y Quizzes ---

    async def get_assignments(
        self,
        course_id: str,
        bucket: Optional[str] = None,
        order_by: str = "due_at",
    ) -> List[Dict[str, Any]]:
        """
        Lista las tareas de un curso.
        bucket puede ser: 'past', 'overdue', 'undated', 'ungraded', 'upcoming', 'future'.
        """
        params = {
            "order_by": order_by,
            "bucket": bucket,
            "include[]": ["submission", "score_statistics"],
            "per_page": 100,
        }
        res = await self._request("GET", f"courses/{course_id}/assignments", params=params)
        return res if isinstance(res, list) else []

    async def get_assignment(self, course_id: str, assignment_id: str) -> Dict[str, Any]:
        """Detalle completo de una tarea incluyendo rúbrica y entrega actual."""
        params = {
            "include[]": ["submission", "rubric"],
        }
        return await self._request("GET", f"courses/{course_id}/assignments/{assignment_id}", params=params)

    async def get_quizzes(self, course_id: str) -> List[Dict[str, Any]]:
        """Lista cuestionarios/exámenes del curso."""
        params = {"per_page": 50}
        res = await self._request("GET", f"courses/{course_id}/quizzes", params=params)
        return res if isinstance(res, list) else []

    async def get_quiz(self, course_id: str, quiz_id: str) -> Dict[str, Any]:
        """Detalle de un cuestionario/examen."""
        return await self._request("GET", f"courses/{course_id}/quizzes/{quiz_id}")

    # --- 4. Entregas (Submissions) y Comentarios ---

    async def get_submission(self, course_id: str, assignment_id: str) -> Dict[str, Any]:
        """Obtiene la entrega propia para una tarea con comentarios y evaluación."""
        params = {
            "include[]": ["submission_comments", "rubric_assessment"],
        }
        return await self._request(
            "GET",
            f"courses/{course_id}/assignments/{assignment_id}/submissions/self",
            params=params,
        )

    async def submit_assignment_text(
        self, course_id: str, assignment_id: str, text_body: str
    ) -> Dict[str, Any]:
        """Envía una entrega de tarea mediante texto en línea/HTML."""
        data = {
            "submission[submission_type]": "online_text_entry",
            "submission[body]": text_body,
        }
        return await self._request(
            "POST",
            f"courses/{course_id}/assignments/{assignment_id}/submissions",
            data=data,
        )

    async def submit_assignment_url(
        self, course_id: str, assignment_id: str, url: str
    ) -> Dict[str, Any]:
        """Envía una entrega de tarea mediante una URL externa (Drive, Github, etc.)."""
        data = {
            "submission[submission_type]": "online_url",
            "submission[url]": url,
        }
        return await self._request(
            "POST",
            f"courses/{course_id}/assignments/{assignment_id}/submissions",
            data=data,
        )

    async def add_submission_comment(
        self, course_id: str, assignment_id: str, comment_text: str
    ) -> Dict[str, Any]:
        """Agrega un comentario del estudiante a su entrega existente."""
        data = {
            "comment[text_comment]": comment_text,
        }
        return await self._request(
            "POST",
            f"courses/{course_id}/assignments/{assignment_id}/submissions/self/comments",
            data=data,
        )

    # --- 5. Agenda, To-Do y Entregas Faltantes ---

    async def get_todo_items(self) -> List[Dict[str, Any]]:
        """Lista de pendientes urgentes (To-Do) del estudiante."""
        res = await self._request("GET", "users/self/todo")
        return res if isinstance(res, list) else []

    async def get_missing_submissions(self) -> List[Dict[str, Any]]:
        """Lista de tareas pasadas de fecha que NO han sido entregadas."""
        params = {"per_page": 50}
        res = await self._request("GET", "users/self/missing_submissions", params=params)
        return res if isinstance(res, list) else []

    async def get_planner_items(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        context_codes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Elementos del planificador de Canvas en un rango de fechas."""
        params: Dict[str, Any] = {"per_page": 50}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if context_codes:
            params["context_codes[]"] = context_codes

        res = await self._request("GET", "planner/items", params=params)
        return res if isinstance(res, list) else []

    async def get_calendar_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        context_codes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Eventos del calendario."""
        params: Dict[str, Any] = {
            "type": "event",
            "per_page": 50,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if context_codes:
            params["context_codes[]"] = context_codes

        res = await self._request("GET", "calendar_events", params=params)
        return res if isinstance(res, list) else []

    # --- 6. Anuncios y Foros de Discusión ---

    async def get_announcements(
        self,
        context_codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        latest_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Obtiene avisos oficiales de cursos (ej: context_codes=['course_123'])."""
        params: Dict[str, Any] = {
            "context_codes[]": context_codes,
            "active_only": "true",
            "latest_only": "true" if latest_only else "false",
            "per_page": 50,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        res = await self._request("GET", "announcements", params=params)
        return res if isinstance(res, list) else []

    async def get_discussions(self, course_id: str) -> List[Dict[str, Any]]:
        """Lista foros y temas de discusión de un curso."""
        params = {"per_page": 50}
        res = await self._request("GET", f"courses/{course_id}/discussion_topics", params=params)
        return res if isinstance(res, list) else []

    async def get_discussion_entries(self, course_id: str, topic_id: str) -> List[Dict[str, Any]]:
        """Obtiene mensajes y respuestas dentro de un foro de discusión."""
        params = {"per_page": 50}
        res = await self._request(
            "GET", f"courses/{course_id}/discussion_topics/{topic_id}/entries", params=params
        )
        return res if isinstance(res, list) else []

    async def post_discussion_reply(
        self, course_id: str, topic_id: str, message: str
    ) -> Dict[str, Any]:
        """Publica un comentario o respuesta en un foro de discusión."""
        data = {"message": message}
        return await self._request(
            "POST", f"courses/{course_id}/discussion_topics/{topic_id}/entries", data=data
        )

    # --- 7. Módulos, Páginas y Archivos ---

    async def get_modules(self, course_id: str) -> List[Dict[str, Any]]:
        """Obtiene las semanas o módulos de aprendizaje con sus respectivos items."""
        params = {"include[]": ["items"], "per_page": 50}
        res = await self._request("GET", f"courses/{course_id}/modules", params=params)
        return res if isinstance(res, list) else []

    async def get_pages(self, course_id: str) -> List[Dict[str, Any]]:
        """Lista las páginas informativas publicadas en el curso."""
        params = {"per_page": 50}
        res = await self._request("GET", f"courses/{course_id}/pages", params=params)
        return res if isinstance(res, list) else []

    async def get_page(self, course_id: str, page_url_or_id: str) -> Dict[str, Any]:
        """Contenido completo de una página específica."""
        return await self._request("GET", f"courses/{course_id}/pages/{page_url_or_id}")

    async def get_files(
        self, course_id: str, search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lista archivos o lecturas compartidas en el curso con opción de búsqueda."""
        params: Dict[str, Any] = {"per_page": 50}
        if search_term:
            params["search_term"] = search_term
        res = await self._request("GET", f"courses/{course_id}/files", params=params)
        return res if isinstance(res, list) else []

    # --- 8. Bandeja de Entrada / Mensajería ---

    async def get_conversations(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista conversaciones de la bandeja de entrada (scope: 'unread', 'starred', 'archived')."""
        params: Dict[str, Any] = {"per_page": 30}
        if scope:
            params["scope"] = scope
        res = await self._request("GET", "conversations", params=params)
        return res if isinstance(res, list) else []

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Obtiene el detalle y mensajes de una conversación."""
        return await self._request("GET", f"conversations/{conversation_id}")

    async def send_message(
        self,
        recipients: List[str],
        body: str,
        subject: Optional[str] = None,
        context_code: Optional[str] = None,
    ) -> Any:
        """Envía un mensaje interno a uno o más destinatarios."""
        data: Dict[str, Any] = {
            "recipients[]": recipients,
            "body": body,
        }
        if subject:
            data["subject"] = subject
        if context_code:
            data["context_code"] = context_code
        return await self._request("POST", "conversations", data=data)


# Instancia compartida
canvas_client = CanvasClient()
