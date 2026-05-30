from collections import defaultdict
from datetime import datetime, timedelta

from app.models.inventory import (
	InventoryCreate,
	InventoryItem,
	InventoryOverview,
	InventoryUpdate,
	InventoryUpsertResponse,
	RestockSuggestion,
	RestockSuggestionsResponse,
)
from app.repositories.inventory_repo import InventoryRepository

# Keyed by shelf_life_type.
# expiry_days: flag the item when it expires within this many days.
# packages: flag the item when number_of_packages is at or below this threshold.
_SHELF_LIFE_CONFIG: dict[str, dict[str, int]] = {
	"short_term":  {"expiry_days": 3,  "packages": 3},
	"medium_term": {"expiry_days": 7,  "packages": 5},
	"long_term":   {"expiry_days": 14, "packages": 2},
}
_DEFAULT_SHELF_LIFE_CONFIG: dict[str, int] = {"expiry_days": 7, "packages": 3}
_OBSERVATION_DAYS = 30


class ItemNotFoundError(Exception):
	pass


class InventoryService:
	def __init__(self, repository: InventoryRepository):
		self.repository = repository

	def get_inventory_overview(self) -> InventoryOverview:
		return InventoryOverview(
			items=self.repository.list_items(),
			transactions=self.repository.list_transactions(),
		)

	def add_or_create_item(self, payload: InventoryCreate) -> InventoryUpsertResponse:
		existing_item = self.repository.find_item_by_name(payload.item_name)
		if existing_item is None:
			created_item = self.repository.create_item(payload)
			self.repository.append_transaction(
				item_id=created_item.item_id,
				action_type="add",
				action_detail="create",
				comments="Created new inventory item.",
			)
			return InventoryUpsertResponse(operation="created", item=created_item)

		incoming_packages = payload.number_of_packages
		if not incoming_packages:
			raise ValueError("number_of_packages is required to restock an existing item.")

		new_packages = (existing_item.number_of_packages or 0) + incoming_packages

		updated_item = self.repository.update_item(
			existing_item.item_id,
			InventoryUpdate(number_of_packages=new_packages),
		)
		if updated_item is None:
			raise ItemNotFoundError(f"Item {existing_item.item_id} was not found.")

		self.repository.append_transaction(
			item_id=updated_item.item_id,
			action_type="add",
			action_detail="restock",
			comments=f"Added {incoming_packages} package(s). New total: {new_packages}.",
		)
		return InventoryUpsertResponse(operation="updated", item=updated_item)

	def get_item(self, item_id: int) -> InventoryItem:
		item = self.repository.get_item(item_id)
		if item is None:
			raise ItemNotFoundError(f"Item {item_id} was not found.")
		return item

	def get_item_transactions(self, item_id: int) -> list:
		all_transactions = self.repository.list_transactions()
		return sorted(
			[t for t in all_transactions if t.item_id == item_id],
			key=lambda t: t.date_of_action,
			reverse=True,
		)

	def update_item(self, item_id: int, payload: InventoryUpdate) -> InventoryItem:
		updated_item = self.repository.update_item(item_id, payload)
		if updated_item is None:
			raise ItemNotFoundError(f"Item {item_id} was not found.")
		return updated_item

	def delete_item(self, item_id: int) -> None:
		deleted = self.repository.delete_item(item_id)
		if not deleted:
			raise ItemNotFoundError(f"Item {item_id} was not found.")

	def get_restock_suggestions(self) -> RestockSuggestionsResponse:
		from datetime import date

		today = date.today()
		cutoff = datetime.now() - timedelta(days=_OBSERVATION_DAYS)

		items = self.repository.list_items()
		transactions = self.repository.list_transactions()

		# Count withdrawal events per item within the observation window.
		withdrawal_counts: dict[int, int] = defaultdict(int)
		for t in transactions:
			if t.action_type != "withdraw":
				continue
			# Strip timezone so naive and aware datetimes compare cleanly.
			if t.date_of_action.replace(tzinfo=None) >= cutoff:
				withdrawal_counts[t.item_id] += 1

		suggestions: list[RestockSuggestion] = []
		for item in items:
			config = _SHELF_LIFE_CONFIG.get(item.shelf_life_type, _DEFAULT_SHELF_LIFE_CONFIG)
			expiry_threshold = config["expiry_days"]
			packages_threshold = config["packages"]

			days_to_expiry = (item.expiration_date - today).days
			usage_count = withdrawal_counts[item.item_id]

			pkgs = item.number_of_packages
			is_low_stock = (
				pkgs is not None and pkgs <= packages_threshold
			) or (
				pkgs is None
				and item.quantity_per_package > 0
				and item.quantity <= packages_threshold * item.quantity_per_package
			)
			is_expiring = days_to_expiry <= expiry_threshold

			stock_label = f"{pkgs} package(s)" if pkgs is not None else f"{item.quantity} {item.quantity_type}"

			if is_expiring and is_low_stock:
				urgency = "critical"
				reason = (
					f"Only {stock_label} remaining and expires in {days_to_expiry} day(s). "
					f"Withdrawn {usage_count} time(s) in the last {_OBSERVATION_DAYS} days."
				)
			elif is_expiring:
				urgency = "expiring_soon"
				reason = (
					f"Expires in {days_to_expiry} day(s) (threshold: {expiry_threshold} for {item.shelf_life_type}). "
					f"Currently has {stock_label}. "
					f"Withdrawn {usage_count} time(s) in the last {_OBSERVATION_DAYS} days."
				)
			elif is_low_stock:
				urgency = "low_stock"
				reason = (
					f"Only {stock_label} remaining (threshold: {packages_threshold} for {item.shelf_life_type}). "
					f"Expires in {days_to_expiry} day(s). "
					f"Withdrawn {usage_count} time(s) in the last {_OBSERVATION_DAYS} days."
				)
			else:
				urgency = "ok"
				reason = (
					f"Stock is adequate ({stock_label}, expires in {days_to_expiry} day(s))."
				)

			suggestions.append(RestockSuggestion(
				item_id=item.item_id,
				item_name=item.item_name,
				current_quantity=item.quantity,
				quantity_type=item.quantity_type,
				number_of_packages=item.number_of_packages,
				usage_count_30d=usage_count,
				days_to_expiry=days_to_expiry,
				urgency=urgency,
				reason=reason,
			))

		_urgency_rank = {"critical": 0, "expiring_soon": 1, "low_stock": 2, "ok": 3}
		suggestions.sort(key=lambda s: _urgency_rank[s.urgency])
		return RestockSuggestionsResponse(generated_at=today, suggestions=suggestions)