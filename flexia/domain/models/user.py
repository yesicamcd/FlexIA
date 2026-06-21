from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class User:
    id: UUID
    center_id: UUID
    full_name: str
    role: str          # admin | professional | viewer
    is_active: bool
    created_at: datetime
