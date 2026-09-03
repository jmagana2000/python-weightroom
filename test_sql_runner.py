"""Self-check for sql_runner.py: pass, fail, error, order, and timeout paths."""

from sql_runner import run_sql_submission

SCHEMA = "CREATE TABLE nums (n INTEGER);"
TESTS = [
    {"seed_sql": "INSERT INTO nums VALUES (3),(1),(2);", "expected": [[1], [2], [3]]}
]


def test_correct_solution_passes():
    result = run_sql_submission("SELECT n FROM nums ORDER BY n;", SCHEMA, TESTS)
    assert result["status"] == "ok", result
    assert all(r["passed"] for r in result["results"]), result


def test_wrong_solution_fails():
    result = run_sql_submission("SELECT n FROM nums WHERE n > 100;", SCHEMA, TESTS)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False
    assert result["results"][0]["actual"] == []


def test_order_insensitive_by_default():
    # Same rows, different order than "expected" -- should still pass since
    # these tests don't set order_sensitive.
    result = run_sql_submission("SELECT n FROM nums;", SCHEMA, TESTS)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is True, result


def test_order_sensitive_catches_wrong_order():
    tests = [
        {
            "seed_sql": TESTS[0]["seed_sql"],
            "expected": [[1], [2], [3]],
            "order_sensitive": True,
        }
    ]
    result = run_sql_submission("SELECT n FROM nums;", SCHEMA, tests)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False, result


def test_invalid_sql_reports_per_test_error():
    result = run_sql_submission("SELEKT n FROM nums;", SCHEMA, TESTS)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False
    assert "error" in result["results"][0]


def test_write_attempt_is_blocked_not_crashed():
    result = run_sql_submission("DELETE FROM nums;", SCHEMA, TESTS)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False
    assert "error" in result["results"][0]


def test_broken_exercise_schema_reports_error_status():
    result = run_sql_submission("SELECT 1;", "NOT VALID SQL;", TESTS)
    assert result["status"] == "error", result


def test_infinite_recursive_cte_times_out():
    query = (
        "WITH RECURSIVE cnt(x) AS "
        "(SELECT 1 UNION ALL SELECT x + 1 FROM cnt) "
        "SELECT x FROM cnt;"
    )
    result = run_sql_submission(query, SCHEMA, TESTS)
    assert result["status"] == "timeout", result


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("All checks passed.")
