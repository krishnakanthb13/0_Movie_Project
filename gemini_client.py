"""
Movie Library Project - Gemini AI Client Module
================================================

Advanced 2-Step AI pipeline for movie identification using Google Gemini.

This module implements a sophisticated two-step approach to accurately
identify movies from filenames:

Step 1 - Search (Live API + Google Search Grounding):
    Uses Gemini's Live API with native audio output and real-time
    web search to find the exact movie match, including IMDb ID.
    
Step 2 - Format (Gemini Flash):
    Takes the transcript from Step 1 and extracts structured JSON
    data (title, year, IMDb ID) using a text-optimized model.

Why Two Steps?
    - The Live API excels at research but outputs unstructured text
    - Gemini Flash excels at structured extraction but can't search
    - Combining them gives both accuracy and structure

Pipeline Flow:
    filename -> Step 1 (Search) -> transcript -> Step 2 (Format) -> JSON

Output Format:
    {
        "movie_title": "The Matrix",
        "year": "1999",
        "imdb_id": "tt0133093",
        "confidence": "high",
        "reasoning": "Found via IMDB search..."
    }

Usage:
    from gemini_client import identify_movie
    
    result = identify_movie("The.Matrix.1999.mkv", "The Matrix", "1999")
    print(result["imdb_id"])  # tt0133093

Dependencies:
    - google-genai: Official Gemini Python client
    - config.py: GEMINI_API_KEY, AI_MODEL, AI_SEARCH_MODEL, AI_REQUEST_DELAY
"""

import json
import asyncio
import time
import logging
import re
from typing import Dict, Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, AI_REQUEST_DELAY, AI_MODEL, AI_SEARCH_MODEL

# Get logger for this module
logger = logging.getLogger(__name__)


# =============================================================================
# MODEL CONFIGURATION
# =============================================================================
# Model selection for each pipeline step.

# MODEL_SEARCH: Model for Step 1 (Live API + Web Search)
# Must support:
#   - Live API connections
#   - Audio output modality
#   - Google Search tool/grounding
# Current: Gemini 2.5 Flash Native Audio Preview
MODEL_SEARCH = AI_SEARCH_MODEL

# MODEL_FORMATTER: Model for Step 2 (JSON extraction)
# Optimized for:
#   - Fast text processing
#   - Structured output generation
#   - JSON formatting
# Current: Gemini 2.5 Flash
MODEL_FORMATTER = AI_MODEL


# =============================================================================
# CLIENT INITIALIZATION
# =============================================================================
# Singleton pattern for Gemini client to reuse connections.

# Global client instance (initialized lazily)
client = None

# Initialize client if API key is available
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)


def get_client() -> genai.Client:
    """
    Get Gemini client instance (singleton pattern).
    
    Returns an existing client or creates one if needed.
    Raises an error if API key is not configured.
    
    Args:
        None
    
    Returns:
        genai.Client: Configured Gemini client instance.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set in environment.
    
    Note:
        Uses global singleton to avoid repeated client creation.
    """
    global client
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env file")
    
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    
    return client


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================
# Carefully crafted prompts for each pipeline step.

# SEARCH_PROMPT: Prompt for Step 1 (Live API with Search)
# Instructs the model to:
#   1. Use Google Search to find movie details
#   2. Verify the IMDb ID specifically
#   3. Speak results clearly (for transcription)
SEARCH_PROMPT = """
I have a video file: "{file_name}"
Parsed as: {extracted_name} ({extracted_year})

Please use Google Search to find the exact Official IMDB Movie Title, Release Year, and IMDb ID (ttXXXXXXX).
Verify the IMDb ID is correct for this specific movie.
Speak the details clearly so I can write them down.
"""

# FORMAT_PROMPT: Prompt for Step 2 (JSON extraction)
# Instructs the model to:
#   1. Parse unstructured transcript text
#   2. Extract specific fields
#   3. Return strict JSON format
FORMAT_PROMPT = """
You are a data extraction assistant.
Extract the movie details from the following text and return them in strict JSON format.

TEXT:
"{transcript}"

RULES:
1. Extract "movie_title", "year", and "imdb_id" (ttXXXXXXX).
2. If the text indicates it's not a movie or found nothing, set fields to "NA".
3. Return ONLY valid JSON.

JSON FORMAT:
{{
  "movie_title": "Title",
  "year": "YYYY",
  "imdb_id": "ttXXXXXXX",
  "confidence": "high/medium/low",
  "reasoning": "Based on..."
}}
"""

