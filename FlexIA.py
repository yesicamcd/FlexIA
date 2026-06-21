"""
FlexIA — Script de creacion de estructura de proyecto
Ejecutar desde la carpeta donde quieras crear el proyecto:
    python create_flexia_structure.py
"""

import os

# Archivos con contenido inicial minimo
FILES = {
    # ── shared ────────────────────────────────────────────────────────────────
    "shared/__init__.py": "",
    "shared/config.py": '''"""Configuracion global — variables de entorno."""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_KEY: str = os.environ["SUPABASE_SERVICE_KEY"]
''',
    "shared/exceptions.py": '''"""Excepciones de dominio propias de FlexIA."""

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
''',
    "shared/constants.py": '''"""Constantes del dominio."""

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
''',
    "shared/logger.py": '''"""Logger centralizado."""
import logging

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    return logging.getLogger(name)
''',
    "shared/container.py": '''"""
Inyeccion de dependencias.
Unico lugar donde infrastructure se instancia y se inyecta en los use cases.
"""
# TODO: instanciar repositorios y servicios al avanzar el proyecto
''',

    # ── domain/models ─────────────────────────────────────────────────────────
    "domain/__init__.py": "",
    "domain/models/__init__.py": "",
    "domain/models/user.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class User:
    id: UUID
    center_id: UUID
    full_name: str
    role: str          # admin | professional | viewer
    is_active: bool
    created_at: datetime
''',
    "domain/models/patient.py": '''from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from typing import Optional

@dataclass
class Patient:
    id: UUID
    center_id: UUID
    created_by: UUID
    full_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    diagnosis: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
''',
    "domain/models/exercise.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Exercise:
    id: UUID
    center_id: Optional[UUID]  # None = ejercicio global del sistema
    name: str
    description: Optional[str]
    target_joint: Optional[str]
    video_ref_url: Optional[str]
    rom_min: Optional[float]
    rom_max: Optional[float]
    reps_expected: Optional[int]
    green_threshold: float
    yellow_threshold: float
    is_active: bool
    created_at: datetime
''',
    "domain/models/routine.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Routine:
    id: UUID
    center_id: UUID
    created_by: UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
''',
    "domain/models/routine_exercise.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class RoutineExercise:
    id: UUID
    routine_id: UUID
    exercise_id: UUID
    order_index: int
    reps_override: Optional[int]
    notes: Optional[str]
    created_at: datetime
''',
    "domain/models/session.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Session:
    id: UUID
    patient_id: UUID
    routine_id: Optional[UUID]
    professional_id: UUID
    status: str           # created | recording | processing | completed | error
    ifi_score: Optional[float]
    session_date: datetime
    notes: Optional[str]
    created_at: datetime
''',
    "domain/models/video.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Video:
    id: UUID
    session_id: UUID
    storage_path: str
    storage_url: Optional[str]
    duration_secs: Optional[float]
    fps: Optional[float]
    resolution: Optional[str]
    status: str           # uploading | uploaded | analyzing | analyzed | error
    error_message: Optional[str]
    created_at: datetime
''',
    "domain/models/exercise_result.py": '''from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class ExerciseResult:
    id: UUID
    session_id: UUID
    exercise_id: UUID
    order_index: int
    rom_achieved: Optional[float]
    rom_expected: Optional[float]
    rom_percentage: Optional[float]
    reps_achieved: Optional[int]
    reps_expected: Optional[int]
    performance: Optional[str]    # green | yellow | red
    ifi_contribution: Optional[float]
    landmarks_json: Optional[dict]
    frame_count: Optional[int]
    created_at: datetime
''',

    # ── domain/value_objects ──────────────────────────────────────────────────
    "domain/value_objects/__init__.py": "",
    "domain/value_objects/performance_label.py": '''from enum import Enum

class PerformanceLabel(str, Enum):
    GREEN  = "green"
    YELLOW = "yellow"
    RED    = "red"
''',
    "domain/value_objects/ifi_score.py": '''from dataclasses import dataclass

@dataclass(frozen=True)
class IfiScore:
    value: float  # 0.0 a 100.0

    def __post_init__(self):
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(f"IFI score debe estar entre 0 y 100. Recibido: {self.value}")

    @property
    def label(self) -> str:
        if self.value >= 85:
            return "green"
        elif self.value >= 60:
            return "yellow"
        return "red"
''',
    "domain/value_objects/rom_measurement.py": '''from dataclasses import dataclass

@dataclass(frozen=True)
class RomMeasurement:
    achieved_degrees: float
    expected_degrees: float

    @property
    def percentage(self) -> float:
        if self.expected_degrees <= 0:
            return 0.0
        return round((self.achieved_degrees / self.expected_degrees) * 100, 2)
''',

    # ── domain/interfaces ─────────────────────────────────────────────────────
    "domain/interfaces/__init__.py": "",
    "domain/interfaces/repositories/__init__.py": "",
    "domain/interfaces/repositories/i_patient_repository.py": '''from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.patient import Patient

class IPatientRepository(ABC):
    @abstractmethod
    def get_by_id(self, patient_id: UUID) -> Optional[Patient]: ...

    @abstractmethod
    def get_all_by_center(self, center_id: UUID) -> List[Patient]: ...

    @abstractmethod
    def save(self, patient: Patient) -> Patient: ...

    @abstractmethod
    def update(self, patient: Patient) -> Patient: ...
''',
    "domain/interfaces/repositories/i_session_repository.py": '''from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.session import Session

class ISessionRepository(ABC):
    @abstractmethod
    def get_by_id(self, session_id: UUID) -> Optional[Session]: ...

    @abstractmethod
    def get_by_patient(self, patient_id: UUID) -> List[Session]: ...

    @abstractmethod
    def save(self, session: Session) -> Session: ...

    @abstractmethod
    def update_status(self, session_id: UUID, status: str) -> None: ...

    @abstractmethod
    def update_ifi(self, session_id: UUID, ifi_score: float) -> None: ...
''',
    "domain/interfaces/repositories/i_routine_repository.py": '''from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.routine import Routine

class IRoutineRepository(ABC):
    @abstractmethod
    def get_by_id(self, routine_id: UUID) -> Optional[Routine]: ...

    @abstractmethod
    def get_all_by_center(self, center_id: UUID) -> List[Routine]: ...

    @abstractmethod
    def save(self, routine: Routine) -> Routine: ...
''',
    "domain/interfaces/repositories/i_exercise_repository.py": '''from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from domain.models.exercise import Exercise

class IExerciseRepository(ABC):
    @abstractmethod
    def get_by_id(self, exercise_id: UUID) -> Optional[Exercise]: ...

    @abstractmethod
    def get_all_available(self, center_id: UUID) -> List[Exercise]: ...
    # Devuelve globales + los del centro
''',
    "domain/interfaces/repositories/i_video_repository.py": '''from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from domain.models.video import Video

class IVideoRepository(ABC):
    @abstractmethod
    def get_by_session(self, session_id: UUID) -> Optional[Video]: ...

    @abstractmethod
    def save(self, video: Video) -> Video: ...

    @abstractmethod
    def update_status(self, video_id: UUID, status: str, error: str = None) -> None: ...
''',
    "domain/interfaces/services/__init__.py": "",
    "domain/interfaces/services/i_auth_service.py": '''from abc import ABC, abstractmethod
from domain.models.user import User

class IAuthService(ABC):
    @abstractmethod
    def login(self, email: str, password: str) -> dict: ...

    @abstractmethod
    def get_current_user(self, token: str) -> User: ...

    @abstractmethod
    def logout(self) -> None: ...
''',
    "domain/interfaces/services/i_storage_service.py": '''from abc import ABC, abstractmethod

class IStorageService(ABC):
    @abstractmethod
    def upload_video(self, file_bytes: bytes, path: str) -> str: ...
    # Devuelve la storage_path

    @abstractmethod
    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str: ...
''',
    "domain/interfaces/services/i_biomechanics_service.py": '''from abc import ABC, abstractmethod
from domain.models.exercise_result import ExerciseResult
from typing import List

class IBiomechanicsService(ABC):
    @abstractmethod
    def process_video(self, video_path: str, exercises: list) -> List[ExerciseResult]: ...
''',

    # ── app/use_cases ─────────────────────────────────────────────────────────
    "app/__init__.py": "",
    "app/use_cases/__init__.py": "",
    "app/use_cases/auth/__init__.py": "",
    "app/use_cases/auth/login_use_case.py": '''"""Caso de uso: login de usuario."""
from domain.interfaces.services.i_auth_service import IAuthService

class LoginUseCase:
    def __init__(self, auth_service: IAuthService):
        self._auth = auth_service

    def execute(self, email: str, password: str) -> dict:
        return self._auth.login(email, password)
''',
    "app/use_cases/patients/__init__.py": "",
    "app/use_cases/patients/create_patient_use_case.py": '''"""Caso de uso: crear paciente."""
from domain.interfaces.repositories.i_patient_repository import IPatientRepository
from app.dto.patient_dto import CreatePatientDTO, PatientDTO

class CreatePatientUseCase:
    def __init__(self, repository: IPatientRepository):
        self._repo = repository

    def execute(self, data: CreatePatientDTO) -> PatientDTO:
        # TODO: implementar
        raise NotImplementedError
''',
    "app/use_cases/patients/get_patient_history_use_case.py": '''"""Caso de uso: obtener historial clinico de un paciente."""
from uuid import UUID
from typing import List
from domain.interfaces.repositories.i_session_repository import ISessionRepository
from app.dto.session_dto import SessionDTO

class GetPatientHistoryUseCase:
    def __init__(self, session_repo: ISessionRepository):
        self._session_repo = session_repo

    def execute(self, patient_id: UUID) -> List[SessionDTO]:
        # TODO: implementar
        raise NotImplementedError
''',
    "app/use_cases/routines/__init__.py": "",
    "app/use_cases/routines/create_routine_use_case.py": '''"""Caso de uso: crear rutina."""
# TODO: implementar
''',
    "app/use_cases/routines/assign_routine_use_case.py": '''"""Caso de uso: asignar rutina a paciente."""
# TODO: implementar
''',
    "app/use_cases/sessions/__init__.py": "",
    "app/use_cases/sessions/create_session_use_case.py": '''"""Caso de uso: crear sesion de evaluacion."""
# TODO: implementar
''',
    "app/use_cases/sessions/upload_video_use_case.py": '''"""Caso de uso: subir video a Storage."""
# TODO: implementar
''',
    "app/use_cases/sessions/get_session_results_use_case.py": '''"""Caso de uso: obtener resultados de una sesion."""
# TODO: implementar
''',
    "app/use_cases/biomechanics/__init__.py": "",
    "app/use_cases/biomechanics/process_video_use_case.py": '''"""Caso de uso: procesar video con vision computacional."""
# TODO: implementar
''',
    "app/use_cases/biomechanics/generate_ifi_use_case.py": '''"""Caso de uso: generar Indice Funcional Integrado."""
# TODO: implementar
''',

    # ── app/dto ───────────────────────────────────────────────────────────────
    "app/dto/__init__.py": "",
    "app/dto/patient_dto.py": '''from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass
class CreatePatientDTO:
    full_name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class PatientDTO:
    id: str
    full_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    diagnosis: Optional[str]
    is_active: bool
''',
    "app/dto/session_dto.py": '''from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from app.dto.exercise_result_dto import ExerciseResultDTO

@dataclass
class SessionDTO:
    id: str
    patient_id: str
    status: str
    ifi_score: Optional[float]
    session_date: datetime
    results: List[ExerciseResultDTO]
''',
    "app/dto/exercise_result_dto.py": '''from dataclasses import dataclass
from typing import Optional

@dataclass
class ExerciseResultDTO:
    exercise_id: str
    exercise_name: str
    rom_achieved: Optional[float]
    rom_percentage: Optional[float]
    reps_achieved: Optional[int]
    performance: Optional[str]   # green | yellow | red
''',
    "app/dto/ifi_dto.py": '''from dataclasses import dataclass
from typing import List
from app.dto.exercise_result_dto import ExerciseResultDTO

@dataclass
class IfiDTO:
    score: float
    label: str    # green | yellow | red
    results: List[ExerciseResultDTO]
''',

    # ── infrastructure/supabase ───────────────────────────────────────────────
    "infrastructure/__init__.py": "",
    "infrastructure/supabase/__init__.py": "",
    "infrastructure/supabase/client.py": '''"""Singleton de conexion a Supabase."""
from supabase import create_client, Client
from shared.config import SUPABASE_URL, SUPABASE_ANON_KEY

_client: Client | None = None

def get_supabase_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client
''',
    "infrastructure/supabase/repositories/__init__.py": "",
    "infrastructure/supabase/repositories/supabase_patient_repository.py": '''"""Implementacion del repositorio de pacientes usando Supabase."""
from uuid import UUID
from typing import List, Optional
from supabase import Client
from domain.interfaces.repositories.i_patient_repository import IPatientRepository
from domain.models.patient import Patient

class SupabasePatientRepository(IPatientRepository):
    def __init__(self, client: Client):
        self._client = client

    def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        # TODO: implementar
        raise NotImplementedError

    def get_all_by_center(self, center_id: UUID) -> List[Patient]:
        # TODO: implementar
        raise NotImplementedError

    def save(self, patient: Patient) -> Patient:
        # TODO: implementar
        raise NotImplementedError

    def update(self, patient: Patient) -> Patient:
        # TODO: implementar
        raise NotImplementedError
''',
    "infrastructure/supabase/repositories/supabase_session_repository.py": '''"""Implementacion del repositorio de sesiones usando Supabase."""
# TODO: implementar
from domain.interfaces.repositories.i_session_repository import ISessionRepository
''',
    "infrastructure/supabase/repositories/supabase_routine_repository.py": '''# TODO: implementar
from domain.interfaces.repositories.i_routine_repository import IRoutineRepository
''',
    "infrastructure/supabase/repositories/supabase_exercise_repository.py": '''# TODO: implementar
from domain.interfaces.repositories.i_exercise_repository import IExerciseRepository
''',
    "infrastructure/supabase/repositories/supabase_video_repository.py": '''# TODO: implementar
from domain.interfaces.repositories.i_video_repository import IVideoRepository
''',
    "infrastructure/supabase/services/__init__.py": "",
    "infrastructure/supabase/services/supabase_auth_service.py": '''"""Implementacion del servicio de autenticacion con Supabase Auth."""
from supabase import Client
from domain.interfaces.services.i_auth_service import IAuthService
from domain.models.user import User

class SupabaseAuthService(IAuthService):
    def __init__(self, client: Client):
        self._client = client

    def login(self, email: str, password: str) -> dict:
        response = self._client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response

    def get_current_user(self, token: str) -> User:
        # TODO: implementar
        raise NotImplementedError

    def logout(self) -> None:
        self._client.auth.sign_out()
''',
    "infrastructure/supabase/services/supabase_storage_service.py": '''"""Implementacion del servicio de storage con Supabase Storage."""
# TODO: implementar
from domain.interfaces.services.i_storage_service import IStorageService
''',

    # ── infrastructure/biomechanics ───────────────────────────────────────────
    "infrastructure/biomechanics/__init__.py": "",
    "infrastructure/biomechanics/mediapipe_service.py": '''"""Implementacion del servicio de biomecanica con MediaPipe."""
from domain.interfaces.services.i_biomechanics_service import IBiomechanicsService

class MediaPipeBiomechanicsService(IBiomechanicsService):
    def process_video(self, video_path: str, exercises: list) -> list:
        # TODO: implementar pipeline completo
        raise NotImplementedError
''',
    "infrastructure/biomechanics/pose_estimator.py": '''"""Extraccion de landmarks de pose con MediaPipe."""
# TODO: implementar
# Entrada: frame (numpy array)
# Salida: landmarks normalizados
''',
    "infrastructure/biomechanics/rom_calculator.py": '''"""Calculo de ROM (Range of Motion) a partir de landmarks."""
# TODO: implementar
# Entrada: landmarks, joint name
# Salida: RomMeasurement
''',
    "infrastructure/biomechanics/rep_counter.py": '''"""Conteo de repeticiones validas a partir de angulos articulares."""
# TODO: implementar
''',
    "infrastructure/biomechanics/performance_evaluator.py": '''"""Clasificacion verde / amarillo / rojo segun umbrales."""
from domain.value_objects.performance_label import PerformanceLabel
from shared.constants import GREEN_THRESHOLD, YELLOW_THRESHOLD

def evaluate(rom_percentage: float) -> PerformanceLabel:
    if rom_percentage >= GREEN_THRESHOLD * 100:
        return PerformanceLabel.GREEN
    elif rom_percentage >= YELLOW_THRESHOLD * 100:
        return PerformanceLabel.YELLOW
    return PerformanceLabel.RED
''',
    "infrastructure/biomechanics/ifi_calculator.py": '''"""Calculo del Indice Funcional Integrado ponderado."""
from domain.value_objects.ifi_score import IfiScore
from typing import List

def calculate_ifi(results: list) -> IfiScore:
    """
    Recibe lista de ExerciseResult y devuelve el IFI ponderado.
    TODO: implementar logica de ponderacion real.
    """
    raise NotImplementedError
''',

    # ── frontend ──────────────────────────────────────────────────────────────
    "frontend/__init__.py": "",
    "frontend/main.py": '''"""Entry point de Streamlit — router de paginas."""
import streamlit as st

st.set_page_config(
    page_title="FlexIA",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# TODO: implementar navegacion entre paginas
st.title("FlexIA — Plataforma de Rehabilitacion")
st.info("Selecciona una seccion en el panel lateral.")
''',
    "frontend/pages/__init__.py": "",
    "frontend/pages/login_page.py": '''"""Pagina de login."""
import streamlit as st

def render():
    st.title("Iniciar sesion")
    email = st.text_input("Email")
    password = st.text_input("Contrasena", type="password")
    if st.button("Ingresar"):
        pass  # TODO: llamar LoginUseCase
''',
    "frontend/pages/patients/__init__.py": "",
    "frontend/pages/patients/patient_list_page.py": '''"""Listado de pacientes."""
import streamlit as st

def render():
    st.title("Pacientes")
    # TODO: llamar GetAllPatientsUseCase y mostrar tabla
''',
    "frontend/pages/patients/patient_detail_page.py": '''"""Detalle de paciente + historial clinico."""
import streamlit as st

def render(patient_id: str):
    st.title("Detalle del paciente")
    # TODO: llamar GetPatientHistoryUseCase
''',
    "frontend/pages/patients/patient_form_page.py": '''"""Formulario de alta / edicion de paciente."""
import streamlit as st

def render(patient_id: str = None):
    st.title("Nuevo paciente" if not patient_id else "Editar paciente")
    # TODO: llamar CreatePatientUseCase o UpdatePatientUseCase
''',
    "frontend/pages/routines/__init__.py": "",
    "frontend/pages/routines/routine_list_page.py": "# TODO",
    "frontend/pages/routines/routine_form_page.py": "# TODO",
    "frontend/pages/sessions/__init__.py": "",
    "frontend/pages/sessions/session_create_page.py": "# TODO",
    "frontend/pages/sessions/session_detail_page.py": "# TODO",
    "frontend/pages/sessions/video_upload_page.py": "# TODO",
    "frontend/pages/dashboards/__init__.py": "",
    "frontend/pages/dashboards/clinical_dashboard_page.py": "# TODO",
    "frontend/pages/dashboards/operational_dashboard_page.py": "# TODO",
    "frontend/components/__init__.py": "",
    "frontend/components/ifi_gauge.py": "# TODO: componente visual del IFI",
    "frontend/components/performance_badge.py": "# TODO: semaforo verde/amarillo/rojo",
    "frontend/components/session_timeline.py": "# TODO",
    "frontend/components/rom_chart.py": "# TODO",
    "frontend/components/report_exporter.py": "# TODO",
    "frontend/state/__init__.py": "",
    "frontend/state/auth_state.py": '''"""Gestion del estado de autenticacion en Streamlit."""
import streamlit as st

def is_authenticated() -> bool:
    return st.session_state.get("user") is not None

def get_current_user():
    return st.session_state.get("user")

def set_user(user):
    st.session_state["user"] = user

def clear_user():
    st.session_state.pop("user", None)
''',
    "frontend/state/navigation_state.py": '''"""Gestion de navegacion entre paginas."""
import streamlit as st

def go_to(page: str, **params):
    st.session_state["page"] = page
    for k, v in params.items():
        st.session_state[k] = v
    st.rerun()

def current_page() -> str:
    return st.session_state.get("page", "login")
''',

    # ── tests ─────────────────────────────────────────────────────────────────
    "tests/__init__.py": "",
    "tests/conftest.py": '''"""Fixtures compartidas para todos los tests."""
import pytest

# TODO: agregar fixtures de base de datos de test, mocks de Supabase, etc.
''',
    "tests/unit/__init__.py": "",
    "tests/unit/domain/__init__.py": "",
    "tests/unit/domain/test_ifi_score.py": '''"""Tests del value object IfiScore."""
import pytest
from domain.value_objects.ifi_score import IfiScore

def test_ifi_score_green():
    score = IfiScore(90.0)
    assert score.label == "green"

def test_ifi_score_yellow():
    score = IfiScore(70.0)
    assert score.label == "yellow"

def test_ifi_score_red():
    score = IfiScore(40.0)
    assert score.label == "red"

def test_ifi_score_invalid():
    with pytest.raises(ValueError):
        IfiScore(150.0)
''',
    "tests/unit/domain/test_rom_measurement.py": '''"""Tests del value object RomMeasurement."""
from domain.value_objects.rom_measurement import RomMeasurement

def test_rom_percentage():
    rom = RomMeasurement(achieved_degrees=85.0, expected_degrees=100.0)
    assert rom.percentage == 85.0

def test_rom_percentage_zero_expected():
    rom = RomMeasurement(achieved_degrees=50.0, expected_degrees=0.0)
    assert rom.percentage == 0.0
''',
    "tests/unit/app/__init__.py": "",
    "tests/unit/infrastructure/__init__.py": "",
    "tests/integration/__init__.py": "",
    "tests/integration/supabase/__init__.py": "",
    "tests/integration/biomechanics/__init__.py": "",

    # ── raiz del proyecto ─────────────────────────────────────────────────────
    ".env.example": '''# Copiar a .env y completar con valores reales
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
''',
    ".gitignore": '''.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
''',
    "requirements.txt": '''streamlit>=1.35.0
supabase>=2.4.0
mediapipe>=0.10.0
opencv-python>=4.9.0
numpy>=1.26.0
python-dotenv>=1.0.0
''',
    "requirements-dev.txt": '''-r requirements.txt
pytest>=8.0.0
pytest-cov>=5.0.0
''',
    "README.md": '''# FlexIA — Plataforma SaaS de Rehabilitacion Biomecanica

## Estructura del proyecto

```
flexia/
├── app/          # Casos de uso (orquestacion)
├── domain/       # Modelos, interfaces y value objects
├── frontend/     # Streamlit (solo presentacion)
├── infrastructure/ # Supabase + MediaPipe (implementaciones)
├── shared/       # Config, logger, excepciones, container DI
└── tests/        # Unit + integration
```

## Setup

```bash
cp .env.example .env
# Completar .env con credenciales de Supabase

python -m venv .venv
source .venv/bin/activate   # Mac/Linux
.venv\\Scripts\\activate    # Windows

pip install -r requirements-dev.txt
```

## Correr la app

```bash
streamlit run frontend/main.py
```

## Correr los tests

```bash
pytest tests/
```

## Desarrolladoras

- **Desarrolladora A**: domain/, infrastructure/, app/use_cases/biomechanics/, app/use_cases/sessions/
- **Desarrolladora B**: frontend/, app/use_cases/patients/, app/use_cases/routines/, app/dto/
''',
}

def create_structure(base_path: str = "flexia"):
    created_files = 0
    created_dirs = 0

    for relative_path, content in FILES.items():
        full_path = os.path.join(base_path, relative_path)
        dir_path = os.path.dirname(full_path)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            created_dirs += 1

        if not os.path.exists(full_path):
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            created_files += 1

    print(f"\nEstructura FlexIA creada en '{base_path}/'")
    print(f"{created_dirs} carpetas creadas")
    print(f"{created_files} archivos creados")
    print(f"\nProximos pasos:")
    print(f"  1. cd {base_path}")
    print(f"  2. cp .env.example .env  →  completar con credenciales Supabase")
    print(f"  3. python -m venv .venv && source .venv/bin/activate")
    print(f"  4. pip install -r requirements-dev.txt")
    print(f"  5. streamlit run frontend/main.py")
    print(f"  6. pytest tests/\n")

if __name__ == "__main__":
    create_structure()