"""
Tests de smoke de integración entre capas.

Validan que el sistema completo funciona end-to-end:
- Carga de configuración real
- Inicialización del engine con tablas
- CRUD completo a través de repositorios
- Flujo Kanban + Jobs con transiciones de dominio
- Separación estricta de capas (domain sin infraestructura)

Referencia: CONTEXT_PACK.md §11, SKILLS.md §4
"""

import ast
import textwrap
from pathlib import Path

import pytest
from sqlmodel import Session

from adaptador.config import load_config
from adaptador.db.engine import create_engine, create_tables
from adaptador.db.idea_repository import SQLIdeaRepository
from adaptador.db.job_repository import SQLJobRepository
from adaptador.domain.entities import Idea, Job
from adaptador.domain.enums import (
    EstadoJob,
    EstadoKanban,
    TipoEntrada,
    TipoJob,
)

# ============================================================
# Smoke: Flujo completo end-to-end
# ============================================================


class TestFlujoEndToEnd:
    """
    Valida el flujo completo de la aplicación:
    config → engine → tablas → idea → job → transiciones.
    """

    @pytest.fixture
    def env(self, tmp_path):
        """Entorno completo temporal: config, engine, session."""
        # Crear config temporal
        config_yaml = textwrap.dedent(f"""\
            database:
              path: "{(tmp_path / 'test.db').as_posix()}"
            ollama:
              url: "http://localhost:11434"
            jobs:
              max_retries: 2
        """)
        config_file = tmp_path / "app.yaml"
        config_file.write_text(config_yaml, encoding="utf-8")

        # Cargar config
        config = load_config(config_file)

        # Crear engine y tablas
        engine = create_engine(config.database.path)
        create_tables(engine)

        # Crear sesión
        session = Session(engine)

        yield {
            "config": config,
            "engine": engine,
            "session": session,
            "tmp_path": tmp_path,
        }

        session.close()
        engine.dispose()

    def test_flujo_idea_completo(self, env) -> None:
        """
        Smoke: Una idea recorre el flujo completo desde
        captura hasta archivado, pasando por procesamiento IA.
        """
        session = env["session"]
        idea_repo = SQLIdeaRepository(session)
        job_repo = SQLJobRepository(session)

        # 1. Capturar una nueva idea
        idea = Idea(
            titulo="Implementar sistema de backups",
            contenido_raw="Necesito backups automáticos de la BD SQLite",
            tipo_entrada=TipoEntrada.TEXTO,
        )
        idea_persistida = idea_repo.create(idea)
        assert idea_persistida.estado_kanban == EstadoKanban.NUEVA

        # 2. Crear un job de enriquecimiento para la idea
        job = Job(
            idea_id=idea.id,
            tipo_job=TipoJob.ENRIQUECIMIENTO,
            payload={
                "prompt": "Analiza y sugiere mejoras",
                "model": "llama3.2",
            },
            max_intentos=env["config"].jobs.max_retries,
        )
        job_persistido = job_repo.create(job)
        assert job_persistido.estado == EstadoJob.PENDIENTE

        # 3. Verificar que el job aparece en la cola pendiente
        pendientes = job_repo.list_pending()
        assert len(pendientes) >= 1
        assert any(j.id == job.id for j in pendientes)

        # 4. Simular ejecución del job
        job.cambiar_estado(EstadoJob.EN_CURSO)
        job.registrar_intento()
        job.cambiar_estado(EstadoJob.COMPLETADO)
        job.resultado = "La idea es viable. Sugerencia: usar shutil.copy2"
        job_repo.update(job)

        # 5. Verificar que ya no está en pendientes
        pendientes_post = job_repo.list_pending()
        assert not any(j.id == job.id for j in pendientes_post)

        # 6. Avanzar la idea por el Kanban
        idea.contenido_enriquecido = job.resultado
        idea.cambiar_estado(EstadoKanban.EN_PROCESO)
        idea_repo.update(idea)

        idea.cambiar_estado(EstadoKanban.REVISION)
        idea_repo.update(idea)

        idea.cambiar_estado(EstadoKanban.ARCHIVADA)
        idea_repo.update(idea)

        # 7. Verificar estado final
        final = idea_repo.get_by_id(idea.id)
        assert final is not None
        assert final.estado_kanban == EstadoKanban.ARCHIVADA
        assert final.contenido_enriquecido is not None
        assert "shutil" in final.contenido_enriquecido

    def test_flujo_job_con_reintento(self, env) -> None:
        """
        Smoke: Un job falla, reintenta y completa exitosamente.
        """
        session = env["session"]
        idea_repo = SQLIdeaRepository(session)
        job_repo = SQLJobRepository(session)

        idea = idea_repo.create(Idea(titulo="Idea para reintento"))

        job = Job(
            idea_id=idea.id,
            tipo_job=TipoJob.TRANSCRIPCION,
            max_intentos=3,
        )
        job_repo.create(job)

        # Intento 1: falla
        job.cambiar_estado(EstadoJob.EN_CURSO)
        job.registrar_intento()
        job.cambiar_estado(EstadoJob.FALLIDO)
        job.resultado = "Error: modelo no disponible"
        job_repo.update(job)

        assert job.puede_reintentar()

        # Reintento: volver a pendiente
        job.cambiar_estado(EstadoJob.PENDIENTE)
        job_repo.update(job)

        # Intento 2: éxito
        job.cambiar_estado(EstadoJob.EN_CURSO)
        job.registrar_intento()
        job.cambiar_estado(EstadoJob.COMPLETADO)
        job.resultado = "Transcripción completada"
        job_repo.update(job)

        final = job_repo.get_by_id(job.id)
        assert final is not None
        assert final.estado == EstadoJob.COMPLETADO
        assert final.intentos == 2

    def test_multiples_ideas_por_estado(self, env) -> None:
        """
        Smoke: list_by_estado funciona con múltiples ideas en
        distintos estados del Kanban.
        """
        session = env["session"]
        repo = SQLIdeaRepository(session)

        # Crear ideas en distintos estados
        estados = {
            EstadoKanban.NUEVA: 3,
            EstadoKanban.EN_PROCESO: 2,
            EstadoKanban.REVISION: 1,
        }

        for estado, cantidad in estados.items():
            for i in range(cantidad):
                repo.create(
                    Idea(
                        titulo=f"{estado.value} #{i+1}",
                        estado_kanban=estado,
                    )
                )

        # Verificar conteos
        assert len(repo.list_by_estado(EstadoKanban.NUEVA)) == 3
        assert len(repo.list_by_estado(EstadoKanban.EN_PROCESO)) == 2
        assert len(repo.list_by_estado(EstadoKanban.REVISION)) == 1
        assert len(repo.list_by_estado(EstadoKanban.ARCHIVADA)) == 0

    def test_config_cargada_correctamente(self, env) -> None:
        """
        Smoke: La configuración cargada refleja los valores
        del YAML temporal.
        """
        config = env["config"]
        assert config.ollama.url == "http://localhost:11434"
        assert config.jobs.max_retries == 2
        # Los demás son defaults
        assert config.whisper.model_size == "base"
        assert config.backup.max_versions == 10

    def test_payload_json_complejo_persiste(self, env) -> None:
        """
        Smoke: Un payload con estructura JSON compleja
        sobrevive el ciclo create → get_by_id.
        """
        session = env["session"]
        idea_repo = SQLIdeaRepository(session)
        job_repo = SQLJobRepository(session)

        idea = idea_repo.create(Idea(titulo="Payload complejo"))

        payload = {
            "prompt": "Genera etiquetas para esta idea",
            "options": {
                "temperature": 0.3,
                "max_tokens": 200,
                "stop_sequences": ["\n\n"],
            },
            "context": ["línea 1", "línea 2 con ñ y acentos: éàü"],
        }

        job = Job(
            idea_id=idea.id,
            tipo_job=TipoJob.ETIQUETAS,
            payload=payload,
        )
        job_repo.create(job)

        recovered = job_repo.get_by_id(job.id)
        assert recovered is not None
        assert recovered.payload == payload
        assert recovered.payload["options"]["temperature"] == 0.3
        assert "ñ" in recovered.payload["context"][1]