# BULK_PROMPT: Prompt for bulk processing (single API call)
# Processes multiple movies at once for efficiency.
BULK_PROMPT = """
You are a movie metadata expert. I will provide a list of filenames with IDs.
For EACH file, you MUST perform a Google Search to find the correct IMDb ID (ttXXXXXXX).

INPUT LIST:
{file_list}

INSTRUCTIONS:
1. For each movie, searching for "movie name year imdb".
2. EXTRACT the IMDb ID (starts with 'tt') from the search results.
3. Return a JSON ARRAY of objects.
4. Each object must have:
   - "id": (The ID provided in the input)
   - "movie_title": (Official Title)
   - "year": (Release Year)
   - "imdb_id": (The IMDb ID you found, e.g., "tt0133093". Do NOT return "NA" unless absolutely impossible.)
   - "confidence": "high" or "low"
5. STRICT JSON OUTPUT ONLY. Do not use code blocks.
"""


# =============================================================================
# STEP 1: LIVE API SEARCH
# =============================================================================

async def get_search_transcript(file_name: str, extracted_name: str, extracted_year: str) -> str:
    """
    Step 1: Use Live API + Google Search to get movie details.
    
    Connects to Gemini's Live API with audio output and search grounding
    to find movie information. Returns the transcription of the AI's
    spoken response.
    
    Args:
        file_name (str): Original filename with extension.
                         Example: "The.Matrix.1999.1080p.BluRay.mkv"
        
        extracted_name (str): Parser-extracted movie title.
                              Example: "The Matrix"
        
        extracted_year (str): Parser-extracted year or "NA".
                              Example: "1999"
    
    Returns:
        str: Transcription of the AI's response containing movie details.
             Empty string if request fails.
    
    API Configuration:
        - response_modalities: ["AUDIO"] - Required for native audio model
        - output_audio_transcription: {} - Enables text transcription
        - tools: [{"google_search": {}}] - Enables web search grounding
    
    Error Handling:
        - Returns empty string on any exception
        - Logs error details for debugging
    
    Note:
        This is an async function. Use asyncio.run() for sync calls.
    """
    # Early return if no API key
    if not GEMINI_API_KEY:
        return ""

    try:
        # Build the prompt with provided values
        prompt = SEARCH_PROMPT.format(
            file_name=file_name,
            extracted_name=extracted_name,
            extracted_year=extracted_year
        )

        # Live API configuration
        # AUDIO modality is required for native audio models
        # output_audio_transcription gives us text back
        # google_search tool enables real-time web search
        config = {
            "response_modalities": ["AUDIO"],
            "output_audio_transcription": {},
            "tools": [{"google_search": {}}]
        }

        gemini_client = get_client()
        transcription_text = ""

        # Connect to Live API
        # async with handles connection lifecycle
        async with gemini_client.aio.live.connect(model=MODEL_SEARCH, config=config) as session:
            # Send the prompt to the model
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": prompt}]},
                turn_complete=True
            )

            # Receive and accumulate transcription chunks
            async for response in session.receive():
                if response.server_content:
                    # Extract transcription text if available
                    if response.server_content.output_transcription:
                        transcription_text += response.server_content.output_transcription.text or ""
                    
                    # Stop when model indicates turn is complete
                    if response.server_content.turn_complete:
                        break
        
        return transcription_text.strip()

    except Exception as e:
        logger.error(f"Step 1 (Search) failed for {file_name}: {e}")
        return ""


# =============================================================================
# STEP 2: JSON FORMATTING
# =============================================================================

