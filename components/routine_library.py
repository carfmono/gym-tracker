import streamlit as st
import pandas as pd
from datetime import date
import db
import gamification as gm

GOAL_LABELS = {
    "fuerza":        "💪 Fuerza",
    "hipertrofia":   "🏋️ Hipertrofia",
    "perdida_grasa": "🔥 Pérdida de grasa",
    "resistencia":   "🏃 Resistencia",
    "movilidad":     "🧘 Movilidad",
    "rehabilitacion":"🦶 Rehabilitación",
    "salud_general": "❤️ Salud general",
}
LEVEL_LABELS = {
    "principiante": "🟢 Principiante",
    "intermedio":   "🟡 Intermedio",
    "avanzado":     "🔴 Avanzado",
}
GOAL_COLORS = {
    "fuerza":        "#8E44AD",
    "hipertrofia":   "#2980B9",
    "perdida_grasa": "#E74C3C",
    "resistencia":   "#E67E22",
    "movilidad":     "#27AE60",
    "rehabilitacion":"#1ABC9C",
    "salud_general": "#3498DB",
}


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:0.68em;font-weight:700;">{text}</span>'
    )


def render_routine_library(profile_id: int = 1):
    # ── Sección 1: Biblioteca ─────────────────────────────────────────────────
    st.subheader("📚 Biblioteca de rutinas")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        goal_filter = st.multiselect(
            "Objetivo", list(GOAL_LABELS.keys()),
            format_func=lambda x: GOAL_LABELS.get(x, x),
        )
    with col_f2:
        level_filter = st.multiselect(
            "Nivel", list(LEVEL_LABELS.keys()),
            format_func=lambda x: LEVEL_LABELS.get(x, x),
        )
    with col_f3:
        days_filter = st.slider("Días/semana", 1, 7, (1, 7))

    try:
        templates = db.get_all_templates()
    except Exception:
        st.warning("No se pudo cargar la biblioteca. Verifica la conexión.")
        return

    if goal_filter:
        templates = [t for t in templates if t["goal"] in goal_filter]
    if level_filter:
        templates = [t for t in templates if t["level"] in level_filter]
    templates = [t for t in templates if days_filter[0] <= (t["days_per_week"] or 0) <= days_filter[1]]

    if not templates:
        st.info("No hay rutinas que coincidan con los filtros.")
    else:
        cols = st.columns(2)
        for i, tmpl in enumerate(templates):
            goal_color = GOAL_COLORS.get(tmpl["goal"], "#2980B9")
            with cols[i % 2]:
                with st.container():
                    days_badge = _badge(f"{tmpl['days_per_week']}d/sem", '#333')
                    st.markdown(
                        f"<div style='background:#1C2833;border-radius:10px;"
                        f"border-left:4px solid {goal_color};padding:12px;margin-bottom:10px;'>"
                        f"<div style='font-weight:700;font-size:0.95rem;'>{tmpl['name']}</div>"
                        f"<div style='font-size:0.75rem;color:#aaa;margin:4px 0;'>{tmpl.get('description','')[:80]}…</div>"
                        f"{_badge(GOAL_LABELS.get(tmpl['goal'],''), goal_color)} "
                        f"{_badge(LEVEL_LABELS.get(tmpl['level'],''), '#555')} "
                        f"{days_badge}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    with st.expander("Ver ejercicios"):
                        try:
                            exs = db.get_template_exercises(tmpl["id"])
                        except Exception:
                            exs = []
                        if exs:
                            current_day = None
                            for ex in exs:
                                if ex["day_name"] != current_day:
                                    current_day = ex["day_name"]
                                    st.markdown(f"**{current_day}**")
                                badges = ""
                                if ex.get("is_posture"):
                                    badges += " ⭐"
                                if ex.get("is_ankle"):
                                    badges += " 🦶"
                                st.caption(
                                    f"{ex['order_index']}. {ex['exercise_name']} "
                                    f"— {ex.get('sets','?')}×{ex.get('reps','?')}{badges}"
                                )
                        else:
                            st.caption("Sin detalle de ejercicios.")

                    if st.button(
                        "▶ Activar esta rutina",
                        key=f"activate_{tmpl['id']}",
                        use_container_width=True,
                    ):
                        _activate_template(profile_id, tmpl)
                        st.rerun()

    st.divider()

    # ── Sección 2: Mis rutinas ─────────────────────────────────────────────────
    st.subheader("📋 Mis rutinas")

    try:
        my_routines = db.get_routines_by_profile(profile_id)
    except Exception:
        my_routines = []

    if not my_routines:
        st.info("No tienes rutinas registradas aún. Activa una desde la biblioteca.")
    else:
        for r in reversed(my_routines):
            is_active = r.get("end_date") is None
            status = "🟢 ACTIVA" if is_active else "⬛ Completada"

            if is_active:
                st.markdown(
                    f"<div style='background:#1C2833;border-radius:8px;"
                    f"border-left:4px solid #27AE60;padding:10px;margin-bottom:8px;'>"
                    f"<b>{r['name']}</b>  "
                    f"<span style='color:#27AE60;font-size:0.8em;'>{status}</span><br>"
                    f"<small>Inicio: {r.get('start_date','')}  |  {r.get('version','')}</small>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button("✅ Marcar como completada", key=f"complete_{r['id']}", use_container_width=True):
                    _complete_routine(profile_id, r)
                    st.rerun()
            else:
                inicio = r.get("start_date", "")
                fin    = r.get("end_date", "")
                st.markdown(
                    f"<div style='background:#161b22;border-radius:8px;"
                    f"padding:8px 10px;margin-bottom:6px;opacity:0.7;'>"
                    f"<b>{r['name']}</b>  "
                    f"<span style='color:#555;font-size:0.8em;'>{status}</span><br>"
                    f"<small>{inicio} → {fin}  |  {r.get('version','')}</small>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Sección 3: Progreso hacia las 25 ─────────────────────────────────────
    st.subheader("🌠 Progreso: Las 25 rutinas")

    completed_names = {r["name"] for r in my_routines if r.get("end_date")}
    try:
        all_templates = db.get_all_templates()
    except Exception:
        all_templates = []

    n_completed = sum(1 for t in all_templates if t["name"] in completed_names)
    total = len(all_templates)
    pct = n_completed / total if total else 0

    st.progress(pct)
    st.caption(f"Has completado **{n_completed}** de **{total}** rutinas disponibles")

    if n_completed == 0:
        st.markdown("💬 *El viaje de mil entrenamientos empieza con el primer día.*")
    elif pct < 0.25:
        st.markdown("💬 *¡Buen comienzo! La consistencia es la clave.*")
    elif pct < 0.5:
        st.markdown("💬 *Ya llevas un cuarto del camino. ¡Sigue así!*")
    elif pct < 0.75:
        st.markdown("💬 *Más de la mitad. Eres una máquina.*")
    elif pct < 1.0:
        st.markdown("💬 *¡Casi! Queda poco para completar todas las rutinas.*")
    else:
        st.balloons()
        st.markdown("🌠 **¡LO LOGRASTE! Completaste las 25 rutinas. Eres una leyenda.**")

    if all_templates:
        cols = st.columns(3)
        for i, t in enumerate(all_templates):
            done = t["name"] in completed_names
            icon = "✅" if done else "⬜"
            with cols[i % 3]:
                st.caption(f"{icon} {t['name'][:30]}")


def _activate_template(profile_id: int, tmpl: dict):
    try:
        db.create_routine(
            profile_id=profile_id,
            version=f"tmpl-{tmpl['id']}",
            name=tmpl["name"],
            start_date=date.today().isoformat(),
            notes=tmpl.get("description") or "",
        )
        # Copiar días desde template_exercises como routine_days
        exs = db.get_template_exercises(tmpl["id"])
        days_seen: dict = {}
        for ex in exs:
            d = ex["day_name"]
            if d not in days_seen:
                days_seen[d] = {"day_name": d, "session_type": ex.get("category", ""), "order_index": len(days_seen)}

        active = db.get_active_routine(profile_id)
        if active:
            db.set_routine_days(active["id"], list(days_seen.values()))

        gm.award_xp(profile_id, "routine_started", tmpl["name"], idempotent=False)
        st.success(f"✅ Rutina '{tmpl['name']}' activada. +50 XP")
        gm.check_achievements(profile_id)
    except Exception as e:
        st.error("Error al activar la rutina.")


def _complete_routine(profile_id: int, routine: dict):
    try:
        with db.get_connection() as conn:
            db._exec(
                conn,
                "UPDATE routines SET end_date=%s WHERE id=%s AND profile_id=%s",
                (date.today().isoformat(), routine["id"], profile_id),
            )
        gm.award_xp(profile_id, "routine_complete", routine["name"], idempotent=False)
        st.success(f"🏁 Rutina completada. +500 XP")
        gm.check_achievements(profile_id)
    except Exception:
        st.error("Error al completar la rutina.")
