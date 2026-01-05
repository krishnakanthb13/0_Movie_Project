"""
Movie Library Project - Storage Layer
Handles CSV and SQLite storage operations.
"""

import csv
import sqlite3
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from config import CSV_FILE, SQLITE_FILE, DATA_DIR

logger = logging.getLogger(__name__)

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# SCHEMA DEFINITION
# =============================================================================

COLUMNS = [
    # Core identifiers
    "uuid",
    "file_name",
    "directory",
    "full_path",
    "is_active", # 1 to enrich, 0 to ignore
    
    # Parsed from filename
    "extracted_name",
    "extracted_year",
    
    # AI enrichment (Gemini)
    "ai_title",
    "ai_year",
    "imdb_id",
    
    # OMDb metadata
    "title",
    "year",
    "genre",
    "director",
    "actors",
    "plot",
    "runtime",
    "language",
    "country",
    "awards",
    "poster",
    "imdb_rating",
    "box_office",
    
    # Metadata
    "created_at",
    "updated_at",
]

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
    uuid            TEXT PRIMARY KEY,
    file_name       TEXT NOT NULL,
    directory       TEXT NOT NULL,
    full_path       TEXT NOT NULL UNIQUE,
    is_active       INTEGER DEFAULT 0,
    
    extracted_name  TEXT DEFAULT 'NA',
    extracted_year  TEXT DEFAULT 'NA',
    
    ai_title        TEXT DEFAULT 'NA',
    ai_year         TEXT DEFAULT 'NA',
    imdb_id         TEXT DEFAULT 'NA',
    
    title           TEXT DEFAULT 'NA',
    year            TEXT DEFAULT 'NA',
    genre           TEXT DEFAULT 'NA',
    director        TEXT DEFAULT 'NA',
    actors          TEXT DEFAULT 'NA',
    plot            TEXT DEFAULT 'NA',
    runtime         TEXT DEFAULT 'NA',
    language        TEXT DEFAULT 'NA',
    country         TEXT DEFAULT 'NA',
    awards          TEXT DEFAULT 'NA',
    poster          TEXT DEFAULT 'NA',
    imdb_rating     TEXT DEFAULT 'NA',
    box_office      TEXT DEFAULT 'NA',
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_full_path ON movies(full_path);
CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id);
"""


# =============================================================================
# CSV OPERATIONS
# =============================================================================

def init_csv() -> None:
    """Initialize CSV file with headers if it doesn't exist."""
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
        logger.info(f"Created CSV file: {CSV_FILE}")


def read_csv() -> List[Dict]:
    """Read all records from CSV."""
    init_csv()
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_existing_paths_csv() -> set:
    """Get set of all existing full_path values from CSV."""
    records = read_csv()
    return {r["full_path"] for r in records}


def append_to_csv(records: List[Dict]) -> int:
    """
    Append new records to CSV (skip duplicates by full_path).
    
    Returns:
        Number of new records added.
    """
    init_csv()
    existing_paths = get_existing_paths_csv()
    
    new_records = [r for r in records if r["full_path"] not in existing_paths]
    
    if not new_records:
        logger.info("No new records to add to CSV")
        return 0
    
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        for record in new_records:
            # Ensure all columns exist with defaults
            row = {col: record.get(col, "NA") for col in COLUMNS}
            writer.writerow(row)
    
    logger.info(f"Added {len(new_records)} new records to CSV")
    return len(new_records)


def update_csv(records: List[Dict]) -> None:
    """Update existing records in CSV (full rewrite)."""
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for record in records:
            row = {col: record.get(col, "NA") for col in COLUMNS}
            writer.writerow(row)
    
    logger.info(f"Updated CSV with {len(records)} records")


# =============================================================================
# SQLITE OPERATIONS
# =============================================================================

def get_db_connection() -> sqlite3.Connection:
    """Get SQLite database connection."""
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite() -> None:
    """Initialize SQLite database with schema."""
    conn = get_db_connection()
    conn.executescript(SQLITE_SCHEMA)
    conn.commit()
    conn.close()
    logger.info(f"Initialized SQLite database: {SQLITE_FILE}")


def get_existing_paths_sqlite() -> set:
    """Get set of all existing full_path values from SQLite."""
    init_sqlite()
    conn = get_db_connection()
    cursor = conn.execute("SELECT full_path FROM movies")
    paths = {row["full_path"] for row in cursor.fetchall()}
    conn.close()
    return paths


def insert_to_sqlite(records: List[Dict]) -> int:
    """
    Insert new records to SQLite (skip duplicates by full_path).
    
    Returns:
        Number of new records added.
    """
    init_sqlite()
    existing_paths = get_existing_paths_sqlite()
    
    new_records = [r for r in records if r["full_path"] not in existing_paths]
    
    if not new_records:
        logger.info("No new records to add to SQLite")
        return 0
    
    conn = get_db_connection()
    
    # Build insert query
    placeholders = ", ".join(["?" for _ in COLUMNS])
    column_names = ", ".join(COLUMNS)
    query = f"INSERT OR IGNORE INTO movies ({column_names}) VALUES ({placeholders})"
    
    for record in new_records:
        values = [record.get(col, "NA") for col in COLUMNS]
        conn.execute(query, values)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Added {len(new_records)} new records to SQLite")
    return len(new_records)


