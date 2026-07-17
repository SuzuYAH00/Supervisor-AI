from fastapi import FastAPI

from supervisor_ai.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Supervisor AI", version="0.1.0")
    app.include_router(api_router)
    return app


app = create_app()
