"""FastAPI main application entrypoint."""

from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langserve import add_routes
from app.api.crew_runnable import crew_runnable
from app.api.middleware import RateLimitMiddleware
from app.api.v1.projects import router as projects_router
from app.api.v1.runs import router as runs_router
from app.api.v1.sse import router as sse_router
from app.logger import logger

app = FastAPI(
    title="Dev Crew Multi-Agent Backend",
    description="Production-grade LangGraph backend for multi-agent software development.",
    version="0.1.0",
)

# Add Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Middleware attaching request_id header and structured log context."""
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Include Routers
app.include_router(projects_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(sse_router, prefix="/api/v1")

# LangServe: exposes the real Planner->Architect->Coder->Reviewer->Tester->Debugger graph
add_routes(app, crew_runnable, path="/crew")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "dev-crew-backend"}
