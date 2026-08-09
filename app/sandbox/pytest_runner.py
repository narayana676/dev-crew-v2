"""Subprocess-based pytest execution: no Docker daemon required for normal operation.

Generated code is written to a fresh temporary directory per run and executed via
`sys.executable -m pytest` with a strict timeout. Success/failure is determined solely
from the subprocess exit code and output, never from an LLM response.
"""

import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Dict

from app.config import settings
from app.core.state import CodeFile, TestResult, TestStatus


def prepare_workspace(code_files: Dict[str, CodeFile], base_dir: str) -> str:
    """Write generated code files into an isolated workspace directory."""
    os.makedirs(base_dir, exist_ok=True)
    for path, code_file in code_files.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path) or base_dir, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code_file.content)
    return base_dir


def parse_pytest_output(stdout: str, stderr: str, exit_code: int, duration: float) -> TestResult:
    """Parse pytest stdout/stderr and exit code into a structured TestResult."""
    passed_count = 0
    failed_count = 0
    error_count = 0

    passed_match = re.search(r"(\d+)\s+passed", stdout)
    failed_match = re.search(r"(\d+)\s+failed", stdout)
    error_match = re.search(r"(\d+)\s+error", stdout)

    if passed_match:
        passed_count = int(passed_match.group(1))
    if failed_match:
        failed_count = int(failed_match.group(1))
    if error_match:
        error_count = int(error_match.group(1))

    if exit_code == 0 and failed_count == 0 and error_count == 0:
        status = TestStatus.PASSED
    elif exit_code in (1, 2) or failed_count > 0:
        status = TestStatus.FAILED
    else:
        status = TestStatus.ERROR

    failure_details = []
    if status != TestStatus.PASSED:
        failures = re.findall(r"_{3,}\s*(.*?)\s*_{3,}(.*?)(?=\n_{3,}|\n={3,}|$)", stdout, re.DOTALL)
        for name, body in failures:
            failure_details.append(f"{name.strip()}: {body.strip()[:300]}")
        if not failure_details and stderr.strip():
            failure_details.append(stderr.strip()[:500])

    return TestResult(
        status=status,
        passed_count=passed_count,
        failed_count=failed_count,
        error_count=error_count,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_seconds=round(duration, 3),
        failure_details=failure_details,
    )


def run_pytest_subprocess(code_files: Dict[str, CodeFile], timeout_seconds: float = None) -> TestResult:
    """Write code_files to a fresh temp workspace and run pytest as a controlled subprocess.

    Determines PASS/FAIL strictly from the subprocess exit code and pytest output.
    Enforces a hard timeout; on expiry the process is killed and a structured
    ERROR result is returned rather than hanging the caller.
    """
    timeout = timeout_seconds if timeout_seconds is not None else settings.SANDBOX_TIMEOUT_SECONDS

    with tempfile.TemporaryDirectory(prefix="devcrew_test_") as temp_dir:
        prepare_workspace(code_files, temp_dir)
        start_time = time.time()

        cmd = [sys.executable, "-m", "pytest", "-v", temp_dir]
        try:
            proc = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as e:
            stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
            stderr = f"Execution timed out after {timeout}s and was terminated."
            duration = time.time() - start_time
            return TestResult(
                status=TestStatus.ERROR,
                passed_count=0,
                failed_count=0,
                error_count=1,
                stdout=stdout,
                stderr=stderr,
                exit_code=124,
                duration_seconds=round(duration, 3),
                failure_details=[stderr],
            )

        duration = time.time() - start_time
        return parse_pytest_output(stdout, stderr, exit_code, duration)
