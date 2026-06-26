import streamlit as st

def get_mock_patients():
    return [
        {"id": "PAC-001", "nombre": "Juan Pérez", "diag": "LCA - Fase 2", "estado": "Activo"},
        {"id": "PAC-002", "nombre": "María Gómez", "diag": "Manguito Rotador", "estado": "En pausa"},
    ]

def render():
    st.title("📋 Pacientes")
    st.markdown("---")

    pacientes = get_mock_patients()

    for p in pacientes:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(p["nombre"])
                st.write(f"Diagnóstico: {p['diag']}")
            with col2:
                st.write(f"Estado: {p['estado']}")
                if st.button("Ver detalle", key=p["id"]):
                    # Guardamos el ID en memoria para que la otra página lo lea
                    st.session_state["selected_patient_id"] = p["id"]
                    st.success(f"Cargando ficha de {p['nombre']}... ¡Hacé clic en 'Detalle Paciente' en el menú de la izquierda para verla!")

render()