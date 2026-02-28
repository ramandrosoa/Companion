"""
core/stage.py
Manages stage, XP progression, and companion state.
"""

# XP required to REACH each stage
XP_THRESHOLDS = {
    1: 0,
    2: 500,
    3: 1500,
    4: 3500,
    5: 7000,
}

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
    "red":   {"hex": "#ff3939", "bg": "#0a0000", "dark": "#1a0000", "glow": "rgba(255,57,57,0.5)"},
    "cyan":  {"hex": "#4ecdc4", "bg": "#000a09", "dark": "#001a18", "glow": "rgba(78,205,196,0.5)"},
}

DEFAULT_TINT = "amber"

DIFFICULTY = {1: "Beginner", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}


def get_stage_from_xp(xp: int) -> int:
    """Return the stage number for a given XP amount."""
    stage = 1
    for s in [5, 4, 3, 2]:
        if xp >= XP_THRESHOLDS[s]:
            stage = s
            break
    return stage


def xp_to_next_stage(xp: int, stage: int) -> int:
    """Return XP needed to reach the next stage."""
    if stage >= 5:
        return 0
    return max(0, XP_THRESHOLDS[stage + 1] - xp)


def xp_bar_percent(xp: int, stage: int) -> int:
    """Return XP bar fill percentage within current stage range."""
    if stage >= 5:
        return 100
    floor = XP_THRESHOLDS[stage]
    ceil  = XP_THRESHOLDS[stage + 1]
    span  = ceil - floor
    earned = xp - floor
    return min(100, max(0, int((earned / span) * 100)))


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