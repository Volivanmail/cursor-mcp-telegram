from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from db import create_task, delete_task, get_stats, init_db, list_tasks, toggle_task
from schemas import TaskCreate, TaskRead

app = FastAPI(title="Task Tracker API")

ACTIVITY_LOG: deque[dict] = deque(maxlen=50)
SKIP_LOG_PATHS = {"/docs", "/redoc", "/openapi.json", "/favicon.ico", "/dashboard", "/api/stats"}


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.middleware("http")
async def log_activity(request: Request, call_next):
    started = datetime.now(UTC)
    response = await call_next(request)

    if request.url.path not in SKIP_LOG_PATHS:
        ACTIVITY_LOG.appendleft(
            {
                "time": started.strftime("%H:%M:%S"),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "client": request.headers.get("user-agent", "unknown")[:40],
            }
        )

    return response


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "message": "Task Tracker API",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "tasks": "/api/tasks",
    }


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "task-tracker-api"}


@app.get("/dashboard", response_class=HTMLResponse, tags=["meta"])
async def dashboard() -> str:
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    return template_path.read_text(encoding="utf-8")


@app.get("/api/stats", tags=["meta"])
async def stats() -> dict:
    return {
        "health": await health(),
        "stats": get_stats(),
        "activity": {
            "total": len(ACTIVITY_LOG),
            "requests": list(ACTIVITY_LOG),
        },
        "tasks": list_tasks()[:10],
    }


@app.get("/api/activity", tags=["meta"])
async def activity() -> dict:
    return {
        "total": len(ACTIVITY_LOG),
        "requests": list(ACTIVITY_LOG),
    }


@app.get("/api/tasks", response_model=list[TaskRead], tags=["tasks"])
async def get_tasks(user_id: str | None = Query(default=None)) -> list[dict]:
    return list_tasks(user_id=user_id)


@app.post("/api/tasks", response_model=TaskRead, tags=["tasks"])
async def post_task(payload: TaskCreate) -> dict:
    return create_task(title=payload.title.strip(), user_id=payload.user_id)


@app.patch("/api/tasks/{task_id}/toggle", response_model=TaskRead, tags=["tasks"])
async def patch_toggle_task(task_id: int) -> dict:
    task = toggle_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/api/tasks/{task_id}", tags=["tasks"])
async def remove_task(task_id: int) -> dict[str, str]:
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted", "id": str(task_id)}
