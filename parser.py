"""
Movie Library Project - Filename Parser Module
===============================================

Extracts movie title and year from video filenames using regex patterns.

Video files from various sources often have messy filenames containing
quality indicators, codec info, and release group tags. This module
cleans these filenames to extract the actual movie title and year.

Example Transformations:
    "The.Matrix.1999.1080p.BluRay.x264.mkv" -> ("The Matrix", "1999")
    "Inception (2010) [1080p].mp4" -> ("Inception", "2010")
    "random_video.avi" -> ("random video", "NA")

Algorithm:
    1. Remove file extension
    2. Replace separators (., _, -) with spaces
    3. Remove noise patterns (1080p, BluRay, x264, etc.)
    4. Extract year using regex
    5. Extract title (text before the year)

Usage:
    from parser import parse_filename
    
    name, year = parse_filename("The.Matrix.1999.1080p.BluRay.mkv")
    # name = "The Matrix", year = "1999"

Dependencies:
    - config.py: NOISE_PATTERNS, YEAR_PATTERN
"""

import re
import logging
from pathlib import Path
from typing import Tuple

from config import NOISE_PATTERNS, YEAR_PATTERN

# Get logger for this module
logger = logging.getLogger(__name__)


# =============================================================================
# FILENAME CLEANING
# =============================================================================

def clean_filename(filename: str) -> str:
    """
    Remove extension and common noise from a video filename.
    
    Applies a series of transformations to clean up messy filenames:
    1. Removes the file extension
    2. Replaces common separators with spaces
    3. Strips noise patterns defined in config.NOISE_PATTERNS
    4. Normalizes whitespace
    
    Args:
        filename (str): Original video filename including extension.
                        Example: "The.Matrix.1999.1080p.BluRay.x264.mkv"
    
    Returns:
        str: Cleaned filename with noise removed.
             Example: "The Matrix 1999"
    
    Processing Steps:
        1. Path(filename).stem - Removes extension (.mkv, .mp4, etc.)
        2. re.sub(r"[._\\-]", " ", name) - Converts separators to spaces
        3. Loop through NOISE_PATTERNS - Removes quality/codec indicators
        4. re.sub(r"\\s+", " ", name) - Collapses multiple spaces
        5. name.strip() - Removes leading/trailing whitespace
    
    Examples:
        >>> clean_filename("The.Matrix.1999.1080p.BluRay.x264.mkv")
        'The Matrix 1999'
        
        >>> clean_filename("Inception (2010) [1080p].mp4")
        'Inception 2010'
        
        >>> clean_filename("Movie_Title-2020.avi")
        'Movie Title 2020'
    
    Note:
        The year is intentionally kept in the output at this stage.
        It will be used by extract_year() and then removed in extract_movie_name().
    """
    # Step 1: Remove file extension using pathlib
    # Path.stem returns filename without the last extension
    name = Path(filename).stem
    
    # Step 2: Replace common separators with spaces
    # Matches: periods (.), underscores (_), hyphens (-)
    name = re.sub(r"[._\-]", " ", name)
    
    # Step 3: Remove noise patterns (case insensitive)
    # Each pattern in NOISE_PATTERNS is applied in sequence
    for pattern in NOISE_PATTERNS:
        name = re.sub(pattern, " ", name, flags=re.IGNORECASE)
    
    # Step 4: Collapse multiple consecutive spaces into one
    name = re.sub(r"\s+", " ", name)
    
    # Step 5: Remove leading and trailing whitespace
    name = name.strip()
    
    return name


# =============================================================================
# YEAR EXTRACTION
# =============================================================================

def extract_year(text: str) -> str:
    """
    Extract a valid movie year (1920-2030) from text.
    
    Searches for 4-digit year patterns and validates them against
    a reasonable range for movie release years.
    
    Args:
        text (str): Text to search for year patterns.
                    Can be a filename or cleaned title string.
                    Example: "The Matrix 1999 Remastered"
    
    Returns:
        str: The extracted year as a string (e.g., "1999"),
             or "NA" if no valid year is found.
    
    Algorithm:
        1. Find all 4-digit patterns matching YEAR_PATTERN (19XX or 20XX)
        2. Filter to valid movie years (1920-2030)
        3. Return the LAST valid year found
    
    Why Last Match?
        Movie filenames often have misleading numbers at the start.
        Example: "2001.A.Space.Odyssey.1968.mkv"
        - First match: "2001" (part of title)
        - Last match: "1968" (actual release year) ✓
    
    Examples:
        >>> extract_year("The Matrix 1999")
        '1999'
        
        >>> extract_year("2001 A Space Odyssey 1968")
        '1968'  # Returns last valid year
        
        >>> extract_year("Some Movie Without Year")
        'NA'
        
        >>> extract_year("Movie 1850")  # Too old, filtered out
        'NA'
    
    Boundary Notes:
        - Years before 1920: Filtered out (few movies exist)
        - Years after 2030: Filtered out (future protection)
        - Pattern matches 1900-2099 initially, then filtered to 1920-2030
    """
    # Find all 4-digit patterns matching the year regex
    # YEAR_PATTERN from config matches: 19XX or 20XX
    matches = re.findall(YEAR_PATTERN, text)
    
    # Return "NA" if no year-like patterns found
    if not matches:
        return "NA"
    
    # Filter to reasonable movie years (1920-2030)
    # This excludes false positives like "1080" and far-future years
    valid_years = [y for y in matches if 1920 <= int(y) <= 2030]
    
    # Return the last valid year (most likely to be release year)
    if valid_years:
        return valid_years[-1]
    
    return "NA"


