from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class Video:
    id: UUID
    session_id: UUID
    storage_path: str
    storage_url: Optional[str]
    duration_secs: Optional[float]
    fps: Optional[float]
    resolution: Optional[str]
    status: str           # uploading | uploaded | analyzing | analyzed | error
    error_message: Optional[str]
    created_at: datetime
