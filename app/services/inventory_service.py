from app.models.inventory import (
	InventoryCreate,
	InventoryItem,
	InventoryOverview,
	InventoryUpdate,
	InventoryUpsertResponse,
)
from app.repositories.inventory_repo import InventoryRepository


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