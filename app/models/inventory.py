from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class InventoryBase(BaseModel):
	item_name: str
	storage_type: str
	shelf_life_type: str
	package_type: str
	quantity_type: str
	quantity_per_package: float              # required; drives the quantity calculation
	batch_based_inventory: str
	expiration_date: date
	supplier_name: str
	pricing: float
	related_dishes: str | None = None
	picture_of_items: str | None = None
	number_of_packages: int | None = None
	quantity: float | None = None            # computed: number_of_packages × quantity_per_package

	@field_validator(
		"item_name",
		"storage_type",
		"shelf_life_type",
		"package_type",
		"quantity_type",
		"batch_based_inventory",
		"supplier_name",
		mode="before",
	)
	@classmethod
	def validate_required_strings(cls, value: str) -> str:
		if value is None:
			raise ValueError("Field is required.")
		stripped = value.strip()
		if not stripped:
			raise ValueError("Field cannot be empty.")
		return stripped

	@field_validator("related_dishes", "picture_of_items", mode="before")
	@classmethod
	def normalize_optional_strings(cls, value: str | None) -> str | None:
		if value is None:
			return None
		stripped = value.strip()
		return stripped or None

	@field_validator("quantity", "quantity_per_package", "pricing")
	@classmethod
	def validate_non_negative_numbers(cls, value: float | None) -> float | None:
		if value is not None and value < 0:
			raise ValueError("Numeric fields cannot be negative.")
		return value

	@model_validator(mode="after")
	def compute_quantity(self) -> "InventoryBase":
		if self.quantity is None:
			if self.number_of_packages is None:
				raise ValueError(
					"Provide quantity directly, or set both number_of_packages "
					"and quantity_per_package so it can be calculated automatically."
				)
			self.quantity = self.number_of_packages * self.quantity_per_package
		return self


class InventoryCreate(InventoryBase):
	pass


class InventoryUpdate(BaseModel):
	item_name: str | None = None
	storage_type: str | None = None
	shelf_life_type: str | None = None
	package_type: str | None = None
	quantity: float | None = None
	quantity_type: str | None = None
	quantity_per_package: float | None = None
	batch_based_inventory: str | None = None
	expiration_date: date | None = None
	supplier_name: str | None = None
	pricing: float | None = None
	related_dishes: str | None = None
	picture_of_items: str | None = None
	number_of_packages: int | None = None

	model_config = ConfigDict(extra="forbid")

	@field_validator(
		"item_name",
		"storage_type",
		"shelf_life_type",
		"package_type",
		"quantity_type",
		"batch_based_inventory",
		"supplier_name",
		mode="before",
	)
	@classmethod
	def validate_optional_required_strings(cls, value: str | None) -> str | None:
		if value is None:
			return None
		stripped = value.strip()
		if not stripped:
			raise ValueError("Field cannot be empty.")
		return stripped

	@field_validator("related_dishes", "picture_of_items", mode="before")
	@classmethod
	def normalize_optional_update_strings(cls, value: str | None) -> str | None:
		if value is None:
			return None
		stripped = value.strip()
		return stripped or None

	@field_validator("quantity", "quantity_per_package", "pricing")
	@classmethod
	def validate_optional_numbers(cls, value: float | None) -> float | None:
		if value is not None and value < 0:
			raise ValueError("Numeric fields cannot be negative.")
		return value


class InventoryItem(InventoryBase):
	item_id: int

	model_config = ConfigDict(from_attributes=True)


class TransactionRecord(BaseModel):
	action_id: int
	item_id: int
	action_type: str
	action_detail: str
	date_of_action: datetime
	comments: str | None = None


class InventoryOverview(BaseModel):
	items: list[InventoryItem]
	transactions: list[TransactionRecord]


class InventoryUpsertResponse(BaseModel):
	operation: str
	item: InventoryItem


class RestockSuggestion(BaseModel):
	item_id: int
	item_name: str
	current_quantity: float
	quantity_type: str
	number_of_packages: int | None
	usage_count_30d: int
	days_to_expiry: int
	urgency: Literal["critical", "expiring_soon", "low_stock", "ok"]
	reason: str


class RestockSuggestionsResponse(BaseModel):
	generated_at: date
	suggestions: list[RestockSuggestion]