def update_sqlite_record(uuid_val: str, updates: Dict) -> None:
    """Update a single record in SQLite by UUID."""
    init_sqlite()
    conn = get_db_connection()
    
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [uuid_val]
    
    conn.execute(f"UPDATE movies SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE uuid = ?", values)
    conn.commit()
    conn.close()


def get_all_movies_sqlite() -> List[Dict]:
    """Get all movies from SQLite."""
    init_sqlite()
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM movies ORDER BY title")
    movies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return movies


def get_movie_by_uuid(uuid_val: str) -> Optional[Dict]:
    """Get a single movie by UUID."""
    init_sqlite()
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM movies WHERE uuid = ?", (uuid_val,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_unenriched_movies() -> List[Dict]:
    """Get movies that haven't been AI-enriched yet."""
    init_sqlite()
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM movies WHERE is_active = 1 AND (ai_title = 'NA' OR ai_title IS NULL)")
    movies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return movies


def get_movies_without_omdb() -> List[Dict]:
    """Get movies that have IMDB ID but no OMDb data."""
    init_sqlite()
    conn = get_db_connection()
    cursor = conn.execute("""
        SELECT * FROM movies 
        WHERE is_active = 1 AND imdb_id != 'NA' AND imdb_id IS NOT NULL
        AND (title = 'NA' OR title IS NULL)
    """)
    movies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return movies


# =============================================================================
# UNIFIED STORAGE OPERATIONS
# =============================================================================

def create_movie_record(file_info: Dict, parsed_name: str, parsed_year: str) -> Dict:
    """
    Create a new movie record with all fields.
    
    Args:
        file_info: Dict with file_name, directory, full_path
        parsed_name: Extracted movie name
        parsed_year: Extracted year
        
    Returns:
        Complete movie record dict
    """
    now = datetime.now().isoformat()
    
    return {
        "uuid": str(uuid.uuid4()),
        "file_name": file_info["file_name"],
        "directory": file_info["directory"],
        "full_path": file_info["full_path"],
        "is_active": "0",  # Default to ignore
        "extracted_name": parsed_name,
        "extracted_year": parsed_year,
        "ai_title": "NA",
        "ai_year": "NA",
        "imdb_id": "NA",
        "title": "NA",
        "year": "NA",
        "genre": "NA",
        "director": "NA",
        "actors": "NA",
        "plot": "NA",
        "runtime": "NA",
        "language": "NA",
        "country": "NA",
        "awards": "NA",
        "poster": "NA",
        "imdb_rating": "NA",
        "box_office": "NA",
        "created_at": now,
        "updated_at": now,
    }


def save_movies(records: List[Dict]) -> int:
    """
    Save movies to both CSV and SQLite.
    
    Returns:
        Number of new records added.
    """
    csv_count = append_to_csv(records)
    sqlite_count = insert_to_sqlite(records)
    
    return max(csv_count, sqlite_count)


def get_missing_movie_paths() -> List[Dict]:
    """Find movies in database whose files no longer exist on disk."""
    from pathlib import Path
    
    movies = get_all_movies_sqlite()
    missing = []
    
    for movie in movies:
        full_path = movie.get("full_path", "")
        if full_path and not Path(full_path).exists():
            missing.append(movie)
    
    return missing


def remove_missing_movies() -> int:
    """
    Remove movies from database that no longer exist on disk.
    
    Returns:
        Number of records removed
    """
    missing = get_missing_movie_paths()
    
    if not missing:
        logger.info("No missing movies found - all files exist on disk")
        return 0
    
    init_sqlite()
    conn = get_db_connection()
    
    for movie in missing:
        uuid_val = movie.get("uuid")
        if uuid_val:
            conn.execute("DELETE FROM movies WHERE uuid = ?", (uuid_val,))
            logger.info(f"Removed missing: {movie.get('file_name', 'Unknown')}")
    
    conn.commit()
    conn.close()
    
    # Also update CSV
    remaining_movies = get_all_movies_sqlite()
    update_csv(remaining_movies)
    
    logger.info(f"Removed {len(missing)} movies with missing files")
    return len(missing)


def sync_csv_to_sqlite() -> None:
    """Sync CSV data to SQLite (CSV is source of truth)."""
    records = read_csv()
    init_sqlite()
    
    conn = get_db_connection()
    conn.execute("DELETE FROM movies")  # Clear existing
    
    placeholders = ", ".join(["?" for _ in COLUMNS])
    column_names = ", ".join(COLUMNS)
    query = f"INSERT INTO movies ({column_names}) VALUES ({placeholders})"
    
    for record in records:
        values = [record.get(col, "NA") for col in COLUMNS]
        conn.execute(query, values)
    
    conn.commit()
    conn.close()
    logger.info(f"Synced {len(records)} records from CSV to SQLite")


if __name__ == "__main__":
    # Test storage
    print("Testing storage layer...")
    
    # Initialize
    init_csv()
    init_sqlite()
    
    # Test record creation
    test_file = {
        "file_name": "Test.Movie.2020.1080p.mkv",
        "directory": "D:\\Movies",
        "full_path": "D:\\Movies\\Test.Movie.2020.1080p.mkv"
    }
    
    record = create_movie_record(test_file, "Test Movie", "2020")
    print(f"Created record: {record['uuid']}")
    
    # Check existing paths
    csv_paths = get_existing_paths_csv()
    sqlite_paths = get_existing_paths_sqlite()
    
    print(f"Existing CSV paths: {len(csv_paths)}")
    print(f"Existing SQLite paths: {len(sqlite_paths)}")
    
    print("\nStorage layer test complete!")
