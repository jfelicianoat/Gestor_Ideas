"""
Fixtures compartidas para los tests del Gestor de Ideas.

Provee engine SQLite en memoria y sesiones para tests de
persistencia sin tocar disco.
"""

import pytest
from sqlmodel import Session, SQLModel

from adaptador.db.engine import create_engine


@pytest.fixture
def sqlite_engine(tmp_path):
    """
    Engine SQLite en archivo temporal para tests.

    Crea las tablas automáticamente y destruye al finalizar.
    Se usa archivo temporal en vez de :memory: para validar
    que los pragmas WAL funcionan correctamente.
    """
    db_path = tmp_path / "test.db"
    engine = create_engine(db_path)

    # Importar modelos para registrar en metadata
    import adaptador.db.models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """
    Sesión de base de datos para tests.

    Cada test recibe una sesión limpia con rollback al finalizar
    para evitar contaminación entre tests.
    """
    with Session(sqlite_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="session")
def qapp():
    """
    QApplication compartida para todos los tests de UI.

    PySide6 solo permite una instancia de QApplication por proceso.
    Se reutiliza la existente si ya fue creada.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
