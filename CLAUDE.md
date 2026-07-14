# CLAUDE.md

Este archivo da contexto e instrucciones a Claude Code para trabajar en el proyecto Saberia.

## Instrucciones de comportamiento (obligatorias)

- Responde siempre en español, sin excepción.
- No hagas commits. No hagas push. No abras Pull Requests. El control de versiones lo maneja el usuario manualmente, siempre.
- No escribas comentarios dentro del código (ni `#`, ni docstrings explicativos línea por línea). El código debe ser legible por sí mismo mediante nombres claros de variables y funciones. Excepción: comentarios estrictamente necesarios para cumplimiento legal o licencias, si aplica.
- Al terminar una tarea, corre la suite de tests relevante y muestra el resultado real, no un resumen inventado.
- Si tomas una decisión de diseño no especificada explícitamente en la tarea, dilo explícitamente al final de tu respuesta junto con el motivo.

## Descripción del proyecto

Saberia es una aplicación que convierte libros digitales (PDF/EPUB) subidos por el propio usuario en audiolibros generados por IA, reproducibles únicamente dentro de la app. No hay catálogo público ni intercambio de libros entre usuarios; cada biblioteca es privada.

Este repositorio contiene el backend. El frontend (Flutter) vive fuera de este repositorio.

## Stack técnico

- Backend: FastAPI (Python), arquitectura de monolito modular (sin microservicios).
- Base de datos: PostgreSQL 15+, accedida vía SQLAlchemy + Alembic para migraciones.
- Cola y cache: Redis.
- Procesamiento asíncrono: Celery (conversión de libros, extracción de texto, detección de capítulos, generación de audio).
- Almacenamiento de archivos: Cloudflare R2 (compatible S3, se accede vía SDK tipo boto3). Nunca se guardan URLs completas en la base de datos, solo paths relativos; las URLs firmadas se generan en runtime.

## Reglas de negocio clave

- Límite de 3 conversiones de libro por usuario por mes calendario (tabla `user_monthly_limits`), validado con `SELECT ... FOR UPDATE` para evitar condiciones de carrera.
- Tamaño máximo de archivo: PDF 50 MB, EPUB 20 MB. Máximo 300 páginas y 100.000 palabras por libro.
- Cada capítulo genera su propio archivo de audio (no un archivo único por libro).
- Soft delete en `users` y `books`: nunca `DELETE` físico. Se usa `deleted_at` (+ `is_active=false` en usuarios).
- Limpieza automática: si un libro no se reproduce en 90 días, se eliminan sus archivos de audio de R2 (no el libro ni sus capítulos), quedando disponibles para regenerar.
- Nunca se muestran anuncios durante la reproducción, entre capítulos, ni en pausas.
- El esquema completo de base de datos (tablas, enums, constraints e índices) ya fue diseñado y se refleja en las migraciones de Alembic una vez creadas — esas migraciones son la fuente de verdad del modelo de datos, no un script SQL externo.

## Estructura de carpetas (monolito modular)

- `app/core/` — configuración, conexión a base de datos, utilidades transversales.
- `app/modules/<nombre>/` — un módulo por dominio de negocio (ej. `users`, `auth`, `books`, `chapters`, `listening`). Cada módulo contiene sus propios modelos, esquemas Pydantic, rutas y lógica de servicio, sin depender del código interno de otros módulos salvo a través de interfaces explícitas.
- `app/shared/` — código verdaderamente transversal usado por más de un módulo (ej. clientes de R2, utilidades de storage).
- `tests/` — refleja la misma estructura de `app/`, un archivo de test por módulo como mínimo.

## Entorno virtual (venv) — regla obligatoria

Este proyecto usa un entorno virtual en backend/venv. Antes de ejecutar cualquier `pip install`, es obligatorio:

1. Activar el venv: `source venv/Scripts/activate` (Git Bash en Windows).
2. Verificar que quedó activo corriendo: `python -c "import sys; print(sys.executable)"`.
3. Confirmar que la ruta impresa está dentro de la carpeta `venv/`. Si no lo está, detente y avisa al usuario en vez de continuar instalando — nunca instales paquetes con el Python global del sistema.

Cualquier paquete nuevo que se instale debe agregarse también a requirements.txt con su versión exacta (`==`), en el mismo turno en que se instala.