"""
core/context.py
Builds the shared template context used by every page.
Call build() and unpack into render_template().
"""

from core.stage import (
    get_companion_info, get_theme_name,
    xp_bar_percent, xp_to_next_stage,
    STAGE_NAMES, TINT_COLORS, XP_THRESHOLDS
)


def build(data: dict) -> dict:
    """
    Build the full shared context dict from user data.
    Every template receives this plus its own page-specific keys.
    """
    stage    = data["stage"]
    xp       = data["xp"]
    tint_key = data.get("tint", "amber")
    tint     = TINT_COLORS.get(tint_key, TINT_COLORS["amber"])
    companion = get_companion_info(stage, data.get("name"))

    return {
        # Stage info
        "stage":       stage,
        "stage_name":  STAGE_NAMES[stage],
        "max_stage":   stage >= 5,

        # XP
        "xp":          xp,
        "xp_percent":  xp_bar_percent(xp, stage),
        "xp_to_next":  xp_to_next_stage(xp, stage),
        "xp_next_stage": XP_THRESHOLDS.get(stage + 1, XP_THRESHOLDS[5]),

        # Theme
        "theme":       get_theme_name(stage),
        "tint":        tint,
        "tint_key":    tint_key,

        # Companion
        "companion":   companion,

        # User
        "user_name":   data.get("name"),
        "streak":      data.get("streak", 0),
        "badges":      data.get("badges", []),

        # Stats
        "stats":       data.get("stats", {}),
        "pillars":     data.get("daily_pillars", {}),

        # All stages context (for stage switcher in dev mode)
        "all_stages":  list(range(1, 6)),
        "stage_names": STAGE_NAMES,

        # Tint colors for stage 2 picker
        "tint_colors": TINT_COLORS,

        # Raw user data (for calendar etc)
        "user":        data,
    }