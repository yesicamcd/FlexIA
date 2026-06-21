from abc import ABC, abstractmethod
from domain.models.user import User

class IAuthService(ABC):
    @abstractmethod
    def login(self, email: str, password: str) -> dict: ...

    @abstractmethod
    def get_current_user(self, token: str) -> User: ...

    @abstractmethod
    def logout(self) -> None: ...
