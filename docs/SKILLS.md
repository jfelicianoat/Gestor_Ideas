# SKILLS - Estándares técnicos por capa

> **Proyecto:** Gestor de Ideas  
> **Versión:** 0.1.0  
> **Estado:** Borrador técnico pre-MVP  
> **Repositorio:** https://github.com/jfelicianoat/Gestor_Ideas  
> **Audiencia:** Desarrollador único + LLM asistente  

---

## 1. Propósito

Este documento define las tecnologías, responsabilidades y estándares técnicos de cada capa del sistema. Su objetivo es mantener una arquitectura modular, testeable y mantenible para una aplicación desktop local construida con Python, PySide6, SQLite e integraciones de IA en red local.

Las reglas descritas aquí son normativas: cualquier módulo nuevo debe ubicarse en una capa clara, depender solo de las capas permitidas y seguir las convenciones de errores, logging, asincronía, UI y persistencia.

---

## 2. Stack autorizado

| Área | Tecnología |
|---|---|
| Lenguaje | Python |
| UI desktop | PySide6 |
| Persistencia | SQLite, SQLModel |
| Migraciones | Alembic |
| Concurrencia | asyncio |
| IA local/LAN | Ollama HTTP API, faster-whisper |
| Logging | Loguru |
| Empaquetado | PyInstaller |
| Testing | pytest |
| Calidad | ruff, mypy, black |

No se deben introducir frameworks, ORMs, sistemas de logging, gestores de tareas o clientes IA alternativos sin una decisión arquitectónica explícita.

---

## 3. Capas

### 3.1 frontend/ui

**Propósito:** Proveer la experiencia desktop, renderizar estado, capturar acciones del usuario y coordinar la interacción con casos de uso sin contener lógica de negocio.

**Librerías permitidas:**

- `PySide6`
- Tipos estándar de Python
- Adaptadores o view models definidos por la aplicación
- `asyncio` solo a través de utilidades aprobadas para integración Qt/event loop
- `Loguru` solo para eventos de UI relevantes, no para trazas ruidosas de renderizado

**Responsabilidades:**

- Construir ventanas, paneles, formularios, diálogos y componentes visuales.
- Validar entradas de usuario a nivel de formato inmediato.
- Mostrar estados de carga, éxito, error y modo degradado.
- Despachar comandos hacia servicios o casos de uso.
- Mantener la UI responsiva durante operaciones largas.
- Traducir errores de aplicación a mensajes comprensibles para el usuario.

**Anti-patterns:**

- Consultar SQLite directamente desde widgets.
- Ejecutar llamadas HTTP, transcripción o jobs IA en el hilo principal.
- Incluir reglas de dominio dentro de slots, callbacks o componentes visuales.
- Usar estado global mutable para compartir datos entre pantallas.
- Bloquear la UI con `time.sleep`, I/O síncrono pesado o bucles largos.

**Convenciones de código:**

- Los widgets deben ser pequeños y componibles.
- Los nombres de clases UI terminan en `View`, `Dialog`, `Panel`, `Widget` o `Window`.
- La comunicación desde UI hacia lógica de aplicación debe pasar por servicios, controladores o view models.
- Los slots deben delegar rápido; si una acción tarda, debe programarse fuera del hilo principal.
- Los textos visibles deben estar centralizados cuando sean reutilizables.

---

### 3.2 domain

**Propósito:** Representar el núcleo del negocio: entidades, value objects, reglas, estados y contratos independientes de infraestructura.

**Librerías permitidas:**

- Python estándar
- `typing`
- `dataclasses` cuando aplique
- Tipos propios del dominio

**Responsabilidades:**

- Definir entidades como idea, adjunto, transcripción, job, estado de pipeline y backup.
- Encapsular invariantes de negocio.
- Definir value objects para identificadores, estados, rutas validadas y configuraciones.
- Exponer interfaces o protocolos para repositorios y servicios externos.
- Mantener reglas independientes de UI, base de datos, HTTP y frameworks.

**Anti-patterns:**

