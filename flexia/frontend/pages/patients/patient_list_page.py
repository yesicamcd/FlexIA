"""Lista de pacientes del centro con datos reales de Supabase."""
import streamlit as st
from frontend.state.auth_state import get_current_user
from shared.container import get_patient_repository
from uuid import UUID

def render():
    st.title("Pacientes")
    
    # Botón general para crear paciente nuevo
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn2:
        if st.button("➕ Nuevo Paciente", type="primary", use_container_width=True):
            st.session_state["edit_patient_id"] = None
            st.switch_page("pages/patients/patient_form_page.py")
            
    st.markdown("---")

    user = get_current_user()
    if not user:
        st.error("Sesion no iniciada.")
        return

    try:
        repo = get_patient_repository()
        pacientes = repo.get_all_by_center(UUID(user["center_id"]))
    except Exception as e:
        st.error(f"Error al cargar pacientes: {e}")
        return

    if not pacientes:
        st.info("No hay pacientes registrados en este centro.")
        if st.button("Agregar primer paciente", type="primary"):
            st.session_state["edit_patient_id"] = None
            st.switch_page("pages/patients/patient_form_page.py")
        return

    st.write(f"**{len(pacientes)} pacientes activos**")

    for p in pacientes:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(p.full_name)
                if p.diagnosis:
                    st.write(f"Diagnóstico: {p.diagnosis}")
                if p.birth_date:
                    st.caption(f"Nacimiento: {p.birth_date}")
                    
            with col2:
                estado = "Activo" if p.is_active else "Inactivo"
                st.write(f"Estado: {estado}")
                
                if st.button("Ver historial", key=str(p.id)):
                    st.session_state["selected_patient_id"] = str(p.id)
                    st.session_state["selected_patient_name"] = p.full_name
                    st.switch_page("pages/patients/patient_detail_page.py")
                    
                # --- ACÁ ESTÁ EL BOTÓN DE EDITAR BIEN ALINEADO ---
                if st.button("Editar", key=f"edit_{p.id}"):
                    st.session_state["edit_patient_id"] = str(p.id)
                    st.switch_page("pages/patients/patient_form_page.py")

render()