from repositories.base import Task, TaskRepository


class TaskService:
    """Application logic that is independent of the storage engine."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def list_tasks(self) -> list[Task]:
        return self.repository.list()

    def get_task(self, task_id: int) -> Task | None:
        return self.repository.get(task_id)

    def create_task(self, title: str) -> Task:
        return self.repository.create(title)

    def update_task(self, task_id: int, title: str, done: bool) -> Task | None:
        return self.repository.update(task_id, title, done)

    def delete_task(self, task_id: int) -> bool:
        return self.repository.delete(task_id)

    def check_database(self) -> None:
        self.repository.ping()
