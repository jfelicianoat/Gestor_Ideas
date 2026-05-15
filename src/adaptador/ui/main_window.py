from collections.abc import Callable
from typing import Any

from loguru import logger
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from adaptador.ai.job_handler import AIJobHandler
from adaptador.ai.metrics import JobMetrics
from adaptador.ai.ollama_client import AsyncOllamaClient
from adaptador.ai.whisper_transcriber import FasterWhisperTranscriber
from adaptador.config import load_config
from adaptador.db.idea_repository import SQLIdeaRepository
from adaptador.db.job_repository import SQLJobRepository
from adaptador.services.idea_service import IdeaService
from adaptador.services.job_runner import AsyncJobRunner
from adaptador.services.job_service import JobService
from adaptador.ui.components.animations import fade_in
from adaptador.ui.navigation.sidebar import ScreenType, Sidebar
from adaptador.ui.screens import (
    IdeasScreen,
    JobsScreen,
    KanbanScreen,
    RepoScreen,
    SettingsScreen,
)
from adaptador.ui.theme import COLORS


class MainWindow(QMainWindow):
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 820

    def __init__(self, engine: Any = None) -> None:
        super().__init__()
        self.engine = engine
        self._screens: dict[ScreenType, QWidget] = {}
        self._services_inited = False
        self._setup_window()
        self._setup_menu()
        self._init_services()
        self._setup_central_widget()
        self._setup_status_bar()
        self._navigate_to(ScreenType.IDEAS)

    # ── Helpers de sesión (session-per-operation) ──────────────

    def _create_services(self) -> tuple[IdeaService, JobService, Any]:
        """Crea servicios con sesión fresca.

        Returns:
            Tupla (idea_svc, job_svc, session).
        """
        from sqlmodel import Session

        session = Session(self.engine)
        idea_repo = SQLIdeaRepository(session)
        job_repo = SQLJobRepository(session)
        idea_svc = IdeaService(idea_repository=idea_repo)
        job_svc = JobService(job_repository=job_repo, idea_repository=idea_repo)
        return idea_svc, job_svc, session

    def _init_services(self) -> None:
        """Inicializa servicios y recupera jobs huérfanos al arrancar."""
        if not self.engine:
            return

        # Sesión efímera solo para recovery al arranque
        idea_svc, job_svc, session = self._create_services()
        try:
            job_svc.recover_in_progress_jobs()
        finally:
            session.close()

        # Crear servicios de vida larga para las pantallas de UI.
        # Cada refresh de pantalla renovará la sesión via _refresh_services().
        self._refresh_services()

        # _job_runner es un Callable factory, NO una instancia de AsyncJobRunner.
        # _JobProcessor en jobs_screen.py invoca el callable para crear
        # un runner + sesión independiente para el hilo de procesamiento.
        self._job_runner: Callable[[], tuple[AsyncJobRunner, Callable]] | None = None
        try:
            load_config()
            self._job_runner = self._build_job_runner
        except Exception as e:
            logger.warning("Runner IA no disponible: {}", e)

        self._services_inited = True

    def _refresh_services(self) -> None:
        """Renueva la sesión y los servicios para evitar datos stale."""
        # Cerrar sesión anterior si existe
        if hasattr(self, "_ui_session") and self._ui_session is not None:
            try:
                self._ui_session.close()
            except Exception:
                pass

        idea_svc, job_svc, session = self._create_services()
        self._idea_service = idea_svc
        self._job_service = job_svc
        self._ui_session = session

    def _build_job_runner(self) -> tuple[AsyncJobRunner, Any]:
        if not self.engine:
            raise RuntimeError("Engine no disponible")

        from sqlmodel import Session

        session = Session(self.engine)
        idea_repo = SQLIdeaRepository(session)
        job_repo = SQLJobRepository(session)
        # Servicios dedicados para el hilo de procesamiento
        idea_service = IdeaService(idea_repository=idea_repo)
        job_service = JobService(
            job_repository=job_repo,
            idea_repository=idea_repo,
        )
        job_service.recover_in_progress_jobs()

        config = load_config()
        ollama = AsyncOllamaClient(
            base_url=config.ollama.url,
            timeout_seconds=config.ollama.timeout_seconds,
            max_retries=config.jobs.max_retries,
            backoff_base_seconds=config.jobs.backoff_base_seconds,
        )
        transcriber = FasterWhisperTranscriber(
            model_size=config.whisper.model_size,
        )
        handler = AIJobHandler(
            idea_repository=idea_repo,
            ollama_client=ollama,
            transcriber=transcriber,
            default_model=config.ollama.default_model,
        )
        runner = AsyncJobRunner(
            job_service,
            handler,
            JobMetrics(),
            idea_service=idea_service,
        )
        return runner, session.close

    def _setup_window(self) -> None:
        self.setWindowTitle("Adaptador de Ideas")
        self.setMinimumSize(900, 640)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

    def _setup_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        archivo = menu_bar.addMenu("&Archivo")
        archivo.addAction("&Salir", self.close)

        ayuda = menu_bar.addMenu("A&yuda")
        ayuda.addAction("&Acerca de", self._show_about)

    def _setup_central_widget(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.screen_changed.connect(self._on_navigate)
        layout.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {COLORS['bg_primary']};")
        layout.addWidget(self._stack, stretch=1)

        self._register_screens()

    def _register_screens(self) -> None:
        ideas_screen = IdeasScreen()
        jobs_screen = JobsScreen()
        kanban_screen = KanbanScreen()
        if self._services_inited:
            ideas_screen.set_services(self._idea_service, self._job_service)
            jobs_screen.set_services(
                self._job_service, self._idea_service, self._job_runner
            )
            kanban_screen.set_services(self._idea_service)

        screens: list[tuple[ScreenType, QWidget]] = [
            (ScreenType.IDEAS, ideas_screen),
            (ScreenType.JOBS, jobs_screen),
            (ScreenType.REPO, RepoScreen()),
            (ScreenType.KANBAN, kanban_screen),
            (ScreenType.SETTINGS, SettingsScreen()),
        ]
        for screen_type, widget in screens:
            self._screens[screen_type] = widget
            self._stack.addWidget(widget)

    # Se refresca la sesión antes de cada navegación para evitar datos stale
    def _on_navigate(self, screen_type: ScreenType) -> None:
        """Renueva la sesión y delega la navegación."""
        if self._services_inited:
            self._refresh_services()
            # Actualizar referencias en las pantallas que usan servicios
            ideas = self._screens.get(ScreenType.IDEAS)
            if isinstance(ideas, IdeasScreen):
                ideas.set_services(self._idea_service, self._job_service)
            jobs = self._screens.get(ScreenType.JOBS)
            if isinstance(jobs, JobsScreen):
                jobs.set_services(
                    self._job_service, self._idea_service, self._job_runner
                )
            kanban = self._screens.get(ScreenType.KANBAN)
            if isinstance(kanban, KanbanScreen):
                kanban.set_services(self._idea_service)
        self._navigate_to(screen_type)

    def _navigate_to(self, screen_type: ScreenType) -> None:
        self._sidebar.set_active_screen(screen_type)
        widget = self._screens.get(screen_type)
        if widget:
            self._stack.setCurrentWidget(widget)
            fade_in(self._stack, 200)

        names = {
            ScreenType.IDEAS: "Ideas",
            ScreenType.JOBS: "Jobs IA",
            ScreenType.REPO: "Repositorio",
            ScreenType.KANBAN: "Kanban",
            ScreenType.SETTINGS: "Settings",
        }
        status_bar = self.statusBar()
        if status_bar:
            status_bar.showMessage(f"Pantalla: {names.get(screen_type, '')}", 2000)

    def _setup_status_bar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        status.showMessage("Listo")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de Adaptador de Ideas",
            "Adaptador de Ideas v0.1.0\n\n"
            "Aplicación desktop para captura, transcripción\n"
            "y enriquecimiento de ideas con IA local.\n\n"
            "Stack: PySide6 · SQLite · Ollama · faster-whisper",
        )

    def get_screen(self, screen_type: ScreenType) -> QWidget | None:
        return self._screens.get(screen_type)

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        """Espera al hilo de procesamiento y cierra la sesión."""
        # Verificar si hay un job en curso
        jobs_screen = self._screens.get(ScreenType.JOBS)
        processor_running = False
        if isinstance(jobs_screen, JobsScreen):
            processor = getattr(jobs_screen, "_processor", None)
            if processor is not None and processor.isRunning():
                processor_running = True

        # Confirmar cierre si hay procesamiento activo
        if processor_running:
            reply = QMessageBox.question(
                self,
                "Procesamiento en curso",
                "Hay un job de IA en curso.\n"
                "Si cierras ahora, el job se"
                " recuperará al reiniciar.\n\n"
                "¿Cerrar de todos modos?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            # Esperar al hilo con timeout de 3 segundos
            if processor is not None:
                processor.requestInterruption()
                if not processor.wait(3000):
                    logger.warning(
                        "Hilo de procesamiento no terminó"
                        " en 3s, forzando cierre"
                    )

        # Cerrar sesión de UI
        if hasattr(self, "_ui_session") and self._ui_session:
            try:
                self._ui_session.close()
            except Exception:
                pass
            self._ui_session = None

        super().closeEvent(event)
