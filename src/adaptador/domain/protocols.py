"""
Protocolos (interfaces) de repositorios del dominio.

Definen los contratos que deben cumplir las implementaciones
concretas de persistencia. Los servicios de aplicación dependen
de estos protocolos, nunca de implementaciones concretas.

Regla: Este módulo NO debe importar SQLModel, PySide6 ni
ninguna librería de infraestructura.

Referencia: SKILLS.md §4 (Dependency Inversion), AGENTS.md §AGENTE-05
"""

from typing import Protocol
from uuid import UUID

from adaptador.domain.entities import Idea, Job
from adaptador.domain.enums import EstadoKanban


class IdeaRepository(Protocol):
    """Contrato de persistencia para la entidad Idea."""

    def create(self, idea: Idea) -> Idea:
        """Persiste una nueva idea y la devuelve con ID asignado."""
        ...

    def get_by_id(self, idea_id: UUID) -> Idea | None:
        """Busca una idea por su ID. Devuelve None si no existe."""
        ...

    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        """Devuelve todas las ideas con el estado Kanban indicado."""
        ...

    def update(self, idea: Idea) -> Idea:
        """Actualiza una idea existente y la devuelve con datos frescos."""
        ...


class JobRepository(Protocol):
    """Contrato de persistencia para la entidad Job."""

    def create(self, job: Job) -> Job:
        """Persiste un nuevo job y lo devuelve con ID asignado."""
        ...

    def get_by_id(self, job_id: UUID) -> Job | None:
        """Busca un job por su ID. Devuelve None si no existe."""
        ...

    def list_pending(self) -> list[Job]:
        """Devuelve todos los jobs en estado pendiente."""
        ...

    def update(self, job: Job) -> Job:
        """Actualiza un job existente y lo devuelve con datos frescos."""
        ...
