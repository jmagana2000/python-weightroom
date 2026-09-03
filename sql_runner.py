"""Runs a user-submitted SQL query against an exercise's test cases in-process.

# ponytail: PRAGMA query_only plus the progress-handler deadline guard against
# accidental damage (a stray UPDATE, a runaway recursive CTE) from a query the
# user wrote themselves -- not against a malicious adversary. If this ever
# needs to run untrusted queries from other people, sandbox the process
# (separate subprocess/container) instead.
"""

import json
import sqlite3
import time

TIMEOUT_SECONDS = 3
PROGRESS_STEPS = 1000


def _normalize_rows(rows) -> list:
    return [list(r) for r in rows]


def _canonical(rows: list) -> list:
    # Multiset compare for order-insensitive tests: sort both sides by their
    # JSON string form so equality doesn't care about row order, and so
    # mixed None/int/str values never hit Python's "unorderable types".
    return sorted(json.dumps(row, default=str) for row in rows)


def run_sql_submission(user_query: str, schema_sql: str, tests: list) -> dict:
    """Executes user_query against each test's seeded database. Returns:
    {"status": "ok", "results": [...]} with a per-test pass/fail,
    {"status": "timeout"} if a query ran too long,
    {"status": "error", "message": ...} if an exercise's own schema/seed is broken.
    """
    results = []
    for test in tests:
        conn = sqlite3.connect(":memory:")
        try:
            try:
                conn.executescript(schema_sql + "\n" + test["seed_sql"])
            except Exception as e:
                return {"status": "error", "message": f"{type(e).__name__}: {e}"}

            deadline = time.monotonic() + TIMEOUT_SECONDS
            conn.set_progress_handler(
                lambda: 1 if time.monotonic() > deadline else 0, PROGRESS_STEPS
            )
            conn.execute("PRAGMA query_only = ON")

            try:
                cursor = conn.execute(user_query)
                actual = _normalize_rows(cursor.fetchall())
            except Exception as e:
                if isinstance(e, sqlite3.OperationalError) and "interrupted" in str(e):
                    return {"status": "timeout"}
                results.append(
                    {
                        "passed": False,
                        "error": f"{type(e).__name__}: {e}",
                        "expected": test["expected"],
                        "seed_sql": test["seed_sql"],
                    }
                )
                continue

            expected = test["expected"]
            if test.get("order_sensitive"):
                passed = actual == expected
            else:
                passed = _canonical(actual) == _canonical(expected)

            results.append(
                {
                    "passed": passed,
                    "actual": actual,
                    "expected": expected,
                    "seed_sql": test["seed_sql"],
                }
            )
        finally:
            conn.close()

    return {"status": "ok", "results": results}
