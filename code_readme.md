# 💻 Code Functionality

## Modular Architecture

The system is split into specialized modules for maximum maintainability:

### 1. `scanner.py`
Uses `os.walk` to recursively scan directories. It filters files based on `VIDEO_EXTENSIONS` defined in `config.py`. It handles Permission Errors gracefully.

### 2. `parser.py`
Uses complex Regular Expressions (Regex) to strip "noise" from filenames (e.g., `1080p`, `x264`). It targets Title and Year patterns to provide a starting point for the AI.

### 3. `gemini_client.py`
The AI heart of the system.
*   **Step 1**: Connects to Gemini Live API with Google Search Grounding to find exact match details.
*   **Step 2**: The transcript is passed to `gemma-3-27b-it` for strict JSON formatting.
*   **Result**: Returns clean `movie_title`, `year`, and `imdb_id`.

### 4. `omdb_client.py`
Standard REST client for the OMDb API. It prioritizes IMDb ID lookups for 100% accuracy and falls back to Title+Year searches.

### 5. `storage.py`
The Persistence Layer managing both `data/movies.csv` and `data/movies.db` (SQLite).
*   **Orphan Management**: Includes `remove_missing_movies()` to synchronize the database with the physical drive.
*   **Enrichment States**: Tracks `is_active` (0: Ignored, 1: Pending, 2: Fully Processed).

### 6. `enricher.py`
Orchestrates the workflow between the Parser, Gemini, and OMDb. It updates `is_active` to `2` only once all metadata is successfully stored.

### 7. `server.py`
Built on Python's native `http.server`.
*   **GET Routes**: Serves the UI, movie list, and handles the `/play` trigger for VLC.
*   **POST Routes**: Features a `/api/manual-enrich` endpoint that allows the web interface to push manual OMDb search results directly into the database and CSV.
*   **System Call**: Uses `subprocess.Popen` to launch the local VLC executable.

### 8. `web/index.html`
A single-page application (SPA) built with vanilla JS and CSS.
*   **Lazy Loading**: Posters only load when requested or clicked, preventing browser hangs on large libraries.
*   **Metadata Filtering**: Dynamically generates Genre, Decade, and Language filters based on the specific movies in your collection.
*   **Search**: Real-time filtering across titles, actors, and filenames.

### 9. `config.py`
Centralized settings for paths, API keys, rate limits, and allowed video extensions.
