"""
Componente visual de Columna Kanban.

Representa una columna del tablero Kanban (ej. "Nuevas", "En Proceso").
Contiene un título con un contador y un área scrollable donde se
apilan dinámicamente las tarjetas (IdeaCard).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from adaptador.domain.enums import EstadoKanban
from adaptador.ui.kanban.idea_card import IdeaCard
from adaptador.ui.theme import COLORS


class KanbanColumn(QWidget):
    """
    Widget que agrupa tarjetas de ideas de un mismo estado.
    """

    def __init__(self, estado: EstadoKanban) -> None:
        """
        Inicializa la columna para un estado específico.

        Args:
            estado: El estado Kanban que representa esta columna.
        """
        super().__init__()
        self.estado = estado
        self._tarjetas: list[IdeaCard] = []

        self._setup_ui()

    def _get_color_for_estado(self) -> str:
        """Devuelve el color semántico asociado al estado actual."""
        color_map = {
            EstadoKanban.NUEVA: COLORS["kanban_nueva"],
            EstadoKanban.EN_PROCESO: COLORS["kanban_en_proceso"],
            EstadoKanban.REVISION: COLORS["kanban_revision"],
            EstadoKanban.ARCHIVADA: COLORS["kanban_archivada"],
        }
        return color_map.get(self.estado, COLORS["border"])

    def _setup_ui(self) -> None:
        """Configura el layout principal de la columna."""
        # Layout principal de la columna
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # 1. Cabecera (Título y Contador)
        header_frame = QFrame()
        header_frame.setObjectName("columnHeader")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 12, 12, 12)

        titulo_limpio = self.estado.value.replace("_", " ").upper()
        self.lbl_titulo = QLabel(titulo_limpio)

        # Estilizar el texto del título con el color del estado
        color_estado = self._get_color_for_estado()
        self.lbl_titulo.setStyleSheet(
            f"font-weight: bold; "
            f"font-size: 14px; "
            f"color: {color_estado}; "
            f"background-color: transparent;"
        )

        self.lbl_contador = QLabel("0 tarjetas")
        self.lbl_contador.setStyleSheet(
            f"color: {COLORS['text_muted']}; "
            f"font-size: 11px; "
            f"background-color: transparent;"
        )

        header_layout.addWidget(self.lbl_titulo)
        header_layout.addWidget(self.lbl_contador)

        # Estilo del frame de cabecera
        header_frame.setStyleSheet(f"""
            #columnHeader {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-top: 3px solid {color_estado};
                border-radius: 6px;
            }}
        """)

        # 2. Área de scroll para las tarjetas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        # Contenedor interno del scroll area
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        # Layout interno donde irán las tarjetas
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setContentsMargins(0, 4, 0, 4)
        self.cards_layout.setSpacing(8)

        self.scroll_area.setWidget(self.scroll_content)

        # Agregar cabecera y área de scroll al layout de la columna
        main_layout.addWidget(header_frame)
        main_layout.addWidget(self.scroll_area)

    def add_card(self, card: IdeaCard) -> None:
        """
        Añade una tarjeta a la columna y actualiza el contador.

        Args:
            card: Instancia de IdeaCard a añadir.
        """
        self.cards_layout.addWidget(card)
        self._tarjetas.append(card)
        self._update_counter()

    def clear_cards(self) -> None:
        """Elimina todas las tarjetas de la columna."""
        # Remover widgets del layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._tarjetas.clear()
        self._update_counter()

    def _update_counter(self) -> None:
        """Actualiza el texto del contador de tarjetas."""
        count = len(self._tarjetas)
        self.lbl_contador.setText(f"{count} tarjeta{'s' if count != 1 else ''}")