def format_with_gemma(transcript: str) -> Dict:
    """
    Step 2: Format transcript into structured JSON.
    
    Takes the unstructured transcript from Step 1 and extracts
    movie details into a clean JSON structure.
    
    Args:
        transcript (str): Text transcript from the Live API containing
                          movie details in natural language.
    
    Returns:
        Dict: Structured movie data with keys:
            - movie_title (str): Official movie title or "NA"
            - year (str): Release year or "NA"
            - imdb_id (str): IMDb ID (ttXXXXXXX) or "NA"
            - confidence (str): "high", "medium", or "low"
            - reasoning (str): Explanation of the identification
    
    Processing Steps:
        1. Build prompt with transcript
        2. Call Gemini Flash model
        3. Parse JSON from response (handles markdown code blocks)
        4. Validate required keys exist
        5. Fall back to regex extraction on parse failure
    
    Error Handling:
        - JSON parse errors: Falls back to extract_fallback()
        - API errors: Returns default_result_na()
    """
    # Default response for failures
    default_response = {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": "NA",
        "confidence": "low",
        "reasoning": "Formatting failed"
    }

    # Early return if no transcript or API key
    if not transcript or not GEMINI_API_KEY:
        return default_result_na("No transcript generated")

    try:
        # Build the formatting prompt
        prompt = FORMAT_PROMPT.format(transcript=transcript)
        
        gemini_client = get_client()
        
        # Call the formatter model
        response = gemini_client.models.generate_content(
            model=MODEL_FORMATTER,
            contents=prompt
        )
        
        # Extract and clean the response text
        text = response.text.strip()
        
        # Handle markdown code blocks (models sometimes wrap JSON in ```)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        # Parse JSON
        result = json.loads(text)
        
        # Ensure required keys exist
        for k in ["movie_title", "year", "imdb_id"]:
            if k not in result:
                result[k] = "NA"
                
        return result

    except Exception as e:
        logger.error(f"Step 2 (Formatting) failed: {e}")
        # Try regex fallback for IMDb ID extraction
        return extract_fallback(transcript)


# =============================================================================
# FALLBACK EXTRACTION
# =============================================================================

def extract_fallback(text: str) -> Dict:
    """
    Fallback extraction using regex if Gemma formatting fails.
    
    Attempts to extract an IMDb ID from raw text using pattern matching.
    Used when Step 2 JSON parsing fails.
    
    Args:
        text (str): Raw text to search for IMDb ID.
    
    Returns:
        Dict: Minimal result with imdb_id if found, "NA" otherwise.
    """
    # IMDb ID pattern: tt followed by 7+ digits
    imdb_match = re.search(r"(tt\d{7,})", text)
    
    return {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": imdb_match.group(1) if imdb_match else "NA",
        "confidence": "low",
        "reasoning": "Fallback regex extraction"
    }


def default_result_na(reason: str) -> Dict:
    """
    Create a default "NA" result with a specific reason.
    
    Args:
        reason (str): Explanation for why identification failed.
    
    Returns:
        Dict: Result with all fields set to "NA" and provided reason.
    """
    return {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": "NA",
        "confidence": "NA",
        "reasoning": reason
    }


# =============================================================================
# PIPELINE ORCHESTRATION
# =============================================================================

async def identify_movie_async(file_name: str, extracted_name: str, extracted_year: str) -> Dict:
    """
    Orchestrate the complete 2-step identification pipeline (async).
    
    Runs both pipeline steps in sequence:
    1. Search via Live API
    2. Format via Gemini Flash
    
    Args:
        file_name (str): Original filename with extension.
        extracted_name (str): Parser-extracted movie title.
        extracted_year (str): Parser-extracted year or "NA".
    
    Returns:
        Dict: Final structured result from the pipeline.
    
    Logs:
        - Step 1 start and transcript preview
        - Step 2 start
        - Final identification result
    """
    # Step 1: Search using Live API
    logger.info(f"Step 1: Searching for {file_name}...")
    transcript = await get_search_transcript(file_name, extracted_name, extracted_year)
    logger.info(f"Step 1 Transcript: {transcript[:100]}...")

    # Handle failed search
    if not transcript:
        return default_result_na("Search step failed to produce transcript")

    # Step 2: Format using Gemini Flash
    logger.info("Step 2: Formatting with Gemma...")
    result = format_with_gemma(transcript)
    
    logger.info(f"Identified: {result.get('movie_title')} ({result.get('year')}) [{result.get('imdb_id')}]")
    return result


