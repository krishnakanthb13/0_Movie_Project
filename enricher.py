"""
Movie Library Project - Enrichment Pipeline Module
===================================================

Orchestrates the AI and OMDb enrichment workflow for movie data.

This module coordinates the complete enrichment pipeline:
1. AI Enrichment: Uses Gemini to identify movies and find IMDb IDs
2. OMDb Enrichment: Fetches detailed metadata from OMDb using AI results
3. State Management: Tracks progress via is_active flag
4. Data Synchronization: Keeps CSV and SQLite in sync

Enrichment States (is_active values):
    0 = Ignored (will not be processed)
    1 = Pending AI enrichment (new scan)
    2 = Pending OMDb enrichment (AI complete)
    3 = Complete (fully enriched)
    4 = Failed (OMDb lookup failed, needs manual fix)

Pipeline Flow:
    [Scan] -> is_active=1
          -> [AI Enrich] -> is_active=2
                        -> [OMDb Enrich] -> is_active=3 (success)
                                         -> is_active=4 (failure)

Usage:
    from enricher import full_enrichment, enrich_with_ai, enrich_with_omdb
    
    # Run complete pipeline
    results = full_enrichment(limit=100)
    
    # Run individual stages
    ai_count = enrich_with_ai(limit=50)
    omdb_count = enrich_with_omdb(limit=50)

Dependencies:
    - gemini_client.py: AI movie identification
    - omdb_client.py: Metadata fetching
    - storage.py: Database operations
    - config.py: Settings and rate limits
"""

import logging
import time
from typing import List, Dict, Optional

from config import AI_REQUEST_DELAY
from storage import (
    get_unenriched_movies,
    get_movies_without_omdb,
    update_sqlite_record,
    read_csv,
    update_csv,
    get_all_movies_sqlite,
    reset_failed_to_pending_omdb
)
from ai_provider import identify_movie
from omdb_client import fetch_movie_data, fetch_by_imdb_id, fetch_by_title

import re

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
# Set up logging for enrichment operations.
# Logs to both console and dedicated enrichment log file.

logger = logging.getLogger(__name__)

# Logging is configured centrally in main.py (single file: data/enrichment.log)
# and propagates here via the root logger. We no longer attach a separate file
# handler, which previously produced a second, duplicate log destination.


# =============================================================================
# MATCH VERIFICATION
# =============================================================================

def verify_match(ai_title: str, ai_year: str, omdb_title: str, omdb_year: str) -> bool:
    """
    Verify if OMDb result matches AI suggestion.
    
    Compares AI-identified movie details with OMDb results to ensure
    the correct movie was found. Uses fuzzy matching for titles and
    allows 1-year tolerance for release years.
    
    Args:
        ai_title (str): Movie title from AI identification.
                        Example: "The Matrix"
        
        ai_year (str): Release year from AI identification.
                       Example: "1999" or "NA"
        
        omdb_title (str): Movie title from OMDb response.
                          Example: "The Matrix"
        
        omdb_year (str): Release year from OMDb response.
                         Example: "1999" or "NA"
    
    Returns:
        bool: True if the results match sufficiently, False otherwise.
    
    Matching Rules:
        1. Title Match (required):
           - Both titles are normalized (lowercase, alphanumeric only)
           - Either title can contain the other (handles subtitles)
           - For very short titles (<4 chars), exact match required
        
        2. Year Match (optional but validated if both present):
           - If both years are provided, they must be within 1 year
           - Accounts for year-end/year-start release differences
    
    Example:
        >>> verify_match("The Matrix", "1999", "The Matrix", "1999")
        True
        >>> verify_match("Matrix", "1999", "The Matrix", "1999")
        True  # "matrix" is in "thematrix"
        >>> verify_match("The Matrix", "1999", "The Matrix", "2021")
        False  # Year difference > 1
    """
    # Title is required from OMDb
    if not omdb_title or omdb_title == "NA":
        return False
    
    # Normalize function: lowercase, alphanumeric only
    def normalize(s):
        if not s:
            return ""
        return re.sub(r'[^a-zA-Z0-9]', '', s.lower())
    
    # Normalize both titles
    t1 = normalize(ai_title)
    t2 = normalize(omdb_title)
    
    # Title matching logic
    # For short titles, require exact match to avoid false positives
    if len(t1) < 4 or len(t2) < 4:
        title_match = t1 == t2
    else:
        # Either title can contain the other
        # Handles cases like "Inception" matching "Inception (2010)"
        title_match = (t1 in t2) or (t2 in t1)
    
    # Year matching logic
    year_match = True  # Default to True if years not provided
    
    if ai_year and ai_year != "NA" and omdb_year and omdb_year != "NA":
        try:
            # Clean years - remove any non-digit characters
            y1_str = re.sub(r'\D', '', str(ai_year))[:4]
            y2_str = re.sub(r'\D', '', str(omdb_year))[:4]
            
            if y1_str and y2_str:
                y1 = int(y1_str)
                y2 = int(y2_str)
                
                # Allow 1-year tolerance
                # Movies released late in year may have different dates in different regions
                if abs(y1 - y2) > 1:
                    year_match = False
        except:
            # If parsing fails, be lenient and allow match
            pass
    
    return title_match and year_match


