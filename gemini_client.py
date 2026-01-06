"""
Movie Library Project - Gemini AI Client
Advanced 2-Step Pipeline:
1. Live API (Native Audio + Search): Finds movie details & IMDb ID.
2. Gemma (Formatter): Extracts structured JSON from the Live API transcript.
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

logger = logging.getLogger(__name__)

# Models
MODEL_SEARCH = AI_SEARCH_MODEL  # Live API + Search
MODEL_FORMATTER = AI_MODEL      # Structuring

# Configure Gemini client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)


# Prompt for Step 1 (Searcher)
SEARCH_PROMPT = """
I have a video file: "{file_name}"
Parsed as: {extracted_name} ({extracted_year})

Please use Google Search to find the exact official Movie Title, Release Year, and IMDb ID (ttXXXXXXX).
Verify the IMDb ID is correct for this specific movie.
Speak the details clearly so I can write them down.
"""

# Prompt for Step 2 (Formatter)
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


def get_client():
    """Get Gemini client instance."""
    global client
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env file")
    
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    
    return client


async def get_search_transcript(file_name: str, extracted_name: str, extracted_year: str) -> str:
    """Step 1: Use Live API + Search to get a transcript with details."""
    if not GEMINI_API_KEY:
        return ""

    try:
        prompt = SEARCH_PROMPT.format(
            file_name=file_name,
            extracted_name=extracted_name,
            extracted_year=extracted_year
        )

        config = {
            "response_modalities": ["AUDIO"],  # Native model requirement
            "output_audio_transcription": {},  # Get text back
            "tools": [{"google_search": {}}]   # Enable Grounding
        }

        gemini_client = get_client()
        transcription_text = ""

        # Connect to Live API
        async with gemini_client.aio.live.connect(model=MODEL_SEARCH, config=config) as session:
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": prompt}]},
                turn_complete=True
            )

            async for response in session.receive():
                if response.server_content:
                    if response.server_content.output_transcription:
                        transcription_text += response.server_content.output_transcription.text or ""
                    
                    if response.server_content.turn_complete:
                        break
        
        return transcription_text.strip()

    except Exception as e:
        logger.error(f"Step 1 (Search) failed for {file_name}: {e}")
        return ""


def format_with_gemma(transcript: str) -> Dict:
    """Step 2: Use Gemma to format the transcript into JSON."""
    default_response = {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": "NA",
        "confidence": "low",
        "reasoning": "Formatting failed"
    }

    if not transcript or not GEMINI_API_KEY:
        return default_result_na("No transcript generated")

    try:
        prompt = FORMAT_PROMPT.format(transcript=transcript)
        
        gemini_client = get_client()
        response = gemini_client.models.generate_content(
            model=MODEL_FORMATTER,
            contents=prompt
        )
        
        # Parse JSON
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        result = json.loads(text)
        
        # Ensure keys exist
        for k in ["movie_title", "year", "imdb_id"]:
            if k not in result:
                result[k] = "NA"
                
        return result

    except Exception as e:
        logger.error(f"Step 2 (Formatting) failed: {e}")
        # Fallback: simple regex if Gemma fails
        return extract_fallback(transcript)


def extract_fallback(text: str) -> Dict:
    """Fallback extraction if Gemma fails."""
    imdb_match = re.search(r"(tt\d{7,})", text)
    return {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": imdb_match.group(1) if imdb_match else "NA",
        "confidence": "low",
        "reasoning": "Fallback regex extraction"
    }


def default_result_na(reason: str) -> Dict:
    return {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": "NA",
        "confidence": "NA",
        "reasoning": reason
    }


async def identify_movie_async(file_name: str, extracted_name: str, extracted_year: str) -> Dict:
    """Orchestrates the 2-step pipeline."""
    
    # Step 1: Search (Live API)
    logger.info(f"Step 1: Searching for {file_name}...")
    transcript = await get_search_transcript(file_name, extracted_name, extracted_year)
    logger.info(f"Step 1 Transcript: {transcript[:100]}...")

    if not transcript:
        return default_result_na("Search step failed to produce transcript")

    # Step 2: Format (Gemma)
    logger.info("Step 2: Formatting with Gemma...")
    result = format_with_gemma(transcript)
    
    logger.info(f"Identified: {result.get('movie_title')} ({result.get('year')}) [{result.get('imdb_id')}]")
    return result


def identify_movie(file_name: str, extracted_name: str, extracted_year: str) -> Dict:
    """Synchronous wrapper."""
    return asyncio.run(identify_movie_async(file_name, extracted_name, extracted_year))


def batch_identify_movies(movies: list, delay: float = AI_REQUEST_DELAY) -> list:
    """Batch process."""
    results = []
    total = len(movies)
    
    logger.info(f"Starting 2-Step Enrichment (Search: {MODEL_SEARCH} -> Format: {MODEL_FORMATTER})")
    
    for i, movie in enumerate(movies):
        logger.info(f"Processing {i+1}/{total}: {movie.get('file_name', 'Unknown')}")
        
        result = identify_movie(
            file_name=movie.get("file_name", ""),
            extracted_name=movie.get("extracted_name", "NA"),
            extracted_year=movie.get("extracted_year", "NA")
        )
        
        results.append({
            "uuid": movie.get("uuid"),
            **result
        })
        
        if i < total - 1:
            time.sleep(delay)
    
    return results


# Prompt for Bulk Mode
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

def identify_movies_bulk(movies: list) -> list:
    """
    Batch identify movies using a single API call.
    Uses the Formatter model (gemini-2.5-flash) which is fast and text-optimized.
    """
    if not movies:
        return []
        
    client = get_client()
    
    # Prepare input list text
    input_lines = []
    for m in movies:
        # Use UUID as ID to map back
        line = f"ID: {m['uuid']} | File: {m['file_name']} | Parsed: {m.get('extracted_name', '')} ({m.get('extracted_year', '')})"
        input_lines.append(line)
        
    file_list_text = "\n".join(input_lines)
    prompt = BULK_PROMPT.format(file_list=file_list_text)
    
    try:
        # The 2.5 Flash model supports tools but combining JSON mode and Tools is tricky.
        # Let's rely on the prompt for JSON structure and keep tools for accuracy.
        config = {
            "tools": [{"google_search": {}}],
            # "response_mime_type": "application/json"  <-- Causing conflict
        }
        
        response = client.models.generate_content(
            model=MODEL_FORMATTER, # Using the flash model (gemini-2.5-flash)
            contents=prompt,
            config=config
        )
        
        # Parse output
        text = response.text.strip()
        # Clean up if wrapped in markdown
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        results = json.loads(text)
        
        # Ensure it's a list
        if isinstance(results, dict):
            # Sometimes models return {"movies": [...]}
            if "movies" in results:
                results = results["movies"]
            else:
                results = [results]
                
        return results

    except Exception as e:
        logger.error(f"Bulk identification failed: {e}")
        return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing 2-Step Pipeline")
    print("-" * 50)
    
    if not GEMINI_API_KEY:
        print("ERROR: API Key missing")
        exit(1)
        
    test_file = "The.Matrix.1999.1080p.BluRay.x264.mkv"
    print(f"\nTesting: {test_file}")
    
    start = time.time()
    result = identify_movie(test_file, "The Matrix", "1999")
    print(f"Time: {time.time() - start:.2f}s")
    print(f"Result: {json.dumps(result, indent=2)}")
