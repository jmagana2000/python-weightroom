"""Flask app: serves exercises, grades submissions, tracks progress."""

import json
import os
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from runner import run_submission
from sql_runner import run_sql_submission

BASE_DIR = Path(__file__).parent
EXERCISES_DIR = BASE_DIR / "exercises"
PROGRESS_FILE = BASE_DIR / "data" / "progress.json"
PY_LEVELS = ["novice", "intermediate", "advanced", "expert"]
SQL_LEVELS = ["sql-novice", "sql-intermediate", "sql-advanced", "sql-expert"]
LEVELS = PY_LEVELS + SQL_LEVELS
LEVEL_UP_THRESHOLD = 0.8
PORT = 5050

# Spaced-repetition schedule for solved exercises: SM-2-lite. First solve
# schedules a review in 1 day; each successful review doubles the interval
# (capped); failing a review (getting a previously-solved exercise wrong
# again) resets it back to 1 day.
REVIEW_INITIAL_DAYS = 1
REVIEW_MAX_DAYS = 60

app = Flask(__name__, static_folder="static", static_url_path="")


def load_exercises(level: str) -> list:
    path = EXERCISES_DIR / f"{level}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def find_exercise(exercise_id: str) -> dict | None:
    for level in LEVELS:
        for ex in load_exercises(level):
            if ex["id"] == exercise_id:
                return ex
    return None


def load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        progress = {"level": "novice", "solved": [], "attempts": {}}
    else:
        progress = json.loads(PROGRESS_FILE.read_text())
    progress.setdefault("review", {})  # ex_id -> {"interval_days", "next_due"}
    progress.setdefault("sql_level", "sql-novice")  # SQL track's own current level
    return progress


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/exercises")
def list_exercises():
    level = request.args.get("level", "novice")
    exercises = load_exercises(level)
    return jsonify(
        [
            {k: v for k, v in ex.items() if k not in ("tests", "starter_code")}
            for ex in exercises
        ]
    )


@app.get("/api/exercises/<exercise_id>")
def get_exercise(exercise_id):
    ex = find_exercise(exercise_id)
    if ex is None:
        return jsonify({"error": "not found"}), 404
    tests = ex["tests"]
    body = {k: v for k, v in ex.items() if k != "tests"}
    body["example"] = pick_example(tests)
    body["hidden_test_count"] = len(tests) - 1
    return jsonify(body)


_BORING_EXPECTED = (None, "", [], {})


def pick_example(tests: list) -> dict:
    """One worked example for the exercise page; the rest of the suite stays
    hidden so passing can't be hardcoded from the page alone. `expect_error`
    tests have no "expected" value to show, so they're never picked as the
    example (only as hidden tests). Edge cases are seeded at the front of
    each test list, so the last test tends to be more representative — but
    skip ones with an uninformative expected value (None/""/[]/{}, e.g.
    two_sum with no valid pair) when a better one exists.
    """
    normal = [t for t in tests if "expected" in t]
    non_boring = [t for t in reversed(normal) if t["expected"] not in _BORING_EXPECTED]
    if non_boring:
        return non_boring[0]
    return normal[-1] if normal else tests[-1]


@app.post("/api/exercises/<exercise_id>/submit")
def submit_exercise(exercise_id):
    ex = find_exercise(exercise_id)
    if ex is None:
        return jsonify({"error": "not found"}), 404

    code = request.get_json(force=True).get("code", "")
    if ex.get("language") == "sql":
        outcome = run_sql_submission(code, ex["schema_sql"], ex["tests"])
    else:
        outcome = run_submission(code, ex["func_name"], ex["tests"])

    progress = load_progress()
    attempts = progress["attempts"].setdefault(exercise_id, 0)
    progress["attempts"][exercise_id] = attempts + 1

    all_passed = outcome["status"] == "ok" and all(
        r["passed"] for r in outcome["results"]
    )
    level_up = None
    already_solved = exercise_id in progress["solved"]
    chain = SQL_LEVELS if ex["level"] in SQL_LEVELS else PY_LEVELS
    if all_passed and not already_solved:
        progress["solved"].append(exercise_id)
        level_up = maybe_suggest_level_up(progress, chain)
    if all_passed:
        schedule_review(progress, exercise_id, is_first_solve=not already_solved)
    elif already_solved:
        # Got a previously-solved exercise wrong on a review attempt --
        # retention slipped, so review it again soon rather than waiting
        # out the interval it had earned.
        reset_review(progress, exercise_id)
    save_progress(progress)

    return jsonify(
        {"outcome": outcome, "solved": all_passed, "level_up_available": level_up}
    )


def schedule_review(progress: dict, exercise_id: str, is_first_solve: bool) -> None:
    entry = progress["review"].get(exercise_id)
    if is_first_solve or entry is None:
        interval = REVIEW_INITIAL_DAYS
    else:
        interval = min(entry["interval_days"] * 2, REVIEW_MAX_DAYS)
    progress["review"][exercise_id] = {
        "interval_days": interval,
        "next_due": (date.today() + timedelta(days=interval)).isoformat(),
    }


def reset_review(progress: dict, exercise_id: str) -> None:
    progress["review"][exercise_id] = {
        "interval_days": REVIEW_INITIAL_DAYS,
        "next_due": (date.today() + timedelta(days=REVIEW_INITIAL_DAYS)).isoformat(),
    }


def due_review_ids(progress: dict) -> list[str]:
    today = date.today().isoformat()
    return sorted(
        ex_id
        for ex_id, entry in progress["review"].items()
        if entry["next_due"] <= today
    )


def maybe_suggest_level_up(progress: dict, chain: list[str]) -> str | None:
    current = progress["sql_level"] if chain is SQL_LEVELS else progress["level"]
    if current not in chain or current == chain[-1]:
        return None
    total = len(load_exercises(current))
    if total == 0:
        return None
    solved_at_level = sum(
        1 for ex_id in progress["solved"] if ex_id.startswith(current + "-")
    )
    if solved_at_level / total >= LEVEL_UP_THRESHOLD:
        return chain[chain.index(current) + 1]
    return None


@app.get("/api/progress")
def get_progress():
    progress = load_progress()
    return jsonify({**progress, "due_for_review": due_review_ids(progress)})


@app.post("/api/progress")
def set_progress():
    body = request.get_json(force=True)
    level = body.get("level")
    if level not in LEVELS:
        return jsonify({"error": f"level must be one of {LEVELS}"}), 400
    progress = load_progress()
    if level in SQL_LEVELS:
        progress["sql_level"] = level
    else:
        progress["level"] = level
    save_progress(progress)
    return jsonify({**progress, "due_for_review": due_review_ids(progress)})


def _kill_port(port: int) -> None:
    # ponytail: macOS/Linux only (relies on lsof) -- fine for a "run it on
    # my laptop" dev server. Lets `uv run python app.py` just work even if
    # a previous run is still holding the port, instead of failing to bind.
    try:
        pids = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True
        ).stdout.split()
    except FileNotFoundError:
        return
    if not pids:
        return
    subprocess.run(["kill", *pids])
    time.sleep(0.3)


if __name__ == "__main__":
    # debug=True's reloader re-execs this file in a child process; only kill
    # from the outer process (before that child exists) -- calling it again
    # from inside the reloader child stomps on the reloader's own subprocess
    # bookkeeping and kills the whole server instead of just the old port.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        _kill_port(PORT)
    app.run(debug=True, port=PORT)
