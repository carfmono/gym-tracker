import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import db
import ui
from data import POSTURE_ROUTINE

DAY_LABELS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
DAY_FULL   = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

MONTH_NAMES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]


def _plotly_base() -> dict:
    """Plotly layout matching current Iron Age palette (reads CSS vars via defaults)."""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font         =dict(color="#2A1C10", family="'Space Mono', monospace", size=11),
        margin       =dict(l=32, r=8, t=12, b=12),
    )


_PLOTLY_CFG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


def render_month_view():
    profile_id = st.session_state.profile_id
    today      = date.today()

    # ── Month navigation ───────────────────────────────────────────────────────
    if "month_offset" not in st.session_state:
        st.session_state.month_offset = 0

    offset = st.session_state.month_offset
    target = date(today.year, today.month, 1)
    for _ in range(abs(offset)):
        if offset < 0:
            target = (target - timedelta(days=1)).replace(day=1)
        else:
            target = (target + timedelta(days=32)).replace(day=1)
    year, month = target.year, target.month
    first_day   = date(year, month, 1)

    col_prev, col_title, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("◀", key="month_prev", use_container_width=True):
            st.session_state.month_offset -= 1
            st.rerun()
    with col_title:
        st.markdown(
            f'<div style="text-align:center;font-family:var(--font-display);font-size:20px;'
            f'text-transform:uppercase;color:var(--ink);padding-top:4px;">'
            f'{MONTH_NAMES[month - 1]} {year}</div>',
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("▶", key="month_next", disabled=offset >= 0, use_container_width=True):
            if st.session_state.month_offset < 0:
                st.session_state.month_offset += 1
                st.rerun()

    all_dates: list[date] = []
    d = first_day
    while d.month == month:
        all_dates.append(d)
        d += timedelta(days=1)

    date_strs    = [d.strftime("%Y-%m-%d") for d in all_dates]
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
    adherence_by_wd    = {i: {"done": 0, "total": 0} for i in range(7)}
    heat_data          = []
    max_ex_day         = max(ex_done_by_date.values(), default=0)

    for d, ds in zip(all_dates, date_strs):
        n_done = ex_done_by_date.get(ds, 0)

        pos_day  = pos_by_date.get(ds, {})
        pos_done = sum(1 for pid in POSTURE_ROUTINE if pos_day.get(pid, False))
        if pos_done == len(POSTURE_ROUTINE):
            total_posture_days += 1

        wd = d.weekday()
        adherence_by_wd[wd]["total"] += 1
        if sessions_map.get(ds):
            adherence_by_wd[wd]["done"] += 1

        pct      = (n_done / max_ex_day * 100) if max_ex_day else 0
        week_col = (d.day + first_day.weekday() - 1) // 7
        heat_data.append({
            "weekday": wd,
            "week":    week_col,
            "pct":     pct,
            "label":   f"{d.strftime('%d/%m')}<br>{n_done} ejercicios",
        })

    adherencia = (total_sessions / len(all_dates) * 100) if all_dates else 0

    # ── Metrics ────────────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    c1.metric("SESIONES", f"{total_sessions}/{len(all_dates)}")
    c2.metric("ADHERENCIA", f"{adherencia:.0f}%")

    c3, c4 = st.columns(2)
    c3.metric("EJERCICIOS", total_ex_done)
    c4.metric("DÍAS POSTURA", f"{total_posture_days}/{len(all_dates)}")

    # ── Mejor día + racha más larga del mes ────────────────────────────────────
    best_wd, best_pct = None, 0.0
    for i in range(7):
        t = adherence_by_wd[i]["total"]
        p = (adherence_by_wd[i]["done"] / t * 100) if t else 0
        if p > best_pct:
            best_wd, best_pct = i, p

    longest_run, run = 0, 0
    for ds in date_strs:
        if sessions_map.get(ds):
            run += 1
            longest_run = max(longest_run, run)
        else:
            run = 0

    c5, c6 = st.columns(2)
    c5.metric("MEJOR DÍA", DAY_FULL[best_wd].upper() if best_wd is not None else "—",
              delta=f"{best_pct:.0f}% adherencia" if best_wd is not None else None,
              delta_color="off")
    c6.metric("RACHA MÁS LARGA", f"{longest_run}d")

    # ── Progress bars ──────────────────────────────────────────────────────────
    st.markdown(ui.label(f"PROGRESO — {MONTH_NAMES[month - 1]} {year}"), unsafe_allow_html=True)
    st.markdown(
        ui.progress_bar("SESIONES", total_sessions, len(all_dates)),
        unsafe_allow_html=True,
    )

    # ── Heatmap ────────────────────────────────────────────────────────────────
    st.markdown(ui.label("HEATMAP"), unsafe_allow_html=True)

    df_heat  = pd.DataFrame(heat_data)
    pivot    = df_heat.pivot_table(index="weekday", columns="week", values="pct", fill_value=None)
    n_weeks  = int(df_heat["week"].max()) + 1
    wk_lbls  = [f"S{i+1}" for i in range(n_weeks)]

    z_vals   = [[pivot.get(col, {}).get(row) for col in range(n_weeks)] for row in range(7)]
    txt_vals = [
        [
            (df_heat[(df_heat["weekday"] == row) & (df_heat["week"] == col)]["label"].values[0]
             if not df_heat[(df_heat["weekday"] == row) & (df_heat["week"] == col)].empty else "")
            for col in range(n_weeks)
        ]
        for row in range(7)
    ]

    fig = go.Figure(go.Heatmap(
        z           = z_vals,
        x           = wk_lbls,
        y           = DAY_LABELS,
        colorscale  = [[0, "#F5EBD3"], [0.5, "#E2A22B"], [1, "#B0392A"]],
        zmin        = 0,
        zmax        = 100,
        text        = txt_vals,
        hovertemplate="%{text}<extra></extra>",
        showscale   = False,
        xgap        = 4,
        ygap        = 4,
    ))
    fig.update_layout(**_plotly_base(), height=220)
    fig.update_xaxes(tickfont=dict(size=9, color="#6B5536"))
    fig.update_yaxes(tickfont=dict(size=9, color="#6B5536"))
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)

    # ── Bar chart: adherence by weekday ────────────────────────────────────────
    st.markdown(ui.label("ADHERENCIA POR DÍA"), unsafe_allow_html=True)

    bar_y = [
        (adherence_by_wd[i]["done"] / adherence_by_wd[i]["total"] * 100)
        if adherence_by_wd[i]["total"] > 0 else 0
        for i in range(7)
    ]
    bar_colors = ["#B0392A", "#D2622A", "#E2A22B", "#2E8C82", "#C9456E", "#B0392A", "#D2622A"]

    fig2 = go.Figure(go.Bar(
        x            = DAY_LABELS,
        y            = bar_y,
        marker_color = bar_colors,
        marker_line  = dict(color="#2A1C10", width=2),
        text         = [f"{v:.0f}%" for v in bar_y],
        textposition = "outside",
        textfont     = dict(size=10, color="#2A1C10", family="'Space Mono', monospace"),
    ))
    fig2.update_layout(
        **_plotly_base(),
        yaxis   = dict(range=[0, 118], showticklabels=False, showgrid=False),
        xaxis   = dict(tickfont=dict(size=10, color="#6B5536")),
        height  = 200,
        showlegend=False,
        bargap  = 0.25,
    )
    st.plotly_chart(fig2, use_container_width=True, config=_PLOTLY_CFG)
