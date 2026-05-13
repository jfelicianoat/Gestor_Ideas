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


def main() -> None:
    """Función principal de arranque de la aplicación."""
    # Configurar logger antes de cualquier otra cosa
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>",
    )

    logger.info("Iniciando Gestor de Ideas v0.1.0")

    # Cargar configuración
    from adaptador.config import ConfigError, load_config

    config_path = Path("config/app.yaml")
    try:
        config = load_config(config_path)
        logger.info(f"Configuración cargada desde {config_path}")
    except ConfigError as e:
        logger.error(f"Error al cargar configuración: {e}")
        sys.exit(1)

    # Inicializar base de datos
    from adaptador.db.engine import create_engine, create_tables

    db_path = Path(config.database.path)
    engine = create_engine(db_path)
    create_tables(engine)
    logger.info(f"Base de datos inicializada en {db_path}")

    # Lanzar aplicación PySide6
    from PySide6.QtWidgets import QApplication

    from adaptador.ui.main_window import MainWindow
    from adaptador.ui.theme import build_stylesheet

    app = QApplication(sys.argv)
    app.setApplicationName("Gestor de Ideas")
    app.setApplicationVersion("0.1.0")

    # Aplicar tema soft-dark
    app.setStyleSheet(build_stylesheet())
    logger.info("Tema soft-dark aplicado")

    # Crear y mostrar ventana principal
    window = MainWindow(engine=engine)
    window.show()
    logger.info("Ventana principal visible — aplicación lista")

    # Bucle de eventos
    exit_code = app.exec()

    # Limpieza
    engine.dispose()
    logger.info("Aplicación cerrada correctamente")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