def identify_movie(file_name: str, extracted_name: str, extracted_year: str) -> Dict:
    """
    Synchronous wrapper for the identification pipeline.
    
    Convenience function that runs the async pipeline using asyncio.run().
    Use this for simple, synchronous code paths.
    
    Args:
        file_name (str): Original filename with extension.
        extracted_name (str): Parser-extracted movie title.
        extracted_year (str): Parser-extracted year or "NA".
    
    Returns:
        Dict: Final identification result.
    
    Example:
        >>> result = identify_movie("The.Matrix.1999.mkv", "The Matrix", "1999")
        >>> print(result["imdb_id"])
        'tt0133093'
    """
    return asyncio.run(identify_movie_async(file_name, extracted_name, extracted_year))


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def batch_identify_movies(movies: list, delay: float = AI_REQUEST_DELAY) -> list:
    """
    Process multiple movies sequentially with rate limiting.
    
    Identifies each movie one at a time with a delay between requests
    to avoid rate limiting.
    
    Args:
        movies (list): List of movie dictionaries, each containing:
                       - file_name (str): Filename
                       - extracted_name (str): Parsed title
                       - extracted_year (str): Parsed year
                       - uuid (str): Unique identifier
        
        delay (float): Seconds to wait between requests.
                       Defaults to AI_REQUEST_DELAY from config.
    
    Returns:
        list: List of result dictionaries, each containing:
              - uuid (str): Original movie's UUID
              - movie_title (str): Identified title
              - year (str): Identified year
              - imdb_id (str): Found IMDb ID
    """
    results = []
    total = len(movies)
    
    logger.info(f"Starting 2-Step Enrichment (Search: {MODEL_SEARCH} -> Format: {MODEL_FORMATTER})")
    
    for i, movie in enumerate(movies):
        logger.info(f"Processing {i+1}/{total}: {movie.get('file_name', 'Unknown')}")
        
        # Run identification pipeline
        result = identify_movie(
            file_name=movie.get("file_name", ""),
            extracted_name=movie.get("extracted_name", "NA"),
            extracted_year=movie.get("extracted_year", "NA")
        )
        
        # Include UUID for mapping back to database
        results.append({
            "uuid": movie.get("uuid"),
            **result
        })
        
        # Rate limiting between requests
        if i < total - 1:
            time.sleep(delay)
    
    return results


def identify_movies_bulk(movies: list) -> list:
    """
    Batch identify movies using a single API call.
    
    More efficient than sequential processing for large batches.
    Uses the formatter model with search grounding.
    
    Args:
        movies (list): List of movie dictionaries (max 50-100 recommended).
                       Each dict should have: uuid, file_name, extracted_name, extracted_year
    
    Returns:
        list: List of result dictionaries with id (uuid), movie_title, year, imdb_id.
              Empty list on failure.
    
    Processing:
        1. Build formatted input list string
        2. Single API call with BULK_PROMPT
        3. Parse JSON array response
        4. Return mapped results
    
    Note:
        Uses search grounding but may be less accurate than 2-step pipeline
        for difficult titles. Recommended for initial passes.
    """
    if not movies:
        return []
        
    client = get_client()
    
    # Build input list text (one line per movie)
    input_lines = []
    for m in movies:
        line = f"ID: {m['uuid']} | File: {m['file_name']} | Parsed: {m.get('extracted_name', '')} ({m.get('extracted_year', '')})"
        input_lines.append(line)
        
    file_list_text = "\n".join(input_lines)
    prompt = BULK_PROMPT.format(file_list=file_list_text)
    
    try:
        # Configure with search grounding
        config = {
            "tools": [{"google_search": {}}],
        }
        
        # Single API call for all movies
        response = client.models.generate_content(
            model=MODEL_FORMATTER,
            contents=prompt,
            config=config
        )
        
        # Parse output
        text = response.text.strip()
        
        # Clean markdown wrapping if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        results = json.loads(text)
        
        # Handle dict response (some models wrap in {"movies": [...]})
        if isinstance(results, dict):
            if "movies" in results:
                results = results["movies"]
            else:
                results = [results]
                
        return results

    except Exception as e:
        logger.error(f"Bulk identification failed: {e}")
        return []


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing 2-Step Pipeline")
    print("-" * 50)
    
    if not GEMINI_API_KEY:
        print("ERROR: API Key missing")
        exit(1)
        
    # Test with a well-known movie
    test_file = "The.Matrix.1999.1080p.BluRay.x264.mkv"
    print(f"\nTesting: {test_file}")
    
    start = time.time()
    result = identify_movie(test_file, "The Matrix", "1999")
    print(f"Time: {time.time() - start:.2f}s")
    print(f"Result: {json.dumps(result, indent=2)}")
