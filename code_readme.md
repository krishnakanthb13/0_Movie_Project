# 💻 Code Functionality

This document provides technical details about each module, their dependencies, parameters, and how they interconnect.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           main.py                                    │
│                    (CLI Entry Point & Orchestrator)                  │
└─────────────┬───────────────┬───────────────┬───────────────────────┘
              │               │               │
              v               v               v
┌─────────────┴───┐   ┌───────┴─────┐   ┌─────┴───────────┐
│   scanner.py    │   │  parser.py  │   │   enricher.py   │
│  (File System)  │   │  (Regex)    │   │  (Orchestrator) │
└────────┬────────┘   └──────┬──────┘   └────┬────────────┘
         │                   │               │
         └─────────┬─────────┘               │
                   │                         │
                   v               ┌─────────┴──────┬──────────┐
          ┌────────┴────────┐      │                │          │
          │   storage.py    │<─────┤   gemini_      │  omdb_   │
          │  (CSV/SQLite)   │      │   client.py    │ client.py│
          └────────┬────────┘      │   (AI API)     │ (REST)   │
                   │               └────────────────┴──────────┘
                   v
          ┌────────┴────────┐
          │    server.py    │
          │   (HTTP API)    │
          └────────┬────────┘
                   │
                   v
          ┌────────┴────────┐
          │  web/index.html │
          │   (Frontend)    │
          └─────────────────┘
```

---

## Module Details

### 1. `config.py` - Configuration Hub

**Purpose**: Centralized settings for the entire application.

**Key Variables**:

| Variable | Type | Description |
|----------|------|-------------|
| `MOVIE_DIRECTORY` | Path | Root directory to scan (default: `E:/`) |
| `PROJECT_ROOT` | Path | Absolute path to project root |
| `DATA_DIR` | Path | Directory for CSV/SQLite files |
| `WEB_DIR` | Path | Directory for HTML/CSS/JS files |
| `CSV_FILE` | Path | Path to `movies.csv` |
| `SQLITE_FILE` | Path | Path to `movies.db` |
| `VIDEO_EXTENSIONS` | Set | Supported video formats (.mp4, .mkv, etc.) |
| `VLC_PATH` | str | Path to VLC executable |
| `GEMINI_API_KEY` | str | Loaded from `.env` |
| `OMDB_API_KEY` | str | Loaded from `.env` |
| `AI_REQUEST_DELAY` | float | Seconds between API calls (rate limiting) |
| `BATCH_SIZE` | int | Movies per batch (default: 50) |
| `AI_MODEL` | str | Model for formatting (default: `gemini-2.5-flash`) |
| `AI_SEARCH_MODEL` | str | Model for searching (default: `gemini-2.5-flash-native-audio-preview-12-2025`) |
| `SERVER_PORT` | int | HTTP server port (default: 8010) |
| `NOISE_PATTERNS` | list | Regex patterns to strip from filenames |
| `YEAR_PATTERN` | str | Regex to extract 4-digit years |

**Dependencies**: `os`, `pathlib`, `dotenv`

---

### 2. `scanner.py` - File System Scanner

**Purpose**: Recursively scans directories for video files.

**Functions**:

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_video_file(file_path)` | `Path` | `bool` | Checks extension against `VIDEO_EXTENSIONS` |
| `scan_directory(root_dir)` | `Path` | `Generator[Dict]` | Yields `{file_name, directory, full_path}` for each video |
| `get_all_videos(root_dir)` | `Path` | `List[Dict]` | Wrapper that returns list instead of generator |

**Error Handling**:
- Catches `PermissionError` for system folders
- Skips hidden files (`.` prefix) and system files (`$` prefix)
- Logs warnings without stopping scan

**Dependencies**: `config.py` (for `MOVIE_DIRECTORY`, `VIDEO_EXTENSIONS`)

---

### 3. `parser.py` - Filename Parser

**Purpose**: Extracts movie title and year from messy filenames.

**Functions**:

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `clean_filename(filename)` | `str` | `str` | Removes extension, noise patterns, normalizes spaces |
| `extract_year(text)` | `str` | `str` | Extracts valid year (1920-2030) or "NA" |
| `extract_movie_name(filename, year)` | `str, str` | `str` | Extracts title, removes year from name |
| `parse_filename(filename)` | `str` | `Tuple[str, str]` | Returns `(name, year)` tuple |

**Algorithm**:
1. Remove file extension via `Path.stem`
2. Replace separators (`.`, `_`, `-`) with spaces
3. Apply each pattern in `NOISE_PATTERNS` (case-insensitive)
4. Extract year using regex
5. Split name at year boundary

**Dependencies**: `config.py` (for `NOISE_PATTERNS`, `YEAR_PATTERN`)

---

### 4. `storage.py` - Data Persistence Layer

**Purpose**: Manages dual-storage (CSV + SQLite) with synchronization.

**Schema** (30 columns):