# =============================================================================
# MOVIE NAME EXTRACTION
# =============================================================================

def extract_movie_name(filename: str, year: str = "NA") -> str:
    """
    Extract the movie title from a filename.
    
    Cleans the filename and extracts the portion before the year,
    which is typically the movie title.
    
    Args:
        filename (str): Original video filename including extension.
                        Example: "The.Matrix.1999.1080p.BluRay.mkv"
        
        year (str): Previously extracted year to use as split point.
                    Defaults to "NA" if year is unknown.
                    Example: "1999"
    
    Returns:
        str: Extracted movie title, or "NA" if extraction fails.
             Example: "The Matrix"
    
    Algorithm:
        1. Clean the filename (remove extension, noise, normalize)
        2. If year is known, split text at year boundary
        3. Take everything BEFORE the year as the title
        4. Apply final cleanup (normalize spaces)
        5. Validate result (not too short, not all digits)
    
    Examples:
        >>> extract_movie_name("The.Matrix.1999.1080p.BluRay.mkv", "1999")
        'The Matrix'
        
        >>> extract_movie_name("Inception (2010) [1080p].mp4", "2010")
        'Inception'
        
        >>> extract_movie_name("random_video.avi", "NA")
        'random video'  # Returns cleaned name without year split
    
    Edge Case Handling:
        - Very short names (< 2 chars): Returns "NA"
        - All-digit names: Returns "NA" (likely misparse)
        - No year provided: Returns full cleaned name
    """
    # Step 1: Clean the filename using our cleaning function
    name = clean_filename(filename)
    
    # Step 2: If we found a year, try to extract text before it
    if year != "NA":
        # Split by the year pattern (word boundary to avoid partial matches)
        # maxsplit=1 ensures we only split at the first occurrence
        parts = re.split(rf"\b{year}\b", name, maxsplit=1)
        
        # Use the part before the year if it exists and has content
        if parts and parts[0].strip():
            name = parts[0].strip()
    
    # Step 3: Final cleanup - normalize spaces
    name = re.sub(r"\s+", " ", name).strip()
    
    # Step 4: Validation - reject invalid results
    # Too short names are likely parsing errors
    if len(name) < 2:
        return "NA"
    
    # All-digit names are likely year fragments or resolution numbers
    if name.isdigit():
        return "NA"
    
    # Return the extracted name, or "NA" if empty
    return name if name else "NA"


# =============================================================================
# MAIN PARSING FUNCTION
# =============================================================================

def parse_filename(filename: str) -> Tuple[str, str]:
    """
    Parse a video filename to extract movie title and year.
    
    Main entry point for filename parsing. Combines year extraction
    and name extraction into a single convenient function.
    
    Args:
        filename (str): Video filename to parse.
                        Can include path or just the filename.
                        Example: "The.Matrix.1999.1080p.BluRay.x264.mkv"
    
    Returns:
        Tuple[str, str]: A tuple containing:
            - extracted_name (str): The movie title or "NA"
            - extracted_year (str): The release year or "NA"
    
    Processing Order:
        1. Extract year FIRST (needed for name extraction)
        2. Extract name using year as reference point
        3. Return both values as tuple
    
    Examples:
        >>> parse_filename("The.Matrix.1999.1080p.BluRay.x264.mkv")
        ('The Matrix', '1999')
        
        >>> parse_filename("Inception (2010) [1080p].mp4")
        ('Inception', '2010')
        
        >>> parse_filename("Avengers.Endgame.2019.2160p.WEB-DL.x265.HEVC.mkv")
        ('Avengers Endgame', '2019')
        
        >>> parse_filename("The Godfather 1972 REMASTERED 1080p BluRay.avi")
        ('The Godfather', '1972')
        
        >>> parse_filename("random_video_without_year.mp4")
        ('random video without year', 'NA')
        
        >>> parse_filename("2001.A.Space.Odyssey.1968.720p.mkv")
        ('2001 A Space Odyssey', '1968')
    
    Note:
        Debug logging is emitted showing the parsing result.
        Use logging level DEBUG to see these messages.
    """
    # Step 1: Extract year first (needed for name extraction)
    year = extract_year(filename)
    
    # Step 2: Extract movie name using the found year
    name = extract_movie_name(filename, year)
    
    # Debug logging for troubleshooting
    logger.debug(f"Parsed '{filename}' -> name='{name}', year='{year}'")
    
    return name, year


# =============================================================================
# STANDALONE TEST
# =============================================================================
# This block runs when the module is executed directly (not imported).
# Provides test cases to verify parsing functionality.

if __name__ == "__main__":
    # Test cases covering various filename formats
    test_files = [
        "The.Matrix.1999.1080p.BluRay.x264.mkv",
        "Inception (2010) [1080p].mp4",
        "Avengers.Endgame.2019.2160p.WEB-DL.x265.HEVC.mkv",
        "The Godfather 1972 REMASTERED 1080p BluRay.avi",
        "random_video_without_year.mp4",
        "2001.A.Space.Odyssey.1968.720p.mkv",
        "Avatar.2009.EXTENDED.1080p.BluRay.AAC.x264.mkv",
        "Parasite.2019.KOREAN.1080p.BluRay.mkv",
    ]
    
    print("Filename Parser Test Results:")
    print("-" * 60)
    
    # Process each test file
    for filename in test_files:
        name, year = parse_filename(filename)
        print(f"Input:  {filename}")
        print(f"Output: name='{name}', year='{year}'")
        print("-" * 60)
