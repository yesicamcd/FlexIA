"""
domain/models/exercise_result.py

Resultado biomecanico de un ejercicio dentro de una sesion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class ExerciseResult:
    id: UUID
    session_id: str
    routine_exercise_id: str    # FK a routine_exercises.id
    order_index: int
    rom_achieved: Optional[float]
    rom_expected: Optional[float]
    rom_percentage: Optional[float]
    reps_achieved: Optional[int]
    reps_expected: Optional[int]
    performance: Optional[str]       # green | yellow | red
    ifi_contribution: Optional[float]
    landmarks_json: Optional[dict]
    frame_count: Optional[int]
    created_at: datetime