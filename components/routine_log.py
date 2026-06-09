import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
import db
import ui


def render_routine_log():
    st.markdown(ui.label("HISTORIAL DE RUTINAS"), unsafe_allow_html=True)

    try:
        routines = db.get_all_routines()
    except psycopg2.DatabaseError:
        st.error("No se pudo cargar el historial. Intenta recargar la página.")
        return

    if routines:
        rows_html = ""
        for r in routines:
            is_active = not r.get("end_date")
            fin_str   = "ACTIVA" if is_active else str(r.get("end_date", ""))[:10]
            chip_html = (
                f'&nbsp;<span class="ia-chip teal" style="font-size:7px;">ACTIVA</span>'
                if is_active else ""
            )
            rows_html += ui.ticket_row(
                num    = str(r.get("id", ""))[:4],
                name   = r["name"],
                detail = f"{r.get('start_date','')} → {fin_str} · {r.get('version','')}",
                done   = not is_active,
                chips_html=chip_html,
            )
        st.markdown(ui.ticket_list(rows_html), unsafe_allow_html=True)
    else:
        st.info("No hay rutinas registradas.")

    # ── New routine form ───────────────────────────────────────────────────────
    st.markdown(ui.label("NUEVA RUTINA"), unsafe_allow_html=True)

    with st.form("new_routine_form"):
        version    = st.text_input("Versión", placeholder="v2")
        name       = st.text_input("Nombre", placeholder="Rutina 2 — Hipertrofia")
        start_date = st.date_input("Fecha de inicio", value=date.today())
        notes      = st.text_area("Notas", placeholder="Descripción del plan...", height=80)

        if st.form_submit_button("GUARDAR RUTINA", type="primary", use_container_width=True):
            if not version.strip() or not name.strip():
                st.error("Versión y nombre son obligatorios.")
            else:
                try:
                    db.add_routine(
                        version   =version.strip(),
                        name      =name.strip(),
                        start_date=start_date.strftime("%Y-%m-%d"),
                        notes     =notes.strip(),
                    )
                    st.success(f"Rutina '{name}' guardada.")
                    st.rerun()
                except psycopg2.DatabaseError:
                    st.error("Error al guardar la rutina.")
