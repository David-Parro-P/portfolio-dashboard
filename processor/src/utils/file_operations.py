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

    # TODO revisar este tipados
    sections: Dict[str, List[str]] = {}
    for line in lines:
        if line.startswith('"'):
            section_name = line[1:line.find('"', 1)]
            rest_of_line = line[line.find('"', 1) + 1:]
        else:
            section_name = line[:line.find(",")]
            rest_of_line = line[line.find(",") + 1:]

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

def save_sections(dataframes: Dict[str, pd.DataFrame], output_dir: str):
    # TODO donde se usa esto? borrar?
    """Saves each section DataFrame to a separate CSV file."""
    os.makedirs(output_dir, exist_ok=True)

    for section_name, df in dataframes.items():
        safe_name = "".join(c if c.isalnum() else "_" for c in section_name)
        file_path = os.path.join(output_dir, f"{safe_name}.csv")
        df.to_csv(file_path, index=False)
        print(f"Saved {section_name} to {file_path}")

def validate_input_file(input_file: str) -> str:
    # TODO mejorar el error d salida
    """Validates input file name and returns the input date."""
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
    return input_date