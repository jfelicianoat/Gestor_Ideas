"""
Servicio de ciclo de vida para procesar la cola persistente de jobs.

Este servicio no depende de UI. Gestiona recovery inicial, ejecuciones
periódicas, parada ordenada y métricas a través de AsyncJobRunner.
"""

import asyncio
from dataclasses import dataclass, field

from loguru import logger

from adaptador.domain.entities import Job
from adaptador.services.job_runner import AsyncJobRunner


class JobWorkerStateError(RuntimeError):
    """Operación inválida para el estado actual del worker."""


@dataclass(slots=True)
class JobWorkerService:
    """Worker asíncrono con start/stop y polling configurable."""

    runner: AsyncJobRunner
    poll_interval_seconds: float
    batch_limit: int | None = None
    recover_on_start: bool = True
    _task: asyncio.Task[None] | None = field(default=None, init=False)
    _stop_event: asyncio.Event | None = field(default=None, init=False)

    @property
    def is_running(self) -> bool:
        """Indica si el loop del worker está activo."""
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Arranca el worker en el event loop actual."""
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds debe ser mayor que cero")
        if self.is_running:
            raise JobWorkerStateError("El worker ya está en ejecución")

        if self.recover_on_start:
            self.recover_stale_jobs()

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="job-worker")
        logger.info(
            "JobWorker iniciado: poll_interval={} batch_limit={}",
            self.poll_interval_seconds,
            self.batch_limit,
        )

    async def stop(self) -> None:
        """Solicita parada y cancela el ciclo actual."""
        if self._task is None:
            return
        if self._stop_event is not None:
            self._stop_event.set()

        try:
            self._task.cancel()
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            self._stop_event = None
            logger.info("JobWorker detenido")

    def recover_stale_jobs(self) -> list[Job]:
        """Recupera jobs que quedaron EN_CURSO antes de procesar."""
        recovered = self.runner.job_service.recover_in_progress_jobs()
        if recovered:
            logger.warning("JobWorker recuperó jobs stale: total={}", len(recovered))
        return recovered

    async def process_once(self) -> list[Job]:
        """Procesa un lote de jobs pendientes."""
        return await self.runner.process_pending(limit=self.batch_limit)

    async def _run_loop(self) -> None:
        if self._stop_event is None:
            raise JobWorkerStateError("El worker no fue inicializado")

        while not self._stop_event.is_set():
            try:
                await self.process_once()
            except Exception as exc:
                logger.exception("JobWorker falló procesando lote: {}", exc)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                continue
