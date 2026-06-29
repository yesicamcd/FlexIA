from __future__ import annotations

"""
shared/container.py

Contenedor de inyeccion de dependencias.
Unico lugar donde se instancian los servicios y se conectan
con sus dependencias concretas.

El resto del sistema importa desde aca — nunca instancia
directamente clases de infrastructure/.
"""

from typing import Optional

import logging
from functools import lru_cache

from infrastructure.biomechanics.feedback.feedback_config import FeedbackConfig
from infrastructure.biomechanics.mediapipe_service import (
    MediaPipeBiomechanicsService,
)
from infrastructure.supabase.client import get_supabase_admin_client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_biomechanics_service(
    feedback_config: Optional[FeedbackConfig] = None,
) -> MediaPipeBiomechanicsService:
    """
    Devuelve la instancia unica del servicio biomecanico.

    Usa lru_cache para garantizar que solo existe una instancia
    durante toda la vida de la aplicacion — el modelo de MediaPipe
    es pesado y no debe cargarse mas de una vez.

    Args:
        feedback_config: configuracion de audio y visual.
                         Si es None usa FeedbackConfig.default().

    Returns:
        Instancia configurada de MediaPipeBiomechanicsService.
    """
    logger.info("Inicializando servicio biomecanico...")
    return MediaPipeBiomechanicsService(
        supabase_client=get_supabase_admin_client(),
        feedback_config=feedback_config or FeedbackConfig.default(),
    )