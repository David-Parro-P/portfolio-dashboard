import pandas as pd
import os
from typing import Dict, List
from io import StringIO
from datetime import date
from datetime import datetime

asset_category_replace = {"Stocks": "stocks", "Equity and Index Options": "options"}

# TODO corregir el otro fichero y borrar este
def split_ib_statement(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Splits an Interactive Brokers CSV statement into separate DataFrames for each section.

    The first column contains the section name and the second column indicates if it's
    a header or data row. Each section has its own structure.
    """

    # Read file line by line since structure varies between sections
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Dictionary to store sections
    sections: Dict[str, List[str]] = {}
    current_section = None

    # First pass: Group rows by section
    for line in lines:
        # Handle quoted section names (some might contain commas)
        if line.startswith('"'):
            section_name = line[1 : line.find('"', 1)]
            rest_of_line = line[line.find('"', 1) + 1 :]
        else:
            section_name = line[: line.find(",")]
            rest_of_line = line[line.find(",") + 1 :]

        if section_name not in sections:
            sections[section_name] = []

        sections[section_name].append(rest_of_line)

    # Second pass: Convert each section to DataFrame
    dataframes = {}
    for section_name, section_lines in sections.items():
        try:
            # Create DataFrame from section lines
            df = pd.read_csv(StringIO("".join(section_lines)))

            dataframes[section_name] = df.reset_index(drop=True)
        except:
            pass
    return dataframes


def post_process_df(df):
    """
    Post-process DataFrame by:
    1. Remove header row and all rows below it
    2. Remove rows containing 'Total' or 'Subtotal'
    3. Reset index

    Args:
        df (pd.DataFrame): Input DataFrame with 'Header' column

    Returns:
        pd.DataFrame: Processed DataFrame
    """
    try:
        # Find last occurrence of 'Header' in the Header column
        header_indices = df[df["Header"] == "Header"].index

        if len(header_indices) > 0:
            # Get the last header index and remove it and everything after
            last_header_idx = header_indices[-1]
            df = df.iloc[:last_header_idx]

        # Remove rows containing Total or Subtotal in any column
        # Convert all values to string to safely check for 'Total' and 'Subtotal'
        mask = (
            df.astype(str)
            .apply(lambda x: ~x.str.contains("Total|Subtotal", case=False, na=False))
            .all(axis=1)
        )
        df = df[mask]

        # Reset index
        df = df.reset_index(drop=True)

        return df

    except Exception as e:
        print(f"Error in post-processing: {str(e)}")
        return df


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=lambda x: x.lower().replace(" ", "_"))


def create_base_tables(df_base_daily: pd.DataFrame) -> tuple[pd.DataFrame]:
    df_base = df_base_daily.assign(
        prior_price=lambda x: pd.to_numeric(x["prior_price"], errors="coerce").fillna(
            0.0
        ),
        current_price=lambda x: pd.to_numeric(
            x["current_price"], errors="coerce"
        ).fillna(0.0),
        is_new=lambda x: x["prior_quantity"] == 0,
    )[
        [
            "asset_category",
            "symbol",
            "prior_quantity",
            "current_quantity",
            "prior_price",
            "current_price",
            "mark-to-market_p/l_position",
            "mark-to-market_p/l_transaction",
            "is_new",
        ]
    ].rename(
        columns={
            "mark-to-market_p/l_position": "pl_delta",
        }
    )
    float_columns = df_base.select_dtypes(include=["float64"]).columns
    df_base[float_columns] = df_base[float_columns].round(2)

    asset_categories = df_base["asset_category"].unique()
    df_by_category = {
        category: df_base.loc[lambda x: x["asset_category"] == category].copy()
        for category in asset_categories
    }

    df_stocks = df_by_category.get("Stocks")
    df_stocks["asset_category"] = df_stocks["asset_category"].str.lower()
    df_options = df_by_category.get("Equity and Index Options")
    df_options["asset_category"] = "options"
    df_forex = df_by_category.get("Forex")
    df_forex["asset_category"] = "forex"
    return df_stocks, df_options, df_forex


def parse_option_symbol(df: pd.DataFrame, symbol_col: str = "symbol") -> None:
    """
    Parse option symbols into separate columns, mutating the original DataFrame.
    Format example: 'ASTS 07FEB25 26 C'

    Args:
        df: DataFrame to modify
        symbol_col: Name of column containing option symbols
    """
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


def separate_trades(trades_df: pd.DataFrame) -> tuple[pd.DataFrame]:
    trades_df = (
        trades_df
        .pipe(clean_column_names)
        .assign(
            asset_category=lambda df: (
                df['asset_category']
                .replace(asset_category_replace)
            )
        )
        .loc[lambda df: df['header'] == 'Data'] 
    )
    stock_trades, options_trades = trades_df[trades_df['asset_category']=="stocks"], trades_df[trades_df['asset_category']=="options"]
    options_trades = parse_option_symbol(options_trades, symbol_col="symbol")
    return stock_trades, options_trades

def auto_convert_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == 'object':
            numeric_conversion = pd.to_numeric(df[col], errors='coerce')
            if not numeric_conversion.isna().all():
                df[col] = numeric_conversion
                continue
            try:
                date_formats = [
                    '%Y-%m-%d',          # 2024-01-30
                    '%Y-%m-%d %H:%M:%S', # 2024-01-30 15:30:00
                    '%d%b%y',            # 30JAN24
                    '%m/%d/%Y'           # 01/30/2024
                ]
                
                for fmt in date_formats:
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

if __name__ == "__main__":
    input_file = "daily_csv.1641291.20250116.csv"
    try:
        input_date = input_file.split(".")[0].split("_")[-1]
        if not (len(input_date) == 8 and input_date.isdigit()):
                raise ValueError
    except:
        try:
            input_date = input_file.split(".")[2]
            if not (len(input_date) == 8 and input_date.isdigit()):
                raise ValueError
        except:
            raise ValueError("UNEXPECTED FILE FORMAT")
    output_dir = "statement_sections"
    dataframes = split_ib_statement(input_file)
    df_base_daily = dataframes["Mark-to-Market Performance Summary"]
    df_base_daily = (
        df_base_daily.pipe(post_process_df)
        .drop("Header", axis=1)
        .pipe(clean_column_names)
    )
    if "Trades" in dataframes.keys():
        df_base_trades = dataframes["Trades"]

        df_trades_stock, df_options_trades = separate_trades(df_base_trades)

        op_trades_agg = (
            df_options_trades
            .pipe(auto_convert_types)
            .groupby('symbol')
            .agg(
                currency=('currency', 'first'),
                total_quantity=('quantity', 'sum'),
                total_proceeds=('proceeds', 'sum')
            )
            .reset_index()
            .pipe(parse_option_symbol)
        )

        stock_trades_agg = (df_trades_stock
            .pipe(auto_convert_types)
            .groupby('symbol')
            .agg(
                currency=('currency', 'first'),
                total_quantity=('quantity', 'sum'),
                total_proceeds=('proceeds', 'sum')
            )
            .reset_index()
    )
        stock_proceeds = stock_trades_agg.copy().assign(
            underlying=lambda x: x['symbol'],
            exp_date="9999-01-01",
            strike=0,
            contract_type="C",
            asset_category="stocks"
        )

        options_proceeds = op_trades_agg.copy().assign(
            asset_category="options"
        )
        df_total_proceeds = pd.concat([stock_proceeds, options_proceeds])

    else:
        df_base_trades, df_trades_stock, df_options_trades, op_trades_agg, stock_trades_agg, stock_proceeds, options_proceeds, df_total_proceeds = [pd.DataFrame()] * 8
    # tabla de stocks
    df_stocks, df_options, df_forex = create_base_tables(
        df_base_daily=df_base_daily
    )

    df_options = parse_option_symbol(df=df_options)

    df_forex = (df_forex
                .rename(columns={"symbol": "currency", "prior_price": "exchange_rate_eur"})
                [['asset_category', 'currency', 'prior_quantity', 'current_quantity', 'exchange_rate_eur', 'pl_delta']]
    )

    metric_gross_val = (df_stocks['current_quantity'] * df_stocks['current_price']).sum() + ((df_options['current_quantity'] * df_options['current_price']).sum()*100)

    # as almost everything is usd no transformation done
    metric_nav = metric_gross_val + df_forex['current_quantity'].sum()

    metric_option_credit = ((df_options[df_options['current_quantity']<0]['current_quantity']  * df_options[df_options['current_quantity']<0]['current_price']).sum() * 100).round(2)
    metric_option_debit = ((df_options[df_options['current_quantity']>0]['current_quantity']  * df_options[df_options['current_quantity']>0]['current_price']).sum() * 100).round(2)
    metric_option_balance = metric_option_debit + metric_option_credit


    df_to_save = [df_stocks, df_options, df_forex, df_total_proceeds, op_trades_agg, stock_trades_agg, df_forex]

    df_for_pbi = {
        "stocks": df_stocks,
        "options": df_options,
        "options_trades": op_trades_agg,
        "stock_traces": stock_trades_agg,
        "total_proceeds": df_total_proceeds,
        "forex": df_forex,
    }
    PREFIX = "/mnt/c/Users/David/Downloads/output"
    today = date.today().isoformat() 
    part_date = datetime.strptime(input_date, '%Y%m%d').isoformat()[:10]
    for key in df_for_pbi.keys():
        df_to_export = df_for_pbi[key]
        if not df_to_export.empty:
            key_column = 'symbol' if 'symbol' in df_to_export.columns else 'currency'
            df_to_export['pk'] = df_to_export[key_column] + "_"+ input_date
            df_to_export['data_date_part'] = part_date
            if os.path.exists(f"{PREFIX}/{key}.csv"):
                df_to_export.to_csv(f"{PREFIX}/{key}.csv", mode='a', header=False, index=False)
            else:
                df_to_export.to_csv(f"{PREFIX}/{key}.csv", mode='w', header=True, index=False)
        else:
            pass
            
    df_date = pd.DataFrame([[part_date]], columns=['data_date_part'])
    if os.path.exists(f"{PREFIX}/master_dates.csv"):
        df_date.to_csv(f"{PREFIX}/master_dates.csv", mode='a', header=False, index=False)
    else:
        df_date.to_csv(f"{PREFIX}/master_dates.csv", mode='w', header=True, index=False)