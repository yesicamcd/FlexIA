import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from frontend.state.auth_state import is_authenticated, get_current_user, clear_user

st.set_page_config(
    page_title="FlexIA",
    page_icon="frontend/logo.png",  # <-- Acá cambiamos el emoji por la ruta de tu imagen
    layout="wide",
    initial_sidebar_state="expanded"
)


if not is_authenticated():
    from frontend.pages.login_page import render
    render()
    st.stop()

user = get_current_user()

with st.sidebar:
    st.markdown(f"**{user['full_name']}**")
    st.caption(user.get("role", ""))
    st.markdown("---")
    if st.button("Cerrar sesion", use_container_width=True):
        clear_user()
        st.rerun()


# Definimos el menú solo con las páginas que sabemos que existen y armamos
paginas = st.navigation([
    st.Page("pages/dashboards/clinical_dashboard_page.py",
            title="Dashboard"),
    st.Page("pages/patients/patient_list_page.py",
            title="Pacientes"),
    st.Page("pages/patients/patient_detail_page.py",
            title="Detalle Paciente"),
    st.Page("pages/patients/patient_form_page.py",
            title="Nuevo Paciente"),
    st.Page("pages/sessions/session_create_page.py",
            title="Nueva Sesion"),
])

# Ejecutamos la navegación
paginas.run()