"""
infrastructure/supabase/client.py

Clientes de conexion a Supabase.

get_supabase_client()       -> cliente con anon key (usuario autenticado)
get_supabase_admin_client() -> cliente con service key (procesos de servidor)
"""

from supabase import create_client, Client
from shared.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

_client: Client | None = None
_admin_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Cliente estandar con anon key.
    Respeta las politicas RLS.
    Usar para operaciones del usuario autenticado.
    """
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def get_supabase_admin_client() -> Client:
    """
    Cliente administrativo con service_role key.
    Bypasea RLS — usar solo en procesos de servidor.
    Nunca exponer en frontend ni en codigo del cliente.
    """
    global _admin_client
    if _admin_client is None:
        _admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _admin_client