```
Core: uuid, file_name, directory, full_path, is_active
Parsed: extracted_name, extracted_year
AI: ai_title, ai_year, ai_imdb_id
OMDb: title, year, genre, director, actors, plot, runtime, 
      language, country, awards, poster, imdb_rating, 
      box_office, imdb_id, additional_info
Metadata: created_at, updated_at
User: user_rating, user_tags
```

**Key Functions**:

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `init_csv()` | None | None | Creates CSV with headers if missing |
| `init_sqlite()` | None | None | Creates SQLite database with schema |
| `read_csv()` | None | `List[Dict]` | Read all CSV records |
| `append_to_csv(records)` | `List[Dict]` | `int` | Add new records, returns count |
| `update_csv(records)` | `List[Dict]` | None | Full CSV rewrite |
| `insert_to_sqlite(records)` | `List[Dict]` | `int` | Insert with duplicate skip |
| `update_sqlite_record(uuid, updates)` | `str, Dict` | None | Update single record |
| `get_all_movies_sqlite()` | None | `List[Dict]` | Fetch all movies |
| `get_movie_by_uuid(uuid)` | `str` | `Dict or None` | Fetch single movie |
| `get_unenriched_movies()` | None | `List[Dict]` | Movies with `is_active=1` |
| `get_movies_without_omdb()` | None | `List[Dict]` | Movies with `is_active=2` |
| `get_missing_movie_paths()` | None | `List[Dict]` | Movies where file doesn't exist |
| `remove_missing_movies()` | None | `int` | Delete orphan records |
| `save_movies(records)` | `List[Dict]` | `int` | Save to both storages |
| `sync_csv_to_sqlite()` | None | None | Sync CSV → SQLite |

**is_active State Machine**:

| Value | State | Meaning |
|-------|-------|---------|
| 0 | Ignored | Will not be processed |
| 1 | Pending AI | New scan, awaiting AI enrichment |
| 2 | Pending OMDb | AI complete, awaiting OMDb |
| 3 | Complete | Fully enriched |
| 4 | Failed | OMDb lookup failed |

**Dependencies**: `csv`, `sqlite3`, `uuid`, `config.py`

---

### 5. `gemini_client.py` - AI Integration

**Purpose**: 2-step AI pipeline for movie identification.

**Architecture**:

```
Step 1: Live API + Search Grounding
   Model: gemini-2.5-flash-native-audio-preview-12-2025
   Input: Filename + parsed data
   Output: Audio transcription with movie details

Step 2: JSON Formatter
   Model: gemini-2.5-flash
   Input: Transcription text
   Output: Structured JSON {movie_title, year, imdb_id}
```

