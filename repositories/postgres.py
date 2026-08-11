import psycopg
from psycopg.rows import dict_row

from .base import Task


class PostgresTaskRepository:
    """PostgreSQL implementation of the task repository contract."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _to_task(row: dict[str, object]) -> Task:
        return {
            "id": int(row["id"]),
            "title": str(row["title"]),
            "done": bool(row["done"]),
        }

    def list(self) -> list[Task]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, done FROM tasks ORDER BY id"
            ).fetchall()
        return [self._to_task(row) for row in rows]

    def get(self, task_id: int) -> Task | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s",
                (task_id,),
            ).fetchone()
        return None if row is None else self._to_task(row)

    def create(self, title: str) -> Task:
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO tasks (title, done)
                VALUES (%s, FALSE)
                RETURNING id, title, done
                """,
                (title,),
            ).fetchone()
        if row is None:
            raise RuntimeError("PostgreSQL did not return the created task")
        return self._to_task(row)

    def update(self, task_id: int, title: str, done: bool) -> Task | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE tasks
                SET title = %s, done = %s
                WHERE id = %s
                RETURNING id, title, done
                """,
                (title, done, task_id),
            ).fetchone()
        return None if row is None else self._to_task(row)

    def delete(self, task_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = %s",
                (task_id,),
            )
        return cursor.rowcount > 0

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1")
