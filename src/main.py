"""
Movie Library Project - Main Entry Point
=========================================

Central orchestrator for all Movie Library operations.

This is the main entry point for the Movie Library system, providing
a command-line interface (CLI) for all operations:

Scan Operations:
    --scan              Scan directory for video files
    --limit N           Limit items to process
    --check-missing     Preview files that no longer exist
    --cleanup           Remove missing file entries from database

Enrichment Operations:
    --enrich            Run AI enrichment (Gemini)
    --bulk              Use bulk mode with --enrich (faster)
    --fetch-omdb        Run OMDb enrichment
    --full-enrich       Run complete pipeline (AI + OMDb)

Database Operations:
    --sync              Sync CSV to SQLite
    --stats             Show database statistics
    --sample N          Show N sample records

Server Operations:
    --server            Start web server

Usage Examples:
    python main.py --scan                    # Scan all movies
    python main.py --scan --limit 50         # Scan first 50
    python main.py --enrich --limit 10       # AI enrich 10 movies
    python main.py --enrich --bulk           # Bulk AI enrichment
    python main.py --fetch-omdb              # Fetch OMDb metadata
    python main.py --full-enrich             # Complete pipeline
    python main.py --server                  # Start web viewer
    python main.py --stats                   # Show statistics

Dependencies:
    All project modules: config, scanner, parser, storage, enricher
"""

import sys
import logging
import argparse
from datetime import datetime

# Make console output crash-proof for emoji/unicode on a non-UTF-8 Windows
# console. MovieLibrary.bat sets `chcp 65001`, but running the CLI directly
# can leave stdout on cp1252, where printing characters like ❌/✅ raises
# UnicodeEncodeError. Re-encode as UTF-8 (replacing anything unencodable)
# instead of failing.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from config import MOVIE_DIRECTORY, CSV_FILE, SQLITE_FILE, LOG_FILE
from scanner import scan_directory, get_all_videos
from parser import parse_filename
from storage import (
    create_movie_record, 
    save_movies, 
    read_csv, 
    get_all_movies_sqlite,
    init_csv,
    init_sqlite,
    sync_csv_to_sqlite,
    get_unenriched_movies,
    get_movies_without_omdb,
    get_missing_movie_paths,
    remove_missing_movies
)
from enricher import enrich_with_ai, enrich_with_omdb, full_enrichment


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
# Configure logging for console output and file persistence.
# All operations are logged to movie_library.log for debugging.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),                  # Console output
        logging.FileHandler(LOG_FILE, encoding="utf-8")     # Single log file (data/enrichment.log)
    ],
    # force=True is required: imported modules (e.g. scanner.py) call
    # logging.basicConfig() at import time, which runs first and would
    # otherwise make this call a silent no-op, leaving file logging broken.
    force=True
)
logger = logging.getLogger(__name__)


# =============================================================================
# SCAN OPERATION
# =============================================================================

def run_scan(limit: int = None) -> int:
    """
    Scan directory for videos and index them.
    
    Recursively scans MOVIE_DIRECTORY for video files, parses each
    filename to extract title and year, and saves records to both
    CSV and SQLite storage.
    
    Args:
        limit (int, optional): Maximum number of files to process.
                               If None, processes all discovered files.
                               Useful for testing or partial scans.
    
    Returns:
        int: Number of NEW movies indexed (duplicates are skipped).
    
    Processing Steps:
        1. Iterate through all video files in MOVIE_DIRECTORY
        2. Parse each filename to extract title and year
        3. Create movie record with UUID and metadata
        4. Save to storage (CSV + SQLite)
    
    Side Effects:
        - Creates/updates CSV_FILE
        - Creates/updates SQLITE_FILE
        - Sets is_active=1 for new records (pending AI enrichment)
    
    Example:
        >>> new_count = run_scan(limit=100)
        >>> print(f"Indexed {new_count} new movies")
    """
    logger.info("=" * 60)
    logger.info("MOVIE LIBRARY - FILE SCAN")
    logger.info("=" * 60)
    logger.info(f"Scanning directory: {MOVIE_DIRECTORY}")
    logger.info(f"Limit: {limit if limit else 'None'}")
    
    records = []
    count = 0
    
    # Iterate through discovered video files
    for file_info in scan_directory(MOVIE_DIRECTORY):
        # Parse filename to extract title and year
        name, year = parse_filename(file_info["file_name"])
        
        # Create complete movie record
        record = create_movie_record(file_info, name, year)
        records.append(record)
        count += 1
        
        # Log progress every 100 files
        if count % 100 == 0:
            logger.info(f"Processed {count} files...")
        
        # Check limit
        if limit and count >= limit:
            logger.info(f"Reached limit of {limit} files")
            break
    
    # Save all records to storage
    new_count = save_movies(records)
    
    # Summary logging
    logger.info("=" * 60)
    logger.info(f"Scan complete!")
    logger.info(f"  Total processed: {count}")
    logger.info(f"  New records added: {new_count}")
    logger.info(f"  CSV file: {CSV_FILE}")
    logger.info(f"  SQLite file: {SQLITE_FILE}")
    logger.info("=" * 60)
    
    return new_count


