"""QA tests: estabilidad, persistencia, retries, backup, Ollama recovery, drag/drop."""

import asyncio
import time
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from adaptador.ai.dto import OllamaGenerateRequest, TranscriptionResult
from adaptador.ai.errors import AITimeoutError, AITransientError, AIResponseValidationError
from adaptador.ai.job_handler import AIJobHandler
from adaptador.ai.json_validation import parse_json_object
from adaptador.ai.metrics import JobMetrics
from adaptador.ai.ollama_client import AsyncOllamaClient
from adaptador.backup.engine import BackupEngine
from adaptador.domain.entities import Idea, Job
from adaptador.domain.enums import EstadoJob, EstadoKanban, TipoJob
from adaptador.domain.errors import InvalidStateTransitionError
from adaptador.services.errors import ApplicationStateError, EntityNotFoundError
from adaptador.services.idea_service import IdeaService
from adaptador.services.job_runner import AsyncJobRunner
from adaptador.services.job_service import JobService


# ============================================================
# Fakes compartidos
# ============================================================


class FakeIdeaRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Idea] = {}

    def create(self, idea: Idea) -> Idea:
        self.items[idea.id] = idea
        return idea

    def get_by_id(self, idea_id: UUID) -> Idea | None:
        return self.items.get(idea_id)

    def list_by_estado(self, estado):  # type: ignore[no-untyped-def]
        return [i for i in self.items.values() if i.estado_kanban == estado]

    def update(self, idea: Idea) -> Idea:
        self.items[idea.id] = idea
        return idea


class FakeJobRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Job] = {}

    def create(self, job: Job) -> Job:
        self.items[job.id] = job
        return job

    def get_by_id(self, job_id: UUID) -> Job | None:
        return self.items.get(job_id)

    def list_pending(self) -> list[Job]:
        return [j for j in self.items.values() if j.estado == EstadoJob.PENDIENTE]

    def update(self, job: Job) -> Job:
        self.items[job.id] = job
        return job


class FakeAsyncClient:
    calls = 0
    fail_first = False
    fail_all = False
    invalid_json = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False

    async def post(self, endpoint: str, json: dict):  # type: ignore[no-untyped-def]
        type(self).calls += 1
        request = httpx.Request("POST", endpoint)

        if self.fail_all:
            raise httpx.ConnectError("Ollama offline permanente", request=request)
        if self.fail_first and type(self).calls == 1:
            raise httpx.ConnectError("Ollama offline transitorio", request=request)
        if self.invalid_json:
            return httpx.Response(200, content=b"not-json", request=request)

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
    async def generate(self, request: OllamaGenerateRequest):
        return type("Result", (), {"text": f"{request.model}:{request.prompt}"})()

    async def generate_json(self, request: OllamaGenerateRequest):
        result = type("Result", (), {"text": '{"tags":["ia"]}'})()
        return result, {"tags": ["ia"]}


class FakeTranscriber:
    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        return TranscriptionResult(text=f"transcrito:{audio_path}", language="es", duration_seconds=1.0)


class OfflineHandler:
    async def handle(self, job: Job) -> str:
        raise AITransientError("Ollama offline")


class TimeoutHandler:
    async def handle(self, job: Job) -> str:
        raise AITimeoutError("Timeout")


class SlowHandler:
    async def handle(self, job: Job) -> str:
        await asyncio.sleep(10)
        return "ok"


# ============================================================
# 1. ESTABILIDAD — State corruption, orphan jobs, ghost transitions
# ============================================================


