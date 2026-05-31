"""
Movie Library Project - OMDb API Client Module
===============================================

Fetches movie metadata from the Open Movie Database (OMDb).

OMDb is a free web service to obtain movie information. This module
provides functions to query OMDb by IMDb ID (preferred) or by title/year
(fallback), and normalizes the response into our schema.

API Information:
    - Base URL: http://www.omdbapi.com/
    - Rate Limit: 1,000 requests per day (free tier)
    - Documentation: https://www.omdbapi.com/
    - API Key: https://www.omdbapi.com/apikey.aspx

Data Retrieved:
    - Title, Year, Genre, Runtime
    - Director, Actors, Plot
    - Language, Country, Awards
    - Poster URL, IMDb Rating
    - Box Office earnings
    - Additional ratings (Rotten Tomatoes, Metacritic)

Usage:
    from omdb_client import fetch_movie_data
    
    # Preferred: Fetch by IMDb ID (most accurate)
    result = fetch_movie_data(imdb_id="tt0133093")
    
    # Alternative: Fetch by title and year
    result = fetch_movie_data(title="The Matrix", year="1999")

Dependencies:
    - requests: HTTP library for API calls
    - config.py: OMDB_API_KEY
"""

import logging
from typing import Dict, Optional

import requests

from config import OMDB_API_KEY

# Get logger for this module
logger = logging.getLogger(__name__)

# =============================================================================
# API CONFIGURATION
# =============================================================================

# OMDB_BASE_URL: Base URL for OMDb API requests.
# All queries are made to this endpoint with parameters.
OMDB_BASE_URL = "http://www.omdbapi.com/"


# =============================================================================
# FETCH BY IMDB ID (PREFERRED)
# =============================================================================

