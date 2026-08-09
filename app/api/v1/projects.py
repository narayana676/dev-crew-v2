"""FastAPI endpoints for managing Projects and triggering Runs."""

from typing import Dict, Optional
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel
from app.api.deps import verify_api_key
from app.services.run_manager import run_manager


router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(verify_api_key)])


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str


class CreateRunRequest(BaseModel):
    task_description: str


class RunCreatedResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    task_description: str


# In-memory storage for projects and idempotency keys
PROJECTS_DB: Dict[str, dict] = {}
IDEMPOTENCY_CACHE: Dict[str, RunCreatedResponse] = {}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(req: CreateProjectRequest):
    """Create a new project workspace."""
    project_id = str(uuid4())
    project_data = {
        "id": project_id,
        "name": req.name,
        "description": req.description or "",
    }
    PROJECTS_DB[project_id] = project_data
    return project_data


@router.post("/{project_id}/runs", response_model=RunCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    project_id: str,
    req: CreateRunRequest,
    background_tasks: BackgroundTasks,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
):
    """Trigger a new asynchronous execution run for a project with idempotency support."""
    if x_idempotency_key and x_idempotency_key in IDEMPOTENCY_CACHE:
        # Return cached response for duplicate request
        return IDEMPOTENCY_CACHE[x_idempotency_key]

    if project_id not in PROJECTS_DB and project_id != "default":
        PROJECTS_DB[project_id] = {"id": project_id, "name": "Default Project", "description": ""}

    # Create run state
    state = run_manager.create_run(project_id=project_id, task_description=req.task_description)

    # Launch background graph execution
    background_tasks.add_task(run_manager.execute_run_async, state.run_id)

    response = RunCreatedResponse(
        run_id=state.run_id,
        project_id=project_id,
        status=state.status.value,
        task_description=state.task_description,
    )

    if x_idempotency_key:
        IDEMPOTENCY_CACHE[x_idempotency_key] = response

    return response
