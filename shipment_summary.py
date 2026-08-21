import pandas as pd
from pathlib import Path


# ============================================================
# 1. FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

CLEAN_FILE = DATA_DIR / "Clean_Shipments.csv"
SUMMARY_FILE = DATA_DIR / "Shipment_Summary.csv"


# ============================================================
# 2. LOAD CLEAN SHIPMENTS
# ============================================================

Clean_Shipments = pd.read_csv(CLEAN_FILE)


# ============================================================
# 3. CALCULATE CARRIER SUMMARY
# ============================================================

def compute_carrier_summary(records: list[dict]) -> list[dict]:

    groups = {}

    for record in records:

        carrier = record.get("carrier")

        if carrier not in groups:
            groups[carrier] = []

        groups[carrier].append(record)

    summary = []

    for carrier, group_records in groups.items():

        shipment_count = len(group_records)

        total_freight_cost = sum(
            r.get("freight_cost")
            for r in group_records
            if r.get("freight_cost") is not None
        )

        delayed_count = sum(
            1
            for r in group_records
            if r.get("status") == "Delayed"
        )

        avg_delay_days = round(
            sum(
                r.get("delay_days", 0)
                for r in group_records
            ) / shipment_count,
            1,
        )

        summary.append(
            {
                "carrier": carrier,
                "shipment_count": shipment_count,
                "total_freight_cost": round(
                    total_freight_cost,
                    2,
                ),
                "delayed_count": delayed_count,
                "avg_delay_days": avg_delay_days,
            }
        )

    return summary


# ============================================================
# 4. CREATE SUMMARY
# ============================================================

records = Clean_Shipments.to_dict(
    orient="records"
)

summary = compute_carrier_summary(records)


# ============================================================
# 5. SAVE SUMMARY CSV
# ============================================================

summary_df = pd.DataFrame(summary)

summary_df.to_csv(
    SUMMARY_FILE,
    index=False,
)


# ============================================================
# 6. DISPLAY RESULTS
# ============================================================

print("=== SHIPMENT RECORDS ===")

for record in records:
    print(record)


print("\n=== CARRIER SUMMARY ===")

for item in summary:
    print(item)


print("\n=== SUMMARY FILE CREATED ===")

print(f"File: {SUMMARY_FILE}")
print(f"Records: {len(summary_df)}")