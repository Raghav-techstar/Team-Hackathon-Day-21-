import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.dialects.postgresql import insert
from urllib.parse import quote_plus


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


# ============================================================
# 2. VALIDATE ENVIRONMENT VARIABLES
# ============================================================

required_variables = {
    "POSTGRES_HOST": POSTGRES_HOST,
    "POSTGRES_PORT": POSTGRES_PORT,
    "POSTGRES_DB": POSTGRES_DB,
    "POSTGRES_USER": POSTGRES_USER,
    "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
}

missing_variables = [name for name, value in required_variables.items() if not value]

if missing_variables:
    raise ValueError(
        "Missing PostgreSQL environment variables: " + ", ".join(missing_variables)
    )


# ============================================================
# 3. CREATE DATABASE CONNECTION
# ============================================================

# Encode the password so special characters such as
# @, #, %, etc. do not break the connection URL.

encoded_password = quote_plus(POSTGRES_PASSWORD)

DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{POSTGRES_USER}:{encoded_password}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL)


# ============================================================
# 4. DEFINE REQUIRED CLEAN COLUMNS
# ============================================================

required_clean_columns = [
    "shipment_id",
    "carrier",
    "ship_date",
    "status",
    "origin",
    "destination",
    "freight_cost",
    "Expected Delivery Date",
    "Delivered Date",
    "delay_days",
]


# ============================================================
# 5. DEFINE REQUIRED REJECTED COLUMNS
# ============================================================

required_rejected_columns = [
    "shipment_id",
    "carrier",
    "ship_date",
    "status",
    "origin",
    "destination",
    "freight_cost",
    "Expected Delivery Date",
    "Delivered Date",
    "delay_days",
    "reason",
]


# ============================================================
# 6. LOAD CLEAN SHIPMENTS CSV
# ============================================================

clean_file = "output/Clean_Shipments.csv"

Clean_Shipments = pd.read_csv(clean_file)

print("\n========== CLEAN SHIPMENTS ==========")
print(f"Records found: {len(Clean_Shipments)}")


# ============================================================
# 7. VALIDATE CLEAN SHIPMENT COLUMNS
# ============================================================

missing_clean_columns = [
    column for column in required_clean_columns if column not in Clean_Shipments.columns
]

if missing_clean_columns:
    raise ValueError(
        "Missing columns in Clean_Shipments.csv: " + ", ".join(missing_clean_columns)
    )


# ============================================================
# 8. KEEP ONLY EXPECTED CLEAN COLUMNS
# ============================================================

Clean_Shipments = Clean_Shipments[required_clean_columns].copy()


# ============================================================
# 9. CONVERT CLEAN DATA TYPES
# ============================================================

# ------------------------------------------------------------
# Ship Date
# ------------------------------------------------------------

Clean_Shipments["ship_date"] = pd.to_datetime(
    Clean_Shipments["ship_date"],
    format="%d/%m/%Y",
    errors="coerce",
).dt.date


# ------------------------------------------------------------
# Expected Delivery Date
# ------------------------------------------------------------

Clean_Shipments["Expected Delivery Date"] = pd.to_datetime(
    Clean_Shipments["Expected Delivery Date"],
    format="%d/%m/%Y",
    errors="coerce",
).dt.date


# ------------------------------------------------------------
# Delivered Date
# ------------------------------------------------------------

Clean_Shipments["Delivered Date"] = pd.to_datetime(
    Clean_Shipments["Delivered Date"],
    format="%d/%m/%Y",
    errors="coerce",
).dt.date


# ------------------------------------------------------------
# Freight Cost
# ------------------------------------------------------------

Clean_Shipments["freight_cost"] = pd.to_numeric(
    Clean_Shipments["freight_cost"],
    errors="coerce",
)


# ------------------------------------------------------------
# Delay Days
# ------------------------------------------------------------

# Nullable integer is important because
# non-Delivered shipments have NULL delay_days.

Clean_Shipments["delay_days"] = pd.to_numeric(
    Clean_Shipments["delay_days"],
    errors="coerce",
).astype("Int64")


