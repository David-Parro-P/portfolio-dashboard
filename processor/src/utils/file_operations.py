"""File operations utilities for IB statement processing."""

import os
from typing import Dict, List
import pandas as pd
from io import StringIO


def split_ib_statement(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Splits an Interactive Brokers CSV statement into separate DataFrames for each section.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    sections: Dict[str, List[str]] = {}
    for line in lines:
        if line.startswith('"'):
            section_name = line[1 : line.find('"', 1)]
            rest_of_line = line[line.find('"', 1) + 1 :]
        else:
            section_name = line[: line.find(",")]
            rest_of_line = line[line.find(",") + 1 :]

        if section_name not in sections:
            sections[section_name] = []
        sections[section_name].append(rest_of_line)

    dataframes = {}
    for section_name, section_lines in sections.items():
        try:
            df = pd.read_csv(StringIO("".join(section_lines)))
            dataframes[section_name] = df.reset_index(drop=True)
        except:
            pass
    return dataframes


def validate_input_file(input_file: str) -> str:
    """
    Validates input file name and returns the input date.
    Tries different patterns to extract an 8-digit date from the filename.
    """
    def is_valid_date(date_str: str) -> bool:
        return len(date_str) == 8 and date_str.isdigit()

    def try_extract_date(file_name: str, pattern_func) -> str | None:
        try:
            date = pattern_func(file_name)
            return date if is_valid_date(date) else None
        except:
            return None

    # List of patterns to try
    patterns = [
        lambda f: f.split(".")[0].split("_")[-1],  # Daily report (basic)
        lambda f: f.split(".")[2],                 # Daily report (custom)
        lambda f: f.split(".")[1],                 # Fallback pattern
    ]

    for pattern in patterns:
        date = try_extract_date(input_file, pattern)
        if date:
            return date

    raise ValueError(f"date could not be extracted from filename: {input_file}")
