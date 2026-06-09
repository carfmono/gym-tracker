import streamlit as st
from datetime import date as date_type
import psycopg2
import db
import gamification as gm
import ui
from data import WEEK_PLAN, POSTURE_ROUTINE, WEEKDAY_TO_KEY, DAY_ORDER

_DB_ERROR = "Error de conexión. Recarga la página."
PROFILE_ID = 1

DAY_LABELS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]


def _award_exercise(eid: str, ex: dict, date_str: str):
    event = (
        "ankle_exercise_complete" if ex.get("ankle")
        else "posture_exercise_complete" if ex.get("postura")
        else "exercise_complete"
    )
    try:
        gm.award_xp(PROFILE_ID, event, f"{date_str}:{eid}", idempotent=True)
        gm.update_weekly_goals(PROFILE_ID)
    except Exception:
        pass


def render_day_view():
    today = date_type.today()
    default_key = WEEKDAY_TO_KEY[today.weekday()]

    # ── Logo bar ───────────────────────────────────────────────────────────────
    try:
        uxp  = db.get_user_xp(PROFILE_ID)
        prog = gm.xp_progress(uxp["total_xp"]) if uxp else None
    except Exception:
        uxp = prog = None

    if prog and uxp:
        xp_badge = ui.xp_strip(
            prog["level"],
            prog["percentage"],
            f"{prog['xp_in_level']}/{prog['xp_needed_for_next']} XP",
            uxp.get("current_streak", 0),
        )
        st.markdown(xp_badge, unsafe_allow_html=True)

    # ── Notifications ─────────────────────────────────────────────────────────
    for ach in st.session_state.pop("new_achievements", []):
        st.balloons()
        st.success(f"{ach['icon']} **¡Logro desbloqueado!** {ach['name']} — +{ach['xp_reward']} XP")

    streak_result = st.session_state.pop("streak_result", None)
    if streak_result and streak_result.get("bonus_event"):
        st.info(f"🔥 ¡Racha de {streak_result['streak']} días!")

    # ── Day / date selectors ──────────────────────────────────────────────────
    col_day, col_date = st.columns(2)
    with col_day:
        day_options  = [WEEK_PLAN[k]["name"] for k in DAY_ORDER]
        default_idx  = DAY_ORDER.index(default_key)
        selected_name = st.selectbox("Día", day_options, index=default_idx, label_visibility="collapsed")
        selected_key  = DAY_ORDER[day_options.index(selected_name)]
    with col_date:
        selected_date = st.date_input("Fecha", value=today, label_visibility="collapsed")

    date_str = selected_date.strftime("%Y-%m-%d")
    day      = WEEK_PLAN[selected_key]

    # ── Screen header ─────────────────────────────────────────────────────────
    tag_html = ui.chip(day["tag"], "brick")
    st.markdown(
        ui.screen_header(
            selected_date.strftime("%d %b %Y").upper(),
            day["name"].upper(),
            badge_html=tag_html,
        ),
        unsafe_allow_html=True,
    )

    # ── Session complete button ───────────────────────────────────────────────
    try:
        session_done = db.get_session(date_str)
    except psycopg2.DatabaseError:
        st.error(_DB_ERROR)
        return

    # Hero card with session status + dial
    try:
        ex_state_hero = db.get_exercises_for_date(date_str)
    except psycopg2.DatabaseError:
        ex_state_hero = {}

    n_total = len(day["exercises"])
    n_done  = sum(1 for eid in day["exercises"] if ex_state_hero.get(eid, False))
    pct_ex  = n_done / n_total if n_total else 0.0

    dial_html  = ui.dial_svg(pct_ex, "EJERCS", f"{n_done}/{n_total}", size=120)
    stamp_html = (ui.stamp("COMPLETADO") if session_done else "") + (
        ui.stamp("NUEVO RÉCORD") if st.session_state.pop("show_pr_stamp", False) else ""
    )

    warmup_line = f'<div style="font-family:var(--font-mono);font-size:10px;color:var(--ink-soft);letter-spacing:0.08em;margin-bottom:4px;">🔥 {day.get("warmup","")}</div>' if day.get("warmup") else ""
    ankle_line  = f'<div style="font-family:var(--font-mono);font-size:10px;color:var(--orange);letter-spacing:0.08em;margin-bottom:4px;">🦶 {day.get("ankle","")}</div>' if day.get("ankle") else ""

    hero_body = (
        f'<div class="ia-hero-card">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'{dial_html}'
        f'<div style="flex:1;">'
        f'{warmup_line}{ankle_line}'
        f'<div style="font-family:var(--font-display);font-size:28px;line-height:0.9;text-transform:uppercase;color:var(--ink);">'
        f'{n_done}<span style="font-size:14px;color:var(--ink-soft);">/{n_total}</span></div>'
        f'<div style="font-family:var(--font-mono);font-size:9px;color:var(--ink-soft);letter-spacing:0.14em;text-transform:uppercase;">EJERCICIOS HOY</div>'
        f'<div style="margin-top:8px;">{stamp_html}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero_body, unsafe_allow_html=True)

    btn_label = "✓ SESIÓN COMPLETADA" if session_done else "MARCAR SESIÓN COMPLETADA"
    btn_type  = "secondary" if session_done else "primary"
    if st.button(btn_label, type=btn_type, key=f"session_{date_str}", use_container_width=True):
        try:
            db.toggle_session(date_str)
            if not session_done:
                gm.award_xp(PROFILE_ID, "session_complete", date_str, idempotent=True)
                streak_res = gm.update_streak(PROFILE_ID, selected_date)
                gm.update_weekly_goals(PROFILE_ID)
                new_achs   = gm.check_achievements(PROFILE_ID)
                if new_achs:
                    st.session_state["new_achievements"] = new_achs
                if streak_res.get("bonus_event"):
                    st.session_state["streak_result"] = streak_res
        except psycopg2.DatabaseError:
            st.error(_DB_ERROR)
        st.rerun()

    # ── Posture routine ───────────────────────────────────────────────────────
    try:
        posture_state = db.get_posture_for_date(date_str)
    except psycopg2.DatabaseError:
        st.error(_DB_ERROR)
        return

    posture_done = sum(1 for pid in POSTURE_ROUTINE if posture_state.get(pid, False))

    with st.expander(f"POSTURA DIARIA — {posture_done}/{len(POSTURE_ROUTINE)}"):
        for pid, pex in POSTURE_ROUTINE.items():
            current = posture_state.get(pid, False)
            checked = st.checkbox(pex["name"], value=current, key=f"posture_{date_str}_{pid}")
            st.caption(pex["detail"])
            if checked != current:
                try:
                    db.set_posture(date_str, pid, checked)
                    if checked:
                        gm.award_xp(PROFILE_ID, "posture_exercise_complete",
                                    f"{date_str}:{pid}", idempotent=True)
                        new_s = db.get_posture_for_date(date_str)
                        if sum(1 for p in POSTURE_ROUTINE if new_s.get(p, False)) == len(POSTURE_ROUTINE):
                            gm.award_xp(PROFILE_ID, "posture_full_day", date_str, idempotent=True)
                        gm.update_weekly_goals(PROFILE_ID)
                        new_ach = gm.check_achievements(PROFILE_ID)
                        if new_ach:
                            st.session_state["new_achievements"] = new_ach
                except psycopg2.DatabaseError:
                    st.error(_DB_ERROR)
                st.rerun()

    # ── Week attendance boxes ─────────────────────────────────────────────────
    from datetime import timedelta
    monday     = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    try:
        stats_week = db.get_stats_for_dates([d.strftime("%Y-%m-%d") for d in week_dates])
        sess_map   = stats_week.get("sessions", {})
    except Exception:
        sess_map = {}

    boxes_data = [
        {
            "label": DAY_LABELS[i],
            "done":  bool(sess_map.get(d.strftime("%Y-%m-%d"))),
            "today": d == today,
        }
        for i, d in enumerate(week_dates)
    ]
    st.markdown(ui.label("SEMANA ACTUAL") + ui.week_boxes(boxes_data), unsafe_allow_html=True)

    # ── Exercise list ─────────────────────────────────────────────────────────
    st.markdown(ui.label("EJERCICIOS"), unsafe_allow_html=True)

    try:
        ex_state = db.get_exercises_for_date(date_str)
    except psycopg2.DatabaseError:
        st.error(_DB_ERROR)
        return

    rows_html = ""
    for i, (eid, ex) in enumerate(day["exercises"].items(), 1):
        current  = ex_state.get(eid, False)
        sub_tags = []
        if ex.get("postura"): sub_tags.append("POSTURA")
        if ex.get("ankle"):   sub_tags.append("TOBILLO")
        chips_in_detail = " ".join(
            f'<span class="ia-chip teal" style="font-size:8px;padding:1px 5px;">{t}</span>'
            for t in sub_tags
        )
        rows_html += ui.ticket_row(i, ex["name"], ex["detail"], done=current, chips_html=chips_in_detail)

    st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)

    # Checkbox area for toggling (hidden visually, functional)
    for eid, ex in day["exercises"].items():
        current = ex_state.get(eid, False)
        checked = st.checkbox(
            ex["name"], value=current, key=f"ex_{date_str}_{eid}",
            label_visibility="collapsed",
        )
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

    if day.get("cardio"):
        st.markdown(
            f'<div class="ia-card" style="margin-top:10px;">'
            f'<div class="ia-mono-row">CARDIO</div>'
            f'<div style="font-family:var(--font-body);font-weight:700;font-size:15px;color:var(--ink);text-transform:uppercase;">{day["cardio"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
