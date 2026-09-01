"""Self-check for runner.py: pass, fail, error, and timeout paths."""

from runner import run_submission

TESTS = [{"args": [[1, 2, 3]], "expected": 6}, {"args": [[]], "expected": 0}]


def test_correct_solution_passes():
    result = run_submission(
        "def sum_list(nums):\n    return sum(nums)\n", "sum_list", TESTS
    )
    assert result["status"] == "ok", result
    assert all(r["passed"] for r in result["results"]), result


def test_wrong_solution_fails():
    result = run_submission("def sum_list(nums):\n    return 0\n", "sum_list", TESTS)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False
    assert result["results"][1]["passed"] is True


def test_crashing_solution_reports_error():
    result = run_submission(
        "def sum_list(nums):\n    return 1 / 0\n", "sum_list", TESTS
    )
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False
    assert "ZeroDivisionError" in result["results"][0]["error"]


def test_bool_and_null_test_literals_are_valid_python():
    tests = [{"args": [4], "expected": True}, {"args": [7], "expected": False}]
    result = run_submission(
        "def is_even(n):\n    return n % 2 == 0\n", "is_even", tests
    )
    assert result["status"] == "ok", result
    assert all(r["passed"] for r in result["results"]), result


def test_expect_error_matches_exact_type():
    tests = [{"args": [-1], "expect_error": "ValueError"}]
    result = run_submission(
        "def check(n):\n    if n < 0:\n        raise ValueError('bad')\n",
        "check",
        tests,
    )
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is True, result


def test_expect_error_matches_subclass():
    tests = [{"args": [-1], "expect_error": "Exception"}]
    result = run_submission(
        "class MyError(Exception):\n    pass\n\n\ndef check(n):\n    raise MyError('bad')\n",
        "check",
        tests,
    )
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is True, result


def test_expect_error_fails_on_wrong_type():
    tests = [{"args": [-1], "expect_error": "ValueError"}]
    result = run_submission(
        "def check(n):\n    raise TypeError('bad')\n", "check", tests
    )
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False, result


def test_expect_error_fails_when_no_exception_raised():
    tests = [{"args": [-1], "expect_error": "ValueError"}]
    result = run_submission("def check(n):\n    return n\n", "check", tests)
    assert result["status"] == "ok", result
    assert result["results"][0]["passed"] is False, result


def test_infinite_loop_times_out():
    result = run_submission(
        "def sum_list(nums):\n    while True:\n        pass\n", "sum_list", TESTS
    )
    assert result["status"] == "timeout", result


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("All checks passed.")
