"""
Interactive Brokers statement processor module.
This module handles the processing of IB statements and exports the processed data.
"""

from datetime import datetime
import pandas as pd

from constants import (
    MTM_SUMMARY_KEY,
    TRADES_KEY,
    ASSET_CATEGORY_COL,
    SYMBOL_COL,
    CURRENCY_COL,
    PK_COL,
    DATA_DATE_PART_COL,
    DEFAULT_EXPIRY_DATE,
    DEFAULT_STRIKE,
    DEFAULT_CONTRACT_TYPE,
    OPTIONS_CONTRACT_MULTIPLIER,
    DF_EXPORT_MAPPING,
    CAP_HEADER,
    OPTION_TRADES,
    STOCK_TRADES,
    PRIOR_PRICE_COL,
    CURRENT_PRICE_COL,
    CURRENT_QUANTITY_COL,
    PRIOR_QUANTITY_COL,
    PL_DELTA_COL,
    STOCKS_TYPE,
    FOREX_TYPE,
    OPTIONS_TYPE,
    TOTAL_PROCEEDS,
    DB_PATH,
    MASTER_DATES_TABLE,
    METRICS,
)

from utils.file_operations import split_ib_statement, validate_input_file
from utils.df_operations import (
    clean_column_names,
    post_process_df,
    parse_option_symbol,
    auto_convert_types,
    create_base_tables,
)
from utils.db_operations import DatabaseManager


