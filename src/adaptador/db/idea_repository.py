from uuid import UUID

from sqlmodel import Session, select

from adaptador.db.mappers import idea_to_model, model_to_idea
from adaptador.db.models import IdeaModel
from adaptador.domain.entities import Idea
from adaptador.domain.enums import EstadoKanban


class SQLIdeaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _commit_or_rollback(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def create(self, idea: Idea) -> Idea:
        model = idea_to_model(idea)
        self._session.add(model)
        self._commit_or_rollback()
        self._session.refresh(model)
        return model_to_idea(model)

    def get_by_id(self, idea_id: UUID) -> Idea | None:
        model = self._session.get(IdeaModel, str(idea_id))
        if model is None:
            return None
        return model_to_idea(model)

    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        statement = select(IdeaModel).where(IdeaModel.estado_kanban == estado.value)
        results = self._session.exec(statement).all()
        return [model_to_idea(m) for m in results]

    def update(self, idea: Idea) -> Idea:
        model = self._session.get(IdeaModel, str(idea.id))
        if model is None:
            raise ValueError(f"Idea no encontrada: {idea.id}")

        model.titulo = idea.titulo
        model.contenido_raw = idea.contenido_raw
        model.contenido_enriquecido = idea.contenido_enriquecido
        model.tipo_entrada = idea.tipo_entrada.value
        model.estado_kanban = idea.estado_kanban.value
        model.archivo_adjunto = idea.archivo_adjunto
        model.fecha_modificacion = idea.fecha_modificacion

        self._session.add(model)
        self._commit_or_rollback()
        self._session.refresh(model)
        return model_to_idea(model)

    def list_by_ids(self, ids: list[UUID]) -> dict[UUID, Idea]:
        if not ids:
            return {}
        str_ids = [str(i) for i in ids]
        statement = select(IdeaModel).where(IdeaModel.id.in_(str_ids))
        models = self._session.exec(statement).all()
        return {UUID(m.id): model_to_idea(m) for m in models}

    def delete(self, idea_id: UUID) -> None:
        model = self._session.get(IdeaModel, str(idea_id))
        if model is None:
            raise ValueError(f"Idea no encontrada: {idea_id}")
        self._session.delete(model)
        self._commit_or_rollback()
