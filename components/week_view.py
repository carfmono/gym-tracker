import streamlit as st
import pandas as pd
from datetime import date, timedelta
import db
from data import WEEK_PLAN, POSTURE_ROUTINE, DAY_ORDER, WEEKDAY_TO_KEY


def render_week_view():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    date_strs = [d.strftime("%Y-%m-%d") for d in week_dates]

    stats = db.get_stats_for_dates(date_strs)
    sessions_map = stats.get("sessions", {})
    exercises_list = stats.get("exercises", [])
    posture_list = stats.get("posture", [])

    ex_by_date: dict[str, dict] = {}
    for r in exercises_list:
        ex_by_date.setdefault(r["date"], {})[r["exercise_id"]] = bool(r["completed"])

    pos_by_date: dict[str, dict] = {}
    for r in posture_list:
        pos_by_date.setdefault(r["date"], {})[r["exercise_id"]] = bool(r["completed"])

    total_sessions = sum(1 for ds in date_strs if sessions_map.get(ds))
    total_posture_days = 0
    total_ex_done = 0
    total_ex_all = 0

    rows = []
    for ds, day_date in zip(date_strs, week_dates):
        key = WEEKDAY_TO_KEY[day_date.weekday()]
        day = WEEK_PLAN[key]
        n_total = len(day["exercises"])
        day_ex = ex_by_date.get(ds, {})
        n_done = sum(1 for eid in day["exercises"] if day_ex.get(eid, False))
        total_ex_done += n_done
        total_ex_all += n_total

        pos_day = pos_by_date.get(ds, {})
        pos_done = sum(1 for pid in POSTURE_ROUTINE if pos_day.get(pid, False))
        if pos_done == len(POSTURE_ROUTINE):
            total_posture_days += 1

        session_icon = "✅" if sessions_map.get(ds) else "○"
        rows.append({
            "Día": day["name"],
            "Fecha": day_date.strftime("%d/%m"),
            "Tipo": day["tag"],
            "Ejerc.": f"{n_done}/{n_total}",
            "Post.": f"{pos_done}/5",
            "✓": session_icon,
        })

    adherencia = (total_sessions / 7 * 100) if total_sessions else 0

    # 2×2 para mobile
    c1, c2 = st.columns(2)
    c1.metric("Sesiones", f"{total_sessions}/7")
    c2.metric("Adherencia", f"{adherencia:.0f}%")

    c3, c4 = st.columns(2)
    c3.metric("Ejercicios", f"{total_ex_done}/{total_ex_all}")
    c4.metric("Días postura", f"{total_posture_days}/7")

    st.divider()

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
