"""Formulario de alta / edicion de paciente."""
import streamlit as st

def render(patient_id: str = None):
    st.title("Nuevo paciente" if not patient_id else "Editar paciente")
    # TODO: llamar CreatePatientUseCase o UpdatePatientUseCase
