"""
Movie Library Project - Name Cleaning Utility
Analyzes movie names for recurring noise tokens and removes them.
"""

import re
import argparse
import logging
from collections import Counter
from typing import List, Dict, Set

from storage import get_all_movies_sqlite, update_sqlite_record, update_csv, sync_csv_to_sqlite

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Common English stop words to PROTECT (don't remove even if recurring)
PROTECTED_WORDS = {
    "the", "and", "or", "of", "to", "in", "on", "at", "by", "for", "with", 
    "a", "an", "is", "are", "was", "were", "be", "been", "from", "part", 
    "vol", "chapter", "movie", "film"
}

def tokenize(text: str) -> List[str]:
    """Split text into words/tokens."""
    # Split by spaces and non-alphanumeric chars
    tokens = re.findall(r"\b\w+\b", text.lower())
    return tokens

def analyze_names(movies: List[Dict], threshold: int) -> Dict[str, int]:
    """Find recurring tokens in extracted names."""
    all_tokens = []
    
    for movie in movies:
        name = movie.get("extracted_name", "")
        # Skip if name matches file name (means parsing failed or empty)
        if name == movie.get("file_name", ""):
            continue
        if name and name != "NA":
            all_tokens.extend(tokenize(name))
            
    # Count frequencies
    counts = Counter(all_tokens)
    
    # Filter by threshold and protected words
    noise_candidates = {
        word: count for word, count in counts.items() 
        if count >= threshold and word not in PROTECTED_WORDS and not word.isdigit()
    }
    
    return noise_candidates

def clean_movie_name(name: str, noise_tokens: Set[str]) -> str:
    """Remove noise tokens from a name."""
    if not name or name == "NA":
        return name
        
    original = name
    
    # Case insensitive replacement
    # We rebuild the string token by token to be safe
    # But regex is better to preserve spacing
    
    cleaned = name
    for noise in noise_tokens:
        # Regex to match whole word, case insensitive
        pattern = re.compile(r'\b' + re.escape(noise) + r'\b', re.IGNORECASE)
        cleaned = pattern.sub('', cleaned)
    
    # Cleanup whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def run_cleaning(threshold: int = 5, apply_changes: bool = False):
    """Run the cleaning process."""
    movies = get_all_movies_sqlite()
    logger.info(f"Analyzing {len(movies)} movies with threshold {threshold}...")
    
    noise_candidates = analyze_names(movies, threshold)
    
    if not noise_candidates:
        logger.info("No recurring noise tokens found above threshold.")
        return

    logger.info("\nRecurring tokens found (Potential Noise):")
    logger.info("-" * 40)
    sorted_candidates = sorted(noise_candidates.items(), key=lambda x: x[1], reverse=True)
    
    noise_tokens = set()
    for word, count in sorted_candidates:
        logger.info(f"  '{word}' : {count} occurrences")
        noise_tokens.add(word)
    logger.info("-" * 40)
    
    if not apply_changes:
        logger.info("\nDry run complete. Use --apply to remove these tokens.")
        
        # Preview changes
        logger.info("\nPreview of changes:")
        logger.info("-" * 60)
        preview_count = 0
        for movie in movies:
            original = movie.get("extracted_name", "NA")
            cleaned = clean_movie_name(original, noise_tokens)
            
            if original != cleaned and cleaned:
                logger.info(f"  '{original}' -> '{cleaned}'")
                preview_count += 1
                if preview_count >= 10:
                    break
        if preview_count == 0:
            logger.info("  No changes would be made.")
        
        return

    # Apply changes
    logger.info("\nApplying changes...")
    updated_count = 0
    
    for movie in movies:
        original = movie.get("extracted_name", "NA")
        if original == "NA": 
            continue
            
        cleaned = clean_movie_name(original, noise_tokens)
        
        if original != cleaned and cleaned:
            # Update record
            # We assume user wants to update 'extracted_name' or should we update 'ai_title'?
            # Usually 'extracted_name' is the base. 
            # If 'title' (OMDb) exists, we usually display that.
            # But let's clear up the extracted name.
            
            update_sqlite_record(movie["uuid"], {"extracted_name": cleaned})
            updated_count += 1
            logger.info(f"Cleaned: '{original}' -> '{cleaned}'")
            
    if updated_count > 0:
        # Update CSV
        sync_csv_to_sqlite() # Actually this function syncs CSV TO SQLite. We want SQLite to CSV.
        # But wait, storage.py sync_sqlite_to_csv is not exported in __init__ properly in my view
        # Let's check storage.py exports.
        # It exports update_csv.
        
        all_movies = get_all_movies_sqlite()
        update_csv(all_movies)
        logger.info(f"\nSuccessfully cleaned {updated_count} movies.")
    else:
        logger.info("\nNo movies needed cleaning.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean recurring noise from movie names")
    parser.add_argument("--threshold", type=int, default=5, help="Minimum occurrences to consider token as noise")
    parser.add_argument("--apply", action="store_true", help="Apply changes to database")
    
    args = parser.parse_args()
    
    run_cleaning(args.threshold, args.apply)