- Importar `PySide6`, `SQLModel`, clientes HTTP, `Loguru` o detalles de Ollama.
- Usar modelos ORM como entidades de dominio.
- Convertir el dominio en una colección de diccionarios sin invariantes.
- Lanzar excepciones genéricas sin contexto.
- Mezclar validaciones visuales con reglas de negocio.

**Convenciones de código:**

- El dominio debe ser testeable sin base de datos, red ni UI.
- Las reglas de transición de estado deben estar centralizadas.
- Las excepciones de dominio deben heredar de una base común, por ejemplo `DomainError`.
- Los contratos deben definirse con `Protocol` cuando ayuden a invertir dependencias.

---

### 3.3 services

**Propósito:** Orquestar casos de uso de aplicación conectando dominio, persistencia, workers e integraciones externas.

**Librerías permitidas:**

- Python estándar
- `asyncio`
- Tipos del dominio
- Interfaces de repositorios
- Clientes de infraestructura a través de abstracciones
- `Loguru`

**Responsabilidades:**

- Implementar casos de uso como crear idea, adjuntar archivo, solicitar transcripción, enviar a IA, archivar y restaurar.
- Coordinar transacciones de persistencia.
- Aplicar políticas de reintento, timeout y modo degradado.
- Convertir errores técnicos en errores de aplicación.
- Emitir eventos o resultados consumibles por UI y workers.

**Anti-patterns:**

- Incluir lógica de presentación.
- Construir SQL manual salvo casos justificados y encapsulados.
- Depender de widgets, señales Qt o clases visuales.
- Ocultar fallos silenciosamente.
- Hacer que un servicio conozca detalles internos de varias infraestructuras no relacionadas.

**Convenciones de código:**

- Los servicios deben tener nombres orientados a caso de uso, por ejemplo `IdeaService`, `TranscriptionService` o `JobService`.
- Los métodos públicos deben devolver resultados tipados o lanzar errores de aplicación conocidos.
- Las dependencias se reciben por constructor.
- Los servicios no deben crear conexiones globales ni clientes externos de forma implícita.

---

### 3.4 workers

**Propósito:** Ejecutar trabajo de fondo, especialmente tareas largas o recuperables: transcripción, enriquecimiento IA, reintentos y mantenimiento.

**Librerías permitidas:**

- `asyncio`
- Python estándar
- `Loguru`
- Servicios de aplicación
- Adaptadores de infraestructura necesarios
- PySide6 solo para integración controlada con señales/hilos, no para lógica de worker

**Responsabilidades:**

- Drenar colas persistentes de jobs.
- Ejecutar transcripciones con `faster-whisper`.
- Invocar Ollama mediante servicios o clientes dedicados.
- Aplicar backoff, timeout, cancelación y reintentos.
- Persistir progreso y resultado de cada job.
- Notificar estado a la UI sin acoplarse a widgets.

**Anti-patterns:**

- Procesar jobs solo en memoria sin persistencia.
- Perder jobs ante cierre inesperado.
- Hacer busy-waiting.
- Capturar excepciones y continuar sin registrar ni actualizar estado.
- Ejecutar trabajo CPU/I/O intensivo en el hilo principal de Qt.

**Convenciones de código:**

- Cada worker debe tener ciclo de vida explícito: `start`, `stop`, `cancel` o equivalentes.
- Los jobs deben ser idempotentes cuando sea razonable.
- Los estados de job deben ser persistidos antes y después de cada fase relevante.
- Los timeouts deben ser configurables.

---

### 3.5 persistence

**Propósito:** Gestionar almacenamiento local confiable, migraciones, transacciones y recuperación de datos.

**Librerías permitidas:**

- `SQLModel`
- `SQLite`
- `Alembic`
- Python estándar
- Tipos de dominio para mapeo
- `Loguru` para eventos de persistencia relevantes

**Responsabilidades:**

- Definir modelos de base de datos.
- Implementar repositorios.
- Gestionar sesiones y transacciones.
- Aplicar migraciones con Alembic.
- Mantener integridad referencial e índices necesarios.
- Mapear entre modelos SQLModel y entidades/value objects del dominio.

**Anti-patterns:**

