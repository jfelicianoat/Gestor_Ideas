"""Métricas básicas en memoria para jobs IA."""

from dataclasses import dataclass

from adaptador.ai.dto import JobMetricsSnapshot


@dataclass(slots=True)
class JobMetrics:
    """Contadores simples para observar el worker sin acoplarlo a UI."""

    processed: int = 0
    completed: int = 0
    failed: int = 0
    retried: int = 0
    timed_out: int = 0

    def record_completed(self) -> None:
        self.processed += 1
        self.completed += 1

    def record_failed(self, *, retried: bool = False, timed_out: bool = False) -> None:
        self.processed += 1
        self.failed += 1
        if retried:
            self.retried += 1
        if timed_out:
            self.timed_out += 1

    def snapshot(self) -> JobMetricsSnapshot:
        return JobMetricsSnapshot(
            processed=self.processed,
            completed=self.completed,
            failed=self.failed,
            retried=self.retried,
            timed_out=self.timed_out,
        )
