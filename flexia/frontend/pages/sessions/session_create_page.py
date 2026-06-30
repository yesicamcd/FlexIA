"""
Crear y lanzar una sesion biomecanica.
Este es el archivo mas importante para la demo —
conecta el frontend con el motor biomecanico completo.
"""
import streamlit as st
from uuid import UUID
from frontend.state.auth_state import get_current_user
from infrastructure.supabase.client import get_supabase_admin_client
from shared.container import get_create_session_use_case, get_process_video_use_case
from app.use_cases.sessions.create_session_use_case import CreateSessionRequest
from app.use_cases.biomechanics.process_video_use_case import ProcessSessionRequest


def load_patient_routines(patient_id: str) -> list[dict]:
    """Carga las rutinas asignadas al paciente."""
    client = get_supabase_admin_client()
    response = (
        client.table("patient_routines")
        .select("id, routine_id, routines(name)")
        .eq("patient_id", patient_id)
        .eq("is_active", True)
        .execute()
    )
    return response.data or []


def render():
    user = get_current_user()
    if not user:
        st.error("Sesion no iniciada.")
        return

    st.title("Nueva Sesion de Evaluacion")
    st.markdown("---")

    patient_id = st.session_state.get("selected_patient_id")
    patient_name = st.session_state.get("selected_patient_name", "Paciente")

    if not patient_id:
        st.warning("Selecciona un paciente primero.")
        if st.button("Ir a lista de pacientes"):
            st.switch_page("pages/patients/patient_list_page.py")
        return

    st.subheader(f"Paciente: {patient_name}")

    routines = load_patient_routines(patient_id)
    if not routines:
        st.error("Este paciente no tiene rutinas asignadas.")
        return

    routine_options = {
        row["routines"]["name"]: row["id"]
        for row in routines
        if isinstance(row.get("routines"), dict)
    }

    selected_routine_name = st.selectbox(
        "Seleccionar rutina",
        options=list(routine_options.keys()),
    )
    patient_routine_id = routine_options[selected_routine_name]

    st.markdown("---")
    st.subheader("Configuracion de camaras")

    col1, col2 = st.columns(2)
    with col1:
        front_cam = st.number_input(
            "Indice camara frontal", min_value=0, max_value=5, value=0
        )
    with col2:
        lateral_cam = st.number_input(
            "Indice camara lateral", min_value=0, max_value=5, value=1
        )

    notes = st.text_area("Notas de la sesion (opcional)")

    st.markdown("---")

    if "session_result" in st.session_state:
        result = st.session_state.pop("session_result")
        if result["was_completed"]:
            st.success("Sesion completada exitosamente.")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("IFI", f"{result['ifi_score']:.1f}" if result["ifi_score"] else "N/A")
            with col2:
                st.metric("Clasificacion", result["ifi_label"] or "N/A")
            with col3:
                st.metric("Ejercicios", result["total_exercises"])
        else:
            st.warning(f"Sesion no completada: {result['abort_reason']}")

    if st.button("Iniciar Sesion Biomecanica", type="primary", use_container_width=True):
        with st.spinner("Creando sesion en Supabase..."):
            try:
                create_uc = get_create_session_use_case()
                created = create_uc.execute(CreateSessionRequest(
                    patient_routine_id=UUID(patient_routine_id),
                    professional_id=UUID(user["id"]),
                    notes=notes or None,
                ))
            except Exception as e:
                st.error(f"Error al crear la sesion: {e}")
                return

        st.info(
            "Sesion creada. Se abrira la ventana de la camara. "
            "Presiona Q para abortar o N para pasar al siguiente ejercicio."
        )

        try:
            process_uc = get_process_video_use_case()
            result = process_uc.execute(ProcessSessionRequest(
                session_id=created.session_id,
                patient_id=patient_id,
                professional_id=user["id"],
                center_id=user["center_id"],
                patient_routine_id=patient_routine_id,
                front_camera_index=int(front_cam),
                lateral_camera_index=int(lateral_cam),
                record_video=True,
            ))

            st.session_state["session_result"] = {
                "was_completed":  result.was_completed,
                "ifi_score":      result.ifi_score,
                "ifi_label":      result.ifi_label,
                "total_exercises": result.total_exercises,
                "abort_reason":   result.abort_reason,
            }
            st.rerun()

        except Exception as e:
            st.error(f"Error durante la sesion: {e}")


render()