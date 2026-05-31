"""
Movie Library Project - Groq AI Client Module
==============================================

Alternative AI provider for movie identification, using Groq's fast
OpenAI-compatible chat completions API (Llama and other open models).

Unlike the Gemini client, Groq has no web-search grounding, so it identifies
movies from the model's own knowledge. That is fine for this pipeline: the
goal of the AI step is a clean official title + year, and OMDb is the
authoritative source that verifies/fetches the real metadata (by IMDb ID when
confident, otherwise by title + year). The model is therefore told to only
return an IMDb ID when it is sure, and "NA" otherwise (no guessing).

Public interface (mirrors gemini_client so the two are interchangeable):
    identify_movie(file_name, extracted_name, extracted_year) -> dict
    identify_movies_bulk(movies) -> list
    set_model(model_name) -> None

Dependencies:
    - requests: HTTP client (already a project dependency)
    - config.py: GROQ_API_KEY, GROQ_MODEL, AI_TIMEOUT_SECONDS
"""

import json
import time
import logging
import re
from typing import Dict, List, Optional

import requests

from config import GROQ_API_KEY, GROQ_MODEL, AI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Active model (overridable at runtime via set_model()).
MODEL = GROQ_MODEL


def set_model(model_name: str) -> None:
    """Override the Groq model used for identification, for this process."""
    global MODEL
    MODEL = model_name
    logger.info(f"Groq model set to: {model_name}")


# =============================================================================
# PROMPTS
# =============================================================================

SINGLE_PROMPT = """You are a movie identification expert. Identify the movie from this video filename using your knowledge.

Filename: "{file_name}"
Parsed guess: {extracted_name} ({extracted_year})

Return STRICT JSON only, with exactly these keys:
{{"movie_title": "Official Title", "year": "YYYY", "imdb_id": "ttXXXXXXX or NA", "confidence": "high|medium|low", "reasoning": "short note"}}

Rules:
- movie_title: the official movie title.
- year: 4-digit release year, or "NA".
- imdb_id: only if you are certain of the exact IMDb ID (format ttXXXXXXX); otherwise "NA". Do NOT guess an IMDb ID.
- If this is not a movie, set movie_title/year/imdb_id to "NA"."""

BULK_PROMPT = """You are a movie identification expert. Identify each movie from its filename using your knowledge.

INPUT (one per line, "ID | filename | parsed guess"):
{file_list}

Return STRICT JSON only: an object with a "movies" array containing one entry per input ID:
{{"movies": [{{"id": "<the exact input ID>", "movie_title": "Official Title", "year": "YYYY", "imdb_id": "ttXXXXXXX or NA", "confidence": "high|low"}}]}}

Rules:
- Include EVERY input ID exactly once, using the ID string provided.
- imdb_id: only if certain (format ttXXXXXXX); otherwise "NA". Do NOT guess.
- If an entry is not a movie, set its title/year/imdb_id to "NA"."""


# =============================================================================
# HTTP CALL WITH RETRY/TIMEOUT
# =============================================================================

def _retry_after_seconds(resp, err_text: str) -> Optional[float]:
    """Extract a retry delay from a 429 response (Retry-After header or body)."""
    ra = resp.headers.get("retry-after")
    if ra:
        try:
            return float(ra)
        except ValueError:
            pass
    m = re.search(r"try again in ([\d.]+)s", err_text)
    return float(m.group(1)) if m else None


