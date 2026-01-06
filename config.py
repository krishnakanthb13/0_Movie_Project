"""
Movie Library Project - Configuration Module
=============================================

Central configuration hub for the entire Movie Library system.
This module contains all configurable settings including:
- Directory paths for scanning and data storage
- Supported video file extensions
- External application paths (VLC)
- API keys loaded from environment variables
- AI model configurations and rate limiting
- Server settings for the web interface
- Regex patterns for filename parsing

All other modules import their configuration from here, ensuring
a single source of truth for settings across the application.

Usage:
    from config import MOVIE_DIRECTORY, VIDEO_EXTENSIONS, GEMINI_API_KEY
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================
# Load environment variables from .env file in the project root.
# This allows sensitive data like API keys to be stored outside the codebase.
# The .env file should contain:
#   GEMINI_API_KEY=your_key_here
#   OMDB_API_KEY=your_key_here

load_dotenv()

# =============================================================================
# DIRECTORY SETTINGS
# =============================================================================
# These paths define where the application looks for movies and stores its data.

# MOVIE_DIRECTORY: Root directory to scan for video files.
# The scanner will recursively search all subdirectories within this path.
# Change this to point to your movie collection (e.g., external drive, NAS).
# Type: Path
# Default: E:/ (common external drive letter on Windows)
MOVIE_DIRECTORY = Path("E:/")

# PROJECT_ROOT: Absolute path to the project directory.
# Automatically detected based on the location of this config file.
# Used as base path for relative directory calculations.
# Type: Path
PROJECT_ROOT = Path(__file__).parent

# DATA_DIR: Directory where CSV and SQLite database files are stored.
# Created automatically if it doesn't exist.
# Contains: movies.csv, movies.db, enrichment.log
# Type: Path
DATA_DIR = PROJECT_ROOT / "data"

# WEB_DIR: Directory containing frontend files (HTML, CSS, JS).
# The web server serves static files from this location.
# Contains: index.html, enrichment.html, favicon.png
# Type: Path
WEB_DIR = PROJECT_ROOT / "web"

# Ensure data directory exists on import
# This creates the 'data' folder if it's missing, preventing FileNotFoundError
DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# FILE PATHS
# =============================================================================
# Specific file locations for data storage and logging.

# CSV_FILE: Path to the CSV file storing all movie records.
# This file serves as the "source of truth" for the database.
# Human-readable and can be edited manually if needed.
# Type: Path
CSV_FILE = DATA_DIR / "movies.csv"

# SQLITE_FILE: Path to the SQLite database file.
# Used for fast queries and filtering in the web interface.
# Synchronized with CSV after enrichment operations.
# Type: Path
SQLITE_FILE = DATA_DIR / "movies.db"

# LOG_FILE: Path to the enrichment log file.
# Records detailed logs of AI and OMDb enrichment operations.
# Useful for debugging failed enrichments.
# Type: Path
LOG_FILE = DATA_DIR / "enrichment.log"

# =============================================================================
# VIDEO SETTINGS
# =============================================================================
# Configuration for video file detection during scanning.

# VIDEO_EXTENSIONS: Set of file extensions recognized as video files.
# Only files with these extensions will be indexed during scanning.
# Extensions are lowercase and include the leading dot.
# Add or remove extensions based on your collection's formats.
# Type: Set[str]
VIDEO_EXTENSIONS = {
    ".mp4",   # MPEG-4 Part 14 - Most common format
    ".mkv",   # Matroska Video - Popular for high-quality rips
    ".avi",   # Audio Video Interleave - Legacy format
    ".mov",   # QuickTime Movie - Apple format
    ".wmv",   # Windows Media Video
    ".flv",   # Flash Video - Legacy web format
    ".webm",  # WebM - Open web format
    ".m4v",   # MPEG-4 Video - iTunes format
    ".mpeg",  # MPEG Video
    ".mpg",   # MPEG Video (alternate extension)
    ".3gp",   # 3GPP Multimedia - Mobile format
    ".ts"     # MPEG Transport Stream
}

# =============================================================================
# VLC SETTINGS
# =============================================================================
# Configuration for VLC media player integration.

# VLC_PATH: Full path to the VLC executable.
# Used by the web server to launch movies for playback.
# Update this path if VLC is installed in a different location.
# On macOS: "/Applications/VLC.app/Contents/MacOS/VLC"
# On Linux: "/usr/bin/vlc"
# Type: str
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

# =============================================================================
# API KEYS (from .env)
# =============================================================================
# External service API keys loaded from environment variables.
# These should NEVER be hardcoded in this file for security reasons.

# GEMINI_API_KEY: Google Gemini API key for AI-powered movie identification.
# Obtain from: https://aistudio.google.com/app/apikey
# Required for: AI enrichment (--enrich command)
# Type: str (empty string if not set)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# OMDB_API_KEY: Open Movie Database API key for fetching movie metadata.
# Obtain from: https://www.omdbapi.com/apikey.aspx (free tier available)
# Required for: OMDb enrichment (--fetch-omdb command)
# Type: str (empty string if not set)
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")

# =============================================================================
# ENRICHMENT SETTINGS
# =============================================================================
# Configuration for the AI and OMDb enrichment pipeline.

# AI_REQUEST_DELAY: Seconds to wait between AI API requests.
# Prevents rate limiting errors from the Gemini API.
# Increase this value if you encounter "quota exceeded" errors.
# Type: float
# Range: 1.0 - 10.0 recommended
AI_REQUEST_DELAY = 3.0

# BATCH_SIZE: Number of movies to process in a single batch operation.
# Used by bulk enrichment mode (--enrich --bulk).
# Higher values = faster processing but more memory usage.
# Type: int
# Range: 10 - 100 recommended
BATCH_SIZE = 50

# AI_MODEL: Gemini model used for JSON formatting (Step 2 of pipeline).
# This model receives the search transcript and outputs structured JSON.
# Options: "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview"
# Type: str
AI_MODEL = "gemini-2.5-flash"

# AI_SEARCH_MODEL: Gemini model used for web search (Step 1 of pipeline).
# This model uses Google Search grounding to find movie details.
# Must be a model that supports the Live API with audio output.
# Type: str
AI_SEARCH_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# =============================================================================
# SERVER SETTINGS
# =============================================================================
# Configuration for the built-in HTTP web server.

# SERVER_HOST: Hostname/IP address for the web server to bind to.
# "localhost" = only accessible from this machine
# "0.0.0.0" = accessible from any device on the network
# Type: str
SERVER_HOST = "localhost"

# SERVER_PORT: TCP port number for the web server.
# Access the viewer at http://localhost:{SERVER_PORT}
# Change if port 8010 is already in use on your system.
# Type: int
# Range: 1024 - 65535 (avoid ports below 1024)
SERVER_PORT = 8010

# =============================================================================
# PARSER SETTINGS
# =============================================================================
# Configuration for extracting movie names from filenames.

# NOISE_PATTERNS: Regex patterns to strip from filenames during parsing.
# These patterns match common video quality indicators, release groups,
# encoding formats, and other non-title content in movie filenames.
# Order doesn't matter - all patterns are applied.
# Type: List[str] (regex patterns)
NOISE_PATTERNS = [
    # Video quality indicators
    r"1080p", r"720p", r"480p", r"2160p", r"4K",
    
    # Source types
    r"BluRay", r"Blu-Ray", r"BRRip", r"BDRip",
    r"WEBRip", r"WEB-DL", r"WEBDL", r"HDRip", r"DVDRip",
    
    # Video codecs
    r"x264", r"x265", r"HEVC", r"H\.264", r"H\.265",
    
    # Audio codecs and channels
    r"AAC", r"AC3", r"DTS", r"5\.1", r"7\.1",
    
    # Release groups (common ones)
    r"YIFY", r"RARBG", r"YTS", r"ETRG", r"EVO",
    
    # Video features
    r"HDR", r"SDR", r"10bit", r"8bit",
    
    # Edition markers
    r"EXTENDED", r"UNRATED", r"REMASTERED", r"PROPER",
    
    # Bracketed content (often contains additional info)
    r"\[.*?\]",  # Square brackets and contents
    r"\(.*?\)",  # Parentheses and contents (careful - may contain year)
]

# YEAR_PATTERN: Regex pattern to extract 4-digit years from filenames.
# Matches years in the range 1900-2099.
# The parser uses the LAST match to avoid false positives (e.g., "2001" in title).
# Type: str (regex pattern)
YEAR_PATTERN = r"(19\d{2}|20\d{2})"
