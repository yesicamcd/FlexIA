"""
infrastructure/biomechanics/analysis/extensions/postural_analyzer.py

Analiza metricas posturales opcionales durante la ejecucion del ejercicio.

Activable y desactivable por el kinesiologo antes de iniciar la sesion.
Cuando esta desactivado, no tiene ningun impacto en el rendimiento
ni en el calculo del IFI.

Metricas disponibles (V2):
    - Alineacion de columna vertebral (desviacion lateral)
    - Simetria de hombros (diferencia de altura entre lados)
    - Inclinacion pelvica (anterior, posterior, lateral)
    - Posicion de la cabeza (protraccion, inclinacion)
    - Alineacion rodilla-pie durante ejercicios de carga

Estado actual: placeholder.
Implementacion completa: V2.

Uso clinico esperado:
    El kinesiologo activa las metricas relevantes para el diagnostico
    del paciente. Por ejemplo, en un paciente con escoliosis se activa
    la alineacion de columna. En un paciente con sindrome de rodilla
    del corredor se activa la alineacion rodilla-pie.

Impacto en IFI:
    Las metricas posturales NO modifican el IFI principal.
    Generan un indice postural separado que el kinesiologo
    interpreta de forma complementaria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from infrastructure.biomechanics.analysis.pose_estimator import PoseLandmarks


@dataclass(frozen=True)
class PosturalMetrics:
    """
    Metricas posturales calculadas para un frame.

    Todos los valores son opcionales — solo se calculan las
    metricas que el kinesiologo activo para la sesion.

    Atributos:
        spinal_deviation_degrees: desviacion lateral de la columna
                                  respecto a la vertical. 0 = neutro.
        shoulder_asymmetry_ratio: diferencia de altura entre hombros
                                  como proporcion del ancho de hombros.
                                  0 = simetrico.
        pelvic_tilt_degrees: inclinacion pelvica en grados.
                             Positivo = anterior, negativo = posterior.
        head_protrusion_ratio: protraccion de cabeza respecto al tronco.
                               0 = alineado, positivo = adelantado.
        knee_foot_alignment_degrees: alineacion rodilla sobre pie
                                     en ejercicios de carga.
    """

    spinal_deviation_degrees: Optional[float] = None
    shoulder_asymmetry_ratio: Optional[float] = None
    pelvic_tilt_degrees: Optional[float] = None
    head_protrusion_ratio: Optional[float] = None
    knee_foot_alignment_degrees: Optional[float] = None


@dataclass
class PosturalConfig:
    """
    Configuracion de metricas posturales para una sesion.
    Definida por el kinesiologo antes de iniciar la sesion.

    Atributos:
        analyze_spine: activar analisis de columna vertebral.
        analyze_shoulders: activar analisis de simetria de hombros.
        analyze_pelvis: activar analisis de inclinacion pelvica.
        analyze_head: activar analisis de posicion de cabeza.
        analyze_knee_foot: activar analisis de alineacion rodilla-pie.
    """

    analyze_spine: bool = False
    analyze_shoulders: bool = False
    analyze_pelvis: bool = False
    analyze_head: bool = False
    analyze_knee_foot: bool = False

    @property
    def any_active(self) -> bool:
        """Indica si al menos una metrica esta activa."""
        return any([
            self.analyze_spine,
            self.analyze_shoulders,
            self.analyze_pelvis,
            self.analyze_head,
            self.analyze_knee_foot,
        ])


class PosturalAnalyzer:
    """
    Analiza metricas posturales opcionales frame a frame.

    Solo ejecuta el analisis si la configuracion tiene
    al menos una metrica activa. Si ninguna esta activa,
    el metodo analyze() devuelve None sin procesamiento.

    Uso futuro:
        config = PosturalConfig(analyze_spine=True, analyze_shoulders=True)
        analyzer = PosturalAnalyzer(config)
        metrics = analyzer.analyze(landmarks)
        if metrics is not None:
            print(metrics.spinal_deviation_degrees)
    """

    def __init__(self, config: PosturalConfig) -> None:
        self._config = config

    @property
    def is_active(self) -> bool:
        """Indica si el analizador tiene metricas activas."""
        return self._config.any_active

    def analyze(
        self,
        landmarks: PoseLandmarks,
    ) -> Optional[PosturalMetrics]:
        """
        Analiza las metricas posturales activas en el frame actual.

        Si ninguna metrica esta activa devuelve None inmediatamente
        sin consumir recursos de procesamiento.

        Args:
            landmarks: landmarks detectados en el frame actual.

        Returns:
            PosturalMetrics con los valores calculados para las
            metricas activas, o None si ninguna esta activa.

        Raises:
            NotImplementedError: hasta la implementacion en V2.
        """
        if not self._config.any_active:
            return None

        raise NotImplementedError(
            "PosturalAnalyzer.analyze() sera implementado en V2. "
            "El punto de extension esta disponible para integracion futura."
        )