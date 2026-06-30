"""Pagina de login con autenticacion real via Supabase."""
import streamlit as st
from infrastructure.supabase.client import get_supabase_client, get_supabase_admin_client
from frontend.state.auth_state import set_user


def render():
    st.title("FlexIA")
    st.subheader("Iniciar sesion")
    st.markdown("---")

    email = st.text_input("Email")
    password = st.text_input("Contrasena", type="password")

    if st.button("Ingresar", type="primary", use_container_width=True):
        if not email or not password:
            st.error("Ingresa email y contrasena.")
            return
        try:
            client = get_supabase_client()
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            user = response.user
            session = response.session

            profile_resp = (
                get_supabase_admin_client()
                .table("users")
                .select("id, full_name, role, center_id")
                .eq("id", user.id)
                .limit(1)
                .execute()
            )

            if not profile_resp.data:
                st.error("Usuario no encontrado en el sistema.")
                return

            profile = profile_resp.data[0]
            set_user({
                "id":          profile["id"],
                "full_name":   profile["full_name"],
                "role":        profile["role"],
                "center_id":   profile["center_id"],
                "email":       user.email,
                "access_token": session.access_token,
            })
            st.rerun()

        except Exception as e:
            st.error(f"Error al iniciar sesion: {e}")


render()