def _chat(messages: List[Dict], json_mode: bool = True, max_retries: int = 4) -> str:
    """
    Call Groq chat completions and return the assistant message content.

    Retries on HTTP 429 with backoff (honoring Retry-After when present), and
    uses AI_TIMEOUT_SECONDS so a stalled request can't hang forever. Non-429
    errors are raised to the caller.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env file")

    payload = {"model": MODEL, "messages": messages, "temperature": 0}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    delay = 8.0
    for attempt in range(max_retries + 1):
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=AI_TIMEOUT_SECONDS)

        if resp.status_code == 429 and attempt < max_retries:
            wait = _retry_after_seconds(resp, resp.text) or delay
            logger.warning(
                f"Groq rate limited (429). Backing off {wait:.0f}s "
                f"(attempt {attempt + 1}/{max_retries})..."
            )
            time.sleep(wait)
            delay = min(delay * 2, 60.0)
            continue

        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _supports_json_mode() -> bool:
    """
    Whether the active model supports response_format=json_object.

    Groq's "compound" agentic systems (which add built-in web search/code
    execution - the closest thing to Gemini's search grounding) do not support
    JSON mode, so we skip it for them and parse JSON defensively from the text.
    """
    return "compound" not in MODEL.lower()


def _extract_json(text: str):
    """
    Parse JSON from a model response, tolerating markdown fences or surrounding
    prose (needed when JSON mode is off, e.g. for compound/grounded models).
    """
    text = text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the first {...} or [...] block in the text.
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(1))


def _na_result(reason: str) -> Dict:
    return {
        "movie_title": "NA",
        "year": "NA",
        "imdb_id": "NA",
        "confidence": "NA",
        "reasoning": reason,
    }


# =============================================================================
# PUBLIC: SINGLE IDENTIFICATION
# =============================================================================

def identify_movie(file_name: str, extracted_name: str, extracted_year: str) -> Dict:
    """
    Identify a single movie from its filename using Groq.

    Returns a dict with keys: movie_title, year, imdb_id, confidence, reasoning
    (matching gemini_client.identify_movie's shape). Returns "NA" values on
    failure.
    """
    if not GROQ_API_KEY:
        return _na_result("GROQ_API_KEY not set")

    prompt = SINGLE_PROMPT.format(
        file_name=file_name,
        extracted_name=extracted_name,
        extracted_year=extracted_year,
    )
    try:
        content = _chat([{"role": "user", "content": prompt}], json_mode=_supports_json_mode())
        result = _extract_json(content)
        for k in ("movie_title", "year", "imdb_id"):
            if k not in result:
                result[k] = "NA"
        result.setdefault("confidence", "low")
        result.setdefault("reasoning", "Groq identification")
        logger.info(
            f"Identified (Groq): {result.get('movie_title')} "
            f"({result.get('year')}) [{result.get('imdb_id')}]"
        )
        return result
    except Exception as e:
        logger.error(f"Groq identification failed for {file_name}: {e}")
        return _na_result(f"Groq error: {e}")


# =============================================================================
# PUBLIC: BULK IDENTIFICATION
# =============================================================================

def identify_movies_bulk(movies: list) -> list:
    """
    Identify multiple movies in a single Groq call.

    Returns a list of dicts with keys: id (uuid), movie_title, year, imdb_id,
    confidence (matching gemini_client.identify_movies_bulk's shape). Returns
    an empty list on failure.
    """
    if not movies:
        return []
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set; cannot run bulk identification")
        return []

    input_lines = [
        f"{m['uuid']} | {m['file_name']} | {m.get('extracted_name', '')} ({m.get('extracted_year', '')})"
        for m in movies
    ]
    prompt = BULK_PROMPT.format(file_list="\n".join(input_lines))

    try:
        content = _chat([{"role": "user", "content": prompt}], json_mode=_supports_json_mode())
        data = _extract_json(content)
        # JSON mode returns an object; expect {"movies": [...]}, but tolerate
        # a bare list or a single object.
        if isinstance(data, dict):
            results = data.get("movies", data if "id" in data else [])
            if isinstance(results, dict):
                results = [results]
        elif isinstance(data, list):
            results = data
        else:
            results = []
        return results
    except Exception as e:
        logger.error(f"Groq bulk identification failed: {e}")
        return []


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not set in .env")
        raise SystemExit(1)
    print(f"Testing Groq ({MODEL})...")
    r = identify_movie("The.Matrix.1999.1080p.BluRay.x264.mkv", "The Matrix", "1999")
    print(json.dumps(r, indent=2))
