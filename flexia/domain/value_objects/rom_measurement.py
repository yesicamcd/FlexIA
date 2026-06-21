from dataclasses import dataclass

@dataclass(frozen=True)
class RomMeasurement:
    achieved_degrees: float
    expected_degrees: float

    @property
    def percentage(self) -> float:
        if self.expected_degrees <= 0:
            return 0.0
        return round((self.achieved_degrees / self.expected_degrees) * 100, 2)
