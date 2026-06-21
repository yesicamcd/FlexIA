"""Constantes del dominio."""

# Umbrales de evaluacion biomecanica
GREEN_THRESHOLD: float = 0.85   # >= 85% del ROM esperado
YELLOW_THRESHOLD: float = 0.60  # >= 60% amarillo, < 60% rojo

# Planes de licencia
PLAN_STARTER = "starter"
PLAN_PROFESSIONAL = "professional"
PLAN_ENTERPRISE = "enterprise"

# Estados de sesion
SESSION_CREATED = "created"
SESSION_RECORDING = "recording"
SESSION_PROCESSING = "processing"
SESSION_COMPLETED = "completed"
SESSION_ERROR = "error"

# Labels de performance
LABEL_GREEN = "green"
LABEL_YELLOW = "yellow"
LABEL_RED = "red"
