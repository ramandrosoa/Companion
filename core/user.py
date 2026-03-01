"""
core/user.py
Handles loading and saving persistent user data to config.json.
All game state that should survive a browser refresh lives here.
"""

import json
import os
from datetime import date
from core.stage import get_stage_from_xp, DEFAULT_TINT

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

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
        "best_score_capitals": 0,
        "best_score_flags": 0,
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
        "capitals": {"1": [], "2": [], "3": [], "4": [], "5": []},
        "flags":    {"1": [], "2": [], "3": [], "4": [], "5": []},
    },
}


def load() -> dict:
    """Load config from disk, creating it if it doesn't exist."""
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge any missing keys from DEFAULT_CONFIG
        _deep_merge(DEFAULT_CONFIG, data)
        return data
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def save(data: dict) -> None:
    """Save config to disk."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Warning: could not save config: {e}")


def add_xp(data: dict, amount: int) -> dict:
    """Add XP, recalculate stage, return updated data."""
    data["xp"] += amount
    data["stage"] = get_stage_from_xp(data["xp"])
    return data


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
    """Return True if this question has already been mastered."""
    return answer in data["mastered"][mode][str(stage)]


def master_question(data: dict, mode: str, stage: int, answer: str) -> tuple[dict, bool]:
    """
    Mark a question as mastered and award XP if it's the first time.
    Returns (updated_data, xp_awarded).

    Rules:
    - First correct answer → mastered, +10 XP
    - Already mastered    → no change, +0 XP
    - Wrong answer        → no change (caller decides, not this function)
    """
    mastered_list = data["mastered"][mode][str(stage)]

    if answer in mastered_list:
        return data, False

    # First time correct — mark mastered and award XP
    mastered_list.append(answer)
    data = add_xp(data, 10)
    return data, True


def mastered_count(data: dict, mode: str, stage: int) -> int:
    """Return how many questions have been mastered for a mode/stage."""
    return len(data["mastered"][mode][str(stage)])


def stage_progress(data: dict, stage: int) -> dict:
    """
    Return mastery progress for both modes at a given stage.
    Example return:
    {
        "capitals": {"mastered": 7, "total": 10},
        "flags":    {"mastered": 3, "total": 10},
    }
    """
    total = 10  # always 10 questions per mode per stage
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