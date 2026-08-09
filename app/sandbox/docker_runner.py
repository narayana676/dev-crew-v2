"""Optional Docker-based sandboxed code runner, kept for local experimentation only.

NOT used in the normal Dev Crew runtime path — the Tester node uses
app.sandbox.pytest_runner (plain subprocess, no Docker daemon required).
Docker is imported lazily so its absence never breaks app startup, unit tests,
or deployment.
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
    """Write generated code files to disk workspace directory."""
    os.makedirs(base_dir, exist_ok=True)
    for path, code_file in code_files.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code_file.content)
    return base_dir


def parse_pytest_output(stdout: str, stderr: str, exit_code: int, duration: float) -> TestResult:
    """Parse pytest stdout/stderr and exit code into structured TestResult."""
    passed_count = 0
    failed_count = 0
    error_count = 0

    # Parse passed/failed counts from pytest summary line (e.g. "2 passed, 1 failed in 0.05s")
    passed_match = re.search(r"(\d+)\s+passed", stdout)
    failed_match = re.search(r"(\d+)\s+failed", stdout)
    error_match = re.search(r"(\d+)\s+error", stdout)

    if passed_match:
        passed_count = int(passed_match.group(1))
    if failed_match:
        failed_count = int(failed_match.group(1))
    if error_match:
        error_count = int(error_match.group(1))

    # Determine overall status
    if exit_code == 0 and failed_count == 0 and error_count == 0:
        status = TestStatus.PASSED
    elif exit_code in (1, 2) or failed_count > 0:
        status = TestStatus.FAILED
    else:
        status = TestStatus.ERROR

    failure_details = []
    if status != TestStatus.PASSED:
        # Extract FAILURE block snippets
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


def run_sandboxed_pytest(code_files: Dict[str, CodeFile]) -> TestResult:
    """Execute pytest inside a locked-down Docker container. Requires a running Docker daemon.

    Optional local-experimentation path only; the Tester node does not call this.
    Falls back to the plain subprocess runner if the `docker` package is missing
    or the daemon is unreachable.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        prepare_workspace(code_files, temp_dir)
        start_time = time.time()

        try:
            import docker
            from docker.errors import DockerException

            client = docker.from_env()
            # Test docker connection
            client.ping()

            # Normalize path for Windows Docker host mount
            host_workspace = os.path.abspath(temp_dir)
            container = client.containers.run(
                image=settings.SANDBOX_DOCKER_IMAGE,
                command="pytest -v /workspace",
                volumes={host_workspace: {"bind": "/workspace", "mode": "rw"}},
                network_mode="none",
                mem_limit=settings.SANDBOX_MEMORY_LIMIT,
                cpu_quota=settings.SANDBOX_CPU_QUOTA,
                read_only=True,
                tmpfs={"/tmp": "rw,size=100m"},
                detach=False,
                stdout=True,
                stderr=True,
            )
            stdout = container.decode("utf-8") if isinstance(container, bytes) else str(container)
            stderr = ""
            exit_code = 0
            duration = time.time() - start_time
            return parse_pytest_output(stdout, stderr, exit_code, duration)

        except Exception as e:
            # Fallback to local isolated python subprocess if Docker daemon is not running
            try:
                cmd = [sys.executable, "-m", "pytest", "-v", temp_dir]
                proc = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=settings.SANDBOX_TIMEOUT_SECONDS,
                )
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                stdout = ""
                stderr = f"Execution timed out after {settings.SANDBOX_TIMEOUT_SECONDS}s"
                exit_code = 124

            duration = time.time() - start_time
            return parse_pytest_output(stdout, stderr, exit_code, duration)
