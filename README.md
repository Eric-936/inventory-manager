# inventory-manager

Restaurant inventory management backend built with Python and FastAPI.

This README is written for frontend teammates who need to know where the CSV data lives and how to call the API.

## What The API Does

The current backend reads and writes CSV files instead of using a database.

It supports these inventory workflows:

- Read all inventory data and transaction data
- Add stock for an item
- Create a new item if it does not exist yet
- Update a specific item by `item_id`
- Delete a specific item by `item_id`

## CSV File Location

The backend expects the CSV files to live in the top-level `data/` folder.

Required file paths:

- `data/items_table.csv`
- `data/transactions_table.csv`

These paths are configured in [app/core/config.py](/Users/ericzhao/Cosmos/inventory-manager/app/core/config.py).

If you move the files or rename them, the API will not find the data unless you update that config file too.

## Expected CSV Files

### `items_table.csv`

This is the main inventory table.

Expected columns:

- `item_id`
- `item_name`
- `storage_type`
- `shelf_life_type`
- `package_type`
- `quantity`
- `quantity_unit`
- `batch_number`
- `expiration_date`
- `supplier_name`
- `price_per_unit`
- `reorder_threshold`
- `related_dishes`
- `picture_url`

### `transactions_table.csv`

This stores inventory actions.

Expected columns:

- `action_id`
- `item_id`
- `action_type`
- `action_detail`
- `quantity_changed`
- `date_of_action`
- `staff_name`
- `comments`

## Run The API Locally

This project can be run with standard Python and `pip`.

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the project from `pyproject.toml`:

```bash
pip install -e .
```

This installs the runtime dependencies listed in [pyproject.toml](/Users/ericzhao/Cosmos/inventory-manager/pyproject.toml).

If you want to run tests locally, install the test dependencies too:

```bash
pip install pytest httpx
```

If you want to run the FastAPI server locally, use `uvicorn`.

Example:

```bash
python -m uvicorn app.main:app --reload
```

Default local base URL:

```text
http://127.0.0.1:8000
```

Health-style root route:

- `GET /`

## API Endpoints

The inventory router is defined in [app/routers/api_inventory.py](/Users/ericzhao/Cosmos/inventory-manager/app/routers/api_inventory.py).

### `GET /api/inventory`

Returns both CSV tables in one response.

Response shape:

```json
{
	"items": [
		{
			"item_id": 1,
			"item_name": "Beef (sliced)",
			"storage_type": "fresh",
			"shelf_life_type": "short_term",
			"package_type": "pack",
			"quantity": 15.5,
			"quantity_unit": "kg",
			"batch_number": "BATCH-2025-001",
			"expiration_date": "2025-05-24",
			"supplier_name": "Fresh Farm Co.",
			"price_per_unit": 12.5,
			"reorder_threshold": 5.0,
			"related_dishes": "Pho Bo / Bun Bo",
			"picture_url": null
		}
	],
	"transactions": [
		{
			"action_id": 1,
			"item_id": 1,
			"action_type": "add",
			"action_detail": "purchase",
			"quantity_changed": 20.0,
			"date_of_action": "2025-05-20T08:00:00",
			"staff_name": "Minh",
			"comments": "Initial stock for opening"
		}
	]
}
```

### `POST /api/inventory`

Adds inventory.

Behavior:

- If an item with the same `item_name` already exists, the backend increases its `quantity`
- If no matching item exists, the backend creates a new item

Required request fields:

- `item_name`
- `storage_type`
- `shelf_life_type`
- `package_type`
- `quantity`
- `quantity_unit`
- `batch_number`
- `expiration_date`
- `supplier_name`
- `price_per_unit`
- `reorder_threshold`

Optional request fields:

- `related_dishes`
- `picture_url`

Example request:

```json
{
	"item_name": "Chicken breast",
	"storage_type": "fresh",
	"shelf_life_type": "short_term",
	"package_type": "pack",
	"quantity": 2.5,
	"quantity_unit": "kg",
	"batch_number": "BATCH-2026-010",
	"expiration_date": "2026-06-01",
	"supplier_name": "Fresh Farm Co.",
	"price_per_unit": 8.5,
	"reorder_threshold": 4.0,
	"related_dishes": "Pho Ga",
	"picture_url": "https://example.com/chicken.jpg"
}
```

Example response:

```json
{
	"operation": "updated",
	"item": {
		"item_id": 2,
		"item_name": "Chicken breast",
		"storage_type": "fresh",
		"shelf_life_type": "short_term",
		"package_type": "pack",
		"quantity": 12.5,
		"quantity_unit": "kg",
		"batch_number": "BATCH-2025-002",
		"expiration_date": "2025-05-23",
		"supplier_name": "Fresh Farm Co.",
		"price_per_unit": 8.0,
		"reorder_threshold": 4.0,
		"related_dishes": "Pho Ga / Com Ga",
		"picture_url": null
	}
}
```

### `PUT /api/inventory/{item_id}`

Updates a specific item.

This is a partial update endpoint, so the frontend only needs to send the fields that should change.

Example request:

```json
{
	"supplier_name": "Updated Supplier",
	"quantity": 12.0,
	"reorder_threshold": 3.0
}
```

Example response:

```json
{
	"item_id": 1,
	"item_name": "Beef (sliced)",
	"storage_type": "fresh",
	"shelf_life_type": "short_term",
	"package_type": "pack",
	"quantity": 12.0,
	"quantity_unit": "kg",
	"batch_number": "BATCH-2025-001",
	"expiration_date": "2025-05-24",
	"supplier_name": "Updated Supplier",
	"price_per_unit": 12.5,
	"reorder_threshold": 3.0,
	"related_dishes": "Pho Bo / Bun Bo",
	"picture_url": null
}
```

### `DELETE /api/inventory/{item_id}`

Deletes a specific item by `item_id`.

Response:

- HTTP `204 No Content` on success

## Validation Rules

Validation is defined in [app/models/inventory.py](/Users/ericzhao/Cosmos/inventory-manager/app/models/inventory.py).

Important frontend-facing rules:

- Required string fields must not be missing
- Required string fields must not be empty strings
- `quantity`, `price_per_unit`, and `reorder_threshold` must be non-negative
- `expiration_date` should be sent as `YYYY-MM-DD`

If the payload fails validation, FastAPI returns HTTP `422`.

## Notes For Frontend Integration

- Use `GET /api/inventory` if your page needs both the inventory list and the transaction history in one request
- Use `POST /api/inventory` for stock-in behavior
- Use `PUT /api/inventory/{item_id}` for editing a single item form
- Use `DELETE /api/inventory/{item_id}` for remove actions
- The current matching rule for the add endpoint is based on `item_name`

## Tests

Focused API and service tests are in:

- [tests/test_api_inventory.py](/Users/ericzhao/Cosmos/inventory-manager/tests/test_api_inventory.py)
- [tests/test_inventory_service.py](/Users/ericzhao/Cosmos/inventory-manager/tests/test_inventory_service.py)

Run them with:

```bash
pytest tests/test_api_inventory.py tests/test_inventory_service.py
```
