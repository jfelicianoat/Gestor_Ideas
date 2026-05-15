"""DTOs de integraciones IA."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OllamaGenerateRequest:
    """Request tipado para `/api/generate` de Ollama."""

    prompt: str
    model: str
    system: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    format_json: bool = False


@dataclass(frozen=True, slots=True)
class OllamaGenerateResult:
    """Resultado normalizado de una generación Ollama."""

    text: str
    model: str
    total_duration_ns: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Resultado normalizado de transcripción."""

    text: str
    language: str | None
    duration_seconds: float | None


@dataclass(frozen=True, slots=True)
class JobMetricsSnapshot:
    """Métricas básicas del runner de jobs IA."""

    processed: int
    completed: int
    failed: int
    retried: int
    timed_out: int
