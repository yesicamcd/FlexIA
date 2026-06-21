"""Detalle de paciente + historial clinico."""
import streamlit as st

def get_mock_patient_history(patient_id: str):
    """
    Simula el caso de uso GetPatientHistoryUseCase.
    Mantiene la separación de datos y UI (Regla 2 y 9).
    """
    # Base de datos simulada por ID de paciente
    historiales = {
        "PAC-001": {
            "nombre": "Juan Pérez",
            "edad": 34,
            "diagnostico": "Rehabilitación LCA - Fase 2",
            "fecha_inicio": "2026-05-10",
            "profesional": "Lic. Martín Suárez",
            "ifi": "80%",
            "rango_articular": [110, 115, 120, 122, 125]
        },
        "PAC-002": {
            "nombre": "María Gómez",
            "edad": 42,
            "diagnostico": "Manguito Rotador - Movilidad activa",
            "fecha_inicio": "2026-06-01",
            "profesional": "Dra. Elena Rostova",
            "ifi": "65%",
            "rango_articular": [45, 50, 55, 60, 62]
        }
    }
    # Si no encuentra el ID, devolvemos el primero por defecto para el mockup
    return historiales.get(patient_id, historiales["PAC-001"])


def render(patient_id: str):
    # Obtenemos los datos clínicos simulando la arquitectura por capas
    paciente = get_mock_patient_history(patient_id)
    
    st.title(f"👤 Historial Clínico: {paciente['nombre']}")
    st.caption(f"Código identificador único: {patient_id}")
    st.markdown("---")
    
    # Ficha de Datos Generales
    with st.container(border=True):
        st.subheader("Información de Ficha")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Edad:** {paciente['edad']} años")
        with col2:
            st.write(f"**Diagnóstico:** {paciente['diagnostico']}")
        with col3:
            st.write(f"**Profesional:** {paciente['profesional']}")

    st.write("")

    # Evolución y Gráficos Biomecánicos
    st.subheader("📊 Análisis de Evolución Cinemática")
    
    col_metric, col_chart = st.columns([1, 2])
    
    with col_metric:
        st.metric(
            label="Índice Funcional Integrado (IFI)", 
            value=paciente["ifi"], 
            delta="Progreso dentro del rango objetivo"
        )
        st.write("El índice refleja una técnica correcta de ejecución sin registrar compensaciones cruzadas.")
        
    with col_chart:
        st.write("**Evolución del Rango Articular Máximo (ROM) en grados:**")
        # Generamos un gráfico de líneas real de Streamlit con los datos del paciente
        st.line_chart(paciente["rango_articular"])

    st.write("")
    
    # Carga de Videos
    st.subheader("📹 Cargar Sesión del Día")
    video_file = st.file_uploader("Seleccionar toma lateral de la sesión (MP4, MOV)", type=["mp4", "mov"])
    
    if video_file is not None:
        st.success("Archivo de video recibido.")
        if st.button("Ejecutar Análisis Biomecánico", type="primary"):
            st.info("Conectando con BiomechanicsService para extraer landmarks...")


# Para que Streamlit dibuje la pantalla al abrir el archivo, 
# recuperamos el ID de la sesión o usamos uno de prueba por defecto.
id_actual = st.session_state.get("selected_patient_id", "PAC-001")
render(id_actual)