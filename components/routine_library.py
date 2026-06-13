import streamlit as st
from datetime import date
import db
import gamification as gm
import ui

GOAL_LABELS = {
    "fuerza":        "FUERZA",
    "hipertrofia":   "HIPERTROFIA",
    "perdida_grasa": "PÉRDIDA GRASA",
    "resistencia":   "RESISTENCIA",
    "movilidad":     "MOVILIDAD",
    "rehabilitacion":"REHABILITACIÓN",
    "salud_general": "SALUD GENERAL",
}
GOAL_CHIPS = {
    "fuerza":        "brick",
    "hipertrofia":   "teal",
    "perdida_grasa": "brick",
    "resistencia":   "teal",
    "movilidad":     "gold",
    "rehabilitacion":"teal",
    "salud_general": "gold",
}
LEVEL_CHIPS = {
    "principiante": "gold",
    "intermedio":   "brick",
    "avanzado":     "ink",
}


def render_routine_library():
    profile_id = st.session_state.profile_id
    st.markdown(ui.label("BIBLIOTECA DE RUTINAS"), unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        goal_filter = st.multiselect(
            "Objetivo", list(GOAL_LABELS.keys()),
            format_func=lambda x: GOAL_LABELS.get(x, x),
        )
    with col_f2:
        level_filter = st.multiselect(
            "Nivel", ["principiante", "intermedio", "avanzado"],
            format_func=lambda x: x.upper(),
        )
    days_filter = st.slider("Días/semana", 1, 7, (1, 7))

    try:
        templates = db.get_all_templates()
    except Exception:
        st.warning("No se pudo cargar la biblioteca.")
        return

    if goal_filter:
        templates = [t for t in templates if t["goal"] in goal_filter]
    if level_filter:
        templates = [t for t in templates if t["level"] in level_filter]
    templates = [t for t in templates if days_filter[0] <= (t["days_per_week"] or 0) <= days_filter[1]]

    if not templates:
        st.info("No hay rutinas con esos filtros.")
        return

    # ── Routine cards ──────────────────────────────────────────────────────────
    for tmpl in templates:
        goal_chip  = ui.chip(GOAL_LABELS.get(tmpl["goal"], tmpl["goal"]), GOAL_CHIPS.get(tmpl["goal"], "gold"))
        level_chip = ui.chip(tmpl["level"].upper(), LEVEL_CHIPS.get(tmpl["level"], "gold"))
        days_chip  = ui.chip(f"{tmpl['days_per_week']}D/SEM", "ink")
        desc       = (tmpl.get("description") or "")[:90]

        card_html = (
            f'<div class="ia-card" style="margin-bottom:10px;">'
            f'<div style="font-family:var(--font-display);font-size:18px;line-height:1;'
            f'text-transform:uppercase;color:var(--ink);margin-bottom:6px;">{ui._e(tmpl["name"])}</div>'
            f'<div style="font-family:var(--font-body);font-size:13px;color:var(--ink-soft);'
            f'margin-bottom:8px;">{ui._e(desc)}{"…" if len(desc) >= 90 else ""}</div>'
            f'<div>{goal_chip}{level_chip}{days_chip}</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        col_exp, col_act = st.columns([1, 1])
        with col_exp:
            with st.expander("VER EJERCICIOS"):
                try:
                    exs = db.get_template_exercises(tmpl["id"])
                except Exception:
                    exs = []
                if exs:
                    current_day = None
                    rows_html   = ""
                    for ex in exs:
                        if ex["day_name"] != current_day:
                            if rows_html:
                                st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)
                                rows_html = ""
                            current_day = ex["day_name"]
                            st.markdown(ui.label(current_day), unsafe_allow_html=True)
                        badges = ("⭐" if ex.get("is_posture") else "") + ("🦶" if ex.get("is_ankle") else "")
                        rows_html += ui.ticket_row(
                            num    = ex["order_index"],
                            name   = ex["exercise_name"],
                            detail = f"{ex.get('sets','?')}×{ex.get('reps','?')} {badges}".strip(),
                        )
                    if rows_html:
                        st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)
                else:
                    st.caption("Sin detalle de ejercicios.")
        with col_act:
            if st.button("ACTIVAR", key=f"activate_{tmpl['id']}", use_container_width=True):
                _activate_template(profile_id, tmpl)
                st.rerun()

        st.markdown("<hr/>", unsafe_allow_html=True)

    # ── My routines ────────────────────────────────────────────────────────────
    st.markdown(ui.label("MIS RUTINAS"), unsafe_allow_html=True)
    try:
        my_routines = db.get_routines_by_profile(profile_id)
    except Exception:
        my_routines = []

    if not my_routines:
        st.info("No tienes rutinas registradas. Activa una de la biblioteca.")
    else:
        rows_html = ""
        for r in reversed(my_routines):
            is_active = r.get("end_date") is None
            chip_html = (
                f'&nbsp;<span class="ia-chip teal" style="font-size:8px;">ACTIVA</span>'
                if is_active else
                f'&nbsp;<span class="ia-chip ink" style="font-size:8px;">COMPLETADA</span>'
            )
            rows_html += ui.ticket_row(
                num    = "●" if is_active else "○",
                name   = r["name"],
                detail = f"Inicio: {r.get('start_date','')} · {r.get('version','')}",
                done   = not is_active,
                chips_html=chip_html,
            )
        st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)

        # Complete button for active routine
        active_r = next((r for r in my_routines if r.get("end_date") is None), None)
        if active_r:
            if st.button("MARCAR COMO COMPLETADA", key=f"complete_{active_r['id']}", use_container_width=True, type="secondary"):
                _complete_routine(profile_id, active_r)
                st.rerun()

    # ── Progress: 25 routines ─────────────────────────────────────────────────
    st.markdown(ui.label("PROGRESO — LAS 25 RUTINAS"), unsafe_allow_html=True)
    completed_names = {r["name"] for r in my_routines if r.get("end_date")}
    try:
        all_tpls = db.get_all_templates()
    except Exception:
        all_tpls = []

    n_done  = sum(1 for t in all_tpls if t["name"] in completed_names)
    n_total = len(all_tpls)
    st.markdown(
        ui.progress_bar("RUTINAS", n_done, max(n_total, 1)),
        unsafe_allow_html=True,
    )

    quotes = {
        0:    "El viaje de mil entrenamientos empieza con el primer día.",
        0.25: "¡Buen comienzo! La consistencia es la clave.",
        0.5:  "Más de la mitad. Eres una máquina.",
        0.75: "¡Casi! Queda poco para ser leyenda.",
        1.0:  "¡LO LOGRASTE! Completaste las 25 rutinas.",
    }
    pct_rut = n_done / n_total if n_total else 0
    for threshold in sorted(quotes.keys(), reverse=True):
        if pct_rut >= threshold:
            st.caption(quotes[threshold])
            break

    if n_done == n_total and n_total > 0:
        st.balloons()
        st.markdown(
            f'<div style="text-align:center;margin:12px 0;">{ui.stamp("LEYENDA")}</div>',
            unsafe_allow_html=True,
        )


