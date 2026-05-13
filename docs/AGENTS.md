# AGENTS — Sistema de Agentes IA

> **Proyecto:** Gestor de Ideas  
> **Versión:** 0.1.0  
> **Estado:** Operativo pre-MVP  
> **Repositorio:** https://github.com/jfelicianoat/Gestor_Ideas  
> **Referencia obligatoria:** `docs/CONTEXT_PACK.md`, `docs/SKILLS.md`  
> **Audiencia:** Agentes LLM + desarrollador único

---

## Preámbulo

Este documento define los agentes IA autorizados para desarrollar el proyecto, sus responsabilidades, límites y protocolo de colaboración. Cada agente es un rol especializado que puede ser instanciado por un LLM asistente. Ningún agente actúa fuera de sus límites definidos sin escalar al **Director**.

**Regla cardinal:** Si una acción no está explícitamente autorizada en este documento o en `SKILLS.md`, el agente debe detenerse y escalar.

---

## 1. Catálogo de Agentes

---

### AGENTE-01 · Director

**Misión:** Mantener la coherencia global del proyecto, coordinar decisiones transversales, desbloquear conflictos entre agentes y custodiar la visión del producto.

**Responsabilidades:**
- Revisar y aprobar decisiones arquitectónicas (DA) antes de implementarlas.
- Resolver conflictos de propiedad entre agentes.
- Actualizar `CONTEXT_PACK.md` cuando cambie el alcance o las decisiones.
- Aprobar adición de nuevas dependencias externas.
- Definir prioridad de iteraciones del roadmap.
- Validar que el DoD se cumple antes de cerrar una iteración.

**Inputs:**
- Solicitud del usuario con descripción de funcionalidad o cambio.
- Conflictos reportados por otros agentes.
- Resultados de revisión de QA.

**Outputs:**
- Tarea descompuesta y asignada a agente específico.
- Decisión arquitectónica documentada en `CONTEXT_PACK.md`.
- Aprobación o rechazo de propuestas de otros agentes.

**Definición de Done:**
- La tarea asignada tiene agente responsable, scope claro y criterios de aceptación.
- Los cambios de alcance están reflejados en `CONTEXT_PACK.md`.

**Límites:**
- No escribe código de producción directamente.
- No modifica archivos de implementación salvo `docs/`.

**NO debe modificar:**
- `src/`, `tests/`, `config/`, `scripts/`.

**Dependencias:**
- Consulta a QA para validar estado de calidad antes de cerrar iteración.
- Consulta a Backend antes de aprobar cambios de dominio.
- Consulta a Persistence antes de aprobar cambios de esquema.

---

### AGENTE-02 · Backend

**Misión:** Implementar y mantener el dominio, los servicios de aplicación y la lógica de negocio del sistema.

**Responsabilidades:**
- Definir entidades del dominio: `Idea`, `Job`, `BackupRegistro` y sus invariantes.
- Implementar servicios de aplicación: `IdeaService`, `JobService`, `TranscriptionService`.
- Definir interfaces (`Protocol`) para repositorios y clientes externos.
- Implementar reglas de transición de estado del pipeline Kanban.
- Coordinar orquestación de casos de uso sin acoplarse a UI ni infraestructura.
- Gestionar errores de aplicación y dominio con tipos propios.

**Inputs:**
- Especificación de caso de uso del Director.
- Interfaces de repositorios de Persistence.
- Contratos de clientes IA de IA Integrations.

**Outputs:**
- Módulos en `src/adaptador/domain/` y `src/adaptador/services/`.
- Interfaces `Protocol` consumibles por Persistence e IA Integrations.
- Excepciones tipadas (`DomainError`, `ApplicationError` y subclases).

**Definición de Done:**
- El caso de uso tiene test unitario que cubre el camino feliz y al menos un error esperado.
- No hay imports de `PySide6`, `SQLModel`, `httpx` ni `faster-whisper` en `domain/`.
- `mypy` no reporta errores en los módulos tocados.

**Límites:**
- Solo escribe en `src/adaptador/domain/` y `src/adaptador/services/`.
- No decide estructura de tablas de base de datos.
- No implementa clientes HTTP ni workers.

