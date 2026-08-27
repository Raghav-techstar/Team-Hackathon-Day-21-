import pandas as pd
from pathlib import Path


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "raw_shipments.csv"

OUTPUT_DIR = BASE_DIR.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLEAN_FILE = OUTPUT_DIR / "Clean_Shipments.csv"
REJECTED_FILE = OUTPUT_DIR / "Rejected_Shipments.csv"


# ============================================================
# 1. READ SOURCE DATA
# ============================================================

df = pd.read_csv(INPUT_FILE)

# Remove accidental spaces from column names
df.columns = df.columns.str.strip()

print("\n========== SOURCE COLUMNS ==========")
print(df.columns.tolist())


# ============================================================
# 2. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "shipment_id",
    "carrier",
    "ship_date",
    "status",
    "origin",
    "destination",
    "freight_cost",
    "Expected Delivery Date",
    "Delivered_Date",
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# 3. CREATE REJECTION MASK
# ============================================================

reject_mask = pd.Series(False, index=df.index)


# ============================================================
# 4. SHIPMENT ID VALIDATION
# ============================================================

df["shipment_id"] = (
    df["shipment_id"]
    .astype("string")
    .str.strip()
)

invalid_shipment_id = (
    df["shipment_id"].isna()
    | (df["shipment_id"] == "")
    | (df["shipment_id"].str.upper() == "NULL")
)

reject_mask |= invalid_shipment_id


# ============================================================
# 5. CARRIER TRANSFORMATION
# ============================================================

df["carrier"] = (
    df["carrier"]
    .astype("string")
    .str.strip()
    .str.upper()
)

valid_carriers = [
    "DHL",
    "BLUEDART",
    "FEDEX",
]

invalid_carrier = ~df["carrier"].isin(valid_carriers)

reject_mask |= invalid_carrier


# ============================================================
# 6. SHIP DATE TRANSFORMATION
# ============================================================

raw_ship_date = (
    df["ship_date"]
    .astype("string")
    .str.strip()
)

ship_date_result = pd.Series(
    pd.NaT,
    index=df.index,
    dtype="datetime64[ns]"
)


# ------------------------------------------------------------
# Dates containing "/" are MM/DD/YYYY
# ------------------------------------------------------------

slash_mask = (
    raw_ship_date.notna()
    & raw_ship_date.str.contains("/", regex=False)
    & ~raw_ship_date.str.contains("-", regex=False)
    & (raw_ship_date != "")
)

ship_date_result.loc[slash_mask] = pd.to_datetime(
    raw_ship_date.loc[slash_mask],
    format="%m/%d/%Y",
    errors="coerce"
)


# ------------------------------------------------------------
# Dates containing "-" are DD-MM-YYYY
# Convert them to MM/DD/YYYY
# ------------------------------------------------------------

dash_mask = (
    raw_ship_date.notna()
    & raw_ship_date.str.contains("-", regex=False)
    & ~raw_ship_date.str.contains("/", regex=False)
    & (raw_ship_date != "")
)

dash_dates = (
    raw_ship_date.loc[dash_mask]
    .str.replace("-", "/", regex=False)
)

ship_date_result.loc[dash_mask] = pd.to_datetime(
    dash_dates,
    format="%d/%m/%Y",
    errors="coerce"
)


# ------------------------------------------------------------
# Invalid / missing ship dates
# ------------------------------------------------------------

invalid_ship_date = (
    raw_ship_date.isna()
    | (raw_ship_date == "")
    | ship_date_result.isna()
)

reject_mask |= invalid_ship_date


# Store formatted ship date
df["ship_date"] = ship_date_result.dt.strftime(
    "%m/%d/%Y"
)


# ============================================================
# 7. STATUS TRANSFORMATION
# ============================================================

df["status"] = (
    df["status"]
    .astype("string")
    .str.strip()
    .str.upper()
)


# ------------------------------------------------------------
# Blank status becomes Accepted
# ------------------------------------------------------------

blank_status = (
    df["status"].isna()
    | (df["status"] == "")
    | (df["status"] == "NULL")
)

df.loc[blank_status, "status"] = "ACCEPTED"


# ------------------------------------------------------------
# Status mapping
# ------------------------------------------------------------

status_mapping = {

    # DELAYED
    "DELAYED": "Delayed",
    "DELAY": "Delayed",

    # DELIVERED
    "DELIVERED": "Delivered",
    "DELIVER": "Delivered",

    # IN TRANSIT
    "IN TRANSIT": "In Transit",
    "IN_TRANSIT": "In Transit",
    "IN-TRANSIT": "In Transit",
    "INTRANSIT": "In Transit",
    "IN TRANS": "In Transit",

    # PENDING
    "PENDING": "Pending",

    # ACCEPTED
    "ACCEPTED": "Accepted",
}

df["status"] = df["status"].replace(status_mapping)


