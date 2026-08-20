# Akhila - Shipment Data Cleaning & PostgreSQL Loading

## Overview

This document describes the shipment data cleaning, validation, transformation, rejection handling, and PostgreSQL loading workflow implemented by **Akhila**.

The pipeline:

- Reads raw shipment data from CSV
- Cleans and standardizes shipment attributes
- Validates carriers, dates, status, and freight cost
- Calculates `delay_days` only for Delivered shipments
- Keeps `delay_days` as `NULL` for other statuses
- Separates clean and rejected records
- Stores rejection reasons for rejected records
- Loads and synchronizes data with PostgreSQL
- Updates existing shipments instead of creating duplicates
- Moves shipments between clean and rejected tables when validation status changes
- Maintains `created_at`, `updated_at`, and `rejected_at` timestamps
- Uses database transactions for consistent loading

---

# 1. Project Environment Setup

The project uses a Python virtual environment to isolate dependencies.

## Create Virtual Environment

From the project root:

```bash
python3 -m venv .venv

Activate Virtual Environment
Linux/macOS
source .venv/bin/activate
Windows
.venv\Scripts\activate
Install Dependencies
pip install -r requirements.txt
2. Environment Variables

Create a .env file in the project root:

POSTGRES_HOST=<POSTGRES_IP>
POSTGRES_PORT=5432
POSTGRES_DB=shipment_db
POSTGRES_USER=<POSTGRES_USERNAME>
POSTGRES_PASSWORD=<POSTGRES_PASSWORD>

Do not commit .env to GitHub.

The .gitignore file should contain:

.env
.venv/
3. Source Data

Raw shipment data is stored in:

data/raw_shipments.csv

Expected columns:

shipment_id
carrier
ship_date
status
origin
destination
freight_cost
Expected Delivery Date
Delivered Date
4. Shipment Cleaning

Run:

python shipment_cleaning.py

The cleaning process:

Standardizes carrier names
Validates allowed carriers
Cleans and validates shipment dates
Standardizes shipment statuses
Converts blank status to Accepted
Validates Expected Delivery Date
Validates Delivered Date for Delivered shipments
Validates date ordering
Validates freight cost
Calculates delay_days
Generates rejection reasons
Separates clean and rejected records

Output files:

output/Clean_Shipments.csv
output/Rejected_Shipments.csv
5. Delay Days Logic

delay_days is calculated only when:

status = Delivered

Formula:

Delivered Date - Expected Delivery Date

If the shipment is delivered late, delay_days contains the number of delayed days.

If the shipment is delivered on time or early:

delay_days = 0

For all other statuses:

delay_days = NULL
6. Rejection Handling

Invalid records are stored in:

output/Rejected_Shipments.csv

Each rejected record contains a reason column.

If a record fails multiple validations, all applicable reasons are stored in the reason field.

Rejected records are loaded into the PostgreSQL table:

rejected_shipments
7. PostgreSQL Tables

The pipeline uses two PostgreSQL tables.

shipments

Stores valid shipment records.

Main fields:

shipment_id
carrier
ship_date
status
origin
destination
Expected Delivery Date
Delivered Date
delay_days
freight_cost
created_at
updated_at
rejected_shipments

Stores rejected shipment records.

Main fields:

shipment_id
carrier
ship_date
status
origin
destination
Expected Delivery Date
Delivered Date
delay_days
reason
rejected_at

Both tables use shipment_id as a unique identifier to prevent duplicate records.

8. PostgreSQL Synchronization

The PostgreSQL loader is incremental. It does not truncate the tables during normal execution.

Run:

python postgres_loader.py

The loader synchronizes the current CSV state with PostgreSQL.

New clean shipment
CSV → shipments → INSERT
Existing clean shipment
CSV → shipments → UPDATE

Existing records are updated instead of creating duplicates.

New rejected shipment
CSV → rejected_shipments → INSERT
Existing rejected shipment
CSV → rejected_shipments → UPDATE
Rejected → Clean

When a previously rejected shipment becomes valid:

Clean CSV
   ↓
shipments → INSERT/UPDATE
   ↓
Remove shipment from rejected_shipments
Clean → Rejected

When a previously clean shipment fails validation:

Rejected CSV
   ↓
rejected_shipments → INSERT/UPDATE
   ↓
Remove shipment from shipments

This keeps the two PostgreSQL tables synchronized with the latest validation state of the source data.

9. PostgreSQL Timestamps

The shipments table maintains:

created_at
updated_at
created_at records when the shipment was first inserted.
updated_at changes whenever an existing shipment is updated.

The rejected_shipments table maintains:

rejected_at

PostgreSQL automatically sets rejected_at using:

DEFAULT CURRENT_TIMESTAMP

The Python loader does not provide the rejected_at value.

The updated_at column is maintained using a PostgreSQL trigger.

10. Complete Pipeline

From the project root:

Step 1 - Activate environment
source .venv/bin/activate
Step 2 - Clean and validate data
python shipment_cleaning.py
Step 3 - Synchronize with PostgreSQL
python postgres_loader.py
11. Verify PostgreSQL Data

Connect to PostgreSQL:

sudo -u postgres psql -d shipment_db

Check clean shipments:

SELECT shipment_id, status, delay_days, created_at, updated_at
FROM shipments
ORDER BY shipment_id;

Check rejected shipments:

SELECT shipment_id, status, reason, rejected_at
FROM rejected_shipments
ORDER BY shipment_id;

Check for duplicate shipment IDs:

SELECT shipment_id, COUNT(*)
FROM shipments
GROUP BY shipment_id
HAVING COUNT(*) > 1;

The duplicate query should return zero rows.

12. Important Notes
Do not commit .env to GitHub.
Do not use TRUNCATE as part of the normal pipeline.
Run shipment_cleaning.py before postgres_loader.py.
PostgreSQL manages created_at, updated_at, and rejected_at.
Existing shipment records are updated rather than duplicated.
New records are inserted incrementally.
Shipments can move between shipments and rejected_shipments when their validation status changes.
Database transactions ensure that a failed load does not leave a partial update.