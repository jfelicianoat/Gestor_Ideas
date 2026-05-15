"""
Funciones de mapeo entre entidades de dominio y modelos SQLModel.

Centralizan la conversión para que los repositorios no dupliquen
lógica de serialización/deserialización. Los modelos ORM nunca
salen de la capa de persistencia.
"""

import json
from uuid import UUID

from adaptador.db.models import IdeaModel, JobModel
from adaptador.domain.entities import Idea, Job
from adaptador.domain.enums import (
    EstadoJob,
    EstadoKanban,
    TipoEntrada,
    TipoJob,
)

# ============================================================
# Idea ↔ IdeaModel
# ============================================================


def idea_to_model(idea: Idea) -> IdeaModel:
    """Convierte una entidad Idea de dominio a modelo ORM."""
    return IdeaModel(
        id=str(idea.id),
        titulo=idea.titulo,
        contenido_raw=idea.contenido_raw,
        contenido_enriquecido=idea.contenido_enriquecido,
        tipo_entrada=idea.tipo_entrada.value,
        estado_kanban=idea.estado_kanban.value,
        archivo_adjunto=idea.archivo_adjunto,
        fecha_creacion=idea.fecha_creacion,
        fecha_modificacion=idea.fecha_modificacion,
    )


def model_to_idea(model: IdeaModel) -> Idea:
    """Convierte un modelo ORM IdeaModel a entidad de dominio."""
    return Idea(
        id=UUID(model.id),
        titulo=model.titulo,
        contenido_raw=model.contenido_raw,
        contenido_enriquecido=model.contenido_enriquecido,
        tipo_entrada=TipoEntrada(model.tipo_entrada),
        estado_kanban=EstadoKanban(model.estado_kanban),
        archivo_adjunto=model.archivo_adjunto,
        fecha_creacion=model.fecha_creacion,
        fecha_modificacion=model.fecha_modificacion,
    )


# ============================================================
# Job ↔ JobModel
# ============================================================


def job_to_model(job: Job) -> JobModel:
    """Convierte una entidad Job de dominio a modelo ORM."""
    return JobModel(
        id=str(job.id),
        idea_id=str(job.idea_id),
        tipo_job=job.tipo_job.value,
        estado=job.estado.value,
        intentos=job.intentos,
        max_intentos=job.max_intentos,
        payload=json.dumps(job.payload, ensure_ascii=False),
        resultado=job.resultado,
        fecha_creado=job.fecha_creado,
        fecha_actualizado=job.fecha_actualizado,
        timeout_segundos=job.timeout_segundos,
    )


def _safe_json_loads(raw: str | None) -> dict:
    """Parsea JSON garantizando que devuelva un dict, nunca None."""
    if not raw:
        return {}
    stripped = raw.strip()
    if stripped in ("null", "", "{}"):
        return {}
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def model_to_job(model: JobModel) -> Job:
    """Convierte un modelo ORM JobModel a entidad de dominio."""
    return Job(
        id=UUID(model.id),
        idea_id=UUID(model.idea_id),
        tipo_job=TipoJob(model.tipo_job),
        estado=EstadoJob(model.estado),
        intentos=model.intentos,
        max_intentos=model.max_intentos,
        payload=_safe_json_loads(model.payload),
        resultado=model.resultado,
        fecha_creado=model.fecha_creado,
        fecha_actualizado=model.fecha_actualizado,
        timeout_segundos=model.timeout_segundos,
    )
