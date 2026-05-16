"""
Punto de entrada principal del Gestor de Ideas.

Responsabilidades:
- Inicializar la aplicación PySide6
- Cargar configuración desde config/app.yaml
- Arrancar el engine de base de datos con WAL
- Crear las tablas si no existen
- Lanzar la ventana principal con tema soft-dark
- Cerrar limpiamente al salir
"""

import sys
from pathlib import Path

from loguru import logger

# ――― PROJECT_ROOT: resuelto contra este archivo, no contra CWD ―――
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _project_path(relative: str) -> Path:
    """Convierte una ruta relativa al proyecto en absoluta."""
    path = Path(relative)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _config_logging() -> None:
    """Configura logging a stderr + archivo rotativo."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>",
    )
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "gestor_ideas_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )
    logger.info(f"Logs en {log_dir}")


_SCHEMA_VERSION = 1


def _check_schema_version(engine) -> None:  # type: ignore[no-untyped-def]
    """Verifica que la versión del schema sea compatible."""
    from sqlmodel import Session, text

    with Session(engine) as session:
        try:
            row = session.exec(
                text("SELECT val FROM _meta WHERE key = 'schema_version'")
            ).one_or_none()
            stored = int(row[0]) if row else 0
        except Exception:
            stored = 0

        if stored > _SCHEMA_VERSION:
            logger.error(
                "Schema versión {} es más nueva que la app (soporta {})",
                stored,
                _SCHEMA_VERSION,
            )
            sys.exit(1)

        if stored < _SCHEMA_VERSION:
            logger.info(
                "Migrando schema de v{} a v{}...", stored, _SCHEMA_VERSION
            )
            _run_migrations(engine, stored)

        session.exec(
            text(
                "CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, val TEXT)"
            )
        )
        session.exec(
            text(
                "INSERT OR REPLACE INTO _meta (key, val) "
                f"VALUES ('schema_version', '{_SCHEMA_VERSION}')"
            )
        )
        session.commit()


def _run_migrations(engine, from_version: int) -> None:  # type: ignore[no-untyped-def]
    """Ejecuta migraciones secuenciales hasta la versión actual."""
    from sqlmodel import Session, text

    with Session(engine) as session:
        for v in range(from_version, _SCHEMA_VERSION):
            logger.info("Ejecutando migración v{} → v{}...", v, v + 1)


def main() -> None:
    """Función principal de arranque de la aplicación."""
    _config_logging()
    logger.info("Iniciando Gestor de Ideas v0.1.0")
    logger.info("Project root: {}", PROJECT_ROOT)

    # Cargar configuración desde el directorio del proyecto
    from adaptador.config import ConfigError, load_config

    config_path = _project_path("config/app.yaml")
    try:
        config = load_config(config_path)
        logger.info(f"Configuración cargada desde {config_path}")
    except ConfigError as e:
        logger.error(f"Error al cargar configuración: {e}")
        sys.exit(1)

    # Inicializar base de datos (paths absolutos contra el proyecto)
    from adaptador.db.engine import create_engine, create_tables

    db_path = _project_path(config.database.path)
    engine = create_engine(db_path)
    create_tables(engine)
    _check_schema_version(engine)
    logger.info(f"Base de datos inicializada en {db_path}")

    # Lanzar aplicación PySide6
    from PySide6.QtWidgets import QApplication

    from adaptador.ui.main_window import MainWindow
    from adaptador.ui.theme import build_stylesheet

    app = QApplication(sys.argv)
    app.setApplicationName("Adaptador de Ideas")
    app.setApplicationVersion("0.1.0")

    app.setStyleSheet(build_stylesheet())
    logger.info("Tema soft-dark aplicado")

    window = MainWindow(engine=engine)
    window.show()
    logger.info("Ventana principal visible — aplicación lista")

    exit_code = app.exec()

    engine.dispose()
    logger.info("Aplicación cerrada correctamente")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
