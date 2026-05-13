"""
Ventana principal del Gestor de Ideas.

Contiene la estructura base de la aplicación: barra de menú,
área central con mensaje de bienvenida y barra de estado.
Se expandirá en iteraciones posteriores con el tablero Kanban,
panel de entrada y sistema de jobs.

Referencia: CONTEXT_PACK.md §12
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from adaptador.ui.theme import COLORS


class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.

    Estructura mínima de Iteración 0:
    - Barra de menú con opciones básicas
    - Área central con mensaje de bienvenida
    - Barra de estado con información de conexión
    """

    # Dimensiones por defecto
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800

    def __init__(self) -> None:
        super().__init__()
        self._setup_window()
        self._setup_menu()
        self._setup_central_widget()
        self._setup_status_bar()

    def _setup_window(self) -> None:
        """Configura propiedades básicas de la ventana."""
        self.setWindowTitle("Gestor de Ideas — v0.1.0")
        self.setMinimumSize(800, 600)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

    def _setup_menu(self) -> None:
        """Configura la barra de menú con opciones básicas."""
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Menú Archivo
        menu_archivo = menu_bar.addMenu("&Archivo")
        menu_archivo.addAction("&Salir", self.close)

        # Menú Ayuda
        menu_ayuda = menu_bar.addMenu("A&yuda")
        menu_ayuda.addAction("&Acerca de", self._show_about)

    def _setup_central_widget(self) -> None:
        """Configura el widget central con mensaje de bienvenida."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Título de bienvenida
        titulo = QLabel("🧠 Gestor de Ideas")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet(
            f"font-size: 32px; "
            f"font-weight: bold; "
            f"color: {COLORS['accent']}; "
            f"background-color: transparent;"
        )

        # Subtítulo descriptivo
        subtitulo = QLabel(
            "Captura, transcribe y enriquece tus ideas con IA local"
        )
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet(
            f"font-size: 16px; "
            f"color: {COLORS['text_secondary']}; "
            f"background-color: transparent;"
        )

        # Indicador de estado del esqueleto
        estado = QLabel("Iteración 0 — Esqueleto activo ✓")
        estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        estado.setStyleSheet(
            f"font-size: 13px; "
            f"color: {COLORS['success']}; "
            f"background-color: transparent; "
            f"margin-top: 24px;"
        )

        # Atajos de teclado (info)
        atajos_layout = QHBoxLayout()
        atajos_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        atajos = QLabel("Alt+A → Archivo  |  Alt+Y → Ayuda")
        atajos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        atajos.setStyleSheet(
            f"font-size: 11px; "
            f"color: {COLORS['text_muted']}; "
            f"background-color: transparent; "
            f"margin-top: 40px;"
        )
        atajos_layout.addWidget(atajos)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addWidget(estado)
        layout.addLayout(atajos_layout)

    def _setup_status_bar(self) -> None:
        """Configura la barra de estado."""
        status = QStatusBar(self)
        self.setStatusBar(status)
        status.showMessage("Listo — Base de datos conectada")

    def _show_about(self) -> None:
        """Muestra información básica de la aplicación."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "Acerca de Gestor de Ideas",
            "Gestor de Ideas v0.1.0\n\n"
            "Aplicación desktop para captura, transcripción\n"
            "y enriquecimiento de ideas con IA local.\n\n"
            "Stack: PySide6 · SQLite · Ollama · faster-whisper",
        )
