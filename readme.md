# 🎬 Movie Library Manager

A robust, AI-powered system for indexing, enriching, and viewing your local movie collection.

## 🚀 Quick Start

1.  **Configure API Keys**: Open `.env` and add your keys:
    ```env
    GEMINI_API_KEY=your_key_here
    OMDB_API_KEY=your_key_here
    ```
2.  **Run the Manager**: Double-click `MovieLibrary.bat`.
3.  **Scan Movies**: Select Option `[1]` to scan your `E:/` drive. New movies start as `is_active=1` (Active for enrichment).
4.  **Manage Database**: Use Option `[D]` to clean up any movies that you've deleted from your drive.
5.  **Enrich Data**: Select Option `[C]` to run AI + OMDb enrichment for active movies. Completed movies are marked `is_active=2`.
6.  **View Library**: Select Option `[S]` to start the web server, then go to `http://localhost:8010`.

## 🛠 Features

*   **Recursive Scanning**: Deep scan of your drive for all video formats.
*   **Database Cleanup**: Automatically detects and removes entries for files that no longer exist on disk.
*   **2-Step AI Identification**:
    *   **Step 1**: Uses Gemini 2.5 Flash (Native Audio) + Google Search Grounding to find exact match details.
    *   **Step 2**: Uses Gemma 3 27B to structure the findings into clean data.
*   **OMDb Integration**: Fetches posters, plot, genre, language, country, and ratings.
*   **Manual Search**: One-click 🔍 button in the web UI to manually fetch/fix movie details via IMDb ID or Title search.
*   **Smart Storage**: Dual-layer storage (CSV for source of truth, SQLite for fast browsing).
*   **Selective Enrichment**: Control processing with the `is_active` flag (0=Ignore, 1=Pending, 2=Complete).
*   **Web Dashboard**: 
    *   **Premium UI**: Dark-mode with glassmorphism and smooth animations.
    *   **Filters**: Instant filtering by Genre, Decade, and Language tags.
    *   **Performance**: Lazy loading and poster toggles for lightning-fast browsing of large collections.
    *   **VLC Playback**: One-click "Play" button launches your local VLC player.

## 📁 Repository Structure

*   `main.py`: Entry point for all CLI operations.
*   `MovieLibrary.bat`: User-friendly menu for non-technical users.
*   `server.py`: Background server for the web interface and API.
*   `data/`: Stores your `movies.csv` and `movies.db`.
*   `web/`: Contains the frontend dashboard (`index.html`).

## ⚖️ License
MIT License - Created for local media management enthusiasts.