- Exponer sesiones SQLAlchemy/SQLModel a UI.
- Usar modelos ORM como DTO universal de toda la aplicación.
- Crear tablas manualmente fuera de migraciones, salvo bootstrap controlado.
- Guardar blobs grandes si una ruta versionada es suficiente.
- Construir consultas SQL dispersas por servicios o widgets.

**Convenciones de código:**

- Cada agregado o entidad persistente debe tener un repositorio claro.
- Las operaciones de escritura deben ser transaccionales.
- Los modelos SQLModel pertenecen a infraestructura, no al dominio.
- Las migraciones deben ser revisables, pequeñas y reversibles cuando sea posible.
- SQLite debe usarse con pragmas adecuados para confiabilidad, como WAL cuando aplique.

---

### 3.6 ai integrations

**Propósito:** Encapsular interacción con IA local o LAN: Ollama HTTP API y transcripción con `faster-whisper`.

**Librerías permitidas:**

- Cliente HTTP estándar o dependencia aprobada por el proyecto
- `asyncio`
- `faster-whisper`
- Tipos del dominio y DTOs propios
- `Loguru`

**Responsabilidades:**

- Construir requests hacia Ollama.
- Parsear respuestas de modelos LLM.
- Gestionar timeouts, errores de red y respuestas inválidas.
- Ejecutar transcripción local de audio.
- Exponer interfaces estables para servicios y workers.
- Mantener prompts, plantillas y parámetros de modelo versionables.

**Anti-patterns:**

- Llamar a Ollama directamente desde UI.
- Hacer prompts embebidos y duplicados en múltiples módulos.
- Asumir disponibilidad permanente de Ollama.
- Persistir respuestas IA sin metadatos de modelo, fecha y parámetros relevantes.
- Mezclar transcripción, enriquecimiento y persistencia en una sola función larga.

**Convenciones de código:**

- Los clientes IA deben tener contratos explícitos de entrada y salida.
- Toda llamada externa debe tener timeout.
- Los errores deben distinguir red, timeout, respuesta inválida y modelo no disponible.
- Los prompts deben tratarse como artefactos versionables.

---

### 3.7 testing

**Propósito:** Garantizar que reglas de negocio, persistencia, workers e integraciones se comportan de forma predecible.

**Librerías permitidas:**

- `pytest`
- Utilidades estándar de Python
- Fixtures locales
- Dobles de prueba propios
- Herramientas de calidad: `ruff`, `mypy`, `black`

**Responsabilidades:**

- Cubrir reglas de dominio con tests unitarios rápidos.
- Probar repositorios con SQLite temporal.
- Probar servicios con repositorios fake o mocks explícitos.
- Probar workers con colas pequeñas, timeouts controlados y clientes IA fake.
- Validar migraciones críticas.
- Mantener fixtures legibles y específicas.

**Anti-patterns:**

- Tests que dependen de Ollama real por defecto.
- Tests frágiles basados en orden temporal no controlado.
- Fixtures globales con estado compartido mutable.
- Ignorar errores de typing o lint en CI/local.
- Usar tests de UI para cubrir lógica que pertenece al dominio.

**Convenciones de código:**

- Los tests deben nombrar comportamiento: `test_creates_job_when_idea_requires_ai_processing`.
- Los tests unitarios no deben tocar red ni disco salvo directorios temporales.
- Las pruebas de integración deben estar separadas y marcadas.
- Cada bug corregido en dominio, servicios o persistencia debe incorporar una prueba.

---

### 3.8 backups

**Propósito:** Proteger la base de datos y archivos locales frente a errores, corrupción o pérdida accidental.

**Librerías permitidas:**

- Python estándar
- SQLite backup API cuando aplique
- Servicios de persistencia
- `Loguru`

**Responsabilidades:**

- Crear backups versionados automáticos.
- Validar integridad básica de backups.
- Mantener política de retención configurable.
- Registrar eventos de backup, restauración y fallo.
- Evitar copias inconsistentes durante escrituras activas.

**Anti-patterns:**

- Copiar el archivo SQLite en caliente sin coordinación.
- Sobrescribir el único backup existente.
- Guardar backups en una ruta no configurable.
- Bloquear la UI durante backups.
- Restaurar sin validación previa y sin backup del estado actual.

**Convenciones de código:**

