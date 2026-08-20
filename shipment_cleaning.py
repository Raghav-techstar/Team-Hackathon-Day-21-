import os
import pandas as pd


# ============================================================
# 1. READ SOURCE DATA
# ============================================================

df = pd.read_csv("data/raw_shipments.csv")

# Remove accidental spaces from column names
df.columns = df.columns.str.strip()

print("Columns detected:")
print(df.columns.tolist())


# ============================================================
# 2. VALIDATE REQUIRED SOURCE COLUMNS
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
    "Delivered Date",
]

missing_columns = [column for column in required_columns if column not in df.columns]

if missing_columns:
    raise ValueError(
        "Missing columns in raw_shipments.csv: " + ", ".join(missing_columns)
    )


# ============================================================
# 3. CREATE REJECTION MASK AND REJECTION REASONS
# ============================================================

reject_mask = pd.Series(False, index=df.index)

rejection_reasons = pd.Series("", index=df.index, dtype="string")


def add_rejection_reason(mask, reason):
    """
    Add a rejection reason to all records matching mask.

    Multiple rejection reasons are combined using '; '.
    """

    global reject_mask

    reject_mask.loc[mask] = True

    empty_reason = rejection_reasons.loc[mask] == ""

    rejection_reasons.loc[mask & empty_reason] = reason

    rejection_reasons.loc[mask & ~empty_reason] = (
        rejection_reasons.loc[mask & ~empty_reason] + "; " + reason
    )


# ============================================================
# 4. CARRIER TRANSFORMATION & VALIDATION
# ============================================================

df["carrier"] = df["carrier"].astype("string").str.strip().str.upper()

valid_carriers = [
    "DHL",
    "BLUEDART",
    "FEDEX",
]

invalid_carrier = ~df["carrier"].isin(valid_carriers)

add_rejection_reason(invalid_carrier, "Invalid carrier")


# ============================================================
# 5. SHIP DATE TRANSFORMATION & VALIDATION
# ============================================================

df["ship_date"] = (
    df["ship_date"].astype("string").str.strip().str.replace("-", "/", regex=False)
)


# The raw file contains both:
#
# 1/27/2024
# 04-06-2024
# 06-12-2024
#
# Therefore format="mixed" is used.
#
# dayfirst=False means:
#
# 04/06/2024 -> April 6, 2024
# 06/12/2024 -> June 12, 2024

ship_date_datetime = pd.to_datetime(
    df["ship_date"],
    format="mixed",
    dayfirst=False,
    errors="coerce",
)

invalid_ship_date = ship_date_datetime.isna()

add_rejection_reason(invalid_ship_date, "Invalid ship date")


# ============================================================
# 6. STATUS TRANSFORMATION
# ============================================================

df["status"] = df["status"].astype("string").str.strip().str.upper()


# ============================================================
# 7. BLANK STATUS -> ACCEPTED
# ============================================================

blank_status = df["status"].isna() | (df["status"].str.strip() == "")

df.loc[blank_status, "status"] = "Accepted"


# ============================================================
# 8. STANDARDIZE STATUS VALUES
# ============================================================

status_mapping = {
    # Delayed
    "DELAYED": "Delayed",
    "DELAY": "Delayed",
    # Delivered
    "DELIVERED": "Delivered",
    "DELIVER": "Delivered",
    # In Transit
    "IN TRANSIT": "In Transit",
    "IN_TRANSIT": "In Transit",
    "IN-TRANSIT": "In Transit",
    "INTRANSIT": "In Transit",
    # Pending
    "PENDING": "Pending",
    # Accepted
    "ACCEPTED": "Accepted",
}

df["status"] = df["status"].replace(status_mapping)


# ============================================================
# 9. STATUS VALIDATION
# ============================================================

valid_statuses = [
    "Delayed",
    "Delivered",
    "In Transit",
    "Pending",
    "Accepted",
]

invalid_status = ~df["status"].isin(valid_statuses)

add_rejection_reason(invalid_status, "Invalid status")


# ============================================================
# 10. EXPECTED DELIVERY DATE TRANSFORMATION
# ============================================================

df["Expected Delivery Date"] = (
    df["Expected Delivery Date"]
    .astype("string")
    .str.strip()
    .str.replace("-", "/", regex=False)
)


expected_delivery_date = pd.to_datetime(
    df["Expected Delivery Date"],
    format="mixed",
    dayfirst=False,
    errors="coerce",
)


invalid_expected_delivery_date = expected_delivery_date.isna()

add_rejection_reason(
    invalid_expected_delivery_date, "Expected Delivery Date is missing or invalid"
)


# ============================================================
# 11. DELIVERED DATE TRANSFORMATION
# ============================================================

# IMPORTANT:
#
# Your actual CSV column is:
#
# Delivered Date
#
# NOT:
#
# Delivered_Date

df["Delivered Date"] = (
    df["Delivered Date"].astype("string").str.strip().str.replace("-", "/", regex=False)
)


delivered_date = pd.to_datetime(
    df["Delivered Date"],
    format="mixed",
    dayfirst=False,
    errors="coerce",
)


# ============================================================
# 12. DELIVERED DATE VALIDATION
# ============================================================

# Delivered Date is required ONLY when
# status is Delivered.

delivered_status_mask = df["status"] == "Delivered"


invalid_delivered_date = delivered_status_mask & delivered_date.isna()

