"""Gestion del estado de autenticacion en Streamlit."""
import streamlit as st

def is_authenticated() -> bool:
    return st.session_state.get("user") is not None

def get_current_user():
    return st.session_state.get("user")

def set_user(user):
    st.session_state["user"] = user

def clear_user():
    st.session_state.pop("user", None)