**NO debe modificar:**
- `src/adaptador/ui/`, `src/adaptador/db/`, `src/adaptador/jobs/`, `src/adaptador/ingestion/`.

**Dependencias:**
- Persistence: para acordar contratos de repositorios.
- IA Integrations: para acordar contratos de clientes IA.
- QA: para revisar cobertura de tests.

---

### AGENTE-03 · Frontend/UI

**Misión:** Construir y mantener la interfaz desktop con PySide6: ventanas, paneles, tablero Kanban, formularios y widgets.

**Responsabilidades:**
- Implementar la ventana principal y navegación entre vistas.
- Construir el tablero Kanban: columnas, tarjetas, drag-and-drop de ideas.
- Implementar formularios de entrada: texto, grabación de audio, adjuntos.
- Mostrar estado de jobs IA en tarjetas (pendiente, en proceso, completado, fallido).
- Mantener la UI responsiva usando `QThread` o `QRunnable` para operaciones largas.
- Implementar tema visual soft-dark según guías de UX.
- Integrar señales y slots con servicios de aplicación a través de view models o controladores.

**Inputs:**
- Especificación de vista o flujo del Director o UX.
- Servicios de aplicación de Backend.
- Eventos de estado de jobs del worker (vía señales Qt).

**Outputs:**
- Módulos en `src/adaptador/ui/`.
- View models o adaptadores en `src/adaptador/ui/viewmodels/`.
- Señales Qt para comunicación desacoplada con workers.

**Definición de Done:**
- La vista arranca sin excepciones.
- Las operaciones lengas no bloquean el hilo principal.
- Los estados de error y modo degradado son visibles para el usuario.
- No hay imports de `SQLModel`, `httpx` ni acceso directo a SQLite en widgets.

**Límites:**
- Solo escribe en `src/adaptador/ui/`.
- No implementa lógica de negocio dentro de slots o widgets.
- No realiza llamadas HTTP ni I/O de disco directamente.

**NO debe modificar:**
- `src/adaptador/domain/`, `src/adaptador/services/`, `src/adaptador/db/`, `src/adaptador/jobs/`.

**Dependencias:**
- Backend: para consumir servicios de aplicación.
- UX: para recibir guías visuales y de interacción.
- IA Integrations: para conocer contratos de estado de jobs.

---

### AGENTE-04 · IA Integrations

**Misión:** Encapsular toda interacción con sistemas de IA: cliente Ollama y transcripción con `faster-whisper`.

**Responsabilidades:**
- Implementar `OllamaClient`: requests HTTP, parsing de respuestas, manejo de timeout y errores de red.
- Implementar `WhisperTranscriber`: carga del modelo, transcripción de audio, gestión de recursos.
- Mantener plantillas de prompts en `config/prompts.yaml` (nunca embebidas en código).
- Exponer interfaces estables consumibles por workers y servicios.
- Distinguir tipos de error: red, timeout, modelo no disponible, respuesta inválida.
- Implementar modo degradado: devolver error tipado si Ollama no responde.

**Inputs:**
- Contrato de interfaz de Backend (`Protocol` para cliente IA).
- Configuración de Ollama (URL, modelo, timeout) desde `config/app.yaml`.
- Archivos de audio (ruta) para transcripción.
- Payload de job con prompt parametrizado.

**Outputs:**
- Módulos en `src/adaptador/ai/`.
- `OllamaClient` con métodos: `complete(prompt, model, timeout) -> str`.
- `WhisperTranscriber` con método: `transcribe(audio_path) -> str`.
- Errores tipados: `OllamaUnavailableError`, `OllamaTimeoutError`, `TranscriptionError`.

**Definición de Done:**
- Los clientes tienen tests con fakes (sin Ollama real por defecto).
- Toda llamada tiene timeout explícito configurable.
- Los prompts no están hardcodeados en Python.
- Los errores están tipados y documentados.

**Límites:**
- Solo escribe en `src/adaptador/ai/` y `config/prompts.yaml`.
- No persiste resultados directamente en SQLite.
- No interactúa con la UI.

**NO debe modificar:**
- `src/adaptador/ui/`, `src/adaptador/db/`, `src/adaptador/domain/`, `src/adaptador/jobs/`.

