"""
Runner asíncrono para procesar jobs persistentes.

El runner no sabe cómo se ejecuta cada tipo de job. Recibe un handler
inyectado, aplica timeout con asyncio y delega las transiciones a JobService.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from loguru import logger

from adaptador.ai.errors import AITimeoutError
from adaptador.ai.metrics import JobMetrics
from adaptador.domain.entities import Job
from adaptador.domain.enums import EstadoJob
from adaptador.services.job_service import JobService


class JobHandler(Protocol):
    """Contrato de ejecución concreta para un job."""

    async def handle(self, job: Job) -> str:
        """Ejecuta el job y devuelve el resultado textual."""
        ...


@dataclass(slots=True)
class AsyncJobRunner:
    """Procesa jobs pendientes usando asyncio y servicios desacoplados."""

    job_service: JobService
    handler: JobHandler
    metrics: JobMetrics = field(default_factory=JobMetrics)
    # Servicio de ideas para guardar el resultado enriquecido.
    # Si es None, el resultado solo se guarda en el job.
    idea_service: Any = field(default=None)

    async def process_one(self, job_id: UUID) -> Job:
        """Procesa un job por ID y persiste su estado final."""
        started = self.job_service.start_job(job_id)

        try:
            result = await asyncio.wait_for(
                self.handler.handle(started),
                timeout=started.timeout_segundos,
            )
        except TimeoutError:
            logger.warning(
                "Timeout procesando job: id={} timeout_segundos={}",
                started.id,
                started.timeout_segundos,
            )
            failed = self.job_service.fail_job(
                started.id,
                f"Timeout tras {started.timeout_segundos}s",
            )
            self.metrics.record_failed(
                retried=failed.estado == EstadoJob.PENDIENTE,
                timed_out=True,
            )
            return failed
        except AITimeoutError as exc:
            logger.warning("Timeout de integración IA: id={} error={}", started.id, exc)
            failed = self.job_service.fail_job(started.id, str(exc))
            self.metrics.record_failed(
                retried=failed.estado == EstadoJob.PENDIENTE,
                timed_out=True,
            )
            return failed
        except Exception as exc:
            logger.exception("Error procesando job: id={}", started.id)
            message = str(exc) or exc.__class__.__name__
            failed = self.job_service.fail_job(started.id, message)
            self.metrics.record_failed(retried=failed.estado == EstadoJob.PENDIENTE)
            return failed

        try:
            completed = self.job_service.complete_job(started.id, result)
        except Exception as exc:
            logger.exception("Error completando job: id={}", started.id)
            message = str(exc) or exc.__class__.__name__
            failed = self.job_service.fail_job(started.id, message)
            self.metrics.record_failed(retried=failed.estado == EstadoJob.PENDIENTE)
            return failed

        # Guardar el resultado como contenido enriquecido de la idea
        self._save_enriched_content(completed, result)
        self._mark_idea_ready_for_review(completed)

        self.metrics.record_completed()
        return completed

    def _save_enriched_content(self, job: Job, result: str) -> None:
        """Guarda el resultado IA en la idea asociada al job."""
        if self.idea_service is None:
            return
        try:
            self.idea_service.set_enriched_content(job.idea_id, result)
            logger.info(
                "Contenido enriquecido guardado: idea_id={}",
                job.idea_id,
            )
        except Exception as exc:
            # No fallar el job por un error al guardar
            # el contenido enriquecido (ya está completado)
            logger.warning(
                "No se pudo guardar contenido enriquecido: idea_id={} error={}",
                job.idea_id,
                exc,
            )

    def _mark_idea_ready_for_review(self, job: Job) -> None:
        """Avanza la idea a revisión si el job se completó correctamente."""
        try:
            moved = self.job_service.mark_idea_ready_for_review(job.idea_id)
            if moved:
                logger.info("Idea avanzada a revisión: idea_id={}", job.idea_id)
        except Exception as exc:
            logger.warning(
                "No se pudo avanzar idea a revisión: idea_id={} error={}",
                job.idea_id,
                exc,
            )

    async def process_pending(self, *, limit: int | None = None) -> list[Job]:
        """Procesa jobs pendientes de forma secuencial y devuelve resultados."""
        if limit is not None and limit < 1:
            raise ValueError("limit debe ser mayor que cero")

        pending = self.job_service.list_pending()
        if limit is not None:
            pending = pending[:limit]

        logger.info("Procesando jobs pendientes: total={}", len(pending))
        processed: list[Job] = []
        for job in pending:
            processed.append(await self.process_one(job.id))
        return processed
