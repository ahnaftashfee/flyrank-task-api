from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small in-memory CRUD API for managing a to-do list.",
)

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Publish to GitHub", "done": True},
]


@app.get("/", summary="Describe the API", description="Returns basic API metadata.")
def root() -> dict[str, object]:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Check API health", description="Confirms the server is running.")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks", description="Returns every task in memory.")
def list_tasks() -> list[dict[str, object]]:
    return tasks


@app.get(
    "/tasks/{task_id}",
    summary="Get one task",
    description="Returns a task by its ID.",
    response_model=None,
)
def get_task(task_id: int) -> dict[str, object] | JSONResponse:
    task = next((task for task in tasks if task["id"] == task_id), None)
    if task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return task


@app.post(
    "/tasks",
    status_code=201,
    summary="Create a task",
    description="Creates a task from a non-empty title and marks it incomplete.",
    response_model=None,
)
def create_task(payload: dict = Body(...)) -> dict[str, object] | JSONResponse:
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "A non-empty title is required"},
        )

    next_id = max((task["id"] for task in tasks), default=0) + 1
    task = {"id": next_id, "title": title.strip(), "done": False}
    tasks.append(task)
    return task


@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
    description="Updates a task title, completion state, or both.",
    response_model=None,
)
def update_task(
    task_id: int, payload: dict = Body(...)
) -> dict[str, object] | JSONResponse:
    task = next((task for task in tasks if task["id"] == task_id), None)
    if task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )

    if not payload or any(key not in {"title", "done"} for key in payload):
        return JSONResponse(status_code=400, content={"error": "Provide title and/or done"})

    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(
                status_code=400, content={"error": "A non-empty title is required"}
            )
        task["title"] = title.strip()

    if "done" in payload:
        if not isinstance(payload["done"], bool):
            return JSONResponse(
                status_code=400, content={"error": "done must be true or false"}
            )
        task["done"] = payload["done"]
    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
    description="Removes a task by its ID.",
    response_model=None,
)
def delete_task(task_id: int) -> None | JSONResponse:
    index = next((i for i, task in enumerate(tasks) if task["id"] == task_id), None)
    if index is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    tasks.pop(index)
    return None
