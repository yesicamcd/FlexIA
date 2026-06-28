"""
infrastructure/biomechanics/analysis/extensions/gravity_center.py

Calcula el centro de gravedad aproximado del cuerpo a partir
de landmarks de pose.

Util para:
    - Analisis de equilibrio durante ejercicios unipodales
    - Deteccion de compensaciones posturales (desplazamiento lateral)
    - Evaluacion de la estabilidad del tronco durante el movimiento
    - Analisis de la base de sustentacion

Estado actual: placeholder.
Implementacion completa: V2.

Punto de extension para analisis de:
    - Desplazamiento del centro de masa durante el movimiento
    - Simetria de carga entre miembro inferior derecho e izquierdo
    - Oscilacion postural en ejercicios de equilibrio
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from infrastructure.biomechanics.analysis.pose_estimator import PoseLandmarks


@dataclass(frozen=True)
class GravityCenterPoint:
    """
    Posicion estimada del centro de gravedad en el frame.

    Atributos:
        x: posicion horizontal normalizada (0.0 = izquierda, 1.0 = derecha).
        y: posicion vertical normalizada (0.0 = arriba, 1.0 = abajo).
        confidence: confianza del calculo basada en la visibilidad
                    de los landmarks usados (0.0 a 1.0).
        lateral_deviation: desviacion lateral respecto a la linea
                           media del cuerpo en valor normalizado.
                           Positivo = desviacion a la derecha.
    """

    x: float
    y: float
    confidence: float
    lateral_deviation: float


class GravityCenterAnalyzer:
    """
    Calcula el centro de gravedad aproximado del cuerpo.

    Usa un modelo simplificado basado en los segmentos corporales
    principales visibles en los landmarks de MediaPipe.

    Uso futuro:
        analyzer = GravityCenterAnalyzer()
        point = analyzer.calculate(landmarks)
        if point is not None:
            print(point.lateral_deviation)
    """

    def calculate(
        self,
        landmarks: PoseLandmarks,
    ) -> Optional[GravityCenterPoint]:
        """
        Calcula el centro de gravedad desde los landmarks del frame actual.

        Args:
            landmarks: landmarks detectados en el frame.

        Returns:
            GravityCenterPoint con la posicion estimada,
            o None si los landmarks necesarios no tienen visibilidad
            suficiente.

        Raises:
            NotImplementedError: hasta la implementacion en V2.
        """
        raise NotImplementedError(
            "GravityCenterAnalyzer.calculate() sera implementado en V2. "
            "El punto de extension esta disponible para integracion futura."
        )