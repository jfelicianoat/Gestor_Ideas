"""Integraciones IA: Ollama HTTP API y faster-whisper."""

from adaptador.ai.dto import (
    JobMetricsSnapshot,
    OllamaGenerateRequest,
    OllamaGenerateResult,
    TranscriptionResult,
)
from adaptador.ai.errors import (
    AIIntegrationError,
    AIResponseValidationError,
    AITimeoutError,
    AITransientError,
    TranscriptionError,
)
from adaptador.ai.job_handler import AIJobHandler
from adaptador.ai.metrics import JobMetrics
from adaptador.ai.ollama_client import AsyncOllamaClient
from adaptador.ai.whisper_transcriber import FasterWhisperTranscriber

__all__ = [
    "AIIntegrationError",
    "AIJobHandler",
    "AIResponseValidationError",
    "AITransientError",
    "AITimeoutError",
    "AsyncOllamaClient",
    "FasterWhisperTranscriber",
    "JobMetrics",
    "JobMetricsSnapshot",
    "OllamaGenerateRequest",
    "OllamaGenerateResult",
    "TranscriptionError",
    "TranscriptionResult",
]
