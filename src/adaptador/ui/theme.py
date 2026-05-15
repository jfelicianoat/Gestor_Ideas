COLORS = {
    # Fondos — tonos más cálidos y suaves estilo Linear/Notion
    "bg_primary": "#1A1A2E",
    "bg_secondary": "#232340",
    "bg_tertiary": "#2C2C4A",
    "bg_hover": "#35355A",
    "bg_selected": "#3D3D6B",
    "bg_card": "#252545",
    # Superficies con opacidad (glass)
    "glass_bg": "rgba(35, 35, 64, 0.85)",
    "glass_border": "rgba(124, 111, 224, 0.15)",
    # Texto
    "text_primary": "#E8E8F0",
    "text_secondary": "#9898B8",
    "text_muted": "#6868A0",
    # Acento principal — índigo suave
    "accent": "#7C6FE0",
    "accent_hover": "#9589E8",
    "accent_pressed": "#6359C0",
    "accent_muted": "rgba(124, 111, 224, 0.15)",
    # Acento secundario — teal suave
    "accent_secondary": "#5CB8B8",
    "accent_secondary_hover": "#6EC8C8",
    # Estados semánticos
    "success": "#5CB87A",
    "success_bg": "rgba(92, 184, 122, 0.12)",
    "warning": "#E0A85C",
    "warning_bg": "rgba(224, 168, 92, 0.12)",
    "error": "#E05C6F",
    "error_bg": "rgba(224, 92, 111, 0.12)",
    "info": "#5CA8E0",
    "info_bg": "rgba(92, 168, 224, 0.12)",
    # Bordes
    "border": "#2E2E52",
    "border_light": "#3A3A60",
    "border_focus": "#7C6FE0",
    # Sombras
    "shadow": "rgba(0, 0, 0, 0.25)",
    "shadow_glow": "rgba(124, 111, 224, 0.2)",
    # Kanban
    "kanban_nueva": "#5CA8E0",
    "kanban_en_proceso": "#E0A85C",
    "kanban_revision": "#9589E8",
    "kanban_archivada": "#6868A0",
    # Sidebar
    "sidebar_bg": "#15152A",
    "sidebar_hover": "#252545",
    "sidebar_active": "#7C6FE0",
    "sidebar_text": "#6868A0",
    "sidebar_text_active": "#E8E8F0",
    "sidebar_divider": "#2E2E52",
}

FONTS = {
    "family": '"Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif',
    "mono": '"Cascadia Code", "Fira Code", "Consolas", monospace',
    "size_xs": "11px",
    "size_sm": "12px",
    "size_base": "13px",
    "size_lg": "15px",
    "size_xl": "18px",
    "size_2xl": "22px",
    "size_3xl": "28px",
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",
}


def build_stylesheet() -> str:
    c = COLORS
    f = FONTS

    return f"""
    QWidget {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
        font-family: {f["family"]};
        font-size: {f["size_base"]};
    }}

    QMainWindow {{
        background-color: {c["bg_primary"]};
    }}

    QMenuBar {{
        background-color: {c["sidebar_bg"]};
        color: {c["text_secondary"]};
        border-bottom: 1px solid {c["border"]};
        padding: 2px 8px;
        font-size: {f["size_sm"]};
    }}

    QMenuBar::item:selected {{
        background-color: {c["bg_hover"]};
        border-radius: 4px;
    }}

    QMenu {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {c["accent"]};
        color: white;
    }}

    QStatusBar {{
        background-color: {c["sidebar_bg"]};
        color: {c["text_muted"]};
        border-top: 1px solid {c["border"]};
        font-size: {f["size_xs"]};
    }}

    QLabel {{
        color: {c["text_primary"]};
        background: transparent;
    }}

    QPushButton {{
        background-color: {c["accent"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: {f["weight_semibold"]};
        font-size: {f["size_sm"]};
    }}

    QPushButton:hover {{
        background-color: {c["accent_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {c["accent_pressed"]};
    }}

    QPushButton:disabled {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_muted"]};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        selection-background-color: {c["accent"]};
        font-size: {f["size_base"]};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c["border_focus"]};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px 0;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c["bg_hover"]};
        border-radius: 3px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c["text_muted"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 0 2px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c["bg_hover"]};
        border-radius: 3px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c["text_muted"]};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QComboBox {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: {f["size_base"]};
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}

    QComboBox:hover {{
        border-color: {c["border_light"]};
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        selection-background-color: {c["accent_muted"]};
        selection-color: {c["text_primary"]};
        padding: 4px;
    }}

    QCheckBox {{
        spacing: 8px;
        color: {c["text_primary"]};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {c["border_light"]};
        background: transparent;
    }}

    QCheckBox::indicator:checked {{
        background-color: {c["accent"]};
        border-color: {c["accent"]};
    }}

    QToolTip {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: {f["size_sm"]};
    }}

    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {c["border"]};
    }}
    """
