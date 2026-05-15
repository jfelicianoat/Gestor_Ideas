from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QByteArray, QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from adaptador.domain.entities import Idea
from adaptador.ui.theme import COLORS

_DND_MIME = "application/x-idea-card"


class IdeaCard(QFrame):
    MAX_TEXT_LEN = 100

    def __init__(
        self, idea: Idea, on_avanzar: Callable[[Idea], object] | None = None
    ) -> None:
        super().__init__()
        self.idea = idea
        self.on_avanzar = on_avanzar
        self._drag_start_pos = None
        self._setup_ui()

    def _on_avanzar_clicked(self) -> None:
        if self.on_avanzar:
            self.on_avanzar(self.idea)

    def _setup_ui(self) -> None:
        self.setObjectName("ideaCard")
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        titulo_text = self.idea.titulo if self.idea.titulo else "Sin título"
        self.lbl_titulo = QLabel(titulo_text)
        self.lbl_titulo.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {COLORS['text_primary']}; background: transparent;"
        )
        self.lbl_titulo.setWordWrap(True)

        contenido = self.idea.contenido_raw
        if len(contenido) > self.MAX_TEXT_LEN:
            contenido = contenido[: self.MAX_TEXT_LEN] + "..."
        self.lbl_contenido = QLabel(contenido)
        self.lbl_contenido.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; background: transparent;"
        )
        self.lbl_contenido.setWordWrap(True)

        layout_meta = QHBoxLayout()
        layout_meta.setContentsMargins(0, 0, 0, 0)

        fecha_str = self.idea.fecha_creacion.strftime("%Y-%m-%d %H:%M")
        tipo_str = self.idea.tipo_entrada.value.capitalize()
        self.lbl_meta = QLabel(f"📅 {fecha_str} • 🏷️ {tipo_str}")
        self.lbl_meta.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent;"
        )
        layout_meta.addWidget(self.lbl_meta)
        layout_meta.addStretch()

        self.btn_avanzar = QPushButton("▶")
        self.btn_avanzar.setToolTip("Avanzar estado")
        self.btn_avanzar.setFixedSize(24, 24)
        self.btn_avanzar.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_primary']}; color: {COLORS['text_primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {COLORS['accent']}; color: {COLORS['bg_primary']}; }}"
        )
        self.btn_avanzar.clicked.connect(self._on_avanzar_clicked)
        layout_meta.addWidget(self.btn_avanzar)

        layout.addWidget(self.lbl_titulo)
        layout.addWidget(self.lbl_contenido)
        layout.addStretch()
        layout.addLayout(layout_meta)

        self.setStyleSheet(
            f"#ideaCard {{ background: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};"
            f" border-radius: 8px; }}"
            f"#ideaCard:hover {{ border-color: {COLORS['accent']}; background: {COLORS['bg_hover']}; }}"
        )

    # ---- Drag support ----

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self._drag_start_pos is None:
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 10:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_DND_MIME, QByteArray(str(self.idea.id).encode()))
        drag.setMimeData(mime)
        drag.setHotSpot(event.position().toPoint() - self.rect().topLeft())
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event: Any) -> None:
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)
