"""Cliente asíncrono robusto para Ollama HTTP API."""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
from loguru import logger

from adaptador.ai.dto import OllamaGenerateRequest, OllamaGenerateResult
from adaptador.ai.errors import (
    AIResponseValidationError,
    AITimeoutError,
    AITransientError,
)
from adaptador.ai.json_validation import parse_json_object


class AsyncOllamaClient:
    """Cliente `/api/generate` con retries, timeout y validación."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: int,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._backoff_base_seconds = backoff_base_seconds
        self._client_factory = client_factory
        self._log = logger.bind(component="ollama_client", base_url=self._base_url)

    async def generate(self, request: OllamaGenerateRequest) -> OllamaGenerateResult:
        """Genera texto con Ollama aplicando retries ante fallos transitorios."""
        payload = self._build_payload(request)
        endpoint = f"{self._base_url}/api/generate"
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 2):
            try:
                self._log.bind(
                    model=request.model,
                    attempt=attempt,
                    timeout_seconds=self._timeout_seconds,
                ).info("ollama_request_started")
                async with self._create_client() as client:
                    response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = self._validate_response(response.json())
                result = self._to_result(data, request.model)
                self._log.bind(
                    model=result.model,
                    attempt=attempt,
                    eval_count=result.eval_count,
                ).info("ollama_request_completed")
                return result
            except httpx.TimeoutException:
                last_error = AITimeoutError("Timeout llamando a Ollama")
                self._log.bind(attempt=attempt).warning("ollama_timeout")
            except (
                httpx.ConnectError,
                httpx.HTTPStatusError,
                httpx.TransportError,
            ) as exc:
                last_error = AITransientError(f"Ollama no disponible: {exc}")
                self._log.bind(attempt=attempt, error=str(exc)).warning(
                    "ollama_transient_error"
                )
            except ValueError as exc:
                raise AIResponseValidationError(
                    "Ollama devolvió una respuesta JSON inválida"
                ) from exc

            if attempt <= self._max_retries:
                await asyncio.sleep(self._backoff_seconds(attempt))

        if last_error is None:
            last_error = AITransientError("Ollama no disponible")
        raise last_error

    async def generate_json(
        self, request: OllamaGenerateRequest
    ) -> tuple[OllamaGenerateResult, dict[str, Any]]:
        """Genera y valida que el texto devuelto sea un objeto JSON."""
        result = await self.generate(
            OllamaGenerateRequest(
                prompt=request.prompt,
                model=request.model,
                system=request.system,
                options=request.options,
                format_json=True,
            )
        )
        return result, parse_json_object(result.text)

    def _build_payload(self, request: OllamaGenerateRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
        }
        if request.system:
            payload["system"] = request.system
        if request.options:
            payload["options"] = request.options
        if request.format_json:
            payload["format"] = "json"
        return payload

    def _validate_response(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise AIResponseValidationError("La respuesta de Ollama no es un objeto")
        if not isinstance(data.get("response"), str):
            raise AIResponseValidationError("La respuesta de Ollama no contiene texto")
        return data

    def _to_result(
        self, data: dict[str, Any], fallback_model: str
    ) -> OllamaGenerateResult:
        return OllamaGenerateResult(
            text=data["response"],
            model=str(data.get("model") or fallback_model),
            total_duration_ns=self._optional_int(data.get("total_duration")),
            prompt_eval_count=self._optional_int(data.get("prompt_eval_count")),
            eval_count=self._optional_int(data.get("eval_count")),
        )

    def _optional_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        return None

    def _backoff_seconds(self, attempt: int) -> float:
        return self._backoff_base_seconds * (2 ** (attempt - 1))

    def _create_client(self) -> httpx.AsyncClient:
        if self._client_factory is not None:
            return self._client_factory()
        return httpx.AsyncClient(timeout=self._timeout_seconds)