# ============================================================
# Validación de separación de capas
# ============================================================


class TestSeparacionDeCapa:
    """
    Valida que la capa de dominio no importa infraestructura.

    Esto es un invariante arquitectónico crítico:
    domain/ NO puede importar PySide6, SQLModel, httpx, etc.
    """

    # Módulos prohibidos en la capa de dominio
    MODULOS_PROHIBIDOS = {
        "PySide6", "sqlmodel", "sqlalchemy",
        "httpx", "faster_whisper", "loguru",
        "pydub", "pypdf", "yaml",
    }

    def _get_imports_from_file(self, filepath: Path) -> set[str]:
        """Extrae todos los módulos importados de un archivo Python."""
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

        return imports

    def test_domain_no_importa_infraestructura(self) -> None:
        """
        Ningún archivo en domain/ importa módulos de infraestructura.
        """
        domain_dir = Path("src/adaptador/domain")
        assert domain_dir.exists(), f"No existe: {domain_dir}"

        violaciones = []

        for py_file in domain_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            imports = self._get_imports_from_file(py_file)
            forbidden_found = imports & self.MODULOS_PROHIBIDOS

            if forbidden_found:
                violaciones.append(
                    f"{py_file.name}: importa {forbidden_found}"
                )

        assert not violaciones, (
            "Violaciones de separación de capas en domain/:\n"
            + "\n".join(f"  - {v}" for v in violaciones)
        )

    def test_domain_solo_importa_stdlib_y_adaptador(self) -> None:
        """
        Los archivos de domain/ solo importan stdlib y
        otros módulos de adaptador.domain.
        """
        domain_dir = Path("src/adaptador/domain")
        allowed_prefixes = {"adaptador", "dataclasses", "datetime",
                            "enum", "typing", "uuid", "abc",
                            "collections", "pathlib"}

        for py_file in domain_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            imports = self._get_imports_from_file(py_file)

            for imp in imports:
                assert imp in allowed_prefixes, (
                    f"{py_file.name} importa '{imp}' que no está "
                    f"en la lista de módulos permitidos para domain/"
                )


