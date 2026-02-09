"""Entrypoint da API FastAPI."""

from src.presentation.api.app import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