def fetch_by_imdb_id(imdb_id: str) -> Dict:
    """
    Fetch movie data by IMDb ID.
    
    This is the preferred method as IMDb ID provides exact identification.
    No ambiguity - the ID uniquely identifies a single movie.
    
    Args:
        imdb_id (str): IMDb ID in format "ttXXXXXXX".
                       Example: "tt0133093" (The Matrix)
    
    Returns:
        Dict: Movie metadata with normalized field names.
              Returns default "NA" values if lookup fails.
              
    Field Mapping (OMDb -> Our Schema):
        Title -> title
        Year -> year
        Genre -> genre
        Director -> director
        Actors -> actors
        Plot -> plot
        Runtime -> runtime
        Language -> language
        Country -> country
        Awards -> awards
        Poster -> poster
        imdbRating -> imdb_rating
        BoxOffice -> box_office
        imdbID -> imdb_id
    
    Error Handling:
        - Missing API key: Returns default response
        - Invalid/empty IMDb ID: Returns default response
        - Network error: Logs error, returns default response
        - OMDb error response: Logs warning, returns default response
    
    Example:
        >>> result = fetch_by_imdb_id("tt0133093")
        >>> print(result["title"])
        'The Matrix'
        >>> print(result["imdb_rating"])
        '8.7'
    """
    default_response = get_default_response()
    
    # Validate API key is configured
    if not OMDB_API_KEY:
        logger.error("OMDB_API_KEY not configured")
        return default_response
    
    # Validate IMDb ID is provided
    if not imdb_id or imdb_id == "NA":
        return default_response
    
    try:
        # Build request parameters
        params = {
            "apikey": OMDB_API_KEY,
            "i": imdb_id,       # 'i' = IMDb ID parameter
            "plot": "short"     # Request short plot (vs "full")
        }
        
        # Make HTTP GET request
        response = requests.get(OMDB_BASE_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for 4xx/5xx
        
        data = response.json()
        
        # Check for OMDb error response
        # OMDb returns {"Response": "False", "Error": "..."} on failure
        if data.get("Response") == "False":
            logger.warning(f"OMDb error for {imdb_id}: {data.get('Error', 'Unknown error')}")
            return default_response
        
        # Parse and normalize the response
        return parse_omdb_response(data)
        
    except requests.RequestException as e:
        # Network errors, timeouts, etc.
        logger.error(f"OMDb request failed for {imdb_id}: {e}")
        return default_response


# =============================================================================
# FETCH BY TITLE (FALLBACK)
# =============================================================================

def fetch_by_title(title: str, year: str = None) -> Dict:
    """
    Fetch movie data by title and optional year.
    
    Fallback method when IMDb ID is not available. Less accurate than
    fetch_by_imdb_id() as title matching can be ambiguous.
    
    Args:
        title (str): Movie title to search for.
                     Example: "The Matrix"
        
        year (str, optional): Release year to refine search.
                              Highly recommended for better accuracy.
                              Example: "1999"
    
    Returns:
        Dict: Movie metadata with normalized field names.
              Returns default "NA" values if lookup fails.
    
    Search Behavior:
        - OMDb tries exact title match first
        - If year is provided, filters results to that year
        - Returns first result if multiple matches
    
    Accuracy Notes:
        - Common titles may return wrong movie (e.g., remakes)
        - Always provide year when available
        - Verify results match expectations
    
    Example:
        >>> result = fetch_by_title("Inception", "2010")
        >>> print(result["director"])
        'Christopher Nolan'
    """
    default_response = get_default_response()
    
    # Validate API key
    if not OMDB_API_KEY:
        logger.error("OMDB_API_KEY not configured")
        return default_response
    
    # Validate title
    if not title or title == "NA":
        return default_response
    
    try:
        # Build request parameters
        params = {
            "apikey": OMDB_API_KEY,
            "t": title,         # 't' = title parameter (exact match)
            "plot": "short"
        }
        
        # Add year if provided (improves accuracy significantly)
        if year and year != "NA":
            params["y"] = year
        
        # Make HTTP GET request
        response = requests.get(OMDB_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for OMDb error response
        if data.get("Response") == "False":
            logger.warning(f"OMDb error for '{title}': {data.get('Error', 'Unknown error')}")
            return default_response
        
        return parse_omdb_response(data)
        
    except requests.RequestException as e:
        logger.error(f"OMDb request failed for '{title}': {e}")
        return default_response


# =============================================================================
# DEFAULT RESPONSE
# =============================================================================

def get_default_response() -> Dict:
    """
    Get default response with all fields set to "NA".
    
    Used as fallback when API requests fail or return no data.
    Ensures all expected fields exist for downstream processing.
    
    Args:
        None
    
    Returns:
        Dict: Complete response structure with "NA" values.
    """
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


# =============================================================================
# RESPONSE PARSING
# =============================================================================

def parse_omdb_response(data: Dict) -> Dict:
    """
    Parse OMDb API response into our normalized schema.
    
    Transforms OMDb's PascalCase/camelCase field names into our
    snake_case schema, and collects additional metadata.
    
    Args:
        data (Dict): Raw response from OMDb API.
                     Example: {"Title": "The Matrix", "Year": "1999", ...}
    
    Returns:
        Dict: Normalized movie data with snake_case keys.
    
    Field Mappings:
        OMDb Field    -> Our Field
        ----------    -> ---------
        Title         -> title
        Year          -> year
        Genre         -> genre
        Director      -> director
        Actors        -> actors
        Plot          -> plot
        Runtime       -> runtime
        Language      -> language
        Country       -> country
        Awards        -> awards
        Poster        -> poster
        imdbRating    -> imdb_rating
        BoxOffice     -> box_office
        imdbID        -> imdb_id
    
    Additional Info:
        Any OMDb fields not explicitly mapped are collected into
        'additional_info' as formatted text lines. This includes:
        - Ratings from different sources (Rotten Tomatoes, Metacritic)
        - DVD release date
        - Production company
        - Website
        - Metascore
    """
    # Keys that we explicitly map to columns (exclude from additional_info)
    captured_keys = {
        "Title", "Year", "Genre", "Director", "Actors", "Plot",
        "Runtime", "Language", "Country", "Awards", "Poster",
        "imdbRating", "BoxOffice", "imdbID", "Response", "Type"
    }

    # Collect unmapped fields as additional info
    additional_info_lines = []
    
    for key, value in data.items():
        if key not in captured_keys:
            # Handle list types (e.g., Ratings array)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # Format: "Source: Value"
                        parts = [f"{k}: {v}" for k, v in item.items()]
                        additional_info_lines.append(" | ".join(parts))
            elif isinstance(value, dict):
                # Skip complex nested dicts for simplicity
                pass
            else:
                # Simple key-value pairs
                additional_info_lines.append(f"**{key}**: {value}")

    # Join additional info lines
    additional_info_str = "\n".join(additional_info_lines)

    # Return normalized response
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
        "additional_info": additional_info_str if additional_info_str else "NA"
    }


# =============================================================================
# UNIFIED FETCH FUNCTION
# =============================================================================

def fetch_movie_data(imdb_id: str = None, title: str = None, year: str = None) -> Dict:
    """
    Fetch movie data using IMDb ID (preferred) or title+year fallback.
    
    Main entry point for OMDb data retrieval. Tries IMDb ID first
    for accuracy, then falls back to title search if needed.
    
    Args:
        imdb_id (str, optional): IMDb ID for exact lookup.
                                 Example: "tt0133093"
        
        title (str, optional): Movie title for search lookup.
                               Used as fallback if imdb_id fails.
                               Example: "The Matrix"
        
        year (str, optional): Release year to refine title search.
                              Only used with title lookup.
                              Example: "1999"
    
    Returns:
        Dict: Movie metadata with all fields populated.
              Uses "NA" for any unavailable data.
    
    Lookup Priority:
        1. Try fetching by IMDb ID (if provided and valid)
        2. If step 1 fails or ID not provided, try title search
        3. If both fail, return default response
    
    Example:
        >>> # With IMDb ID (preferred)
        >>> result = fetch_movie_data(imdb_id="tt0133093")
        
        >>> # Fallback to title
        >>> result = fetch_movie_data(title="Inception", year="2010")
        
        >>> # Both provided - tries ID first
        >>> result = fetch_movie_data(
        ...     imdb_id="tt0133093",
        ...     title="The Matrix",
        ...     year="1999"
        ... )
    """
    # Priority 1: Try IMDb ID lookup (most accurate)
    if imdb_id and imdb_id != "NA":
        result = fetch_by_imdb_id(imdb_id)
        if result.get("title") != "NA":
            logger.info(f"Fetched by IMDb ID: {imdb_id} -> {result.get('title')}")
            return result
    
    # Priority 2: Fall back to title search
    if title and title != "NA":
        result = fetch_by_title(title, year)
        if result.get("title") != "NA":
            logger.info(f"Fetched by title: {title} -> {result.get('title')}")
            return result
    
    # Both methods failed
    logger.warning(f"Could not fetch data for imdb_id={imdb_id}, title={title}")
    return get_default_response()


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Test the OMDb client
    logging.basicConfig(level=logging.INFO)
    
    print("Testing OMDb API Client...")
    print("-" * 50)
    
    # Check for API key
    if not OMDB_API_KEY:
        print("ERROR: OMDB_API_KEY not set in .env file")
        print("Please add your API key to: e:\\0 Movie Project\\.env")
        exit(1)
    
    # Test 1: Fetch by IMDb ID
    print("\n1. Fetching The Matrix by IMDb ID...")
    result = fetch_by_imdb_id("tt0133093")
    print(f"   Title: {result['title']}")
    print(f"   Year: {result['year']}")
    print(f"   IMDb Rating: {result['imdb_rating']}")
    print(f"   Genre: {result['genre']}")
    
    # Test 2: Fetch by title
    print("\n2. Fetching Inception by title...")
    result = fetch_by_title("Inception", "2010")
    print(f"   Title: {result['title']}")
    print(f"   Year: {result['year']}")
    print(f"   IMDb Rating: {result['imdb_rating']}")
    print(f"   Director: {result['director']}")
    
    print("\n" + "-" * 50)
    print("OMDb client test complete!")
