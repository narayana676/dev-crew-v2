"""Integration tests for the subprocess-based pytest tester (no Docker required)."""

import os

from app.core.state import CodeFile, TestStatus
from app.sandbox.pytest_runner import parse_pytest_output, run_pytest_subprocess


def test_parse_pytest_output_success():
    """Verify parsing successful pytest output."""
    stdout = "test_main.py ..                                      [100%]\n2 passed in 0.05s"
    result = parse_pytest_output(stdout, "", 0, 0.05)
    assert result.status == TestStatus.PASSED
    assert result.passed_count == 2
    assert result.failed_count == 0
    assert result.exit_code == 0


def test_parse_pytest_output_failure():
    """Verify parsing failing pytest output."""
    stdout = """
    ___ test_add ___
    assert 1 + 1 == 3
    1 passed, 1 failed in 0.12s
    """
    result = parse_pytest_output(stdout, "", 1, 0.12)
    assert result.status == TestStatus.FAILED
    assert result.passed_count == 1
    assert result.failed_count == 1
    assert result.exit_code == 1


def test_subprocess_pytest_execution_passing_code():
    """Run subprocess pytest on passing python code files -> real PASS from actual exit code."""
    code_files = {
        "calculator.py": CodeFile(
            path="calculator.py",
            content="def multiply(x, y):\n    return x * y\n",
            language="python",
        ),
        "test_calculator.py": CodeFile(
            path="test_calculator.py",
            content="from calculator import multiply\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n",
            language="python",
        ),
    }

    result = run_pytest_subprocess(code_files)
    assert result.status == TestStatus.PASSED
    assert result.passed_count >= 1
    assert result.failed_count == 0
    assert result.exit_code == 0
    assert "passed" in result.stdout


def test_subprocess_pytest_execution_failing_code():
    """Run subprocess pytest on failing python code files -> real FAIL from actual exit code."""
    code_files = {
        "calculator.py": CodeFile(
            path="calculator.py",
            content="def multiply(x, y):\n    return x + y  # Bug\n",
            language="python",
        ),
        "test_calculator.py": CodeFile(
            path="test_calculator.py",
            content="from calculator import multiply\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n",
            language="python",
        ),
    }

    result = run_pytest_subprocess(code_files)
    assert result.status == TestStatus.FAILED
    assert result.failed_count >= 1
    assert result.exit_code != 0
    assert len(result.failure_details) > 0


def test_subprocess_pytest_timeout_is_enforced():
    """A deliberately long-running test must be killed and return a structured ERROR, not hang."""
    code_files = {
        "test_slow.py": CodeFile(
            path="test_slow.py",
            content="import time\n\ndef test_slow():\n    time.sleep(30)\n    assert True\n",
            language="python",
        ),
    }

    result = run_pytest_subprocess(code_files, timeout_seconds=1.0)
    assert result.status == TestStatus.ERROR
    assert result.exit_code == 124
    assert "timed out" in result.stderr.lower()


def test_workspace_is_temporary_and_cleaned_up():
    """Generated files must live in a temp dir that is removed after the run."""
    from app.sandbox.pytest_runner import prepare_workspace
    import tempfile

    code_files = {
        "sample.py": CodeFile(path="sample.py", content="x = 1\n", language="python"),
    }

    with tempfile.TemporaryDirectory() as tmp:
        prepare_workspace(code_files, tmp)
        assert os.path.exists(os.path.join(tmp, "sample.py"))

    # Directory removed once the context manager exits (workspace does not persist)
    assert not os.path.exists(tmp)
