"""
infrastructure/biomechanics/capture/video_recorder.py

Graba frames de video a disco en tiempo real durante la sesion.

Genera un archivo de video por camara. Los archivos se guardan
localmente durante la sesion y se suben a Supabase Storage
al finalizar mediante storage/video_uploader.py.

El codec y formato son configurables. Por defecto usa MP4V
que genera archivos .mp4 compatibles con la mayoria de sistemas.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from infrastructure.biomechanics.capture.camera_manager import CameraRole
from shared.constants import CAPTURE_FPS, CAPTURE_HEIGHT, CAPTURE_WIDTH

logger = logging.getLogger(__name__)

# Directorio temporal para videos grabados durante la sesion.
# Se limpia despues de subir los archivos a Supabase.
_RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "recordings"


class VideoRecorderError(Exception):
    """Error especifico del grabador de video."""


class VideoRecorder:
    """
    Graba frames de video a disco en tiempo real.

    Una instancia por camara por sesion.
    El archivo se crea al llamar start() y se cierra al llamar stop().

    Uso:
        recorder = VideoRecorder(
            session_id='uuid-sesion',
            role=CameraRole.FRONT,
        )
        recorder.start()
        for frame in frames:
            recorder.write_frame(frame)
        output_path = recorder.stop()
        # output_path es la ruta al archivo grabado
    """

    def __init__(
        self,
        session_id: str,
        role: CameraRole,
        fps: int = CAPTURE_FPS,
        width: int = CAPTURE_WIDTH,
        height: int = CAPTURE_HEIGHT,
        output_dir: Optional[Path] = None,
    ) -> None:
        """
        Args:
            session_id: UUID de la sesion. Forma parte del nombre
                        del archivo para trazabilidad.
            role: rol de la camara (FRONT o LATERAL).
            fps: frames por segundo del video grabado.
                 Debe coincidir con los FPS de captura para
                 que el video se reproduzca a velocidad correcta.
            width: ancho del frame en pixeles.
            height: alto del frame en pixeles.
            output_dir: directorio de salida. Si es None usa
                        el directorio recordings/ del modulo.
        """
        self._session_id = session_id
        self._role = role
        self._fps = fps
        self._width = width
        self._height = height
        self._output_dir = output_dir or _RECORDINGS_DIR
        self._writer: Optional[cv2.VideoWriter] = None
        self._output_path: Optional[Path] = None
        self._frame_count: int = 0
        self._started: bool = False

    @property
    def is_recording(self) -> bool:
        """Indica si la grabacion esta activa."""
        return self._started and self._writer is not None

    @property
    def frame_count(self) -> int:
        """Cantidad de frames grabados hasta el momento."""
        return self._frame_count

    @property
    def output_path(self) -> Optional[Path]:
        """
        Ruta al archivo de video.
        Disponible desde que se llama start() hasta que
        el archivo es eliminado del disco.
        """
        return self._output_path

    def start(self) -> Path:
        """
        Crea el archivo de video e inicia la grabacion.

        El nombre del archivo incluye el session_id y el rol
        de la camara para identificacion unica.

        Returns:
            Path al archivo de video que se esta grabando.

        Raises:
            VideoRecorderError: si el writer no pudo inicializarse.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._build_filename()
        self._output_path = self._output_dir / filename

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(
            str(self._output_path),
            fourcc,
            self._fps,
            (self._width, self._height),
        )

        if not self._writer.isOpened():
            self._writer = None
            raise VideoRecorderError(
                f"No se pudo inicializar el grabador de video para "
                f"camara {self._role.name}. "
                f"Verificar que el codec MP4V esta disponible en el sistema."
            )

        self._frame_count = 0
        self._started = True

        logger.info(
            "Grabacion iniciada: %s (%dx%d @ %dfps).",
            self._output_path.name,
            self._width, self._height, self._fps,
        )

        return self._output_path

    def write_frame(self, frame: np.ndarray) -> None:
        """
        Escribe un frame al archivo de video.

        Si el frame tiene dimensiones distintas a las configuradas,
        lo redimensiona automaticamente para evitar archivos corruptos.

        Args:
            frame: frame en formato BGR como numpy array.

        Raises:
            VideoRecorderError: si se llama antes de start().
        """
        if not self.is_recording:
            raise VideoRecorderError(
                "write_frame() llamado antes de start(). "
                "Iniciar la grabacion primero."
            )

        if frame is None:
            logger.warning(
                "Frame None recibido en grabacion %s. Ignorado.",
                self._role.name,
            )
            return

        resized = self._ensure_dimensions(frame)
        self._writer.write(resized)
        self._frame_count += 1

    def write_frame_safe(self, frame: np.ndarray) -> None:
        """
        Escribe un frame sin lanzar excepcion si falla.
        Util en el loop principal donde un frame perdido
        no debe interrumpir la sesion.
        """
        try:
            self.write_frame(frame)
        except VideoRecorderError as e:
            logger.warning("Error al grabar frame: %s", str(e))

    def stop(self) -> Optional[Path]:
        """
        Finaliza la grabacion y cierra el archivo.

        Returns:
            Path al archivo grabado, o None si la grabacion
            nunca fue iniciada.
        """
        if self._writer is not None:
            self._writer.release()
            self._writer = None

        self._started = False

        if self._output_path is not None and self._output_path.exists():
            size_mb = self._output_path.stat().st_size / (1024 * 1024)
            logger.info(
                "Grabacion finalizada: %s — %d frames, %.2f MB.",
                self._output_path.name,
                self._frame_count,
                size_mb,
            )
            return self._output_path

        return None

    def discard(self) -> None:
        """
        Detiene la grabacion y elimina el archivo del disco.
        Usar cuando la sesion fue cancelada antes de completarse
        y no se quiere subir el video a Supabase.
        """
        path = self.stop()
        if path is not None and path.exists():
            path.unlink()
            logger.info("Grabacion descartada: %s", path.name)

    def _build_filename(self) -> str:
        """
        Construye el nombre del archivo de video.
        Formato: {session_id}_{role}_{timestamp}.mp4
        El timestamp evita colisiones si se graba mas de una
        sesion con el mismo ID en el mismo dia.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        role_name = self._role.name.lower()
        short_id = self._session_id[:8]
        return f"{short_id}_{role_name}_{timestamp}.mp4"

    def _ensure_dimensions(self, frame: np.ndarray) -> np.ndarray:
        """
        Redimensiona el frame si sus dimensiones no coinciden
        con las configuradas para el grabador.
        Evita archivos de video corruptos por frames inconsistentes.
        """
        h, w = frame.shape[:2]
        if w != self._width or h != self._height:
            logger.debug(
                "Frame redimensionado de %dx%d a %dx%d.",
                w, h, self._width, self._height,
            )
            return cv2.resize(frame, (self._width, self._height))
        return frame