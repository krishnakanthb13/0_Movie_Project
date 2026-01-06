"""
Movie Library Project - Storage Layer Module
=============================================

Handles all data persistence operations for the movie library.

This module provides a dual-storage architecture:
- CSV: Human-readable, portable, serves as "source of truth"
- SQLite: Fast queries, filtering, used by the web interface

Key Features:
- Atomic record creation with UUID primary keys
- Duplicate prevention based on file path
- State tracking via is_active flag (0-4)
- Bidirectional sync between CSV and SQLite
- Orphan detection for deleted files

Database Schema (30 columns):
- Core: uuid, file_name, directory, full_path, is_active
- Parsed: extracted_name, extracted_year
- AI: ai_title, ai_year, ai_imdb_id
- OMDb: title, year, genre, director, actors, plot, runtime,
        language, country, awards, poster, imdb_rating, box_office,
        imdb_id, additional_info
- Metadata: created_at, updated_at
- User: user_rating, user_tags

Usage:
    from storage import save_movies, get_all_movies_sqlite
    
    # Save new movies
    count = save_movies(records)
    
    # Retrieve all movies
    movies = get_all_movies_sqlite()

Dependencies:
    - config.py: CSV_FILE, SQLITE_FILE
"""

import csv
import sqlite3
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from config import CSV_FILE, SQLITE_FILE

# Get logger for this module
logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================
# These define the structure for both CSV and SQLite storage.

# CSV_COLUMNS: Ordered list of all columns in the CSV file.
# The order matters for CSV reading/writing operations.
# New columns should be added at the end to maintain backward compatibility.
CSV_COLUMNS = [
    # -------------------------------------------------------------------------
    # Core identification fields (required for all records)
    # -------------------------------------------------------------------------
    "uuid",           # Unique identifier (UUID4 format)
    "file_name",      # Original filename with extension
    "directory",      # Parent directory path
    "full_path",      # Absolute path to file (used for deduplication)
    "is_active",      # Processing state: 0=ignored, 1=pending AI, 2=pending OMDb, 3=success, 4=failed
    
    # -------------------------------------------------------------------------
    # Parser-extracted fields (from filename parsing)
    # -------------------------------------------------------------------------
    "extracted_name", # Movie title extracted from filename
    "extracted_year", # Year extracted from filename
    
    # -------------------------------------------------------------------------
    # AI-enriched fields (from Gemini AI)
    # -------------------------------------------------------------------------
    "ai_title",       # AI-identified movie title
    "ai_year",        # AI-identified release year
    "ai_imdb_id",     # AI-suggested IMDb ID (unverified)
    
    # -------------------------------------------------------------------------
    # OMDb-verified fields (from OMDb API)
    # -------------------------------------------------------------------------
    "imdb_id",        # Verified IMDb ID (ttXXXXXXX format)
    "title",          # Official movie title from OMDb
    "year",           # Official release year from OMDb
    "genre",          # Comma-separated genres (e.g., "Action, Sci-Fi")
    "director",       # Director name(s)
    "actors",         # Main cast (comma-separated)
    "plot",           # Short plot summary
    "runtime",        # Duration (e.g., "136 min")
    "language",       # Primary language(s)
    "country",        # Production country/countries
    "awards",         # Awards summary
    "poster",         # URL to movie poster image
    "imdb_rating",    # IMDb rating (e.g., "8.7")
    "box_office",     # Box office earnings
    "additional_info",# Extra metadata not captured elsewhere
    
    # -------------------------------------------------------------------------
    # Timestamp fields
    # -------------------------------------------------------------------------
    "created_at",     # Record creation timestamp (ISO format)
    "updated_at",     # Last update timestamp (ISO format)
    
    # -------------------------------------------------------------------------
    # User metadata fields
    # -------------------------------------------------------------------------
    "user_rating",    # User's personal rating (1-10)
    "user_tags"       # User-defined tags (comma-separated)
]

# SQLITE_SCHEMA: SQL statement to create the movies table.
# Uses TEXT for all fields for simplicity and flexibility.
# Indexes are created on frequently queried columns.
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
    -- Core fields
    uuid            TEXT PRIMARY KEY,
    file_name       TEXT NOT NULL,
    directory       TEXT NOT NULL,
    full_path       TEXT NOT NULL UNIQUE,
    is_active       INTEGER DEFAULT 0,
    
    -- Parser fields
    extracted_name  TEXT,
    extracted_year  TEXT,
    
    -- AI fields
    ai_title        TEXT,
    ai_year         TEXT,
    ai_imdb_id      TEXT,
    
    -- OMDb fields
    imdb_id         TEXT,
    title           TEXT,
    year            TEXT,
    genre           TEXT,
    director        TEXT,
    actors          TEXT,
    plot            TEXT,
    runtime         TEXT,
    language        TEXT,
    country         TEXT,
    awards          TEXT,
    poster          TEXT,
    imdb_rating     TEXT,
    box_office      TEXT,
    additional_info TEXT,
    
    -- Timestamps
    created_at      TEXT,
    updated_at      TEXT,
    
    -- User metadata
    user_rating     TEXT,
    user_tags       TEXT
);

