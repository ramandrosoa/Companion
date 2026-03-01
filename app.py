"""
app.py
Main Flask application — all routes live here.

Run with:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import (
    Flask, render_template, redirect,
    url_for, request, session as flask_session
)

from core import user, context
from core import session as game_session
from games.geo import game
from games.geo.game import DIFFICULTY, QUESTIONS_PER_STAGE

# ─── APP SETUP ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "companion-dev-key"

# Set DEV_MODE = False when running on the real device
DEV_MODE = True


# ─── HELPERS ────────────────────────────────────────────────
def get_mode() -> str:
    """Return the current game mode from the Flask session."""
    return flask_session.get("geo_mode", "capitals")


# ─── MAIN MENU ──────────────────────────────────────────────
@app.route("/")
def menu():
    data         = user.load()
    data, _      = user.check_and_update_streak(data)
    user.save(data)

    ctx          = context.build(data)
    ctx["progress"] = user.stage_progress(data, data["stage"])
    return render_template("menu.html", **ctx)


# ─── STAGE 2 TINT PICKER ────────────────────────────────────
@app.route("/set-tint/<tint_key>")
def set_tint(tint_key):
    """Save the user's chosen tint color. Only meaningful at stage 2+."""
    from core.stage import TINT_COLORS
    data = user.load()
    if tint_key in TINT_COLORS:
        data["tint"] = tint_key
        user.save(data)
    return redirect(url_for("menu"))


# ─── GEOGRAPHY MENU ─────────────────────────────────────────
@app.route("/geo")
def geo_menu():
    """Mode selection screen — Capitals or Flags."""
    data    = user.load()
    ctx     = context.build(data)
    ctx["progress"] = user.stage_progress(data, data["stage"])
    return render_template("games/geo_menu.html", **ctx)


# ─── START A NEW GAME ───────────────────────────────────────
@app.route("/geo/play/<mode>")
def geo_play(mode):
    """
    Start a new game session for the given mode.
    mode: 'capitals' or 'flags'
    Redirects to the first question.
    """
    if mode not in ("capitals", "flags"):
        return redirect(url_for("geo_menu"))

    data      = user.load()
    stage     = data["stage"]
    questions = game.get_session_questions(mode, stage)

    game_session.start(mode, questions)
    return redirect(url_for("geo_question"))


# ─── SHOW CURRENT QUESTION ──────────────────────────────────
@app.route("/geo/question")
def geo_question():
    """Render the current question in the session."""
    if not game_session.is_active():
        return redirect(url_for("geo_menu"))

    if game_session.is_finished():
        return redirect(url_for("geo_results"))

    data     = user.load()
    stage    = data["stage"]
    mode     = get_mode()
    question = game_session.current_question()
    progress = game_session.get_progress()
    hint     = game.get_hint(question, stage)

    # Check if this question is already mastered
    already_mastered = user.is_mastered(data, mode, stage, question["a"])

    ctx = context.build(data)
    ctx.update({
        "question":          question,
        "progress":          progress,
        "hint":              hint,
        "already_mastered":  already_mastered,
        "difficulty":        DIFFICULTY[stage],
        "mode":              mode,
        "answered":          False,
        "feedback":          None,
        "is_correct":        None,
    })
    return render_template("games/question.html", **ctx)


# ─── SUBMIT AN ANSWER ───────────────────────────────────────
@app.route("/geo/answer", methods=["POST"])
def geo_answer():
    """
    Receive the submitted answer, check it, award XP if first-time correct,
    then re-render the question screen with feedback shown.
    """
    if not game_session.is_active():
        return redirect(url_for("geo_menu"))

    data      = user.load()
    stage     = data["stage"]
    old_stage = stage
    mode      = get_mode()
    question  = game_session.current_question()
    submitted = request.form.get("answer", "")

    is_correct = game.check_answer(question, submitted)

    # XP only awarded for first-time correct answers
    if is_correct:
        data, xp_awarded = user.master_question(data, mode, stage, question["a"])
        xp_gained = 10 if xp_awarded else 0
    else:
        xp_gained = 0

    # Record answer in session
    game_session.record_answer(is_correct, xp_gained)

    # Check if the user just crossed a stage threshold
    new_stage = data["stage"]
    if new_stage > old_stage:
        flask_session["stage_up_from"] = old_stage
        flask_session["stage_up_to"]   = new_stage

    # Save updated user data
    user.save(data)

    # Re-render question with feedback visible
    progress = game_session.get_progress()
    hint     = game.get_hint(question, stage)

    ctx = context.build(data)
    ctx.update({
        "question":          question,
        "progress":          progress,
        "hint":              hint,
        "already_mastered":  xp_gained == 0 and is_correct,
        "difficulty":        DIFFICULTY[stage],
        "mode":              mode,
        "answered":          True,
        "feedback":          question["fact"],
        "is_correct":        is_correct,
        "submitted":         submitted,
        "xp_gained":         xp_gained,
    })
    return render_template("games/question.html", **ctx)


