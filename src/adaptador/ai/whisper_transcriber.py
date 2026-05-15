"""Adaptador asíncrono para faster-whisper."""

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger

from adaptador.ai.dto import TranscriptionResult
from adaptador.ai.errors import AITimeoutError, TranscriptionError


class FasterWhisperTranscriber:
    """Transcriptor local con carga perezosa del modelo."""

    def __init__(
        self,
        *,
        model_size: str,
        timeout_seconds: int = 600,
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        self._model_size = model_size
        self._timeout_seconds = timeout_seconds
        self._device = device
        self._compute_type = compute_type
        self._model: Any | None = None
        self._log = logger.bind(component="faster_whisper", model_size=model_size)

    async def transcribe(self, audio_path: str | Path) -> TranscriptionResult:
        """Transcribe un archivo de audio sin bloquear el event loop."""
        path = Path(audio_path)
        if not path.exists() or not path.is_file():
            raise TranscriptionError(f"Archivo de audio no encontrado: {path}")

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._transcribe_sync, path),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            self._log.bind(path=str(path)).warning("whisper_timeout")
            raise AITimeoutError(
                f"Timeout transcribiendo audio tras {self._timeout_seconds}s"
            ) from exc
        except TranscriptionError:
            raise
        except Exception as exc:
            self._log.bind(path=str(path), error=str(exc)).exception(
                "whisper_transcription_failed"
            )
            raise TranscriptionError(f"No se pudo transcribir audio: {path}") from exc

    def _transcribe_sync(self, path: Path) -> TranscriptionResult:
        model = self._get_model()
        self._log.bind(path=str(path)).info("whisper_transcription_started")
        segments, info = model.transcribe(str(path))
        text = " ".join(segment.text.strip() for segment in segments).strip()
        self._log.bind(
            path=str(path),
            language=getattr(info, "language", None),
            duration_seconds=getattr(info, "duration", None),
        ).info("whisper_transcription_completed")
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            duration_seconds=getattr(info, "duration", None),
        )

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise TranscriptionError("faster-whisper no está instalado") from exc

            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model
