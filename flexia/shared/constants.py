"""
shared/constants.py

Constantes globales del sistema FlexIA.
Separadas por dominio para facilitar su mantenimiento.
"""


# ---------------------------------------------------------------------------
# Evaluacion de desempeno biomecanico
# ---------------------------------------------------------------------------

# Porcentaje del ROM esperado para clasificar como verde (ej: 0.85 = 85%)
GREEN_THRESHOLD: float = 0.85

# Porcentaje del ROM esperado para clasificar como amarillo
YELLOW_THRESHOLD: float = 0.60

# Por debajo de YELLOW_THRESHOLD se clasifica como rojo automaticamente


# ---------------------------------------------------------------------------
# Conteo de repeticiones
# ---------------------------------------------------------------------------

# Angulo minimo de cambio para considerar que inicio un movimiento (grados)
REP_MOVEMENT_THRESHOLD_DEGREES: float = 15.0

# Porcentaje del ROM requerido para validar una repeticion como completa
REP_COMPLETION_THRESHOLD: float = 0.75


# ---------------------------------------------------------------------------
# Validacion de sesion (pre-checks antes de iniciar)
# ---------------------------------------------------------------------------

# Luminosidad minima aceptable del frame (0-255, escala de grises promedio)
MIN_BRIGHTNESS: int = 60

# Confianza minima de deteccion de pose para considerar el cuerpo visible
MIN_POSE_CONFIDENCE: float = 0.65

# Porcentaje minimo del frame que debe ocupar el cuerpo del paciente
MIN_BODY_FRAME_RATIO: float = 0.30


# ---------------------------------------------------------------------------
# Captura de video
# ---------------------------------------------------------------------------

# Indice de camara frontal (0 = primera camara del sistema)
CAMERA_FRONT_INDEX: int = 0

# Indice de camara lateral (1 = segunda camara del sistema)
CAMERA_LATERAL_INDEX: int = 1

# Resolucion de captura
CAPTURE_WIDTH: int = 1280
CAPTURE_HEIGHT: int = 720

# Frames por segundo de captura
CAPTURE_FPS: int = 30


# ---------------------------------------------------------------------------
# Cuenta regresiva
# ---------------------------------------------------------------------------

# Segundos de cuenta regresiva antes de iniciar la sesion
COUNTDOWN_SECONDS: int = 5


# ---------------------------------------------------------------------------
# Planes de licencia
# ---------------------------------------------------------------------------

PLAN_STARTER: str = "starter"
PLAN_PROFESSIONAL: str = "professional"
PLAN_ENTERPRISE: str = "enterprise"


# ---------------------------------------------------------------------------
# Estados de sesion
# ---------------------------------------------------------------------------

SESSION_CREATED: str = "created"
SESSION_RECORDING: str = "recording"
SESSION_PROCESSING: str = "processing"
SESSION_COMPLETED: str = "completed"
SESSION_ERROR: str = "error"


# ---------------------------------------------------------------------------
# Labels de performance
# ---------------------------------------------------------------------------

LABEL_GREEN: str = "green"
LABEL_YELLOW: str = "yellow"
LABEL_RED: str = "red"


# ---------------------------------------------------------------------------
# Almacenamiento
# ---------------------------------------------------------------------------

# Bucket de Supabase Storage donde se guardan los videos
STORAGE_BUCKET_VIDEOS: str = "videos"

# Formato de ruta dentro del bucket
# Se completa con: centers/{center_id}/sessions/{session_id}/{camera}.mp4
STORAGE_PATH_TEMPLATE: str = "centers/{center_id}/sessions/{session_id}/{camera}.mp4"