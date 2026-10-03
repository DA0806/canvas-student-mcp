# Accesibilidad e instalación: auditoría y plan

Este documento registra mejoras para que una persona estudiante pueda instalar y usar Canvas Student MCP con menos decisiones y menos riesgo. Se basa en una lectura local del repositorio el 2 de octubre de 2026. La actualización documental está aplicada; las mejoras de código y las pruebas con estudiantes siguen **pendientes**.

## Alcance actual

La ruta que tiene menos superficie de riesgo es:

1. Copiar el repositorio o su ZIP.
2. Crear `.venv` e instalar `requirements.txt` con el Python de ese entorno.
3. Guardar el origen HTTPS de Canvas y el token personal en `.env`.
4. Registrar `fastmcp.exe` o `fastmcp` con una ruta absoluta y `--transport stdio`.
5. Hacer handshake, ejecutar `test_canvas_connection` y luego una consulta de cursos.

La experiencia es de una persona por proceso. El servidor no proporciona una cuenta de usuario propia, un almacén seguro de secretos ni autorización multiusuario.

## Evidencia auditada

| Evidencia | Ubicación |
| --- | --- |
| Dependencias directas y ausencia de lockfile, Dockerfile, scripts, CI y tests | `requirements.txt`; inventario de raíz, 2026-10-02 |
| Entrada MCP, exportación de `mcp` y fallback HTTP/STDIO del proceso | `server.py:1-66` |
| `/health` devuelve estado del proceso y transporte, no una prueba de Canvas | `main.py:26-39` |
| 29 decoradores `@mcp.tool()` y cinco operaciones de escritura | `main.py:51-807` |
| Carga de `.env`, prioridad de entorno, fallback de `fastmcp.json`, headers HTTP y URL por defecto | `canvas_client.py:10-90` |
| Parámetros `per_page` sin seguimiento de `Link` | `canvas_client.py:190-455` |
| Limpieza parcial de HTML, truncamiento y fechas etiquetadas UTC | `utils.py`; `main.py:14` |
| Sintaxis de registro STDIO comprobada con `codex mcp add --help`, sin registrar el servidor en Codex | Validación local, 2026-10-02 |

La comprobación local usó Windows, Python 3.14.4, FastMCP 4.0.10 y HTTPX 0.28.1. Se creó una `.venv` nueva con `uv` y se instalaron los requisitos allí. Después se ejecutó también `python -m venv .venv` y se confirmó con `pip` que los requisitos ya estaban satisfechos; esto no constituye una segunda instalación limpia con `pip`.

Un cliente FastMCP inició un proceso STDIO real desde una carpeta de trabajo distinta, usando rutas absolutas al ejecutable y a `server.py`. El handshake y el descubrimiento exacto de las 29 herramientas coincidieron con los decoradores del código. La llamada a `test_canvas_connection` sin token devolvió la credencial faltante antes de HTTP: cero peticiones a Canvas. La prueba adicional `client.ping()` respondió `Method not found`; no se corrigió el runtime ni se usa ese método como criterio de diagnóstico.

Secuencia de instalación y diagnóstico usada desde la raíz, con rutas del equipo sustituidas por la referencia portable `python`; todas las ejecuciones terminaron correctamente:

```powershell
uv venv .venv --python python
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\fastmcp.exe run --help
py -3 --version
codex mcp add --help
git ls-remote https://github.com/DA0806/canvas-student-mcp.git HEAD
```

Los dos primeros comandos muestran la secuencia usada con una referencia portable a Python; la ejecución local seleccionó explícitamente el Python 3.14.4 instalado. `pip check` no encontró dependencias rotas. La consulta remota confirmó acceso al repositorio, sin modificar remotes locales. Las pruebas no cubren una cuenta Canvas real, escrituras, un cliente gráfico, macOS/Linux, hosting ni accesibilidad con lector de pantalla. La `.venv` de prueba queda local e ignorada por Git.

## Mejoras por prioridad

### P0: documentar y mantener la ruta segura actual

**Aplicado en documentación:** la instalación local STDIO es el camino principal y se retiraron las promesas de hosting, Docker o acceso remoto listo para usar. La facilidad de uso con estudiantes aún necesita validación.

**Criterios de aceptación:**

- Una persona nueva puede seguir solo el README desde una copia limpia.
- Los comandos de Windows y macOS/Linux usan rutas absolutas del `.venv` y no requieren activar el entorno.
- El README explica dónde colocar el token, no lo imprime en comandos y advierte que la URL no lleva `/courses` ni `/api/v1`.
- La primera comprobación distingue handshake, llamada real a Canvas y `/health`.
- El texto no declara soporte de clientes o sistemas que no se hayan probado.

**Accesibilidad documental:** usar encabezados jerárquicos, párrafos cortos, tablas con encabezados, texto visible para cada error y comandos que puedan copiarse con teclado. No depender de capturas de pantalla, color, emojis o pasos que solo existan en una interfaz gráfica.

### P1: asistente de instalación para pruebas personales

**Propuesto, no implementado:** añadir un instalador de consola guiado, opcional y reversible. Debe detectar Python, crear `.venv`, instalar requisitos, pedir el token sin mostrarlo y generar la entrada STDIO para el cliente elegido. No necesita una UI web pesada ni debe modificar configuraciones del usuario sin mostrar el diff y pedir confirmación.

