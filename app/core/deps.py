from app.core.config import ITEMS_CSV_PATH, TRANSACTIONS_CSV_PATH
from app.repositories.inventory_repo import InventoryRepository
from app.services.inventory_service import InventoryService


def get_inventory_service() -> InventoryService:
    repository = InventoryRepository(
        items_path=ITEMS_CSV_PATH,
        transactions_path=TRANSACTIONS_CSV_PATH,
    )
    return InventoryService(repository)
