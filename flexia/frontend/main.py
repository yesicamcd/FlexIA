"""Entry point de Streamlit – router de paginas."""
import streamlit as st

st.set_page_config(
    page_title="FlexIA",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# TODO: implementar navegacion entre paginas
st.title("FlexIA – Plataforma de Rehabilitacion")
st.info("Selecciona una seccion en el panel lateral.")