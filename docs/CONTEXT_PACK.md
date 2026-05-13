# CONTEXT_PACK — Gestor de Ideas

> **Versión:** 0.1.0  
> **Fecha:** 2026-05-13  
> **Estado:** Borrador inicial — pre-MVP  
> **Repositorio:** https://github.com/jfelicianoat/Gestor_Ideas  
> **Audiencia:** Desarrollador único + LLM asistente

---

## 1. Visión del Producto

**Adaptador de Ideas** es una aplicación desktop personal que actúa como puente entre la captura desestructurada de ideas (texto libre, audio, documentos) y su transformación en conocimiento procesable mediante IA local.

El usuario captura una idea en cualquier formato; el sistema la transcribe, enriquece y organiza automáticamente, sin dependencias de servicios en la nube. Todo el procesamiento ocurre en la máquina local o en la red de área local (LAN).

---

## 2. Objetivos

| # | Objetivo | Criterio de éxito |
|---|----------|-------------------|
| O1 | Captura de ideas sin fricción desde múltiples fuentes | El usuario puede ingresar texto, grabar audio, adjuntar MP3, PDF o Markdown en menos de 3 clics |
| O2 | Transcripción local de audio sin API externa | Audio → texto usando `faster-whisper` en la misma máquina |
| O3 | Enriquecimiento IA mediante Ollama en LAN | Cada idea puede ser procesada por un modelo LLM sin salir de la red privada |
| O4 | Organización visual del flujo de trabajo | Tablero Kanban que refleja el estado de cada idea a lo largo del pipeline |
| O5 | Persistencia confiable y recuperable | SQLite + backups automáticos versionados; sin pérdida de datos ante crash |
| O6 | Resiliencia de jobs IA | Cola persistente con reintentos y timeouts; sin pérdida de trabajos por fallos transitorios |

---

## 3. Alcance MVP

### ✅ Dentro del alcance (MVP)

- Entrada de ideas vía:
  - Texto libre (campo de texto)
  - Grabación de audio en tiempo real
  - Archivo MP3 adjunto
  - Archivo PDF adjunto
  - Archivo Markdown adjunto
- Transcripción de audio con `faster-whisper` (local)
- Extracción de texto plano de PDF y Markdown
- Envío de ideas al pipeline IA (Ollama en LAN)
- Tablero Kanban con columnas: `Nueva → En proceso → Revisión → Archivada`
- Sistema de jobs IA:
  - Cola persistente en SQLite
  - Reintentos automáticos con backoff
  - Timeout configurable por job
- Repositorio intermedio de trabajos (staging area antes de archivar)
- UI desktop con PySide6 (tema soft-dark)
- Persistencia con SQLite + SQLModel
- Backups automáticos versionados en directorio local
- Operación single-user, sin autenticación

### ❌ Fuera del alcance (MVP)

- Sincronización en la nube o multi-dispositivo
- Soporte multi-usuario
- Integración con APIs externas de IA (OpenAI, Anthropic, etc.)
- Aplicación web o móvil
- OCR de imágenes dentro de PDFs (escaneados)
- Exportación a formatos externos (Notion, Obsidian, etc.)
- Soporte de video como fuente de entrada

---

## 4. Restricciones

| Restricción | Detalle |
|-------------|---------|
| **Sin nube** | Todo el procesamiento ocurre en la máquina local o en la LAN. No se envía información a servidores externos. |
| **Single-user** | No hay gestión de sesiones, roles ni permisos. |
| **LLM vía Ollama** | El modelo IA está disponible en la LAN. La app debe tolerar que Ollama no esté disponible temporalmente. |
| **Python** | El backend y la lógica de negocio se implementan íntegramente en Python. |
| **PySide6** | La UI es exclusivamente desktop; no existe interfaz web. |
| **SQLite** | Base de datos embebida; no se requiere servidor de base de datos. |
| **`faster-whisper`** | Única librería autorizada para transcripción de audio. |
| **Sin dependencias críticas externas** | La app debe poder operar en modo degradado si Ollama no responde (captura funciona, IA en cola). |

---

## 5. Decisiones Arquitectónicas

### DA-01 — Monolito Modular

**Decisión:** Arquitectura monolítica con módulos internos bien delimitados.  
**Razón:** El contexto es single-user desktop. La complejidad de microservicios no está justificada. Los módulos se definen como paquetes Python con interfaces claras.  
**Consecuencia:** El acoplamiento es aceptable dentro del proceso; los cambios de un módulo pueden afectar a otros si se rompen las interfaces.

### DA-02 — SQLite + SQLModel como capa de persistencia

