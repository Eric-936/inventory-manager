from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import APP_NAME
from app.routers.api_inventory import router as inventory_router
from app.routers.pages import router as pages_router


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(pages_router)
app.include_router(inventory_router)
