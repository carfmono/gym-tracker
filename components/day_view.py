import streamlit as st
from datetime import date as date_type, timedelta
import db
import gamification as gm
import ui
from data import POSTURE_ROUTINE

_PR_TYPES = {"weight_kg": "KG", "reps": "REPS", "time_seconds": "SEG"}

_DB_ERROR = "Error de conexión. Recarga la página."

DAY_LABELS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]


def _award_exercise(profile_id: int, eid: str, ex: dict, date_str: str):
    event = (
        "ankle_exercise_complete" if ex.get("is_ankle")
        else "posture_exercise_complete" if ex.get("is_posture")
        else "exercise_complete"
    )
    try:
        gm.award_xp(profile_id, event, f"{date_str}:{eid}", idempotent=True)
        gm.update_weekly_goals(profile_id)
    except Exception:
        pass


def _render_posture(date_str: str, profile_id: int):
    try:
        posture_state = db.get_posture_for_date(date_str, profile_id)
    except Exception:
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
                    db.set_posture(date_str, pid, checked, profile_id)
                    if checked:
                        gm.award_xp(profile_id, "posture_exercise_complete",
                                    f"{date_str}:{pid}", idempotent=True)
                        new_s = db.get_posture_for_date(date_str, profile_id)
                        if sum(1 for p in POSTURE_ROUTINE if new_s.get(p, False)) == len(POSTURE_ROUTINE):
                            gm.award_xp(profile_id, "posture_full_day", date_str, idempotent=True)
                        gm.update_weekly_goals(profile_id)
                        new_ach = gm.check_achievements(profile_id)
                        if new_ach:
                            st.session_state["new_achievements"] = new_ach
                except Exception:
                    st.error(_DB_ERROR)
                st.rerun()


def _render_week_boxes(today: date_type, profile_id: int):
    monday     = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    try:
        stats_week = db.get_stats_for_dates(
            [d.strftime("%Y-%m-%d") for d in week_dates], profile_id
        )
        sess_map = stats_week.get("sessions", {})
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


