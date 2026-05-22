from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.inventory import InventoryCreate
from app.repositories.inventory_repo import ITEM_FIELDNAMES, TRANSACTION_FIELDNAMES, InventoryRepository
from app.routers.api_inventory import get_inventory_service
from app.services.inventory_service import InventoryService


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
	lines = [",".join(fieldnames)]
	for row in rows:
		lines.append(",".join(str(row.get(field, "")) for field in fieldnames))
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_test_client(tmp_path: Path) -> TestClient:
	items_path = tmp_path / "items.csv"
	transactions_path = tmp_path / "transactions.csv"

	_write_csv(
		items_path,
		ITEM_FIELDNAMES,
		[
			{
				"item_id": "1",
				"item_name": "Beef (sliced)",
				"storage_type": "fresh",
				"shelf_life_type": "short_term",
				"package_type": "pack",
				"quantity": "15.5",
				"quantity_unit": "kg",
				"batch_number": "BATCH-001",
				"expiration_date": "2026-05-31",
				"supplier_name": "Fresh Farm Co.",
				"price_per_unit": "12.5",
				"reorder_threshold": "5.0",
				"related_dishes": "Pho Bo",
				"picture_url": "https://example.com/beef.jpg",
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
				"quantity_changed": "15.5",
				"date_of_action": "2026-05-21 08:00:00",
				"staff_name": "Minh",
				"comments": "Initial stock",
			}
		],
	)

	def override_service() -> InventoryService:
		repository = InventoryRepository(items_path=items_path, transactions_path=transactions_path)
		return InventoryService(repository)

	app.dependency_overrides[get_inventory_service] = override_service
	return TestClient(app)


def test_get_inventory_returns_items_and_transactions(tmp_path: Path) -> None:
	client = _build_test_client(tmp_path)

	response = client.get("/api/inventory")

	assert response.status_code == 200
	payload = response.json()
	assert len(payload["items"]) == 1
	assert len(payload["transactions"]) == 1


def test_post_inventory_updates_existing_item_quantity(tmp_path: Path) -> None:
	client = _build_test_client(tmp_path)

	response = client.post(
		"/api/inventory",
		json=InventoryCreate(
			item_name="Beef (sliced)",
			storage_type="fresh",
			shelf_life_type="short_term",
			package_type="pack",
			quantity=2.0,
			quantity_unit="kg",
			batch_number="BATCH-001",
			expiration_date="2026-05-31",
			supplier_name="Fresh Farm Co.",
			price_per_unit=12.5,
			reorder_threshold=5.0,
			related_dishes="Pho Bo",
			picture_url="https://example.com/beef.jpg",
		).model_dump(mode="json"),
	)

	assert response.status_code == 201
	payload = response.json()
	assert payload["operation"] == "updated"
	assert payload["item"]["quantity"] == 17.5


def test_put_inventory_updates_single_item(tmp_path: Path) -> None:
	client = _build_test_client(tmp_path)

	response = client.put(
		"/api/inventory/1",
		json={"supplier_name": "Updated Supplier", "quantity": 12.0},
	)

	assert response.status_code == 200
	payload = response.json()
	assert payload["supplier_name"] == "Updated Supplier"
	assert payload["quantity"] == 12.0


def test_delete_inventory_removes_item(tmp_path: Path) -> None:
	client = _build_test_client(tmp_path)

	response = client.delete("/api/inventory/1")

	assert response.status_code == 204
	follow_up = client.get("/api/inventory")
	assert follow_up.status_code == 200
	assert follow_up.json()["items"] == []