"""
Tests unitarios del dominio: entidades, enums y transiciones.

Cubre:
- Transiciones válidas e inválidas de EstadoKanban
- Transiciones válidas e inválidas de EstadoJob
- Comportamiento de Idea.cambiar_estado()
- Comportamiento de Job.cambiar_estado(), registrar_intento(), puede_reintentar()
- Creación de entidades con valores por defecto
- Contexto del error InvalidStateTransitionError
"""

import pytest

from adaptador.domain.entities import BackupRegistro, Idea, Job
from adaptador.domain.enums import (
    EstadoJob,
    EstadoKanban,
    TipoEntrada,
)
from adaptador.domain.errors import (
    DomainError,
    InvalidStateTransitionError,
)
from adaptador.domain.transitions import (
    validate_job_transition,
    validate_kanban_transition,
)

# ============================================================
# Transiciones de EstadoKanban
# ============================================================


class TestKanbanTransiciones:
    """Transiciones válidas e inválidas del tablero Kanban."""

    @pytest.mark.parametrize(
        "origen, destino",
        [
            (EstadoKanban.NUEVA, EstadoKanban.EN_PROCESO),
            (EstadoKanban.EN_PROCESO, EstadoKanban.REVISION),
            (EstadoKanban.REVISION, EstadoKanban.ARCHIVADA),
            (EstadoKanban.REVISION, EstadoKanban.EN_PROCESO),
        ],
    )
    def test_transicion_kanban_valida(
        self, origen: EstadoKanban, destino: EstadoKanban
    ) -> None:
        """Las transiciones definidas en CONTEXT_PACK no lanzan error."""
        # No debe lanzar excepción
        validate_kanban_transition(origen, destino)

    @pytest.mark.parametrize(
        "origen, destino",
        [
            (EstadoKanban.NUEVA, EstadoKanban.REVISION),
            (EstadoKanban.NUEVA, EstadoKanban.ARCHIVADA),
            (EstadoKanban.EN_PROCESO, EstadoKanban.NUEVA),
            (EstadoKanban.EN_PROCESO, EstadoKanban.ARCHIVADA),
            (EstadoKanban.ARCHIVADA, EstadoKanban.NUEVA),
            (EstadoKanban.ARCHIVADA, EstadoKanban.REVISION),
        ],
    )
    def test_transicion_kanban_invalida(
        self, origen: EstadoKanban, destino: EstadoKanban
    ) -> None:
        """Las transiciones no definidas lanzan InvalidStateTransitionError."""
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            validate_kanban_transition(origen, destino)

        # Verificar contexto del error
        assert exc_info.value.entity_type == "EstadoKanban"
        assert exc_info.value.current_state == origen.value
        assert exc_info.value.target_state == destino.value

    def test_error_hereda_de_domain_error(self) -> None:
        """InvalidStateTransitionError es subclase de DomainError."""
        with pytest.raises(DomainError):
            validate_kanban_transition(
                EstadoKanban.NUEVA, EstadoKanban.ARCHIVADA
            )


# ============================================================
# Transiciones de EstadoJob
# ============================================================


class TestJobTransiciones:
    """Transiciones válidas e inválidas del sistema de jobs."""

    @pytest.mark.parametrize(
        "origen, destino",
        [
            (EstadoJob.PENDIENTE, EstadoJob.EN_CURSO),
            (EstadoJob.PENDIENTE, EstadoJob.CANCELADO),
            (EstadoJob.EN_CURSO, EstadoJob.COMPLETADO),
            (EstadoJob.EN_CURSO, EstadoJob.FALLIDO),
            (EstadoJob.FALLIDO, EstadoJob.PENDIENTE),
        ],
    )
    def test_transicion_job_valida(
        self, origen: EstadoJob, destino: EstadoJob
    ) -> None:
        """Las transiciones definidas no lanzan error."""
        validate_job_transition(origen, destino)

    @pytest.mark.parametrize(
        "origen, destino",
        [
            (EstadoJob.PENDIENTE, EstadoJob.COMPLETADO),
            (EstadoJob.PENDIENTE, EstadoJob.FALLIDO),
            (EstadoJob.EN_CURSO, EstadoJob.PENDIENTE),
            (EstadoJob.EN_CURSO, EstadoJob.CANCELADO),
            (EstadoJob.COMPLETADO, EstadoJob.PENDIENTE),
            (EstadoJob.COMPLETADO, EstadoJob.FALLIDO),
            (EstadoJob.CANCELADO, EstadoJob.PENDIENTE),
        ],
    )
    def test_transicion_job_invalida(
        self, origen: EstadoJob, destino: EstadoJob
    ) -> None:
        """Las transiciones no definidas lanzan error con contexto."""
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            validate_job_transition(origen, destino)

        assert exc_info.value.entity_type == "EstadoJob"
        assert exc_info.value.current_state == origen.value
        assert exc_info.value.target_state == destino.value


