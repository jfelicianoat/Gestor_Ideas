"""
Tests de smoke para la interfaz de usuario.

Validan que los componentes UI se instancian sin error.
Usan QApplication headless (sin ventana visible) para
funcionar en entornos CI sin display.
"""

import pytest
from PySide6.QtWidgets import QApplication

from adaptador.ui.main_window import MainWindow
from adaptador.ui.theme import COLORS, build_stylesheet


@pytest.fixture(scope="module")
def qapp():
    """
    QApplication compartida para todos los tests del módulo.

    PySide6 solo permite una instancia de QApplication por proceso.
    Se reutiliza la existente si ya fue creada.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTheme:
    """Tests del tema visual soft-dark."""

    def test_colors_tiene_claves_esenciales(self) -> None:
        """La paleta tiene todos los colores necesarios."""
        claves_requeridas = [
            "bg_primary", "bg_secondary", "bg_tertiary",
            "text_primary", "text_secondary",
            "accent", "accent_hover",
            "success", "warning", "error",
            "border", "border_focus",
        ]
        for clave in claves_requeridas:
            assert clave in COLORS, f"Falta color: {clave}"

    def test_colors_son_hex_validos(self) -> None:
        """Todos los colores son códigos hex de 7 caracteres."""
        for nombre, valor in COLORS.items():
            assert valor.startswith("#"), f"{nombre} no es hex: {valor}"
            assert len(valor) == 7, f"{nombre} no tiene 7 chars: {valor}"

    def test_stylesheet_genera_string_no_vacio(self) -> None:
        """build_stylesheet() devuelve una hoja de estilos no vacía."""
        css = build_stylesheet()
        assert isinstance(css, str)
        assert len(css) > 100
        assert "QMainWindow" in css


class TestMainWindow:
    """Tests de instanciación de la ventana principal."""

    def test_ventana_se_instancia(self, qapp) -> None:
        """MainWindow se crea sin excepción."""
        window = MainWindow()
        assert window is not None

    def test_titulo_correcto(self, qapp) -> None:
        """La ventana tiene el título esperado."""
        window = MainWindow()
        assert "Gestor de Ideas" in window.windowTitle()

    def test_dimensiones_minimas(self, qapp) -> None:
        """La ventana tiene las dimensiones mínimas configuradas."""
        window = MainWindow()
        assert window.minimumWidth() >= 800
        assert window.minimumHeight() >= 600

    def test_tiene_barra_de_estado(self, qapp) -> None:
        """La ventana tiene barra de estado con mensaje."""
        window = MainWindow()
        status = window.statusBar()
        assert status is not None

    def test_tiene_menu_bar(self, qapp) -> None:
        """La ventana tiene barra de menú configurada."""
        window = MainWindow()
        menu = window.menuBar()
        assert menu is not None
