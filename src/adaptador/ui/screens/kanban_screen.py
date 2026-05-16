from typing import Any

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from adaptador.domain.enums import EstadoKanban
from adaptador.ui.components.state_view import StateView
from adaptador.ui.kanban.kanban_column import KanbanColumn
from adaptador.ui.theme import COLORS


class KanbanScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("kanbanScreen")
        self._columnas: dict[EstadoKanban, KanbanColumn] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("Kanban")
        header.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        layout.addWidget(header)

        self._state_view = StateView()
        layout.addWidget(self._state_view, stretch=1)

        # Content: Kanban board
        content = QWidget()
        board_layout = QHBoxLayout(content)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(12)

        for estado in EstadoKanban:
            col = KanbanColumn(estado)
            col.card_dropped.connect(self._on_card_dropped)
            self._columnas[estado] = col
            board_layout.addWidget(col)

        self._state_view.set_content_widget(content)

    @property
    def columnas(self) -> dict[EstadoKanban, KanbanColumn]:
        return self._columnas

    def set_services(self, idea_service: Any) -> None:
        """Asigna el servicio de ideas y recarga el tablero."""
        self._idea_service = idea_service
        self._load_data()

    def _load_data(self) -> None:
        if not hasattr(self, "_idea_service"):
            return

        self._state_view.show_state(
            StateView.LOADING,
            title="Cargando Kanban...",
            description="Organizando tus ideas.",
        )

        try:
            # Cargar ideas para cada estado
            hay_ideas = False
            for estado, col in self._columnas.items():
                ideas = self._idea_service.list_by_estado(estado)
                if ideas:
                    hay_ideas = True
                
                # Se delega la recreación/actualización al componente, 
                # que recicla los widgets si el ID coincide.
                col.set_ideas(ideas)

            if hay_ideas:
                self._state_view.show_state(StateView.CONTENT)
            else:
                self._state_view.show_state(
                    StateView.EMPTY,
                    title="Tablero vacío",
                    description="No hay ideas en el sistema.",
                    icon="📋",
                )
        except Exception:
            for col in self._columnas.values():
                col.clear_cards()
            self._state_view.show_state(
                StateView.ERROR,
                title="Error al cargar",
                description="No se pudieron cargar las ideas.",
            )

    def _on_card_dropped(self, idea_id: str, nuevo_estado: EstadoKanban) -> None:
        """Maneja el drop de una tarjeta en una nueva columna."""
        if not hasattr(self, "_idea_service"):
            return
        from uuid import UUID

        try:
            self._idea_service.move_idea(UUID(idea_id), nuevo_estado)
            self._load_data()
        except Exception:
            # Revertir recargando los datos
            self._load_data()
