import streamlit as st
from datetime import date, timedelta
import db
import ui
from data import WEEK_PLAN, POSTURE_ROUTINE, DAY_ORDER, WEEKDAY_TO_KEY

DAY_LABELS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]


def render_week_view():
    today      = date.today()
    monday     = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    date_strs  = [d.strftime("%Y-%m-%d") for d in week_dates]

    stats        = db.get_stats_for_dates(date_strs)
    sessions_map = stats.get("sessions", {})
    exercises_l  = stats.get("exercises", [])
    posture_l    = stats.get("posture", [])

    ex_by_date: dict  = {}
    for r in exercises_l:
        ex_by_date.setdefault(r["date"], {})[r["exercise_id"]] = bool(r["completed"])

    pos_by_date: dict = {}
    for r in posture_l:
        pos_by_date.setdefault(r["date"], {})[r["exercise_id"]] = bool(r["completed"])

    total_sessions     = sum(1 for ds in date_strs if sessions_map.get(ds))
    total_posture_days = 0
    total_ex_done      = 0
    total_ex_all       = 0

    for ds, day_date in zip(date_strs, week_dates):
        key    = WEEKDAY_TO_KEY[day_date.weekday()]
        day    = WEEK_PLAN[key]
        n_tot  = len(day["exercises"])
        day_ex = ex_by_date.get(ds, {})
        n_done = sum(1 for eid in day["exercises"] if day_ex.get(eid, False))
        total_ex_done += n_done
        total_ex_all  += n_tot

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
    c3.metric("EJERCICIOS", f"{total_ex_done}/{total_ex_all}")
    c4.metric("DÍAS POSTURA", f"{total_posture_days}/7")

    # ── Day-by-day ticket list ─────────────────────────────────────────────────
    st.markdown(ui.label("DETALLE SEMANAL"), unsafe_allow_html=True)

    rows_html = ""
    for ds, day_date in zip(date_strs, week_dates):
        key      = WEEKDAY_TO_KEY[day_date.weekday()]
        day      = WEEK_PLAN[key]
        n_tot    = len(day["exercises"])
        day_ex   = ex_by_date.get(ds, {})
        n_done   = sum(1 for eid in day["exercises"] if day_ex.get(eid, False))
        session  = bool(sessions_map.get(ds))
        is_today = day_date == today

        label_txt = DAY_LABELS[day_date.weekday()]
        chip_html = (
            f'&nbsp;<span class="ia-chip brick" style="font-size:8px;">HOY</span>' if is_today else ""
        )
        rows_html += ui.ticket_row(
            num    = label_txt,
            name   = day["name"],
            detail = f"{day['tag']} · {n_done}/{n_tot} EJERCICIOS",
            done   = session,
            chips_html = chip_html,
        )

    st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)

    # ── Progress bars ──────────────────────────────────────────────────────────
    st.markdown(ui.label("PROGRESO"), unsafe_allow_html=True)
    st.markdown(
        ui.progress_bar("SESIONES", total_sessions, 7)
        + ui.progress_bar("EJERCICIOS", total_ex_done, max(total_ex_all, 1))
        + ui.progress_bar("DÍAS POSTURA", total_posture_days, 7),
        unsafe_allow_html=True,
    )
