import streamlit as st
import pandas as pd
from datetime import date
import db


def render_routine_log():
    st.subheader("Historial de rutinas")

    routines = db.get_all_routines()
    if routines:
        df = pd.DataFrame(routines)
        df = df.rename(columns={
            "id": "ID",
            "version": "Versión",
            "name": "Nombre",
            "start_date": "Inicio",
            "end_date": "Fin",
            "notes": "Notas",
        })
        df["Fin"] = df["Fin"].fillna("Activa ✅")
        st.dataframe(df[["ID", "Versión", "Nombre", "Inicio", "Fin", "Notas"]], use_container_width=True, hide_index=True)
    else:
        st.info("No hay rutinas registradas.")

    st.divider()
    st.subheader("Registrar nueva rutina")

    with st.form("new_routine_form"):
        col1, col2 = st.columns(2)
        with col1:
            version = st.text_input("Versión (ej: v2)", placeholder="v2")
            name = st.text_input("Nombre de la rutina", placeholder="Rutina 2 — Hipertrofia")
        with col2:
            start_date = st.date_input("Fecha de inicio", value=date.today())
        notes = st.text_area("Notas", placeholder="Descripción del plan, cambios respecto a anterior...")

        submitted = st.form_submit_button("💾 Guardar rutina", type="primary")

        if submitted:
            if not version.strip() or not name.strip():
                st.error("Versión y nombre son obligatorios.")
            else:
                db.add_routine(
                    version=version.strip(),
                    name=name.strip(),
                    start_date=start_date.strftime("%Y-%m-%d"),
                    notes=notes.strip(),
                )
                st.success(f"Rutina '{name}' guardada correctamente.")
                st.rerun()
