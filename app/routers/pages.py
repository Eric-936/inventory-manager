from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import ITEMS_CSV_PATH, TRANSACTIONS_CSV_PATH
from app.repositories.inventory_repo import InventoryRepository
from app.services.inventory_service import InventoryService, ItemNotFoundError


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["pages"])


def get_inventory_service() -> InventoryService:
    repository = InventoryRepository(
        items_path=ITEMS_CSV_PATH,
        transactions_path=TRANSACTIONS_CSV_PATH,
    )
    return InventoryService(repository)


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    service: InventoryService = Depends(get_inventory_service),
) -> HTMLResponse:
    overview = service.get_inventory_overview()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "items": overview.items,
        },
    )


@router.get("/item/{item_id}", response_class=HTMLResponse)
def item_detail(
    item_id: int,
    request: Request,
    service: InventoryService = Depends(get_inventory_service),
) -> HTMLResponse:
    try:
        item = service.get_item(item_id)
    except ItemNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found.")
    transactions = service.get_item_transactions(item_id)
    return templates.TemplateResponse(
        request,
        "detail.html",
        {
            "item": item,
            "transactions": transactions,
        },
    )
