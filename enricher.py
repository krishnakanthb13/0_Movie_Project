"""
Movie Library Project - Enrichment Pipeline
Orchestrates AI and OMDb enrichment of movie data.
"""

import logging
import time
from typing import List, Dict, Optional

from config import AI_REQUEST_DELAY, LOG_FILE
from storage import (
    get_unenriched_movies,
    get_movies_without_omdb,
    update_sqlite_record,
    read_csv,
    update_csv,
    get_all_movies_sqlite
)
from gemini_client import identify_movie
from omdb_client import fetch_movie_data, fetch_by_imdb_id, fetch_by_title

import re

# Configure logging
logger = logging.getLogger(__name__)

# File handler for enrichment logs
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


def verify_match(ai_title: str, ai_year: str, omdb_title: str, omdb_year: str) -> bool:
    """
    Verify if OMDb result matches AI suggestion.
    """
    if not omdb_title or omdb_title == "NA":
        return False
        
    # Title Check
    def normalize(s):
        if not s: return ""
        return re.sub(r'[^a-zA-Z0-9]', '', s.lower())
        
    t1 = normalize(ai_title)
    t2 = normalize(omdb_title)
    
    # If one title is very short, be stricter
    if len(t1) < 4 or len(t2) < 4:
        title_match = t1 == t2
    else:
        title_match = (t1 in t2) or (t2 in t1)
    
    # Year Check
    year_match = True
    if ai_year and ai_year != "NA" and omdb_year and omdb_year != "NA":
        try:
            # Clean years (remove non-digits)
            y1_str = re.sub(r'\D', '', str(ai_year))[:4]
            y2_str = re.sub(r'\D', '', str(omdb_year))[:4]
            
            if y1_str and y2_str:
                y1 = int(y1_str)
                y2 = int(y2_str)
                if abs(y1 - y2) > 1:
                    year_match = False
        except:
            pass # Relax if parsing fails
            
    return title_match and year_match


def enrich_with_ai(limit: Optional[int] = None) -> int:
    """
    Enrich movies using Gemini AI.
    
    Args:
        limit: Optional limit on number of movies to process
        
    Returns:
        Number of movies enriched
    """
    # Get unenriched movies
    movies = get_unenriched_movies()
    
    if limit:
        movies = movies[:limit]
    
    if not movies:
        logger.info("No movies pending AI enrichment")
        return 0
    
    logger.info(f"Starting AI enrichment for {len(movies)} movies...")
    enriched_count = 0
    
    for i, movie in enumerate(movies):
        logger.info(f"[{i+1}/{len(movies)}] Processing: {movie['file_name']}")
        
        try:
            # Get AI identification
            result = identify_movie(
                file_name=movie["file_name"],
                extracted_name=movie.get("extracted_name", "NA"),
                extracted_year=movie.get("extracted_year", "NA")
            )
            
            # Update database
            updates = {
                "ai_title": result.get("movie_title", "NA"),
                "ai_year": result.get("year", "NA"),
                "ai_imdb_id": result.get("imdb_id", "NA")
                # Note: We do NOT update verified "imdb_id" here waiting for OMDb confirmation
            }
            
            update_sqlite_record(movie["uuid"], updates)
            enriched_count += 1
            
            logger.info(f"  -> {result.get('movie_title', 'NA')} ({result.get('year', 'NA')}) [{result.get('imdb_id', 'NA')}]")
            
            # Note: is_active will be set to 2 after OMDb enrichment is complete
            
            # Rate limiting
            if i < len(movies) - 1:
                time.sleep(AI_REQUEST_DELAY)
                
        except Exception as e:
            logger.error(f"  -> Error: {e}")
            continue
    
    # Sync to CSV
    sync_sqlite_to_csv()
    
    logger.info(f"AI enrichment complete. Enriched {enriched_count} movies.")
    return enriched_count


def enrich_with_ai_bulk(limit: Optional[int] = None) -> int:
    """
    Enrich movies using Gemini AI in Bulk Mode.
    
    Args:
        limit: Optional limit on number of movies to process
        
    Returns:
        Number of movies enriched
    """
    from gemini_client import identify_movies_bulk
    
    # Get unenriched movies
    movies = get_unenriched_movies()
    
    if limit:
        movies = movies[:limit]
    
    if not movies:
        logger.info("No movies pending AI enrichment")
        return 0
    
    logger.info(f"Starting BULK AI enrichment for {len(movies)} movies...")
    
    # Process in chunks (maximum 50 per call)
    CHUNK_SIZE = 50
    enriched_count = 0
    
    for i in range(0, len(movies), CHUNK_SIZE):
        chunk = movies[i : i + CHUNK_SIZE]
        logger.info(f"Processing chunk {i//CHUNK_SIZE + 1} ({len(chunk)} movies)...")
        
        try:
            results = identify_movies_bulk(chunk)
            
            # Map results map to UUID map for easier lookup
            results_map = {r.get("id"): r for r in results if r.get("id")}
            
            for movie in chunk:
                uuid_val = movie["uuid"]
                if uuid_val in results_map:
                    res = results_map[uuid_val]
                    
                    updates = {
                        "ai_title": res.get("movie_title", "NA"),
                        "ai_year": res.get("year", "NA"),
                        "ai_imdb_id": res.get("imdb_id", "NA")
                    }
                    
                    if updates["ai_title"] != "NA":
                        update_sqlite_record(uuid_val, updates)
                        enriched_count += 1
                        logger.info(f"  -> {updates['ai_title']} ({updates['ai_year']})")
                else:
                    logger.warning(f"  -> No result returned for {movie['file_name']}")
                    
            # Small delay between chunks
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            continue
            
    # Sync to CSV
    sync_sqlite_to_csv()
    
    logger.info(f"Bulk AI enrichment complete. Enriched {enriched_count} movies.")
    return enriched_count


