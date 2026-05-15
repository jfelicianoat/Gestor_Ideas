"""
Entidades de dominio del Gestor de Ideas.

Clases puras que representan los conceptos centrales del sistema.
No dependen de SQLModel, PySide6 ni ninguna infraestructura.
Los métodos de mutación de estado delegan la validación a
transitions.py para mantener las reglas centralizadas.

Referencia: CONTEXT_PACK.md §6
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from adaptador.domain.enums import (
    EstadoJob,
    EstadoKanban,
    TipoEntrada,
    TipoJob,
)
from adaptador.domain.transitions import (
    validate_job_transition,
    validate_kanban_transition,
)


def _now() -> datetime:
    """Genera un timestamp UTC actual."""
    return datetime.now(UTC)


@dataclass
class Idea:
    """
    Unidad central del sistema — representa una entrada del usuario
    en cualquier formato (texto, audio, PDF, Markdown).
    """

    # Identificador único de la idea
    id: UUID = field(default_factory=uuid4)
    # Título generado o ingresado por el usuario
    titulo: str = ""
    # Texto tal como fue ingresado o transcrito
    contenido_raw: str = ""
    # Resultado del procesamiento IA (None si no procesada aún)
    contenido_enriquecido: str | None = None
    # Tipo de fuente de la idea
    tipo_entrada: TipoEntrada = TipoEntrada.TEXTO
    # Estado actual en el tablero Kanban
    estado_kanban: EstadoKanban = EstadoKanban.NUEVA
    # Ruta al archivo original adjunto (None si entrada por texto)
    archivo_adjunto: str | None = None
    # Timestamps
    fecha_creacion: datetime = field(default_factory=_now)
    fecha_modificacion: datetime = field(default_factory=_now)

    def cambiar_estado(self, nuevo_estado: EstadoKanban) -> None:
        """
        Cambia el estado Kanban de la idea, validando la transición.

        Args:
            nuevo_estado: Estado destino deseado.

        Raises:
            InvalidStateTransitionError: Si la transición no es válida.
        """
        validate_kanban_transition(self.estado_kanban, nuevo_estado)
        self.estado_kanban = nuevo_estado
        self.fecha_modificacion = _now()


@dataclass
class Job:
    """
    Tarea de procesamiento IA asociada a una Idea.

    Los jobs se persisten en cola antes de ejecutarse y soportan
    reintentos con backoff en caso de fallo.
    """

    # FK a la idea que originó el job (obligatorio — sin default)
    idea_id: UUID
    # Identificador único del job
    id: UUID = field(default_factory=uuid4)
    # Tipo de procesamiento IA
    tipo_job: TipoJob = TipoJob.ENRIQUECIMIENTO
    # Estado actual del job
    estado: EstadoJob = EstadoJob.PENDIENTE
    # Número de intentos realizados
    intentos: int = 0
    # Límite máximo de reintentos
    max_intentos: int = 3
    # Parámetros del job (prompt, modelo, opciones)
    payload: dict[str, Any] = field(default_factory=dict)
    # Resultado del LLM o descripción del error
    resultado: str | None = None
    # Timestamps
    fecha_creado: datetime = field(default_factory=_now)
    fecha_actualizado: datetime = field(default_factory=_now)
    # Timeout máximo por intento en segundos
    timeout_segundos: int = 120

    def cambiar_estado(self, nuevo_estado: EstadoJob) -> None:
        """
        Cambia el estado del job, validando la transición.

        Args:
            nuevo_estado: Estado destino deseado.

        Raises:
            InvalidStateTransitionError: Si la transición no es válida.
        """
        validate_job_transition(self.estado, nuevo_estado)
        self.estado = nuevo_estado
        self.fecha_actualizado = _now()

    def registrar_intento(self) -> None:
        """Incrementa el contador de intentos y actualiza timestamp."""
        self.intentos += 1
        self.fecha_actualizado = _now()

    def puede_reintentar(self) -> bool:
        """Indica si el job no ha agotado sus reintentos."""
        return self.intentos < self.max_intentos


@dataclass
class BackupRegistro:
    """
    Registro de un backup automático realizado.

    Almacena metadatos del backup para control de retención
    y restauración.
    """

    # Identificador autonumérico (asignado por persistencia)
    id: int | None = None
    # Ruta completa al archivo de backup
    ruta_archivo: str = ""
    # Timestamp del momento del backup
    fecha_backup: datetime = field(default_factory=_now)
    # Tamaño del archivo en bytes
    tamano_bytes: int = 0
