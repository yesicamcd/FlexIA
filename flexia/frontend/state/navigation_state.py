"""Gestion de navegacion entre paginas."""
import streamlit as st

def go_to(page: str, **params):
    st.session_state["page"] = page
    for k, v in params.items():
        st.session_state[k] = v
    st.rerun()

def current_page() -> str:
    return st.session_state.get("page", "login")
