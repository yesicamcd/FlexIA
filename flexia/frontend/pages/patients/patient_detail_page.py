"""Historial clinico real del paciente desde Supabase."""
import streamlit as st
from frontend.state.auth_state import get_current_user
from shared.container import get_patient_history_use_case


def render():
    user = get_current_user()
    if not user:
        st.error("Sesion no iniciada.")
        return

    patient_id = st.session_state.get("selected_patient_id")
    patient_name = st.session_state.get("selected_patient_name", "Paciente")

    if not patient_id:
        st.warning("Selecciona un paciente desde la lista.")
        if st.button("Ir a lista de pacientes"):
            st.switch_page("pages/patients/patient_list_page.py")
        return

    st.title(f"Historial Clinico: {patient_name}")
    st.markdown("---")

    try:
        uc = get_patient_history_use_case()
        history = uc.execute(patient_id)
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")
        return

    if not history:
        st.info("Este paciente no tiene sesiones registradas.")
        if st.button("Iniciar primera sesion", type="primary"):
            st.session_state["selected_patient_id"] = patient_id
            st.switch_page("pages/sessions/session_create_page.py")
        return

    ifis = [s["ifi_score"] for s in history if s["ifi_score"] is not None]
    if ifis:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("IFI Ultima Sesion", f"{ifis[0]:.1f}")
        with col2:
            st.metric("IFI Promedio", f"{sum(ifis)/len(ifis):.1f}")
        with col3:
            st.metric("Total Sesiones", len(history))

        st.markdown("---")
        st.subheader("Evolucion del IFI")
        import pandas as pd
        df = pd.DataFrame([
            {
                "Fecha": s["session_date"][:10],
                "IFI":   s["ifi_score"],
            }
            for s in reversed(history)
            if s["ifi_score"] is not None
        ])
        if not df.empty:
            st.line_chart(df.set_index("Fecha")["IFI"])

    st.markdown("---")
    st.subheader("Sesiones")

    for s in history:
        with st.expander(
            f"{s['session_date'][:10]} — {s['routine_name']} — "
            f"IFI: {s['ifi_score'] or 'N/A'} — {s['status']}"
        ):
            if s["results"]:
                for r in s["results"]:
                    perf = r.get("performance", "N/A")
                    rom = r.get("rom_percentage")
                    color = (
                        "🟢" if perf == "green"
                        else "🟡" if perf == "yellow"
                        else "🔴"
                    )
                    st.write(
                        f"{color} ROM: {rom:.1f}%" if rom else f"{color} Sin datos"
                    )
            else:
                st.write("Sin resultados de ejercicios.")

    st.markdown("---")
    if st.button("Nueva sesion para este paciente", type="primary"):
        st.switch_page("pages/sessions/session_create_page.py")


render()