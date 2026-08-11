import unittest

from fastapi.testclient import TestClient

import main
from repositories.base import Task
from service import TaskService


class MemoryTaskRepository:
    """Small repository fake used only for route regression tests."""

    def __init__(self) -> None:
        self.tasks: dict[int, Task] = {
            1: {"id": 1, "title": "Test task", "done": False}
        }
        self.next_id = 2

    def list(self) -> list[Task]:
        return list(self.tasks.values())

    def get(self, task_id: int) -> Task | None:
        return self.tasks.get(task_id)

    def create(self, title: str) -> Task:
        task: Task = {"id": self.next_id, "title": title, "done": False}
        self.tasks[self.next_id] = task
        self.next_id += 1
        return task

    def update(self, task_id: int, title: str, done: bool) -> Task | None:
        if task_id not in self.tasks:
            return None
        task: Task = {"id": task_id, "title": title, "done": done}
        self.tasks[task_id] = task
        return task

    def delete(self, task_id: int) -> bool:
        return self.tasks.pop(task_id, None) is not None

    def ping(self) -> None:
        return None


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        main.task_service = TaskService(MemoryTaskRepository())
        self.client = TestClient(main.app)

    def test_health_and_list(self) -> None:
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/tasks").status_code, 200)

    def test_create_update_and_delete(self) -> None:
        created = self.client.post("/tasks", json={"title": "Containerize API"})
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["id"]

        updated = self.client.put(
            f"/tasks/{task_id}", json={"title": "Use PostgreSQL", "done": True}
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["done"], True)

        deleted = self.client.delete(f"/tasks/{task_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/tasks/{task_id}").status_code, 404)

    def test_validation_contract_is_unchanged(self) -> None:
        self.assertEqual(self.client.post("/tasks", json={}).status_code, 400)
        self.assertEqual(
            self.client.put("/tasks/1", json={"done": "yes"}).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
