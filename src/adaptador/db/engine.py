"""
Engine SQLite para el Gestor de Ideas.

Configura la conexión con SQLite aplicando pragmas de
confiabilidad (WAL, foreign_keys) y expone funciones
para crear el engine y las tablas iniciales.

Referencia: CONTEXT_PACK.md DA-02, SKILLS.md §3.5
"""

from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, text
from sqlmodel import create_engine as sqlmodel_create_engine


def _apply_sqlite_pragmas(dbapi_conn, connection_record) -> None:  # type: ignore[no-untyped-def]
    """
    Aplica pragmas SQLite al establecerse cada conexión.

    - WAL mode: permite lecturas concurrentes sin bloquear escrituras.
    - foreign_keys: activa la validación de claves foráneas.
    - journal_size_limit: limita el tamaño del WAL a 64MB.
    - busy_timeout: espera hasta 5 segundos ante bloqueo.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_size_limit=67108864")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_engine(db_path: str | Path, echo: bool = False):  # type: ignore[no-untyped-def]
    """
    Crea un engine SQLAlchemy/SQLModel conectado a SQLite.

    Crea el directorio padre del archivo .db si no existe.
    Registra los pragmas de confiabilidad en cada conexión.

    Args:
        db_path: Ruta al archivo de base de datos SQLite.
        echo: Si True, imprime las sentencias SQL ejecutadas.

    Returns:
        Engine configurado con pragmas WAL y foreign_keys.
    """
    path = Path(db_path)
    # Crear directorio padre si no existe
    path.parent.mkdir(parents=True, exist_ok=True)

    url = f"sqlite:///{path}"
    engine = sqlmodel_create_engine(url, echo=echo)

    # Registrar pragmas en cada nueva conexión
    event.listen(engine, "connect", _apply_sqlite_pragmas)

    return engine


def create_tables(engine) -> None:  # type: ignore[no-untyped-def]
    """
    Crea todas las tablas definidas en los modelos SQLModel.

    Debe llamarse después de importar los modelos para que
    SQLModel.metadata contenga las definiciones de tablas.

    Args:
        engine: Engine SQLAlchemy/SQLModel configurado.
    """
    # Importar modelos para registrarlos en el metadata
    import adaptador.db.models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    ensure_performance_indexes(engine)


def ensure_performance_indexes(engine) -> None:  # type: ignore[no-untyped-def]
    """Crea índices idempotentes necesarios para consultas frecuentes."""
    with Session(engine) as session:
        session.exec(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_ideas_estado_kanban ON ideas (estado_kanban)"
            )
        )
        session.exec(text("CREATE INDEX IF NOT EXISTS ix_jobs_estado ON jobs (estado)"))
        session.commit()


def get_session(engine) -> Session:  # type: ignore[no-untyped-def]
    """
    Crea una sesión de base de datos vinculada al engine.

    Args:
        engine: Engine SQLAlchemy/SQLModel configurado.

    Returns:
        Session lista para operaciones de lectura/escritura.
    """
    return Session(engine)
