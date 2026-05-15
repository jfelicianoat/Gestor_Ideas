"""
Servicios de aplicación para jobs persistentes.

Los workers deben usar este servicio para cambiar estados de jobs en
vez de manipular repositorios y transiciones de dominio directamente.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loguru import logger

from adaptador.domain.entities import Job
from adaptador.domain.enums import EstadoJob, TipoJob
from adaptador.domain.errors import DomainError
from adaptador.domain.protocols import IdeaRepository, JobRepository
from adaptador.services.errors import (
    ApplicationStateError,
    EntityNotFoundError,
    PersistenceOperationError,
    ValidationAppError,
)


@dataclass(slots=True)
class JobService:
    """Casos de uso relacionados con cola y ciclo de vida de jobs."""

    job_repository: JobRepository
    idea_repository: IdeaRepository

    def enqueue_job(
        self,
        *,
        idea_id: UUID,
        tipo_job: TipoJob,
        payload: dict[str, Any] | None = None,
        max_intentos: int = 3,
        timeout_segundos: int = 120,
    ) -> Job:
        """
        Persiste un job pendiente asociado a una idea existente.

        Raises:
            EntityNotFoundError: Si la idea asociada no existe.
            ValidationAppError: Si los límites de ejecución son inválidos.
            PersistenceOperationError: Si falla la persistencia.
        """
        if max_intentos < 0:
            raise ValidationAppError("max_intentos no puede ser negativo")
        if timeout_segundos <= 0:
            raise ValidationAppError("timeout_segundos debe ser mayor que cero")

        try:
            idea = self.idea_repository.get_by_id(idea_id)
        except Exception as exc:
            logger.exception("No se pudo validar idea para job: idea_id={}", idea_id)
            raise PersistenceOperationError(
                f"No se pudo validar la idea del job: {idea_id}"
            ) from exc

        if idea is None:
            raise EntityNotFoundError("Idea", idea_id)

        job = Job(
            idea_id=idea_id,
            tipo_job=tipo_job,
            payload=payload or {},
            max_intentos=max_intentos,
            timeout_segundos=timeout_segundos,
        )

        try:
            created = self.job_repository.create(job)
        except Exception as exc:
            logger.exception("No se pudo encolar job: idea_id={}", idea_id)
            raise PersistenceOperationError(
                f"No se pudo encolar job para idea: {idea_id}"
            ) from exc

        logger.info(
            "Job encolado: id={} idea_id={} tipo={} max_intentos={}",
            created.id,
            created.idea_id,
            created.tipo_job.value,
            created.max_intentos,
        )
        return created

    def get_job_or_raise(self, job_id: UUID) -> Job:
        """Recupera un job o lanza un error explícito si no existe."""
        try:
            job = self.job_repository.get_by_id(job_id)
        except Exception as exc:
            logger.exception("No se pudo recuperar job: id={}", job_id)
            raise PersistenceOperationError(
                f"No se pudo recuperar el job: {job_id}"
            ) from exc

        if job is None:
            raise EntityNotFoundError("Job", job_id)
        return job

    def list_pending(self) -> list[Job]:
        """Devuelve los jobs pendientes de ejecución."""
        try:
            return self.job_repository.list_pending()
        except Exception as exc:
            logger.exception("No se pudieron listar jobs pendientes")
            raise PersistenceOperationError(
                "No se pudieron listar jobs pendientes"
            ) from exc

    def recover_in_progress_jobs(self) -> list[Job]:
        """
        Recupera jobs que quedaron EN_CURSO tras un cierre inesperado.

        Si aún tienen intentos disponibles vuelven a PENDIENTE. Si ya agotaron
        intentos, quedan FALLIDO con una causa explícita.
        """
        try:
            stale_jobs = self.job_repository.list_by_estado(EstadoJob.EN_CURSO)
        except Exception as exc:
            logger.exception("No se pudieron listar jobs en curso para recuperación")
            raise PersistenceOperationError(
                "No se pudieron recuperar jobs en curso"
            ) from exc

        recovered: list[Job] = []
        for job in stale_jobs:
            try:
                job.cambiar_estado(EstadoJob.FALLIDO)
                job.resultado = "Recuperado tras cierre inesperado"
                if job.puede_reintentar():
                    job.cambiar_estado(EstadoJob.PENDIENTE)
                recovered.append(self._update_job(job, "recuperar job en curso"))
            except DomainError as exc:
                raise ApplicationStateError(str(exc)) from exc

        if recovered:
            logger.warning("Jobs en curso recuperados: total={}", len(recovered))
        return recovered

    def start_job(self, job_id: UUID) -> Job:
        """Marca un job pendiente como en curso y registra un intento."""
        job = self.get_job_or_raise(job_id)

        try:
            job.cambiar_estado(EstadoJob.EN_CURSO)
            job.registrar_intento()
        except DomainError as exc:
            raise ApplicationStateError(str(exc)) from exc

        updated = self._update_job(job, "iniciar job")
        logger.info(
            "Job iniciado: id={} intento={}/{}",
            updated.id,
            updated.intentos,
            updated.max_intentos,
        )
        return updated

    def complete_job(self, job_id: UUID, resultado: str) -> Job:
        """Marca un job en curso como completado y guarda su resultado."""
        clean_result = resultado.strip()
        if not clean_result:
            raise ValidationAppError("El resultado del job no puede estar vacío")

        job = self.get_job_or_raise(job_id)

        try:
            job.cambiar_estado(EstadoJob.COMPLETADO)
        except DomainError as exc:
            raise ApplicationStateError(str(exc)) from exc

        job.resultado = clean_result
        updated = self._update_job(job, "completar job")
        logger.info("Job completado: id={}", updated.id)
        return updated

    def fail_job(self, job_id: UUID, error_message: str, *, retry: bool = True) -> Job:
        """
        Marca un job en curso como fallido y opcionalmente lo reencola.

        Si `retry` es True y quedan intentos disponibles, el job vuelve a
        `PENDIENTE`. Si no quedan intentos, permanece en `FALLIDO`.
        """
        clean_error = error_message.strip()
        if not clean_error:
            raise ValidationAppError("El mensaje de error del job es obligatorio")

        job = self.get_job_or_raise(job_id)

        try:
            job.cambiar_estado(EstadoJob.FALLIDO)
            job.resultado = clean_error
            if retry and job.puede_reintentar():
                job.cambiar_estado(EstadoJob.PENDIENTE)
        except DomainError as exc:
            raise ApplicationStateError(str(exc)) from exc

        updated = self._update_job(job, "registrar fallo de job")
        logger.warning(
            "Job fallido: id={} estado={} intentos={}/{} retry={}",
            updated.id,
            updated.estado.value,
            updated.intentos,
            updated.max_intentos,
            retry,
        )
        return updated

    def delete_job(self, job_id: UUID) -> None:
        self.get_job_or_raise(job_id)
        try:
            self.job_repository.delete(job_id)
        except Exception as exc:
            logger.exception("No se pudo eliminar el job: id={}", job_id)
            raise PersistenceOperationError(
                f"No se pudo eliminar el job: {job_id}"
            ) from exc
        logger.info("Job eliminado: id={}", job_id)

    def cancel_job(self, job_id: UUID) -> Job:
        """Cancela un job pendiente."""
        job = self.get_job_or_raise(job_id)

        try:
            job.cambiar_estado(EstadoJob.CANCELADO)
        except DomainError as exc:
            raise ApplicationStateError(str(exc)) from exc

        updated = self._update_job(job, "cancelar job")
        logger.info("Job cancelado: id={}", updated.id)
        return updated

    def _update_job(self, job: Job, operation: str) -> Job:
        """Actualiza un job traduciendo errores de persistencia."""
        try:
            return self.job_repository.update(job)
        except Exception as exc:
            logger.exception("No se pudo {}: job_id={}", operation, job.id)
            raise PersistenceOperationError(
                f"No se pudo {operation}: {job.id}"
            ) from exc
