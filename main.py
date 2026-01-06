"""
Movie Library Project - Main Entry Point
Orchestrates scanning, parsing, storage, and enrichment operations.
"""

import sys
import logging
import argparse
from datetime import datetime

from config import MOVIE_DIRECTORY, CSV_FILE, SQLITE_FILE
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("movie_library.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


def run_scan(limit: int = None) -> int:
    """
    Scan directory for videos and index them.
    
    Args:
        limit: Optional limit on number of files to process
        
    Returns:
        Number of new movies indexed
    """
    logger.info("=" * 60)
    logger.info("MOVIE LIBRARY - FILE SCAN")
    logger.info("=" * 60)
    logger.info(f"Scanning directory: {MOVIE_DIRECTORY}")
    logger.info(f"Limit: {limit if limit else 'None'}")
    
    records = []
    count = 0
    
    for file_info in scan_directory(MOVIE_DIRECTORY):
        # Parse filename
        name, year = parse_filename(file_info["file_name"])
        
        # Create record
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
    
    # Save to storage
    new_count = save_movies(records)
    
    logger.info("=" * 60)
    logger.info(f"Scan complete!")
    logger.info(f"  Total processed: {count}")
    logger.info(f"  New records added: {new_count}")
    logger.info(f"  CSV file: {CSV_FILE}")
    logger.info(f"  SQLite file: {SQLITE_FILE}")
    logger.info("=" * 60)
    
    return new_count


def show_stats() -> None:
    """Display current database statistics."""
    init_csv()
    init_sqlite()
    
    csv_records = read_csv()
    sqlite_records = get_all_movies_sqlite()
    
    # Count enriched records
    ai_enriched = sum(1 for r in sqlite_records if r.get("ai_title", "NA") != "NA")
    omdb_enriched = sum(1 for r in sqlite_records if r.get("title", "NA") != "NA")
    
    # States
    state_0 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "0")
    state_1 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "1") # Pending AI
    state_2 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "2") # Pending OMDb
    state_3 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "3") # Success
    state_4 = sum(1 for r in sqlite_records if str(r.get("is_active", "0")) == "4") # Failure
    
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


def show_sample(count: int = 10) -> None:
    """Show sample records from database."""
    movies = get_all_movies_sqlite()
    
    print(f"\nShowing {min(count, len(movies))} of {len(movies)} movies:\n")
    print("-" * 80)
    
    for movie in movies[:count]:
        name = movie.get("extracted_name", "NA")
        year = movie.get("extracted_year", "NA")
        file_name = movie.get("file_name", "NA")
        ai_title = movie.get("ai_title", "NA")
        imdb = movie.get("imdb_rating", "NA")
        
        display_title = ai_title if ai_title != "NA" else name
        
        print(f"  {display_title} ({year})")
        print(f"    File: {file_name}")
        if imdb != "NA":
            print(f"    IMDb: {imdb}")
        print("-" * 80)


def main():
    """Main entry point with CLI."""
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
    
    parser.add_argument("--scan", action="store_true", help="Scan directory for videos")
    parser.add_argument("--limit", type=int, help="Limit number of items to process")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--sample", type=int, metavar="N", help="Show N sample records")
    parser.add_argument("--sync", action="store_true", help="Sync CSV to SQLite")
    parser.add_argument("--cleanup", action="store_true", help="Remove movies with missing files from database")
    parser.add_argument("--check-missing", action="store_true", help="Check for movies with missing files (preview only)")
    parser.add_argument("--enrich", action="store_true", help="Enrich movies with Gemini AI")
    parser.add_argument("--fetch-omdb", action="store_true", help="Fetch OMDb metadata")
    parser.add_argument("--full-enrich", action="store_true", help="Run full enrichment (AI + OMDb)")
    parser.add_argument("--server", action="store_true", help="Start Web Viewer Server")
    parser.add_argument("--bulk", action="store_true", help="Use text-based bulk enrichment (faster, uses configured AI model)")
    
    args = parser.parse_args()
    
    # Default action if no args
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # Execute actions
    if args.server:
        from server import run_server
        run_server()
        return

    if args.scan:
        run_scan(args.limit)
    
    if args.sync:
        sync_csv_to_sqlite()
        logger.info("Sync complete!")
    
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
    
    if args.cleanup:
        count = remove_missing_movies()
        logger.info(f"Cleanup complete: {count} missing movies removed")
    
    
    if args.enrich:
        if args.bulk:
            from enricher import enrich_with_ai_bulk
            count = enrich_with_ai_bulk(args.limit)
            logger.info(f"Bulk AI enrichment complete: {count} movies processed")
        else:
            count = enrich_with_ai(args.limit)
            logger.info(f"AI enrichment complete: {count} movies processed")
    
    if args.fetch_omdb:
        count = enrich_with_omdb(args.limit)
        logger.info(f"OMDb enrichment complete: {count} movies processed")
    
    if args.full_enrich:
        results = full_enrichment(args.limit)
        logger.info(f"Full enrichment complete: AI={results['ai_enriched']}, OMDb={results['omdb_enriched']}")
    
    if args.stats:
        show_stats()
    
    if args.sample:
        show_sample(args.sample)


if __name__ == "__main__":
    main()

