"""FastAPI endpoints for inspecting run states and retrieving generated artifacts."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.run_manager import run_manager


router = APIRouter(prefix="/runs", tags=["runs"])


class RunStatusResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    task_description: str
    retry_count: int
    max_retries: int
    tests_passed: bool
    plan_approved: bool
    usage: Dict[str, Any]
    file_tree: list[str]
    test_results_count: int


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str):
    """Retrieve detailed state snapshot of execution run by run_id."""
    state = run_manager.get_run(run_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found.")

    return RunStatusResponse(
        run_id=state.run_id,
        project_id=state.project_id,
        status=state.status.value,
        task_description=state.task_description,
        retry_count=state.retry_count,
        max_retries=state.max_retries,
        tests_passed=state.tests_passed,
        plan_approved=state.plan_approved,
        usage=state.usage.model_dump(),
        file_tree=state.file_tree,
        test_results_count=len(state.test_results),
    )


@router.get("/{run_id}/artifacts")
async def get_run_artifacts(run_id: str) -> Dict[str, Any]:
    """Retrieve all generated code files and artifacts for run."""
    state = run_manager.get_run(run_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found.")

    artifacts = {}
    for path, code_file in state.code_files.items():
        artifacts[path] = code_file.model_dump()

    return {
        "run_id": run_id,
        "count": len(artifacts),
        "artifacts": artifacts,
    }
