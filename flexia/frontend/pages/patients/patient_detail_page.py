"""Detalle de paciente + historial clinico."""
import streamlit as st

def render(patient_id: str):
    st.title("Detalle del paciente")
    # TODO: llamar GetPatientHistoryUseCase
