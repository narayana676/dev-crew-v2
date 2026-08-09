"""LangServe-compatible Runnable wrapping the real Dev Crew LangGraph workflow."""

from typing import List, Optional

from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from app.core.state import AgentState, AgentStatus
from app.graph.workflow import build_dev_crew_graph
from app.logger import logger


class CrewInput(BaseModel):
    """Public input contract for the /crew LangServe endpoint."""

    task: str = Field(..., description="The coding task description")
    max_retries: int = Field(3, description="Max Debugger->Coder retry attempts")


class CodeFileOut(BaseModel):
    path: str
    content: str
    language: str = "python"


class CrewOutput(BaseModel):
    """Public output contract for the /crew LangServe endpoint."""

    status: str = Field(..., description="Final graph status: DONE or FAILED_MAX_RETRIES")
    files: List[CodeFileOut] = Field(default_factory=list)
    tests_passed: bool = False
    review: Optional[str] = None
    retry_count: int = 0
    error: Optional[str] = None


_compiled_graph = build_dev_crew_graph()


def run_dev_crew(input_data: CrewInput) -> CrewOutput:
    """Invoke the compiled Dev Crew graph and adapt AgentState to the public output contract."""
    task = input_data.task if isinstance(input_data, CrewInput) else input_data.get("task", "")
    max_retries = (
        input_data.max_retries if isinstance(input_data, CrewInput) else input_data.get("max_retries", 3)
    )

    logger.info(f"[/crew] invoking dev crew graph for task: {task!r}")
    initial_state = AgentState(task_description=task, max_retries=max_retries)

    try:
        final_state_dict = _compiled_graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"[/crew] graph execution failed: {e}", exc_info=True)
        return CrewOutput(status="ERROR", error=str(e))

    final_state = AgentState.model_validate(final_state_dict)

    review_text = None
    if final_state.review_notes:
        last_review = final_state.review_notes[-1]
        review_text = "; ".join(last_review.comments) if last_review.comments else (
            "passed" if last_review.passed else "failed"
        )

    return CrewOutput(
        status=final_state.status.value if isinstance(final_state.status, AgentStatus) else str(final_state.status),
        files=[
            CodeFileOut(path=f.path, content=f.content, language=f.language)
            for f in final_state.code_files.values()
        ],
        tests_passed=final_state.tests_passed,
        review=review_text,
        retry_count=final_state.retry_count,
    )


crew_runnable = RunnableLambda(run_dev_crew).with_types(
    input_type=CrewInput,
    output_type=CrewOutput,
)
