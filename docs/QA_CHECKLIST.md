# Manual QA Checklist — Adaptador de Ideas

## 1. Smoke Tests (app-wide)
- [ ] `python -m pytest tests/ -v` → 161 passed, 0 failed
- [ ] `ruff check src/adaptador/` → 0 errors (F, I, E)
- [ ] `mypy src/adaptador/ --ignore-missing-imports` → solo errores pre-existentes (yaml stubs, Any return)

## 2. State Corruption
- [ ] Transición NUEVA → saltar a REVISION → rechazada
- [ ] Transición REVISION → volver a NUEVA → rechazada
- [ ] ARCHIVADA → cualquier estado → rechazado (terminal)
- [ ] Job COMPLETADO → EN_CURSO → rechazado
- [ ] Job CANCELADO → cualquier estado → rechazado
- [ ] fail_job con `retry=True` e intentos disponibles → vuelve a PENDIENTE
- [ ] fail_job sin `retry` → queda FALLIDO
- [ ] fail_job con intentos agotados → queda FALLIDO aunque retry=True

## 3. Persistence
- [ ] Commit exitoso → datos recuperables en nueva sesión
- [ ] Update de entidad inexistente → ValueError sin corromper otras
- [ ] list_pending excluye EN_CURSO, COMPLETADO, FALLIDO
- [ ] WAL mode: lectura durante escritura concurrente
- [ ] FK constraint impide jobs huérfanos

## 4. Retries
- [ ] max_retries=0 → exactamente 1 intento
- [ ] max_retries=3 → exactamente 4 intentos
- [ ] Backoff exponencial: 1s, 2s, 4s, 8s...
- [ ] Timeout en runner → job no queda EN_CURSO
- [ ] Múltiples fallos → métricas consistentes (processed = failed + completed)

## 5. Backup / Restore
- [ ] Crear backup → archivo .db en backup_dir
- [ ] Restaurar → archivo .db.restored con contenido original
- [ ] Listar backups → entries ordenados por fecha
- [ ] Prune: max_versions respetado (más viejos eliminados)
- [ ] Integrity check detecta archivos faltantes
- [ ] Metadata corrupta → list_backups() devuelve vacío (no crash)
- [ ] Restore sin backups → FileNotFoundError descriptivo

## 6. Ollama Recovery
- [ ] Primer intento falla → segundo funciona (reintento transitorio)
- [ ] Todas las conexiones fallan → AITransientError final
- [ ] JSON inválido → AIResponseValidationError (no corrupción de job)
- [ ] Runner con Ollama offline → job nunca EN_CURSO al final
- [ ] Timeout en handler → timed_out incrementado en métricas

## 7. Kanban Drag/Drop
- [ ] Arrastrar tarjeta → cursor mano cerrada durante drag
- [ ] Soltar en columna destino → signal card_dropped emitido
- [ ] Soltar fuera de columna → no signal
- [ ] MIME type incorrecto → drop ignorado
- [ ] remove_card → tarjeta eliminada de lista interna

## 8. UI Freeze Protection
- [ ] Ollama client timeout=120s → httpx timeout configurado
- [ ] Transcriber timeout ≥ 60s
- [ ] process_one con handler lento → timeout corta antes de 5s

---

# Edge Cases Documentados

| # | Escenario | Comportamiento esperado | Estado |
|---|-----------|------------------------|--------|
| 1 | Idea con título vacío y contenido vacío | lanza ValidationAppError | ✅ test |
| 2 | max_intentos=0 | job falla en primer intento, sin reintento | ✅ test |
| 3 | max_intentos=-1 | lanza ValidationAppError | ✅ test |
| 4 | timeout_segundos=0 | lanza ValidationAppError | ✅ test |
| 5 | payoad.options no es dict | lanza ValidationAppError en handler | ✅ test |
| 6 | Audio path inexistente en transcripción | TranscriptionError | ✅ test |
| 7 | Backup sin base de datos | FileNotFoundError | ✅ test |
| 8 | Restore con backup_id inexistente | ValueError | ✅ test |
| 9 | Múltiples backups en mismo segundo | timestamp colisión manejada (overwrite) | ⚠️ conocido |
| 10 | Windows file locking durante backup | shutil.copy2 maneja en la mayoría de casos | ⚠️ manual |
| 11 | Ollama devuelve HTML en vez de JSON | AIResponseValidationError | ✅ test |
| 12 | FK constraint en jobs huérfanos | IntegrityError al insertar | ✅ test |
| 13 | Ventana cerrada durante job en curso | job runner completará o fallará con timeout | ✅ test |
| 14 | Drag empezado y cancelado (Escape) | cursor vuelve a mano abierta | ✅ code |