# =============================================================================
# STATISTICS DISPLAY
# =============================================================================

def show_stats() -> None:
    """
    Display current database statistics.
    
    Shows comprehensive statistics about the movie database including:
    - Total record count
    - AI enrichment count
    - OMDb enrichment count
    - Breakdown by is_active state
    
    Args:
        None
    
    Returns:
        None (prints to stdout)
    
    State Meanings:
        0 = Ignored (will not be processed)
        1 = Pending AI enrichment
        2 = Pending OMDb enrichment
        3 = Successfully enriched
        4 = Failed (needs manual intervention)
    """
    # Ensure storage is initialized
    init_csv()
    init_sqlite()
    
    # Read current data
    csv_records = read_csv()
    sqlite_records = get_all_movies_sqlite()
    
    # Count enriched records
    ai_enriched = sum(1 for r in sqlite_records if r.get("ai_title", "NA") != "NA")
    omdb_enriched = sum(1 for r in sqlite_records if r.get("title", "NA") != "NA")
    
    # Count by state
    state_0 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "0")
    state_1 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "1")
    state_2 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "2")
    state_3 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "3")
    state_4 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "4")
    
    # Display statistics
    print("\n" + "=" * 50)
    print("MOVIE LIBRARY STATISTICS")
    print("=" * 50)
    print(f"  Total Records:    {len(sqlite_records)}")
    print(f"  AI Enriched:      {ai_enriched}")
    print(f"  OMDb Enriched:    {omdb_enriched}")
    print("-" * 50)
    print(f"  [0] Ignored:      {state_0}")
    print(f"  [1] Pending AI:   {state_1}")
    print(f"  [2] Pending OMDb: {state_2}")
    print(f"  [3] Success:      {state_3}")
    print(f"  [4] Failed:       {state_4}") 
    print("=" * 50)


# =============================================================================
# SAMPLE DISPLAY
# =============================================================================

