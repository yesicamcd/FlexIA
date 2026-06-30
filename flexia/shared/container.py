"""
shared/container.py

Contenedor de inyeccion de dependencias.
Unico lugar donde se instancian servicios y use cases.
El frontend importa desde aqui — nunca instancia directamente
clases de infrastructure/.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from infrastructure.biomechanics.feedback.feedback_config import FeedbackConfig
from infrastructure.biomechanics.mediapipe_service import MediaPipeBiomechanicsService
from infrastructure.supabase.client import get_supabase_admin_client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_biomechanics_service(
    feedback_config: Optional[FeedbackConfig] = None,
) -> MediaPipeBiomechanicsService:
    """Instancia unica del motor biomecanico."""
    logger.info("Inicializando servicio biomecanico...")
    return MediaPipeBiomechanicsService(
        supabase_client=get_supabase_admin_client(),
        feedback_config=feedback_config or FeedbackConfig.default(),
    )


def get_create_session_use_case():
    """Use case para crear sesiones."""
    from app.use_cases.sessions.create_session_use_case import CreateSessionUseCase
    return CreateSessionUseCase(get_supabase_admin_client())


def get_process_video_use_case():
    """Use case para lanzar el motor biomecanico."""
    from app.use_cases.biomechanics.process_video_use_case import ProcessVideoUseCase
    return ProcessVideoUseCase(get_supabase_admin_client())


def get_session_results_use_case():
    """Use case para leer resultados de una sesion."""
    from app.use_cases.sessions.get_session_results_use_case import GetSessionResultsUseCase
    return GetSessionResultsUseCase(get_supabase_admin_client())


def get_create_patient_use_case():
    """Use case para dar de alta pacientes."""
    from app.use_cases.patients.create_patient_use_case import CreatePatientUseCase
    from infrastructure.supabase.repositories.supabase_patient_repository import SupabasePatientRepository
    return CreatePatientUseCase(SupabasePatientRepository(get_supabase_admin_client()))


def get_patient_repository():
    """Repositorio de pacientes."""
    from infrastructure.supabase.repositories.supabase_patient_repository import SupabasePatientRepository
    return SupabasePatientRepository(get_supabase_admin_client())


def get_session_repository():
    """Repositorio de sesiones."""
    from infrastructure.supabase.repositories.supabase_session_repository import SupabaseSessionRepository
    return SupabaseSessionRepository(get_supabase_admin_client())


def get_patient_history_use_case():
    """Use case para obtener historial de un paciente."""
    from app.use_cases.patients.get_patient_history_use_case import GetPatientHistoryUseCase
    return GetPatientHistoryUseCase(get_supabase_admin_client())

def get_register_professional_use_case():
    """Use case para dar de alta profesionales con Auth sincronizado."""
    from app.use_cases.auth.register_professional_use_case import RegisterProfessionalUseCase
    return RegisterProfessionalUseCase(get_supabase_admin_client())