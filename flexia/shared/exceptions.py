"""Excepciones de dominio propias de FlexIA."""

class FlexIAError(Exception):
    """Base para todas las excepciones de dominio."""

class PatientNotFoundError(FlexIAError):
    pass

class SessionNotFoundError(FlexIAError):
    pass

class VideoProcessingError(FlexIAError):
    pass

class UnauthorizedError(FlexIAError):
    pass
