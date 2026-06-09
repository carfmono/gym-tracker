import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db

db.init_db()
db.migrate_db()
db.seed_achievements()
db.seed_routine_templates()
db.init_user_xp(1)

st.set_page_config(
    layout="centered",
    page_title="Gym Tracker",
    page_icon="🏋️",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; }
    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.78rem; }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
            padding-top: 0.5rem !important;
            max-width: 100% !important;
        }
        [data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
        [data-testid="stButton"] > button {
            width: 100% !important;
            min-height: 3rem !important;
            font-size: 1rem !important;
        }
        [data-testid="stCheckbox"] { padding: 5px 0 !important; }
        [data-testid="stCheckbox"] label p { font-size: 0.95rem !important; }
        [data-testid="metric-container"] {
            background: #1C2833;
            border-radius: 10px;
            padding: 10px 12px !important;
        }
        div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
        [data-testid="stTabs"] > div:first-child {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        [data-testid="stTabs"] > div:first-child::-webkit-scrollbar { display: none; }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; margin-top: 0.5rem !important; }
        h3 { font-size: 1rem !important; }
        [data-testid="stExpander"] > div > div {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }
        [data-testid="stDataFrame"] { overflow-x: auto !important; }
        [data-testid="stForm"] { padding: 0.75rem !important; }

        /* Sidebar más compacto en móvil */
        [data-testid="stSidebarContent"] { padding: 0.5rem !important; }
        [data-testid="stSidebarNav"] { padding-top: 0 !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Navegación sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏋️ Gym Tracker")
    page = st.radio(
        "Menú",
        [
            "📅 Hoy",
            "📊 Semana",
            "📆 Mes",
            "🎮 Gamificación",
            "📚 Rutinas",
            "📋 Registro rutinas",
        ],
        label_visibility="collapsed",
    )

# ── Páginas ───────────────────────────────────────────────────────────────────
if page == "📅 Hoy":
    from components.day_view import render_day_view
    render_day_view()

elif page == "📊 Semana":
    st.title("📊 Semana")
    from components.week_view import render_week_view
    render_week_view()

elif page == "📆 Mes":
    st.title("📆 Mes")
    from components.month_view import render_month_view
    render_month_view()

elif page == "🎮 Gamificación":
    st.title("🎮 Gamificación")
    from components.gamification_dashboard import render_gamification_dashboard
    render_gamification_dashboard()

elif page == "📚 Rutinas":
    st.title("📚 Biblioteca de Rutinas")
    from components.routine_library import render_routine_library
    render_routine_library()

elif page == "📋 Registro rutinas":
    st.title("📋 Registro de Rutinas")
    from components.routine_log import render_routine_log
    render_routine_log()
