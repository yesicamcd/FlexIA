"""
infrastructure/biomechanics/analysis/rom_calculator.py

Calcula el rango de movimiento (ROM) articular a partir de landmarks
de pose. Usa algebra vectorial para maxima estabilidad numerica.

Referencia angular: posicion anatomica = 0 grados.
Los angulos representan desviacion desde la postura neutra,
no el angulo absoluto entre segmentos corporales.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from domain.value_objects.rom_measurement import RomMeasurement
from infrastructure.biomechanics.analysis.pose_estimator import (
    Landmark,
    PoseLandmarks,
    PoseEstimator,
)


@dataclass(frozen=True)
class JointConfig:
    """
    Configuracion de una articulacion para el calculo de ROM.

    Define los tres landmarks que forman el angulo articular
    y el offset anatomico necesario para que la posicion
    anatomica corresponda a 0 grados.

    Atributos:
        proximal_index: landmark del segmento proximal (ej: cadera para rodilla).
        joint_index: landmark de la articulacion que se mide (ej: rodilla).
        distal_index: landmark del segmento distal (ej: tobillo para rodilla).
        anatomical_offset_degrees: angulo que la posicion anatomica forma
                                   naturalmente entre los tres puntos.
                                   Se resta al resultado para que el cero
                                   corresponda a la postura neutra.
    """

    proximal_index: int
    joint_index: int
    distal_index: int
    anatomical_offset_degrees: float = 0.0


class RomCalculator:
    """
    Calcula el ROM articular desde landmarks de pose.

    Configuraciones predefinidas para las articulaciones mas comunes
    en rehabilitacion musculoesqueletica. Nuevas articulaciones se
    agregan definiendo un JointConfig sin modificar el codigo existente.

    Uso:
        calculator = RomCalculator()
        rom = calculator.calculate(
            landmarks=pose_landmarks,
            joint_name="knee",
            side="left",
            expected_degrees=120.0,
        )
    """

    # Configuraciones de articulaciones por nombre.
    # Cada articulacion define sus tres puntos de referencia
    # y su offset anatomico.
    # Para agregar una articulacion nueva: agregar una entrada aca.
    # No modificar el metodo calculate()!!!!
    JOINT_CONFIGS: dict[str, dict[str, JointConfig]] = {
        "knee": {
            "left": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["left_hip"],
                joint_index=PoseEstimator.LANDMARK_INDEX["left_knee"],
                distal_index=PoseEstimator.LANDMARK_INDEX["left_ankle"],
                anatomical_offset_degrees=180.0,
            ),
            "right": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["right_hip"],
                joint_index=PoseEstimator.LANDMARK_INDEX["right_knee"],
                distal_index=PoseEstimator.LANDMARK_INDEX["right_ankle"],
                anatomical_offset_degrees=180.0,
            ),
        },
        "hip_flexion": {
            "left": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["left_shoulder"],
                joint_index=PoseEstimator.LANDMARK_INDEX["left_hip"],
                distal_index=PoseEstimator.LANDMARK_INDEX["left_knee"],
                anatomical_offset_degrees=180.0,
            ),
            "right": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["right_shoulder"],
                joint_index=PoseEstimator.LANDMARK_INDEX["right_hip"],
                distal_index=PoseEstimator.LANDMARK_INDEX["right_knee"],
                anatomical_offset_degrees=180.0,
            ),
        },
        "shoulder_flexion": {
            "left": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["left_hip"],
                joint_index=PoseEstimator.LANDMARK_INDEX["left_shoulder"],
                distal_index=PoseEstimator.LANDMARK_INDEX["left_elbow"],
                anatomical_offset_degrees=180.0,
            ),
            "right": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["right_hip"],
                joint_index=PoseEstimator.LANDMARK_INDEX["right_shoulder"],
                distal_index=PoseEstimator.LANDMARK_INDEX["right_elbow"],
                anatomical_offset_degrees=180.0,
            ),
        },
        "elbow_flexion": {
            "left": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["left_shoulder"],
                joint_index=PoseEstimator.LANDMARK_INDEX["left_elbow"],
                distal_index=PoseEstimator.LANDMARK_INDEX["left_wrist"],
                anatomical_offset_degrees=180.0,
            ),
            "right": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["right_shoulder"],
                joint_index=PoseEstimator.LANDMARK_INDEX["right_elbow"],
                distal_index=PoseEstimator.LANDMARK_INDEX["right_wrist"],
                anatomical_offset_degrees=180.0,
            ),
        },
        "ankle_dorsiflexion": {
            "left": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["left_knee"],
                joint_index=PoseEstimator.LANDMARK_INDEX["left_ankle"],
                distal_index=PoseEstimator.LANDMARK_INDEX["left_foot_index"],
                anatomical_offset_degrees=90.0,
            ),
            "right": JointConfig(
                proximal_index=PoseEstimator.LANDMARK_INDEX["right_knee"],
                joint_index=PoseEstimator.LANDMARK_INDEX["right_ankle"],
                distal_index=PoseEstimator.LANDMARK_INDEX["right_foot_index"],
                anatomical_offset_degrees=90.0,
            ),
        },
    }

    def calculate(
        self,
        landmarks: PoseLandmarks,
        joint_name: str,
        side: str,
        expected_degrees: float,
        min_visibility: float = 0.5,
    ) -> Optional[RomMeasurement]:
        """
        Calcula el ROM para una articulacion en un frame dado.

        Devuelve None si alguno de los landmarks necesarios no tiene
        suficiente visibilidad para un calculo confiable. Esto es
        preferible a devolver un valor incorrecto que afecte la
        evaluacion clinica.

        Args:
            landmarks: landmarks detectados en el frame actual.
            joint_name: nombre de la articulacion (ej: 'knee', 'hip_flexion').
            side: lado a evaluar ('left', 'right', 'bilateral').
            expected_degrees: rango funcional esperado para este ejercicio,
                              cargado desde la base de datos.
            min_visibility: visibilidad minima requerida en los landmarks.

        Returns:
            RomMeasurement con el angulo calculado,
            o None si la visibilidad es insuficiente.

        Raises:
            ValueError: si joint_name o side no estan configurados.
        """
        config = self._get_config(joint_name, side)

        if not self._landmarks_are_visible(landmarks, config, min_visibility):
            return None

        achieved = self._calculate_angle(landmarks, config)

        return RomMeasurement(
            achieved_degrees=achieved,
            expected_degrees=expected_degrees,
            joint_name=joint_name,
            side=side,
        )

    def calculate_bilateral(
        self,
        landmarks: PoseLandmarks,
        joint_name: str,
        expected_degrees: float,
        min_visibility: float = 0.5,
    ) -> Optional[RomMeasurement]:
        """
        Calcula el ROM bilateral promediando ambos lados.
        Usado cuando el ejercicio es simetrico y se evaluan
        los dos lados simultaneamente.

        Devuelve None si ninguno de los dos lados tiene visibilidad
        suficiente.
        """
        left = self.calculate(
            landmarks, joint_name, "left", expected_degrees, min_visibility
        )
        right = self.calculate(
            landmarks, joint_name, "right", expected_degrees, min_visibility
        )

        if left is None and right is None:
            return None

        available = [r for r in (left, right) if r is not None]
        avg_achieved = sum(r.achieved_degrees for r in available) / len(available)

        return RomMeasurement(
            achieved_degrees=round(avg_achieved, 2),
            expected_degrees=expected_degrees,
            joint_name=joint_name,
            side="bilateral",
        )

    def _get_config(self, joint_name: str, side: str) -> JointConfig:
        """
        Obtiene la configuracion de la articulacion solicitada.

        Raises:
            ValueError: si la articulacion o el lado no estan configurados.
        """
        if joint_name not in self.JOINT_CONFIGS:
            available = list(self.JOINT_CONFIGS.keys())
            raise ValueError(
                f"Articulacion '{joint_name}' no configurada. "
                f"Disponibles: {available}"
            )

        side_key = "left" if side == "bilateral" else side

        if side_key not in self.JOINT_CONFIGS[joint_name]:
            raise ValueError(
                f"Lado '{side}' no configurado para '{joint_name}'."
            )

        return self.JOINT_CONFIGS[joint_name][side_key]

    def _landmarks_are_visible(
        self,
        landmarks: PoseLandmarks,
        config: JointConfig,
        min_visibility: float,
    ) -> bool:
        """
        Verifica que los tres landmarks necesarios para el calculo
        tienen visibilidad suficiente.
        """
        indices = (
            config.proximal_index,
            config.joint_index,
            config.distal_index,
        )
        return all(landmarks.is_visible(i, min_visibility) for i in indices)

    def _calculate_angle(
        self,
        landmarks: PoseLandmarks,
        config: JointConfig,
    ) -> float:
        """
        Calcula el angulo articular usando algebra vectorial.

        El angulo se forma entre el vector proximal->joint
        y el vector distal->joint, medido en el punto de la articulacion.

        Se usa np.arctan2 en lugar de np.arccos porque:
        - arccos es inestable en los extremos del dominio (-1, 1)
        - arctan2 maneja correctamente todos los cuadrantes
        - arctan2 nunca falla por valores fuera de dominio

        El resultado se ajusta restando el offset anatomico para
        que la posicion anatomica corresponda a 0 grados.
        """
        proximal = self._to_array(landmarks.get(config.proximal_index))
        joint = self._to_array(landmarks.get(config.joint_index))
        distal = self._to_array(landmarks.get(config.distal_index))

        vector_a = proximal - joint
        vector_b = distal - joint

        angle_radians = np.arctan2(
            np.cross(vector_a, vector_b),
            np.dot(vector_a, vector_b),
        )

        angle_degrees = abs(np.degrees(angle_radians))
        adjusted = abs(angle_degrees - config.anatomical_offset_degrees)

        return round(float(adjusted), 2)

    def _to_array(self, landmark: Landmark) -> np.ndarray:
        """
        Convierte un Landmark a un array 2D de numpy para calculo vectorial.
        Usa solo x e y porque las coordenadas z de MediaPipe en modo imagen
        son menos confiables que x e y para calculos angulares en 2D.
        """
        return np.array([landmark.x, landmark.y])