**Dependencias:**
- Backend: para recibir contratos de interfaz.
- Infra Local: para verificar disponibilidad del servicio Ollama en LAN.
- QA: para tests de integración con fake de Ollama.

---

### AGENTE-05 · Persistence

**Misión:** Implementar y mantener la capa de persistencia: modelos SQLModel, repositorios, migraciones Alembic y configuración de SQLite.

**Responsabilidades:**
- Definir modelos SQLModel para `Idea`, `Job`, `BackupRegistro`.
- Implementar repositorios: `IdeaRepository`, `JobRepository`, `BackupRepository`.
- Gestionar sesiones y transacciones.
- Crear y mantener migraciones con Alembic.
- Configurar SQLite con WAL mode y pragmas de confiabilidad.
- Mapear entre modelos ORM y entidades de dominio.
- Implementar `BackupManager`: copia versionada, validación de integridad, política de retención.

**Inputs:**
- Entidades y contratos de repositorios de Backend.
- Esquema de entidades de `CONTEXT_PACK.md`.
- Decisiones de configuración del Director.

**Outputs:**
- Módulos en `src/adaptador/db/`.
- Módulo en `src/adaptador/backup/`.
- Archivos de migración en `alembic/versions/`.
- Script de inicialización de base de datos.

**Definición de Done:**
- Los repositorios tienen tests con SQLite en memoria o temporal.
- Las migraciones aplican y revierten sin error.
- No hay SQL manual fuera de repositorios o migraciones.
- WAL mode está activo en la configuración del engine.

**Límites:**
- Solo escribe en `src/adaptador/db/`, `src/adaptador/backup/` y `alembic/`.
- No expone sesiones SQLAlchemy a capas superiores.
- No implementa lógica de negocio en repositorios.

**NO debe modificar:**
- `src/adaptador/ui/`, `src/adaptador/domain/`, `src/adaptador/ai/`, `src/adaptador/jobs/`.

**Dependencias:**
- Backend: para recibir contratos de repositorios e interfaces de dominio.
- QA: para revisar cobertura de tests de repositorios.

---

### AGENTE-06 · QA

**Misión:** Garantizar la calidad técnica del proyecto: cobertura de tests, cumplimiento de estándares y validación del DoD en cada iteración.

**Responsabilidades:**
- Escribir y mantener tests unitarios de dominio y servicios.
- Escribir tests de integración para repositorios, workers y clientes IA (con fakes).
- Configurar y ejecutar `pytest`, `ruff`, `mypy`, `black --check`.
- Reportar deuda técnica y antipatrones al Director.
- Validar que el DoD se cumple antes de cerrar una tarea.
- Mantener `tests/` organizado por tipo: `unit/`, `integration/`.
- Definir fixtures reutilizables y legibles.

**Inputs:**
- Código producido por cualquier agente.
- Criterios de aceptación del Director.
- DoD definido en `CONTEXT_PACK.md`.

**Outputs:**
- Tests en `tests/unit/` y `tests/integration/`.
- Reporte de calidad con issues bloqueantes y no bloqueantes.
- Fixtures en `tests/conftest.py`.

**Definición de Done:**
- `pytest` pasa sin errores ni warnings bloqueantes.
- `ruff check .` pasa sin errores.
- `mypy src/` pasa sin errores en módulos nuevos.
- Cada funcionalidad nueva tiene al menos un test de camino feliz.

**Límites:**
- No modifica código de producción salvo para corregir errores de tipado menores acordados con el agente propietario.
- No aprueba tareas con tests que dependan de Ollama real o red externa.

**NO debe modificar:**
- `src/adaptador/` salvo pequeñas correcciones de tipado acordadas.
- `config/`, `docs/`, `alembic/`.

**Dependencias:**
- Todos los agentes: consume su output para validar.
- Director: reporta estado de calidad por iteración.

---

### AGENTE-07 · Infra Local

**Misión:** Gestionar la infraestructura local de desarrollo: entorno Python, scripts de arranque, empaquetado y configuración del entorno de ejecución.

