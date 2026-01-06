# 🎬 Movie Library Manager

A robust, AI-powered system for indexing, enriching, and viewing your local movie collection.

---

## 📦 Prerequisites

Before running the Movie Library Manager, ensure you have the following installed:

- **Python 3.9+** - [Download Python](https://www.python.org/downloads/)
- **VLC Media Player** - [Download VLC](https://www.videolan.org/) (for playback functionality)
- **Git** (optional) - For version control

### Required Python Packages

Install dependencies using pip:

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes:
- `google-genai` - Gemini AI client
- `requests` - HTTP client for OMDb API
- `python-dotenv` - Environment variable management

---

## 🔐 Configuration

### Step 1: Create Environment File

Create a `.env` file in the project root with your API keys:

```env
# Google Gemini API Key (required for AI enrichment)
# Get yours at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# OMDb API Key (required for movie metadata)
# Get yours at: https://www.omdbapi.com/apikey.aspx
OMDB_API_KEY=your_omdb_api_key_here
```

### Step 2: Configure Paths (Optional)

Edit `config.py` to customize:

```python
# Directory to scan for movies (default: E:/)
MOVIE_DIRECTORY = Path("E:/")

# VLC executable path
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

# Web server port
SERVER_PORT = 8010
```

---

## 🚀 Quick Start

### Option A: Using the Batch File (Recommended)

1. Double-click `MovieLibrary.bat`
2. Select from the menu:
   - `[1]` Scan - Index all movies from your drive
   - `[C]` Enrich - Run AI + OMDb enrichment pipeline
   - `[S]` Server - Start web viewer at `http://localhost:8010`
   - `[D]` Cleanup - Remove deleted movie entries

### Option B: Using Command Line

```bash
# Scan for movies
python main.py --scan

# Scan with limit (for testing)
python main.py --scan --limit 50

# Run AI enrichment
python main.py --enrich --limit 10

# Run bulk AI enrichment (faster, uses single API call)
python main.py --enrich --bulk --limit 100

# Fetch OMDb metadata
python main.py --fetch-omdb --limit 10

# Run full pipeline (AI + OMDb)
python main.py --full-enrich

# Start web server
python main.py --server

# Show database statistics
python main.py --stats

# Check for missing files
python main.py --check-missing

# Remove missing movie entries
python main.py --cleanup
```

---

## 🌐 Web Viewer

Once the server is running, open your browser to:

```
http://localhost:8010
```

### Features:

| Feature | Description |
|---------|-------------|
| 🔍 **Search** | Real-time filtering across titles, actors, genres |
| 📂 **Filters** | Filter by Genre, Decade, and Language |
| ▶ **Play** | Launch movies directly in VLC |
| 📂 **Open Folder** | Open containing folder in Explorer |
| 🔍 **Manual Search** | Manually search/fix movie data via OMDb |
| ℹ **Info** | View full movie details in modal |
| 👁️ **Views** | Toggle Grid/List/Wall view modes |
| 🖼️ **Posters** | Toggle poster visibility for performance |

---

## 🛠 Features

### Scanning & Indexing
- **Recursive Scanning**: Deep scan of your drive for all video formats
- **Smart Parsing**: Extracts title and year from messy filenames
- **Duplicate Prevention**: Skip already-indexed files automatically

### AI-Powered Enrichment
- **2-Step Pipeline**:
  1. **Gemini 2.5 Flash + Google Search** - Finds exact movie match with IMDb ID
  2. **Gemma 3 27B** - Structures results into clean JSON
- **Bulk Mode**: Process up to 100 movies in a single API call

### OMDb Integration
- Fetches: Poster, Plot, Genre, Director, Actors, Runtime, Language, Country, Awards, Ratings
- IMDb-verified metadata for accuracy

### Database Management
- **Cleanup**: Automatically detects and removes entries for deleted files
- **State Tracking**: `is_active` flag tracks enrichment progress (0-4)
- **Dual Storage**: CSV for portability + SQLite for speed

### Web Dashboard
- **Premium Dark UI**: Glassmorphism effects and smooth animations
- **Performance**: Lazy loading for large collections (1000+ movies)
- **VLC Integration**: One-click playback

---

## 📁 Repository Structure

```
📂 0_Movie_Project/
├── 📄 main.py              # CLI entry point
├── 📄 server.py            # HTTP server for web viewer
├── 📄 config.py            # Centralized configuration
├── 📄 scanner.py           # File system scanner
├── 📄 parser.py            # Filename parser
├── 📄 enricher.py          # Enrichment pipeline orchestrator
├── 📄 gemini_client.py     # Gemini AI integration
├── 📄 omdb_client.py       # OMDb API client
├── 📄 storage.py           # CSV/SQLite data layer
├── 📄 MovieLibrary.bat     # Windows batch launcher
├── 📄 requirements.txt     # Python dependencies
├── 📄 .env                 # API keys (create this)
├── 📂 web/                 # Frontend files
│   ├── index.html          # Main viewer page
│   ├── enrichment.html     # Enrichment manager
│   └── favicon.png         # Browser tab icon
└── 📂 data/                # Generated data
    ├── movies.csv          # Source of truth
    └── movies.db           # SQLite database
```

---

## 🔄 Enrichment Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  SCAN       │ => │  AI ENRICH  │ => │  OMDb FETCH │ => │  COMPLETE   │
│  is_active=1│    │  is_active=2│    │  is_active=3│    │  Web Ready  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                      │
                                      v (if failed)
                                ┌─────────────┐
                                │  FAILED     │
                                │  is_active=4│
                                └─────────────┘
```

---

## 🐞 Troubleshooting

| Issue | Solution |
|-------|----------|
| "VLC not found" | Update `VLC_PATH` in `config.py` |
| "API key not set" | Add keys to `.env` file |
| "Permission denied" | Run as Administrator or check folder permissions |
| Movies not showing | Run `--sync` to refresh database |
| Slow browsing | Disable auto-images in viewer (⚡ button) |

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

**In brief:**
- ✅ You can freely use, modify, and distribute this software
- ✅ You can use it for commercial purposes
- ⚠️ Any modifications must also be open-sourced under GPL v3
- ⚠️ No warranty is provided

For the full license text, see: https://www.gnu.org/licenses/gpl-3.0.html

---

## 🤝 Contributing

Contributions are welcome! Please see the code documentation in:
- `context_readme.md` - Project philosophy and design goals
- `code_readme.md` - Technical implementation details
