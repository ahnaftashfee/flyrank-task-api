from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse

from auth import APIError, router as auth_router
from dependencies import task_service


app = FastAPI(
    title="Task API",
    version="3.0",
    description="A PostgreSQL task API secured with Supabase Auth.",
)

app.include_router(auth_router)


@app.exception_handler(APIError)
def handle_api_error(_request: Request, error: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": error.message},
    )


@app.get("/", summary="Describe the API", description="Returns basic API metadata.")
def root() -> dict[str, object]:
    return {
        "name": "Task API",
        "version": "3.0",
        "endpoints": ["/tasks", "/auth/signup", "/auth/login", "/docs"],
    }


@app.get("/health", summary="Check API health", description="Checks the API and database.")
def health() -> dict[str, str]:
    task_service.check_database()
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks", description="Returns every task in PostgreSQL.")
def list_tasks() -> list[dict[str, object]]:
    return task_service.list_tasks()


@app.get(
    "/tasks/{task_id}",
    summary="Get one task",
    description="Returns a task by its ID.",
    response_model=None,
)
def get_task(task_id: int) -> dict[str, object] | JSONResponse:
    task = task_service.get_task(task_id)
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
def create_task(
    payload: object | None = Body(default=None),
) -> dict[str, object] | JSONResponse:
    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400, content={"error": "A JSON object is required"}
        )
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "A non-empty title is required"},
        )
    return task_service.create_task(title.strip())


@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
    description="Updates a task title, completion state, or both.",
    response_model=None,
)
def update_task(
    task_id: int, payload: object | None = Body(default=None)
) -> dict[str, object] | JSONResponse:
    task = task_service.get_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )

    if (
        not isinstance(payload, dict)
        or not payload
        or any(key not in {"title", "done"} for key in payload)
    ):
        return JSONResponse(
            status_code=400, content={"error": "Provide title and/or done"}
        )

    title = task["title"]
    done = task["done"]

    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "A non-empty title is required"},
            )
        title = title.strip()

    if "done" in payload:
        if not isinstance(payload["done"], bool):
            return JSONResponse(
                status_code=400,
                content={"error": "done must be true or false"},
            )
        done = payload["done"]

    updated_task = task_service.update_task(task_id, title, done)
    if updated_task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return updated_task


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
    description="Removes a task by its ID.",
    response_model=None,
)
def delete_task(task_id: int) -> None | JSONResponse:
    if not task_service.delete_task(task_id):
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return None
