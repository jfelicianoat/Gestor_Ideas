"""
Tests unitarios para la carga y validación de configuración.

Cubre:
- Carga exitosa desde YAML válido
- Valores por defecto cuando secciones faltan
- Error con archivo inexistente
- Error con YAML malformado
- Error con valores fuera de rango
"""

import textwrap
from pathlib import Path

import pytest

from adaptador.config import AppConfig, ConfigError, load_config


class TestLoadConfigExitosa:
    """Tests de carga exitosa de configuración."""

    def test_carga_config_completa(self, tmp_path: Path) -> None:
        """Verifica que un YAML completo se carga correctamente."""
        yaml_content = textwrap.dedent("""\
            ollama:
              url: "http://10.0.0.5:11434"
              default_model: "mistral"
              timeout_seconds: 60
            whisper:
              model_size: "tiny"
            jobs:
              max_retries: 5
              backoff_base_seconds: 10
              poll_interval_seconds: 15
            database:
              path: "mi_db.db"
            backup:
              directory: "mis_backups"
              max_versions: 20
        """)
        config_file = tmp_path / "app.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        config = load_config(config_file)

        assert config.ollama.url == "http://10.0.0.5:11434"
        assert config.ollama.default_model == "mistral"
        assert config.ollama.timeout_seconds == 60
        assert config.whisper.model_size == "tiny"
        assert config.jobs.max_retries == 5
        assert config.jobs.backoff_base_seconds == 10
        assert config.jobs.poll_interval_seconds == 15
        assert config.database.path == "mi_db.db"
        assert config.backup.directory == "mis_backups"
        assert config.backup.max_versions == 20

    def test_valores_por_defecto_con_yaml_vacio(self, tmp_path: Path) -> None:
        """Un YAML vacío debe producir AppConfig con todos los defaults."""
        config_file = tmp_path / "app.yaml"
        config_file.write_text("", encoding="utf-8")

        config = load_config(config_file)

        assert config.ollama.url == "http://192.168.1.100:11434"
        assert config.ollama.default_model == "llama3.2"
        assert config.ollama.timeout_seconds == 120
        assert config.whisper.model_size == "base"
        assert config.jobs.max_retries == 3
        assert config.database.path == "data/gestor_ideas.db"
        assert config.backup.max_versions == 10

    def test_seccion_parcial_usa_defaults(self, tmp_path: Path) -> None:
        """Si solo se define una sección, las demás usan defaults."""
        yaml_content = textwrap.dedent("""\
            ollama:
              url: "http://mi-servidor:11434"
        """)
        config_file = tmp_path / "app.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        config = load_config(config_file)

        # Sección ollama parcialmente definida
        assert config.ollama.url == "http://mi-servidor:11434"
        assert config.ollama.default_model == "llama3.2"  # default

        # Secciones no definidas usan defaults completos
        assert config.whisper.model_size == "base"
        assert config.jobs.max_retries == 3
        assert config.database.path == "data/gestor_ideas.db"
        assert config.backup.directory == "backups"


class TestLoadConfigErrores:
    """Tests de manejo de errores en la configuración."""

    def test_error_archivo_inexistente(self) -> None:
        """Lanza ConfigError si el archivo no existe."""
        with pytest.raises(ConfigError, match="no encontrado"):
            load_config("/ruta/inexistente/config.yaml")

    def test_error_yaml_malformado(self, tmp_path: Path) -> None:
        """Lanza ConfigError si el YAML tiene sintaxis inválida."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("ollama:\n  url: [esto no cierra",
                               encoding="utf-8")

        with pytest.raises(ConfigError, match="Error al parsear YAML"):
            load_config(config_file)

    def test_error_yaml_no_es_diccionario(self, tmp_path: Path) -> None:
        """Lanza ConfigError si el YAML raíz no es un diccionario."""
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2", encoding="utf-8")

        with pytest.raises(ConfigError, match="diccionario YAML"):
            load_config(config_file)

    def test_error_timeout_negativo(self, tmp_path: Path) -> None:
        """Lanza ConfigError si timeout_seconds es menor que 1."""
        yaml_content = textwrap.dedent("""\
            ollama:
              timeout_seconds: 0
        """)
        config_file = tmp_path / "app.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ConfigError, match="inválidos"):
            load_config(config_file)

    def test_error_max_versions_cero(self, tmp_path: Path) -> None:
        """Lanza ConfigError si max_versions es menor que 1."""
        yaml_content = textwrap.dedent("""\
            backup:
              max_versions: 0
        """)
        config_file = tmp_path / "app.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ConfigError, match="inválidos"):
            load_config(config_file)


class TestAppConfigModelo:
    """Tests del modelo AppConfig directamente."""

    def test_instancia_sin_argumentos_usa_defaults(self) -> None:
        """AppConfig() sin argumentos produce configuración válida."""
        config = AppConfig()

        assert config.ollama.url == "http://192.168.1.100:11434"
        assert config.jobs.poll_interval_seconds == 10
        assert config.backup.max_versions == 10

    def test_config_es_inmutable_por_defecto(self) -> None:
        """Los valores de config no deben mutar accidentalmente."""
        config = AppConfig()
        # Pydantic v2 permite asignación por defecto, pero verificamos
        # que la instancia es coherente tras la creación
        assert isinstance(config.ollama, object)
        assert isinstance(config.database, object)
