from typing import Protocol, TypedDict


class Task(TypedDict):
    id: int
    title: str
    done: bool


class TaskRepository(Protocol):
    def list(self) -> list[Task]: ...

    def get(self, task_id: int) -> Task | None: ...

    def create(self, title: str) -> Task: ...

    def update(self, task_id: int, title: str, done: bool) -> Task | None: ...

    def delete(self, task_id: int) -> bool: ...

    def ping(self) -> None: ...
