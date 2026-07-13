from fastapi import FastAPI
from fastapi.responses import JSONResponse


app = FastAPI()

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Publish to GitHub", "done": True},
]


@app.get("/", summary="Describe the API")
def root() -> dict[str, object]:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Check API health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
def list_tasks() -> list[dict[str, object]]:
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task")
def get_task(task_id: int) -> dict[str, object] | JSONResponse:
    task = next((task for task in tasks if task["id"] == task_id), None)
    if task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return task
