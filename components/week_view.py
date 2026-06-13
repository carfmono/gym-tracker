import streamlit as st
from datetime import date, timedelta
import db
import ui
from data import POSTURE_ROUTINE

DAY_LABELS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
DAY_FULL   = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def render_week_view():
    profile_id = st.session_state.profile_id
    today      = date.today()
    monday     = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    date_strs  = [d.strftime("%Y-%m-%d") for d in week_dates]

    stats        = db.get_stats_for_dates(date_strs, profile_id)
    sessions_map = stats.get("sessions", {})
    exercises_l  = stats.get("exercises", [])
    posture_l    = stats.get("posture", [])

    ex_done_by_date: dict[str, int] = {}
    for r in exercises_l:
        if bool(r["completed"]):
            ex_done_by_date[r["date"]] = ex_done_by_date.get(r["date"], 0) + 1

    pos_by_date: dict = {}
    for r in posture_l:
        pos_by_date.setdefault(r["date"], {})[r["exercise_id"]] = bool(r["completed"])

    total_sessions     = sum(1 for ds in date_strs if sessions_map.get(ds))
    total_ex_done      = sum(ex_done_by_date.values())
    total_posture_days = 0

    for ds in date_strs:
        pos_day  = pos_by_date.get(ds, {})
        pos_done = sum(1 for pid in POSTURE_ROUTINE if pos_day.get(pid, False))
        if pos_done == len(POSTURE_ROUTINE):
            total_posture_days += 1

    adherencia = (total_sessions / 7 * 100) if total_sessions else 0

    # ── Week boxes ─────────────────────────────────────────────────────────────
    boxes_data = [
        {
            "label": DAY_LABELS[i],
            "done":  bool(sessions_map.get(d.strftime("%Y-%m-%d"))),
            "today": d == today,
        }
        for i, d in enumerate(week_dates)
    ]
    st.markdown(ui.week_boxes(boxes_data), unsafe_allow_html=True)

    # ── Metric cards ───────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    c1.metric("SESIONES", f"{total_sessions}/7")
    c2.metric("ADHERENCIA", f"{adherencia:.0f}%")

    c3, c4 = st.columns(2)
    c3.metric("EJERCICIOS", total_ex_done)
    c4.metric("DÍAS POSTURA", f"{total_posture_days}/7")

    # ── Day-by-day ticket list ─────────────────────────────────────────────────
    st.markdown(ui.label("DETALLE SEMANAL"), unsafe_allow_html=True)

    rows_html = ""
    for ds, day_date in zip(date_strs, week_dates):
        n_done   = ex_done_by_date.get(ds, 0)
        session  = bool(sessions_map.get(ds))
        is_today = day_date == today

        chip_html = (
            f'&nbsp;<span class="ia-chip brick" style="font-size:8px;">HOY</span>' if is_today else ""
        )
        rows_html += ui.ticket_row(
            num    = DAY_LABELS[day_date.weekday()],
            name   = DAY_FULL[day_date.weekday()],
            detail = f"{n_done} EJERCICIOS",
            done   = session,
            chips_html = chip_html,
        )

    st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)

    # ── Progress bars ──────────────────────────────────────────────────────────
    goals = db.get_weekly_goals(profile_id, monday.isoformat())
    ex_goal = goals["exercises_goal"] if goals else 30

    st.markdown(ui.label("PROGRESO"), unsafe_allow_html=True)
    st.markdown(
        ui.progress_bar("SESIONES", total_sessions, 7)
        + ui.progress_bar("EJERCICIOS", total_ex_done, max(ex_goal, 1))
        + ui.progress_bar("DÍAS POSTURA", total_posture_days, 7),
        unsafe_allow_html=True,
    )

    # ── Comparación semanal ────────────────────────────────────────────────────
    st.markdown(ui.label("VS SEMANA ANTERIOR"), unsafe_allow_html=True)
    prev_dates = [(monday - timedelta(days=7 - i)).strftime("%Y-%m-%d") for i in range(7)]
    try:
        prev_stats = db.get_stats_for_dates(prev_dates, profile_id)
    except Exception:
        prev_stats = {"sessions": {}, "exercises": [], "posture": []}
    prev_sessions = sum(1 for ds in prev_dates if prev_stats["sessions"].get(ds))
    prev_ex_done  = sum(1 for r in prev_stats["exercises"] if bool(r["completed"]))

    c1, c2 = st.columns(2)
    c1.metric("SESIONES ESTA SEMANA", total_sessions, delta=total_sessions - prev_sessions)
    c2.metric("SESIONES SEMANA PASADA", prev_sessions)

    c3, c4 = st.columns(2)
    c3.metric("EJERCICIOS ESTA SEMANA", total_ex_done, delta=total_ex_done - prev_ex_done)
    c4.metric("EJERCICIOS SEMANA PASADA", prev_ex_done)
