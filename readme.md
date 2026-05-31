# 🎬 Movie Library Manager

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

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
- `requests` - HTTP client for OMDb API (and the Groq provider, which uses Groq's OpenAI-compatible REST API)
- `python-dotenv` - Environment variable management

> The optional Groq AI provider needs no extra packages — it talks to Groq's HTTP API using `requests`, which is already installed.

---

## 🔐 Configuration

### Step 1: Create Environment File

Create a `.env` file in the project root with your API keys:

```env
# Google Gemini API Key (required for AI enrichment with the default provider)
# Get yours at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# OMDb API Key (required for movie metadata)
# Get yours at: https://www.omdbapi.com/apikey.aspx
OMDB_API_KEY=your_omdb_api_key_here

# Groq API Key (OPTIONAL - only needed when using the Groq AI provider)
# Get yours at: https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here

# AI provider to use for identification (OPTIONAL, default: gemini)
# Accepts "gemini" or "groq". Can also be overridden per-run with --provider.
AI_PROVIDER=gemini
```

**API key summary:**

| Key | Required? | Used by |
|-----|-----------|---------|
| `GEMINI_API_KEY` | Required for Gemini AI enrichment (the default provider) | `--enrich`, `--full-enrich` |
| `OMDB_API_KEY` | Required for all metadata fetching | `--fetch-omdb`, `--full-enrich`, `--retry-failed` |
| `GROQ_API_KEY` | Optional — only when using the Groq provider | `--provider groq` |
| `AI_PROVIDER` | Optional — defaults to `gemini` | selects the default AI backend |

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
   - `[1]` Full Scan - Index all movies from your drive
   - `[A]` AI Enrichment - Identify movies with AI
   - `[B]` OMDb Enrichment - Fetch metadata from OMDb
   - `[C]` Full Enrichment - AI + OMDb pipeline (line by line)
   - `[K]` Bulk AI Enrichment - Faster, single-call AI mode
   - `[L]` Full Bulk Enrichment - Bulk AI + OMDb
   - `[F]` Retry Failed OMDb Enrichments - Re-run movies that failed (state 4)
   - `[S]` Server - Start web viewer at `http://localhost:8010`
   - `[D]` Cleanup - Remove deleted movie entries

> The AI actions (`[A]`, `[C]`, `[K]`, `[L]`) prompt you to choose a provider/model:
> Gemini 2.5 Flash (default), Gemini 3.5 Flash, Groq Llama 3.3 70B, Groq Compound
> (web-search grounded), or a custom Groq model id. The Groq options require
> `GROQ_API_KEY` in `.env`.

### Option B: Using Command Line

```bash
# Scan for movies
python main.py --scan

# Scan with limit (for testing)
python main.py --scan --limit 50

# Run AI enrichment (uses the configured/default provider)
python main.py --enrich --limit 10

# Run bulk AI enrichment (faster, uses single API call)
python main.py --enrich --bulk --limit 100

# Choose the AI provider and model for a run
python main.py --enrich --provider gemini --model 2.5      # Gemini 2.5 Flash (default)
python main.py --enrich --provider gemini --model 3.5      # Gemini 3.5 Flash
python main.py --enrich --provider groq --model llama-3.3-70b-versatile
python main.py --enrich --provider groq --model groq/compound   # web-search grounded

# Fetch OMDb metadata
python main.py --fetch-omdb --limit 10

# Run full pipeline (AI + OMDb)
python main.py --full-enrich

# Retry movies that previously failed OMDb (state 4 -> 2, re-run OMDb)
python main.py --retry-failed

# Start web server
python main.py --server

# Show database statistics
python main.py --stats

# Check for missing files
python main.py --check-missing

# Remove missing movie entries
python main.py --cleanup
```

### CLI Flags Reference

| Flag | Description |
|------|-------------|
| `--scan` | Scan `MOVIE_DIRECTORY` for video files and index them |
| `--limit N` | Limit the number of items processed (works with most operations) |
| `--enrich` | Run AI identification on pending movies (state 1) |
| `--bulk` | With `--enrich`: use single-call bulk mode (chunked by `BATCH_SIZE`) |
| `--fetch-omdb` | Fetch OMDb metadata for AI-identified movies (state 2) |
| `--full-enrich` | Run the full pipeline (AI + OMDb) |
| `--retry-failed` | Reset failed movies (state 4 → 2) and re-run OMDb |
| `--provider {gemini,groq}` | Choose the AI provider for this run (default: `AI_PROVIDER`) |
| `--model M` | Model to use. Gemini shortcuts: `2.5`, `3.5`; otherwise a full model id (e.g. `llama-3.3-70b-versatile`, `groq/compound`). For Gemini this sets the formatter/bulk model; the Live-API search model is `AI_SEARCH_MODEL` (configured separately). |
| `--sync` | Sync the CSV source of truth into SQLite |
| `--stats` | Show database statistics (including state breakdown) |
| `--sample N` | Print N sample records |
| `--check-missing` | Preview database entries whose files no longer exist |
| `--cleanup` | Remove database entries for missing files |
| `--server` | Start the web viewer server |

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
- **Two AI providers** (choose via `AI_PROVIDER` config or `--provider`):
  - **Gemini** (default) — a 2-step pipeline:
    1. **Gemini search model** (`AI_SEARCH_MODEL`, a Live-API model with Google Search grounding) finds the exact movie match and IMDb ID
    2. **Gemini formatter model** (`AI_MODEL`, default `gemini-2.5-flash`) structures the result into clean JSON
  - **Groq** — fast open models (default `llama-3.3-70b-versatile`) via Groq's OpenAI-compatible API. Standard models identify from the model's own knowledge (OMDb still verifies by title/year); the `groq/compound` models add built-in web-search grounding.
- **OMDb verifies everything**: the AI step only needs to produce a clean official title + year (and an IMDb ID when confident); OMDb is the authoritative metadata source.
- **Bulk Mode**: identify many movies in a single API call (chunk size set by `config.BATCH_SIZE`, default 50 — lower it if a bulk run stalls).
- **Resilience**: per-request timeout (`AI_TIMEOUT_SECONDS`, 120s) and automatic backoff/retry on HTTP 429 (rate limit).

### OMDb Integration
- Fetches: Poster, Plot, Genre, Director, Actors, Runtime, Language, Country, Awards, Ratings
- IMDb-verified metadata for accuracy

### Database Management
- **Cleanup**: Automatically detects and removes entries for deleted files
- **State Tracking**: `is_active` flag tracks enrichment progress (see the state table below)
- **Retry**: `--retry-failed` recovers movies that failed OMDb (state 4)
- **Dual Storage**: CSV for portability + SQLite for speed

### Web Dashboard
- **Premium Dark UI**: Glassmorphism effects and smooth animations
- **Performance**: Lazy loading for large collections (1000+ movies)
- **VLC Integration**: One-click playback
- **Multi-threaded server**: handles concurrent requests so the UI stays responsive
- **Security-hardened**: binds to `localhost` by default; side-effecting actions
  (`/play`, `/api/open-folder`) are **POST-only** to prevent cross-site triggering;
  serves a Content-Security-Policy plus `X-Content-Type-Options`, `X-Frame-Options`,
  and `Referrer-Policy` headers; static serving is confined to `web/` (path-traversal safe)

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
├── 📄 ai_provider.py       # AI provider dispatcher (Gemini / Groq)
├── 📄 gemini_client.py     # Gemini AI integration
├── 📄 groq_client.py       # Groq AI integration (alternative provider)
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

### `is_active` State Machine

| State | Meaning | Set by |
|-------|---------|--------|
| `0` | Ignored — not a movie / skipped, never processed | manual / parser |
| `1` | Pending AI identification | scan |
| `2` | AI done, pending OMDb metadata | AI enrichment |
| `3` | Success — fully enriched, shown in web viewer | OMDb enrichment |
| `4` | Failed — OMDb could not match it (needs manual fix or retry) | OMDb enrichment |

`--retry-failed` (menu `[F]`) resets state `4` → `2` and re-runs the OMDb pass.
This recovers transient failures and matches that now succeed via a verified AI
IMDb ID. Movies that still can't be matched return to state `4` and are best
fixed with the web viewer's **Manual Search**.

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

Contributions are welcome! Please see the documentation in:
- [DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md) - Project philosophy and design goals
- [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) - Technical implementation details
- [CONTRIBUTING.md](CONTRIBUTING.md) - Guidelines for contributors
