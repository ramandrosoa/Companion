"""
core/user.py
Handles loading and saving persistent user data to config.json.
All game state that should survive a browser refresh lives here.
"""

import json
import os
from datetime import date
from core.stage import DEFAULT_TINT
from core.redis_client import redis
from flask import session as flask_session

DEFAULT_CONFIG = {
    "name": None,
    "xp": 0,
    "stage": 1,
    "tint": DEFAULT_TINT,            # Stage 2 color choice
    "streak": 0,
    "longest_streak": 0,
    "last_opened": None,             # ISO date string
    "daily_pillars": {               # Resets each day
        "word_seen": False,
        "game_played": False,
        "steps_goal": False,
    },
    "stats": {
        "total_steps": 0,
        "games_played": 0,
        "best_capitals": {"pct": 0, "time": None},
        "best_flags":    {"pct": 0, "time": None},
        "words_learned": 0,
        "correct_answers": 0,
        "wrong_answers": 0,
    },
    "badges": [],
    "calendar": {},                  # "YYYY-MM-DD": "full" | "partial" | "missed"
    "preferences": {
        "companion_name": None,      # Stage 5 custom name
        "theme_override": None,      # Stage 5 theme choice
    },
    # Tracks which questions have been mastered (answered correctly at least once)
    # Structure: {"capitals": {"1": ["Paris", "Tokyo"], "2": [...], ...},
    #             "flags":    {"1": ["France", "Japan"], "2": [...], ...}}
    # The answer string (question["a"]) is used as the unique identifier
    "mastered": {
        "capitals": {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}},
        "flags":    {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}},
    },
}


def _get_username() -> str | None:
    """Return current username from Flask session."""
    return flask_session.get("username")


def load() -> dict:
    """Load user data from Redis using username as key."""
    username = _get_username()
    if not username:
        return DEFAULT_CONFIG.copy()
    try:
        raw = redis.get(f"user:{username}")
        if raw is None:
            return None
  
        data = json.loads(raw)
        _deep_merge(DEFAULT_CONFIG, data)
        return data
    except Exception as e:
        print(f"Redis load error: {e}")
        return DEFAULT_CONFIG.copy()


def save(data: dict) -> None:
    """Save user data to Redis using username as key."""
    username = _get_username()
    if not username:
        return
    try:
        redis.set(f"user:{username}", json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"Redis save error: {e}")


def username_exists(username: str) -> bool:
    """Check if a username is already taken."""
    return redis.exists(f"user:{username}") == 1


def create_user(username: str, email: str) -> dict:
    """Create a new user profile and store in Redis."""
    data = DEFAULT_CONFIG.copy()
    data["name"]  = username
    data["email"] = email
    redis.set(f"user:{username}", json.dumps(data, ensure_ascii=False))
    redis.set(f"email:{email.lower()}", username)
    return data


def find_by_email(email: str) -> str | None:
    """Return username associated with email, or None."""
    return redis.get(f"email:{email.lower()}")


def login(identifier: str) -> str | None:
    """
    Accept username or email, return username if found, else None.
    """
    identifier = identifier.strip()
    # Try as username first
    if redis.exists(f"user:{identifier}"):
        return identifier
    # Try as email
    username = find_by_email(identifier)
    if username:
        return username
    return None


def check_and_update_streak(data: dict) -> tuple[dict, bool]:
    """
    Call once per day on first open.
    Returns (updated_data, is_new_day).
    """
    today = date.today().isoformat()
    last = data.get("last_opened")
    is_new_day = last != today

    if is_new_day:
        if last is not None:
            # Check if yesterday's pillars were completed
            from datetime import timedelta
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            pillars = data.get("daily_pillars", {})
            all_done = all([
                pillars.get("word_seen", False),
                pillars.get("game_played", False),
            ])
            # Record calendar
            data["calendar"][last] = "full" if all_done else "partial"

            # Update streak
            if all_done:
                data["streak"] += 1
                if data["streak"] > data.get("longest_streak", 0):
                    data["longest_streak"] = data["streak"]
            else:
                data["streak"] = 0

        # Reset daily pillars
        data["daily_pillars"] = {
            "word_seen": False,
            "game_played": False,
            "steps_goal": False,
        }
        data["last_opened"] = today

    return data, is_new_day


def mark_game_played(data: dict) -> dict:
    data["daily_pillars"]["game_played"] = True
    data["stats"]["games_played"] = data["stats"].get("games_played", 0) + 1
    return data


def _deep_merge(defaults: dict, target: dict) -> None:
    """Add any missing keys from defaults into target (in-place)."""
    for key, val in defaults.items():
        if key not in target:
            target[key] = val
        elif isinstance(val, dict) and isinstance(target[key], dict):
            _deep_merge(val, target[key])


def is_mastered(data: dict, mode: str, stage: int, answer: str) -> bool:
    """Return True if this question has reached the full 10 XP cap."""
    entry = data["mastered"][mode][str(stage)].get(answer)
    if entry is None:
        return False
    return entry["remaining"] == 0


def award_xp(data: dict, mode: str, stage: int, answer: str, worth: int) -> tuple[dict, int]:
    """
    Award XP for a correct answer, respecting the 10 XP lifetime cap per question.
    - worth: XP this attempt is worth (10 full, 5 after hint S3, etc.)
    Returns (updated_data, xp_actually_awarded).
    """
    stage_key = str(stage)
    mastered = data["mastered"][mode][stage_key]

    if answer not in mastered:
        # First time correct — create entry
        mastered[answer] = {"earned": 0, "remaining": 10}

    entry = mastered[answer]

    if entry["remaining"] == 0:
        # Already sealed — no XP but question still counts as mastered
        return data, 0

    awarded = min(worth, entry["remaining"])
    entry["earned"] += awarded
    entry["remaining"] -= awarded
    data["xp"] += awarded
    return data, awarded


def mastered_count(data: dict, mode: str, stage: int) -> int:
    """Return how many questions have reached the full 10 XP cap."""
    entries = data["mastered"][mode][str(stage)]
    return sum(1 for e in entries.values() if e["remaining"] == 0)


def stage_progress(data: dict, stage: int) -> dict:
    """Return mastery progress for both modes at a given stage."""
    total = 10
    return {
        "capitals": {
            "mastered": mastered_count(data, "capitals", stage),
            "total": total,
        },
        "flags": {
            "mastered": mastered_count(data, "flags", stage),
            "total": total,
        },
    }