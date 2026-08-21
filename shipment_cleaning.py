import pandas as pd


# ============================================================
# 1. READ SOURCE DATA
# ============================================================

df = pd.read_csv("data/raw_shipments.csv")


# ============================================================
# 2. CREATE REJECTION MASK
# ============================================================

reject_mask = pd.Series(False, index=df.index)


# ============================================================
# 3. CARRIER TRANSFORMATION
# ============================================================

# Remove leading/trailing spaces
# Convert carrier names to uppercase

df["carrier"] = df["carrier"].astype("string").str.strip().str.upper()


# Allowed carriers

valid_carriers = ["DHL", "BLUEDART", "FEDEX"]


# Identify invalid carriers

invalid_carrier = ~df["carrier"].isin(valid_carriers)


# Add invalid carriers to rejection mask

reject_mask |= invalid_carrier


# ============================================================
# 4. SHIP_DATE TRANSFORMATION
# ============================================================

# Remove leading/trailing spaces
# Convert "-" to "/"

df["ship_date"] = (
    df["ship_date"].astype("string").str.strip().str.replace("-", "/", regex=False)
)


# Convert source date to datetime
#
# format="mixed" allows multiple date formats.
#
# Examples:
# 1/27/2024
# 04-06-2024
# 06-12-2024

ship_date_datetime = pd.to_datetime(
    df["ship_date"], format="mixed", dayfirst=False, errors="coerce"
)


# Reject invalid ship dates

invalid_ship_date = ship_date_datetime.isna()

reject_mask |= invalid_ship_date


# ============================================================
# 5. STATUS TRANSFORMATION
# ============================================================

# Remove leading/trailing spaces
# Convert to uppercase

df["status"] = df["status"].astype("string").str.strip().str.upper()


# Standardize status values

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
    # PENDING
    "PENDING": "Pending",
    # ACCEPTED
    "ACCEPTED": "Accepted",
}


df["status"] = df["status"].replace(status_mapping)


# ============================================================
# 6. STATUS VALIDATION
# ============================================================

valid_statuses = ["Delayed", "Delivered", "In Transit", "Pending", "Accepted"]


# Empty / NULL status

empty_status = df["status"].isna() | (df["status"].str.strip() == "")


# Invalid status

invalid_status = ~df["status"].isin(valid_statuses)


# Add status validation to rejection mask

reject_mask |= empty_status
reject_mask |= invalid_status


# ============================================================
# 7. EXPECTED DELIVERY DATE TRANSFORMATION
# ============================================================

df["Expected Delivery Date"] = (
    df["Expected Delivery Date"]
    .astype("string")
    .str.strip()
    .str.replace("-", "/", regex=False)
)


# Convert Expected Delivery Date to datetime

expected_delivery_date = pd.to_datetime(
    df["Expected Delivery Date"], format="mixed", dayfirst=False, errors="coerce"
)


# Reject invalid Expected Delivery Date

invalid_expected_delivery_date = expected_delivery_date.isna()

reject_mask |= invalid_expected_delivery_date


# ============================================================
# 8. DELIVERED DATE TRANSFORMATION
# ============================================================

df["Delivered Date"] = (
    df["Delivered Date"].astype("string").str.strip().str.replace("-", "/", regex=False)
)


# Convert Delivered Date to datetime

delivered_date = pd.to_datetime(
    df["Delivered Date"], format="mixed", dayfirst=False, errors="coerce"
)


# ============================================================
# 9. DELIVERED DATE VALIDATION
# ============================================================

# Delivered Date is required ONLY when
# status is Delivered.

delivered_status_mask = df["status"] == "Delivered"


# If status is Delivered and Delivered Date
# is missing or invalid, reject the record.

invalid_delivered_date = delivered_status_mask & delivered_date.isna()

reject_mask |= invalid_delivered_date


# ============================================================
# 10. DATE ORDER VALIDATION
# ============================================================

# Expected Delivery Date cannot be older
# than Ship Date.
#
# Example:
#
# Ship Date              = 15/06/2024
# Expected Delivery Date = 27/01/2024
#
# This record is rejected.

invalid_expected_date_order = expected_delivery_date < ship_date_datetime

reject_mask |= invalid_expected_date_order


# ------------------------------------------------------------
# Delivered Date cannot be before Ship Date.
#
# This validation is required only for
# Delivered shipments.
# ------------------------------------------------------------

