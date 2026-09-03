# python-weightroom 🏋️

A local, self-hosted skill-reinforcement trainer — like LeetCode/HackerRank,
but private, offline-friendly, and adaptive to your own pace. It exists to
answer one question on demand: *"give me a problem at my level, right now,
that actually checks whether I understand this."*

It currently trains two skills, each as its own leveled track:

- **🐍 Python** — novice → intermediate → advanced → expert, 100+ exercises
  per level (401 total), covering everything from basic loops to dynamic
  programming and a hand-written refactoring kata.
- **🗄️ SQL** — novice → intermediate → advanced → expert, 100 exercises per
  level (400 total), covering the kinds of problems Joe Celko's books and
  LeetCode/HackerRank's SQL sections are known for — gaps-and-islands,
  window functions, recursive CTEs, relational division, sessionization,
  medians — all original content, not reproductions.

Everything runs on your machine. No account, no cloud grading, no telemetry.

## Why this exists

Generic problem sets don't adapt to you: they're either too easy (bored),
too hard (stuck), or cover topics you already know cold. This app is a
single-user trainer that:

1. **Grades for real** — your code/query actually runs against hidden test
   cases, not just a syntax check.
2. **Hides most of the test suite** — you see one worked example per
   exercise; the rest (usually a dozen-plus cases, including edge cases)
   only run when you submit, so you can't hardcode your way to a pass.
3. **Shows you what actually happened when you're stuck** — every test
   result (pass *or* fail) displays the exact inputs it ran with, so you
   can reproduce and debug the failure yourself instead of guessing blind.
4. **Remembers what you've solved** — a lightweight spaced-repetition
   scheduler (SM-2-lite) resurfaces exercises you solved before, so skills
   don't quietly decay.
5. **Levels you up automatically** — solve 80% of a level's bank and the
   app offers to bump you to the next one.

## Quick start

```bash
uv run app.py
```

Starts a Flask server at **http://localhost:5050** (auto-kills anything
already bound to that port, so re-running just works). Pick a track (Python
or SQL) from the header, pick a level, click an exercise in the sidebar, and
start solving.

### Run the test suites

```bash
uv run test_runner.py       # self-check for the Python grading harness
uv run test_sql_runner.py   # self-check for the SQL grading harness
```

Both are dependency-free self-checks (no pytest) — pass/fail/error/timeout
paths for each harness, run directly with `python`.

## How grading works

### Python track