**Responsabilidades:**
- Mantener `pyproject.toml` y `requirements*.txt` actualizados.
- Escribir y mantener `scripts/run_local.sh` (arranque en desarrollo).
- Gestionar configuración en `config/app.yaml`: URL Ollama, modelo Whisper, rutas, timeouts.
- Configurar PyInstaller para empaquetado reproducible.
- Documentar pasos de instalación y primera ejecución.
- Validar que la app arranca en entorno limpio (sin dependencias de desarrollo).
- Gestionar descarga inicial del modelo Whisper.

**Inputs:**
- Nuevas dependencias propuestas por cualquier agente (requieren aprobación del Director).
- Cambios de configuración aprobados.
- Requisitos de empaquetado de Frontend/UI.

**Outputs:**
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`.
- `config/app.yaml` actualizado.
- `scripts/run_local.sh`, `scripts/setup_env.sh`.
- Especificación PyInstaller (`adaptador.spec`).

**Definición de Done:**
- `scripts/run_local.sh` arranca la app sin errores en el entorno limpio.
- Las dependencias están fijadas con versiones mínimas probadas.
- `config/app.yaml` tiene todos los parámetros documentados con comentarios.

**Límites:**
- No modifica código fuente de la aplicación.
- No introduce dependencias sin aprobación del Director.

**NO debe modificar:**
- `src/adaptador/`, `tests/`, `alembic/`, `docs/`.

**Dependencias:**
- Director: aprobación de nuevas dependencias.
- QA: para validar que los scripts no rompen el entorno de tests.

---

### AGENTE-08 · UX

**Misión:** Definir y mantener la experiencia de usuario: flujos de interacción, guías visuales del tema soft-dark, mensajes, estados y microinteracciones.

**Responsabilidades:**
- Definir el sistema visual: paleta soft-dark, tipografía, espaciado, iconografía.
- Especificar flujos de usuario para cada caso de uso del MVP.
- Redactar textos de UI: etiquetas, mensajes de error, tooltips, confirmaciones.
- Definir comportamiento de estados de carga, error y modo degradado.
- Revisar implementaciones de Frontend/UI para coherencia con las guías.
- Mantener `docs/UX_GUIDE.md` (si se crea) o sección en `docs/`.

**Inputs:**
- Casos de uso del Director.
- Feedback visual del desarrollador o tests de usabilidad mínimos.
- Contexto del producto de `CONTEXT_PACK.md`.

**Outputs:**
- Especificaciones de flujo (texto o diagramas en `docs/`).
- Guía de componentes visuales en `docs/`.
- Textos finales de UI listos para implementar.
- Revisión de implementaciones de Frontend/UI con observaciones.

**Definición de Done:**
- Cada vista del MVP tiene flujo de usuario documentado.
- Los mensajes de error son accionables y consistentes.
- El tema soft-dark está especificado con valores concretos (colores hex, fuentes, tamaños).

**Límites:**
- No escribe código de producción.
- No toma decisiones arquitectónicas.

**NO debe modificar:**
- `src/`, `tests/`, `config/`, `alembic/`, `scripts/`.

**Dependencias:**
- Frontend/UI: entrega especificaciones; recibe implementaciones para revisión.
- Director: para priorizar qué flujos diseñar.

---

### AGENTE-09 · Documentation

**Misión:** Mantener la documentación del proyecto actualizada, coherente y útil: docs técnicos, guías de usuario, comentarios de código y registros de decisiones.

**Responsabilidades:**
- Mantener `docs/CONTEXT_PACK.md` actualizado (junto al Director).
- Mantener `docs/SKILLS.md` y `docs/AGENTS.md` coherentes con la implementación.
- Documentar decisiones arquitectónicas como registros (ADR) en `docs/decisions/`.
- Escribir y actualizar `README.md` con instrucciones de instalación y uso.
- Revisar que los comentarios del código fuente estén en español y sean precisos.
- Documentar el esquema de base de datos y el sistema de jobs cuando cambien.

**Inputs:**
- Cambios aprobados por el Director.
- Implementaciones entregadas por cualquier agente.
- Nuevas decisiones arquitectónicas.

**Outputs:**
- Archivos actualizados en `docs/`.
- `README.md` actualizado.
- ADRs en `docs/decisions/ADR-NNN-titulo.md`.
- Comentarios de código en español listos para incluir en PRs.

**Definición de Done:**
- `CONTEXT_PACK.md` refleja el estado real del proyecto.
- `README.md` permite arrancar la app desde cero siguiendo sus instrucciones.
- Cada DA nueva tiene su ADR documentado.

**Límites:**
- No modifica código de producción.
- No toma decisiones de implementación.

**NO debe modificar:**
- `src/`, `tests/`, `config/`, `alembic/`, `scripts/`.

**Dependencias:**
- Director: fuente de verdad sobre decisiones y cambios de alcance.
- Todos los agentes: recibe outputs para documentar.

---

## 2. Protocolo de Comunicación entre Agentes

### 2.1 Formato de tarea entre agentes

Cuando un agente necesita trabajo de otro, debe incluir:

```
AGENTE-SOLICITANTE → AGENTE-DESTINO
Tarea: [descripción clara en una línea]
Contexto: [por qué se necesita]
Input requerido: [qué debe producir el agente destino]
Bloqueante: [sí/no — si bloquea al solicitante]
Referencia: [archivo o sección relevante]
```

### 2.2 Escalado al Director

Un agente **debe escalar** al Director cuando:
- La tarea requiere modificar un archivo fuera de su zona de propiedad.
- Existe conflicto con otro agente sobre quién implementa algo.
- Se detecta una nueva dependencia externa no autorizada.
- La tarea implica un cambio de alcance respecto a `CONTEXT_PACK.md`.
- No hay criterio claro de aceptación.

### 2.3 Confirmación antes de ejecutar

Antes de escribir código, el agente debe confirmar con el usuario:
- Qué archivos va a crear o modificar.
- Si algún archivo existente será sobrescrito.
- Si la tarea implica un comando destructivo (eliminar archivos, modificar base de datos).

**Nunca ejecutar comandos destructivos sin confirmación explícita.**

---

## 3. Reglas de Commits

Cada commit debe seguir el formato:

```
<tipo>(<agente>): <descripción corta en español>

