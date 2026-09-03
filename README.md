# python-weightroom

Local Python skill-reinforcement trainer. Serves coding exercises (novice →
expert), grades submissions in a sandboxed subprocess, and tracks progress
with spaced-repetition review scheduling.

## Run

```bash
uv run app.py
```

Opens a Flask server at http://localhost:5050. Starting it kills anything
already bound to that port.

## Test

```bash
uv run test_runner.py
```

Self-check for the grading harness (`runner.py`): pass/fail/error/timeout
paths, no test framework required.

## Structure

- `app.py` — Flask routes: serve exercises, grade submissions, track/persist
  progress (`data/progress.json`, gitignored).
- `runner.py` — runs submitted code against an exercise's test cases in a
  sandboxed subprocess (timeout + CPU limit).
- `exercises/{novice,intermediate,advanced,expert}.json` — exercise bank.
- `static/` — frontend (vanilla JS).
