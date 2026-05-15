# Premortem — Adaptador de Ideas v0.1.0

> **Fecha:** 2026-05-15
> **Premisa:** Es junio de 2027. La app lleva 6 meses sin usarse. ¿Qué salió mal?

---

## Metodología

Un *premortem* asume que el proyecto **ya fracasó** y trabaja hacia atrás para identificar las causas. A diferencia de una auditoría técnica (que busca bugs), un premortem busca **los motivos por los que dejarías de usar la app**, incluyendo problemas de UX, fricciones operacionales y deuda técnica acumulada.

He revisado los 40+ archivos del repositorio para identificar **7 escenarios de fracaso** organizados en 3 categorías.

---

## 🔴 Categoría A: Fracasos de Adopción / UX

### A1. "Dejé de usarla porque el pipeline IA nunca funcionó bien"

**Narrativa:** El usuario crea ideas, las envía a Jobs IA, pero los resultados son inconsistentes: a veces Ollama no responde, a veces el resultado es genérico e inútil. Tras 2 semanas, el usuario deja de presionar "Enviar a Jobs IA" y la app se convierte en un notepad con tema oscuro.

**Evidencia en el código:**

1. **El prompt es genérico y no iterativo** ([ideas_screen.py:423-438](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/ideas_screen.py#L423-L438)):
   ```python
   _PROMPT_TEMPLATE = (
       "Actúa como un experto en gestión de proyectos..."
       " Voy a darte una idea y quiero que la desgloses..."
   )
   ```
   Un solo template hardcodeado para TODAS las ideas. No hay forma de que el usuario personalice el prompt, elija un estilo de enriquecimiento, o itere sobre el resultado.

2. **El resultado del job no se muestra en la UI** — `complete_job()` guarda `resultado` en la BD ([job_service.py:164-180](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/services/job_service.py#L164-L180)), y `set_enriched_content()` existe ([idea_service.py:136-156](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/services/idea_service.py#L136-L156)), pero **nadie invoca `set_enriched_content()`** tras completar el job. El resultado se pierde en una columna de la BD que ninguna pantalla lee.

3. **No hay feedback visual del progreso** — El usuario presiona "Procesar pendientes", ve un botón que dice "Procesando..." y luego un QMessageBox genérico. No hay barra de progreso, no hay indicación de qué job está procesando, no hay preview del resultado.

**Probabilidad:** 🔴 **Muy alta** — Es el escenario de fracaso más probable. La propuesta de valor central (IA local) no cierra el loop.

**Mitigación:**
- [ ] Conectar `complete_job → set_enriched_content` automáticamente en el handler
- [ ] Mostrar `contenido_enriquecido` en la UI de detalle de idea
- [ ] Permitir múltiples templates de prompt (seleccionables por el usuario)
- [ ] Añadir barra de progreso con nombre del job actual

---

### A2. "Las pantallas Kanban, Repo y Settings no hacen nada real"

**Narrativa:** El usuario navega por las pantallas pero descubre que la mitad de la app es decoración.

**Evidencia:**

| Pantalla | Estado real |
|----------|-------------|
| **Kanban** ([kanban_screen.py](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/kanban_screen.py)) | Simula carga con `QTimer.singleShot(700)` y luego muestra columnas **vacías**. No conecta con datos reales — no tiene `set_services()`. |
| **Repo** ([repo_screen.py](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/repo_screen.py)) | Simula carga y siempre muestra "Repositorio vacío". No tiene lógica de importación de archivos. |
| **Settings** ([settings_screen.py](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/settings_screen.py)) | Los switches `_SimpleSwitch` son **decorativos** — no tienen evento `clicked`, no leen/escriben config. La URL de Ollama está **hardcodeada como "192.168.1.100"** en la línea 139, diferente de la real en `app.yaml`. |

**Probabilidad:** 🟠 **Alta** — El usuario percibirá que la app es un prototipo incompleto.

**Mitigación:**
- [ ] `KanbanScreen` debe recibir servicios y cargar ideas reales por columna
- [ ] `SettingsScreen` debe leer `app.yaml` y los switches deben ser funcionales
- [ ] `RepoScreen` puede ser un placeholder explícito ("Próximamente") en vez de simular actividad

---

### A3. "Capturar ideas es más lento que un TXT"

**Narrativa:** El panel de captura requiere título + contenido con dos clicks. Para un sistema de "captura sin fricción" (Objetivo O1), esto es demasiada ceremonia. El usuario abre Notepad en su lugar.

**Evidencia:** [_CapturePanel._on_save](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/ideas_screen.py#L94-L102) requiere contenido no vacío, pero el título es opcional (se auto-genera). Sin embargo, no hay atajos de teclado (Ctrl+Enter), no hay captura rápida desde system tray, y el campo de audio (uno de los pilares del MVP) **no existe en la UI**.

**Probabilidad:** 🟠 **Alta** — Si la captura no es más rápida que alternativas existentes, la app pierde su razón de ser.

**Mitigación:**
- [ ] Ctrl+Enter para guardar rápido
- [ ] System tray con captura global por hotkey
- [ ] Botón de grabación de audio en el panel de captura
- [ ] Import de archivos (PDF, MP3, MD) por drag & drop

---

## 🟠 Categoría B: Fracasos Técnicos Silenciosos

### B1. "La BD creció hasta que la app se congeló"

**Narrativa:** Tras meses de uso con cientos de ideas y jobs, la app empieza a tardar 3-5 segundos al cambiar de pantalla. Los jobs completados nunca se purgan.

**Evidencia:**

1. **Jobs completados se acumulan para siempre** — `_do_load` en [jobs_screen.py:302-305](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/jobs_screen.py#L302-L305) solo muestra `list_pending()`, pero jobs completados/fallidos nunca se limpian de la BD. No hay GC ni purge.

2. **`list_pending()` hace un full scan** — [job_repository.py](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/db/job_repository.py) filtra por `estado='pendiente'`, pero no hay índice en la columna `estado` del modelo ([models.py:79](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/db/models.py#L79)).

3. **No hay paginación** — `list_by_estado()` carga TODAS las ideas de un estado en memoria.

4. **`shutil.copy2` para backups** — [backup/engine.py:152](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/backup/engine.py#L152) copia el archivo entero de la BD. Si la BD crece a 200MB, cada backup copia 200MB.

**Probabilidad:** 🟡 **Media** — Depende del volumen de uso. Single-user puede tardar meses en manifestarse.

**Mitigación:**
- [ ] Añadir índice en `JobModel.estado` y `IdeaModel.estado_kanban`
- [ ] Implementar paginación en repositorios
- [ ] Auto-purge de jobs completados > 30 días
- [ ] Usar `sqlite3.backup()` nativo en vez de `shutil.copy2`

---

### B2. "Perdí datos tras un crash durante el procesamiento IA"

**Narrativa:** Ollama tarda 90 segundos en responder. El usuario se frustra y cierra la app con Alt+F4. Al reiniciar, la idea está en estado `EN_PROCESO` pero el job quedó `EN_CURSO` — el resultado del LLM se perdió.

**Evidencia:**

1. **`recover_in_progress_jobs` funciona** ([job_service.py:115-143](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/services/job_service.py#L115-L143)) — los jobs vuelven a `PENDIENTE`. ✅

2. **Pero la idea NO se recupera** — `move_idea(idea_id, EN_PROCESO)` se llama en [ideas_screen.py:459](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/ideas_screen.py#L459), pero cuando el job falla/se recupera, **nadie devuelve la idea a `NUEVA`**. La idea queda atrapada en `EN_PROCESO` sin job activo.

3. **`closeEvent` no espera al QThread** — [main_window.py:245-253](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/main_window.py#L245-L253) cierra la sesión pero no llama a `_processor.wait()` ni `_processor.requestInterruption()`. El hilo de procesamiento muere bruscamente.

**Probabilidad:** 🟠 **Alta** — Ollama es lento. El usuario CERRARÁ la app durante procesamiento.

**Mitigación:**
- [ ] `closeEvent` debe esperar al QThread con timeout (o `requestInterruption`)
- [ ] Cuando un job falla/se reencola, devolver la idea a `NUEVA` automáticamente
- [ ] Mostrar diálogo "Hay procesamiento en curso, ¿cerrar de todos modos?"

---

## 🟡 Categoría C: Fracasos de Arquitectura a Mediano Plazo

### C1. "El código se volvió inmantenible al añadir features"

**Narrativa:** Al implementar la Iteración 2 (audio + transcripción), cada cambio toca 8 archivos porque la UI está acoplada con la lógica de negocio.

**Evidencia:**

1. **`IdeasScreen` conoce el prompt template** — La pantalla de UI define cómo formular la petición a la IA ([ideas_screen.py:423-438](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/ideas_screen.py#L423-L438)). Esto es lógica de negocio en la capa de presentación.

2. **`_on_enqueue_selected` orquesta 3 capas** — En un solo método ([ideas_screen.py:440-472](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/ui/screens/ideas_screen.py#L440-L472)): construye prompts, encola jobs, mueve ideas, y muestra resultados. Es un God Method.

3. **No hay evento/signal entre pantallas** — Si el usuario procesa un job en `JobsScreen`, `IdeasScreen` no se entera del cambio de estado. Tampoco `KanbanScreen`. Cada pantalla opera en aislamiento.

4. **Entidades mutables** — `Idea` y `Job` son dataclasses mutables. Cualquier capa puede modificar un campo sin notificar a las demás.

**Probabilidad:** 🟡 **Media** — Mientras sea single-developer, es manejable. Se agrava con cada feature.

**Mitigación:**
- [ ] Extraer `_PROMPT_TEMPLATE` y la lógica de encolado a `IdeaService` o un nuevo `EnqueueService`
- [ ] Implementar un event bus (Signal de Qt) para cambios de estado cross-screen
- [ ] Considerar entidades inmutables (`frozen=True` en dataclass)

---

### C2. "Los backups nunca se probaron y fallan en producción"

**Narrativa:** El usuario confía en los "backups automáticos" que la pantalla de Settings dice que están activos, pero nunca se ejecutaron realmente. Cuando la BD se corrompe, no hay backup.

**Evidencia:**

1. **Los backups no son automáticos** — No hay ningún `QTimer` ni scheduler que invoque `BackupEngine.create_backup()` periódicamente. La config `backup.max_versions: 10` existe pero nadie la usa en runtime.

2. **`BackupEngine._copy_sqlite_snapshot` usa `shutil.copy2`** ([engine.py:152](file:///d:/Desarrollo/Adaptador%20de%20ideas/src/adaptador/backup/engine.py#L150-L152)) — Esto puede producir un backup inconsistente si SQLite está escribiendo durante la copia (race condition con WAL). El método correcto es `sqlite3.backup()`.

3. **Los tests de backup fallan** — Los 5 tests en `test_qa.py::TestBackupRestore` fallan con `sqlite3.DatabaseError: file is not a database`. Esto confirma que el módulo de backup nunca fue validado end-to-end.

4. **El switch "Backups" en Settings es decorativo** — No conecta con nada.

**Probabilidad:** 🔴 **Muy alta** — Los backups están rotos desde el inicio. Cuando se necesiten, no existirán.

**Mitigación:**
- [ ] Implementar `sqlite3.backup()` nativo
- [ ] Añadir `QTimer` en `MainWindow` que ejecute backup cada N minutos
- [ ] Corregir los tests de backup
- [ ] Conectar el switch de Settings con la lógica real

---

## Resumen de Riesgos

| # | Escenario | Prob. | Impacto | Riesgo |
|---|-----------|-------|---------|--------|
| A1 | Pipeline IA no cierra el loop | 🔴 Muy alta | 🔴 Fatal | **Crítico** |
| C2 | Backups rotos / inexistentes | 🔴 Muy alta | 🔴 Fatal | **Crítico** |
| A2 | Pantallas decorativas | 🟠 Alta | 🟠 Alto | **Alto** |
| B2 | Pérdida de estado tras crash | 🟠 Alta | 🟠 Alto | **Alto** |
| A3 | Captura más lenta que TXT | 🟠 Alta | 🟠 Alto | **Alto** |
| C1 | Código inmantenible | 🟡 Media | 🟠 Alto | **Medio** |
| B1 | BD crece sin límite | 🟡 Media | 🟡 Medio | **Medio** |

---

## Roadmap de Mitigaciones (por esfuerzo/impacto)

### 🏃 Quick Wins (1-2 horas cada uno)
1. Conectar `complete_job → set_enriched_content` (A1)
2. `closeEvent` que espera al QThread (B2)
3. Corregir URL hardcodeada en `settings_screen.py:139` (A2)
4. Añadir índices en `estado` y `estado_kanban` (B1)
5. `KanbanScreen.set_services()` con carga real (A2)

### 🔧 Medium Effort (medio día cada uno)
6. Mostrar `contenido_enriquecido` en la UI (A1)
7. Implementar `sqlite3.backup()` y corregir tests (C2)
8. Extraer prompt template a servicio (C1)
9. Auto-recovery de ideas cuando job falla (B2)
10. Ctrl+Enter y hotkeys de captura (A3)

### 🏗️ Major Effort (1+ día)
11. Timer de backups automáticos (C2)
12. Pantalla de Settings funcional (A2)
13. Captura de audio con UI (A3)
14. Event bus entre pantallas (C1)
15. Paginación y purge de jobs (B1)

> [!IMPORTANT]
> Los escenarios **A1** y **C2** son los más peligrosos porque afectan directamente la propuesta de valor y la confiabilidad de los datos. Sin resolverlos, la app no sobrevivirá al primer mes de uso real.
