from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mangum import Mangum
from starlette.middleware.cors import CORSMiddleware

from src.config import settings
from src.exceptions import AppError, app_exception_handler
from src.resources.router import router as resources_router

SHOW_DOCS_IN = {"local", "staging"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield


app_kwargs: dict = {
    "title": settings.APP_TITLE,
    "version": settings.APP_VERSION,
    "lifespan": lifespan,
}

if settings.ENVIRONMENT not in SHOW_DOCS_IN:
    app_kwargs["openapi_url"] = None

app = FastAPI(**app_kwargs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS[settings.ENVIRONMENT],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=300,
)

app.add_exception_handler(AppError, app_exception_handler)
app.include_router(resources_router)

handler = Mangum(app)
