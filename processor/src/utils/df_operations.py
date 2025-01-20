"""DataFrame processing utilities for IB statement processing."""
import pandas as pd
from typing import Tuple
from constants import (
    DATE_FORMATS,
    SYMBOL_COL,
    ASSET_CATEGORY_COL,
    CAP_HEADER,
    CAP_FOREX,
    CAP_OPTIONS,
    CAP_STOCK,
    OPTIONS_TYPE,
    FOREX_TYPE,
    PRIOR_PRICE_COL,
    CURRENT_PRICE_COL,
    PRIOR_QUANTITY_COL,
    CURRENT_QUANTITY_COL,
    MARKET_PL_POS,
    MARKET_PL_TRANS,
    IS_NEW_COL,
    PL_DELTA_COL
)

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans column names by converting to lowercase and replacing spaces with underscores."""
    return df.rename(columns=lambda x: x.lower().replace(" ", "_"))

def post_process_df(df: pd.DataFrame) -> pd.DataFrame:
    """Post-processes DataFrame by removing headers and totals."""
    try:
        header_indices = df[df[CAP_HEADER] == CAP_HEADER].index
        if len(header_indices) > 0:
            last_header_idx = header_indices[-1]
            df = df.iloc[:last_header_idx]

        mask = (
            df.astype(str)
            .apply(lambda x: ~x.str.contains("Total|Subtotal", case=False, na=False))
            .all(axis=1)
        )
        df = df[mask]
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"Error in post-processing: {str(e)}")
        return df

def parse_option_symbol(df: pd.DataFrame, symbol_col: str = SYMBOL_COL) -> pd.DataFrame:
    """Parses option symbols into separate columns."""
    split_series = df[symbol_col].str.split(" ", expand=True)
    
    return (
        df
        .assign(
            underlying=split_series[0],
            exp_date=lambda _: pd.to_datetime(split_series[1], format="%d%b%y").dt.strftime("%Y-%m-%d"),
            strike=lambda _: pd.to_numeric(split_series[2]),
            contract_type=split_series[3]
        )
    )

def auto_convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """Automatically converts column types based on content."""
    for col in df.columns:
        if df[col].dtype == 'object':
            numeric_conversion = pd.to_numeric(df[col], errors='coerce')
            if not numeric_conversion.isna().all():
                df[col] = numeric_conversion
                continue
            
            try:
                for fmt in DATE_FORMATS:
                    try:
                        date_conversion = pd.to_datetime(df[col], format=fmt, errors='coerce')
                        if not date_conversion.isna().all():
                            df[col] = date_conversion
                            break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Could not convert {col}: {str(e)}")
                continue
    
    return df

def create_base_tables(df_base_daily: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Creates base tables for stocks, options, and forex."""
    df_base = df_base_daily.assign(
        prior_price=lambda x: pd.to_numeric(x[PRIOR_PRICE_COL], errors="coerce").fillna(0.0),
        current_price=lambda x: pd.to_numeric(x[CURRENT_PRICE_COL], errors="coerce").fillna(0.0),
        is_new=lambda x: x[PRIOR_QUANTITY_COL] == 0,
    )[
        [
            ASSET_CATEGORY_COL,
            SYMBOL_COL,
            PRIOR_QUANTITY_COL,
            CURRENT_QUANTITY_COL,
            PRIOR_PRICE_COL,
            CURRENT_PRICE_COL,
            MARKET_PL_POS,
            MARKET_PL_TRANS,
            IS_NEW_COL,
        ]
    ].rename(
        columns={
            MARKET_PL_POS: PL_DELTA_COL,
        }
    )
    
    float_columns = df_base.select_dtypes(include=["float64"]).columns
    df_base[float_columns] = df_base[float_columns].round(2)

    asset_categories = df_base[ASSET_CATEGORY_COL].unique()
    df_by_category = {
        category: df_base.loc[lambda x: x[ASSET_CATEGORY_COL] == category].copy()
        for category in asset_categories
    }

    df_stocks = df_by_category.get(CAP_STOCK)
    if df_stocks is not None:
        df_stocks[ASSET_CATEGORY_COL] = df_stocks[ASSET_CATEGORY_COL].str.lower()
    
    df_options = df_by_category.get(CAP_OPTIONS)
    if df_options is not None:
        df_options[ASSET_CATEGORY_COL] = OPTIONS_TYPE
    
    df_forex = df_by_category.get(CAP_FOREX)
    if df_forex is not None:
        df_forex[ASSET_CATEGORY_COL] = FOREX_TYPE
    
    return df_stocks, df_options, df_forex