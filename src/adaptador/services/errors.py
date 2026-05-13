"""
Errores de la capa de servicios de aplicación.

Los servicios traducen errores de dominio o persistencia a errores
explícitos de aplicación para que UI, workers o CLI puedan reaccionar
sin depender de detalles internos.
"""

from uuid import UUID


class ApplicationError(Exception):
    """Error base de la capa de aplicación."""


class ValidationAppError(ApplicationError):
    """Entrada inválida para ejecutar un caso de uso."""


class EntityNotFoundError(ApplicationError):
    """Entidad requerida por un caso de uso no encontrada."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} no encontrada: {entity_id}")


class ApplicationStateError(ApplicationError):
    """El estado actual no permite completar el caso de uso."""


class PersistenceOperationError(ApplicationError):
    """Fallo al ejecutar una operación de persistencia."""
