"""
infrastructure/biomechanics/capture/camera_manager.py

Gestiona el ciclo de vida de una camara individual usando OpenCV.
Es el unico archivo del sistema con acceso directo a hardware de camara.

Si la camara no esta disponible o falla durante la sesion,
lanza excepciones especificas que capture/dual_capture.py
puede manejar sin interrumpir el sistema completo.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Optional

import cv2
import numpy as np

from shared.constants import (
    CAPTURE_FPS,
    CAPTURE_HEIGHT,
    CAPTURE_WIDTH,
)

logger = logging.getLogger(__name__)


class CameraRole(Enum):
    """
    Rol de la camara dentro del sistema de captura dual.
    Define su posicion fisica respecto al paciente.
    """

    FRONT = auto()
    LATERAL = auto()


class CameraError(Exception):
    """
    Error especifico de camara. Permite que el caller
    distinga entre errores de hardware y otros errores del sistema.
    """


class CameraManager:
    """
    Gestiona una camara individual: apertura, configuracion,
    lectura de frames y cierre.

    Una instancia por camara fisica. El indice de camara
    corresponde al indice de OpenCV (0 = primera camara del sistema).

    Uso:
        cam = CameraManager(index=0, role=CameraRole.FRONT)
        cam.open()
        frame = cam.read_frame()
        cam.close()

    O como context manager:
        with CameraManager(index=0, role=CameraRole.FRONT) as cam:
            frame = cam.read_frame()
    """

    def __init__(
        self,
        index: int,
        role: CameraRole,
        width: int = CAPTURE_WIDTH,
        height: int = CAPTURE_HEIGHT,
        fps: int = CAPTURE_FPS,
    ) -> None:
        """
        Args:
            index: indice de camara de OpenCV (0, 1, 2...).
            role: rol de la camara (FRONT o LATERAL).
            width: ancho de captura en pixeles.
            height: alto de captura en pixeles.
            fps: frames por segundo solicitados al driver.
                 El driver puede no respetar exactamente este valor.
        """
        self._index = index
        self._role = role
        self._width = width
        self._height = height
        self._fps = fps
        self._capture: Optional[cv2.VideoCapture] = None

    @property
    def role(self) -> CameraRole:
        return self._role

    @property
    def index(self) -> int:
        return self._index

    @property
    def is_open(self) -> bool:
        """Indica si la camara esta actualmente abierta y lista."""
        return (
            self._capture is not None
            and self._capture.isOpened()
        )

    @property
    def actual_fps(self) -> float:
        """FPS reales reportados por el driver de la camara."""
        if not self.is_open:
            return 0.0
        return self._capture.get(cv2.CAP_PROP_FPS)

    @property
    def actual_width(self) -> int:
        """Ancho real de captura reportado por el driver."""
        if not self.is_open:
            return 0
        return int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def actual_height(self) -> int:
        """Alto real de captura reportado por el driver."""
        if not self.is_open:
            return 0
        return int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def open(self) -> None:
        """
        Abre la camara y aplica la configuracion solicitada.

        El driver puede no respetar exactamente la resolucion
        y FPS solicitados — los valores reales se pueden consultar
        con actual_fps, actual_width y actual_height.

        Raises:
            CameraError: si la camara no pudo abrirse.
        """
        logger.info(
            "Abriendo camara %s (indice=%d, %dx%d @ %dfps).",
            self._role.name, self._index,
            self._width, self._height, self._fps,
        )

        self._capture = cv2.VideoCapture(self._index)

        if not self._capture.isOpened():
            raise CameraError(
                f"No se pudo abrir la camara {self._role.name} "
                f"(indice={self._index}). "
                f"Verificar que la camara esta conectada y no esta "
                f"siendo usada por otra aplicacion."
            )

        self._apply_settings()

        logger.info(
            "Camara %s abierta. Resolucion real: %dx%d @ %.1ffps.",
            self._role.name,
            self.actual_width, self.actual_height, self.actual_fps,
        )

    def read_frame(self) -> np.ndarray:
        """
        Lee el siguiente frame de la camara.

        Returns:
            Frame en formato BGR como numpy array (H, W, 3).

        Raises:
            CameraError: si la camara no esta abierta o la lectura falla.
        """
        if not self.is_open:
            raise CameraError(
                f"Camara {self._role.name} no esta abierta. "
                f"Llamar open() antes de read_frame()."
            )

        success, frame = self._capture.read()

        if not success or frame is None:
            raise CameraError(
                f"Fallo la lectura de frame en camara {self._role.name} "
                f"(indice={self._index}). "
                f"La camara puede haber sido desconectada."
            )

        return frame

    def read_frame_safe(self) -> Optional[np.ndarray]:
        """
        Lee el siguiente frame sin lanzar excepcion si falla.
        Devuelve None en caso de error.

        Util para el loop de captura donde un frame perdido
        no debe interrumpir la sesion.
        """
        try:
            return self.read_frame()
        except CameraError as e:
            logger.warning("Frame perdido en camara %s: %s", self._role.name, str(e))
            return None

    def close(self) -> None:
        """
        Libera los recursos de la camara.
        Seguro de llamar aunque la camara no este abierta.
        """
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("Camara %s liberada.", self._role.name)

    def __enter__(self) -> CameraManager:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _apply_settings(self) -> None:
        """
        Aplica la configuracion de resolucion y FPS al driver.
        Los drivers de camara pueden ignorar estos valores parcialmente.
        """
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._capture.set(cv2.CAP_PROP_FPS, self._fps)

        # Reducir el buffer interno de OpenCV a 1 frame
        # para minimizar latencia en captura en tiempo real.
        # Con buffer mayor, read_frame() devuelve frames antiguos
        # que ya estaban en cola, introduciendo lag visual.
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)