"""Tests unitarios de servicios de aplicación."""

import asyncio
from uuid import UUID, uuid4

import pytest

from adaptador.domain.entities import Idea, Job
from adaptador.domain.enums import EstadoJob, EstadoKanban, TipoEntrada, TipoJob
from adaptador.services.errors import (
    ApplicationStateError,
    EntityNotFoundError,
    PersistenceOperationError,
    ValidationAppError,
)
from adaptador.services.idea_service import IdeaService
from adaptador.services.job_runner import AsyncJobRunner
from adaptador.services.job_service import JobService


class FakeIdeaRepository:
    """Repositorio fake en memoria para tests de servicios."""

    def __init__(self) -> None:
        self.items: dict[UUID, Idea] = {}
        self.fail_next_update = False

    def create(self, idea: Idea) -> Idea:
        self.items[idea.id] = idea
        return idea

    def get_by_id(self, idea_id: UUID) -> Idea | None:
        return self.items.get(idea_id)

    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        return [idea for idea in self.items.values() if idea.estado_kanban == estado]

    def update(self, idea: Idea) -> Idea:
        if self.fail_next_update:
            self.fail_next_update = False
            raise ValueError("fallo simulado")
        if idea.id not in self.items:
            raise ValueError("idea no encontrada")
        self.items[idea.id] = idea
        return idea


class FakeJobRepository:
    """Repositorio fake en memoria para tests de servicios."""

    def __init__(self) -> None:
        self.items: dict[UUID, Job] = {}
        self.fail_next_update = False

    def create(self, job: Job) -> Job:
        self.items[job.id] = job
        return job

    def get_by_id(self, job_id: UUID) -> Job | None:
        return self.items.get(job_id)

    def list_pending(self) -> list[Job]:
        return [job for job in self.items.values() if job.estado == EstadoJob.PENDIENTE]

    def update(self, job: Job) -> Job:
        if self.fail_next_update:
            self.fail_next_update = False
            raise ValueError("fallo simulado")
        if job.id not in self.items:
            raise ValueError("job no encontrado")
        self.items[job.id] = job
        return job


class TestIdeaService:
    """Casos de uso de ideas."""

    def test_create_idea_valida_y_persiste(self) -> None:
        repo = FakeIdeaRepository()
        service = IdeaService(repo)

        idea = service.create_idea(
            titulo="  Captura  ",
            contenido_raw="  Texto original  ",
            tipo_entrada=TipoEntrada.TEXTO,
        )

        assert idea.id in repo.items
        assert idea.titulo == "Captura"
        assert idea.contenido_raw == "Texto original"
        assert idea.estado_kanban == EstadoKanban.NUEVA

    def test_create_idea_rechaza_contenido_vacio(self) -> None:
        service = IdeaService(FakeIdeaRepository())

        with pytest.raises(ValidationAppError):
            service.create_idea(titulo="Idea", contenido_raw=" ")

    def test_move_idea_respeta_transiciones_de_dominio(self) -> None:
        repo = FakeIdeaRepository()
        idea = repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        service = IdeaService(repo)

        moved = service.move_idea(idea.id, EstadoKanban.EN_PROCESO)

        assert moved.estado_kanban == EstadoKanban.EN_PROCESO

    def test_move_idea_inexistente_lanza_error_explicito(self) -> None:
        service = IdeaService(FakeIdeaRepository())

        with pytest.raises(EntityNotFoundError):
            service.move_idea(uuid4(), EstadoKanban.EN_PROCESO)

    def test_move_idea_invalida_traduce_error_de_dominio(self) -> None:
        repo = FakeIdeaRepository()
        idea = repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        service = IdeaService(repo)

        with pytest.raises(ApplicationStateError):
            service.move_idea(idea.id, EstadoKanban.ARCHIVADA)

    def test_set_enriched_content_persiste_resultado(self) -> None:
        repo = FakeIdeaRepository()
        idea = repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        service = IdeaService(repo)

        updated = service.set_enriched_content(idea.id, " Resultado IA ")

        assert updated.contenido_enriquecido == "Resultado IA"

    def test_error_de_persistencia_se_traduce(self) -> None:
        repo = FakeIdeaRepository()
        idea = repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        repo.fail_next_update = True
        service = IdeaService(repo)

        with pytest.raises(PersistenceOperationError):
            service.set_enriched_content(idea.id, "Resultado")


