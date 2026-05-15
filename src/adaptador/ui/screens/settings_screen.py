from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from adaptador.ui.theme import COLORS


class _SettingRow(QFrame):
    def __init__(
        self,
        label: str,
        description: str,
        widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingRow")
        self._setup_ui(label, description, widget)

    def _setup_ui(self, label: str, description: str, widget: QWidget) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        title = QLabel(label)
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 600;"
            f" color: {COLORS['text_primary']}; background: transparent;"
        )
        text_container.addWidget(title)

        desc = QLabel(description)
        desc.setStyleSheet(
            f"font-size: 12px;"
            f" color: {COLORS['text_secondary']}; background: transparent;"
        )
        text_container.addWidget(desc)

        layout.addLayout(text_container, stretch=1)
        layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignRight)

        self.setStyleSheet(
            f"""
            #settingRow {{
                background: {COLORS["bg_card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
            }}
        """
        )


class _SimpleSwitch(QFrame):
    def __init__(
        self, checked: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self) -> None:
        bg = COLORS["accent"] if self._checked else COLORS["bg_tertiary"]
        self.setStyleSheet(
            f"""
            background: {bg};
            border-radius: 12px;
            border: none;
        """
        )


def _load_config_values() -> tuple[str, str]:
    """Lee modelo y URL de Ollama desde config/app.yaml.

    Returns:
        Tupla (modelo, url) con valores reales o fallback.
    """
    try:
        from adaptador.config import load_config

        config = load_config()
        return config.ollama.default_model, config.ollama.url
    except Exception:
        return "no disponible", "no disponible"


class SettingsScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsScreen")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        header = QLabel("Configuración")
        header.setStyleSheet(
            f"font-size: 22px; font-weight: 700;"
            f" color: {COLORS['text_primary']};"
        )
        layout.addWidget(header)

        # Sección General
        general_header = QLabel("General")
        general_header.setStyleSheet(
            f"font-size: 13px; font-weight: 600;"
            f" color: {COLORS['text_muted']};"
            f" text-transform: uppercase; letter-spacing: 1px;"
        )
        layout.addWidget(general_header)

        layout.addWidget(
            _SettingRow(
                "Transcripción",
                "Activar transcripción automática de audio",
                _SimpleSwitch(True),
            )
        )

        layout.addWidget(
            _SettingRow(
                "Enriquecimiento",
                "Enriquecer ideas con IA automáticamente",
                _SimpleSwitch(True),
            )
        )

        layout.addWidget(
            _SettingRow(
                "Backups",
                "Realizar backups automáticos periódicos",
                _SimpleSwitch(True),
            )
        )

        # Sección IA — valores reales de app.yaml
        ia_header = QLabel("Inteligencia Artificial")
        ia_header.setStyleSheet(
            f"font-size: 13px; font-weight: 600;"
            f" color: {COLORS['text_muted']};"
            f" text-transform: uppercase; letter-spacing: 1px;"
        )
        layout.addSpacing(8)
        layout.addWidget(ia_header)

        modelo, url_ollama = _load_config_values()
        _info_style = (
            f"font-size: 14px; color: {COLORS['text_primary']};"
            f" padding: 14px 16px; background: {COLORS['bg_card']};"
            f" border: 1px solid {COLORS['border']};"
            f" border-radius: 10px;"
        )

        model_label = QLabel(f"Modelo: {modelo}")
        model_label.setStyleSheet(_info_style)
        layout.addWidget(model_label)

        url_label = QLabel(f"Servidor: {url_ollama}")
        url_label.setStyleSheet(_info_style)
        layout.addWidget(url_label)

        layout.addStretch()

        footer = QLabel("Los cambios se aplican automáticamente")
        footer.setStyleSheet(
            f"font-size: 12px; color: {COLORS['text_muted']};"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
