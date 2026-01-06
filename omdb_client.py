"""
Movie Library Project - OMDb API Client
Fetches movie metadata from the Open Movie Database (OMDb).
"""

import logging
from typing import Dict, Optional

import requests

from config import OMDB_API_KEY

logger = logging.getLogger(__name__)

OMDB_BASE_URL = "http://www.omdbapi.com/"


def fetch_by_imdb_id(imdb_id: str) -> Dict:
    """
    Fetch movie data by IMDb ID.
    
    Args:
        imdb_id: IMDb ID (e.g., "tt0133093")
        
    Returns:
        Dict with movie metadata or default NA values
    """
    default_response = get_default_response()
    
    if not OMDB_API_KEY:
        logger.error("OMDB_API_KEY not configured")
        return default_response
    
    if not imdb_id or imdb_id == "NA":
        return default_response
    
    try:
        params = {
            "apikey": OMDB_API_KEY,
            "i": imdb_id,
            "plot": "short"
        }
        
        response = requests.get(OMDB_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("Response") == "False":
            logger.warning(f"OMDb error for {imdb_id}: {data.get('Error', 'Unknown error')}")
            return default_response
        
        return parse_omdb_response(data)
        
    except requests.RequestException as e:
        logger.error(f"OMDb request failed for {imdb_id}: {e}")
        return default_response


def fetch_by_title(title: str, year: str = None) -> Dict:
    """
    Fetch movie data by title and optional year.
    
    Args:
        title: Movie title
        year: Optional release year
        
    Returns:
        Dict with movie metadata or default NA values
    """
    default_response = get_default_response()
    
    if not OMDB_API_KEY:
        logger.error("OMDB_API_KEY not configured")
        return default_response
    
    if not title or title == "NA":
        return default_response
    
    try:
        params = {
            "apikey": OMDB_API_KEY,
            "t": title,
            "plot": "short"
        }
        
        if year and year != "NA":
            params["y"] = year
        
        response = requests.get(OMDB_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("Response") == "False":
            logger.warning(f"OMDb error for '{title}': {data.get('Error', 'Unknown error')}")
            return default_response
        
        return parse_omdb_response(data)
        
    except requests.RequestException as e:
        logger.error(f"OMDb request failed for '{title}': {e}")
        return default_response


def get_default_response() -> Dict:
    """Get default response with NA values."""
    return {
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
        "imdb_id": "NA",
        "additional_info": "NA"
    }


def parse_omdb_response(data: Dict) -> Dict:
    """
    Parse OMDb API response into our schema.
    
    Args:
        data: Raw OMDb API response
        
    Returns:
        Dict with normalized field names
    """
    # Keys that we already map to specific columns
    captured_keys = {
        "Title", "Year", "Genre", "Director", "Actors", "Plot",
        "Runtime", "Language", "Country", "Awards", "Poster",
        "imdbRating", "BoxOffice", "imdbID", "Response", "Type"
    }

    # Collect additional info
    additional_info_lines = []
    
    # Process Ratings separately to format nicely if needed, or just let them fall through 
    # But usually Ratings is a list of dicts. Let's handle special cases or just all others.
    
    for key, value in data.items():
        if key not in captured_keys:
             # Handle list/dict types if necessary (like Ratings)
             if isinstance(value, list):
                 for item in value:
                     if isinstance(item, dict):
                         # Example: Source: Value
                         parts = [f"{k}: {v}" for k,v in item.items()]
                         additional_info_lines.append(" | ".join(parts))
             elif isinstance(value, dict):
                 pass # Simple implementation ignores complex nested dicts for now
             else:
                 additional_info_lines.append(f"**{key}**: {value}")

    additional_info_str = "\n".join(additional_info_lines)

    return {
        "title": data.get("Title", "NA"),
        "year": data.get("Year", "NA"),
        "genre": data.get("Genre", "NA"),
        "director": data.get("Director", "NA"),
        "actors": data.get("Actors", "NA"),
        "plot": data.get("Plot", "NA"),
        "runtime": data.get("Runtime", "NA"),
        "language": data.get("Language", "NA"),
        "country": data.get("Country", "NA"),
        "awards": data.get("Awards", "NA"),
        "poster": data.get("Poster", "NA"),
        "imdb_rating": data.get("imdbRating", "NA"),
        "box_office": data.get("BoxOffice", "NA"),
        "imdb_id": data.get("imdbID", "NA"),
        "additional_info": additional_info_str
    }


def fetch_movie_data(imdb_id: str = None, title: str = None, year: str = None) -> Dict:
    """
    Fetch movie data using IMDb ID (preferred) or title+year fallback.
    
    Args:
        imdb_id: IMDb ID (preferred)
        title: Movie title (fallback)
        year: Release year (optional, for fallback)
        
    Returns:
        Dict with movie metadata
    """
    # Try IMDb ID first
    if imdb_id and imdb_id != "NA":
        result = fetch_by_imdb_id(imdb_id)
        if result.get("title") != "NA":
            logger.info(f"Fetched by IMDb ID: {imdb_id} -> {result.get('title')}")
            return result
    
    # Fallback to title search
    if title and title != "NA":
        result = fetch_by_title(title, year)
        if result.get("title") != "NA":
            logger.info(f"Fetched by title: {title} -> {result.get('title')}")
            return result
    
    logger.warning(f"Could not fetch data for imdb_id={imdb_id}, title={title}")
    return get_default_response()


if __name__ == "__main__":
    # Test the OMDb client
    logging.basicConfig(level=logging.INFO)
    
    print("Testing OMDb API Client...")
    print("-" * 50)
    
    if not OMDB_API_KEY:
        print("ERROR: OMDB_API_KEY not set in .env file")
        print("Please add your API key to: e:\\0 Movie Project\\.env")
        exit(1)
    
    # Test by IMDb ID
    print("\n1. Fetching The Matrix by IMDb ID...")
    result = fetch_by_imdb_id("tt0133093")
    print(f"   Title: {result['title']}")
    print(f"   Year: {result['year']}")
    print(f"   IMDb Rating: {result['imdb_rating']}")
    print(f"   Genre: {result['genre']}")
    
    # Test by title
    print("\n2. Fetching Inception by title...")
    result = fetch_by_title("Inception", "2010")
    print(f"   Title: {result['title']}")
    print(f"   Year: {result['year']}")
    print(f"   IMDb Rating: {result['imdb_rating']}")
    print(f"   Director: {result['director']}")
    
    print("\n" + "-" * 50)
    print("OMDb client test complete!")
