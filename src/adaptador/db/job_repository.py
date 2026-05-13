"""
Repositorio SQL para la entidad Job.

Implementación concreta del protocolo JobRepository usando
SQLModel/SQLAlchemy. Todas las operaciones reciben y devuelven
entidades de dominio — los modelos ORM no salen de este módulo.
"""

import json
from uuid import UUID

from sqlmodel import Session, select

from adaptador.db.mappers import job_to_model, model_to_job
from adaptador.db.models import JobModel
from adaptador.domain.entities import Job
from adaptador.domain.enums import EstadoJob


class SQLJobRepository:
    """Implementación SQLModel del protocolo JobRepository."""

    def __init__(self, session: Session) -> None:
        """
        Inicializa el repositorio con una sesión activa.

        Args:
            session: Sesión SQLModel/SQLAlchemy vinculada a un engine.
        """
        self._session = session

    def create(self, job: Job) -> Job:
        """
        Persiste un nuevo job en la base de datos.

        Args:
            job: Entidad de dominio a persistir.

        Returns:
            Job con los datos tal como quedaron en BD.
        """
        model = job_to_model(job)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return model_to_job(model)

    def get_by_id(self, job_id: UUID) -> Job | None:
        """
        Busca un job por su UUID.

        Args:
            job_id: Identificador único del job.

        Returns:
            Entidad Job si existe, None en caso contrario.
        """
        model = self._session.get(JobModel, str(job_id))
        if model is None:
            return None
        return model_to_job(model)

    def list_pending(self) -> list[Job]:
        """
        Lista todos los jobs en estado PENDIENTE.

        Returns:
            Lista de entidades Job pendientes de ejecución.
        """
        statement = select(JobModel).where(
            JobModel.estado == EstadoJob.PENDIENTE.value
        )
        results = self._session.exec(statement).all()
        return [model_to_job(m) for m in results]

    def update(self, job: Job) -> Job:
        """
        Actualiza un job existente en la base de datos.

        Busca el modelo por ID y actualiza todos sus campos
        con los valores de la entidad de dominio.

        Args:
            job: Entidad con los datos actualizados.

        Returns:
            Job con los datos tal como quedaron en BD.

        Raises:
            ValueError: Si el job no existe en la BD.
        """
        model = self._session.get(JobModel, str(job.id))
        if model is None:
            raise ValueError(f"Job no encontrado: {job.id}")

        # Actualizar campos del modelo
        model.tipo_job = job.tipo_job.value
        model.estado = job.estado.value
        model.intentos = job.intentos
        model.max_intentos = job.max_intentos
        model.payload = json.dumps(job.payload, ensure_ascii=False)
        model.resultado = job.resultado
        model.fecha_actualizado = job.fecha_actualizado
        model.timeout_segundos = job.timeout_segundos

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return model_to_job(model)
