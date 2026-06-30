"""
app/use_cases/auth/register_professional_use_case.py

Caso de uso: registrar un profesional nuevo.
Crea el usuario en Supabase Auth y su perfil en public.users
usando el MISMO UUID generado por Auth, evitando desajustes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class RegisterProfessionalRequest:
    email: str
    password: str
    full_name: str
    center_id: str
    role: str = "professional"


@dataclass
class RegisteredProfessional:
    user_id: str
    email: str
    full_name: str


class RegisterProfessionalUseCase:
    """
    Registra un profesional creando primero el usuario de Auth
    y luego su perfil en public.users con el mismo UUID.

    Uso desde Streamlit (pantalla de alta de usuario):
        use_case = RegisterProfessionalUseCase(supabase_admin_client)
        result = use_case.execute(RegisterProfessionalRequest(
            email='nuevo@centro.com',
            password='password123',
            full_name='Dra. Ana Lopez',
            center_id='uuid-del-centro',
        ))
    """

    def __init__(self, admin_client: Client) -> None:
        # Requiere el cliente admin (service_role) porque
        # crear usuarios de Auth necesita privilegios elevados
        self._client = admin_client

    def execute(
        self,
        request: RegisterProfessionalRequest,
    ) -> RegisteredProfessional:
        """
        Crea el usuario en Auth y su perfil en una sola operacion.

        Si falla la creacion del perfil despues de crear el usuario
        de Auth, queda un usuario huerfano en Auth sin perfil —
        en ese caso se loguea el error para resolverlo manualmente.

        Raises:
            Exception: si la creacion en Auth falla.
        """
        auth_response = self._client.auth.admin.create_user({
            "email": request.email,
            "password": request.password,
            "email_confirm": True,
        })

        user_id = auth_response.user.id

        try:
            self._client.table("users").insert({
                "id": user_id,
                "center_id": request.center_id,
                "full_name": request.full_name,
                "role": request.role,
            }).execute()
        except Exception as e:
            logger.error(
                "Usuario de Auth creado (%s) pero fallo el perfil en users: %s. "
                "Revisar manualmente.",
                user_id, str(e),
            )
            raise

        logger.info(
            "Profesional registrado: %s (%s) en centro %s.",
            request.full_name, user_id[:8], request.center_id[:8],
        )

        return RegisteredProfessional(
            user_id=user_id,
            email=request.email,
            full_name=request.full_name,
        )