# ============================================================
# 10. LOAD REJECTED SHIPMENTS CSV
# ============================================================

rejected_file = "output/Rejected_Shipments.csv"

Rejected_Shipments = pd.read_csv(
    rejected_file,
    dtype=str,
    keep_default_na=False,
)

print("\n========== REJECTED SHIPMENTS ==========")
print(f"Records found: {len(Rejected_Shipments)}")


# ============================================================
# 11. VALIDATE REJECTED SHIPMENT COLUMNS
# ============================================================

missing_rejected_columns = [
    column
    for column in required_rejected_columns
    if column not in Rejected_Shipments.columns
]

if missing_rejected_columns:
    raise ValueError(
        "Missing columns in Rejected_Shipments.csv: "
        + ", ".join(missing_rejected_columns)
    )


# ============================================================
# 12. KEEP ONLY REJECTED CSV COLUMNS
# ============================================================

# rejected_at is intentionally NOT included.
#
# PostgreSQL automatically generates rejected_at using:
#
# DEFAULT CURRENT_TIMESTAMP

Rejected_Shipments = Rejected_Shipments[required_rejected_columns].copy()


# Keep rejected data as VARCHAR-compatible strings

Rejected_Shipments = Rejected_Shipments.astype(str)


# ============================================================
# 13. REMOVE DUPLICATES WITHIN CSV FILES
# ============================================================

# If the same shipment_id appears multiple times
# in the same CSV, keep only the first occurrence.

clean_duplicate_count = Clean_Shipments["shipment_id"].duplicated().sum()

rejected_duplicate_count = Rejected_Shipments["shipment_id"].duplicated().sum()

if clean_duplicate_count > 0:
    print(f"Duplicate clean shipment IDs found in CSV: {clean_duplicate_count}")

    Clean_Shipments = Clean_Shipments.drop_duplicates(
        subset=["shipment_id"],
        keep="first",
    )


if rejected_duplicate_count > 0:
    print(f"Duplicate rejected shipment IDs found in CSV: {rejected_duplicate_count}")

    Rejected_Shipments = Rejected_Shipments.drop_duplicates(
        subset=["shipment_id"],
        keep="first",
    )


# ============================================================
# 14. CHECK FOR IDs APPEARING IN BOTH CSV FILES
# ============================================================

clean_ids = set(Clean_Shipments["shipment_id"].dropna().astype(str))

rejected_ids = set(Rejected_Shipments["shipment_id"].dropna().astype(str))

overlapping_ids = clean_ids.intersection(rejected_ids)

if overlapping_ids:
    raise ValueError(
        "The same shipment_id appears in both clean and rejected "
        f"CSV files: {sorted(overlapping_ids)}"
    )


# ============================================================
# 15. LOAD TABLE METADATA
# ============================================================

metadata = MetaData()

shipments_table = Table(
    "shipments",
    metadata,
    autoload_with=engine,
)

rejected_shipments_table = Table(
    "rejected_shipments",
    metadata,
    autoload_with=engine,
)


# ============================================================
# 16. START DATABASE TRANSACTION
# ============================================================