- Los nombres de backup deben incluir fecha y versión.
- Toda restauración debe ser explícita y reversible en lo posible.
- La política de retención debe estar centralizada.
- Los backups deben ejecutarse como tarea de fondo.

---

### 3.9 packaging

**Propósito:** Construir una distribución local instalable/ejecutable que incluya dependencias necesarias sin romper rutas, migraciones o recursos.

**Librerías permitidas:**

- `PyInstaller`
- Python estándar
- Scripts propios de build

**Responsabilidades:**

- Generar ejecutables reproducibles.
- Incluir recursos de PySide6, migraciones Alembic, assets y configuraciones por defecto.
- Separar datos de usuario de archivos de aplicación.
- Documentar pasos de build y verificación.
- Validar arranque limpio en entorno sin dependencias de desarrollo.

**Anti-patterns:**

- Escribir datos de usuario dentro del directorio empaquetado.
- Depender de rutas relativas frágiles.
- Omitir migraciones o recursos necesarios.
- Publicar builds sin prueba de arranque.
- Empaquetar secretos, rutas locales personales o datos de prueba.

**Convenciones de código:**

- Las rutas deben resolverse mediante una utilidad central compatible con modo fuente y modo empaquetado.
- Los scripts de build deben ser repetibles.
- La configuración sensible al entorno debe vivir fuera del binario.
- Cada release debe incluir versión, fecha y notas mínimas de compatibilidad.

---

## 4. Principios SOLID aplicables

| Principio | Regla práctica |
|---|---|
| Single Responsibility | Cada clase debe tener una razón principal para cambiar. Un widget no procesa IA; un repositorio no decide reglas de negocio. |
| Open/Closed | Los nuevos tipos de procesamiento deben añadirse mediante nuevos servicios/adaptadores sin reescribir flujos existentes. |
| Liskov Substitution | Las implementaciones fake, SQLite o reales de una interfaz deben ser intercambiables sin romper servicios. |
| Interface Segregation | Las interfaces deben ser pequeñas: un repositorio de ideas no debe exponer operaciones de jobs, backups o audio. |
| Dependency Inversion | Dominio y servicios dependen de abstracciones; infraestructura implementa esas abstracciones. |

Regla general: las dependencias apuntan hacia el dominio, nunca desde el dominio hacia frameworks o infraestructura.

---

## 5. Reglas async

- Toda operación de red, transcripción, backup o procesamiento largo debe ejecutarse fuera del hilo principal de UI.
- Toda llamada a Ollama debe tener timeout explícito.
- Los workers deben soportar cancelación ordenada.
- No se debe mezclar `asyncio.run()` dentro de código ya ejecutado por un event loop.
- Los límites entre Qt y `asyncio` deben estar encapsulados en adaptadores concretos.
- Los errores en tareas background deben observarse, registrarse y reflejarse en estado persistente.
- Los reintentos deben usar backoff y límite máximo.
- Las tareas periódicas deben evitar busy-waiting; usar sleeps controlados, señales o polling con intervalo configurable.

---

## 6. Reglas UI

- La UI nunca debe bloquearse por I/O, transcripción, IA, backup o migraciones largas.
- La UI muestra estado real: pendiente, en progreso, completado, error, reintentando o modo degradado.
- Los mensajes de error deben ser accionables para el usuario.
- Las pantallas deben delegar lógica a servicios o view models.
- Los widgets no deben conocer modelos ORM.
- Las actualizaciones desde workers hacia UI deben cruzar mediante señales, colas o adaptadores seguros para hilos.
- La validación visual no reemplaza validaciones de dominio.
- El usuario debe poder cerrar la aplicación sin perder jobs persistidos.

---

## 7. Reglas de persistencia

- SQLite es la fuente local de verdad para ideas, jobs, estados y metadatos.
- Toda escritura relevante debe estar dentro de una transacción.
- Los jobs se persisten antes de ejecutarse.
- Las migraciones de esquema se gestionan con Alembic.
- Los repositorios son la única entrada permitida a persistencia desde servicios.
- Las consultas deben ser explícitas, testeables y encapsuladas.
- Los archivos grandes deben almacenarse como archivos gestionados, con metadatos en SQLite, salvo justificación contraria.
- Antes de operaciones destructivas debe existir una ruta de recuperación o backup.

