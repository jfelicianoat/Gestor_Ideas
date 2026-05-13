"""
Tema visual soft-dark para el Gestor de Ideas.

Define la paleta de colores y la hoja de estilos QSS que se
aplica a toda la aplicación PySide6. Basado en tonos oscuros
suaves con acentos en azul-índigo para una estética moderna.

Referencia: CONTEXT_PACK.md §12 (UI moderna soft-dark)
"""

# --- Paleta de colores ---
# Colores organizados por función semántica

COLORS = {
    # Fondos
    "bg_primary": "#1E1E2E",       # Fondo principal de la ventana
    "bg_secondary": "#2A2A3C",     # Paneles, tarjetas, sidebars
    "bg_tertiary": "#333347",      # Inputs, campos de texto
    "bg_hover": "#3A3A50",         # Estado hover de elementos
    "bg_selected": "#44446A",      # Estado seleccionado

    # Texto
    "text_primary": "#E0E0EC",     # Texto principal
    "text_secondary": "#A0A0B8",   # Texto secundario, placeholders
    "text_muted": "#6E6E8A",       # Texto deshabilitado

    # Acentos
    "accent": "#7C6FE0",           # Color de acento principal (índigo suave)
    "accent_hover": "#9589E8",     # Acento en hover
    "accent_pressed": "#6359C0",   # Acento al presionar

    # Estado
    "success": "#5CB87A",          # Operaciones exitosas
    "warning": "#E0A85C",          # Advertencias
    "error": "#E05C6F",            # Errores
    "info": "#5CA8E0",             # Información

    # Bordes
    "border": "#3A3A50",           # Bordes generales
    "border_focus": "#7C6FE0",     # Bordes al enfocar un input

    # Kanban (colores para columnas)
    "kanban_nueva": "#5CA8E0",
    "kanban_en_proceso": "#E0A85C",
    "kanban_revision": "#9589E8",
    "kanban_archivada": "#6E6E8A",
}


def build_stylesheet() -> str:
    """
    Construye la hoja de estilos QSS para la aplicación.

    Returns:
        String QSS completo con todos los estilos aplicados.
    """
    c = COLORS
    return f"""
    /* ===== Base ===== */
    QMainWindow {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
    }}

    QWidget {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}

    /* ===== Barra de menú ===== */
    QMenuBar {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border-bottom: 1px solid {c["border"]};
        padding: 2px;
    }}

    QMenuBar::item:selected {{
        background-color: {c["bg_hover"]};
        border-radius: 4px;
    }}

    QMenu {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 4px;
    }}

    QMenu::item:selected {{
        background-color: {c["accent"]};
        color: white;
        border-radius: 4px;
    }}

    /* ===== Barra de estado ===== */
    QStatusBar {{
        background-color: {c["bg_secondary"]};
        color: {c["text_secondary"]};
        border-top: 1px solid {c["border"]};
        font-size: 12px;
    }}

    /* ===== Labels ===== */
    QLabel {{
        color: {c["text_primary"]};
        background-color: transparent;
    }}

    /* ===== Botones ===== */
    QPushButton {{
        background-color: {c["accent"]};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 13px;
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

    /* ===== Inputs de texto ===== */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 10px;
        selection-background-color: {c["accent"]};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c["border_focus"]};
    }}

    /* ===== ScrollBars ===== */
    QScrollBar:vertical {{
        background-color: {c["bg_primary"]};
        width: 10px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c["bg_hover"]};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c["text_muted"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {c["bg_primary"]};
        height: 10px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c["bg_hover"]};
        border-radius: 5px;
        min-width: 30px;
    }}

    /* ===== Separadores ===== */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {c["border"]};
    }}

    /* ===== ToolTips ===== */
    QToolTip {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    """
