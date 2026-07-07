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
        font-size: 40px;
        font-weight: bold;
        margin: 0;
    }
    .titulo-tarjeta {
        margin-top:0px; 
        color: white;
        font-size: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Panel de Control Clínico")
st.caption("Resumen general de la actividad y estado del centro de rehabilitación.")
st.markdown("---")

# 1. Fila Superior: Métricas Generales (KPIs del centro)
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

with col_kpi1:
    st.markdown("""
        <div class="tarjeta-oscura">
            <h3 class="titulo-tarjeta">Pacientes Activos</h3>
            <p class="metrica-destacada">42</p>
            <p style="margin-bottom: 0; color: #E0E0E0;">En tratamiento actual</p>
        </div>
    """, unsafe_allow_html=True)

with col_kpi2:
    st.markdown("""
        <div class="tarjeta-oscura">
            <h3 class="titulo-tarjeta">Sesiones de Hoy</h3>
            <p class="metrica-destacada">14</p>
            <p style="margin-bottom: 0; color: #E0E0E0;">8 completadas | 6 pendientes</p>
        </div>
    """, unsafe_allow_html=True)

with col_kpi3:
    st.markdown("""
        <div class="tarjeta-oscura" style="border-bottom: 6px solid #F9A826;">
            <h3 class="titulo-tarjeta">IFI Promedio</h3>
            <p class="metrica-destacada">78%</p>
            <p style="margin-bottom: 0; color: #E0E0E0;">Índice Funcional global</p>
        </div>
    """, unsafe_allow_html=True)

st.write("") # Espaciador

# 2. Fila Inferior: Agenda y Alertas
col_agenda, col_alertas = st.columns([1, 1])

with col_agenda:
    st.subheader("Próximos Turnos")
    
    st.markdown("""
        <div class="tarjeta-clara">
            <h4 style="margin-top:0px; margin-bottom:5px; color: #1A4049;">Juan Pérez</h4>
            <p style="margin:0px;"><b>11:00 - 12:00</b> | Lic. Martín Suárez</p>
            <p style="margin:0px;">Rehabilitación LCA - Fase 2</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="tarjeta-clara">
            <h4 style="margin-top:0px; margin-bottom:5px; color: #1A4049;">María Gómez</h4>
            <p style="margin:0px;"><b>12:30 - 13:30</b> | Dra. Elena Rostova</p>
            <p style="margin:0px;">Manguito Rotador - Movilidad activa</p>
        </div>
    """, unsafe_allow_html=True)

with col_alertas:
    st.subheader("Alertas y Novedades")
    
    st.warning("**Atención requerida:** Carlos López presentó compensaciones cruzadas en su última sesión. Revisar progresión biomecánica.")
    st.info("**Evaluación pendiente:** El video de la sesión de Ana Martínez está listo para procesar en FlexIA.")
    st.success("**Objetivo alcanzado:** Juan Pérez ha superado el 90% en su Score IFI sostenido durante 3 sesiones seguidas.")