`runner.py` takes your submitted function body, wraps it in a small harness
with the exercise's test cases embedded as JSON, and runs the whole thing as
a **subprocess** — not `exec()` in-process — with a wall-clock timeout and a
CPU-time `rlimit`. This is deliberately a guard against *accidents* (an
infinite loop, a typo'd destructive call) from code you wrote yourself, not
a hardened sandbox against a malicious adversary; if this app ever needed to
run code from other people, it would need real containerization instead.

Each test case is `{"args": [...], "expected": <value>}` (or
`{"args": [...], "expect_error": "ValueError"}` for exercises that test
exception handling). Return values are normalized (tuples → lists) before
comparison so either is an acceptable return type.

### SQL track

`sql_runner.py` runs your query against an in-memory **SQLite** database
(stdlib `sqlite3`, no extra dependency) that's freshly seeded per test case.
Before your query runs, the connection is switched to `PRAGMA query_only`
so a stray `UPDATE`/`DROP` can't corrupt the seeded tables, and a
`set_progress_handler` deadline aborts runaway queries (a pathological
recursive CTE, a giant unintended cross join) after a few seconds — same
"guard against accidents" philosophy as the Python side.

Each test case is `{"seed_sql": "...", "expected": [[...], ...],
"order_sensitive": bool}`. Rows are compared as an unordered multiset unless
the puzzle explicitly requires a specific order (e.g. "ordered by date"),
in which case `order_sensitive: true` enforces exact row order too.

### Both tracks

- One test case per exercise is picked as the visible "Example" (preferring
  a non-trivial expected value over a boring one like `[]` or `None`) —
  everything else stays hidden until you hit **Run Tests**.
- Every result row — pass or fail — shows the inputs it ran with (function
  args for Python, seed data for SQL) alongside the actual/expected output,
  specifically so a stuck learner can see *why* without it becoming "just
  read the answer."

## Progress & spaced repetition

`data/progress.json` (gitignored — it's your local state, not shipped
content) tracks, per track:

- **Current level** — Python and SQL track their "current level" tab
  independently (`level` and `sql_level` fields), so switching tracks
  doesn't lose your place in either one.
- **Solved exercises** — a flat list of exercise ids (each id is
  self-prefixed with its level, e.g. `sql-advanced-gaps-islands-02`, so no
  extra bookkeeping is needed to know which level an id belongs to).
- **Attempt counts** — how many times you've submitted each exercise.
- **Review schedule** — an SM-2-lite scheduler: first solve → due again in
  1 day; each successful review doubles the interval (capped at 60 days);
  getting a previously-solved exercise *wrong* on a review resets it back
  to 1 day. The sidebar's 📌 badge and per-exercise dot show what's due
  today.
- **Level-up suggestions** — solving ≥80% of a level's bank offers to
  advance you to the next level in that track (Python and SQL advance
  independently; finishing Python "expert" will never suggest jumping into
  the SQL track, or vice versa).

## Content

| Level | Python exercises | SQL exercises |
|---|---|---|
| Novice | 100 | 100 |
| Intermediate | 100 | 100 |
| Advanced | 101 | 100 |
| Expert | 100 | 100 |

Exercises are grouped into topic **clusters** (e.g. Python's "Hash Maps &
Dicts", SQL's "Gaps & Islands") shown as collapsible sections in the
sidebar, each with its own solved-count badge. A live search box filters by
title, topic, or cluster name across the whole level.

All SQL content is original — authored to cover the same skill areas that
Celko's books and LeetCode/HackerRank's SQL sections are known for
(hierarchical queries, window functions, set operations, and so on) without
reproducing their copyrighted problem text.

## Structure

```
app.py                          Flask routes: serve exercises, grade
                                 submissions, persist/track progress
runner.py                       Python grading harness (subprocess sandbox)
sql_runner.py                   SQL grading harness (in-memory SQLite)
test_runner.py                  Self-check for runner.py
test_sql_runner.py              Self-check for sql_runner.py
exercises/
  novice.json                   100 Python exercises
  intermediate.json             100 Python exercises
  advanced.json                 101 Python exercises
  expert.json                   100 Python exercises
  sql-novice.json               100 SQL puzzles
  sql-intermediate.json         100 SQL puzzles
  sql-advanced.json             100 SQL puzzles
  sql-expert.json               100 SQL puzzles
data/
  progress.json                 Your local progress (gitignored)
static/
  index.html                    Page shell — track/level tabs, editor, results
  app.js                        All frontend logic (vanilla JS, no build step)
  style.css                     Styling
```

## Exercise data model

Every exercise is one object in its level's JSON array. Fields common to
both tracks: `id`, `title`, `level`, `cluster`, `topics`, `prompt`, `hint`
(optional), `starter_code`, `tests`.

**Python-specific:** `func_name` (the function your code must define) and
tests shaped `{"args": [...], "expected": ...}` or `{"args": [...],
"expect_error": "SomeException"}`.

**SQL-specific:** `"language": "sql"`, `schema_sql` (the `CREATE TABLE`
statement(s) shared by every test case), and tests shaped `{"seed_sql":
"...", "expected": [[...], ...], "order_sensitive": bool}`.

Reference solutions are never shipped in these files — they're used only
during content authoring/verification, then stripped, so a curious learner
reading the JSON can't just find the answer.

## Extending it

Adding an exercise is just appending an object to the right
`exercises/<level>.json` file in the shape above and making sure its
reference solution actually passes its own tests against the real harness
(`runner.py`'s `run_submission` or `sql_runner.py`'s `run_sql_submission`) —
there's no build step or registration required beyond that.

## Stack

Flask + vanilla JS + CodeMirror (via CDN) on the frontend; Python stdlib
(`subprocess`, `sqlite3`) for grading on the backend. No database server,
no account system, no external API calls at runtime.
