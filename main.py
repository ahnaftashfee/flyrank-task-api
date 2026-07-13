from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def hello() -> dict[str, str]:
    return {"message": "Hello from Task API"}
