from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class InventoryBase(BaseModel):
	item_name: str
	storage_type: str
	shelf_life_type: str
	package_type: str
	quantity: float
	quantity_unit: str
	batch_number: str
	expiration_date: date
	supplier_name: str
	price_per_unit: float
	reorder_threshold: float
	related_dishes: str | None = None
	picture_url: str | None = None

	@field_validator(
		"item_name",
		"storage_type",
		"shelf_life_type",
		"package_type",
		"quantity_unit",
		"batch_number",
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

	@field_validator("related_dishes", "picture_url", mode="before")
	@classmethod
	def normalize_optional_strings(cls, value: str | None) -> str | None:
		if value is None:
			return None
		stripped = value.strip()
		return stripped or None

	@field_validator("quantity", "price_per_unit", "reorder_threshold")
	@classmethod
	def validate_non_negative_numbers(cls, value: float) -> float:
		if value < 0:
			raise ValueError("Numeric fields cannot be negative.")
		return value


class InventoryCreate(InventoryBase):
	pass


class InventoryUpdate(BaseModel):
	item_name: str | None = None
	storage_type: str | None = None
	shelf_life_type: str | None = None
	package_type: str | None = None
	quantity: float | None = None
	quantity_unit: str | None = None
	batch_number: str | None = None
	expiration_date: date | None = None
	supplier_name: str | None = None
	price_per_unit: float | None = None
	reorder_threshold: float | None = None
	related_dishes: str | None = None
	picture_url: str | None = None

	model_config = ConfigDict(extra="forbid")

	@field_validator(
		"item_name",
		"storage_type",
		"shelf_life_type",
		"package_type",
		"quantity_unit",
		"batch_number",
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

	@field_validator("related_dishes", "picture_url", mode="before")
	@classmethod
	def normalize_optional_update_strings(cls, value: str | None) -> str | None:
		if value is None:
			return None
		stripped = value.strip()
		return stripped or None

	@field_validator("quantity", "price_per_unit", "reorder_threshold")
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
	quantity_changed: float
	date_of_action: datetime
	staff_name: str
	comments: str | None = None


class InventoryOverview(BaseModel):
	items: list[InventoryItem]
	transactions: list[TransactionRecord]


class InventoryUpsertResponse(BaseModel):
	operation: str
	item: InventoryItem