invalid_delivered_date_order = (
    delivered_status_mask
    & delivered_date.notna()
    & (delivered_date < ship_date_datetime)
)

reject_mask |= invalid_delivered_date_order


# ============================================================
# 11. FREIGHT COST VALIDATION
# ============================================================

# Convert freight_cost to numeric.
#
# Invalid values such as:
#
# abc
# xyz
# empty
#
# become NaN.

freight_cost_numeric = pd.to_numeric(df["freight_cost"], errors="coerce")


# Reject:
#
# - non-numeric values
# - NULL/empty values
# - zero
# - negative values

invalid_freight_cost = freight_cost_numeric.isna() | (freight_cost_numeric <= 0)


reject_mask |= invalid_freight_cost


# Keep validated numeric freight cost

df["freight_cost"] = freight_cost_numeric


# ============================================================
# 12. CALCULATE delay_days
# ============================================================

# Delay days are calculated ONLY when
# status is Delivered.
#
# Formula:
#
# delay_days =
# Delivered Date - Expected Delivery Date
#
# If Delivered Date is later than Expected Delivery Date:
#     delay_days = number of delayed days
#
# If Delivered Date is on or before Expected Delivery Date:
#     delay_days = 0
#
# For all other statuses:
#     delay_days = 0


delay_difference = (delivered_date - expected_delivery_date).dt.days


# Default delay_days to 0 for all records

df["delay_days"] = 0


# Calculate delay ONLY for Delivered shipments

df.loc[delivered_status_mask, "delay_days"] = delay_difference[
    delivered_status_mask
].clip(lower=0)


# Keep delay_days as integer

df["delay_days"] = df["delay_days"].astype("Int64")


# ============================================================
# 13. CREATE REJECTED_SHIPMENTS DATASET
# ============================================================

Rejected_Shipments = df[reject_mask].copy()


# ============================================================
# 14. CREATE CLEAN_SHIPMENTS DATASET
# ============================================================

Clean_Shipments = df[~reject_mask].copy()


# ============================================================
# 15. FORMAT DATES FOR OUTPUT
# ============================================================

# ------------------------------------------------------------
# Clean dataset - Ship Date
# ------------------------------------------------------------

Clean_Shipments["ship_date"] = ship_date_datetime[~reject_mask].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# Clean dataset - Expected Delivery Date
# ------------------------------------------------------------

Clean_Shipments["Expected Delivery Date"] = expected_delivery_date[
    ~reject_mask
].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# Clean dataset - Delivered Date
# ------------------------------------------------------------

Clean_Shipments["Delivered Date"] = delivered_date[~reject_mask].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# Rejected dataset - Ship Date
# ------------------------------------------------------------

Rejected_Shipments["ship_date"] = ship_date_datetime[reject_mask].dt.strftime(
    "%d/%m/%Y"
)


# ------------------------------------------------------------
# Rejected dataset - Expected Delivery Date
# ------------------------------------------------------------

Rejected_Shipments["Expected Delivery Date"] = expected_delivery_date[
    reject_mask
].dt.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# Rejected dataset - Delivered Date
# ------------------------------------------------------------

Rejected_Shipments["Delivered Date"] = delivered_date[reject_mask].dt.strftime(
    "%d/%m/%Y"
)


# ============================================================
# 16. DISPLAY CLEAN RECORDS
# ============================================================

print("\n========== CLEAN SHIPMENTS ==========")

print(Clean_Shipments)


# ============================================================
# 17. DISPLAY REJECTED RECORDS
# ============================================================

print("\n========== REJECTED SHIPMENTS ==========")

print(Rejected_Shipments)


# ============================================================
# 18. PRINT TRANSFORMATION SUMMARY
# ============================================================

print("\n========== TRANSFORMATION SUMMARY ==========")

print(f"Original records : {len(df)}")
print(f"Clean records    : {len(Clean_Shipments)}")
print(f"Rejected records : {len(Rejected_Shipments)}")


# ============================================================
# 19. SAVE CLEAN DATASET
# ============================================================

Clean_Shipments.to_csv("output/Clean_Shipments.csv", index=False)


# ============================================================
# 20. SAVE REJECTED DATASET
# ============================================================

Rejected_Shipments.to_csv("output/Rejected_Shipments.csv", index=False)


# ============================================================
# 21. PRINT OUTPUT FILES
# ============================================================

print("\nFiles created:")

print(" - output/Clean_Shipments.csv")
print(" - output/Rejected_Shipments.csv")