**Decisión:** Una única base de datos SQLite gestionada mediante SQLModel (ORM sobre SQLAlchemy).  
**Razón:** Sin infraestructura de servidor, fácil portabilidad, soporte nativo de Python. SQLModel provee tipado estático con Pydantic.  
**Consecuencia:** No apto para concurrencia de escritura intensiva; aceptable para single-user.

### DA-03 — Cola de jobs IA persistente

**Decisión:** Los jobs de IA se persisten en SQLite antes de enviarse a Ollama.  
**Razón:** Ollama puede no estar disponible. Los jobs no deben perderse entre reinicios de la app.  
**Consecuencia:** Requiere un worker de fondo (hilo o proceso) que drene la cola.

### DA-04 — Transcripción local con `faster-whisper`

**Decisión:** Audio (grabado o adjunto MP3) se transcribe localmente usando `faster-whisper`.  
**Razón:** Privacidad de datos y operación sin conexión a internet.  
**Consecuencia:** Requiere descarga del modelo Whisper en la primera ejecución; consumo de CPU/GPU local.

### DA-05 — Ollama remoto en LAN

**Decisión:** El LLM se accede vía HTTP a una instancia de Ollama en la red local.  
**Razón:** Permite usar hardware dedicado (ej. máquina con GPU) sin instalar Ollama en la máquina del usuario.  
**Consecuencia:** La app debe gestionar errores de red y reintentos. La URL de Ollama es configurable.

### DA-06 — PySide6 como framework de UI

**Decisión:** La interfaz de usuario se construye con PySide6 (Qt para Python).  
**Razón:** UI nativa, rica en componentes, con soporte de hilos (QThread) para no bloquear la UI durante operaciones largas.  
**Consecuencia:** Distribución requiere incluir librerías Qt. Mayor tamaño de instalación respecto a alternativas ligeras.

### DA-07 — Backups versionados automáticos

**Decisión:** La base de datos se copia automáticamente en un directorio de backups con timestamp.  
**Razón:** Proteger contra corrupción de SQLite o errores del usuario.  
**Consecuencia:** El directorio de backups debe ser monitoreado para no crecer indefinidamente (política de retención a definir).

---

## 6. Entidades Principales

### `Idea`
Unidad central del sistema. Representa una entrada del usuario en cualquier formato.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único |
| `titulo` | str | Título generado o ingresado por el usuario |
| `contenido_raw` | str | Texto tal como fue ingresado o transcrito |
| `contenido_enriquecido` | str \| None | Resultado del procesamiento IA |
| `tipo_entrada` | Enum | `texto`, `audio_grabado`, `mp3`, `pdf`, `markdown` |
| `estado_kanban` | Enum | `nueva`, `en_proceso`, `revision`, `archivada` |
| `archivo_adjunto` | str \| None | Ruta al archivo original |
| `fecha_creacion` | datetime | Timestamp de creación |
| `fecha_modificacion` | datetime | Timestamp de última modificación |

### `Job`
Representa una tarea de procesamiento IA asociada a una `Idea`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único |
| `idea_id` | UUID | FK a `Idea` |
| `tipo_job` | Enum | `transcripcion`, `enriquecimiento`, `resumen`, etc. |
| `estado` | Enum | `pendiente`, `en_curso`, `completado`, `fallido`, `cancelado` |
| `intentos` | int | Número de intentos realizados |
| `max_intentos` | int | Límite de reintentos configurado |
| `payload` | JSON | Parámetros del job (prompt, modelo, opciones) |
| `resultado` | str \| None | Respuesta del LLM o error descriptivo |
| `fecha_creado` | datetime | Timestamp de creación |
| `fecha_actualizado` | datetime | Timestamp de última actualización |
| `timeout_segundos` | int | Timeout máximo por intento |

### `BackupRegistro`
Registro de cada backup automático realizado.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | Autonumérico |
| `ruta_archivo` | str | Ruta completa del archivo de backup |
| `fecha_backup` | datetime | Timestamp del backup |
| `tamano_bytes` | int | Tamaño del archivo |

---

## 7. Riesgos

| ID | Riesgo | Probabilidad | Impacto | Mitigación |
|----|--------|-------------|---------|------------|
| R1 | Ollama no disponible en LAN | Media | Alto | Jobs persisten en cola; la app opera en modo captura. Notificación visual al usuario. |
| R2 | Transcripción lenta en hardware sin GPU | Alta | Medio | Usar modelo Whisper `tiny` o `base` por defecto; permitir selección de modelo. |
| R3 | Corrupción de SQLite | Baja | Alto | WAL mode activado; backups automáticos antes de operaciones masivas. |
| R4 | Bloqueo de UI durante operaciones largas | Alta | Medio | Usar `QThread` o `QRunnable` para transcripción y llamadas a Ollama. |
| R5 | Crecimiento ilimitado de backups | Media | Bajo | Implementar política de retención (N últimos backups o por antigüedad). |
| R6 | Modelos Whisper no descargados | Media | Alto | Verificación en arranque; wizard de primera ejecución o descarga automática. |
| R7 | Cambios de API de Ollama | Baja | Medio | Encapsular llamadas a Ollama en un adaptador; tests de integración contra instancia local. |

