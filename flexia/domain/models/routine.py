from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Routine:
    id: UUID
    center_id: UUID
    created_by: UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
