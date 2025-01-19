"""
Interactive Brokers statement processor module.
This module handles the processing of IB statements and exports the processed data.
"""
import os
from datetime import datetime
import pandas as pd
from typing import Dict, Tuple

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
    ASSET_CATEGORY_REPLACE
)
from utils.file_operations import split_ib_statement, validate_input_file
from utils.df_operations import (
    clean_column_names,
    post_process_df,
    parse_option_symbol,
    auto_convert_types,
    create_base_tables
)
from utils.db_operations import DatabaseManager

class IBStatementProcessor:
    def __init__(self, input_file: str):
        """Initialize the processor with input file."""
        self.input_file = input_file
        self.input_date = validate_input_file(input_file)
        self.part_date = datetime.strptime(self.input_date, '%Y%m%d').isoformat()[:10]
        self.dataframes = {}
        self.processed_data = {}
        
    def process(self) -> None:
        """Main processing method."""
        # Split and load statement sections
        self.dataframes = split_ib_statement(self.input_file)
        
        # Process MTM summary
        self._process_mtm_summary()
        
        # Process trades if available
        if TRADES_KEY in self.dataframes:
            self._process_trades()
        else:
            self._initialize_empty_trades()
        
        # Calculate metrics
        self._calculate_metrics()
        
        # Prepare data for export
        self._prepare_export_data()
        
    def _process_mtm_summary(self) -> None:
        """Process Mark-to-Market summary data."""
        df_base_daily = self.dataframes[MTM_SUMMARY_KEY]
        df_base_daily = (
            df_base_daily.pipe(post_process_df)
            .drop("Header", axis=1)
            .pipe(clean_column_names)
        )
        
        # Create base tables
        df_stocks, df_options, df_forex = create_base_tables(df_base_daily)
        
        # Process options
        if df_options is not None:
            df_options = parse_option_symbol(df=df_options)
            
        # Process forex
        if df_forex is not None:
            df_forex = (
                df_forex.rename(columns={"symbol": "currency", "prior_price": "exchange_rate_eur"})
                [['asset_category', 'currency', 'prior_quantity', 'current_quantity', 
                  'exchange_rate_eur', 'pl_delta']]
            )
        
        self.processed_data.update({
            'stocks': df_stocks,
            'options': df_options,
            'forex': df_forex
        })
    
    def _process_trades(self) -> None:
        """Process trades data."""
        df_base_trades = self.dataframes[TRADES_KEY]
        
        # Separate and process trades
        stock_trades, options_trades = self._separate_trades(df_base_trades)
        
        # Process options trades
        op_trades_agg = (
            options_trades
            .pipe(auto_convert_types)
            .groupby(SYMBOL_COL)
            .agg(
                currency=(CURRENCY_COL, 'first'),
                total_quantity=('quantity', 'sum'),
                total_proceeds=('proceeds', 'sum')
            )
            .reset_index()
            .pipe(parse_option_symbol)
        )
        
        # Process stock trades
        stock_trades_agg = (
            stock_trades
            .pipe(auto_convert_types)
            .groupby(SYMBOL_COL)
            .agg(
                currency=(CURRENCY_COL, 'first'),
                total_quantity=('quantity', 'sum'),
                total_proceeds=('proceeds', 'sum')
            )
            .reset_index()
        )
        
        # Create proceeds DataFrames
        stock_proceeds = stock_trades_agg.assign(
            underlying=lambda x: x[SYMBOL_COL],
            exp_date=DEFAULT_EXPIRY_DATE,
            strike=DEFAULT_STRIKE,
            contract_type=DEFAULT_CONTRACT_TYPE,
            asset_category="stocks"
        )
        
        options_proceeds = op_trades_agg.assign(asset_category="options")
        df_total_proceeds = pd.concat([stock_proceeds, options_proceeds])
        
        self.processed_data.update({
            'options_trades': op_trades_agg,
            'stock_trades': stock_trades_agg,
            'total_proceeds': df_total_proceeds
        })
    
    def _separate_trades(self, trades_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Separate trades into stocks and options."""
        trades_df = (
            trades_df
            .pipe(clean_column_names)
            .assign(
                asset_category=lambda df: (
                    df[ASSET_CATEGORY_COL].replace(ASSET_CATEGORY_REPLACE)
                )
            )
            .loc[lambda df: df['header'] == 'Data']
        )
        
        stock_trades = trades_df[trades_df[ASSET_CATEGORY_COL] == "stocks"]
        options_trades = trades_df[trades_df[ASSET_CATEGORY_COL] == "options"]
        options_trades = parse_option_symbol(options_trades)
        
        return stock_trades, options_trades
    
    def _initialize_empty_trades(self) -> None:
        """Initialize empty DataFrames when no trades are present."""
        self.processed_data.update({
            'options_trades': pd.DataFrame(),
            'stock_trades': pd.DataFrame(),
            'total_proceeds': pd.DataFrame()
        })
    
    def _calculate_metrics(self) -> None:
        """Calculate various portfolio metrics."""
        df_stocks = self.processed_data['stocks']
        df_options = self.processed_data['options']
        df_forex = self.processed_data['forex']
        
        # Calculate gross value
        stock_value = (df_stocks['current_quantity'] * df_stocks['current_price']).sum()
        option_value = ((df_options['current_quantity'] * 
                        df_options['current_price']).sum() * OPTIONS_CONTRACT_MULTIPLIER)
        metric_gross_val = stock_value + option_value
        
        # Calculate NAV
        metric_nav = metric_gross_val + df_forex['current_quantity'].sum()
        
        # Calculate option metrics
        option_credit = ((df_options[df_options['current_quantity'] < 0]['current_quantity'] * 
                         df_options[df_options['current_quantity'] < 0]['current_price']).sum() * 
                        OPTIONS_CONTRACT_MULTIPLIER).round(2)
        
        option_debit = ((df_options[df_options['current_quantity'] > 0]['current_quantity'] * 
                        df_options[df_options['current_quantity'] > 0]['current_price']).sum() * 
                       OPTIONS_CONTRACT_MULTIPLIER).round(2)
        
        self.metrics = {
            'gross_value': metric_gross_val,
            'nav': metric_nav,
            'option_credit': option_credit,
            'option_debit': option_debit,
            'option_balance': option_debit + option_credit
        }
    
    def _prepare_export_data(self) -> None:
        """Prepare data for export."""
        self.export_data = {
            key: df.copy() for key, df in self.processed_data.items() 
            if key in DF_EXPORT_MAPPING
        }
        
        # Add metadata columns
        for key, df in self.export_data.items():
            if not df.empty:
                key_column = SYMBOL_COL if SYMBOL_COL in df.columns else CURRENCY_COL
                df[PK_COL] = df[key_column] + "_" + self.input_date
                df[DATA_DATE_PART_COL] = self.part_date
    
    def export(self) -> None:
        """Export processed data to SQLite database."""
        
        
        # Initialize database connection
        db_manager = DatabaseManager(os.getenv('DB_PATH', '/app/db/statements.db'))
        
        # Export main dataframes
        for key, df in self.export_data.items():
            if not df.empty:
                # Convert DataFrame column types appropriately if needed
                # Ensure date columns are in correct format
                if 'data_date' in df.columns:
                    df['data_date'] = pd.to_datetime(df['data_date'])
                
                # Export to SQLite
                db_manager.dataframe_to_sql(df, key)
        
        # Export master dates
        df_date = pd.DataFrame([[self.part_date]], columns=[DATA_DATE_PART_COL])
        db_manager.dataframe_to_sql(df_date, 'master_dates')

        # Export metrics to a metrics table
        metrics_df = pd.DataFrame([self.metrics])
        metrics_df['data_date'] = self.part_date
        db_manager.dataframe_to_sql(metrics_df, 'metrics')
    
    def get_metrics(self) -> Dict:
        """Return calculated metrics."""
        return self.metrics


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