import re
import streamlit as st
import db
import ui

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _post_login(user, display_name: str = ""):
    profile = db.get_or_create_profile(user.id, display_name or (user.email or "").split("@")[0])
    st.session_state.user = user
    st.session_state.profile_id = profile["id"]
    db.init_user_xp(profile["id"])


def render_auth():
    st.markdown(
        ui.logo_bar(right_html=ui.chip("SOLO MIEMBROS", "brick")),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ia-hero-card" style="text-align:center;margin-bottom:14px;">'
        '<div style="font-family:var(--font-display);font-size:34px;line-height:0.95;'
        'text-transform:uppercase;color:var(--ink);">Iron Age</div>'
        '<div style="font-family:var(--font-mono);font-size:10px;letter-spacing:0.14em;'
        'text-transform:uppercase;color:var(--ink-soft);margin-top:6px;">'
        'TU GIMNASIO · TU PROGRESO · TU RACHA</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["INICIAR SESIÓN", "REGISTRARSE"])

    with tab_login:
        with st.form("auth_login_form"):
            email    = st.text_input("Email", key="login_email")
            password = st.text_input("Contraseña", type="password", key="login_password")
            if st.form_submit_button("ENTRAR", type="primary", use_container_width=True):
                email = email.strip()
                if not _EMAIL_RE.match(email):
                    st.error("Ingresa un email válido.")
                elif not password:
                    st.error("Ingresa tu contraseña.")
                else:
                    try:
                        res = db.sign_in(email, password)
                        if res.user:
                            _post_login(res.user)
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas.")
                    except Exception:
                        st.error("Credenciales incorrectas o error de conexión.")

    with tab_signup:
        with st.form("auth_signup_form"):
            name     = st.text_input("Nombre", max_chars=40, key="signup_name")
            email    = st.text_input("Email", key="signup_email")
            password = st.text_input("Contraseña (mínimo 6 caracteres)", type="password", key="signup_password")
            confirm  = st.text_input("Confirmar contraseña", type="password", key="signup_confirm")
            if st.form_submit_button("CREAR CUENTA", type="primary", use_container_width=True):
                email = email.strip()
                if not _EMAIL_RE.match(email):
                    st.error("Ingresa un email válido.")
                elif len(password) < 6:
                    st.error("La contraseña debe tener mínimo 6 caracteres.")
                elif password != confirm:
                    st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        res = db.sign_up(email, password)
                        if res.user and res.session:
                            _post_login(res.user, name.strip())
                            st.rerun()
                        elif res.user:
                            st.success("Cuenta creada. Revisa tu email para confirmarla y luego inicia sesión.")
                        else:
                            st.error("No se pudo crear la cuenta.")
                    except Exception as e:
                        msg = str(e).lower()
                        if "already" in msg or "registered" in msg:
                            st.error("Ese email ya está registrado. Inicia sesión.")
                        else:
                            st.error("No se pudo crear la cuenta. Intenta de nuevo.")
