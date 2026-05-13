"""
Componente visual de Tarjeta de Idea (IdeaCard).

Representa visualmente una Idea dentro de una columna del tablero Kanban.
Muestra información clave (título, extracto, fecha, tipo) y permite
interacciones básicas (como avanzar a la siguiente columna).
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from adaptador.domain.entities import Idea
from adaptador.ui.theme import COLORS


class IdeaCard(QFrame):
    """
    Widget que renderiza los datos de una Idea como una tarjeta.
    """

    MAX_TEXT_LEN = 100  # Caracteres máximos para el extracto de contenido

    def __init__(self, idea: Idea, on_avanzar: callable | None = None) -> None:
        """
        Inicializa la tarjeta con los datos de una Idea.

        Args:
            idea: Entidad de dominio Idea a mostrar.
            on_avanzar: Callback llamado cuando se presiona el botón avanzar.
        """
        super().__init__()
        self.idea = idea
        self.on_avanzar = on_avanzar
        self._setup_ui()

    def _on_avanzar_clicked(self) -> None:
        """Manejador del clic en el botón de avanzar."""
        if self.on_avanzar:
            self.on_avanzar(self.idea)

    def _setup_ui(self) -> None:
        """Configura el layout y estilos de la tarjeta."""
        self.setObjectName("ideaCard")

        # Layout principal de la tarjeta
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 1. Título de la idea (o "Sin título" si está vacío)
        titulo_text = self.idea.titulo if self.idea.titulo else "Sin título"
        self.lbl_titulo = QLabel(titulo_text)
        self.lbl_titulo.setStyleSheet(
            f"font-weight: bold; "
            f"font-size: 14px; "
            f"color: {COLORS['text_primary']}; "
            f"background-color: transparent;"
        )
        self.lbl_titulo.setWordWrap(True)

        # 2. Extracto del contenido
        contenido = self.idea.contenido_raw
        if len(contenido) > self.MAX_TEXT_LEN:
            contenido = contenido[:self.MAX_TEXT_LEN] + "..."

        self.lbl_contenido = QLabel(contenido)
        self.lbl_contenido.setStyleSheet(
            f"color: {COLORS['text_secondary']}; "
            f"font-size: 12px; "
            f"background-color: transparent;"
        )
        self.lbl_contenido.setWordWrap(True)

        # 3. Metadatos (Fecha y Tipo) y botón avanzar
        layout_meta = QHBoxLayout()
        layout_meta.setContentsMargins(0, 0, 0, 0)

        fecha_str = self.idea.fecha_creacion.strftime("%Y-%m-%d %H:%M")
        tipo_str = self.idea.tipo_entrada.value.capitalize()
        self.lbl_meta = QLabel(f"📅 {fecha_str} • 🏷️ {tipo_str}")
        self.lbl_meta.setStyleSheet(
            f"color: {COLORS['text_muted']}; "
            f"font-size: 11px; "
            f"background-color: transparent;"
        )
        layout_meta.addWidget(self.lbl_meta)
        layout_meta.addStretch()

        self.btn_avanzar = QPushButton("▶")
        self.btn_avanzar.setToolTip("Avanzar estado")
        self.btn_avanzar.setFixedSize(24, 24)
        self.btn_avanzar.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
                color: {COLORS['bg_primary']};
            }}
        """)
        self.btn_avanzar.clicked.connect(self._on_avanzar_clicked)
        layout_meta.addWidget(self.btn_avanzar)

        # Agregar widgets al layout
        layout.addWidget(self.lbl_titulo)
        layout.addWidget(self.lbl_contenido)
        layout.addStretch()  # Empujar meta abajo si la tarjeta es alta
        layout.addLayout(layout_meta)

        # Estilo general del frame (tarjeta)
        self.setStyleSheet(f"""
            #ideaCard {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            #ideaCard:hover {{
                border-color: {COLORS['accent']};
                background-color: {COLORS['bg_hover']};
            }}
        """)
