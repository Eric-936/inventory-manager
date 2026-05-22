from pathlib import Path

from app.models.inventory import InventoryCreate, InventoryUpdate
from app.repositories.inventory_repo import ITEM_FIELDNAMES, TRANSACTION_FIELDNAMES, InventoryRepository
from app.services.inventory_service import InventoryService, ItemNotFoundError


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
	lines = [",".join(fieldnames)]
	for row in rows:
		lines.append(",".join(str(row.get(field, "")) for field in fieldnames))
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_service(tmp_path: Path) -> InventoryService:
	items_path = tmp_path / "items.csv"
	transactions_path = tmp_path / "transactions.csv"

	_write_csv(
		items_path,
		ITEM_FIELDNAMES,
		[
			{
				"item_id": "1",
				"item_name": "Chicken breast",
				"storage_type": "fresh",
				"shelf_life_type": "short_term",
				"package_type": "pack",
				"quantity": "10.0",
				"quantity_unit": "kg",
				"batch_number": "BATCH-001",
				"expiration_date": "2026-05-31",
				"supplier_name": "Fresh Farm Co.",
				"price_per_unit": "8.0",
				"reorder_threshold": "4.0",
				"related_dishes": "Pho Ga",
				"picture_url": "https://example.com/chicken.jpg",
			}
		],
	)
	_write_csv(
		transactions_path,
		TRANSACTION_FIELDNAMES,
		[
			{
				"action_id": "1",
				"item_id": "1",
				"action_type": "add",
				"action_detail": "purchase",
				"quantity_changed": "10.0",
				"date_of_action": "2026-05-21 08:00:00",
				"staff_name": "Minh",
				"comments": "Initial stock",
			}
		],
	)

	repository = InventoryRepository(items_path=items_path, transactions_path=transactions_path)
	return InventoryService(repository)


def test_add_or_create_item_increases_quantity_for_existing_item(tmp_path: Path) -> None:
	service = _build_service(tmp_path)

	response = service.add_or_create_item(
		InventoryCreate(
			item_name="Chicken breast",
			storage_type="fresh",
			shelf_life_type="short_term",
			package_type="pack",
			quantity=2.5,
			quantity_unit="kg",
			batch_number="BATCH-NEW",
			expiration_date="2026-06-01",
			supplier_name="Fresh Farm Co.",
			price_per_unit=8.5,
			reorder_threshold=4.0,
			related_dishes="Pho Ga",
			picture_url="https://example.com/chicken.jpg",
		)
	)

	assert response.operation == "updated"
	assert response.item.quantity == 12.5


def test_update_item_changes_target_fields(tmp_path: Path) -> None:
	service = _build_service(tmp_path)

	updated = service.update_item(
		1,
		InventoryUpdate(quantity=7.0, supplier_name="Updated Supplier"),
	)

	assert updated.quantity == 7.0
	assert updated.supplier_name == "Updated Supplier"


def test_delete_item_raises_for_missing_id(tmp_path: Path) -> None:
	service = _build_service(tmp_path)

	try:
		service.delete_item(999)
	except ItemNotFoundError:
		pass
	else:
		raise AssertionError("Expected missing item to raise ItemNotFoundError")