"""Caso de uso: login de usuario."""
from domain.interfaces.services.i_auth_service import IAuthService

class LoginUseCase:
    def __init__(self, auth_service: IAuthService):
        self._auth = auth_service

    def execute(self, email: str, password: str) -> dict:
        return self._auth.login(email, password)
