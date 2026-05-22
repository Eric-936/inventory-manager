from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import ITEMS_CSV_PATH, TRANSACTIONS_CSV_PATH
from app.models.inventory import (
	InventoryCreate,
	InventoryOverview,
	InventoryItem,
	InventoryUpdate,
	InventoryUpsertResponse,
)
from app.repositories.inventory_repo import InventoryRepository
from app.services.inventory_service import InventoryService, ItemNotFoundError


router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def get_inventory_service() -> InventoryService:
	repository = InventoryRepository(
		items_path=ITEMS_CSV_PATH,
		transactions_path=TRANSACTIONS_CSV_PATH,
	)
	return InventoryService(repository)


@router.get("", response_model=InventoryOverview)
def get_inventory_overview(
	service: InventoryService = Depends(get_inventory_service),
) -> InventoryOverview:
	return service.get_inventory_overview()


@router.post(
	"",
	response_model=InventoryUpsertResponse,
	status_code=status.HTTP_201_CREATED,
)
def add_or_create_inventory_item(
	payload: InventoryCreate,
	service: InventoryService = Depends(get_inventory_service),
) -> InventoryUpsertResponse:
	return service.add_or_create_item(payload)


@router.put("/{item_id}", response_model=InventoryItem)
def update_inventory_item(
	item_id: int,
	payload: InventoryUpdate,
	service: InventoryService = Depends(get_inventory_service),
) -> InventoryItem:
	try:
		return service.update_item(item_id, payload)
	except ItemNotFoundError as error:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
	item_id: int,
	service: InventoryService = Depends(get_inventory_service),
) -> None:
	try:
		service.delete_item(item_id)
	except ItemNotFoundError as error:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error