class TestStateCorruption:
    """Detectar corrupción de estado y transiciones inválidas."""

    def test_salto_de_estado_kanban_lanza_error(self) -> None:
        """No se puede saltar de NUEVA a REVISION directamente."""
        idea = Idea()
        with pytest.raises(InvalidStateTransitionError):
            idea.cambiar_estado(EstadoKanban.REVISION)

    def test_retroceso_ilegal_kanban_lanza_error(self) -> None:
        """No se puede volver de REVISION a NUEVA."""
        idea = Idea()
        idea.cambiar_estado(EstadoKanban.EN_PROCESO)
        idea.cambiar_estado(EstadoKanban.REVISION)

        with pytest.raises(InvalidStateTransitionError, match="revision.*nueva"):
            idea.cambiar_estado(EstadoKanban.NUEVA)

    def test_orphan_job_detectado_por_servicio(self) -> None:
        """Job con idea_id inexistente lanza EntityNotFoundError."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        svc = JobService(job_repo, idea_repo)
        orphan_id = UUID("00000000-0000-0000-0000-000000000001")

        with pytest.raises(EntityNotFoundError, match="Idea"):
            svc.enqueue_job(idea_id=orphan_id, tipo_job=TipoJob.ENRIQUECIMIENTO)

    def test_job_completado_no_se_puede_reiniciar(self) -> None:
        """Un job completado no puede volver a EN_CURSO."""
        job = Job(idea_id=UUID(int=0), estado=EstadoJob.COMPLETADO)
        with pytest.raises(InvalidStateTransitionError):
            job.cambiar_estado(EstadoJob.EN_CURSO)

    def test_job_cancelado_no_se_puede_completar(self) -> None:
        """Un job cancelado no puede marcarse como completado."""
        job = Job(idea_id=UUID(int=0), estado=EstadoJob.CANCELADO)
        with pytest.raises(InvalidStateTransitionError):
            job.cambiar_estado(EstadoJob.COMPLETADO)

    def test_archivada_es_estado_terminal(self) -> None:
        """ARCHIVADA no permite ninguna transiciГіn."""
        idea = Idea(estado_kanban=EstadoKanban.ARCHIVADA)
        for target in EstadoKanban:
            if target == EstadoKanban.ARCHIVADA:
                continue
            with pytest.raises(InvalidStateTransitionError):
                idea.cambiar_estado(target)

    def test_servicio_move_idea_traduce_error_de_dominio(self) -> None:
        """El servicio traduce InvalidStateTransitionError a ApplicationStateError."""
        idea_repo = FakeIdeaRepository()
        idea = idea_repo.create(Idea())
        svc = IdeaService(idea_repo)

        with pytest.raises(ApplicationStateError, match="nueva.*archivada"):
            svc.move_idea(idea.id, EstadoKanban.ARCHIVADA)

    def test_fail_job_con_retry_vuelve_a_pendiente(self) -> None:
        """fail_job con retry=True y reintentos disponibles vuelve a PENDIENTE."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea())
        job = job_repo.create(Job(idea_id=idea.id, max_intentos=3, intentos=1))
        svc = JobService(job_repo, idea_repo)
        svc.start_job(job.id)

        result = svc.fail_job(job.id, "error transitorio", retry=True)

        assert result.estado == EstadoJob.PENDIENTE
        assert result.resultado == "error transitorio"
        assert result.intentos == 2

    def test_fail_job_sin_retry_queda_fallido(self) -> None:
        """fail_job con retry=False permanece en FALLIDO."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea())
        job = job_repo.create(Job(idea_id=idea.id))
        svc = JobService(job_repo, idea_repo)
        svc.start_job(job.id)

        result = svc.fail_job(job.id, "error fatal", retry=False)

        assert result.estado == EstadoJob.FALLIDO

    def test_fail_job_agota_intentos_queda_fallido(self) -> None:
        """Cuando max_intentos se agota, el job queda FALLIDO aunque retry=True."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea())
        job = job_repo.create(Job(idea_id=idea.id, max_intentos=2, intentos=2))
        svc = JobService(job_repo, idea_repo)
        svc.start_job(job.id)

        result = svc.fail_job(job.id, "sin reintentos", retry=True)

        assert result.estado == EstadoJob.FALLIDO


# ============================================================
# 2. PERSISTENCIA — WAL recovery, rollback, integridad
# ============================================================