# ============================================================
# Smoke: import chain del main
# ============================================================


class TestMainImports:
    """Verifica que la cadena de imports del main no falla."""

    def test_import_main(self) -> None:
        """El módulo main se puede importar sin excepción."""
        import adaptador.main  # noqa: F401

    def test_import_config(self) -> None:
        """El módulo config se puede importar sin excepción."""
        from adaptador.config import load_config  # noqa: F401

    def test_import_domain(self) -> None:
        """Las entidades de dominio se pueden importar sin excepción."""
        from adaptador.domain.entities import BackupRegistro, Idea, Job  # noqa: F401
        from adaptador.domain.enums import EstadoJob, EstadoKanban  # noqa: F401
        from adaptador.domain.transitions import (  # noqa: F401
            validate_job_transition,
            validate_kanban_transition,
        )

    def test_import_db(self) -> None:
        """Los módulos de persistencia se importan sin excepción."""
        from adaptador.db.engine import create_engine, create_tables  # noqa: F401
        from adaptador.db.idea_repository import SQLIdeaRepository  # noqa: F401
        from adaptador.db.job_repository import SQLJobRepository  # noqa: F401
        from adaptador.db.models import (  # noqa: F401
            BackupRegistroModel,
            IdeaModel,
            JobModel,
        )

    def test_import_ui(self) -> None:
        """Los módulos UI se importan sin excepción."""
        from adaptador.ui.theme import COLORS, build_stylesheet  # noqa: F401