# ─── NEXT QUESTION ──────────────────────────────────────────
@app.route("/geo/next", methods=["POST"])
def geo_next():
    """
    Advance to the next question.
    Called when user clicks the Next button after seeing feedback.
    """
    game_session.advance()

    if game_session.is_finished():
        return redirect(url_for("geo_results"))

    return redirect(url_for("geo_question"))


# ─── RESULTS ────────────────────────────────────────────────
@app.route("/geo/results")
def geo_results():
    """Show the end of game results screen."""
    if not game_session.is_finished():
        return redirect(url_for("geo_menu"))

    data    = user.load()
    stage   = data["stage"]
    mode    = get_mode()
    summary = game_session.get_summary()

    # Award completion and perfect bonuses
    # Mastery XP was already saved during the game in geo_answer
    bonus = summary["xp_completion"] + summary["xp_perfect"]
    if bonus > 0:
        data = user.add_xp(data, bonus)

    # Update best score if this session beats the record
    best_key = f"best_score_{mode}"
    if summary["score"] > data["stats"].get(best_key, 0):
        data["stats"][best_key] = summary["score"]
        summary["new_best"] = True
    else:
        summary["new_best"] = False

    # Mark game as played for today's daily pillar
    data = user.mark_game_played(data)
    user.save(data)

    # Clear the game session
    game_session.clear()

    ctx = context.build(data)
    ctx.update({
        "summary":  summary,
        "mode":     mode,
        "progress": user.stage_progress(data, stage),
    })
    return render_template("games/results.html", **ctx)


# ─── STAGE TRANSITION SCREEN ────────────────────────────────
@app.route("/stage-up")
def stage_up():
    """
    Celebration screen shown when the user crosses a stage threshold.
    Redirects to results after the user continues.
    """
    from_stage = flask_session.pop("stage_up_from", None)
    to_stage   = flask_session.pop("stage_up_to", None)

    if not from_stage or not to_stage:
        return redirect(url_for("menu"))

    data = user.load()
    ctx  = context.build(data)
    ctx.update({
        "from_stage": from_stage,
        "to_stage":   to_stage,
    })
    return render_template("stage_up.html", **ctx)


# ─── DEV PANEL ──────────────────────────────────────────────
@app.route("/dev")
def dev():
    """Dev panel — only accessible when DEV_MODE = True."""
    if not DEV_MODE:
        return redirect(url_for("menu"))

    data = user.load()
    ctx  = context.build(data)
    ctx["progress"] = user.stage_progress(data, data["stage"])
    return render_template("dev.html", **ctx)


@app.route("/dev/set-xp/<int:xp>")
def dev_set_xp(xp):
    """Set XP directly to any value. Dev only."""
    if not DEV_MODE:
        return redirect(url_for("menu"))

    from core.stage import get_stage_from_xp
    data          = user.load()
    data["xp"]    = xp
    data["stage"] = get_stage_from_xp(xp)
    user.save(data)
    return redirect(url_for("dev"))


@app.route("/dev/reset")
def dev_reset():
    """Reset all user data back to zero. Dev only."""
    if not DEV_MODE:
        return redirect(url_for("menu"))

    user.save(user.DEFAULT_CONFIG.copy())
    game_session.clear()
    return redirect(url_for("dev"))


@app.route("/dev/set-stage/<int:stage>")
def dev_set_stage(stage):
    """Jump directly to a stage by setting XP to its threshold. Dev only."""
    if not DEV_MODE:
        return redirect(url_for("menu"))

    from core.stage import XP_THRESHOLDS
    if stage not in XP_THRESHOLDS:
        return redirect(url_for("dev"))

    data          = user.load()
    data["xp"]    = XP_THRESHOLDS[stage]
    data["stage"] = stage
    user.save(data)
    return redirect(url_for("dev"))


# ─── RUN ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)