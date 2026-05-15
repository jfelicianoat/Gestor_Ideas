from enum import StrEnum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from adaptador.ui.theme import COLORS


class ScreenType(StrEnum):
    IDEAS = auto()
    JOBS = auto()
    REPO = auto()
    KANBAN = auto()
    SETTINGS = auto()


NAV_ITEMS: list[tuple[ScreenType, str, str]] = [
    (ScreenType.IDEAS, "💡", "Ideas"),
    (ScreenType.JOBS, "⚡", "Jobs IA"),
    (ScreenType.REPO, "📚", "Repositorio"),
    (ScreenType.KANBAN, "📋", "Kanban"),
    (ScreenType.SETTINGS, "⚙", "Settings"),
]


class NavButton(QPushButton):
    def __init__(self, screen_type: ScreenType, icon: str, label: str) -> None:
        super().__init__()
        self.screen_type = screen_type
        self._icon = icon
        self._label = label
        self._active = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        icon_label = QLabel(self._icon)
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(icon_label)

        text_label = QLabel(self._label)
        text_label.setStyleSheet(
            "font-size: 13px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(text_label)
        layout.addStretch()

        self._text_label = text_label
        self._icon_label = icon_label
        self._update_style()

    def _update_style(self) -> None:
        if self._active:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS["accent_muted"]};
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {COLORS["accent_muted"]};
                }}
            """
            )
            self._text_label.setStyleSheet(
                f"font-size: 13px; font-weight: 600;"
                f" color: {COLORS['accent']}; background: transparent;"
            )
            self._icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {COLORS["bg_hover"]};
                }}
            """
            )
            self._text_label.setStyleSheet(
                f"font-size: 13px; font-weight: 400;"
                f" color: {COLORS['sidebar_text']}; background: transparent;"
            )
            self._icon_label.setStyleSheet("font-size: 16px; background: transparent;")

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setChecked(active)
        self._update_style()


class Sidebar(QFrame):
    screen_changed = Signal(ScreenType)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self._buttons: dict[ScreenType, NavButton] = {}
        self._active_screen: ScreenType = ScreenType.IDEAS
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(
            f"""
            #sidebar {{
                background-color: {COLORS["sidebar_bg"]};
                border-right: 1px solid {COLORS["border"]};
            }}
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        # App branding
        brand = QLabel("Adaptador de Ideas")
        brand.setStyleSheet(
            f"""
            font-size: 15px;
            font-weight: 700;
            color: {COLORS["text_primary"]};
            padding: 4px 12px 16px 12px;
            background: transparent;
        """
        )
        layout.addWidget(brand)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {COLORS['sidebar_divider']}; margin: 4px 12px;")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # Nav buttons
        for screen_type, icon, label in NAV_ITEMS:
            btn = NavButton(screen_type, icon, label)
            btn.clicked.connect(lambda checked, st=screen_type: self._on_nav_click(st))
            self._buttons[screen_type] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Version
        version = QLabel("v0.1.0")
        version.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']};"
            f" padding: 8px 12px; background: transparent;"
        )
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

    def _on_nav_click(self, screen_type: ScreenType) -> None:
        self.set_active_screen(screen_type)
        self.screen_changed.emit(screen_type)

    def set_active_screen(self, screen_type: ScreenType) -> None:
        self._active_screen = screen_type
        for st, btn in self._buttons.items():
            btn.set_active(st == screen_type)
