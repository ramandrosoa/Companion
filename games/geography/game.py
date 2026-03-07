"""
games/geography/game.py
Shared logic for all geography game modes.
"""

import json
import os
import random

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "questions.json")

# Questions per session per stage
QUESTIONS_PER_STAGE = {1: 5, 2: 6, 3: 7, 4: 8, 5: 8}

# Number of options shown per stage (before any hints)
OPTIONS_PER_STAGE = {1: 2, 2: 3, 3: 4, 4: 5, 5: 0}  # 0 = type answer

# Difficulty labels
DIFFICULTY = {1: "Beginner", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}

# XP worth per attempt depending on hints used
XP_WORTH = {
    # (stage, hints_used): xp_worth
    (1, 0): 10,
    (2, 0): 10,
    (3, 0): 10, (3, 1): 5,
    (4, 0): 10, (4, 1): 6, (4, 2): 2,
    (5, 0): 10, (5, 1): 7, (5, 2): 4, (5, 3): 1,
}


def load_questions() -> dict:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_session_questions(mode: str, stage: int) -> list:
    """
    Pick a random set of questions for a game session.
    Slices options to the correct count for the stage.
    """
    all_q = load_questions()
    pool = all_q[mode][str(stage)]
    count = QUESTIONS_PER_STAGE[stage]
    selected = random.sample(pool, min(count, len(pool)))

    n_opts = OPTIONS_PER_STAGE[stage]
    for q in selected:
        if n_opts > 0:
            wrong = [o for o in q["opts"] if o != q["a"]]
            random.shuffle(wrong)
            opts = wrong[:n_opts - 1] + [q["a"]]
            random.shuffle(opts)
            q["shuffled_opts"] = opts
        else:
            # S5 type answer — store all 4 opts for hint elimination
            # but shuffled_opts starts empty until first hint is used
            opts = q["opts"][:]
            random.shuffle(opts)
            q["all_opts"] = opts
            q["shuffled_opts"] = []
    return selected


def get_xp_worth(stage: int, hints_used: int) -> int:
    """Return XP this attempt is worth given stage and hints used."""
    return XP_WORTH.get((stage, hints_used), 0)


def apply_hint(shuffled_opts: list, correct: str, target_count: int) -> list:
    """
    Eliminate wrong options down to target_count.
    Always keeps the correct answer.
    Returns new shuffled_opts list.
    """
    wrong = [o for o in shuffled_opts if o != correct]
    random.shuffle(wrong)
    keep_wrong = wrong[:target_count - 1]
    new_opts = keep_wrong + [correct]
    random.shuffle(new_opts)
    return new_opts


def check_answer(question: dict, submitted: str) -> bool:
    return submitted.strip() == question["a"]


def session_max_xp(stage: int) -> int:
    return QUESTIONS_PER_STAGE[stage] * 10