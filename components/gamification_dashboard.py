import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import db
import gamification as gm
import ui

_PLOTLY_CFG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


def _plotly_base() -> dict:
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font         =dict(color="#2A1C10", family="'Space Mono', monospace", size=10),
        margin       =dict(l=32, r=8, t=12, b=12),
    )


_UNIT_LABELS = {
    "reps":          "REPS",
    "weight_kg":     "KG",
    "time_seconds":  "SEG",
}


def render_gamification_dashboard(profile_id: int = 1):
    try:
        uxp = db.get_user_xp(profile_id)
        if not uxp:
            db.init_user_xp(profile_id)
            uxp = db.get_user_xp(profile_id)
    except Exception:
        st.warning("No se pudo cargar el sistema de XP.")
        return

    prog = gm.xp_progress(uxp["total_xp"])

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(
        ui.logo_bar(right_html=ui.chip(f"NV. {prog['level']}", "brick")),
        unsafe_allow_html=True,
    )

    # ── Hero card: XP dial + streak ───────────────────────────────────────────
    dial_html = ui.dial_svg(
        pct        = prog["percentage"] / 100,
        label_text = "XP",
        value_str  = f"NV.{prog['level']}",
        size       = 130,
    )
    profile    = db.get_profile(profile_id) or {}
    nombre     = profile.get("name", "ENTRENADOR")

    streak     = uxp.get("current_streak", 0)
    streak_badge = ui.stamp(f"🔥×{streak}\nRACHA") if streak > 1 else ""

    hero_html = (
        f'<div class="ia-hero-card">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'{dial_html}'
        f'<div style="flex:1;">'
        f'<div style="font-family:var(--font-script);font-size:18px;color:var(--brick);">Iron Age</div>'
        f'<div style="font-family:var(--font-display);font-size:28px;line-height:0.9;'
        f'text-transform:uppercase;color:var(--ink);">{ui._e(nombre)}</div>'
        f'<div style="font-family:var(--font-mono);font-size:10px;color:var(--ink-soft);'
        f'letter-spacing:0.14em;margin-top:4px;">'
        f'{prog["xp_in_level"]:,} / {prog["xp_needed_for_next"]:,} XP</div>'
        f'<div style="margin-top:8px;">{streak_badge}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    # ── Stats row ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("XP TOTAL",   f"{uxp['total_xp']:,}")
    c2.metric("SESIONES",   uxp["total_sessions"])
    c3.metric("EJERCICIOS", uxp["total_exercises_completed"])

    # ── Weekly goals ──────────────────────────────────────────────────────────
    st.markdown(ui.label("METAS DE LA SEMANA"), unsafe_allow_html=True)

    today    = date.today()
    monday   = today - timedelta(days=today.weekday())
    wk_start = monday.isoformat()

    goals = db.get_weekly_goals(profile_id, wk_start) or {
        "sessions_goal": 4,   "exercises_goal": 30,  "posture_days_goal": 5,
        "sessions_done": 0,   "exercises_done": 0,   "posture_days_done": 0,
        "completed": False,
    }

    if goals.get("completed"):
        st.markdown(
            f'<div style="text-align:center;margin:10px 0;">{ui.stamp("SEMANA PERFECTA")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        ui.progress_bar("SESIONES",    goals["sessions_done"],      goals["sessions_goal"])
        + ui.progress_bar("EJERCICIOS",  goals["exercises_done"],     goals["exercises_goal"])
        + ui.progress_bar("POSTURA",     goals["posture_days_done"],  goals["posture_days_goal"]),
        unsafe_allow_html=True,
    )

    with st.expander("EDITAR METAS"):
        with st.form("edit_goals_form"):
            sg = st.number_input("Sesiones",    1, 7,   int(goals["sessions_goal"]))
            eg = st.number_input("Ejercicios",  1, 100, int(goals["exercises_goal"]))
            pg = st.number_input("Días postura",1, 7,   int(goals["posture_days_goal"]))
            if st.form_submit_button("GUARDAR METAS", use_container_width=True):
                db.upsert_weekly_goals(profile_id, wk_start,
                                       sessions_goal=sg, exercises_goal=eg, posture_days_goal=pg)
                st.rerun()

    # ── Personal Records ───────────────────────────────────────────────────────
    st.markdown(ui.label("RÉCORDS PERSONALES"), unsafe_allow_html=True)

    try:
        records = db.get_personal_records(profile_id)
    except Exception:
        records = []

    if records:
        for r in records[:8]:
            unit = _UNIT_LABELS.get(r.get("record_type", ""), r.get("record_type", ""))
            st.markdown(
                ui.pr_row(
                    value    = float(r["value"]),
                    unit     = unit,
                    exercise = r["exercise_name"],
                    date_str = str(r.get("date", ""))[:10],
                ),
                unsafe_allow_html=True,
            )
    else:
        st.info("Sin récords aún. Añade tu primero abajo.")

    with st.expander("NUEVO RÉCORD"):
        with st.form("add_record_form"):
            ex_name = st.text_input("Ejercicio", placeholder="Prensa de piernas máquina")
            c1r, c2r = st.columns(2)
            with c1r:
                rtype = st.selectbox("Tipo", ["weight_kg", "reps", "time_seconds"],
                                     format_func=lambda x: _UNIT_LABELS.get(x, x))
            with c2r:
                rval  = st.number_input("Valor", min_value=0.0, step=0.5)
            rdate  = st.date_input("Fecha", value=date.today())
            rnotes = st.text_input("Notas (opcional)")
            if st.form_submit_button("GUARDAR RÉCORD", use_container_width=True):
                if not ex_name.strip():
                    st.error("El nombre del ejercicio es obligatorio.")
                else:
                    try:
                        is_new = db.upsert_personal_record(
                            profile_id, ex_name.strip(), rtype, rval,
                            rdate.isoformat(), rnotes.strip(),
                        )
                        if is_new:
                            xp = gm.award_xp(profile_id, "personal_record", ex_name.strip())
                            st.success(f"¡Nuevo récord! +{xp} XP")
                            gm.check_achievements(profile_id)
                        else:
                            st.info("Actualizado (no superó el récord anterior).")
                        st.rerun()
                    except Exception:
                        st.error("Error al guardar.")

    # ── Achievements ──────────────────────────────────────────────────────────
    st.markdown(ui.label("LOGROS"), unsafe_allow_html=True)

    all_ach      = db.get_all_achievements()
    user_ach     = db.get_user_achievements(profile_id)
    unlocked_ids = {a["id"] for a in user_ach}
    unlocked_map = {a["id"]: a for a in user_ach}

    tab_on, tab_off = st.tabs(["DESBLOQUEADOS", "POR DESBLOQUEAR"])

    with tab_on:
        done = [a for a in all_ach if a["id"] in unlocked_ids]
        if not done:
            st.info("¡Empieza a entrenar para desbloquear logros!")
        else:
            badges_html = ""
            for ach in done:
                ua       = unlocked_map.get(ach["id"], {})
                fecha    = str(ua.get("unlocked_at", ""))[:10]
                badges_html += ui.ach_badge(ach["icon"], ach["name"], ach["xp_reward"], fecha)
            st.markdown(f'<div class="ach-grid">{badges_html}</div>', unsafe_allow_html=True)

    with tab_off:
        pending = [a for a in all_ach if a["id"] not in unlocked_ids]
        uxp_now = db.get_user_xp(profile_id) or {}
        state   = {
            "sessions_total":     uxp_now.get("total_sessions", 0),
            "streak_days":        uxp_now.get("current_streak", 0),
            "exercises_total":    uxp_now.get("total_exercises_completed", 0),
            "level_reached":      uxp_now.get("current_level", 1),
            "routines_completed": 0,
            "perfect_weeks":      0,
            "posture_days":       0,
        }
        badges_html = ""
        for ach in pending:
            ctype       = ach.get("condition_type")
            cval        = ach.get("condition_value") or 1
            current_val = state.get(ctype, 0) if ctype else 0
            pct         = min(100, int(current_val / cval * 100)) if cval else 0
            detail      = f"{current_val}/{cval}"
            badges_html += (
                f'<div class="ach-badge locked">'
                f'<div class="ab-icon">{ach["icon"]}</div>'
                f'<div class="ab-name">{ui._e(ach["name"])}</div>'
                f'<div class="ab-xp">+{ach["xp_reward"]} XP</div>'
                f'<div class="ab-date">{detail}</div>'
                f'</div>'
            )
        st.markdown(f'<div class="ach-grid">{badges_html}</div>', unsafe_allow_html=True)

    # ── XP history chart ──────────────────────────────────────────────────────
    st.markdown(ui.label("XP ACUMULADO — 30 DÍAS"), unsafe_allow_html=True)

    days30 = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    try:
        with db.get_connection() as conn:
            rows = db._fetch_all(
                conn,
                """SELECT DATE(created_at) AS day, SUM(xp_gained) AS xp
                   FROM xp_log WHERE profile_id=%s AND created_at >= NOW() - INTERVAL '30 days'
                   GROUP BY DATE(created_at) ORDER BY day""",
                (profile_id,),
            )
        day_xp = {str(r["day"]): r["xp"] for r in rows}
    except Exception:
        day_xp = {}

    cumulative, total = [], 0
    for d in days30:
        total += day_xp.get(d, 0)
        cumulative.append(total)

    if any(v > 0 for v in cumulative):
        fig = go.Figure(go.Scatter(
            x=days30, y=cumulative,
            mode="lines+markers",
            line=dict(color="#B0392A", width=2.5),
            marker=dict(size=5, color="#B0392A", line=dict(color="#2A1C10", width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(226,162,43,0.15)",
        ))
        fig.update_layout(
            **_plotly_base(),
            height=190,
            xaxis=dict(tickangle=-45, tickfont=dict(size=8, color="#6B5536")),
            yaxis=dict(tickfont=dict(size=8, color="#6B5536"), gridcolor="rgba(42,28,16,0.1)"),
        )
        st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
    else:
        st.info("Completa tu primera sesión para ver el historial de XP.")

    # ── XP log ────────────────────────────────────────────────────────────────
    with st.expander("ÚLTIMOS EVENTOS XP"):
        try:
            logs = db.get_xp_log(profile_id, 15)
            if logs:
                rows_html = ""
                for i, log in enumerate(logs, 1):
                    rows_html += ui.ticket_row(
                        num    = f"+{log['xp_gained']}",
                        name   = str(log.get("event_type", "")).replace("_", " ").upper(),
                        detail = str(log.get("created_at", ""))[:16],
                        done   = True,
                    )
                st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)
            else:
                st.caption("Sin eventos aún.")
        except Exception:
            st.caption("Sin eventos.")
