"""
Repositorio SQL para la entidad Idea.

Implementación concreta del protocolo IdeaRepository usando
SQLModel/SQLAlchemy. Todas las operaciones reciben y devuelven
entidades de dominio — los modelos ORM no salen de este módulo.
"""

from uuid import UUID

from sqlmodel import Session, select

from adaptador.db.mappers import idea_to_model, model_to_idea
from adaptador.db.models import IdeaModel
from adaptador.domain.entities import Idea
from adaptador.domain.enums import EstadoKanban


class SQLIdeaRepository:
    """Implementación SQLModel del protocolo IdeaRepository."""

    def __init__(self, session: Session) -> None:
        """
        Inicializa el repositorio con una sesión activa.

        Args:
            session: Sesión SQLModel/SQLAlchemy vinculada a un engine.
        """
        self._session = session

    def create(self, idea: Idea) -> Idea:
        """
        Persiste una nueva idea en la base de datos.

        Args:
            idea: Entidad de dominio a persistir.

        Returns:
            Idea con los datos tal como quedaron en BD.
        """
        model = idea_to_model(idea)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return model_to_idea(model)

    def get_by_id(self, idea_id: UUID) -> Idea | None:
        """
        Busca una idea por su UUID.

        Args:
            idea_id: Identificador único de la idea.

        Returns:
            Entidad Idea si existe, None en caso contrario.
        """
        model = self._session.get(IdeaModel, str(idea_id))
        if model is None:
            return None
        return model_to_idea(model)

    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        """
        Lista todas las ideas con un estado Kanban específico.

        Args:
            estado: Estado Kanban a filtrar.

        Returns:
            Lista de entidades Idea que coinciden con el estado.
        """
        statement = select(IdeaModel).where(
            IdeaModel.estado_kanban == estado.value
        )
        results = self._session.exec(statement).all()
        return [model_to_idea(m) for m in results]

    def update(self, idea: Idea) -> Idea:
        """
        Actualiza una idea existente en la base de datos.

        Busca el modelo por ID y actualiza todos sus campos
        con los valores de la entidad de dominio.

        Args:
            idea: Entidad con los datos actualizados.

        Returns:
            Idea con los datos tal como quedaron en BD.

        Raises:
            ValueError: Si la idea no existe en la BD.
        """
        model = self._session.get(IdeaModel, str(idea.id))
        if model is None:
            raise ValueError(f"Idea no encontrada: {idea.id}")

        # Actualizar campos del modelo
        model.titulo = idea.titulo
        model.contenido_raw = idea.contenido_raw
        model.contenido_enriquecido = idea.contenido_enriquecido
        model.tipo_entrada = idea.tipo_entrada.value
        model.estado_kanban = idea.estado_kanban.value
        model.archivo_adjunto = idea.archivo_adjunto
        model.fecha_modificacion = idea.fecha_modificacion

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return model_to_idea(model)
