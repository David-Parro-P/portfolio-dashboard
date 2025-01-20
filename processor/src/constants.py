from typing import Dict, Final
import os

# MAster date table
MASTER_DATES_TABLE: Final = "master_dates"
METRICS: Final = "metrics"
# Input N8N request body fields
CSV_CONTENT: Final = "csv_content"
SUBJECT: Final = "subject"

# File paths and directories
DEFAULT_OUTPUT_DIR: Final = "statement_sections"


# Asset type values
STOCKS_TYPE: Final = "stocks"
OPTIONS_TYPE: Final = "options"
FOREX_TYPE: Final = "forex"
OPTION_TRADES: Final = "option_trades"
STOCK_TRADES: Final = "stock_trades"
TOTAL_PROCEEDS: Final = "total_proceeds"
# Asset categories
CAP_HEADER: Final = "Header"
CAP_FOREX: Final = "Forex"
CAP_STOCK: Final = "Stocks"
CAP_OPTIONS: Final = "Equity and Index Options"
# File patterns and formats
DATE_FORMATS: Final = [
    "%Y-%m-%d",  # 2024-01-30
    "%Y-%m-%d %H:%M:%S",  # 2024-01-30 15:30:00
    "%d%b%y",  # 30JAN24
    "%m/%d/%Y",  # 01/30/2024
]

# Asset categories mapping
ASSET_CATEGORY_REPLACE: Dict[str, str] = {
    CAP_STOCK: STOCKS_TYPE,
    CAP_OPTIONS: OPTIONS_TYPE,
}

# DataFrame keys and columns
MTM_SUMMARY_KEY: Final = "Mark-to-Market Performance Summary"
TRADES_KEY: Final = "Trades"

# Default values
DEFAULT_EXPIRY_DATE: Final = "9999-01-01"
DEFAULT_STRIKE: Final = 0
DEFAULT_CONTRACT_TYPE: Final = "C"

# Column names
SYMBOL_COL: Final = "symbol"
CURRENCY_COL: Final = "currency"
ASSET_CATEGORY_COL: Final = "asset_category"
PK_COL: Final = "pk"
DATA_DATE_PART_COL: Final = "data_date_part"
PRIOR_QUANTITY_COL: Final = "prior_quantity"
CURRENT_QUANTITY_COL: Final = "current_quantity"
PRIOR_PRICE_COL: Final = "prior_price"
CURRENT_PRICE_COL: Final = "current_price"
MARKET_PL_POS: Final = "mark-to-market_p/l_position"
MARKET_PL_TRANS: Final = "mark-to-market_p/l_transaction"
IS_NEW_COL: Final = "is_new"
PL_DELTA_COL: Final = "pl_delta"


# DataFrame export mapping
DF_EXPORT_MAPPING: Dict[str, str] = {
    STOCKS_TYPE: STOCKS_TYPE,
    OPTIONS_TYPE: OPTIONS_TYPE,
    OPTION_TRADES: OPTION_TRADES,
    STOCK_TRADES: STOCK_TRADES,
    TOTAL_PROCEEDS: TOTAL_PROCEEDS,
    FOREX_TYPE: FOREX_TYPE,
}

# Options contract multiplier
OPTIONS_CONTRACT_MULTIPLIER: Final = 100

DB_PATH = os.getenv("DB_PATH", "/app/db/statements.db")
