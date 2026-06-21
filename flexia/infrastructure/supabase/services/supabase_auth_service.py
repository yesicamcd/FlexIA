"""Implementacion del servicio de autenticacion con Supabase Auth."""
from supabase import Client
from domain.interfaces.services.i_auth_service import IAuthService
from domain.models.user import User

class SupabaseAuthService(IAuthService):
    def __init__(self, client: Client):
        self._client = client

    def login(self, email: str, password: str) -> dict:
        response = self._client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response

    def get_current_user(self, token: str) -> User:
        # TODO: implementar
        raise NotImplementedError

    def logout(self) -> None:
        self._client.auth.sign_out()
