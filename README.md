# Dev Crew — Production Multi-Agent Backend

A production-grade FastAPI backend orchestrating a **LangGraph state machine** of specialized AI agents (**Planner, Architect, Coder, Reviewer, Tester, Debugger**) that take software task descriptions and produce working, tested code.

## Key Features & Architecture
- **Deterministic Router**: No LLM routing calls. Decisions come strictly from pure Python edge functions reading structured Pydantic state fields (`tests_passed`, `retry_count`, `cost_exceeded`, `timed_out`).
- **Structured LLM Outputs**: Swappable LLM provider (`BaseLLMProvider`) producing validated Pydantic models for all agent node outputs.
- **Docker-Sandboxed Execution**: AI-generated code is executed exclusively inside a locked-down Docker container (`network_mode="none"`, CPU/memory limits, read-only root, mounted workspace).
- **Enforced Budget & Timeout Ceilings**: Strict `max_execution_seconds` and `max_budget_usd` ceilings enforced in routing state guards.
- **Retry Ceiling & Terminal Failure**: Hard limit on Debugger→Coder retry loops returning partial results at `FAILED_MAX_RETRIES`.
- **Postgres-Backed Checkpointing**: State machine state persisted via checkpointers to allow run resumption by `run_id`.
- **FastAPI API & SSE Streaming**: Async run triggers (`POST /projects/{id}/runs`), status inspection (`GET /runs/{id}`), artifact extraction (`GET /runs/{id}/artifacts`), and real-time event streaming (`GET /runs/{id}/stream`).

## Project Structure
```
.
├── app/
│   ├── api/                # FastAPI endpoints, auth deps & rate limit middleware
│   │   └── v1/
│   │       ├── projects.py # POST /projects & POST /projects/{id}/runs
│   │       ├── runs.py     # GET /runs/{id} & GET /runs/{id}/artifacts
│   │       └── sse.py      # GET /runs/{id}/stream (SSE)
│   ├── core/               # Pydantic v2 AgentState schema, resource limits & routing logic
│   │   ├── limits.py
│   │   ├── routing.py
│   │   └── state.py
│   ├── db/                 # Async SQLAlchemy models & connection base
│   ├── graph/              # LangGraph workflow definition, nodes & checkpointer
│   │   ├── checkpointer.py
│   │   ├── nodes.py
│   │   └── workflow.py
│   ├── llm/                # Provider-agnostic LLM interface & prompt templates
│   │   ├── base.py
│   │   └── prompts/
│   ├── sandbox/            # Docker SDK sandboxed test execution
│   ├── config.py
│   ├── logger.py
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Running Tests
Run the complete unit and integration test suite:
```bash
pytest tests/ -v
```

## Running with Docker Compose
To launch the FastAPI server and PostgreSQL database:
```bash
docker-compose up --build
```
The REST API will be available at `http://localhost:8000`. OpenAPI docs available at `http://localhost:8000/docs`.

