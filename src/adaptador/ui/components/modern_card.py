from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from adaptador.ui.theme import COLORS


class ModernCard(QFrame):
    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        icon: str = "",
        accent_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("modernCard")
        self._title = title
        self._subtitle = subtitle
        self._icon = icon
        self._accent_color = accent_color or COLORS["accent"]

        self._header_widgets: list[QWidget] = []
        self._footer_widgets: list[QWidget] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        if self._icon:
            icon_label = QLabel(self._icon)
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(
                f"""
                background: {COLORS["accent_muted"]};
                color: {self._accent_color};
                font-size: 16px;
                border-radius: 8px;
            """
            )
            header.addWidget(icon_label)

        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        title_label = QLabel(self._title)
        title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']};"
        )
        text_container.addWidget(title_label)

        if self._subtitle:
            sub_label = QLabel(self._subtitle)
            sub_label.setStyleSheet(
                f"font-size: 12px; color: {COLORS['text_secondary']};"
            )
            text_container.addWidget(sub_label)

        header.addLayout(text_container)
        header.addStretch()

        self._header_layout = header

        layout.addLayout(header)

        # Content (placeholder for subclasses)
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(8)
        layout.addLayout(self._content_layout)

        # Footer
        self._footer_layout = QHBoxLayout()
        self._footer_layout.setSpacing(8)
        layout.addLayout(self._footer_layout)

        bg = COLORS["bg_card"]
        border = self._accent_color

        self.setStyleSheet(
            f"""
            #modernCard {{
                background-color: {bg};
                border: 1px solid {COLORS["border"]};
                border-left: 3px solid {border};
                border-radius: 10px;
            }}
            #modernCard:hover {{
                border-color: {COLORS["border_light"]};
                background-color: {COLORS["bg_hover"]};
            }}
        """
        )

    def set_header_widget(self, widget: QWidget) -> None:
        self._header_layout.addWidget(widget)

    def add_content(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def add_footer(self, widget: QWidget) -> None:
        self._footer_layout.addWidget(widget)