-- Index for faster lookups by common query patterns
CREATE INDEX IF NOT EXISTS idx_is_active ON movies(is_active);
CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id);
"""


# =============================================================================
# CSV OPERATIONS
# =============================================================================
# Functions for reading and writing the CSV file.

def init_csv() -> None:
    """
    Initialize CSV file with headers if it doesn't exist.
    
    Creates a new CSV file with column headers from CSV_COLUMNS.
    If the file already exists, this function does nothing.
    
    Args:
        None
    
    Returns:
        None
    
    Side Effects:
        - Creates CSV_FILE if it doesn't exist
        - Writes header row to new file
    """
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
        logger.info(f"Created new CSV file: {CSV_FILE}")


def read_csv() -> List[Dict]:
    """
    Read all records from CSV file.
    
    Reads the entire CSV file and returns all records as a list
    of dictionaries, where keys are column names.
    
    Args:
        None
    
    Returns:
        List[Dict]: List of movie records. Empty list if file doesn't exist
                    or is empty.
    
    Note:
        Initializes CSV file if it doesn't exist to prevent errors.
    """
    init_csv()
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_existing_paths_csv() -> set:
    """
    Get set of all existing full_path values from CSV.
    
    Used for deduplication when adding new records.
    
    Args:
        None
    
    Returns:
        set: Set of all full_path strings currently in the CSV.
             Empty set if file is empty.
    """
    records = read_csv()
    return {r["full_path"] for r in records}


def append_to_csv(records: List[Dict]) -> int:
    """
    Append new records to CSV, skipping duplicates by full_path.
    
    Only adds records whose full_path doesn't already exist in the CSV.
    This prevents duplicate entries for the same file.
    
    Args:
        records (List[Dict]): List of movie record dictionaries to add.
                              Each dict should have keys matching CSV_COLUMNS.
    
    Returns:
        int: Number of new records actually added (after deduplication).
    
    Side Effects:
        - Appends new rows to CSV_FILE
        - Logs count of new records added
    """
    # Get existing paths to check for duplicates
    existing = get_existing_paths_csv()
    
    # Filter to only new records (not already in CSV)
    new_records = [r for r in records if r["full_path"] not in existing]
    
    if new_records:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            for record in new_records:
                writer.writerow(record)
        logger.info(f"Appended {len(new_records)} new records to CSV")
    
    return len(new_records)


def update_csv(records: List[Dict]) -> None:
    """
    Update CSV file with new records (full rewrite).
    
    Completely rewrites the CSV file with the provided records.
    Used for syncing changes from SQLite back to CSV.
    
    Args:
        records (List[Dict]): Complete list of all movie records.
                              This will replace all existing data.
    
    Returns:
        None
    
    Warning:
        This is a destructive operation. All existing CSV data
        is replaced with the provided records.
    """
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    logger.info(f"Updated CSV with {len(records)} records")


# =============================================================================
# SQLITE OPERATIONS
# =============================================================================
# Functions for interacting with the SQLite database.

def get_db_connection() -> sqlite3.Connection:
    """
    Get SQLite database connection with row factory enabled.
    
    Creates a connection with row_factory set to sqlite3.Row,
    allowing column access by name instead of index.
    
    Args:
        None
    
    Returns:
        sqlite3.Connection: Active database connection.
    
    Note:
        Caller is responsible for closing the connection.
    """
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn


def init_sqlite() -> None:
    """
    Initialize SQLite database with schema.
    
    Creates the movies table and indexes if they don't exist.
    Also runs migration to add any new columns.
    
    Args:
        None
    
    Returns:
        None
    
    Side Effects:
        - Creates SQLITE_FILE if it doesn't exist
        - Creates movies table and indexes
        - Runs schema migrations
    """
    conn = get_db_connection()
    try:
        conn.executescript(SQLITE_SCHEMA)
        conn.commit()
        logger.info(f"Initialized SQLite database: {SQLITE_FILE}")
    finally:
        conn.close()
    
    # Run migrations for any new columns
    migrate_db()


def migrate_db() -> None:
    """
    Migrate database schema for new columns.
    
    Checks for missing columns and adds them if needed.
    This allows the schema to evolve without data loss.
    
    Args:
        None
    
    Returns:
        None
    
    Migration Strategy:
        - Get current columns from PRAGMA table_info
        - Compare against CSV_COLUMNS (source of truth)
        - Add missing columns with ALTER TABLE
    """
    conn = get_db_connection()
    try:
        # Get existing columns
        cursor = conn.execute("PRAGMA table_info(movies)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        # Add missing columns
        for col in CSV_COLUMNS:
            if col not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE movies ADD COLUMN {col} TEXT")
                    logger.info(f"Added column: {col}")
                except sqlite3.OperationalError:
                    pass  # Column might already exist
        
        conn.commit()
    finally:
        conn.close()


def get_existing_paths_sqlite() -> set:
    """
    Get set of all existing full_path values from SQLite.
    
    Used for deduplication when inserting new records.
    
    Args:
        None
    
    Returns:
        set: Set of all full_path strings currently in the database.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT full_path FROM movies")
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def insert_to_sqlite(records: List[Dict]) -> int:
    """
    Insert new records to SQLite, skipping duplicates by full_path.
    
    Uses INSERT OR IGNORE to skip records with duplicate full_path.
    
    Args:
        records (List[Dict]): List of movie record dictionaries.
    
    Returns:
        int: Number of new records actually inserted.
    
    Note:
        Uses batch insertion for performance.
    """
    if not records:
        return 0
    
    conn = get_db_connection()
    try:
        # Build column and placeholder strings
        columns = ", ".join(CSV_COLUMNS)
        placeholders = ", ".join(["?" for _ in CSV_COLUMNS])
        
        inserted = 0
        for record in records:
            # Create tuple of values in column order
            values = tuple(record.get(col, "") for col in CSV_COLUMNS)
            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO movies ({columns}) VALUES ({placeholders})",
                    values
                )
                if conn.total_changes > inserted:
                    inserted += 1
            except sqlite3.IntegrityError:
                pass  # Duplicate, skip
        
        conn.commit()
        logger.info(f"Inserted {inserted} new records to SQLite")
        return inserted
    finally:
        conn.close()