def _activate_template(profile_id: int, tmpl: dict):
    try:
        db.create_routine(
            profile_id=profile_id,
            version    =f"tmpl-{tmpl['id']}",
            name       =tmpl["name"],
            start_date =date.today().isoformat(),
            notes      =tmpl.get("description") or "",
        )
        exs        = db.get_template_exercises(tmpl["id"])
        days_seen  = {}
        for ex in exs:
            d = ex["day_name"]
            if d not in days_seen:
                days_seen[d] = {"day_name": d, "session_type": ex.get("category", ""), "order_index": len(days_seen)}
        active = db.get_active_routine(profile_id)
        if active:
            db.set_routine_days(active["id"], list(days_seen.values()))
        gm.award_xp(profile_id, "routine_started", tmpl["name"], idempotent=False)
        st.success(f"Rutina '{tmpl['name']}' activada. +50 XP")
        gm.check_achievements(profile_id)
    except Exception:
        st.error("Error al activar la rutina.")


def _complete_routine(profile_id: int, routine: dict):
    try:
        (db.get_client().table("routines")
         .update({"end_date": date.today().isoformat()})
         .eq("id", routine["id"])
         .eq("profile_id", profile_id)
         .execute())
        gm.award_xp(profile_id, "routine_complete", routine["name"], idempotent=False)
        st.success("Rutina completada. +500 XP")
        gm.check_achievements(profile_id)
    except Exception:
        st.error("Error al completar la rutina.")
