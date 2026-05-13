"""
Ventana principal del Gestor de Ideas.

Contiene la estructura base de la aplicación: barra de menú,
área central con el tablero Kanban y el panel de captura rápida.

Referencia: CONTEXT_PACK.md §12
"""

from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import Session

from adaptador.db.idea_repository import SQLIdeaRepository
from adaptador.domain.entities import Idea
from adaptador.domain.enums import EstadoKanban
from adaptador.ui.kanban.idea_card import IdeaCard
from adaptador.ui.kanban.kanban_column import KanbanColumn
from adaptador.ui.theme import COLORS


class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.

    Estructura de Iteración 1:
    - Barra de menú
    - Panel izquierdo: Formulario de captura rápida
    - Panel derecho: Tablero Kanban
    - Barra de estado
    """

    # Dimensiones por defecto
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800

    def __init__(self, engine: Any = None) -> None:
        """
        Inicializa la ventana principal.

        Args:
            engine: Engine de SQLAlchemy/SQLModel (opcional para tests).
        """
        super().__init__()
        self.engine = engine
        self._setup_window()
        self._setup_menu()
        self._setup_central_widget()
        self._setup_status_bar()
        self._load_ideas()

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
        """Configura el widget central con captura y Kanban."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. Panel Izquierdo: Captura Rápida
        panel_captura = QFrame()
        panel_captura.setObjectName("panelCaptura")
        panel_captura.setStyleSheet(
            f"""
            #panelCaptura {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """
        )
        panel_captura.setFixedWidth(300)

        layout_captura = QVBoxLayout(panel_captura)
        layout_captura.setContentsMargins(16, 16, 16, 16)
        layout_captura.setSpacing(12)

        lbl_captura = QLabel("📝 Captura Rápida")
        lbl_captura.setStyleSheet(
            f"font-size: 16px; font-weight: bold; "
            f"color: {COLORS['accent']}; background: transparent;"
        )

        self.txt_titulo = QLineEdit()
        self.txt_titulo.setPlaceholderText("Título de la idea (opcional)")
        self.txt_titulo.setStyleSheet(
            f"padding: 8px; border: 1px solid {COLORS['border']}; "
            f"border-radius: 4px; background: {COLORS['bg_primary']};"
        )

        self.txt_contenido = QTextEdit()
        self.txt_contenido.setPlaceholderText("Escribe tu idea aquí...")
        self.txt_contenido.setStyleSheet(
            f"padding: 8px; border: 1px solid {COLORS['border']}; "
            f"border-radius: 4px; background: {COLORS['bg_primary']};"
        )

        self.btn_guardar = QPushButton("Guardar Idea")
        self.btn_guardar.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: {COLORS['bg_primary']};
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: #55aaff; }}
        """
        )
        self.btn_guardar.clicked.connect(self._on_guardar_click)

        layout_captura.addWidget(lbl_captura)
        layout_captura.addWidget(self.txt_titulo)
        layout_captura.addWidget(self.txt_contenido)
        layout_captura.addWidget(self.btn_guardar)

        # 2. Panel Derecho: Tablero Kanban
        panel_kanban = QWidget()
        layout_kanban = QHBoxLayout(panel_kanban)
        layout_kanban.setContentsMargins(0, 0, 0, 0)
        layout_kanban.setSpacing(12)

        # Inicializar y guardar las 4 columnas
        self.columnas: dict[EstadoKanban, KanbanColumn] = {}
        for estado in EstadoKanban:
            col = KanbanColumn(estado)
            self.columnas[estado] = col
            layout_kanban.addWidget(col)

        # Agregar paneles al layout principal
        main_layout.addWidget(panel_captura)
        main_layout.addWidget(panel_kanban, stretch=1)

    def _setup_status_bar(self) -> None:
        """Configura la barra de estado."""
        status = QStatusBar(self)
        self.setStatusBar(status)
        status.showMessage("Listo — Base de datos conectada")

    def _on_guardar_click(self) -> None:
        """Crea una idea desde el panel y refresca."""
        if not self.engine:
            QMessageBox.warning(self, "Error", "No hay conexión a la base de datos.")
            return

        contenido = self.txt_contenido.toPlainText().strip()
        if not contenido:
            return  # No hacer nada si está vacío

        idea = Idea(
            titulo=self.txt_titulo.text().strip(),
            contenido_raw=contenido,
        )

        try:
            with Session(self.engine) as session:
                repo = SQLIdeaRepository(session)
                repo.create(idea)

            # Limpiar el formulario si fue exitoso
            self.txt_titulo.clear()
            self.txt_contenido.clear()
            self._load_ideas()
            self.statusBar().showMessage(f"Idea guardada: {idea.id}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo guardar la idea:\n{str(e)}"
            )

    def _load_ideas(self) -> None:
        """Carga las ideas de la BD y refresca el tablero Kanban."""
        if not self.engine:
            return

        # Limpiar columnas
        for col in self.columnas.values():
            col.clear_cards()

        try:
            with Session(self.engine) as session:
                repo = SQLIdeaRepository(session)
                for estado in EstadoKanban:
                    ideas = repo.list_by_estado(estado)
                    for idea in ideas:
                        card = IdeaCard(idea, on_avanzar=self._on_avanzar_idea)
                        self.columnas[estado].add_card(card)
        except Exception as e:
            self.statusBar().showMessage(f"Error al cargar ideas: {str(e)}", 5000)

    def _on_avanzar_idea(self, idea: Idea) -> None:
        """Avanza la idea al siguiente estado y actualiza."""
        if not self.engine:
            return

        # Calcular siguiente estado
        estados = list(EstadoKanban)
        idx_actual = estados.index(idea.estado_kanban)
        if idx_actual >= len(estados) - 1:
            return  # Ya está en el último estado

        siguiente_estado = estados[idx_actual + 1]

        try:
            idea.cambiar_estado(siguiente_estado)
            with Session(self.engine) as session:
                repo = SQLIdeaRepository(session)
                repo.update(idea)

            self._load_ideas()
            self.statusBar().showMessage(
                f"Idea movida a {siguiente_estado.value}", 3000
            )
        except Exception as e:
            QMessageBox.warning(self, "Error al mover idea", str(e))

    def _show_about(self) -> None:
        """Muestra información básica de la aplicación."""
        QMessageBox.about(
            self,
            "Acerca de Gestor de Ideas",
            "Gestor de Ideas v0.1.0\n\n"
            "Aplicación desktop para captura, transcripción\n"
            "y enriquecimiento de ideas con IA local.\n\n"
            "Stack: PySide6 · SQLite · Ollama · faster-whisper",
        )
