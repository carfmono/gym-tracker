import streamlit as st
from datetime import date as date_type
import psycopg2
import db
import gamification as gm
from data import WEEK_PLAN, POSTURE_ROUTINE, WEEKDAY_TO_KEY, DAY_ORDER

_DB_ERROR = "Error de conexión. Recarga la página."
PROFILE_ID = 1


def _award_exercise(eid: str, ex: dict, date_str: str):
    if ex.get("ankle"):
        event = "ankle_exercise_complete"
    elif ex.get("postura"):
        event = "posture_exercise_complete"
    else:
        event = "exercise_complete"
    try:
        gm.award_xp(PROFILE_ID, event, f"{date_str}:{eid}", idempotent=True)
        gm.update_weekly_goals(PROFILE_ID)
    except Exception:
        pass


def render_day_view():
    today = date_type.today()
    default_key = WEEKDAY_TO_KEY[today.weekday()]

    # ── Mini barra de XP ──────────────────────────────────────────────────────
    try:
        uxp = db.get_user_xp(PROFILE_ID)
        if uxp:
            prog = gm.xp_progress(uxp["total_xp"])
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
                f"<span style='font-size:1.2rem;'>{prog['avatar']}</span>"
                f"<span style='font-weight:700;color:#2980B9;'>Nv.{prog['level']}</span>"
                f"<div style='flex:1;background:#1C2833;border-radius:4px;height:8px;'>"
                f"<div style='background:#2980B9;width:{prog['percentage']}%;height:8px;"
                f"border-radius:4px;'></div></div>"
                f"<span style='font-size:0.75rem;color:#888;'>{prog['xp_in_level']}/{prog['xp_needed_for_next']} XP</span>"
                f"{'🔥×'+str(uxp['current_streak']) if uxp['current_streak'] > 1 else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Notificaciones de achievements ───────────────────────────────────────
    new_ach = st.session_state.pop("new_achievements", [])
    for ach in new_ach:
        st.balloons()
        st.success(f"{ach['icon']} **¡Logro desbloqueado!** {ach['name']} — +{ach['xp_reward']} XP")

    streak_result = st.session_state.pop("streak_result", None)
    if streak_result and streak_result.get("bonus_event"):
        st.info(f"🔥 ¡Racha de {streak_result['streak']} días!")

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
            if not session_done:  # se está marcando como completada
                xp = gm.award_xp(PROFILE_ID, "session_complete", date_str, idempotent=True)
                streak_res = gm.update_streak(PROFILE_ID, selected_date)
                gm.update_weekly_goals(PROFILE_ID)
                new_achievements = gm.check_achievements(PROFILE_ID)
                if new_achievements:
                    st.session_state["new_achievements"] = new_achievements
                if streak_res.get("bonus_event"):
                    st.session_state["streak_result"] = streak_res
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
                    if checked:
                        gm.award_xp(PROFILE_ID, "posture_exercise_complete",
                                    f"{date_str}:{pid}", idempotent=True)
                        # Si se completaron los 5
                        new_state = db.get_posture_for_date(date_str)
                        if sum(1 for p in POSTURE_ROUTINE if new_state.get(p, False)) == len(POSTURE_ROUTINE):
                            gm.award_xp(PROFILE_ID, "posture_full_day", date_str, idempotent=True)
                        gm.update_weekly_goals(PROFILE_ID)
                        new_ach = gm.check_achievements(PROFILE_ID)
                        if new_ach:
                            st.session_state["new_achievements"] = new_ach
                except psycopg2.DatabaseError:
                    st.error(_DB_ERROR)
                st.rerun()

    st.divider()

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

        checked = st.checkbox(ex["name"], value=current, key=f"ex_{date_str}_{eid}")
        st.caption("  ·  ".join(sub_parts))

        if checked != current:
            try:
                db.set_exercise(date_str, eid, checked)
                if checked:
                    _award_exercise(eid, ex, date_str)
                    new_ach = gm.check_achievements(PROFILE_ID)
                    if new_ach:
                        st.session_state["new_achievements"] = new_ach
            except psycopg2.DatabaseError:
                st.error(_DB_ERROR)
            st.rerun()

    if day["cardio"]:
        st.divider()
        st.markdown(f"**🚴 Cardio:** {day['cardio']}")
