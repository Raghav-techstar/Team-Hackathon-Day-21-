import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
# 2. CREATE DATABASE CONNECTION
# ============================================================

encoded_password = quote_plus(POSTGRES_PASSWORD)

DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{POSTGRES_USER}:{encoded_password}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
engine = create_engine(DATABASE_URL)


# ============================================================
# 3. LOAD CLEAN SHIPMENTS
# ============================================================

clean_file = "output/Clean_Shipments.csv"

Clean_Shipments = pd.read_csv(clean_file)

print("\n========== CLEAN SHIPMENTS ==========")
print(f"Records found: {len(Clean_Shipments)}")


# ============================================================
# 4. CONVERT CLEAN DATA TYPES
# ============================================================

Clean_Shipments["ship_date"] = pd.to_datetime(
    Clean_Shipments["ship_date"],
    format="%d/%m/%Y",
    errors="coerce",
).dt.date

Clean_Shipments["Expected Delivery Date"] = pd.to_datetime(
    Clean_Shipments["Expected Delivery Date"],
    format="%d/%m/%Y",
    errors="coerce",
).dt.date

Clean_Shipments["Delivered Date"] = pd.to_datetime(
    Clean_Shipments["Delivered Date"],
    format="%d/%m/%Y",
    errors="coerce",
).dt.date

Clean_Shipments["freight_cost"] = pd.to_numeric(
    Clean_Shipments["freight_cost"],
    errors="coerce",
)

Clean_Shipments["delay_days"] = pd.to_numeric(
    Clean_Shipments["delay_days"],
    errors="coerce",
).astype("Int64")


# ============================================================
# 5. LOAD CLEAN DATA
# ============================================================

Clean_Shipments.to_sql(
    "shipments",
    engine,
    if_exists="append",
    index=False,
)

print(f"Successfully loaded {len(Clean_Shipments)} records into shipments.")


# ============================================================
# 6. LOAD REJECTED SHIPMENTS
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
# 7. KEEP REJECTED DATA AS VARCHAR
# ============================================================

Rejected_Shipments = Rejected_Shipments.astype(str)


# ============================================================
# 8. LOAD REJECTED DATA
# ============================================================

Rejected_Shipments.to_sql(
    "rejected_shipments",
    engine,
    if_exists="append",
    index=False,
)

print(f"Successfully loaded {len(Rejected_Shipments)} records into rejected_shipments.")


# ============================================================
# 9. CLOSE CONNECTION
# ============================================================

engine.dispose()

print("\n========== DATABASE LOAD COMPLETE ==========")
