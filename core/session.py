"""
core/session.py
Manages temporary quiz session state between page loads.
Uses Flask's built-in session (stored as a browser cookie).

This is DIFFERENT from user.py:
  - user.py  = permanent data saved to config.json (XP, stage, streak)
  - session.py = temporary data that lives only during a game (score, current question)

When a game ends or the user quits, the session is cleared.
"""

from flask import session


# ─── SESSION KEYS ───────────────────────────────────────────
# Using constants avoids typos when reading/writing session keys
MODE       = "geo_mode"        # "capitals" or "flags"
QUESTIONS  = "geo_questions"   # list of question dicts for this session
Q_INDEX    = "geo_q_index"     # which question we're on (0-based)
SCORE      = "geo_score"       # current score (10 pts per correct answer)
STREAK     = "geo_streak"      # current consecutive correct streak
BEST_STREAK= "geo_best_streak" # highest streak reached this session
CORRECT    = "geo_correct"     # total correct answers
XP_EARNED  = "geo_xp_earned"   # XP accumulated so far this session


# ─── START ──────────────────────────────────────────────────
def start(mode: str, questions: list) -> None:
    """
    Start a new game session.
    Call this when the user clicks Play on the geo menu.
    Wipes any previous session data and starts fresh.
    """
    session[MODE]        = mode
    session[QUESTIONS]   = questions
    session[Q_INDEX]     = 0
    session[SCORE]       = 0
    session[STREAK]      = 0
    session[BEST_STREAK] = 0
    session[CORRECT]     = 0
    session[XP_EARNED]   = 0


# ─── READ ───────────────────────────────────────────────────
def current_question() -> dict | None:
    """
    Return the current question dict, or None if session is empty.
    Example return value:
    {
        "q": "What is the capital of France?",
        "opts": ["London", "Berlin", "Paris", "Madrid"],
        "a": "Paris",
        "fact": "Paris is also known as the City of Light!",
        "shuffled_opts": ["Madrid", "Paris", "London", "Berlin"]
    }
    """
    questions = session.get(QUESTIONS, [])
    index     = session.get(Q_INDEX, 0)
    if not questions or index >= len(questions):
        return None
    return questions[index]


def is_active() -> bool:
    """Return True if there is an active game session."""
    return QUESTIONS in session and len(session[QUESTIONS]) > 0


def is_finished() -> bool:
    """Return True if all questions have been answered."""
    questions = session.get(QUESTIONS, [])
    index     = session.get(Q_INDEX, 0)
    return len(questions) > 0 and index >= len(questions)


def get_progress() -> dict:
    """
    Return current progress info for display in the quiz header.
    Example: {"current": 3, "total": 7, "score": 20, "streak": 2}
    """
    questions = session.get(QUESTIONS, [])
    return {
        "current":     session.get(Q_INDEX, 0) + 1,
        "total":       len(questions),
        "score":       session.get(SCORE, 0),
        "streak":      session.get(STREAK, 0),
        "best_streak": session.get(BEST_STREAK, 0),
        "correct":     session.get(CORRECT, 0),
        "xp_earned":   session.get(XP_EARNED, 0),
        "mode":        session.get(MODE, "capitals"),
    }


# ─── UPDATE ─────────────────────────────────────────────────
def record_answer(is_correct: bool, xp_gained: int) -> None:
    """
    Update session state after the user submits an answer.
    Call this immediately after checking if the answer is right or wrong.

    xp_gained: pass 10 if first-time correct, 0 if already mastered or wrong.
    The caller (app.py) determines xp_gained using user.master_question().
    """
    if is_correct:
        session[SCORE]     = session.get(SCORE, 0) + 10
        session[CORRECT]   = session.get(CORRECT, 0) + 1
        session[STREAK]    = session.get(STREAK, 0) + 1
        session[XP_EARNED] = session.get(XP_EARNED, 0) + xp_gained

        # Update best streak if current streak is higher
        if session[STREAK] > session.get(BEST_STREAK, 0):
            session[BEST_STREAK] = session[STREAK]
    else:
        # Wrong answer resets the streak but no penalty
        session[STREAK] = 0

    # Force Flask to recognise the session has changed
    # (needed because we're mutating values, not replacing them)
    session.modified = True


def advance() -> None:
    """
    Move to the next question.
    Call this after showing feedback and the user taps Next.
    """
    session[Q_INDEX] = session.get(Q_INDEX, 0) + 1
    session.modified = True


# ─── SUMMARY ────────────────────────────────────────────────
def get_summary() -> dict:
    """
    Build the full results summary at the end of a game.
    Returns everything needed to render the results screen.

    XP breakdown:
    - xp_from_mastery : XP earned from newly mastered questions this session
    - xp_completion   : flat +20 for finishing the session
    - xp_perfect      : flat +15 if every answer was correct
    - xp_earned       : total XP awarded this session
    """
    questions  = session.get(QUESTIONS, [])
    total      = len(questions)
    correct    = session.get(CORRECT, 0)
    score      = session.get(SCORE, 0)
    max_score  = total * 10
    pct        = int((score / max_score) * 100) if max_score > 0 else 0

    xp_from_mastery = session.get(XP_EARNED, 0)
    xp_completion   = 20
    xp_perfect      = 15 if pct == 100 else 0
    xp_total        = xp_from_mastery + xp_completion + xp_perfect

    # Pick result emoji and title based on percentage
    if pct == 100:
        emoji, title = "🏆", "Perfect Score!"
    elif pct >= 80:
        emoji, title = "🌟", "Amazing!"
    elif pct >= 50:
        emoji, title = "👏", "Good Job!"
    else:
        emoji, title = "🌱", "Keep Going!"

    return {
        "emoji":            emoji,
        "title":            title,
        "score":            score,
        "max_score":        max_score,
        "pct":              pct,
        "correct":          correct,
        "wrong":            total - correct,
        "total":            total,
        "xp_from_mastery":  xp_from_mastery,
        "xp_completion":    xp_completion,
        "xp_perfect":       xp_perfect,
        "xp_earned":        xp_total,
        "best_streak":      session.get(BEST_STREAK, 0),
        "mode":             session.get(MODE, "capitals"),
    }


# ─── CLEAR ──────────────────────────────────────────────────
def clear() -> None:
    """
    Wipe all game session data.
    Call this when the user finishes a game or quits back to menu.
    """
    for key in [MODE, QUESTIONS, Q_INDEX, SCORE, STREAK, BEST_STREAK, CORRECT, XP_EARNED]:
        session.pop(key, None)