# ------------------------------------------------------------
# Validate status
# ------------------------------------------------------------

valid_statuses = [
    "Delayed",
    "Delivered",
    "In Transit",
    "Pending",
    "Accepted",
]

invalid_status = ~df["status"].isin(valid_statuses)

reject_mask |= invalid_status


# ============================================================
# 8. EXPECTED DELIVERY DATE
# ============================================================

raw_expected_date = (
    df["Expected Delivery Date"]
    .astype("string")
    .str.strip()
)

expected_delivery_date = pd.Series(
    pd.NaT,
    index=df.index,
    dtype="datetime64[ns]"
)


# ------------------------------------------------------------
# "/" = MM/DD/YYYY
# ------------------------------------------------------------

expected_slash_mask = (
    raw_expected_date.notna()
    & raw_expected_date.str.contains("/", regex=False)
    & ~raw_expected_date.str.contains("-", regex=False)
    & (raw_expected_date != "")
)

expected_delivery_date.loc[expected_slash_mask] = pd.to_datetime(
    raw_expected_date.loc[expected_slash_mask],
    format="%m/%d/%Y",
    errors="coerce"
)


# ------------------------------------------------------------
# "-" = DD-MM-YYYY
# ------------------------------------------------------------

expected_dash_mask = (
    raw_expected_date.notna()
    & raw_expected_date.str.contains("-", regex=False)
    & ~raw_expected_date.str.contains("/", regex=False)
    & (raw_expected_date != "")
)

expected_dash_dates = (
    raw_expected_date.loc[expected_dash_mask]
    .str.replace("-", "/", regex=False)
)

expected_delivery_date.loc[expected_dash_mask] = pd.to_datetime(
    expected_dash_dates,
    format="%d/%m/%Y",
    errors="coerce"
)


# ============================================================
# 9. EXPECTED DELIVERY DATE VALIDATION
# ============================================================

# Expected Delivery Date is required only
# when shipment status is Delivered.

delivered_status_mask = (
    df["status"] == "Delivered"
)

invalid_expected_date = (
    delivered_status_mask
    & (
        raw_expected_date.isna()
        | (raw_expected_date == "")
        | expected_delivery_date.isna()
    )
)

reject_mask |= invalid_expected_date


# ============================================================
# 10. DELIVERED DATE
# ============================================================

raw_delivered_date = (
    df["Delivered_Date"]
    .astype("string")
    .str.strip()
)

delivered_date = pd.Series(
    pd.NaT,
    index=df.index,
    dtype="datetime64[ns]"
)


# ------------------------------------------------------------
# "/" = MM/DD/YYYY
# ------------------------------------------------------------

delivered_slash_mask = (
    raw_delivered_date.notna()
    & raw_delivered_date.str.contains("/", regex=False)
    & ~raw_delivered_date.str.contains("-", regex=False)
    & (raw_delivered_date != "")
)

delivered_date.loc[delivered_slash_mask] = pd.to_datetime(
    raw_delivered_date.loc[delivered_slash_mask],
    format="%m/%d/%Y",
    errors="coerce"
)


# ------------------------------------------------------------
# "-" = DD-MM-YYYY
# ------------------------------------------------------------

delivered_dash_mask = (
    raw_delivered_date.notna()
    & raw_delivered_date.str.contains("-", regex=False)
    & ~raw_delivered_date.str.contains("/", regex=False)
    & (raw_delivered_date != "")
)

delivered_dash_dates = (
    raw_delivered_date.loc[delivered_dash_mask]
    .str.replace("-", "/", regex=False)
)

delivered_date.loc[delivered_dash_mask] = pd.to_datetime(
    delivered_dash_dates,
    format="%d/%m/%Y",
    errors="coerce"
)


# ============================================================
# 11. DELIVERED DATE VALIDATION
# ============================================================

# Delivered_Date is required only for Delivered shipments.

invalid_delivered_date = (
    delivered_status_mask
    & (
        raw_delivered_date.isna()
        | (raw_delivered_date == "")
        | delivered_date.isna()
    )
)

reject_mask |= invalid_delivered_date


# ============================================================
# 12. CONVERT SHIP DATE TO DATETIME
# ============================================================

ship_date_datetime = pd.to_datetime(
    df["ship_date"],
    format="%m/%d/%Y",
    errors="coerce"
)


# ============================================================
# 13. DATE ORDER VALIDATION
# ============================================================

# Expected Delivery Date cannot be before Ship Date.

invalid_expected_date_order = (
    expected_delivery_date.notna()
    & ship_date_datetime.notna()
    & (
        expected_delivery_date
        < ship_date_datetime
    )
)

reject_mask |= invalid_expected_date_order


# ------------------------------------------------------------
# Delivered Date cannot be before Ship Date
# ------------------------------------------------------------