# =============================================================================
# AI ENRICHMENT (STEP 1)
# =============================================================================

def enrich_with_ai(limit: Optional[int] = None) -> int:
    """
    Enrich movies using Gemini AI.
    
    Processes movies with is_active=1 (pending AI enrichment).
    For each movie, calls the AI pipeline to identify the movie
    and extract: title, year, and IMDb ID.
    
    Args:
        limit (int, optional): Maximum number of movies to process.
                               If None, processes all pending movies.
                               Useful for testing or rate limit management.
    
    Returns:
        int: Number of movies successfully enriched.
    
    Processing Steps:
        1. Fetch movies with is_active=1
        2. For each movie:
           a. Call identify_movie() with filename and parsed data
           b. Store AI results (ai_title, ai_year, ai_imdb_id)
           c. Update is_active to 2 (ready for OMDb)
           d. Wait for AI_REQUEST_DELAY to avoid rate limits
        3. Sync changes to CSV
    
    State Transitions:
        is_active: 1 -> 2
    
    Error Handling:
        - Individual movie failures are logged and skipped
        - Pipeline continues with remaining movies
        - Failed movies remain at is_active=1 for retry
    
    Example:
        >>> # Enrich first 10 movies
        >>> count = enrich_with_ai(limit=10)
        >>> print(f"Enriched {count} movies")
    """
    # Get movies pending AI enrichment (is_active = 1)
    movies = get_unenriched_movies()
    
    # Apply limit if specified
    if limit:
        movies = movies[:limit]
    
    # Handle empty queue
    if not movies:
        logger.info("No movies pending AI enrichment")
        return 0
    
    logger.info(f"Starting AI enrichment for {len(movies)} movies...")
    enriched_count = 0
    
    # Process each movie
    for i, movie in enumerate(movies):
        logger.info(f"[{i+1}/{len(movies)}] Processing: {movie['file_name']}")
        
        try:
            # Call AI identification pipeline
            # This runs the 2-step process: Search -> Format
            result = identify_movie(
                file_name=movie["file_name"],
                extracted_name=movie.get("extracted_name", "NA"),
                extracted_year=movie.get("extracted_year", "NA")
            )
            
            # Prepare database updates
            # Store AI results and advance state to 2
            updates = {
                "ai_title": result.get("movie_title", "NA"),
                "ai_year": result.get("year", "NA"),
                "ai_imdb_id": result.get("imdb_id", "NA"),
                "is_active": 2,  # Mark ready for OMDb enrichment
                # Note: imdb_id (verified) is NOT updated here
                # That happens in OMDb enrichment after verification
            }
            
            # Update database record
            update_sqlite_record(movie["uuid"], updates)
            enriched_count += 1
            
            logger.info(f"  -> {result.get('movie_title', 'NA')} ({result.get('year', 'NA')}) [{result.get('imdb_id', 'NA')}]")
            
            # Rate limiting to avoid API quota issues
            if i < len(movies) - 1:
                time.sleep(AI_REQUEST_DELAY)
                
        except Exception as e:
            # Log error but continue with next movie
            logger.error(f"  -> Error: {e}")
            continue
    
    # Sync SQLite changes back to CSV
    sync_sqlite_to_csv()
    
    logger.info(f"AI enrichment complete. Enriched {enriched_count} movies.")
    return enriched_count


