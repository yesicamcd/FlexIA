"""Clasificacion verde / amarillo / rojo segun umbrales."""
from domain.value_objects.performance_label import PerformanceLabel
from shared.constants import GREEN_THRESHOLD, YELLOW_THRESHOLD

def evaluate(rom_percentage: float) -> PerformanceLabel:
    if rom_percentage >= GREEN_THRESHOLD * 100:
        return PerformanceLabel.GREEN
    elif rom_percentage >= YELLOW_THRESHOLD * 100:
        return PerformanceLabel.YELLOW
    return PerformanceLabel.RED
