from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.deps import get_inventory_service
from app.services.inventory_service import URGENCY_RANK, InventoryService, ItemNotFoundError


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STYLE_CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "css" / "style.css"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Cache-bust the stylesheet URL with its mtime so browsers always fetch the
# latest CSS instead of serving a stale cached copy (no Cache-Control header
# is set on /static, so browsers fall back to long heuristic caching).
templates.env.globals["asset_version"] = lambda: int(STYLE_CSS_PATH.stat().st_mtime)

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    service: InventoryService = Depends(get_inventory_service),
) -> HTMLResponse:
    overview = service.get_inventory_overview()
    restock_data = service.get_restock_suggestions()
    suggestions = {s.item_id: s for s in restock_data.suggestions}
    sorted_items = sorted(
        overview.items,
        key=lambda i: URGENCY_RANK.get(
            suggestions[i.item_id].urgency if i.item_id in suggestions else "ok", 3
        ),
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "items": sorted_items,
            "suggestions": suggestions,
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
