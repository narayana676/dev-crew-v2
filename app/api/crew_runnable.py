"""LangServe-compatible Runnable wrapping the real Dev Crew LangGraph workflow."""

from typing import List, Optional

from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from app.core.state import AgentState, AgentStatus
from app.graph.workflow import build_dev_crew_graph
from app.logger import logger


class CrewInput(BaseModel):
    """Public input contract for the /crew LangServe endpoint."""

    task: str = Field(
        ...,
        description="The coding task description",
    )

    max_retries: int = Field(
        3,
        description="Maximum Debugger -> Coder retry attempts",
    )


class CrewOutput(BaseModel):
    """Clean public output contract for the /crew LangServe endpoint."""

    status: str = Field(
        ...,
        description="Final graph status",
    )

    task: str = Field(
        ...,
        description="The task processed by Dev Crew",
    )

    files_created: List[str] = Field(
        default_factory=list,
        description="Names of generated files",
    )

    tests_passed: bool = Field(
        False,
        description="Whether generated code passed tests",
    )

    test_status: str = Field(
        "",
        description="Human-readable test status",
    )

    review_status: str = Field(
        "",
        description="Human-readable code review status",
    )

    review: Optional[str] = Field(
        None,
        description="Code review comments",
    )

    retry_count: int = Field(
        0,
        description="Number of debugging retries",
    )

    summary: str = Field(
        "",
        description="Human-readable final summary",
    )

    error: Optional[str] = Field(
        None,
        description="Error message if execution failed",
    )


_compiled_graph = build_dev_crew_graph()


def run_dev_crew(input_data: CrewInput) -> CrewOutput:
    """Run the Dev Crew graph and return a clean public response."""

    task = (
        input_data.task
        if isinstance(input_data, CrewInput)
        else input_data.get("task", "")
    )

    max_retries = (
        input_data.max_retries
        if isinstance(input_data, CrewInput)
        else input_data.get("max_retries", 3)
    )

    logger.info(
        f"[/crew] invoking dev crew graph for task: {task!r}"
    )

    initial_state = AgentState(
        task_description=task,
        max_retries=max_retries,
    )

    try:
        final_state_dict = _compiled_graph.invoke(initial_state)

    except Exception as e:
        logger.error(
            f"[/crew] graph execution failed: {e}",
            exc_info=True,
        )

        return CrewOutput(
            status="ERROR",
            task=task,
            files_created=[],
            tests_passed=False,
            test_status="FAILED",
            review_status="NOT AVAILABLE",
            review=None,
            retry_count=0,
            summary="Dev Crew failed while processing the task.",
            error=str(e),
        )

    final_state = AgentState.model_validate(final_state_dict)

    # Get final status
    status = (
        final_state.status.value
        if isinstance(final_state.status, AgentStatus)
        else str(final_state.status)
    )

    # Get generated file names only.
    # We intentionally do NOT return the complete source code here.
    files_created = [
        code_file.path
        for code_file in final_state.code_files.values()
    ]

    # Test result
    if final_state.tests_passed:
        test_status = "PASSED"
    else:
        test_status = "FAILED"

    # Review result
    review_text = None
    review_status = "NOT AVAILABLE"

    if final_state.review_notes:
        last_review = final_state.review_notes[-1]

        if last_review.passed:
            review_status = "APPROVED"
        else:
            review_status = "NEEDS IMPROVEMENT"

        if last_review.comments:
            review_text = "; ".join(last_review.comments)
        else:
            review_text = (
                "Code review passed."
                if last_review.passed
                else "Code review found issues."
            )

    # Final summary
    if status == "DONE":
        summary = (
            f"Task completed successfully. "
            f"{len(files_created)} file(s) were generated, "
            f"reviewed, and tested."
        )

    elif status == "FAILED_MAX_RETRIES":
        summary = (
            f"Task could not be completed after "
            f"{final_state.retry_count} retry attempt(s)."
        )

    else:
        summary = (
            f"Dev Crew finished with status: {status}."
        )

    return CrewOutput(
        status=status,
        task=task,
        files_created=files_created,
        tests_passed=final_state.tests_passed,
        test_status=test_status,
        review_status=review_status,
        review=review_text,
        retry_count=final_state.retry_count,
        summary=summary,
        error=None,
    )


crew_runnable = RunnableLambda(
    run_dev_crew
).with_types(
    input_type=CrewInput,
    output_type=CrewOutput,
)