try:
    with engine.begin() as connection:
        # ====================================================
        # 16A. GET SHIPMENT IDS FROM CURRENT CSV
        # ====================================================

        clean_ids = Clean_Shipments["shipment_id"].tolist()

        rejected_ids = Rejected_Shipments["shipment_id"].tolist()

        # ====================================================
        # 16B. MOVE CLEAN RECORDS OUT OF REJECTED TABLE
        # ====================================================

        clean_moved_from_rejected = 0

        if clean_ids:
            delete_rejected_statement = rejected_shipments_table.delete().where(
                rejected_shipments_table.c.shipment_id.in_(clean_ids)
            )

            result = connection.execute(delete_rejected_statement)

            clean_moved_from_rejected = result.rowcount or 0

        print(
            f"Removed {clean_moved_from_rejected} "
            f"records from rejected_shipments because "
            f"they are now clean."
        )

        # ====================================================
        # 16C. UPSERT CLEAN SHIPMENTS
        # ====================================================

        clean_records = Clean_Shipments.to_dict(orient="records")

        clean_inserted = 0
        clean_updated = 0

        if clean_records:
            clean_statement = insert(shipments_table).values(clean_records)

            clean_statement = clean_statement.on_conflict_do_update(
                index_elements=["shipment_id"],
                set_={
                    "carrier": clean_statement.excluded.carrier,
                    "ship_date": clean_statement.excluded.ship_date,
                    "status": clean_statement.excluded.status,
                    "origin": clean_statement.excluded.origin,
                    "destination": clean_statement.excluded.destination,
                    "freight_cost": clean_statement.excluded.freight_cost,
                    "Expected Delivery Date": clean_statement.excluded[
                        "Expected Delivery Date"
                    ],
                    "Delivered Date": clean_statement.excluded["Delivered Date"],
                    "delay_days": clean_statement.excluded.delay_days,
                    "updated_at": clean_statement.excluded.updated_at,
                },
            ).returning(shipments_table.c.shipment_id)

            result = connection.execute(clean_statement)

            inserted_or_updated_ids = result.fetchall()

            # PostgreSQL returns one row for both
            # INSERT and UPDATE, so this count represents
            # records successfully synchronized.

            clean_inserted = len(inserted_or_updated_ids)

            clean_updated = clean_inserted

        print(
            f"Successfully synchronized {clean_inserted} clean records into shipments."
        )

        # ====================================================
        # 16D. MOVE REJECTED RECORDS OUT OF CLEAN TABLE
        # ====================================================

        rejected_moved_from_clean = 0

        if rejected_ids:
            delete_clean_statement = shipments_table.delete().where(
                shipments_table.c.shipment_id.in_(rejected_ids)
            )

            result = connection.execute(delete_clean_statement)

            rejected_moved_from_clean = result.rowcount or 0

        print(
            f"Removed {rejected_moved_from_clean} "
            f"records from shipments because "
            f"they are now rejected."
        )

        # ====================================================
        # 16E. UPSERT REJECTED SHIPMENTS
        # ====================================================

        rejected_records = Rejected_Shipments.to_dict(orient="records")

        rejected_synchronized = 0

        if rejected_records:
            rejected_statement = insert(rejected_shipments_table).values(
                rejected_records
            )

            rejected_statement = rejected_statement.on_conflict_do_update(
                index_elements=["shipment_id"],
                set_={
                    "carrier": rejected_statement.excluded.carrier,
                    "ship_date": rejected_statement.excluded.ship_date,
                    "status": rejected_statement.excluded.status,
                    "origin": rejected_statement.excluded.origin,
                    "destination": rejected_statement.excluded.destination,
                    "freight_cost": rejected_statement.excluded.freight_cost,
                    "Expected Delivery Date": rejected_statement.excluded[
                        "Expected Delivery Date"
                    ],
                    "Delivered Date": rejected_statement.excluded["Delivered Date"],
                    "delay_days": rejected_statement.excluded.delay_days,
                    "reason": rejected_statement.excluded.reason,
                },
            ).returning(rejected_shipments_table.c.shipment_id)

            result = connection.execute(rejected_statement)

            rejected_inserted_or_updated = result.fetchall()

            rejected_synchronized = len(rejected_inserted_or_updated)

        print(
            f"Successfully synchronized "
            f"{rejected_synchronized} rejected records "
            f"into rejected_shipments."
        )

    # ========================================================
    # 17. TRANSACTION SUCCESSFUL
    # ========================================================

    print("\n========== DATABASE LOAD COMPLETE ==========")
    print("Transaction committed successfully.")


except Exception as error:
    # ========================================================
    # 18. TRANSACTION FAILED
    # ========================================================

    print("\n========== DATABASE LOAD FAILED ==========")
    print(f"Error: {error}")
    print("Transaction rolled back.")

    raise


finally:
    # ========================================================
    # 19. CLOSE DATABASE CONNECTION
    # ========================================================

    engine.dispose()
