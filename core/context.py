"""
core/context.py
Builds the shared template context used by every page.
Call build() and unpack with **ctx into render_template().
"""

from core.stage import (
    get_companion_info, get_theme_name,
    xp_bar_percent,
    STAGE_NAMES, TINT_COLORS
)

# Set this to True to show the dev switcher in templates
# Mirrors the DEV_MODE flag in app.py
DEV_MODE = False


def build(data: dict) -> dict:
    """
    Build the full shared context dict from user data.
    Every template receives this plus its own page-specific keys.
    All keys are flat so templates can use {{ key }} directly.
    """
    stage     = data["stage"]
    xp        = data["xp"]
    tint_key  = data.get("tint", "amber")
    tint      = TINT_COLORS.get(tint_key, TINT_COLORS["amber"])
    companion = get_companion_info(stage, data.get("name"))
    stats     = data.get("stats", {})

    return {
        # ── Stage ────────────────────────────────────────────
        "stage":          stage,
        "stage_name":     STAGE_NAMES[stage],
        "max_stage":      stage >= 5,

        # ── XP ───────────────────────────────────────────────
        "xp":             xp,
        "xp_bar_percent": xp_bar_percent(data),
        "xp_to_next":     max(0, 200 - xp),

        # ── Theme ────────────────────────────────────────────
        "theme":          get_theme_name(stage),

        # ── Tint (stage 2 color choice) ──────────────────────
        # tint_key  : "amber", "green", etc.
        # tint      : the full dict with hex/bg/dark/glow values
        # tint_hex etc. : flat values for inline CSS injection
        "tint":           tint_key,
        "tint_colors":    TINT_COLORS,
        "tint_hex":       tint["hex"],
        "tint_bg":        tint["bg"],
        "tint_dark":      tint["dark"],
       # "tint_glow":      tint["glow"],

        # ── Companion ────────────────────────────────────────
        # Flattened so templates use {{ companion_emoji }} directly
        "companion_emoji":    companion["emoji"],
        "companion_name":     companion["name"],
        "companion_greeting": companion["greeting"],

        # ── User ─────────────────────────────────────────────
        "user_name":          data.get("name"),
        "streak":             data.get("streak", 0),
        "longest_streak":     data.get("longest_streak", 0),
        "badges":             data.get("badges", []),

        # ── Stats (flat for easy template access) ────────────
        "games_played":       stats.get("games_played", 0),
        "correct_answers":    stats.get("correct_answers", 0),
        "wrong_answers":      stats.get("wrong_answers", 0),
        "best_score_capitals": stats.get("best_score_capitals", 0),
        "best_score_flags":    stats.get("best_score_flags", 0),

        # ── Daily pillars ────────────────────────────────────
        "pillars":            data.get("daily_pillars", {}),

        # ── Dev tools ────────────────────────────────────────
        "dev_mode":           DEV_MODE,
        "all_stages":         list(range(1, 6)),
        "stage_names":        STAGE_NAMES,
    }