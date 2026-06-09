import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db

db.init_db()
db.migrate_db()

st.set_page_config(
    layout="centered",
    page_title="Gym Tracker",
    page_icon="🏋️",
)

st.markdown(
    """
    <style>
    /* ── Base ── */
    .stApp { background-color: #0E1117; }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem;
    }

    /* ── Mobile ── */
    @media (max-width: 640px) {
        /* Padding mínimo en pantalla pequeña */
        .block-container {
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
            padding-top: 0.75rem !important;
            max-width: 100% !important;
        }

        /* Columnas apiladas verticalmente */
        [data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }

        /* Botones más grandes y full-width */
        [data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 3rem !important;
            font-size: 1rem !important;
        }

        /* Checkboxes con más aire para toque */
        [data-testid="stCheckbox"] {
            padding: 5px 0 !important;
        }
        [data-testid="stCheckbox"] label p {
            font-size: 0.95rem !important;
            line-height: 1.4 !important;
        }

        /* Métricas con fondo sutil */
        [data-testid="metric-container"] {
            background: #1C2833;
            border-radius: 10px;
            padding: 10px 12px !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.72rem !important;
        }

        /* Tabs: scroll horizontal si no caben */
        [data-testid="stTabs"] > div:first-child {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        [data-testid="stTabs"] > div:first-child::-webkit-scrollbar {
            display: none;
        }

        /* Títulos más compactos */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; margin-top: 0.5rem !important; }
        h3 { font-size: 1rem !important; }

        /* Expanders con padding mínimo */
        [data-testid="stExpander"] > div > div {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }

        /* Dataframe scroll horizontal sin overflow */
        [data-testid="stDataFrame"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }

        /* Selectbox y date_input full width */
        [data-testid="stSelectbox"],
        [data-testid="stDateInput"] {
            width: 100% !important;
        }

        /* Formularios sin gap excesivo */
        [data-testid="stForm"] {
            padding: 0.75rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏋️ Gym Tracker")

tab_hoy, tab_semana, tab_mes, tab_rutinas = st.tabs(
    ["📅 Hoy", "📊 Semana", "📆 Mes", "📋 Rutinas"]
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
