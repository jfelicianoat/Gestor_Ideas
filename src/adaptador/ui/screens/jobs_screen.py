import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from adaptador.domain.enums import EstadoJob, TipoJob
from adaptador.services.idea_service import IdeaService
from adaptador.services.job_service import JobService
from adaptador.ui.components.state_view import StateView
from adaptador.ui.theme import COLORS

_STATUS_COLORS = {
    EstadoJob.PENDIENTE: COLORS["info"],
    EstadoJob.EN_CURSO: COLORS["warning"],
    EstadoJob.COMPLETADO: COLORS["success"],
    EstadoJob.FALLIDO: COLORS["error"],
    EstadoJob.CANCELADO: COLORS["text_muted"],
}

_TIPO_LABELS = {
    TipoJob.TRANSCRIPCION: "Transcripción",
    TipoJob.ENRIQUECIMIENTO: "Enriquecimiento",
    TipoJob.RESUMEN: "Resumen",
    TipoJob.ETIQUETAS: "Etiquetas",
}

_STATUS_LABELS = {
    EstadoJob.PENDIENTE: "Pendiente",
    EstadoJob.EN_CURSO: "En curso",
    EstadoJob.COMPLETADO: "Completado",
    EstadoJob.FALLIDO: "Fallido",
    EstadoJob.CANCELADO: "Cancelado",
}


class _JobCard(QFrame):
    def __init__(
        self,
        job_type: str,
        status: str,
        status_color: str,
        idea_title: str,
        intentos: str = "",
        job_id: UUID | None = None,
        on_delete: Callable[[UUID], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._job_id = job_id
        self.on_delete = on_delete
        self.setObjectName("jobCard")
        self._status_color = status_color
        self._setup_ui(job_type, status, idea_title, intentos)

    def _setup_ui(
        self, job_type: str, status: str, idea_title: str, intentos: str
    ) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        status_dot = QLabel("●")
        status_dot.setStyleSheet(
            f"color: {self._status_color}; font-size: 10px; background: transparent;"
        )
        layout.addWidget(status_dot)

        info = QVBoxLayout()
        info.setSpacing(2)

        type_label = QLabel(job_type)
        type_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600;"
            f" color: {COLORS['text_primary']}; background: transparent;"
        )
        info.addWidget(type_label)

        idea_label = QLabel(idea_title)
        idea_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['text_secondary']};"
            " background: transparent;"
        )
        info.addWidget(idea_label)

        if intentos:
            intentos_label = QLabel(intentos)
            intentos_label.setStyleSheet(
                f"font-size: 11px; color: {COLORS['text_muted']};"
                " background: transparent;"
            )
            info.addWidget(intentos_label)

        layout.addLayout(info, stretch=1)

        status_badge = QLabel(status)
        status_badge.setStyleSheet(
            f"background: {self._status_color}22; color: {self._status_color};"
            " font-size: 11px; font-weight: 600; padding: 4px 10px;"
            " border-radius: 6px;"
        )
        layout.addWidget(status_badge)

        if self._job_id and self.on_delete:
            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(28, 28)
            del_btn.setToolTip("Eliminar job")
            del_btn.setStyleSheet(
                f"QPushButton {{ background: {COLORS['error_bg']};"
                f" color: {COLORS['error']};"
                f" border: none; border-radius: 5px; font-size: 13px; }}"
                f"QPushButton:hover {{ background: {COLORS['error']}; color: white; }}"
            )
            del_btn.clicked.connect(lambda: self.on_delete(self._job_id))
            layout.addWidget(del_btn)

        self.setStyleSheet(
            f"#jobCard {{ background: {COLORS['bg_card']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 10px; }}"
            f"#jobCard:hover {{ background: {COLORS['bg_hover']}; }}"
        )


