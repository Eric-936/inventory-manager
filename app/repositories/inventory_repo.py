import csv
from datetime import UTC, datetime
from pathlib import Path

from app.models.inventory import (
	InventoryCreate,
	InventoryItem,
	InventoryUpdate,
	TransactionRecord,
)


ITEM_FIELDNAMES = [
	"item_id",
	"item_name",
	"storage_type",
	"shelf_life_type",
	"package_type",
	"quantity",
	"quantity_type",
	"batch_based_inventory",
	"expiration_date",
	"supplier_name",
	"pricing",
	"related_dishes",
	"picture_of_items",
	"number_of_packages",
]

TRANSACTION_FIELDNAMES = [
	"action_id",
	"item_id",
	"action_type",
	"action_detail",
	"date_of_action",
	"comments",
]


class InventoryRepository:
	def __init__(self, items_path: Path, transactions_path: Path):
		self.items_path = Path(items_path)
		self.transactions_path = Path(transactions_path)

	def list_items(self) -> list[InventoryItem]:
		return [self._parse_item(row) for row in self._read_csv(self.items_path)]

	def list_transactions(self) -> list[TransactionRecord]:
		return [
			self._parse_transaction(row)
			for row in self._read_csv(self.transactions_path)
		]

	def get_item(self, item_id: int) -> InventoryItem | None:
		for item in self.list_items():
			if item.item_id == item_id:
				return item
		return None

	def find_item_by_name(self, item_name: str) -> InventoryItem | None:
		normalized_name = item_name.strip().casefold()
		for item in self.list_items():
			if item.item_name.casefold() == normalized_name:
				return item
		return None

	def create_item(self, payload: InventoryCreate) -> InventoryItem:
		item = InventoryItem(item_id=self._next_item_id(), **payload.model_dump())
		rows = self._read_csv(self.items_path)
		rows.append(self._serialize_item(item))
		self._write_csv(self.items_path, ITEM_FIELDNAMES, rows)
		return item

	def update_item(self, item_id: int, payload: InventoryUpdate) -> InventoryItem | None:
		rows = self._read_csv(self.items_path)
		updated_item: InventoryItem | None = None

		for index, row in enumerate(rows):
			if int(row["item_id"]) != item_id:
				continue

			current_item = self._parse_item(row)
			merged = current_item.model_dump()
			merged.update(payload.model_dump(exclude_none=True))
			updated_item = InventoryItem.model_validate(merged)
			rows[index] = self._serialize_item(updated_item)
			break

		if updated_item is None:
			return None

		self._write_csv(self.items_path, ITEM_FIELDNAMES, rows)
		return updated_item

	def delete_item(self, item_id: int) -> bool:
		rows = self._read_csv(self.items_path)
		filtered_rows = [row for row in rows if int(row["item_id"]) != item_id]
		if len(filtered_rows) == len(rows):
			return False
		self._write_csv(self.items_path, ITEM_FIELDNAMES, filtered_rows)
		return True

	def append_transaction(
		self,
		*,
		item_id: int,
		action_type: str,
		action_detail: str,
		comments: str | None,
	) -> TransactionRecord:
		transaction = TransactionRecord(
			action_id=self._next_action_id(),
			item_id=item_id,
			action_type=action_type,
			action_detail=action_detail,
			date_of_action=datetime.now(UTC),
			comments=comments,
		)
		rows = self._read_csv(self.transactions_path)
		rows.append(self._serialize_transaction(transaction))
		self._write_csv(self.transactions_path, TRANSACTION_FIELDNAMES, rows)
		return transaction

	def _next_item_id(self) -> int:
		rows = self._read_csv(self.items_path)
		if not rows:
			return 1
		return max(int(row["item_id"]) for row in rows) + 1

	def _next_action_id(self) -> int:
		rows = self._read_csv(self.transactions_path)
		if not rows:
			return 1
		return max(int(row["action_id"]) for row in rows) + 1

	def _read_csv(self, path: Path) -> list[dict[str, str]]:
		if not path.exists():
			return []
		with path.open("r", newline="", encoding="utf-8") as csv_file:
			return list(csv.DictReader(csv_file))

	def _write_csv(
		self,
		path: Path,
		fieldnames: list[str],
		rows: list[dict[str, str]],
	) -> None:
		path.parent.mkdir(parents=True, exist_ok=True)
		with path.open("w", newline="", encoding="utf-8") as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
			writer.writeheader()
			writer.writerows(rows)

	def _parse_item(self, row: dict[str, str]) -> InventoryItem:
		raw_packages = row.get("number_of_packages")
		raw_pricing = row.get("pricing")
		return InventoryItem(
			item_id=int(row["item_id"]),
			item_name=row["item_name"],
			storage_type=row["storage_type"],
			shelf_life_type=row["shelf_life_type"],
			package_type=row["package_type"],
			quantity=float(row["quantity"]) if row.get("quantity") else 0.0,
			quantity_type=row["quantity_type"],
			batch_based_inventory=row["batch_based_inventory"],
			expiration_date=row["expiration_date"],
			supplier_name=row["supplier_name"],
			pricing=float(raw_pricing) if raw_pricing else 0.0,
			related_dishes=row.get("related_dishes") or None,
			picture_of_items=row.get("picture_of_items") or None,
			number_of_packages=int(raw_packages) if raw_packages else None,
		)

	def _serialize_item(self, item: InventoryItem) -> dict[str, str]:
		return {
			"item_id": str(item.item_id),
			"item_name": item.item_name,
			"storage_type": item.storage_type,
			"shelf_life_type": item.shelf_life_type,
			"package_type": item.package_type,
			"quantity": str(item.quantity),
			"quantity_type": item.quantity_type,
			"batch_based_inventory": item.batch_based_inventory,
			"expiration_date": item.expiration_date.isoformat(),
			"supplier_name": item.supplier_name,
			"pricing": str(item.pricing),
			"related_dishes": item.related_dishes or "",
			"picture_of_items": item.picture_of_items or "",
			"number_of_packages": str(item.number_of_packages) if item.number_of_packages is not None else "",
		}

	def _parse_transaction(self, row: dict[str, str]) -> TransactionRecord:
		return TransactionRecord(
			action_id=int(row["action_id"]),
			item_id=int(row["item_id"]),
			action_type=row["action_type"],
			action_detail=row["action_detail"],
			date_of_action=row["date_of_action"],
			comments=row.get("comments") or None,
		)

	def _serialize_transaction(self, transaction: TransactionRecord) -> dict[str, str]:
		return {
			"action_id": str(transaction.action_id),
			"item_id": str(transaction.item_id),
			"action_type": transaction.action_type,
			"action_detail": transaction.action_detail,
			"date_of_action": transaction.date_of_action.isoformat(sep=" ", timespec="seconds"),
			"comments": transaction.comments or "",
		}