def update_sqlite_record(uuid_val: str, updates: Dict) -> None:
    """
    Update a single record in SQLite by UUID.
    
    Updates specified fields for the record matching the given UUID.
    Also updates the updated_at timestamp automatically.
    
    Args:
        uuid_val (str): UUID of the record to update.
        updates (Dict): Dictionary of column:value pairs to update.
                        Example: {"title": "The Matrix", "year": "1999"}
    
    Returns:
        None
    
    Side Effects:
        - Updates record in database
        - Sets updated_at to current timestamp
    """
    conn = get_db_connection()
    try:
        # Add timestamp
        updates["updated_at"] = datetime.now().isoformat()
        
        # Build SET clause
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [uuid_val]
        
        conn.execute(
            f"UPDATE movies SET {set_clause} WHERE uuid = ?",
            values
        )
        conn.commit()
    finally:
        conn.close()


def get_all_movies_sqlite() -> List[Dict]:
    """
    Get all movies from SQLite database.
    
    Returns complete list of all movie records as dictionaries.
    
    Args:
        None
    
    Returns:
        List[Dict]: All movie records from the database.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM movies")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_movie_by_uuid(uuid_val: str) -> Optional[Dict]:
    """
    Get a single movie by UUID.
    
    Args:
        uuid_val (str): UUID of the movie to retrieve.
    
    Returns:
        Dict: Movie record if found, None otherwise.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM movies WHERE uuid = ?", (uuid_val,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_unenriched_movies() -> List[Dict]:
    """
    Get movies that haven't been AI-enriched yet.
    
    Returns movies with is_active = 1 (pending AI enrichment).
    
    Args:
        None
    
    Returns:
        List[Dict]: Movies pending AI enrichment.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM movies WHERE is_active = 1")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_movies_without_omdb() -> List[Dict]:
    """
    Get movies ready for OMDb enrichment.
    
    Returns movies with is_active = 2 (AI done, pending OMDb).
    
    Args:
        None
    
    Returns:
        List[Dict]: Movies pending OMDb enrichment, ordered by
                    extracted_name for predictable processing.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM movies WHERE is_active = 2 ORDER BY extracted_name"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# =============================================================================
# UNIFIED STORAGE OPERATIONS
# =============================================================================
# Higher-level functions that work with both storage backends.

