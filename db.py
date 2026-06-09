import json
import streamlit as st
import psycopg2
import psycopg2.extras
from contextlib import contextmanager


@contextmanager
def get_connection():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
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


# ── sessions ──────────────────────────────────────────────────────────────────

def get_session(date: str) -> bool:
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT completed FROM sessions WHERE date=%s", (date,))
        return bool(row["completed"]) if row else False


def toggle_session(date: str):
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
    row_id = f"{date}:{exercise_id}"
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT completed FROM exercises WHERE id=%s", (row_id,))
        return bool(row["completed"]) if row else False


def set_exercise(date: str, exercise_id: str, completed: bool):
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
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT exercise_id, completed FROM exercises WHERE date=%s", (date,))
        return {r["exercise_id"]: bool(r["completed"]) for r in rows}


# ── posture ───────────────────────────────────────────────────────────────────

def get_posture(date: str, exercise_id: str) -> bool:
    row_id = f"{date}:{exercise_id}"
    with get_connection() as conn:
        row = _fetch_one(conn, "SELECT completed FROM posture WHERE id=%s", (row_id,))
        return bool(row["completed"]) if row else False


def set_posture(date: str, exercise_id: str, completed: bool):
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
    with get_connection() as conn:
        rows = _fetch_all(conn, "SELECT exercise_id, completed FROM posture WHERE date=%s", (date,))
        return {r["exercise_id"]: bool(r["completed"]) for r in rows}


# ── stats helpers ─────────────────────────────────────────────────────────────

def get_stats_for_dates(dates: list[str]) -> dict:
    if not dates:
        return {}
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
