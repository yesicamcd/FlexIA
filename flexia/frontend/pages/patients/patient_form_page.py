"""Formulario de alta / edicion de paciente."""
import streamlit as st
from frontend.state.auth_state import get_current_user
from shared.container import get_patient_repository
from uuid import UUID

def render(patient_id: str = None):
    repo = get_patient_repository()
    paciente_real = None

    # Si la lista nos mandó un ID, buscamos a ese paciente específico en la base de datos
    if patient_id:
        try:
            # Usamos la función oficial para obtener el usuario e ID del centro de forma segura
            user = get_current_user()
            if user and "center_id" in user:
                pacientes_centro = repo.get_all_by_center(UUID(user["center_id"]))
                paciente_real = next((p for p in pacientes_centro if str(p.id) == patient_id), None)
        except Exception as e:
            st.error(f"Error al recuperar los datos del paciente: {e}")

    # Estructuramos los títulos según la acción
    if paciente_real:
        st.title(f"Editar Paciente: {paciente_real.full_name}")
        st.caption("Modificá los datos personales y clínicos guardados en el sistema.")
    else:
        st.title("Nuevo Paciente")
        st.caption("Completá los datos para ingresar un nuevo paciente al sistema FlexIA.")
        
    st.markdown("---")

    # Construcción del formulario
    with st.form("patient_form", border=True):
        
        # --- SECCIÓN 1: DATOS PERSONALES ---
        st.subheader("Datos Personales")
        col1, col2 = st.columns(2)
        
        with col1:
            nombre_input = st.text_input(
                "Nombre completo", 
                value=paciente_real.full_name if paciente_real else ""
            )
        with col2:
            fecha_nac = st.text_input(
                "Fecha de Nacimiento / Edad", 
                value=str(paciente_real.birth_date) if (paciente_real and hasattr(paciente_real, 'birth_date') and paciente_real.birth_date) else ""
            )

        st.write("") # Espaciador visual
        
        # --- SECCIÓN 2: DATOS CLÍNICOS ---
        st.subheader("Datos Clínicos")
        col_diag, col_prof = st.columns([2, 1])
        
        with col_diag:
            diagnostico_input = st.text_input(
                "Diagnóstico inicial o patología", 
                value=paciente_real.diagnosis if (paciente_real and paciente_real.diagnosis) else ""
            )
        with col_prof:
            profesional_input = st.selectbox(
                "Profesional Asignado",
                options=["Lic. Martín Suárez", "Dra. Elena Rostova", "Lic. Ana Gómez"],
                index=0
            )

        st.write("") # Espaciador visual
        
        # Botón de envío del formulario
        texto_boton = "💾 Actualizar Datos" if paciente_real else "💾 Guardar Nuevo Paciente"
        submitted = st.form_submit_button(texto_boton, type="primary")

        if submitted:
            if paciente_real:
                # TODO: Aquí irá el UpdatePatientUseCase pasándole los nuevos datos inputs
                st.success(f"¡Datos de {nombre_input} actualizados correctamente en la base de datos!")
            else:
                # TODO: Aquí irá el CreatePatientUseCase para dar el alta
                st.success(f"¡Paciente {nombre_input} creado con éxito!")

# Ejecutamos la pantalla leyendo la memoria de navegación
id_para_editar = st.session_state.get("edit_patient_id", None)
render(id_para_editar)