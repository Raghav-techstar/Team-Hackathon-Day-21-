import pandas as pd


REQUIRED_FIELDS = [
    "shipment_id",
    "carrier",
    "ship_date",
    "origin",
    "destination",
]


def data_quality_report(
    clean_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
) -> dict:
    """Run basic data quality checks."""

    total_records = len(clean_df)

    # ---------------------------------------------------------
    # 1. Duplicate shipment IDs
    # ---------------------------------------------------------

    duplicate_count = int(
        clean_df["shipment_id"].duplicated().sum()
    )

    duplicate_status = (
        "PASS"
        if duplicate_count == 0
        else "FAIL"
    )

    # ---------------------------------------------------------
    # 2. Null required fields
    # ---------------------------------------------------------

    null_count = int(
        clean_df[REQUIRED_FIELDS]
        .isna()
        .sum()
        .sum()
    )

    null_status = (
        "PASS"
        if null_count == 0
        else "FAIL"
    )

    # ---------------------------------------------------------
    # 3. Rejected records check
    # ---------------------------------------------------------

    rejected_count = len(rejected_df)

    rejected_status = (
        "PASS"
        if rejected_count >= 0
        else "FAIL"
    )

    # ---------------------------------------------------------
    # Overall status
    # ---------------------------------------------------------

    overall_status = (
        "PASS"
        if duplicate_status == "PASS"
        and null_status == "PASS"
        else "FAIL"
    )

    return {
        "overall_status": overall_status,
        "total_records": total_records,
        "duplicate_shipment_ids": duplicate_count,
        "null_required_fields": null_count,
        "checks": [
            {
                "check_name": "Duplicate shipment IDs",
                "status": duplicate_status,
                "details": (
                    f"{duplicate_count} duplicate shipment IDs found."
                ),
            },
            {
                "check_name": "Required field null check",
                "status": null_status,
                "details": (
                    f"{null_count} null values found "
                    f"in required fields."
                ),
            },
            {
                "check_name": "Rejected shipment records",
                "status": rejected_status,
                "details": (
                    f"{rejected_count} records were rejected "
                    f"during data cleaning."
                ),
            },
        ],
    }