# ============================================================
# Entidad Idea
# ============================================================


class TestIdea:
    """Tests de la entidad Idea."""

    def test_idea_default_es_nueva(self) -> None:
        """Una idea recién creada tiene estado NUEVA."""
        idea = Idea(titulo="Mi idea", contenido_raw="Contenido de prueba")
        assert idea.estado_kanban == EstadoKanban.NUEVA
        assert idea.tipo_entrada == TipoEntrada.TEXTO

    def test_idea_cambiar_estado_valido(self) -> None:
        """cambiar_estado() con transición válida actualiza estado y fecha."""
        idea = Idea(titulo="Test")
        fecha_original = idea.fecha_modificacion

        idea.cambiar_estado(EstadoKanban.EN_PROCESO)

        assert idea.estado_kanban == EstadoKanban.EN_PROCESO
        assert idea.fecha_modificacion >= fecha_original

    def test_idea_cambiar_estado_invalido(self) -> None:
        """cambiar_estado() con transición inválida lanza error sin mutar."""
        idea = Idea(titulo="Test")

        with pytest.raises(InvalidStateTransitionError):
            idea.cambiar_estado(EstadoKanban.ARCHIVADA)

        # Estado no debe haber cambiado
        assert idea.estado_kanban == EstadoKanban.NUEVA

    def test_idea_flujo_completo_kanban(self) -> None:
        """Una idea puede recorrer el flujo completo del Kanban."""
        idea = Idea(titulo="Flujo completo")

        idea.cambiar_estado(EstadoKanban.EN_PROCESO)
        assert idea.estado_kanban == EstadoKanban.EN_PROCESO

        idea.cambiar_estado(EstadoKanban.REVISION)
        assert idea.estado_kanban == EstadoKanban.REVISION

        idea.cambiar_estado(EstadoKanban.ARCHIVADA)
        assert idea.estado_kanban == EstadoKanban.ARCHIVADA


# ============================================================
# Entidad Job
# ============================================================


class TestJob:
    """Tests de la entidad Job."""

    def test_job_default_es_pendiente(self) -> None:
        """Un job recién creado tiene estado PENDIENTE."""
        job = Job()
        assert job.estado == EstadoJob.PENDIENTE
        assert job.intentos == 0

    def test_job_cambiar_estado_valido(self) -> None:
        """cambiar_estado() actualiza estado y timestamp."""
        job = Job()
        fecha_original = job.fecha_actualizado

        job.cambiar_estado(EstadoJob.EN_CURSO)

        assert job.estado == EstadoJob.EN_CURSO
        assert job.fecha_actualizado >= fecha_original

    def test_job_cambiar_estado_invalido(self) -> None:
        """cambiar_estado() inválido lanza error sin mutar estado."""
        job = Job()

        with pytest.raises(InvalidStateTransitionError):
            job.cambiar_estado(EstadoJob.COMPLETADO)

        assert job.estado == EstadoJob.PENDIENTE

    def test_job_registrar_intento(self) -> None:
        """registrar_intento() incrementa el contador."""
        job = Job(max_intentos=3)
        assert job.intentos == 0

        job.registrar_intento()
        assert job.intentos == 1

        job.registrar_intento()
        assert job.intentos == 2

    def test_job_puede_reintentar(self) -> None:
        """puede_reintentar() devuelve False al agotar intentos."""
        job = Job(max_intentos=2)

        assert job.puede_reintentar() is True
        job.registrar_intento()
        assert job.puede_reintentar() is True
        job.registrar_intento()
        assert job.puede_reintentar() is False

    def test_job_flujo_reintento(self) -> None:
        """Un job fallido puede volver a pendiente para reintento."""
        job = Job()
        job.cambiar_estado(EstadoJob.EN_CURSO)
        job.cambiar_estado(EstadoJob.FALLIDO)
        job.cambiar_estado(EstadoJob.PENDIENTE)  # reintento

        assert job.estado == EstadoJob.PENDIENTE


# ============================================================
# Entidad BackupRegistro
# ============================================================


class TestBackupRegistro:
    """Tests de la entidad BackupRegistro."""

    def test_backup_registro_creacion(self) -> None:
        """BackupRegistro se crea con valores razonables."""
        backup = BackupRegistro(
            ruta_archivo="/backups/db_20260513.db",
            tamano_bytes=1024,
        )

        assert backup.id is None  # Asignado por persistencia
        assert backup.ruta_archivo == "/backups/db_20260513.db"
        assert backup.tamano_bytes == 1024
        assert backup.fecha_backup is not None