def create_movie_record(file_info: Dict, parsed_name: str, parsed_year: str) -> Dict:
    """
    Create a new movie record with all fields initialized.
    
    Generates a complete movie record dictionary ready for storage.
    Sets core fields from file_info and parsing results, initializes
    all other fields to "NA", and sets timestamps.
    
    Args:
        file_info (Dict): Dictionary containing file discovery results.
                          Required keys: file_name, directory, full_path
        
        parsed_name (str): Movie title extracted by parser.
                           Example: "The Matrix"
        
        parsed_year (str): Release year extracted by parser.
                           Example: "1999" or "NA"
    
    Returns:
        Dict: Complete movie record with all columns populated.
              uuid is auto-generated, is_active defaults to 1.
    
    Field Initialization:
        - uuid: New UUID4
        - Core fields: From file_info
        - parsed_name/year: From parameters
        - is_active: 1 (pending AI enrichment)
        - Timestamps: Current time for both
        - All other fields: "NA"
    """
    now = datetime.now().isoformat()
    
    # Create record with all columns
    record = {col: "NA" for col in CSV_COLUMNS}
    
    # Set core fields from file discovery
    record.update({
        "uuid": str(uuid.uuid4()),
        "file_name": file_info["file_name"],
        "directory": file_info["directory"],
        "full_path": file_info["full_path"],
        "is_active": 1,  # Mark as pending AI enrichment
        
        # Parser results
        "extracted_name": parsed_name,
        "extracted_year": parsed_year,
        
        # Timestamps
        "created_at": now,
        "updated_at": now,
    })
    
    return record


def save_movies(records: List[Dict]) -> int:
    """
    Save movies to both CSV and SQLite storage.
    
    Ensures both storage backends stay synchronized by saving
    to both in a single operation.
    
    Args:
        records (List[Dict]): List of movie records to save.
    
    Returns:
        int: Number of new records added (based on CSV count).
    
    Side Effects:
        - Initializes storage if needed
        - Appends to CSV
        - Inserts to SQLite
    """
    init_csv()
    init_sqlite()
    
    csv_count = append_to_csv(records)
    insert_to_sqlite(records)
    
    return csv_count


def get_missing_movie_paths() -> List[Dict]:
    """
    Find movies in database whose files no longer exist on disk.
    
    Scans all records and checks if the file at full_path still exists.
    Used to identify orphan records from deleted files.
    
    Args:
        None
    
    Returns:
        List[Dict]: Movie records where the file is missing from disk.
    """
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
    
    Identifies and removes orphan records (files deleted from disk).
    Updates both SQLite and CSV.
    
    Args:
        None
    
    Returns:
        int: Number of records removed.
    
    Side Effects:
        - Deletes orphan records from SQLite
        - Rewrites CSV without orphan records
        - Logs removal count
    """
    missing = get_missing_movie_paths()
    
    if not missing:
        logger.info("No missing movies found")
        return 0
    
    logger.info(f"Found {len(missing)} movies with missing files")
    
    # Get UUIDs of missing movies
    missing_uuids = {m["uuid"] for m in missing}
    
    # Remove from SQLite
    conn = get_db_connection()
    try:
        for uuid_val in missing_uuids:
            conn.execute("DELETE FROM movies WHERE uuid = ?", (uuid_val,))
        conn.commit()
        logger.info(f"Removed {len(missing_uuids)} records from SQLite")
    finally:
        conn.close()
    
    # Remove from CSV (rewrite without missing)
    all_records = get_all_movies_sqlite()
    update_csv(all_records)
    
    return len(missing_uuids)


def sync_csv_to_sqlite() -> None:
    """
    Sync CSV data to SQLite (CSV is source of truth).
    
    Reads all records from CSV and ensures they exist in SQLite.
    Useful for recovery or after manual CSV edits.
    
    Args:
        None
    
    Returns:
        None
    
    Side Effects:
        - Reads CSV file
        - Inserts missing records to SQLite
        - Logs sync result
    """
    init_sqlite()
    
    csv_records = read_csv()
    if not csv_records:
        logger.info("CSV is empty, nothing to sync")
        return
    
    # Get existing SQLite paths
    existing = get_existing_paths_sqlite()
    
    # Find records not in SQLite
    to_sync = [r for r in csv_records if r["full_path"] not in existing]
    
    if to_sync:
        insert_to_sqlite(to_sync)
        logger.info(f"Synced {len(to_sync)} records from CSV to SQLite")
    else:
        logger.info("SQLite already in sync with CSV")


# =============================================================================
# STANDALONE TEST
# =============================================================================
# Test block for module verification.

if __name__ == "__main__":
    # Test storage layer functionality
    print("Testing storage layer...")
    
    # Initialize storage
    init_csv()
    init_sqlite()
    
    # Test record creation
    test_file = {
        "file_name": "Test.Movie.2020.1080p.mkv",
        "directory": "E:/Movies",
        "full_path": "E:/Movies/Test.Movie.2020.1080p.mkv"
    }
    
    record = create_movie_record(test_file, "Test Movie", "2020")
    print(f"Created record with UUID: {record['uuid']}")
    
    # Show existing record counts
    csv_paths = get_existing_paths_csv()
    sqlite_paths = get_existing_paths_sqlite()
    
    print(f"Existing CSV paths: {len(csv_paths)}")
    print(f"Existing SQLite paths: {len(sqlite_paths)}")
    
    print("\nStorage layer test complete!")
