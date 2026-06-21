"""Implementacion del servicio de biomecanica con MediaPipe."""
from domain.interfaces.services.i_biomechanics_service import IBiomechanicsService

class MediaPipeBiomechanicsService(IBiomechanicsService):
    def process_video(self, video_path: str, exercises: list) -> list:
        # TODO: implementar pipeline completo
        raise NotImplementedError
