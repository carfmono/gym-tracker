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
