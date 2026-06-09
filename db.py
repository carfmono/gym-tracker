import json
import re
import streamlit as st
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(date: str) -> str:
    if not _DATE_RE.match(date):
        raise ValueError(f"Formato de fecha inválido: {date!r}")
    return date


@contextmanager
def get_connection():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"], sslmode="require")
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _exec(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())


def _fetch_one(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def _fetch_all(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


# ── init ──────────────────────────────────────────────────────────────────────

def init_db():
    with get_connection() as conn:
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS sessions (
                date TEXT PRIMARY KEY,
                completed INTEGER DEFAULT 0
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS exercises (
                id TEXT PRIMARY KEY,
                date TEXT,
                exercise_id TEXT,
                completed INTEGER DEFAULT 0
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS posture (
                id TEXT PRIMARY KEY,
                date TEXT,
                exercise_id TEXT,
                completed INTEGER DEFAULT 0
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS routines (
                id SERIAL PRIMARY KEY,
                version TEXT,
                name TEXT,
                start_date TEXT,
                end_date TEXT,
                notes TEXT
            )
        """)
        row = _fetch_one(conn, "SELECT COUNT(*) AS cnt FROM routines")
        if row["cnt"] == 0:
            _exec(
                conn,
                "INSERT INTO routines (version, name, start_date, end_date, notes) VALUES (%s,%s,%s,%s,%s)",
                (
                    "v1",
                    "Rutina 1 — Base salud general",
                    "2026-06-09",
                    None,
                    "Plan inicial de retorno al gym. Tobillo/peroneal adaptado. Incluye trabajo de postura.",
                ),
            )


def migrate_db():
    """Idempotente — puede correr N veces sin efectos secundarios."""
    with get_connection() as conn:
        # 1. Perfiles
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS profiles (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at DATE DEFAULT CURRENT_DATE,
                training_days INTEGER DEFAULT 4,
                selected_days JSONB DEFAULT '[]',
                goal TEXT DEFAULT 'salud_general',
                weight_kg REAL,
                height_cm REAL,
                birth_year INTEGER,
                notes TEXT
            )
        """)
        _exec(conn, """
            INSERT INTO profiles (id, name, goal, training_days, selected_days)
            SELECT 1, 'Mono', 'salud_general', 6,
                '["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"]'::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM profiles WHERE id = 1)
        """)
        # Resincroniza la secuencia SERIAL para que el próximo INSERT use id > MAX(id)
        _exec(conn, "SELECT setval('profiles_id_seq', (SELECT MAX(id) FROM profiles))")

        # 2. profile_id en tablas existentes
        _exec(conn, "ALTER TABLE routines ADD COLUMN IF NOT EXISTS profile_id INTEGER DEFAULT 1")
        _exec(conn, "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS profile_id INTEGER DEFAULT 1")
        _exec(conn, "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS profile_id INTEGER DEFAULT 1")
        _exec(conn, "ALTER TABLE posture ADD COLUMN IF NOT EXISTS profile_id INTEGER DEFAULT 1")

        # 3. Días de rutina
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS routine_days (
                id SERIAL PRIMARY KEY,
                routine_id INTEGER REFERENCES routines(id),
                day_name TEXT,
                session_type TEXT,
                order_index INTEGER
            )
        """)

        # 4. Ejercicios personalizados
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS custom_exercises (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                routine_id INTEGER REFERENCES routines(id),
                day_name TEXT,
                name TEXT NOT NULL,
                sets TEXT,
                reps TEXT,
                rest_seconds INTEGER,
                notes TEXT,
                category TEXT,
                order_index INTEGER
            )
        """)

        # 5. Métricas corporales
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS body_metrics (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                date DATE NOT NULL,
                weight_kg REAL,
                body_fat_pct REAL,
                muscle_mass_kg REAL,
                waist_cm REAL,
                chest_cm REAL,
                notes TEXT,
                UNIQUE(profile_id, date)
            )
        """)

        # 6. Nutrición
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS nutrition_log (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                date DATE NOT NULL,
                meal_type TEXT,
                food_name TEXT NOT NULL,
                quantity_g REAL,
                calories REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                notes TEXT
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS nutrition_targets (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id) UNIQUE,
                calories_target REAL DEFAULT 1900,
                protein_target_g REAL DEFAULT 135,
                carbs_target_g REAL DEFAULT 200,
                fat_target_g REAL DEFAULT 65
            )
        """)
        _exec(conn, """
            INSERT INTO nutrition_targets
                (profile_id, calories_target, protein_target_g, carbs_target_g, fat_target_g)
            SELECT 1, 1900, 135, 200, 65
            WHERE NOT EXISTS (SELECT 1 FROM nutrition_targets WHERE profile_id = 1)
        """)

        # 7. Fotos de progreso
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS progress_photos (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                date DATE,
                storage_path TEXT,
                public_url TEXT,
                notes TEXT,
                next_check_date DATE
            )
        """)

        # 8. Índices
        _exec(conn, """
            CREATE INDEX IF NOT EXISTS idx_sessions_profile_date
                ON sessions(profile_id, date)
        """)
        _exec(conn, """
            CREATE INDEX IF NOT EXISTS idx_exercises_profile_date
                ON exercises(profile_id, date)
        """)
        _exec(conn, """
            CREATE INDEX IF NOT EXISTS idx_nutrition_profile_date
                ON nutrition_log(profile_id, date)
        """)
        _exec(conn, """
            CREATE INDEX IF NOT EXISTS idx_metrics_profile_date
                ON body_metrics(profile_id, date)
        """)

        # 9. Plantillas de rutinas
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS routine_templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                goal TEXT,
                level TEXT,
                days_per_week INTEGER,
                duration_weeks INTEGER DEFAULT 4,
                tags JSONB DEFAULT '[]',
                created_at DATE DEFAULT CURRENT_DATE
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS template_exercises (
                id SERIAL PRIMARY KEY,
                template_id INTEGER REFERENCES routine_templates(id),
                day_name TEXT,
                order_index INTEGER,
                exercise_name TEXT NOT NULL,
                sets TEXT,
                reps TEXT,
                rest_seconds INTEGER,
                notes TEXT,
                category TEXT,
                is_posture BOOLEAN DEFAULT FALSE,
                is_ankle BOOLEAN DEFAULT FALSE
            )
        """)

        # 10. XP y niveles
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS user_xp (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id) UNIQUE,
                total_xp INTEGER DEFAULT 0,
                current_level INTEGER DEFAULT 1,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_session_date DATE,
                total_sessions INTEGER DEFAULT 0,
                total_exercises_completed INTEGER DEFAULT 0
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS xp_log (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                event_type TEXT NOT NULL,
                xp_gained INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # 11. Achievements
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                xp_reward INTEGER DEFAULT 0,
                category TEXT,
                condition_type TEXT,
                condition_value INTEGER
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS user_achievements (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                achievement_id INTEGER REFERENCES achievements(id),
                unlocked_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(profile_id, achievement_id)
            )
        """)

        # 12. Metas semanales y records
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS weekly_goals (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                week_start DATE NOT NULL,
                sessions_goal INTEGER DEFAULT 4,
                exercises_goal INTEGER DEFAULT 30,
                posture_days_goal INTEGER DEFAULT 5,
                sessions_done INTEGER DEFAULT 0,
                exercises_done INTEGER DEFAULT 0,
                posture_days_done INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                UNIQUE(profile_id, week_start)
            )
        """)
        _exec(conn, """
            CREATE TABLE IF NOT EXISTS personal_records (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER REFERENCES profiles(id),
                exercise_name TEXT NOT NULL,
                record_type TEXT DEFAULT 'reps',
                value REAL NOT NULL,
                date DATE NOT NULL,
                notes TEXT,
                UNIQUE(profile_id, exercise_name, record_type)
            )
        """)

        # Índices nuevos
        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_xp_log_profile ON xp_log(profile_id, created_at DESC)")
        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_user_achievements_profile ON user_achievements(profile_id)")
        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_weekly_goals_profile_week ON weekly_goals(profile_id, week_start)")


def seed_achievements():
    """Solo inserta si la tabla está vacía."""
    _ACHIEVEMENTS = [
        # ── Consistencia ──────────────────────────────────────────────────────
        ("primera_sesion",  "🏁 Primera sesión",        "Completa tu primera sesión de entrenamiento",       "🏁", 50,   "consistencia", "sessions_total",    1),
        ("semana_1",        "🔥 Una semana activo",      "Completa 7 sesiones en total",                      "🔥", 100,  "consistencia", "sessions_total",    7),
        ("mes_1",           "📅 Un mes en el gym",       "Acumula 30 sesiones completadas",                   "📅", 300,  "consistencia", "sessions_total",    30),
        ("tres_meses",      "💪 Tres meses",             "90 sesiones — ya es un hábito real",                "💪", 750,  "consistencia", "sessions_total",    90),
        ("seis_meses",      "🏆 Seis meses",             "180 sesiones. Constancia total.",                   "🏆", 1500, "consistencia", "sessions_total",    180),
        ("un_año",          "👑 Un año",                 "365 sesiones. Leyenda viva.",                       "👑", 3000, "consistencia", "sessions_total",    365),
        ("racha_7",         "🔥×7 Racha de 7 días",      "7 días consecutivos de entrenamiento",              "⚡", 150,  "consistencia", "streak_days",       7),
        ("racha_14",        "⚡ Racha de 14 días",       "14 días sin parar",                                 "⚡", 300,  "consistencia", "streak_days",       14),
        ("racha_30",        "🌟 Racha de 30 días",       "Un mes completo de racha",                          "🌟", 600,  "consistencia", "streak_days",       30),
        ("semana_perfecta", "✨ Semana perfecta",        "Completa todas las sesiones programadas en una semana", "✨", 200, "consistencia", "perfect_weeks",  1),
        # ── Volumen ───────────────────────────────────────────────────────────
        ("ejercicios_50",   "💥 50 ejercicios",          "Completa 50 ejercicios en total",                   "💥", 100,  "volumen", "exercises_total",   50),
        ("ejercicios_100",  "🎯 100 ejercicios",         "100 ejercicios completados",                        "🎯", 200,  "volumen", "exercises_total",   100),
        ("ejercicios_250",  "🏋️ 250 ejercicios",        "250 ejercicios — el volumen suma",                  "🏋️", 400, "volumen", "exercises_total",   250),
        ("ejercicios_500",  "🔱 500 ejercicios",         "500 ejercicios. Máquina de trabajo.",               "🔱", 750,  "volumen", "exercises_total",   500),
        ("ejercicios_1000", "🌌 1000 ejercicios",        "1000 ejercicios completados. Élite.",               "🌌", 1500, "volumen", "exercises_total",   1000),
        ("postura_7",       "🧘 7 días de postura",      "Completa la rutina de postura 7 días",              "🧘", 100,  "volumen", "posture_days",      7),
        ("postura_30",      "🌿 30 días de postura",     "30 días consecutivos de postura",                   "🌿", 400,  "volumen", "posture_days",      30),
        ("madrugador",      "🌅 Madrugador",             "10 sesiones registradas en un lunes",               "🌅", 200,  "volumen", "sessions_total",    10),
        ("nocturno",        "🌙 Búho nocturno",          "10 sesiones de sábado completadas",                 "🌙", 200,  "volumen", "sessions_total",    10),
        ("fin_de_semana",   "🏖️ Guerrero de fin de semana", "10 sesiones en fin de semana",                  "🏖️", 150, "volumen", "sessions_total",    10),
        # ── Rutinas ───────────────────────────────────────────────────────────
        ("primera_rutina",      "📋 Primera rutina",        "Activa tu primera rutina",                      "📋", 100,  "rutinas", "routines_completed", 1),
        ("rutinas_3",           "📚 3 rutinas",             "Completa 3 rutinas distintas",                  "📚", 250,  "rutinas", "routines_completed", 3),
        ("rutinas_5",           "🎓 5 rutinas",             "5 rutinas completadas",                         "🎓", 500,  "rutinas", "routines_completed", 5),
        ("rutinas_10",          "🏛️ 10 rutinas",           "10 rutinas. Diversidad total.",                  "🏛️", 1000, "rutinas", "routines_completed", 10),
        ("rutinas_25",          "🌠 ¡Las 25 rutinas!",      "Completaste las 25 plantillas. Leyenda.",        "🌠", 5000, "rutinas", "routines_completed", 25),
        ("fuerza_iniciado",     "⚔️ Iniciado en Fuerza",   "Completa una rutina de fuerza",                  "⚔️", 200, "rutinas", "routines_completed", 1),
        ("hipertrofia_iniciado","💪 Iniciado en Hipertrofia","Completa una rutina de hipertrofia",            "💪", 200, "rutinas", "routines_completed", 1),
        ("cardio_iniciado",     "🏃 Iniciado en Cardio",    "Completa una rutina de pérdida de grasa",        "🏃", 200, "rutinas", "routines_completed", 1),
        ("movilidad_iniciado",  "🧘 Iniciado en Movilidad", "Completa una rutina de movilidad",               "🧘", 200, "rutinas", "routines_completed", 1),
        ("explorador",          "🗺️ Explorador",            "Prueba 5 categorías de rutinas distintas",       "🗺️", 300, "rutinas", "routines_completed", 5),
        # ── Niveles ───────────────────────────────────────────────────────────
        ("nivel_2",   "⭐ Nivel 2",        "Alcanza el nivel 2",   "⭐", 0,  "niveles", "level_reached", 2),
        ("nivel_5",   "⭐⭐ Nivel 5",      "Alcanza el nivel 5",   "⭐", 0,  "niveles", "level_reached", 5),
        ("nivel_10",  "🌟 Nivel 10",       "Alcanza el nivel 10",  "🌟", 0,  "niveles", "level_reached", 10),
        ("nivel_15",  "💫 Nivel 15",       "Alcanza el nivel 15",  "💫", 0,  "niveles", "level_reached", 15),
        ("nivel_20",  "✨ Nivel 20",       "Alcanza el nivel 20",  "✨", 0,  "niveles", "level_reached", 20),
        ("nivel_25",  "🏆 Nivel 25",       "Alcanza el nivel 25",  "🏆", 0,  "niveles", "level_reached", 25),
        ("nivel_30",  "👑 Nivel 30",       "Alcanza el nivel 30",  "👑", 0,  "niveles", "level_reached", 30),
        ("nivel_40",  "🔱 Nivel 40",       "Alcanza el nivel 40",  "🔱", 0,  "niveles", "level_reached", 40),
        ("nivel_50",  "🌌 Nivel 50",       "Alcanza el nivel 50",  "🌌", 0,  "niveles", "level_reached", 50),
        ("nivel_100", "🌠 Leyenda Nivel 100","Nivel máximo alcanzado","🌠",0, "niveles", "level_reached", 100),
    ]
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT COUNT(*) AS cnt FROM achievements")
        if row["cnt"] > 0:
            return
        for code, name, desc, icon, xp, cat, ctype, cval in _ACHIEVEMENTS:
            _exec(
                conn,
                """INSERT INTO achievements
                   (code, name, description, icon, xp_reward, category, condition_type, condition_value)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (code, name, desc, icon, xp, cat, ctype, cval),
            )


# ── user_xp ───────────────────────────────────────────────────────────────────

def init_user_xp(profile_id: int = 1):
    with get_connection() as conn:
        _exec(
            conn,
            """INSERT INTO user_xp (profile_id) VALUES (%s)
               ON CONFLICT (profile_id) DO NOTHING""",
            (profile_id,),
        )


def get_user_xp(profile_id: int = 1) -> dict | None:
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT * FROM user_xp WHERE profile_id=%s", (profile_id,))
        return dict(row) if row else None


def update_user_xp(profile_id: int, **kwargs):
    allowed = {
        "total_xp", "current_level", "current_streak", "longest_streak",
        "last_session_date", "total_sessions", "total_exercises_completed",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clauses = [f"{k}=%s" for k in fields]
    values = list(fields.values()) + [profile_id]
    _sql = f"UPDATE user_xp SET {', '.join(set_clauses)} WHERE profile_id=%s"
    with get_connection() as conn:
        _exec(conn, _sql, values)


def add_xp_log(profile_id: int, event_type: str, xp_gained: int, description: str = "") -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xp_log (profile_id, event_type, xp_gained, description) VALUES (%s,%s,%s,%s) RETURNING id",
                (profile_id, event_type, xp_gained, description),
            )
            return cur.fetchone()["id"]


def get_xp_log(profile_id: int, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM xp_log WHERE profile_id=%s ORDER BY created_at DESC LIMIT %s",
            (profile_id, limit),
        )
        return [dict(r) for r in rows]


def xp_log_exists_today(profile_id: int, event_type: str, description: str) -> bool:
    with get_connection() as conn:
        row = _fetch_one(
            conn,
            """SELECT id FROM xp_log
               WHERE profile_id=%s AND event_type=%s AND description=%s
               AND created_at::date = CURRENT_DATE""",
            (profile_id, event_type, description),
        )
        return row is not None


def get_all_achievements() -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT * FROM achievements ORDER BY category, condition_value")
        return [dict(r) for r in rows]


def get_user_achievements(profile_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            """SELECT a.*, ua.unlocked_at FROM achievements a
               JOIN user_achievements ua ON a.id = ua.achievement_id
               WHERE ua.profile_id=%s ORDER BY ua.unlocked_at DESC""",
            (profile_id,),
        )
        return [dict(r) for r in rows]


def unlock_achievement(profile_id: int, achievement_id: int) -> bool:
    """Retorna True si fue desbloqueado ahora (no existía antes)."""
    with get_connection() as conn:
        try:
            _exec(
                conn,
                "INSERT INTO user_achievements (profile_id, achievement_id) VALUES (%s,%s)",
                (profile_id, achievement_id),
            )
            return True
        except Exception:
            conn.rollback()
            return False


# ── weekly_goals ──────────────────────────────────────────────────────────────

def get_weekly_goals(profile_id: int, week_start: str) -> dict | None:
    with get_connection() as conn:
        row = _fetch_one(
            conn,
            "SELECT * FROM weekly_goals WHERE profile_id=%s AND week_start=%s",
            (profile_id, week_start),
        )
        return dict(row) if row else None


def upsert_weekly_goals(profile_id: int, week_start: str, **kwargs):
    allowed = {"sessions_goal", "exercises_goal", "posture_days_goal",
               "sessions_done", "exercises_done", "posture_days_done", "completed"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    with get_connection() as conn:
        existing = _fetch_one(
            conn,
            "SELECT id FROM weekly_goals WHERE profile_id=%s AND week_start=%s",
            (profile_id, week_start),
        )
        if existing:
            if fields:
                set_clauses = [f"{k}=%s" for k in fields]
                values = list(fields.values()) + [profile_id, week_start]
                _exec(conn, f"UPDATE weekly_goals SET {', '.join(set_clauses)} WHERE profile_id=%s AND week_start=%s", values)
        else:
            _exec(
                conn,
                "INSERT INTO weekly_goals (profile_id, week_start) VALUES (%s,%s)",
                (profile_id, week_start),
            )
            if fields:
                set_clauses = [f"{k}=%s" for k in fields]
                values = list(fields.values()) + [profile_id, week_start]
                _exec(conn, f"UPDATE weekly_goals SET {', '.join(set_clauses)} WHERE profile_id=%s AND week_start=%s", values)


# ── personal_records ──────────────────────────────────────────────────────────

def get_personal_records(profile_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM personal_records WHERE profile_id=%s ORDER BY exercise_name",
            (profile_id,),
        )
        return [dict(r) for r in rows]


def upsert_personal_record(
    profile_id: int,
    exercise_name: str,
    record_type: str,
    value: float,
    date: str,
    notes: str = "",
) -> bool:
    """Retorna True si es un nuevo record (supera el anterior)."""
    with get_connection() as conn:
        existing = _fetch_one(
            conn,
            "SELECT value FROM personal_records WHERE profile_id=%s AND exercise_name=%s AND record_type=%s",
            (profile_id, exercise_name, record_type),
        )
        is_new_record = existing is None or value > existing["value"]
        _exec(
            conn,
            """INSERT INTO personal_records
               (profile_id, exercise_name, record_type, value, date, notes)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (profile_id, exercise_name, record_type)
               DO UPDATE SET value=%s, date=%s, notes=%s""",
            (profile_id, exercise_name, record_type, value, date, notes, value, date, notes),
        )
        return is_new_record


# ── routine_templates ─────────────────────────────────────────────────────────

def get_all_templates(goal: str | None = None, level: str | None = None,
                      days_per_week: int | None = None) -> list[dict]:
    sql = "SELECT * FROM routine_templates WHERE 1=1"
    params: list = []
    if goal:
        sql += " AND goal=%s"
        params.append(goal)
    if level:
        sql += " AND level=%s"
        params.append(level)
    if days_per_week:
        sql += " AND days_per_week=%s"
        params.append(days_per_week)
    sql += " ORDER BY goal, level, name"
    with get_connection() as conn:
        rows = _fetch_all(conn, sql, params)
        return [dict(r) for r in rows]


def get_template_exercises(template_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM template_exercises WHERE template_id=%s ORDER BY day_name, order_index",
            (template_id,),
        )
        return [dict(r) for r in rows]


# ── sessions ──────────────────────────────────────────────────────────────────

def get_session(date: str) -> bool:
    _validate_date(date)
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT completed FROM sessions WHERE date=%s", (date,))
        return bool(row["completed"]) if row else False


def toggle_session(date: str):
    _validate_date(date)
    current = get_session(date)
    new_val = 0 if current else 1
    with get_connection() as conn:
        _exec(
            conn,
            """
            INSERT INTO sessions (date, completed) VALUES (%s,%s)
            ON CONFLICT (date) DO UPDATE SET completed=%s
            """,
            (date, new_val, new_val),
        )


# ── exercises ─────────────────────────────────────────────────────────────────

def get_exercise(date: str, exercise_id: str) -> bool:
    _validate_date(date)
    row_id = f"{date}:{exercise_id}"
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT completed FROM exercises WHERE id=%s", (row_id,))
        return bool(row["completed"]) if row else False


def set_exercise(date: str, exercise_id: str, completed: bool):
    _validate_date(date)
    row_id = f"{date}:{exercise_id}"
    val = 1 if completed else 0
    with get_connection() as conn:
        _exec(
            conn,
            """
            INSERT INTO exercises (id, date, exercise_id, completed) VALUES (%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET completed=%s
            """,
            (row_id, date, exercise_id, val, val),
        )


def get_exercises_for_date(date: str) -> dict:
    _validate_date(date)
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT exercise_id, completed FROM exercises WHERE date=%s", (date,))
        return {r["exercise_id"]: bool(r["completed"]) for r in rows}


# ── posture ───────────────────────────────────────────────────────────────────

def get_posture(date: str, exercise_id: str) -> bool:
    _validate_date(date)
    row_id = f"{date}:{exercise_id}"
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT completed FROM posture WHERE id=%s", (row_id,))
        return bool(row["completed"]) if row else False


def set_posture(date: str, exercise_id: str, completed: bool):
    _validate_date(date)
    row_id = f"{date}:{exercise_id}"
    val = 1 if completed else 0
    with get_connection() as conn:
        _exec(
            conn,
            """
            INSERT INTO posture (id, date, exercise_id, completed) VALUES (%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET completed=%s
            """,
            (row_id, date, exercise_id, val, val),
        )


def get_posture_for_date(date: str) -> dict:
    _validate_date(date)
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT exercise_id, completed FROM posture WHERE date=%s", (date,))
        return {r["exercise_id"]: bool(r["completed"]) for r in rows}


# ── stats helpers ─────────────────────────────────────────────────────────────

def get_stats_for_dates(dates: list[str]) -> dict:
    if not dates:
        return {}
    for d in dates:
        _validate_date(d)
    placeholders = ",".join(["%s"] * len(dates))
    with get_connection() as conn:
        sessions = _fetch_all(
            conn, f"SELECT date, completed FROM sessions WHERE date IN ({placeholders})", dates
        )
        exercises = _fetch_all(
            conn, f"SELECT date, exercise_id, completed FROM exercises WHERE date IN ({placeholders})", dates
        )
        posture_rows = _fetch_all(
            conn, f"SELECT date, exercise_id, completed FROM posture WHERE date IN ({placeholders})", dates
        )
    return {
        "sessions": {r["date"]: bool(r["completed"]) for r in sessions},
        "exercises": exercises,
        "posture": posture_rows,
    }


# ── routines ──────────────────────────────────────────────────────────────────

def get_all_routines() -> list:
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT * FROM routines ORDER BY id")
        return [dict(r) for r in rows]


def add_routine(version: str, name: str, start_date: str, notes: str):
    with get_connection() as conn:
        _exec(conn, "UPDATE routines SET end_date=%s WHERE end_date IS NULL", (start_date,))
        _exec(
            conn,
            "INSERT INTO routines (version, name, start_date, end_date, notes) VALUES (%s,%s,%s,%s,%s)",
            (version, name, start_date, None, notes),
        )


def get_active_routine(profile_id: int = 1) -> dict | None:
    with get_connection() as conn:
        row = _fetch_one(
            conn,
            "SELECT * FROM routines WHERE profile_id=%s AND end_date IS NULL ORDER BY id DESC LIMIT 1",
            (profile_id,),
        )
        return dict(row) if row else None


def get_routines_by_profile(profile_id: int = 1) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM routines WHERE profile_id=%s ORDER BY id",
            (profile_id,),
        )
        return [dict(r) for r in rows]


def create_routine(profile_id: int, version: str, name: str, start_date: str, notes: str):
    with get_connection() as conn:
        _exec(
            conn,
            "UPDATE routines SET end_date=%s WHERE profile_id=%s AND end_date IS NULL",
            (start_date, profile_id),
        )
        _exec(
            conn,
            """
            INSERT INTO routines (profile_id, version, name, start_date, end_date, notes)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (profile_id, version, name, start_date, None, notes),
        )


# ── profiles ──────────────────────────────────────────────────────────────────

def get_all_profiles() -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT * FROM profiles ORDER BY id")
        return [dict(r) for r in rows]


def get_profile(profile_id: int = 1) -> dict | None:
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT * FROM profiles WHERE id=%s", (profile_id,))
        return dict(row) if row else None


def create_profile(
    name: str,
    goal: str = "salud_general",
    training_days: int = 4,
    selected_days: list | None = None,
    weight_kg: float | None = None,
    height_cm: float | None = None,
    birth_year: int | None = None,
    notes: str | None = None,
) -> int:
    selected_days_json = json.dumps(selected_days or [])
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO profiles
                    (name, goal, training_days, selected_days, weight_kg, height_cm, birth_year, notes)
                VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                RETURNING id
                """,
                (name, goal, training_days, selected_days_json, weight_kg, height_cm, birth_year, notes),
            )
            return cur.fetchone()["id"]


def update_profile(profile_id: int, **kwargs):
    if not kwargs:
        return
    allowed = {
        "name", "goal", "training_days", "selected_days",
        "weight_kg", "height_cm", "birth_year", "notes",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clauses = []
    values = []
    for k, v in fields.items():
        if k == "selected_days":
            set_clauses.append(f"{k}=%s::jsonb")
            values.append(json.dumps(v))
        else:
            set_clauses.append(f"{k}=%s")
            values.append(v)
    values.append(profile_id)
    sql = f"UPDATE profiles SET {', '.join(set_clauses)} WHERE id=%s"
    with get_connection() as conn:
        _exec(conn, sql, values)


# ── body_metrics ──────────────────────────────────────────────────────────────

def get_body_metrics(profile_id: int = 1, limit: int = 90) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM body_metrics WHERE profile_id=%s ORDER BY date DESC LIMIT %s",
            (profile_id, limit),
        )
        return [dict(r) for r in rows]


def get_body_metric_on_date(profile_id: int, date: str) -> dict | None:
    with get_connection() as conn:
        row = _fetch_one(
            conn,
            "SELECT * FROM body_metrics WHERE profile_id=%s AND date=%s",
            (profile_id, date),
        )
        return dict(row) if row else None


def upsert_body_metric(
    profile_id: int,
    date: str,
    weight_kg: float | None = None,
    body_fat_pct: float | None = None,
    muscle_mass_kg: float | None = None,
    waist_cm: float | None = None,
    chest_cm: float | None = None,
    notes: str | None = None,
):
    with get_connection() as conn:
        _exec(
            conn,
            """
            INSERT INTO body_metrics
                (profile_id, date, weight_kg, body_fat_pct, muscle_mass_kg, waist_cm, chest_cm, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (profile_id, date) DO UPDATE SET
                weight_kg      = COALESCE(EXCLUDED.weight_kg, body_metrics.weight_kg),
                body_fat_pct   = COALESCE(EXCLUDED.body_fat_pct, body_metrics.body_fat_pct),
                muscle_mass_kg = COALESCE(EXCLUDED.muscle_mass_kg, body_metrics.muscle_mass_kg),
                waist_cm       = COALESCE(EXCLUDED.waist_cm, body_metrics.waist_cm),
                chest_cm       = COALESCE(EXCLUDED.chest_cm, body_metrics.chest_cm),
                notes          = COALESCE(EXCLUDED.notes, body_metrics.notes)
            """,
            (profile_id, date, weight_kg, body_fat_pct, muscle_mass_kg, waist_cm, chest_cm, notes),
        )


# ── nutrition ─────────────────────────────────────────────────────────────────

def get_nutrition_targets(profile_id: int = 1) -> dict | None:
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT * FROM nutrition_targets WHERE profile_id=%s", (profile_id,))
        return dict(row) if row else None


def update_nutrition_targets(
    profile_id: int,
    calories_target: float,
    protein_target_g: float,
    carbs_target_g: float,
    fat_target_g: float,
):
    with get_connection() as conn:
        _exec(
            conn,
            """
            INSERT INTO nutrition_targets
                (profile_id, calories_target, protein_target_g, carbs_target_g, fat_target_g)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (profile_id) DO UPDATE SET
                calories_target  = EXCLUDED.calories_target,
                protein_target_g = EXCLUDED.protein_target_g,
                carbs_target_g   = EXCLUDED.carbs_target_g,
                fat_target_g     = EXCLUDED.fat_target_g
            """,
            (profile_id, calories_target, protein_target_g, carbs_target_g, fat_target_g),
        )


def get_nutrition_log(profile_id: int, date: str) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM nutrition_log WHERE profile_id=%s AND date=%s ORDER BY id",
            (profile_id, date),
        )
        return [dict(r) for r in rows]


def get_nutrition_log_range(profile_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM nutrition_log WHERE profile_id=%s AND date BETWEEN %s AND %s ORDER BY date, id",
            (profile_id, date_from, date_to),
        )
        return [dict(r) for r in rows]


def add_nutrition_entry(
    profile_id: int,
    date: str,
    food_name: str,
    meal_type: str | None = None,
    quantity_g: float | None = None,
    calories: float | None = None,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    notes: str | None = None,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nutrition_log
                    (profile_id, date, meal_type, food_name, quantity_g,
                     calories, protein_g, carbs_g, fat_g, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (profile_id, date, meal_type, food_name, quantity_g,
                 calories, protein_g, carbs_g, fat_g, notes),
            )
            return cur.fetchone()["id"]


def delete_nutrition_entry(entry_id: int, profile_id: int):
    with get_connection() as conn:
        _exec(
            conn,
            "DELETE FROM nutrition_log WHERE id=%s AND profile_id=%s",
            (entry_id, profile_id),
        )


# ── custom_exercises ──────────────────────────────────────────────────────────

def get_custom_exercises(profile_id: int, day_name: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if day_name:
            rows = _fetch_all(
                conn,
                "SELECT * FROM custom_exercises WHERE profile_id=%s AND day_name=%s ORDER BY order_index, id",
                (profile_id, day_name),
            )
        else:
            rows = _fetch_all(
                conn,
                "SELECT * FROM custom_exercises WHERE profile_id=%s ORDER BY day_name, order_index, id",
                (profile_id,),
            )
        return [dict(r) for r in rows]


def add_custom_exercise(
    profile_id: int,
    day_name: str,
    name: str,
    routine_id: int | None = None,
    sets: str | None = None,
    reps: str | None = None,
    rest_seconds: int | None = None,
    notes: str | None = None,
    category: str | None = None,
    order_index: int | None = None,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO custom_exercises
                    (profile_id, routine_id, day_name, name, sets, reps,
                     rest_seconds, notes, category, order_index)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (profile_id, routine_id, day_name, name, sets, reps,
                 rest_seconds, notes, category, order_index),
            )
            return cur.fetchone()["id"]


def delete_custom_exercise(exercise_id: int, profile_id: int):
    with get_connection() as conn:
        _exec(
            conn,
            "DELETE FROM custom_exercises WHERE id=%s AND profile_id=%s",
            (exercise_id, profile_id),
        )


# ── progress_photos ───────────────────────────────────────────────────────────

def get_progress_photos(profile_id: int = 1) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM progress_photos WHERE profile_id=%s ORDER BY date DESC",
            (profile_id,),
        )
        return [dict(r) for r in rows]


def add_progress_photo(
    profile_id: int,
    date: str,
    public_url: str,
    storage_path: str | None = None,
    notes: str | None = None,
    next_check_date: str | None = None,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO progress_photos
                    (profile_id, date, storage_path, public_url, notes, next_check_date)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (profile_id, date, storage_path, public_url, notes, next_check_date),
            )
            return cur.fetchone()["id"]


def delete_progress_photo(photo_id: int, profile_id: int):
    with get_connection() as conn:
        _exec(
            conn,
            "DELETE FROM progress_photos WHERE id=%s AND profile_id=%s",
            (photo_id, profile_id),
        )


# ── routine_days ──────────────────────────────────────────────────────────────

def get_routine_days(routine_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = _fetch_all(
            conn,
            "SELECT * FROM routine_days WHERE routine_id=%s ORDER BY order_index",
            (routine_id,),
        )
        return [dict(r) for r in rows]


def set_routine_days(routine_id: int, days: list[dict]):
    """Reemplaza completamente los días de una rutina. days = [{day_name, session_type, order_index}]"""
    with get_connection() as conn:
        _exec(conn, "DELETE FROM routine_days WHERE routine_id=%s", (routine_id,))
        for d in days:
            _exec(
                conn,
                "INSERT INTO routine_days (routine_id, day_name, session_type, order_index) VALUES (%s,%s,%s,%s)",
                (routine_id, d.get("day_name"), d.get("session_type"), d.get("order_index")),
            )


# ── routine_templates seed ─────────────────────────────────────────────────────

def seed_routine_templates():
    """Solo inserta si la tabla está vacía."""
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT COUNT(*) AS cnt FROM routine_templates")
        if row["cnt"] > 0:
            return

        # ── helper local ──────────────────────────────────────────────────────
        def _insert_template(name, description, goal, level, days_per_week, duration_weeks, tags):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO routine_templates
                        (name, description, goal, level, days_per_week, duration_weeks, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, description, goal, level, days_per_week, duration_weeks, json.dumps(tags)),
                )
                return cur.fetchone()["id"]

        def _insert_exercise(tid, day_name, order_index, name, sets, reps,
                             rest_seconds=90, category=None, notes=None,
                             is_posture=False, is_ankle=False):
            _exec(
                conn,
                """
                INSERT INTO template_exercises
                    (template_id, day_name, order_index, exercise_name, sets, reps,
                     rest_seconds, category, notes, is_posture, is_ankle)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (tid, day_name, order_index, name, sets, reps,
                 rest_seconds, category, notes, is_posture, is_ankle),
            )

        # ══════════════════════════════════════════════════════════════════════
        # GRUPO A — FUERZA
        # ══════════════════════════════════════════════════════════════════════

        # A1 — Fuerza Base 3 días
        tid = _insert_template(
            "Fuerza Base 3 días",
            "Full body de lunes, miércoles y viernes. Énfasis en patrones básicos de fuerza con máquinas y barras.",
            "fuerza", "principiante", 3, 8,
            ["fuerza", "full_body", "principiante", "máquinas"],
        )
        for day in ["Lunes", "Miércoles", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",          "4", "5", 120, "piernas")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",        "4", "5", 120, "empuje")
            _insert_exercise(tid, day, 3, "Remo en máquina sentado agarre neutro","4", "5", 120, "jale")
            _insert_exercise(tid, day, 4, "Press militar en máquina",            "4", "5", 120, "empuje")
            _insert_exercise(tid, day, 5, "Curl en polea baja con barra",        "4", "5",  90, "jale")
            _insert_exercise(tid, day, 6, "Extensión de tríceps en polea (cuerda)","4","5", 90, "empuje")

        # A2 — Upper/Lower Fuerza
        tid = _insert_template(
            "Upper/Lower Fuerza",
            "División upper/lower 4 días con progresión de fuerza 5×5. Upper A empuje, Upper B jale, Lower A y B.",
            "fuerza", "intermedio", 4, 8,
            ["fuerza", "upper_lower", "intermedio", "5x5"],
        )
        # Upper A — Lunes (empuje)
        _insert_exercise(tid, "Lunes",   1, "Press de banca plana (barra)",          "5", "5", 180, "empuje")
        _insert_exercise(tid, "Lunes",   2, "Press inclinado con mancuernas",         "3", "6", 120, "empuje")
        _insert_exercise(tid, "Lunes",   3, "Press militar en máquina",               "4", "5", 150, "empuje")
        _insert_exercise(tid, "Lunes",   4, "Extensión de tríceps en polea (cuerda)", "3", "8",  90, "empuje")
        # Lower A — Martes
        _insert_exercise(tid, "Martes",  1, "Prensa de piernas máquina",              "5", "5", 180, "piernas")
        _insert_exercise(tid, "Martes",  2, "Extensión de cuádriceps máquina",        "3", "8",  90, "piernas")
        _insert_exercise(tid, "Martes",  3, "Curl femoral tumbado máquina",           "3", "8",  90, "piernas")
        _insert_exercise(tid, "Martes",  4, "Hip thrust con barra o mancuerna",       "4", "6", 120, "piernas")
        # Upper B — Jueves (jale)
        _insert_exercise(tid, "Jueves",  1, "Remo en máquina sentado agarre neutro",  "5", "5", 180, "jale")
        _insert_exercise(tid, "Jueves",  2, "Jalón al pecho en polea agarre ancho",   "4", "6", 120, "jale")
        _insert_exercise(tid, "Jueves",  3, "Remo en polea baja un brazo a la vez",   "3", "8",  90, "jale")
        _insert_exercise(tid, "Jueves",  4, "Curl en polea baja con barra",           "3", "8",  90, "jale")
        # Lower B — Viernes
        _insert_exercise(tid, "Viernes", 1, "Prensa de piernas máquina (agarre sumo)","4", "6", 150, "piernas")
        _insert_exercise(tid, "Viernes", 2, "Hip thrust con barra o mancuerna",       "4", "5", 150, "piernas")
        _insert_exercise(tid, "Viernes", 3, "Curl femoral tumbado máquina",           "4", "6", 120, "piernas")
        _insert_exercise(tid, "Viernes", 4, "Abducción en máquina",                   "3", "12",  60, "piernas")

        # A3 — 5×5 StrongLifts adaptado
        tid = _insert_template(
            "5×5 StrongLifts adaptado",
            "Protocolo StrongLifts adaptado a máquinas. Workout A (Lun/Vie) y Workout B (Mié) alternados.",
            "fuerza", "intermedio", 3, 12,
            ["fuerza", "5x5", "stronglifts", "intermedio"],
        )
        for day in ["Lunes", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "5", "5", 180, "piernas",
                             notes="Workout A")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "5", "5", 180, "empuje",
                             notes="Workout A")
            _insert_exercise(tid, day, 3, "Remo en máquina sentado agarre neutro",  "5", "5", 180, "jale",
                             notes="Workout A — agarre neutro")
        _insert_exercise(tid, "Miércoles", 1, "Prensa de piernas máquina",          "5", "5", 180, "piernas",
                         notes="Workout B")
        _insert_exercise(tid, "Miércoles", 2, "Press militar en máquina",           "5", "5", 180, "empuje",
                         notes="Workout B")
        _insert_exercise(tid, "Miércoles", 3, "Curl femoral tumbado máquina",       "1", "5", 120, "piernas",
                         notes="Workout B")

        # A4 — PPL Fuerza Avanzada
        tid = _insert_template(
            "PPL Fuerza Avanzada",
            "Push/Pull/Legs 6 días con énfasis en fuerza. A y B alternan variando agarre y ángulo cada semana.",
            "fuerza", "avanzado", 6, 12,
            ["fuerza", "ppl", "avanzado", "6_dias"],
        )
        # Push A — Lunes
        _insert_exercise(tid, "Lunes",   1, "Press de banca plana (barra)",          "5", "4", 180, "empuje", notes="Push A")
        _insert_exercise(tid, "Lunes",   2, "Press inclinado con mancuernas",         "4", "5", 150, "empuje", notes="Push A")
        _insert_exercise(tid, "Lunes",   3, "Press militar en máquina",               "4", "5", 150, "empuje", notes="Push A")
        _insert_exercise(tid, "Lunes",   4, "Extensión de tríceps en polea (cuerda)", "4", "6",  90, "empuje", notes="Push A")
        # Pull A — Martes
        _insert_exercise(tid, "Martes",  1, "Remo en máquina sentado agarre neutro",  "5", "4", 180, "jale",   notes="Pull A")
        _insert_exercise(tid, "Martes",  2, "Jalón al pecho en polea agarre ancho",   "4", "5", 150, "jale",   notes="Pull A")
        _insert_exercise(tid, "Martes",  3, "Remo en polea baja un brazo a la vez",   "3", "6", 120, "jale",   notes="Pull A")
        _insert_exercise(tid, "Martes",  4, "Curl en polea baja con barra",           "4", "6",  90, "jale",   notes="Pull A")
        # Legs A — Miércoles
        _insert_exercise(tid, "Miércoles",1, "Prensa de piernas máquina",             "5", "4", 180, "piernas",notes="Legs A")
        _insert_exercise(tid, "Miércoles",2, "Extensión de cuádriceps máquina",       "3", "8",  90, "piernas",notes="Legs A")
        _insert_exercise(tid, "Miércoles",3, "Curl femoral tumbado máquina",          "3", "8",  90, "piernas",notes="Legs A")
        _insert_exercise(tid, "Miércoles",4, "Hip thrust con barra o mancuerna",      "4", "5", 150, "piernas",notes="Legs A")
        # Push B — Jueves (variación ángulo/agarre)
        _insert_exercise(tid, "Jueves",  1, "Press inclinado con mancuernas",         "5", "4", 180, "empuje", notes="Push B — ángulo alto")
        _insert_exercise(tid, "Jueves",  2, "Press de banca plana (barra)",           "4", "5", 150, "empuje", notes="Push B")
        _insert_exercise(tid, "Jueves",  3, "Press militar en máquina",               "4", "5", 150, "empuje", notes="Push B")
        _insert_exercise(tid, "Jueves",  4, "Extensión de tríceps en polea (cuerda)", "4", "6",  90, "empuje", notes="Push B")
        # Pull B — Viernes (variación agarre)
        _insert_exercise(tid, "Viernes", 1, "Jalón al pecho en polea agarre ancho",   "5", "4", 180, "jale",   notes="Pull B — agarre ancho")
        _insert_exercise(tid, "Viernes", 2, "Remo en máquina sentado agarre neutro",  "4", "5", 150, "jale",   notes="Pull B")
        _insert_exercise(tid, "Viernes", 3, "Remo en polea baja un brazo a la vez",   "3", "6", 120, "jale",   notes="Pull B")
        _insert_exercise(tid, "Viernes", 4, "Curl en polea baja con cuerda martillo", "4", "6",  90, "jale",   notes="Pull B — martillo")
        # Legs B — Sábado
        _insert_exercise(tid, "Sábado",  1, "Prensa de piernas máquina (agarre sumo)","5", "4", 180, "piernas",notes="Legs B")
        _insert_exercise(tid, "Sábado",  2, "Curl femoral tumbado máquina",           "3", "8",  90, "piernas",notes="Legs B")
        _insert_exercise(tid, "Sábado",  3, "Extensión de cuádriceps máquina",        "3", "8",  90, "piernas",notes="Legs B")
        _insert_exercise(tid, "Sábado",  4, "Hip thrust con barra o mancuerna",       "4", "5", 150, "piernas",notes="Legs B")

        # A5 — Fuerza Express 2 días
        tid = _insert_template(
            "Fuerza Express 2 días",
            "Full body compacto en 2 sesiones semanales. Ideal para quien tiene poco tiempo.",
            "fuerza", "principiante", 2, 6,
            ["fuerza", "full_body", "principiante", "express"],
        )
        for day in ["Martes", "Sábado"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "3", "6", 90, "piernas")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "3", "6", 90, "empuje")
            _insert_exercise(tid, day, 3, "Remo en máquina sentado agarre neutro",  "3", "6", 90, "jale")
            _insert_exercise(tid, day, 4, "Extensión de tríceps en polea (cuerda)", "3", "6", 90, "empuje")

        # ══════════════════════════════════════════════════════════════════════
        # GRUPO B — HIPERTROFIA
        # ══════════════════════════════════════════════════════════════════════

        # B1 — PPL Hipertrofia Clásica
        tid = _insert_template(
            "PPL Hipertrofia Clásica",
            "Push/Pull/Legs 6 días clásico para hipertrofia. Volumen moderado-alto con rangos 10-15 repeticiones.",
            "hipertrofia", "intermedio", 6, 12,
            ["hipertrofia", "ppl", "intermedio", "6_dias", "volumen"],
        )
        for push_day in ["Lunes", "Jueves"]:
            _insert_exercise(tid, push_day, 1, "Press de banca plana (barra)",          "4", "10",  90, "empuje")
            _insert_exercise(tid, push_day, 2, "Press inclinado con mancuernas",         "4", "12",  75, "empuje")
            _insert_exercise(tid, push_day, 3, "Elevaciones laterales",                  "4", "15",  60, "empuje")
            _insert_exercise(tid, push_day, 4, "Extensión de tríceps en polea (cuerda)", "4", "12",  60, "empuje")
        for pull_day in ["Martes", "Viernes"]:
            _insert_exercise(tid, pull_day, 1, "Jalón al pecho en polea agarre ancho",   "4", "10",  90, "jale")
            _insert_exercise(tid, pull_day, 2, "Remo en polea baja un brazo a la vez",   "4", "12",  75, "jale")
            _insert_exercise(tid, pull_day, 3, "Remo en máquina sentado agarre neutro",  "3", "12",  75, "jale")
            _insert_exercise(tid, pull_day, 4, "Curl en polea baja con barra",           "4", "12",  60, "jale")
        for legs_day in ["Miércoles", "Sábado"]:
            _insert_exercise(tid, legs_day, 1, "Prensa de piernas máquina",              "4", "12",  90, "piernas")
            _insert_exercise(tid, legs_day, 2, "Extensión de cuádriceps máquina",        "3", "15",  60, "piernas")
            _insert_exercise(tid, legs_day, 3, "Curl femoral tumbado máquina",           "3", "15",  60, "piernas")
            _insert_exercise(tid, legs_day, 4, "Hip thrust con barra o mancuerna",       "4", "15",  90, "piernas")
            _insert_exercise(tid, legs_day, 5, "Abducción en máquina",                   "3", "20",  60, "piernas")

        # B2 — Bro Split 5 días
        tid = _insert_template(
            "Bro Split 5 días",
            "División clásica por grupo muscular: pecho, espalda, hombros, brazos, piernas. 5 días a la semana.",
            "hipertrofia", "intermedio", 5, 10,
            ["hipertrofia", "bro_split", "intermedio", "5_dias"],
        )
        # Lunes — Pecho
        _insert_exercise(tid, "Lunes",    1, "Press de banca plana (barra)",              "4", "10", 90, "empuje", notes="Pecho")
        _insert_exercise(tid, "Lunes",    2, "Press inclinado con mancuernas",             "3", "12", 75, "empuje", notes="Pecho")
        _insert_exercise(tid, "Lunes",    3, "Press de banca declinado máquina",           "3", "12", 75, "empuje", notes="Pecho")
        _insert_exercise(tid, "Lunes",    4, "Face pull en polea (cuerda)",                "3", "15", 60, "jale",   notes="Pecho — equilibrio", is_posture=True)
        # Martes — Espalda
        _insert_exercise(tid, "Martes",   1, "Jalón al pecho en polea agarre ancho",       "4", "10", 90, "jale",   notes="Espalda")
        _insert_exercise(tid, "Martes",   2, "Remo en polea baja un brazo a la vez",       "4", "12", 75, "jale",   notes="Espalda")
        _insert_exercise(tid, "Martes",   3, "Remo en máquina sentado agarre neutro",      "3", "12", 75, "jale",   notes="Espalda")
        _insert_exercise(tid, "Martes",   4, "Jalón agarre supino",                        "3", "15", 60, "jale",   notes="Espalda — pull-over polea")
        # Miércoles — Hombros
        _insert_exercise(tid, "Miércoles",1, "Press militar en máquina",                   "4", "12", 90, "empuje", notes="Hombros")
        _insert_exercise(tid, "Miércoles",2, "Elevaciones laterales",                      "4", "15", 60, "empuje", notes="Hombros")
        _insert_exercise(tid, "Miércoles",3, "Elevaciones frontales con mancuernas",       "3", "12", 60, "empuje", notes="Hombros")
        _insert_exercise(tid, "Miércoles",4, "Face pull en polea (cuerda)",                "3", "20", 60, "jale",   notes="Hombros — rear delt", is_posture=True)
        # Jueves — Brazos
        _insert_exercise(tid, "Jueves",   1, "Curl en polea baja con barra",               "4", "12", 75, "jale",   notes="Brazos")
        _insert_exercise(tid, "Jueves",   2, "Curl en polea baja con cuerda martillo",     "4", "12", 75, "jale",   notes="Brazos")
        _insert_exercise(tid, "Jueves",   3, "Extensión de tríceps en polea (cuerda)",     "4", "12", 75, "empuje", notes="Brazos")
        _insert_exercise(tid, "Jueves",   4, "Press francés máquina / Skull crusher",      "3", "12", 75, "empuje", notes="Brazos")
        # Viernes — Piernas
        _insert_exercise(tid, "Viernes",  1, "Prensa de piernas máquina",                  "4", "12", 90, "piernas",notes="Piernas")
        _insert_exercise(tid, "Viernes",  2, "Extensión de cuádriceps máquina",            "3", "15", 60, "piernas",notes="Piernas")
        _insert_exercise(tid, "Viernes",  3, "Curl femoral tumbado máquina",               "3", "15", 60, "piernas",notes="Piernas")
        _insert_exercise(tid, "Viernes",  4, "Hip thrust con barra o mancuerna",           "4", "15", 90, "piernas",notes="Piernas")

        # B3 — Upper/Lower Volumen
        tid = _insert_template(
            "Upper/Lower Volumen",
            "División upper/lower 4 días orientada a hipertrofia. Rangos altos de repeticiones y volumen total elevado.",
            "hipertrofia", "intermedio", 4, 10,
            ["hipertrofia", "upper_lower", "intermedio", "volumen"],
        )
        # Upper A — Lunes
        _insert_exercise(tid, "Lunes",    1, "Press de banca plana (barra)",          "4", "12", 90, "empuje")
        _insert_exercise(tid, "Lunes",    2, "Press inclinado con mancuernas",         "3", "15", 75, "empuje")
        _insert_exercise(tid, "Lunes",    3, "Jalón al pecho en polea agarre ancho",   "4", "12", 90, "jale")
        _insert_exercise(tid, "Lunes",    4, "Remo en máquina sentado agarre neutro",  "4", "12", 75, "jale")
        # Lower A — Martes
        _insert_exercise(tid, "Martes",   1, "Prensa de piernas máquina",              "4", "15", 90, "piernas")
        _insert_exercise(tid, "Martes",   2, "Extensión de cuádriceps máquina",        "4", "15", 60, "piernas")
        _insert_exercise(tid, "Martes",   3, "Curl femoral tumbado máquina",           "4", "15", 60, "piernas")
        _insert_exercise(tid, "Martes",   4, "Hip thrust con barra o mancuerna",       "4", "15", 90, "piernas")
        # Upper B — Jueves
        _insert_exercise(tid, "Jueves",   1, "Press militar en máquina",               "4", "12", 90, "empuje")
        _insert_exercise(tid, "Jueves",   2, "Elevaciones laterales",                  "4", "15", 60, "empuje")
        _insert_exercise(tid, "Jueves",   3, "Remo en polea baja un brazo a la vez",   "4", "12", 75, "jale")
        _insert_exercise(tid, "Jueves",   4, "Curl en polea baja con barra",           "4", "15", 60, "jale")
        # Lower B — Viernes
        _insert_exercise(tid, "Viernes",  1, "Prensa de piernas máquina",              "4", "15", 90, "piernas")
        _insert_exercise(tid, "Viernes",  2, "Curl femoral tumbado máquina",           "4", "15", 60, "piernas")
        _insert_exercise(tid, "Viernes",  3, "Abducción en máquina",                   "3", "20", 60, "piernas")
        _insert_exercise(tid, "Viernes",  4, "Extensión de glúteo en polea baja",      "3", "20", 60, "piernas")

        # B4 — Full Body Hipertrofia 3 días
        tid = _insert_template(
            "Full Body Hipertrofia 3 días",
            "Full body 3 veces por semana para principiantes que buscan ganar masa muscular con frecuencia alta.",
            "hipertrofia", "principiante", 3, 8,
            ["hipertrofia", "full_body", "principiante", "frecuencia_alta"],
        )
        for day in ["Lunes", "Miércoles", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "4", "12", 90, "piernas")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "4", "12", 90, "empuje")
            _insert_exercise(tid, day, 3, "Jalón al pecho en polea agarre ancho",   "4", "12", 90, "jale")
            _insert_exercise(tid, day, 4, "Press militar en máquina",               "3", "12", 75, "empuje")
            _insert_exercise(tid, day, 5, "Curl en polea baja con barra",           "3", "12", 60, "jale")
            _insert_exercise(tid, day, 6, "Extensión de tríceps en polea (cuerda)", "3", "12", 60, "empuje")

        # B5 — GVT Alemán
        tid = _insert_template(
            "GVT Alemán",
            "German Volume Training: 10 series de 10 repeticiones por ejercicio principal. Alta demanda metabólica.",
            "hipertrofia", "avanzado", 4, 6,
            ["hipertrofia", "gvt", "avanzado", "volumen", "alta_intensidad"],
        )
        # Lunes — Pecho + Espalda
        _insert_exercise(tid, "Lunes",    1, "Press de banca plana (barra)",              "10", "10", 90,  "empuje", notes="GVT — 10×10")
        _insert_exercise(tid, "Lunes",    2, "Jalón al pecho en polea agarre ancho",       "10", "10", 90,  "jale",   notes="GVT — 10×10")
        _insert_exercise(tid, "Lunes",    3, "Elevaciones laterales",                      "3",  "15", 60,  "empuje", notes="Accesorio")
        # Martes — Piernas + Abdomen
        _insert_exercise(tid, "Martes",   1, "Prensa de piernas máquina",                  "10", "10", 90,  "piernas",notes="GVT — 10×10")
        _insert_exercise(tid, "Martes",   2, "Curl femoral tumbado máquina",               "10", "10", 90,  "piernas",notes="GVT — 10×10")
        _insert_exercise(tid, "Martes",   3, "Plancha frontal",                            "3",  "45s",45,  "core",   notes="Accesorio — 45 segundos")
        # Jueves — Hombros + Espalda alta
        _insert_exercise(tid, "Jueves",   1, "Press militar en máquina",                   "10", "10", 90,  "empuje", notes="GVT — 10×10")
        _insert_exercise(tid, "Jueves",   2, "Remo en máquina sentado agarre neutro",      "10", "10", 90,  "jale",   notes="GVT — 10×10")
        _insert_exercise(tid, "Jueves",   3, "Face pull en polea (cuerda)",                "3",  "20", 60,  "jale",   notes="Accesorio", is_posture=True)
        # Viernes — Brazos
        _insert_exercise(tid, "Viernes",  1, "Curl en polea baja con barra",               "10", "10", 90,  "jale",   notes="GVT — 10×10")
        _insert_exercise(tid, "Viernes",  2, "Extensión de tríceps en polea (cuerda)",     "10", "10", 90,  "empuje", notes="GVT — 10×10")
        _insert_exercise(tid, "Viernes",  3, "Curl en polea baja con cuerda martillo",     "3",  "12", 60,  "jale",   notes="Accesorio")

        # ══════════════════════════════════════════════════════════════════════
        # GRUPO C — PÉRDIDA DE GRASA
        # ══════════════════════════════════════════════════════════════════════

        # C1 — Circuito Metabólico 3 días
        tid = _insert_template(
            "Circuito Metabólico 3 días",
            "Circuito de máquinas 4 rondas, 45s trabajo / 15s descanso. Ideal para quema calórica sin impacto.",
            "perdida_grasa", "principiante", 3, 8,
            ["perdida_grasa", "circuito", "principiante", "metabolico"],
        )
        for day in ["Lunes", "Miércoles", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "4", "45s", 15,  "piernas", notes="Circuito — 45s/15s")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "4", "45s", 15,  "empuje",  notes="Circuito — 45s/15s")
            _insert_exercise(tid, day, 3, "Remo en polea baja un brazo a la vez",   "4", "45s", 15,  "jale",    notes="Circuito — 45s/15s")
            _insert_exercise(tid, day, 4, "Press militar en máquina",               "4", "45s", 15,  "empuje",  notes="Circuito — 45s/15s")
            _insert_exercise(tid, day, 5, "Curl en polea baja con barra",           "4", "45s", 15,  "jale",    notes="Circuito — 45s/15s")
            _insert_exercise(tid, day, 6, "Extensión de tríceps en polea (cuerda)", "4", "45s", 15,  "empuje",  notes="Circuito — 45s/15s")

        # C2 — HIIT + Fuerza 4 días
        tid = _insert_template(
            "HIIT + Fuerza 4 días",
            "Combinación de días de fuerza y días HIIT en cardio. Máxima quema calórica semanal.",
            "perdida_grasa", "intermedio", 4, 8,
            ["perdida_grasa", "hiit", "intermedio", "cardio", "fuerza"],
        )
        # Lunes — Fuerza Full Body
        _insert_exercise(tid, "Lunes",    1, "Prensa de piernas máquina",              "3", "10", 90, "piernas")
        _insert_exercise(tid, "Lunes",    2, "Press de banca plana (barra)",           "3", "10", 90, "empuje")
        _insert_exercise(tid, "Lunes",    3, "Remo en máquina sentado agarre neutro",  "3", "10", 90, "jale")
        _insert_exercise(tid, "Lunes",    4, "Plancha frontal",                        "3", "30s",45, "core",   notes="Core al final")
        # Martes — HIIT cardio
        _insert_exercise(tid, "Martes",   1, "Bicicleta estática intervalos",          "1", "20min",0, "cardio", notes="30s máx / 30s suave × 20 min")
        # Jueves — Fuerza Upper
        _insert_exercise(tid, "Jueves",   1, "Press de banca plana (barra)",           "4", "12", 75, "empuje")
        _insert_exercise(tid, "Jueves",   2, "Press militar en máquina",               "4", "12", 75, "empuje")
        _insert_exercise(tid, "Jueves",   3, "Jalón al pecho en polea agarre ancho",   "4", "12", 75, "jale")
        _insert_exercise(tid, "Jueves",   4, "Remo en máquina sentado agarre neutro",  "4", "12", 75, "jale")
        # Viernes — HIIT cardio
        _insert_exercise(tid, "Viernes",  1, "Elíptica intervalos",                    "1", "20min",0, "cardio", notes="40s moderado / 20s intenso × 20 min")

        # C3 — Full Body 5 días Déficit
        tid = _insert_template(
            "Full Body 5 días Déficit",
            "Full body diario 5 días con 15 min de cardio al final. Diseñado para déficit calórico sostenido.",
            "perdida_grasa", "intermedio", 5, 12,
            ["perdida_grasa", "full_body", "intermedio", "deficit", "cardio"],
        )
        for day in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "3", "15", 60, "piernas")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "3", "15", 60, "empuje")
            _insert_exercise(tid, day, 3, "Remo en máquina sentado agarre neutro",  "3", "15", 60, "jale")
            _insert_exercise(tid, day, 4, "Press militar en máquina",               "3", "15", 60, "empuje")
            _insert_exercise(tid, day, 5, "Curl en polea baja con barra",           "3", "15", 60, "jale")
            _insert_exercise(tid, day, 6, "Extensión de tríceps en polea (cuerda)", "3", "15", 60, "empuje")
            _insert_exercise(tid, day, 7, "Cardio final bicicleta o elíptica",      "1", "15min",0, "cardio", notes="Ritmo moderado — zona 2")

        # C4 — Tonificación Máquinas
        tid = _insert_template(
            "Tonificación Máquinas 4 días",
            "Upper/lower con cardio LISS al final. 100% máquinas, ideal para principiantes con objetivo de tonificación.",
            "perdida_grasa", "principiante", 4, 8,
            ["perdida_grasa", "maquinas", "principiante", "tonificacion", "cardio"],
        )
        # Lunes y Jueves — Upper
        for day in ["Lunes", "Jueves"]:
            _insert_exercise(tid, day, 1, "Press de banca plana (barra)",           "3", "12", 75, "empuje")
            _insert_exercise(tid, day, 2, "Jalón al pecho en polea agarre ancho",   "3", "12", 75, "jale")
            _insert_exercise(tid, day, 3, "Press militar en máquina",               "3", "12", 75, "empuje")
            _insert_exercise(tid, day, 4, "Remo en máquina sentado agarre neutro",  "3", "12", 75, "jale")
            _insert_exercise(tid, day, 5, "Bicicleta estática ritmo constante",     "1", "20min",0, "cardio", notes="Cardio post — zona 2")
        # Martes y Viernes — Lower
        for day in ["Martes", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "3", "15", 75, "piernas")
            _insert_exercise(tid, day, 2, "Extensión de cuádriceps máquina",        "3", "15", 60, "piernas")
            _insert_exercise(tid, day, 3, "Curl femoral tumbado máquina",           "3", "15", 60, "piernas")
            _insert_exercise(tid, day, 4, "Hip thrust con barra o mancuerna",       "3", "15", 75, "piernas")
            _insert_exercise(tid, day, 5, "Elíptica ritmo constante",               "1", "20min",0, "cardio", notes="Cardio post — zona 2")

        # C5 — PPL + Cardio LISS
        tid = _insert_template(
            "PPL + Cardio LISS",
            "Push/Pull/Legs 6 días con 20 min de cardio de baja intensidad al final de cada sesión.",
            "perdida_grasa", "avanzado", 6, 12,
            ["perdida_grasa", "ppl", "avanzado", "liss", "cardio"],
        )
        # Push — Lunes y Jueves
        for push_day in ["Lunes", "Jueves"]:
            _insert_exercise(tid, push_day, 1, "Press de banca plana (barra)",          "4", "12", 75, "empuje")
            _insert_exercise(tid, push_day, 2, "Press inclinado con mancuernas",         "3", "12", 60, "empuje")
            _insert_exercise(tid, push_day, 3, "Press militar en máquina",               "3", "12", 60, "empuje")
            _insert_exercise(tid, push_day, 4, "Elevaciones laterales",                  "3", "15", 45, "empuje")
            _insert_exercise(tid, push_day, 5, "Extensión de tríceps en polea (cuerda)", "3", "15", 45, "empuje")
            _insert_exercise(tid, push_day, 6, "Cardio LISS bicicleta o elíptica",       "1", "20min",0,"cardio", notes="Zona 2 — 60-65% FC máx")
        # Pull — Martes y Viernes
        for pull_day in ["Martes", "Viernes"]:
            _insert_exercise(tid, pull_day, 1, "Jalón al pecho en polea agarre ancho",   "4", "12", 75, "jale")
            _insert_exercise(tid, pull_day, 2, "Remo en polea baja un brazo a la vez",   "4", "12", 60, "jale")
            _insert_exercise(tid, pull_day, 3, "Remo en máquina sentado agarre neutro",  "3", "12", 60, "jale")
            _insert_exercise(tid, pull_day, 4, "Curl en polea baja con barra",           "3", "12", 45, "jale")
            _insert_exercise(tid, pull_day, 5, "Face pull en polea (cuerda)",            "3", "15", 45, "jale",  is_posture=True)
            _insert_exercise(tid, pull_day, 6, "Cardio LISS bicicleta o elíptica",       "1", "20min",0,"cardio", notes="Zona 2 — 60-65% FC máx")
        # Legs — Miércoles y Sábado
        for legs_day in ["Miércoles", "Sábado"]:
            _insert_exercise(tid, legs_day, 1, "Prensa de piernas máquina",              "4", "15", 90, "piernas")
            _insert_exercise(tid, legs_day, 2, "Extensión de cuádriceps máquina",        "3", "15", 60, "piernas")
            _insert_exercise(tid, legs_day, 3, "Curl femoral tumbado máquina",           "3", "15", 60, "piernas")
            _insert_exercise(tid, legs_day, 4, "Hip thrust con barra o mancuerna",       "3", "15", 75, "piernas")
            _insert_exercise(tid, legs_day, 5, "Abducción en máquina",                   "3", "20", 45, "piernas")
            _insert_exercise(tid, legs_day, 6, "Cardio LISS bicicleta o elíptica",       "1", "20min",0,"cardio", notes="Zona 2 — 60-65% FC máx")

        # ══════════════════════════════════════════════════════════════════════
        # GRUPO D — MOVILIDAD Y REHABILITACIÓN
        # ══════════════════════════════════════════════════════════════════════

        # D1 — Movilidad Total Diaria
        tid = _insert_template(
            "Movilidad Total Diaria",
            "Rutina de movilidad articular completa para hacer todos los días. Énfasis en columna, cadera y cadena posterior.",
            "movilidad", "principiante", 7, 4,
            ["movilidad", "diario", "principiante", "postura", "columna"],
        )
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        for day in dias_semana:
            _insert_exercise(tid, day, 1, "Foam rolling columna torácica",           "1", "2min",  0, "movilidad", notes="Rodillo bajo escápulas", is_posture=True)
            _insert_exercise(tid, day, 2, "Extensión torácica sobre el rodillo",     "1", "5 reps por zona", 30, "movilidad", is_posture=True)
            _insert_exercise(tid, day, 3, "Cat-cow + rotación torácica",             "1", "10 reps",30, "movilidad", is_posture=True)
            _insert_exercise(tid, day, 4, "Movilidad de cadera paloma modificada",   "1", "90s c/lado",0,"movilidad", notes="En suelo o en banco")
            _insert_exercise(tid, day, 5, "Estiramiento cadena posterior",           "1", "2min c/lado",0,"movilidad")
            _insert_exercise(tid, day, 6, "Apertura de pecho en marco de puerta",    "1", "30s × 2",  30, "movilidad", is_posture=True)

        # D2 — Rehabilitación Tobillo/Peroneo
        tid = _insert_template(
            "Rehabilitación Tobillo/Peroneo",
            "Protocolo de rehabilitación para peroneal y tendón de Aquiles. Progresión excéntrica Alfredson.",
            "rehabilitacion", "principiante", 3, 8,
            ["rehabilitacion", "tobillo", "peroneo", "aquiles", "principiante"],
        )
        for day in ["Lunes", "Miércoles", "Viernes"]:
            _insert_exercise(tid, day, 1, "Eversión con banda elástica sentado",             "3", "20", 45, "tobillo", is_ankle=True)
            _insert_exercise(tid, day, 2, "Inversión con banda elástica sentado",            "3", "15", 45, "tobillo", is_ankle=True)
            _insert_exercise(tid, day, 3, "Excéntrico de pantorrilla en escalón (Alfredson)","3", "15", 60, "tobillo", notes="Baja lento en 3s", is_ankle=True)
            _insert_exercise(tid, day, 4, "Estiramiento de sóleo rodilla flexionada",        "3", "45s",  0, "tobillo", notes="45 segundos c/lado", is_ankle=True)
            _insert_exercise(tid, day, 5, "Movilidad tobillo knee-to-wall",                  "1", "10 reps c/lado", 30, "tobillo", is_ankle=True)

        # D3 — Corrección Postural
        tid = _insert_template(
            "Corrección Postural",
            "Programa 5 días para corregir postura: hombros adelantados, cifosis dorsal y cabeza adelantada.",
            "rehabilitacion", "principiante", 5, 6,
            ["rehabilitacion", "postura", "principiante", "cifosis", "hombros"],
        )
        for day in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]:
            _insert_exercise(tid, day, 1, "Face pull en polea (cuerda)",             "3", "15-20", 60, "jale",     is_posture=True)
            _insert_exercise(tid, day, 2, "Y-T-W en banco inclinado",               "3", "10 c/forma",60,"movilidad", is_posture=True)
            _insert_exercise(tid, day, 3, "Chin tuck doble mentón",                 "3", "10",    30, "movilidad", is_posture=True)
            _insert_exercise(tid, day, 4, "Rotación torácica en suelo",             "1", "8 reps × lado",30,"movilidad", is_posture=True)
            _insert_exercise(tid, day, 5, "Apertura de pecho en marco de puerta",   "1", "30s × 2", 30, "movilidad", is_posture=True)
            _insert_exercise(tid, day, 6, "Jalón agarre supino",                    "3", "12",    60, "jale",     is_posture=True)

        # D4 — Yoga Atlético
        tid = _insert_template(
            "Yoga Atlético",
            "Rutina de yoga adaptado para atletas. Mejora movilidad funcional y reduce riesgo de lesiones.",
            "movilidad", "principiante", 4, 6,
            ["movilidad", "yoga", "principiante", "flexibilidad", "atletico"],
        )
        # Lunes y Jueves — cadena posterior
        for day in ["Lunes", "Jueves"]:
            _insert_exercise(tid, day, 1, "Estiramiento cadena posterior",         "1", "2min",    0, "movilidad", notes="Piernas estiradas — 2 minutos")
            _insert_exercise(tid, day, 2, "Movilidad de cadera paloma modificada", "1", "90s c/lado",0,"movilidad", notes="Paloma modificada")
            _insert_exercise(tid, day, 3, "Estiramiento de flexores de cadera media luna","1","45s c/lado",0,"movilidad")
        # Martes y Viernes — torácico y hombros
        for day in ["Martes", "Viernes"]:
            _insert_exercise(tid, day, 1, "Rotación torácica en suelo",             "1", "8 reps × lado",30,"movilidad", is_posture=True)
            _insert_exercise(tid, day, 2, "Apertura de hombros con banda o toalla", "1", "15 reps",   30, "movilidad", is_posture=True)
            _insert_exercise(tid, day, 3, "Movilidad de cadera 90/90",             "1", "90s c/lado",  0, "movilidad", notes="Rotación interna y externa")

        # D5 — Movilidad + Fuerza Ligera
        tid = _insert_template(
            "Movilidad + Fuerza Ligera",
            "Combinación de trabajo de fuerza con máquinas ligeras y movilidad activa. Para mantenimiento o recuperación.",
            "movilidad", "principiante", 3, 6,
            ["movilidad", "fuerza_ligera", "principiante", "mantenimiento"],
        )
        for day in ["Lunes", "Miércoles", "Viernes"]:
            _insert_exercise(tid, day, 1, "Face pull en polea (cuerda)",             "3", "15", 60, "jale",     is_posture=True)
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "3", "12", 75, "empuje",   notes="Carga ligera — técnica")
            _insert_exercise(tid, day, 3, "Prensa de piernas peso ligero",          "3", "15", 60, "piernas",  notes="50-60% del 1RM")
            _insert_exercise(tid, day, 4, "Foam rolling columna torácica",          "1", "5min",  0, "movilidad",is_posture=True)
            _insert_exercise(tid, day, 5, "Estiramiento global post-sesión",        "1", "10min", 0, "movilidad")

        # ══════════════════════════════════════════════════════════════════════
        # GRUPO E — MIXTAS
        # ══════════════════════════════════════════════════════════════════════

        # E1 — Rutina Mono v1
        tid = _insert_template(
            "Rutina Mono v1",
            "Rutina de salud general 6 días: empuje, jale, descanso activo, piernas, core+cardio, full body ligero. "
            "Adaptada para tobillo/peroneal. Idéntica al plan activo del perfil Mono.",
            "salud_general", "intermedio", 6, 12,
            ["salud_general", "intermedio", "6_dias", "tobillo", "postura", "mono_v1"],
        )
        # Lunes — Empuje
        _insert_exercise(tid, "Lunes",    1, "Face pull en polea (cuerda)",             "3", "15-20", 60, "empuje",  is_posture=True)
        _insert_exercise(tid, "Lunes",    2, "Press de banca plana (barra)",            "4", "10-12", 90, "empuje")
        _insert_exercise(tid, "Lunes",    3, "Press inclinado con mancuernas",          "3", "10-12", 75, "empuje")
        _insert_exercise(tid, "Lunes",    4, "Press militar en máquina",                "3", "10-12", 75, "empuje")
        _insert_exercise(tid, "Lunes",    5, "Elevaciones laterales",                   "3", "12-15", 60, "empuje")
        _insert_exercise(tid, "Lunes",    6, "Extensión de tríceps en polea (cuerda)",  "3", "12-15", 60, "empuje")
        # Martes — Jale
        _insert_exercise(tid, "Martes",   1, "Jalón al pecho en polea agarre ancho",    "4", "10-12", 90, "jale")
        _insert_exercise(tid, "Martes",   2, "Remo en polea baja un brazo a la vez",    "3", "10-12 c/lado",75,"jale")
        _insert_exercise(tid, "Martes",   3, "Remo en máquina sentado agarre neutro",   "3", "10-12", 75, "jale")
        _insert_exercise(tid, "Martes",   4, "Jalón agarre supino",                     "3", "10-12", 75, "jale",   is_posture=True)
        _insert_exercise(tid, "Martes",   5, "Curl en polea baja con barra",            "3", "10-12", 60, "jale")
        _insert_exercise(tid, "Martes",   6, "Curl en polea baja con cuerda martillo",  "3", "12",    60, "jale")
        # Miércoles — Descanso activo
        _insert_exercise(tid, "Miércoles",1, "Foam rolling columna torácica",           "1", "2min",   0, "movilidad", is_posture=True)
        _insert_exercise(tid, "Miércoles",2, "Extensión torácica sobre el rodillo",     "1", "5 reps por zona",30,"movilidad",is_posture=True)
        _insert_exercise(tid, "Miércoles",3, "Estiramiento cadena posterior",           "1", "2min c/lado",0,"movilidad")
        _insert_exercise(tid, "Miércoles",4, "Movilidad de cadera paloma modificada",   "1", "90s c/lado",0,"movilidad")
        _insert_exercise(tid, "Miércoles",5, "Cat-cow + rotación torácica",             "1", "10 reps",30,"movilidad",  is_posture=True)
        # Jueves — Piernas
        _insert_exercise(tid, "Jueves",   1, "Prensa de piernas máquina",               "4", "12-15", 90, "piernas")
        _insert_exercise(tid, "Jueves",   2, "Extensión de cuádriceps máquina",         "3", "12-15", 60, "piernas")
        _insert_exercise(tid, "Jueves",   3, "Curl femoral tumbado máquina",            "3", "12-15", 60, "piernas")
        _insert_exercise(tid, "Jueves",   4, "Hip thrust con barra o mancuerna",        "4", "12-15", 90, "piernas",  is_posture=True)
        _insert_exercise(tid, "Jueves",   5, "Abducción en máquina",                    "3", "15-20", 60, "piernas")
        _insert_exercise(tid, "Jueves",   6, "Eversión con banda elástica sentado",     "3", "15-20", 45, "tobillo",  is_ankle=True)
        _insert_exercise(tid, "Jueves",   7, "Inversión con banda elástica sentado",    "3", "15",    45, "tobillo",  is_ankle=True)
        _insert_exercise(tid, "Jueves",   8, "Excéntrico de pantorrilla en escalón (Alfredson)","3","15",60,"tobillo",is_ankle=True)
        _insert_exercise(tid, "Jueves",   9, "Estiramiento de sóleo rodilla flexionada","3", "45s",   0,  "tobillo",  is_ankle=True)
        _insert_exercise(tid, "Jueves",  10, "Movilidad tobillo knee-to-wall",          "1", "10 reps c/lado",30,"tobillo",is_ankle=True)
        # Viernes — Core + Cardio
        _insert_exercise(tid, "Viernes",  1, "Plancha frontal",                         "3", "30-45s", 45, "core",   is_posture=True)
        _insert_exercise(tid, "Viernes",  2, "Plancha lateral",                         "3", "20-30s c/lado",45,"core")
        _insert_exercise(tid, "Viernes",  3, "Crunch en máquina",                       "3", "15-20",  60, "core")
        _insert_exercise(tid, "Viernes",  4, "Superman en suelo",                       "3", "12-15",  45, "core",   is_posture=True)
        _insert_exercise(tid, "Viernes",  5, "Bird-dog",                                "3", "10 c/lado",45,"core",  is_posture=True)
        _insert_exercise(tid, "Viernes",  6, "Pallof press polea",                      "3", "12 c/lado",60,"core")
        _insert_exercise(tid, "Viernes",  7, "Cardio bicicleta o elíptica intervalos",  "1", "20min",   0, "cardio", notes="Intervalos suaves 20 min")
        # Sábado — Full Body Ligero
        _insert_exercise(tid, "Sábado",   1, "Remo en máquina sentado",                 "3", "12",    75, "jale")
        _insert_exercise(tid, "Sábado",   2, "Press de mancuernas banco plano",         "3", "12",    75, "empuje")
        _insert_exercise(tid, "Sábado",   3, "Prensa de piernas peso ligero",           "3", "15",    60, "piernas")
        _insert_exercise(tid, "Sábado",   4, "Y-T-W en banco inclinado",               "3", "10 c/forma",60,"movilidad",is_posture=True)
        _insert_exercise(tid, "Sábado",   5, "Curl con mancuernas excéntrico",          "3", "12",    60, "jale")
        _insert_exercise(tid, "Sábado",   6, "Plancha",                                 "2", "30s",   45, "core")
        _insert_exercise(tid, "Sábado",   7, "Eversión con banda elástica sentado",     "3", "15-20", 45, "tobillo", is_ankle=True)
        _insert_exercise(tid, "Sábado",   8, "Excéntrico de pantorrilla en escalón",   "3", "15",    60, "tobillo", is_ankle=True)
        _insert_exercise(tid, "Sábado",   9, "Estiramiento de sóleo rodilla flexionada","3", "45s",    0, "tobillo", is_ankle=True)

        # E2 — Mantenimiento Mínimo
        tid = _insert_template(
            "Mantenimiento Mínimo",
            "Programa 2 días para mantener masa muscular y salud básica. Ideal para semanas de viaje o alta carga laboral.",
            "salud_general", "principiante", 2, None,
            ["salud_general", "mantenimiento", "principiante", "minimo", "2_dias"],
        )
        for day in ["Martes", "Sábado"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "3", "10", 90, "piernas")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "3", "10", 90, "empuje")
            _insert_exercise(tid, day, 3, "Remo en máquina sentado agarre neutro",  "3", "10", 90, "jale")
            _insert_exercise(tid, day, 4, "Curl en polea baja con barra",           "2", "12", 60, "jale")
            _insert_exercise(tid, day, 5, "Extensión de tríceps en polea (cuerda)", "2", "12", 60, "empuje")
            _insert_exercise(tid, day, 6, "Cardio final bicicleta o elíptica",      "1", "10min",0,"cardio", notes="Ritmo confortable")

        # E3 — Vuelta al Gym Post-Pausa
        tid = _insert_template(
            "Vuelta al Gym Post-Pausa",
            "Reintroducción progresiva al entrenamiento tras 2-8 semanas de pausa. 50-60% 1RM, énfasis en técnica.",
            "salud_general", "principiante", 4, 4,
            ["salud_general", "principiante", "retorno", "tecnica", "post_pausa"],
        )
        for day in ["Lunes", "Martes", "Jueves", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "3", "10-12", 90, "piernas", notes="50-60% 1RM — sin llegar al fallo")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "3", "10-12", 90, "empuje",  notes="50-60% 1RM — sin llegar al fallo")
            _insert_exercise(tid, day, 3, "Jalón al pecho en polea agarre ancho",   "3", "12",    75, "jale",    notes="50-60% 1RM — técnica prioritaria")
            _insert_exercise(tid, day, 4, "Remo en máquina sentado agarre neutro",  "3", "12",    75, "jale",    notes="50-60% 1RM — técnica prioritaria")
            _insert_exercise(tid, day, 5, "Press militar en máquina",               "3", "12",    75, "empuje",  notes="50-60% 1RM")
            _insert_exercise(tid, day, 6, "Hip thrust con barra o mancuerna",       "3", "12",    75, "piernas", notes="Sin carga excesiva")

        # E4 — Atleta Funcional
        tid = _insert_template(
            "Atleta Funcional",
            "Entrenamiento funcional 5 días combinando fuerza, estabilidad de core y patrones multiarticulares.",
            "fuerza", "intermedio", 5, 8,
            ["fuerza", "funcional", "intermedio", "core", "estabilidad"],
        )
        # Lunes
        _insert_exercise(tid, "Lunes",    1, "Prensa de piernas máquina",            "4", "10", 90, "piernas")
        _insert_exercise(tid, "Lunes",    2, "Hip thrust con barra o mancuerna",     "4", "10", 90, "piernas")
        _insert_exercise(tid, "Lunes",    3, "Pallof press polea",                   "3", "12 c/lado",60,"core")
        _insert_exercise(tid, "Lunes",    4, "Bird-dog",                             "3", "10 c/lado",45,"core",  is_posture=True)
        # Martes
        _insert_exercise(tid, "Martes",   1, "Press de banca plana (barra)",         "4", "10", 90, "empuje")
        _insert_exercise(tid, "Martes",   2, "Remo en máquina sentado agarre neutro","4", "10", 90, "jale")
        _insert_exercise(tid, "Martes",   3, "Press militar en máquina",             "3", "12", 75, "empuje")
        _insert_exercise(tid, "Martes",   4, "Face pull en polea (cuerda)",          "3", "15", 60, "jale",    is_posture=True)
        # Miércoles
        _insert_exercise(tid, "Miércoles",1, "Prensa de piernas máquina (agarre sumo)","4","10",90,"piernas")
        _insert_exercise(tid, "Miércoles",2, "Curl femoral tumbado máquina",         "3", "12", 75, "piernas")
        _insert_exercise(tid, "Miércoles",3, "Plancha frontal",                      "3", "45s",45, "core",    is_posture=True)
        _insert_exercise(tid, "Miércoles",4, "Superman en suelo",                    "3", "12", 45, "core",    is_posture=True)
        # Jueves
        _insert_exercise(tid, "Jueves",   1, "Jalón al pecho en polea agarre ancho", "4", "10", 90, "jale")
        _insert_exercise(tid, "Jueves",   2, "Remo en polea baja un brazo a la vez", "4", "10 c/lado",75,"jale")
        _insert_exercise(tid, "Jueves",   3, "Extensión de tríceps en polea (cuerda)","3","12", 60, "empuje")
        _insert_exercise(tid, "Jueves",   4, "Curl en polea baja con barra",         "3", "12", 60, "jale")
        # Viernes — Full body funcional + cardio
        _insert_exercise(tid, "Viernes",  1, "Prensa de piernas máquina",            "3", "12", 75, "piernas")
        _insert_exercise(tid, "Viernes",  2, "Press de banca plana (barra)",         "3", "12", 75, "empuje")
        _insert_exercise(tid, "Viernes",  3, "Remo en máquina sentado agarre neutro","3", "12", 75, "jale")
        _insert_exercise(tid, "Viernes",  4, "Pallof press polea",                   "3", "12 c/lado",60,"core")
        _insert_exercise(tid, "Viernes",  5, "Cardio final bicicleta o elíptica",    "1", "20min",0,"cardio", notes="Zona 2-3 — ritmo moderado")

        # E5 — Semana de Descarga (Deload)
        tid = _insert_template(
            "Semana de Descarga (Deload)",
            "Semana de descarga: 50% del volumen normal y movilidad extra. Permite recuperación activa sin perder adaptaciones.",
            "salud_general", "intermedio", 4, 1,
            ["salud_general", "deload", "intermedio", "recuperacion", "movilidad"],
        )
        for day in ["Lunes", "Martes", "Jueves", "Viernes"]:
            _insert_exercise(tid, day, 1, "Prensa de piernas máquina",              "2", "10", 90, "piernas", notes="Deload — 50% carga habitual")
            _insert_exercise(tid, day, 2, "Press de banca plana (barra)",           "2", "10", 90, "empuje",  notes="Deload — 50% carga habitual")
            _insert_exercise(tid, day, 3, "Jalón al pecho en polea agarre ancho",   "2", "10", 90, "jale",    notes="Deload — 50% carga habitual")
            _insert_exercise(tid, day, 4, "Remo en máquina sentado agarre neutro",  "2", "10", 90, "jale",    notes="Deload — 50% carga habitual")
            _insert_exercise(tid, day, 5, "Foam rolling columna torácica",          "1", "5min",  0, "movilidad",is_posture=True)
            _insert_exercise(tid, day, 6, "Estiramiento cadena posterior",          "1", "2min c/lado",0,"movilidad")
            _insert_exercise(tid, day, 7, "Movilidad de cadera paloma modificada",  "1", "90s c/lado",0,"movilidad")
            _insert_exercise(tid, day, 8, "Rotación torácica en suelo",             "1", "8 reps × lado",30,"movilidad",is_posture=True)
