from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from adaptador.ui.theme import COLORS


class StateWidget(QWidget):
    def __init__(
        self,
        icon: str = "",
        title: str = "",
        description: str = "",
        action_text: str | None = None,
        action_callback: Callable[[], object] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("stateWidget")
        self._icon = icon
        self._title = title
        self._description = description
        self._action_text = action_text
        self._action_callback = action_callback
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self._icon_label = QLabel(self._icon)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(
            f"font-size: 40px; color: {COLORS['text_muted']};"
        )

        self._title_label = QLabel(self._title)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {COLORS['text_secondary']};"
        )

        self._desc_label = QLabel(self._description)
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(
            f"font-size: 13px; color: {COLORS['text_muted']};"
        )

        layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._desc_label)

        if self._action_text and self._action_callback:
            self._action_btn = QPushButton(self._action_text)
            self._action_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS["accent"]};
                    border: 1px solid {COLORS["accent"]};
                    border-radius: 8px;
                    padding: 8px 24px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {COLORS["accent_muted"]};
                }}
            """
            )
            self._action_btn.clicked.connect(self._action_callback)
            btn_container = QHBoxLayout()
            btn_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_container.addWidget(self._action_btn)
            layout.addLayout(btn_container)

        layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

    def set_icon(self, icon: str) -> None:
        self._icon_label.setText(icon)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_description(self, desc: str) -> None:
        self._desc_label.setText(desc)


class StateView(QFrame):
    LOADING = "loading"
    EMPTY = "empty"
    ERROR = "error"
    SUCCESS = "success"
    CONTENT = "content"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stateView")
        self.setStyleSheet("#stateView { background: transparent; }")

        self._stack = QVBoxLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setSpacing(0)

        self._content_widget: QWidget | None = None
        self._state_widgets: dict[str, StateWidget] = {}

        self._setup_default_states()

    def _setup_default_states(self) -> None:
        self._state_widgets[self.LOADING] = StateWidget(
            icon="⟳",
            title="Cargando...",
            description="Un momento, por favor.",
        )

        self._state_widgets[self.EMPTY] = StateWidget(
            icon="📭",
            title="Sin resultados",
            description="No hay nada aquí todavía.",
        )

        self._state_widgets[self.ERROR] = StateWidget(
            icon="⚠",
            title="Algo salió mal",
            description="Ocurrió un error inesperado.",
        )

        self._state_widgets[self.SUCCESS] = StateWidget(
            icon="✓",
            title="Operación exitosa",
            description="Todo salió bien.",
        )

    def clear(self) -> None:
        while self._stack.count():
            item = self._stack.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.hide()

    def set_content(self, widget: QWidget) -> None:
        self.clear()
        self._content_widget = widget
        self._stack.addWidget(widget)
        widget.show()

    def show_state(self, state: str, **overrides: str) -> None:
        self.clear()
        if state == self.CONTENT and self._content_widget:
            self._content_widget.show()
            self._stack.addWidget(self._content_widget)
            return

        widget = self._state_widgets.get(state)
        if not widget:
            return

        if "icon" in overrides:
            widget.set_icon(overrides["icon"])
        if "title" in overrides:
            widget.set_title(overrides["title"])
        if "description" in overrides:
            widget.set_description(overrides["description"])

        self._stack.addWidget(widget)
        widget.show()

    def set_content_widget(self, widget: QWidget) -> None:
        self._content_widget = widget
