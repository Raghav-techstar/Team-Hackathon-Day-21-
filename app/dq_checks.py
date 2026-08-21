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
    """Run data-quality checks."""

    total_records = len(clean_df)

    # =========================================================
    # 1. Duplicate shipment IDs
    # =========================================================

    duplicate_count = int(
        clean_df["shipment_id"]
        .duplicated()
        .sum()
    )

    duplicate_status = (
        "PASS"
        if duplicate_count == 0
        else "FAIL"
    )

    # =========================================================
    # 2. Null / empty required fields
    # =========================================================

    required_df = clean_df[REQUIRED_FIELDS].copy()

    # Treat empty strings and whitespace as missing
    required_df = required_df.replace(
        r"^\s*$",
        pd.NA,
        regex=True,
    )

    null_count = int(
        required_df
        .isna()
        .sum()
        .sum()
    )

    null_status = (
        "PASS"
        if null_count == 0
        else "FAIL"
    )

    # =========================================================
    # 3. Rejected shipment records
    # =========================================================

    rejected_count = len(rejected_df)

    rejected_status = (
        "PASS"
        if rejected_count == 0
        else "WARNING"
    )

    # =========================================================
    # 4. Overall status
    #
    # Rejected records are warnings, not critical failures.
    # =========================================================

    overall_status = (
        "PASS"
        if (
            duplicate_status == "PASS"
            and null_status == "PASS"
        )
        else "FAIL"
    )

    # =========================================================
    # 5. Return report
    # =========================================================

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
                    f"{duplicate_count} duplicate "
                    f"shipment IDs found."
                ),
            },

            {
                "check_name": "Required field null check",
                "status": null_status,
                "details": (
                    f"{null_count} null or empty values "
                    f"found in required fields."
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