"""Tests de configuracion mostrada en Settings."""

from types import SimpleNamespace

from PySide6.QtWidgets import QLabel

from adaptador.ui.screens.settings_screen import SettingsScreen, _load_config_values


def test_load_config_values_usa_config_real_inyectada() -> None:
    config = SimpleNamespace(
        ollama=SimpleNamespace(
            default_model="mistral",
            url="http://10.0.0.5:11434",
        )
    )

    modelo, url = _load_config_values(lambda: config)

    assert modelo == "mistral"
    assert url == "http://10.0.0.5:11434"


def test_load_config_values_no_expone_url_hardcodeada_si_config_falla() -> None:
    def failing_loader() -> object:
        raise RuntimeError("config rota")

    modelo, url = _load_config_values(failing_loader)

    assert modelo == "no disponible"
    assert url == "no disponible"
    assert "192.168" not in url


def test_settings_muestra_backups_como_pendientes(qapp) -> None:
    screen = SettingsScreen()

    labels = [label.text() for label in screen.findChildren(QLabel)]

    assert "Pendiente" in labels
    assert "Motor disponible; programacion automatica pendiente" in labels
    assert "Realizar backups automaticos periodicos" not in labels
    assert "Los cambios se aplican automaticamente" not in labels
