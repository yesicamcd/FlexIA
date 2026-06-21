"""Listado de pacientes."""
#import streamlit as st

#def render():
    #st.title("Pacientes")
    # TODO: llamar GetAllPatientsUseCase y mostrar tabla
import streamlit as st

# Mantenemos la lógica de la UI separada
def get_mock_patients():
    """
    Simula la llamada a GetAllPatientsUseCase.
    En el futuro, esto llamará a 'patient_service.get_all()'
    """
    return [
        {"id": "1", "nombre": "Juan Pérez", "diag": "LCA", "estado": "Activo"},
        {"id": "2", "nombre": "María Gómez", "diag": "Hombro", "estado": "En pausa"},
    ]

def render():
    st.title("📋 Pacientes")
    st.markdown("---")

    # Obtenemos los datos
    pacientes = get_mock_patients()

    # Usamos st.columns para un diseño más limpio (Regla 11: Modularización)
    for p in pacientes:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(p["nombre"])
                st.write(f"Diagnóstico: {p['diag']}")
            with col2:
                st.write(f"Estado: {p['estado']}")
                if st.button("Ver detalle", key=p["id"]):
                    # Redirección simplificada para el Sprint 1
                    st.info(f"Redirigiendo a ficha de {p['nombre']}...")