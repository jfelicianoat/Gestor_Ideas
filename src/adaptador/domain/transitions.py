"""
Reglas de transición de estado del dominio.

Define las transiciones válidas para EstadoKanban y EstadoJob
como conjuntos inmutables. La función validate_transition()
es el único punto de validación — las entidades la invocan
antes de cambiar de estado.

Referencia: CONTEXT_PACK.md §6, §10
"""

from adaptador.domain.enums import EstadoJob, EstadoKanban
from adaptador.domain.errors import InvalidStateTransitionError

# --- Transiciones válidas de EstadoKanban ---
# nueva → en_proceso
# en_proceso → revision
# revision → archivada
# revision → en_proceso (retorno para re-trabajo)
KANBAN_TRANSITIONS: dict[EstadoKanban, frozenset[EstadoKanban]] = {
    EstadoKanban.NUEVA: frozenset({EstadoKanban.EN_PROCESO}),
    EstadoKanban.EN_PROCESO: frozenset({EstadoKanban.NUEVA, EstadoKanban.REVISION}),
    EstadoKanban.REVISION: frozenset({EstadoKanban.ARCHIVADA, EstadoKanban.EN_PROCESO}),
    EstadoKanban.ARCHIVADA: frozenset(),
}

# --- Transiciones válidas de EstadoJob ---
# pendiente → en_curso
# pendiente → cancelado
# en_curso → completado
# en_curso → fallido
# fallido → pendiente (reintento)
JOB_TRANSITIONS: dict[EstadoJob, frozenset[EstadoJob]] = {
    EstadoJob.PENDIENTE: frozenset({EstadoJob.EN_CURSO, EstadoJob.CANCELADO}),
    EstadoJob.EN_CURSO: frozenset({EstadoJob.COMPLETADO, EstadoJob.FALLIDO}),
    EstadoJob.COMPLETADO: frozenset(),
    EstadoJob.FALLIDO: frozenset({EstadoJob.PENDIENTE}),
    EstadoJob.CANCELADO: frozenset(),
}


def validate_kanban_transition(current: EstadoKanban, target: EstadoKanban) -> None:
    """
    Valida que una transición de EstadoKanban sea permitida.

    Args:
        current: Estado actual de la idea.
        target: Estado destino deseado.

    Raises:
        InvalidStateTransitionError: Si la transición no está
            en KANBAN_TRANSITIONS.
    """
    allowed = KANBAN_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidStateTransitionError(
            entity_type="EstadoKanban",
            current_state=current.value,
            target_state=target.value,
        )


def validate_job_transition(current: EstadoJob, target: EstadoJob) -> None:
    """
    Valida que una transición de EstadoJob sea permitida.

    Args:
        current: Estado actual del job.
        target: Estado destino deseado.

    Raises:
        InvalidStateTransitionError: Si la transición no está
            en JOB_TRANSITIONS.
    """
    allowed = JOB_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidStateTransitionError(
            entity_type="EstadoJob",
            current_state=current.value,
            target_state=target.value,
        )
