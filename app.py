import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db

db.init_db()

st.set_page_config(
    layout="wide",
    page_title="Gym Tracker",
    page_icon="🏋️",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏋️ Gym Tracker")

tab_hoy, tab_semana, tab_mes, tab_rutinas = st.tabs(
    ["📅 Hoy", "📊 Semana", "📆 Mes", "📋 Registro de rutinas"]
)

with tab_hoy:
    from components.day_view import render_day_view
    render_day_view()

with tab_semana:
    from components.week_view import render_week_view
    render_week_view()

with tab_mes:
    from components.month_view import render_month_view
    render_month_view()

with tab_rutinas:
    from components.routine_log import render_routine_log
    render_routine_log()
