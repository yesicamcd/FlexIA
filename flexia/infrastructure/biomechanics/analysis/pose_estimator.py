"""
infrastructure/biomechanics/analysis/pose_estimator.py

Extrae landmarks de pose humana desde un frame de video usando
la API moderna de MediaPipe (mp.tasks), compatible con MediaPipe >= 0.10.
Es el unico archivo del sistema con dependencia directa de MediaPipe.
Si el modelo o la libreria cambian, solo este archivo se modifica.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark


@dataclass(frozen=True)
class Landmark:
    """
    Posicion normalizada de un punto del cuerpo en el frame.

    Atributos:
        x: posicion horizontal normalizada entre 0.0 y 1.0.
        y: posicion vertical normalizada entre 0.0 y 1.0.
        z: profundidad relativa normalizada. Negativo = mas cerca de la camara.
        visibility: confianza de deteccion entre 0.0 y 1.0.
        presence: probabilidad de que el punto este dentro del frame.
    """

    x: float
    y: float
    z: float
    visibility: float
    presence: float


@dataclass(frozen=True)
class PoseLandmarks:
    """
    Conjunto completo de landmarks detectados en un frame.
    Contiene los 33 puntos del modelo de pose de MediaPipe.

    El acceso a cada punto se hace por nombre usando los indices
    definidos en PoseEstimator.LANDMARK_INDEX para evitar magic numbers.
    """

    landmarks: tuple[Landmark, ...]

    def get(self, index: int) -> Landmark:
        """
        Devuelve el landmark en la posicion indicada.

        Args:
            index: indice del landmark segun el modelo de MediaPipe (0-32).

        Raises:
            IndexError: si el indice esta fuera del rango valido.
        """
        if not (0 <= index < len(self.landmarks)):
            raise IndexError(
                f"Indice de landmark invalido: {index}. "
                f"Rango valido: 0-{len(self.landmarks) - 1}."
            )
        return self.landmarks[index]

    def is_visible(self, index: int, min_visibility: float = 0.5) -> bool:
        """
        Indica si un landmark tiene suficiente confianza para usarse
        en calculos biomecanicos.

        Args:
            index: indice del landmark.
            min_visibility: umbral minimo de confianza (default 0.5).
        """
        return self.get(index).visibility >= min_visibility

    def is_present(self, index: int, min_presence: float = 0.5) -> bool:
        """
        Indica si un landmark esta probablemente dentro del encuadre.
        Complementa is_visible para casos donde el punto esta ocluido
        pero dentro del frame.

        Args:
            index: indice del landmark.
            min_presence: umbral minimo de presencia (default 0.5).
        """
        return self.get(index).presence >= min_presence


class PoseEstimator:
    """
    Wrapper sobre MediaPipe PoseLandmarker para extraccion de landmarks.
    Usa la API moderna mp.tasks compatible con MediaPipe >= 0.10.

    Uso:
        estimator = PoseEstimator(model_path="ruta/al/modelo.task")
        landmarks = estimator.estimate(frame)
        if landmarks is not None:
            hip = landmarks.get(PoseEstimator.LANDMARK_INDEX["left_hip"])
        estimator.release()
    """

    # Indices de landmarks segun el modelo de MediaPipe Pose.
    # Centralizados aqui para que el resto del sistema use nombres,
    # nunca numeros magicos.
    LANDMARK_INDEX: dict[str, int] = {
        "nose":              0,
        "left_eye":          2,
        "right_eye":         5,
        "left_shoulder":    11,
        "right_shoulder":   12,
        "left_elbow":       13,
        "right_elbow":      14,
        "left_wrist":       15,
        "right_wrist":      16,
        "left_hip":         23,
        "right_hip":        24,
        "left_knee":        25,
        "right_knee":       26,
        "left_ankle":       27,
        "right_ankle":      28,
        "left_heel":        29,
        "right_heel":       30,
        "left_foot_index":  31,
        "right_foot_index": 32,
    }

    # Ruta por defecto al modelo dentro del proyecto
    DEFAULT_MODEL_PATH: str = os.path.join(
        os.path.dirname(__file__),
        "models",
        "pose_landmarker_heavy.task",
    )

    def __init__(
        self,
        model_path: Optional[str] = None,
        min_pose_detection_confidence: float = 0.65,
        min_pose_presence_confidence: float = 0.65,
        min_tracking_confidence: float = 0.65,
    ) -> None:
        """
        Inicializa el modelo PoseLandmarker de MediaPipe.

        Args:
            model_path: ruta al archivo .task del modelo.
                        Si es None usa DEFAULT_MODEL_PATH.
            min_pose_detection_confidence: confianza minima para
                        deteccion inicial de pose.
            min_pose_presence_confidence: confianza minima para
                        considerar que la pose esta presente en el frame.
            min_tracking_confidence: confianza minima para tracking
                        entre frames consecutivos.
        """
        resolved_path = model_path or self.DEFAULT_MODEL_PATH
        self._validate_model_path(resolved_path)

        base_options = mp.tasks.BaseOptions(model_asset_path=resolved_path)

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=min_pose_detection_confidence,
            min_pose_presence_confidence=min_pose_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
            num_poses=1,
            output_segmentation_masks=False,
        )

        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    def estimate(self, frame: np.ndarray) -> Optional[PoseLandmarks]:
        """
        Detecta los landmarks de pose en un frame de video.

        El frame debe estar en formato BGR (formato nativo de OpenCV).
        La conversion a RGB se realiza internamente antes de pasarlo
        a MediaPipe para que el resto del sistema no necesite saberlo.

        Args:
            frame: imagen en formato BGR como numpy array (H, W, 3).

        Returns:
            PoseLandmarks con los 33 puntos detectados,
            o None si MediaPipe no detecto un cuerpo en el frame.
        """
        mp_image = self._to_mediapipe_image(frame)
        result = self._landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return None

        return self._parse_landmarks(result.pose_landmarks[0])

    def release(self) -> None:
        """
        Libera los recursos del modelo.
        Debe llamarse cuando la sesion termina para evitar memory leaks.
        """
        self._landmarker.close()

    def _validate_model_path(self, path: str) -> None:
        """
        Verifica que el archivo de modelo existe antes de intentar cargarlo.
        Falla rapido con un mensaje claro en lugar de un error críptico
        de MediaPipe.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"Modelo de MediaPipe no encontrado en: {path}\n"
                f"Descargalo con:\n"
                f"  python -c \"import urllib.request; "
                f"urllib.request.urlretrieve("
                f"'https://storage.googleapis.com/mediapipe-models/"
                f"pose_landmarker/pose_landmarker_heavy/float16/latest/"
                f"pose_landmarker_heavy.task', '{path}')\""
            )

    def _to_mediapipe_image(self, frame: np.ndarray) -> mp.Image:
        """
        Convierte un frame BGR de OpenCV a mp.Image en formato RGB.
        MediaPipe requiere RGB. OpenCV entrega BGR.
        La inversion de canales es la conversion mas eficiente disponible.
        """
        rgb_frame = frame[:, :, ::-1].copy()
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    def _parse_landmarks(
        self,
        raw_landmarks: list[NormalizedLandmark],
    ) -> PoseLandmarks:
        """
        Convierte los landmarks de MediaPipe al tipo propio del sistema.
        Desacopla el resto del sistema de la estructura interna de MediaPipe.
        """
        parsed = tuple(
            Landmark(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility if lm.visibility is not None else 0.0,
                presence=lm.presence if lm.presence is not None else 0.0,
            )
            for lm in raw_landmarks
        )
        return PoseLandmarks(landmarks=parsed)