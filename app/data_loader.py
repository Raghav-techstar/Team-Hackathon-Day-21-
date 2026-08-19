from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CLEAN_FILE = DATA_DIR / "Clean_Shipments.csv"
REJECTED_FILE = DATA_DIR / "Rejected_Shipments.csv"
SUMMARY_FILE = DATA_DIR / "Shipment_Summary.csv"


def load_clean_shipments() -> pd.DataFrame:
    """Load cleaned shipment records from CSV."""
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(
            f"Clean shipments file not found: {CLEAN_FILE}"
        )

    return pd.read_csv(CLEAN_FILE)


def load_rejected_shipments() -> pd.DataFrame:
    """Load rejected shipment records from CSV."""
    if not REJECTED_FILE.exists():
        raise FileNotFoundError(
            f"Rejected shipments file not found: {REJECTED_FILE}"
        )

    return pd.read_csv(REJECTED_FILE)


def load_shipment_summary() -> pd.DataFrame:
    """Load shipment summary data from CSV."""
    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"Shipment summary file not found: {SUMMARY_FILE}"
        )

    return pd.read_csv(SUMMARY_FILE)