invalid_delivered_date_order = (
    delivered_date.notna()
    & ship_date_datetime.notna()
    & (
        delivered_date
        < ship_date_datetime
    )
)

reject_mask |= invalid_delivered_date_order


# ============================================================
# 14. FREIGHT COST VALIDATION
# ============================================================

freight_cost_numeric = pd.to_numeric(
    df["freight_cost"],
    errors="coerce"
)

invalid_freight_cost = (
    freight_cost_numeric.isna()
    | (freight_cost_numeric <= 0)
)

reject_mask |= invalid_freight_cost

df["freight_cost"] = freight_cost_numeric


# ============================================================
# 15. CALCULATE delay_days
# ============================================================

# delay_days is calculated ONLY for Delivered shipments.
#
# Formula:
#
# Delivered Date - Expected Delivery Date
#
# Negative values become 0.

df["delay_days"] = pd.Series(
    pd.NA,
    index=df.index,
    dtype="Int64"
)

delay_difference = (
    delivered_date
    - expected_delivery_date
).dt.days

delivered_with_valid_dates = (
    delivered_status_mask
    & expected_delivery_date.notna()
    & delivered_date.notna()
)

df.loc[
    delivered_with_valid_dates,
    "delay_days"
] = (
    delay_difference.loc[
        delivered_with_valid_dates
    ]
    .clip(lower=0)
    .astype("Int64")
)


# ============================================================
# 16. CREATE REJECTED SHIPMENTS
# ============================================================

Rejected_Shipments = df.loc[
    reject_mask
].copy()


# ============================================================
# 17. CREATE CLEAN SHIPMENTS
# ============================================================

Clean_Shipments = df.loc[
    ~reject_mask
].copy()


# ============================================================
# 18. FORMAT DATES
# ============================================================

Clean_Shipments["Expected Delivery Date"] = (
    expected_delivery_date
    .loc[~reject_mask]
    .dt.strftime("%m/%d/%Y")
)

Clean_Shipments["Delivered_Date"] = (
    delivered_date
    .loc[~reject_mask]
    .dt.strftime("%m/%d/%Y")
)

Rejected_Shipments["Expected Delivery Date"] = (
    expected_delivery_date
    .loc[reject_mask]
    .dt.strftime("%m/%d/%Y")
)

Rejected_Shipments["Delivered_Date"] = (
    delivered_date
    .loc[reject_mask]
    .dt.strftime("%m/%d/%Y")
)


# ============================================================
# 19. NULL HANDLING
# ============================================================

# Only these columns use "NULL" instead of NaN.

null_columns = [
    "freight_cost",
    "Expected Delivery Date",
    "Delivered_Date",
    "delay_days",
]

for column in null_columns:

    Clean_Shipments[column] = (
        Clean_Shipments[column]
        .astype(object)
        .where(
            Clean_Shipments[column].notna(),
            "NULL"
        )
    )

    Rejected_Shipments[column] = (
        Rejected_Shipments[column]
        .astype(object)
        .where(
            Rejected_Shipments[column].notna(),
            "NULL"
        )
    )


# ============================================================
# 20. RESET INDEX
# ============================================================

Clean_Shipments.reset_index(
    drop=True,
    inplace=True
)

Rejected_Shipments.reset_index(
    drop=True,
    inplace=True
)


# ============================================================
# 21. DISPLAY CLEAN SHIPMENTS
# ============================================================

print("\n========== CLEAN SHIPMENTS ==========")

print(
    Clean_Shipments.to_string(
        index=False
    )
)


# ============================================================
# 22. DISPLAY REJECTED SHIPMENTS
# ============================================================

print("\n========== REJECTED SHIPMENTS ==========")

print(
    Rejected_Shipments.to_string(
        index=False
    )
)


# ============================================================
# 23. TRANSFORMATION SUMMARY
# ============================================================

print("\n========== TRANSFORMATION SUMMARY ==========")

print(
    f"Original records : {len(df)}"
)

print(
    f"Clean records    : {len(Clean_Shipments)}"
)

print(
    f"Rejected records : {len(Rejected_Shipments)}"
)


# ============================================================
# 24. FINAL STATUS VALUES
# ============================================================

print("\n========== FINAL STATUS VALUES ==========")

print(
    Clean_Shipments["status"]
    .value_counts()
)


# ============================================================
# 25. SAVE CLEAN DATASET
# ============================================================

Clean_Shipments.to_csv(
    CLEAN_FILE,
    index=False
)


# ============================================================
# 26. SAVE REJECTED DATASET
# ============================================================

Rejected_Shipments.to_csv(
    REJECTED_FILE,
    index=False
)


# ============================================================
# 27. FINAL MESSAGE
# ============================================================

print("\n========== FILES CREATED ==========")

print(
    f"Clean file    : {CLEAN_FILE}"
)

print(
    f"Rejected file : {REJECTED_FILE}"
)