"""
Configuración tipada de la aplicación Gestor de Ideas.

Carga los parámetros desde config/app.yaml y los expone como un
objeto Pydantic validado. Si el archivo no existe o es inválido,
lanza ConfigError con contexto descriptivo.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class ConfigError(Exception):
    """Error al cargar o validar la configuración de la aplicación."""

    pass


# --- Secciones de configuración ---


class OllamaConfig(BaseModel):
    """Parámetros de conexión con el servidor Ollama en LAN."""

    # URL base del servidor Ollama (se recomienda configurar en app.yaml)
    url: str = Field(default="http://localhost:11434")
    # Modelo LLM por defecto
    default_model: str = Field(default="llama3.2")
    # Timeout máximo por request en segundos
    timeout_seconds: int = Field(default=120, ge=1)


class WhisperConfig(BaseModel):
    """Parámetros de transcripción con faster-whisper."""

    # Tamaño del modelo: tiny, base, small, medium, large-v3
    model_size: str = Field(default="base")


class JobsConfig(BaseModel):
    """Parámetros del sistema de jobs IA persistentes."""

    # Máximo de reintentos ante fallo
    max_retries: int = Field(default=3, ge=0)
    # Base del backoff exponencial en segundos
    backoff_base_seconds: int = Field(default=5, ge=1)
    # Intervalo de polling del worker en segundos
    poll_interval_seconds: int = Field(default=10, ge=1)


class DatabaseConfig(BaseModel):
    """Parámetros de la base de datos SQLite."""

    # Ruta al archivo .db (relativa al directorio raíz de la app)
    path: str = Field(default="data/gestor_ideas.db")


class BackupConfig(BaseModel):
    """Parámetros del sistema de backups automáticos."""

    # Directorio de backups (relativo al directorio raíz de la app)
    directory: str = Field(default="backups")
    # Número máximo de backups a conservar
    max_versions: int = Field(default=10, ge=1)


class AppConfig(BaseModel):
    """
    Configuración completa de la aplicación.

    Agrupa todas las secciones de configuración en un objeto
    único, validado y tipado.
    """

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    jobs: JobsConfig = Field(default_factory=JobsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)


def load_config(path: str | Path | None = None) -> AppConfig:
    """
    Carga la configuración desde un archivo YAML.

    Si no se especifica path, busca en config/app.yaml relativo
    al directorio de trabajo actual.

    Args:
        path: Ruta al archivo YAML de configuración.

    Returns:
        AppConfig validado con todos los parámetros.

    Raises:
        ConfigError: Si el archivo no existe, no es YAML válido
            o los valores no pasan la validación de Pydantic.
    """
    if path is None:
        path = Path("config/app.yaml")
    else:
        path = Path(path)

    # Verificar que el archivo existe
    if not path.exists():
        raise ConfigError(
            f"Archivo de configuración no encontrado: {path.resolve()}"
        )

    # Leer y parsear el YAML
    try:
        with open(path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Error al parsear YAML en {path}: {e}") from e

    # Manejar archivo vacío
    if raw_data is None:
        raw_data = {}

    # Validar con Pydantic
    if not isinstance(raw_data, dict):
        raise ConfigError(
            f"El archivo de configuración debe contener un diccionario YAML, "
            f"se encontró: {type(raw_data).__name__}"
        )

    try:
        return AppConfig(**raw_data)
    except ValidationError as e:
        raise ConfigError(
            f"Valores de configuración inválidos en {path}:\n{e}"
        ) from e
