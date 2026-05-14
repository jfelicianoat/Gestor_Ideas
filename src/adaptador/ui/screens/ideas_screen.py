from collections.abc import Callable
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from adaptador.domain.entities import Idea
from adaptador.domain.enums import EstadoKanban, TipoJob
from adaptador.services.idea_service import IdeaService
from adaptador.services.job_service import JobService
from adaptador.ui.components.state_view import StateView
from adaptador.ui.theme import COLORS


class _CapturePanel(QFrame):
    def __init__(
        self, on_save: Callable[[str, str], None], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.on_save = on_save
        self.setObjectName("capturePanel")
        self.setFixedWidth(340)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(
            f"#capturePanel {{ background: {COLORS['bg_secondary']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 12px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QLabel("Nueva Idea")
        header.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        layout.addWidget(header)

        subtitle = QLabel("Capturá tu idea rápida")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
        layout.addWidget(subtitle)

        self._save_status = QLabel("")
        self._save_status.setStyleSheet(f"font-size: 12px; color: {COLORS['success']};")
        self._save_status.setVisible(False)
        layout.addWidget(self._save_status)

        layout.addSpacing(8)

        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("Título")
        self._title_input.setStyleSheet(
            f"QLineEdit {{ background: {COLORS['bg_tertiary']}; color: {COLORS['text_primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 8px 12px; }}"
            f"QLineEdit:focus {{ border-color: {COLORS['border_focus']}; }}"
        )
        layout.addWidget(self._title_input)

        self._content_input = QTextEdit()
        self._content_input.setPlaceholderText("Escribí tu idea acá...")
        self._content_input.setMinimumHeight(140)
        self._content_input.setStyleSheet(
            f"QTextEdit {{ background: {COLORS['bg_tertiary']}; color: {COLORS['text_primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 8px 12px; }}"
            f"QTextEdit:focus {{ border-color: {COLORS['border_focus']}; }}"
        )
        layout.addWidget(self._content_input)

        self._save_btn = QPushButton("Guardar Idea")
        self._save_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['accent']}; color: white;"
            f" border: none; border-radius: 8px; padding: 10px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_hover']}; }}"
            f"QPushButton:disabled {{ background: {COLORS['bg_tertiary']}; color: {COLORS['text_muted']}; }}"
        )
        self._save_btn.clicked.connect(self._on_save)
        layout.addWidget(self._save_btn)

        layout.addStretch()

    def _on_save(self) -> None:
        title = self._title_input.text().strip()
        content = self._content_input.toPlainText().strip()
        if not content:
            self._show_status("El contenido no puede estar vacío", COLORS["error"])
            return
        self._save_btn.setEnabled(False)
        self._save_btn.setText("Guardando...")
        self.on_save(title, content)

    def on_save_result(self, success: bool, message: str) -> None:
        self._save_btn.setEnabled(True)
        self._save_btn.setText("Guardar Idea")
        if success:
            self._title_input.clear()
            self._content_input.clear()
            self._show_status(message, COLORS["success"])
        else:
            self._show_status(message, COLORS["error"])

    def _show_status(self, text: str, color: str) -> None:
        self._save_status.setText(text)
        self._save_status.setStyleSheet(f"font-size: 12px; color: {color};")
        self._save_status.setVisible(True)
        QTimer.singleShot(4000, lambda: self._save_status.setVisible(False))


class _IdeaListItem(QFrame):
    def __init__(
        self,
        idea: Idea,
        on_delete: Callable[[UUID], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.idea = idea
        self.on_delete = on_delete
        self.setObjectName("ideaListItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self._checkbox = QCheckBox()
        self._checkbox.setStyleSheet(
            f"QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px;"
            f" border: 2px solid {COLORS['border_light']}; }}"
            f"QCheckBox::indicator:checked {{ background: {COLORS['accent']};"
            f" border-color: {COLORS['accent']}; }}"
        )
        layout.addWidget(self._checkbox)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        titulo = self.idea.titulo if self.idea.titulo else "Sin título"
        title_label = QLabel(titulo)
        title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']}; background: transparent;"
        )
        text_layout.addWidget(title_label)

        preview = self.idea.contenido_raw[:80] + (
            "..." if len(self.idea.contenido_raw) > 80 else ""
        )
        preview_label = QLabel(preview)
        preview_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['text_secondary']}; background: transparent;"
        )
        preview_label.setWordWrap(True)
        text_layout.addWidget(preview_label)

        fecha = self.idea.fecha_creacion.strftime("%d/%m/%Y %H:%M")
        tipo = self.idea.tipo_entrada.value.capitalize()
        meta_label = QLabel(f"{fecha} · {tipo}")
        meta_label.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_muted']}; background: transparent;"
        )
        text_layout.addWidget(meta_label)

        layout.addLayout(text_layout, stretch=1)

        self._delete_btn = QPushButton("🗑")
        self._delete_btn.setFixedSize(30, 30)
        self._delete_btn.setToolTip("Eliminar idea")
        self._delete_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['error_bg']}; color: {COLORS['error']};"
            f" border: none; border-radius: 6px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {COLORS['error']}; color: white; }}"
        )
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self._delete_btn)

        self.setStyleSheet(
            f"#ideaListItem {{ background: {COLORS['bg_card']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 8px; }}"
            f"#ideaListItem:hover {{ background: {COLORS['bg_hover']};"
            f" border-color: {COLORS['accent']}; }}"
        )

    def is_checked(self) -> bool:
        return self._checkbox.isChecked()

    def set_checked(self, checked: bool) -> None:
        self._checkbox.setChecked(checked)

    def _on_delete_clicked(self) -> None:
        if self.on_delete:
            self.on_delete(self.idea.id)