class IBStatementProcessor:
    def __init__(self, input_file: str):
        """Initialize the processor with input file."""
        self.input_file = input_file
        self.input_date = validate_input_file(input_file)
        self.part_date = datetime.strptime(self.input_date, "%Y%m%d").isoformat()[:10]
        self.dataframes = {}
        self.processed_data = {}

    def process(self) -> None:
        """Main processing method."""
        self.dataframes = split_ib_statement(self.input_file)
        self._process_mtm_summary()
        if TRADES_KEY in self.dataframes:
            self._process_trades()
        else:
            self._initialize_empty_trades()
        self._calculate_metrics()
        self._prepare_export_data()

    def _process_mtm_summary(self) -> None:
        """Process Mark-to-Market summary data."""
        df_base_daily = self.dataframes[MTM_SUMMARY_KEY]
        df_base_daily = (
            df_base_daily.pipe(post_process_df)
            .drop(CAP_HEADER, axis=1)
            .pipe(clean_column_names)
        )
        df_stocks, df_options, df_forex = create_base_tables(df_base_daily)
        if df_options is not None:
            df_options = parse_option_symbol(df=df_options)

        if df_forex is not None:
            df_forex = df_forex.rename(
                columns={SYMBOL_COL: CURRENCY_COL, PRIOR_PRICE_COL: "exchange_rate_eur"}
            )[
                [
                    ASSET_CATEGORY_COL,
                    CURRENCY_COL,
                    PRIOR_QUANTITY_COL,
                    CURRENT_QUANTITY_COL,
                    "exchange_rate_eur",
                    PL_DELTA_COL,
                ]
            ]

        self.processed_data.update(
            {STOCKS_TYPE: df_stocks, OPTIONS_TYPE: df_options, FOREX_TYPE: df_forex}
        )

    def _process_trades(self) -> None:
        """Process trades data."""
        df_base_trades = self.dataframes[TRADES_KEY]

        # Separate and process trades
        stock_trades, options_trades = self._separate_trades(df_base_trades)

        # Process options trades
        op_trades_agg = (
            options_trades.pipe(auto_convert_types)
            .groupby(SYMBOL_COL)
            .agg(
                currency=(CURRENCY_COL, "first"),
                total_quantity=("quantity", "sum"),
                total_proceeds=("proceeds", "sum"),
            )
            .reset_index()
            .pipe(parse_option_symbol)
        )

        # Process stock trades
        stock_trades_agg = (
            stock_trades.pipe(auto_convert_types)
            .groupby(SYMBOL_COL)
            .agg(
                currency=(CURRENCY_COL, "first"),
                total_quantity=("quantity", "sum"),
                total_proceeds=("proceeds", "sum"),
            )
            .reset_index()
        )
        stock_proceeds = stock_trades_agg.assign(
            underlying=lambda x: x[SYMBOL_COL],
            exp_date=DEFAULT_EXPIRY_DATE,
            strike=DEFAULT_STRIKE,
            contract_type=DEFAULT_CONTRACT_TYPE,
            asset_category=STOCKS_TYPE,
        )

        options_proceeds = op_trades_agg.assign(asset_category=OPTIONS_TYPE)
        df_total_proceeds = pd.concat([stock_proceeds, options_proceeds])

        self.processed_data.update(
            {
                OPTION_TRADES: op_trades_agg,
                STOCK_TRADES: stock_trades_agg,
                TOTAL_PROCEEDS: df_total_proceeds,
            }
        )

    def _initialize_empty_trades(self) -> None:
        """Initialize empty DataFrames when no trades are present."""
        self.processed_data.update(
            {
                OPTION_TRADES: pd.DataFrame(),
                STOCK_TRADES: pd.DataFrame(),
                TOTAL_PROCEEDS: pd.DataFrame(),
            }
        )

    def _calculate_metrics(self) -> None:
        """Calculate various portfolio metrics."""
        df_stocks = self.processed_data[STOCKS_TYPE]
        df_options = self.processed_data[OPTIONS_TYPE]
        df_forex = self.processed_data[FOREX_TYPE]

        stock_value = (
            df_stocks[CURRENT_QUANTITY_COL] * df_stocks[CURRENT_PRICE_COL]
        ).sum()
        option_value = (
            df_options[CURRENT_QUANTITY_COL] * df_options[CURRENT_PRICE_COL]
        ).sum() * OPTIONS_CONTRACT_MULTIPLIER

        metric_gross_val = stock_value + option_value
        metric_nav = metric_gross_val + df_forex[CURRENT_QUANTITY_COL].sum()
        option_credit = (
            (
                df_options[df_options[CURRENT_QUANTITY_COL] < 0][CURRENT_QUANTITY_COL]
                * df_options[df_options[CURRENT_QUANTITY_COL] < 0][CURRENT_PRICE_COL]
            ).sum()
            * OPTIONS_CONTRACT_MULTIPLIER
        ).round(2)

        option_debit = (
            (
                df_options[df_options[CURRENT_QUANTITY_COL] > 0][CURRENT_QUANTITY_COL]
                * df_options[df_options[CURRENT_QUANTITY_COL] > 0][CURRENT_PRICE_COL]
            ).sum()
            * OPTIONS_CONTRACT_MULTIPLIER
        ).round(2)

        self.metrics = {
            "gross_value": metric_gross_val,
            "nav": metric_nav,
            "option_credit": option_credit,
            "option_debit": option_debit,
            "option_balance": option_debit + option_credit,
        }

    def _prepare_export_data(self) -> None:
        """Prepare data for export."""
        self.export_data = {
            key: df.copy()
            for key, df in self.processed_data.items()
            if key in DF_EXPORT_MAPPING
        }

        for key, df in self.export_data.items():
            if not df.empty:
                key_column = SYMBOL_COL if SYMBOL_COL in df.columns else CURRENCY_COL
                df[PK_COL] = df[key_column] + "_" + self.input_date
                df[DATA_DATE_PART_COL] = self.part_date

    def export(self) -> None:
        """Export processed data to SQLite database."""
        db_manager = DatabaseManager(DB_PATH)
        for key, df in self.export_data.items():
            if not df.empty:
                if DATA_DATE_PART_COL in df.columns:
                    df[DATA_DATE_PART_COL] = pd.to_datetime(df[DATA_DATE_PART_COL])

                db_manager.dataframe_to_sql(df, key)

        df_date = pd.DataFrame([[self.part_date]], columns=[DATA_DATE_PART_COL])
        db_manager.dataframe_to_sql(df_date, MASTER_DATES_TABLE)


def process_statement(input_file: str) -> IBStatementProcessor:
    """
    Main function to process an IB statement file.

    Args:
        input_file: Path to the input CSV file

    Returns:
        IBStatementProcessor: Processor instance with processed data
    """
    processor = IBStatementProcessor(input_file)
    processor.process()
    processor.export()
    return processor
