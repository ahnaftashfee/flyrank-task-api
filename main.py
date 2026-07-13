from fastapi import FastAPI


app = FastAPI()


@app.get("/", summary="Describe the API")
def root() -> dict[str, object]:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Check API health")
def health() -> dict[str, str]:
    return {"status": "ok"}