class _JobProcessor(QThread):
    """Hilo de procesamiento de jobs IA con protección de recursos."""

    finished = Signal()
    failed = Signal(str)

    # Límite de jobs por batch para evitar procesar sin backpressure
    MAX_JOBS_PER_BATCH = 10

    def __init__(self, runner: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner

    def run(self) -> None:
        cleanup: Callable[[], None] | None = None
        try:
            runner = self._runner
            if callable(runner):
                built = runner()
                if isinstance(built, tuple):
                    runner, cleanup = built
                else:
                    runner = built
            asyncio.run(runner.process_pending(limit=self.MAX_JOBS_PER_BATCH))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if cleanup is not None:
                cleanup()
            self.finished.emit()


class JobsScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("jobsScreen")
        self._job_service: JobService | None = None
        self._idea_service: IdeaService | None = None
        self._runner: Any = None
        self._processor: _JobProcessor | None = None
        self._last_process_error: str | None = None
        self._setup_ui()

    def set_services(
        self,
        job_service: JobService,
        idea_service: IdeaService,
        runner: Any = None,
    ) -> None:
        self._job_service = job_service
        self._idea_service = idea_service
        self._runner = runner
        self._load_jobs()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header + process button
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header = QLabel("Jobs IA")
        header.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        header_row.addWidget(header)
        header_row.addStretch()

        self._process_btn = QPushButton("▶ Procesar pendientes")
        self._process_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['accent_secondary']}; color: white;"
            " border: none; border-radius: 8px; padding: 8px 18px;"
            " font-weight: 600; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_secondary_hover']}; }}"
            f"QPushButton:disabled {{ background: {COLORS['bg_tertiary']};"
            f" color: {COLORS['text_muted']}; }}"
        )
        self._process_btn.clicked.connect(self._process_pending)
        header_row.addWidget(self._process_btn)

        layout.addLayout(header_row)

        subtitle = QLabel("Procesamiento de ideas con inteligencia artificial")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
        layout.addWidget(subtitle)

        self._state_view = StateView()
        layout.addWidget(self._state_view, stretch=1)

        # Content: scrollable job list
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._job_list_layout = QVBoxLayout(self._list_widget)
        self._job_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._job_list_layout.setContentsMargins(0, 0, 0, 0)
        self._job_list_layout.setSpacing(8)

        self._scroll.setWidget(self._list_widget)
        content_layout.addWidget(self._scroll)

        self._state_view.set_content_widget(content)

    def add_job_card(self, card: _JobCard) -> None:
        self._job_list_layout.addWidget(card)

    def _process_pending(self) -> None:
        if not self._runner:
            QMessageBox.information(
                self, "Info", "Runner no disponible. Conectá Ollama y reiniciá."
            )
            return

        # Protección contra doble-clic: verificar si ya hay un hilo activo
        if self._processor is not None and self._processor.isRunning():
            QMessageBox.information(
                self, "Info", "Ya hay un procesamiento en curso."
            )
            return

        try:
            pending = self._job_service.list_pending()  # type: ignore[union-attr]
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        if not pending:
            QMessageBox.information(
                self, "Info", "No hay jobs pendientes para procesar."
            )
            return

        self._process_btn.setEnabled(False)
        self._process_btn.setText("Procesando...")
        self._last_process_error = None

        self._processor = _JobProcessor(self._runner)
        self._processor.finished.connect(self._on_process_finished)
        self._processor.failed.connect(self._on_process_failed)
        self._processor.start()

    def _on_process_finished(self) -> None:
        self._process_btn.setEnabled(True)
        self._process_btn.setText("▶ Procesar pendientes")
        if self._last_process_error is None:
            QMessageBox.information(self, "Listo", "Procesamiento completado.")
        self._load_jobs()

    def _on_process_failed(self, message: str) -> None:
        self._last_process_error = message
        QMessageBox.warning(self, "Error", f"Procesamiento incompleto: {message}")

    def _load_jobs(self) -> None:
        if not self._job_service:
            self._state_view.show_state(
                StateView.EMPTY,
                icon="⚡",
                title="Sin conexión",
                description="Servicio de jobs no disponible.",
            )
            return
        self._state_view.show_state(StateView.LOADING, title="Cargando jobs...")
        QTimer.singleShot(0, self._do_load)

    def _do_load(self) -> None:
        try:
            all_jobs = self._job_service.job_repository.list_by_estado(  # type: ignore[union-attr]
                EstadoJob.PENDIENTE
            )
            all_jobs += self._job_service.job_repository.list_by_estado(  # type: ignore[union-attr]
                EstadoJob.EN_CURSO
            )
            all_jobs += self._job_service.job_repository.list_by_estado(  # type: ignore[union-attr]
                EstadoJob.COMPLETADO
            )
            all_jobs += self._job_service.job_repository.list_by_estado(  # type: ignore[union-attr]
                EstadoJob.FALLIDO
            )
            all_jobs += self._job_service.job_repository.list_by_estado(  # type: ignore[union-attr]
                EstadoJob.CANCELADO
            )
        except Exception as e:
            self._state_view.show_state(
                StateView.ERROR, title="Error al cargar jobs",
                description=str(e),
            )
            return

        # Clear old items
        while self._job_list_layout.count():
            item = self._job_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for job in all_jobs:
            tipo = _TIPO_LABELS.get(job.tipo_job, job.tipo_job.value.capitalize())
            estado = _STATUS_LABELS.get(job.estado, job.estado.value.capitalize())
            color = _STATUS_COLORS.get(job.estado, COLORS["text_muted"])

            idea_title = self._get_idea_title(job.idea_id)
            intentos = (
                f"Intento {job.intentos}/{job.max_intentos}" if job.intentos > 0 else ""
            )

            card = _JobCard(
                tipo, estado, color, idea_title, intentos,
                job_id=job.id, on_delete=self._on_delete_job,
            )
            self.add_job_card(card)

        if not all_jobs:
            self._state_view.show_state(
                StateView.EMPTY, icon="⚡", title="Sin jobs",
                description="No hay jobs todavía.",
            )
        else:
            self._state_view.show_state(StateView.CONTENT)

    def _on_delete_job(self, job_id: UUID) -> None:
        if not self._job_service:
            return
        try:
            self._job_service.delete_job(job_id)
            self._load_jobs()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Error", f"No se pudo eliminar el job: {e}")

    def _get_idea_title(self, idea_id: Any) -> str:
        if not self._idea_service:
            return str(idea_id)[:8]
        try:
            idea = self._idea_service.get_idea_or_raise(idea_id)
            return idea.titulo if idea.titulo else str(idea_id)[:8]
        except Exception:
            return str(idea_id)[:8]
