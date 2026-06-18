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
- Get restocking suggestions for all items based on current stock and expiration date

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
- `quantity_type`
- `quantity_per_package`
- `batch_based_inventory`
- `expiration_date`
- `supplier_name`
- `pricing`
- `related_dishes`
- `picture_of_items`
- `number_of_packages`

### `transactions_table.csv`

This stores inventory actions.

Expected columns:

- `action_id`
- `item_id`
- `action_type`
- `action_detail`
- `date_of_action`
- `comments`

## Run The API Locally

This project can be run with standard Python and `pip`.

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the project and its dependencies:

```bash
pip install -e .
```

If you want to run tests locally, install the test dependencies too:

```bash
pip install pytest httpx
```

If you want to run the FastAPI server locally, use `uvicorn`:

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
			"quantity_type": "kg",
			"quantity_per_package": 1.55,
			"batch_based_inventory": "BATCH-2025-001",
			"expiration_date": "2025-05-24",
			"supplier_name": "Fresh Farm Co.",
			"pricing": 12.5,
			"related_dishes": "Pho Bo / Bun Bo",
			"picture_of_items": null,
			"number_of_packages": 10
		}
	],
	"transactions": [
		{
			"action_id": 1,
			"item_id": 1,
			"action_type": "add",
			"action_detail": "purchase",
			"date_of_action": "2025-05-20T08:00:00",
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
- `quantity_type`
- `quantity_per_package`
- `batch_based_inventory`
- `expiration_date`
- `supplier_name`
- `pricing`

At least one of the following is required to establish the quantity:

- `number_of_packages` — quantity is computed automatically as `number_of_packages × quantity_per_package`
- `quantity` — set directly if packages are not applicable

Optional request fields:

- `related_dishes`
- `picture_of_items`

Example request:

```json
{
	"item_name": "Chicken breast",
	"storage_type": "fresh",
	"shelf_life_type": "short_term",
	"package_type": "pack",
	"quantity_type": "kg",
	"quantity_per_package": 1.25,
	"number_of_packages": 2,
	"batch_based_inventory": "BATCH-2026-010",
	"expiration_date": "2026-06-01",
	"supplier_name": "Fresh Farm Co.",
	"pricing": 8.5,
	"related_dishes": "Pho Ga"
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
		"quantity_type": "kg",
		"quantity_per_package": 1.25,
		"batch_based_inventory": "BATCH-2025-002",
		"expiration_date": "2025-05-23",
		"supplier_name": "Fresh Farm Co.",
		"pricing": 8.0,
		"related_dishes": "Pho Ga / Com Ga",
		"picture_of_items": null,
		"number_of_packages": 10
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
	"number_of_packages": 8
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
	"quantity": 12.4,
	"quantity_type": "kg",
	"quantity_per_package": 1.55,
	"batch_based_inventory": "BATCH-2025-001",
	"expiration_date": "2025-05-24",
	"supplier_name": "Updated Supplier",
	"pricing": 12.5,
	"related_dishes": "Pho Bo / Bun Bo",
	"picture_of_items": null,
	"number_of_packages": 8
}
```

### `DELETE /api/inventory/{item_id}`

Deletes a specific item by `item_id`.

Response:

- HTTP `204 No Content` on success

### `GET /api/inventory/restock-suggestions`

Scans all inventory items and returns a prioritised list of restocking suggestions.

No request parameters required.

Response shape:

```json
{
	"generated_at": "2026-05-30",
	"suggestions": [
		{
			"item_id": 1,
			"item_name": "Beef (sliced)",
			"current_quantity": 4.65,
			"quantity_type": "kg",
			"number_of_packages": 3,
			"usage_count_30d": 5,
			"days_to_expiry": 2,
			"urgency": "critical",
			"reason": "Only 3 package(s) remaining and expires in 2 day(s). Withdrawn 5 time(s) in the last 30 days."
		}
	]
}
```

#### Response fields

| Field | Type | Description |
|---|---|---|
| `generated_at` | date | The date this response was produced |
| `item_id` | int | Item identifier |
| `item_name` | string | Item name |
| `current_quantity` | float | Current stock quantity |
| `quantity_type` | string | Unit of measurement (e.g. `kg`, `bottle`) |
| `number_of_packages` | int \| null | Number of packages currently in stock |
| `usage_count_30d` | int | Number of `withdraw` transactions recorded in the last 30 days |
| `days_to_expiry` | int | Days until `expiration_date`; negative means already expired |
| `urgency` | string | One of `critical`, `expiring_soon`, `low_stock`, `ok` |
| `reason` | string | Human-readable explanation of the urgency level |

Results are sorted by urgency: `critical` first, then `expiring_soon`, then `low_stock`, then `ok`.

#### How urgency is determined

Each `shelf_life_type` has two thresholds:

| `shelf_life_type` | Expiry threshold (days) | Low-stock threshold (packages) |
|---|---|---|
| `short_term` | 3 | 3 |
| `medium_term` | 7 | 5 |
| `long_term` | 14 | 2 |

The urgency level is assigned as follows:

- **`critical`** — both conditions are true: stock is at or below the package threshold AND the item expires within the expiry threshold. Order immediately.
- **`expiring_soon`** — item expires within the threshold but stock is still adequate. Monitor or plan ahead.
- **`low_stock`** — stock is at or below the threshold but expiry is not imminent. Plan a restock.
- **`ok`** — neither condition is triggered.

## Validation Rules

Validation is defined in [app/models/inventory.py](app/models/inventory.py).

Important frontend-facing rules:

- Required string fields must not be missing or empty
- `quantity`, `quantity_per_package`, and `pricing` must be non-negative
- `expiration_date` must be sent as `YYYY-MM-DD`
- `quantity` is computed automatically from `number_of_packages × quantity_per_package`; you must provide either `number_of_packages` or a direct `quantity` value

If the payload fails validation, FastAPI returns HTTP `422`.

## Notes For Frontend Integration

- Use `GET /api/inventory` if your page needs both the inventory list and the transaction history in one request
- Use `GET /api/inventory/restock-suggestions` to drive a restocking dashboard or alert banner
- Use `POST /api/inventory` for stock-in behavior
- Use `PUT /api/inventory/{item_id}` for editing a single item form
- Use `DELETE /api/inventory/{item_id}` for remove actions
- The current matching rule for the add endpoint is based on `item_name`
- `usage_count_30d` in the suggestions response reflects raw withdrawal event count, not quantity consumed — one transaction equals one count

## Tests

Focused API and service tests are in:

- [tests/test_api_inventory.py](/Users/ericzhao/Cosmos/inventory-manager/tests/test_api_inventory.py)
- [tests/test_inventory_service.py](/Users/ericzhao/Cosmos/inventory-manager/tests/test_inventory_service.py)

Run them with:

```bash
pytest tests/test_api_inventory.py tests/test_inventory_service.py
```
