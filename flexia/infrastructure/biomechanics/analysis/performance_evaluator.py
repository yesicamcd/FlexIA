"""
infrastructure/biomechanics/analysis/performance_evaluator.py

Clasifica el desempeno biomecanico de un ejercicio como verde,
amarillo o rojo segun el ROM alcanzado y los umbrales clinicos
definidos para cada ejercicio en Supabase.

Los umbrales se reciben como parametros — nunca se definen aqui.
Este modulo solo contiene la logica de clasificacion.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.performance_label import PerformanceLabel
from domain.value_objects.rom_measurement import RomMeasurement


@dataclass(frozen=True)
class PerformanceResult:
    """
    Resultado de la evaluacion de desempeno para un frame o ejercicio.

    Atributos:
        label: clasificacion verde, amarillo o rojo.
        rom: medicion de ROM sobre la que se basa la clasificacion.
        green_threshold: umbral usado para verde (proporcion, ej: 0.85).
        yellow_threshold: umbral usado para amarillo (proporcion, ej: 0.60).
        message: descripcion textual del resultado para logs y reportes.
                 No se muestra durante la ejecucion del ejercicio,
                 solo en el reporte posterior.
    """

    label: PerformanceLabel
    rom: RomMeasurement
    green_threshold: float
    yellow_threshold: float
    message: str

    @property
    def is_green(self) -> bool:
        return self.label == PerformanceLabel.GREEN

    @property
    def is_yellow(self) -> bool:
        return self.label == PerformanceLabel.YELLOW

    @property
    def is_red(self) -> bool:
        return self.label == PerformanceLabel.RED

    @property
    def requires_alert(self) -> bool:
        """
        Indica si este resultado debe disparar una alerta sonora.
        Solo amarillo y rojo generan alerta.
        """
        return self.label in (PerformanceLabel.YELLOW, PerformanceLabel.RED)


class PerformanceEvaluator:
    """
    Clasifica el desempeno biomecanico de un ejercicio.

    Los umbrales se pasan en cada llamada a evaluate() porque
    provienen del ejercicio cargado desde Supabase y pueden
    ser distintos para cada ejercicio de la sesion.

    Uso:
        evaluator = PerformanceEvaluator()
        result = evaluator.evaluate(
            rom=rom_measurement,
            green_threshold=0.85,
            yellow_threshold=0.60,
        )
        if result.requires_alert:
            audio_alert.emit(result.label)
    """

    def evaluate(
        self,
        rom: RomMeasurement,
        green_threshold: float,
        yellow_threshold: float,
    ) -> PerformanceResult:
        """
        Clasifica el desempeno basandose en el porcentaje del ROM alcanzado.

        Args:
            rom: medicion de ROM del frame o ejercicio actual.
            green_threshold: proporcion minima para clasificar como verde.
                             Cargado desde exercises.green_threshold en Supabase.
            yellow_threshold: proporcion minima para clasificar como amarillo.
                              Cargado desde exercises.yellow_threshold en Supabase.

        Returns:
            PerformanceResult con el label y el mensaje correspondiente.

        Raises:
            ValueError: si los umbrales son invalidos o incoherentes.
        """
        self._validate_thresholds(green_threshold, yellow_threshold)

        label = self._classify(rom.percentage, green_threshold, yellow_threshold)
        message = self._build_message(rom, label)

        return PerformanceResult(
            label=label,
            rom=rom,
            green_threshold=green_threshold,
            yellow_threshold=yellow_threshold,
            message=message,
        )

    def evaluate_session(
        self,
        roms: list[RomMeasurement],
        green_threshold: float,
        yellow_threshold: float,
    ) -> PerformanceResult:
        """
        Clasifica el desempeno global de un ejercicio completo
        promediando los ROM de todas las repeticiones.

        Usado al finalizar el ejercicio para generar el resultado
        que se guarda en exercise_results de Supabase.

        Args:
            roms: lista de RomMeasurement, uno por repeticion valida.
            green_threshold: umbral para verde del ejercicio.
            yellow_threshold: umbral para amarillo del ejercicio.

        Returns:
            PerformanceResult representando el desempeno global
            del ejercicio en la sesion.

        Raises:
            ValueError: si la lista de roms esta vacia.
        """
        if not roms:
            raise ValueError(
                "No se pueden evaluar resultados de sesion sin "
                "mediciones de ROM. La lista esta vacia."
            )

        avg_percentage = sum(r.percentage for r in roms) / len(roms)
        avg_achieved = sum(r.achieved_degrees for r in roms) / len(roms)

        representative_rom = RomMeasurement(
            achieved_degrees=round(avg_achieved, 2),
            expected_degrees=roms[0].expected_degrees,
            joint_name=roms[0].joint_name,
            side=roms[0].side,
        )

        label = self._classify(avg_percentage, green_threshold, yellow_threshold)
        message = self._build_session_message(representative_rom, label, len(roms))

        return PerformanceResult(
            label=label,
            rom=representative_rom,
            green_threshold=green_threshold,
            yellow_threshold=yellow_threshold,
            message=message,
        )

    def _validate_thresholds(
        self,
        green_threshold: float,
        yellow_threshold: float,
    ) -> None:
        """
        Verifica que los umbrales son valores validos y coherentes.
        El umbral verde debe ser mayor que el amarillo.
        """
        if not (0.0 < yellow_threshold < green_threshold <= 1.0):
            raise ValueError(
                f"Umbrales invalidos. Se requiere: "
                f"0 < yellow_threshold ({yellow_threshold}) "
                f"< green_threshold ({green_threshold}) <= 1.0"
            )

    def _classify(
        self,
        percentage: float,
        green_threshold: float,
        yellow_threshold: float,
    ) -> PerformanceLabel:
        """
        Aplica la logica de clasificacion sobre el porcentaje del ROM.
        El porcentaje viene expresado entre 0 y 100.
        Los umbrales vienen como proporcion entre 0 y 1.
        """
        ratio = percentage / 100.0

        if ratio >= green_threshold:
            return PerformanceLabel.GREEN
        if ratio >= yellow_threshold:
            return PerformanceLabel.YELLOW
        return PerformanceLabel.RED

    def _build_message(
        self,
        rom: RomMeasurement,
        label: PerformanceLabel,
    ) -> str:
        """
        Construye el mensaje descriptivo para logs y reportes.
        No se muestra en pantalla durante la ejecucion.
        """
        return (
            f"{rom.joint_name} ({rom.side}): "
            f"{rom.achieved_degrees:.1f} / {rom.expected_degrees:.1f} grados "
            f"({rom.percentage:.1f}%) -> {label.value}"
        )

    def _build_session_message(
        self,
        rom: RomMeasurement,
        label: PerformanceLabel,
        rep_count: int,
    ) -> str:
        """
        Construye el mensaje para el resultado global del ejercicio.
        """
        return (
            f"{rom.joint_name} ({rom.side}): "
            f"promedio {rom.achieved_degrees:.1f} / {rom.expected_degrees:.1f} grados "
            f"({rom.percentage:.1f}%) en {rep_count} repeticiones -> {label.value}"
        )