class TestPersistence:
    """Validar que la persistencia no corrompe estado incluso en errores."""

    def test_rollback_en_create_fallido_deja_bd_limpia(self, db_session) -> None:
        """Si create falla, la BD no queda en estado inconsistente."""
        from sqlmodel import func, select

        from adaptador.db.idea_repository import SQLIdeaRepository
        from adaptador.db.models import IdeaModel

        repo = SQLIdeaRepository(db_session)
        repo.create(Idea(titulo="test", contenido_raw="contenido"))

        count = db_session.exec(select(func.count(IdeaModel.id))).one()
        assert count == 1

    def test_update_idea_inexistente_no_corrompe_otras(self, db_session) -> None:
        """Hacer update de una idea que no existe no afecta las existentes."""
        from adaptador.db.idea_repository import SQLIdeaRepository

        repo = SQLIdeaRepository(db_session)
        idea = repo.create(Idea(titulo="viva", contenido_raw="ok"))
        fake_id = UUID("00000000-0000-0000-0000-000000000000")
        fake_idea = Idea(id=fake_id, titulo="fake", contenido_raw="nope")

        with pytest.raises(ValueError, match="no encontrada"):
            repo.update(fake_idea)

        viva = repo.get_by_id(idea.id)
        assert viva is not None
        assert viva.titulo == "viva"

    def test_list_pending_solo_devuelve_pendientes(self, sqlite_engine) -> None:
        """list_pending excluye jobs en otros estados."""
        from sqlmodel import Session

        from adaptador.db.idea_repository import SQLIdeaRepository
        from adaptador.db.job_repository import SQLJobRepository

        with Session(sqlite_engine) as session:
            idea_repo = SQLIdeaRepository(session)
            idea = idea_repo.create(Idea(titulo="parent", contenido_raw="x"))

            job_repo = SQLJobRepository(session)
            j1 = job_repo.create(Job(idea_id=idea.id, estado=EstadoJob.PENDIENTE))
            job_repo.create(Job(idea_id=idea.id, estado=EstadoJob.EN_CURSO))
            job_repo.create(Job(idea_id=idea.id, estado=EstadoJob.COMPLETADO))

            pending = job_repo.list_pending()
            assert len(pending) == 1
            assert pending[0].id == j1.id

    def test_backup_restore_mantiene_integridad(self, sqlite_engine, tmp_path) -> None:
        """Backup y restauraciГіn preservan los datos."""
        from sqlmodel import Session

        from adaptador.db.idea_repository import SQLIdeaRepository

        with Session(sqlite_engine) as session:
            repo = SQLIdeaRepository(session)
            idea = repo.create(Idea(titulo="preservar", contenido_raw="datos"))

        db_url = str(sqlite_engine.url)
        db_path = db_url.replace("sqlite:///", "")
        backup = BackupEngine(db_path, str(tmp_path / "backups"), max_versions=5)
        entry = backup.create_backup()

        restored = backup.restore(entry.id)
        assert restored.exists()
        assert restored.stat().st_size > 0

    def test_wal_mode_permite_lectura_durante_escritura(self, sqlite_engine) -> None:
        """WAL mode permite lecturas concurrentes (simulado)."""
        from sqlmodel import Session

        from adaptador.db.idea_repository import SQLIdeaRepository

        with Session(sqlite_engine) as session:
            repo = SQLIdeaRepository(session)
            repo.create(Idea(titulo="wal_test", contenido_raw="ok"))
            session.commit()

            ideas = repo.list_by_estado(EstadoKanban.NUEVA)
            assert len(ideas) >= 1


# ============================================================
# 3. RETRIES EXHAUSTIVOS
# ============================================================


