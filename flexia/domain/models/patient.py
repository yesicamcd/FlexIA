from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from typing import Optional

@dataclass
class Patient:
    id: UUID
    center_id: UUID
    created_by: UUID
    full_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    diagnosis: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
