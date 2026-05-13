"""
Tests unitarios de los modelos SQLModel y el engine SQLite.

Cubre:
- Creación de tablas sin error
- Pragmas WAL y foreign_keys activos
- Inserción y lectura de IdeaModel
- Inserción y lectura de JobModel con FK a IdeaModel
- Inserción y lectura de BackupRegistroModel
- Relación 1-a-muchos entre Idea y Job
"""

from sqlmodel import Session, text

from adaptador.db.models import BackupRegistroModel, IdeaModel, JobModel


class TestEngineYPragmas:
    """Tests de configuración del engine SQLite."""

    def test_tablas_creadas(self, sqlite_engine) -> None:
        """Verifica que las 3 tablas existen tras create_all."""
        with Session(sqlite_engine) as session:
            result = session.exec(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' ORDER BY name"
                )
            )
            tables = [row[0] for row in result]

        assert "ideas" in tables
        assert "jobs" in tables
        assert "backup_registros" in tables

    def test_wal_mode_activo(self, sqlite_engine) -> None:
        """Verifica que el pragma WAL está activado."""
        with Session(sqlite_engine) as session:
            result = session.exec(text("PRAGMA journal_mode"))
            mode = result.one()[0]

        assert mode == "wal"

    def test_foreign_keys_activo(self, sqlite_engine) -> None:
        """Verifica que las foreign keys están habilitadas."""
        with Session(sqlite_engine) as session:
            result = session.exec(text("PRAGMA foreign_keys"))
            fk_enabled = result.one()[0]

        assert fk_enabled == 1


class TestIdeaModel:
    """Tests de persistencia del modelo Idea."""

    def test_crear_idea_minima(self, db_session: Session) -> None:
        """Una idea con campos mínimos se persiste correctamente."""
        idea = IdeaModel(
            titulo="Mi primera idea",
            contenido_raw="Contenido de prueba",
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)

        assert idea.id is not None
        assert len(idea.id) == 36  # UUID string
        assert idea.titulo == "Mi primera idea"
        assert idea.estado_kanban == "nueva"
        assert idea.tipo_entrada == "texto"

    def test_crear_idea_completa(self, db_session: Session) -> None:
        """Una idea con todos los campos se persiste correctamente."""
        idea = IdeaModel(
            titulo="Idea completa",
            contenido_raw="Texto original",
            contenido_enriquecido="Texto mejorado por IA",
            tipo_entrada="pdf",
            estado_kanban="en_proceso",
            archivo_adjunto="/docs/archivo.pdf",
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)

        assert idea.contenido_enriquecido == "Texto mejorado por IA"
        assert idea.tipo_entrada == "pdf"
        assert idea.archivo_adjunto == "/docs/archivo.pdf"

    def test_leer_idea_por_id(self, db_session: Session) -> None:
        """Se puede recuperar una idea por su ID."""
        idea = IdeaModel(titulo="Buscar esta")
        db_session.add(idea)
        db_session.commit()

        found = db_session.get(IdeaModel, idea.id)
        assert found is not None
        assert found.titulo == "Buscar esta"


class TestJobModel:
    """Tests de persistencia del modelo Job."""

    def test_crear_job_con_idea(self, db_session: Session) -> None:
        """Un job se asocia correctamente a una idea existente."""
        idea = IdeaModel(titulo="Idea para job")
        db_session.add(idea)
        db_session.commit()

        job = JobModel(
            idea_id=idea.id,
            tipo_job="enriquecimiento",
            estado="pendiente",
            max_intentos=3,
            timeout_segundos=60,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.id is not None
        assert job.idea_id == idea.id
        assert job.estado == "pendiente"
        assert job.intentos == 0

    def test_relacion_idea_jobs(self, db_session: Session) -> None:
        """La relación 1-a-muchos entre Idea y Job funciona."""
        idea = IdeaModel(titulo="Idea con múltiples jobs")
        db_session.add(idea)
        db_session.commit()

        job1 = JobModel(idea_id=idea.id, tipo_job="transcripcion")
        job2 = JobModel(idea_id=idea.id, tipo_job="enriquecimiento")
        db_session.add(job1)
        db_session.add(job2)
        db_session.commit()

        # Refrescar para cargar la relación
        db_session.refresh(idea)
        assert len(idea.jobs) == 2

    def test_job_referencia_idea(self, db_session: Session) -> None:
        """Un job puede acceder a su idea vía la relación inversa."""
        idea = IdeaModel(titulo="Idea referenciada")
        db_session.add(idea)
        db_session.commit()

        job = JobModel(idea_id=idea.id, tipo_job="resumen")
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.idea is not None
        assert job.idea.titulo == "Idea referenciada"


class TestBackupRegistroModel:
    """Tests de persistencia del modelo BackupRegistro."""

    def test_crear_backup_registro(self, db_session: Session) -> None:
        """Un registro de backup se persiste con ID autoincremental."""
        backup = BackupRegistroModel(
            ruta_archivo="/backups/db_20260513.db",
            tamano_bytes=2048,
        )
        db_session.add(backup)
        db_session.commit()
        db_session.refresh(backup)

        assert backup.id is not None
        assert backup.id >= 1
        assert backup.ruta_archivo == "/backups/db_20260513.db"
        assert backup.tamano_bytes == 2048
        assert backup.fecha_backup is not None