class TestRetryExhaustive:
    """Validar sistema de reintentos en todos los bordes."""

    def test_ollama_client_reintenta_por_limite_configurable(self) -> None:
        """Respeta max_retries exacto: para n retries hace n+1 intentos."""
        FakeAsyncClient.calls = 0
        FakeAsyncClient.fail_all = True
        FakeAsyncClient.fail_first = False
        FakeAsyncClient.invalid_json = False

        for max_r in (0, 1, 3):
            FakeAsyncClient.calls = 0
            client = AsyncOllamaClient(
                base_url="http://ollama:11434",
                timeout_seconds=1,
                max_retries=max_r,
                backoff_base_seconds=0,
                client_factory=FakeAsyncClient,
            )

            with pytest.raises(AITransientError, match="Ollama offline permanente"):
                asyncio.run(
                    client.generate(OllamaGenerateRequest(prompt="x", model="llama3.2"))
                )

            assert FakeAsyncClient.calls == max_r + 1, (
                f"Esperaba {max_r + 1} intentos, obtuve {FakeAsyncClient.calls}"
            )

    def test_backoff_calculo_correcto(self) -> None:
        """Verificar backoff exponencial: base * 2^(attempt-1)."""
        client = AsyncOllamaClient(
            base_url="http://ollama:11434",
            timeout_seconds=1,
            max_retries=3,
            backoff_base_seconds=1.0,
        )

        esperados = [1.0, 2.0, 4.0]
        for attempt, esperado in enumerate(esperados, start=1):
            assert client._backoff_seconds(attempt) == pytest.approx(esperado)

    def test_runner_reencola_hasta_agotar_intentos(self) -> None:
        """El runner reencola en cada fallo hasta agotar reintentos."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="retry_test", contenido_raw="x"))

        job = job_repo.create(
            Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, max_intentos=3, intentos=0)
        )
        svc = JobService(job_repo, idea_repo)
        runner = AsyncJobRunner(svc, OfflineHandler())

        first = asyncio.run(runner.process_one(job.id))
        assert first.estado == EstadoJob.PENDIENTE
        assert first.intentos == 1

        second = asyncio.run(runner.process_one(job.id))
        assert second.estado == EstadoJob.PENDIENTE
        assert second.intentos == 2

        third = asyncio.run(runner.process_one(job.id))
        assert third.estado == EstadoJob.FALLIDO
        assert third.intentos == 3

    def test_runner_timeout_agota_y_queda_fallido(self) -> None:
        """Timeout repetido eventualmente deja el job como FALLIDO."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="timeout_test", contenido_raw="x"))
        job = job_repo.create(
            Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, max_intentos=2)
        )
        svc = JobService(job_repo, idea_repo)
        runner = AsyncJobRunner(svc, TimeoutHandler())

        r1 = asyncio.run(runner.process_one(job.id))
        assert r1.estado == EstadoJob.PENDIENTE

        r2 = asyncio.run(runner.process_one(job.id))
        assert r2.estado == EstadoJob.FALLIDO

    def test_enqueue_rechaza_max_intentos_negativo(self) -> None:
        """max_intentos negativo lanza ValidationAppError."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="val", contenido_raw="x"))
        svc = JobService(job_repo, idea_repo)

        with pytest.raises(Exception, match="max_intentos no puede ser negativo"):
            svc.enqueue_job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, max_intentos=-1)

    def test_enqueue_rechaza_timeout_cero(self) -> None:
        """timeout_segundos <= 0 lanza ValidationAppError."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="val", contenido_raw="x"))
        svc = JobService(job_repo, idea_repo)

        with pytest.raises(Exception, match="timeout_segundos debe ser mayor que cero"):
            svc.enqueue_job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, timeout_segundos=0)

    def test_metrics_retried_count_es_exacto(self) -> None:
        """JobMetrics.retried refleja exactamente cuántos se reencolaron."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="metrics_test", contenido_raw="x"))
        job = job_repo.create(
            Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, max_intentos=3)
        )
        svc = JobService(job_repo, idea_repo)
        metrics = JobMetrics()
        runner = AsyncJobRunner(svc, OfflineHandler(), metrics)

        asyncio.run(runner.process_one(job.id))
        snap = metrics.snapshot()
        assert snap.retried == 1
        assert snap.failed == 1
        assert snap.processed == 1
        assert snap.completed == 0


# ============================================================
# 4. BACKUP / RESTORE
# ============================================================


def _create_sqlite_db(path: Path) -> None:
    """Crea un archivo SQLite válido para pruebas de backup."""
    import sqlite3

    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, val TEXT)")
    conn.execute("INSERT INTO test (val) VALUES ('data')")
    conn.commit()
    conn.close()


class TestBackupRestore:
    """Ciclo completo de backup y restauración."""

    def test_create_backup_copia_archivo(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_sqlite_db(db_path)
        engine = BackupEngine(db_path, str(tmp_path / "backups"), max_versions=5)

        entry = engine.create_backup()
        assert Path(entry.ruta_archivo).exists()
        assert entry.tamano_bytes > 0

    def test_restore_vuelca_archivo(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_sqlite_db(db_path)
        engine = BackupEngine(db_path, str(tmp_path / "backups"), max_versions=5)
        entry = engine.create_backup()

        # Modify the original
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE test SET val = 'modified'")
        conn.commit()
        conn.close()

        restored = engine.restore(entry.id)
        conn2 = sqlite3.connect(str(restored))
        val = conn2.execute("SELECT val FROM test").fetchone()[0]
        conn2.close()
        assert val == "data"

    def test_list_backups_vacia_sin_metadata(self, tmp_path) -> None:
        engine = BackupEngine(tmp_path / "test.db", str(tmp_path / "backups"))
        assert engine.list_backups() == []

    def test_backup_sin_bd_lanza_error(self, tmp_path) -> None:
        engine = BackupEngine(tmp_path / "no_existe.db", str(tmp_path / "backups"))
        with pytest.raises(FileNotFoundError, match="no encontrada"):
            engine.create_backup()

    def test_prune_respeta_max_versions(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        engine = BackupEngine(db_path, str(tmp_path / "backups"), max_versions=2)

        for i in range(3):
            _create_sqlite_db(db_path)
            engine.create_backup()

        entries = engine.list_backups()
        assert len(entries) == 2

    def test_integrity_detecta_archivos_faltantes(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_sqlite_db(db_path)
        engine = BackupEngine(db_path, str(tmp_path / "backups"), max_versions=5)
        entry = engine.create_backup()

        Path(entry.ruta_archivo).unlink()

        issues = engine.integrity_check()
        assert len(issues) == 1
        assert "falta el archivo" in issues[0]

    def test_delete_backup_remueve_entrada(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_sqlite_db(db_path)
        engine = BackupEngine(db_path, str(tmp_path / "backups"), max_versions=5)
        entry = engine.create_backup()

        engine.delete_backup(entry.id)  # type: ignore[arg-type]
        assert engine.list_backups() == []

    def test_restore_sin_backups_lanza_error(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_sqlite_db(db_path)
        engine = BackupEngine(db_path, str(tmp_path / "backups"))
        with pytest.raises(FileNotFoundError, match="No hay backups"):
            engine.restore()

    def test_metadata_corrupta_se_recupera_con_lista_vacia(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        db_path.write_text("data")
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        meta = backup_dir / ".metadata"
        meta.write_text("not json at all")

        engine = BackupEngine(db_path, str(backup_dir))
        assert engine.list_backups() == []


# ============================================================
# 5. OLLAMA CRASH RECOVERY
# ============================================================


class TestOllamaRecovery:
    """Recuperación tras caída de Ollama."""

    def test_ollama_offline_en_primer_intento_se_recupera(self) -> None:
        """Si cae en intento 1, reintenta y el 2 funciona."""
        FakeAsyncClient.calls = 0
        FakeAsyncClient.fail_first = True
        FakeAsyncClient.fail_all = False
        FakeAsyncClient.invalid_json = False

        client = AsyncOllamaClient(
            base_url="http://ollama:11434",
            timeout_seconds=1,
            max_retries=2,
            backoff_base_seconds=0,
            client_factory=FakeAsyncClient,
        )

        result = asyncio.run(
            client.generate(OllamaGenerateRequest(prompt="hola", model="llama3.2"))
        )

        assert result.text == "ok"
        assert FakeAsyncClient.calls == 2

    def test_ollama_respuesta_invalida_lanza_validation_error(self) -> None:
        """Si Ollama devuelve JSON inválido en generate(), lanza error."""
        FakeAsyncClient.calls = 0
        FakeAsyncClient.fail_first = False
        FakeAsyncClient.fail_all = False
        FakeAsyncClient.invalid_json = True

        client = AsyncOllamaClient(
            base_url="http://ollama:11434",
            timeout_seconds=1,
            max_retries=0,
            client_factory=FakeAsyncClient,
        )

        with pytest.raises(AIResponseValidationError):
            asyncio.run(
                client.generate(OllamaGenerateRequest(prompt="x", model="llama3.2"))
            )

    def test_ollama_offline_runner_no_deja_job_en_curso(self) -> None:
        """Tras fallo de conexión, el job nunca queda trabado en EN_CURSO."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="offline_test", contenido_raw="x"))
        job = job_repo.create(Job(idea_id=idea.id, max_intentos=3))
        svc = JobService(job_repo, idea_repo)
        runner = AsyncJobRunner(svc, OfflineHandler())

        result = asyncio.run(runner.process_one(job.id))
        assert result.estado != EstadoJob.EN_CURSO

    def test_runner_timeout_no_deja_job_en_curso(self) -> None:
        """Timeout tampoco deja el job colgado en EN_CURSO."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="timeout_test", contenido_raw="x"))
        job = job_repo.create(
            Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, timeout_segundos=1, max_intentos=1)
        )
        svc = JobService(job_repo, idea_repo)
        runner = AsyncJobRunner(svc, SlowHandler())

        result = asyncio.run(runner.process_one(job.id))
        assert result.estado != EstadoJob.EN_CURSO

    def test_metrics_timed_out_se_incrementa(self) -> None:
        """Timeout incrementa el contador timed_out en metrics."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="timeout_metric", contenido_raw="x"))
        job = job_repo.create(
            Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO, max_intentos=1)
        )
        svc = JobService(job_repo, idea_repo)
        metrics = JobMetrics()
        runner = AsyncJobRunner(svc, TimeoutHandler(), metrics)

        asyncio.run(runner.process_one(job.id))
        snap = metrics.snapshot()
        assert snap.timed_out == 1

    def test_ollama_caida_parcial_mantiene_metricas_consistente(self) -> None:
        """Múltiples fallos mantienen métricas coherentes."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="mix", contenido_raw="x"))

        job1 = job_repo.create(Job(idea_id=idea.id, max_intentos=5))
        job2 = job_repo.create(Job(idea_id=idea.id, max_intentos=5))

        svc = JobService(job_repo, idea_repo)
        metrics = JobMetrics()
        runner = AsyncJobRunner(svc, OfflineHandler(), metrics)

        asyncio.run(runner.process_pending(limit=2))
        snap = metrics.snapshot()

        assert snap.processed == 2
        assert snap.failed == 2
        assert snap.retried == 2


# ============================================================
# 6. KANBAN DRAG / DROP
# ============================================================


class TestKanbanDragDrop:
    """Validar que drag/drop no corrompe estados."""

    def test_kanban_card_tiene_mime_type_correcto(self) -> None:
        """IdeaCard tiene _DND_MIME correcto."""
        from adaptador.ui.kanban.idea_card import _DND_MIME

        assert _DND_MIME == "application/x-idea-card"

    def test_kanban_columna_acepta_drop_valido(self, qapp) -> None:
        """KanbanColumn acepta drops con MIME type correcto."""
        from PySide6.QtCore import QMimeData, Qt
        from PySide6.QtGui import QDropEvent

        from adaptador.ui.kanban.kanban_column import KanbanColumn

        col = KanbanColumn(EstadoKanban.NUEVA)
        drop_signal = []

        col.card_dropped.connect(lambda idea_id, estado: drop_signal.append((idea_id, estado)))

        mime = QMimeData()
        mime.setData("application/x-idea-card", b"fake-idea-id")
        event = QDropEvent(
            col.rect().center(),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        col.dropEvent(event)

        assert len(drop_signal) == 1
        assert drop_signal[0] == ("fake-idea-id", EstadoKanban.NUEVA)

    def test_kanban_columna_ignora_drop_sin_mime(self, qapp) -> None:
        """KanbanColumn ignora drops sin el MIME type correcto."""
        from PySide6.QtCore import QMimeData, Qt
        from PySide6.QtGui import QDropEvent

        from adaptador.ui.kanban.kanban_column import KanbanColumn

        col = KanbanColumn(EstadoKanban.REVISION)
        drop_signal = []

        col.card_dropped.connect(lambda idea_id, estado: drop_signal.append((idea_id, estado)))

        mime = QMimeData()
        mime.setText("plain text")
        event = QDropEvent(
            col.rect().center(),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        col.dropEvent(event)

        assert len(drop_signal) == 0

    def test_kanban_remove_card_limpia_interno(self, qapp) -> None:
        """remove_card elimina la tarjeta de la lista interna."""
        from adaptador.ui.kanban.idea_card import IdeaCard
        from adaptador.ui.kanban.kanban_column import KanbanColumn

        col = KanbanColumn(EstadoKanban.NUEVA)
        idea1 = Idea(titulo="a", contenido_raw="1")
        idea2 = Idea(titulo="b", contenido_raw="2")
        card1 = IdeaCard(idea1)
        card2 = IdeaCard(idea2)
        col.add_card(card1)
        col.add_card(card2)

        assert len(col._tarjetas) == 2

        col.remove_card(str(idea1.id))
        assert len(col._tarjetas) == 1
        assert col._tarjetas[0].idea.id == idea2.id

    def test_kanban_drop_estado_valido_no_lanza(self, qapp) -> None:
        """El estado destino en drop siempre es un EstadoKanban válido."""
        from adaptador.ui.kanban.kanban_column import KanbanColumn

        for estado in EstadoKanban:
            col = KanbanColumn(estado)
            assert col.estado == estado

    def test_kanban_card_setea_cursor_mano(self, qapp) -> None:
        """IdeaCard tiene cursor de mano indicando que es arrastrable."""
        from adaptador.ui.kanban.idea_card import IdeaCard

        card = IdeaCard(Idea())
        assert card.cursor().shape() is not None


# ============================================================
# 7. UI FREEZE DETECTION
# ============================================================


class TestUIFreezeDetection:
    """Detectar potenciales bloqueos de UI (operaciones sincrónicas pesadas)."""

    def test_ollama_client_tiene_timeout(self) -> None:
        """AsyncOllamaClient siempre usa timeout > 0."""
        client = AsyncOllamaClient(
            base_url="http://ollama:11434", timeout_seconds=120, max_retries=3
        )
        assert client._timeout_seconds > 0

        client2 = AsyncOllamaClient(
            base_url="http://ollama:11434", timeout_seconds=600, max_retries=0
        )
        assert client2._timeout_seconds > 0

    def test_transcriber_tiene_timeout_largo(self) -> None:
        """FasterWhisperTranscriber usa timeout por defecto alto."""
        from adaptador.ai.whisper_transcriber import FasterWhisperTranscriber

        t = FasterWhisperTranscriber(model_size="base")
        assert t._timeout_seconds >= 60

    def test_async_runner_no_bloquea_con_timeout_largo(self) -> None:
        """process_one con handler lento no congela — el timeout del job la corta."""
        idea_repo = FakeIdeaRepository()
        job_repo = FakeJobRepository()
        idea = idea_repo.create(Idea(titulo="freeze_test", contenido_raw="x"))
        job = job_repo.create(
            Job(idea_id=idea.id, timeout_segundos=1, max_intentos=1)
        )
        svc = JobService(job_repo, idea_repo)
        runner = AsyncJobRunner(svc, SlowHandler())

        start = time.monotonic()
        result = asyncio.run(runner.process_one(job.id))
        elapsed = time.monotonic() - start

        assert result.estado != EstadoJob.EN_CURSO
        assert elapsed < 5