def render_day_view():
    profile_id = st.session_state.profile_id
    today      = date_type.today()

    # ── XP strip ──────────────────────────────────────────────────────────────
    try:
        uxp  = db.get_user_xp(profile_id)
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

    # ── Active routine ────────────────────────────────────────────────────────
    try:
        active = db.get_active_routine(profile_id)
    except Exception:
        st.error(_DB_ERROR)
        return

    selected_date = st.date_input("Fecha", value=today, label_visibility="collapsed")
    date_str      = selected_date.strftime("%Y-%m-%d")

    # Limpiar override al cambiar de fecha
    if st.session_state.get("last_date") != date_str:
        st.session_state.pop("day_override", None)
        st.session_state.last_date = date_str

    if not active:
        st.markdown(
            ui.screen_header(selected_date.strftime("%d %b %Y").upper(), "SIN RUTINA"),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ia-card" style="text-align:center;padding:24px;">'
            '<div style="font-family:var(--font-display);font-size:22px;text-transform:uppercase;'
            'color:var(--ink);margin-bottom:8px;">Activa una rutina</div>'
            '<div style="font-family:var(--font-body);font-size:13px;color:var(--ink-soft);">'
            'Activa una rutina en ENTRENOS para comenzar tu entrenamiento.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.link_button("IR A ENTRENOS ⚡", "?tab=entrenos", use_container_width=True)
        _render_posture(date_str, profile_id)
        _render_week_boxes(today, profile_id)
        return

    try:
        routine_days = db.get_routine_days(active["id"])
    except Exception:
        st.error(_DB_ERROR)
        return

    day_names = [d["day_name"] for d in routine_days]
    if not day_names:
        st.warning("La rutina activa no tiene días configurados. Reactívala desde la biblioteca.")
        _render_posture(date_str, profile_id)
        _render_week_boxes(today, profile_id)
        return

    # ── Day selector + swap (cambio de grupo muscular) ────────────────────────
    suggested_idx = today.weekday() % len(day_names)

    col_day, col_swap = st.columns([3, 1])
    with col_day:
        selected_day = st.selectbox("Día de entrenamiento", day_names,
                                    index=suggested_idx, key="day_selector",
                                    label_visibility="collapsed")
    with col_swap:
        if st.button("↕ CAMBIAR", use_container_width=True):
            st.session_state.show_swap = not st.session_state.get("show_swap", False)
            st.rerun()

    if st.session_state.get("show_swap"):
        swap_options = [d for d in day_names if d != selected_day]
        if swap_options:
            override = st.selectbox("Elegir grupo muscular para hoy",
                                    swap_options, key="swap_selector")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("CONFIRMAR", type="primary", use_container_width=True):
                    st.session_state.day_override = override
                    st.session_state.show_swap = False
                    st.rerun()
            with c2:
                if st.button("CANCELAR", use_container_width=True):
                    st.session_state.show_swap = False
                    st.rerun()

    final_day = st.session_state.get("day_override", selected_day)

    day_info     = next((d for d in routine_days if d["day_name"] == final_day), {})
    session_type = (day_info.get("session_type") or "").upper()

    # ── Screen header ─────────────────────────────────────────────────────────
    badge = ui.chip(session_type, "brick") if session_type else ""
    if st.session_state.get("day_override"):
        badge += ui.chip("DÍA CAMBIADO", "teal")
    st.markdown(
        ui.screen_header(
            f"{selected_date.strftime('%d %b %Y').upper()} · {active['name'].upper()}",
            final_day.upper(),
            badge_html=badge,
        ),
        unsafe_allow_html=True,
    )

    # ── Exercises for the day ─────────────────────────────────────────────────
    try:
        exercises = db.get_exercises_for_routine_day(active["id"], final_day)
    except Exception:
        st.error(_DB_ERROR)
        return

    exercises = [{**ex, "eid": f"tex-{ex['id']}"} for ex in exercises]

    try:
        session_done = db.get_session(date_str, profile_id)
        ex_state     = db.get_exercises_for_date(date_str, profile_id)
    except Exception:
        st.error(_DB_ERROR)
        return

    n_total = len(exercises)
    n_done  = sum(1 for ex in exercises if ex_state.get(ex["eid"], False))
    pct_ex  = n_done / n_total if n_total else 0.0

    dial_html  = ui.dial_svg(pct_ex, "EJERCS", f"{n_done}/{n_total}", size=120)
    stamp_html = (ui.stamp("COMPLETADO") if session_done else "") + (
        ui.stamp("NUEVO RÉCORD") if st.session_state.pop("show_pr_stamp", False) else ""
    )

    hero_body = (
        f'<div class="ia-hero-card">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'{dial_html}'
        f'<div style="flex:1;">'
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
            db.toggle_session(date_str, profile_id)
            if not session_done:
                gm.award_xp(profile_id, "session_complete", date_str, idempotent=True)
                streak_res = gm.update_streak(profile_id, selected_date)
                gm.update_weekly_goals(profile_id)
                new_achs   = gm.check_achievements(profile_id)
                if new_achs:
                    st.session_state["new_achievements"] = new_achs
                if streak_res.get("bonus_event"):
                    st.session_state["streak_result"] = streak_res
        except Exception:
            st.error(_DB_ERROR)
        st.rerun()

    # ── Posture routine ───────────────────────────────────────────────────────
    _render_posture(date_str, profile_id)

    # ── Week attendance boxes ─────────────────────────────────────────────────
    _render_week_boxes(today, profile_id)

    # ── Exercise list ─────────────────────────────────────────────────────────
    st.markdown(ui.label("EJERCICIOS"), unsafe_allow_html=True)

    if not exercises:
        st.info("Esta rutina no tiene ejercicios cargados para este día.")
        return

    for i, ex in enumerate(exercises, 1):
        eid     = ex["eid"]
        current = ex_state.get(eid, False)

        tags    = ("⭐" if ex.get("is_posture") else "") + (" 🦶" if ex.get("is_ankle") else "")
        detail  = f"{ex.get('sets', '?')}×{ex.get('reps', '?')}"

        col_chk, col_det = st.columns([3, 1])
        with col_chk:
            checked = st.checkbox(
                f"{i}. {ex['exercise_name']}{(' ' + tags.strip()) if tags.strip() else ''}",
                value=current,
                key=f"ex_{date_str}_{eid}",
            )
        with col_det:
            st.markdown(
                f'<div style="text-align:right;padding-top:13px;'
                f'font-family:var(--font-mono);font-size:10px;color:var(--ink-soft);">'
                f'{detail}</div>',
                unsafe_allow_html=True,
            )

        if checked != current:
            try:
                db.set_exercise(date_str, eid, checked, profile_id)
                if checked:
                    _award_exercise(profile_id, eid, ex, date_str)
                    new_ach = gm.check_achievements(profile_id)
                    if new_ach:
                        st.session_state["new_achievements"] = new_ach
            except Exception:
                st.error(_DB_ERROR)
            st.rerun()

        # Inline PR logger
        with st.expander(f"📊 LOG — {ex['exercise_name']}", expanded=False):
            with st.form(f"pr_form_{date_str}_{eid}"):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    pr_type = st.selectbox(
                        "Tipo",
                        list(_PR_TYPES.keys()),
                        format_func=lambda x: _PR_TYPES[x],
                        key=f"prt_{date_str}_{eid}",
                    )
                with c2:
                    pr_val = st.number_input(
                        _PR_TYPES.get(pr_type, "Valor"),
                        min_value=0.0, step=0.5,
                        key=f"prv_{date_str}_{eid}",
                    )
                with c3:
                    pr_notes = st.text_input("Notas", key=f"prn_{date_str}_{eid}")
                if st.form_submit_button("GUARDAR", use_container_width=True):
                    try:
                        is_new = db.upsert_personal_record(
                            profile_id, ex["exercise_name"], pr_type,
                            pr_val, date_str, pr_notes.strip(),
                        )
                        if is_new:
                            xp = gm.award_xp(profile_id, "personal_record",
                                             ex["exercise_name"])
                            st.success(f"¡Nuevo PR! +{xp} XP")
                            st.session_state["show_pr_stamp"] = True
                            gm.check_achievements(profile_id)
                        else:
                            st.info("Guardado (sin superar PR previo).")
                    except Exception:
                        st.error(_DB_ERROR)
