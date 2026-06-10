"""DB layer — Supabase Python client (pure Python, no C compilation needed)."""
from __future__ import annotations
import re
import streamlit as st
from supabase import create_client, Client

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(d: str) -> str:
    if not _DATE_RE.match(d):
        raise ValueError(f"Formato de fecha inválido: {d!r}")
    return d


@st.cache_resource
def get_client() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


# ── No-ops (tables managed in Supabase dashboard) ─────────────────────────────

def init_db():
    pass


def migrate_db():
    pass


# ── Seed achievements ─────────────────────────────────────────────────────────

def seed_achievements():
    c = get_client()
    res = c.table("achievements").select("id", count="exact").execute()
    if (res.count or 0) > 0:
        return
    _ACHIEVEMENTS = [
        ("primera_sesion",      "🏁 Primera sesión",           "Completa tu primera sesión",                        "🏁", 50,   "consistencia", "sessions_total",     1),
        ("semana_1",            "🔥 Una semana activo",         "Completa 7 sesiones en total",                      "🔥", 100,  "consistencia", "sessions_total",     7),
        ("mes_1",               "📅 Un mes en el gym",          "Acumula 30 sesiones completadas",                   "📅", 300,  "consistencia", "sessions_total",     30),
        ("tres_meses",          "💪 Tres meses",                "90 sesiones — ya es un hábito real",                "💪", 750,  "consistencia", "sessions_total",     90),
        ("seis_meses",          "🏆 Seis meses",                "180 sesiones. Constancia total.",                   "🏆", 1500, "consistencia", "sessions_total",     180),
        ("un_año",              "👑 Un año",                    "365 sesiones. Leyenda viva.",                       "👑", 3000, "consistencia", "sessions_total",     365),
        ("racha_7",             "🔥×7 Racha de 7 días",         "7 días consecutivos",                               "⚡", 150,  "consistencia", "streak_days",        7),
        ("racha_14",            "⚡ Racha de 14 días",          "14 días sin parar",                                 "⚡", 300,  "consistencia", "streak_days",        14),
        ("racha_30",            "🌟 Racha de 30 días",          "Un mes completo de racha",                          "🌟", 600,  "consistencia", "streak_days",        30),
        ("semana_perfecta",     "✨ Semana perfecta",           "Cumple todas las metas semanales",                  "✨", 200,  "consistencia", "perfect_weeks",      1),
        ("ejercicios_50",       "💥 50 ejercicios",             "Completa 50 ejercicios en total",                   "💥", 100,  "volumen",      "exercises_total",    50),
        ("ejercicios_100",      "🎯 100 ejercicios",            "100 ejercicios completados",                        "🎯", 200,  "volumen",      "exercises_total",    100),
        ("ejercicios_250",      "🏋️ 250 ejercicios",           "250 ejercicios — el volumen suma",                  "🏋️",400,  "volumen",      "exercises_total",    250),
        ("ejercicios_500",      "🔱 500 ejercicios",            "500 ejercicios. Máquina de trabajo.",               "🔱", 750,  "volumen",      "exercises_total",    500),
        ("ejercicios_1000",     "🌌 1000 ejercicios",           "1000 ejercicios completados. Élite.",               "🌌", 1500, "volumen",      "exercises_total",    1000),
        ("postura_7",           "🧘 7 días de postura",         "Completa la rutina de postura 7 días",              "🧘", 100,  "volumen",      "posture_days",       7),
        ("postura_30",          "🌿 30 días de postura",        "30 días de postura completados",                    "🌿", 400,  "volumen",      "posture_days",       30),
        ("madrugador",          "🌅 Madrugador",                "10 sesiones registradas",                           "🌅", 200,  "volumen",      "sessions_total",     10),
        ("nocturno",            "🌙 Búho nocturno",             "10 sesiones completadas",                           "🌙", 200,  "volumen",      "sessions_total",     10),
        ("fin_de_semana",       "🏖️ Guerrero de fin de semana", "10 sesiones",                                      "🏖️",150,  "volumen",      "sessions_total",     10),
        ("primera_rutina",      "📋 Primera rutina",            "Activa tu primera rutina",                          "📋", 100,  "rutinas",      "routines_completed", 1),
        ("rutinas_3",           "📚 3 rutinas",                 "Completa 3 rutinas distintas",                      "📚", 250,  "rutinas",      "routines_completed", 3),
        ("rutinas_5",           "🎓 5 rutinas",                 "5 rutinas completadas",                             "🎓", 500,  "rutinas",      "routines_completed", 5),
        ("rutinas_10",          "🏛️ 10 rutinas",               "10 rutinas. Diversidad total.",                     "🏛️",1000, "rutinas",      "routines_completed", 10),
        ("rutinas_25",          "🌠 ¡Las 25 rutinas!",          "Completaste las 25 plantillas. Leyenda.",            "🌠", 5000, "rutinas",      "routines_completed", 25),
        ("fuerza_iniciado",     "⚔️ Iniciado en Fuerza",       "Completa una rutina de fuerza",                     "⚔️", 200, "rutinas",      "routines_completed", 1),
        ("hipertrofia_iniciado","💪 Iniciado en Hipertrofia",   "Completa una rutina de hipertrofia",                "💪", 200, "rutinas",      "routines_completed", 1),
        ("cardio_iniciado",     "🏃 Iniciado en Cardio",        "Completa una rutina de pérdida de grasa",           "🏃", 200, "rutinas",      "routines_completed", 1),
        ("movilidad_iniciado",  "🧘 Iniciado en Movilidad",     "Completa una rutina de movilidad",                  "🧘", 200, "rutinas",      "routines_completed", 1),
        ("explorador",          "🗺️ Explorador",               "Prueba 5 categorías de rutinas distintas",          "🗺️",300, "rutinas",      "routines_completed", 5),
        ("nivel_2",   "⭐ Nivel 2",           "Alcanza el nivel 2",   "⭐", 0, "niveles", "level_reached", 2),
        ("nivel_5",   "⭐⭐ Nivel 5",         "Alcanza el nivel 5",   "⭐", 0, "niveles", "level_reached", 5),
        ("nivel_10",  "🌟 Nivel 10",          "Alcanza el nivel 10",  "🌟", 0, "niveles", "level_reached", 10),
        ("nivel_15",  "💫 Nivel 15",          "Alcanza el nivel 15",  "💫", 0, "niveles", "level_reached", 15),
        ("nivel_20",  "✨ Nivel 20",          "Alcanza el nivel 20",  "✨", 0, "niveles", "level_reached", 20),
        ("nivel_25",  "🏆 Nivel 25",          "Alcanza el nivel 25",  "🏆", 0, "niveles", "level_reached", 25),
        ("nivel_30",  "👑 Nivel 30",          "Alcanza el nivel 30",  "👑", 0, "niveles", "level_reached", 30),
        ("nivel_40",  "🔱 Nivel 40",          "Alcanza el nivel 40",  "🔱", 0, "niveles", "level_reached", 40),
        ("nivel_50",  "🌌 Nivel 50",          "Alcanza el nivel 50",  "🌌", 0, "niveles", "level_reached", 50),
        ("nivel_100", "🌠 Leyenda Nivel 100", "Nivel máximo alcanzado","🌠", 0, "niveles", "level_reached", 100),
    ]
    rows = [
        {
            "code": code, "name": name, "description": desc, "icon": icon,
            "xp_reward": xp, "category": cat,
            "condition_type": ctype, "condition_value": cval,
        }
        for code, name, desc, icon, xp, cat, ctype, cval in _ACHIEVEMENTS
    ]
    c.table("achievements").insert(rows).execute()


