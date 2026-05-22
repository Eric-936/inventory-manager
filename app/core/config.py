from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

APP_NAME = "inventory-manager"
ITEMS_CSV_PATH = DATA_DIR / "items_table.csv"
TRANSACTIONS_CSV_PATH = DATA_DIR / "transactions_table.csv"