def show_sample(count: int = 10) -> None:
    """
    Show sample records from the database.
    
    Displays a preview of movies in the database with their
    extracted and enriched data.
    
    Args:
        count (int): Number of records to display (default: 10).
    
    Returns:
        None (prints to stdout)
    
    Display Format:
        - Title (Year)
        - Original filename
        - IMDb rating (if available)
    """
    movies = get_all_movies_sqlite()
    
    print(f"\nShowing {min(count, len(movies))} of {len(movies)} movies:\n")
    print("-" * 80)
    
    for movie in movies[:count]:
        name = movie.get("extracted_name", "NA")
        year = movie.get("extracted_year", "NA")
        file_name = movie.get("file_name", "NA")
        ai_title = movie.get("ai_title", "NA")
        imdb = movie.get("imdb_rating", "NA")
        
        # Prefer AI title over extracted name
        display_title = ai_title if ai_title != "NA" else name
        
        print(f"  {display_title} ({year})")
        print(f"    File: {file_name}")
        if imdb != "NA":
            print(f"    IMDb: {imdb}")
        print("-" * 80)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point with CLI argument parsing.
    
    Parses command-line arguments and dispatches to appropriate
    handler functions.
    
    Supported Commands:
        --scan              Scan for videos
        --limit N           Limit processing count
        --stats             Show statistics
        --sample N          Show sample records
        --sync              Sync CSV to SQLite
        --check-missing     Preview missing files
        --cleanup           Remove missing entries
        --enrich            AI enrichment
        --bulk              Bulk AI mode
        --fetch-omdb        OMDb enrichment
        --full-enrich       Complete pipeline
        --server            Start web server
    
    Exit Behavior:
        Returns to shell after operation completes.
        Server mode runs until Ctrl+C.
    """
    # Set up argument parser with description and examples
    parser = argparse.ArgumentParser(
        description="Movie Library Indexing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --scan              Scan for all movies
  python main.py --scan --limit 50   Scan first 50 movies
  python main.py --stats             Show database statistics
  python main.py --sample 20         Show 20 sample records
  python main.py --sync              Sync CSV to SQLite
  python main.py --cleanup           Remove deleted movies from database
  
  python main.py --enrich            AI enrich all pending movies
  python main.py --enrich --limit 10 AI enrich first 10 movies
  python main.py --fetch-omdb        Fetch OMDb data for enriched movies
  python main.py --full-enrich       Run full enrichment pipeline (AI + OMDb)
        """
    )
    
    # -----------------------------------------------------------------
    # ARGUMENT DEFINITIONS
    # -----------------------------------------------------------------
    
    # Scan operations
    parser.add_argument("--scan", action="store_true", 
                        help="Scan directory for videos")
    parser.add_argument("--limit", type=int, 
                        help="Limit number of items to process")
    
    # Database operations
    parser.add_argument("--stats", action="store_true", 
                        help="Show database statistics")
    parser.add_argument("--sample", type=int, metavar="N", 
                        help="Show N sample records")
    parser.add_argument("--sync", action="store_true", 
                        help="Sync CSV to SQLite")
    
    # Cleanup operations
    parser.add_argument("--cleanup", action="store_true", 
                        help="Remove movies with missing files from database")
    parser.add_argument("--check-missing", action="store_true", 
                        help="Check for movies with missing files (preview only)")
    
    # Enrichment operations
    parser.add_argument("--enrich", action="store_true", 
                        help="Enrich movies with Gemini AI")
    parser.add_argument("--fetch-omdb", action="store_true", 
                        help="Fetch OMDb metadata")
    parser.add_argument("--full-enrich", action="store_true",
                        help="Run full enrichment (AI + OMDb)")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Retry movies that failed OMDb enrichment (state 4): "
                             "reset them to pending and run OMDb again")
    parser.add_argument("--bulk", action="store_true",
                        help="Use text-based bulk enrichment (faster, uses configured AI model)")
    parser.add_argument("--provider", choices=["gemini", "groq"],
                        help="AI provider for enrichment (default: config AI_PROVIDER). "
                             "groq requires GROQ_API_KEY in .env.")
    parser.add_argument("--model",
                        help="Model for AI enrichment. Gemini shortcuts: 2.5, 3.5. "
                             "Or a full model id (e.g. a Groq model like "
                             "llama-3.3-70b-versatile or groq/compound). "
                             "Default: the provider's configured model. "
                             "(For Gemini this sets the formatter/bulk model; the "
                             "Live-API search model used by the standard --enrich "
                             "path is configured separately as AI_SEARCH_MODEL.)")
    
    # Server operations
    parser.add_argument("--server", action="store_true", 
                        help="Start Web Viewer Server")
    
    # Parse arguments
    args = parser.parse_args()
    
    # -----------------------------------------------------------------
    # DEFAULT ACTION (no arguments)
    # -----------------------------------------------------------------
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # -----------------------------------------------------------------
    # PROVIDER / MODEL SELECTION (optional overrides)
    # Choose the AI provider (gemini/groq) and model for this run. Gemini
    # accepts the friendly 2.5/3.5 shortcuts; any other value is passed
    # through as a full model id (e.g. a Groq model). Affects AI enrichment;
    # the Gemini Live API search model is separate.
    # -----------------------------------------------------------------
    MODEL_ALIASES = {"2.5": "gemini-2.5-flash", "3.5": "gemini-3.5-flash"}
    if args.provider or args.model:
        import ai_provider
        if args.provider:
            ai_provider.set_provider(args.provider)
        if args.model:
            ai_provider.set_model(MODEL_ALIASES.get(args.model, args.model))

    # -----------------------------------------------------------------
    # COMMAND DISPATCH
    # -----------------------------------------------------------------

    # Server (handled first as it runs indefinitely)
    if args.server:
        from server import run_server
        run_server()
        return

    # Scan operation
    if args.scan:
        run_scan(args.limit)
    
    # Sync operation
    if args.sync:
        sync_csv_to_sqlite()
        logger.info("Sync complete!")
    
    # Check missing files (preview)
    if args.check_missing:
        missing = get_missing_movie_paths()
        if missing:
            print(f"\nFound {len(missing)} movies with missing files:")
            print("-" * 60)
            for m in missing[:20]:  # Show first 20
                print(f"  ❌ {m.get('file_name', 'Unknown')}")
            if len(missing) > 20:
                print(f"  ... and {len(missing) - 20} more")
            print("\nRun with --cleanup to remove these from database.")
        else:
            print("\n✅ All movies in database exist on disk!")
    
    # Cleanup operation
    if args.cleanup:
        count = remove_missing_movies()
        logger.info(f"Cleanup complete: {count} missing movies removed")
    
    # AI enrichment
    if args.enrich:
        if args.bulk:
            # Use bulk mode (faster, single API call)
            from enricher import enrich_with_ai_bulk
            count = enrich_with_ai_bulk(args.limit)
            logger.info(f"Bulk AI enrichment complete: {count} movies processed")
        else:
            # Use standard mode (more accurate)
            count = enrich_with_ai(args.limit)
            logger.info(f"AI enrichment complete: {count} movies processed")
    
    # OMDb enrichment
    if args.fetch_omdb:
        count = enrich_with_omdb(args.limit)
        logger.info(f"OMDb enrichment complete: {count} movies processed")

    # Retry failed OMDb enrichments (state 4 -> 2 -> re-run OMDb)
    if args.retry_failed:
        from enricher import retry_failed_omdb
        count = retry_failed_omdb(args.limit)
        logger.info(f"Retry complete: {count} previously-failed movies processed")
    
    # Full enrichment pipeline
    if args.full_enrich:
        results = full_enrichment(args.limit)
        logger.info(f"Full enrichment complete: AI={results['ai_enriched']}, OMDb={results['omdb_enriched']}")
    
    # Statistics display
    if args.stats:
        show_stats()
    
    # Sample display
    if args.sample:
        show_sample(args.sample)


# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

if __name__ == "__main__":
    main()
