"""
Tests unitarios de los repositorios SQL.

Cubre:
- CRUD de IdeaRepository (create, get_by_id, list_by_estado, update)
- CRUD de JobRepository (create, get_by_id, list_pending, update)
- Mapeo correcto entre entidades de dominio y modelos ORM
- Manejo de errores (update de entidad inexistente)
"""

import pytest

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
# Tests del repositorio de Ideas
# ============================================================


class TestSQLIdeaRepository:
    """Tests CRUD del repositorio de Ideas."""

    def test_create_y_get_by_id(self, db_session) -> None:
        """Una idea creada puede recuperarse por su ID."""
        repo = SQLIdeaRepository(db_session)
        idea = Idea(
            titulo="Idea de prueba",
            contenido_raw="Contenido original",
            tipo_entrada=TipoEntrada.TEXTO,
        )

        created = repo.create(idea)
        assert created.id == idea.id
        assert created.titulo == "Idea de prueba"

        found = repo.get_by_id(idea.id)
        assert found is not None
        assert found.titulo == "Idea de prueba"
        assert found.estado_kanban == EstadoKanban.NUEVA

    def test_get_by_id_inexistente(self, db_session) -> None:
        """get_by_id devuelve None si la idea no existe."""
        from uuid import uuid4

        repo = SQLIdeaRepository(db_session)
        assert repo.get_by_id(uuid4()) is None

    def test_list_by_estado(self, db_session) -> None:
        """list_by_estado filtra correctamente por EstadoKanban."""
        repo = SQLIdeaRepository(db_session)

        # Crear ideas en distintos estados
        idea1 = Idea(titulo="Nueva 1", estado_kanban=EstadoKanban.NUEVA)
        idea2 = Idea(titulo="Nueva 2", estado_kanban=EstadoKanban.NUEVA)
        idea3 = Idea(titulo="En proceso", estado_kanban=EstadoKanban.EN_PROCESO)
        repo.create(idea1)
        repo.create(idea2)
        repo.create(idea3)

        nuevas = repo.list_by_estado(EstadoKanban.NUEVA)
        assert len(nuevas) == 2

        en_proceso = repo.list_by_estado(EstadoKanban.EN_PROCESO)
        assert len(en_proceso) == 1
        assert en_proceso[0].titulo == "En proceso"

        archivadas = repo.list_by_estado(EstadoKanban.ARCHIVADA)
        assert len(archivadas) == 0

    def test_update_idea(self, db_session) -> None:
        """update modifica los datos y devuelve la entidad actualizada."""
        repo = SQLIdeaRepository(db_session)
        idea = Idea(titulo="Título original", contenido_raw="Texto")
        repo.create(idea)

        # Modificar la entidad
        idea.titulo = "Título modificado"
        idea.contenido_enriquecido = "Texto enriquecido por IA"
        idea.cambiar_estado(EstadoKanban.EN_PROCESO)

        updated = repo.update(idea)
        assert updated.titulo == "Título modificado"
        assert updated.contenido_enriquecido == "Texto enriquecido por IA"
        assert updated.estado_kanban == EstadoKanban.EN_PROCESO

        # Verificar que persiste en BD
        found = repo.get_by_id(idea.id)
        assert found is not None
        assert found.titulo == "Título modificado"

    def test_update_idea_inexistente(self, db_session) -> None:
        """update lanza ValueError si la idea no existe."""
        repo = SQLIdeaRepository(db_session)
        idea = Idea(titulo="Fantasma")

        with pytest.raises(ValueError, match="no encontrada"):
            repo.update(idea)

    def test_mapeo_tipo_entrada_preservado(self, db_session) -> None:
        """El tipo de entrada se serializa y deserializa correctamente."""
        repo = SQLIdeaRepository(db_session)

        for tipo in TipoEntrada:
            idea = Idea(titulo=f"Idea {tipo.value}", tipo_entrada=tipo)
            repo.create(idea)
            found = repo.get_by_id(idea.id)
            assert found is not None
            assert found.tipo_entrada == tipo


