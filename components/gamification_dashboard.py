import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import db
import gamification as gm

PLOTLY_CFG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}
PLOTLY_BASE = dict(
    paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
    font=dict(color="#FAFAFA", size=12),
    margin=dict(l=36, r=12, t=16, b=16),
)


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

    # ── Sección 1: Perfil del jugador ─────────────────────────────────────────
    profile = db.get_profile(profile_id) or {}
    nombre = profile.get("name", "Entrenador")

    st.markdown(
        f"<div style='text-align:center;padding:1rem 0 0.5rem;'>"
        f"<div style='font-size:3.5rem;line-height:1;'>{prog['avatar']}</div>"
        f"<div style='font-size:1.4rem;font-weight:700;margin-top:4px;'>{nombre}</div>"
        f"<div style='color:#2980B9;font-size:1rem;'>Nivel {prog['level']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    pct = prog["percentage"]
    st.progress(pct / 100)
    st.caption(
        f"{prog['xp_in_level']:,} / {prog['xp_needed_for_next']:,} XP "
        f"para nivel {prog['level'] + 1}  ·  Total: {prog['total_xp']:,} XP"
    )

    c1, c2 = st.columns(2)
    c1.metric("⚡ XP Total", f"{uxp['total_xp']:,}")
    c2.metric("🔥 Racha actual", f"{uxp['current_streak']} días")

    c3, c4 = st.columns(2)
    c3.metric("🏋️ Sesiones", uxp["total_sessions"])
    c4.metric("💥 Ejercicios", uxp["total_exercises_completed"])

    st.divider()

    # ── Sección 2: Metas de la semana ─────────────────────────────────────────
    st.subheader("📅 Metas de esta semana")

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.isoformat()

    goals = db.get_weekly_goals(profile_id, week_start) or {
        "sessions_goal": 4, "exercises_goal": 30, "posture_days_goal": 5,
        "sessions_done": 0, "exercises_done": 0, "posture_days_done": 0,
        "completed": False,
    }

    if goals.get("completed"):
        st.success("⭐ ¡SEMANA PERFECTA! Todas las metas cumplidas.")

    with st.expander("✏️ Editar metas"):
        with st.form("edit_goals_form"):
            sg = st.number_input("Sesiones", 1, 7, int(goals["sessions_goal"]))
            eg = st.number_input("Ejercicios", 1, 100, int(goals["exercises_goal"]))
            pg = st.number_input("Días de postura", 1, 7, int(goals["posture_days_goal"]))
            if st.form_submit_button("Guardar metas", use_container_width=True):
                db.upsert_weekly_goals(profile_id, week_start,
                                       sessions_goal=sg, exercises_goal=eg, posture_days_goal=pg)
                st.rerun()

    def _prog_bar(label, done, goal):
        pct = min(1.0, done / goal) if goal else 0
        color = "#27AE60" if pct >= 1.0 else "#2980B9"
        st.markdown(
            f"**{label}** — {done}/{goal}  \n"
            f"<div style='background:#1C2833;border-radius:6px;height:12px;'>"
            f"<div style='background:{color};width:{pct*100:.0f}%;height:12px;border-radius:6px;'></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    _prog_bar("🏋️ Sesiones",  goals["sessions_done"],      goals["sessions_goal"])
    _prog_bar("💥 Ejercicios", goals["exercises_done"],     goals["exercises_goal"])
    _prog_bar("⭐ Días postura", goals["posture_days_done"], goals["posture_days_goal"])

    st.divider()

    # ── Sección 3: Logros ─────────────────────────────────────────────────────
    st.subheader("🏆 Logros")

    all_ach  = db.get_all_achievements()
    user_ach = db.get_user_achievements(profile_id)
    unlocked_ids = {a["id"] for a in user_ach}
    unlocked_map = {a["id"]: a for a in user_ach}

    tab_on, tab_off = st.tabs(["✅ Desbloqueados", "🔒 Por desbloquear"])

    with tab_on:
        done = [a for a in all_ach if a["id"] in unlocked_ids]
        if not done:
            st.info("Aún no has desbloqueado ningún logro. ¡Empieza a entrenar!")
        else:
            cols = st.columns(2)
            for i, ach in enumerate(done):
                ua = unlocked_map.get(ach["id"], {})
                fecha = str(ua.get("unlocked_at", ""))[:10] if ua else ""
                with cols[i % 2]:
                    st.markdown(
                        f"<div style='background:#1C2833;border-radius:8px;padding:10px;margin-bottom:8px;'>"
                        f"<div style='font-size:1.5rem;'>{ach['icon']}</div>"
                        f"<div style='font-weight:700;font-size:0.85rem;'>{ach['name']}</div>"
                        f"<div style='font-size:0.7rem;color:#888;'>{fecha}</div>"
                        f"<div style='color:#F39C12;font-size:0.75rem;'>+{ach['xp_reward']} XP</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    with tab_off:
        pending = [a for a in all_ach if a["id"] not in unlocked_ids]
        uxp_now = db.get_user_xp(profile_id) or {}
        state = {
            "sessions_total":     uxp_now.get("total_sessions", 0),
            "streak_days":        uxp_now.get("current_streak", 0),
            "exercises_total":    uxp_now.get("total_exercises_completed", 0),
            "level_reached":      uxp_now.get("current_level", 1),
            "routines_completed": 0,
            "perfect_weeks":      0,
            "posture_days":       0,
        }
        cols = st.columns(2)
        for i, ach in enumerate(pending):
            ctype = ach["condition_type"]
            cval  = ach["condition_value"] or 1
            current_val = state.get(ctype, 0) if ctype else 0
            pct = min(100, int(current_val / cval * 100)) if cval else 0
            with cols[i % 2]:
                st.markdown(
                    f"<div style='background:#161b22;border-radius:8px;padding:10px;"
                    f"margin-bottom:8px;opacity:0.7;'>"
                    f"<div style='font-size:1.5rem;filter:grayscale(1);'>{ach['icon']}</div>"
                    f"<div style='font-weight:700;font-size:0.85rem;color:#888;'>{ach['name']}</div>"
                    f"<div style='font-size:0.7rem;color:#555;'>{current_val}/{cval}</div>"
                    f"<div style='background:#222;border-radius:4px;height:6px;margin-top:4px;'>"
                    f"<div style='background:#2980B9;width:{pct}%;height:6px;border-radius:4px;'></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Sección 4: Historial XP ───────────────────────────────────────────────
    st.subheader("📈 XP acumulado (30 días)")

    today = date.today()
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
            x=days30, y=cumulative, mode="lines+markers",
            line=dict(color="#2980B9", width=2),
            marker=dict(size=4),
            fill="tozeroy", fillcolor="rgba(41,128,185,0.15)",
        ))
        fig.update_layout(**PLOTLY_BASE, height=200,
                          xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
                          yaxis=dict(tickfont=dict(size=9)))
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    else:
        st.info("Aún no hay XP registrado. ¡Completa tu primera sesión!")

    st.subheader("📋 Últimos eventos")
    try:
        logs = db.get_xp_log(profile_id, 20)
        if logs:
            df = pd.DataFrame(logs)[["event_type", "description", "xp_gained", "created_at"]]
            df.columns = ["Evento", "Descripción", "XP", "Fecha"]
            df["Fecha"] = df["Fecha"].astype(str).str[:16]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("Sin eventos aún.")
    except Exception:
        st.caption("Sin eventos.")

    st.divider()

    # ── Sección 5: Records personales ─────────────────────────────────────────
    st.subheader("🏅 Records personales")

    try:
        records = db.get_personal_records(profile_id)
    except Exception:
        records = []

    if records:
        df_r = pd.DataFrame(records)[["exercise_name", "record_type", "value", "date", "notes"]]
        df_r.columns = ["Ejercicio", "Tipo", "Valor", "Fecha", "Notas"]
        st.dataframe(df_r, use_container_width=True, hide_index=True)
    else:
        st.info("Sin records aún. Agrega tu primero abajo.")

    with st.form("add_record_form"):
        st.markdown("**Nuevo record**")
        ex_name = st.text_input("Ejercicio", placeholder="Prensa de piernas máquina")
        c1, c2 = st.columns(2)
        with c1:
            rtype = st.selectbox("Tipo", ["reps", "weight_kg", "time_seconds"])
        with c2:
            rval = st.number_input("Valor", min_value=0.0, step=0.5)
        rdate = st.date_input("Fecha", value=date.today())
        rnotes = st.text_input("Notas (opcional)")

        if st.form_submit_button("💾 Guardar record", use_container_width=True):
            if not ex_name.strip():
                st.error("El nombre del ejercicio es obligatorio.")
            else:
                try:
                    is_new = db.upsert_personal_record(
                        profile_id, ex_name.strip(), rtype, rval,
                        rdate.isoformat(), rnotes.strip()
                    )
                    if is_new:
                        award_xp = gm.award_xp(profile_id, "personal_record", ex_name.strip())
                        st.success(f"🏅 ¡Nuevo record! +{award_xp} XP")
                        gm.check_achievements(profile_id)
                    else:
                        st.info("Record actualizado (no superó el anterior).")
                    st.rerun()
                except Exception:
                    st.error("Error al guardar el record.")
