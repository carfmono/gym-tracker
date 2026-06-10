import streamlit as st
import db
import gamification as gm
import ui
from styles import PALETTE_LABELS

PROFILE_ID = 1


def render_profile():
    try:
        uxp     = db.get_user_xp(PROFILE_ID)
        prog    = gm.xp_progress(uxp["total_xp"]) if uxp else None
        profile = db.get_profile(PROFILE_ID) or {}
    except Exception:
        uxp = prog = None
        profile = {}

    nombre    = profile.get("name", "ENTRENADOR")
    since_raw = profile.get("created_at", "")
    since_str = str(since_raw)[:10] if since_raw else "2024"

    # ── Member card ────────────────────────────────────────────────────────────
    try:
        user_ach = db.get_user_achievements(PROFILE_ID)
        badges   = [a["icon"] + " " + a["name"] for a in user_ach[:6]]
    except Exception:
        badges = []

    st.markdown(
        ui.logo_bar(right_html=f'<span class="ia-chip brick">SOCIO ACTIVO</span>'),
        unsafe_allow_html=True,
    )
    st.markdown(
        ui.member_card(
            name=nombre,
            member_id=str(PROFILE_ID).zfill(4),
            since=since_str,
            level=prog["level"] if prog else 1,
            total_xp=uxp["total_xp"] if uxp else 0,
            badges=badges,
        ),
        unsafe_allow_html=True,
    )

    # ── Stats row ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("SESIONES", uxp.get("total_sessions", 0) if uxp else 0)
    c2.metric("EJERCICIOS", uxp.get("total_exercises_completed", 0) if uxp else 0)
    c3.metric("RACHA", f"{uxp.get('current_streak', 0)}d" if uxp else "0d")

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
                ).eq("id", PROFILE_ID).execute()
                st.success("Nombre actualizado.")
                st.rerun()
            except Exception:
                st.error("Error al guardar.")
