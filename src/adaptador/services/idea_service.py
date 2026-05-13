"""
Servicios de aplicación para casos de uso de ideas.

Esta capa orquesta repositorios y entidades de dominio. No conoce UI,
SQLModel ni detalles concretos de almacenamiento.
"""

from dataclasses import dataclass
from uuid import UUID

from loguru import logger

from adaptador.domain.entities import Idea
from adaptador.domain.enums import EstadoKanban, TipoEntrada
from adaptador.domain.errors import DomainError
from adaptador.domain.protocols import IdeaRepository
from adaptador.services.errors import (
    ApplicationStateError,
    EntityNotFoundError,
    PersistenceOperationError,
    ValidationAppError,
)


@dataclass(slots=True)
class IdeaService:
    """Casos de uso relacionados con captura y ciclo de vida de ideas."""

    idea_repository: IdeaRepository

    def create_idea(
        self,
        *,
        titulo: str,
        contenido_raw: str,
        tipo_entrada: TipoEntrada = TipoEntrada.TEXTO,
        archivo_adjunto: str | None = None,
    ) -> Idea:
        """
        Crea una idea validada y la persiste.

        Raises:
            ValidationAppError: Si título o contenido están vacíos.
            PersistenceOperationError: Si el repositorio falla.
        """
        clean_title = titulo.strip()
        clean_content = contenido_raw.strip()
        if not clean_title:
            raise ValidationAppError("El título de la idea es obligatorio")
        if not clean_content:
            raise ValidationAppError("El contenido de la idea es obligatorio")

        idea = Idea(
            titulo=clean_title,
            contenido_raw=clean_content,
            tipo_entrada=tipo_entrada,
            archivo_adjunto=archivo_adjunto,
        )

        try:
            created = self.idea_repository.create(idea)
        except Exception as exc:
            logger.exception("No se pudo crear la idea")
            raise PersistenceOperationError("No se pudo crear la idea") from exc

        logger.info(
            "Idea creada: id={} tipo_entrada={} estado={}",
            created.id,
            created.tipo_entrada.value,
            created.estado_kanban.value,
        )
        return created

    def get_idea_or_raise(self, idea_id: UUID) -> Idea:
        """Recupera una idea o lanza un error explícito si no existe."""
        try:
            idea = self.idea_repository.get_by_id(idea_id)
        except Exception as exc:
            logger.exception("No se pudo recuperar la idea: id={}", idea_id)
            raise PersistenceOperationError(
                f"No se pudo recuperar la idea: {idea_id}"
            ) from exc

        if idea is None:
            raise EntityNotFoundError("Idea", idea_id)
        return idea

    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        """Lista ideas por estado Kanban."""
        try:
            return self.idea_repository.list_by_estado(estado)
        except Exception as exc:
            logger.exception("No se pudieron listar ideas: estado={}", estado.value)
            raise PersistenceOperationError(
                f"No se pudieron listar ideas en estado {estado.value}"
            ) from exc

    def move_idea(self, idea_id: UUID, nuevo_estado: EstadoKanban) -> Idea:
        """
        Cambia el estado Kanban de una idea respetando reglas de dominio.

        Raises:
            EntityNotFoundError: Si la idea no existe.
            ApplicationStateError: Si la transición no está permitida.
            PersistenceOperationError: Si el repositorio falla.
        """
        idea = self.get_idea_or_raise(idea_id)
        estado_anterior = idea.estado_kanban

        try:
            idea.cambiar_estado(nuevo_estado)
        except DomainError as exc:
            raise ApplicationStateError(str(exc)) from exc

        try:
            updated = self.idea_repository.update(idea)
        except Exception as exc:
            logger.exception(
                "No se pudo mover la idea: id={} desde={} hasta={}",
                idea_id,
                estado_anterior.value,
                nuevo_estado.value,
            )
            raise PersistenceOperationError(
                f"No se pudo actualizar el estado de la idea: {idea_id}"
            ) from exc

        logger.info(
            "Idea movida: id={} desde={} hasta={}",
            updated.id,
            estado_anterior.value,
            updated.estado_kanban.value,
        )
        return updated

    def set_enriched_content(self, idea_id: UUID, contenido_enriquecido: str) -> Idea:
        """Guarda el resultado enriquecido de IA en una idea existente."""
        clean_content = contenido_enriquecido.strip()
        if not clean_content:
            raise ValidationAppError("El contenido enriquecido no puede estar vacío")

        idea = self.get_idea_or_raise(idea_id)
        idea.contenido_enriquecido = clean_content

        try:
            updated = self.idea_repository.update(idea)
        except Exception as exc:
            logger.exception(
                "No se pudo guardar contenido enriquecido: idea_id={}", idea_id
            )
            raise PersistenceOperationError(
                f"No se pudo guardar contenido enriquecido: {idea_id}"
            ) from exc

        logger.info("Contenido enriquecido guardado: idea_id={}", updated.id)
        return updated
