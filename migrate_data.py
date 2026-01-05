"""
Migration script to add is_active column to existing data.
"""
import csv
import os
from pathlib import Path
from storage import CSV_FILE, COLUMNS, sync_csv_to_sqlite

def migrate():
    if not CSV_FILE.exists():
        print("CSV file not found. Nothing to migrate.")
        return

    print(f"Migrating {CSV_FILE}...")
    
    # Read existing records
    records = []
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        records = list(reader)

    # Check if is_active already exists
    if "is_active" in fieldnames:
        print("is_active column already exists. Updating existing records to 0 if NA/missing.")
    
    # Update records
    updated_records = []
    for r in records:
        if "is_active" not in r or r["is_active"] == "NA" or not r["is_active"]:
            r["is_active"] = "0"
        updated_records.append(r)

    # Write back with new COLUMNS
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in updated_records:
            # Ensure all columns exist from the new COLUMNS list
            row = {col: r.get(col, "NA") for col in COLUMNS}
            writer.writerow(row)

    print(f"Successfully updated {len(updated_records)} records in CSV.")
    
    # Sync to SQLite
    from storage import SQLITE_FILE
    if SQLITE_FILE.exists():
        print(f"Deleting old database {SQLITE_FILE} to update schema...")
        os.remove(SQLITE_FILE)
        
    print("Syncing to SQLite...")
    sync_csv_to_sqlite()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
