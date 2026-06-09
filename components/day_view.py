import streamlit as st
from datetime import date as date_type
import psycopg2
import db
from data import WEEK_PLAN, POSTURE_ROUTINE, WEEKDAY_TO_KEY, DAY_ORDER

ANKLE_COLORS = {"PERONEO": "#C0392B", "AQUILES": "#A93226"}

_DB_ERROR = "Error de conexión. Recarga la página."


def render_day_view():
    today = date_type.today()
    default_key = WEEKDAY_TO_KEY[today.weekday()]

    col_day, col_date = st.columns(2)
    with col_day:
        day_options = [WEEK_PLAN[k]["name"] for k in DAY_ORDER]
        default_idx = DAY_ORDER.index(default_key)
        selected_name = st.selectbox("Día", day_options, index=default_idx)
        selected_key = DAY_ORDER[day_options.index(selected_name)]
    with col_date:
        selected_date = st.date_input("Fecha", value=today)

    date_str = selected_date.strftime("%Y-%m-%d")
    day = WEEK_PLAN[selected_key]
    accent = day["accent"]

    st.markdown(
        f'<h2 style="color:{accent};margin:0.4rem 0 0.2rem;">'
        f'{day["name"]} &nbsp;'
        f'<span style="background:{accent};color:#fff;padding:2px 9px;border-radius:5px;'
        f'font-size:0.6em;font-weight:700;vertical-align:middle;">{day["tag"]}</span>'
        f'</h2>',
        unsafe_allow_html=True,
    )

    # ── Botón sesión ──────────────────────────────────────────────────────────
    try:
        session_done = db.get_session(date_str)
    except psycopg2.DatabaseError:
        st.error(_DB_ERROR)
        return

    btn_label = "✅ Sesión completada" if session_done else "○  Marcar sesión completada"
    btn_type = "secondary" if session_done else "primary"
    if st.button(btn_label, type=btn_type, key=f"session_{date_str}", use_container_width=True):
        try:
            db.toggle_session(date_str)
        except psycopg2.DatabaseError:
            st.error(_DB_ERROR)
        st.rerun()

    st.divider()

    # ── Rutina de postura ─────────────────────────────────────────────────────
    try:
        posture_state = db.get_posture_for_date(date_str)
    except psycopg2.DatabaseError:
        st.error(_DB_ERROR)
        return

    posture_done = sum(1 for pid in POSTURE_ROUTINE if posture_state.get(pid, False))

    with st.expander(f"⭐ Postura diaria — {posture_done}/{len(POSTURE_ROUTINE)}"):
        for pid, pex in POSTURE_ROUTINE.items():
            current = posture_state.get(pid, False)
            checked = st.checkbox(
                pex["name"],
                value=current,
                key=f"posture_{date_str}_{pid}",
            )
            st.caption(pex["detail"])
            if checked != current:
                try:
                    db.set_posture(date_str, pid, checked)
                except psycopg2.DatabaseError:
                    st.error(_DB_ERROR)
                st.rerun()

    st.divider()

    # ── Tarjeta del día ───────────────────────────────────────────────────────
    if day["warmup"]:
        st.markdown(f"**🔥** {day['warmup']}")

    if day["ankle"]:
        ankle_color = "#E74C3C" if "⚠️" in day["ankle"] else "#27AE60"
        st.markdown(
            f'<p style="color:{ankle_color};font-weight:600;margin:0.3rem 0;">🦶 {day["ankle"]}</p>',
            unsafe_allow_html=True,
        )

    st.markdown("**Ejercicios**")

    # ── Lista de ejercicios ───────────────────────────────────────────────────
    try:
        ex_state = db.get_exercises_for_date(date_str)
    except psycopg2.DatabaseError:
        st.error(_DB_ERROR)
        return

    for eid, ex in day["exercises"].items():
        current = ex_state.get(eid, False)

        sub_parts = [ex["detail"]]
        if ex.get("postura"):
            sub_parts.append("⭐ POSTURA")
        if ex.get("ankle"):
            sub_parts.append(f"🦶 {ex['ankle']}")

        checked = st.checkbox(
            ex["name"],
            value=current,
            key=f"ex_{date_str}_{eid}",
        )
        st.caption("  ·  ".join(sub_parts))

        if checked != current:
            try:
                db.set_exercise(date_str, eid, checked)
            except psycopg2.DatabaseError:
                st.error(_DB_ERROR)
            st.rerun()

    # ── Cardio ────────────────────────────────────────────────────────────────
    if day["cardio"]:
        st.divider()
        st.markdown(f"**🚴 Cardio:** {day['cardio']}")
