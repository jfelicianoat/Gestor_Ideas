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
