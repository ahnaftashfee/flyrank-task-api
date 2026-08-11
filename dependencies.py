import os

from dotenv import load_dotenv

from repositories import PostgresTaskRepository
from service import TaskService


load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is required. Copy .env.example to .env and set its values."
    )

task_service = TaskService(PostgresTaskRepository(database_url))
