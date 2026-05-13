"""
Tests unitarios para componentes Kanban de la interfaz.
"""


from adaptador.domain.entities import Idea
from adaptador.domain.enums import TipoEntrada
from adaptador.ui.kanban.idea_card import IdeaCard


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
