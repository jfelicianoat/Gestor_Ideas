from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from adaptador.ui.components.state_view import StateView
from adaptador.ui.theme import COLORS


class RepoScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("repoScreen")
        self._setup_ui()
        self._simulate_loading()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("Repositorio")
        header.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        layout.addWidget(header)

        subtitle = QLabel("Archivos, PDFs y recursos importados")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
        layout.addWidget(subtitle)

        self._state_view = StateView()
        layout.addWidget(self._state_view, stretch=1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self._state_view.set_content_widget(content)

    def _simulate_loading(self) -> None:
        self._state_view.show_state(
            StateView.LOADING,
            title="Escaneando repositorio...",
            description="Buscando archivos indexados.",
        )
        QTimer.singleShot(
            900,
            lambda: self._state_view.show_state(
                StateView.EMPTY,
                icon="📚",
                title="Repositorio vacío",
                description="Subí archivos desde la pantalla de Ideas.",
            ),
        )
