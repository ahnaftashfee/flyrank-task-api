# Task API

A small in-memory CRUD API for managing a to-do list. It was built with FastAPI for FlyRank's Backend AI Engineering assignment (BE-01).

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive Swagger UI is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Endpoints

| Method | Path | Description | Success status |
| --- | --- | --- | --- |
| GET | `/` | API metadata | 200 |
| GET | `/health` | Server health check | 200 |
| GET | `/tasks` | List all tasks | 200 |
| GET | `/tasks/{id}` | Get one task | 200 |
| POST | `/tasks` | Create a task with `title` | 201 |
| PUT | `/tasks/{id}` | Update a task's `title` and/or `done` status | 200 |
| DELETE | `/tasks/{id}` | Delete a task | 204 |

Unknown task IDs return a JSON `404` error. POST and PUT reject missing or blank titles with a JSON `400` error.

## Example request

```console
$ curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

FastAPI generates interactive OpenAPI documentation automatically. Use **Try it out** in Swagger UI to create, list, update, and delete tasks without curl.

![Swagger UI showing all Task API endpoints](docs/swagger-ui.jpg)

## In-memory storage

Tasks are deliberately stored only in the application process. Restarting the server resets the list to its three sample tasks; this assignment uses that behavior to demonstrate why a database is needed in later work.
