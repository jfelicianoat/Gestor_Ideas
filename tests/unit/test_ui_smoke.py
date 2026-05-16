"""
Tests de smoke para la interfaz de usuario.

Validan que los componentes UI se instancian sin error.
Usan QApplication headless (sin ventana visible) para
funcionar en entornos CI sin display.
"""

from uuid import UUID

from adaptador.domain.entities import Job
from adaptador.ui.main_window import MainWindow
from adaptador.ui.navigation.sidebar import ScreenType
from adaptador.ui.screens.jobs_screen import JobsScreen, _JobProcessor
from adaptador.ui.theme import COLORS, build_stylesheet


class _FakeProcessor:
    def __init__(self, *, running: bool = True, wait_result: bool = True) -> None:
        self._running = running
        self._wait_result = wait_result
        self.interruption_requested = False
        self.wait_timeout_ms: int | None = None

    def isRunning(self) -> bool:  # noqa: N802
        return self._running

    def requestInterruption(self) -> None:  # noqa: N802
        self.interruption_requested = True

    def wait(self, timeout_ms: int) -> bool:
        self.wait_timeout_ms = timeout_ms
        self._running = False
        return self._wait_result


class _FakeBackgroundWorker(_FakeProcessor):
    pass


class _FakeRunnerJobService:
    def __init__(self, jobs: list[Job]) -> None:
        self._jobs = jobs

    def list_pending(self) -> list[Job]:
        return self._jobs


class _FakeRunner:
    def __init__(self, jobs: list[Job]) -> None:
        self.job_service = _FakeRunnerJobService(jobs)
        self.processed_ids: list[object] = []

    async def process_one(self, job_id: object) -> None:
        self.processed_ids.append(job_id)


class TestTheme:
    """Tests del tema visual soft-dark."""

    def test_colors_tiene_claves_esenciales(self) -> None:
        """La paleta tiene todos los colores necesarios."""
        claves_requeridas = [
            "bg_primary",
            "bg_secondary",
            "bg_tertiary",
            "text_primary",
            "text_secondary",
            "accent",
            "accent_hover",
            "success",
            "warning",
            "error",
            "border",
            "border_focus",
        ]
        for clave in claves_requeridas:
            assert clave in COLORS, f"Falta color: {clave}"

    def test_colors_son_hex_o_rgba_validos(self) -> None:
        """Todos los colores son códigos hex (#xxxxxx) o rgba()."""
        for nombre, valor in COLORS.items():
            assert valor.startswith("#") or valor.startswith("rgba("), (
                f"{nombre} no es hex ni rgba: {valor}"
            )

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
        assert "Adaptador de Ideas" in window.windowTitle()

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

    def test_close_event_cancela_si_hay_processor_y_usuario_rechaza(
        self, qapp, monkeypatch
    ) -> None:
        """El cierre se puede cancelar si hay procesamiento activo."""
        from PySide6.QtGui import QCloseEvent
        from PySide6.QtWidgets import QMessageBox

        window = MainWindow()
        jobs_screen = window.get_screen(ScreenType.JOBS)
        assert isinstance(jobs_screen, JobsScreen)
        processor = _FakeProcessor()
        jobs_screen._processor = processor  # type: ignore[assignment]
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.No,
        )
        event = QCloseEvent()

        window.closeEvent(event)

        assert event.isAccepted() is False
        assert processor.interruption_requested is False
        assert processor.wait_timeout_ms is None

    def test_close_event_interrumpe_y_espera_processor_si_usuario_confirma(
        self, qapp, monkeypatch
    ) -> None:
        """El cierre confirmado pide interrupciÃ³n y espera al QThread."""
        from PySide6.QtGui import QCloseEvent
        from PySide6.QtWidgets import QMessageBox

        window = MainWindow()
        jobs_screen = window.get_screen(ScreenType.JOBS)
        assert isinstance(jobs_screen, JobsScreen)
        processor = _FakeProcessor(wait_result=True)
        jobs_screen._processor = processor  # type: ignore[assignment]
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        event = QCloseEvent()

        window.closeEvent(event)

        assert processor.interruption_requested is True
        assert processor.wait_timeout_ms == 3000

    def test_close_event_detiene_background_worker(self, qapp) -> None:
        """El cierre detiene el worker IA automático."""
        from PySide6.QtGui import QCloseEvent

        window = MainWindow()
        worker = _FakeBackgroundWorker()
        window._background_job_worker = worker  # type: ignore[assignment]
        event = QCloseEvent()

        window.closeEvent(event)

        assert worker.interruption_requested is True
        assert worker.wait_timeout_ms == 3000
        assert window._background_job_worker is None

    def test_job_processor_ejecuta_jobs_en_batch(self, qapp) -> None:
        """El processor ejecuta hasta MAX_JOBS_PER_BATCH jobs."""
        import asyncio

        uid = UUID(int=0)
        jobs = [Job(idea_id=uid), Job(idea_id=uid)]
        runner = _FakeRunner(jobs)
        processor = _JobProcessor(runner)

        asyncio.run(processor._process_until_interrupted(runner))

        assert len(runner.processed_ids) == 2
