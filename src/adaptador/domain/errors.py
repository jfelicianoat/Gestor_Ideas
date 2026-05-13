"""
Excepciones del dominio del Gestor de Ideas.

Jerarquía de errores para reglas de negocio. Todas heredan
de DomainError para facilitar captura selectiva en capas
superiores sin acoplar a detalles internos.
"""


class DomainError(Exception):
    """Error base para violaciones de reglas de dominio."""

    pass


class InvalidStateTransitionError(DomainError):
    """
    Error al intentar una transición de estado no permitida.

    Incluye el estado actual y el estado destino para
    facilitar diagnóstico sin exponer internos.
    """

    def __init__(self, entity_type: str, current_state: str, target_state: str) -> None:
        self.entity_type = entity_type
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(
            f"Transición inválida en {entity_type}: "
            f"'{current_state}' → '{target_state}' no está permitida"
        )
