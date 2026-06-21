from abc import ABC, abstractmethod

class IStorageService(ABC):
    @abstractmethod
    def upload_video(self, file_bytes: bytes, path: str) -> str: ...
    # Devuelve la storage_path

    @abstractmethod
    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str: ...
