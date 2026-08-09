"""State schema definitions for the Dev Crew multi-agent graph."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Execution status of the multi-agent graph."""
    PLANNING = "PLANNING"
    ARCHITECTING = "ARCHITECTING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    CODING = "CODING"
    REVIEWING = "REVIEWING"
    TESTING = "TESTING"
    DEBUGGING = "DEBUGGING"
    DONE = "DONE"
    FAILED_MAX_RETRIES = "FAILED_MAX_RETRIES"


class TestStatus(str, Enum):
    """Result status of test execution."""
    __test__ = False
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class UsageMetrics(BaseModel):
    """Token and cost tracking metrics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def add_usage(self, prompt: int, completion: int, cost_per_1k_prompt: float = 0.0015, cost_per_1k_comp: float = 0.002) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        added_cost = (prompt / 1000.0 * cost_per_1k_prompt) + (completion / 1000.0 * cost_per_1k_comp)
        self.total_cost_usd += round(added_cost, 6)


class CodeFile(BaseModel):
    """Represents a generated or modified file."""
    path: str
    content: str
    language: str = "python"
    description: Optional[str] = None


class PlanTask(BaseModel):
    """Individual sub-task within an execution plan."""
    id: str
    title: str
    description: str
    status: str = "pending"
    target_files: List[str] = Field(default_factory=list)


class PlanOutput(BaseModel):
    """Structured plan produced by the Planner node."""
    summary: str
    architecture_overview: str
    tasks: List[PlanTask] = Field(default_factory=list)


class ArchitectureOutput(BaseModel):
    """Structured architecture spec produced by Architect node."""
    components: List[str] = Field(default_factory=list)
    interfaces: List[str] = Field(default_factory=list)
    file_structure: List[str] = Field(default_factory=list)
    design_notes: str = ""


class ReviewOutput(BaseModel):
    """Structured feedback produced by the Reviewer node."""
    passed: bool
    score: float = 1.0
    comments: List[str] = Field(default_factory=list)
    requested_changes: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Structured test result from Docker sandbox execution."""
    __test__ = False
    status: TestStatus
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_seconds: float = 0.0
    failure_details: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Strict Pydantic v2 state schema for LangGraph agent workflow."""

    task_description: str
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str = Field(default_factory=lambda: str(uuid4()))
    status: AgentStatus = AgentStatus.PLANNING

    plan: Optional[PlanOutput] = None
    architecture: Optional[ArchitectureOutput] = None
    plan_approved: bool = False

    file_tree: List[str] = Field(default_factory=list)
    code_files: Dict[str, CodeFile] = Field(default_factory=dict)
    current_file: Optional[str] = None

    review_notes: List[ReviewOutput] = Field(default_factory=list)
    test_results: List[TestResult] = Field(default_factory=list)
    tests_passed: bool = False

    retry_count: int = 0
    max_retries: int = 3

    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    max_budget_usd: float = 2.0

    mock_force_fail: bool = False

    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    max_execution_seconds: float = 300.0

    def update_status(self, new_status: AgentStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