class TestJobService:
    """Casos de uso de jobs."""

    def test_enqueue_job_valida_idea_y_persiste_pendiente(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        service = JobService(job_repo, idea_repo)

        job = service.enqueue_job(
            idea_id=idea.id,
            tipo_job=TipoJob.ENRIQUECIMIENTO,
            payload={"prompt": "Analiza"},
            max_intentos=2,
            timeout_segundos=30,
        )

        assert job.id in job_repo.items
        assert job.estado == EstadoJob.PENDIENTE
        assert job.payload == {"prompt": "Analiza"}
        assert job.max_intentos == 2

    def test_enqueue_job_rechaza_idea_inexistente(self) -> None:
        service = JobService(FakeJobRepository(), FakeIdeaRepository())

        with pytest.raises(EntityNotFoundError):
            service.enqueue_job(idea_id=uuid4(), tipo_job=TipoJob.RESUMEN)

    def test_start_job_cambia_estado_y_registra_intento(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        job = job_repo.create(Job(idea_id=idea.id))
        service = JobService(job_repo, idea_repo)

        started = service.start_job(job.id)

        assert started.estado == EstadoJob.EN_CURSO
        assert started.intentos == 1

    def test_complete_job_guarda_resultado(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        job = job_repo.create(Job(idea_id=idea.id))
        service = JobService(job_repo, idea_repo)

        started = service.start_job(job.id)
        completed = service.complete_job(started.id, " Resultado ")

        assert completed.estado == EstadoJob.COMPLETADO
        assert completed.resultado == "Resultado"

    def test_fail_job_reencola_si_quedan_intentos(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        job = job_repo.create(Job(idea_id=idea.id, max_intentos=2))
        service = JobService(job_repo, idea_repo)

        started = service.start_job(job.id)
        failed = service.fail_job(started.id, "Ollama timeout")

        assert failed.estado == EstadoJob.PENDIENTE
        assert failed.resultado == "Ollama timeout"
        assert failed.intentos == 1

    def test_fail_job_permanece_fallido_si_agota_intentos(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        job = job_repo.create(Job(idea_id=idea.id, max_intentos=1))
        service = JobService(job_repo, idea_repo)

        started = service.start_job(job.id)
        failed = service.fail_job(started.id, "Error permanente")

        assert failed.estado == EstadoJob.FALLIDO
        assert failed.resultado == "Error permanente"

    def test_cancel_job_solo_permite_pendiente(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        job = job_repo.create(Job(idea_id=idea.id))
        service = JobService(job_repo, idea_repo)

        canceled = service.cancel_job(job.id)

        assert canceled.estado == EstadoJob.CANCELADO

    def test_complete_job_sin_iniciar_traduce_error_de_estado(self) -> None:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        job = job_repo.create(Job(idea_id=idea.id))
        service = JobService(job_repo, idea_repo)

        with pytest.raises(ApplicationStateError):
            service.complete_job(job.id, "Resultado")


class SuccessfulHandler:
    """Handler async fake que completa jobs."""

    async def handle(self, job: Job) -> str:
        return f"procesado:{job.id}"


class FailingHandler:
    """Handler async fake que falla jobs."""

    async def handle(self, job: Job) -> str:
        raise RuntimeError("fallo de integración")


class TestAsyncJobRunner:
    """Procesamiento asíncrono desacoplado de jobs."""

    def _build_service(self) -> tuple[JobService, Idea, FakeJobRepository]:
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="Idea", contenido_raw="Texto"))
        return JobService(job_repo, idea_repo), idea, job_repo

    def test_process_one_completa_job_con_handler_exitoso(self) -> None:
        service, idea, job_repo = self._build_service()
        job = job_repo.create(Job(idea_id=idea.id))
        runner = AsyncJobRunner(service, SuccessfulHandler())

        processed = asyncio.run(runner.process_one(job.id))

        assert processed.estado == EstadoJob.COMPLETADO
        assert processed.resultado == f"procesado:{job.id}"
        assert processed.intentos == 1

    def test_process_one_reencola_job_si_handler_falla(self) -> None:
        service, idea, job_repo = self._build_service()
        job = job_repo.create(Job(idea_id=idea.id, max_intentos=2))
        runner = AsyncJobRunner(service, FailingHandler())

        processed = asyncio.run(runner.process_one(job.id))

        assert processed.estado == EstadoJob.PENDIENTE
        assert processed.resultado == "fallo de integración"
        assert processed.intentos == 1

    def test_process_pending_respeta_limit(self) -> None:
        service, idea, job_repo = self._build_service()
        first = job_repo.create(Job(idea_id=idea.id))
        second = job_repo.create(Job(idea_id=idea.id))
        runner = AsyncJobRunner(service, SuccessfulHandler())

        processed = asyncio.run(runner.process_pending(limit=1))

        assert [job.id for job in processed] == [first.id]
        assert job_repo.items[first.id].estado == EstadoJob.COMPLETADO
        assert job_repo.items[second.id].estado == EstadoJob.PENDIENTE
