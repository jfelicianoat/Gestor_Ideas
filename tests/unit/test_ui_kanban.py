"""
Tests unitarios para componentes Kanban de la interfaz.
"""

from adaptador.domain.entities import Idea
from adaptador.domain.enums import EstadoKanban, TipoEntrada
from adaptador.ui.kanban.idea_card import IdeaCard
from adaptador.ui.screens.kanban_screen import KanbanScreen


class _FakeIdeaService:
    def __init__(self, ideas: list[Idea]) -> None:
        self.ideas = {idea.id: idea for idea in ideas}
        self.moves: list[tuple[object, EstadoKanban]] = []

    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        return [idea for idea in self.ideas.values() if idea.estado_kanban == estado]

    def move_idea(self, idea_id: object, nuevo_estado: EstadoKanban) -> Idea:
        self.moves.append((idea_id, nuevo_estado))
        idea = self.ideas[idea_id]
        idea.estado_kanban = nuevo_estado
        return idea


class _FailingIdeaService:
    def list_by_estado(self, estado: EstadoKanban) -> list[Idea]:
        raise RuntimeError("fallo de lectura")


class TestIdeaCard:
    """Tests del widget IdeaCard."""

    def test_instanciacion_idea_card(self, qapp) -> None:
        """Una IdeaCard se puede instanciar con una idea."""
        idea = Idea(
            titulo="Mi Idea",
            contenido_raw="Contenido de prueba muy interesante.",
            tipo_entrada=TipoEntrada.TEXTO,
        )
        card = IdeaCard(idea)

        # Validar elementos UI
        assert card.lbl_titulo.text() == "Mi Idea"
        assert card.lbl_contenido.text() == "Contenido de prueba muy interesante."
        assert "Texto" in card.lbl_meta.text()

    def test_truncado_contenido_largo(self, qapp) -> None:
        """El contenido de la idea se trunca si excede el máximo."""
        contenido_largo = "A" * 150
        idea = Idea(titulo="Idea Larga", contenido_raw=contenido_largo)
        card = IdeaCard(idea)

        texto_mostrado = card.lbl_contenido.text()
        assert len(texto_mostrado) <= IdeaCard.MAX_TEXT_LEN + 3
        assert texto_mostrado.endswith("...")

    def test_titulo_por_defecto_si_vacio(self, qapp) -> None:
        """Si la idea no tiene título, muestra 'Sin título'."""
        idea = Idea(titulo="", contenido_raw="Algo")
        card = IdeaCard(idea)

        assert card.lbl_titulo.text() == "Sin título"


class TestKanbanColumn:
    """Tests del widget KanbanColumn."""

    def test_instanciacion_columna(self, qapp) -> None:
        """KanbanColumn se inicializa con su estado y contador en 0."""
        from adaptador.domain.enums import EstadoKanban
        from adaptador.ui.kanban.kanban_column import KanbanColumn

        col = KanbanColumn(EstadoKanban.NUEVA)
        assert col.lbl_titulo.text() == "NUEVA"
        assert col.lbl_contador.text() == "0 tarjetas"

    def test_add_y_clear_cards(self, qapp) -> None:
        """add_card añade widgets al layout y clear_cards los elimina."""
        from adaptador.domain.enums import EstadoKanban
        from adaptador.ui.kanban.kanban_column import KanbanColumn

        col = KanbanColumn(EstadoKanban.EN_PROCESO)

        idea1 = Idea(titulo="Idea 1")
        idea2 = Idea(titulo="Idea 2")

        col.add_card(IdeaCard(idea1))
        col.add_card(IdeaCard(idea2))

        assert col.cards_layout.count() == 2
        assert col.lbl_contador.text() == "2 tarjetas"

        col.clear_cards()

        assert col.cards_layout.count() == 0
        assert col.lbl_contador.text() == "0 tarjetas"


class TestKanbanScreen:
    """Tests de carga real del tablero Kanban."""

    def test_set_services_carga_ideas_por_estado(self, qapp) -> None:
        nueva = Idea(titulo="Nueva", estado_kanban=EstadoKanban.NUEVA)
        proceso = Idea(titulo="Proceso", estado_kanban=EstadoKanban.EN_PROCESO)
        service = _FakeIdeaService([nueva, proceso])
        screen = KanbanScreen()

        screen.set_services(service)

        assert len(screen.columnas[EstadoKanban.NUEVA]._tarjetas) == 1
        assert len(screen.columnas[EstadoKanban.EN_PROCESO]._tarjetas) == 1
        assert len(screen.columnas[EstadoKanban.REVISION]._tarjetas) == 0
        assert screen.columnas[EstadoKanban.NUEVA]._tarjetas[0].idea.id == nueva.id

    def test_drop_mueve_idea_y_recarga_columnas(self, qapp) -> None:
        idea = Idea(titulo="Mover", estado_kanban=EstadoKanban.NUEVA)
        service = _FakeIdeaService([idea])
        screen = KanbanScreen()
        screen.set_services(service)

        screen._on_card_dropped(str(idea.id), EstadoKanban.EN_PROCESO)

        assert service.moves == [(idea.id, EstadoKanban.EN_PROCESO)]
        assert len(screen.columnas[EstadoKanban.NUEVA]._tarjetas) == 0
        assert len(screen.columnas[EstadoKanban.EN_PROCESO]._tarjetas) == 1

    def test_set_services_con_error_no_deja_tarjetas_stale(self, qapp) -> None:
        idea = Idea(titulo="Vieja", estado_kanban=EstadoKanban.NUEVA)
        screen = KanbanScreen()
        screen.set_services(_FakeIdeaService([idea]))

        screen.set_services(_FailingIdeaService())

        assert all(len(col._tarjetas) == 0 for col in screen.columnas.values())
