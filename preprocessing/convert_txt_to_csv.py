#!/usr/bin/env python3
"""
Script to convert all .txt files to CSV files in the Capstone dataset directory.
The CSV files are saved in the same folder as their source .txt files.
"""

import os
import csv
from pathlib import Path


def convert_txt_to_csv(txt_path):
    """
    Convert a single .txt file to CSV format.
    Skips comment lines (starting with //) and writes data to a .csv file.
    """
    csv_path = txt_path.with_suffix('.csv')

    with open(txt_path, 'r') as txt_file:
        lines = txt_file.readlines()

    # Filter out comment lines (lines starting with //)
    data_lines = [line.strip() for line in lines if not line.strip().startswith('//')]

    if not data_lines:
        print(f"  Skipped (no data): {txt_path}")
        return False

    # Write to CSV
    with open(csv_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for line in data_lines:
            # Split by comma and write as row
            row = line.split(',')
            writer.writerow(row)

    return True


def main():
    # Define the base directory (dataset folder in Capstone project)
    base_dir = Path("/Users/dhritigabani/Capstone/dataset")

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        return

    # Find all .txt files recursively
    txt_files = list(base_dir.rglob("*.txt"))

    print(f"Found {len(txt_files)} .txt files to convert\n")

    converted = 0
    skipped = 0

    for txt_path in txt_files:
        relative_path = txt_path.relative_to(base_dir)
        print(f"Converting: {relative_path}")

        if convert_txt_to_csv(txt_path):
            converted += 1
        else:
            skipped += 1

    print(f"\nConversion complete!")
    print(f"  Converted: {converted} files")
    print(f"  Skipped: {skipped} files")


if __name__ == "__main__":
    main()
