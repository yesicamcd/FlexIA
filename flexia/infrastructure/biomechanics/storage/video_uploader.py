"""
infrastructure/biomechanics/storage/video_uploader.py

Sube los videos grabados durante la sesion a Supabase Storage
y persiste los resultados biomecanicos en la base de datos.

Se ejecuta despues de que el motor biomecanico termino de procesar.
Si la subida falla, los resultados biomecanicos ya calculados
no se pierden — estan en SessionState y MappedSessionResult.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from supabase import Client

from infrastructure.biomechanics.capture.camera_manager import CameraRole
from infrastructure.biomechanics.storage.result_mapper import MappedSessionResult
from shared.constants import STORAGE_BUCKET_VIDEOS, STORAGE_PATH_TEMPLATE

logger = logging.getLogger(__name__)


class VideoUploadError(Exception):
    """Error especifico de subida de video a Supabase Storage."""


class VideoUploader:
    """
    Sube videos grabados a Supabase Storage y persiste resultados.

    Uso:
        uploader = VideoUploader(supabase_client)
        uploader.upload_and_persist(
            mapped_result=mapped,
            center_id='uuid-centro',
            front_video_path=Path('recordings/abc_front.mp4'),
            lateral_video_path=Path('recordings/abc_lateral.mp4'),
        )
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def upload_and_persist(
        self,
        mapped_result: MappedSessionResult,
        center_id: str,
        front_video_path: Optional[Path] = None,
        lateral_video_path: Optional[Path] = None,
    ) -> None:
        """
        Sube los videos y persiste todos los resultados en Supabase.

        El orden de operaciones es importante:
            1. Subir videos a Storage (puede fallar sin perder datos)
            2. Actualizar tabla sessions (status + ifi_score)
            3. Insertar exercise_results

        Si la subida de video falla, las operaciones 2 y 3 igual
        se ejecutan — los resultados clinicos son mas importantes
        que el video.

        Args:
            mapped_result: resultado mapeado por ResultMapper.
            center_id: UUID del centro para construir la ruta en Storage.
            front_video_path: ruta al video frontal grabado. None si no
                              se grabo o si la grabacion fallo.
            lateral_video_path: ruta al video lateral grabado.
        """
        if not mapped_result.was_successful:
            logger.warning(
                "Sesion %s sin resultados. No se persiste nada.",
                mapped_result.session_id[:8],
            )
            return

        self._upload_videos(
            session_id=mapped_result.session_id,
            center_id=center_id,
            front_path=front_video_path,
            lateral_path=lateral_video_path,
        )

        self._update_session(mapped_result)
        self._insert_exercise_results(mapped_result)

        logger.info(
            "Sesion %s persistida: %d ejercicios, IFI=%s.",
            mapped_result.session_id[:8],
            len(mapped_result.exercise_results),
            f"{mapped_result.ifi_score.value:.1f}"
            if mapped_result.ifi_score else "N/A",
        )

    def _upload_videos(
        self,
        session_id: str,
        center_id: str,
        front_path: Optional[Path],
        lateral_path: Optional[Path],
    ) -> None:
        """
        Sube los archivos de video a Supabase Storage.

        Los sube al bucket configurado en STORAGE_BUCKET_VIDEOS
        usando la ruta definida en STORAGE_PATH_TEMPLATE.

        Si alguna subida falla, loguea el error y continua
        con la persistencia de resultados — el video no es
        critico para el registro clinico.
        """
        videos = [
            (front_path, CameraRole.FRONT),
            (lateral_path, CameraRole.LATERAL),
        ]

        for path, role in videos:
            if path is None or not path.exists():
                logger.info(
                    "Video %s no disponible para subir. Omitido.",
                    role.name,
                )
                continue

            storage_path = STORAGE_PATH_TEMPLATE.format(
                center_id=center_id,
                session_id=session_id,
                camera=role.name.lower(),
            )

            try:
                self._upload_file(path, storage_path)
                self._register_video(
                    session_id=session_id,
                    storage_path=storage_path,
                    file_path=path,
                )
                path.unlink()
                logger.info(
                    "Video %s subido y archivo local eliminado.",
                    role.name,
                )
            except Exception as e:
                logger.error(
                    "Error al subir video %s: %s. "
                    "El archivo local se conserva en: %s",
                    role.name, str(e), path,
                )

    def _upload_file(self, local_path: Path, storage_path: str) -> None:
        """
        Sube un archivo al bucket de Supabase Storage.

        Args:
            local_path: ruta local al archivo de video.
            storage_path: ruta destino dentro del bucket.

        Raises:
            VideoUploadError: si la subida falla.
        """
        logger.info(
            "Subiendo %s -> %s/%s",
            local_path.name,
            STORAGE_BUCKET_VIDEOS,
            storage_path,
        )

        with open(local_path, "rb") as f:
            file_bytes = f.read()

        response = self._client.storage.from_(STORAGE_BUCKET_VIDEOS).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "video/mp4", "upsert": "true"},
        )

        if hasattr(response, "error") and response.error:
            raise VideoUploadError(
                f"Supabase Storage rechazo la subida: {response.error}"
            )

    def _register_video(
        self,
        session_id: str,
        storage_path: str,
        file_path: Path,
    ) -> None:
        """
        Inserta el registro del video en la tabla videos de Supabase.
        """
        file_size = file_path.stat().st_size

        self._client.table("videos").insert({
            "session_id": session_id,
            "storage_path": storage_path,
            "status": "analyzed",
        }).execute()

    def _update_session(self, mapped_result: MappedSessionResult) -> None:
        """
        Actualiza el registro de la sesion en Supabase con el
        status final y el IFI calculado.
        """
        try:
            self._client.table("sessions").update(
                mapped_result.session_fields
            ).eq(
                "id", mapped_result.session_id
            ).execute()

            logger.info(
                "Sesion %s actualizada en Supabase.",
                mapped_result.session_id[:8],
            )
        except Exception as e:
            logger.error(
                "Error al actualizar sesion %s: %s",
                mapped_result.session_id[:8], str(e),
            )

    def _insert_exercise_results(
        self,
        mapped_result: MappedSessionResult,
    ) -> None:
        if not mapped_result.exercise_results:
            return

        rows = [
            {
                "session_id": result.session_id,
                "routine_exercise_id": result.routine_exercise_id,
                "order_index": result.order_index,
                "rom_achieved": result.rom_achieved,
                "rom_expected": result.rom_expected,
                "rom_percentage": result.rom_percentage,
                "reps_achieved": result.reps_achieved,
                "reps_expected": result.reps_expected,
                "performance": result.performance,
                "frame_count": result.frame_count,
            }
            for result in mapped_result.exercise_results
        ]

        try:
            self._client.table("exercise_results").insert(rows).execute()
            logger.info(
                "%d resultados insertados para sesion %s.",
                len(rows),
                mapped_result.session_id[:8],
            )
        except Exception as e:
            logger.error("Error al insertar exercise_results: %s", str(e))