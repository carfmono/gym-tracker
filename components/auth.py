import re
import streamlit as st
import db
import ui

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _auth_error_msg(e: Exception) -> str:
    """Convierte excepciones de Supabase en mensajes de usuario en español."""
    msg = str(e).lower()
    if "already registered" in msg or "user already" in msg:
        return "Ese email ya tiene cuenta. Usa **Iniciar sesión**."
    if "invalid login credentials" in msg or "invalid email or password" in msg:
        return "Email o contraseña incorrectos."
    if "email not confirmed" in msg:
        return "Confirma tu email antes de entrar. Revisa tu bandeja de entrada."
    if "password should be at least" in msg:
        return "La contraseña debe tener al menos 6 caracteres."
    if "unable to validate email" in msg or "invalid email" in msg:
        return "El formato del email no es válido."
    if "signup is disabled" in msg:
        return "El registro está deshabilitado. Contacta al administrador."
    if "email rate limit" in msg or "too many requests" in msg:
        return "Demasiados intentos. Espera unos minutos y vuelve a intentar."
    if "connection" in msg or "timeout" in msg or "network" in msg or "connect" in msg:
        return "Sin conexión con el servidor. Recarga la página."
    if "invalid api key" in msg or "unauthorized" in msg or "apikey" in msg:
        return "Error de configuración del servidor (API key inválida)."
    if "relation" in msg or "does not exist" in msg:
        return (
            "La base de datos no está configurada. "
            "Ejecuta el script SQL del README en Supabase."
        )
    # fallback: mostrar el error real para diagnóstico
    return f"Error: {str(e)[:200]}"


def _post_login(user, display_name: str = ""):
    profile = db.get_or_create_profile(
        user.id, display_name or (user.email or "").split("@")[0]
    )
    st.session_state.user = user
    st.session_state.profile_id = profile["id"]
    db.init_user_xp(profile["id"])


def try_restore_session() -> bool:
    """
    Intenta restaurar la sesión desde el cliente Supabase cacheado.
    Retorna True si se restauró correctamente.
    Útil cuando session_state se limpia (recarga, nueva pestaña dentro del mismo proceso).
    """
    try:
        session = db.get_client().auth.get_session()
        if session and session.user:
            profile = db.get_or_create_profile(session.user.id)
            st.session_state.user = session.user
            st.session_state.profile_id = profile["id"]
            db.init_user_xp(profile["id"])
            return True
    except Exception:
        pass
    return False


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

    # ── Login ──────────────────────────────────────────────────────────────────
    with tab_login:
        with st.form("auth_login_form"):
            email    = st.text_input("Email", key="login_email")
            password = st.text_input("Contraseña", type="password", key="login_password")
            submitted = st.form_submit_button(
                "ENTRAR", type="primary", use_container_width=True
            )

        if submitted:
            email = email.strip()
            if not _EMAIL_RE.match(email):
                st.error("Ingresa un email válido.")
            elif not password:
                st.error("Ingresa tu contraseña.")
            else:
                with st.spinner("Entrando..."):
                    try:
                        res = db.sign_in(email, password)
                        if res.user:
                            try:
                                _post_login(res.user)
                            except Exception as db_err:
                                st.error(_auth_error_msg(db_err))
                                st.stop()
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas.")
                    except Exception as e:
                        st.error(_auth_error_msg(e))

    # ── Registro ───────────────────────────────────────────────────────────────
    with tab_signup:
        with st.form("auth_signup_form"):
            name     = st.text_input("Nombre", max_chars=40, key="signup_name")
            email    = st.text_input("Email", key="signup_email")
            password = st.text_input(
                "Contraseña (mínimo 6 caracteres)", type="password", key="signup_password"
            )
            confirm  = st.text_input(
                "Confirmar contraseña", type="password", key="signup_confirm"
            )
            submitted = st.form_submit_button(
                "CREAR CUENTA", type="primary", use_container_width=True
            )

        if submitted:
            email = email.strip()
            if not _EMAIL_RE.match(email):
                st.error("Ingresa un email válido.")
            elif len(password) < 6:
                st.error("La contraseña debe tener mínimo 6 caracteres.")
            elif password != confirm:
                st.error("Las contraseñas no coinciden.")
            else:
                with st.spinner("Creando cuenta..."):
                    # 1) Crear usuario en Supabase Auth
                    try:
                        res = db.sign_up(email, password)
                    except Exception as auth_err:
                        st.error(_auth_error_msg(auth_err))
                        st.stop()

                    if res.user and res.session:
                        # Confirmación de email deshabilitada → entramos directo
                        try:
                            _post_login(res.user, name.strip())
                        except Exception as db_err:
                            st.error(_auth_error_msg(db_err))
                            st.stop()
                        st.rerun()

                    elif res.user:
                        # Confirmación de email requerida
                        st.success(
                            "✅ **Cuenta creada.** Revisa tu email y haz clic en el "
                            "enlace de confirmación. Luego vuelve aquí e inicia sesión."
                        )
                        st.info(
                            "💡 Si no ves el email en 2 minutos, revisa la carpeta de spam. "
                            "El remitente es Supabase."
                        )
                        st.markdown(
                            '<div style="font-family:var(--font-mono);font-size:10px;'
                            'color:var(--ink-soft);text-align:center;margin-top:6px;">'
                            '¿Ya confirmaste? → usa la pestaña INICIAR SESIÓN</div>',
                            unsafe_allow_html=True,
                        )

                    else:
                        st.error(
                            "No se pudo crear la cuenta. "
                            "Intenta con otro email o contacta al administrador."
                        )
