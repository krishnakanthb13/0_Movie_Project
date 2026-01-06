"""
Movie Library Project - Configuration
Central configuration for paths, extensions, and API keys.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# DIRECTORY SETTINGS
# =============================================================================

# Root directory to scan for movies
MOVIE_DIRECTORY = Path("E:/")

# Project directories
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
WEB_DIR = PROJECT_ROOT / "web"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# FILE PATHS
# =============================================================================

CSV_FILE = DATA_DIR / "movies.csv"
SQLITE_FILE = DATA_DIR / "movies.db"
LOG_FILE = DATA_DIR / "enrichment.log"

# =============================================================================
# VIDEO SETTINGS
# =============================================================================

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpeg", ".mpg", ".3gp", ".ts"
}

# =============================================================================
# VLC SETTINGS
# =============================================================================

VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

# =============================================================================
# API KEYS (from .env)
# =============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")

# =============================================================================
# ENRICHMENT SETTINGS
# =============================================================================

# Delay between AI requests (seconds) - increase if hitting rate limits
AI_REQUEST_DELAY = 3.0

# Batch size for processing
# Batch size for processing
BATCH_SIZE = 50

# AI Models
# Options: "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview"
AI_MODEL = "gemini-2.5-flash"
AI_SEARCH_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# =============================================================================
# SERVER SETTINGS
# =============================================================================

SERVER_HOST = "localhost"
SERVER_PORT = 8010

# =============================================================================
# PARSER SETTINGS
# =============================================================================

# Noise patterns to strip from filenames
NOISE_PATTERNS = [
    r"1080p", r"720p", r"480p", r"2160p", r"4K",
    r"BluRay", r"Blu-Ray", r"BRRip", r"BDRip",
    r"WEBRip", r"WEB-DL", r"WEBDL", r"HDRip", r"DVDRip",
    r"x264", r"x265", r"HEVC", r"H\.264", r"H\.265",
    r"AAC", r"AC3", r"DTS", r"5\.1", r"7\.1",
    r"YIFY", r"RARBG", r"YTS", r"ETRG", r"EVO",
    r"HDR", r"SDR", r"10bit", r"8bit",
    r"EXTENDED", r"UNRATED", r"REMASTERED", r"PROPER",
    r"\[.*?\]", r"\(.*?\)",  # Bracketed content
]

# Year extraction pattern
YEAR_PATTERN = r"(19\d{2}|20\d{2})"
