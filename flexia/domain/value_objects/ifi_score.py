from dataclasses import dataclass

@dataclass(frozen=True)
class IfiScore:
    value: float  # 0.0 a 100.0

    def __post_init__(self):
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(f"IFI score debe estar entre 0 y 100. Recibido: {self.value}")

    @property
    def label(self) -> str:
        if self.value >= 85:
            return "green"
        elif self.value >= 60:
            return "yellow"
        return "red"
