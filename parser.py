"""
Movie Library Project - Filename Parser
Extracts movie name and year from video filenames.
"""

import re
import logging
from pathlib import Path
from typing import Tuple

from config import NOISE_PATTERNS, YEAR_PATTERN

logger = logging.getLogger(__name__)


def clean_filename(filename: str) -> str:
    """
    Remove extension and common noise from filename.
    
    Args:
        filename: Original video filename
        
    Returns:
        Cleaned filename string
    """
    # Remove extension
    name = Path(filename).stem
    
    # Replace common separators with spaces
    name = re.sub(r"[._\-]", " ", name)
    
    # Remove noise patterns (case insensitive)
    for pattern in NOISE_PATTERNS:
        name = re.sub(pattern, " ", name, flags=re.IGNORECASE)
    
    # Remove multiple spaces
    name = re.sub(r"\s+", " ", name)
    
    # Strip whitespace
    name = name.strip()
    
    return name


def extract_year(text: str) -> str:
    """
    Extract a valid movie year (1900-2099) from text.
    
    Args:
        text: Text to search for year
        
    Returns:
        Year string or "NA" if not found
    """
    matches = re.findall(YEAR_PATTERN, text)
    
    if not matches:
        return "NA"
    
    # Return the last match (usually the year is at the end)
    # Filter for reasonable years (1920-2030)
    valid_years = [y for y in matches if 1920 <= int(y) <= 2030]
    
    if valid_years:
        return valid_years[-1]  # Last valid year
    
    return "NA"


def extract_movie_name(filename: str, year: str = "NA") -> str:
    """
    Extract the movie name from a filename.
    
    Args:
        filename: Original video filename
        year: Already extracted year (to remove from name)
        
    Returns:
        Extracted movie name or "NA"
    """
    # Clean the filename first
    name = clean_filename(filename)
    
    # If we found a year, try to get text before it
    if year != "NA":
        # Split by year and take everything before
        parts = re.split(rf"\b{year}\b", name, maxsplit=1)
        if parts and parts[0].strip():
            name = parts[0].strip()
    
    # Final cleanup
    name = re.sub(r"\s+", " ", name).strip()
    
    # If name is too short or just numbers, return NA
    if len(name) < 2 or name.isdigit():
        return "NA"
    
    return name if name else "NA"


def parse_filename(filename: str) -> Tuple[str, str]:
    """
    Parse a video filename to extract movie name and year.
    
    Args:
        filename: Video filename to parse
        
    Returns:
        Tuple of (extracted_name, extracted_year)
        
    Examples:
        >>> parse_filename("The.Matrix.1999.1080p.BluRay.x264.mkv")
        ('The Matrix', '1999')
        
        >>> parse_filename("Inception (2010) [1080p].mp4")
        ('Inception', '2010')
    """
    # Extract year first
    year = extract_year(filename)
    
    # Extract name
    name = extract_movie_name(filename, year)
    
    logger.debug(f"Parsed '{filename}' -> name='{name}', year='{year}'")
    
    return name, year


if __name__ == "__main__":
    # Test cases
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
    
    for filename in test_files:
        name, year = parse_filename(filename)
        print(f"Input:  {filename}")
        print(f"Output: name='{name}', year='{year}'")
        print("-" * 60)
