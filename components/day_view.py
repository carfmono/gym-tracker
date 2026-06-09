import streamlit as st
from datetime import date as date_type
import db
from data import WEEK_PLAN, POSTURE_ROUTINE, WEEKDAY_TO_KEY, DAY_ORDER


def badge(text: str, color: str, bg: str = None) -> str:
    bg = bg or color
    return (
        f'<span style="background:{bg};color:#fff;padding:2px 7px;border-radius:4px;'
        f'font-size:0.72em;font-weight:700;letter-spacing:.5px;">{text}</span>'
    )


def render_day_view():
    today = date_type.today()
    default_key = WEEKDAY_TO_KEY[today.weekday()]

    col_day, col_date = st.columns([1, 1])
    with col_day:
        day_options = [WEEK_PLAN[k]["name"] for k in DAY_ORDER]
        default_idx = DAY_ORDER.index(default_key)
        selected_name = st.selectbox("Día de la semana", day_options, index=default_idx)
        selected_key = DAY_ORDER[day_options.index(selected_name)]

    with col_date:
        selected_date = st.date_input("Fecha", value=today)

    date_str = selected_date.strftime("%Y-%m-%d")
    day = WEEK_PLAN[selected_key]
    accent = day["accent"]

    st.markdown(
        f'<h2 style="color:{accent};margin-top:0.5rem;">'
        f'{day["name"]} — {badge(day["tag"], accent)}</h2>',
        unsafe_allow_html=True,
    )

    # ── Botón sesión ──────────────────────────────────────────────────────────
    session_done = db.get_session(date_str)
    btn_label = "✅ Sesión completada" if session_done else "○ Marcar sesión completada"
    btn_type = "primary" if not session_done else "secondary"
    if st.button(btn_label, type=btn_type, key=f"session_{date_str}"):
        db.toggle_session(date_str)
        st.rerun()

    st.divider()

    # ── Rutina de postura ─────────────────────────────────────────────────────
    posture_state = db.get_posture_for_date(date_str)
    posture_done = sum(1 for pid in POSTURE_ROUTINE if posture_state.get(pid, False))

    with st.expander(f"⭐ Rutina de postura diaria (~8 min) — {posture_done}/{len(POSTURE_ROUTINE)}"):
        for pid, pex in POSTURE_ROUTINE.items():
            current = posture_state.get(pid, False)
            checked = st.checkbox(
                f"**{pex['name']}** — {pex['detail']}",
                value=current,
                key=f"posture_{date_str}_{pid}",
            )
            if checked != current:
                db.set_posture(date_str, pid, checked)
                st.rerun()

    st.divider()

    # ── Tarjeta del día ───────────────────────────────────────────────────────
    if day["warmup"]:
        st.markdown(f"**🔥 Calentamiento:** {day['warmup']}")

    if day["ankle"]:
        ankle_color = "#E74C3C" if "⚠️" in day["ankle"] else "#27AE60"
        st.markdown(
            f'<p style="color:{ankle_color};font-weight:600;">🦶 Tobillo: {day["ankle"]}</p>',
            unsafe_allow_html=True,
        )

    st.markdown(f"**Ejercicios — {day['name']}**")

    # ── Lista de ejercicios ───────────────────────────────────────────────────
    ex_state = db.get_exercises_for_date(date_str)

    for eid, ex in day["exercises"].items():
        current = ex_state.get(eid, False)

        badges_html = ""
        if ex.get("postura"):
            badges_html += " " + badge("⭐ POSTURA", "#E67E22")
        if ex.get("ankle"):
            ankle_tag = ex["ankle"]
            ankle_col = "#C0392B" if ankle_tag in ("PERONEO", "AQUILES") else "#7D3C98"
            badges_html += " " + badge(f"🦶 {ankle_tag}", ankle_col)

        label = f"**{ex['name']}** — {ex['detail']}"

        col_check, col_badge = st.columns([3, 1])
        with col_check:
            checked = st.checkbox(label, value=current, key=f"ex_{date_str}_{eid}")
            if checked != current:
                db.set_exercise(date_str, eid, checked)
                st.rerun()
        with col_badge:
            if badges_html:
                st.markdown(badges_html, unsafe_allow_html=True)

    # ── Cardio ────────────────────────────────────────────────────────────────
    if day["cardio"]:
        st.divider()
        st.markdown(f"**🚴 Cardio:** {day['cardio']}")