def enrich_with_ai_bulk(limit: Optional[int] = None) -> int:
    """
    Enrich movies using Gemini AI in Bulk Mode.
    
    Faster alternative to enrich_with_ai() that processes multiple
    movies in a single API call. Less accurate for difficult titles
    but significantly faster for large batches.
    
    Args:
        limit (int, optional): Maximum number of movies to process.
                               If None, processes all pending movies.
    
    Returns:
        int: Number of movies successfully enriched.
    
    Processing:
        - Movies are processed in chunks of CHUNK_SIZE (50)
        - Each chunk is sent in a single API call
        - Results are mapped back to UUIDs
    
    Trade-offs vs Standard Mode:
        + Much faster (50 movies per API call)
        - May be less accurate for obscure titles
        - Harder to retry individual failures
    
    Example:
        >>> count = enrich_with_ai_bulk(limit=100)
        >>> print(f"Enriched {count} movies in bulk mode")
    """
    from ai_provider import identify_movies_bulk

    # Get movies pending AI enrichment
    movies = get_unenriched_movies()
    
    if limit:
        movies = movies[:limit]
    
    if not movies:
        logger.info("No movies pending AI enrichment")
        return 0
    
    logger.info(f"Starting BULK AI enrichment for {len(movies)} movies...")
    
    # Process in chunks
    CHUNK_SIZE = 50  # Maximum movies per API call
    enriched_count = 0
    
    for i in range(0, len(movies), CHUNK_SIZE):
        chunk = movies[i : i + CHUNK_SIZE]
        logger.info(f"Processing chunk {i//CHUNK_SIZE + 1} ({len(chunk)} movies)...")
        
        try:
            # Single API call for entire chunk
            results = identify_movies_bulk(chunk)
            
            # Create UUID -> result mapping
            results_map = {r.get("id"): r for r in results if r.get("id")}
            
            # Update each movie in the chunk
            for movie in chunk:
                uuid_val = movie["uuid"]
                
                if uuid_val in results_map:
                    res = results_map[uuid_val]
                    
                    updates = {
                        "ai_title": res.get("movie_title", "NA"),
                        "ai_year": res.get("year", "NA"),
                        "ai_imdb_id": res.get("imdb_id", "NA"),
                        "is_active": 2  # Ready for OMDb
                    }
                    
                    # Only update if we got a valid result
                    if updates["ai_title"] != "NA":
                        update_sqlite_record(uuid_val, updates)
                        enriched_count += 1
                        logger.info(f"  -> {updates['ai_title']} ({updates['ai_year']})")
                else:
                    logger.warning(f"  -> No result returned for {movie['file_name']}")
                    
            # Brief pause between chunks
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            continue
    
    # Sync to CSV
    sync_sqlite_to_csv()
    
    logger.info(f"Bulk AI enrichment complete. Enriched {enriched_count} movies.")
    return enriched_count


# =============================================================================
# OMDB ENRICHMENT (STEP 2)
# =============================================================================

