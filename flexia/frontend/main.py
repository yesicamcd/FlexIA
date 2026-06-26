import streamlit as st

st.set_page_config(
    page_title="FlexIA",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definimos el menú solo con las páginas que sabemos que existen y armamos
paginas = st.navigation([
    st.Page("pages/dashboards/clinical_dashboard_page.py", title="Dashboard Clínico", icon="📊"),
    st.Page("pages/patients/patient_list_page.py", title="Lista de Pacientes", icon="📋"),
    st.Page("pages/patients/patient_detail_page.py", title="Detalle Paciente", icon="👤")
])

# Ejecutamos la navegación
paginas.run()