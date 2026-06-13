import streamlit as st
import plotly.graph_objects as go
import db
import gamification as gm
import ui
from styles import PALETTE_LABELS

_PLOTLY_CFG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


def _render_weight_tracker(profile_id: int):
    st.markdown(ui.label("PESO CORPORAL"), unsafe_allow_html=True)

    try:
        records = [
            r for r in db.get_personal_records(profile_id)
            if r["exercise_name"] == "Peso corporal" and r["record_type"] == "weight_kg"
        ]
    except Exception:
        records = []

    # Fetch full history from xp_log doesn't work — use personal_records as single latest.
    # Instead pull all rows for this exercise from the table (no history API, but we can query directly).
    try:
        res = (
            db.get_client().table("personal_records")
            .select("value,date,notes")
            .eq("profile_id", profile_id)
            .eq("exercise_name", "Peso corporal")
            .eq("record_type", "weight_kg")
            .order("date", desc=False)
            .execute()
        )
        history = res.data or []
    except Exception:
        history = []

    if history:
        last = history[-1]
        st.markdown(
            f'<div class="ia-card" style="text-align:center;">'
            f'<div style="font-family:var(--font-display);font-size:40px;color:var(--brick);">'
            f'{float(last["value"]):.1f}</div>'
            f'<div style="font-family:var(--font-mono);font-size:9px;color:var(--ink-soft);">KG · {str(last["date"])[:10]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if len(history) > 1:
            dates  = [str(r["date"])[:10] for r in history]
            values = [float(r["value"]) for r in history]
            fig = go.Figure(go.Scatter(
                x=dates, y=values,
                mode="lines+markers",
                line=dict(color="#B0392A", width=2),
                marker=dict(size=6, color="#B0392A", line=dict(color="#2A1C10", width=1.5)),
                fill="tozeroy",
                fillcolor="rgba(226,162,43,0.12)",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2A1C10", family="'Space Mono', monospace", size=10),
                margin=dict(l=32, r=8, t=8, b=8),
                height=150,
                xaxis=dict(tickangle=-45, tickfont=dict(size=8, color="#6B5536")),
                yaxis=dict(tickfont=dict(size=8, color="#6B5536"), gridcolor="rgba(42,28,16,0.1)"),
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)

    with st.expander("REGISTRAR PESO"):
        with st.form("weight_form"):
            from datetime import date as _date
            col1, col2 = st.columns(2)
            with col1:
                peso = st.number_input("Peso (kg)", min_value=30.0, max_value=300.0, step=0.1, value=70.0)
            with col2:
                fecha = st.date_input("Fecha", value=_date.today())
            notas = st.text_input("Notas (opcional)", placeholder="En ayunas, mañana...")
            if st.form_submit_button("GUARDAR PESO", use_container_width=True):
                try:
                    db.upsert_personal_record(
                        profile_id, "Peso corporal", "weight_kg",
                        peso, fecha.isoformat(), notas.strip(),
                    )
                    st.success(f"Peso {peso:.1f} kg guardado.")
                    st.rerun()
                except Exception:
                    st.error("Error al guardar.")


def render_profile():
    profile_id = st.session_state.profile_id
    try:
        uxp     = db.get_user_xp(profile_id)
        prog    = gm.xp_progress(uxp["total_xp"]) if uxp else None
        profile = db.get_profile(profile_id) or {}
    except Exception:
        uxp = prog = None
        profile = {}

    nombre    = profile.get("name", "ENTRENADOR")
    since_raw = profile.get("created_at", "")
    since_str = str(since_raw)[:10] if since_raw else "2024"

    # ── Member card ────────────────────────────────────────────────────────────
    try:
        user_ach = db.get_user_achievements(profile_id)
        badges   = [a["icon"] + " " + a["name"] for a in user_ach[:6]]
    except Exception:
        badges = []

    level_now = prog["level"] if prog else 1
    avatar    = gm.avatar_for_level(level_now)

    st.markdown(
        ui.logo_bar(right_html=f'<span class="ia-chip brick">SOCIO ACTIVO</span>'),
        unsafe_allow_html=True,
    )
    st.markdown(
        ui.member_card(
            name=nombre,
            member_id=str(profile_id).zfill(4),
            since=since_str,
            level=level_now,
            total_xp=uxp["total_xp"] if uxp else 0,
            badges=badges,
            avatar=avatar,
        ),
        unsafe_allow_html=True,
    )

    # ── Stats row ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("SESIONES", uxp.get("total_sessions", 0) if uxp else 0)
    c2.metric("EJERCICIOS", uxp.get("total_exercises_completed", 0) if uxp else 0)
    c3.metric("RACHA", f"{uxp.get('current_streak', 0)}d" if uxp else "0d")

    _render_weight_tracker(profile_id)

    st.markdown(ui.label("CONFIGURACIÓN"), unsafe_allow_html=True)

    # ── Palette selector ───────────────────────────────────────────────────────
    palette_options = list(PALETTE_LABELS.keys())
    palette_labels  = [PALETTE_LABELS[k] for k in palette_options]
    current_idx = palette_options.index(st.session_state.get("palette", "venice"))

    new_palette_label = st.selectbox(
        "Paleta de colores",
        palette_labels,
        index=current_idx,
    )
    new_palette = palette_options[palette_labels.index(new_palette_label)]
    if new_palette != st.session_state.get("palette"):
        st.session_state.palette = new_palette
        st.rerun()

    # ── Grain texture ──────────────────────────────────────────────────────────
    new_grain = st.slider(
        "Nivel de textura",
        min_value=0.0,
        max_value=0.28,
        value=float(st.session_state.get("grain_opacity", 0.10)),
        step=0.02,
        format="%.2f",
    )
    if abs(new_grain - st.session_state.get("grain_opacity", 0.10)) > 0.001:
        st.session_state.grain_opacity = new_grain
        st.rerun()

    # ── Headline font ──────────────────────────────────────────────────────────
    font_opts   = ["Anton", "Alfa Slab One"]
    current_f   = st.session_state.get("headline_font", "Anton")
    new_font    = st.selectbox("Fuente de titulares", font_opts,
                               index=font_opts.index(current_f) if current_f in font_opts else 0)
    if new_font != current_f:
        st.session_state.headline_font = new_font
        st.rerun()

    # ── Accent color ──────────────────────────────────────────────────────────
    accent_presets = {
        "Ladrillo (default)": None,
        "Rojo":   "#C0392B",
        "Turquesa": "#2E8C82",
        "Magenta": "#C9456E",
        "Azul":   "#2E6DA4",
    }
    current_accent = st.session_state.get("accent", None)
    accent_labels  = list(accent_presets.keys())
    # find current
    default_accent_idx = 0
    for i, (lbl, val) in enumerate(accent_presets.items()):
        if val == current_accent:
            default_accent_idx = i
            break

    chosen_label = st.selectbox("Color de acento", accent_labels, index=default_accent_idx)
    new_accent   = accent_presets[chosen_label]
    if new_accent != current_accent:
        st.session_state.accent = new_accent
        st.rerun()

    st.markdown(ui.label("DATOS DEL PERFIL"), unsafe_allow_html=True)

    # ── Name edit ─────────────────────────────────────────────────────────────
    with st.form("profile_name_form"):
        new_name = st.text_input("Nombre", value=nombre, max_chars=40)
        if st.form_submit_button("GUARDAR NOMBRE", use_container_width=True):
            try:
                db.get_client().table("profiles").update(
                    {"name": new_name.strip() or "Entrenador"}
                ).eq("id", profile_id).execute()
                st.success("Nombre actualizado.")
                st.rerun()
            except Exception:
                st.error("Error al guardar.")

    # ── Logout ────────────────────────────────────────────────────────────────
    st.markdown(ui.label("SESIÓN"), unsafe_allow_html=True)
    if st.button("CERRAR SESIÓN", use_container_width=True, type="secondary"):
        try:
            db.sign_out()
        except Exception:
            pass
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
