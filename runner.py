"""Runs user-submitted code against an exercise's test cases in a subprocess.

# ponytail: timeout + resource limits guard against accidental damage
# (infinite loops, memory blowups, typo'd destructive calls) from code the
# user wrote themselves — not against a malicious adversary. If this ever
# needs to run untrusted code from other people, containerize the subprocess
# (Docker/firejail) instead.
"""

import json
import resource
import subprocess
import sys
import tempfile
from pathlib import Path

SENTINEL = "###RESULTS###"
TIMEOUT_SECONDS = 5
CPU_SECONDS = 2

HARNESS_TEMPLATE = """
import json

{user_code}

def _normalize(x):
    # Tuples are a natural return type (e.g. index pairs) but JSON has no
    # tuple, so expected values always arrive as lists — normalize actual
    # return values the same way before comparing, recursively.
    if isinstance(x, (tuple, list)):
        return [_normalize(v) for v in x]
    if isinstance(x, dict):
        return {{k: _normalize(v) for k, v in x.items()}}
    return x


_tests = json.loads({tests_json_literal})
_results = []
for _t in _tests:
    if "expect_error" in _t:
        _wanted = _t["expect_error"]
        try:
            {func_name}(*_t["args"])
        except Exception as _e:
            _names = [c.__name__ for c in type(_e).__mro__]
            if _wanted in _names:
                _results.append({{"passed": True, "actual": f"raised {{type(_e).__name__}}", "expected": f"raises {{_wanted}}"}})
            else:
                _results.append({{"passed": False, "error": f"raised {{type(_e).__name__}}: {{_e}} (expected {{_wanted}})", "expected": f"raises {{_wanted}}"}})
        else:
            _results.append({{"passed": False, "error": f"no exception raised (expected {{_wanted}})", "expected": f"raises {{_wanted}}"}})
        continue
    try:
        _actual = _normalize({func_name}(*_t["args"]))
        _results.append({{"passed": _actual == _t["expected"], "actual": _actual, "expected": _t["expected"]}})
    except Exception as _e:
        _results.append({{"passed": False, "error": f"{{type(_e).__name__}}: {{_e}}", "expected": _t["expected"]}})

print("{sentinel}" + json.dumps({{"results": _results}}))
"""


def _limit_resources():
    # ponytail: no memory cap here — macOS refuses to lower RLIMIT_AS below
    # what dyld/malloc already reserve at interpreter startup, so every
    # subprocess launch would fail. CPU limit + the wall-clock timeout in
    # run_submission cover the realistic accident cases (infinite/CPU-bound
    # loops); a deliberate memory bomb isn't caught. Upgrade path: run the
    # subprocess in a cgroup/container if that risk ever matters.
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))


def run_submission(user_code: str, func_name: str, tests: list) -> dict:
    """Executes user_code's func_name against tests. Returns a result dict:
    {"status": "ok", "results": [...]} on a clean run,
    {"status": "timeout"} if it ran too long,
    {"status": "error", "message": ...} on a crash/non-zero exit.
    """
    harness = HARNESS_TEMPLATE.format(
        user_code=user_code,
        # Embed as a Python string literal (not a raw literal) so JSON's
        # true/false/null decode via json.loads instead of being spliced in
        # as invalid Python syntax.
        tests_json_literal=json.dumps(json.dumps(tests)),
        func_name=func_name,
        sentinel=SENTINEL,
    )

    with tempfile.TemporaryDirectory() as scratch_dir:
        script_path = Path(scratch_dir) / "submission.py"
        script_path.write_text(harness)

        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                cwd=scratch_dir,
                env={"PATH": "/usr/bin:/bin"},
                preexec_fn=_limit_resources,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}

        if proc.returncode < 0:
            # Killed by a signal — e.g. SIGXCPU from the CPU rlimit, which
            # fires before subprocess's own wall-clock timeout on tight
            # infinite loops. Same class of failure from the user's view.
            return {"status": "timeout"}

        if proc.returncode != 0:
            return {"status": "error", "message": proc.stderr.strip()[-2000:]}

        for line in proc.stdout.splitlines():
            if line.startswith(SENTINEL):
                payload = json.loads(line[len(SENTINEL) :])
                return {"status": "ok", "results": payload["results"]}

        return {
            "status": "error",
            "message": "No result produced.\n" + proc.stderr[-2000:],
        }
