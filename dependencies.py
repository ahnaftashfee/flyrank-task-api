import os

from dotenv import load_dotenv

from auth_service import AuthService
from repositories import PostgresTaskRepository
from service import TaskService


load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is required. Copy .env.example to .env and set its values."
    )

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY are required. Copy .env.example to .env "
        "and set their values."
    )

task_service = TaskService(PostgresTaskRepository(database_url))
auth_service = AuthService(supabase_url, supabase_key)
