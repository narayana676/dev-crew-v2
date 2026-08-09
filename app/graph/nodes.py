"""Node handlers for the LangGraph multi-agent graph with real LLM integration."""

from app.core.state import (
    AgentState,
    AgentStatus,
    ArchitectureOutput,
    CodeFile,
    PlanOutput,
    ReviewOutput,
    TestResult,
    TestStatus,
)
from app.llm.base import CoderOutput, DebugOutput, get_llm_provider
from app.llm.prompts.architect import ARCHITECT_SYSTEM_PROMPT, ARCHITECT_USER_PROMPT
from app.llm.prompts.coder import CODER_SYSTEM_PROMPT, CODER_USER_PROMPT
from app.llm.prompts.debugger import DEBUGGER_SYSTEM_PROMPT, DEBUGGER_USER_PROMPT
from app.llm.prompts.planner import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from app.llm.prompts.reviewer import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT


def planner_node(state: AgentState) -> dict:
    """Planner node: generates structured plan via LLM interface."""
    provider = get_llm_provider()
    prompt = PLANNER_USER_PROMPT.format(task_description=state.task_description)
    
    plan, usage = provider.generate_structured(
        prompt=prompt, system_prompt=PLANNER_SYSTEM_PROMPT, response_model=PlanOutput
    )
    
    state.usage.add_usage(usage.prompt_tokens, usage.completion_tokens)
    return {"plan": plan, "status": AgentStatus.ARCHITECTING, "usage": state.usage}


def architect_node(state: AgentState) -> dict:
    """Architect node: produces component specifications via LLM interface."""
    provider = get_llm_provider()
    plan_summary = state.plan.summary if state.plan else "N/A"
    arch_overview = state.plan.architecture_overview if state.plan else "N/A"
    tasks = str([t.model_dump() for t in state.plan.tasks]) if state.plan else "[]"
    
    prompt = ARCHITECT_USER_PROMPT.format(
        plan_summary=plan_summary,
        architecture_overview=arch_overview,
        tasks=tasks,
    )
    
    arch, usage = provider.generate_structured(
        prompt=prompt, system_prompt=ARCHITECT_SYSTEM_PROMPT, response_model=ArchitectureOutput
    )
    
    state.usage.add_usage(usage.prompt_tokens, usage.completion_tokens)
    return {
        "architecture": arch,
        "file_tree": arch.file_structure,
        "status": AgentStatus.AWAITING_APPROVAL,
        "usage": state.usage,
    }


def approval_stub_node(state: AgentState) -> dict:
    """Human approval stub node: auto-approves plan and sets status to CODING."""
    return {"plan_approved": True, "status": AgentStatus.CODING}


def coder_node(state: AgentState) -> dict:
    """Coder node: generates runnable code and tests via LLM interface."""
    provider = get_llm_provider()
    components = str(state.architecture.components) if state.architecture else "[]"
    file_structure = str(state.architecture.file_structure) if state.architecture else "[]"
    existing_files = str({path: file.content for path, file in state.code_files.items()})
    
    prompt = CODER_USER_PROMPT.format(
        task_description=state.task_description,
        components=components,
        file_structure=file_structure,
        existing_files=existing_files,
    )
    
    coder_out, usage = provider.generate_structured(
        prompt=prompt, system_prompt=CODER_SYSTEM_PROMPT, response_model=CoderOutput
    )
    
    code_files = dict(state.code_files)
    for code_file in coder_out.code_files:
        code_files[code_file.path] = code_file
        
    state.usage.add_usage(usage.prompt_tokens, usage.completion_tokens)
    first_file = coder_out.code_files[0].path if coder_out.code_files else None
    return {
        "code_files": code_files,
        "current_file": first_file,
        "status": AgentStatus.REVIEWING,
        "usage": state.usage,
    }


def reviewer_node(state: AgentState) -> dict:
    """Reviewer node: checks Coder output against architectural spec and plan via LLM interface."""
    provider = get_llm_provider()
    components = str(state.architecture.components) if state.architecture else "[]"
    code_files_str = str({path: file.content for path, file in state.code_files.items()})

    prompt = REVIEWER_USER_PROMPT.format(
        task_description=state.task_description,
        components=components,
        code_files=code_files_str,
    )

    review, usage = provider.generate_structured(
        prompt=prompt, system_prompt=REVIEWER_SYSTEM_PROMPT, response_model=ReviewOutput
    )

    review_notes = list(state.review_notes) + [review]
    state.usage.add_usage(usage.prompt_tokens, usage.completion_tokens)

    return {
        "review_notes": review_notes,
        "status": AgentStatus.TESTING,
        "usage": state.usage,
    }


def tester_node(state: AgentState) -> dict:
    """Tester node: executes generated code and pytest in sandboxed container."""
    from app.sandbox.pytest_runner import run_pytest_subprocess

    # If mock_force_fail is explicitly set on state for unit test isolation, honor it
    if getattr(state, "mock_force_fail", False) is True:
        test_result = TestResult(
            status=TestStatus.FAILED,
            passed_count=0,
            failed_count=1,
            stdout="1 failed",
            exit_code=1,
        )
        passed = False
    else:
        test_result = run_pytest_subprocess(state.code_files)
        passed = test_result.status == TestStatus.PASSED

    test_results = list(state.test_results) + [test_result]
    return {"test_results": test_results, "tests_passed": passed, "status": AgentStatus.TESTING}


def debugger_node(state: AgentState) -> dict:
    """Debugger node: analyzes test failure outputs and patches code files via LLM interface."""
    provider = get_llm_provider()
    latest_test = state.test_results[-1] if state.test_results else None

    exit_code = latest_test.exit_code if latest_test else 1
    stdout = latest_test.stdout if latest_test else ""
    stderr = latest_test.stderr if latest_test else ""
    failure_details = str(latest_test.failure_details) if latest_test else "[]"
    existing_files = str({path: file.content for path, file in state.code_files.items()})

    prompt = DEBUGGER_USER_PROMPT.format(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        failure_details=failure_details,
        existing_files=existing_files,
    )

    debug_out, usage = provider.generate_structured(
        prompt=prompt, system_prompt=DEBUGGER_SYSTEM_PROMPT, response_model=DebugOutput
    )

    code_files = dict(state.code_files)
    for code_file in debug_out.code_files:
        code_files[code_file.path] = code_file

    new_retry_count = state.retry_count + 1
    state.usage.add_usage(usage.prompt_tokens, usage.completion_tokens)

    return {
        "code_files": code_files,
        "retry_count": new_retry_count,
        "status": AgentStatus.DEBUGGING,
        "usage": state.usage,
    }


def done_node(state: AgentState) -> dict:
    """Terminal node when graph succeeds."""
    return {"status": AgentStatus.DONE}


def failed_max_retries_node(state: AgentState) -> dict:
    """Terminal node when retry ceiling is exceeded."""
    return {"status": AgentStatus.FAILED_MAX_RETRIES}