def enrich_with_omdb(limit: Optional[int] = None) -> int:
    """
    Enrich movies using OMDb API.
    
    Processes movies with is_active=2 (AI complete, pending OMDb).
    For each movie, fetches detailed metadata from OMDb using the
    AI-identified title and year.
    
    Args:
        limit (int, optional): Maximum number of movies to process.
                               If None, processes all pending movies.
    
    Returns:
        int: Number of movies processed (includes failures).
    
    Processing Steps:
        1. Fetch movies with is_active=2
        2. For each movie:
           a. Search OMDb by AI title/year
           b. Store metadata (title, year, genre, poster, etc.)
           c. Update is_active to 3 (success) or 4 (failure)
        3. Sync changes to CSV
    
    State Transitions:
        is_active: 2 -> 3 (success)
        is_active: 2 -> 4 (failure, needs manual fix)
    
    Metadata Fields Updated:
        - title, year, genre, director, actors
        - plot, runtime, language, country
        - awards, poster, imdb_rating, box_office
        - imdb_id (verified), additional_info
    
    Error Handling:
        - Movies not found in OMDb: is_active set to 4
        - Network errors: Logged, movie skipped (remains at 2)
    
    Example:
        >>> count = enrich_with_omdb(limit=50)
        >>> print(f"Processed {count} movies")
    """
    # Get movies ready for OMDb enrichment (is_active = 2)
    movies = get_movies_without_omdb()
    
    if limit:
        movies = movies[:limit]
    
    if not movies:
        logger.info("No movies pending OMDb enrichment")
        return 0
    
    logger.info(f"Starting OMDb enrichment for {len(movies)} movies...")
    enriched_count = 0
    
    for i, movie in enumerate(movies):
        logger.info(f"[{i+1}/{len(movies)}] Fetching OMDb data: {movie.get('ai_title', movie['file_name'])}")
        
        try:
            # Get AI-identified values
            ai_title = movie.get("ai_title", "NA")
            ai_year = movie.get("ai_year", "NA")
            ai_imdb_id = movie.get("ai_imdb_id", "NA")

            # Look up OMDb. fetch_movie_data prefers the AI-found IMDb ID
            # (an exact, unambiguous match) and only falls back to a
            # title/year search if the ID is missing or returns nothing.
            res = fetch_movie_data(imdb_id=ai_imdb_id, title=ai_title, year=ai_year)

            if res.get("title") != "NA":
                result = res
                match_found = True
                logger.info(f"  -> Found: {result.get('title')} ({result.get('year')})")
            else:
                logger.warning(f"  -> No OMDb match found for AI Title: {ai_title}")
                match_found = False

            # Handle failed lookups
            if not match_found:
                # Mark as failed for manual intervention
                update_sqlite_record(movie["uuid"], {"is_active": 4})
                enriched_count += 1  # Count as processed even if failed
                continue

            # Verify the OMDb result actually matches what the AI identified.
            # A title-only fallback can return a different movie (remakes,
            # common titles), so reject mismatches rather than silently
            # attaching the wrong metadata. Skip verification when the lookup
            # was by exact IMDb ID, which is already unambiguous.
            matched_by_id = (
                ai_imdb_id != "NA"
                and result.get("imdb_id", "NA") == ai_imdb_id
            )
            if not matched_by_id and not verify_match(
                ai_title, ai_year, result.get("title", "NA"), result.get("year", "NA")
            ):
                logger.warning(
                    f"  -> OMDb result rejected (mismatch): "
                    f"AI='{ai_title}' ({ai_year}) vs "
                    f"OMDb='{result.get('title')}' ({result.get('year')})"
                )
                update_sqlite_record(movie["uuid"], {"is_active": 4})
                enriched_count += 1  # Count as processed even if rejected
                continue

            # Prepare comprehensive update with all OMDb fields
            updates = {
                "title": result.get("title", "NA"),
                "year": result.get("year", "NA"),
                "genre": result.get("genre", "NA"),
                "director": result.get("director", "NA"),
                "actors": result.get("actors", "NA"),
                "plot": result.get("plot", "NA"),
                "runtime": result.get("runtime", "NA"),
                "language": result.get("language", "NA"),
                "country": result.get("country", "NA"),
                "awards": result.get("awards", "NA"),
                "poster": result.get("poster", "NA"),
                "imdb_rating": result.get("imdb_rating", "NA"),
                "box_office": result.get("box_office", "NA"),
                "additional_info": result.get("additional_info", "NA")
            }
            
            # Update verified IMDb ID (from OMDb response)
            if result.get("imdb_id", "NA") != "NA":
                updates["imdb_id"] = result["imdb_id"]
            
            # Mark as SUCCESS (is_active = 3)
            updates["is_active"] = 3
            
            # Update database
            update_sqlite_record(movie["uuid"], updates)
            enriched_count += 1
            
            logger.info(f"  -> {result.get('title', 'NA')} | IMDb: {result.get('imdb_rating', 'NA')} | {result.get('genre', 'NA')} | Status: COMPLETE")
            
            # Brief delay to be nice to OMDb API
            if i < len(movies) - 1:
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"  -> Error: {e}")
            continue
    
    # Sync to CSV
    sync_sqlite_to_csv()
    
    logger.info(f"OMDb enrichment complete. Enriched {enriched_count} movies.")
    return enriched_count


