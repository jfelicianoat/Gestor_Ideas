"""
Enumeraciones del dominio del Gestor de Ideas.

Define los tipos y estados válidos para las entidades principales.
Estas enumeraciones son la fuente de verdad para los valores
permitidos en el sistema — no deben depender de infraestructura.
"""

from enum import StrEnum


class TipoEntrada(StrEnum):
    """Tipo de fuente de una idea capturada por el usuario."""

    TEXTO = "texto"
    AUDIO_GRABADO = "audio_grabado"
    MP3 = "mp3"
    PDF = "pdf"
    MARKDOWN = "markdown"


class EstadoKanban(StrEnum):
    """
    Estado de una idea en el tablero Kanban.

    Transiciones válidas definidas en transitions.py:
    nueva → en_proceso → revision → archivada
                          ↓
                     en_proceso (retorno)
    """

    NUEVA = "nueva"
    EN_PROCESO = "en_proceso"
    REVISION = "revision"
    ARCHIVADA = "archivada"


class TipoJob(StrEnum):
    """Tipo de procesamiento IA que se aplica a una idea."""

    TRANSCRIPCION = "transcripcion"
    ENRIQUECIMIENTO = "enriquecimiento"
    RESUMEN = "resumen"
    ETIQUETAS = "etiquetas"


class EstadoJob(StrEnum):
    """
    Estado de un job de procesamiento IA.

    Transiciones válidas definidas en transitions.py:
    pendiente → en_curso → completado
                         → fallido → pendiente (reintento)
    pendiente → cancelado
    """

    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    CANCELADO = "cancelado"