# ── Seed routine templates ────────────────────────────────────────────────────

def seed_routine_templates():
    c = get_client()
    res = c.table("routine_templates").select("id", count="exact").execute()
    if (res.count or 0) > 0:
        return

    templates = [
        {"name": "Fuerza Base 3x/sem",        "description": "Sentadilla, peso muerto y press. Progresión lineal.", "goal": "fuerza",        "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Fuerza Intermedia 4x/sem",   "description": "Upper/Lower split. Periodización ondulante.",         "goal": "fuerza",        "level": "intermedio",   "days_per_week": 4, "duration_weeks": 8},
        {"name": "Powerlifting 5x/sem",        "description": "Especialización en los 3 grandes levantamientos.",    "goal": "fuerza",        "level": "avanzado",     "days_per_week": 5, "duration_weeks": 12},
        {"name": "Hipertrofia Push/Pull/Legs", "description": "PPL clásico. 6 días, máximo volumen muscular.",        "goal": "hipertrofia",   "level": "intermedio",   "days_per_week": 6, "duration_weeks": 10},
        {"name": "Hipertrofia Full Body 3x",   "description": "Full body con énfasis en hipertrofia. Ideal para principiantes.", "goal": "hipertrofia", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Hipertrofia Upper/Lower",    "description": "4 días upper/lower con volumen progresivo.",           "goal": "hipertrofia",   "level": "intermedio",   "days_per_week": 4, "duration_weeks": 10},
        {"name": "Hipertrofia Torso/Pierna",   "description": "Split torso/pierna con alta frecuencia.",              "goal": "hipertrofia",   "level": "avanzado",     "days_per_week": 5, "duration_weeks": 10},
        {"name": "Pérdida de Grasa HIIT 3x",   "description": "HIIT + pesas. Máximo gasto calórico.",                "goal": "perdida_grasa", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Pérdida de Grasa Circuito",  "description": "Circuitos metabólicos de alta intensidad.",           "goal": "perdida_grasa", "level": "intermedio",   "days_per_week": 4, "duration_weeks": 8},
        {"name": "Cardio + Fuerza 5x",         "description": "Combinación de cardio moderado y fuerza.",            "goal": "perdida_grasa", "level": "intermedio",   "days_per_week": 5, "duration_weeks": 10},
        {"name": "Resistencia Funcional 3x",   "description": "Entrenamiento funcional de alta resistencia.",        "goal": "resistencia",   "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Resistencia Avanzada 5x",    "description": "Volumen alto, series largas, poca recuperación.",     "goal": "resistencia",   "level": "avanzado",     "days_per_week": 5, "duration_weeks": 10},
        {"name": "Movilidad & Flexibilidad",   "description": "Yoga-gym. Fuerza + rango de movimiento.",             "goal": "movilidad",     "level": "principiante", "days_per_week": 3, "duration_weeks": 6},
        {"name": "Movilidad Avanzada 5x",      "description": "Trabajo de movilidad articular profunda.",            "goal": "movilidad",     "level": "avanzado",     "days_per_week": 5, "duration_weeks": 8},
        {"name": "Rehabilitación Tobillo",     "description": "Programa peroneal + equilibrio. Adaptado para tobillo.", "goal": "rehabilitacion", "level": "principiante", "days_per_week": 4, "duration_weeks": 8},
        {"name": "Rehabilitación Rodilla",     "description": "Fortalecimiento gradual VMO y glúteos.",              "goal": "rehabilitacion", "level": "principiante", "days_per_week": 3, "duration_weeks": 10},
        {"name": "Rehabilitación Hombro",      "description": "Trabajo de manguito rotador y estabilizadores.",      "goal": "rehabilitacion", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Salud General 3x/sem",       "description": "Rutina completa para mantenerse en forma.",           "goal": "salud_general", "level": "principiante", "days_per_week": 3, "duration_weeks": 8},
        {"name": "Salud General 4x/sem",       "description": "Equilibrio entre fuerza, cardio y flexibilidad.",     "goal": "salud_general", "level": "principiante", "days_per_week": 4, "duration_weeks": 8},
        {"name": "Salud General Avanzada",     "description": "Alto volumen con variedad. Cuerpo completo.",         "goal": "salud_general", "level": "avanzado",     "days_per_week": 5, "duration_weeks": 10},
        {"name": "Rutina 1 — Base salud",      "description": "Plan inicial de retorno al gym. Tobillo/peroneal adaptado.", "goal": "salud_general", "level": "principiante", "days_per_week": 6, "duration_weeks": 8},
        {"name": "Fuerza Avanzada 6x",         "description": "Alta frecuencia por grupos musculares. Para avanzados.", "goal": "fuerza",    "level": "avanzado",     "days_per_week": 6, "duration_weeks": 12},
        {"name": "Cuerpo y Mente 4x",          "description": "Integra meditación activa, respiración y fuerza.",    "goal": "salud_general", "level": "intermedio",   "days_per_week": 4, "duration_weeks": 8},
        {"name": "Atlético Explosivo 4x",      "description": "Pliometría, sprints y fuerza explosiva.",             "goal": "resistencia",   "level": "avanzado",     "days_per_week": 4, "duration_weeks": 8},
        {"name": "Mantenimiento 3x",           "description": "Mantener condición física actual sin sobrecarga.",    "goal": "salud_general", "level": "intermedio",   "days_per_week": 3, "duration_weeks": 4},
    ]
    res2 = c.table("routine_templates").insert(templates).execute()
    # add a few exercises for the first template so the UI has something
    if res2.data:
        tid = res2.data[0]["id"]
        exs = [
            {"template_id": tid, "day_name": "Día A", "order_index": 1, "exercise_name": "Sentadilla", "sets": "3", "reps": "8-10", "category": "piernas", "is_posture": False, "is_ankle": False},
            {"template_id": tid, "day_name": "Día A", "order_index": 2, "exercise_name": "Press banca", "sets": "3", "reps": "8-10", "category": "pecho",  "is_posture": False, "is_ankle": False},
            {"template_id": tid, "day_name": "Día B", "order_index": 1, "exercise_name": "Peso muerto", "sets": "3", "reps": "5",    "category": "espalda","is_posture": False, "is_ankle": False},
            {"template_id": tid, "day_name": "Día B", "order_index": 2, "exercise_name": "Remo con barra", "sets": "3", "reps": "8", "category": "espalda","is_posture": False, "is_ankle": False},
        ]
        c.table("template_exercises").insert(exs).execute()


# ── user_xp ───────────────────────────────────────────────────────────────────

def init_user_xp(profile_id: int = 1):
    c = get_client()
    res = c.table("user_xp").select("id").eq("profile_id", profile_id).execute()
    if not res.data:
        c.table("user_xp").insert({
            "profile_id": profile_id,
            "total_xp": 0, "current_level": 1,
            "current_streak": 0, "longest_streak": 0,
            "total_sessions": 0, "total_exercises_completed": 0,
        }).execute()


def get_user_xp(profile_id: int = 1) -> dict | None:
    res = get_client().table("user_xp").select("*").eq("profile_id", profile_id).execute()
    return dict(res.data[0]) if res.data else None


def update_user_xp(profile_id: int, **kwargs):
    allowed = {
        "total_xp", "current_level", "current_streak", "longest_streak",
        "last_session_date", "total_sessions", "total_exercises_completed",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    get_client().table("user_xp").update(fields).eq("profile_id", profile_id).execute()


def add_xp_log(profile_id: int, event_type: str, xp_gained: int, description: str = ""):
    get_client().table("xp_log").insert({
        "profile_id": profile_id,
        "event_type": event_type,
        "xp_gained":  xp_gained,
        "description": description,
    }).execute()


def get_xp_log(profile_id: int, limit: int = 20) -> list[dict]:
    res = (
        get_client().table("xp_log")
        .select("*")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def xp_log_exists_today(profile_id: int, event_type: str, description: str) -> bool:
    from datetime import date
    today = date.today().isoformat()
    res = (
        get_client().table("xp_log")
        .select("id")
        .eq("profile_id", profile_id)
        .eq("event_type", event_type)
        .eq("description", description)
        .gte("created_at", today)
        .execute()
    )
    return bool(res.data)


# ── achievements ──────────────────────────────────────────────────────────────

def get_all_achievements() -> list[dict]:
    res = get_client().table("achievements").select("*").order("category").execute()
    return res.data or []


def get_user_achievements(profile_id: int) -> list[dict]:
    res = (
        get_client().table("user_achievements")
        .select("*, achievements(*)")
        .eq("profile_id", profile_id)
        .execute()
    )
    # flatten: merge achievements fields into top-level dict
    out = []
    for row in (res.data or []):
        ach = dict(row.get("achievements") or {})
        flat = {k: v for k, v in row.items() if k != "achievements"}
        out.append({**ach, **flat})
    return out


def unlock_achievement(profile_id: int, achievement_id: int) -> bool:
    try:
        get_client().table("user_achievements").insert({
            "profile_id": profile_id,
            "achievement_id": achievement_id,
        }).execute()
        return True
    except Exception:
        return False


# ── sessions ──────────────────────────────────────────────────────────────────

def get_session(date: str, profile_id: int = 1) -> bool:
    _validate_date(date)
    res = (
        get_client().table("sessions")
        .select("completed")
        .eq("profile_id", profile_id)
        .eq("date", date)
        .execute()
    )
    return bool(res.data[0]["completed"]) if res.data else False


def toggle_session(date: str, profile_id: int = 1):
    _validate_date(date)
    current = get_session(date, profile_id)
    get_client().table("sessions").upsert(
        {"profile_id": profile_id, "date": date, "completed": not current},
        on_conflict="profile_id,date",
    ).execute()


# ── exercises ─────────────────────────────────────────────────────────────────

def set_exercise(date: str, exercise_id: str, completed: bool, profile_id: int = 1):
    _validate_date(date)
    row_id = f"{profile_id}:{date}:{exercise_id}"
    get_client().table("exercises").upsert(
        {"id": row_id, "profile_id": profile_id, "date": date,
         "exercise_id": exercise_id, "completed": completed},
        on_conflict="id",
    ).execute()


def get_exercises_for_date(date: str, profile_id: int = 1) -> dict:
    _validate_date(date)
    res = (
        get_client().table("exercises")
        .select("exercise_id,completed")
        .eq("profile_id", profile_id)
        .eq("date", date)
        .execute()
    )
    return {r["exercise_id"]: bool(r["completed"]) for r in (res.data or [])}


# ── posture ───────────────────────────────────────────────────────────────────

def set_posture(date: str, exercise_id: str, completed: bool, profile_id: int = 1):
    _validate_date(date)
    row_id = f"{profile_id}:{date}:{exercise_id}"
    get_client().table("posture").upsert(
        {"id": row_id, "profile_id": profile_id, "date": date,
         "exercise_id": exercise_id, "completed": completed},
        on_conflict="id",
    ).execute()


def get_posture_for_date(date: str, profile_id: int = 1) -> dict:
    _validate_date(date)
    res = (
        get_client().table("posture")
        .select("exercise_id,completed")
        .eq("profile_id", profile_id)
        .eq("date", date)
        .execute()
    )
    return {r["exercise_id"]: bool(r["completed"]) for r in (res.data or [])}


# ── stats ─────────────────────────────────────────────────────────────────────

def get_stats_for_dates(dates: list[str], profile_id: int = 1) -> dict:
    if not dates:
        return {"sessions": {}, "exercises": [], "posture": []}
    c = get_client()
    sess_res = (
        c.table("sessions")
        .select("date,completed")
        .eq("profile_id", profile_id)
        .in_("date", dates)
        .execute()
    )
    ex_res = (
        c.table("exercises")
        .select("date,exercise_id,completed")
        .eq("profile_id", profile_id)
        .in_("date", dates)
        .execute()
    )
    pos_res = (
        c.table("posture")
        .select("date,exercise_id,completed")
        .eq("profile_id", profile_id)
        .in_("date", dates)
        .execute()
    )
    return {
        "sessions":  {r["date"]: bool(r["completed"]) for r in (sess_res.data or [])},
        "exercises": [dict(r) for r in (ex_res.data  or [])],
        "posture":   [dict(r) for r in (pos_res.data or [])],
    }


# ── routines ──────────────────────────────────────────────────────────────────

def get_all_routines(profile_id: int = 1) -> list[dict]:
    res = (
        get_client().table("routines")
        .select("*")
        .eq("profile_id", profile_id)
        .order("id")
        .execute()
    )
    return res.data or []


def add_routine(version: str, name: str, start_date: str, notes: str, profile_id: int = 1):
    c = get_client()
    # close any open routine
    open_res = (
        c.table("routines")
        .select("id")
        .eq("profile_id", profile_id)
        .is_("end_date", "null")
        .execute()
    )
    for r in (open_res.data or []):
        c.table("routines").update({"end_date": start_date}).eq("id", r["id"]).execute()
    c.table("routines").insert({
        "profile_id": profile_id, "version": version,
        "name": name, "start_date": start_date, "notes": notes,
    }).execute()


def get_active_routine(profile_id: int = 1) -> dict | None:
    res = (
        get_client().table("routines")
        .select("*")
        .eq("profile_id", profile_id)
        .is_("end_date", "null")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_routines_by_profile(profile_id: int = 1) -> list[dict]:
    res = (
        get_client().table("routines")
        .select("*")
        .eq("profile_id", profile_id)
        .order("id")
        .execute()
    )
    return res.data or []


def create_routine(profile_id: int, version: str, name: str, start_date: str, notes: str):
    c = get_client()
    open_res = (
        c.table("routines")
        .select("id")
        .eq("profile_id", profile_id)
        .is_("end_date", "null")
        .execute()
    )
    for r in (open_res.data or []):
        c.table("routines").update({"end_date": start_date}).eq("id", r["id"]).execute()
    c.table("routines").insert({
        "profile_id": profile_id, "version": version,
        "name": name, "start_date": start_date, "notes": notes,
    }).execute()


def set_routine_days(routine_id: int, days: list[dict]):
    c = get_client()
    c.table("routine_days").delete().eq("routine_id", routine_id).execute()
    if days:
        rows = [{**d, "routine_id": routine_id} for d in days]
        c.table("routine_days").insert(rows).execute()


# ── profiles ──────────────────────────────────────────────────────────────────

def get_profile(profile_id: int = 1) -> dict | None:
    res = get_client().table("profiles").select("*").eq("id", profile_id).execute()
    return res.data[0] if res.data else None


# ── weekly_goals ──────────────────────────────────────────────────────────────

def get_weekly_goals(profile_id: int, week_start: str) -> dict | None:
    res = (
        get_client().table("weekly_goals")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("week_start", week_start)
        .execute()
    )
    return res.data[0] if res.data else None


def upsert_weekly_goals(profile_id: int, week_start: str, **kwargs):
    allowed = {
        "sessions_goal", "exercises_goal", "posture_days_goal",
        "sessions_done", "exercises_done", "posture_days_done", "completed",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    get_client().table("weekly_goals").upsert(
        {"profile_id": profile_id, "week_start": week_start, **fields},
        on_conflict="profile_id,week_start",
    ).execute()


# ── personal_records ──────────────────────────────────────────────────────────

def get_personal_records(profile_id: int) -> list[dict]:
    res = (
        get_client().table("personal_records")
        .select("*")
        .eq("profile_id", profile_id)
        .order("exercise_name")
        .execute()
    )
    return res.data or []


def upsert_personal_record(
    profile_id: int,
    exercise_name: str,
    record_type: str,
    value: float,
    date: str,
    notes: str = "",
) -> bool:
    c = get_client()
    existing = (
        c.table("personal_records")
        .select("value")
        .eq("profile_id", profile_id)
        .eq("exercise_name", exercise_name)
        .eq("record_type", record_type)
        .execute()
    )
    is_new = not existing.data or value > existing.data[0]["value"]
    c.table("personal_records").upsert(
        {
            "profile_id": profile_id, "exercise_name": exercise_name,
            "record_type": record_type, "value": value, "date": date, "notes": notes,
        },
        on_conflict="profile_id,exercise_name,record_type",
    ).execute()
    return is_new


# ── routine_templates ─────────────────────────────────────────────────────────

def get_all_templates(
    goal: str | None = None,
    level: str | None = None,
    days_per_week: int | None = None,
) -> list[dict]:
    q = get_client().table("routine_templates").select("*")
    if goal:          q = q.eq("goal", goal)
    if level:         q = q.eq("level", level)
    if days_per_week: q = q.eq("days_per_week", days_per_week)
    return q.order("goal").order("name").execute().data or []


def get_template_exercises(template_id: int) -> list[dict]:
    res = (
        get_client().table("template_exercises")
        .select("*")
        .eq("template_id", template_id)
        .order("day_name")
        .order("order_index")
        .execute()
    )
    return res.data or []


# ── perfect-weeks & posture-days counters (for gamification) ──────────────────

def count_perfect_weeks(profile_id: int) -> int:
    res = (
        get_client().table("weekly_goals")
        .select("id", count="exact")
        .eq("profile_id", profile_id)
        .eq("completed", True)
        .execute()
    )
    return res.count or 0


def count_posture_days(profile_id: int) -> int:
    """Days where every posture exercise was completed."""
    from data import POSTURE_ROUTINE
    n = len(POSTURE_ROUTINE)
    res = (
        get_client().table("posture")
        .select("date,completed")
        .eq("profile_id", profile_id)
        .eq("completed", True)
        .execute()
    )
    by_date: dict[str, int] = {}
    for r in (res.data or []):
        by_date[r["date"]] = by_date.get(r["date"], 0) + 1
    return sum(1 for cnt in by_date.values() if cnt >= n)
