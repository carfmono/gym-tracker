import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db
import styles
import ui

# ── DB init ────────────────────────────────────────────────────────────────────
db.init_db()
db.migrate_db()
db.seed_achievements()
db.seed_routine_templates()
db.init_user_xp(1)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    layout="centered",
    page_title="Iron Age",
    page_icon="🏋️",
)

# ── Session defaults ──────────────────────────────────────────────────────────
if "palette"       not in st.session_state: st.session_state.palette       = "venice"
if "accent"        not in st.session_state: st.session_state.accent        = None
if "grain_opacity" not in st.session_state: st.session_state.grain_opacity = 0.10
if "headline_font" not in st.session_state: st.session_state.headline_font = "Anton"

# ── Inject Iron Age CSS ───────────────────────────────────────────────────────
st.markdown(
    styles.build_css(
        palette       = st.session_state.palette,
        accent        = st.session_state.accent,
        grain_opacity = st.session_state.grain_opacity,
        headline_font = st.session_state.headline_font,
    ),
    unsafe_allow_html=True,
)

# ── Tab routing ───────────────────────────────────────────────────────────────
tab = st.query_params.get("tab", "hoy")

# Tab bar (fixed bottom)
st.markdown(ui.tab_bar(tab), unsafe_allow_html=True)

# ── Render current page ───────────────────────────────────────────────────────
if tab == "hoy":
    from components.day_view import render_day_view
    render_day_view()

elif tab == "entrenos":
    from components.week_view import render_week_view
    from components.month_view import render_month_view
    from components.routine_library import render_routine_library
    from components.routine_log import render_routine_log

    st.markdown(ui.screen_header("PROGRESO & RUTINAS", "ENTRENOS"), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["SEMANA", "MES", "BIBLIOTECA", "HISTORIAL"])
    with t1:
        render_week_view()
    with t2:
        render_month_view()
    with t3:
        render_routine_library()
    with t4:
        render_routine_log()

elif tab == "records":
    from components.gamification_dashboard import render_gamification_dashboard
    render_gamification_dashboard()

elif tab == "perfil":
    from components.profile import render_profile
    render_profile()

else:
    from components.day_view import render_day_view
    render_day_view()
