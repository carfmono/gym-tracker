"""Sistema de XP, niveles, rachas, achievements y metas semanales."""
import math
from datetime import date, timedelta
import db

# ── Tabla de XP por evento ────────────────────────────────────────────────────
XP_EVENTS = {
    "exercise_complete":          10,
    "posture_exercise_complete":  15,
    "ankle_exercise_complete":    15,
    "session_complete":           50,
    "posture_full_day":           30,
    "streak_bonus_3":             25,
    "streak_bonus_7":             75,
    "streak_bonus_14":           150,
    "streak_bonus_30":           400,
    "perfect_week":              200,
    "routine_complete":          500,
    "routine_started":            50,
    "personal_record":           100,
    "level_up":                    0,
}

LEVEL_AVATAR = {
    range(1, 5):   "🥚",
    range(5, 10):  "🐣",
    range(10, 20): "💪",
    range(20, 30): "🔥",
    range(30, 40): "⚡",
    range(40, 50): "🌟",
    range(50, 75): "👑",
    range(75, 100):"🔱",
}


def avatar_for_level(level: int) -> str:
    for r, emoji in LEVEL_AVATAR.items():
        if level in r:
            return emoji
    return "🌠"


# ── Curva de nivel ────────────────────────────────────────────────────────────

def xp_for_level(level: int) -> int:
    return max(1, int(100 * (level ** 1.5)))


def current_level_from_xp(total_xp: int) -> int:
    level = 1
    accumulated = 0
    while True:
        needed = xp_for_level(level)
        if accumulated + needed > total_xp:
            break
        accumulated += needed
        level += 1
    return level


def xp_progress(total_xp: int) -> dict:
    level = 1
    accumulated = 0
    while True:
        needed = xp_for_level(level)
        if accumulated + needed > total_xp:
            break
        accumulated += needed
        level += 1
    xp_in_level = total_xp - accumulated
    xp_needed = xp_for_level(level)
    return {
        "level": level,
        "xp_in_level": xp_in_level,
        "xp_needed_for_next": xp_needed,
        "percentage": min(100, int(xp_in_level / xp_needed * 100)) if xp_needed > 0 else 100,
        "total_xp": total_xp,
        "avatar": avatar_for_level(level),
    }


# ── award_xp ──────────────────────────────────────────────────────────────────

def award_xp(
    profile_id: int,
    event_type: str,
    description: str = "",
    multiplier: float = 1.0,
    idempotent: bool = True,
) -> int:
    """Otorga XP. Si idempotent=True, verifica que no se haya dado hoy para el mismo evento+descripción."""
    xp = int(XP_EVENTS.get(event_type, 0) * multiplier)
    if xp <= 0:
        return 0

    if idempotent and db.xp_log_exists_today(profile_id, event_type, description):
        return 0

    db.add_xp_log(profile_id, event_type, xp, description)

    uxp = db.get_user_xp(profile_id)
    if not uxp:
        db.init_user_xp(profile_id)
        uxp = db.get_user_xp(profile_id)

    old_level = uxp["current_level"]
    new_total = uxp["total_xp"] + xp
    new_level = current_level_from_xp(new_total)

    updates: dict = {"total_xp": new_total, "current_level": new_level}
    if event_type == "session_complete":
        updates["total_sessions"] = uxp["total_sessions"] + 1
    if event_type in ("exercise_complete", "posture_exercise_complete", "ankle_exercise_complete"):
        updates["total_exercises_completed"] = uxp["total_exercises_completed"] + 1

    db.update_user_xp(profile_id, **updates)

    if new_level > old_level:
        db.add_xp_log(profile_id, "level_up", 0, f"Nivel {new_level}")

    return xp


# ── check_achievements ────────────────────────────────────────────────────────

def check_achievements(profile_id: int) -> list[dict]:
    """Desbloquea achievements que cumplan condición. Retorna lista de los nuevos."""
    uxp = db.get_user_xp(profile_id)
    if not uxp:
        return []

    already = {a["code"] for a in db.get_user_achievements(profile_id)}
    all_ach = db.get_all_achievements()
    newly_unlocked: list[dict] = []

    state = {
        "sessions_total":    uxp["total_sessions"],
        "streak_days":       uxp["current_streak"],
        "exercises_total":   uxp["total_exercises_completed"],
        "level_reached":     uxp["current_level"],
        "routines_completed": _count_completed_routines(profile_id),
        "perfect_weeks":     _count_perfect_weeks(profile_id),
        "posture_days":      _count_posture_days(profile_id),
    }

    for ach in all_ach:
        if ach["code"] in already:
            continue
        ctype = ach["condition_type"]
        cval  = ach["condition_value"]
        if ctype and cval is not None and state.get(ctype, 0) >= cval:
            unlocked = db.unlock_achievement(profile_id, ach["id"])
            if unlocked:
                if ach["xp_reward"] > 0:
                    award_xp(profile_id, "achievement_unlock",
                             ach["name"], idempotent=False)
                newly_unlocked.append(ach)

    return newly_unlocked


