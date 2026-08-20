# Akhila - Shipment Data Cleaning & PostgreSQL Loading


## Overview


This document describes the shipment data cleaning, validation, transformation, rejection handling, and PostgreSQL loading workflow implemented by **Akhila**.


The pipeline:


- Reads raw shipment data from CSV
- Cleans and standardizes shipment attributes
- Validates carriers, dates, status, freight cost, and shipment IDs
- Rejects records with missing or duplicate shipment IDs
- Calculates `delay_days` only for Delivered shipments
- Keeps `delay_days` as `NULL` for other statuses
- Separates clean and rejected records
- Stores rejection reasons for rejected records
- Loads and synchronizes data with PostgreSQL
- Updates existing shipments instead of creating duplicates
- Inserts new records incrementally
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

The Delivered Date column name must match the expected source column name exactly.

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
Validates shipment IDs
Rejects records with missing shipment IDs
Rejects duplicate shipment IDs
Calculates delay_days
Generates rejection reasons
Separates clean and rejected records

The cleaning script generates:

output/Clean_Shipments.csv
output/Rejected_Shipments.csv
5. Delay Days Logic

delay_days is calculated only when:

status = Delivered

Formula:

delay_days = Delivered Date - Expected Delivery Date

If the shipment is delivered late, delay_days contains the number of delayed days.

If the shipment is delivered on time or early:

delay_days = 0

For all other statuses:

delay_days = NULL

Example:

Delivered   → delay_days = 3
Delivered   → delay_days = 0
In Transit  → delay_days = NULL
Pending     → delay_days = NULL
Delayed     → delay_days = NULL
Accepted    → delay_days = NULL
6. Rejection Handling

Invalid records are stored in:

output/Rejected_Shipments.csv

Each rejected record contains a reason column.

If a record fails multiple validations, all applicable reasons are combined in the reason field.

For example:

Expected Delivery Date is missing or invalid;
Delivered Date is missing or invalid for Delivered status

Rejected records are loaded into the PostgreSQL table:

rejected_shipments
7. PostgreSQL Tables

The pipeline uses two PostgreSQL tables:

shipments
rejected_shipments
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
freight_cost
Expected Delivery Date
Delivered Date
delay_days
reason
rejected_at

Both tables use shipment_id as a unique identifier.

PostgreSQL has unique constraints on shipment_id to prevent duplicate records from being stored in either table.

The cleaning process identifies missing and duplicate shipment IDs before loading data into PostgreSQL.

8. PostgreSQL Synchronization

The PostgreSQL loader performs incremental synchronization.

It does not truncate the tables during normal execution.

Run:

python postgres_loader.py

The loader synchronizes the current clean and rejected CSV state with PostgreSQL using shipment_id as the unique identifier.

New Clean Shipment

If a shipment does not already exist in shipments:

Clean CSV
    ↓
shipments
    ↓
INSERT
Existing Clean Shipment

If the shipment already exists in shipments:

Clean CSV
    ↓
Existing shipment_id
    ↓
UPDATE shipments

The existing record is updated instead of creating a duplicate.

New Rejected Shipment

If a shipment does not already exist in rejected_shipments:

Rejected CSV
    ↓
rejected_shipments
    ↓
INSERT
Existing Rejected Shipment

If the shipment already exists in rejected_shipments:

Rejected CSV
    ↓
Existing shipment_id
    ↓
UPDATE rejected_shipments
Rejected → Clean

If a previously rejected shipment becomes valid after the source data is corrected:

rejected_shipments
    ↓
REMOVE
    ↓
shipments
    ↓
INSERT / UPDATE

The shipment is removed from rejected_shipments and synchronized into shipments.

Clean → Rejected

If a previously valid shipment becomes invalid after the source data changes:

shipments
    ↓
REMOVE
    ↓
rejected_shipments
    ↓
INSERT / UPDATE

The shipment is removed from shipments and synchronized into rejected_shipments.

This keeps the two PostgreSQL tables synchronized with the latest validation state of the source data.

The loader does not perform a full database reload during normal execution.

Therefore:

New records are inserted
Existing records are updated
Unchanged records remain unchanged
Clean records can move to rejected
Rejected records can move back to clean
Duplicate database records are prevented
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

10. PostgreSQL Update Trigger

The shipments table uses a PostgreSQL trigger to automatically update updated_at whenever an existing shipment record is modified.

Function:

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

Trigger:

CREATE TRIGGER shipments_updated_at_trigger
BEFORE UPDATE ON shipments
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

This means:

New shipment
    ↓
created_at = insertion time
updated_at = insertion time

When the shipment is updated:

created_at = remains unchanged
updated_at = current timestamp
11. Database Transactions

The PostgreSQL loader performs synchronization inside a database transaction.

If all operations succeed:

Transaction → COMMIT

If an error occurs:

Transaction → ROLLBACK

This prevents a partial synchronization where only some shipment records are updated.

The loader either completes the synchronization successfully or rolls back the transaction when an error occurs.

12. Complete Pipeline

From the project root:

Step 1 - Activate Environment

Linux/macOS:

source .venv/bin/activate

Windows:

.venv\Scripts\activate
Step 2 - Clean and Validate Data
python shipment_cleaning.py

This reads:

data/raw_shipments.csv

and generates:

output/Clean_Shipments.csv
output/Rejected_Shipments.csv
Step 3 - Synchronize with PostgreSQL
python postgres_loader.py

The loader synchronizes the generated clean and rejected datasets with PostgreSQL.

13. Verify PostgreSQL Data

Connect to PostgreSQL:

sudo -u postgres psql -d shipment_db
Check Clean Shipments
SELECT
    shipment_id,
    status,
    delay_days,
    created_at,
    updated_at
FROM shipments
ORDER BY shipment_id;
Check Rejected Shipments
SELECT
    shipment_id,
    status,
    reason,
    rejected_at
FROM rejected_shipments
ORDER BY shipment_id;
Check for Duplicate Shipment IDs in Shipments
SELECT
    shipment_id,
    COUNT(*)
FROM shipments
GROUP BY shipment_id
HAVING COUNT(*) > 1;

The query should return zero rows.

Check for Duplicate Shipment IDs in Rejected Shipments
SELECT
    shipment_id,
    COUNT(*)
FROM rejected_shipments
GROUP BY shipment_id
HAVING COUNT(*) > 1;

The query should return zero rows.

14. Important Notes
Do not commit .env to GitHub.
Do not use TRUNCATE as part of the normal pipeline.
Run shipment_cleaning.py before postgres_loader.py.
PostgreSQL manages created_at, updated_at, and rejected_at.
Existing shipment records are updated rather than duplicated.
New records are inserted incrementally.
Shipments can move between shipments and rejected_shipments when their validation status changes.
Database transactions ensure that a failed load does not leave a partial update.