---

## 8. Roadmap Iterativo

### Iteración 0 — Esqueleto (Semana 1-2)
- [ ] Estructura de carpetas del proyecto
- [ ] Configuración de entorno (`pyproject.toml` / `requirements.txt`)
- [ ] Esquema de base de datos (`Idea`, `Job`, `BackupRegistro`) con SQLModel
- [ ] Migraciones iniciales
- [ ] Tests unitarios del modelo de datos
- [ ] Script de arranque básico

### Iteración 1 — Captura de texto (Semana 3-4)
- [ ] UI principal con PySide6 (ventana principal, layout base, tema soft-dark)
- [ ] Formulario de entrada de texto libre
- [ ] Persistencia de `Idea` vía texto
- [ ] Tablero Kanban básico (columnas, tarjetas)
- [ ] Mover ideas entre columnas manualmente

### Iteración 2 — Audio y transcripción (Semana 5-6)
- [ ] Grabación de audio en tiempo real desde la UI
- [ ] Adjuntar archivo MP3
- [ ] Integración con `faster-whisper`
- [ ] Pipeline: audio → texto → `Idea`
- [ ] Indicador de progreso de transcripción (no bloquea UI)

### Iteración 3 — Documentos (Semana 7-8)
- [ ] Adjuntar y parsear PDF (extracción de texto plano)
- [ ] Adjuntar y leer archivo Markdown
- [ ] Pipeline: documento → texto → `Idea`

### Iteración 4 — Jobs IA (Semana 9-10)
- [ ] Worker de cola de jobs (hilo de fondo)
- [ ] Integración con Ollama (HTTP client configurable)
- [ ] Retry con backoff exponencial
- [ ] Timeout por job
- [ ] Visualización del estado del job en la tarjeta Kanban
- [ ] Repositorio intermedio de trabajos (staging antes de archivar)

### Iteración 5 — Persistencia avanzada y backups (Semana 11-12)
- [ ] Backups automáticos versionados en cada arranque
- [ ] Política de retención de backups
- [ ] Exportación de una idea como Markdown
- [ ] Restauración manual de backup (UI)

### Iteración 6 — Pulido MVP (Semana 13-14)
- [ ] Búsqueda de ideas por texto
- [ ] Filtros en el Kanban (por estado, por tipo de entrada, por fecha)
- [ ] Configuración de la app (URL Ollama, modelo Whisper, directorio de backups)
- [ ] Tests de integración end-to-end
- [ ] Documentación de usuario básica

---

## 9. Definición de Done (DoD)

Una funcionalidad se considera **Done** cuando cumple todos los criterios siguientes:

1. **Funciona**: El caso de uso principal ejecuta sin errores en la máquina de desarrollo.
2. **Persiste**: Los datos relevantes se guardan en SQLite y sobreviven un reinicio de la app.
3. **No bloquea la UI**: Las operaciones lentas (transcripción, IA) ocurren en un hilo separado.
4. **Tiene test**: Al menos un test de smoke o unitario cubre el camino feliz.
5. **Código comentado en español**: El código fuente está comentado siguiendo la convención del proyecto.
6. **Sin regresión**: Los tests existentes siguen pasando.
7. **Maneja errores**: Los fallos esperables (Ollama caído, archivo no encontrado) muestran un mensaje claro al usuario.

---

## 10. Estrategia IA

### Modelo de interacción

La app no llama directamente a Ollama desde la UI. Toda solicitud IA pasa por el sistema de jobs:

```
Idea creada/modificada
      │
      ▼
   Job creado (estado: pendiente)
   [persistido en SQLite]
      │
      ▼
   Worker de cola (hilo de fondo)
   polls cada N segundos
      │
      ├─► Ollama disponible → envía request HTTP
      │         │
      │         ├─► Éxito → resultado guardado en Job + Idea actualizada
      │         └─► Error/Timeout → incrementa intentos; si max_intentos → estado: fallido
      │
      └─► Ollama no disponible → espera backoff; reintenta
```

### Prompts

- Los prompts se definen en archivos de configuración (YAML o TOML), **no hardcodeados** en el código.
- Cada tipo de job tiene su plantilla de prompt parametrizable.
- El modelo de Ollama a usar es configurable por tipo de job.

### Tipos de job IA (MVP)

| Tipo | Entrada | Salida |
|------|---------|--------|
| `enriquecimiento` | Texto de la idea | Versión mejorada/estructurada |
| `resumen` | Texto largo (PDF, Markdown) | Resumen ejecutivo |
| `etiquetas` | Texto de la idea | Lista de tags relevantes |

