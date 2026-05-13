"""
Runner asíncrono para procesar jobs persistentes.

El runner no sabe cómo se ejecuta cada tipo de job. Recibe un handler
inyectado, aplica timeout con asyncio y delega las transiciones a JobService.
"""

import asyncio
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from loguru import logger

from adaptador.domain.entities import Job
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
            return self.job_service.fail_job(
                started.id,
                f"Timeout tras {started.timeout_segundos}s",
            )
        except Exception as exc:
            logger.exception("Error procesando job: id={}", started.id)
            message = str(exc) or exc.__class__.__name__
            return self.job_service.fail_job(started.id, message)

        return self.job_service.complete_job(started.id, result)

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
