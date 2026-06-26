import streamlit as st

# Inyectamos los estilos visuales (Azul petróleo y Naranja)
st.markdown("""
    <style>
    .tarjeta-oscura {
        background-color: #1A4049;
        color: white;
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    .tarjeta-clara {
        background-color: #FFF0E0;
        color: #1A4049;
        padding: 20px;
        border-radius: 15px;
        border-left: 6px solid #F9A826;
        margin-bottom: 15px;
    }
    .metrica-destacada {
        color: #F9A826;
        font-size: 48px;
        font-weight: bold;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Panel de Control Clínico")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    # Tarjeta principal de evolución
    st.markdown("""
        <div class="tarjeta-oscura">
            <h3 style="margin-top:0px; color: white;">Evolución de Rango Articular</h3>
            <p>El paciente ha mantenido la técnica correcta sin compensaciones.</p>
            <p class="metrica-destacada">80%</p>
            <p>Índice Funcional Integrado</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    # Agenda clínica
    st.markdown("#### Pacientes de Hoy")
    st.markdown("""
        <div class="tarjeta-clara">
            <h4 style="margin-top:0px; margin-bottom:5px; color: #1A4049;">Juan Pérez</h4>
            <p style="margin:0px;"><b>11:00 - 12:00</b></p>
            <p style="margin:0px;">Rehabilitación LCA - Fase 2</p>
        </div>
    """, unsafe_allow_html=True)