def enrich_with_omdb(limit: Optional[int] = None) -> int:
    """
    Enrich movies using OMDb API.
    
    Args:
        limit: Optional limit on number of movies to process
        
    Returns:
        Number of movies enriched
    """
    # Get movies with IMDb ID but no OMDb data
    movies = get_movies_without_omdb()
    
    # Also include movies that have AI title but no OMDb data
    all_movies = get_all_movies_sqlite()
    for movie in all_movies:
        if movie.get("ai_title", "NA") != "NA" and movie.get("title", "NA") == "NA":
            if movie not in movies:
                movies.append(movie)
    
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
            ai_id = movie.get("ai_imdb_id", "NA")
            ai_title = movie.get("ai_title", "NA")
            ai_year = movie.get("ai_year", "NA")

            # Fallback for legacy records that might have ID in imdb_id but not ai_imdb_id
            if ai_id == "NA":
                ai_id = movie.get("imdb_id", "NA")
            
            result = {}
            match_found = False
            
            # 1. Try with AI ID (if available)
            if ai_id and ai_id != "NA":
                res = fetch_by_imdb_id(ai_id)
                # Check if valid response
                if res.get("title") != "NA":
                    # Verify Match
                    if verify_match(ai_title, ai_year, res.get("title"), res.get("year")):
                        result = res
                        match_found = True
                        logger.info(f"  -> Verified Match via ID: {ai_id}")
                    else:
                        logger.warning(f"  -> Mismatch via ID {ai_id}: AI({ai_title}) vs OMDb({res.get('title')}). Retrying search...")
                else:
                    logger.warning(f"  -> Invalid OMDb response for ID {ai_id}")

            # 2. Search by Title/Year if ID failed or mismatched
            if not match_found:
                 res = fetch_by_title(ai_title, ai_year)
                 if res.get("title") != "NA":
                     result = res
                     match_found = True
                     logger.info(f"  -> Found via Search: {ai_title}")
            
            if not match_found:
                 logger.warning("  -> No OMDb match found")
                 continue

            # Update database
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
                "box_office": result.get("box_office", "NA")
            }
            
            # Update verified imdb_id
            if result.get("imdb_id", "NA") != "NA":
                updates["imdb_id"] = result["imdb_id"]
            
            # Mark as fully enriched (is_active = 2)
            updates["is_active"] = 2
            
            update_sqlite_record(movie["uuid"], updates)
            enriched_count += 1
            
            logger.info(f"  -> {result.get('title', 'NA')} | IMDb: {result.get('imdb_rating', 'NA')} | {result.get('genre', 'NA')} | Status: COMPLETE")
            
            # Small delay to be nice to the API
            if i < len(movies) - 1:
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"  -> Error: {e}")
            continue
    
    # Sync to CSV
    sync_sqlite_to_csv()
    
    logger.info(f"OMDb enrichment complete. Enriched {enriched_count} movies.")
    return enriched_count


def full_enrichment(limit: Optional[int] = None) -> Dict:
    """
    Run full enrichment pipeline (AI + OMDb).
    
    Args:
        limit: Optional limit on number of movies per stage
        
    Returns:
        Dict with counts for each stage
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


def sync_sqlite_to_csv():
    """Sync SQLite data back to CSV."""
    movies = get_all_movies_sqlite()
    update_csv(movies)
    logger.debug(f"Synced {len(movies)} records to CSV")


if __name__ == "__main__":
    # Test enrichment
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    print("Enrichment Pipeline Test")
    print("=" * 50)
    
    # Show pending counts
    unenriched = get_unenriched_movies()
    pending_omdb = get_movies_without_omdb()
    
    print(f"Movies pending AI enrichment: {len(unenriched)}")
    print(f"Movies pending OMDb enrichment: {len(pending_omdb)}")
    
    print("\nRun with:")
    print("  python main.py --enrich --limit 5      # AI enrich 5 movies")
    print("  python main.py --fetch-omdb --limit 5  # OMDb fetch 5 movies")
