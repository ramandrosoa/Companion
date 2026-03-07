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
from games.geography import game
from games.geography.game import DIFFICULTY, QUESTIONS_PER_STAGE, get_xp_worth

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

    ctx             = context.build(data)
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
    data            = user.load()
    ctx             = context.build(data)
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


# ─── CALENDAR ───────────────────────────────────────────────
@app.route("/calendar")
def calendar():
    from datetime import date, timedelta
    data     = user.load()
    today    = date.today()
    cal_days = []
    for i in range(69, -1, -1):
        d      = today - timedelta(days=i)
        iso    = d.isoformat()
        status = data["calendar"].get(iso, "empty")
        cal_days.append({"date": iso, "status": status})
    ctx             = context.build(data)
    ctx["cal_days"] = cal_days
    return render_template("calendar.html", **ctx)


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
    q_index      = game_session.get_progress()["current"] - 1
    hints_used   = game_session.get_hints_used(q_index)

    already_mastered = user.is_mastered(data, mode, stage, question["a"])

    ctx = context.build(data)
    ctx.update({
        "question":         question,
        "progress":         progress,
        "hints_used":       hints_used,
        "already_mastered": already_mastered,
        "difficulty":       DIFFICULTY[stage],
        "mode":             mode,
        "answered":         False,
        "feedback":         None,
        "is_correct":       None,
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
    q_index    = game_session.get_progress()["current"] - 1
    hints_used = game_session.get_hints_used(q_index)
    worth      = get_xp_worth(stage, hints_used)

    if is_correct:
        data, xp_gained = user.award_xp(data, mode, stage, question["a"], worth)
    else:
        xp_gained = 0

    game_session.record_answer(is_correct, xp_gained)

    user.save(data)

    progress = game_session.get_progress()
    ctx = context.build(data)
    ctx.update({
        "question":         question,
        "progress":         progress,
        "hints_used":       hints_used,
        "already_mastered": xp_gained == 0 and is_correct,
        "difficulty":       DIFFICULTY[stage],
        "mode":             mode,
        "answered":         True,
        "feedback":         question["fact"],
        "is_correct":       is_correct,
        "submitted":        submitted,
        "xp_gained":        xp_gained,
    })
    return render_template("games/question.html", **ctx)



# ─── NEXT QUESTION ──────────────────────────────────────────
@app.route("/geo/next", methods=["POST"])
def geo_next():
    """Advance to the next question."""
    game_session.advance()

    if game_session.is_finished():
        return redirect(url_for("geo_results"))

    return redirect(url_for("geo_question"))

# ─── USE A HINT ─────────────────────────────────────────────
@app.route("/geo/hint", methods=["POST"])
def geo_hint():
    """
    Eliminate wrong options for the current question.
    Returns updated shuffled_opts via redirect back to question.
    """
    if not game_session.is_active():
        return redirect(url_for("geo_menu"))

    data     = user.load()
    stage    = data["stage"]
    q_index  = game_session.get_progress()["current"] - 1
    hints_used = game_session.use_hint(q_index)

    question = game_session.current_question()

    # Determine target option count after this hint
    from games.geography.game import OPTIONS_PER_STAGE, apply_hint
    targets = {3: [2], 4: [3, 2], 5: [4, 3, 2]}
    target_counts = targets.get(stage, [])

    if hints_used <= len(target_counts):
        target = target_counts[hints_used - 1]
            # For S5 first hint, start from all_opts since shuffled_opts is empty
        current_opts = question.get("all_opts", question["shuffled_opts"]) if hints_used == 1 else question["shuffled_opts"]
        new_opts = apply_hint(current_opts, question["a"], target)
        # Update the question in the session
        questions = flask_session["geo_questions"]
        questions[q_index]["shuffled_opts"] = new_opts
        flask_session["geo_questions"] = questions
        flask_session.modified = True

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

    from core.stage import can_stage_up, do_stage_up
    if can_stage_up(data, stage):
        data = do_stage_up(data)
        user.save(data)
        game_session.clear()
        flask_session["stage_up_from"] = stage
        flask_session["stage_up_to"]   = data["stage"]
        return redirect(url_for("stage_up"))


    best_key = f"best_score_{mode}"
    if summary["pct"] > data["stats"].get(best_key, 0):
        data["stats"][best_key] = summary["pct"]
        summary["new_best"] = True
    else:
        summary["new_best"] = False

    data = user.mark_game_played(data)
    user.save(data)

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
    """Celebration screen shown when the user crosses a stage threshold."""
    from_stage = flask_session.pop("stage_up_from", None)
    to_stage   = flask_session.pop("stage_up_to", None)

    if not from_stage or not to_stage:
        return redirect(url_for("menu"))

    data = user.load()
    ctx  = context.build(data)
    ctx.update({
        "from_stage":  from_stage,
        "to_stage":    to_stage,
        "next_url":    url_for("menu"),
    })
    return render_template("stage_up.html", **ctx)



# ─── DEV PANEL ──────────────────────────────────────────────
@app.route("/dev")
def dev():
    """Dev panel — only accessible when DEV_MODE = True."""
    if not DEV_MODE:
        return redirect(url_for("menu"))

    data            = user.load()
    ctx             = context.build(data)
    ctx["progress"] = user.stage_progress(data, data["stage"])
    return render_template("dev.html", **ctx)


@app.route("/dev/set-xp/<int:xp>")
def dev_set_xp(xp):
    if not DEV_MODE:
        return redirect(url_for("menu"))

    data       = user.load()
    data["xp"] = xp
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
    if not DEV_MODE:
        return redirect(url_for("menu"))

    if stage not in range(1, 6):
        return redirect(url_for("dev"))

    data          = user.load()
    data["stage"] = stage
    data["xp"]    = 0
    user.save(data)
    return redirect(url_for("dev"))


# ─── RUN ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)