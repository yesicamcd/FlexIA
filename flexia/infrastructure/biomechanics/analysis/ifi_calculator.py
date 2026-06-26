"""
infrastructure/biomechanics/analysis/ifi_calculator.py

Calcula el Indice Funcional Integrado (IFI) de una sesion completa.
El IFI es un indicador ponderado que sintetiza el desempeno del
paciente en todos los ejercicios de la sesion en un valor entre 0 y 100.

El calculo se realiza una sola vez al finalizar la sesion,
no frame a frame.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.ifi_score import IfiScore


@dataclass(frozen=True)
class ExerciseIfiInput:
    """
    Datos de un ejercicio necesarios para el calculo del IFI.

    Agrupa el desempeno del ejercicio y su peso clinico relativo.
    Una instancia por ejercicio completado en la sesion.

    Atributos:
        exercise_id: identificador del ejercicio (UUID como string).
        exercise_name: nombre del ejercicio para logs y reportes.
        rom_percentage: porcentaje del ROM alcanzado (0 a 100+).
                        Viene de RomMeasurement.percentage.
        rep_completion_ratio: proporcion de repeticiones validas
                              sobre las esperadas (0.0 a 1.0+).
                              Viene de RepCounter.completion_ratio.
        weight: peso clinico relativo del ejercicio en la sesion.
                Cargado desde routine_exercises.ifi_contribution en Supabase.
                Si todos los ejercicios tienen peso 1.0, el IFI es
                el promedio simple del desempeno.
    """

    exercise_id: str
    exercise_name: str
    rom_percentage: float
    rep_completion_ratio: float
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                f"El peso del ejercicio debe ser mayor que cero. "
                f"Ejercicio: '{self.exercise_name}', weight: {self.weight}"
            )
        if self.rom_percentage < 0:
            raise ValueError(
                f"rom_percentage no puede ser negativo. "
                f"Ejercicio: '{self.exercise_name}', valor: {self.rom_percentage}"
            )
        if self.rep_completion_ratio < 0:
            raise ValueError(
                f"rep_completion_ratio no puede ser negativo. "
                f"Ejercicio: '{self.exercise_name}', valor: {self.rep_completion_ratio}"
            )

    @property
    def performance_score(self) -> float:
        """
        Puntaje de desempeno combinado para este ejercicio.

        Combina el ROM alcanzado y el cumplimiento de repeticiones
        con igual peso entre ambos componentes.

        El resultado se limita a 100 para evitar que superar el
        objetivo infle artificialmente el IFI mas alla de ese techo.

        Formula:
            score = (rom_percentage * 0.6 + rep_ratio_pct * 0.4)
            score = min(score, 100.0)

        La ponderacion 60/40 entre ROM y repeticiones refleja
        que la calidad del movimiento (ROM) tiene mayor peso clinico
        que la cantidad (repeticiones).
        """
        rom_component = self.rom_percentage * 0.6
        rep_component = min(self.rep_completion_ratio * 100, 100.0) * 0.4
        return min(rom_component + rep_component, 100.0)


@dataclass(frozen=True)
class IfiCalculationDetail:
    """
    Detalle del calculo del IFI por ejercicio.
    Util para transparencia clinica y auditoria del resultado.

    Atributos:
        exercise_name: nombre del ejercicio.
        performance_score: puntaje combinado ROM + repeticiones (0-100).
        weight: peso clinico asignado al ejercicio.
        weighted_contribution: aporte ponderado de este ejercicio al IFI total.
    """

    exercise_name: str
    performance_score: float
    weight: float
    weighted_contribution: float


@dataclass(frozen=True)
class IfiResult:
    """
    Resultado completo del calculo del IFI.

    Combina el score final con el detalle por ejercicio para
    que el reporte clinico pueda mostrar el desglose completo.

    Atributos:
        score: IfiScore con el valor final entre 0 y 100.
        details: detalle del aporte de cada ejercicio al IFI.
        total_weight: suma de pesos de todos los ejercicios.
                      Util para verificar la consistencia del calculo.
    """

    score: IfiScore
    details: tuple[IfiCalculationDetail, ...]
    total_weight: float

    def summary(self) -> str:
        """
        Genera un resumen textual del calculo para logs y reportes.
        """
        lines = [f"IFI final: {self.score.value:.2f} / 100 ({self.score.label})"]
        lines.append(f"Peso total: {self.total_weight:.2f}")
        lines.append("Detalle por ejercicio:")
        for detail in self.details:
            lines.append(
                f"  {detail.exercise_name}: "
                f"score={detail.performance_score:.1f} "
                f"peso={detail.weight:.2f} "
                f"aporte={detail.weighted_contribution:.2f}"
            )
        return "\n".join(lines)


class IfiCalculator:
    """
    Calcula el Indice Funcional Integrado de una sesion completa.

    El IFI es una media ponderada del desempeno en cada ejercicio,
    donde el peso de cada ejercicio esta definido clinicamente
    por el kinesiologo en la rutina de Supabase.

    Uso:
        calculator = IfiCalculator()
        result = calculator.calculate(exercise_inputs)
        print(result.score)
        print(result.summary())
    """

    def calculate(self, inputs: list[ExerciseIfiInput]) -> IfiResult:
        """
        Calcula el IFI ponderado para una sesion.

        Args:
            inputs: lista de ExerciseIfiInput, uno por ejercicio
                    completado en la sesion. El orden no afecta
                    el resultado.

        Returns:
            IfiResult con el score final y el detalle por ejercicio.

        Raises:
            ValueError: si la lista de inputs esta vacia.
        """
        if not inputs:
            raise ValueError(
                "No se puede calcular el IFI sin ejercicios. "
                "La lista de inputs esta vacia."
            )

        details = self._build_details(inputs)
        total_weight = sum(d.weight for d in details)
        weighted_sum = sum(d.weighted_contribution for d in details)

        raw_ifi = weighted_sum / total_weight
        clamped_ifi = max(0.0, min(raw_ifi, 100.0))

        return IfiResult(
            score=IfiScore.from_percentage(clamped_ifi),
            details=tuple(details),
            total_weight=round(total_weight, 4),
        )

    def _build_details(
        self,
        inputs: list[ExerciseIfiInput],
    ) -> list[IfiCalculationDetail]:
        """
        Construye el detalle de calculo por ejercicio.
        Calcula el aporte ponderado de cada uno al IFI total.
        """
        return [
            IfiCalculationDetail(
                exercise_name=inp.exercise_name,
                performance_score=round(inp.performance_score, 2),
                weight=inp.weight,
                weighted_contribution=round(inp.performance_score * inp.weight, 4),
            )
            for inp in inputs
        ]