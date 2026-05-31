"""
Movie Library Project - AI Provider Dispatcher
==============================================

Thin indirection layer that routes movie-identification calls to the active
AI provider (Gemini or Groq). The enrichment pipeline imports the identify_*
functions from here instead of a specific client, so the provider can be
chosen via config (AI_PROVIDER) or overridden at runtime (e.g. the CLI
--provider / --model flags) without touching the pipeline.

Both providers expose the same interface:
    identify_movie(file_name, extracted_name, extracted_year) -> dict
    identify_movies_bulk(movies) -> list
    set_model(model_name) -> None

Usage:
    from ai_provider import identify_movie, identify_movies_bulk
    set_provider("groq"); set_model("llama-3.3-70b-versatile")
"""

import logging

import config
import gemini_client
import groq_client

logger = logging.getLogger(__name__)

# Map provider name -> client module (each implements the shared interface).
_PROVIDERS = {
    "gemini": gemini_client,
    "groq": groq_client,
}

# Active provider, seeded from config (overridable via set_provider()).
_active = config.AI_PROVIDER if config.AI_PROVIDER in _PROVIDERS else "gemini"


def set_provider(name: str) -> None:
    """Select the active AI provider ("gemini" or "groq") for this process."""
    global _active
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown AI provider: {name!r} (choose from {list(_PROVIDERS)})")
    _active = name
    logger.info(f"AI provider set to: {name}")


def current_provider() -> str:
    """Return the name of the active provider."""
    return _active


def _client():
    return _PROVIDERS[_active]


def set_model(model_name: str) -> None:
    """Override the model used by the active provider."""
    _client().set_model(model_name)


def identify_movie(file_name, extracted_name, extracted_year):
    """Identify a single movie via the active provider."""
    return _client().identify_movie(file_name, extracted_name, extracted_year)


def identify_movies_bulk(movies):
    """Identify multiple movies via the active provider."""
    return _client().identify_movies_bulk(movies)
