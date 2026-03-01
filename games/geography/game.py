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

# Difficulty labels
DIFFICULTY = {1: "Beginner", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}


def load_questions() -> dict:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_session_questions(mode: str, stage: int) -> list:
    """
    Pick a random set of questions for a game session.
    mode: 'capitals' or 'flags'
    """
    all_q = load_questions()
    pool = all_q[mode][str(stage)]
    count = QUESTIONS_PER_STAGE[stage]
    selected = random.sample(pool, min(count, len(pool)))
    # Shuffle answer options for each question
    for q in selected:
        opts = q["opts"][:]
        random.shuffle(opts)
        q["shuffled_opts"] = opts
    return selected


def check_answer(question: dict, submitted: str) -> bool:
    return submitted == question["a"]



def get_hint(question: dict, stage: int) -> str | None:
    """Return a hint string for stages 2-3, None otherwise."""
    if stage == 2:
        return f"Starts with '{question['a'][0]}'"
    if stage == 3:
        return f"Starts with '{question['a'][:2]}'"
    return None

def session_max_xp(stage: int) -> int:
    return QUESTIONS_PER_STAGE[stage] * 10 + 20 + 15