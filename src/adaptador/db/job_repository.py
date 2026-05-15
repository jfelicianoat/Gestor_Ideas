import json
from uuid import UUID

from sqlmodel import Session, select

from adaptador.db.mappers import job_to_model, model_to_job
from adaptador.db.models import JobModel
from adaptador.domain.entities import Job
from adaptador.domain.enums import EstadoJob


class SQLJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _commit_or_rollback(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def create(self, job: Job) -> Job:
        model = job_to_model(job)
        self._session.add(model)
        self._commit_or_rollback()
        self._session.refresh(model)
        return model_to_job(model)

    def get_by_id(self, job_id: UUID) -> Job | None:
        model = self._session.get(JobModel, str(job_id))
        if model is None:
            return None
        return model_to_job(model)

    def list_pending(self) -> list[Job]:
        return self.list_by_estado(EstadoJob.PENDIENTE)

    def list_by_estado(self, estado: EstadoJob) -> list[Job]:
        statement = select(JobModel).where(JobModel.estado == estado.value)
        results = self._session.exec(statement).all()
        return [model_to_job(m) for m in results]

    def update(self, job: Job) -> Job:
        model = self._session.get(JobModel, str(job.id))
        if model is None:
            raise ValueError(f"Job no encontrado: {job.id}")

        model.tipo_job = job.tipo_job.value
        model.estado = job.estado.value
        model.intentos = job.intentos
        model.max_intentos = job.max_intentos
        model.payload = json.dumps(job.payload, ensure_ascii=False)
        model.resultado = job.resultado
        model.fecha_actualizado = job.fecha_actualizado
        model.timeout_segundos = job.timeout_segundos

        self._session.add(model)
        self._commit_or_rollback()
        self._session.refresh(model)
        return model_to_job(model)

    def delete(self, job_id: UUID) -> None:
        model = self._session.get(JobModel, str(job_id))
        if model is None:
            raise ValueError(f"Job no encontrado: {job_id}")
        self._session.delete(model)
        self._commit_or_rollback()
