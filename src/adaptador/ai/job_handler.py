"""Handler de jobs IA sobre Ollama y faster-whisper."""

import json
from typing import Any

from loguru import logger

from adaptador.ai.dto import OllamaGenerateRequest
from adaptador.ai.json_validation import parse_json_object
from adaptador.ai.ollama_client import AsyncOllamaClient
from adaptador.ai.whisper_transcriber import FasterWhisperTranscriber
from adaptador.domain.entities import Job
from adaptador.domain.enums import TipoJob
from adaptador.domain.protocols import IdeaRepository
from adaptador.services.errors import EntityNotFoundError, ValidationAppError


class AIJobHandler:
    """Ejecuta jobs persistentes usando integraciones IA concretas."""

    def __init__(
        self,
        *,
        idea_repository: IdeaRepository,
        ollama_client: AsyncOllamaClient,
        transcriber: FasterWhisperTranscriber,
        default_model: str,
    ) -> None:
        self._idea_repository = idea_repository
        self._ollama_client = ollama_client
        self._transcriber = transcriber
        self._default_model = default_model
        self._log = logger.bind(component="ai_job_handler")

    async def handle(self, job: Job) -> str:
        """Ejecuta un job y devuelve el resultado serializable."""
        self._log.bind(
            job_id=str(job.id),
            idea_id=str(job.idea_id),
            tipo_job=job.tipo_job.value,
        ).info("ai_job_started")

        if job.tipo_job == TipoJob.TRANSCRIPCION:
            return await self._handle_transcription(job)
        if job.tipo_job in {TipoJob.ENRIQUECIMIENTO, TipoJob.RESUMEN}:
            return await self._handle_text_generation(job)
        if job.tipo_job == TipoJob.ETIQUETAS:
            return await self._handle_json_generation(job)

        raise ValidationAppError(f"Tipo de job no soportado: {job.tipo_job.value}")

    async def _handle_transcription(self, job: Job) -> str:
        audio_path = self._payload_str(job.payload, "audio_path")
        result = await self._transcriber.transcribe(audio_path)
        return result.text

    async def _handle_text_generation(self, job: Job) -> str:
        request = self._ollama_request(job, format_json=False)
        result = await self._ollama_client.generate(request)
        return result.text

    async def _handle_json_generation(self, job: Job) -> str:
        request = self._ollama_request(job, format_json=True)
        result, parsed = await self._ollama_client.generate_json(request)
        if self._payload_bool(job.payload, "return_raw_response"):
            parse_json_object(result.text)
            return result.text
        return json.dumps(parsed, ensure_ascii=False)

    def _ollama_request(self, job: Job, *, format_json: bool) -> OllamaGenerateRequest:
        idea = self._idea_repository.get_by_id(job.idea_id)
        if idea is None:
            raise EntityNotFoundError("Idea", job.idea_id)

        prompt = self._payload_str(job.payload, "prompt", required=False)
        if not prompt:
            prompt = idea.contenido_raw
        if not prompt.strip():
            raise ValidationAppError("El prompt del job IA no puede estar vacío")

        system = self._payload_str(job.payload, "system", required=False)
        model = self._payload_str(job.payload, "model", required=False)
        payload = job.payload if isinstance(job.payload, dict) else {}
        options = payload.get("options", {})
        if not isinstance(options, dict):
            raise ValidationAppError("payload.options debe ser un objeto JSON")

        return OllamaGenerateRequest(
            prompt=prompt,
            model=model or self._default_model,
            system=system,
            options=options,
            format_json=format_json,
        )

    def _payload_str(
        self, payload: dict[str, Any] | None, key: str, *, required: bool = True
    ) -> str:
        if not isinstance(payload, dict):
            if required:
                raise ValidationAppError(f"payload.{key} debe ser texto")
            return ""
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if required:
            raise ValidationAppError(f"payload.{key} debe ser texto")
        return ""

    def _payload_bool(self, payload: dict[str, Any] | None, key: str) -> bool:
        if not isinstance(payload, dict):
            raise ValidationAppError(f"payload.{key} debe ser booleano")
        value = payload.get(key, False)
        if isinstance(value, bool):
            return value
        raise ValidationAppError(f"payload.{key} debe ser booleano")
