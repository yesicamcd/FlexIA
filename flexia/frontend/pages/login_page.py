"""Pagina de login."""
import streamlit as st

def render():
    st.title("Iniciar sesion")
    email = st.text_input("Email")
    password = st.text_input("Contrasena", type="password")
    if st.button("Ingresar"):
        pass  # TODO: llamar LoginUseCase
