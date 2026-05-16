from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from adaptador.domain.enums import EstadoKanban
from adaptador.ui.kanban.idea_card import _DND_MIME, IdeaCard
from adaptador.ui.theme import COLORS


class KanbanColumn(QWidget):
    card_dropped = Signal(str, EstadoKanban)

    def __init__(self, estado: EstadoKanban) -> None:
        super().__init__()
        self.estado = estado
        self._tarjetas: list[IdeaCard] = []
        self._setup_ui()
        self.setAcceptDrops(True)

    def _get_color_for_estado(self) -> str:
        color_map = {
            EstadoKanban.NUEVA: COLORS["kanban_nueva"],
            EstadoKanban.EN_PROCESO: COLORS["kanban_en_proceso"],
            EstadoKanban.REVISION: COLORS["kanban_revision"],
            EstadoKanban.ARCHIVADA: COLORS["kanban_archivada"],
        }
        return color_map.get(self.estado, COLORS["border"])

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        header_frame = QFrame()
        header_frame.setObjectName("columnHeader")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 12, 12, 12)

        titulo_limpio = self.estado.value.replace("_", " ").upper()
        self.lbl_titulo = QLabel(titulo_limpio)

        color_estado = self._get_color_for_estado()
        self.lbl_titulo.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: %s; background: transparent;"
            % color_estado
        )

        self.lbl_contador = QLabel("0 tarjetas")
        self.lbl_contador.setStyleSheet(
            "color: %s; font-size: 11px; background: transparent;"
            % COLORS["text_muted"]
        )

        header_layout.addWidget(self.lbl_titulo)
        header_layout.addWidget(self.lbl_contador)

        header_frame.setStyleSheet(
            "#columnHeader { background: %s; border: 1px solid %s;"
            " border-top: 3px solid %s; border-radius: 6px; }"
            % (COLORS["bg_secondary"], COLORS["border"], color_estado)
        )

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: %s;" % COLORS["bg_primary"])

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: %s;" % COLORS["bg_primary"])

        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setContentsMargins(0, 4, 0, 4)
        self.cards_layout.setSpacing(8)

        self.scroll_area.setWidget(self.scroll_content)

        main_layout.addWidget(header_frame)
        main_layout.addWidget(self.scroll_area)

    def add_card(self, card: IdeaCard) -> None:
        self.cards_layout.addWidget(card)
        self._tarjetas.append(card)
        self._update_counter()

    def remove_card(self, idea_id: str) -> None:
        for card in list(self._tarjetas):
            if str(card.idea.id) == idea_id:
                self._tarjetas.remove(card)
                self.cards_layout.removeWidget(card)
                card.setParent(None)
                break
        self._update_counter()

    def clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self._tarjetas.clear()
        self._update_counter()

    def set_ideas(self, ideas: list['Idea'], on_avanzar: Any = None) -> None:
        """Actualiza la lista de ideas, reutilizando widgets existentes."""
        current_map = {card.idea.id: card for card in self._tarjetas}
        new_tarjetas = []
        
        new_ids = {idea.id for idea in ideas}
        for card in self._tarjetas:
            if card.idea.id not in new_ids:
                self.cards_layout.removeWidget(card)
                card.deleteLater()
                
        for idea in ideas:
            if idea.id in current_map:
                card = current_map[idea.id]
                card.update_idea(idea)
                card.on_avanzar = on_avanzar
            else:
                card = IdeaCard(idea, on_avanzar=on_avanzar)
                self.cards_layout.addWidget(card)
            new_tarjetas.append(card)
            
        self._tarjetas = new_tarjetas
        self._update_counter()

    # ---- Drop support ----

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasFormat(_DND_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: Any) -> None:
        if event.mimeData().hasFormat(_DND_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        mime = event.mimeData()
        if not mime.hasFormat(_DND_MIME):
            return

        idea_id = mime.data(_DND_MIME).data().decode("utf-8")
        self.card_dropped.emit(idea_id, self.estado)
        event.acceptProposedAction()

    def _update_counter(self) -> None:
        count = len(self._tarjetas)
        self.lbl_contador.setText(f"{count} tarjeta{'s' if count != 1 else ''}")
