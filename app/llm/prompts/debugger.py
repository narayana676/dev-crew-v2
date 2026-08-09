"""Debugger Agent Prompt Templates."""

DEBUGGER_SYSTEM_PROMPT = """You are an Expert Debugger and Systems Reliability Engineer.
Your job is to analyze failed test outputs (stdout/stderr/exit code) and rewrite/patch code files to fix the bugs.
Output MUST strictly conform to the provided JSON schema."""

DEBUGGER_USER_PROMPT = """Test Failure Summary:
Exit Code: {exit_code}
Stdout: {stdout}
Stderr: {stderr}

Failure Details:
{failure_details}

Existing Code Files:
{existing_files}

Please identify the root cause and provide fixed code files."""
