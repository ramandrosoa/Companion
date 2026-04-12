"""
app.py
Main Flask application — all routes live here.

Run with:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import (
    Flask, render_template, redirect,
    url_for, request, session as flask_session, jsonify
)
from datetime import timedelta
import os
from dotenv import load_dotenv
from groq import Groq
from core.user import username_exists, create_user, find_by_email
from core import user, context
from core import session as game_session
from games.geography import game
from games.geography.game import DIFFICULTY, QUESTIONS_PER_STAGE, get_xp_worth
from pip_prompts import get_system_prompt, build_game_context
from datetime import timedelta
import random
from core.stage import is_game_complete


load_dotenv()
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])


# ─── APP SETUP ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "companion-dev-key"
app.permanent_session_lifetime = timedelta(days = 30)

# Set DEV_MODE = False when running on the real device
DEV_MODE = False


# ─── HELPERS ────────────────────────────────────────────────
def get_mode() -> str:
    """Return the current game mode from the Flask session."""
    return flask_session.get("geo_mode", "capitals")

# ─── ONBOARDING GUARD ───────────────────────────────────────
@app.before_request
def require_username():
    allowed = ["login_page", "signup", "static", "ping"]
    if request.endpoint in allowed:
        return
    if "username" not in flask_session:
        return redirect(url_for("login_page"))
    # Check user still exists in Redis
    from core.user import username_exists
    if not username_exists(flask_session["username"]):
        flask_session.clear()
        return redirect(url_for("login_page"))


# ─── LOGIN ──────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        if not identifier:
            error = "Please enter your username or email."
        else:
            from core.user import login
            username = login(identifier)
            if username:
                flask_session["username"] = username
                flask_session.permanent = True
                return redirect(url_for("menu"))
            else:
                error = "No account found. Check your username or email, or sign up below."
    return render_template("login.html", error=error,
        theme="s1", stage=1, stage_name="Seed",
        companion_emoji="✨", xp_bar_percent=0,
        xp_to_next=200, max_stage=False,
        dev_mode=False, all_stages=[],
        stage_names={}, tint_hex=None,
        tint_bg=None, tint_dark=None, tint_glow=None)


# ─── SIGN UP ────────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()

        if not username or not email:
            error = "Both username and email are required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif len(username) > 20:
            error = "Username must be under 20 characters."
        elif not username.replace("_","").replace("-","").isalnum():
            error = "Username: only letters, numbers, - and _ allowed."
        elif "@" not in email:
            error = "Please enter a valid email address."
        elif username_exists(username):
            error = "That username is already taken."
        elif find_by_email(email):
            error = "An account with that email already exists."
        else:
            create_user(username, email)
            flask_session["username"] = username
            flask_session.permanent = True
            return redirect(url_for("menu"))

    return render_template("signup.html", error=error,
        theme="s1", stage=1, stage_name="Seed",
        companion_emoji="✨", xp_bar_percent=0,
        xp_to_next=200, max_stage=False,
        dev_mode=False, all_stages=[],
        stage_names={}, tint_hex=None,
        tint_bg=None, tint_dark=None, tint_glow=None)


# ─── LOGOUT ─────────────────────────────────────────────────
@app.route("/logout")
def logout():
    flask_session.clear()
    return redirect(url_for("login_page"))

# ─── PING ───────────────────────────────────────────────────
@app.route("/ping")
def ping():
    return "ok", 200


# ─── MAIN MENU ──────────────────────────────────────────────
@app.route("/")
def menu():
    flask_session.permanent = True
    data = user.load()
    if data is None:
        flask_session.clear()
        return redirect(url_for("login_page"))
    data, _ = user.check_and_update_streak(data)
    user.save(data)

    ctx             = context.build(data)
    ctx["progress"] = user.stage_progress(data, data["stage"])
    ctx["pep_auto"]         = None
    username = flask_session.get("username", "there")
    ctx["pep_welcome_back"] = f"Welcome back, {username}! Ready to explore some geography today?"

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
    ctx              = context.build(data)
    ctx["progress"]  = user.stage_progress(data, data["stage"])
    ctx["best_capitals"] = data["stats"].get("best_capitals", {"pct": 0, "time": None})
    ctx["best_flags"]    = data["stats"].get("best_flags",    {"pct": 0, "time": None})

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

    theoretical = get_xp_worth(stage, hints_used) if is_correct else 0
    game_session.record_answer(is_correct, xp_gained, theoretical)

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
        data["stats"]["best_capitals"] = {"pct": 0, "time": None}
        data["stats"]["best_flags"]    = {"pct": 0, "time": None}
        user.save(data)
        game_session.clear()
        flask_session["stage_up_from"] = stage
        flask_session["stage_up_to"]   = data["stage"]
        return redirect(url_for("stage_up"))

    best_key    = f"best_{mode}"
    current_best = data["stats"].get(best_key, {"pct": 0, "time": None})
    new_pct     = summary["pct"]
    new_time    = summary["duration"]

    is_new_best = (
        new_pct > current_best["pct"] or
        (new_pct == current_best["pct"] and current_best["time"] is not None and new_time < current_best["time"])
    )

    if is_new_best:
        data["stats"][best_key] = {"pct": new_pct, "time": new_time}
        summary["new_best"] = True
    else:
        summary["new_best"] = False
    

    data = user.mark_game_played(data)
    user.save(data)

    if is_game_complete(data):
        return redirect(url_for("game_complete"))

    # Set Pep game context so he knows how the session went
    flask_session["pep_game_context"] = build_game_context(
        stage, mode,
        summary["correct"], summary["wrong"],
        summary["total"],   summary["mastered_hit"],
        summary["flagged"]
    )

    game_session.clear()

    ctx = context.build(data)

    # Build Pep auto-open message based on performance
    pct     = summary["pct"]
    correct = summary["correct"]
    total   = summary["total"]
    flagged = summary["flagged"]

    # Append flagged questions naturally

    perfect_msgs = [
        f"Perfect score! {correct}/{total} correct. You're on fire! 🔥",
        f"Flawless! {correct}/{total} — not a single mistake. Incredible. 🏆",
        f"{correct}/{total}. Clean sweep! You really know your geography. ⭐",
        f"100%! Every single one correct. That's mastery right there. 🌟",
        f"Wow — {correct}/{total}. Nothing got past you today. 🔥",
    ]
    great_msgs = [
        f"Great game! {correct}/{total} correct. Really solid work.",
        f"Strong session — {correct}/{total}. You're getting sharper. 💪",
        f"{correct}/{total} correct. Nearly perfect — just a couple slipped through.",
        f"Nice work! {correct}/{total}. You clearly know most of this. 🌍",
        f"{correct}/{total} — that's a great score. Keep this up. ✨",
    ]
    ok_msgs = [
        f"{correct}/{total} correct. Not bad — keep at it!",
        f"Decent effort — {correct}/{total}. There's room to grow though.",
        f"{correct}/{total}. Halfway there! A bit more practice and you'll nail it.",
        f"Not bad at all — {correct}/{total}. You're building knowledge. 📚",
        f"{correct}/{total} correct. Solid base — keep pushing. 🌱",
    ]
    tough_msgs = [
        f"Tough one — {correct}/{total} correct. Don't worry, every attempt builds knowledge.",
        f"{correct}/{total}. This one was hard. The only way is up from here. 💪",
        f"Rough session — {correct}/{total}. But you showed up, and that matters.",
        f"{correct}/{total} correct. Don't be discouraged — this stuff takes time. 🌱",
        f"Only {correct}/{total} this time. Review those countries and try again!",
    ]

    if pct == 100:
        pep_auto = random.choice(perfect_msgs)
    elif pct >= 80:
        pep_auto = random.choice(great_msgs)
    elif pct >= 50:
        pep_auto = random.choice(ok_msgs)
    else:
        pep_auto = random.choice(tough_msgs)

    # Append flagged questions naturally
    if flagged:
        single_flagged_msgs = [
            f" Looks like {flagged[0]} gave you some trouble.",
            f" I noticed you struggled a bit with {flagged[0]}.",
            f" Worth reviewing {flagged[0]} — that one tripped you up.",
            f" {flagged[0]} was a tough one for you today.",
            f" Keep an eye on {flagged[0]} — it slipped past you this time.",
        ]
        multi_flagged_msgs = [
            f" A few gave you trouble: {', '.join(flagged)}. Worth revisiting those.",
            f" You had some difficulty with {', '.join(flagged)}. Don't worry — practice makes perfect.",
            f" {', '.join(flagged)} were tricky ones. Give them another look.",
            f" I'd review {', '.join(flagged)} if I were you — those ones caught you out.",
            f" Stumbled on {', '.join(flagged)}. Keep an eye on those next time.",
        ]
        if len(flagged) == 1:
            pep_auto += random.choice(single_flagged_msgs)
        else:
            pep_auto += random.choice(multi_flagged_msgs)

    if flagged:
        if len(flagged) == 1:
            pep_auto += f" I noticed you had some trouble with {flagged[0]}."
        else:
            countries = ", ".join(flagged)
            pep_auto += f" A few questions gave you trouble: {countries}. Worth revisiting those."

    ctx.update({
        "summary":      summary,
        "mode":         mode,
        "progress":     user.stage_progress(data, stage),
        "pep_auto":     pep_auto,
        "best_record":  data["stats"].get(f"best_{mode}", {"pct": 0, "time": None}),
    })

    return render_template("games/results.html", **ctx)

# ─── PEP CHAT ───────────────────────────────────────────────
@app.route("/pep", methods=["POST"])
def pep_chat():
    """
    Receive a message from the Pep widget.
    Returns a JSON response with Pep's reply.
    """
    data     = user.load()
    stage    = data["stage"]
    payload  = request.get_json()
    message  = payload.get("message", "").strip()

    if not message:
        return jsonify({"reply": ""})

    # Build or retrieve conversation history
    history = flask_session.get("pep_history", [])

    # Game context — set after a game ends, cleared once Pep acknowledges it
    game_context = flask_session.get("pep_game_context", None)

    # Build system prompt with optional game context
    system = get_system_prompt(stage, game_context, username=flask_session.get('username'))

    # Call Groq
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                *history,
                {"role": "user", "content": message}
            ],
            max_tokens=200,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = "Sorry, I can't talk right now."
        print(f"Groq error: {e}")

    # Update history
    history.append({"role": "user",      "content": message})
    history.append({"role": "assistant", "content": reply})

    # Keep last 20 messages to avoid token overflow
    if len(history) > 10:
        history = history[-10:]

    flask_session["pep_history"]      = history
    flask_session["pep_game_context"] = None  # clear after first use
    flask_session.modified = True

    return jsonify({"reply": reply})

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

    stage_names = {1:"Seed",2:"Sprout",3:"Sapling",4:"Tree",5:"Ancient"}
    pep_autos = {
        2: "You reached Stage 2! The screen just changed — that's all you. Welcome to Sprout. 🌿",
        3: "Stage 3 unlocked! Colors everywhere now. You've earned it. Welcome to Sapling. 🌳",
        4: "Stage 4. The whole interface transformed. You've grown past the retro phase. Welcome to Tree. 🌲",
        5: "Stage 5. The final form. Very few make it here. Welcome to Ancient. ✨",
    }
    ctx.update({
        "from_stage":  from_stage,
        "to_stage":    to_stage,
        "next_url":    url_for("menu"),
        "pep_auto":    pep_autos.get(to_stage, "You leveled up!"),
    })

    return render_template("stage_up.html", **ctx)

# ─── GAME COMPLETE ──────────────────────────────────────────
@app.route("/complete")
def game_complete():
    data = user.load()
    ctx  = context.build(data)
    ctx["pep_auto"] = "You did it. Every single country, every stage. This is as far as the game goes — and you made it. 🏆"
    return render_template("complete.html", **ctx)


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
    app.run(debug=False, host='0.0.0.0')