Este flujo con token manual se limita a pruebas personales. Para distribuir la aplicación a estudiantes, el asistente debe conectar mediante OAuth en lugar de pedirles tokens manuales, conforme a la [documentación de Canvas sobre tokens y OAuth](https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth).

**Criterios de aceptación:**

- Funciona con teclado y lector de pantalla, con foco lineal, etiquetas textuales y errores accionables.
- Nunca muestra el token en pantalla, historial, logs o argumentos de proceso.
- Puede cancelarse y repetirse sin borrar el repositorio ni las credenciales existentes.
- Comprueba el origen HTTPS antes de una llamada real y ofrece un modo de diagnóstico que no contacte Canvas.
- Una prueba con una persona que nunca instaló MCP completa la ruta desde una copia limpia y registra cada bloqueo.

Un lockfile o empaquetado reproducible debe añadirse cuando el proyecto se distribuya a más personas o se necesite reconstruir exactamente el entorno; no es necesario inventarlo para esta mejora documental.

### P1: modo de solo lectura y confirmación de escrituras

**Propuesto, no implementado:** imponer el modo de solo lectura en el servidor, declarar explícitamente las cinco herramientas de escritura y exigir una aprobación contextual antes de enviar entregas, comentarios, respuestas o mensajes. La aprobación del cliente ayuda, pero no sustituye una regla server-side.

**Criterios de aceptación:**

- Una configuración de solo lectura bloquea las cinco escrituras aunque el cliente intente llamarlas.
- Cada escritura muestra destino, contenido y efecto antes de ejecutarse.
- Las pruebas verifican que el token y el contenido no aparecen en errores ni logs.
- `configure_canvas_credentials` deja claro que cambia el proceso y no crea una sesión aislada.

### P1: paginación completa en la fuente

**Propuesto, no implementado:** seguir los enlaces `Link` de Canvas hasta el final, con límite, timeout y manejo de errores. El `per_page` alto por sí solo no garantiza listas completas.

**Criterios de aceptación:**

- Las listas paginadas devuelven todos los elementos o un estado explícito de truncamiento.
- Un límite de seguridad evita ciclos y respuestas sin acotar.
- Una prueba con varias páginas cubre `next`, `last`, ausencia de `Link` y error de una página posterior.

### P2: conservar estructura y contexto temporal

**Propuesto, no implementado:** conservar `alt` de imágenes, enlaces, tablas y listas de forma semántica; evitar truncamiento silencioso; incluir la longitud y un enlace al contenido original. Convertir fechas a la zona elegida por la persona y mantener el offset de origen cuando no sea UTC.

**Criterios de aceptación:**

- El lector de pantalla recibe una alternativa textual para imágenes con `alt`.
- Una tabla se devuelve como tabla accesible o como filas etiquetadas.
- El resultado indica cuándo fue truncado y cómo consultar el contenido completo.
- Una fecha con offset distinto de `Z` conserva su zona y se puede comparar con la zona local.

### P0/P1 para una futura distribución a terceros: OAuth y aislamiento

**Propuesto, no implementado:** diseñar una modalidad remota con OAuth de Canvas, sesión por usuario, almacenamiento seguro y autorización de origen. Canvas indica que los tokens personales sirven para uso manual de una cuenta; las aplicaciones utilizadas por múltiples usuarios deben usar OAuth. Separar procesos no convierte un token personal en un mecanismo de distribución aprobado.

**Criterios de aceptación:**

- La institución registra y aprueba la aplicación OAuth.
- Cada usuario autoriza su propia cuenta y los tokens se almacenan fuera del código y de los logs.
- Las peticiones no pueden cruzar credenciales, sesiones, organizaciones ni conversaciones.
- El servicio usa TLS, lista de orígenes permitidos, límites, revocación, auditoría sin secretos y borrado documentado.
- Un revisor de seguridad prueba una sesión válida, una sesión revocada y dos usuarios concurrentes.

Esta modalidad requiere una decisión de producto y soporte operativo. No debe promocionarse junto a la instalación local mientras esos criterios estén pendientes.

## Criterios de accesibilidad verificables

No se declara conformidad WCAG con la documentación actual. Para una futura validación:

- Una persona que use solo teclado puede copiar comandos, editar `.env` con instrucciones claras y reconocer cada resultado.
- Un lector de pantalla puede recorrer el documento por encabezados y leer tablas con sus encabezados.
- Los errores incluyen causa probable y siguiente acción en texto, sin depender de color o iconos.
- La guía ofrece una alternativa textual a cada captura que se añada después.
- La prueba incluye al menos una persona estudiante novel y una prueba con lector de pantalla; se registran sistema, cliente, versión de Python y resultado.

## Fuentes de referencia

- [FastMCP: ejecutar servidores](https://gofastmcp.com/deployment/running-server)
- [uv: entornos virtuales](https://docs.astral.sh/uv/pip/environments/)
- [Canvas: OAuth2 y autenticación](https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth)
- [OpenAI Codex: configuración de MCP](https://developers.openai.com/codex/mcp/)
