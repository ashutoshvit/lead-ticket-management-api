import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.events import dispatch_outbox_once
from app import models  # noqa: F401 - ensure models are registered before create_all
from app.routes import router

logging.basicConfig(level=logging.INFO)


async def outbox_worker() -> None:
    while True:
        await asyncio.to_thread(dispatch_outbox_once)
        await asyncio.sleep(settings.outbox_poll_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    worker = asyncio.create_task(outbox_worker())
    yield
    worker.cancel()
    with suppress(asyncio.CancelledError):
        await worker
    engine.dispose()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
def live():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready"}