def _count_completed_routines(profile_id: int) -> int:
    routines = db.get_routines_by_profile(profile_id)
    return sum(1 for r in routines if r.get("end_date"))


def _count_perfect_weeks(profile_id: int) -> int:
    return db.count_perfect_weeks(profile_id)


def _count_posture_days(profile_id: int) -> int:
    return db.count_posture_days(profile_id)


# ── update_streak ─────────────────────────────────────────────────────────────

def update_streak(profile_id: int, session_date: date) -> dict:
    """Actualiza racha según la fecha de sesión. Retorna dict con nuevo estado."""
    uxp = db.get_user_xp(profile_id)
    if not uxp:
        db.init_user_xp(profile_id)
        uxp = db.get_user_xp(profile_id)

    last = uxp["last_session_date"]
    current = uxp["current_streak"]
    longest = uxp["longest_streak"]
    streak_broken = False
    bonus_event = None

    if last is None:
        current = 1
    elif session_date == last:
        pass  # ya contó hoy
    elif session_date == last + timedelta(days=1):
        current += 1
    else:
        streak_broken = current > 1
        current = 1

    if current > longest:
        longest = current

    # Bonos por hito
    for hito, event in [(30, "streak_bonus_30"), (14, "streak_bonus_14"),
                        (7, "streak_bonus_7"), (3, "streak_bonus_3")]:
        if current == hito:
            bonus_event = event
            break

    db.update_user_xp(
        profile_id,
        current_streak=current,
        longest_streak=longest,
        last_session_date=session_date.isoformat(),
    )

    if bonus_event:
        award_xp(profile_id, bonus_event, f"Racha de {current} días", idempotent=True)

    return {
        "streak": current,
        "longest_streak": longest,
        "streak_broken": streak_broken,
        "bonus_event": bonus_event,
    }


# ── update_weekly_goals ───────────────────────────────────────────────────────

def update_weekly_goals(profile_id: int) -> dict:
    """Recalcula el estado de las metas de la semana actual."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.isoformat()

    all_dates = [(monday + timedelta(days=i)).isoformat() for i in range(7)]

    stats = db.get_stats_for_dates(all_dates, profile_id)
    sessions_done = sum(1 for ds in all_dates if stats["sessions"].get(ds))

    from data import POSTURE_ROUTINE
    exercises_done = sum(
        sum(1 for _ in [r for r in stats["exercises"] if r["date"] == ds and bool(r["completed"])])
        for ds in all_dates
    )
    posture_days_done = 0
    pos_by_date: dict = {}
    for r in stats["posture"]:
        pos_by_date.setdefault(r["date"], {})[r["exercise_id"]] = bool(r["completed"])
    for ds in all_dates:
        if sum(1 for pid in POSTURE_ROUTINE if pos_by_date.get(ds, {}).get(pid, False)) == len(POSTURE_ROUTINE):
            posture_days_done += 1

    goals = db.get_weekly_goals(profile_id, week_start)
    sessions_goal  = goals["sessions_goal"]  if goals else 4
    exercises_goal = goals["exercises_goal"] if goals else 30
    posture_goal   = goals["posture_days_goal"] if goals else 5

    was_completed = goals["completed"] if goals else False
    now_completed = (
        sessions_done  >= sessions_goal and
        exercises_done >= exercises_goal and
        posture_days_done >= posture_goal
    )

    db.upsert_weekly_goals(
        profile_id, week_start,
        sessions_done=sessions_done,
        exercises_done=exercises_done,
        posture_days_done=posture_days_done,
        completed=now_completed,
    )

    if now_completed and not was_completed:
        award_xp(profile_id, "perfect_week", f"Semana {week_start}", idempotent=True)

    return {
        "week_start": week_start,
        "sessions_done": sessions_done,   "sessions_goal": sessions_goal,
        "exercises_done": exercises_done,  "exercises_goal": exercises_goal,
        "posture_days_done": posture_days_done, "posture_days_goal": posture_goal,
        "completed": now_completed,
    }