---

## 8. Estrategia de errores

Los errores se clasifican por capa:

| Tipo | Ejemplos | Manejo |
|---|---|---|
| Dominio | Estado inválido, transición no permitida | Excepción de dominio; no requiere logging ruidoso si se muestra al usuario |
| Aplicación | Caso de uso no puede completarse | Error tipado; mensaje accionable; posible recuperación |
| Infraestructura | SQLite, archivo, red, Ollama, Whisper | Logging con contexto; traducción a error de aplicación |
| Worker | Timeout, cancelación, fallo transitorio | Persistir estado, reintentar si aplica, registrar evento |
| UI | Entrada inválida, acción no disponible | Mensaje claro sin stack trace |

Reglas:

- No capturar `Exception` sin registrar o traducir el error.
- No mostrar stack traces al usuario final.
- No perder la causa original; usar encadenamiento de excepciones cuando aporte contexto.
- Los errores recuperables deben distinguirse de los permanentes.
- Los jobs fallidos deben conservar causa, número de intentos y próxima acción.

---

## 9. Estrategia de logging

La aplicación usa `Loguru` como sistema único de logging.

**Niveles:**

- `DEBUG`: diagnóstico local detallado, desactivable en distribución normal.
- `INFO`: eventos relevantes de ciclo de vida, creación de jobs, inicio/fin de workers, backups correctos.
- `WARNING`: degradación recuperable, reintentos, Ollama no disponible temporalmente.
- `ERROR`: fallo de caso de uso, job agotado, error de persistencia recuperado.
- `CRITICAL`: corrupción, fallo irreversible de arranque, imposibilidad de acceder a datos.

**Reglas:**

- Todo log debe incluir contexto útil: identificador de idea/job, operación y causa.
- No registrar contenido sensible completo si puede contener ideas privadas del usuario.
- No usar `print` para diagnóstico de aplicación.
- No duplicar logs en cada capa para el mismo error; registrar donde exista mejor contexto.
- Los workers deben registrar inicio, fin, cancelación, reintento y fallo definitivo.
- Los logs deben rotar o tener política de tamaño cuando se habilite persistencia en archivo.

---

## 10. Convenciones globales de código

- Formato con `black`.
- Lint con `ruff`.
- Tipado con `mypy`.
- Imports ordenados y sin dependencias circulares.
- Funciones pequeñas, nombres explícitos y tipos en firmas públicas.
- Evitar estado global mutable.
- Configuración centralizada y tipada.
- DTOs separados de entidades de dominio y modelos ORM.
- Los módulos deben declarar claramente a qué capa pertenecen por ubicación y dependencias.
- Ningún módulo debe introducir dependencias externas nuevas sin justificación técnica.

---

## 11. Matriz de dependencias permitidas

| Capa | Puede depender de |
|---|---|
| `frontend/ui` | `services`, view models, tipos de aplicación |
| `services` | `domain`, interfaces, repositorios, clientes abstractos |
| `domain` | Python estándar |
| `workers` | `services`, `domain`, adaptadores controlados |
| `persistence` | `domain`, `SQLModel`, `SQLite`, `Alembic` |
| `ai integrations` | `domain`, DTOs, `asyncio`, Ollama HTTP API, `faster-whisper` |
| `testing` | Cualquier capa bajo prueba, dobles controlados |
| `backups` | `persistence`, servicios de aplicación, Python estándar |
| `packaging` | Scripts de build, recursos, configuración |

La dependencia inversa desde `domain` hacia cualquier capa está prohibida.

---

## 12. Criterio de aceptación técnico

Un cambio se considera aceptable cuando:

- Respeta la capa donde se implementa.
- No introduce dependencias prohibidas.
- Mantiene la UI responsiva.
- Persiste jobs antes de ejecutarlos.
- Maneja errores con clasificación clara.
- Registra eventos relevantes sin exponer contenido privado innecesario.
- Incluye tests proporcionales al riesgo.
- Pasa `pytest`, `ruff`, `mypy` y `black --check` cuando el proyecto tenga esos comandos configurados.
