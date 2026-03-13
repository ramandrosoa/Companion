"""
core/stage.py
Manages stage, XP progression, and companion state.
"""

# XP required to REACH each stage (cumulative)
# Based on geography quiz only: 10 questions per stage × 10 XP per correct answer
# Stage 1: master 10 questions = 100 XP
# Stage 2: master 10 more     = 200 XP (total 300)
# Stage 3: master 10 more     = 300 XP (total 600)
# Stage 4: master 10 more     = 400 XP (total 1000)
# When more games are added later, these thresholds scale up accordingly
# XP needed within a stage to be eligible for stage up
# Always 20 questions × 10 XP max = 200

XP_PER_STAGE = 200

STAGE_NAMES = {
    1: "Seed",
    2: "Sprout",
    3: "Sapling",
    4: "Tree",
    5: "Ancient",
}

COMPANION_EMOJIS = {
    1: "🌱",
    2: "🌿",
    3: "🌳",
    4: "🌲",
    5: "✨",
}

COMPANION_NAMES = {
    1: "Seedling",
    2: "Sprout",
    3: "Sapling",
    4: "Tree",
    5: "Ancient",
}

COMPANION_GREETINGS = {
    1: "Hello! I am just waking up. Let's play!",
    2: "Hi! I'm learning new things every day. Ready to play?",
    3: "Good to see you! Shall we play Geography?",
    4: "Welcome back! I can launch a game for you. Let's play!",
    5: "Greetings, friend. We've come a long way together. What shall we explore today?",
}

# Colors available for Stage 2 tint selection
TINT_COLORS = {
    "amber": {"hex": "#ffb300", "bg": "#0a0800", "dark": "#1a1200", "glow": "rgba(255,179,0,0.5)"},
    "green": {"hex": "#39ff14", "bg": "#000a00", "dark": "#001200", "glow": "rgba(57,255,20,0.5)"},
    "blue":  {"hex": "#39b4ff", "bg": "#00080a", "dark": "#001020", "glow": "rgba(57,180,255,0.5)"},
   # "red":   {"hex": "#ff3939", "bg": "#0a0000", "dark": "#1a0000", "glow": "rgba(255,57,57,0.5)"},
}

DEFAULT_TINT = "amber"

DIFFICULTY = {1: "Beginner", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}


def is_game_complete(data: dict) -> bool:
    """Return True if stage 5 and all 20 questions mastered."""
    from core.user import mastered_count
    if data["stage"] != 5:
        return False
    return (
        mastered_count(data, "capitals", 5) >= 10 and
        mastered_count(data, "flags", 5) >= 10
    )


def can_stage_up(data: dict, stage: int) -> bool:
    """
    Returns True if both stage-up conditions are met:
    1. All 20 questions mastered (10 capitals + 10 flags)
    2. XP >= 200
    3. Not already at max stage
    """
    if stage >= 5:
        return False
    from core.user import mastered_count
    capitals_done = mastered_count(data, "capitals", stage) >= 10
    flags_done    = mastered_count(data, "flags", stage) >= 10
    xp_done       = data["xp"] >= XP_PER_STAGE
    return capitals_done and flags_done and xp_done


def do_stage_up(data: dict) -> dict:
    """
    Advance to next stage, reset XP to 0.
    Mastery data is preserved.
    """
    if data["stage"] < 5:
        data["stage"] += 1
        data["xp"] = 0
    return data


def xp_bar_percent(data: dict) -> int:
    """Return XP bar fill percentage within current stage (0-200 range)."""
    return min(100, int((data["xp"] / XP_PER_STAGE) * 100))



def get_companion_info(stage: int, user_name: str = None) -> dict:
    """Return full companion display data for a given stage."""
    greeting = COMPANION_GREETINGS[stage]
    if user_name and stage >= 3:
        greeting = f"Good to see you, {user_name}! Shall we play?"
    if user_name and stage >= 4:
        greeting = f"Welcome back, {user_name}! I can launch a game for you."
    if user_name and stage >= 5:
        greeting = f"Greetings, {user_name}. We've come so far together."
    return {
        "emoji":   COMPANION_EMOJIS[stage],
        "name":    COMPANION_NAMES[stage],
        "greeting": greeting,
    }


def get_theme_name(stage: int) -> str:
    """Return the CSS theme class name for a given stage."""
    return {
        1: "s1",
        2: "s2",
        3: "s3",
        4: "s4",
        5: "s5",
    }[stage]


# XP rewards
XP_REWARDS = {
    "quiz_correct":      5,
    "quiz_complete":    20,
    "perfect_quiz":     15,   # bonus for 100%
    "personal_best":    10,
    "daily_word":       10,
    "full_day":         20,
    "streak_3":         30,
    "streak_7":         75,
    "streak_14":       150,
    "streak_30":       400,
    "streak_100":     1000,
    "steps_1000":      10,
    "active_30min":    25,
    "solar":            5,
    "pet_companion":    5,
}