class _IdeaListWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[_IdeaListItem] = []
        self._all_items: list[_IdeaListItem] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("Tus Ideas")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        header.addWidget(title)
        header.addStretch()

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['text_muted']}; padding: 4px 10px;"
            f" background: {COLORS['bg_tertiary']}; border-radius: 8px;"
        )
        header.addWidget(self._count_label)

        layout.addLayout(header)

        # Search
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Buscar ideas...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet(
            f"QLineEdit {{ background: {COLORS['bg_tertiary']}; color: {COLORS['text_primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 8px 12px; }}"
            f"QLineEdit:focus {{ border-color: {COLORS['border_focus']}; }}"
        )
        self._search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_input)

        # Timer de debounce para evitar lag al escribir (150ms)
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(150)
        self._filter_timer.timeout.connect(self._apply_filter)

        # Scrollable list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)

        self._scroll.setWidget(self._list_widget)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._select_all_btn = QPushButton("Seleccionar todo")
        self._select_all_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['accent']};"
            f" border: 1px solid {COLORS['accent']}; border-radius: 8px; padding: 8px 16px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_muted']}; }}"
        )
        self._select_all_btn.clicked.connect(self._toggle_select_all)
        btn_layout.addWidget(self._select_all_btn)

        btn_layout.addStretch()

        self._enqueue_btn = QPushButton("Enviar a Jobs IA")
        self._enqueue_btn.setEnabled(False)
        self._enqueue_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['accent_secondary']}; color: white;"
            f" border: none; border-radius: 8px; padding: 8px 18px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_secondary_hover']}; }}"
            f"QPushButton:disabled {{ background: {COLORS['bg_tertiary']}; color: {COLORS['text_muted']}; }}"
        )
        btn_layout.addWidget(self._enqueue_btn)

        layout.addWidget(self._scroll, stretch=1)
        layout.addLayout(btn_layout)

    on_item_delete: Callable[[UUID], None] | None = None

    def set_items(self, ideas: list[Idea]) -> None:
        """Reemplaza la lista completa de ideas, destruyendo las anteriores."""
        # Destruir widgets anteriores correctamente
        for item in self._all_items:
            self._list_layout.removeWidget(item)
            item.deleteLater()

        self._all_items = []
        self._items = []

        for idea in ideas:
            item = _IdeaListItem(idea, on_delete=self.on_item_delete)
            item._checkbox.toggled.connect(self._update_enqueue_btn)
            self._all_items.append(item)
            self._list_layout.addWidget(item)

        self._items = list(self._all_items)
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Muestra/oculta widgets según el filtro (sin destruir)."""
        visible_set = set(id(item) for item in self._items)
        for item in self._all_items:
            item.setVisible(id(item) in visible_set)

        self._count_label.setText(str(len(self._items)))
        self._update_enqueue_btn()

    def _on_search_changed(self, text: str) -> None:
        """Reinicia el timer de debounce al escribir."""
        self._filter_timer.start()

    def _apply_filter(self) -> None:
        """Ejecuta el filtro real tras el debounce."""
        q = self._search_input.text().lower().strip()
        if not q:
            self._items = list(self._all_items)
        else:
            self._items = [
                item
                for item in self._all_items
                if q in item.idea.titulo.lower()
                or q in item.idea.contenido_raw.lower()
            ]
        self._refresh_list()

    def _toggle_select_all(self) -> None:
        any_unchecked = any(not item.is_checked() for item in self._items)
        for item in self._items:
            item.set_checked(any_unchecked)
        self._update_enqueue_btn()

    def _update_enqueue_btn(self) -> None:
        has_checked = any(item.is_checked() for item in self._items)
        self._enqueue_btn.setEnabled(has_checked)

    def get_selected_ids(self) -> list[UUID]:
        return [item.idea.id for item in self._items if item.is_checked()]

    def get_selected_ideas(self) -> list[Idea]:
        return [item.idea for item in self._items if item.is_checked()]


class IdeasScreen(QWidget):
    def __init__(
        self,
        idea_service: IdeaService | None = None,
        job_service: JobService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ideasScreen")
        self._idea_service = idea_service
        self._job_service = job_service
        self._setup_ui()

    def set_services(self, idea_service: IdeaService, job_service: JobService) -> None:
        self._idea_service = idea_service
        self._job_service = job_service
        self._load_ideas()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        self._capture = _CapturePanel(on_save=self._on_save_idea)
        layout.addWidget(self._capture)

        self._state_view = StateView()
        layout.addWidget(self._state_view, stretch=1)

        content = _IdeaListWidget()
        self._idea_list = content
        self._idea_list.on_item_delete = self._on_delete_idea

        self._idea_list._enqueue_btn.clicked.connect(self._on_enqueue_selected)
        self._state_view.set_content_widget(content)

    def _on_save_idea(self, title: str, content: str) -> None:
        if not self._idea_service:
            self._capture.on_save_result(False, "Servicio no disponible")
            return
        try:
            if not title:
                title = content[:50]
            self._idea_service.create_idea(titulo=title, contenido_raw=content)
            self._capture.on_save_result(True, "Idea guardada")
            self._load_ideas()
        except Exception as e:
            self._capture.on_save_result(False, str(e))

    def _on_delete_idea(self, idea_id: UUID) -> None:
        if not self._idea_service:
            return
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar esta idea? También se eliminarán sus jobs asociados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._idea_service.delete_idea(idea_id)
            self._load_ideas()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo eliminar: {e}")

    _PROMPT_TEMPLATE = (
        "Actúa como un experto en gestión de proyectos y productividad."
        " Voy a darte una idea y quiero que la desgloses en un plan de acción detallado.\n\n"
        "La idea es: {idea}\n\n"
        "Por favor, organiza la respuesta de la siguiente manera:\n\n"
        "Objetivo Principal: Define en una frase el éxito de este proyecto.\n"
        "Fases del Proyecto: Divide el proceso en fases lógicas"
        " (ej. Planificación, Ejecución, Lanzamiento, Revisión).\n"
        "Lista de Tareas: Dentro de cada fase, crea una lista de tareas accionables."
        " Cada tarea debe empezar con un verbo fuerte"
        " (ej. 'Investigar', 'Diseñar', 'Contactar').\n"
        "Recursos Necesarios: Una lista de herramientas, software o conocimientos"
        " que necesitaré para completar las tareas.\n"
        "Primer Paso Crítico: Dime exactamente qué es lo primero"
        " que debo hacer hoy mismo para romper la inercia."
    )

    def _on_enqueue_selected(self) -> None:
        if not self._job_service or not self._idea_service:
            QMessageBox.warning(self, "Error", "Servicio no disponible")
            return
        ideas = self._idea_list.get_selected_ideas()
        if not ideas:
            return

        ok = 0
        errors: list[str] = []
        for idea in ideas:
            try:
                safe_content = idea.contenido_raw.replace("{", "{{").replace("}", "}}")
                prompt = self._PROMPT_TEMPLATE.format(idea=safe_content)
                self._job_service.enqueue_job(
                    idea_id=idea.id,
                    tipo_job=TipoJob.ENRIQUECIMIENTO,
                    payload={"prompt": prompt},
                )
                self._idea_service.move_idea(idea.id, EstadoKanban.EN_PROCESO)
                ok += 1
            except Exception as e:
                errors.append(f"  {idea.titulo or 'sin título'}: {e}")

        if errors:
            QMessageBox.warning(
                self,
                "Resultado",
                f"{ok} enviada(s), {len(errors)} fallaron:\n" + "\n".join(errors),
            )
        elif ok:
            QMessageBox.information(self, "Resultado", f"{ok} enviada(s) a Jobs IA")
        self._load_ideas()

    def _load_ideas(self) -> None:
        if not self._idea_service:
            self._state_view.show_state(
                StateView.EMPTY,
                icon="💡",
                title="Sin conexión",
                description="El servicio de datos no está disponible.",
            )
            return

        self._state_view.show_state(StateView.LOADING, title="Cargando ideas...")
        QTimer.singleShot(0, self._do_load)

    def _do_load(self) -> None:
        try:
            ideas = self._idea_service.list_by_estado(EstadoKanban.NUEVA)  # type: ignore[union-attr]
            ideas += self._idea_service.list_by_estado(EstadoKanban.EN_PROCESO)  # type: ignore[union-attr]
        except Exception as e:
            self._state_view.show_state(
                StateView.ERROR,
                title="Error al cargar",
                description=str(e),
            )
            return

        if not ideas:
            self._state_view.show_state(
                StateView.EMPTY,
                icon="💡",
                title="Todavía no hay ideas",
                description="Comenzá creando tu primera idea con el panel de captura.",
            )
        else:
            self._idea_list.set_items(ideas)
            self._state_view.show_state(StateView.CONTENT)
