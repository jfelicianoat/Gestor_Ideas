"""
Modelos SQLModel para persistencia del Gestor de Ideas.

Estos modelos son la representación ORM de las entidades de dominio.
Pertenecen exclusivamente a la capa de persistencia — no deben
exportarse ni usarse directamente fuera de src/adaptador/db/.

La conversión entre modelos ORM y entidades de dominio se realiza
en los repositorios correspondientes.

Referencia: CONTEXT_PACK.md §6
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import Column, Field, Relationship, SQLModel, Text


class IdeaModel(SQLModel, table=True):
    """
    Modelo ORM para la entidad Idea.

    Almacena la captura del usuario con su contenido original,
    contenido enriquecido por IA y estado en el tablero Kanban.
    """

    __tablename__ = "ideas"

    # Identificador único (UUID como string para SQLite)
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    # Título de la idea
    titulo: str = Field(default="", max_length=500)
    # Texto original tal como fue ingresado o transcrito
    contenido_raw: str = Field(default="", sa_column=Column(Text))
    # Resultado del procesamiento IA
    contenido_enriquecido: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    # Tipo de entrada: texto, audio_grabado, mp3, pdf, markdown
    tipo_entrada: str = Field(default="texto", max_length=50)
    # Estado Kanban: nueva, en_proceso, revision, archivada
    estado_kanban: str = Field(default="nueva", max_length=50, index=True)
    # Ruta al archivo adjunto original
    archivo_adjunto: str | None = Field(default=None, max_length=1000)
    # Timestamps
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fecha_modificacion: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relación 1-a-muchos con JobModel
    jobs: list["JobModel"] = Relationship(
        back_populates="idea",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class JobModel(SQLModel, table=True):
    """
    Modelo ORM para la entidad Job.

    Representa una tarea de procesamiento IA asociada a una Idea.
    Los jobs se persisten antes de ejecutarse y soportan
    reintentos con backoff.
    """

    __tablename__ = "jobs"

    # Identificador único del job
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    # FK a la idea que originó el job
    idea_id: str = Field(foreign_key="ideas.id", max_length=36)
    # Tipo de job: transcripcion, enriquecimiento, resumen, etiquetas
    tipo_job: str = Field(default="enriquecimiento", max_length=50)
    # Estado: pendiente, en_curso, completado, fallido, cancelado
    estado: str = Field(default="pendiente", max_length=50, index=True)
    # Número de intentos realizados
    intentos: int = Field(default=0)
    # Límite máximo de reintentos
    max_intentos: int = Field(default=3)
    # Parámetros del job serializado como JSON string
    payload: str = Field(default="{}")
    # Resultado del LLM o descripción del error
    resultado: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # Timestamps
    fecha_creado: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fecha_actualizado: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Timeout máximo por intento en segundos
    timeout_segundos: int = Field(default=120)

    # Relación inversa con IdeaModel
    idea: IdeaModel | None = Relationship(back_populates="jobs")


class BackupRegistroModel(SQLModel, table=True):
    """
    Modelo ORM para el registro de backups automáticos.

    Almacena metadatos de cada backup para control de
    retención y restauración.
    """

    __tablename__ = "backup_registros"

    # Identificador autonumérico
    id: int | None = Field(default=None, primary_key=True)
    # Ruta completa al archivo de backup
    ruta_archivo: str = Field(max_length=1000)
    # Timestamp del momento del backup
    fecha_backup: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Tamaño del archivo en bytes
    tamano_bytes: int = Field(default=0)