### Modo degradado

Si Ollama no está disponible:
- La app **captura y persiste** ideas con normalidad.
- Los jobs quedan en estado `pendiente` hasta que Ollama esté disponible.
- La UI muestra un indicador de estado de conexión con Ollama.
- El worker reintenta automáticamente al reconectar.

---

## 11. Convenciones Técnicas

### Estructura de carpetas

```
adaptador-de-ideas/
├── docs/                    # Documentación del proyecto
│   └── CONTEXT_PACK.md
├── config/                  # Configuración (YAML/TOML)
│   ├── app.yaml             # Parámetros de la app
│   └── prompts.yaml         # Plantillas de prompts IA
├── src/
│   └── adaptador/           # Paquete principal
│       ├── __init__.py
│       ├── main.py          # Punto de entrada
│       ├── db/              # Capa de persistencia
│       │   ├── models.py    # Entidades SQLModel
│       │   ├── engine.py    # Configuración SQLite
│       │   └── migrations.py
│       ├── ui/              # Capa de interfaz de usuario (PySide6)
│       │   ├── main_window.py
│       │   ├── kanban/
│       │   └── widgets/
│       ├── jobs/            # Sistema de jobs IA
│       │   ├── worker.py    # Hilo de cola de jobs
│       │   ├── queue.py     # Gestión de la cola persistente
│       │   └── ollama_client.py
│       ├── ingestion/       # Pipeline de entrada de ideas
│       │   ├── audio.py     # Grabación + transcripción
│       │   ├── pdf.py       # Extracción de texto de PDF
│       │   └── markdown.py  # Lectura de archivos Markdown
│       └── backup/          # Sistema de backups
│           └── manager.py
├── tests/                   # Tests automatizados
│   ├── unit/
│   └── integration/
├── scripts/                 # Scripts utilitarios
│   ├── run_local.sh         # Arranque en desarrollo
│   └── setup_env.sh         # Configuración de entorno
├── pyproject.toml           # Metadatos y dependencias del proyecto
└── README.md
```

### Convenciones de código

| Aspecto | Convención |
|---------|------------|
| **Idioma del código** | Inglés para nombres de variables, funciones y clases |
| **Comentarios** | Español (regla de proyecto) |
| **Tipado** | Type hints en todas las funciones públicas |
| **Formato** | `black` con ancho 88 |
| **Linting** | `ruff` |
| **Tests** | `pytest` |
| **ORM** | `SQLModel` (nunca SQL raw salvo migraciones) |
| **Configuración** | Archivos YAML en `config/`; nunca hardcoded |
| **Logging** | `logging` estándar de Python; niveles: DEBUG, INFO, WARNING, ERROR |
| **Manejo de errores** | Excepciones tipadas; nunca `except Exception` silencioso |

### Dependencias clave (MVP)

| Librería | Propósito |
|----------|-----------|
| `PySide6` | UI desktop |
| `SQLModel` | ORM + validación |
| `faster-whisper` | Transcripción de audio local |
| `httpx` | Cliente HTTP para Ollama (async-compatible) |
| `pydub` | Manipulación de audio (MP3) |
| `pypdf` | Extracción de texto de PDF |
| `pyyaml` | Lectura de configuración YAML |
| `pytest` | Tests |
| `black` | Formateo de código |
| `ruff` | Linting |

### Gestión de configuración

La URL de Ollama, el modelo Whisper a usar, los timeouts, los límites de reintentos y el directorio de backups se configuran en `config/app.yaml`. La app carga esta configuración al arrancar y la expone como un objeto Pydantic validado.

---

## 12. Glosario

| Término | Definición |
|---------|------------|
| **Idea** | Unidad de información capturada por el usuario, en cualquier formato |
| **Job** | Tarea de procesamiento IA asociada a una Idea |
| **Pipeline** | Secuencia de pasos para transformar una entrada en una Idea procesada |
| **Ollama** | Servidor de modelos LLM que corre en la LAN |
| **Kanban** | Tablero de columnas para visualizar el estado de cada Idea |
| **Staging / Repositorio intermedio** | Área temporal donde las Ideas son revisadas antes de archivarse |
| **Worker** | Hilo de fondo que drena la cola de jobs IA |
| **faster-whisper** | Implementación optimizada de Whisper para transcripción local |
| **Modo degradado** | Operación de la app cuando Ollama no está disponible |
| **DoD** | Definition of Done — criterios que debe cumplir una funcionalidad para considerarse completa |

---

*Este documento es la fuente de verdad para el alcance y las decisiones del proyecto durante el MVP. Cualquier funcionalidad no descrita aquí debe ser discutida y añadida explícitamente antes de implementarse.*
