"""Tests unitarios de integraciones IA sin red ni modelos reales."""

import asyncio
from uuid import UUID

import httpx
import pytest

from adaptador.ai.dto import OllamaGenerateRequest, TranscriptionResult
from adaptador.ai.errors import AIResponseValidationError, AITransientError
from adaptador.ai.job_handler import AIJobHandler
from adaptador.ai.json_validation import parse_json_object
from adaptador.ai.metrics import JobMetrics
from adaptador.ai.ollama_client import AsyncOllamaClient
from adaptador.domain.entities import Idea, Job
from adaptador.domain.enums import EstadoJob, TipoJob
from adaptador.services.job_runner import AsyncJobRunner
from adaptador.services.job_service import JobService


class FakeIdeaRepository:
    """Repositorio de ideas en memoria."""

    def __init__(self) -> None:
        self.items: dict[UUID, Idea] = {}

    def create(self, idea: Idea) -> Idea:
        self.items[idea.id] = idea
        return idea

    def get_by_id(self, idea_id: UUID) -> Idea | None:
        return self.items.get(idea_id)

    def list_by_estado(self, estado):  # type: ignore[no-untyped-def]
        return [idea for idea in self.items.values() if idea.estado_kanban == estado]

    def update(self, idea: Idea) -> Idea:
        self.items[idea.id] = idea
        return idea


class FakeJobRepository:
    """Repositorio de jobs en memoria."""

    def __init__(self) -> None:
        self.items: dict[UUID, Job] = {}

    def create(self, job: Job) -> Job:
        self.items[job.id] = job
        return job

    def get_by_id(self, job_id: UUID) -> Job | None:
        return self.items.get(job_id)

    def list_pending(self) -> list[Job]:
        return [job for job in self.items.values() if job.estado == EstadoJob.PENDIENTE]

    def update(self, job: Job) -> Job:
        self.items[job.id] = job
        return job


class FakeAsyncClient:
    """Cliente async compatible con la parte usada de httpx.AsyncClient."""

    calls = 0
    fail_first = False
    invalid_json = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False

    async def post(self, endpoint: str, json: dict):  # type: ignore[no-untyped-def]
        type(self).calls += 1
        if self.fail_first and type(self).calls == 1:
            request = httpx.Request("POST", endpoint)
            raise httpx.ConnectError("offline", request=request)
        if self.invalid_json:
            request = httpx.Request("POST", endpoint)
            return httpx.Response(200, content=b"not-json", request=request)
        request = httpx.Request("POST", endpoint)
        return httpx.Response(
            200,
            json={
                "model": json["model"],
                "response": '{"tags":["local"]}' if json.get("format") else "ok",
                "eval_count": 3,
            },
            request=request,
        )


class FakeOllama:
    """Cliente Ollama fake para handler."""

    async def generate(self, request: OllamaGenerateRequest):
        return type("Result", (), {"text": f"{request.model}:{request.prompt}"})()

    async def generate_json(self, request: OllamaGenerateRequest):
        result = type("Result", (), {"text": '{"tags":["ia"]}'})()
        return result, {"tags": ["ia"]}


class FakeTranscriber:
    """Transcriptor fake para handler."""

    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        return TranscriptionResult(
            text=f"transcrito:{audio_path}",
            language="es",
            duration_seconds=1.0,
        )


class OfflineHandler:
    """Handler que simula Ollama offline."""

    async def handle(self, job: Job) -> str:
        raise AITransientError("Ollama offline")


def test_parse_json_object_rechaza_texto_no_json() -> None:
    with pytest.raises(AIResponseValidationError):
        parse_json_object("no es json")


def test_ollama_client_reintenta_fallo_transitorio() -> None:
    FakeAsyncClient.calls = 0
    FakeAsyncClient.fail_first = True
    FakeAsyncClient.invalid_json = False
    client = AsyncOllamaClient(
        base_url="http://ollama.local:11434",
        timeout_seconds=1,
        max_retries=1,
        backoff_base_seconds=0,
        client_factory=FakeAsyncClient,
    )

    result = asyncio.run(
        client.generate(OllamaGenerateRequest(prompt="hola", model="llama3.2"))
    )

    assert result.text == "ok"
    assert result.eval_count == 3
    assert FakeAsyncClient.calls == 2


def test_ollama_client_valida_json_generado() -> None:
    FakeAsyncClient.calls = 0
    FakeAsyncClient.fail_first = False
    FakeAsyncClient.invalid_json = False
    client = AsyncOllamaClient(
        base_url="http://ollama.local:11434",
        timeout_seconds=1,
        max_retries=0,
        client_factory=FakeAsyncClient,
    )

    result, parsed = asyncio.run(
        client.generate_json(OllamaGenerateRequest(prompt="tags", model="llama3.2"))
    )

    assert result.text == '{"tags":["local"]}'
    assert parsed == {"tags": ["local"]}


def test_ai_job_handler_ejecuta_transcripcion() -> None:
    idea_repo = FakeIdeaRepository()
    idea = idea_repo.create(Idea(titulo="Audio", contenido_raw=""))
    handler = AIJobHandler(
        idea_repository=idea_repo,
        ollama_client=FakeOllama(),  # type: ignore[arg-type]
        transcriber=FakeTranscriber(),  # type: ignore[arg-type]
        default_model="llama3.2",
    )
    job = Job(
        idea_id=idea.id,
        tipo_job=TipoJob.TRANSCRIPCION,
        payload={"audio_path": "nota.mp3"},
    )

    result = asyncio.run(handler.handle(job))

    assert result == "transcrito:nota.mp3"


def test_ai_job_handler_valida_respuesta_json_de_etiquetas() -> None:
    idea_repo = FakeIdeaRepository()
    idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Genera etiquetas"))
    handler = AIJobHandler(
        idea_repository=idea_repo,
        ollama_client=FakeOllama(),  # type: ignore[arg-type]
        transcriber=FakeTranscriber(),  # type: ignore[arg-type]
        default_model="llama3.2",
    )
    job = Job(idea_id=idea.id, tipo_job=TipoJob.ETIQUETAS)

    result = asyncio.run(handler.handle(job))

    assert result == '{"tags": ["ia"]}'


def test_runner_reencola_job_si_ollama_esta_offline() -> None:
    idea_repo = FakeIdeaRepository()
    job_repo = FakeJobRepository()
    idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="texto"))
    job = job_repo.create(
        Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, max_intentos=2)
    )
    service = JobService(job_repo, idea_repo)
    metrics = JobMetrics()
    runner = AsyncJobRunner(service, OfflineHandler(), metrics)

    processed = asyncio.run(runner.process_one(job.id))

    assert processed.estado == EstadoJob.PENDIENTE
    assert processed.resultado == "Ollama offline"
    assert metrics.snapshot().retried == 1
    assert metrics.snapshot().failed == 1
