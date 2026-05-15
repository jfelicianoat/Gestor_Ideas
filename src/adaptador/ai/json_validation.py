"""Validación de JSON devuelto por modelos IA."""

import json
from typing import Any

from adaptador.ai.errors import AIResponseValidationError


def parse_json_object(raw: str) -> dict[str, Any]:
    """
    Parsea una respuesta IA como objeto JSON.

    Ollama puede devolver texto alrededor del JSON si el prompt no fue
    estricto. Esta función exige un objeto JSON válido para que capas
    superiores no consuman respuestas ambiguas.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIResponseValidationError("La respuesta no es JSON válido") from exc

    if not isinstance(parsed, dict):
        raise AIResponseValidationError("La respuesta JSON debe ser un objeto")
    return parsed
