import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import calendar
import db
from data import WEEK_PLAN, POSTURE_ROUTINE, WEEKDAY_TO_KEY


def render_month_view():
    today = date.today()
    year, month = today.year, today.month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    all_dates = []
    d = first_day
    while d <= last_day:
        all_dates.append(d)
        d += timedelta(days=1)

    date_strs = [d.strftime("%Y-%m-%d") for d in all_dates]
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
    adherence_by_weekday = {i: {"done": 0, "total": 0} for i in range(7)}

    for d, ds in zip(all_dates, date_strs):
        key = WEEKDAY_TO_KEY[d.weekday()]
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

        wd = d.weekday()
        adherence_by_weekday[wd]["total"] += 1
        if sessions_map.get(ds):
            adherence_by_weekday[wd]["done"] += 1

    adherencia = (total_sessions / len(all_dates) * 100) if all_dates else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sesiones en el mes", f"{total_sessions}/{len(all_dates)}")
    c2.metric("Ejercicios realizados", f"{total_ex_done}/{total_ex_all}")
    c3.metric("Días postura completa", f"{total_posture_days}/{len(all_dates)}")
    c4.metric("Adherencia mensual", f"{adherencia:.0f}%")

    st.divider()

    # ── Heatmap ───────────────────────────────────────────────────────────────
    st.subheader(f"Heatmap — {today.strftime('%B %Y')}")

    heat_data = []
    for d, ds in zip(all_dates, date_strs):
        key = WEEKDAY_TO_KEY[d.weekday()]
        day_ex = ex_by_date.get(ds, {})
        day_data = WEEK_PLAN[key]
        n_total = len(day_data["exercises"])
        n_done = sum(1 for eid in day_data["exercises"] if day_ex.get(eid, False))
        pct = (n_done / n_total * 100) if n_total else 0
        heat_data.append({
            "date": d,
            "day": d.day,
            "weekday": d.weekday(),
            "week": (d.day + first_day.weekday() - 1) // 7,
            "pct": pct,
            "session": sessions_map.get(ds, False),
            "label": f"{d.strftime('%d/%m')}<br>{n_done}/{n_total} ej.",
        })

    df_heat = pd.DataFrame(heat_data)
    pivot = df_heat.pivot_table(index="weekday", columns="week", values="pct", fill_value=None)

    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    n_weeks = df_heat["week"].max() + 1
    week_labels = [f"Sem {i+1}" for i in range(n_weeks)]

    z_vals = [[pivot.get(col, {}).get(row) for col in range(n_weeks)] for row in range(7)]

    fig = go.Figure(
        go.Heatmap(
            z=z_vals,
            x=week_labels,
            y=day_names,
            colorscale=[[0, "#1c2833"], [0.5, "#2980B9"], [1, "#27AE60"]],
            zmin=0,
            zmax=100,
            text=[[
                df_heat[(df_heat["weekday"] == row) & (df_heat["week"] == col)]["label"].values[0]
                if not df_heat[(df_heat["weekday"] == row) & (df_heat["week"] == col)].empty else ""
                for col in range(n_weeks)
            ] for row in range(7)],
            hovertemplate="%{text}<br>Completado: %{z:.0f}%<extra></extra>",
            showscale=True,
        )
    )
    fig.update_layout(
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font_color="#FAFAFA",
        height=320,
        margin=dict(l=40, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Adherencia por día ────────────────────────────────────────────────────
    st.subheader("Adherencia por día de la semana")
    bar_x = day_names
    bar_y = [
        (adherence_by_weekday[i]["done"] / adherence_by_weekday[i]["total"] * 100)
        if adherence_by_weekday[i]["total"] > 0 else 0
        for i in range(7)
    ]
    colors = ["#2980B9", "#27AE60", "#F39C12", "#8E44AD", "#C0392B", "#1A5276", "#1E8449"]

    fig2 = go.Figure(
        go.Bar(
            x=bar_x,
            y=bar_y,
            marker_color=colors,
            text=[f"{v:.0f}%" for v in bar_y],
            textposition="outside",
        )
    )
    fig2.update_layout(
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font_color="#FAFAFA",
        yaxis=dict(range=[0, 110], title="% sesiones completadas"),
        height=300,
        margin=dict(l=40, r=20, t=10, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)
