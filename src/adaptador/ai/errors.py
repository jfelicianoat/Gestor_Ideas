"""Errores explícitos para integraciones de IA."""


class AIIntegrationError(Exception):
    """Error base de las integraciones de IA."""


class AITransientError(AIIntegrationError):
    """Fallo recuperable: red, servidor no disponible o timeout transitorio."""


class AITimeoutError(AITransientError):
    """La operación de IA agotó su timeout."""


class AIResponseValidationError(AIIntegrationError):
    """La respuesta de IA no cumple el formato esperado."""


class TranscriptionError(AIIntegrationError):
    """Fallo durante la transcripción local."""
