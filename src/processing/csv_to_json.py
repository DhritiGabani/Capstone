import sys
import json
import argparse
import pandas as pd
from pathlib import Path

REQUIRED_COLUMNS = {"device", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"}
VALID_DEVICES = {"imu1", "imu2"}


def load_csv(filepath: Path) -> pd.DataFrame:
    """
    Load and validate the raw sensor CSV file.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    df = pd.read_csv(filepath)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    invalid_devices = set(df["device"].unique()) - VALID_DEVICES
    if invalid_devices:
        raise ValueError(f"Unexpected device identifiers found: {invalid_devices}")

    if df["device"].isin(VALID_DEVICES).sum() == 0:
        raise ValueError("No valid imu1 or imu2 rows found in CSV.")

    return df


def extract_imu_samples(df: pd.DataFrame, device: str) -> list[dict]:
    """
    Extract and format signal samples for a single IMU device.
    """
    imu_df = (
        df[df["device"] == device]
        .reset_index(drop=True)  # reindex after filtering
        [["ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"]]
    )

    samples = []
    for idx, row in imu_df.iterrows():
        samples.append({
            "sample_idx": int(idx),
            "ax_g":   round(float(row["ax_g"]),   6),
            "ay_g":   round(float(row["ay_g"]),   6),
            "az_g":   round(float(row["az_g"]),   6),
            "gx_dps": round(float(row["gx_dps"]), 6),
            "gy_dps": round(float(row["gy_dps"]), 6),
            "gz_dps": round(float(row["gz_dps"]), 6),
        })

    return samples


def build_imu_json(samples: list[dict]) -> dict:
    """
    Wrap samples in the standard IMU JSON envelope.
    """
    return {"samples": samples}


def save_json(data: dict, output_path: Path) -> None:
    """
    Write a dictionary to a JSON file.
    """
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def convert(csv_path: Path, output_dir: Path) -> tuple[dict, dict]:
    """
    Full conversion pipeline: CSV → imu1 and imu2 JSON structures
    """
    df = load_csv(csv_path)

    imu1_samples = extract_imu_samples(df, "imu1")
    imu1_json = build_imu_json(imu1_samples)

    imu2_samples = extract_imu_samples(df, "imu2")
    imu2_json = build_imu_json(imu2_samples)

    output_dir.mkdir(parents=True, exist_ok=True)
    imu1_path = output_dir / "imu1_data.json"
    imu2_path = output_dir / "imu2_data.json"

    save_json(imu1_json, imu1_path)
    save_json(imu2_json, imu2_path)

    return imu1_json, imu2_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert CSV file to IMU JSON structures."
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the raw sensor CSV file."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory to write output JSON files (default: ./output)."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        convert(args.csv_path, args.output_dir)
        print("Done")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)