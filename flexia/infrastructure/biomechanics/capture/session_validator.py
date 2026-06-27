"""
infrastructure/biomechanics/capture/session_validator.py

Ejecuta los pre-checks de validacion antes de iniciar una sesion.

Verifica:
    - Camaras disponibles y entregando frames
    - Cuerpo del paciente visible con confianza suficiente
    - Iluminacion minima aceptable
    - Paciente correctamente encuadrado en el frame

Cada check es independiente y se reporta por separado para
que el kinesiologo sepa exactamente que corregir antes de iniciar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from infrastructure.biomechanics.analysis.pose_estimator import (
    PoseEstimator,
    PoseLandmarks,
)
from infrastructure.biomechanics.capture.camera_manager import (
    CameraManager,
    CameraError,
)
from shared.constants import (
    MIN_BRIGHTNESS,
    MIN_BODY_FRAME_RATIO,
    MIN_POSE_CONFIDENCE,
)

logger = logging.getLogger(__name__)

# Landmarks que deben ser visibles para considerar el cuerpo encuadrado.
# Incluye puntos clave del tronco y extremidades inferiores.
_REQUIRED_LANDMARKS: list[int] = [
    PoseEstimator.LANDMARK_INDEX["left_shoulder"],
    PoseEstimator.LANDMARK_INDEX["right_shoulder"],
    PoseEstimator.LANDMARK_INDEX["left_hip"],
    PoseEstimator.LANDMARK_INDEX["right_hip"],
    PoseEstimator.LANDMARK_INDEX["left_knee"],
    PoseEstimator.LANDMARK_INDEX["right_knee"],
]


@dataclass
class ValidationResult:
    """
    Resultado de los pre-checks de validacion de sesion.

    Cada campo representa un check independiente.
    True = check superado. False = check fallido.

    Atributos:
        camera_front_ok: camara frontal disponible y entregando frames.
        camera_lateral_ok: camara lateral disponible y entregando frames.
        body_visible: cuerpo del paciente detectado con confianza suficiente.
        brightness_ok: iluminacion minima aceptable en ambas camaras.
        framing_ok: paciente correctamente encuadrado (cuerpo completo visible).
        brightness_value: valor de brillo medido (0-255) para diagnostico.
        missing_landmarks: indices de landmarks que no tienen visibilidad
                           suficiente, para ayudar al kinesiologo a
                           corregir el encuadre.
    """

    camera_front_ok: bool = False
    camera_lateral_ok: bool = False
    body_visible: bool = False
    brightness_ok: bool = False
    framing_ok: bool = False
    brightness_value: float = 0.0
    missing_landmarks: list[int] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """True si todos los checks fueron superados."""
        return (
            self.camera_front_ok
            and self.camera_lateral_ok
            and self.body_visible
            and self.brightness_ok
            and self.framing_ok
        )

    @property
    def as_display_dict(self) -> dict[str, bool]:
        """
        Diccionario con nombres legibles para mostrar en pantalla.
        Usado por VisualRenderer.render_validation_status().
        """
        return {
            "Camara frontal":   self.camera_front_ok,
            "Camara lateral":   self.camera_lateral_ok,
            "Cuerpo visible":   self.body_visible,
            "Iluminacion OK":   self.brightness_ok,
            "Encuadre OK":      self.framing_ok,
        }

    def describe(self) -> str:
        """Descripcion textual del resultado para logs."""
        lines = ["Resultado de validacion:"]
        for name, passed in self.as_display_dict.items():
            symbol = "OK" if passed else "FALLO"
            lines.append(f"  [{symbol}] {name}")
        if self.missing_landmarks:
            lines.append(f"  Landmarks faltantes: {self.missing_landmarks}")
        lines.append(f"  Brillo medido: {self.brightness_value:.1f} / {MIN_BRIGHTNESS} minimo")
        return "\n".join(lines)


class SessionValidator:
    """
    Ejecuta los pre-checks de validacion antes de iniciar una sesion.

    Uso:
        validator = SessionValidator(pose_estimator)
        result = validator.validate(
            front_camera=cam_front,
            lateral_camera=cam_lateral,
        )
        if result.all_passed:
            session_runner.start_countdown()
        else:
            renderer.render_validation_status(frame, result.as_display_dict)
    """

    def __init__(self, pose_estimator: PoseEstimator) -> None:
        self._estimator = pose_estimator

    def validate(
        self,
        front_camera: CameraManager,
        lateral_camera: CameraManager,
    ) -> ValidationResult:
        """
        Ejecuta todos los checks de validacion.

        Lee un frame de cada camara y ejecuta los checks
        sobre esos frames. No modifica el estado de las camaras.

        Args:
            front_camera: camara frontal ya abierta.
            lateral_camera: camara lateral ya abierta.

        Returns:
            ValidationResult con el estado de cada check.
        """
        result = ValidationResult()

        front_frame = self._check_camera(front_camera, "frontal")
        lateral_frame = self._check_camera(lateral_camera, "lateral")

        result.camera_front_ok = front_frame is not None
        result.camera_lateral_ok = lateral_frame is not None

        if front_frame is None:
            logger.warning("Validacion abortada: camara frontal no disponible.")
            return result

        brightness = self._measure_brightness(front_frame)
        result.brightness_value = brightness
        result.brightness_ok = brightness >= MIN_BRIGHTNESS

        if not result.brightness_ok:
            logger.warning(
                "Iluminacion insuficiente: %.1f (minimo requerido: %d).",
                brightness, MIN_BRIGHTNESS,
            )

        landmarks = self._estimator.estimate(front_frame)

        if landmarks is None:
            logger.warning("No se detecto pose en el frame frontal.")
            return result

        result.body_visible = self._check_body_visible(landmarks)
        result.framing_ok, result.missing_landmarks = self._check_framing(
            landmarks, front_frame
        )

        logger.info(result.describe())
        return result

    def _check_camera(
        self,
        camera: CameraManager,
        name: str,
    ) -> np.ndarray | None:
        """
        Verifica que la camara esta abierta y puede leer frames.

        Returns:
            Frame leido, o None si la camara no esta disponible.
        """
        if not camera.is_open:
            logger.warning("Camara %s no esta abierta.", name)
            return None

        frame = camera.read_frame_safe()
        if frame is None:
            logger.warning("Camara %s no pudo leer un frame.", name)
            return None

        return frame

    def _measure_brightness(self, frame: np.ndarray) -> float:
        """
        Mide el brillo promedio del frame en escala de grises.

        Convierte a escala de grises y calcula el promedio de todos
        los pixeles. Valor entre 0 (negro total) y 255 (blanco total).

        Este metodo es reutilizable para cualquier proyecto que necesite
        validacion de iluminacion minima con OpenCV.
        """
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def _check_body_visible(self, landmarks: PoseLandmarks) -> bool:
        """
        Verifica que los landmarks clave del cuerpo tienen
        confianza de deteccion suficiente.

        Usa MIN_POSE_CONFIDENCE de constants.py como umbral.
        """
        return all(
            landmarks.is_visible(idx, MIN_POSE_CONFIDENCE)
            for idx in _REQUIRED_LANDMARKS
        )

    def _check_framing(
        self,
        landmarks: PoseLandmarks,
        frame: np.ndarray,
    ) -> tuple[bool, list[int]]:
        """
        Verifica que el cuerpo del paciente ocupa suficiente
        espacio en el frame y que los landmarks requeridos
        estan dentro del encuadre.

        El encuadre se considera correcto cuando:
            1. Todos los landmarks requeridos son visibles.
            2. El area del bounding box del cuerpo ocupa al menos
               MIN_BODY_FRAME_RATIO del frame total.

        Returns:
            Tupla (framing_ok, missing_landmarks).
        """
        h, w = frame.shape[:2]
        frame_area = h * w

        missing = [
            idx for idx in _REQUIRED_LANDMARKS
            if not landmarks.is_visible(idx, 0.4)
        ]

        if missing:
            return False, missing

        visible_x = [
            landmarks.get(idx).x * w
            for idx in _REQUIRED_LANDMARKS
            if landmarks.is_visible(idx, 0.4)
        ]
        visible_y = [
            landmarks.get(idx).y * h
            for idx in _REQUIRED_LANDMARKS
            if landmarks.is_visible(idx, 0.4)
        ]

        if not visible_x or not visible_y:
            return False, _REQUIRED_LANDMARKS

        body_w = max(visible_x) - min(visible_x)
        body_h = max(visible_y) - min(visible_y)
        body_area = body_w * body_h

        ratio = body_area / frame_area
        framing_ok = ratio >= MIN_BODY_FRAME_RATIO

        if not framing_ok:
            logger.warning(
                "Encuadre insuficiente: el cuerpo ocupa %.1f%% del frame "
                "(minimo requerido: %.1f%%).",
                ratio * 100,
                MIN_BODY_FRAME_RATIO * 100,
            )

        return framing_ok, []