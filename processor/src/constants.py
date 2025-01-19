from typing import Dict
import os

# File paths and directories
PREFIX = "/mnt/c/Users/David/Downloads/output"
DEFAULT_OUTPUT_DIR = "statement_sections"

# File patterns and formats
DATE_FORMATS = [
    '%Y-%m-%d',          # 2024-01-30
    '%Y-%m-%d %H:%M:%S', # 2024-01-30 15:30:00
    '%d%b%y',            # 30JAN24
    '%m/%d/%Y'           # 01/30/2024
]

# Asset categories mapping
ASSET_CATEGORY_REPLACE: Dict[str, str] = {
    "Stocks": "stocks",
    "Equity and Index Options": "options"
}

# DataFrame keys and columns
MTM_SUMMARY_KEY = "Mark-to-Market Performance Summary"
TRADES_KEY = "Trades"

# Default values
DEFAULT_EXPIRY_DATE = "9999-01-01"
DEFAULT_STRIKE = 0
DEFAULT_CONTRACT_TYPE = "C"

# Column names
SYMBOL_COL = "symbol"
CURRENCY_COL = "currency"
ASSET_CATEGORY_COL = "asset_category"
PK_COL = "pk"
DATA_DATE_PART_COL = "data_date_part"

# Asset type values
STOCKS_TYPE = "stocks"
OPTIONS_TYPE = "options"
FOREX_TYPE = "forex"

# DataFrame export mapping
DF_EXPORT_MAPPING = {
    "stocks": STOCKS_TYPE,
    "options": OPTIONS_TYPE,
    "options_trades": "options_trades",
    "stock_traces": "stock_traces",
    "total_proceeds": "total_proceeds",
    "forex": FOREX_TYPE
}

# Master dates filename
MASTER_DATES_FILE = "master_dates.csv"

# Options contract multiplier
OPTIONS_CONTRACT_MULTIPLIER = 100

DB_PATH = os.getenv('DB_PATH', '/app/db/statements.db')