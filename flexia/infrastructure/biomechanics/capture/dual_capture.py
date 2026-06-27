"""
infrastructure/biomechanics/capture/dual_capture.py

Coordina la captura sincronizada de camaras frontal y lateral.

Gestiona el ciclo de vida de ambas camaras como unidad:
abre, lee frames en pares y cierra ambas de forma segura.

La sincronizacion es por software — ambos frames se leen
en la misma iteracion del loop. Para sincronizacion perfecta
por hardware se necesitaria un trigger externo, lo cual
esta fuera del alcance del MVP.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from infrastructure.biomechanics.capture.camera_manager import (
    CameraManager,
    CameraRole,
    CameraError,
)
from shared.constants import (
    CAMERA_FRONT_INDEX,
    CAMERA_LATERAL_INDEX,
    CAPTURE_FPS,
    CAPTURE_HEIGHT,
    CAPTURE_WIDTH,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FramePair:
    """
    Par de frames capturados en la misma iteracion.

    Atributos:
        front: frame de la camara frontal en formato BGR.
               None si la camara frontal fallo en esta iteracion.
        lateral: frame de la camara lateral en formato BGR.
                 None si la camara lateral fallo en esta iteracion.
        frame_index: numero de iteracion desde el inicio de la sesion.
    """

    front: Optional[np.ndarray]
    lateral: Optional[np.ndarray]
    frame_index: int

    @property
    def both_available(self) -> bool:
        """True si ambas camaras entregaron frame en esta iteracion."""
        return self.front is not None and self.lateral is not None

    @property
    def any_available(self) -> bool:
        """True si al menos una camara entrego frame."""
        return self.front is not None or self.lateral is not None


class DualCaptureError(Exception):
    """Error especifico del sistema de captura dual."""


class DualCapture:
    """
    Gestiona la captura sincronizada de camaras frontal y lateral.

    Abre ambas camaras al iniciar y las cierra al finalizar.
    Lee frames en pares en cada iteracion del loop de sesion.

    Uso:
        capture = DualCapture()
        capture.open()

        while session_active:
            pair = capture.read_frames()
            if pair.both_available:
                process(pair.front, pair.lateral)

        capture.close()

    O como context manager:
        with DualCapture() as capture:
            pair = capture.read_frames()
    """

    def __init__(
        self,
        front_index: int = CAMERA_FRONT_INDEX,
        lateral_index: int = CAMERA_LATERAL_INDEX,
        width: int = CAPTURE_WIDTH,
        height: int = CAPTURE_HEIGHT,
        fps: int = CAPTURE_FPS,
    ) -> None:
        """
        Args:
            front_index: indice OpenCV de la camara frontal.
            lateral_index: indice OpenCV de la camara lateral.
            width: ancho de captura solicitado a ambas camaras.
            height: alto de captura solicitado a ambas camaras.
            fps: FPS solicitados a ambas camaras.
        """
        self._front = CameraManager(
            index=front_index,
            role=CameraRole.FRONT,
            width=width,
            height=height,
            fps=fps,
        )
        self._lateral = CameraManager(
            index=lateral_index,
            role=CameraRole.LATERAL,
            width=width,
            height=height,
            fps=fps,
        )
        self._frame_index: int = 0

    @property
    def front_camera(self) -> CameraManager:
        """Acceso a la camara frontal para validacion y configuracion."""
        return self._front

    @property
    def lateral_camera(self) -> CameraManager:
        """Acceso a la camara lateral para validacion y configuracion."""
        return self._lateral

    @property
    def is_open(self) -> bool:
        """True si ambas camaras estan abiertas."""
        return self._front.is_open and self._lateral.is_open

    @property
    def frame_index(self) -> int:
        """Numero de iteraciones completadas desde open()."""
        return self._frame_index

    def open(self) -> None:
        """
        Abre ambas camaras.

        Si la camara frontal falla, aborta sin intentar abrir
        la lateral — la frontal es la camara primaria del sistema
        y sin ella no tiene sentido iniciar la sesion.

        Si la camara lateral falla despues de abrir la frontal,
        cierra la frontal antes de lanzar la excepcion para
        no dejar recursos abiertos.

        Raises:
            DualCaptureError: si alguna camara no pudo abrirse.
        """
        try:
            self._front.open()
        except CameraError as e:
            raise DualCaptureError(
                f"No se pudo abrir la camara frontal: {e}"
            ) from e

        try:
            self._lateral.open()
        except CameraError as e:
            self._front.close()
            raise DualCaptureError(
                f"No se pudo abrir la camara lateral: {e}"
            ) from e

        self._frame_index = 0
        logger.info("Sistema de captura dual inicializado correctamente.")

    def read_frames(self) -> FramePair:
        """
        Lee un frame de cada camara en la misma iteracion.

        Usa read_frame_safe() para que un frame perdido en una
        camara no interrumpa la captura de la otra. El caller
        decide que hacer cuando solo una camara entrega frame.

        Returns:
            FramePair con los frames de ambas camaras y el
            indice de iteracion actual.
        """
        front_frame = self._front.read_frame_safe()
        lateral_frame = self._lateral.read_frame_safe()

        self._frame_index += 1

        if not FramePair(front_frame, lateral_frame, self._frame_index).both_available:
            logger.warning(
                "Frame %d: captura incompleta — "
                "frontal=%s, lateral=%s.",
                self._frame_index,
                "OK" if front_frame is not None else "FALLO",
                "OK" if lateral_frame is not None else "FALLO",
            )

        return FramePair(
            front=front_frame,
            lateral=lateral_frame,
            frame_index=self._frame_index,
        )

    def close(self) -> None:
        """
        Cierra ambas camaras de forma segura.
        Siempre intenta cerrar ambas aunque una falle.
        """
        self._front.close()
        self._lateral.close()
        logger.info(
            "Sistema de captura dual cerrado. "
            "Total de iteraciones: %d.",
            self._frame_index,
        )

    def __enter__(self) -> DualCapture:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()