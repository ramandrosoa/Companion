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
MODE        = "geo_mode"
QUESTIONS   = "geo_questions"
Q_INDEX     = "geo_q_index"
SCORE       = "geo_score"
STREAK      = "geo_streak"
BEST_STREAK = "geo_best_streak"
CORRECT     = "geo_correct"
XP_EARNED   = "geo_xp_earned"
HINTS_USED  = "geo_hints_used"   # {q_index: hints_used_count}
WRONG_COUNT = "geo_wrong_count"  # {q_index: wrong_attempts}
FLAGGED     = "geo_flagged"      # [question strings answered wrong twice]
MASTERED_HIT = "geo_mastered_hit"  # correct answers that were already mastered

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
    session[HINTS_USED]  = {}
    session[WRONG_COUNT] = {}
    session[FLAGGED]     = []
    session[MASTERED_HIT] = 0


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
        if xp_gained == 0:
            session[MASTERED_HIT] = session.get(MASTERED_HIT, 0) + 1

        # Update best streak if current streak is higher
        if session[STREAK] > session.get(BEST_STREAK, 0):
            session[BEST_STREAK] = session[STREAK]

    else:
        session[STREAK] = 0
        # Track wrong attempts for flagging
        q_index = str(session.get(Q_INDEX, 0))
        wrong = session.get(WRONG_COUNT, {})
        wrong[q_index] = wrong.get(q_index, 0) + 1
        session[WRONG_COUNT] = wrong
        # Flag question if wrong twice
        if wrong[q_index] == 2:
            q = current_question()
            if q and q["a"] not in session.get(FLAGGED, []):
                flagged = session.get(FLAGGED, [])
                flagged.append(q["a"])
                session[FLAGGED] = flagged


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

def use_hint(q_index: int) -> int:
    """
    Record that a hint was used for question at q_index.
    Returns the new hint count for that question.
    """
    hints = session.get(HINTS_USED, {})
    key = str(q_index)
    hints[key] = hints.get(key, 0) + 1
    session[HINTS_USED] = hints
    session.modified = True
    return hints[key]


def get_hints_used(q_index: int) -> int:
    """Return how many hints have been used for a given question."""
    hints = session.get(HINTS_USED, {})
    return hints.get(str(q_index), 0)

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
    correct      = session.get(CORRECT, 0)
    wrong        = total - correct
    mastered_hit = session.get(MASTERED_HIT, 0)
    pct          = int((correct / total) * 100) if total > 0 else 0
    
    xp_total = session.get(XP_EARNED, 0)

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
        "pct":              pct,
        "correct":          correct,
        "wrong":            wrong,
        "total":            total,
        "mastered_hit":     mastered_hit,
        "xp_earned":        xp_total,
        "flagged":          session.get(FLAGGED, []),
        "best_streak":      session.get(BEST_STREAK, 0),
        "mode":             session.get(MODE, "capitals"),
    }




# ─── CLEAR ──────────────────────────────────────────────────
def clear() -> None:
    """
    Wipe all game session data.
    Call this when the user finishes a game or quits back to menu.
    """
    for key in [MODE, QUESTIONS, Q_INDEX, SCORE, STREAK, BEST_STREAK, CORRECT, XP_EARNED, HINTS_USED, WRONG_COUNT, FLAGGED, MASTERED_HIT]:
        session.pop(key, None)
