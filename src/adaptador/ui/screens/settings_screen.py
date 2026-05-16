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
        desc.setWordWrap(True)
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


class _StatusBadge(QLabel):
    def __init__(
        self,
        text: str,
        *,
        color: str,
        background: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(104)
        self.setStyleSheet(
            f"background: {background}; color: {color};"
            " border: none; border-radius: 6px; padding: 6px 10px;"
            " font-size: 12px; font-weight: 600;"
        )


def _load_config_values(load_config_func=None) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    """Lee modelo y URL de Ollama desde config/app.yaml."""
    try:
        if load_config_func is None:
            from adaptador.config import load_config as load_config_func

        config = load_config_func()
        return config.ollama.default_model, config.ollama.url
    except Exception:
        return "no disponible", "no disponible"


class SettingsScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsScreen")
        self._setup_ui()

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"font-size: 13px; font-weight: 600;"
            f" color: {COLORS['text_muted']};"
            f" text-transform: uppercase; letter-spacing: 1px;"
        )
        return label

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        header = QLabel("Configuracion")
        header.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        layout.addWidget(header)

        layout.addWidget(self._section_header("General"))

        layout.addWidget(
            _SettingRow(
                "Transcripcion",
                "Disponible para jobs de audio; sin captura de audio en UI todavia",
                _StatusBadge(
                    "Parcial",
                    color=COLORS["warning"],
                    background=COLORS["warning_bg"],
                ),
            )
        )

        layout.addWidget(
            _SettingRow(
                "Enriquecimiento",
                "Procesa la cola persistente de Jobs IA en segundo plano",
                _StatusBadge(
                    "Activo",
                    color=COLORS["success"],
                    background=COLORS["success_bg"],
                ),
            )
        )

        layout.addWidget(
            _SettingRow(
                "Backups",
                "Motor disponible; programacion automatica pendiente",
                _StatusBadge(
                    "Pendiente",
                    color=COLORS["text_muted"],
                    background=COLORS["bg_tertiary"],
                ),
            )
        )

        layout.addSpacing(8)
        layout.addWidget(self._section_header("Inteligencia Artificial"))

        modelo, url_ollama = _load_config_values()
        info_style = (
            f"font-size: 14px; color: {COLORS['text_primary']};"
            f" padding: 14px 16px; background: {COLORS['bg_card']};"
            f" border: 1px solid {COLORS['border']};"
            f" border-radius: 10px;"
        )

        model_label = QLabel(f"Modelo: {modelo}")
        model_label.setStyleSheet(info_style)
        layout.addWidget(model_label)

        url_label = QLabel(f"Servidor: {url_ollama}")
        url_label.setStyleSheet(info_style)
        layout.addWidget(url_label)

        layout.addStretch()

        footer = QLabel("Configuracion cargada desde config/app.yaml al iniciar")
        footer.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']};")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
