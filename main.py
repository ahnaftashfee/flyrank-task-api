import sqlite3
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse


DATABASE_PATH = Path(__file__).with_name("tasks.db")
SEED_TASKS = (
    ("Learn FastAPI", False),
    ("Build a CRUD API", False),
    ("Publish to GitHub", True),
)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
            )
            """
        )
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if task_count == 0:
            connection.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                SEED_TASKS,
            )


def row_to_task(row: sqlite3.Row) -> dict[str, object]:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small SQLite-backed CRUD API for managing a to-do list.",
)

initialize_database()

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


@app.get("/tasks", summary="List all tasks", description="Returns every task in SQLite.")
def list_tasks() -> list[dict[str, object]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, done FROM tasks ORDER BY id"
        ).fetchall()
    return [row_to_task(row) for row in rows]


@app.get(
    "/tasks/{task_id}",
    summary="Get one task",
    description="Returns a task by its ID.",
    response_model=None,
)
def get_task(task_id: int) -> dict[str, object] | JSONResponse:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return row_to_task(row)


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

    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done) VALUES (?, 0)",
            (title.strip(),),
        )
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    assert row is not None
    return row_to_task(row)


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
