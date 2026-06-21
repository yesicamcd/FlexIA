from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from domain.models.video import Video

class IVideoRepository(ABC):
    @abstractmethod
    def get_by_session(self, session_id: UUID) -> Optional[Video]: ...

    @abstractmethod
    def save(self, video: Video) -> Video: ...

    @abstractmethod
    def update_status(self, video_id: UUID, status: str, error: str = None) -> None: ...
