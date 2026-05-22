from fastapi import FastAPI

from app.core.config import APP_NAME
from app.routers.api_inventory import router as inventory_router


app = FastAPI(title=APP_NAME)
app.include_router(inventory_router)


@app.get("/")
def read_root() -> dict[str, str]:
	return {"message": "inventory-manager is running."}