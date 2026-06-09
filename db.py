import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "gym_tracker.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                date TEXT PRIMARY KEY,
                completed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS exercises (
                id TEXT PRIMARY KEY,
                date TEXT,
                exercise_id TEXT,
                completed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS posture (
                id TEXT PRIMARY KEY,
                date TEXT,
                exercise_id TEXT,
                completed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT,
                name TEXT,
                start_date TEXT,
                end_date TEXT,
                notes TEXT
            );
        """)

        row = conn.execute("SELECT COUNT(*) FROM routines").fetchone()
        if row[0] == 0:
            conn.execute(
                "INSERT INTO routines (version, name, start_date, end_date, notes) VALUES (?,?,?,?,?)",
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
        row = conn.execute("SELECT completed FROM sessions WHERE date=?", (date,)).fetchone()
        return bool(row["completed"]) if row else False


def toggle_session(date: str):
    current = get_session(date)
    new_val = 0 if current else 1
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (date, completed) VALUES (?,?) ON CONFLICT(date) DO UPDATE SET completed=?",
            (date, new_val, new_val),
        )


# ── exercises ─────────────────────────────────────────────────────────────────

def get_exercise(date: str, exercise_id: str) -> bool:
    row_id = f"{date}:{exercise_id}"
    with get_connection() as conn:
        row = conn.execute("SELECT completed FROM exercises WHERE id=?", (row_id,)).fetchone()
        return bool(row["completed"]) if row else False


def set_exercise(date: str, exercise_id: str, completed: bool):
    row_id = f"{date}:{exercise_id}"
    val = 1 if completed else 0
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO exercises (id, date, exercise_id, completed) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET completed=?",
            (row_id, date, exercise_id, val, val),
        )


def get_exercises_for_date(date: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute("SELECT exercise_id, completed FROM exercises WHERE date=?", (date,)).fetchall()
        return {r["exercise_id"]: bool(r["completed"]) for r in rows}


# ── posture ───────────────────────────────────────────────────────────────────

def get_posture(date: str, exercise_id: str) -> bool:
    row_id = f"{date}:{exercise_id}"
    with get_connection() as conn:
        row = conn.execute("SELECT completed FROM posture WHERE id=?", (row_id,)).fetchone()
        return bool(row["completed"]) if row else False


def set_posture(date: str, exercise_id: str, completed: bool):
    row_id = f"{date}:{exercise_id}"
    val = 1 if completed else 0
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO posture (id, date, exercise_id, completed) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET completed=?",
            (row_id, date, exercise_id, val, val),
        )


def get_posture_for_date(date: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute("SELECT exercise_id, completed FROM posture WHERE date=?", (date,)).fetchall()
        return {r["exercise_id"]: bool(r["completed"]) for r in rows}


# ── stats helpers ─────────────────────────────────────────────────────────────

def get_stats_for_dates(dates: list[str]) -> dict:
    """Returns aggregated stats for a list of dates."""
    if not dates:
        return {}
    placeholders = ",".join("?" * len(dates))
    with get_connection() as conn:
        sessions = conn.execute(
            f"SELECT date, completed FROM sessions WHERE date IN ({placeholders})", dates
        ).fetchall()
        exercises = conn.execute(
            f"SELECT date, exercise_id, completed FROM exercises WHERE date IN ({placeholders})", dates
        ).fetchall()
        posture_rows = conn.execute(
            f"SELECT date, exercise_id, completed FROM posture WHERE date IN ({placeholders})", dates
        ).fetchall()

    return {
        "sessions": {r["date"]: bool(r["completed"]) for r in sessions},
        "exercises": exercises,
        "posture": posture_rows,
    }


# ── routines ──────────────────────────────────────────────────────────────────

def get_all_routines() -> list:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM routines ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def add_routine(version: str, name: str, start_date: str, notes: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE routines SET end_date=? WHERE end_date IS NULL",
            (start_date,),
        )
        conn.execute(
            "INSERT INTO routines (version, name, start_date, end_date, notes) VALUES (?,?,?,?,?)",
            (version, name, start_date, None, notes),
        )
