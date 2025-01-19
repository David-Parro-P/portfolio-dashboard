import sqlite3
import pandas as pd
from pathlib import Path
import os

class DatabaseManager:
    def __init__(self, db_path: str):
        """Initialize database connection."""
        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        
    def dataframe_to_sql(self, df: pd.DataFrame, table_name: str) -> None:
        """
        Write DataFrame to SQLite table, create if doesn't exist
        and append if it does.
        """
        if df.empty:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(
                name=table_name,
                con=conn,
                if_exists='append',
                index=False
            )

    def execute_query(self, query: str) -> None:
        """Execute a SQL query."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query)
            conn.commit()