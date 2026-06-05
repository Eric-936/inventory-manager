from datetime import date, timedelta
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


# ---------------------------------------------------------------------------
# Restock suggestion tests
# ---------------------------------------------------------------------------

def _make_item_row(
	item_id: int,
	item_name: str,
	shelf_life_type: str,
	expiration_date: str,
	number_of_packages: int,
	quantity_per_package: float = 1.0,
) -> dict[str, str]:
	return {
		"item_id": str(item_id),
		"item_name": item_name,
		"storage_type": "fresh",
		"shelf_life_type": shelf_life_type,
		"package_type": "pack",
		"quantity": str(number_of_packages * quantity_per_package),
		"quantity_type": "kg",
		"quantity_per_package": str(quantity_per_package),
		"batch_based_inventory": f"BATCH-{item_id:03d}",
		"expiration_date": expiration_date,
		"supplier_name": "Test Supplier",
		"pricing": "5.0",
		"related_dishes": "",
		"picture_of_items": "",
		"number_of_packages": str(number_of_packages),
	}


def _build_restock_service(tmp_path: Path, items: list[dict[str, str]]) -> InventoryService:
	items_path = tmp_path / "items.csv"
	transactions_path = tmp_path / "transactions.csv"
	_write_csv(items_path, ITEM_FIELDNAMES, items)
	_write_csv(transactions_path, TRANSACTION_FIELDNAMES, [])
	repository = InventoryRepository(items_path=items_path, transactions_path=transactions_path)
	return InventoryService(repository)


def test_restock_suggestions_critical(tmp_path: Path) -> None:
	# short_term threshold: expiry_days=3, packages=3
	# item expires in 2 days AND has only 2 packages → critical
	expiring_soon = (date.today() + timedelta(days=2)).isoformat()
	service = _build_restock_service(
		tmp_path,
		[_make_item_row(1, "Bean sprouts", "short_term", expiring_soon, number_of_packages=2)],
	)

	result = service.get_restock_suggestions()

	assert len(result.suggestions) == 1
	suggestion = result.suggestions[0]
	assert suggestion.urgency == "critical"
	assert suggestion.days_to_expiry == 2
	assert suggestion.number_of_packages == 2


def test_restock_suggestions_expiring_soon(tmp_path: Path) -> None:
	# expires in 2 days but has 10 packages → only expiry condition met
	expiring_soon = (date.today() + timedelta(days=2)).isoformat()
	service = _build_restock_service(
		tmp_path,
		[_make_item_row(1, "Lime", "short_term", expiring_soon, number_of_packages=10)],
	)

	result = service.get_restock_suggestions()

	assert result.suggestions[0].urgency == "expiring_soon"


def test_restock_suggestions_low_stock(tmp_path: Path) -> None:
	# expires in 30 days (well outside 3-day threshold) but only 2 packages → low_stock
	not_expiring = (date.today() + timedelta(days=30)).isoformat()
	service = _build_restock_service(
		tmp_path,
		[_make_item_row(1, "Spring onion", "short_term", not_expiring, number_of_packages=2)],
	)

	result = service.get_restock_suggestions()

	assert result.suggestions[0].urgency == "low_stock"


def test_restock_suggestions_ok(tmp_path: Path) -> None:
	# expires in 30 days and has 10 packages → ok
	not_expiring = (date.today() + timedelta(days=30)).isoformat()
	service = _build_restock_service(
		tmp_path,
		[_make_item_row(1, "Chicken breast", "short_term", not_expiring, number_of_packages=10)],
	)

	result = service.get_restock_suggestions()

	assert result.suggestions[0].urgency == "ok"


def test_restock_suggestions_sorted_by_urgency(tmp_path: Path) -> None:
	# Multiple items — result must be sorted critical → expiring_soon → low_stock → ok
	today = date.today()
	items = [
		_make_item_row(1, "OK item",            "short_term", (today + timedelta(days=30)).isoformat(), number_of_packages=10),
		_make_item_row(2, "Low stock item",     "short_term", (today + timedelta(days=30)).isoformat(), number_of_packages=2),
		_make_item_row(3, "Expiring soon item", "short_term", (today + timedelta(days=2)).isoformat(),  number_of_packages=10),
		_make_item_row(4, "Critical item",      "short_term", (today + timedelta(days=2)).isoformat(),  number_of_packages=2),
	]
	service = _build_restock_service(tmp_path, items)

	result = service.get_restock_suggestions()

	urgencies = [s.urgency for s in result.suggestions]
	assert urgencies == ["critical", "expiring_soon", "low_stock", "ok"]