# ============================================================
# Tests del repositorio de Jobs
# ============================================================


class TestSQLJobRepository:
    """Tests CRUD del repositorio de Jobs."""

    def _crear_idea(self, db_session) -> Idea:
        """Helper: crea una idea para asociar jobs."""
        repo_ideas = SQLIdeaRepository(db_session)
        return repo_ideas.create(Idea(titulo="Idea para jobs"))

    def test_create_y_get_by_id(self, db_session) -> None:
        """Un job creado puede recuperarse por su ID."""
        idea = self._crear_idea(db_session)
        repo = SQLJobRepository(db_session)

        job = Job(
            idea_id=idea.id,
            tipo_job=TipoJob.ENRIQUECIMIENTO,
            payload={"prompt": "Enriquece esta idea"},
        )

        created = repo.create(job)
        assert created.id == job.id
        assert created.tipo_job == TipoJob.ENRIQUECIMIENTO
        assert created.payload == {"prompt": "Enriquece esta idea"}

        found = repo.get_by_id(job.id)
        assert found is not None
        assert found.payload == {"prompt": "Enriquece esta idea"}

    def test_get_by_id_inexistente(self, db_session) -> None:
        """get_by_id devuelve None si el job no existe."""
        from uuid import uuid4

        repo = SQLJobRepository(db_session)
        assert repo.get_by_id(uuid4()) is None

    def test_list_pending(self, db_session) -> None:
        """list_pending devuelve solo jobs en estado PENDIENTE."""
        idea = self._crear_idea(db_session)
        repo = SQLJobRepository(db_session)

        job1 = Job(idea_id=idea.id, tipo_job=TipoJob.TRANSCRIPCION)
        job2 = Job(idea_id=idea.id, tipo_job=TipoJob.RESUMEN)
        job3 = Job(
            idea_id=idea.id,
            tipo_job=TipoJob.ENRIQUECIMIENTO,
            estado=EstadoJob.COMPLETADO,
        )
        repo.create(job1)
        repo.create(job2)
        repo.create(job3)

        pending = repo.list_pending()
        assert len(pending) == 2
        assert all(j.estado == EstadoJob.PENDIENTE for j in pending)

    def test_update_job(self, db_session) -> None:
        """update modifica los datos y devuelve la entidad actualizada."""
        idea = self._crear_idea(db_session)
        repo = SQLJobRepository(db_session)

        job = Job(idea_id=idea.id, tipo_job=TipoJob.ENRIQUECIMIENTO)
        repo.create(job)

        # Simular ejecución
        job.cambiar_estado(EstadoJob.EN_CURSO)
        job.registrar_intento()
        job.cambiar_estado(EstadoJob.COMPLETADO)
        job.resultado = "Idea enriquecida exitosamente"

        updated = repo.update(job)
        assert updated.estado == EstadoJob.COMPLETADO
        assert updated.intentos == 1
        assert updated.resultado == "Idea enriquecida exitosamente"

    def test_update_job_inexistente(self, db_session) -> None:
        """update lanza ValueError si el job no existe."""
        idea = self._crear_idea(db_session)
        repo = SQLJobRepository(db_session)
        job = Job(idea_id=idea.id)

        with pytest.raises(ValueError, match="no encontrado"):
            repo.update(job)

    def test_payload_json_roundtrip(self, db_session) -> None:
        """El payload dict se serializa/deserializa correctamente."""
        idea = self._crear_idea(db_session)
        repo = SQLJobRepository(db_session)

        payload_complejo = {
            "prompt": "Analiza esta idea",
            "model": "llama3.2",
            "temperature": 0.7,
            "tags": ["urgente", "revisión"],
        }
        job = Job(
            idea_id=idea.id,
            tipo_job=TipoJob.ETIQUETAS,
            payload=payload_complejo,
        )
        repo.create(job)

        found = repo.get_by_id(job.id)
        assert found is not None
        assert found.payload == payload_complejo
        assert found.payload["tags"] == ["urgente", "revisión"]