# =============================================================================
# RETRY FAILED
# =============================================================================

def retry_failed_omdb(limit: Optional[int] = None) -> int:
    """
    Retry movies that previously failed OMDb enrichment (is_active = 4).

    Resets failed movies back to pending OMDb (is_active = 2) and runs the
    OMDb enrichment pass again. This recovers:
      - transient failures (network/rate errors at the time), and
      - matches that now succeed via the AI IMDb ID (the verified-ID path
        skips the title/year verification that may have rejected them).

    Movies that fail again are returned to is_active = 4. Genuinely
    unmatchable titles will keep failing and are best fixed via the web UI
    manual search, or by re-running AI enrichment to get a better title/ID.

    Args:
        limit (int, optional): Maximum number of movies to process.

    Returns:
        int: Number of movies processed by the OMDb pass (0 if none failed).
    """
    reset_count = reset_failed_to_pending_omdb()
    logger.info(f"Reset {reset_count} failed movie(s) to pending OMDb")

    if reset_count == 0:
        logger.info("No failed movies to retry")
        return 0

    return enrich_with_omdb(limit)


# =============================================================================
# FULL PIPELINE
# =============================================================================

def full_enrichment(limit: Optional[int] = None) -> Dict:
    """
    Run full enrichment pipeline (AI + OMDb).
    
    Convenience function that runs both enrichment stages in sequence.
    First enriches with AI, then enriches with OMDb.
    
    Args:
        limit (int, optional): Maximum movies to process PER STAGE.
                               If limit=10, processes up to 10 in AI stage
                               and up to 10 in OMDb stage.
    
    Returns:
        Dict: Results dictionary with keys:
            - "ai_enriched" (int): Movies processed in AI stage
            - "omdb_enriched" (int): Movies processed in OMDb stage
    
    Example:
        >>> results = full_enrichment(limit=50)
        >>> print(f"AI: {results['ai_enriched']}, OMDb: {results['omdb_enriched']}")
    """
    logger.info("=" * 60)
    logger.info("FULL ENRICHMENT PIPELINE")
    logger.info("=" * 60)
    
    # Stage 1: AI enrichment
    ai_count = enrich_with_ai(limit)
    
    # Stage 2: OMDb enrichment
    omdb_count = enrich_with_omdb(limit)
    
    logger.info("=" * 60)
    logger.info(f"Pipeline complete. AI: {ai_count}, OMDb: {omdb_count}")
    logger.info("=" * 60)
    
    return {
        "ai_enriched": ai_count,
        "omdb_enriched": omdb_count
    }


# =============================================================================
# DATA SYNCHRONIZATION
# =============================================================================

def sync_sqlite_to_csv():
    """
    Sync SQLite data back to CSV.
    
    Reads all records from SQLite and writes them to CSV.
    Ensures both storage backends contain identical data.
    
    Args:
        None
    
    Returns:
        None
    
    Side Effects:
        - Completely rewrites CSV file with SQLite data
        - Logs record count for verification
    """
    # Delegate to the storage helper, which holds the write lock across the
    # read+rewrite so concurrent writers can't clobber the CSV.
    import storage
    storage.sync_sqlite_to_csv()


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Test enrichment pipeline
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    print("Enrichment Pipeline Test")
    print("=" * 50)
    
    # Show pending counts for each stage
    unenriched = get_unenriched_movies()
    pending_omdb = get_movies_without_omdb()
    
    print(f"Movies pending AI enrichment: {len(unenriched)}")
    print(f"Movies pending OMDb enrichment: {len(pending_omdb)}")
    
    print("\nRun with:")
    print("  python main.py --enrich --limit 5      # AI enrich 5 movies")
    print("  python main.py --fetch-omdb --limit 5  # OMDb fetch 5 movies")