**Functions**:

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_client()` | None | `genai.Client` | Singleton client instance |
| `get_search_transcript(file_name, extracted_name, extracted_year)` | `str, str, str` | `str` | Async Live API call |
| `format_with_gemma(transcript)` | `str` | `Dict` | Format transcript to JSON |
| `extract_fallback(text)` | `str` | `Dict` | Regex fallback for IMDb ID |
| `identify_movie_async(...)` | `str, str, str` | `Dict` | Full async pipeline |
| `identify_movie(...)` | `str, str, str` | `Dict` | Sync wrapper |
| `batch_identify_movies(movies, delay)` | `list, float` | `list` | Sequential processing |
| `identify_movies_bulk(movies)` | `list` | `list` | Single API call bulk mode |

**Output Format**:
```json
{
  "movie_title": "The Matrix",
  "year": "1999",
  "imdb_id": "tt0133093",
  "confidence": "high",
  "reasoning": "Based on Google Search..."
}
```

**Dependencies**: `google-genai`, `asyncio`, `config.py`

---

### 6. `omdb_client.py` - OMDb API Client

**Purpose**: Fetches movie metadata from Open Movie Database.

**Functions**:

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `fetch_by_imdb_id(imdb_id)` | `str` | `Dict` | Fetch by IMDb ID (most accurate) |
| `fetch_by_title(title, year)` | `str, str` | `Dict` | Fallback search by title |
| `get_default_response()` | None | `Dict` | Returns all "NA" fields |
| `parse_omdb_response(data)` | `Dict` | `Dict` | Normalize OMDb → internal schema |
| `fetch_movie_data(imdb_id, title, year)` | `str, str, str` | `Dict` | Combined fetch with fallback |

**Output Fields**:
```
title, year, genre, director, actors, plot, runtime,
language, country, awards, poster, imdb_rating, box_office,
imdb_id, additional_info
```

**Dependencies**: `requests`, `config.py`

---

### 7. `enricher.py` - Pipeline Orchestrator

**Purpose**: Coordinates AI and OMDb enrichment workflow.

**Functions**:

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `verify_match(ai_title, ai_year, omdb_title, omdb_year)` | `str x4` | `bool` | Title/year fuzzy matching |
| `enrich_with_ai(limit)` | `int or None` | `int` | Process pending AI enrichments |
| `enrich_with_ai_bulk(limit)` | `int or None` | `int` | Bulk mode (50 per call) |
| `enrich_with_omdb(limit)` | `int or None` | `int` | Process pending OMDb enrichments |
| `full_enrichment(limit)` | `int or None` | `Dict` | Run full pipeline |
| `sync_sqlite_to_csv()` | None | None | Sync database to CSV |

**Workflow**:
```
1. Get movies with is_active=1
2. Call gemini_client.identify_movie()
3. Update AI fields, set is_active=2
4. Get movies with is_active=2
5. Call omdb_client.fetch_movie_data()
6. Update OMDb fields, set is_active=3 (or 4 if failed)
7. Sync SQLite → CSV
```

**Dependencies**: `gemini_client.py`, `omdb_client.py`, `storage.py`, `config.py`

---

### 8. `server.py` - HTTP Server

**Purpose**: Serves web interface and handles API requests.

**Endpoints**:

| Method | Path | Parameters | Response |
|--------|------|------------|----------|
| GET | `/` | None | `index.html` |
| GET | `/api/movies` | None | JSON array of all movies |
| GET | `/play?id={uuid}` | uuid | Launches VLC |
| GET | `/api/open-folder?id={uuid}` | uuid | Opens Explorer |
| POST | `/api/manual-enrich` | `{uuid, imdb_id, title, year}` | Updates movie via OMDb |
| POST | `/api/update-metadata` | `{uuid, user_rating, user_tags}` | Updates user fields |

**Content Types Served**:
- `.html` → `text/html`
- `.css` → `text/css`
- `.js` → `application/javascript`
- `.png` → `image/png`
- `.ico` → `image/x-icon`

**Dependencies**: `http.server`, `subprocess`, `storage.py`, `omdb_client.py`, `config.py`

---

### 9. `main.py` - CLI Entry Point

**Purpose**: Command-line interface for all operations.

**Arguments**:

| Flag | Description |
|------|-------------|
| `--scan` | Scan directory for videos |
| `--limit N` | Limit items to process |
| `--stats` | Show database statistics |
| `--sample N` | Show N sample records |
| `--sync` | Sync CSV to SQLite |
| `--check-missing` | Preview missing files |
| `--cleanup` | Remove missing entries |
| `--enrich` | AI enrichment |
| `--bulk` | Use bulk mode with --enrich |
| `--fetch-omdb` | OMDb enrichment |
| `--full-enrich` | Full pipeline |
| `--server` | Start web server |

**Dependencies**: All modules

---

### 10. `web/index.html` - Frontend SPA

**Purpose**: Single-page application for browsing movies.

**Key Features**:

| Feature | Implementation |
|---------|----------------|
| Movie Grid | CSS Grid with auto-fill |
| Lazy Loading | `data-src` + click-to-load |
| Filters | Client-side filtering (no API calls) |
| Search | Real-time text matching |
| Poster Toggle | Hide posters for performance |
| View Modes | Grid, List, Wall via CSS classes |
| Info Modal | Dynamic content injection |
| Search Modal | Manual OMDb search interface |
| Randomization | Fisher-Yates shuffle on load |

**API Calls**:
- `GET /api/movies` - Load all movies
- `GET /play?id={uuid}` - Play button
- `GET /api/open-folder?id={uuid}` - Folder button
- `POST /api/manual-enrich` - Search modal submit

**CSS Variables**:
```css
--bg-color: #0a0a0f        /* Deep black */
--card-bg: rgba(30,30,46,0.8)
--accent: #bb86fc          /* Purple */
--success: #4caf50
--warning: #ffc107
```

---

## Data Flow

```
[Video Files on Disk]
         │
         v
    scanner.py ──────────────> [file_name, directory, full_path]
         │
         v
    parser.py ───────────────> [extracted_name, extracted_year]
         │
         v
    storage.py ──────────────> movies.csv + movies.db (is_active=1)
         │
         v
    gemini_client.py ────────> [ai_title, ai_year, ai_imdb_id] (is_active=2)
         │
         v
    omdb_client.py ──────────> [title, year, genre, poster, ...] (is_active=3)
         │
         v
    server.py ───────────────> JSON API
         │
         v
    web/index.html ──────────> Visual Display
```

---

## Error Handling Strategy

| Module | Strategy |
|--------|----------|
| `scanner.py` | Log warning, skip file, continue |
| `parser.py` | Return "NA" for unparseable data |
| `gemini_client.py` | Return default_result_na(), log error |
| `omdb_client.py` | Return get_default_response(), log warning |
| `storage.py` | Raise exception (critical path) |
| `server.py` | send_error() with HTTP status code |

---

## Testing

Each module has a `if __name__ == "__main__":` block for standalone testing:

```bash
# Test scanner
python scanner.py

# Test parser
python parser.py

# Test Gemini client
python gemini_client.py

# Test OMDb client
python omdb_client.py

# Test storage
python storage.py

# Test enricher
python enricher.py
```