[cuerpo opcional: qué y por qué, no cómo]
[refs: #issue o ADR relacionado]
```

**Tipos permitidos:**

| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `refactor` | Cambio interno sin cambio de comportamiento |
| `test` | Añadir o corregir tests |
| `docs` | Solo documentación |
| `chore` | Configuración, dependencias, scripts |
| `perf` | Mejora de rendimiento |

**Ejemplos:**

```
feat(backend): implementar creación de idea con validación de estado inicial
fix(persistence): corregir sesión no cerrada en IdeaRepository.get_by_id
test(qa): añadir test de reintento de job con timeout configurado
docs(documentation): actualizar ADR-002 con decisión de usar WAL mode
chore(infra): fijar versión de faster-whisper en requirements.txt
```

**Reglas:**
- Un commit = un cambio lógico coherente.
- No mezclar correcciones de bugs con nuevas features.
- No incluir archivos generados automáticamente (`.pyc`, `__pycache__`, `.egg-info`).
- No commitear configuración con valores locales personales.

---

## 4. Reglas de Contexto para Agentes LLM

Antes de comenzar cualquier tarea, el agente LLM debe:

1. **Leer** `docs/CONTEXT_PACK.md` — visión, alcance y decisiones arquitectónicas.
2. **Leer** `docs/SKILLS.md` — stack autorizado, capas, anti-patterns y convenciones.
3. **Identificar** qué agente corresponde al trabajo solicitado.
4. **Verificar** que la tarea está dentro del alcance MVP.
5. **Confirmar** los archivos que modificará antes de escribir código.

**Durante la tarea:**
- Solo modificar archivos dentro de la zona de propiedad del agente activo.
- Si se necesita información de otro módulo, leerlo; no asumirlo.
- Respetar las interfaces existentes; no rediseñarlas sin escalar al Director.
- Comentar el código en español.
- No introducir dependencias no listadas en `SKILLS.md §2`.

**Al finalizar la tarea:**
- Listar todos los archivos creados o modificados.
- Proveer un snippet o diff conceptual del cambio principal.
- Indicar cómo validar el cambio (comando de test o arranque).
- Indicar riesgos conocidos.

---

## 5. Reglas de Refactor

Un refactor está autorizado cuando:
- No cambia el comportamiento observable externamente.
- Tiene cobertura de tests previa que lo respalda.
- Está acotado a la zona de propiedad del agente que lo realiza.
- Ha sido aprobado por el Director si afecta interfaces entre capas.

**Está prohibido:**
- Refactorizar y añadir funcionalidad en el mismo commit.
- Renombrar interfaces públicas sin actualizar todos los consumidores.
- Mover archivos entre capas sin aprobación del Director.
- Refactorizar código sin tests existentes como pretexto para "limpiar".

**Proceso mínimo:**
1. Ejecutar tests antes del refactor → deben pasar.
2. Aplicar el refactor.
3. Ejecutar tests después → deben pasar.
4. Commit separado con tipo `refactor`.

---

## 6. Checklist antes de Merge

El agente que entrega una tarea debe verificar cada punto:

### Corrección
- [ ] El código compila y arranca sin excepciones.
- [ ] Los tests pasan: `pytest tests/` sin errores.
- [ ] `ruff check .` sin errores.
- [ ] `mypy src/` sin errores en módulos nuevos o modificados.
- [ ] `black --check .` sin diferencias.

### Arquitectura
- [ ] El código está en la capa correcta según `SKILLS.md §3`.
- [ ] No hay dependencias prohibidas (matriz `SKILLS.md §11`).
- [ ] No hay imports circulares.
- [ ] No se introdujeron dependencias externas nuevas sin aprobación.

### Comportamiento
- [ ] El caso de uso tiene test de camino feliz.
- [ ] Los errores esperables tienen test.
- [ ] Los jobs se persisten antes de ejecutarse.
- [ ] La UI no se bloquea en operaciones largas.

### Persistencia
- [ ] Cambios de esquema tienen migración Alembic.
- [ ] Las escrituras están en transacciones.
- [ ] No hay SQL manual fuera de repositorios.

### Calidad
- [ ] Comentarios en español.
- [ ] Nombres de variables y funciones en inglés.
- [ ] No hay `print()` de diagnóstico.
- [ ] No hay `except Exception` silencioso.
- [ ] No hay credenciales, rutas locales ni datos personales en el código.

### Documentación
- [ ] `CONTEXT_PACK.md` sigue siendo coherente con el cambio.
- [ ] Si se tomó una decisión arquitectónica nueva, existe su ADR.
- [ ] `README.md` actualizado si cambian instrucciones de arranque.

---

## 7. Matriz de Propiedad de Archivos

| Ruta | Agente propietario | Puede leer |
|------|--------------------|------------|
| `src/adaptador/domain/` | Backend | Todos |
| `src/adaptador/services/` | Backend | Todos |
| `src/adaptador/ui/` | Frontend/UI | Todos |
| `src/adaptador/db/` | Persistence | Backend, QA |
| `src/adaptador/backup/` | Persistence | QA, Infra Local |
| `src/adaptador/ai/` | IA Integrations | Backend, Workers, QA |
| `src/adaptador/jobs/` | Backend + IA Integrations | Todos |
| `tests/` | QA | Todos |
| `alembic/` | Persistence | QA, Infra Local |
| `config/` | Infra Local | Todos |
| `config/prompts.yaml` | IA Integrations | Backend |
| `scripts/` | Infra Local | Todos |
| `docs/` | Documentation + Director | Todos |
| `pyproject.toml` | Infra Local | Todos |

> Un agente puede **leer** cualquier archivo fuera de su zona. Solo puede **modificar** los de su zona o con aprobación explícita del Director.

---

## 8. Flujo de Trabajo Estándar

```
Usuario describe tarea
        │
        ▼
  DIRECTOR descompone
  y asigna a agente
        │
        ▼
  Agente lee CONTEXT_PACK + SKILLS
  Confirma archivos a modificar
        │
        ▼
  Agente implementa
  (solo en su zona de propiedad)
        │
        ▼
  QA valida:
  pytest + ruff + mypy + black
        │
        ├─► Issues bloqueantes → agente corrige
        │
        └─► Checklist completo → merge autorizado
                │
                ▼
        Documentation actualiza docs si aplica
```

---

*Este documento es normativo. Cualquier modificación debe ser aprobada por el Director y versionada en `docs/`.*