add_rejection_reason(
    invalid_delivered_date, "Delivered Date is missing or invalid for Delivered status"
)


# ============================================================
# 13. DATE ORDER VALIDATION
# ============================================================

# Expected Delivery Date cannot be before Ship Date.

invalid_expected_date_order = expected_delivery_date < ship_date_datetime

add_rejection_reason(
    invalid_expected_date_order, "Expected Delivery Date is before Ship Date"
)


# Delivered Date cannot be before Ship Date.
#
# This validation applies only to Delivered shipments.

invalid_delivered_date_order = (
    delivered_status_mask
    & delivered_date.notna()
    & (delivered_date < ship_date_datetime)
)

add_rejection_reason(invalid_delivered_date_order, "Delivered Date is before Ship Date")


# ============================================================
# 14. FREIGHT COST VALIDATION
# ============================================================

freight_cost_numeric = pd.to_numeric(
    df["freight_cost"],
    errors="coerce",
)


invalid_freight_cost = freight_cost_numeric.isna() | (freight_cost_numeric <= 0)

add_rejection_reason(invalid_freight_cost, "Invalid freight cost")


# Keep validated numeric freight cost

df["freight_cost"] = freight_cost_numeric


# ============================================================
# 15. CALCULATE DELAY DAYS
# ============================================================

# Delay days are calculated ONLY when status is Delivered.
#
# Delivered:
#     delay_days = Delivered Date - Expected Delivery Date
#
# Delivered late:
#     positive number
#
# Delivered on time / early:
#     0
#
# All other statuses:
#     NULL

delay_difference = (delivered_date - expected_delivery_date).dt.days


# Default delay_days to NULL for all records

df["delay_days"] = pd.NA


# Calculate delay ONLY for Delivered shipments

df.loc[delivered_status_mask, "delay_days"] = delay_difference[
    delivered_status_mask
].clip(lower=0)


# Keep as nullable integer

df["delay_days"] = df["delay_days"].astype("Int64")

# ============================================================
# 16. CREATE REJECTED SHIPMENTS DATASET
# ============================================================

Rejected_Shipments = df[reject_mask].copy()


# Add rejection reason

Rejected_Shipments["reason"] = rejection_reasons[reject_mask].str.strip()


# ============================================================
# 17. CREATE CLEAN SHIPMENTS DATASET
# ============================================================

Clean_Shipments = df[~reject_mask].copy()


# ============================================================
# 18. FORMAT DATES FOR OUTPUT
# ============================================================

# ------------------------------------------------------------
# CLEAN - Ship Date
# ------------------------------------------------------------

Clean_Shipments["ship_date"] = ship_date_datetime[~reject_mask].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# CLEAN - Expected Delivery Date
# ------------------------------------------------------------

Clean_Shipments["Expected Delivery Date"] = expected_delivery_date[
    ~reject_mask
].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# CLEAN - Delivered Date
# ------------------------------------------------------------

Clean_Shipments["Delivered Date"] = delivered_date[~reject_mask].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# REJECTED - Ship Date
# ------------------------------------------------------------

Rejected_Shipments["ship_date"] = ship_date_datetime[reject_mask].dt.strftime(
    "%d/%m/%Y"
)


# ------------------------------------------------------------
# REJECTED - Expected Delivery Date
# ------------------------------------------------------------

Rejected_Shipments["Expected Delivery Date"] = expected_delivery_date[
    reject_mask
].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# REJECTED - Delivered Date
# ------------------------------------------------------------

Rejected_Shipments["Delivered Date"] = delivered_date[reject_mask].dt.strftime(
    "%d/%m/%Y"
)


# ============================================================
# 19. DISPLAY CLEAN SHIPMENTS
# ============================================================

print("\n========== CLEAN SHIPMENTS ==========")

print(Clean_Shipments.to_string(index=False))


# ============================================================
# 20. DISPLAY REJECTED SHIPMENTS
# ============================================================

print("\n========== REJECTED SHIPMENTS ==========")

print(Rejected_Shipments.to_string(index=False))


# ============================================================
# 21. TRANSFORMATION SUMMARY
# ============================================================

print("\n========== TRANSFORMATION SUMMARY ==========")

print(f"Original records : {len(df)}")

print(f"Clean records    : {len(Clean_Shipments)}")

print(f"Rejected records : {len(Rejected_Shipments)}")


# ============================================================
# 22. FINAL STATUS SUMMARY
# ============================================================

print("\n========== FINAL STATUS VALUES ==========")

print(Clean_Shipments["status"].value_counts())


# ============================================================
# 23. REJECTION REASON SUMMARY
# ============================================================

print("\n========== REJECTION REASONS ==========")

if len(Rejected_Shipments) > 0:
    print(Rejected_Shipments["reason"].value_counts())
else:
    print("No rejected records.")


# ============================================================
# 24. CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs("output", exist_ok=True)


# ============================================================
# 25. SAVE CLEAN DATASET
# ============================================================

Clean_Shipments.to_csv("output/Clean_Shipments.csv", index=False)


# ============================================================
# 26. SAVE REJECTED DATASET
# ============================================================

Rejected_Shipments.to_csv("output/Rejected_Shipments.csv", index=False)


# ============================================================
# 27. PRINT OUTPUT FILES
# ============================================================

print("\nFiles created successfully:")

print(" - output/Clean_Shipments.csv")

print(" - output/Rejected_Shipments.csv")
